"""End-to-end run on two simulated monitors (1.5x laptop + 1.0x monitor).

Drives the real app with mouse/keyboard events and saves screenshots.
"""
import os, sys, time, tempfile, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "shots")
OUT.mkdir(exist_ok=True)
os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(ROOT / "app"))

from PySide6.QtCore import Qt, QPoint, QTimer, QRect
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap, QFont, QColor
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QDialog, QPushButton, QToolButton
from PySide6.QtTest import QTest
from purrsum import ui

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
laptop, mon2 = QGuiApplication.screens()
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name, detail)


def pump(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def compose(scr, include_overlays=False):
    g = scr.geometry(); d = scr.devicePixelRatio()
    pm = QPixmap(g.size() * d); pm.setDevicePixelRatio(d); pm.fill(QColor("#3b3b40"))
    p = QPainter(pm)
    order = lambda w: 0 if isinstance(w, Doc) else 2 if isinstance(w, ui.Overlay) else 1
    for w in sorted(QApplication.topLevelWidgets(), key=order):
        if not w.isVisible() or w.isWindow() is False:
            continue
        if isinstance(w, ui.Overlay):
            if not include_overlays or w.screen_ is not scr:
                continue
        if not w.geometry().intersects(g):
            continue
        p.drawPixmap(w.geometry().topLeft() - g.topLeft(), w.grab())
    p.end()
    return pm


LAST_CROPS = []
_orig_selected = ui.PurrSum._selected
def _spy(self, crops):
    LAST_CROPS[:] = crops
    return _orig_selected(self, crops)
ui.PurrSum._selected = _spy
ui.grab_screen = compose      # what the OS screenshot would return


def desktop(path):
    """Composite both monitors into one picture, like a photo of the desk."""
    g = QRect()
    for s in QGuiApplication.screens():
        g = g.united(s.geometry())
    img = QPixmap(g.size())
    img.fill(QColor("#555"))
    p = QPainter(img)
    for s in QGuiApplication.screens():
        p.drawPixmap(s.geometry(), compose(s, True))
    p.end()
    img.save(str(path))
    return img


# ---- "documents" open on each monitor
class Doc(QWidget):
    def __init__(self, screen, html, bg="#ffffff"):
        super().__init__(None, Qt.FramelessWindowHint)
        self.setStyleSheet(f"background:{bg};")
        self.lbl = QLabel(html, self)
        self.lbl.setStyleSheet("color:#222; font-family:'DejaVu Sans'; font-size:13px;")
        self.lbl.move(60, 50)
        self.setGeometry(screen.availableGeometry())
        self.show()


invoice = Doc(mon2, """
<div style='font-size:20px;font-weight:bold'>INVOICE</div>
<p>INV-24081 &nbsp;&nbsp;&nbsp; Date: 10/06/2026 &nbsp;&nbsp;&nbsp; PO#55</p>
<table cellspacing=0 cellpadding=7 style='font-size:13px'>
<tr style='background:#eee'><td width=170><b>Item</b></td><td width=60><b>Qty</b></td><td width=110><b>Size</b></td><td width=120 align=right><b>Amount</b></td></tr>
<tr><td>Steel plate</td><td>3</td><td>12*1800</td><td align=right>1641. 60</td></tr>
<tr><td>Anchor bolts</td><td>10</td><td>173.5*265</td><td align=right>$1,250.00</td></tr>
<tr><td>Handling</td><td>1</td><td></td><td align=right>45.00</td></tr>
<tr><td>Credit memo</td><td></td><td></td><td align=right>(75.25)</td></tr>
<tr><td>Adjustment</td><td></td><td></td><td align=right>300.00-</td></tr>
</table>""")
email = Doc(laptop, """
<div style='font-size:17px;font-weight:bold'>RE: Extra charges for shipment</div>
<p style='color:#666'>From: Accounts &lt;ap@example.com&gt;</p>
<p style='font-size:14px'>Hi Yoonah, there's one more line: freight surcharge $88.10 billed Oct 6, 2026 at 10:42 AM.</p>
<p style='font-size:14px'>Thanks!</p>""", bg="#fbfbfd")
pump(300)

# ---- first run: kitty picker
server = ui.claim_single_instance()
assert server is not None
ps = ui.PurrSum(app)
ui.listen_for_summons(server, ps)


def drive_picker():
    d = next(w for w in QApplication.topLevelWidgets() if isinstance(w, ui.Picker) and w.isVisible())
    d.grab().save(str(OUT / "1_picker_default.png"))
    btns = [b for b in d.findChildren(QToolButton) if b.objectName() == "kitty"]
    QTest.mouseClick(btns[2], Qt.LeftButton)              # gray tabby -> name follows
    pump(50)
    check("picker suggests a name per kitty", d.name.text() == "Pebble", d.name.text())
    QTest.mouseClick(btns[0], Qt.LeftButton)              # back to the black cat
    d.name.selectAll()
    QTest.keyClicks(d.name, "Mochi")
    pump(50)
    d.grab().save(str(OUT / "2_picker_named.png"))
    QTest.keyClick(d.name, Qt.Key_Return)


QTimer.singleShot(400, drive_picker)
ok = ps.run()
check("first-run picker shown and accepted", ok and ps.s.get("kitty") == "noir" and ps.s.get("name") == "Mochi", str(dict(ps.s)))
pump(300)
cat = ps.cat
a = laptop.availableGeometry()
check("cat starts bottom-right of main screen", cat.geometry().right() > a.right() - 120 and cat.geometry().bottom() > a.bottom() - 120, str(cat.geometry()))

# ---- drag the cat onto the second monitor
start = cat.mapToGlobal(QPoint(30, 40))
QTest.mousePress(cat, Qt.LeftButton, Qt.NoModifier, QPoint(30, 40))
target = QPoint(mon2.geometry().left() + 1100, mon2.geometry().top() + 330)
steps = 12
for i in range(1, steps + 1):
    gp = start + (target - start) * i / steps
    QTest.mouseMove(cat, cat.mapFromGlobal(gp))
    pump(10)
QTest.mouseRelease(cat, Qt.LeftButton, Qt.NoModifier, cat.mapFromGlobal(target))
pump(200)
check("cat dragged onto monitor 2", QGuiApplication.screenAt(cat.geometry().center()) is mon2, str(cat.geometry()))
check("position remembered", ps.s.get("x") == cat.x())
pump(600)
desktop(OUT / "3_desktop_cat.png")

# ---- click the cat -> dim screens, draw boxes
QTest.mouseClick(cat, Qt.LeftButton, Qt.NoModifier, QPoint(30, 40))
pump(500)
sel = ps.sel
check("clicking cat dims every monitor", sel is not None and len(sel.overlays) == 2)


def find_text_rect(doc, needle):
    """Where a cell of the invoice is on screen (rough, via the label's text layout)."""
    raise NotImplementedError


def overlay_for(gp):
    return next(o for o in sel.overlays if o.geometry().contains(gp))


def box(x1, y1, x2, y2, shift):
    p1, p2 = QPoint(x1, y1), QPoint(x2, y2)
    o = overlay_for(p1)
    mod = Qt.ShiftModifier if shift else Qt.NoModifier
    QTest.mousePress(o, Qt.LeftButton, mod, o.mapFromGlobal(p1))
    for i in range(1, 9):
        QTest.mouseMove(o, o.mapFromGlobal(p1 + (p2 - p1) * i / 8))
        pump(5)
    QTest.mouseRelease(o, Qt.LeftButton, mod, o.mapFromGlobal(p2))
    pump(80)


# locate invoice rows from the rendered label
lbl = invoice.lbl
ox = lbl.mapToGlobal(QPoint(0, 0))
inv_shot = invoice.grab().toImage()
print("invoice label at", ox, lbl.size())
ROW_H = None
# measure rows by scanning the Amount column for dark text
col_x1, col_x2 = ox.x() + 320, ox.x() + 520
ys = []
g = mon2.geometry()
for y in range(ox.y(), ox.y() + lbl.height()):
    dark = any(inv_shot.pixelColor(x - g.x(), y - g.y()).lightness() < 120 for x in range(col_x1, col_x2, 1))
    ys.append((y, dark))
bands, cur = [], None
for y, dark in ys:
    if dark and cur is None:
        cur = y
    if not dark and cur is not None:
        bands.append((cur, y))
        cur = None
print("text bands in Amount column:", bands)
# bands: header 'Amount', then 5 amounts
hdr, r1, r2, r3, r4, r5 = bands[:6]
size_x = ox.x() + 236

box(size_x, r1[0] - 6, col_x2, r2[1] + 6, shift=True)        # rows 1-2 incl. the Size column
box(col_x1, r4[0] - 6, col_x2, r5[1] + 6, shift=True)        # rows 4-5 (skip row 3)
pump(200)
desktop(OUT / "4_selecting.png")
# third box on the OTHER monitor (laptop email), released without Shift -> adds up
el = email.lbl.mapToGlobal(QPoint(0, 0))
eshot = email.grab().toImage()
d = eshot.devicePixelRatio()
ebands, cur = [], None
for y in range(el.y(), el.y() + email.lbl.height()):
    dark = any(eshot.pixelColor(int(x * d), int(y * d)).lightness() < 120 for x in range(el.x(), el.x() + 700, 2))
    if dark and cur is None:
        cur = y
    if not dark and cur is not None:
        ebands.append((cur, y)); cur = None
print("email bands:", ebands)
line = max(ebands, key=lambda b: b[1]-b[0] if b[0] > 100 and b[0] < 135 else 0)
box(el.x() - 4, line[0] - 6, el.x() + email.lbl.width() + 4, line[1] + 6, shift=False)
check("letting go without Shift adds up", ps.sel is None)

# ---- wait for local OCR
t0 = time.time()
while cat.busy and time.time() - t0 < 120:
    pump(100)
print(f"OCR took {time.time() - t0:.1f}s")
pump(300)
found = ps.bubble.found
print("found:", [(f.box, f.text, str(f.value)) for f in found])
vals = sorted(str(f.value) for f in found)
want = sorted(["1641.60", "1250.00", "-75.25", "-300.00", "88.10"])
check("reads the right numbers (gap decimal, negatives, ignores sizes/dates/times)", vals == want, str(vals))
clip = QGuiApplication.clipboard().text()
check("total copied without commas", clip == "2604.45", clip)
check("bubble shown next to cat", ps.bubble.isVisible() and QGuiApplication.screenAt(ps.bubble.geometry().center()) is mon2)
desktop(OUT / "5_result_desktop.png")
ps.bubble.grab().save(str(OUT / "6_bubble.png"))
for i, (r, img) in enumerate(LAST_CROPS, 1):
    img.save(str(OUT / f"crop{i}.png"))

# leave a number out
rows = [b for b in ps.bubble.findChildren(QPushButton) if b.objectName() == "row"]
neg = next(b for b in rows if b.f.value == -300)
QTest.mouseClick(neg, Qt.LeftButton)
pump(100)
check("clicking a number leaves it out", QGuiApplication.clipboard().text() == "2904.45", QGuiApplication.clipboard().text())
ps.bubble.grab().save(str(OUT / "7_bubble_excluded.png"))

# bubble follows the cat
before = ps.bubble.pos()
QTest.mousePress(cat, Qt.LeftButton, Qt.NoModifier, QPoint(30, 40))
g0 = cat.mapToGlobal(QPoint(30, 40))
for i in range(1, 6):
    QTest.mouseMove(cat, cat.mapFromGlobal(g0 + QPoint(0, i * 40)))
    pump(10)
QTest.mouseRelease(cat, Qt.LeftButton, Qt.NoModifier, cat.mapFromGlobal(g0 + QPoint(0, 200)))
pump(100)
check("bubble follows the cat", ps.bubble.pos().y() > before.y() + 100, f"{before} -> {ps.bubble.pos()}")
desktop(OUT / "8_after_move.png")

# ---- add more to the same list: bubble's Add button, then a typed number
def wait_ocr():
    t0 = time.time()
    while cat.busy and time.time() - t0 < 60:
        pump(100)
    pump(200)

QTest.mouseClick(ps.bubble.add_btn, Qt.LeftButton); pump(400)
check("Add button opens the dimmed screens to add more", ps.sel is not None and ps.appending)
sel = ps.sel
box(col_x1, r3[0] - 6, col_x2, r3[1] + 6, shift=False)       # the Handling row skipped earlier
wait_ocr()
f = ps.bubble.found
check("Add keeps the old list and adds the new box", len(f) == 6 and f[-1].box == 4 and str(f[-1].value) == "45.00",
      str([(x.box, x.text) for x in f]))
check("…and keeps what you left out", QGuiApplication.clipboard().text() == "2949.45", QGuiApplication.clipboard().text())
check("…and every earlier number is still visible in the bubble",
      ps.bubble.scroll.viewport().height() >= ps.bubble.list.sizeHint().height() - 2,
      f"{ps.bubble.scroll.viewport().height()} vs {ps.bubble.list.sizeHint().height()}")
QTest.mouseClick(ps.bubble.entry, Qt.LeftButton)
QTest.keyClicks(ps.bubble.entry, "(50.55)")
QTest.keyClick(ps.bubble.entry, Qt.Key_Return); pump(150)
check("typing a number adds it (with the invoice rules)", len(ps.bubble.found) == 7 and ps.bubble.found[-1].box == 0
      and QGuiApplication.clipboard().text() == "2898.90", QGuiApplication.clipboard().text())
QTest.keyClicks(ps.bubble.entry, "hello")
QTest.keyClick(ps.bubble.entry, Qt.Key_Return); pump(100)
check("typing something that isn't a number is gently refused", len(ps.bubble.found) == 7 and "number" in ps.bubble.hint.text())
ps.bubble.entry.clear(); pump(50)
ps.bubble.grab().save(str(OUT / "7b_bubble_added.png"))
desktop(OUT / "8b_added_desktop.png")

# ---- Esc cancels / right-click cancels
ps.start_sum(); pump(400)
QTest.keyClick(ps.sel.overlays[0], Qt.Key_Escape); pump(100)
check("Esc cancels and the list comes back unchanged", ps.sel is None and cat.isVisible()
      and ps.bubble.isVisible() and len(ps.bubble.found) == 7)
ps.start_sum(); pump(400)
o = ps.sel.overlays[1]
QTest.mouseClick(o, Qt.RightButton, Qt.NoModifier, QPoint(100, 100)); pump(100)
check("right-click cancels", ps.sel is None and cat.isVisible())
# Enter adds up after Shift boxes
ps.start_sum(); pump(400)
sel = ps.sel
box(col_x1, r3[0] - 6, col_x2, r3[1] + 6, shift=True)
check("Shift keeps the box and waits", ps.sel is sel and len(sel.rects) == 1)
QTest.keyClick(sel.overlays[1], Qt.Key_Return); pump(100)
t0 = time.time()
while cat.busy and time.time() - t0 < 60:
    pump(100)
check("Enter adds up", QGuiApplication.clipboard().text() == "45.00", QGuiApplication.clipboard().text())
check("clicking the cat starts a fresh list", len(ps.bubble.found) == 1, str(len(ps.bubble.found)))

# ---- tuck into the side
ps._tuck(); pump(300)
r = cat.geometry(); ag = mon2.availableGeometry()
check("tucks into the screen edge as a paw tab", cat.tucked and (r.right() == ag.right() or r.left() == ag.left()), str(r))
desktop(OUT / "9_tucked.png")
cat.grab().save(str(OUT / "10_paw.png"))

# ---- second launch just calls the cat back
env = dict(os.environ)
p = subprocess.run([sys.executable, str(ROOT / "app" / "purrsum.pyw")], env=env, timeout=30,
                   capture_output=True, text=True, stdin=subprocess.DEVNULL) if False else None
proc = subprocess.Popen([sys.executable, str(ROOT / "app" / "purrsum.pyw")], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
t0 = time.time()
while proc.poll() is None and time.time() - t0 < 20:
    pump(50)
pump(400)
check("second launch exits right away (one cat only)", proc.poll() == 0, f"rc={proc.poll()} {proc.stdout.read()[-600:] if proc.poll() is not None else ''}")
check("…and calls the cat back", not cat.tucked and cat.isVisible())

# ---- change kitty from the menu
def drive_picker2():
    d = next(w for w in QApplication.topLevelWidgets() if isinstance(w, ui.Picker) and w.isVisible())
    btns = [b for b in d.findChildren(QToolButton) if b.objectName() == "kitty"]
    QTest.mouseClick(btns[3], Qt.LeftButton)
    QTest.keyClick(d.name, Qt.Key_Return)
QTimer.singleShot(300, drive_picker2)
ps.choose_kitty()
check("changing buddy fills in the new buddy's name", ps.s["kitty"] == "mango" and ps.s["name"] == "Mango", str(dict(ps.s)))
pump(300)
cat.grab().save(str(OUT / "11_mango.png"))
ps.s["kitty"] = "noir"; cat.set_kitty("noir")

bad = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} checks passed")
sys.exit(1 if bad else 0)
