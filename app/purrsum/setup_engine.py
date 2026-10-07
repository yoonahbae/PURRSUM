"""Download and unpack the number-reading engine (run once by the installer).

Downloads pinned packages from the official Python package index (PyPI),
checks every file's SHA-256 fingerprint, and unpacks them next to Python.
Nothing about the user is sent anywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.request
import zipfile

# don't let this folder's own modules shadow Python's
if sys.path and os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
    sys.path.pop(0)

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = ("opencv_videoio_ffmpeg", "/tests/", "cv2/data/")


def site_packages() -> str:
    return os.path.join(sys.prefix, "Lib", "site-packages")


def say(msg: str):
    print(msg, flush=True)


def fetch(url: str, dest: str, size: int, label: str):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
                got, last = 0, -1
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    pct = got * 100 // max(size, 1)
                    if pct // 25 != last:
                        last = pct // 25
                        say(f"  {label}: {min(pct, 100)}%")
            return
        except Exception as e:  # network hiccup: try again
            if attempt == 3:
                raise
            say(f"  {label}: retrying ({e.__class__.__name__})")
            time.sleep(2 + attempt * 3)


def install():
    sp = site_packages()
    files = json.load(open(os.path.join(HERE, "engine_files.json"), encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        for i, item in enumerate(files, 1):
            label = f"Reading engine part {i} of {len(files)} ({item['name']})"
            say(f"Downloading {label}...")
            dest = os.path.join(tmp, item["file"])
            fetch(item["url"], dest, item["size"], label)
            h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
            if h != item["sha256"]:
                raise RuntimeError(f"{item['file']} did not match its fingerprint")
            with zipfile.ZipFile(dest) as z:
                for n in z.namelist():
                    if any(s in n for s in SKIP):
                        continue
                    z.extract(n, sp)
            os.remove(dest)
    say("Checking the reading engine...")
    sys.path.insert(0, os.path.dirname(HERE))
    from purrsum import ocr  # noqa: E402
    ocr.engine()
    say("Reading engine ready.")


def installed() -> bool:
    sp = site_packages()
    return all(os.path.isdir(os.path.join(sp, d)) for d in ("numpy", "cv2", "onnxruntime", "PIL", "rapidocr_onnxruntime"))


if __name__ == "__main__":
    if "--if-needed" in sys.argv and installed():
        say("Reading engine already set up.")
        sys.exit(0)
    try:
        install()
    except Exception as e:
        say(f"Could not set up the reading engine: {e}")
        sys.exit(1)
