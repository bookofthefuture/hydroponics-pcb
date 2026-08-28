# hydroponics-pcb

KiCad PCB designs for the hydroponics monitoring/control system on a two-tier
IKEA growing rack.

## Boards

| Board | Status | MCU | Purpose |
|-------|--------|-----|---------|
| `tray-board` | in design (KiCad, added here) | ESP32-WROOM-32E | Per-tray sensor + display node. One per tray (top / bottom). |
| `reservoir-board` | not started | ESP32-WROOM-32E | Reservoir-side control: fill pumps, A/B + pH dosing pumps, level/EC/pH/temp sensing. |

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

No high-power switching on the tray board.

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

`kicad-cli` is used for DRC/ERC checks and generating fabrication outputs.
Generated gerbers / production files are git-ignored and regenerated from source.
