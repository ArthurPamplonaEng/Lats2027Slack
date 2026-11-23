"""28 nm results (Nexys 4 DDR, Artix-7, 16-bit RCA path, 17.857 ps per step): Run 1.

* the 214.6 h burn-in log (summary only: conditions and mean reading);
* the corners before and after the burn-in at ~104 C (pre: screenshots; post: logged sweep);
* the post-burn-in cold corners (~46 C): temperature dependence and its sign change near 1.0 V;
* the slack-voltage slope of the post-burn-in sweep, which turns the slack lost into mV of margin.
"""
from __future__ import annotations

import os

import numpy as np

from common import DATA, STEP_NEXYS_PS, V, read_csv_dicts, read_csv_numeric

D = os.path.join(DATA, "nexys4_run1")
CORNERS_V = (1.10, 1.00, 0.90)


def burnin() -> dict:
    hdr, d = read_csv_numeric(os.path.join(D, "Tentative_1_20260524_203756.csv"))
    c = {k: i for i, k in enumerate(hdr)}
    t, s = d[:, c["time_sec"]], d[:, c["dut_slack"]]
    T, Vc = d[:, c["dut_temp_c"]], d[:, c["dut_volt"]]
    ov, psu = d[:, c["oven_temp_c"]], d[:, c["psu_voltage_v"]]
    ok = (s > 0) & (Vc > 0.5) & (T > 0)
    dur_h = (t[-1] - t[0]) / 3600.0
    r = {
        "dur_h": dur_h, "n": int(ok.sum()),
        "slack_mean": s[ok].mean(), "slack_sd": s[ok].std(),
        "slack_min": s[ok].min(), "slack_max": s[ok].max(),
        "T_mean": T[ok].mean(), "T_sd": T[ok].std(),
        "V_mean": Vc[ok].mean(), "V_sd": Vc[ok].std(),
        "oven_mean": ov[ok].mean(), "oven_sd": ov[ok].std(),
        "psu_mean": psu[ok].mean(),
        "t_h": t[ok] / 3600.0, "s": s[ok], "T": T[ok], "V": Vc[ok],
    }
    V.put("RunDurH", dur_h, "{:.1f}")
    V.put("RunN", f"{r['n']:,}".replace(",", "\\,"))
    V.put("RunSlack", r["slack_mean"], "{:.1f}")
    V.put("RunSlackSd", r["slack_sd"], "{:.1f}")
    V.put("RunSlackNs", r["slack_mean"] * STEP_NEXYS_PS / 1000.0, "{:.2f}")
    V.put("RunT", r["T_mean"], "{:.1f}")
    V.put("RunTsd", r["T_sd"], "{:.1f}")
    V.put("RunV", r["V_mean"], "{:.3f}")
    V.put("RunVsdmV", r["V_sd"] * 1000.0, "{:.0f}")
    V.put("RunOven", r["oven_mean"], "{:.1f}")
    V.put("RunPsu", r["psu_mean"], "{:.2f}")
    return r


