"""16 nm failure validation: reading versus first functional error on the tapped chain.

Input: data/au15p_tap/tap_<tag>_<stamp>.csv written by bench/tapbench.py (one row per 1 s window).
For every shmoo point (phase "point<i>") and tap j it aggregates the windows:
  reading  = mean phase-step count over the sweeps in which the tap alarmed
  got      = fraction of sweeps with an alarm (1 for a tap with a valid reading)
  err_rate = cycles with FF2 != expected / cycles observed (1e8 per window)
and classifies the tap: FAIL (err > 0), ZERO (no error, every sweep alarmed at step 0) or OK.
Per tap and sweep direction:
  V_f   highest VCCINT with errors; V_pass the lowest error-free VCCINT above it
  V_0   VCCINT where the reading reaches zero: straight line through the last error-free points
        with a positive reading, extrapolated to zero (V_0z: highest VCCINT read as ZERO)
  margin = V_0 - (V_f + V_pass) / 2, +-5 mV from the 10 mV PMIC step
"""
from __future__ import annotations

import csv
import glob
import json
import os
from dataclasses import dataclass, field

import numpy as np

from common import DATA, STEP_TAP_PS, V

TAPDIR = os.path.join(DATA, "au15p_tap")
N_TAPS = 23
STAGES = [24, 48] + [70 + 4 * k for k in range(21)]
CYCLES_PER_WINDOW = 100_000_000


def sysmon_v(raw: str) -> float | None:
    """UltraScale+ SYSMON supply code (16-bit register, 3 V full scale) -> volts."""
    try:
        return int(raw, 16) / 65536.0 * 3.0
    except (TypeError, ValueError):
        return None


@dataclass
class Point:
    idx: int
    vc_cmd: float
    vccint: float
    vccint_raw: float | None
    temp: float
    windows: int
    sweeps: int
    sat: int
    reading: np.ndarray = field(default_factory=lambda: np.full(N_TAPS, np.nan))
    rmin: np.ndarray = field(default_factory=lambda: np.full(N_TAPS, np.nan))
    rmax: np.ndarray = field(default_factory=lambda: np.full(N_TAPS, np.nan))
    got_frac: np.ndarray = field(default_factory=lambda: np.zeros(N_TAPS))
    err_rate: np.ndarray = field(default_factory=lambda: np.zeros(N_TAPS))

    def state(self, j: int) -> str:
        if self.err_rate[j] > 0:
            return "FAIL"
        if self.got_frac[j] > 0.999 and self.rmax[j] == 0:
            return "ZERO"
        if self.got_frac[j] < 0.999:
            return "NOALARM"
        return "OK"


