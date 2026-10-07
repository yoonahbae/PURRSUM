"""Original pixel-art kitties, drawn as character grids so they stay crisp at any size.

Legend: . empty  K outline  B fur  P ear/paw pink  E eye  S stripe  L light fur  W whisker
"""
from __future__ import annotations

CAT = [
    "..KK.........KK........",
    "..KPK.......KPK........",
    "..KPPKKKKKKKPPK........",
    "..KBBBBBBBBBBBK........",
    "..KBBBBBBBBBBBK........",
    "..KBBEEBBBEEBBK........",
    "WWKBBEEBBBEEBBKWW......",
    "..KBBBBBKBBBBBK........",
    "WWKBBBBKBKBBBBKWW......",
    "..KBBBBBBBBBBBK........",
    "...KBBBBBBBBBK.........",
    "...KBBBBBBBBBK.....KKK.",
    "...KBBBBBBBBBK....KBBBK",
    "...KBBBBBBBBBK...KBBBK.",
    "...KBBBBBBBBBK..KBBK...",
    "...KBBKBBBKBBKKKBBK....",
    "...KBBKBBBKBBBBBBK.....",
    "...KKKKKKKKKKKKKK......",
]
W = len(CAT[0])
H = len(CAT)

# extra markings per kitty (row, col) -> code, only painted over fur
TABBY = [(3, 6), (3, 8), (3, 10), (4, 8), (4, 3), (5, 3), (4, 13), (5, 13),
         (11, 4), (12, 4), (11, 12), (12, 12), (13, 4), (13, 12),
         (12, 20), (13, 19), (15, 16)]
BELLY = [(r, c) for r in range(11, 17) for c in range(7, 10)]

KITTIES = {
    "noir":  dict(label="Black", default="Noir",
                  K="#0b0b0e", B="#2f2f36", P="#f39bb0", E="#ffb21e", W="#0b0b0e"),
    "snow":  dict(label="White", default="Snowball",
                  K="#16161a", B="#fbfbfb", P="#f7a8bb", E="#3fb3f2", W="#16161a"),
    "pebble": dict(label="Gray tabby", default="Pebble",
                   K="#16161a", B="#aaa59f", P="#f2a7b6", E="#ffffff", W="#16161a",
                   S="#6c6762", L="#e7c3bd", stripes=True, belly=True),
    "mango": dict(label="Orange tabby", default="Mango",
                  K="#16161a", B="#e3803d", P="#f7cfb2", E="#ffffff", W="#16161a",
                  S="#b85a1f", L="#f6dcc2", stripes=True, belly=True),
}
ORDER = ["noir", "snow", "pebble", "mango"]


def grid(kitty: str, blink: bool = False) -> list[list[str | None]]:
    """Return a H x W grid of hex colours (or None) for one frame."""
    pal = KITTIES[kitty]
    rows = [list(r) for r in CAT]
    if pal.get("belly"):
        for r, c in BELLY:
            if rows[r][c] == "B":
                rows[r][c] = "L"
    if pal.get("stripes"):
        for r, c in TABBY:
            if rows[r][c] == "B":
                rows[r][c] = "S"
    for r in range(H):
        for c in range(W):
            if rows[r][c] == "E":
                if blink:
                    rows[r][c] = "K" if r == 6 else "B"
                elif pal["E"] == "#ffffff" and c in (6, 11):
                    rows[r][c] = "K"          # pupils for the light-eyed tabbies
    return [[None if ch == "." else pal[ch] for ch in row] for row in rows]


PAW = [
    "...PP..PP...",
    "...PP..PP...",
    "PP........PP",
    "PP..PPPP..PP",
    "...PPPPPP...",
    "..PPPPPPPP..",
    "..PPPPPPPP..",
    "...PPPPPP...",
]


def paw_grid(kitty: str) -> list[list[str | None]]:
    pal = KITTIES[kitty]
    return [[None if ch == "." else pal[ch] for ch in row] for row in PAW]
