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

TAP_BUILD = os.path.join(ROOT, "hw", "au15p_tap", "build", "impl")
TAP_STA_FROZEN = os.path.join(ROOT, "data", "au15p_tap", "build_frozen", "taps_sta.csv")


def sta() -> list[dict]:
    path = TAP_STA_FROZEN if os.path.exists(TAP_STA_FROZEN) else os.path.join(TAP_BUILD, "taps_sta.csv")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        rows = list(csv.DictReader(f))
    slow = [r for r in rows if r["corner"] == "Slow"]
    fast = [r for r in rows if r["corner"] == "Fast"]
    ds = [float(r["delta_ns"]) for r in slow]
    df = [float(r["delta_ns"]) for r in fast]
    V.put("StaDeltaLo", min(ds), "{:.2f}")
    V.put("StaDeltaHi", max(ds), "{:.2f}")
    V.put("StaDeltaFastLo", min(df), "{:.2f}")
    V.put("StaDeltaFastHi", max(df), "{:.2f}")
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
