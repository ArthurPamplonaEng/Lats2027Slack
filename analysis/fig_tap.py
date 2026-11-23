"""Figures of the 16 nm failure validation (tapped chain on the AU15P).

fig_tap_shmoo : reading versus VCCINT for the taps whose failure boundary falls inside the sweep
                (placement A, solid; the same routed design with the 250 ps guard, dashed), and the
                error rate of the failing points.
fig_tap_offset: measured margin at failure (reading-zero minus first error, in ps) against the
                static-timing prediction. Filled: the independent taps of the two placements without
                guard (the model statistics use only these); hollow: the same taps with a guard.
"""
from __future__ import annotations

import numpy as np

import figstyle as fs
from common import STEP_TAP_PS
from tap_analysis import STAGES, vaxis

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


def shmoo(sweep, taps_sel, name="fig_tap_shmoo", guard=None):
    fs.setup()
    cmap = fs.plt.get_cmap("viridis")
    fig, (ax, ax2) = fs.plt.subplots(2, 1, figsize=(fs.COL_W, 2.85), sharex=True,
                                     gridspec_kw={"height_ratios": [2.7, 1.0], "hspace": 0.07})
    smin, smax = min(STAGES[j] for j in taps_sel), max(STAGES[j] for j in taps_sel)
    vmax = max(vaxis(p) for p in sweep)
    for j in taps_sel:
        col = cmap(0.05 + 0.85 * (STAGES[j] - smin) / max(smax - smin, 1))
        v, r, er = _curve(sweep, j)
        ax.plot(v, r, "-o", color=col, ms=1.9, lw=0.8)
        ok = np.isfinite(r)
        if ok.any():
            k = np.argmax(np.where(ok, v, -np.inf))
            ax.annotate(f"S{STAGES[j]}", (v[k], r[k]), xytext=(3, 0), textcoords="offset points",
                        fontsize=6, color=col, ha="left", va="center")
        if guard is not None:
            vg, rg, _ = _curve(guard, j)
            ax.plot(vg, rg, "--", color=col, lw=0.7, alpha=0.9)
        bad = er > 0
        ax2.semilogy(v[bad], er[bad], "-x", color=col, ms=3.0, mew=0.8, lw=0.6)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("reading $r$ (steps)")
    ax.set_ylim(-3, None)
    ax.set_xlim(None, vmax + 0.022)
    if guard is not None:
        ax.plot([], [], "k-", lw=0.8, label="placement A")
        ax.plot([], [], "k--", lw=0.7, label="A + 250 ps guard")
        ax.legend(loc="upper left", fontsize=6.3, handlelength=2.0)
    ax2.set_ylabel("error rate")
    ax2.set_xlabel(r"$V_\mathrm{CCINT}$ (V, SYSMON)")
    ax2.set_ylim(5e-5, 2)
    ax2.set_yticks([1e-4, 1e-2, 1])
    for a in (ax, ax2):
        a.grid(True, lw=0.3, alpha=0.4)
    fs.save(fig, name)


def offset(summary, name="fig_tap_offset"):
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
