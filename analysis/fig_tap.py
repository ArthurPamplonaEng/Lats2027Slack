"""Figures of the 16 nm failure validation (tapped chain on the AU15P).

fig_tap_shmoo : reading versus VCCINT for the taps whose failure boundary falls inside the sweep
                (placement A, solid; the same routed design with the 250 ps guard, dashed; x: first
                failing voltage), and a close-up near zero that shows how the margin m is obtained:
                the line through the lowest error-free readings extrapolated to the failure voltage,
                and the readings of failing points at which every sweep still alarmed.
fig_tap_offset: measured margin at failure (reading-zero minus first error, in ps) against the
                static-timing prediction. Filled: the independent taps of the two placements without
                guard (the model statistics use only these); hollow: the same taps with a guard.
"""
from __future__ import annotations

import numpy as np

import figstyle as fs
from common import STEP_TAP_PS
from tap_analysis import STAGES, margin_steps, vaxis

STYLE = {"A": ("o", fs.C["blue"], True, "placement A"),
         "B": ("^", fs.C["green"], True, "placement B"),
         "A'": ("o", fs.C["blue"], False, "A + 250 ps guard"),
         "B'": ("^", fs.C["green"], False, "B + 250 ps guard"),
         "B''": ("D", fs.C["purple"], False, "B + 125 ps guard")}


def _curve(sweep, j):
    seq = sorted(sweep, key=vaxis)
    v = np.array([vaxis(p) for p in seq])
    st = [p.state(j) for p in seq]
    r = np.array([p.reading[j] if s in ("OK", "ZERO") else np.nan for s, p in zip(st, seq)])
    er = np.array([p.err_rate[j] for p in seq])
    return v, r, er


def shmoo(sweep, taps_sel, name="fig_tap_shmoo", guard=None, example=None):
    """example: stage whose margin is drawn as an arrow in the close-up."""
    fs.setup()
    cmap = fs.plt.get_cmap("viridis")
    fig, (ax, ax2) = fs.plt.subplots(2, 1, figsize=(fs.COL_W, 3.25), sharex=True,
                                     gridspec_kw={"height_ratios": [2.0, 1.45], "hspace": 0.08})
    smin, smax = min(STAGES[j] for j in taps_sel), max(STAGES[j] for j in taps_sel)
    vmax = max(vaxis(p) for p in sweep)
    for j in taps_sel:
        col = cmap(0.05 + 0.80 * (STAGES[j] - smin) / max(smax - smin, 1))
        v, r, er = _curve(sweep, j)
        ax.plot(v, r, "-o", color=col, ms=1.9, lw=0.8)
        ok = np.isfinite(r)
        if ok.any():
            k = np.argmax(np.where(ok, v, -np.inf))
            ax.annotate(f"S{STAGES[j]}", (v[k], r[k]), xytext=(3, 0), textcoords="offset points",
                        fontsize=6.5, color=col, ha="left", va="center")
        if guard is not None:
            vg, rg, _ = _curve(guard, j)
            ax.plot(vg, rg, "--", color=col, lw=0.7, alpha=0.9)
        ms = margin_steps(sweep, j)
        if ms is None:
            continue
        for a in (ax, ax2):
            a.plot(ms["V_f"], 0, "x", color=col, ms=4.2, mew=1.1, zorder=6, clip_on=False)
        # close-up: error-free readings, the fitted line down to the failure voltage, and the
        # failing points at which every sweep still alarmed (not aliased)
        ax2.plot(v, r, "o", color=col, ms=2.3, zorder=4)
        kk = ms["k_steps_per_mV"] * 1000.0
        vv = np.linspace(ms["V_f"], ms["V_fit_lo"] + 0.012, 30)
        ax2.plot(vv, kk * (vv - ms["V_0"]), "-", color=col, lw=0.7, zorder=3)
        fp = [(vaxis(p), p.reading[j]) for p in sweep
              if p.state(j) == "FAIL" and p.got_frac[j] > 0.999 and 0 < p.reading[j] < 30]
        if fp:
            ax2.plot([a for a, _ in fp], [b for _, b in fp], "o", mfc="white", mec=col, mew=0.9,
                     ms=3.2, zorder=5)
        if STAGES[j] == example:
            r_star = kk * (ms["V_star"] - ms["V_0"])
            ax2.annotate("", xy=(ms["V_star"], 0), xytext=(ms["V_star"], r_star),
                         arrowprops={"arrowstyle": "<->", "lw": 0.7, "color": "k",
                                     "shrinkA": 0, "shrinkB": 0}, zorder=7)
            ax2.text(ms["V_star"] + 0.024, 0.62 * r_star, f"$m={ms['m_steps']:+.0f}$ steps\n(S{STAGES[j]})",
                     fontsize=6.3, ha="left", va="center")
    ax.axhline(0, color="k", lw=0.5)
    ax2.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("reading $r$ (steps)")
    ax.set_ylim(-3, None)
    ax.set_xlim(None, vmax + 0.022)
    if guard is not None:
        ax.plot([], [], "k-", lw=0.8, label="placement A")
        ax.plot([], [], "k--", lw=0.7, label="A + 250 ps guard")
        ax.plot([], [], "kx", ms=4.2, mew=1.1, label="first error ($V_f$)")
        ax.legend(loc="upper left", fontsize=6.3, handlelength=2.0)
    ax2.plot([], [], "ko", ms=2.3, label="no error")
    ax2.plot([], [], "ko", mfc="white", mew=0.9, ms=3.2, label="errors, still alarming")
    ax2.plot([], [], "k-", lw=0.7, label="3-point line")
    ax2.legend(loc="lower right", fontsize=6.0, handlelength=1.6, ncol=1, borderaxespad=0.2)
    ax2.set_ylabel("$r$ near zero")
    ax2.set_ylim(-22, 27)
    ax2.set_xlabel(r"$V_\mathrm{CCINT}$ (V, SYSMON)")
    for a in (ax, ax2):
        a.grid(True, lw=0.3, alpha=0.4)
    fs.save(fig, name)


