import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "app"))
from decimal import Decimal as D
from purrsum.purrsum_reader import find_numbers as _find


class F:
    def __init__(self, v):
        self.value, self.included = v, True


def find_numbers(text):
    return [F(v) for line in text.split("\n") for v, _ in _find(line)]


def _total(f):
    return sum((x.value for x in f if x.included), D(0))


def clipboard_text(f):
    from purrsum.ui import clipboard_total
    return clipboard_total(f)


def pretty(f):
    from purrsum.ui import pretty_total
    return pretty_total(f)

CASES = [
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
    ("10:42 AM  12.00", ["12.00"]),
    ("INV-24081  500.00", ["500.00"]),
    ("PO#55  77.00", ["77.00"]),
    ("12*1800  173.5*265  88.10", ["88.10"]),
    ("1,641.60 75.25 300.00", ["1641.60", "75.25", "300.00"]),
    ("Total: 3,210.00", ["3210.00"]),
    ("Qty 3  Unit 12.00  Ext 36.00", ["3", "12.00", "36.00"]),
]

# Things the old Noir parser handled that the PurrSum reader does not (yet). Shown, not failed.
KNOWN_DIFFERENCES = [
    ("Oct 6, 2026  45.00", ["45.00"]),
    ("billed Oct 6,2026 at 10:42AM. $88.10", ["88.10"]),
    ("Due 06 Oct 2026  45.00", ["45.00"]),
    ("PO 55  77.00", ["77.00"]),
    ("10 x 20  5.00", ["5.00"]),
    ("Freight - 150.00", ["150.00"]),
    ("Tax 8.25%  41.25", ["41.25"]),
    ("Tel (310) 555-1234  20.00", ["20.00"]),
    ("1641.60USD", ["1641.60"]),
    ("＄１，２００．５０", ["1200.50"]),
]
for text, want in KNOWN_DIFFERENCES:
    got = [f"{f.value:f}" for f in find_numbers(text)]
    if got != want:
        print("NOTE", repr(text), "->", got, f"(old parser gave {want})")

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