def post_sweep() -> dict:
    """The logged post-burn-in run of 2026-06-02 (~104 C): plateaus at 1.10/1.00/0.90 V and the
    transitions between them, read as a slack-voltage curve."""
    hdr, d = read_csv_numeric(os.path.join(D, "Corners_20260602_191558.csv"))
    c = {k: i for i, k in enumerate(hdr)}
    s, Vc, T = d[:, c["dut_slack"]], d[:, c["dut_volt"]], d[:, c["dut_temp_c"]]
    ok = (s > 0) & (Vc > 0.5)
    s, Vc, T = s[ok], Vc[ok], T[ok]
    vr = np.round(Vc, 2)
    levels = np.array(sorted(set(vr)))
    med = np.array([np.median(s[vr == x]) for x in levels])
    mean = np.array([s[vr == x].mean() for x in levels])
    n = np.array([(vr == x).sum() for x in levels])
    Tm = np.array([T[vr == x].mean() for x in levels])
    # local slope at each corner: straight line through the level means within +-50 mV
    # (model-free); the alpha-power law S = a - b V / (V - Vt)^1.3 is the cross-check
    slope, slope_alpha = {}, {}
    for v in CORNERS_V:
        m = np.abs(levels - v) <= 0.05 + 1e-9
        slope[v] = np.polyfit(levels[m], mean[m], 1)[0]
    from scipy.optimize import curve_fit

    def alpha(Vv, a, b, vt):
        return a - b * Vv / np.clip(Vv - vt, 1e-3, None) ** 1.3
    pa, _ = curve_fit(alpha, levels, mean, p0=(500, 100, 0.4), sigma=1 / np.sqrt(n), maxfev=20000)
    for v in CORNERS_V:
        h = 1e-4
        slope_alpha[v] = (alpha(v + h, *pa) - alpha(v - h, *pa)) / (2 * h)
    return {"levels": levels, "median": med, "mean": mean, "n": n, "T": Tm, "alpha": pa,
            "slope": slope, "slope_alpha": slope_alpha, "T_all": T, "s_all": s, "vr_all": vr}


def post_at(ps: dict, v: float, T_ref: float, tol: float = 0.5) -> tuple[float, float, int]:
    """Median (and sd, n) of the post-burn-in plateau at v, restricted to die temperatures within
    tol of the pre-burn-in reading, so the two corners are compared at the same temperature."""
    m = (ps["vr_all"] == v) & (np.abs(ps["T_all"] - T_ref) < tol)
    if m.sum() < 10:
        m = ps["vr_all"] == v
    x = ps["s_all"][m]
    return float(np.median(x)), float(x.std()), int(m.sum())


def alpha_curve(ps: dict):
    a, b, vt = ps["alpha"]
    return lambda Vv: a - b * Vv / np.clip(Vv - vt, 1e-3, None) ** 1.3


def voltage_shift(ps: dict, cs: dict) -> dict:
    """One-parameter test of how the burn-in acted: the pre-burn-in readings are compared with the
    post-burn-in curve (alpha-power fit of the logged sweep) moved by dV along the voltage axis,
    pre(V) = post(V + dV), and with a constant slack offset, pre(V) = post(V) + c. The spread of
    dV comes from +-1 step on each single pre-burn-in reading."""
    from scipy.optimize import minimize_scalar
    f = alpha_curve(ps)
    Vv = np.array(CORNERS_V)
    pre = np.array([cs["pre"][v][0] for v in CORNERS_V])

    def fit(p):
        return minimize_scalar(lambda d: np.sum((f(Vv + d) - p) ** 2), bounds=(-0.05, 0.08),
                               method="bounded").x
    dv = fit(pre)
    rng = np.random.default_rng(1)
    dvs = [fit(pre + rng.normal(0, 1.0, 3)) for _ in range(2000)]
    res = f(Vv + dv) - pre
    c = np.mean(pre - f(Vv))
    res_c = f(Vv) + c - pre
    return {"dv": dv, "dv_sd": float(np.std(dvs)), "res": res, "res_rms": float(np.sqrt(np.mean(res ** 2))),
            "c": c, "res_c": res_c, "res_c_rms": float(np.sqrt(np.mean(res_c ** 2))), "f": f}


def corners() -> dict:
    rows = read_csv_dicts(os.path.join(D, "corners_from_screenshots.csv"))
    out: dict[str, dict[float, tuple[float, float]]] = {}
    for r in rows:
        v = round(float(r["vccint_v"]), 1)
        out.setdefault(r["phase"], {})[v] = (float(r["slack_inc"]), float(r["die_c"]))
    return out


