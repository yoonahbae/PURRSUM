from __future__ import annotations

import json
import math
import os
import random
import sys
import threading
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtCore import (QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt,
                            QTimer, Signal)
from PySide6.QtGui import (QAction, QColor, QCursor, QFont, QGuiApplication,
                           QIcon, QImage, QKeySequence, QPainter, QPainterPath,
                           QPen, QPixmap, QShortcut)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QToolButton,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import sprites
from .purrsum_reader import Reader, decimals_in, find_numbers, fmt

APP = "PurrSum Noir"
SERVER = "PurrSumNoir-" + (os.environ.get("USERNAME") or os.environ.get("USER") or "me")
PX = 3                    # one sprite pixel = 3 screen points: a tiny cat
ACCENT = QColor("#ffb21e")


# ---------------------------------------------------------------- settings
def _settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, APP)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")


class Settings(dict):
    def __init__(self):
        super().__init__()
        try:
            with open(_settings_path(), encoding="utf-8") as f:
                self.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(self, f, indent=1)
        except Exception:
            pass


# ---------------------------------------------------------------- drawing
def draw_grid(p: QPainter, g, x: float, y: float, px: float):
    for r, row in enumerate(g):
        for c, col in enumerate(row):
            if col:
                p.fillRect(QRectF(x + c * px, y + r * px, px, px), QColor(col))


def sprite_pixmap(kitty: str, px: int, blink=False) -> QPixmap:
    pm = QPixmap(sprites.W * px, sprites.H * px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    draw_grid(p, sprites.grid(kitty, blink), 0, 0, px)
    p.end()
    return pm


def app_icon(kitty="noir") -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.transparent)
        px = s / (sprites.W + 1)
        p = QPainter(pm)
        draw_grid(p, sprites.grid(kitty), px / 2, (s - sprites.H * px) / 2, px)
        p.end()
        icon.addPixmap(pm)
    return icon


def grab_screen(scr) -> QPixmap:
    """Freeze-frame of one monitor (device pixels, devicePixelRatio set)."""
    return scr.grabWindow(0)


def screen_at(pt: QPoint):
    s = QGuiApplication.screenAt(pt)
    if s:
        return s

    def dist(scr):
        g = scr.geometry()
        dx = max(g.left() - pt.x(), 0, pt.x() - g.right())
        dy = max(g.top() - pt.y(), 0, pt.y() - g.bottom())
        return dx * dx + dy * dy
    return min(QGuiApplication.screens(), key=dist)


