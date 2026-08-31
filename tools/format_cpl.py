#!/usr/bin/env python3
"""
Convert kicad-cli's raw `pcb export pos --format csv` output into the exact
CPL format JLCPCB's assembly uploader expects (confirmed against JLCPCB's
own sample file, JLCSMT_Sample_CPL1.xlsx):

    Designator, Mid X, Mid Y, Layer, Rotation

- Coordinates carry an inline "mm" suffix (e.g. "95.0518mm").
- Layer is capitalized ("Top"/"Bottom"), not lowercase.
- Rotation is normalized to [0, 360), never negative.

kicad-cli's `pos` export has no header-customization flag (unlike
`sch export bom`), so this does it as a post-processing step.

Usage:
    tools/format_cpl.py <input.csv> <output.csv>
"""

import csv
import sys


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)

    in_path, out_path = sys.argv[1], sys.argv[2]

    with open(in_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in rows:
            designator = row["Ref"]
            mid_x = f"{float(row['PosX']):.4f}mm"
            mid_y = f"{float(row['PosY']):.4f}mm"
            layer = row["Side"].strip().capitalize()
            rot = float(row["Rot"]) % 360
            rotation = str(int(rot)) if rot == int(rot) else f"{rot:.4f}"
            writer.writerow([designator, mid_x, mid_y, layer, rotation])

    print(f"format_cpl: wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