def load(path: str) -> tuple[list[Point], dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    meta = {}
    if os.path.exists(path + ".json"):
        with open(path + ".json") as f:
            meta = json.load(f)
    pts: dict[int, list[dict]] = {}
    for r in rows:
        if r["phase"].startswith("point"):
            pts.setdefault(int(r["phase"][5:]), []).append(r)
    out = []
    for i in sorted(pts):
        ws = pts[i]
        vr = [sysmon_v(w["vccint_raw"]) for w in ws]
        vr = [x for x in vr if x is not None]
        p = Point(idx=i, vc_cmd=float(ws[0]["vc_cmd"]),
                  vccint=float(np.mean([float(w["vccint_v"]) for w in ws])),
                  vccint_raw=float(np.mean(vr)) if vr else None,
                  temp=float(np.mean([float(w["temp_c"]) for w in ws])),
                  windows=len(ws), sweeps=sum(int(w["sweeps"]) for w in ws),
                  sat=sum(int(w["sat"]) for w in ws))
        for j in range(N_TAPS):
            g = np.array([int(w[f"t{j}_got"]) for w in ws])
            sw = np.array([int(w["sweeps"]) for w in ws])
            e = np.array([int(w[f"t{j}_err"]) for w in ws])
            m = np.array([float(w[f"t{j}_mean"]) if w[f"t{j}_mean"] else np.nan for w in ws])
            mn = [int(w[f"t{j}_min"]) for w in ws if w[f"t{j}_min"] != ""]
            mx = [int(w[f"t{j}_max"]) for w in ws if w[f"t{j}_max"] != ""]
            p.got_frac[j] = g.sum() / max(sw.sum(), 1)
            if g.sum():
                ok = g > 0
                p.reading[j] = float(np.sum(m[ok] * g[ok]) / g[ok].sum())
                p.rmin[j] = min(mn)
                p.rmax[j] = max(mx)
            p.err_rate[j] = e.sum() / (len(ws) * CYCLES_PER_WINDOW)
        out.append(p)
    return out, meta


def vaxis(p: Point) -> float:
    return p.vccint_raw if p.vccint_raw is not None else p.vccint


def boundaries(pts: list[Point], j: int) -> dict:
    """V_0, V_f and the margin of tap j on one monotonic sweep (points in measurement order)."""
    seq = sorted(pts, key=vaxis, reverse=True)          # high -> low voltage
    states = [p.state(j) for p in seq]
    vs = np.array([vaxis(p) for p in seq])
    res = {"tap": j, "stage": STAGES[j], "V_f": None, "V_pass": None, "V_0": None, "V_0z": None,
           "fails": "FAIL" in states, "slope_cnt_per_V": None}
    if "FAIL" in states:
        k = states.index("FAIL")
        res["V_f"] = float(vs[k])
        if k > 0:
            res["V_pass"] = float(vs[k - 1])
        # any error-free point below a failing one? (non-monotonic boundary)
        res["reentrant"] = any(s != "FAIL" for s in states[k + 1:])
    zeros = [vs[i] for i, s in enumerate(states) if s == "ZERO"]
    if zeros:
        res["V_0z"] = float(max(zeros))
    okpts = [(vs[i], seq[i].reading[j]) for i, s in enumerate(states)
             if s == "OK" and seq[i].reading[j] > 0 and (res["V_f"] is None or vs[i] > res["V_f"])]
    if len(okpts) >= 2:
        okpts = sorted(okpts)[:4]                       # the four lowest-voltage positive readings
        x = np.array([a for a, _ in okpts])
        y = np.array([b for _, b in okpts])
        k, b = np.polyfit(x, y, 1)
        res["slope_cnt_per_V"] = float(k)
        if k > 0:
            res["V_0"] = float(-b / k)
    if res["V_0"] is not None and res["V_f"] is not None and res["V_pass"] is not None:
        res["margin_mV"] = (res["V_0"] - 0.5 * (res["V_f"] + res["V_pass"])) * 1000.0
    return res


def margin_steps(pts: list[Point], j: int) -> dict | None:
    """Sensor offset at failure for tap j on one monotonic sweep, in phase steps.

    The reading of the error-free points with a positive reading is fitted with a straight line
    (local slope k, steps per volt, from the lowest three such points) and extrapolated to the
    failure voltage V* (rule below). m = -r(V*): m > 0 means the reading had
    already reached zero when the first error appeared (sensor early, a warning margin); m < 0
    means errors appeared while the reading was still m steps above zero (sensor late). The
    uncertainty u is k (V_pass - V_f) / 2, from the 10 mV PMIC step."""
    b = boundaries(pts, j)
    if not b["fails"] or b["V_pass"] is None:
        return None
    seq = sorted(pts, key=vaxis, reverse=True)
    okp = [(vaxis(p), p.reading[j]) for p in seq
           if p.state(j) == "OK" and p.reading[j] > 0 and vaxis(p) > b["V_f"]]
    if len(okp) < 2:
        return None
    okp = sorted(okp)[:3]
    x = np.array([a for a, _ in okp])
    y = np.array([c for _, c in okp])
    k, c0 = np.polyfit(x, y, 1)
    if k <= 0:
        return None
    pf = next(p for p in seq if abs(vaxis(p) - b["V_f"]) < 1e-9)
    e_f = float(pf.err_rate[j])
    # The failure threshold lies in [V_f, V_pass]. With e(V_f) < 0.5 only the tail of one edge
    # fails at V_f, i.e. V_f sits within a few jitter sigmas (~1 mV) of the threshold: V* = V_f.
    # With e(V_f) >= 0.5 a whole edge already fails at V_f and the threshold is anywhere inside
    # the interval: V* = its middle. The bounds m_lo / m_hi always span the whole interval.
    vstar = b["V_f"] if e_f < 0.5 else 0.5 * (b["V_f"] + b["V_pass"])
    r_star = k * vstar + c0
    m_lo = -(k * b["V_pass"] + c0)
    m_hi = -(k * b["V_f"] + c0)
    zero_free = sum(1 for p in seq if p.state(j) == "ZERO" and vaxis(p) > b["V_f"])
    return {"tap": j, "stage": STAGES[j], "k_steps_per_mV": k / 1000.0, "V_0": -c0 / k,
            "V_f": b["V_f"], "V_pass": b["V_pass"], "V_star": vstar,
            "m_steps": -r_star, "m_lo": m_lo, "m_hi": m_hi,
            "u_steps": 0.5 * (m_hi - m_lo), "m_ps": -r_star * STEP_TAP_PS,
            "u_ps": 0.5 * (m_hi - m_lo) * STEP_TAP_PS,
            "m_mV": -r_star / k * 1000.0, "u_mV": 0.5 * (b["V_pass"] - b["V_f"]) * 1000,
            "zero_points": zero_free, "err_at_Vf": e_f,
            "r_at_Vf": float(pf.reading[j]), "rmin_at_Vf": float(pf.rmin[j]),
            "rmax_at_Vf": float(pf.rmax[j])}


def split_sweeps(pts: list[Point]) -> list[list[Point]]:
    """A --back shmoo is one down sweep and one up sweep that share the lowest point."""
    vs = [p.vc_cmd for p in pts]
    if len(vs) > 2 and vs[0] > vs[1] and vs[-1] > vs[-2]:
        k = int(np.argmin(vs))
        return [pts[:k + 1], pts[k:]]
    return [pts]


def latest(pattern: str) -> list[str]:
    files = sorted(glob.glob(os.path.join(TAPDIR, pattern)))
    if not files:
        raise FileNotFoundError(os.path.join(TAPDIR, pattern))
    return files


def summary_table(pts: list[Point]) -> str:
    rows = []
    for p in sorted(pts, key=vaxis, reverse=True):
        cells = []
        for j in range(N_TAPS):
            s = p.state(j)
            if s == "FAIL":
                cells.append(f"{'X' if p.err_rate[j] > 0.5 else 'x'}{p.err_rate[j]*100:3.0f}%")
            elif s == "ZERO":
                cells.append("   0 ")
            elif s == "NOALARM":
                cells.append("  -- ")
            else:
                cells.append(f"{p.reading[j]:5.0f}")
        rows.append(f"{p.vc_cmd:.2f} {vaxis(p):.4f} {p.temp:5.1f} | " + " ".join(cells))
    head = "Vc   VCCINT  die  | " + " ".join(f"S{s:<4d}" for s in STAGES)
    return "\n".join([head] + rows)


def run() -> dict:
    files = latest("tap_shmoo*.csv")
    out = {"files": files, "taps": []}
    for path in files[-1:]:
        pts, meta = load(path)
        print(summary_table(pts))
        for j in range(N_TAPS):
            out["taps"].append(boundaries(pts, j))
    return out


if __name__ == "__main__":
    import pprint
    r = run()
    pprint.pprint([t for t in r["taps"] if t["fails"]])
