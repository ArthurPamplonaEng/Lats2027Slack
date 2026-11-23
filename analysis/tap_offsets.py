"""Sensor offset at failure versus static timing, per tap and implementation (16 nm).

For every shmoo CSV (bench/tapbench.py) the implementation is taken from the bitstream path in its
.json metadata (build/impl = A, build/impl_aguard = A', build/impl_b = B, build/impl_c = C, ...;
build/impl_a14 = A at a 14 ns clock period, see IMPLS). The repetition of A on the second bench
session (tag shmooArep, 23/11) is labelled "Arep" and kept out of A, whose margins stay those of the
first session (20/11); it measures the day-to-day repeatability. For each tap that fails inside a
sweep, margin_steps() gives m (phase steps; > 0: the reading reached zero before the first error).
The prediction from the routed checkpoint of the same implementation is
    Delta_si = (s2 + U2 - CPR2) - (s1 + U1 - CPR1)        (slow corner, ns)
the FF2-minus-FF1 setup-slack difference without the analysis-only uncertainty U and clock
pessimism CPR, which are larger on the FF1 path because it crosses into the phase-swept clock.
"""
from __future__ import annotations

import csv
import glob
import json
import os

import numpy as np

from common import ROOT, STEP_TAP_PS
from tap_analysis import STAGES, TAPDIR, load, margin_steps, split_sweeps

BUILD = os.path.join(ROOT, "hw", "au15p_tap", "build")
# build folder -> implementation label. Placements A-D (four regions of the die, same RTL); a
# trailing number is the clock period in ns of a variant that changes only the MMCM dividers of the
# routed design (make_period.tcl; no number: 10 ns); ' and '' mark the designed guards
# (make_guard.tcl: 250 and 125 ps).
IMPLS = {"impl": "A", "impl_aguard": "A'", "impl_b": "B", "impl_bguard": "B'",
         "impl_bguard125": "B''", "impl_c": "C", "impl_d": "D"}
IMPLS.update({f"impl_{p}{t}": f"{p.upper()}{t}" for p in "ab" for t in (12, 14, 16, 18)})
IMPLS.update({f"impl_{p}{t}": f"{p.upper()}{t}" for p in "cd" for t in (14, 18)})
# repeated shmoos of an implementation on a later session: their own label, same STA model
REPEATS = {"shmooArep": ("Arep", "impl")}
BUILD_OF = {name: d for d, name in IMPLS.items()}
BUILD_OF.update({lab: d for lab, d in REPEATS.values()})


def impl_of(meta: dict) -> str | None:
    if meta.get("tag") in REPEATS:
        return REPEATS[meta["tag"]][0]
    bit = meta.get("bitstream", "")
    for d, name in IMPLS.items():
        if f"/build/{d}/" in bit:
            return name
    return None


def placement(label: str) -> str:
    return label[0]


def period_ns(label: str) -> int:
    """Clock period of an implementation label: A14 -> 14, A, A', Arep -> 10."""
    digits = "".join(c for c in label if c.isdigit())
    return int(digits) if digits else 10


def guarded(label: str) -> bool:
    return "'" in label


def sta_model(impl_dir: str, corner: str = "Slow") -> dict[int, dict]:
    path = os.path.join(BUILD, impl_dir, "taps_sta_detail.csv")
    out: dict[int, dict] = {}
    if not os.path.exists(path):
        return out
    rows = list(csv.DictReader(open(path)))
    by = {}
    for r in rows:
        if r["corner"] == corner:
            by[(int(r["tap"]), r["ff"])] = {k: float(v) for k, v in r.items()
                                             if k not in ("tap", "corner", "ff")}
    for j in range(len(STAGES)):
        if (j, "FF1") not in by:
            continue
        a, b = by[(j, "FF1")], by[(j, "FF2")]
        # setup time of each flip-flop as STA charges it (the slack equation solved for it)
        su = {k: q["requirement"] + q["end_clk"] + q["pessimism"] - q["uncertainty"] - q["start_clk"]
              - q["datapath"] - q["slack"] for k, q in (("FF1", a), ("FF2", b))}
        d_sta = b["slack"] - a["slack"]
        d_si = (b["slack"] + b["uncertainty"] - b["pessimism"]) - (a["slack"] + a["uncertainty"] - a["pessimism"])
        # Delta_si = clock part (capture clock at FF2 minus FF1, minus the launch-clock difference
        # of the two worst paths) + routing part (data route to FF1 minus the route to FF2) + setup
        # part (setup of FF1 minus FF2; 0 in most taps, 0.39 ns where STA gives FF2 the smaller
        # setup of some slice columns)
        out[j] = {"delta_sta_ns": d_sta, "delta_si_ns": d_si,
                  "clkpart_ns": (b["end_clk"] - a["end_clk"]) - (b["start_clk"] - a["start_clk"]),
                  "setup_ns": su["FF1"] - su["FF2"],
                  "dU_ns": a["uncertainty"] - b["uncertainty"],
                  "dCPR_ns": a["pessimism"] - b["pessimism"],
                  "clk_ns": b["end_clk"] - a["end_clk"],
                  "data_ns": a["datapath"] - b["datapath"],
                  "ff2_delay_ns": b["datapath"],
                  # period at which the FF2 path would just meet setup in this corner, with the
                  # same analysis terms removed as in Delta_si (data delay plus setup minus skew)
                  "ff2_need_ns": b["requirement"] - (b["slack"] + b["uncertainty"] - b["pessimism"])}
    return out


