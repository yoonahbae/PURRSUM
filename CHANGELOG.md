# Changelog

Every released version of PurrSum Noir, newest first.
Installers for each version: `versions/vX.Y.Z/` on the `downloads` branch (and on the GitHub Releases page).

## 1.8.2 (2026-10-07)
- Fixed: numbers in typewriter-style reports with a gap after the thousands comma
  (e.g. `8, 764.46`) now read as one amount instead of two. Only joined when the
  number ends in cents, so real lists like `3, 120 boxes` still read as two numbers.
- Added a real-screenshot test so this can't come back.

## 1.8.1 (2026-10-07)
- New: tap **Shift** on its own while the bubble is open to "Add more from screen".
  Shift used for capitals, Shift+click in Excel, or a held Shift never triggers it.
- The bubble shows "Shortcut: tap Shift" under the Add button; also in the right-click menu.
- Clicking the cat always starts a fresh list (Shift+click from 1.8.0 removed).

## 1.8.0 (2026-10-07)
- New: Shift+click the cat as a shortcut for "Add more" (replaced in 1.8.1).

## 1.7.0 (2026-10-06)
- The buddy picker opens right after installing, so you choose your cat first.
- DooBoo's tucked-away paw is brown so it's easy to see.
- Shadows centred under each buddy; "Smokey" renamed **Beans**; Noir is the default.

## Earlier (1.0 – 1.6, 2026-10-06)
- 1.0: floating pixel cat, dim-all-screens box selection (Shift for more boxes),
  local OCR, total copied without commas, click a number to leave it out, tuck into the side,
  invoice rules (`1641. 60`, `(75.25)`, `300.00-`, skips dates/codes/sizes), one-file installer.
- Then: buddy picker and naming; "+ Add more from screen" and typed numbers; muted row numbers
  with dividers between boxes; built-in buddies (Snowball, Pebble, Mango, DooBoo, Beans, Bunny)
  and "+ My Pet" from your own picture; curled tails.
