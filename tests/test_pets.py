"""My Pet + picker + row numbers. Run with QT_QPA_PLATFORM=offscreen."""
import os, sys, tempfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "pet_shots")
OUT.mkdir(exist_ok=True)
os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(ROOT / "app"))

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QToolButton
from PySide6.QtTest import QTest
from purrsum import ui, pets, petmaker, numparse
from purrsum.petui import PetMaker

app = QApplication(sys.argv)
results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name, detail)


def pump(n=20):
    for _ in range(n):
        app.processEvents()


# a hand-made pixel bunny (not one of the built-ins), drawn 14x bigger on a beige
# background with a soft shadow — like an AI "pixel pet" picture would be
BUNNY = [
    "...KK...KK....",
    "..KWWK.KWWK...",
    "..KWPK.KWPK...",
    "..KWPK.KWPK...",
    "..KWWKKKWWK...",
    ".KWWWWWWWWWK..",
    ".KWWEWWWEWWK..",
    ".KWWEWWWEWWK..",
    ".KWWWWPWWWWK..",
    "..KWWWWWWWK...",
    "..KWWWWWWWKKK.",
    ".KWWWWWWWWKWWK",
    ".KWWWWWWWWKKK.",
    ".KWWKWWWKWWK..",
    ".KKKKKKKKKKK..",
]
COL = {"K": (40, 34, 38), "W": (236, 232, 226), "P": (240, 150, 170), "E": (30, 24, 28)}
S = 14
img = Image.new("RGB", (600, 520), (229, 218, 207))
d = ImageDraw.Draw(img)
d.ellipse((190, 400, 410, 430), fill=(205, 194, 184))         # soft shadow
for r, row in enumerate(BUNNY):
    for c, ch in enumerate(row):
        if ch in COL:
            d.rectangle((200 + c * S, 190 + r * S, 200 + c * S + S - 1, 190 + r * S + S - 1), fill=COL[ch])
bunny = OUT / "bunny_input.png"
img.save(bunny)

# ---- picker: six built-ins + "My Pet"
pk = ui.Picker("noir", "")
tiles = [b for b in pk.findChildren(QToolButton) if b.objectName() == "kitty"]
check("picker shows the seven built-in buddies", [b.text() for b in tiles] ==
      ["Noir", "Snowball", "Pebble", "Mango", "DooBoo", "Beans", "Bunny"],
      str([b.text() for b in tiles]))
check("…and a + My Pet tile", pk.add_tile.text() == "+ My Pet")
QTest.mouseClick(tiles[4], Qt.LeftButton); pump()
check("picking DooBoo suggests his name", pk.name.text() == "DooBoo")
pk.name.setText("Sir Fluff"); QTest.mouseClick(tiles[6], Qt.LeftButton); pump()
check("picking another buddy always fills in its name", pk.name.text() == "Bunny")
pk.show(); pump(); pk.grab().save(str(OUT / "1_picker.png")); pk.hide()

# ---- My Pet: a pixel picture goes straight to the eye step
mk = PetMaker()
mk.load(str(bunny)); pump()
check("pixel picture is recognised and skips the box step", mk.info["kind"] == "pixel" and mk.pages.currentIndex() == 2,
      str(mk.info))
g = mk.grid
check("sprite is chunky, kitty-sized and has a capped palette",
      12 <= len(g) <= 24 and len({c for row in g for c in row if c}) <= 17, f"{len(g)}x{len(g[0])}")
check("Save is off until eyes are tapped and a name is given", not mk.save_btn.isEnabled())
eye_hex = "#%02x%02x%02x" % COL["E"]
cells = [(r, c) for r, row in enumerate(g) for c, col in enumerate(row)
         if col and abs(ui.QColor(col).red() - COL["E"][0]) < 8 and abs(ui.QColor(col).green() - COL["E"][1]) < 8
         and 5 <= r <= 8]
eyes = []
for rc in cells:         # one cell from each eye (left and right)
    if all(abs(rc[1] - e[1]) > 2 for e in eyes):
        eyes.append(rc)
for rc in eyes[:2]:
    mk.eyes._toggle(rc)
QTest.keyClicks(mk.pet_name, "Mochi Bun"); pump()
check("two eye taps + a name enable Save", len(mk.eyes.eyes) == 2 and mk.save_btn.isEnabled(), str(mk.eyes.eyes))
closed = mk._closed()
check("blink frame closes the eyes", closed != g)
mk.show(); mk.resize(720, 620); pump(10); mk.grab().save(str(OUT / "2_mypet_eyes.png"))
QTest.mouseClick(mk.save_btn, Qt.LeftButton); pump()
check("pet saved", mk.saved_id and pets.exists("pet:" + mk.saved_id))
cid = "pet:" + mk.saved_id

