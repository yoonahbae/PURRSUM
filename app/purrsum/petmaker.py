"""Turn a pet image into a PurrSum sprite, entirely on this computer (no AI, no upload).

Pixel-art images (made with the pixel-pet prompt, or drawn by hand) become clean sprites:
background removed, cropped, snapped to a chunky grid, ≤16 colours, dark outline.
Regular photos can be turned into a "mosaic" after the user boxes the pet (OpenCV GrabCut).
Grids are lists of rows of '#rrggbb' strings or None (transparent).
"""
from __future__ import annotations

import numpy as np

TARGET_ROWS = 22          # about the kitties' height (18 rows + room for ears/tails)
MAX_COLS = 34
MAX_COLORS = 16
OUTLINE = (22, 22, 26)

PROMPT = """Turn my pet photo into a tiny pixel-art character for a desktop app.
- Keep my pet's real coat colors and markings, ear shape and tail.
- Sitting, facing forward, full body, about 24 pixels tall: big chunky square pixels, hard edges, no blur or gradients.
- A 1-pixel dark outline around the whole body.
- Eyes: two small solid square eyes (black, or the pet's real eye color).
- A small pink tongue is optional. The tail should be visible and curled.
- At most 12 colors, with 2-3 shades per color.
- Plain solid light background with no shadow, scenery, props or text, and only one pet in the picture."""


# ---------------------------------------------------------------- loading & checks
def load_image(path: str, max_side: int = 1600) -> np.ndarray:
    """RGBA uint8 array (first frame of a GIF), shrunk so the longest side ≤ max_side."""
    from PIL import Image
    im = Image.open(path)
    try:
        im.seek(0)
    except Exception:
        pass
    im = im.convert("RGBA")
    if max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.NEAREST)
    return np.asarray(im).copy()


def _border(a: np.ndarray, frac=0.02) -> np.ndarray:
    h, w = a.shape[:2]
    b = max(2, int(min(h, w) * frac))
    return np.concatenate([a[:b].reshape(-1, a.shape[2]), a[-b:].reshape(-1, a.shape[2]),
                           a[:, :b].reshape(-1, a.shape[2]), a[:, -b:].reshape(-1, a.shape[2])])


def _dist(rgb: np.ndarray, c) -> np.ndarray:
    return np.sqrt(((rgb.astype(np.int32) - np.asarray(c, np.int32)) ** 2).sum(-1))


