"""16 nm stress bound (AU15P, RV02A boards A and B, au15p_hub_B bitstream, 19.841 ps per step).

Corners at room temperature (oven off) before (2026-11-07) and after (2026-11-09) the 37.4 h run
Cornerdesabadoadomingo_20261107_212830 (both boards at VCCINT 0.85 V closed loop, oven 85 C).
"""
from __future__ import annotations

import os

import numpy as np

from common import DATA, STEP_AU15P_HUB_PS, V, read_cols, read_csv_dicts

D = os.path.join(DATA, "au15p")


def corners() -> dict:
    pre = read_csv_dicts(os.path.join(D, "corners", "corners_20261107_124606_resumo.csv"))
    post = read_csv_dicts(os.path.join(D, "corners", "corners_20261109_161850_resumo.csv"))
    out = {}
    for b in ("placa A", "placa B"):
        rows = []
        for p in ("1", "2", "3"):      # 0.85, 0.90, 0.95 V; point 4 ("volta") is not comparable on 07/11
            a = next(r for r in pre if r["placa"] == b and r["ponto"] == p)
            z = next(r for r in post if r["placa"] == b and r["ponto"] == p)
            rows.append({
                "target": float(a["alvo_v"]),
                "vcc_pre": float(a["vccint_v"]), "vcc_post": float(z["vccint_v"]),
                "s_pre": float(a["slack_media"]), "s_post": float(z["slack_media"]),
                "sd_pre": float(a["slack_dp_entre_janelas"]), "sd_post": float(z["slack_dp_entre_janelas"]),
                "T_pre": float(a["die_c"]), "T_post": float(z["die_c"]),
                "n": int(a["janelas"]),
            })
        out[b] = rows
    return out


def run37() -> dict:
    cols = ["time_sec", "oven_temp_c"] + [f"{k}_{x}" for k in ("d0", "d1")
                                          for x in ("vccint_v", "temp_c", "slack_mean")]
    d = read_cols(os.path.join(D, "run_37h", "Cornerdesabadoadomingo_20261107_212830.csv"), cols)
    t = d["time_sec"]
    r = {"dur_h": (np.nanmax(t) - np.nanmin(t)) / 3600.0, "oven": np.nanmean(d["oven_temp_c"])}
    for k, b in (("d0", "A"), ("d1", "B")):
        r[f"V{b}"] = np.nanmean(d[f"{k}_vccint_v"])
        r[f"Vsd{b}"] = np.nanstd(d[f"{k}_vccint_v"])
        r[f"T{b}"] = np.nanmean(d[f"{k}_temp_c"])
        r[f"Tsd{b}"] = np.nanstd(d[f"{k}_temp_c"])
        r[f"S{b}"] = np.nanmean(d[f"{k}_slack_mean"])
    return r


def run() -> dict:
    cs = corners()
    r = run37()
    V.put("UsDurH", r["dur_h"], "{:.1f}")
    V.put("UsOven", r["oven"], "{:.0f}")
    V.put("UsVA", r["VA"], "{:.3f}")
    V.put("UsTA", r["TA"], "{:.0f}")
    V.put("UsTsdA", r["TsdA"], "{:.1f}")
    V.put("UsTB", r["TB"], "{:.0f}")
    V.put("UsStepPs", STEP_AU15P_HUB_PS, "{:.2f}")
    dmax = 0.0
    for b, tag in (("placa A", "A"), ("placa B", "B")):
        for row, nm in zip(cs[b], ("Lo", "Mid", "Hi")):
            ds = row["s_post"] - row["s_pre"]
            dmax = max(dmax, abs(ds))
            V.put(f"UsPre{tag}{nm}", row["s_pre"], "{:.2f}")
            V.put(f"UsPost{tag}{nm}", row["s_post"], "{:.2f}")
            V.put(f"UsD{tag}{nm}", ds, "{:+.2f}")
            V.put(f"UsT{tag}{nm}", row["T_pre"], "{:.0f}")
    V.put("UsDmax", dmax, "{:.1f}")
    V.put("UsDmaxPs", dmax * STEP_AU15P_HUB_PS, "{:.0f}")
    # path delay of the measured path at 0.85 V on board A: one period minus the reading (upper bound)
    a = cs["placa A"][0]
    V.put("UsPathNs", (10.0 - a["s_pre"] * STEP_AU15P_HUB_PS / 1000.0), "{:.1f}")
    V.put("UsSensA", (cs["placa A"][2]["s_pre"] - cs["placa A"][0]["s_pre"]) /
          (cs["placa A"][2]["vcc_pre"] - cs["placa A"][0]["vcc_pre"]) / 10.0, "{:.1f}")  # counts / 10 mV
    return {"corners": cs, "run": r}


if __name__ == "__main__":
    out = run()
    for k, (v, f) in sorted(V.v.items()):
        print(k, f.format(v) if not isinstance(v, str) else v)