def collect(npts: int = 3) -> list[dict]:
    res = []
    for f in sorted(glob.glob(os.path.join(TAPDIR, "tap_*.csv"))):
        js = f + ".json"
        if not os.path.exists(js):
            continue
        meta = json.load(open(js))
        if meta.get("mode") != "shmoo":
            continue
        imp = impl_of(meta)
        if imp is None:
            continue
        pts, _ = load(f)
        for k, sw in enumerate(split_sweeps(pts)):
            if len(sw) < 5:
                continue
            for j in range(len(STAGES)):
                m = margin_steps(sw, j, npts)
                if m:
                    m.update({"impl": imp, "file": os.path.basename(f), "sweep": k})
                    res.append(m)
    return res


def summarize(res: list[dict]) -> list[dict]:
    """Mean margin per (implementation, tap) over sweeps, with the STA prediction."""
    models = {name: sta_model(d) for name, d in BUILD_OF.items()}
    out = []
    for imp in sorted({r["impl"] for r in res}):
        for j in sorted({r["tap"] for r in res if r["impl"] == imp}):
            rs = [r for r in res if r["impl"] == imp and r["tap"] == j]
            m = np.mean([r["m_steps"] for r in rs])
            sd = np.std([r["m_steps"] for r in rs]) if len(rs) > 1 else 0.0
            u = np.mean([r["u_steps"] for r in rs])
            md = models.get(imp, {}).get(j, {})
            mlo = np.mean([r["m_lo"] for r in rs])
            mhi = np.mean([r["m_hi"] for r in rs])
            out.append({"impl": imp, "tap": j, "stage": STAGES[j], "n": len(rs),
                        "m_lo_ps": mlo * STEP_TAP_PS, "m_hi_ps": mhi * STEP_TAP_PS,
                        "e_f": np.mean([r["err_at_Vf"] for r in rs]),
                        "m_steps": m, "sd_steps": sd, "u_steps": u,
                        "m_ps": m * STEP_TAP_PS, "u_ps": u * STEP_TAP_PS,
                        "m_mV": np.mean([r["m_mV"] for r in rs]),
                        "zero_points": max(r["zero_points"] for r in rs),
                        "k_steps_per_mV": np.mean([r["k_steps_per_mV"] for r in rs]),
                        "V_f": np.mean([r["V_f"] for r in rs]),
                        "pred_ps": md.get("delta_si_ns", np.nan) * 1000.0,
                        "sta_ps": md.get("delta_sta_ns", np.nan) * 1000.0})
    return out


if __name__ == "__main__":
    s = summarize(collect())
    print("impl tap stage   n  m(steps)  sd   m(ps) [lo,hi]ps   pred(ps) inside zeros  e(Vf)   Vf")
    for r in s:
        ins = r["m_lo_ps"] - 40 <= r["pred_ps"] <= r["m_hi_ps"] + 40
        print(f"{r['impl']:4s} {r['tap']:3d} S{r['stage']:3d} {r['n']:3d} {r['m_steps']:+8.1f} {r['sd_steps']:4.1f} "
              f"{r['m_ps']:+6.0f} [{r['m_lo_ps']:+5.0f},{r['m_hi_ps']:+5.0f}] {r['pred_ps']:+7.0f} {'yes' if ins else 'NO':>5} "
              f"{r['zero_points']:4d} {r['e_f']:.1e} {r['V_f']:.4f}")
    ok = [r for r in s if np.isfinite(r["pred_ps"])]
    if len(ok) > 2:
        x = np.array([r["pred_ps"] for r in ok])
        y = np.array([r["m_ps"] for r in ok])
        k, b = np.polyfit(x, y, 1)
        rr = np.corrcoef(x, y)[0, 1]
        resid = y - x
        print(f"n={len(ok)} fit m = {k:.2f} pred {b:+.0f} ps, r={rr:.3f}; residual (m-pred) mean {resid.mean():+.0f} ps rms {np.sqrt(np.mean(resid**2)):.0f} ps")
