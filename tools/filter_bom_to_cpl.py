#!/usr/bin/env python3
"""
Restrict a BOM CSV (kicad-cli sch export bom output, comma-joined
designators, no ranges) to only the designators that actually appear in
the CPL — i.e. only parts JLCPCB will actually place.

Why: the BOM is generated from the schematic (DNP-excluded) and the CPL
from the PCB (DNP-excluded AND smd-only). Anything through-hole that
you're hand-soldering yourself shows up in the BOM but never in the
CPL, which JLCPCB's uploader rejects as "designators don't exist in the
CPL file." Filtering the BOM down to the CPL's designator set keeps the
two in sync regardless of the mount-type mix.

If filtering empties a grouped row entirely, the row is dropped. If it
only partially empties one, Quantity is recalculated for what remains.
Whatever gets dropped from the JLC-bound BOM is written out to a second
CSV in the same shape - a shopping list for the parts you're sourcing
and hand-soldering yourself.

Usage:
    tools/filter_bom_to_cpl.py <bom.csv> <cpl.csv> <output_bom.csv> <hand_solder_csv>
"""

import csv
import sys


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(2)

    bom_path, cpl_path, out_path, hand_solder_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    with open(cpl_path, newline="", encoding="utf-8") as f:
        cpl_designators = {row["Designator"] for row in csv.DictReader(f)}

    with open(bom_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    kept = []
    hand_solder = []
    for row in rows:
        refs = [r.strip() for r in row["Designator"].split(",")]
        remaining = [r for r in refs if r in cpl_designators]
        removed = [r for r in refs if r not in cpl_designators]

        if remaining:
            kept_row = dict(row)
            kept_row["Designator"] = ",".join(remaining)
            if "Quantity" in kept_row:
                kept_row["Quantity"] = str(len(remaining))
            kept.append(kept_row)

        if removed:
            hs_row = dict(row)
            hs_row["Designator"] = ",".join(removed)
            if "Quantity" in hs_row:
                hs_row["Quantity"] = str(len(removed))
            hand_solder.append(hs_row)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(kept)

    with open(hand_solder_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(hand_solder)

    dropped_count = sum(len(r["Designator"].split(",")) for r in hand_solder)
    print(f"filter_bom_to_cpl: kept {len(kept)} rows ({sum(len(r['Designator'].split(',')) for r in kept)} parts) for JLC, "
          f"{len(hand_solder)} rows ({dropped_count} parts) to hand-solder -> {hand_solder_path}")


if __name__ == "__main__":
    main()
