"""The "+ My Pet" dialog: image → (box) → tap the eyes → name → save. All on this computer."""
from __future__ import annotations

import math
import os

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from . import pets
from .ui import ACCENT, PICK_CSS, PX, app_icon, draw_grid

PET_CSS = PICK_CSS + """
#body { color:#3d3746; font-size:13px; }
#small { color:#5c5566; font-size:12px; }
#warn { color:#7a3e00; background:#fff3d6; border-radius:10px; padding:10px 12px; font-size:13px; }
QPushButton#ghost { background:transparent; color:#1f1b24; border:2px solid #1f1b24; border-radius:10px;
                    padding:9px 18px; font-size:14px; font-weight:600; }
QPushButton#ghost:hover { background:#efe8de; }
QPushButton#ghost:focus { outline:none; border:3px solid #b8740a; }
QPushButton#go:disabled { background:#b9b0a4; color:#ffffff; }
QCheckBox { color:#1f1b24; font-size:13px; spacing:8px; }
"""


def _button(text, primary=True, slot=None):
    b = QPushButton(text, objectName="go" if primary else "ghost")
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(44)
    if slot:
        b.clicked.connect(slot)
    return b


# ---------------------------------------------------------------- box around the pet
class BoxCanvas(QWidget):
    """Shows the picture; drag a box around the pet (a sensible box is there by default)."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 380)
        self.setCursor(Qt.CrossCursor)
        self.setAccessibleName("Your picture. Drag a box around your pet.")
        self.img = QImage()
        self.sel = QRectF()
        self._start = None

    def set_image(self, img: QImage):
        self.img = img
        r = self._img_rect()
        self.sel = r.adjusted(r.width() * 0.1, r.height() * 0.08, -r.width() * 0.1, -r.height() * 0.04)
        self.update()

    def _img_rect(self) -> QRectF:
        if self.img.isNull():
            return QRectF()
        s = min(self.width() / self.img.width(), self.height() / self.img.height())
        w, h = self.img.width() * s, self.img.height() * s
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def image_rect(self):
        """The box in the original picture's pixels: (x, y, w, h)."""
        r = self._img_rect()
        s = self.img.width() / r.width()
        b = self.sel.intersected(r)
        return (int((b.x() - r.x()) * s), int((b.y() - r.y()) * s), int(b.width() * s), int(b.height() * s))

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#efe8de"))
        r = self._img_rect()
        if self.img.isNull():
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(r, self.img)
        p.fillRect(r, QColor(20, 18, 26, 110))
        p.drawImage(self.sel, self.img, QRectF(
            (self.sel.x() - r.x()) * self.img.width() / r.width(),
            (self.sel.y() - r.y()) * self.img.height() / r.height(),
            self.sel.width() * self.img.width() / r.width(),
            self.sel.height() * self.img.height() / r.height()))
        p.setPen(QPen(ACCENT, 3))
        p.drawRect(self.sel)

    def mousePressEvent(self, e):
        self._start = e.position()
        self.sel = QRectF(self._start, self._start)
        self.update()

    def mouseMoveEvent(self, e):
        if self._start is not None:
            self.sel = QRectF(self._start, e.position()).normalized().intersected(self._img_rect())
            self.update()

    def mouseReleaseEvent(self, e):
        self._start = None
        if self.sel.width() < 12 or self.sel.height() < 12:
            self.set_image(self.img)          # too small: back to the default box


