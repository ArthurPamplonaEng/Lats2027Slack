#!/usr/bin/env python3
"""Run every analysis, write paper/generated/values.tex and the figures.

    .venv/bin/python analysis/run_all.py
"""
from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import ROOT, V  # noqa: E402
import run1  # noqa: E402
import au15p_corners  # noqa: E402
import fig_run1  # noqa: E402

FROZEN = os.path.join(ROOT, "data", "au15p_tap", "build_frozen")
PLACEMENTS = ("impl", "impl_b", "impl_c", "impl_d")      # placements A-D at 10 ns


def sta() -> list[dict]:
    """Raw STA slack difference (FF2 minus FF1) of every tap of the four placements, from the
    frozen copies of taps_sta.csv; the ns-per-stage fit uses placement A."""
    tabs = {}
    for d in PLACEMENTS:
        path = os.path.join(FROZEN, d, "taps_sta.csv")
        if os.path.exists(path):
            with open(path) as f:
                tabs[d] = list(csv.DictReader(f))
    if "impl" not in tabs:
        return []
    rows = tabs["impl"]
    every = [r for t in tabs.values() for r in t]
    ds = [float(r["delta_ns"]) for r in every if r["corner"] == "Slow"]
    df = [float(r["delta_ns"]) for r in every if r["corner"] == "Fast"]
    V.put("StaDeltaLo", min(ds), "{:.2f}")
    V.put("StaDeltaHi", max(ds), "{:.2f}")
    V.put("StaDeltaPosN", sum(1 for v in ds if v > 0), "{}")
    V.put("StaDeltaTaps", len(ds), "{}")
    V.put("StaDeltaFastLo", min(df), "{:.2f}")
    V.put("StaDeltaFastHi", max(df), "{:.2f}")
    slow = [r for r in rows if r["corner"] == "Slow"]
    fast = [r for r in rows if r["corner"] == "Fast"]
    s_slow = [(float(r["ff2_delay_ns"]), int(r["stage"])) for r in slow]
    s_fast = [(float(r["ff2_delay_ns"]), int(r["stage"])) for r in fast]
    # ns per stage (linear fit over the graded taps)
    import numpy as np
    for name, pts in (("Slow", s_slow), ("Fast", s_fast)):
        d = np.array([p[0] for p in pts if p[1] >= 70])
        s = np.array([p[1] for p in pts if p[1] >= 70])
        V.put(f"StaStage{name}Ps", np.polyfit(s, d, 1)[0] * 1000.0, "{:.0f}")
    return rows


def main():
    r1 = run1.run()
    au15p_corners.run()
    rows = sta()
    # structure constants
    V.put("TapN", 23, "{}")
    V.put("TapNlong", 21, "{}")
    V.put("ChainStages", 160, "{}")
    V.put("MaxSteps", 440, "{}")
    # absolute values used in running text
    for nm in ("Hi", "Mid", "Lo"):
        V.put(f"Dslack{nm}Abs", abs(V.v[f"Dslack{nm}"][0]), "{:.0f}")
        V.put(f"Dps{nm}Abs", abs(V.v[f"Dps{nm}"][0]), "{:.0f}")
        V.put(f"HotMinusCold{nm}Abs", abs(V.v[f"HotMinusCold{nm}"][0]), "{:.0f}")
    try:
        import tap_values  # noqa: E402  (16 nm failure validation)
        tap_values.run()
    except (FileNotFoundError, ModuleNotFoundError) as e:
        print(f"16 nm tap data not found yet: {e}")
    fig_run1.make(r1)
    V.write()
    print(f"wrote {len(V.v)} values; STA rows: {len(rows)}")


if __name__ == "__main__":
    main()
