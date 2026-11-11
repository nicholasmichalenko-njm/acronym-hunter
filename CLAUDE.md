# Stationkeeper: read this first

Stationkeeper (formerly Acronym Hunter) is an offline Windows desktop app (Python, PySide6) for proposal efforts: reading
the customer's documents, the compliance matrix, assignments, the response structure, production standards and Word
templates, and checks. One person builds it, with Claude. Keep this file under two pages; it points, it doesn't repeat.

## House rules (the development rules; "Rule N" means the app's production rules, a different list)
1. **Offline only.** No code that reaches a network. The engine module blocks sockets at start; `tools/network_audit.py`
   checks every shipped binary. The OCR runs in a no-network sandbox.
2. **No generative AI** in the app (removed in 2.55). Rules, lists and trained readers only.
3. **No Chinese-derived components in US editions.** RapidOCR/PaddleOCR exist only for the legacy edition; the build's
   leak check refuses them in US builds. A new package needs its origin and license checked first.
4. **No real proposal data** in the repository, tests, fixtures or any Claude session. Fixtures are fictional
   (the Kestrel set in `test_samples/`). No team, customer, program or employer names in code or docs that ship.
5. **Nothing ships but the approved files.** No sample or demo content (`test_no_demo`), no team data in git
   (`test_data_guard`). Only README.txt, OVERVIEW.md and SECURITY.md ship as documents.
6. **Plain words in the UI.** Say what a thing does in the user's words. No emoji.
7. **A failing test stops the release.** `tools/run_tests.py` runs every `tests/test_*.py` and `tests/qt_*.py`.
   `test_house_rules` checks rules 1, 3 and 6 (network imports, approved packages in `tools/approved_packages.csv`, emoji);
   `test_golden` opens every saved set in `tests/golden/`; `test_formats` holds every saved file to `formats.py`;
   `test_file_sizes` keeps files under 800 lines (or 5% past `tools/size_baseline.json`); the build stops when reading
   drops below `tools/eval_floor.json`.
8. **Fewer controls per screen** (3.74.0, `claude/stationkeeper-simplify-decisions-2026-11-06.md`). One job and one main
   button per screen; at most five commands in a bar (`skqt/commandbar.py`), the rest in one More menu, every export in
   one Export menu; act on the row; one editor at a time; link to another screen only with the selection or as the next
   step; one home per function; rare tools by role; an empty screen shows one way in. `qt_screenrules` holds every bar to
   five and every screen to its count in `tools/screen_baseline.json` (lower it when a screen loses controls).

## Words we use
- **Company Standards (Default)**: the formatting for every effort (was "global standards"; never "team standard"); its
  values live in the team library's Company Standards.xlsx (4.7.0). **Effort Formatting**: one effort's own.
- **Rule N**: the production rules (Rules page, `rulebook.py`; check codes RU1 to RU8). **house rules**: this file's list.
- **effort**, **volume**, **section**, **response structure**, **Used on** (a style's family, set by the user, never
  guessed from its name).

## Where things are
- Core logic: top-level modules (`compliance.py`, `setupdoc.py`, `prodrules.py`, `prodfix.py`, `templatelib.py`, ...).
- Qt pages: `skqt/` (one module per page; `mainwin.py` holds the menu). Entry: `skqt_main.py`.
- Word engine: `prodengine/`. The engine core is still named `app_gui.py` (from the retired Classic window).
- Tests: `tests/` (offscreen Qt; standard library checks, no pytest). Build: `build.ps1`, `Stationkeeper.spec`.
- Big files to split when a feature touches them, never all at once: `skqt/assign.py`, `app_gui.py`,
  `skqt/prodstdpage.py`, `skqt/homepage.py`, `compliance.py`, `skqt/custdocs.py`.

## How a release runs
1. One worktree and branch per release (`/home/claude/ahNNNN`, `dev-X.Y.Z`). No more than two releases in flight, or three
   when each builds on the one before (2026-11-11).
2. Commit at each finished step. Run the suite:
   `QT_QPA_PLATFORM=offscreen AH_TEST=1 python tools/run_tests.py` (one test: add its name).
3. Merge `origin/main` before the PC build. On the PC: notes in `_local_sandbox\notes_X.Y.Z.md`,
   `mkscripts.ps1 -N NNNN -D X.Y.Z`, then `buildNNNN.cmd` (stops on any failure), `verifyNNNN.cmd`, `pubNNNN.cmd`.
4. After publishing: check the release's SHA-256 values against the committed checksum files, write the project's
   release notes (`claude/release-notes-X.Y.Z-<slug>.md`), revise the architecture map, update `claude/stationkeeper-now.md`.
5. Once per minor version: `python tools/make_golden.py X.Y` saves that version's golden set. A saved file's format
   changes only with a new number in `formats.py`, the step that reads the old one, and a golden set.

## Read next
- `DECISIONS.md`: settled decisions, one line each. Don't reopen one without a new reason.
- Project docs: `claude/stationkeeper-now.md` (what's in flight), `claude/stationkeeper-production-rules.md`,
  `claude/stationkeeper-architecture-map.html`, the latest plan for the release at hand.
