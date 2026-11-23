#!/usr/bin/env bash
# Behavioural simulation of tap_top (xsim, real MMCME4_ADV model). Prints "TB RESULT: PASS".
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VIV="${VIVADO_BIN:-$HOME/2025.2/Vivado/bin/vivado}"
BIN="$(dirname "$VIV")"
XV="$(cd "$BIN/.." && pwd)"
OUT="${1:-$ROOT/build/sim}"
# Vivado's bundled gcc does not search the Debian/Ubuntu multiarch path for crti.o
export LIBRARY_PATH="/usr/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
mkdir -p "$OUT"
cd "$OUT"
"$BIN/xvlog" --sv -d TAP_SIM \
  "$ROOT/rtl/tap_pkg.sv" "$ROOT/rtl/tap_clocks.sv" "$ROOT/rtl/tap_chain.sv" \
  "$ROOT/rtl/tap_sensor.sv" "$ROOT/rtl/tap_sweep.sv" "$ROOT/rtl/tap_stats.sv" \
  "$ROOT/rtl/tap_top.sv" "$HERE/tb_tap.sv" > xvlog.log 2>&1 || { tail -30 xvlog.log; exit 1; }
"$BIN/xvlog" "$XV/data/verilog/src/glbl.v" >> xvlog.log 2>&1
"$BIN/xelab" -L unisims_ver -L secureip --relax -timescale 1ns/1ps tb_tap glbl -s tb_tap_snap \
  > xelab.log 2>&1 || { tail -30 xelab.log; exit 1; }
"$BIN/xsim" tb_tap_snap -R > xsim.log 2>&1 || true
grep -E "^TB" xsim.log
