"""Fig.: 28 nm slack-voltage curves of the 16-bit adder path before and after the 214.6 h burn-in
(~104 C), the post-burn-in curve moved by the fitted supply shift (it passes through the
pre-burn-in corners), and the cold (~46 C) post-burn-in corners that show the sign change of the
temperature coefficient near 1.0 V."""
from __future__ import annotations

import numpy as np

import figstyle as fs
from common import STEP_NEXYS_PS
from run1 import CORNERS_V, run


def make(r: dict | None = None):
    r = r or run()
    fs.setup()
    ps, cs, sh = r["post"], r["corners"], r["shift"]
    fig, ax = fs.plt.subplots(figsize=(fs.COL_W, 2.2))

    lv, mean, n = ps["levels"], ps["mean"], ps["n"]
    ax.scatter(lv, mean, s=np.clip(np.sqrt(n) * 1.2, 3, 14), color=fs.C["red"], zorder=3, lw=0,
               label="after burn-in, logged sweep (104 °C)")
    vv = np.linspace(0.885, 1.105, 200)
    ax.plot(vv, sh["f"](vv), "-", color=fs.C["red"], lw=0.7, zorder=2)
    ax.plot(vv, sh["f"](vv + sh["dv"]), "--", color=fs.C["blue"], lw=0.8, zorder=2,
            label=f"after, shifted by $-${sh['dv'] * 1000:.1f} mV")

    pre_v = np.array(CORNERS_V)
    pre_s = np.array([cs["pre"][v][0] for v in CORNERS_V])
    ax.plot(pre_v, pre_s, "o", color=fs.C["blue"], mfc="white", mew=1.0, ms=4.6, zorder=5,
            label="before burn-in (104 °C)")
    cold_s = np.array([cs["post_cold"][v][0] for v in CORNERS_V])
    ax.plot(pre_v, cold_s, "s:", color=fs.C["green"], ms=3.4, lw=0.8, zorder=4,
            label="after burn-in, cold (46 °C)")

    for v in CORNERS_V:
        pre = cs["pre"][v][0]
        post = np.median(ps["s_all"][(ps["vr_all"] == v)])
        ax.annotate(f"{post - pre:+.0f}", xy=(v, post), xytext=(4, -3), textcoords="offset points",
                    fontsize=6.5, ha="left", va="top", color=fs.C["red"])

    ax.set_xlabel(r"$V_\mathrm{CCINT}$ (V, XADC)")
    ax.set_ylabel("slack reading (steps)")
    ax.set_xlim(0.88, 1.12)
    sec = ax.secondary_yaxis("right", functions=(lambda c: c * STEP_NEXYS_PS / 1000.0,
                                                 lambda ns: ns * 1000.0 / STEP_NEXYS_PS))
    sec.set_ylabel("slack (ns)")
    ax.legend(loc="lower right", handlelength=1.8, borderaxespad=0.2, fontsize=6.3)
    ax.grid(True, lw=0.3, alpha=0.4)
    fs.save(fig, "fig_run1_corners")


if __name__ == "__main__":
    make()
    print("ok")
