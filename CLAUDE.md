# PurrSum Noir — project guide

A tiny floating pixel cat for Windows that adds up numbers anywhere on screen.
Click the cat → every monitor dims → drag box(es) (Shift = more boxes, Enter/release = add up,
Esc/right-click = cancel) → local OCR → bubble with total + numbers (click one to leave it out),
total copied to clipboard without commas. Bubble footer: type a number + Enter (uses the
same invoice rules, badge ✎, box 0) or "+ Add more from screen" (append mode: keeps the list,
new boxes continue the numbering). A quick tap of Shift on its own while the bubble is open is the
power-user shortcut for that same "Add more" (`ShiftTap` + `PurrSum._poll_shift`, Windows key
polling; Shift used with another key/click, held > 0.6 s, or already held when the bubble opened
never counts). Also in the right-click menu once there's a list; the bubble shows "Shortcut: tap
Shift" under the button. Any click on the cat always starts a fresh list; cancelling a
selection brings the previous bubble back unchanged. Right-click cat: Sum numbers / Tuck into the side /
Change kitty… / Quit. First run: pick a buddy (Noir, Snowball, Pebble, Mango, DooBoo, Beans, Bunny, or
"+ My Pet") and name it. The installer launches the app with --welcome, which always opens the
picker first (current buddy pre-selected); there's no finish-page "run" checkbox. Bubble rows show muted row numbers 1..N (for matching the document) with a
faint divider where each box starts; left-out rows keep their number.

Owner: Yoonah (designer, non-developer). Keep changes small, explain in plain words.

## Layout
- `app/purrsum.pyw` — entry (pythonw-safe logging to %APPDATA%\PurrSum Noir\log.txt)
- `app/purrsum/ui.py` — everything visual (PySide6): `Cat`, `Selection` + `Overlay` (dimmed
  screens), `Bubble`, `Picker`, `PurrSum` controller, single-instance (`claim_single_instance`).
  Windows-only: Enter/Esc/Shift also read via GetAsyncKeyState in `Selection._poll_keys`.
- `app/purrsum/numparse.py` — the invoice number rules. NEVER rename back to `numbers.py`
  (it shadows Python's stdlib `numbers` and breaks numpy).
- `app/purrsum/ocr.py` — RapidOCR (ONNX) tuned for screen text: forced detection, det limit
  "max" 960, 2x upscale for small crops, no angle classifier.
- `app/purrsum/sprites.py` — built-in buddies as character grids: cat template (noir, snow,
  pebble, mango), pups dooboo (golden/floppy/collar) and smokey (grey-white, shown as "Beans"; old "Smokey" names migrate) — original art, NOT copies, NO costumes;
  tails drawn as a curled path via with_tail(); bunny; paw tab. Noir is the default. Pepper removed for now. Shadow is centred under SEAT (body columns,
  tail ignored); user pets use pets.seat_of() = widest run in the bottom rows.
  Picking a buddy always fills the name field with its name. Rows added to an open bubble must be
  .show()n before measuring (else the list collapses — the v1.2 "list disappears after Add" bug).
- `app/purrsum/pets.py` — every character by id ("noir" or "pet:<id>"): frames, names, paw-tab
  colours; user pets stored as two 1px-per-cell PNGs + JSON in %APPDATA%\PurrSum Noir\pets.
- `app/purrsum/petmaker.py` — image → sprite with no AI: background removed (edge-connected
  only, so white pets survive), crop, native pixel-grid detection or 22-row block resample,
  ≤16 colours, dark outline; photos → GrabCut mosaic after the user boxes the pet. Also the
  copyable pixel-pet PROMPT and the blink (eye_region / blink_frame).
- `app/purrsum/petui.py` — "+ My Pet" dialog: choose → (box) → tap eyes (mouse or arrows+Space)
  → live preview → name → save.
- `app/purrsum/setup_engine.py` + `engine_files.json` — the installer downloads the OCR engine
  (numpy 1.26.4, opencv-headless 4.11, onnxruntime 1.30, pillow, rapidocr_onnxruntime 1.2.3)
  from PyPI with pinned SHA-256s. Keep numpy 1.26.x (numpy 2 hangs under Wine testing).
- `tests/test_numbers.py` — parser rules (fast; run after any numparse change).
- `tests/test_ocr_fixtures.py` — real screenshots that once read wrong (e.g. "8, 764.46" comma gap); add new ones to `tests/fixtures/`.
- `tests/test_pets.py` — picker, My Pet (pixel picture, photo, bad file), blink, remove, row numbers.
  Run: `QT_QPA_PLATFORM=offscreen python3 tests/test_pets.py pet_shots` (needs scikit-image for the sample photo).
- `tests/e2e.py` — full app on two simulated monitors (Qt offscreen; needs a screens.json
  config, see the docstring/env in the run command below). Slower; run before releases.
- `build/` — `build.sh` (rebuild installer), `installer.nsi`, `prune.py`, `welcome.bmp`,
  `purrsum.ico`.
- `website/` — landing page source (Claude Design canvas files). `website/netlify/` = the standalone
  copy (plain HTML + small script for the hamburger menu and demo) for Netlify project "purrsum-noir"
  (purrsum-noir.netlify.app). That copy is also on the GitHub `site` branch; the installer is on the
  `downloads` branch (raw link used by every Download button).

## Commands
- Parser tests: `python3 tests/test_numbers.py`
- E2E: `QT_QPA_PLATFORM="offscreen:configfile=tests/screens.json" python3 tests/e2e.py shots`
  (tests/screens.json = a 1.5x laptop + a 1.0x monitor).
- Run the app from source: `pip install PySide6-Essentials rapidocr_onnxruntime` then
  `python app/purrsum.pyw`
- Installer: `cd build && ./build.sh` (Linux with nsis). Output ~22 MB.

## Saving versions (do this for every release)
GitHub branches: `main` = source code (this folder), `downloads` = installers
(`Install PurrSum Noir.exe` at the top = what the website serves, plus `versions/vX.Y.Z/`),
`site` = standalone website copy. (`claude/new-session-t70a5r` is an older, separate experiment
that swapped in `purrsum_reader.py`; it is NOT what ships.)
1. Bump `VERSION` in `build/installer.nsi`, add a CHANGELOG.md entry (newest first, plain words).
2. Run all tests (numbers, OCR fixtures, pets, e2e), then `cd build && ./build.sh`.
3. `downloads` branch: replace the top-level installer AND add `versions/vX.Y.Z/Install PurrSum Noir.exe`.
4. `main` branch: commit the source, then push tag `vX.Y.Z` → `.github/workflows/release.yml`
   publishes the GitHub Release (notes from CHANGELOG + that version's installer).
5. Website changes only when the page's words/design change (canvas "Send to Netlify" creates a
   NEW Netlify site each time: rename it to `purrsum-noir` and the old one to `purrsum-noir-previous`,
   and set visitor access so the live site needs no login).

## Known gaps / next ideas
- Installer is unsigned → SmartScreen warning. Plan: Microsoft Store (MSIX) for public release.
- No Mac build yet.
- Not yet verified on a real dual-monitor Windows PC with mixed scaling.
- Option: Windows built-in OCR instead of the 90 MB engine (installer ~25 MB, no download). Needs real-PC testing.
- Don't bundle character costumes (e.g. Disney) — users can add their own via My Pet.