# ---------------------------------------------------------------- the cat
class Cat(QWidget):
    clicked = Signal()
    moved = Signal()
    menu_requested = Signal(QPoint)

    def __init__(self, settings: Settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.s = settings
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAccessibleName("PurrSum cat")
        self.kitty = settings.get("kitty", "noir")
        self.tucked = False
        self.side = "right"
        self.restore_pos = None
        self.bob = 0.0
        self.blink = False
        self.busy = False
        self.hop = 0
        self._press = None
        self._dragging = False
        self.cat_size = QSize(sprites.W * PX + 4, sprites.H * PX + 18)
        self.tab_size = QSize(34, 44)
        self.resize(self.cat_size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to add up numbers · drag to move · right-click for more")

        self.t_bob = QTimer(self, interval=60, timeout=self._tick)
        self.t_bob.start()
        self.t_blink = QTimer(self, singleShot=True, timeout=self._blink)
        self.t_blink.start(2500)

    # animation
    def _tick(self):
        self.bob += 0.11
        if self.hop:
            self.hop -= 1
        self.update()

    def _blink(self):
        self.blink = not self.blink
        self.update()
        self.t_blink.start(140 if self.blink else random.randint(2500, 6000))

    def happy_hop(self):
        self.hop = 12

    def set_kitty(self, kitty):
        self.kitty = kitty
        self.update()

    # geometry
    def place_default(self):
        a = QGuiApplication.primaryScreen().availableGeometry()
        self.move(a.right() - self.width() - 24, a.bottom() - self.height() - 24)

    def place_saved(self):
        x, y = self.s.get("x"), self.s.get("y")
        if x is not None and QGuiApplication.screenAt(QPoint(x + 20, y + 20)):
            self.move(x, y)
        else:
            self.place_default()

    def keep_on_screen(self):
        """Never let the cat get lost off the edge of a monitor."""
        a = screen_at(self.frameGeometry().center()).availableGeometry()
        x = min(max(self.x(), a.left()), a.right() - self.width() + 1)
        y = min(max(self.y(), a.top()), a.bottom() - self.height() + 1)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
            self.moved.emit()

    def anchor(self) -> QRect:
        return self.frameGeometry()

    def tuck(self):
        if self.tucked:
            return
        self.restore_pos = self.pos()
        a = screen_at(self.frameGeometry().center()).availableGeometry()
        self.side = "left" if self.frameGeometry().center().x() < a.center().x() else "right"
        self.tucked = True
        self.resize(self.tab_size)
        y = min(max(self.restore_pos.y() + 10, a.top()), a.bottom() - self.height())
        x = a.left() if self.side == "left" else a.right() - self.width() + 1
        self.move(x, y)
        self.setToolTip("Click to bring the cat back")
        self.moved.emit()
        self.update()

    def untuck(self):
        if not self.tucked:
            return
        self.tucked = False
        self.resize(self.cat_size)
        if self.restore_pos is not None:
            self.move(self.restore_pos)
        if not QGuiApplication.screenAt(self.frameGeometry().center()):
            self.place_default()
        self.setToolTip("Click to add up numbers · drag to move · right-click for more")
        self.happy_hop()
        self.moved.emit()
        self.update()

    def summon(self):
        self.untuck()
        if not QGuiApplication.screenAt(self.frameGeometry().center()):
            self.place_default()
        self.show()
        self.raise_()
        self.happy_hop()

    # painting
    def paintEvent(self, _):
        p = QPainter(self)
        # an almost-invisible fill keeps the whole cat clickable (no click-through gaps)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        if self.tucked:
            self._paint_tab(p)
            return
        if self.hop:
            lift = abs(math.sin(self.hop / 12 * math.pi)) * 10
        else:
            lift = abs(math.sin(self.bob)) * 2.5
        h = sprites.H * PX
        # soft shadow that shrinks as the cat lifts
        p.setRenderHint(QPainter.Antialiasing)
        sw = 50 - lift * 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(QRectF(4 + (50 - sw) / 2, 10 + h - 4, sw, 7))
        p.setRenderHint(QPainter.Antialiasing, False)
        draw_grid(p, sprites.grid(self.kitty, self.blink and not self.busy), 2, 10 - round(lift), PX)
        if self.busy:  # thinking dots
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(ACCENT)
            for i in range(3):
                on = int(self.bob * 4) % 3 == i
                p.drawEllipse(QPointF(46 + i * 7, 6), 2.6 if on else 1.8, 2.6 if on else 1.8)

    def _paint_tab(self, p: QPainter):
        pal = sprites.KITTIES[self.kitty]
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        if self.side == "right":
            path.addRoundedRect(r.adjusted(0, 0, 12, 0), 10, 10)
        else:
            path.addRoundedRect(r.adjusted(-12, 0, 0, 0), 10, 10)
        p.setClipRect(self.rect())
        p.setPen(QPen(QColor(pal["K"]), 2))
        p.setBrush(QColor(pal["B"]))
        p.drawPath(path)
        p.setRenderHint(QPainter.Antialiasing, False)
        draw_grid(p, sprites.paw_grid(self.kitty), (self.width() - 24) / 2 + (2 if self.side == "right" else -2), 14, 2)

    # mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragging = False
        elif e.button() == Qt.RightButton:
            self.menu_requested.emit(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._press is None or self.tucked:
            return
        d = e.globalPosition().toPoint() - self._press
        if not self._dragging and d.manhattanLength() > 4:
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        if self._dragging:
            self.move(self._origin + d)
            self.moved.emit()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._press is None:
            return
        self._press = None
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.PointingHandCursor)
            self.keep_on_screen()
            self.s["x"], self.s["y"] = self.x(), self.y()
            self.s.save()
        elif self.tucked:
            self.untuck()
        else:
            self.clicked.emit()

    def contextMenuEvent(self, e):
        e.accept()


# ---------------------------------------------------------------- numbers found
@dataclass
class Found:
    value: Decimal
    text: str            # as it was written, for the bubble
    box: int = 1         # which selection box it came from
    included: bool = True


def total_of(found) -> Decimal:
    return sum((f.value for f in found if f.included), Decimal(0))


def places_of(found) -> int:
    return max((decimals_in(f.value) for f in found), default=0)


def pretty_total(found) -> str:
    return fmt(total_of(found), places_of(found))


def clipboard_total(found) -> str:
    """Total for pasting: no thousands commas."""
    return pretty_total(found).replace(",", "")


# ---------------------------------------------------------------- selection overlay
class Selection(QObject):
    """Dims every monitor and collects one or more boxes."""
    done = Signal(list)      # [(global QRect, QImage crop), ...]
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.rects: list[QRect] = []
        self.current: QRect | None = None
        self.start: QPoint | None = None
        self.start_screen = None
        self.overlays: list[Overlay] = []
        self.shots = {}
        self.closed = False
        self._keys_down = set()
        self.key_timer = None

    def begin(self):
        for scr in QGuiApplication.screens():
            self.shots[scr] = grab_screen(scr)
        for scr in QGuiApplication.screens():
            o = Overlay(self, scr, self.shots[scr])
            self.overlays.append(o)
        for o in self.overlays:
            o.show_on_screen()
        under = screen_at(QCursor.pos())
        for o in self.overlays:
            if o.screen_ == under:
                o.activateWindow()
                o.raise_()
                o.setFocus()
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.SetForegroundWindow(int(o.winId()))
                    except Exception:
                        pass
        if sys.platform == "win32":
            # Enter / Esc work even if Windows didn't give the dimmed screen keyboard focus
            self.key_timer = QTimer(self, interval=30, timeout=self._poll_keys)
            self.key_timer.start()

    def _poll_keys(self):
        try:
            import ctypes
            gaks = ctypes.windll.user32.GetAsyncKeyState
        except Exception:
            return
        for vk, action in ((0x1B, self.cancel), (0x0D, self.finish)):
            down = bool(gaks(vk) & 0x8000)
            if down and vk not in self._keys_down:
                self._keys_down.add(vk)
                action()
                return
            if not down:
                self._keys_down.discard(vk)

    @staticmethod
    def shift_down() -> bool:
        if sys.platform == "win32":
            try:
                import ctypes
                return bool(ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000)
            except Exception:
                pass
        return False

    def refresh(self):
        for o in self.overlays:
            o.update()

    def _close(self):
        self.closed = True
        if self.key_timer:
            self.key_timer.stop()
        for o in self.overlays:
            o.hide()
            o.deleteLater()
        self.overlays = []

    def cancel(self):
        if self.closed:
            return
        self._close()
        self.cancelled.emit()

    def finish(self):
        if self.closed:
            return
        if self.current is not None:
            self._commit()
        if not self.rects:
            return self.cancel()
        crops = []
        for r in self.rects:
            scr = screen_at(r.center())
            pm = self.shots[scr]
            g = scr.geometry()
            d = pm.devicePixelRatio()
            src = QRect(round((r.x() - g.x()) * d), round((r.y() - g.y()) * d),
                        round(r.width() * d), round(r.height() * d))
            crops.append((r, pm.copy(src).toImage()))
        self._close()
        self.done.emit(crops)

    # mouse from any overlay, in global coordinates
    def press(self, gp: QPoint):
        self.start = gp
        self.start_screen = screen_at(gp)
        self.current = QRect(gp, gp)
        self.refresh()

    def drag(self, gp: QPoint):
        if self.start is None:
            return
        g = self.start_screen.geometry()
        gp = QPoint(min(max(gp.x(), g.left()), g.right()), min(max(gp.y(), g.top()), g.bottom()))
        self.current = QRect(self.start, gp).normalized()
        self.refresh()

    def release(self, shift: bool):
        if self.current is None:
            return
        self._commit()
        if not shift and self.rects:
            self.finish()

    def _commit(self):
        if self.current and self.current.width() > 4 and self.current.height() > 4:
            self.rects.append(self.current)
        self.current = None
        self.start = None
        self.refresh()


class Overlay(QWidget):
    def __init__(self, sel: Selection, screen, shot: QPixmap):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.sel, self.screen_, self.shot = sel, screen, shot
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName("Drag a box over the numbers to add up")

    def show_on_screen(self):
        self.setGeometry(self.screen_.geometry())
        self.winId()
        self.windowHandle().setScreen(self.screen_)
        self.setGeometry(self.screen_.geometry())
        self.show()
        self.raise_()

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.shot)
        p.fillRect(self.rect(), QColor(8, 8, 14, 150))
        off = self.screen_.geometry().topLeft()
        d = self.shot.devicePixelRatio()
        boxes = list(enumerate(self.sel.rects, 1))
        if self.sel.current is not None:
            boxes.append((len(self.sel.rects) + 1, self.sel.current))
        p.setRenderHint(QPainter.Antialiasing)
        for n, r in boxes:
            if not r.intersects(self.screen_.geometry()):
                continue
            lr = r.translated(-off)
            src = QRectF(lr.x() * d, lr.y() * d, lr.width() * d, lr.height() * d)
            p.drawPixmap(QRectF(lr), self.shot, src)
            p.setPen(QPen(ACCENT, 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(lr).adjusted(-1, -1, 1, 1))
            # numbered badge
            c = QPointF(lr.left(), lr.top())
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawEllipse(c, 11, 11)
            p.setPen(QColor("#1a1206"))
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSizeF(9)
            p.setFont(f)
            p.drawText(QRectF(c.x() - 11, c.y() - 11, 22, 22), Qt.AlignCenter, str(n))
        # hint
        hint = ("Drag over numbers   ·   hold Shift to add more boxes   ·   "
                "Enter to add up   ·   Esc to cancel")
        f = QFont(self.font())
        f.setPointSizeF(10.5)
        p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(hint) + 36
        hr = QRectF((self.width() - w) / 2, 22, w, 36)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 18, 26, 235))
        p.drawRoundedRect(hr, 18, 18)
        p.setPen(QColor("#f4f1ea"))
        p.drawText(hr, Qt.AlignCenter, hint)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.sel.cancel()
        elif e.button() == Qt.LeftButton:
            self.sel.press(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        self.sel.drag(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            shift = (bool((e.modifiers() | QGuiApplication.queryKeyboardModifiers()) & Qt.ShiftModifier)
                     or self.sel.shift_down())
            self.sel.release(shift)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.sel.cancel()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.sel.finish()


# ---------------------------------------------------------------- result bubble
BUBBLE_CSS = """
#card { background:#1c1a22; border:1px solid #3a3644; border-radius:14px; }
QLabel { color:#f4f1ea; }
#who { color:#b9b3c6; font-size:12px; }
#total { font-size:26px; font-weight:700; color:#ffffff; }
#copied { background:#2e2a12; color:#ffcf6b; border-radius:9px; padding:2px 8px; font-size:11px; }
#hint { color:#8f889e; font-size:11px; }
#badge { background:#ffb21e; color:#1a1206; border-radius:9px; font-size:10px; font-weight:700; }
#val { font-size:14px; font-family:"Segoe UI", "Inter", sans-serif; }
QPushButton#row { text-align:left; border:none; border-radius:7px; padding:5px 8px;
                  color:#f4f1ea; background:transparent; font-size:13px; }
QPushButton#row:hover { background:#2a2632; }
QPushButton#row:focus { outline:none; background:#2a2632; border:1px solid #ffb21e; }
QPushButton#row:checked { color:#6f6880; }
QPushButton#close { border:none; color:#b9b3c6; font-size:16px; padding:0 6px; background:transparent; }
QPushButton#close:hover, QPushButton#close:focus { color:#ffffff; }
QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; border:none; }
QScrollBar:vertical { width:6px; background:transparent; }
QScrollBar::handle:vertical { background:#4a4556; border-radius:3px; }
"""


class Bubble(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(BUBBLE_CSS)
        self.setFixedWidth(250)
        self.found: list[Found] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame(objectName="card")
        outer.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(14, 10, 10, 12)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.who = QLabel(objectName="who")
        top.addWidget(self.who, 1)
        x = QPushButton("×", objectName="close", clicked=self.hide)
        x.setAccessibleName("Close")
        x.setCursor(Qt.PointingHandCursor)
        top.addWidget(x)
        lay.addLayout(top)
        tl = QHBoxLayout()
        self.total = QLabel(objectName="total")
        self.total.setTextInteractionFlags(Qt.TextSelectableByMouse)
        tl.addWidget(self.total, 1)
        self.copied = QLabel("Copied ✓", objectName="copied")
        tl.addWidget(self.copied, 0, Qt.AlignVCenter)
        lay.addLayout(tl)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list = QWidget()
        self.rows = QVBoxLayout(self.list)
        self.rows.setContentsMargins(0, 2, 4, 0)
        self.rows.setSpacing(1)
        self.scroll.setWidget(self.list)
        lay.addWidget(self.scroll)
        self.hint = QLabel(objectName="hint")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.hide)

    def _clear_rows(self):
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w:
                w.deleteLater()

    def show_busy(self, name):
        self.found = []
        self._clear_rows()
        self.who.setText(f"{name} is counting…")
        self.total.setText("…")
        self.copied.hide()
        self.scroll.hide()
        self.hint.hide()
        self.adjustSize()

    def show_error(self, name, msg):
        self.who.setText(name)
        self.total.setText("Hmm.")
        self.copied.hide()
        self.scroll.hide()
        self.hint.setText(msg)
        self.hint.show()
        self.adjustSize()

    def show_result(self, name, found: list[Found], nboxes: int):
        self.found = found
        self._clear_rows()
        if not found:
            self.show_error(name, "I couldn't find any numbers in there. Try a slightly bigger box.")
            return
        self.who.setText(f"{name} found {len(found)} number{'s' if len(found) != 1 else ''}")
        multi = len({f.box for f in found}) > 1
        for f in found:
            b = QPushButton(objectName="row", checkable=True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(28)
            b.f = f
            rl = QHBoxLayout(b)
            rl.setContentsMargins(8, 0, 8, 0)
            badge = QLabel(str(f.box) if multi else "", objectName="badge")
            badge.setFixedSize(18, 18)
            badge.setAlignment(Qt.AlignCenter)
            badge.setVisible(multi)
            b.val = QLabel(objectName="val")
            b.val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            b.val.setAttribute(Qt.WA_TransparentForMouseEvents)
            badge.setAttribute(Qt.WA_TransparentForMouseEvents)
            rl.addWidget(badge)
            rl.addStretch(1)
            rl.addWidget(b.val)
            b.toggled.connect(lambda on, b=b: self._toggle(b, on))
            self._label(b)
            self.rows.addWidget(b)
        self.rows.addStretch(1)
        self.scroll.show()
        rows_h = min(len(found), 8) * 29 + 4
        self.scroll.setFixedHeight(rows_h)
        self.hint.setText("Click a number to leave it out.")
        self.hint.show()
        self._update_total()
        self.adjustSize()

    def _label(self, b):
        f = b.f
        b.val.setText(f.text)
        font = b.val.font()
        font.setStrikeOut(not f.included)
        b.val.setFont(font)
        b.val.setStyleSheet("color:#f4f1ea;" if f.included else "color:#6f6880;")
        b.setToolTip("Click to leave this out" if f.included else "Click to add this back")
        b.setAccessibleName(f"{f.text}, {'included' if f.included else 'left out'}. Press to toggle.")

    def _toggle(self, b, checked):
        b.f.included = not checked
        self._label(b)
        self._update_total()

    def _update_total(self):
        self.total.setText(pretty_total(self.found))
        QGuiApplication.clipboard().setText(clipboard_total(self.found))
        self.copied.show()

    def follow(self, anchor: QRect):
        if not self.isVisible():
            return
        self.adjustSize()
        a = screen_at(anchor.center()).availableGeometry()
        w, h = self.width(), self.height()
        x = anchor.left() - w - 6
        if x < a.left():
            x = anchor.right() + 6
        if x + w > a.right():
            x = a.right() - w
        y = anchor.bottom() - h
        y = min(max(y, a.top()), a.bottom() - h)
        self.move(x, y)


# ---------------------------------------------------------------- kitty picker
PICK_CSS = """
QDialog { background:#faf7f2; }
QLabel { color:#1f1b24; }
#title { font-size:20px; font-weight:700; }
#sub { color:#5c5566; font-size:12px; }
QToolButton#kitty { background:#ffffff; border:2px solid #e6e0d8; border-radius:14px;
                    padding:10px 6px 8px 6px; color:#1f1b24; font-size:12px; }
QToolButton#kitty:hover { border-color:#c9bfb2; }
QToolButton#kitty:checked { border:3px solid #1f1b24; background:#fff6e3; }
QToolButton#kitty:focus { outline:none; border:3px solid #b8740a; }
QLineEdit { background:#ffffff; border:2px solid #d9d2c8; border-radius:10px; padding:8px 10px;
            font-size:14px; color:#1f1b24; }
QLineEdit:focus { border-color:#1f1b24; }
QPushButton#go { background:#1f1b24; color:#ffffff; border:none; border-radius:10px;
                 padding:10px 22px; font-size:14px; font-weight:600; }
QPushButton#go:hover { background:#3a3344; }
QPushButton#go:focus { outline:none; border:3px solid #b8740a; }
"""


class Picker(QDialog):
    def __init__(self, kitty="noir", name=""):
        super().__init__(None, Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("Meet your PurrSum kitty")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(PICK_CSS)
        self.kitty = kitty
        self._typed = bool(name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Pick your kitty", objectName="title"))
        lay.addWidget(QLabel("They'll sit on your screen and add up numbers for you.", objectName="sub"))
        row = QHBoxLayout()
        row.setSpacing(12)
        self.group = QButtonGroup(self)
        for k in sprites.ORDER:
            b = QToolButton(objectName="kitty", checkable=True)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setIcon(QIcon(sprite_pixmap(k, 4)))
            b.setIconSize(QSize(sprites.W * 4, sprites.H * 4))
            b.setText(sprites.KITTIES[k]["label"])
            b.setAccessibleName(f"{sprites.KITTIES[k]['label']} kitty")
            b.setMinimumSize(118, 118)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(k == kitty)
            b.clicked.connect(lambda _=False, k=k: self._pick(k))
            self.group.addButton(b)
            row.addWidget(b)
        lay.addLayout(row)
        lay.addSpacing(6)
        lbl = QLabel("Name your kitty")
        lbl.setStyleSheet("font-weight:600;")
        lay.addWidget(lbl)
        self.name = QLineEdit(name or sprites.KITTIES[kitty]["default"])
        self.name.setMaxLength(24)
        self.name.setAccessibleName("Kitty name")
        self.name.textEdited.connect(lambda _: setattr(self, "_typed", True))
        lbl.setBuddy(self.name)
        self.name.returnPressed.connect(self.accept)
        lay.addWidget(self.name)
        lay.addSpacing(6)
        go = QPushButton("Let's go", objectName="go", clicked=self.accept)
        go.setDefault(True)
        go.setCursor(Qt.PointingHandCursor)
        lay.addWidget(go, 0, Qt.AlignRight)
        self.name.selectAll()
        self.name.setFocus()

    def _pick(self, k):
        self.kitty = k
        if not self._typed:
            self.name.setText(sprites.KITTIES[k]["default"])

    def result_name(self):
        return self.name.text().strip() or sprites.KITTIES[self.kitty]["default"]


# ---------------------------------------------------------------- app controller
class OcrSignals(QObject):
    finished = Signal(list, int)
    failed = Signal(str)


class PurrSum(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.s = Settings()
        self.cat = Cat(self.s)
        self.bubble = Bubble()
        self.sel = None
        self.sig = OcrSignals()
        self.sig.finished.connect(self._ocr_done)
        self.sig.failed.connect(self._ocr_failed)
        self.cat.clicked.connect(lambda: self.start_sum())
        self.cat.moved.connect(lambda: self.bubble.follow(self.cat.anchor()))
        self.cat.menu_requested.connect(self.show_menu)
        self.reader = Reader()          # loads the OCR engine in the background

    @property
    def name(self):
        return self.s.get("name") or sprites.KITTIES[self.cat.kitty]["default"]

    def run(self):
        if "kitty" not in self.s:
            if not self.choose_kitty(first=True):
                return False
        self.cat.set_kitty(self.s["kitty"])
        self.cat.place_saved()
        self.cat.show()
        if self.s.get("tucked"):
            self.cat.tuck()
        return True

    def choose_kitty(self, first=False):
        d = Picker(self.s.get("kitty", "noir"), self.s.get("name", ""))
        ok = d.exec() == QDialog.Accepted
        if ok or first:
            self.s["kitty"] = d.kitty
            self.s["name"] = d.result_name()
            self.s.save()
            self.cat.set_kitty(d.kitty)
            self.cat.happy_hop()
        return True

    def show_menu(self, gp: QPoint):
        m = QMenu()
        m.setStyleSheet("QMenu{background:#1c1a22;color:#f4f1ea;border:1px solid #3a3644;padding:4px;}"
                        "QMenu::item{padding:6px 18px;border-radius:6px;}"
                        "QMenu::item:selected{background:#3a3344;}"
                        "QMenu::separator{height:1px;background:#3a3644;margin:4px 8px;}")
        m.addAction(QAction("Sum numbers", m, triggered=lambda *_: self.start_sum()))
        if self.cat.tucked:
            m.addAction(QAction(f"Bring {self.name} back", m, triggered=lambda *_: self._untuck()))
        else:
            m.addAction(QAction("Tuck into the side", m, triggered=lambda *_: self._tuck()))
        m.addAction(QAction("Change kitty…", m, triggered=lambda *_: self.choose_kitty()))
        m.addSeparator()
        m.addAction(QAction("Quit", m, triggered=lambda *_: self.app.quit()))
        m.exec(gp)

    def _tuck(self):
        self.bubble.hide()
        self.cat.tuck()
        self.s["tucked"] = True
        self.s.save()

    def _untuck(self):
        self.cat.untuck()
        self.s["tucked"] = False
        self.s.save()

    def summon(self):
        self.cat.summon()
        self.s["tucked"] = False
        self.s.save()

    # summing
    def start_sum(self):
        if self.sel is not None:
            return
        self.bubble.hide()
        self.cat.hide()
        QTimer.singleShot(120, self._begin_selection)   # let the cat vanish before the screenshot

    def _begin_selection(self):
        self.sel = Selection()
        self.sel.done.connect(self._selected)
        self.sel.cancelled.connect(self._sel_cancelled)
        self.sel.begin()

    def _sel_cancelled(self):
        self.sel = None
        self.cat.show()

    def _selected(self, crops):
        self.sel = None
        self.cat.show()
        self.cat.busy = True
        self.bubble.show_busy(self.name)
        self.bubble.show()
        self.bubble.follow(self.cat.anchor())
        imgs = [qimage_to_pil(img) for _, img in crops]
        threading.Thread(target=self._ocr, args=(imgs,), daemon=True).start()

    def _ocr(self, imgs):
        try:
            found = []
            for i, img in enumerate(imgs, 1):         # boxes in the order they were drawn
                lines = self.reader.read(img)
                found += [Found(v, t, i) for line in lines for v, t in find_numbers(line)]
            self.sig.finished.emit(found, len(imgs))
        except RuntimeError as e:
            if self.reader.engine is None:
                self.sig.failed.emit("My number-reading part isn't set up yet. Run the "
                                     "\u201cInstall PurrSum Noir\u201d file again while "
                                     "connected to the internet.")
            else:
                self.sig.failed.emit("Something went wrong reading the screen:\n" + str(e))
        except Exception as e:      # pragma: no cover
            self.sig.failed.emit("Something went wrong reading the screen:\n" + str(e))

    def _ocr_done(self, found, n):
        self.cat.busy = False
        self.bubble.show_result(self.name, found, n)
        self.bubble.follow(self.cat.anchor())
        if found:
            self.cat.happy_hop()

    def _ocr_failed(self, msg):
        self.cat.busy = False
        self.bubble.show_error(self.name, msg)
        self.bubble.follow(self.cat.anchor())


def qimage_to_pil(img: QImage):
    """Full-resolution (device pixel) crop as a PIL image."""
    from PIL import Image
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    return Image.frombuffer("RGB", (w, h), bytes(img.constBits())[: bpl * h], "raw", "RGB", bpl, 1).copy()


# ---------------------------------------------------------------- entry
def claim_single_instance():
    """Only one cat at a time. If one is already running, knock on its door and return None."""
    sock = QLocalSocket()
    sock.connectToServer(SERVER)
    if sock.waitForConnected(500):
        sock.write(b"summon")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()
        return None
    QLocalServer.removeServer(SERVER)
    server = QLocalServer()
    server.listen(SERVER)
    return server


def listen_for_summons(server, ps):
    def on_conn():
        # any knock on the door means "the icon was clicked again": call the cat back
        while server.hasPendingConnections():
            c = server.nextPendingConnection()
            c.disconnected.connect(c.deleteLater)
        ps.summon()
    server.newConnection.connect(on_conn)
    ps._server = server


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PurrSum.Noir")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    server = claim_single_instance()
    if server is None:
        return 0
    ps = PurrSum(app)
    listen_for_summons(server, ps)

    if not ps.run():
        return 0
    return app.exec()
