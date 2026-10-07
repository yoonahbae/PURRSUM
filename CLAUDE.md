# PurrSum Noir — project guide

A tiny floating pixel cat for Windows that adds up numbers anywhere on screen.
Click the cat → every monitor dims → drag box(es) (Shift = more boxes, Enter/release = add up,
Esc/right-click = cancel) → local OCR → bubble with total + numbers (click one to leave it out),
total copied to clipboard without commas. Right-click cat: Sum numbers / Tuck into the side /
Change kitty… / Quit. First run: pick one of 4 kitties and name it.

Owner: Yoonah (designer, non-developer). Keep changes small, explain in plain words.

## Layout
- `app/purrsum.pyw` — entry (pythonw-safe logging to %APPDATA%\PurrSum Noir\log.txt)
- `app/purrsum/ui.py` — everything visual (PySide6): `Cat`, `Selection` + `Overlay` (dimmed
  screens), `Bubble`, `Picker`, `PurrSum` controller, single-instance (`claim_single_instance`).
  Windows-only: Enter/Esc/Shift also read via GetAsyncKeyState in `Selection._poll_keys`.
- `app/purrsum/purrsum_reader.py` — the reading engine from the original PurrSum (RapidOCR + invoice
  number rules: `Reader`, `find_numbers`, `decimals_in`, `fmt`). Replaced Noir's own ocr.py/numparse.py.
  Run `python app/purrsum/purrsum_reader.py` — it must print "reader ok". Keep it identical to the
  copy at the repo root.
- `app/purrsum/sprites.py` — pixel-art kitties as character grids (noir, snow, pebble, mango)
  and the paw tab.
- `app/purrsum/setup_engine.py` + `engine_files.json` — the installer downloads the OCR engine
  (numpy 1.26.4, opencv-headless 4.11, onnxruntime 1.30, pillow, rapidocr_onnxruntime 1.2.3)
  from PyPI with pinned SHA-256s. Keep numpy 1.26.x (numpy 2 hangs under Wine testing).
- `tests/test_numbers.py` — parser rules (prints NOTE for old Noir rules the reader doesn't cover) (fast; run after any numparse change).
- `tests/e2e.py` — full app on two simulated monitors (Qt offscreen; needs a screens.json
  config, see the docstring/env in the run command below). Slower; run before releases.
- `build/` — `build.sh` (rebuild installer), `installer.nsi`, `prune.py`, `welcome.bmp`,
  `purrsum.ico`.
- `website/` — landing page source (Claude Design canvas files).

## Commands
- Parser tests: `python3 tests/test_numbers.py`
- E2E: `QT_QPA_PLATFORM="offscreen:configfile=tests/screens.json" python3 tests/e2e.py shots`
  (tests/screens.json = a 1.5x laptop + a 1.0x monitor).
- Run the app from source: `pip install PySide6-Essentials rapidocr_onnxruntime` then
  `python app/purrsum.pyw`
- Installer: `cd build && ./build.sh` (Linux with nsis). Output ~22 MB.

## Known gaps / next ideas
- Installer is unsigned → SmartScreen warning. Plan: Microsoft Store (MSIX) for public release.
- No Mac build yet.
- Not yet verified on a real dual-monitor Windows PC with mixed scaling.
