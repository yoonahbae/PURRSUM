"""Local OCR (RapidOCR / ONNX). Nothing leaves the computer."""
from __future__ import annotations

import threading

import numpy as np

_engine = None
_lock = threading.Lock()


def engine():
    global _engine
    with _lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            e = RapidOCR()
            # screen snippets are small and often one long line: always detect text
            # boxes, never blow the picture up to a giant size, skip rotation checks
            e.width_height_ratio = -1
            e.min_height = 0
            e.use_angle_cls = False
            for op in e.text_detector.preprocess_op:
                if type(op).__name__ == "DetResizeForTest":
                    op.limit_type, op.limit_side_len = "max", 960
            _engine = e
        return _engine


def warm_up():
    try:
        engine()
    except Exception:
        pass


def _prep(rgb: np.ndarray) -> np.ndarray:
    import cv2
    h, w = rgb.shape[:2]
    # screen text is small; give the model more pixels to work with
    scale = 2 if h < 500 and w < 1400 else 1
    if scale > 1:
        rgb = cv2.resize(rgb, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    pad = 24
    rgb = cv2.copyMakeBorder(rgb, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def read_lines(rgb: np.ndarray) -> list[str]:
    """OCR an RGB image and return text lines, left-to-right, top-to-bottom."""
    result, _ = engine()(_prep(rgb))
    if not result:
        return []
    items = []
    for box, text, _score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), min(xs), max(xs), text))
    items.sort(key=lambda t: t[0])
    heights = sorted(t[1] for t in items)
    tol = max(4.0, heights[len(heights) // 2] * 0.5)
    lines: list[list[tuple]] = []
    for it in items:
        if lines and abs(lines[-1][-1][0] - it[0]) <= tol:
            lines[-1].append(it)
        else:
            lines.append([it])
    out = []
    for ln in lines:
        ln.sort(key=lambda t: t[2])
        # boxes that nearly touch are one phrase ("1641." + "60"); far ones are columns
        parts, prev_right = [], None
        for _, h, left, right, text in ln:
            if prev_right is not None:
                parts.append(" " if left - prev_right < h * 1.2 else "   ")
            parts.append(text)
            prev_right = right
        out.append("".join(parts))
    return out
