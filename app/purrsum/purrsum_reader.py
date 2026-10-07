"""
purrsum_reader.py — the number-reading engine from the original PurrSum (tested on real invoices).

Drop-in module. Use it like this:

    from purrsum_reader import Reader, find_numbers, decimals_in, fmt

    reader = Reader()                        # loads the OCR engine in the background
    lines = reader.read(pil_image)           # one string per visual row, left→right
    nums = [n for line in lines for n in find_numbers(line)]   # [(Decimal, original_text), ...]
    total = sum(v for v, _ in nums)

Needs: pip install rapidocr_onnxruntime pillow numpy   (Python 3.12 or lower)
"""

import re
import threading
from decimal import Decimal, InvalidOperation

# Things that look like numbers but aren't amounts: dates and times.
_DATE_RE = re.compile(r"\b\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

# An amount: optional ( or -, optional currency sign, digits with optional
# thousands commas and decimals, optional ) or trailing - (accounting style).
_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9.,#/_*×-])"        # not part of a code like INV-1234, #5 or 12*1800
    r"(?P<open>\()?\s*"
    r"(?P<lead>[-−–])?\s*"
    r"(?:[$€£₩¥]|USD|KRW)?\s*"
    r"(?P<lead2>[-−–])?"
    r"(?P<num>\d{1,3}(?:[,.]\d{3})+(?:[.,]\d{1,4})?|\d+(?:[.,]\d{1,4})?)"
    r"(?P<close>\))?"
    r"(?P<trail>-(?!\d))?"
    r"(?![A-Za-z0-9*×]|[.,]\d)"
)


def _to_decimal(raw: str):
    """Turn '1,234.56' / '1.234.56' (OCR slip) / '1234' into a Decimal."""
    s = raw
    seps = [c for c in s if c in ",."]
    if seps:
        last = s.rfind(seps[-1])
        tail = s[last + 1:]
        if len(tail) == 3 and len(seps) >= 1 and (seps[-1] == "," or len(seps) > 1 and seps.count(".") > 1):
            s = s.replace(",", "").replace(".", "")          # 1,234 or 1.234.567 → thousands only
        elif len(tail) == 3 and seps == ["."]:
            pass                                              # 1.234 is ambiguous; treat as decimal
        else:
            head = s[:last].replace(",", "").replace(".", "")
            s = head + "." + tail
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def find_numbers(text: str):
    """Return a list of (Decimal value, original text) found in a string."""
    # Some PDF fonts leave a gap after the decimal point ("1641. 60"); glue the cents back on.
    text = re.sub(r"(\d)\s*([.,])\s+(\d{1,2})(?![\d.,])", r"\1\2\3", text)
    cleaned = _DATE_RE.sub(" ", text)
    cleaned = _TIME_RE.sub(" ", cleaned)
    out = []
    for m in _NUM_RE.finditer(cleaned):
        val = _to_decimal(m.group("num"))
        if val is None:
            continue
        negative = bool(m.group("lead") or m.group("lead2") or m.group("trail")
                        or (m.group("open") and m.group("close")))
        if negative:
            val = -val
        out.append((val, m.group(0).strip()))
    return out


def decimals_in(d: Decimal) -> int:
    exp = d.as_tuple().exponent
    return -exp if isinstance(exp, int) and exp < 0 else 0


def fmt(d: Decimal, places: int) -> str:
    q = Decimal(1).scaleb(-places) if places else Decimal(1)
    return f"{d.quantize(q):,}"


class Reader:
    def __init__(self):
        self.engine = None
        self.error = None
        self.ready = threading.Event()
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
        except Exception as e:
            self.error = str(e)
        self.ready.set()

    def read(self, pil_image):
        """Return OCR lines sorted top-to-bottom, left-to-right."""
        import numpy as np
        from PIL import ImageOps
        self.ready.wait()
        if self.engine is None:
            raise RuntimeError(self.error or "OCR engine failed to load")
        img = pil_image.convert("RGB")
        # Text touching the edge of the box reads badly; add a margin in the page colour.
        img = ImageOps.expand(img, border=14, fill=img.getpixel((0, 0)))
        # Small crops read much better when enlarged.
        if img.height < 400:
            f = min(max(2, int(400 / max(img.height, 1))), 4)
            img = img.resize((img.width * f, img.height * f))
        result, _ = self.engine(np.array(img))
        if not result:
            return []
        items = []
        for box, text, score in result:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            items.append((sum(ys) / 4, min(xs), max(ys) - min(ys), text))
        # group into rows by vertical position, then left→right
        items.sort()
        rows, cur, cur_y = [], [], None
        for y, x, h, t in items:
            if cur_y is None or abs(y - cur_y) <= max(h * 0.6, 6):
                cur.append((x, t))
                cur_y = y if cur_y is None else (cur_y + y) / 2
            else:
                rows.append(cur)
                cur, cur_y = [(x, t)], y
        if cur:
            rows.append(cur)
        lines = []
        for r in rows:
            r.sort()
            lines.append("   ".join(t for _, t in r))
        return lines


if __name__ == "__main__":
    # Self-test: these cases come from real invoices that tripped up simpler readers.
    T = lambda s: [v for v, _ in find_numbers(s)]
    assert T("1641. 60") == [Decimal("1641.60")]
    assert T("TY5612   12*1800   408   1. 95   795. 60") == [Decimal("408"), Decimal("1.95"), Decimal("795.60")]
    assert T("$1,234.56") == [Decimal("1234.56")]
    assert T("(250.00)") == [Decimal("-250.00")] and T("300.00-") == [Decimal("-300.00")]
    assert T("₩15,000") == [Decimal("15000")] and T("1.234.56") == [Decimal("1234.56")]
    assert T("Date 09/30/2026 at 15:32") == [] and T("INV-24081 PO#55") == []
    assert T("173.5*265/10*1200") == []
    print("reader ok")
