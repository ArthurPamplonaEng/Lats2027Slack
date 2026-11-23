"""Register the 16 nm failure-validation numbers in values.tex (called by run_all.py).

Statistics of the STA model use only the independent observations: the failing taps of the two
placements without guard (A, B). The guard variants (A', B' at 250 ps, B'' at 125 ps) are the same
taps with the same routing, so they are reported separately, as a shift of the readings measured
at identical voltage points.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
from scipy import stats

import fig_tap
from common import GEN, STEP_TAP_PS, V
from tap_analysis import TAPDIR, load, split_sweeps, vaxis
from tap_offsets import collect, impl_of, sta_model, summarize

GUARDS = {"A'": ("A", 250.0), "B'": ("B", 250.0), "B''": ("B", 125.0)}


def readings_by_impl() -> dict[str, dict[tuple[int, float], list[float]]]:
    """Error-free, positive readings per (tap, PMIC command) for every implementation."""
    out: dict[str, dict] = {}
    for f in sorted(glob.glob(os.path.join(TAPDIR, "tap_*.csv"))):
        js = f + ".json"
        if not os.path.exists(js):
            continue
        meta = json.load(open(js))
        imp = impl_of(meta)
        if imp is None or meta.get("mode") != "shmoo":
            continue
        pts, _ = load(f)
        d = out.setdefault(imp, {})
        for p in pts:
            for j in range(23):
                if p.state(j) == "OK" and p.reading[j] > 0.5:
                    d.setdefault((j, round(p.vc_cmd, 2)), []).append(p.reading[j])
    return out


def block(rows, tag):
    if not rows:
        return
    m = np.array([r["m_ps"] for r in rows])
    st = np.array([r["m_steps"] for r in rows])
    V.put(f"Tap{tag}N", len(rows), "{}")
    V.put(f"Tap{tag}MinPs", m.min(), "{:+.0f}")
    V.put(f"Tap{tag}MaxPs", m.max(), "{:+.0f}")
    V.put(f"Tap{tag}MinPsAbs", abs(m.min()), "{:.0f}")
    V.put(f"Tap{tag}MaxPsAbs", abs(m.max()), "{:.0f}")
    V.put(f"Tap{tag}MinSt", st.min(), "{:+.1f}")
    V.put(f"Tap{tag}MaxSt", st.max(), "{:+.1f}")
    V.put(f"Tap{tag}SdMax", max(r["sd_steps"] for r in rows), "{:.1f}")
    V.put(f"Tap{tag}Sweeps", int(round(np.mean([r["n"] for r in rows]))), "{}")
    V.put(f"Tap{tag}SweepsMin", min(r["n"] for r in rows), "{}")
    V.put(f"Tap{tag}SweepsMax", max(r["n"] for r in rows), "{}")
    mv = np.array([r["m_mV"] for r in rows])
    V.put(f"Tap{tag}MinmV", mv.min(), "{:+.0f}")
    V.put(f"Tap{tag}MaxmV", mv.max(), "{:+.0f}")
    V.put(f"Tap{tag}Early", int(sum(1 for r in rows if r["m_lo_ps"] > 0)), "{}")
    V.put(f"Tap{tag}LateSure", int(sum(1 for r in rows if r["m_hi_ps"] < 0)), "{}")


def run() -> dict:
    res = collect()
    if not res:
        raise FileNotFoundError("no tap shmoo data")
    s = summarize(res)
    by_imp = {k: [r for r in s if r["impl"] == k] for k in ("A", "B", "A'", "B'", "B''")}
    NG = by_imp["A"] + by_imp["B"]

    # bench conditions (first shmoo of A)
    f = sorted(glob.glob(os.path.join(TAPDIR, "tap_shmoo1_*.csv")))[0]
    pts, _ = load(f)
    V.put("TapVlo", min(vaxis(p) for p in pts), "{:.3f}")
    V.put("TapVhi", max(vaxis(p) for p in pts), "{:.3f}")
    V.put("TapSweepsPerS", np.mean([p.sweeps / p.windows for p in pts]), "{:,.0f}")
    V.put("TapDie", np.mean([p.temp for p in pts]), "{:.0f}")
    nshmoo = len([g for g in glob.glob(os.path.join(TAPDIR, "tap_shmoo*.csv"))])
    V.put("TapShmoos", nshmoo, "{}")

    block(by_imp["A"], "A")
    block(by_imp["B"], "B")
    block(NG, "NoG")
    block(by_imp["A'"] + by_imp["B'"], "G")
    block(by_imp["B''"], "Gh")
    worst = min(NG, key=lambda r: r["m_steps"])
    V.put("WorstLateSt", -worst["m_steps"], "{:.1f}")
    V.put("WorstLatePs", -worst["m_ps"], "{:.0f}")
    V.put("WorstLatemV", -worst["m_mV"], "{:.0f}")

    # slopes of the reading near failure
    ks = [r["k_steps_per_mV"] for r in NG]
    V.put("TapKlo", min(ks), "{:.2f}")
    V.put("TapKhi", max(ks), "{:.2f}")
    V.put("TapKloPs", min(ks) * STEP_TAP_PS, "{:.0f}")
    V.put("TapKhiPs", max(ks) * STEP_TAP_PS, "{:.0f}")
    # smallest error rate seen at a first failing point (any sweep), as LaTeX mantissa x 10^exp
    ef = min(r["err_at_Vf"] for r in res if r["impl"] in ("A", "B") and r["err_at_Vf"] > 0)
    ex = int(np.floor(np.log10(ef)))
    V.put("ErrRateMin", f"{ef / 10 ** ex:.0f}\\times10^{{{ex}}}")
    V.put("ZeroPtsMax", max(r["zero_points"] for r in NG), "{}")
    V.put("TapVfLo", min(r["V_f"] for r in NG), "{:.3f}")
    V.put("TapVfHi", max(r["V_f"] for r in NG), "{:.3f}")

    # STA terms (placement A) and the model on the independent taps
    mA = sta_model("impl")
    V.put("StaDU", np.mean([v["dU_ns"] for v in mA.values()]) * 1000, "{:.0f}")
    V.put("StaDCPR", -np.mean([v["dCPR_ns"] for v in mA.values()]) * 1000, "{:.0f}")
    x = np.array([r["pred_ps"] for r in NG])
    y = np.array([r["m_ps"] for r in NG])
    k, b = np.polyfit(x, y, 1)
    pr = stats.pearsonr(x, y)
    sp = stats.spearmanr(x, y)
    resid = y - x
    V.put("FitN", len(NG), "{}")
    V.put("FitSlope", k, "{:.2f}")
    V.put("FitIcpt", b, "{:+.0f}")
    V.put("FitR", pr.statistic, "{:.2f}")
    V.put("FitP", pr.pvalue, "{:.3f}")
    V.put("FitRho", sp.statistic, "{:.2f}")
    V.put("FitRhoP", sp.pvalue, "{:.3f}")
    V.put("FitRms", np.sqrt(np.mean(resid ** 2)), "{:.0f}")
    V.put("FitBias", resid.mean(), "{:+.0f}")
    V.put("FitNullRms", np.sqrt(np.mean((y - y.mean()) ** 2)), "{:.0f}")
    V.put("FitHalfW", np.mean([0.5 * (r["m_hi_ps"] - r["m_lo_ps"]) for r in NG]), "{:.0f}")
    V.put("FitResVfR", np.corrcoef(resid, [r["V_f"] for r in NG])[0, 1], "{:+.2f}")
    raw = np.array([r["sta_ps"] for r in NG])
    V.put("FitRawBiasAbs", abs((y - raw).mean()), "{:.0f}")
    inside = [r for r in NG if r["m_lo_ps"] <= r["pred_ps"] <= r["m_hi_ps"]]
    V.put("FitInside", len(inside), "{}")
    V.put("FitInsideA", sum(1 for r in inside if r["impl"] == "A"), "{}")
    V.put("FitInsideB", sum(1 for r in inside if r["impl"] == "B"), "{}")
    V.put("FitMissMax", max(max(r["pred_ps"] - r["m_hi_ps"], r["m_lo_ps"] - r["pred_ps"])
                            for r in NG if r not in inside), "{:.0f}")
    # a guard sized from STA alone: cover the most negative prediction plus twice the rms error,
    # rounded up to the static phase resolution (1/8 VCO period = 125 ps)
    dmin = -min(r["pred_ps"] for r in NG)
    sized = dmin + 2 * np.sqrt(np.mean(resid ** 2))
    V.put("DstMinAbs", dmin, "{:.0f}")
    V.put("GuardSizedPs", sized, "{:.0f}")
    V.put("GuardSizedSet", int(np.ceil(sized / 125.0)), "{}")
    xb = np.array([r["pred_ps"] for r in by_imp["B"]])
    yb = np.array([r["m_ps"] for r in by_imp["B"]])
    V.put("FitRmsB", np.sqrt(np.mean((yb - xb) ** 2)), "{:.0f}")
    V.put("FitRmsA", np.sqrt(np.mean((np.array([r["m_ps"] for r in by_imp["A"]]) -
                                       np.array([r["pred_ps"] for r in by_imp["A"]])) ** 2)), "{:.0f}")

    # guard: drop of the reading at identical (tap, voltage) points, and V_f change
    rd = readings_by_impl()
    gsum = {}
    for g, (base, ps_designed) in GUARDS.items():
        if g not in rd or base not in rd:
            continue
        keys = [kk for kk in rd[g] if kk in rd[base]]
        d = np.array([np.mean(rd[base][kk]) - np.mean(rd[g][kk]) for kk in keys])
        b0 = {r["tap"]: r for r in by_imp[base]}
        g0 = {r["tap"]: r for r in by_imp[g]}
        dvf = [abs(g0[j]["V_f"] - b0[j]["V_f"]) * 1000 for j in set(b0) & set(g0)]
        gsum[g] = {"mean": d.mean(), "sd": d.std(), "n": len(d), "designed": ps_designed / STEP_TAP_PS,
                   "dvf": max(dvf) if dvf else np.nan}
    g250 = [gsum[g] for g in ("A'", "B'") if g in gsum]
    if g250:
        allm = np.array([x["mean"] for x in g250])
        V.put("GuardPtSt", np.mean(allm), "{:.2f}")
        V.put("GuardPtSd", max(x["sd"] for x in g250), "{:.2f}")
        V.put("GuardPtPs", np.mean(allm) * STEP_TAP_PS, "{:.0f}")
        V.put("GuardPtN", sum(x["n"] for x in g250), "{}")
        V.put("GuardDVfmV", max(x["dvf"] for x in g250), "{:.1f}")
        V.put("GuardDesignSt", 250.0 / STEP_TAP_PS, "{:.1f}")
        V.put("GuardPairs", len(by_imp["A'"]) + len(by_imp["B'"]), "{}")
    if "B''" in gsum:
        x = gsum["B''"]
        # taps of B expected to read zero first once their margins move by the measured shift
        V.put("GuardHPredEarly", sum(1 for r in by_imp["B"]
                                     if r["m_lo_ps"] + x["mean"] * STEP_TAP_PS > 0), "{}")
        V.put("GuardHPtSt", x["mean"], "{:.2f}")
        V.put("GuardHPtSd", x["sd"], "{:.2f}")
        V.put("GuardHPtPs", x["mean"] * STEP_TAP_PS, "{:.0f}")
        V.put("GuardHPtN", x["n"], "{}")
        V.put("GuardHDesignSt", 125.0 / STEP_TAP_PS, "{:.1f}")
        V.put("GuardHDVfmV", x["dvf"], "{:.1f}")

    table(s, os.path.join(GEN, "tab_taps.tex"))
    fig_tap.offset(s)
    shm = sorted(glob.glob(os.path.join(TAPDIR, "tap_shmoo2_*.csv")))
    gua = sorted(glob.glob(os.path.join(TAPDIR, "tap_shmooAguard_*.csv")))
    if shm:
        p2, _ = load(shm[-1])
        pg = split_sweeps(load(gua[-1])[0])[0] if gua else None
        fig_tap.shmoo(split_sweeps(p2)[0], [2, 3, 4, 5, 6, 7, 8], guard=pg)
    return {"summary": s, "guards": gsum}


def table(summary, path):
    """paper/generated/tab_taps.tex: per-tap results of the two placements and their guards."""
    by = {(r["impl"], r["stage"]): r for r in summary}
    stages = sorted({r["stage"] for r in summary if r["impl"] in ("A", "B")})
    lines = [r"\begin{tabular}{@{}r@{\hspace{4pt}}ccc@{\hspace{5pt}}c@{\hspace{7pt}}ccc@{\hspace{5pt}}cc@{}}",
             r"\toprule",
             r" & \multicolumn{4}{c}{placement A} & \multicolumn{5}{c}{placement B} \\",
             r"\cmidrule(lr){2-5}\cmidrule(lr){6-10}",
             r"$S$ & $V_f$ & $m$ & $\Dst$ & $m'$ & $V_f$ & $m$ & $\Dst$ & $m''$ & $m'$ \\",
             r"\midrule"]

    def cell(imp, s, key, fmt):
        r = by.get((imp, s))
        if not r:
            return "--"
        v = r[key]
        if fmt == "{:+.0f}" and abs(v) < 0.5:
            return "0"
        return fmt.format(v)
    for s in stages:
        row = [f"{s}",
               cell("A", s, "V_f", "{:.3f}"), cell("A", s, "m_ps", "{:+.0f}"), cell("A", s, "pred_ps", "{:+.0f}"),
               cell("A'", s, "m_ps", "{:+.0f}"),
               cell("B", s, "V_f", "{:.3f}"), cell("B", s, "m_ps", "{:+.0f}"), cell("B", s, "pred_ps", "{:+.0f}"),
               cell("B''", s, "m_ps", "{:+.0f}"), cell("B'", s, "m_ps", "{:+.0f}")]
        lines.append(" & ".join(row).replace("-", "$-$").replace("$-$$-$", "--") + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(path, "w") as f:
        f.write("% generated by analysis/tap_values.py -- do not edit\n" + "\n".join(lines) + "\n")