def analyze(rgba: np.ndarray) -> dict:
    """Decide how to treat an image: 'pixel' (go straight on), 'box' (ask for a box) or 'photo'."""
    rgb = rgba[..., :3]
    alpha = rgba[..., 3]
    border = _border(rgba)
    transparent_bg = (border[:, 3] < 30).mean() > 0.9
    bg = np.median(border[:, :3], axis=0)
    flat = transparent_bg or (_dist(border[:, :3], bg) < 24).mean() > 0.9

    # blockiness: how often a pixel equals its right/lower neighbour (colours coarsened)
    small = rgb
    s = max(1, max(rgb.shape[:2]) // 700)
    if s > 1:
        small = rgb[::s, ::s]
    q = (small >> 4).astype(np.int16)
    same_r = (np.abs(q[:, 1:] - q[:, :-1]).sum(-1) == 0)
    same_d = (np.abs(q[1:] - q[:-1]).sum(-1) == 0)
    if transparent_bg:
        keep_r = alpha[::s, ::s][:, 1:] > 128
        keep_d = alpha[::s, ::s][1:] > 128
    else:
        keep_r = _dist(small[:, 1:], bg) > 30
        keep_d = _dist(small[1:], bg) > 30
    blocky = (same_r[keep_r].mean() + same_d[keep_d].mean()) / 2 if keep_r.any() else 0.0
    kind = "pixel" if (flat and blocky > 0.55) else ("box" if blocky > 0.55 else "photo")
    if kind == "pixel":
        m = _fg_mask_flat(rgba, bg, transparent_bg)
        if m.mean() < 0.002:          # nothing found on the plain background
            kind = "box"
    return {"kind": kind, "flat": bool(flat), "blocky": float(blocky),
            "bg": tuple(int(v) for v in bg), "transparent": bool(transparent_bg)}


# ---------------------------------------------------------------- masks
def _clean(mask: np.ndarray) -> np.ndarray:
    import cv2
    m = mask.astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m.astype(bool)
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = np.zeros(n, bool)
    keep[1:] = areas >= max(30, areas.max() * 0.02)
    return keep[lab]


def _fg_mask_flat(rgba, bg, transparent) -> np.ndarray:
    if transparent:
        return _clean(rgba[..., 3] > 128)
    import cv2
    rgb = rgba[..., :3].astype(np.int32)
    d = _dist(rgb, bg)
    # background = background-coloured areas that touch the picture's edge, so a white or
    # cream pet inside its outline is kept even though it's close to the background colour
    like_bg = (d <= 34).astype(np.uint8)
    n, lab = cv2.connectedComponents(like_bg, connectivity=4)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bgmask = np.isin(lab, edge[edge > 0]) & (like_bg > 0)
    fg = ~bgmask
    # drop the soft drop-shadow under the paws: greyish, a bit darker than the
    # background, close to it in colour, in the lower part of the figure
    ys = np.where(fg.any(1))[0]
    if len(ys):
        top, bot = ys[0], ys[-1]
        lower = np.zeros_like(fg)
        lower[top + int((bot - top) * 0.7):] = True
        sat = rgb.max(-1) - rgb.min(-1)
        lum = rgb.mean(-1)
        shadow = lower & (d < 80) & (sat < 40) & (lum < np.mean(bg) - 6) & (lum > np.mean(bg) - 90)
        fg &= ~shadow
    return _clean(fg)


def _fg_mask_box(rgba, rect) -> np.ndarray:
    """GrabCut inside the user's box (works on photos and busy backgrounds)."""
    import cv2
    h, w = rgba.shape[:2]
    s = min(1.0, 640 / max(h, w))
    small = cv2.resize(rgba[..., :3], (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    x, y, rw, rh = rect
    r = (max(0, int(x * s)), max(0, int(y * s)), max(2, int(rw * s)), max(2, int(rh * s)))
    r = (r[0], r[1], min(r[2], small.shape[1] - r[0] - 1), min(r[3], small.shape[0] - r[1] - 1))
    mask = np.zeros(small.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, r, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    m = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    return _clean(m)


# ---------------------------------------------------------------- to grid
def _native_scale(rgb, mask) -> int:
    """For crisp pixel art (each art pixel = s×s screen pixels) return s, else 0."""
    h, w = mask.shape
    best = 0
    for s in range(2, 65):
        if h // s < 6 or w // s < 6:
            break
        o = s // 2
        small = rgb[o::s, o::s][: h // s, : w // s]
        up = np.repeat(np.repeat(small, s, 0), s, 1)[: h, : w]
        hh, ww = up.shape[:2]
        same = (np.abs(up.astype(np.int16) - rgb[:hh, :ww]).sum(-1) <= 12)
        if same[mask[:hh, :ww]].mean() > 0.97:
            best = s
    return best


def _blocks(rgb, mask, rows) -> tuple[np.ndarray, np.ndarray]:
    h, w = mask.shape
    cell = h / rows
    cols = max(1, min(MAX_COLS, round(w / cell)))
    cell_w = w / cols
    out = np.zeros((rows, cols, 3), np.uint8)
    on = np.zeros((rows, cols), bool)
    for r in range(rows):
        y0, y1 = int(r * cell), max(int(r * cell) + 1, int((r + 1) * cell))
        for c in range(cols):
            x0, x1 = int(c * cell_w), max(int(c * cell_w) + 1, int((c + 1) * cell_w))
            m = mask[y0:y1, x0:x1]
            if m.size and m.mean() >= 0.45:
                px = rgb[y0:y1, x0:x1][m]
                # most common coarse colour wins (keeps hard pixel colours, ignores blur)
                q = (px >> 3).astype(np.int32)
                key = (q[:, 0] << 10) | (q[:, 1] << 5) | q[:, 2]
                vals, counts = np.unique(key, return_counts=True)
                top = vals[counts.argmax()]
                out[r, c] = np.median(px[key == top], axis=0)
                on[r, c] = True
    return out, on


def _quantize(cells, on, k) -> np.ndarray:
    import cv2
    px = cells[on].astype(np.float32)
    uniq = np.unique(px, axis=0)
    if len(uniq) <= k:
        return cells
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    out = cells.copy()
    out[on] = centers[labels.ravel()].clip(0, 255).astype(np.uint8)
    return out


def _lum(c) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _outline(cells, on) -> tuple[np.ndarray, np.ndarray]:
    """Add a 1-cell dark outline wherever the silhouette edge isn't already dark."""
    rows, cols = on.shape
    cells = np.pad(cells, ((1, 1), (1, 1), (0, 0)))
    on = np.pad(on, 1)
    add = np.zeros_like(on)
    for r in range(rows + 2):
        for c in range(cols + 2):
            if on[r, c]:
                continue
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows + 2 and 0 <= cc < cols + 2 and on[rr, cc] and _lum(cells[rr, cc]) > 70:
                    add[r, c] = True
                    break
    cells[add] = OUTLINE
    on = on | add
    # trim empty margins
    ys, xs = np.where(on)
    return cells[ys.min():ys.max() + 1, xs.min():xs.max() + 1], on[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def make_sprite(rgba: np.ndarray, info: dict, rect=None) -> list[list[str | None]]:
    """Image → sprite grid. rect=(x, y, w, h) uses the box (needed for photos)."""
    rgb = rgba[..., :3]
    if rect is not None:
        mask = _fg_mask_box(rgba, rect)
    else:
        mask = _fg_mask_flat(rgba, info["bg"], info["transparent"])
    if not mask.any():
        raise ValueError("I couldn't find a pet in there.")
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, mask = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]

    photo = info["kind"] == "photo"
    s = 0 if photo else _native_scale(rgb, mask)
    if s and (y1 - y0) // s <= 40:
        rows = (y1 - y0) // s
    else:
        rows = TARGET_ROWS
    cells, on = _blocks(rgb, mask, rows)
    if photo:   # a touch more colour so the mosaic reads as a character
        import cv2
        hsv = cv2.cvtColor(cells, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * 1.2, 0, 255)
        cells = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    cells = _quantize(cells, on, 12 if photo else MAX_COLORS)
    cells, on = _outline(cells, on)
    return [[("#%02x%02x%02x" % tuple(int(v) for v in cells[r, c])) if on[r, c] else None
             for c in range(on.shape[1])] for r in range(on.shape[0])]


# ---------------------------------------------------------------- blinking
def _rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def eye_region(grid, r, c) -> list[tuple[int, int]]:
    """The cells that make up the eye the user tapped (pupil + highlight), max 3×3."""
    base = grid[r][c]
    if base is None:
        return []
    b = _rgb(base)
    cells = []
    for rr in range(r - 1, r + 2):
        for cc in range(c - 1, c + 2):
            if 0 <= rr < len(grid) and 0 <= cc < len(grid[0]) and grid[rr][cc]:
                col = _rgb(grid[rr][cc])
                close = sum((x - y) ** 2 for x, y in zip(col, b)) ** 0.5 < 40
                highlight = _lum(col) > 215 and _lum(b) < 120
                if (rr, cc) == (r, c) or close or highlight:
                    cells.append((rr, cc))
    return cells


def blink_frame(grid, eyes: list[tuple[int, int]]) -> list[list[str | None]]:
    """Closed-eye frame: eye cells become fur with a short dark line underneath."""
    out = [row[:] for row in grid]
    taken = set()
    for (r, c) in eyes:
        region = [p for p in eye_region(grid, r, c) if p not in taken]
        taken.update(region)
        if not region:
            continue
        ring = {}
        rs = [p[0] for p in region]
        cs = [p[1] for p in region]
        for rr in range(min(rs) - 2, max(rs) + 3):
            for cc in range(min(cs) - 2, max(cs) + 3):
                if (rr, cc) in region or not (0 <= rr < len(grid) and 0 <= cc < len(grid[0])):
                    continue
                col = grid[rr][cc]
                if col and _lum(_rgb(col)) > 45:
                    ring[col] = ring.get(col, 0) + 1
        lid = max(ring, key=ring.get) if ring else grid[r][c]
        line = "#%02x%02x%02x" % OUTLINE
        if _lum(_rgb(lid)) < 60:          # very dark fur: a slightly lighter line shows the blink
            line = "#5a5a64"
        low = max(rs)
        for (rr, cc) in region:
            out[rr][cc] = line if (rr == low and max(rs) > min(rs)) else lid
        if max(rs) == min(rs):            # one-row eye: close it as a short line
            for cc in range(min(cs), max(cs) + 1):
                out[low][cc] = line
    return out
