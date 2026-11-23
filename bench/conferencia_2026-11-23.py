"""Quick check of the 2026-11-23 bench (bench/ROTEIRO_revisao.md); not the paper analysis.

Measured margin m of every (implementation, tap) against the STA prediction Delta*, now including the
period variants of A and B (12-18 ns), the new implementations C and D (10 ns) and their 14/18 ns
variants. The repetition of A (shmooArep) is kept apart from the 20/11 data. It only extends the
IMPLS table of analysis/tap_offsets.py at run time; the analysis of section 5 of the roadmap is
separate. Numbers quoted in bench/REGISTRO_bancada_2026-11-23.md come from this script.

    .venv/bin/python -I bench/conferencia_2026-11-23.py
"""
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import tap_offsets as T  # noqa: E402
from common import STEP_TAP_PS  # noqa: E402
from tap_analysis import STAGES  # noqa: E402

GUARD_PS = 254      # realized guard of Section V-C (\vGuardPtPs)
PAPER_RMS_PS = 74   # rms of the paper before this bench (\vFitRms), fixed before these measurements

NEW = {f"impl_{p}{d}": f"{p.upper()}{d}" for p in "abcd" for d in (12, 14, 16, 18)}
NEW.update({"impl_c": "C", "impl_d": "D"})
T.IMPLS.update(NEW)

res = T.collect()
for r in res:
    if "Arep" in r["file"]:
        r["impl"] = "Arep"
base = {"A": "impl", "Arep": "impl", "B": "impl_b", "C": "impl_c", "D": "impl_d"}
base.update({v: k for k, v in NEW.items()})
models = {name: T.sta_model(d) for name, d in base.items()}

rows = []
for imp in sorted({r["impl"] for r in res}):
    if "'" in imp:          # designed-guard builds (A', B', B'') stay out of the offset test
        continue
    for j in sorted({r["tap"] for r in res if r["impl"] == imp}):
        rs = [r for r in res if r["impl"] == imp and r["tap"] == j]
        rows.append({
            "impl": imp, "tap": j, "S": STAGES[j], "n": len(rs),
            "m": np.mean([r["m_steps"] for r in rs]) * STEP_TAP_PS,
            "sd": (np.std([r["m_steps"] for r in rs]) * STEP_TAP_PS) if len(rs) > 1 else 0.0,
            "lo": np.mean([r["m_lo"] for r in rs]) * STEP_TAP_PS,
            "hi": np.mean([r["m_hi"] for r in rs]) * STEP_TAP_PS,
            "pred": models[imp].get(j, {}).get("delta_si_ns", np.nan) * 1000.0,
            "Vf": np.mean([r["V_f"] for r in rs]),
        })

print("impl  S    n   m(ps)  sd  [lo, hi] ps      Delta*  m-D*   V_f")
for r in rows:
    print(f"{r['impl']:5s} {r['S']:<4d} {r['n']:2d} {r['m']:+6.0f} {r['sd']:3.0f} [{r['lo']:+5.0f},{r['hi']:+5.0f}] "
          f"{r['pred']:+6.0f} {r['m'] - r['pred']:+6.0f}  {r['Vf']:.3f}")


def stats(sel, label):
    x = np.array([r["pred"] for r in sel])
    y = np.array([r["m"] for r in sel])
    e = y - x
    print(f"{label}: n={len(sel)} r={np.corrcoef(x, y)[0, 1]:+.2f} slope={np.polyfit(x, y, 1)[0]:.2f} "
          f"rms(m-D*)={np.sqrt(np.mean(e ** 2)):.0f} ps bias={e.mean():+.0f} ps | best constant {y.std():.0f} ps")


def period(r):
    return 10 if len(r["impl"]) == 1 else int(r["impl"][1:])


measured = [r for r in rows if r["impl"] != "Arep"]
# one entry per (placement, tap): the 10 ns value if any, else the shortest period that crosses
by = {}
for r in measured:
    key = (r["impl"][0], r["tap"])
    if key not in by or period(r) < period(by[key]):
        by[key] = r
indep = list(by.values())

print("\n-- Delta* against m (no fitted parameter)")
stats([r for r in rows if r["impl"] in ("A", "B")], "20/11, A+B at 10 ns (the paper)")
stats(indep, "independent taps, A B C D")
stats([r for r in indep if not (r["impl"] == "A" and r["S"] == 74)], "independent, without A-S74")
stats([r for r in indep if r["impl"] not in ("A", "B")], "new taps only (out of sample)")
stats([r for r in indep if r["impl"][0] in "AB" and r["impl"] not in ("A", "B")], "A+B long periods")
stats([r for r in indep if r["impl"][0] in "CD"], "C+D (Delta* committed in 812b19e before measuring)")
stats([r for r in indep if r["impl"] in ("C", "D")], "C+D at 10 ns only")
for pl in "ABCD":
    stats([r for r in indep if r["impl"][0] == pl], f"placement {pl}")

