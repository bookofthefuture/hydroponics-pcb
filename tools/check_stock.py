#!/usr/bin/env python3
"""
Check LCSC stock (and existence) for every LCSC Part # in a BOM CSV before
it goes anywhere near a JLCPCB upload.

LCSC's product page embeds live stock data as server-rendered JSON, so a
plain GET with a browser User-Agent is enough - no API key, no headless
browser. For each LCSC code we check that the page's own productCode
actually matches what we asked for (an invalid/delisted code silently
redirects to an unrelated part instead of 404ing - this is exactly what
happened with a bogus code that looked plausible but wasn't real) and
that stockNumber is above a minimum threshold.

Usage:
    tools/check_stock.py <bom.csv> [--min-stock N]

Exits non-zero if any part is invalid or out of stock, so it can gate
fab.sh the same way ERC/DRC/check_pins.py do.
"""

import argparse
import csv
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def fetch_stock(code: str):
    """Return (ok, stock_number, actual_product_code, error_message)."""
    url = f"https://www.lcsc.com/product-detail/{code}.html"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        return False, None, None, f"fetch failed: {e}"

    code_m = re.search(r'"productCode":"([^"]+)"', text)
    actual_code = code_m.group(1) if code_m else None
    stock_m = re.search(r'"stockNumber":(\d+)', text)
    stock = int(stock_m.group(1)) if stock_m else None

    if actual_code is None or stock is None:
        return False, None, actual_code, "couldn't find product data on page (code may not exist)"
    if actual_code != code:
        return False, stock, actual_code, f"redirected to a different part ({actual_code}) - code is invalid/delisted"
    return True, stock, actual_code, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bom_csv")
    ap.add_argument("--min-stock", type=int, default=1,
                     help="warn if stock is below this (default: 1, i.e. only flag zero)")
    args = ap.parse_args()

    with open(args.bom_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lcsc_col = None
    for candidate in ("LCSC Part #", "LCSC"):
        if rows and candidate in rows[0]:
            lcsc_col = candidate
            break
    if lcsc_col is None:
        print("check_stock: no LCSC column found in BOM - nothing to check", file=sys.stderr)
        sys.exit(0)

    problems = []
    checked = 0
    for row in rows:
        code = row.get(lcsc_col, "").strip()
        designator = row.get("Designator", "?")
        if not code:
            problems.append((designator, code, "no LCSC code set"))
            continue
        checked += 1
        ok, stock, actual_code, err = fetch_stock(code)
        if not ok:
            problems.append((designator, code, err))
        elif stock < args.min_stock:
            problems.append((designator, code, f"stock is {stock} (below minimum {args.min_stock})"))
        else:
            print(f"[OK] {designator} ({code}): {stock} in stock")

    print(f"\ncheck_stock: checked {checked} parts, {len(problems)} problem(s)")
    if problems:
        for designator, code, msg in problems:
            print(f"[PROBLEM] {designator} ({code or 'no code'}): {msg}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
