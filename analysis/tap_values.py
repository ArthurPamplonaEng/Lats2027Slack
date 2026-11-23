"""Register the 16 nm failure-validation numbers in values.tex (called by run_all.py).

Two bench sessions on board 2. Session 1 (20/11): placements A and B at the 10 ns period and the
designed guards (A', B' at 250 ps, B'' at 125 ps). Session 2 (23/11): the same routed A and B at 12
to 18 ns (only the MMCM dividers change, so taps that fail at the top of the range at 10 ns cross
failure inside it), two new placements C and D at 10, 14 and 18 ns, and a repetition of A (Arep).

Statistics of the STA model use only independent observations: each failing tap counts once per
placement, at the shortest period at which it fails inside the range (10 ns when it does). The
guard variants are the same taps with the same routing and are reported as a shift of the readings
at identical voltage points; the same tap at two periods tests how the margin depends on the
failure voltage; Arep gives the day-to-day repeatability. The session-1 statistics (Fit*, Loo*)
are kept as they were computed before session 2, which tested them out of sample.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import date, datetime

import numpy as np
from scipy import stats

import fig_tap
from common import GEN, STEP_TAP_PS, V
from tap_analysis import STAGES, TAPDIR, load, split_sweeps, vaxis
from tap_offsets import BUILD_OF, collect, guarded, impl_of, period_ns, placement, sta_model, summarize

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
    rate = np.mean([p.sweeps / p.windows for p in pts])
    # SI style: no separator up to four digits, a thin space from five on (as \vRunN)
    V.put("TapSweepsPerS", f"{rate:,.0f}".replace(",", "\\," if rate >= 1e4 else ""))
    V.put("TapDie", np.mean([p.temp for p in pts]), "{:.0f}")
    nshmoo = len([g for g in glob.glob(os.path.join(TAPDIR, "tap_shmoo*.csv"))])
    V.put("TapShmoos", nshmoo, "{}")
    # the two bench sessions: shmoos per day, days apart, and the duration of one shmoo
    days, mins = {}, []
    for g in sorted(glob.glob(os.path.join(TAPDIR, "tap_shmoo*.csv"))):
        meta = json.load(open(g + ".json"))
        day = meta["created"][:10]
        days[day] = days.get(day, 0) + 1
        with open(g) as fh:
            t = [ln.split(",", 1)[0] for ln in fh.read().splitlines()[1:] if ln]
        mins.append((datetime.fromisoformat(t[-1]) - datetime.fromisoformat(t[0])).total_seconds() / 60)
    d0, d1 = sorted(days)[:2]
    V.put("ShmoosFirst", days[d0], "{}")
    V.put("ShmoosSecond", days[d1], "{}")
    V.put("SessGapDays", (date.fromisoformat(d1) - date.fromisoformat(d0)).days, "{}")
    V.put("ShmooMinLo", min(mins), "{:.0f}")
    V.put("ShmooMinHi", max(mins), "{:.0f}")

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

    # STA terms of placement A over its modelled (failing) taps, and the model on the independent taps
    mA = sta_model("impl")
    tA = [r["tap"] for r in by_imp["A"]]
    V.put("StaDU", np.mean([mA[j]["dU_ns"] for j in tA]) * 1000, "{:.0f}")
    V.put("StaDCPR", -np.mean([mA[j]["dCPR_ns"] for j in tA]) * 1000, "{:.0f}")
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

    def rms(v):
        return float(np.sqrt(np.mean(np.asarray(v) ** 2)))

    # correction terms of placement B (the text gives A's in StaDU / StaDCPR) and the total
    # correction (raw minus corrected prediction) of each placement
    mB = sta_model("impl_b")
    tB = [r["tap"] for r in by_imp["B"]]
    V.put("StaDUB", np.mean([mB[j]["dU_ns"] for j in tB]) * 1000, "{:.0f}")
    V.put("StaDCPRB", -np.mean([mB[j]["dCPR_ns"] for j in tB]) * 1000, "{:.0f}")
    for imp in ("A", "B"):
        V.put(f"StaCorr{imp}", np.mean([r["sta_ps"] - r["pred_ps"] for r in by_imp[imp]]), "{:.0f}")
    # the raw slack difference: correlation, and raw plus the best constant
    V.put("FitRawR", stats.pearsonr(raw, y).statistic, "{:.2f}")
    V.put("FitRawConstRms", rms(y - raw - (y - raw).mean()), "{:.0f}")

    # leave-one-out: the tap whose removal lowers r most, and the model without it
    loo = []
    for i in range(len(NG)):
        keep = np.arange(len(NG)) != i
        pr_i = stats.pearsonr(x[keep], y[keep])
        loo.append((pr_i.statistic, pr_i.pvalue, rms(y[keep] - x[keep]),
                    rms(y[keep] - y[keep].mean()), i))
    lo = min(loo)
    out = NG[lo[4]]
    V.put("LooImpl", out["impl"])
    V.put("LooStage", out["stage"], "{}")
    V.put("LooR", lo[0], "{:.2f}")
    V.put("LooP", lo[1], "{:.2f}")
    V.put("LooRms", lo[2], "{:.0f}")
    V.put("LooNullRms", lo[3], "{:.0f}")
    others = [t for t in loo if t[4] != lo[4]]
    V.put("LooOtherRLo", min(t[0] for t in others), "{:.2f}")
    V.put("LooOtherRHi", max(t[0] for t in others), "{:.2f}")
    # within each placement, without that tap: STA ranks the taps but overstates their spread
    for imp in ("A", "B"):
        rs = [r for r in by_imp[imp] if r is not out]
        xx = np.array([r["pred_ps"] for r in rs])
        yy = np.array([r["m_ps"] for r in rs])
        V.put(f"FitSlopeIn{imp}", np.polyfit(xx, yy, 1)[0], "{:.2f}")
        V.put(f"FitRIn{imp}", np.corrcoef(xx, yy)[0, 1], "{:.2f}")
    # out of sample: B predicted from what A gave (its mean margin) versus the STA of B
    yA = np.array([r["m_ps"] for r in by_imp["A"]])
    yA_no = np.array([r["m_ps"] for r in by_imp["A"] if r is not out])
    V.put("FitOosConstRmsB", rms(yb - yA.mean()), "{:.0f}")
    V.put("FitOosConstNoRmsB", rms(yb - yA_no.mean()), "{:.0f}")
    V.put("FitNullRmsB", rms(yb - yb.mean()), "{:.0f}")
    # what Delta* is made of: clock arrival at FF2 minus FF1, and data route to FF1 minus FF2
    models = {"A": mA, "B": mB}
    clk = {imp: {r["tap"]: models[imp][r["tap"]]["clk_ns"] * 1000 for r in by_imp[imp]} for imp in ("A", "B")}
    dat = {imp: {r["tap"]: models[imp][r["tap"]]["data_ns"] * 1000 for r in by_imp[imp]} for imp in ("A", "B")}
    rest = [c for j, c in clk[out["impl"]].items() if j != out["tap"]]
    V.put("ClkOutPs", clk[out["impl"]][out["tap"]] - np.median(rest), "{:.0f}")
    V.put("ClkSpreadPs", max(max(c for j, c in clk[imp].items() if not (imp == out["impl"] and j == out["tap"])) -
                             min(c for j, c in clk[imp].items() if not (imp == out["impl"] and j == out["tap"]))
                             for imp in ("A", "B")), "{:.0f}")
    V.put("RouteSpreadPs", max(max(dat[imp].values()) - min(dat[imp].values()) for imp in ("A", "B")), "{:.0f}")
    for imp in ("A", "B"):
        V.put(f"ClkLevel{imp}", np.median([c for j, c in clk[imp].items()
                                           if not (imp == out["impl"] and j == out["tap"])]), "{:+.0f}")

    # how much the margins depend on the number of points of the extrapolated line
    sens = {}
    for npts in (2, 4):
        alt = {(r["impl"], r["tap"]): r for r in summarize(collect(npts))}
        for r in s:
            a = alt.get((r["impl"], r["tap"]))
            if a is not None:
                if r["impl"] == "Arep":
                    continue
                key = "G" if guarded(r["impl"]) else "NoG"
                sens[key] = max(sens.get(key, 0.0), abs(a["m_ps"] - r["m_ps"]))
    V.put("ExtrapSensPs", sens["NoG"], "{:.0f}")
    V.put("ExtrapSensGPs", sens["G"], "{:.0f}")
    V.put("TapGZeroPtsMax", max(r["zero_points"] for r in by_imp["A'"] + by_imp["B'"]), "{}")

    # failing points at which every sweep still alarmed with a positive reading, at an error
    # rate of one half (one edge fails in every cycle in which it occurs, the other passes)
    half = {}
    for f in sorted(glob.glob(os.path.join(TAPDIR, "tap_*.csv"))):
        meta = json.load(open(f + ".json"))
        imp = impl_of(meta)
        if imp not in ("A", "B") or meta.get("mode") != "shmoo":
            continue
        taps = {r["tap"] for r in by_imp[imp]}
        for sw in split_sweeps(load(f)[0]):
            for p in sw:
                for j in taps:
                    if (p.state(j) == "FAIL" and abs(p.err_rate[j] - 0.5) < 0.02 and p.got_frac[j] > 0.999
                            and p.reading[j] >= 1.0):
                        half.setdefault((imp, j), []).append(p.reading[j])
    hr = [np.mean(v) for v in half.values()]
    V.put("HalfN", len(half), "{}")
    V.put("HalfRLo", min(hr), "{:.1f}")
    V.put("HalfRHi", max(hr), "{:.1f}")
    V.put("HalfStages", " and ".join(f"S{STAGES[j]}" for (_, j) in sorted(half, key=lambda t: t[1])))
    V.put("HalfImpl", "/".join(sorted({imp for imp, _ in half})))

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
        if "B'" in gsum:
            V.put("GuardStepTwoPs", (gsum["B'"]["mean"] - x["mean"]) * STEP_TAP_PS, "{:.0f}")

    table(s, os.path.join(GEN, "tab_taps.tex"))
    full = full_set(s, res, float(np.sqrt(np.mean(resid ** 2))), out)
    fig_tap.offset(full["ind"])
    shm = sorted(glob.glob(os.path.join(TAPDIR, "tap_shmoo2_*.csv")))
    gua = sorted(glob.glob(os.path.join(TAPDIR, "tap_shmooAguard_*.csv")))
    if shm:
        p2, _ = load(shm[-1])
        pg = split_sweeps(load(gua[-1])[0])[0] if gua else None
        sel = sorted({r["tap"] for r in by_imp["A"]})          # taps that fail inside the sweep
        fig_tap.shmoo(split_sweeps(p2)[0], sel, guard=pg, example=out["stage"])
    return {"summary": s, "guards": gsum, "full": full}


def table(summary, path):
    """paper/generated/tab_taps.tex: per-tap results of the two placements and their guards.

    The margins of the placements without guard carry their interval (from the last passing and
    the first failing voltage) as super- and subscripts: m^{+(m_hi - m)}_{-(m - m_lo)}."""
    by = {(r["impl"], r["stage"]): r for r in summary}
    stages = sorted({r["stage"] for r in summary if r["impl"] in ("A", "B")})
    lines = [r"\begin{tabular}{@{}r@{\hspace{4pt}}ccc@{\hspace{5pt}}c@{\hspace{7pt}}ccc@{\hspace{5pt}}cc@{}}",
             r"\toprule",
             r" & \multicolumn{4}{c}{placement A} & \multicolumn{5}{c}{placement B} \\",
             r"\cmidrule(lr){2-5}\cmidrule(lr){6-10}",
             r"$S$ & $V_f$ & $m$ & $\Dst$ & $m'$ & $V_f$ & $m$ & $\Dst$ & $m''$ & $m'$ \\",
             r"\midrule"]

    def num(v, fmt="{:+.0f}"):
        t = fmt.format(v)
        if fmt == "{:+.0f}" and abs(v) < 0.5:
            return "0"
        return t.replace("-", "$-$")

    def cell(imp, s, key, fmt="{:+.0f}"):
        r = by.get((imp, s))
        return num(r[key], fmt) if r else "--"

    def mcell(imp, s):
        r = by.get((imp, s))
        if not r:
            return "--"
        up = r["m_hi_ps"] - r["m_ps"]
        dn = r["m_ps"] - r["m_lo_ps"]
        return (f"{num(r['m_ps'])}$^{{\\text{{+{abs(up):.0f}}}}}_{{\\text{{$-${abs(dn):.0f}}}}}$")
    for s in stages:
        row = [f"{s}",
               cell("A", s, "V_f", "{:.3f}"), mcell("A", s), cell("A", s, "pred_ps"), cell("A'", s, "m_ps"),
               cell("B", s, "V_f", "{:.3f}"), mcell("B", s), cell("B", s, "pred_ps"),
               cell("B''", s, "m_ps"), cell("B'", s, "m_ps")]
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(path, "w") as f:
        f.write("% generated by analysis/tap_values.py -- do not edit\n" + "\n".join(lines) + "\n")


def _rms(v) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(v, dtype=float)))))


def _stats(sel: list[dict]) -> dict:
    x = np.array([r["pred_ps"] for r in sel])
    y = np.array([r["m_ps"] for r in sel])
    return {"n": len(sel), "r": float(np.corrcoef(x, y)[0, 1]), "slope": float(np.polyfit(x, y, 1)[0]),
            "rms": _rms(y - x), "null": _rms(y - y.mean()), "bias": float(np.mean(y - x)),
            "rho": float(stats.spearmanr(x, y).statistic)}


def full_set(s: list[dict], res: list[dict], sigma1: float, out_tap: dict) -> dict:
    """Both sessions: the independent taps of placements A-D at every period, out-of-sample tests,
    the parts of Delta*, the margin at two failure voltages, guard sizing and repeatability.

    sigma1: rms of m - Delta* of session 1, fixed before session 2 (sizes the guard below).
    out_tap: the session-1 tap whose removal lowered r most (A-S74)."""
    models = {lab: sta_model(d) for lab, d in BUILD_OF.items()}
    cases = [dict(r) for r in s if not guarded(r["impl"]) and r["impl"] != "Arep"]
    for r in cases:
        md = models[r["impl"]][r["tap"]]
        r.update({"pl": placement(r["impl"]), "T": period_ns(r["impl"]),
                  "clk": md["clkpart_ns"] * 1000, "route": md["data_ns"] * 1000,
                  "setup": md["setup_ns"] * 1000, "dcpr": -md["dCPR_ns"] * 1000, "du": md["dU_ns"] * 1000})
    first = {}
    for r in cases:                      # each tap once per placement: its shortest period
        k = (r["pl"], r["tap"])
        if k not in first or r["T"] < first[k]["T"]:
            first[k] = r
    ind = sorted(first.values(), key=lambda r: (r["pl"], r["stage"]))
    sess1 = [r for r in ind if r["impl"] in ("A", "B")]
    new = [r for r in ind if r["impl"] not in ("A", "B")]
    ablong = [r for r in new if r["pl"] in "AB"]
    cd = [r for r in ind if r["pl"] in "CD"]
    sets = {"All": ind, "New": new, "ABLong": ablong, "CD": cd}
    sets.update({f"Pl{p}": [r for r in ind if r["pl"] == p] for p in "ABCD"})
    st = {k: _stats(v) for k, v in sets.items()}
    st["Sess"] = _stats(sess1)
    for k, d in st.items():
        V.put(f"{k}N", d["n"], "{}")
        V.put(f"{k}R", d["r"], "{:.2f}")
        V.put(f"{k}Slope", d["slope"], "{:.2f}")
        V.put(f"{k}Rms", d["rms"], "{:.0f}")
        V.put(f"{k}NullRms", d["null"], "{:.0f}")
        V.put(f"{k}Bias", d["bias"], "{:+.0f}")
    V.put("AllRho", st["All"]["rho"], "{:.2f}")
    for k, nm in (("rms", "Rms"), ("null", "NullRms"), ("r", "R"), ("slope", "Slope")):
        v = [st[f"Pl{p}"][k] for p in "ABCD"]
        fmt = "{:.0f}" if "Rms" in nm else "{:.2f}"
        V.put(f"Pl{nm}Lo", min(v), fmt)
        V.put(f"Pl{nm}Hi", max(v), fmt)
    V.put("AllCases", len(cases), "{}")
    V.put("AllPlN", len({r["pl"] for r in ind}), "{}")
    for p in "CD":
        V.put(f"Tap{p}N", sum(1 for r in ind if r["impl"] == p), "{}")
    # stages that cross failure inside the range at 10 ns (all placements), and those of A
    ten = [r["stage"] for r in ind if r["T"] == 10]
    V.put("TenStageLo", min(ten), "{}")
    V.put("TenStageHi", max(ten), "{}")
    sa = [r["stage"] for r in ind if r["impl"] == "A"]
    V.put("TapAStageLo", min(sa), "{}")
    V.put("TapAStageHi", max(sa), "{}")
    # without the tap that carried session 1, and leaving out any one tap
    no = [r for r in ind if not (r["impl"] == out_tap["impl"] and r["tap"] == out_tap["tap"])]
    d = _stats(no)
    V.put("AllNoOutR", d["r"], "{:.2f}")
    V.put("AllNoOutRms", d["rms"], "{:.0f}")
    V.put("AllNoOutNullRms", d["null"], "{:.0f}")
    x = np.array([r["pred_ps"] for r in ind])
    y = np.array([r["m_ps"] for r in ind])
    loo = [np.corrcoef(x[np.arange(len(x)) != i], y[np.arange(len(x)) != i])[0, 1] for i in range(len(x))]
    V.put("AllLooRLo", min(loo), "{:.2f}")
    V.put("AllLooRHi", max(loo), "{:.2f}")
    # the choice of period: each tap at its longest period, or averaged over its periods
    last, grp = {}, {}
    for r in cases:
        k = (r["pl"], r["tap"])
        if k not in last or r["T"] > last[k]["T"]:
            last[k] = r
        grp.setdefault(k, []).append(r)
    V.put("AllAltLongRms", _stats(list(last.values()))["rms"], "{:.0f}")
    V.put("AllAltMeanRms", _rms([np.mean([q["m_ps"] for q in v]) - v[0]["pred_ps"] for v in grp.values()]), "{:.0f}")
    # range of the margin and how often the sensor is late
    w = min(ind, key=lambda r: r["m_ps"])
    b = max(ind, key=lambda r: r["m_ps"])
    V.put("AllMinPs", w["m_ps"], "{:+.0f}")
    V.put("AllMinPsAbs", -w["m_ps"], "{:.0f}")
    V.put("AllMinSt", -w["m_steps"], "{:.1f}")
    V.put("AllMinmV", -w["m_mV"], "{:.0f}")
    V.put("AllMinStage", w["stage"], "{}")
    V.put("AllMinImpl", w["pl"])
    V.put("AllMinT", w["T"], "{}")
    V.put("AllMinDst", w["pred_ps"], "{:+.0f}")
    V.put("AllMaxPs", b["m_ps"], "{:+.0f}")
    V.put("AllMaxPsAbs", b["m_ps"], "{:.0f}")
    V.put("AllLateSure", sum(1 for r in ind if r["m_hi_ps"] < 0), "{}")
    V.put("AllLateBest", sum(1 for r in ind if r["m_ps"] < 0), "{}")
    V.put("AllEarly", sum(1 for r in ind if r["m_lo_ps"] > 0), "{}")
    V.put("AllZeroPtsMax", max(r["zero_points"] for r in ind), "{}")
    V.put("AllVfLo", min(r["V_f"] for r in ind), "{:.3f}")
    V.put("AllVfHi", max(r["V_f"] for r in ind), "{:.3f}")
    V.put("AllHalfW", np.mean([0.5 * (r["m_hi_ps"] - r["m_lo_ps"]) for r in ind]), "{:.0f}")
    V.put("AllKhiPs", max(r["k_steps_per_mV"] for r in ind) * STEP_TAP_PS, "{:.0f}")
    V.put("AllResVfR", np.corrcoef(y - x, [r["V_f"] for r in ind])[0, 1], "{:+.2f}")
    inside = [r for r in ind if r["m_lo_ps"] <= r["pred_ps"] <= r["m_hi_ps"]]
    V.put("AllInside", len(inside), "{}")
    V.put("AllMissMax", max(max(r["pred_ps"] - r["m_hi_ps"], r["m_lo_ps"] - r["pred_ps"])
                            for r in ind if r not in inside), "{:.0f}")
    raw = np.array([r["sta_ps"] for r in ind])
    V.put("AllRawR", np.corrcoef(raw, y)[0, 1], "{:.2f}")
    V.put("AllRawBiasAbs", abs(np.mean(y - raw)), "{:.0f}")
    # sweep-to-sweep spread: where every sweep first failed at the same voltage step, and how
    # many cases had their down and up sweeps fail one 10 mV step apart
    sd_same, split = [], 0
    for r in cases:
        vf = [q["V_f"] for q in res if q["impl"] == r["impl"] and q["tap"] == r["tap"]]
        if max(vf) - min(vf) < 0.005:      # every sweep first failed at the same 10 mV step
            sd_same.append(r["sd_steps"])
        else:
            split += 1
    V.put("AllSdMax", max(sd_same), "{:.1f}")
    V.put("AllSweepsMin", min(r["n"] for r in cases), "{}")
    V.put("AllSweepsMax", max(r["n"] for r in cases), "{}")
    V.put("AllVfSplit", split, "{}")
    V.put("AllSdSplitMax", max(r["sd_steps"] for r in cases), "{:.1f}")
    # STA terms over the independent taps of all placements
    V.put("AllDCPRLo", min(r["dcpr"] for r in ind), "{:.0f}")
    V.put("AllDCPRHi", max(r["dcpr"] for r in ind), "{:.0f}")
    V.put("AllDU", np.mean([r["du"] for r in ind]), "{:.0f}")

    # the three parts of Delta*: their spread, and how much of each the silicon shows
    for k, nm in (("clk", "Clk"), ("route", "Route")):
        v = [r[k] for r in ind]
        V.put(f"Dec{nm}Lo", min(v), "{:+.0f}")
        V.put(f"Dec{nm}Hi", max(v), "{:+.0f}")
    su = [r for r in ind if r["setup"] > 100]
    V.put("DecSuN", len(su), "{}")
    pls = sorted({r["pl"] for r in su})
    V.put("DecSuPl", ", ".join(pls[:-1]) + " and " + pls[-1] if len(pls) > 1 else pls[0])
    V.put("DecSuPs", np.mean([r["setup"] for r in su]), "{:.0f}")
    V.put("DecSuRes", np.mean([r["m_ps"] - r["pred_ps"] for r in su]), "{:+.0f}")
    V.put("DecSuNoRes", np.mean([r["m_ps"] - r["pred_ps"] + r["setup"] for r in su]), "{:+.0f}")
    X = np.c_[[r["clk"] for r in ind], [r["route"] for r in ind], [r["setup"] for r in ind], np.ones(len(ind))]
    co = np.linalg.lstsq(X, y, rcond=None)[0]
    rng = np.random.default_rng(2027)
    boot = np.array([np.linalg.lstsq(X[i], y[i], rcond=None)[0][:3]
                     for i in (rng.integers(0, len(y), len(y)) for _ in range(4000))])
    for k, nm in enumerate(("Clk", "Route", "Su")):
        V.put(f"DecCo{nm}", co[k], "{:.2f}")
        V.put(f"DecCo{nm}Lo", np.percentile(boot[:, k], 2.5), "{:.2f}")
        V.put(f"DecCo{nm}Hi", np.percentile(boot[:, k], 97.5), "{:.2f}")
    V.put("DecIcpt", co[3], "{:+.0f}")
    V.put("DecRms", _rms(y - X @ co), "{:.0f}")

    # the same tap at two periods: STA gives the same Delta*, the failure voltage moves
    dmax = 0.0
    for lab, dd in BUILD_OF.items():
        if guarded(lab) or lab == "Arep" or period_ns(lab) == 10:
            continue
        base = models[{"A": "A", "B": "B", "C": "C", "D": "D"}[placement(lab)]]
        dmax = max(dmax, max(abs(models[lab][j]["delta_si_ns"] - base[j]["delta_si_ns"]) * 1000 for j in base))
    V.put("PeriodDstMaxPs", round(dmax), "{:.0f}")
    pairs = []
    for k, v in grp.items():
        v = sorted(v, key=lambda r: r["V_f"])
        pairs += [(a, b2) for a, b2 in zip(v, v[1:])]
    V.put("PairN", len(pairs), "{}")
    V.put("PairDmPs", np.mean([abs(b2["m_ps"] - a["m_ps"]) for a, b2 in pairs]), "{:.0f}")
    V.put("PairDVmV", np.mean([b2["V_f"] - a["V_f"] for a, b2 in pairs]) * 1000, "{:.0f}")
    big = [(a, b2) for a, b2 in pairs if abs(a["pred_ps"]) >= 100]
    V.put("PairBigN", len(big), "{}")
    V.put("PairBigGrow", sum(1 for a, b2 in big if np.sign(a["pred_ps"]) * (a["m_ps"] - b2["m_ps"]) > 0), "{}")

    # guard bands: the realized 250 ps guard applied to every case, and a guard sized per
    # placement from STA alone (most negative Delta* of its routed design plus 2 sigma1)
    g250 = V.v["GuardPtPs"][0]
    late = [r for r in cases if r["m_ps"] + g250 <= 0]
    V.put("GuardFixLate", len(late), "{}")
    lp = sorted({r["pl"] for r in late})
    V.put("GuardFixLatePl", " and ".join(lp))
    base_dir = {"A": "impl", "B": "impl_b", "C": "impl_c", "D": "impl_d"}
    gpl = {p: -min(v["delta_si_ns"] for v in sta_model(dd).values()) * 1000 + 2 * sigma1
           for p, dd in base_dir.items()}
    for p, g in gpl.items():
        V.put(f"GuardPl{p}", g, "{:.0f}")
    V.put("GuardPlLo", min(gpl.values()), "{:.0f}")
    V.put("GuardPlHi", max(gpl.values()), "{:.0f}")
    V.put("GuardPlSetLo", int(np.ceil(min(gpl.values()) / 125.0)), "{}")
    V.put("GuardPlSetHi", int(np.ceil(max(gpl.values()) / 125.0)), "{}")
    V.put("GuardPlMinPs", min(r["m_ps"] + gpl[r["pl"]] for r in cases), "{:.0f}")
    V.put("GuardPlLate", sum(1 for r in cases if r["m_ps"] + gpl[r["pl"]] <= 0), "{}")

    # repeatability: placement A on both sessions, same bitstream and board
    a1 = {r["tap"]: r for r in s if r["impl"] == "A"}
    rep = [(r, a1[r["tap"]]) for r in s if r["impl"] == "Arep" and r["tap"] in a1]
    dm = [r["m_ps"] - a["m_ps"] for r, a in rep]
    V.put("RepN", len(rep), "{}")
    V.put("RepDLo", min(dm), "{:+.0f}")
    V.put("RepDHi", max(dm), "{:+.0f}")
    V.put("RepDMean", np.mean(dm), "{:+.0f}")
    V.put("RepDVfmV", max(abs(r["V_f"] - a["V_f"]) for r, a in rep) * 1000, "{:.1f}")

    sta_table(st, os.path.join(GEN, "tab_sta.tex"))
    return {"ind": ind, "cases": cases, "stats": st}


def sta_table(st: dict, path: str):
    """paper/generated/tab_sta.tex: the STA prediction per set of independent taps."""
    def row(label, k):
        d = st[k]
        return (f"{label} & {d['n']} & {d['r']:.2f} & {d['slope']:.2f} & {d['rms']:.0f} & "
                f"{d['null']:.0f} \\\\")
    lines = [r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
             r"Taps & $n$ & $r$ & slope & \multicolumn{2}{c}{rms (ps)} \\",
             r"\cmidrule(l){5-6}",
             r" & & & & $m-\Dst$ & $m-\bar{m}$ \\", r"\midrule",
             row("Session 1: A, B at 10\\,ns", "Sess"),
             row("Session 2: A, B at 12--18\\,ns", "ABLong"),
             row("Session 2: C, D$^\\dagger$", "CD"),
             row("All", "All"), r"\midrule"]
    lines += [row(f"Placement {p}", f"Pl{p}") for p in "ABCD"]
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(path, "w") as f:
        f.write("% generated by analysis/tap_values.py -- do not edit\n" + "\n".join(lines) + "\n")
