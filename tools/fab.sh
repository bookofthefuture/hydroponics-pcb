#!/usr/bin/env bash
# Regenerate fabrication + assembly outputs for a board from KiCad source.
# Requires kicad-cli (KiCad 10.x) and the standard symbol/footprint libraries.
#
# Usage:  tools/fab.sh <board-dir>
#   e.g.  tools/fab.sh tray-board
#
# Output goes to <board-dir>/production/  (git-ignored) as a fab-ready zip.

set -euo pipefail

board_dir="${1:?usage: tools/fab.sh <board-dir>}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
board_dir="$repo_root/$board_dir"

pcb="$(find "$board_dir" -name '*.kicad_pcb' -not -path '*-backups/*' | head -1)"
sch="${pcb%.kicad_pcb}.kicad_sch"
name="$(basename "${pcb%.kicad_pcb}")"
out="$board_dir/production"

[ -f "$pcb" ] || { echo "no .kicad_pcb found under $board_dir" >&2; exit 1; }

rm -rf "$out"
mkdir -p "$out/gerbers"

echo "==> ERC"
kicad-cli sch erc --exit-code-violations --severity-error --severity-warning \
  "$sch" -o "$out/${name}-erc.rpt"

echo "==> DRC"
kicad-cli pcb drc --exit-code-violations --severity-error --severity-warning \
  "$pcb" -o "$out/${name}-drc.rpt"

echo "==> Gerbers (fab layers only)"
kicad-cli pcb export gerbers --no-protel-ext --subtract-soldermask \
  --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts \
  --output "$out/gerbers/" "$pcb"

echo "==> Drill (Excellon, PTH/NPTH merged, drill-origin)"
kicad-cli pcb export drill --format excellon --drill-origin absolute \
  --excellon-units mm --generate-map --map-format gerberx2 \
  --output "$out/gerbers/" "$pcb"

echo "==> Pick-and-place (SMD only, DNP excluded)"
kicad-cli pcb export pos --format csv --units mm --side both \
  --exclude-dnp --smd-only --use-drill-file-origin \
  --output "$out/${name}-pos.csv" "$pcb"

echo "==> BOM"
kicad-cli sch export bom --group-by Value \
  --fields 'Reference,Value,Footprint,${QUANTITY},${DNP},MPN' \
  --labels 'Refs,Value,Footprint,Qty,DNP,MPN' \
  --output "$out/${name}-bom.csv" "$sch"

echo "==> Zipping gerbers + drill"
( cd "$out/gerbers" && python3 -m zipfile -c "../${name}-gerbers.zip" ./* )

echo
echo "Done. Outputs in $out/"
ls -1 "$out"
