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
