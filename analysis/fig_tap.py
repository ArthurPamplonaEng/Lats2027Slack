"""Figures of the 16 nm failure validation (tapped chain on the AU15P).

fig_tap_shmoo : reading versus VCCINT for the taps whose failure boundary falls inside the sweep
                (placement A, solid; the same routed design with the 250 ps guard, dashed; x: first
                failing voltage), and a close-up near zero that shows how the margin m is obtained:
                the line through the lowest error-free readings extrapolated to the failure voltage,
                and the readings of failing points at which every sweep still alarmed.
fig_tap_offset: measured margin at failure (reading-zero minus first error, in ps) against the
                static-timing prediction, for the independent taps of the four placements (each tap
                once per placement, at the shortest period at which it fails inside the range).
                Filled: 10 ns; hollow: 12-18 ns (same routing, MMCM dividers only).
"""
from __future__ import annotations

import numpy as np

import figstyle as fs
from common import STEP_TAP_PS
from tap_analysis import STAGES, margin_steps, vaxis

PLACE = {"A": ("o", fs.C["blue"]), "B": ("^", fs.C["green"]), "C": ("s", fs.C["orange"]),
         "D": ("D", fs.C["purple"])}


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


def offset(ind, name="fig_tap_offset"):
    """ind: the independent taps (dicts with pl, T, pred_ps, m_ps, m_lo_ps, m_hi_ps)."""
    fs.setup()
    fig, ax = fs.plt.subplots(figsize=(fs.COL_W, 2.55))
    allx = [r["pred_ps"] for r in ind]
    lo, hi = min(allx) - 50, max(allx) + 50
    ax.fill_between([lo, hi], 0, -1000, color=fs.C["red"], alpha=0.06, lw=0)
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.6, zorder=2)
    ax.axhline(0, color=fs.C["grey"], lw=0.5)
    ax.axvline(0, color=fs.C["grey"], lw=0.5)
    for pl, (mk, col) in PLACE.items():
        for long_t in (False, True):
            rs = [r for r in ind if r["pl"] == pl and (r["T"] > 10) == long_t]
            if not rs:
                continue
            x = np.array([r["pred_ps"] for r in rs])
            y = np.array([r["m_ps"] for r in rs])
            e = np.clip(np.array([[r["m_ps"] - r["m_lo_ps"] for r in rs],
                                  [r["m_hi_ps"] - r["m_ps"] for r in rs]]), 0, None)
            n = sum(1 for r in ind if r["pl"] == pl)
            ax.errorbar(x, y, yerr=e, fmt=mk, color=col, ms=3.0, mfc="white" if long_t else col,
                        mew=0.8, lw=0.45, capsize=0, alpha=0.9, zorder=4,
                        label=None if long_t else f"{pl} ({n})")
    ax.plot([], [], "o", color="k", ms=3.0, label="10 ns")
    ax.plot([], [], "o", color="k", mfc="white", mew=0.8, ms=3.0, label="12\u201318 ns")
    ax.plot([], [], "k--", lw=0.6, label="$m=\\Delta_\\mathrm{STA}^{*}$")
    ax.text(hi - 10, -18, "errors while $r>0$", fontsize=6.5, color=fs.C["red"], va="top", ha="right")
    ytop = max(r["m_hi_ps"] for r in ind) + 30
    ybot = min(r["m_lo_ps"] for r in ind) - 30
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(ybot, lo), max(ytop, hi))
    ax.set_xlabel(r"predicted offset $\Delta^{*}_\mathrm{STA}$ (ps)")
    ax.set_ylabel("measured margin $m$ (ps)")
    h, lab = ax.get_legend_handles_labels()
    order = [lab.index(k) for k in lab if k[0] in "ABCD"] + [lab.index(k) for k in lab if k[0] not in "ABCD"]
    ax.legend([h[i] for i in order], [lab[i] for i in order], loc="upper left", fontsize=6.0,
              handlelength=1.4, ncol=2, columnspacing=0.8, borderaxespad=0.3)
    ax.grid(True, lw=0.3, alpha=0.4)
    sec = ax.secondary_yaxis("right", functions=(lambda ps: ps / STEP_TAP_PS, lambda st: st * STEP_TAP_PS))
    sec.set_ylabel("steps")
    fs.save(fig, name)
