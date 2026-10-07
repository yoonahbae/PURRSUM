"""All characters in one place: the built-in kitties and pups, plus the user's own pets.

A user's pet is stored as two tiny PNGs (one pixel per sprite cell: eyes open / closed)
and a small JSON file, under %APPDATA%\\PurrSum Noir\\pets.
Ids: built-ins use their name ("noir"); user pets use "pet:<id>".
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid

from PySide6.QtGui import QColor, QImage

from . import sprites

PAW_PINK = "#f39bb0"
_cache: dict[str, tuple] = {}


def pets_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "PurrSum Noir", "pets")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- grid <-> png
def grid_to_image(grid) -> QImage:
    h, w = len(grid), len(grid[0])
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    for r, row in enumerate(grid):
        for c, col in enumerate(row):
            if col:
                img.setPixelColor(c, r, QColor(col))
    return img


def image_to_grid(img: QImage):
    return [[(img.pixelColor(c, r).name() if img.pixelColor(c, r).alpha() > 127 else None)
             for c in range(img.width())] for r in range(img.height())]


# ---------------------------------------------------------------- user pets
def list_pets() -> list[dict]:
    out = []
    d = pets_dir()
    for f in os.listdir(d):
        if f.endswith(".json"):
            try:
                meta = json.load(open(os.path.join(d, f), encoding="utf-8"))
                if os.path.exists(os.path.join(d, meta["id"] + ".png")):
                    out.append(meta)
            except Exception:
                pass
    return sorted(out, key=lambda m: m.get("created", 0))


def save_pet(name: str, grid, blink) -> str:
    pid = uuid.uuid4().hex[:10]
    d = pets_dir()
    grid_to_image(grid).save(os.path.join(d, pid + ".png"))
    grid_to_image(blink).save(os.path.join(d, pid + "_blink.png"))
    with open(os.path.join(d, pid + ".json"), "w", encoding="utf-8") as f:
        json.dump({"id": pid, "name": name, "created": time.time()}, f)
    return pid


def delete_pet(pid: str):
    d = pets_dir()
    for f in (pid + ".png", pid + "_blink.png", pid + ".json"):
        try:
            os.remove(os.path.join(d, f))
        except OSError:
            pass
    _cache.pop("pet:" + pid, None)


def _pet_meta(pid: str) -> dict | None:
    try:
        return json.load(open(os.path.join(pets_dir(), pid + ".json"), encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------- any character
def exists(cid: str) -> bool:
    if cid in sprites.KITTIES:
        return True
    if cid.startswith("pet:"):
        return os.path.exists(os.path.join(pets_dir(), cid[4:] + ".png"))
    return False


def frames(cid: str):
    """(eyes-open grid, eyes-closed grid)."""
    if cid in sprites.KITTIES:
        return sprites.grid(cid), sprites.grid(cid, blink=True)
    if cid not in _cache:
        d, pid = pets_dir(), cid[4:]
        op = QImage(os.path.join(d, pid + ".png"))
        cl = QImage(os.path.join(d, pid + "_blink.png"))
        if op.isNull():
            return frames("noir")
        g = image_to_grid(op)
        _cache[cid] = (g, image_to_grid(cl) if not cl.isNull() else g)
    return _cache[cid]


def seat(cid: str, g=None) -> tuple[int, int]:
    """First and last column the buddy sits on (ignoring the tail), for centring the shadow."""
    if cid in sprites.KITTIES:
        return sprites.SEAT[sprites.KITTIES[cid]["shape"]]
    return seat_of(g or frames(cid)[0])


def seat_of(g) -> tuple[int, int]:
    """For your own pets: the widest solid stretch along the bottom rows (its paws)."""
    best = (0, len(g[0]) - 1)
    best_len = -1
    for row in g[-3:]:
        c = 0
        while c < len(row):
            if row[c] is None:
                c += 1
                continue
            s = c
            while c < len(row) and row[c] is not None:
                c += 1
            if c - s > best_len:
                best, best_len = (s, c - 1), c - s
    return best


def default_name(cid: str) -> str:
    if cid in sprites.KITTIES:
        return sprites.KITTIES[cid]["default"]
    meta = _pet_meta(cid[4:]) if cid.startswith("pet:") else None
    return (meta or {}).get("name", "My Pet")


def colors(cid: str) -> dict:
    """Outline, fur and paw colours for the tucked-away paw tab."""
    if cid in sprites.KITTIES:
        pal = sprites.KITTIES[cid]
        return {"K": pal["K"], "B": pal["B"], "P": pal.get("paw", pal.get("P", PAW_PINK))}
    g = frames(cid)[0]
    cols = [c for row in g for c in row if c]
    count = {}
    for c in cols:
        count[c] = count.get(c, 0) + 1
    darkest = min(count, key=lambda c: QColor(c).lightness())
    fur = max((c for c in count if c != darkest), key=count.get, default=darkest)
    return {"K": darkest, "B": fur, "P": PAW_PINK}