def offset(summary, name="fig_tap_offset", mark=None):
    """mark: (implementation, stage) of a tap to label."""
    fs.setup()
    fig, ax = fs.plt.subplots(figsize=(fs.COL_W, 2.35))
    allx = []
    for imp, (mk, col, filled, lab) in STYLE.items():
        rs = [r for r in summary if r["impl"] == imp and np.isfinite(r["pred_ps"])]
        if not rs:
            continue
        x = np.array([r["pred_ps"] for r in rs])
        y = np.array([r["m_ps"] for r in rs])
        e = np.clip(np.array([[r["m_ps"] - r["m_lo_ps"] for r in rs],
                              [r["m_hi_ps"] - r["m_ps"] for r in rs]]), 0, None)
        allx += list(x)
        ax.errorbar(x, y, yerr=e, fmt=mk, color=col, ms=3.6, mfc=col if filled else "white",
                    mew=0.9, lw=0.6, capsize=1.2, label=lab, alpha=1.0 if filled else 0.85,
                    zorder=4 if filled else 3)
    if mark is not None:
        r = next((r for r in summary if (r["impl"], r["stage"]) == mark), None)
        if r is not None:
            ax.annotate(f"S{r['stage']} ({r['impl']}): late\nFF2 clock", (r["pred_ps"], r["m_ps"]),
                        xytext=(-6, 6), textcoords="offset points", fontsize=6.3, ha="right",
                        va="bottom", color=fs.C["blue"])
    lo, hi = (min(allx) - 60, max(allx) + 60) if allx else (-300, 500)
    ytop = max([r["m_hi_ps"] for r in summary if np.isfinite(r["pred_ps"])] + [hi]) + 40
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.6, label="$m=\\Delta_\\mathrm{STA}^{*}$")
    ax.axhline(0, color=fs.C["grey"], lw=0.5)
    ax.axvline(0, color=fs.C["grey"], lw=0.5)
    ax.fill_between([lo, hi], 0, -1000, color=fs.C["red"], alpha=0.06, lw=0)
    ax.text(hi - 10, -20, "errors while $r>0$", fontsize=6.5, color=fs.C["red"], va="top", ha="right")
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(lo, -300), max(ytop, 450))
    ax.set_xlabel(r"predicted offset $\Delta^{*}_\mathrm{STA}$ (ps)")
    ax.set_ylabel("measured margin $m$ (ps)")
    ax.legend(loc="upper left", fontsize=6.0, handlelength=1.5, ncol=1)
    ax.grid(True, lw=0.3, alpha=0.4)
    sec = ax.secondary_yaxis("right", functions=(lambda ps: ps / STEP_TAP_PS, lambda st: st * STEP_TAP_PS))
    sec.set_ylabel("steps")
    fs.save(fig, name)
