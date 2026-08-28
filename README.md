# hydroponics-pcb

KiCad PCB designs for the hydroponics monitoring/control system on a two-tier
IKEA growing rack.

## Boards

| Board | Status | MCU | Purpose |
|-------|--------|-----|---------|
| `tray-board` | schematic + layout drawn, ERC/DRC clean | socketed ESP32 30-pin DevKit | Per-tray sensor + display node. One per tray (top / bottom). |
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
| Display | 2.4" ST7789 240×320, no touch | SPI | LVGL, encoder-driven UI |

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
docs/              pin maps, block diagrams, datasheets
```

## Working with KiCad from the CLI

Requires KiCad 10.x (`kicad-cli`) plus the standard symbol/footprint libraries.

```
tools/fab.sh tray-board
```

runs ERC + DRC (fails on any error/warning) and writes trimmed gerbers, Excellon
drill + map, SMD-only pick-and-place, BOM, and a gerber zip to
`tray-board/production/` (git-ignored — regenerated from source).
