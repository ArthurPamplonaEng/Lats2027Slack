#!/usr/bin/env bash
# Build tap_top: scripts/build.sh [out_dir] [jobs]  (Vivado 2025.2 by default, VIVADO_BIN to change)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VIV="${VIVADO_BIN:-$HOME/2025.2/Vivado/bin/vivado}"
OUT="$(mkdir -p "${1:-$ROOT/build/impl}" && cd "${1:-$ROOT/build/impl}" && pwd)"
JOBS="${2:-8}"
mkdir -p "$OUT"
cd "$OUT"
"$VIV" -mode batch -nojournal -log "$OUT/build.log" -source "$ROOT/scripts/build.tcl" -tclargs "$OUT" "$JOBS"
grep -E "TAPIMPL|TAPSTA|TAPBUILD|^ERROR|CRITICAL WARNING" "$OUT/build.log" | head -40