def run() -> dict:
    b = burnin()
    ps = post_sweep()
    cs = corners()
    names = {1.10: "Hi", 1.00: "Mid", 0.90: "Lo"}
    dvm = {}
    dvm_alpha, dvm_err = {}, {}
    for v in CORNERS_V:
        pre, T_pre = cs["pre"][v]
        post, post_sd, post_n = post_at(ps, v, T_pre)
        dS = post - pre
        # the pre value is one sweep (screenshot): its spread is the plateau sd, plus 0.5 count of
        # reading quantisation on each side
        sig = float(np.sqrt(post_sd ** 2 + 2 * 0.5 ** 2 + post_sd ** 2 / post_n))
        k = ps["slope"][v]                    # counts per volt at ~104 C
        dV_mV = -dS / k * 1000.0
        dvm[v] = dV_mV
        dvm_alpha[v] = -dS / ps["slope_alpha"][v] * 1000.0
        dvm_err[v] = sig / k * 1000.0
        nm = names[v]
        V.put(f"Pre{nm}", pre, "{:.0f}")
        V.put(f"PreT{nm}", T_pre, "{:.1f}")
        V.put(f"Post{nm}", post, "{:.0f}")
        V.put(f"PostSd{nm}", post_sd, "{:.1f}")
        V.put(f"PostNs{nm}", post * STEP_NEXYS_PS / 1000.0, "{:.1f}")
        V.put(f"Dslack{nm}", dS, "{:+.0f}")
        V.put(f"DslackErr{nm}", sig, "{:.1f}")
        V.put(f"Dps{nm}", dS * STEP_NEXYS_PS, "{:+.0f}")
        V.put(f"Slope{nm}", k, "{:.0f}")
        V.put(f"SlopePs{nm}", k * STEP_NEXYS_PS / 1000.0, "{:.1f}")   # ps of slack per mV
        V.put(f"DVmin{nm}", dV_mV, "{:.0f}")
        V.put(f"DVminErr{nm}", dvm_err[v], "{:.0f}")
        V.put(f"DVminAlpha{nm}", dvm_alpha[v], "{:.1f}")
        cold, Tc = cs["post_cold"][v]
        hot, Th = cs["post_hot"][v]
        V.put(f"Cold{nm}", cold, "{:.0f}")
        V.put(f"ColdT{nm}", Tc, "{:.0f}")
        V.put(f"HotT{nm}", Th, "{:.0f}")
        V.put(f"Kt{nm}", (hot - cold) / (Th - Tc), "{:+.2f}")
        V.put(f"HotMinusCold{nm}", hot - cold, "{:+.0f}")
    V.put("PreT", np.mean([cs["pre"][v][1] for v in CORNERS_V]), "{:.0f}")
    V.put("ColdT", np.mean([cs["post_cold"][v][1] for v in CORNERS_V]), "{:.0f}")
    V.put("AlphaVt", ps["alpha"][2], "{:.2f}")
    V.put("DVminAlphaLo", min(dvm_alpha.values()), "{:.1f}")
    V.put("DVminAlphaHi", max(dvm_alpha.values()), "{:.1f}")
    shift = voltage_shift(ps, cs)
    V.put("ShiftmV", shift["dv"] * 1000, "{:.1f}")
    V.put("ShiftErrmV", shift["dv_sd"] * 1000, "{:.1f}")
    V.put("ShiftResMax", np.max(np.abs(shift["res"])), "{:.1f}")
    V.put("ShiftResRms", shift["res_rms"], "{:.1f}")
    V.put("OffsetResMax", np.max(np.abs(shift["res_c"])), "{:.1f}")
    V.put("OffsetResRms", shift["res_c_rms"], "{:.1f}")
    V.put("SweepLo", ps["levels"].min(), "{:.2f}")
    V.put("SweepHi", ps["levels"].max(), "{:.2f}")
    V.put("DVminRangeLo", min(dvm.values()), "{:.0f}")
    V.put("DVminRangeHi", max(dvm.values()), "{:.0f}")
    return {"burnin": b, "post": ps, "corners": cs, "dvmin": dvm, "shift": shift}


if __name__ == "__main__":
    r = run()
    for k, (v, f) in sorted(V.v.items()):
        print(k, f.format(v) if not isinstance(v, str) else v)
