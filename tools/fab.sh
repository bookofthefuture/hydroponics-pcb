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
out="$(dirname "$pcb")/production"

[ -f "$pcb" ] || { echo "no .kicad_pcb found under $board_dir" >&2; exit 1; }

rm -rf "$out"
mkdir -p "$out/gerbers"

echo "==> ERC"
kicad-cli sch erc --exit-code-violations --severity-error \
  "$sch" -o "$out/${name}-erc.rpt"

echo "==> Pin usage / strapping-pin check"
python3 "$repo_root/tools/check_pins.py" "$sch"

echo "==> DRC"
kicad-cli pcb drc --exit-code-violations --severity-error --severity-warning \
  "$pcb" -o "$out/${name}-drc.rpt"

echo "==> Gerbers (fab layers only, Protel extensions for JLCPCB)"
kicad-cli pcb export gerbers --subtract-soldermask \
  --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts \
  --output "$out/gerbers/" "$pcb"

echo "==> Drill (Excellon, separate PTH/NPTH, drill-origin)"
kicad-cli pcb export drill --format excellon --drill-origin absolute \
  --excellon-units mm --excellon-separate-th --generate-map --map-format gerberx2 \
  --output "$out/gerbers/" "$pcb"

echo "==> Pick-and-place / CPL (SMD only, DNP excluded)"
kicad-cli pcb export pos --format csv --units mm --side both \
  --exclude-dnp --smd-only --use-drill-file-origin \
  --output "$out/${name}-cpl-raw.csv" "$pcb"
python3 "$repo_root/tools/format_cpl.py" "$out/${name}-cpl-raw.csv" "$out/${name}-cpl.csv"
rm -f "$out/${name}-cpl-raw.csv"

echo "==> BOM (DNP excluded, grouped so differing LCSC codes don't get merged away)"
kicad-cli sch export bom --group-by 'Value,Footprint,LCSC' --exclude-dnp \
  --fields 'Reference,Footprint,${QUANTITY},Value,LCSC' \
  --labels 'Designator,Footprint,Quantity,Value,LCSC Part #' \
  --output "$out/${name}-bom.csv" "$sch"

echo "==> Zipping gerbers + drill (JLCPCB layers only — job file/drill map left out)"
( cd "$out/gerbers" && python3 -c "
import zipfile, glob
files = [f for f in glob.glob('*') if not (f.endswith('.gbrjob') or '_map' in f or f.endswith('-drl_report.txt'))]
with zipfile.ZipFile('../${name}-gerbers.zip', 'w') as z:
    for f in sorted(files):
        z.write(f)
" )

echo
echo "Done. Outputs in $out/"
ls -1 "$out"
