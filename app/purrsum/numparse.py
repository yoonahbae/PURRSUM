"""Turn OCR text into the numbers worth adding up.

Rules (from real invoices):
  * "1641. 60"  -> 1641.60   (PDF fonts often put a gap after the decimal point)
  * "8, 764.46" -> 8764.46   (typewriter-style fonts put a gap after the thousands comma;
                              only joined when the number ends in a decimal part)
  * (75.25), 300.00-, -12  -> negatives
  * dates, times, item codes (INV-24081, PO#55), sizes (12*1800, 173.5*265),
    phone numbers and percentages are ignored
  * $, ₩, €, £, ¥ and thousands commas are understood
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

CUR = "$₩€£¥"
MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"

# Things that look numeric but must never be summed. Order matters.
IGNORE = [
    # 2026-10-06, 10/06/2026, 06.10.26, 10/06
    re.compile(r"(?<![\d.])\d{1,4}[/\-.]\d{1,2}[/\-.]\d{2,4}(?![\d.])"),
    re.compile(r"(?<![\d.,])\d{1,2}/\d{1,2}(?![\d/.,])"),
    # Oct 6, 2026 / 6 Oct 2026 / October 2026
    re.compile(rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s*\d{{4}})?\b", re.I),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:,?\s+\d{{4}})?\b", re.I),
    re.compile(rf"\b{MONTHS}\s+\d{{4}}\b", re.I),
    # 10:42, 10:42:05 PM
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?", re.I),
    # (310) 555-1234, 310-555-1234
    re.compile(r"\(?\b\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"),
    # sizes: 12*1800, 173.5*265, 10 x 20 x 30
    re.compile(r"\d+(?:\.\d+)?(?:\s*[*×xX]\s*\d+(?:\.\d+)?)+"),
    # percentages (tax rates etc.)
    re.compile(r"\d+(?:\.\d+)?\s*%"),
    # codes: INV-24081, PO#55, A12, 24081A, SKU_9, #123, No.5
    re.compile(r"\b(?:PO|P\.O\.|INV|Invoice|No|Ref|SKU|Item|Lot|Order)\.?\s?(?:No\.?\s?)?#\s?\d[\w\-/]*", re.I),
    re.compile(r"\b(?:PO|INV|No|Ref|SKU|Lot)\.?\s\d[\w\-/]*", re.I),
    re.compile(r"[A-Za-z]+[#\-_/]?\d[\w\-/#]*"),
    re.compile(r"\d+[A-Za-z_][\w\-/#]*"),
    re.compile(r"#\s?\d[\w\-]*"),
]

NUM = re.compile(
    r"(?P<open>\()?\s*"
    r"(?P<lead>(?<![\w.])-(?=[\d$₩€£¥]))?"
    rf"(?P<cur>[{CUR}])?\s*"
    r"(?P<lead2>-(?=\d))?"
    r"(?P<int>\d{1,3}(?:\s?,\s?\d{3})+(?=\s?\.\s?\d)"   # "8, 764.46" is one number
    r"|\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\s?\.\s?(?P<frac>\d+))?"          # "1641. 60" is one number
    r"(?P<close>\s*\))?"
    r"(?P<trail>-(?!\d))?"
)


@dataclass
class Found:
    value: Decimal
    text: str            # what it looked like, cleaned up for display
    box: int = 1         # which selection box it came from
    included: bool = True


def _normalize(s: str) -> str:
    # full-width digits/punctuation (common in Asian PDFs) -> ASCII
    s = s.translate({c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)})
    s = s.replace("￦", "₩").replace("＄", "$").replace(" ", " ")
    s = s.replace("−", "-").replace("–", "-")
    s = re.sub(r"(\d)\s?(USD|KRW|EUR|GBP|JPY|CNY|CAD|AUD|원|円)\b", r"\1 ", s)
    # OCR sometimes reads the letter O inside a number
    s = re.sub(r"(?<=\d)[Oo](?=[\d.,])|(?<=[\d,.])[Oo](?=\d)", "0", s)
    return s


def find_numbers(text: str, box: int = 1) -> list[Found]:
    out: list[Found] = []
    for line in text.splitlines():
        line = _normalize(line)
        for pat in IGNORE:
            line = pat.sub(lambda m: " " * len(m.group(0)), line)
        for m in NUM.finditer(line):
            int_txt = re.sub(r"\s", "", m.group("int"))
            whole = int_txt.replace(",", "")
            frac = m.group("frac")
            val = Decimal(whole + ("." + frac if frac else ""))
            neg = bool(m.group("lead") or m.group("lead2") or m.group("trail")
                       or (m.group("open") and m.group("close")))
            if neg:
                val = -val
            cur = m.group("cur") or ""
            shown = f"{'-' if neg else ''}{cur}{int_txt}{'.' + frac if frac else ''}"
            out.append(Found(val, shown, box))
    return out


def total_of(found: list[Found]) -> Decimal:
    return sum((f.value for f in found if f.included), Decimal(0))


def places(found: list[Found]) -> int:
    return max((max(0, -f.value.as_tuple().exponent) for f in found), default=0)


def clipboard_text(found: list[Found]) -> str:
    """Total for pasting: no commas, keeps the decimals the inputs had."""
    t = total_of(found)
    p = places(found)
    q = Decimal(1).scaleb(-p)
    return f"{t.quantize(q):f}"


def pretty(found: list[Found]) -> str:
    """Total for showing: with thousands commas."""
    t = total_of(found)
    p = places(found)
    return f"{t:,.{p}f}"
