# Docs / tooling TODO

## Automated project documentation (web format)

**Goal:** generate a browsable project site from the repo, and make updating it part
of the deployment process rather than a separate chore.

Content it should pull together:

- Project overview / block diagram (tray boards + reservoir board + HA, WiFi + RS-485).
- Per-board pages: schematic render, PCB render (front/back), board specs
  (layers, size, thickness), revision.
- Links to artifacts: this repo, per-board 3D/STEP files, gerber zips, BOM, P&P.
- Deployment / assembly manual — for Tom and for anyone else building one:
  BOM sourcing, assembly order, flashing the ESPHome firmware, wiring the RS-485
  bus and sensor harnesses, first-power checks, calibration (EC/pH, ToF zero).

Ideas on how:

- `kicad-cli pcb render` + `pcb export svg/pdf` + `sch export svg` for the images.
- `kicad-cli pcb export step` for the 3D (needs `kicad-packages3d` installed).
- Static site — plain HTML, or MkDocs / Eleventy — published to GitHub Pages.
- A `tools/docs.sh` that regenerates images + site from source; call it from the
  release/deploy flow so docs can't drift from the hardware.
- Version the deployment manual alongside the board revision it describes.

Not started — captured 2026-08-28.

## Tray-board display connector footprint (for the redesign)

`docs/datasheets/MSP2401_2.4in_TFT_touch_SD_mechanical.pdf` — mechanical
drawing for the LCD Wiki MSP2401/MSP2402 2.4" ILI9341+XPT2046 module.
Confirmed against the physical board (2026-08-31) — this is the correct
footprint, not just a probable match.

Trustworthy, dimensioned numbers from this drawing:
- PCB outline: 42.72 x 77.18mm
- Main 14-pin header: 2.54mm pitch, 33.02mm span (13 gaps), 4.85mm from
  the PCB edge
- 4 mounting holes: 3.20mm drill / 4.70mm pad, at 36.72mm x 67.26mm
  hole-to-hole spacing

**Not trustworthy from this drawing:** the SD card header position. The
drawing shows the SD socket and its 4 signal breakouts (SD_SCK,
SD_MISO, SD_MOSI, SD_CS) as bare labeled pads near the top-right
mounting hole, not a dimensioned connector — but the physical board
has an actual pin header there. Before laying out J3 in the redesign,
measure that header's position directly off the physical board, using
the top-right mounting hole as the reference point (cross-check the
board's actual hole spacing against the 36.72mm/67.26mm figures above
first, to confirm it's the same revision as this drawing).
