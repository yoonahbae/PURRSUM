"""Real screenshots that once read wrong. Run: python3 tests/test_ocr_fixtures.py"""
import pathlib, sys
from decimal import Decimal
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import numpy as np
from PIL import Image
from purrsum import ocr, numparse

CASES = [
    # A/R aging column in a typewriter font: OCR sees "8, 764.46" (gap after the comma).
    # Must stay ONE number per row; the report's own 15-30 total is 331,987.93.
    ("comma_gap_column.png", 30, Decimal("331987.93")),
]
ok = True
for name, count, total in CASES:
    img = np.array(Image.open(ROOT / "tests" / "fixtures" / name).convert("RGB"))
    f = numparse.find_numbers("\n".join(ocr.read_lines(img)), box=1)
    good = len(f) == count and numparse.total_of(f) == total
    ok &= good
    print("PASS" if good else "FAIL", name, len(f), numparse.total_of(f))
sys.exit(0 if ok else 1)
