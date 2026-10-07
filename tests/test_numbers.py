import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "app"))
from decimal import Decimal as D
from purrsum.numparse import find_numbers, clipboard_text, pretty

CASES = [
    # typewriter-style fonts put a gap after the thousands comma (real A/R aging report)
    ("8, 764.46", ["8764.46"]),
    ("11, 724.76", ["11724.76"]),
    ("16 ,682.31", ["16682.31"]),
    ("1, 234, 567.89", ["1234567.89"]),
    ("06.15.26 8, 764.46     8,764.46", ["8764.46", "8764.46"]),
    ("$8, 764.46", ["8764.46"]),
    ("3, 120 boxes", ["3", "120"]),          # a real list, no cents: stays two numbers
    ("1641. 60", ["1641.60"]),
    ("Amount 1641. 60", ["1641.60"]),
    ("(75.25)", ["-75.25"]),
    ("300.00-", ["-300.00"]),
    ("-12.50", ["-12.50"]),
    ("($1,200.00)", ["-1200.00"]),
    ("$1,234.56", ["1234.56"]),
    ("₩1,250,000", ["1250000"]),
    ("€ 99.90  £5  ¥3,000", ["99.90", "5", "3000"]),
    ("10/06/2026  1,000.00", ["1000.00"]),
    ("2026-10-06 250.00", ["250.00"]),
    ("Oct 6, 2026  45.00", ["45.00"]),
    ("billed Oct 6,2026 at 10:42AM. $88.10", ["88.10"]),
    ("Due 06 Oct 2026  45.00", ["45.00"]),
    ("10:42 AM  12.00", ["12.00"]),
    ("INV-24081  500.00", ["500.00"]),
    ("PO#55  77.00", ["77.00"]),
    ("PO 55  77.00", ["77.00"]),
    ("12*1800  173.5*265  88.10", ["88.10"]),
    ("10 x 20  5.00", ["5.00"]),
    ("Freight - 150.00", ["150.00"]),
    ("Tax 8.25%  41.25", ["41.25"]),
    ("Tel (310) 555-1234  20.00", ["20.00"]),
    ("1,641.60 75.25 300.00", ["1641.60", "75.25", "300.00"]),
    ("1641.60USD", ["1641.60"]),
    ("Total: 3,210.00", ["3210.00"]),
    ("＄１，２００．５０", ["1200.50"]),
    ("Qty 3  Unit 12.00  Ext 36.00", ["3", "12.00", "36.00"]),
]

bad = 0
for text, want in CASES:
    got = [f"{f.value:f}" for f in find_numbers(text)]
    ok = got == want
    bad += not ok
    print(("PASS" if ok else "FAIL"), repr(text), "->", got, "" if ok else f"(want {want})")

f = find_numbers("1641. 60\n(75.25)\n300.00-\n1,000")
assert clipboard_text(f) == "2266.35", clipboard_text(f)
assert pretty(f) == "2,266.35"
f[0].included = False
assert clipboard_text(f) == "624.75"
print("totals OK")
sys.exit(1 if bad else 0)