e = np.array([r["m"] - r["pred"] for r in indep])
print(f"|m-D*|: median {np.median(abs(e)):.0f} ps, 90th pct {np.percentile(abs(e), 90):.0f} ps, max {abs(e).max():.0f} ps; "
      + ", ".join(f"within +-{b} ps {np.mean(abs(e) <= b) * 100:.0f}%" for b in (100, 150, 200)))
for sel, lab in ((indep, "independent"), (measured, "all rows")):
    vf = np.array([r["Vf"] for r in sel])
    ee = np.array([r["m"] - r["pred"] for r in sel])
    print(f"corr(m-D*, V_f), {lab}: n={len(sel)} r={np.corrcoef(ee, vf)[0, 1]:+.2f} over {vf.min():.3f}-{vf.max():.3f} V")
late = [r for r in indep if r["m"] < 0 <= r["pred"]]
print("late (m<0) although Delta*>=0: " + ", ".join(f"{r['impl']} S{r['S']} m {r['m']:+.0f} / D* {r['pred']:+.0f}" for r in late))

print("\n-- repetition of A (23/11) against 20/11")
A = {r["S"]: r for r in rows if r["impl"] == "A"}
for r in [r for r in rows if r["impl"] == "Arep"]:
    a = A[r["S"]]
    print(f"S{r['S']}: m {a['m']:+.0f} -> {r['m']:+.0f} ps ({r['m'] - a['m']:+.0f}); V_f {a['Vf']:.3f} -> {r['Vf']:.3f} V")

print(f"\n-- latest offsets and guard bands (m<0: the reading reaches zero after the first error)")
for pl in "ABCD":
    rs = [r for r in measured if r["impl"][0] == pl]
    w = min(rs, key=lambda r: r["m"])
    g = -min(r["pred"] for r in rs) + 2 * PAPER_RMS_PS
    print(f"{pl}: latest m {w['m']:+.0f} ps at {w['impl']} S{w['S']} (D* {w['pred']:+.0f}); min D* {min(r['pred'] for r in rs):+.0f}; "
          f"rows late with the {GUARD_PS} ps guard: "
          + (", ".join(f"{r['impl']} S{r['S']} ({r['m']:+.0f})" for r in rs if r["m"] + GUARD_PS <= 0) or "none")
          + f"; guard -min(D*)+2x{PAPER_RMS_PS} = {g:.0f} ps leaves min(m+g) = {min(r['m'] for r in rs) + g:+.0f} ps")

print("\n-- same (placement, tap) at several periods")
pairs = {}
for r in measured:
    pairs.setdefault((r["impl"][0], r["tap"]), []).append(r)
d = []
for (pl, j), rs in sorted(pairs.items()):
    if len(rs) > 1:
        print(f"  {pl} S{STAGES[j]} (D* {rs[0]['pred']:+.0f}): " + ", ".join(f"{r['impl']} {r['m']:+.0f}" for r in rs))
        rs = sorted(rs, key=lambda r: r["Vf"])
        d += [(b["Vf"] - a["Vf"], b["m"] - a["m"], a["pred"]) for a, b in zip(rs, rs[1:])]
d = np.array(d)
print(f"pairs: n={len(d)}, mean |dm| {np.mean(abs(d[:, 1])):.0f} ps for mean dV_f {np.mean(d[:, 0]) * 1000:.0f} mV; "
      f"m moves toward zero as V_f rises in {np.mean(np.sign(d[:, 2]) * d[:, 1] < 0) * 100:.0f}% of the pairs")

print("\n-- integrity: bitstream MD5 recorded by tapbench against build_frozen/MD5SUMS")
md5 = dict(reversed(line.split()) for line in open("data/au15p_tap/build_frozen/MD5SUMS"))
files = sorted(f for f in os.listdir("data/au15p_tap") if re.match(r"tap_shmoo.*_20261123_.*\.csv\.json$", f))
bad = [f for f in files
       if (lambda m: md5.get(re.search(r"/build/([^/]+)/", m["bitstream"]).group(1) + "/tap_top.bit") != m["bitstream_md5"])(
           json.load(open(os.path.join("data/au15p_tap", f))))]
print(f"{len(files)} shmoos of 23/11, MD5 mismatches: {bad or 'none'}")
