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

Dimensioned numbers from this drawing, all confirmed against physical
measurement:
- PCB outline: 42.72 x 77.18mm
- Main 14-pin header (J2): 2.54mm pitch, 33.02mm span (13 gaps), pin 1
  at X=4.85mm, Y=75.18mm (2.00mm up from the bottom edge) from the
  top-left PCB corner
- SD card header (J4): 4 pins, 2.54mm pitch, pin 1 at X=17.23mm,
  Y=6.51mm from the top-left PCB corner
- 4 mounting holes: 3.20mm drill / 4.70mm pad, at 36.72mm x 67.26mm
  hole-to-hole spacing, inset 3.00mm from each edge

All of the above is already built as a footprint:
`shared-library/Library.pretty/Display_MSP2401_2.4in_Touch.kicad_mod`
(outline, mounting holes, J2 pins 1-14, J4 pins SD1-SD4) — use it
directly for correct connector spacing in the redesign rather than
re-deriving these numbers.