# ---------------------------------------------------------------- tap the eyes
class EyeCanvas(QWidget):
    """The new sprite, big. Tap (or arrow keys + Space) to mark the eyes."""

    def __init__(self, on_change):
        super().__init__()
        self.setMinimumSize(360, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Your pet, enlarged. Tap each eye, or use the arrow keys and Space.")
        self.grid = None
        self.eyes: list[tuple[int, int]] = []
        self.cursor = (0, 0)
        self.on_change = on_change

    def set_grid(self, g):
        self.grid = g
        self.eyes = []
        self.cursor = (len(g) // 3, len(g[0]) // 2)
        self.update()

    def _geom(self):
        rows, cols = len(self.grid), len(self.grid[0])
        cell = max(4, min(16, (self.width() - 20) // cols, (self.height() - 20) // rows))
        x0 = (self.width() - cols * cell) // 2
        y0 = (self.height() - rows * cell) // 2
        return cell, x0, y0

    def _toggle(self, rc):
        if self.grid is None or self.grid[rc[0]][rc[1]] is None:
            return
        if rc in self.eyes:
            self.eyes.remove(rc)
        else:
            self.eyes.append(rc)
            self.eyes = self.eyes[-2:]
        self.update()
        self.on_change()

    def mousePressEvent(self, e):
        if self.grid is None:
            return
        cell, x0, y0 = self._geom()
        c = int((e.position().x() - x0) // cell)
        r = int((e.position().y() - y0) // cell)
        if 0 <= r < len(self.grid) and 0 <= c < len(self.grid[0]):
            self.cursor = (r, c)
            self._toggle((r, c))

    def keyPressEvent(self, e):
        if self.grid is None:
            return super().keyPressEvent(e)
        r, c = self.cursor
        moves = {Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1), Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0)}
        if e.key() in moves:
            dr, dc = moves[e.key()]
            self.cursor = (min(max(r + dr, 0), len(self.grid) - 1), min(max(c + dc, 0), len(self.grid[0]) - 1))
            self.update()
        elif e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self._toggle(self.cursor)
        else:
            super().keyPressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#cfc6ba"))       # mid-tone so white and black pets both show
        if self.grid is None:
            return
        cell, x0, y0 = self._geom()
        draw_grid(p, self.grid, x0, y0, cell)
        p.setRenderHint(QPainter.Antialiasing)
        for i, (r, c) in enumerate(self.eyes, 1):
            ctr = QPointF(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell)
            p.setPen(QPen(QColor("#ffffff"), 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(ctr, cell * 0.9, cell * 0.9)
            p.setPen(QPen(ACCENT, 2.5))
            p.drawEllipse(ctr, cell * 0.9, cell * 0.9)
        if self.hasFocus():
            r, c = self.cursor
            p.setPen(QPen(QColor("#b8740a"), 2, Qt.DashLine))
            p.drawRect(QRectF(x0 + c * cell, y0 + r * cell, cell, cell))


# ---------------------------------------------------------------- live preview
class Preview(QWidget):
    """The pet at real size: floating and blinking, like it will on your screen."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(150, 150)
        self.setAccessibleName("Preview of your pet")
        self.frames = None
        self.t = 0.0
        self.timer = QTimer(self, interval=60, timeout=self._tick)
        self.timer.start()

    def set_frames(self, op, cl):
        self.frames = (op, cl)
        self.update()

    def _tick(self):
        self.t += 0.06
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2a2632"))
        p.drawRoundedRect(QRectF(self.rect()), 14, 14)
        if not self.frames:
            return
        blink = (self.t % 2.4) > 2.25
        g = self.frames[1] if blink else self.frames[0]
        gw, gh = len(g[0]) * PX, len(g) * PX
        lift = abs(math.sin(self.t * 1.8)) * 2.5
        x, y = (self.width() - gw) / 2, (self.height() - gh) / 2 + 4
        p.setBrush(QColor(0, 0, 0, 90))
        a, b = pets.seat_of(g)
        cx = x + (a + b + 1) / 2 * PX
        sw = (b - a + 1) * PX * 0.95 - lift * 2
        p.drawEllipse(QRectF(cx - sw / 2, y + gh - 4, sw, 7))
        p.setRenderHint(QPainter.Antialiasing, False)
        draw_grid(p, g, x, y - round(lift), PX)


# ---------------------------------------------------------------- the dialog
class PetMaker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("Add your own pet")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(PET_CSS)
        self.saved_id = None
        self.saved_name = ""
        self.rgba = None
        self.info = None
        self.grid = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        self.pages = QStackedWidget()
        lay.addWidget(self.pages)
        self.pages.addWidget(self._page_start())
        self.pages.addWidget(self._page_box())
        self.pages.addWidget(self._page_eyes())

    # page 1 ------------------------------------------------------------------
    def _page_start(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        v.addWidget(QLabel("Add your own pet", objectName="title"))
        t = QLabel("Best results: a <b>pixel-art picture of your pet on a plain background</b>. "
                   "Turn any pet photo into one with an AI image tool using our prompt, then choose "
                   "that picture here. Everything else happens on this computer.", objectName="body")
        t.setWordWrap(True)
        v.addWidget(t)
        self.copy_btn = _button("Copy the pixel-pet prompt", primary=False, slot=self._copy_prompt)
        v.addWidget(self.copy_btn, 0, Qt.AlignLeft)
        v.addSpacing(8)
        self.start_msg = QLabel("", objectName="warn")
        self.start_msg.setWordWrap(True)
        self.start_msg.hide()
        v.addWidget(self.start_msg)
        v.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(QLabel("PNG, JPG, WebP, BMP or GIF", objectName="small"))
        row.addStretch(1)
        row.addWidget(_button("Choose a picture…", slot=self._choose))
        v.addLayout(row)
        w.setMinimumSize(560, 260)
        return w

    def _copy_prompt(self):
        from .petmaker import PROMPT
        QGuiApplication.clipboard().setText(PROMPT)
        for b in (self.copy_btn, getattr(self, "copy_btn2", None)):
            if b:
                b.setText("Prompt copied ✓")
                QTimer.singleShot(2500, lambda b=b: b.setText("Copy the pixel-pet prompt"))

    def _choose(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose your pet's picture", os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if path:
            self.load(path)

    def load(self, path):
        """Open a picture and decide what happens next (public so tests can call it)."""
        try:
            from . import petmaker
        except ImportError:
            return self._start_error("PurrSum's picture tools aren't set up yet. Run the "
                                     "“Install PurrSum Noir” file again while online.")
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.rgba = petmaker.load_image(path)
            self.info = petmaker.analyze(self.rgba)
        except Exception:
            return self._start_error("That file couldn't be opened as a picture. "
                                     "Try a PNG or JPG.")
        finally:
            QApplication.restoreOverrideCursor()
        if self.info["kind"] == "pixel":
            self._make(None)
        else:
            self._show_box()

    def _start_error(self, msg):
        self.start_msg.setText(msg)
        self.start_msg.show()
        self.pages.setCurrentIndex(0)

    # page 2 ------------------------------------------------------------------
    def _page_box(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.box_title = QLabel("", objectName="title")
        v.addWidget(self.box_title)
        self.box_msg = QLabel("", objectName="body")
        self.box_msg.setWordWrap(True)
        v.addWidget(self.box_msg)
        self.box = BoxCanvas()
        v.addWidget(self.box, 1)
        row = QHBoxLayout()
        row.addWidget(_button("Back", primary=False, slot=lambda: self.pages.setCurrentIndex(0)))
        self.copy_btn2 = _button("Copy the pixel-pet prompt", primary=False, slot=self._copy_prompt)
        row.addWidget(self.copy_btn2)
        row.addStretch(1)
        row.addWidget(_button("Use this box", slot=lambda: self._make(self.box.image_rect())))
        v.addLayout(row)
        return w

    def _show_box(self):
        h, w = self.rgba.shape[:2]
        img = QImage(self.rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
        self.box.set_image(img)
        if self.info["kind"] == "photo":
            self.box_title.setText("This looks like a regular photo")
            self.box_msg.setText("PurrSum can turn it into a little pixel mosaic, but it won't look "
                                 "hand-drawn. For a cuter buddy, copy the pixel-pet prompt, make a pixel "
                                 "version with an AI image tool, and choose that instead. Or drag a box "
                                 "around your pet to try the mosaic.")
            self.copy_btn2.show()
        else:
            self.box_title.setText("Drag a box around your pet")
            self.box_msg.setText("The background is busy, so show PurrSum where your pet is.")
            self.copy_btn2.hide()
        self.pages.setCurrentIndex(1)

    # page 3 ------------------------------------------------------------------
    def _page_eyes(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(QLabel("Tap your pet's eyes", objectName="title"))
        t = QLabel("Tap each eye once so your pet can blink. Tap again to undo.", objectName="body")
        t.setWordWrap(True)
        v.addWidget(t)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.eyes = EyeCanvas(self._refresh)
        row.addWidget(self.eyes, 1)
        side = QVBoxLayout()
        side.setSpacing(8)
        side.addWidget(QLabel("Preview", objectName="small"))
        self.preview = Preview()
        side.addWidget(self.preview)
        self.no_blink = QCheckBox("No blink")
        self.no_blink.toggled.connect(self._refresh)
        side.addWidget(self.no_blink)
        side.addStretch(1)
        row.addLayout(side)
        v.addLayout(row, 1)
        lbl = QLabel("Name your pet")
        lbl.setStyleSheet("font-weight:600;")
        v.addWidget(lbl)
        self.pet_name = QLineEdit()
        self.pet_name.setMaxLength(24)
        self.pet_name.setPlaceholderText("e.g. Pepper")
        self.pet_name.setAccessibleName("Pet name")
        lbl.setBuddy(self.pet_name)
        self.pet_name.textChanged.connect(self._refresh)
        v.addWidget(self.pet_name)
        row2 = QHBoxLayout()
        row2.addWidget(_button("Start over", primary=False, slot=lambda: self.pages.setCurrentIndex(0)))
        row2.addStretch(1)
        self.save_btn = _button("Save my pet", slot=self._save)
        row2.addWidget(self.save_btn)
        v.addLayout(row2)
        return w

    def _make(self, rect):
        from . import petmaker
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.grid = petmaker.make_sprite(self.rgba, self.info, rect)
        except Exception:
            QApplication.restoreOverrideCursor()
            if rect is None:
                return self._show_box()
            self.box_msg.setText("I couldn't find a pet in that box. Try drawing it a little bigger.")
            return
        QApplication.restoreOverrideCursor()
        self.eyes.set_grid(self.grid)
        self.no_blink.setChecked(False)
        self._refresh()
        self.pages.setCurrentIndex(2)
        self.eyes.setFocus()

    def _closed(self):
        from . import petmaker
        if self.no_blink.isChecked() or not self.eyes.eyes:
            return self.grid
        return petmaker.blink_frame(self.grid, self.eyes.eyes)

    def _refresh(self, *_):
        if self.grid is None:
            return
        self.preview.set_frames(self.grid, self._closed())
        ok = bool(self.pet_name.text().strip()) and (self.no_blink.isChecked() or bool(self.eyes.eyes))
        self.save_btn.setEnabled(ok)

    def _save(self):
        name = self.pet_name.text().strip()
        self.saved_id = pets.save_pet(name, self.grid, self._closed())
        self.saved_name = name
        self.accept()