# ---- it appears in the picker, can be chosen, drives the cat, and can be removed
pk = ui.Picker("noir", "")
labels = [b.text() for b in pk.findChildren(QToolButton) if b.objectName() == "kitty"]
check("your pet gets its own tile", labels[-1] == "Mochi Bun" and len(labels) == 8, str(labels))
pk.tiles[cid].click(); pump()
check("choosing it fills in its name", pk.kitty == cid and pk.name.text() == "Mochi Bun")
pk.show(); pump(); pk.grab().save(str(OUT / "3_picker_with_pet.png")); pk.hide()

cat = ui.Cat(ui.Settings())
cat.set_kitty(cid); cat.show(); pump()
check("the floating buddy uses your pet", cat.frames[0] == pets.frames(cid)[0] and cat.width() == len(g[0]) * ui.PX + 4)
cat.blink = True; cat.update(); pump(); cat.grab().save(str(OUT / "4_pet_blink.png"))
cat.blink = False; cat.update(); pump(); cat.grab().save(str(OUT / "4_pet_open.png"))
for k in ("dooboo", "smokey"):
    cat.set_kitty(k); pump(); cat.grab().save(str(OUT / f"5_{k}.png"))
cat.hide()

ui.QMessageBox.question = staticmethod(lambda *a, **k: ui.QMessageBox.Yes)   # answer "Yes"
pk._remove(cid, "Mochi Bun"); pump()
check("removing a pet takes its tile away", not pets.exists(cid) and cid not in pk.tiles)

# ---- a regular photo goes to the box step with an honest explanation
import skimage.data
photo = OUT / "photo_input.jpg"
Image.fromarray(skimage.data.chelsea()).save(photo)
mk2 = PetMaker()
mk2.load(str(photo)); pump()
check("a regular photo is spotted and asks for a box", mk2.info["kind"] == "photo" and mk2.pages.currentIndex() == 1
      and "photo" in mk2.box_title.text())
mk2.show(); mk2.resize(720, 620); pump(10); mk2.grab().save(str(OUT / "6_photo_box.png"))
mk2.box.sel = mk2.box._img_rect().adjusted(60, 10, -60, -10)
mk2._make(mk2.box.image_rect()); pump()
check("…and still makes a mosaic sprite from the box", mk2.pages.currentIndex() == 2 and mk2.grid is not None)
mk3 = PetMaker()
bad = OUT / "not_an_image.png"; bad.write_text("hello")
mk3.load(str(bad)); pump()
check("a file that isn't a picture gets a friendly message", mk3.start_msg.isVisible() or not mk3.start_msg.isHidden())

# ---- the shadow sits centred under each buddy's body (measured on the real rendering)
from purrsum import sprites
offs = {}
for k in sprites.ORDER:
    c = ui.Cat(ui.Settings()); c.set_kitty(k); c.hop = 0; c.bob = 0.0; c.show(); pump()
    img = c.grab().toImage()
    gh = len(c.frames[0]) * ui.PX
    y = 10 + gh                                   # a row through the shadow, below the paws
    xs = [x for x in range(img.width()) if img.pixelColor(x, y).alpha() > 20]
    a_, b_ = sprites.SEAT[sprites.KITTIES[k]["shape"]]
    body_mid = 2 + (a_ + b_ + 1) / 2 * ui.PX
    offs[k] = round((min(xs) + max(xs)) / 2 - body_mid, 1) if xs else None
    if k in ("noir", "dooboo"):
        c.grab().save(str(OUT / f"9_shadow_{k}.png"))
    c.hide()
check("shadows are centred under each body, not the tail", all(o is not None and abs(o) <= 1.5 for o in offs.values()), str(offs))
check("the pixel-pet prompt asks for a plain background and no shadow",
      "Plain solid light background" in petmaker.PROMPT and "no shadow" in petmaker.PROMPT)

# ---- right after installing, the buddy picker opens even if a buddy was already chosen
ps_s = ui.Settings(); ps_s.update({"kitty": "mango", "name": "Mango"}); ps_s.save()
shown = {}
def _close_picker():
    d = [w for w in QApplication.topLevelWidgets() if isinstance(w, ui.Picker) and w.isVisible()]
    shown["picker"] = bool(d)
    if d:
        shown["preselected"] = d[0].kitty
        d[0].accept()
