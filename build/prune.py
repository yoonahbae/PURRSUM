"""Trim the bundled Windows Python down to what PurrSum Noir actually uses."""
import pathlib, shutil, sys

py = pathlib.Path(sys.argv[1])
sp = py / "Lib" / "site-packages"
ps = sp / "PySide6"

KEEP_QT = {"Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Network.dll", "Qt6Svg.dll"}
KEEP_PYD = {"QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd", "QtNetwork.pyd"}
KEEP_MISC = {"__init__.py", "_config.py", "_git_pyside_version.py", "concrt140.dll",
             "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "msvcp140_codecvt_ids.dll",
             "pyside6.abi3.dll", "plugins", "support", "py.typed"}
KEEP_PLUGINS = {"platforms", "styles", "imageformats", "iconengines"}


def rm(p):
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()


for f in ps.iterdir():
    if f.name in KEEP_QT or f.name in KEEP_PYD or f.name in KEEP_MISC:
        continue
    rm(f)
for f in (ps / "plugins").iterdir():
    if f.name not in KEEP_PLUGINS:
        rm(f)
for f in (ps / "plugins" / "imageformats").iterdir():
    if not f.name.startswith(("qico", "qsvg")):
        rm(f)
for f in (ps / "plugins" / "platforms").iterdir():
    if f.name != "qwindows.dll":
        rm(f)

# python stdlib extras nobody needs here
for name in ["tcl", "include", "libs", "Lib/test", "Lib/idlelib", "Lib/tkinter", "Lib/turtledemo",
             "Lib/ensurepip", "Lib/lib2to3", "DLLs/_tkinter.pyd", "DLLs/tcl86t.dll", "DLLs/tk86t.dll",
             "Lib/site-packages/shiboken6_generator"]:
    rm(py / name)
for p in list(sp.glob("**/tests")):
    if "numpy" in str(p) or "shapely" in str(p):
        rm(p)
for p in sp.glob("**/*.pyi"):
    rm(p)
for p in py.glob("**/__pycache__"):
    rm(p)
print("pruned")
