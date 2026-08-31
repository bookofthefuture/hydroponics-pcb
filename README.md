# hydroponics-pcb

KiCad PCB designs for the hydroponics monitoring/control system on a two-tier
IKEA growing rack.

## Boards

| Board | Status | MCU | Purpose |
|-------|--------|-----|---------|
| `tray-board` | schematic updated for touch+SD display (ERC clean), PCB layout needs re-sync (`Update PCB from Schematic`) + routing for the new footprint | socketed ESP32 30-pin DevKit | Per-tray sensor + display node. One per tray (top / bottom). |
| `reservoir-board` | not started | ESP32 (TBD) | Reservoir-side control: fill pumps, A/B + pH dosing pumps, level/EC/pH/temp sensing. |

Grow-lamp switching currently stays on the original ESP8266 `hydroponics_monitor`
node and is out of scope for these boards (may move to the reservoir board later).

## Tray board peripherals

| Function | Part | Bus | Notes |
|----------|------|-----|-------|
| ToF distance (water level) | VL53L0X / VL53L1X | I²C 3.3 V | Shared SDA/SCL |
| Air pressure (+ humidity/temp on BME) | BMP280 / BME280 | I²C 3.3 V | Shared SDA/SCL |
| Lux level | BH1750 | I²C 3.3 V | Shared SDA/SCL |
| Water temperature | DS18B20 | 1-Wire 3.3 V | Dedicated GPIO, 4.7 kΩ pull-up |
| User input | Rotary encoder + push switch | GPIO / quadrature | 3.3 V |
| Display | 2.4" ILI9341 240×320, resistive touch (XPT2046) + SD card | SPI (shared bus, separate CS lines) | LVGL, encoder-driven UI; SD card wired but not yet used by firmware |

Display connector (J2, 14-pin) pinout: VCC, GND, CS(D5), RESET(D4), DC(D2),
MOSI(D23), SCK(D18), LED(D15), MISO(D34), T_CLK(D18, shared), T_CS(D14),
T_DIN(D23, shared), T_DO(D34, shared), T_IRQ(D35). SD card connector (J3,
4-pin, separate from J2): CS(D19), MOSI(D23, shared), MISO(D34, shared),
SCK(D18, shared). New GPIOs used: 14, 19, 34, 35 — none of these were
previously assigned, so add them to the ESPHome configs without touching the
existing pin numbers.

No high-power switching on the tray board. An SP3485EN RS-485 transceiver
(120 Ω termination, direction pin on GPIO12) links the two tray boards to the
reservoir board.

## Comms

All three ESPs talk to Home Assistant over WiFi (ESPHome native API). The tray
boards *also* talk to the reservoir board over RS-485 — a local wired link so
fill-level reads and pump control don't depend on WiFi/HA. The reservoir is the
controlling node.

## Firmware

ESPHome configs live in the separate `ha-config` repo under `esphome/`
(`hydro-tray-top.yaml`, `hydro-tray-bottom.yaml`). The pin map is shared between
the schematic here and those configs — keep them in sync.

## Repo layout

```
tray-board/        KiCad project for the tray sensor board
reservoir-board/   (future) KiCad project for the reservoir board
shared-library/    custom symbol (New_Library) + footprint (Library.pretty)
                   library, referenced by both boards' sym-lib-table/
                   fp-lib-table via ${KIPRJMOD}/../../shared-library/ - keep
                   custom parts (ESP32 DevKit socket, display modules, etc.)
                   here rather than per-board copies, which drift silently
docs/              pin maps, block diagrams, datasheets
```

## Working with KiCad from the CLI

Requires KiCad 10.x (`kicad-cli`) plus the standard symbol/footprint libraries.

```
tools/fab.sh tray-board
```

runs ERC + DRC (fails on any error/warning) and writes a JLCPCB-ready set to
`tray-board/production/` (git-ignored — regenerated from source): gerbers
(Protel extensions) + separate PTH/NPTH Excellon drill files, zipped as
`<name>-gerbers.zip`; `<name>-cpl.csv` (SMD-only pick-and-place, DNP parts
excluded); `<name>-bom.csv` (DNP excluded, `LCSC Part #` column from each
part's `LCSC` schematic field). Parts you're sourcing/fitting yourself (e.g.
the socketed ESP32 module) should be marked Do Not Populate in the schematic
so they're left out of both the BOM and the CPL automatically.

It also runs `tools/check_pins.py`, which checks the MCU's pin usage for
hardware hazards ERC doesn't catch — currently ESP32 strapping pins (GPIO0,
2, 5, 12, 15) with an external pull that conflicts with their required
boot-time level, GPIO6-11 (internal flash, must never be used externally),
and UART0 (GPIO1/3, reserved for USB-serial). Fails the build on any
ERROR-severity finding; can also be run standalone:

```
tools/check_pins.py path/to/board.kicad_sch
```