QTimer.singleShot(300, _close_picker)
ctl = ui.PurrSum(app)
ctl.run(welcome=True); pump()
check("after install the buddy picker opens, with the current buddy pre-selected",
      shown.get("picker") and shown.get("preselected") == "mango", str(shown))
ctl.cat.hide()

# ---- a long running list stays fully visible after adding more
b0 = ui.Bubble()
b0.show_result("Noir", numparse.find_numbers("\n".join(f"{i}.00" for i in range(1, 8)), box=1))
b0.show(); pump()
b0.add_found(numparse.find_numbers("\n".join(f"{i}.50" for i in range(1, 6)), box=2)); pump(10)
check("after Add, all earlier numbers are still shown (no hidden rows)",
      len(b0.found) == 12 and b0.scroll.viewport().height() >= b0.list.sizeHint().height() - 2,
      f"{b0.scroll.viewport().height()} vs {b0.list.sizeHint().height()}")
b0.grab().save(str(OUT / "8_bubble_after_add.png")); b0.hide()

# ---- bubble: muted row numbers 1..N, a divider between boxes, typed rows too
b = ui.Bubble()
found = numparse.find_numbers("1641. 60\n$1,250.00", box=1) + numparse.find_numbers("(75.25)", box=2)
b.show_result("Noir", found)
b.add_found(numparse.find_numbers("45.00", box=0))
rows = [w for w in b.list.findChildren(ui.QPushButton) if w.objectName() == "row"]
nums = [w.findChild(ui.QLabel, "rownum").text() for w in rows]
divs = [w for w in b.list.findChildren(ui.QFrame) if w.objectName() == "divider"]
check("rows are numbered 1..N for matching the document", nums == ["1", "2", "3", "4"], str(nums))
check("a faint divider marks where each box starts", len(divs) == 2)
rows[2].click(); pump()
nums2 = [w.findChild(ui.QLabel, "rownum").text() for w in b.list.findChildren(ui.QPushButton) if w.objectName() == "row"]
check("leaving a number out keeps the numbering", nums2 == ["1", "2", "3", "4"] and app.clipboard().text() == "2936.60",
      app.clipboard().text())
b.show(); pump(); b.grab().save(str(OUT / "7_bubble_rows.png"))

# ---- a quick tap of Shift (bubble open) is the shortcut for "Add more from screen"
t = ui.ShiftTap()
def taps(seq):
    t.reset(); return [t.feed(sh, ot, tm) for sh, ot, tm in seq]
check("a quick Shift tap on its own counts",
      any(taps([(False, False, 0), (True, False, .05), (True, False, .1), (False, False, .2)])))
check("Shift used for a capital letter doesn't count",
      not any(taps([(False, False, 0), (True, False, .05), (True, True, .1), (False, False, .2)])))
check("Shift+click (e.g. selecting cells) doesn't count",
      not any(taps([(False, False, 0), (True, True, .05), (False, False, .15)])))
check("holding Shift a long time doesn't count",
      not any(taps([(False, False, 0), (True, False, .05), (False, False, 1.5)])))
check("a Shift still held from boxing doesn't count when released",
      not any(taps([(True, False, 0), (True, False, .1), (False, False, .2)])))
got = []
c2 = ui.Cat(ui.Settings()); c2.set_kitty("noir"); c2.show(); pump()
c2.clicked.connect(lambda: got.append("fresh"))
QTest.mouseClick(c2, Qt.LeftButton, Qt.ShiftModifier, c2.rect().center()); pump()
check("clicking the cat (even with Shift) starts a fresh list", got == ["fresh"], str(got))
c2.hide()
ctl2 = ui.PurrSum(app); ctl2.cat.set_kitty("noir"); ctl2.cat.show()
ctl2.bubble.show_result("Noir", numparse.find_numbers("10.00\n20.00", box=1)); ctl2.bubble.show(); pump()
keys = iter([(False, False), (True, False), (False, False)])
ctl2._read_keys = lambda: next(keys)
for _ in range(3): ctl2._poll_shift()
check("tapping Shift with the bubble open starts Add more (keeps the list)", ctl2.appending)
pump(); QTest.qWait(300); pump()
if ctl2.sel: ctl2.sel.cancel()
pump()
check("…and the bubble shows the shortcut under the Add button",
      ctl2.bubble.shortcut_tip.text() == "Shortcut: tap Shift" and "tap Shift" in ctl2.bubble.add_btn.toolTip())
ctl2.cat.hide(); ctl2.bubble.hide()

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
