#!/usr/bin/env python3
"""
Check MCU pin usage in a KiCad schematic for hardware-boot / strapping-pin
hazards before it goes to production. Currently has a rule set for the
ESP32 (strapping pins, input-only pins, reserved-flash pins, UART0).

Usage:
    tools/check_pins.py <path-to.kicad_sch>

Exits non-zero if any ERROR-severity issue is found (matches the
ERC/DRC convention used by tools/fab.sh).
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

# --- ESP32 pin rules -------------------------------------------------------
# Keyed by the pin "name" as it appears in the schematic symbol (before the
# trailing "_<pinnumber>" KiCad appends to pinfunction in the netlist).
#
# bad_pull: "up" | "down" | None  - an external pull in this direction on the
#   net conflicts with the pin's required state during the ESP32 boot/reset
#   window (before firmware takes over).
STRAPPING_RULES = {
    "D0": {
        "severity": "error",
        "bad_pull": "down",
        "note": "GPIO0 (BOOT) must be HIGH at reset for normal boot; an "
                "external pull-down (or hard tie to GND) forces download "
                "mode and the board will not run firmware.",
    },
    "D2": {
        "severity": "error",
        "bad_pull": "up",
        "note": "GPIO2 must be LOW or floating at reset for normal SPI "
                "boot; an external pull-up can prevent the board from "
                "booting.",
    },
    "D5": {
        "severity": "warning",
        "bad_pull": "down",
        "note": "GPIO5 should be HIGH at reset (affects VSPI/boot timing "
                "default on some modules); an external pull-down may cause "
                "intermittent boot issues.",
    },
    "D12": {
        "severity": "error",
        "bad_pull": "up",
        "note": "GPIO12 (MTDI) selects flash voltage at reset. An external "
                "pull-up forces 1.8V flash detection and will break boot "
                "on the (standard) 3.3V-flash modules this project uses.",
    },
    "D15": {
        "severity": "info",
        "bad_pull": None,
        "note": "GPIO15 (MTDO) LOW silences the ROM boot log on UART0; "
                "HIGH (its internal pull-up default) is functionally fine, "
                "just noisier on the console.",
    },
}

INPUT_ONLY_PINS = {"D34", "D35", "VP", "VN"}
UART0_PINS = {"RX0", "TX0"}
RESERVED_FLASH_PINS = {"D6", "D7", "D8", "D9", "D10", "D11"}

POWER_NET_POSITIVE = re.compile(r"^\+?(3V3|5V|VCC|VDD)$", re.I)
POWER_NET_GROUND = re.compile(r"^(GND|AGND|DGND)$", re.I)


def run_netlist_export(sch_path: Path, out_path: Path) -> None:
    subprocess.run(
        [
            "kicad-cli", "sch", "export", "netlist",
            "--format", "kicadsexpr",
            "-o", str(out_path),
            str(sch_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def parse_netlist(text: str):
    """Return (components: {ref: part_name}, nets: [{name, nodes:[(ref,pin,pinfunction,pintype)]}])."""
    components = {}
    for comp_block in re.finditer(
        r'\(comp\s*\n\s*\(ref "([^"]+)"\).*?\(libsource\s*\n\s*\(lib "[^"]*"\)\s*\n\s*\(part "([^"]*)"\)',
        text, re.S,
    ):
        ref, part = comp_block.groups()
        components[ref] = part

    nets = []
    net_blocks = re.split(r"\n\t\t\(net\n", text)
    for block in net_blocks[1:]:
        block = "\t\t(net\n" + block
        name_m = re.search(r'\(name "([^"]*)"\)', block)
        name = name_m.group(1) if name_m else ""
        nodes = re.findall(
            r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)\s*(?:\(pinfunction "([^"]*)"\)\s*)?\(pintype "([^"]*)"\)',
            block,
        )
        nets.append({"name": name, "nodes": nodes})
    return components, nets


def pin_name_from_function(pinfunction: str, pin_number: str) -> str:
    if not pinfunction:
        return pin_number
    suffix = f"_{pin_number}"
    if pinfunction.endswith(suffix):
        return pinfunction[: -len(suffix)]
    return pinfunction


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)

    sch_path = Path(sys.argv[1]).resolve()
    if not sch_path.exists():
        print(f"error: {sch_path} not found", file=sys.stderr)
        sys.exit(2)

    with tempfile.TemporaryDirectory() as tmp:
        nl_path = Path(tmp) / "check_pins.net"
        try:
            run_netlist_export(sch_path, nl_path)
        except subprocess.CalledProcessError as e:
            print("error: kicad-cli netlist export failed", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            sys.exit(2)
        text = nl_path.read_text()

    components, nets = parse_netlist(text)

    mcu_refs = [ref for ref, part in components.items() if "esp32" in part.lower()]
    if not mcu_refs:
        print("check_pins: no ESP32 symbol found in this schematic — nothing to check.")
        sys.exit(0)

    # net lookup: (ref, pin) -> net dict, for tracing pull-resistor legs
    pin_to_net = {}
    for net in nets:
        for ref, pin, _pf, _pt in net["nodes"]:
            pin_to_net[(ref, pin)] = net

    findings = []  # (severity, message)

    checked_strapping = []  # (pname, ref, pin) with no hazard found

    for net in nets:
        mcu_nodes = [n for n in net["nodes"] if n[0] in mcu_refs]
        if not mcu_nodes:
            continue
        # KiCad gives every truly-unconnected pin its own placeholder net
        # named "unconnected-(...)" — nothing is actually wired there.
        is_unconnected = net["name"].startswith("unconnected-")

        for ref, pin, pinfunction, _pintype in mcu_nodes:
            pname = pin_name_from_function(pinfunction, pin)

            if is_unconnected:
                continue

            if pname in RESERVED_FLASH_PINS:
                findings.append((
                    "error",
                    f"{ref} pin {pin} ({pname}) is one of the ESP32's internal "
                    f"SPI-flash pins (GPIO6-11) and is wired to net "
                    f"'{net['name']}'. These must never be used externally on "
                    f"a module with integrated flash.",
                ))
                continue

            if pname in UART0_PINS:
                findings.append((
                    "warning",
                    f"{ref} pin {pin} ({pname}) is UART0 (USB-serial console "
                    f"/ flashing) and is wired to net '{net['name']}'. Using "
                    f"it for anything else will conflict with programming "
                    f"and the serial monitor.",
                ))

            if pname in INPUT_ONLY_PINS:
                findings.append((
                    "info",
                    f"{ref} pin {pin} ({pname}) is input-only (no internal "
                    f"pull, cannot be driven as an output) on net "
                    f"'{net['name']}'. Confirm nothing expects the ESP32 to "
                    f"drive this line (e.g. as a chip-select or reset).",
                ))

            rule = STRAPPING_RULES.get(pname)
            if not rule:
                continue

            # Direct hard-tie to a power net (net IS the power rail).
            if POWER_NET_POSITIVE.match(net["name"]) or POWER_NET_GROUND.match(net["name"]):
                pulled = "up" if POWER_NET_POSITIVE.match(net["name"]) else "down"
                if rule["bad_pull"] and pulled == rule["bad_pull"]:
                    findings.append((rule["severity"],
                        f"{ref} pin {pin} ({pname}) is hard-tied to "
                        f"{net['name']} — {rule['note']}"))
                else:
                    findings.append(("info",
                        f"{ref} pin {pin} ({pname}) is hard-tied to "
                        f"{net['name']} (likely intentional strapping) — "
                        f"verify this is deliberate."))
                continue

            # Look for a pull resistor: another node on this net that is a
            # 2-pin resistor whose OTHER leg lands on a power net.
            bad_pull_found = False
            for other_ref, other_pin, _opf, _opt in net["nodes"]:
                if other_ref == ref or not other_ref.startswith("R"):
                    continue
                other_leg = "2" if other_pin == "1" else "1"
                far_net = pin_to_net.get((other_ref, other_leg))
                if not far_net:
                    continue
                if POWER_NET_POSITIVE.match(far_net["name"]):
                    pulled = "up"
                elif POWER_NET_GROUND.match(far_net["name"]):
                    pulled = "down"
                else:
                    continue
                if rule["bad_pull"] and pulled == rule["bad_pull"]:
                    bad_pull_found = True
                    findings.append((rule["severity"],
                        f"{ref} pin {pin} ({pname}) has a pull-{pulled} "
                        f"({other_ref}, to {far_net['name']}) on net "
                        f"'{net['name']}' — {rule['note']}"))
            if not bad_pull_found:
                checked_strapping.append(f"{pname} ({ref} pin {pin})")

    if not findings:
        clean = ", ".join(checked_strapping) if checked_strapping else "none present"
        print(f"check_pins: {', '.join(mcu_refs)} — no strapping-pin hazards found.")
        print(f"  strapping pins checked clean: {clean}")
        sys.exit(0)

    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f[0], 3))

    had_error = False
    for severity, message in findings:
        had_error = had_error or severity == "error"
        print(f"[{severity.upper()}] {message}")

    if checked_strapping:
        print(f"\nstrapping pins checked clean: {', '.join(checked_strapping)}")

    print()
    if had_error:
        print("check_pins: FAILED — resolve ERROR-severity findings above.")
        sys.exit(1)
    print("check_pins: passed with warnings/info above — review before fab.")
    sys.exit(0)


if __name__ == "__main__":
    main()
