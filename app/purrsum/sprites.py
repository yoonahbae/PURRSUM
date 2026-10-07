"""Original pixel-art characters, drawn as character grids so they stay crisp at any size.

Legend: . empty  K outline  B fur  P ear/paw pink  E eye  H eye highlight  S stripe
        L light fur (belly/muzzle)  D darker fur (dog ears)  T tongue  W whisker
The two eye rows blink: the upper one turns to fur, the lower one to a closed-eye line.
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

# pups (original pixel art). Bodies are drawn without tails; a curled tail is added below.
DOOBOO = [            # golden, floppy ears, white blaze, navy collar
    "....KKKKKKKK...........",
    "...KBBBLLBBBK..........",
    ".KKDBBBLLBBBDKK........",
    "KDDDBBBLLBBBDDDK.......",
    "KDDDBHELLHEBDDDK.......",
    "KDDDBEELLEEBDDDK.......",
    ".KDDBPLLLLPBDDK........",
    "..KKBLLKKLLBKK.........",
    "....KBLTTLBK...........",
    "...KCCCCCCCCK..........",
    "..KBBBLLLLBBBK.........",
    "..KBBBLLLLBBBK.........",
    "..KBBBLLLLBBBK.........",
    "..KBBBBLLBBBBK.........",
    "..KBBBBBBBBBBK.........",
    "..KBBKBBBBKBBK.........",
    "..KBBKBBBBKBBK.........",
    "..KKKKKKKKKKKK.........",
]

SMOKEY = [            # Beans: grey & white, folded ears, tongue out
    "..KKK......KKK.........",
    ".KPPBKKKKKKBPPK........",
    ".KKBBBBLLBBBBKK........",
    "..KBBBBLLBBBBK.........",
    "..KBHEBLLBHEBK.........",
    "..KBEEBLLBEEBK.........",
    "..KBBLLLLLLBBK.........",
    "..KBLLLKKLLLBK.........",
    "...KLLLTTLLLK..........",
    "....KLLTTLLK...........",
    "...KLLLLLLLLK..........",
    "..KLLLLLLLLLLK.........",
    "..KLSLLLLLLSLK.........",
    "..KLSLLLLLLSLK.........",
    "..KLLLLLLLLLLK.........",
    "..KLLKLLLLKLLK.........",
    "..KLLKLLLLKLLK.........",
    "..KKKKKKKKKKKK.........",
]

# a tail that leaves the body low, sweeps out and up, and curls back at the tip
SIT_TAIL = [(15, 14), (14, 15), (13, 16), (12, 17), (11, 17), (10, 17), (9, 16)]


def with_tail(rows, path, fur="B"):
    g = [list(r) for r in rows]
    H, W = len(g), len(g[0])
    for r, c in path:
        g[r][c] = fur
    for r, c in path:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == ".":
                    g[rr][cc] = "K"
    return ["".join(r) for r in g]


DOOBOO = with_tail(DOOBOO, SIT_TAIL)
SMOKEY = with_tail(SMOKEY, SIT_TAIL, "L")

BUNNY = [
    "..KKKK....KKKK.........",
    "..KBPK....KPBK.........",
    "..KBPK....KPBK.........",
    "..KBPK....KPBK.........",
    "..KBPKKKKKKPBK.........",
    "..KBBBBBBBBBBK.........",
    "..KBHEBBBBHEBK.........",
    "..KBEEBBBBEEBK.........",
    "..KBPBBPPBBPBK.........",
    "...KBBBKKBBBK..........",
    "...KBBLLLLBBK..........",
    "..KBBLLLLLLBBK.........",
    "..KBBLLLLLLBBKKK.......",
    "..KBBLLLLLLBBKLLK......",
    "..KBBBLLLLBBBKLLK......",
    "..KBBKBBBBKBBKKK.......",
    "..KBBKBBBBKBBK.........",
    "..KKKKKKKKKKKK.........",
]

EYE_ROWS = {"cat": (5, 6), "bunny": (6, 7), "dooboo": (4, 5), "smokey": (4, 5)}
TEMPLATES = {"cat": CAT, "bunny": BUNNY, "dooboo": DOOBOO, "smokey": SMOKEY}

# extra markings per tabby (row, col) -> painted over fur
TABBY = [(3, 6), (3, 8), (3, 10), (4, 8), (4, 3), (5, 3), (4, 13), (5, 13),
         (11, 4), (12, 4), (11, 12), (12, 12), (13, 4), (13, 12),
         (12, 20), (13, 19), (15, 16)]
BELLY = [(r, c) for r in range(11, 17) for c in range(7, 10)]

KITTIES = {
    "noir":  dict(label="Noir", default="Noir", shape="cat",
                  K="#0b0b0e", B="#2f2f36", P="#f39bb0", E="#ffb21e", W="#0b0b0e"),
    "snow":  dict(label="Snowball", default="Snowball", shape="cat",
                  K="#16161a", B="#fbfbfb", P="#f7a8bb", E="#3fb3f2", W="#16161a"),
    "pebble": dict(label="Pebble", default="Pebble", shape="cat",
                   K="#16161a", B="#aaa59f", P="#f2a7b6", E="#ffffff", W="#16161a",
                   S="#6c6762", L="#e7c3bd", stripes=True, belly=True),
    "mango": dict(label="Mango", default="Mango", shape="cat",
                  K="#16161a", B="#e3803d", P="#f7cfb2", E="#ffffff", W="#16161a",
                  S="#b85a1f", L="#f6dcc2", stripes=True, belly=True),
    "dooboo": dict(label="DooBoo", default="DooBoo", shape="dooboo",
                   K="#2a1a10", B="#e9a44a", D="#c4762c", L="#fbf3e4", E="#1a1210", H="#ffffff",
                   T="#f07a95", P="#f4a3a3", C="#2b3a6e",
                   paw="#5c3417"),     # tucked-away tab: brown paw, 5:1 on the golden tab
    "smokey": dict(label="Beans", default="Beans", shape="smokey",          # id kept as "smokey"
                   K="#24252b", B="#8b909e", L="#f6f6f8", S="#d9dbe3", P="#f4a3b6", E="#1a1b20",
                   H="#ffffff", T="#f07a95"),
    "bunny": dict(label="Bunny", default="Bunny", shape="bunny",
                  K="#2a1e1a", B="#f1e3cf", L="#fffaf1", P="#f4a3b6", E="#2a1e1a", H="#ffffff"),
}
# the columns each body sits on (tail ignored) — the shadow is centred under these
SEAT = {"cat": (3, 13), "bunny": (2, 13), "dooboo": (2, 13), "smokey": (2, 13)}
ORDER = ["noir", "snow", "pebble", "mango", "dooboo", "smokey", "bunny"]
W = len(CAT[0])
H = len(CAT)


def grid(kitty: str, blink: bool = False) -> list[list[str | None]]:
    """Return a grid of hex colours (or None) for one frame of a built-in character."""
    pal = KITTIES[kitty]
    shape = pal.get("shape", "cat")
    rows = [list(r) for r in TEMPLATES[shape]]
    if pal.get("belly"):
        for r, c in BELLY:
            if rows[r][c] == "B":
                rows[r][c] = "L"
    if pal.get("stripes"):
        for r, c in TABBY:
            if rows[r][c] == "B":
                rows[r][c] = "S"
    top, low = EYE_ROWS[shape]
    for r in range(len(rows)):
        for c in range(len(rows[r])):
            if rows[r][c] in "EH":
                if blink:
                    rows[r][c] = "K" if r == low else pal.get("lid", "B")
                elif shape == "cat" and rows[r][c] == "E" and pal["E"] == "#ffffff" and c in (6, 11):
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


def paw_grid(color: str) -> list[list[str | None]]:
    return [[None if ch == "." else color for ch in row] for row in PAW]
