# Acronym Hunter: Complete Overview

**Version:** 1.4.1 | **Updated:** 2026-10-20 | **Platform:** Windows 10/11, 64-bit

This document has two parts.
**Part 1** explains the whole application in plain language: what it is, what is inside it, how it works,
how to use it, how it improves over time, and why it is safe for sensitive documents.
**Part 2** is the full security assessment for IT and security teams, with the evidence behind every claim.

---

# Part 1: How Acronym Hunter Works

## 1. What it is, in one paragraph

Acronym Hunter is a desktop program that reads your documents and makes a list of every acronym
(SOW, CDR), abbreviation (approx., w/o), and unit of measure (psi, kWh) it finds. For each one it tells you
what it means (from a list you control), where it appears (page, slide, section, picture), and whether it
needs your attention, such as a term with two possible meanings or a new term it has never seen.
It runs entirely on your own computer. Nothing is sent anywhere.

## 2. A simple way to picture it

Think of the app as **a librarian who works in a locked room with no phone and no window.**

- You hand the librarian your documents through the door.
- The librarian reads every page, including the words inside pictures, using reading glasses kept in the room.
- The librarian checks each short form against a **notebook of known terms** that lives in the same room.
- The librarian hands you back a list. You can write corrections in the notebook so next time is better.
- When you are done, you can **throw away the whole room**. The librarian, the glasses, the notebook,
  and every scrap of paper go with it.

The "room" is the `AcronymHunter` folder. The "no phone" is the network block. The "reading glasses" are
the OCR models stored inside the folder. The "notebook" is `acronym_database.csv`.

## 3. What is in the folder

```
AcronymHunter\
  AcronymHunter.exe          The scanner: the program you double-click
  AcronymHunterTrainer.exe   The Trainer: re-read missed spots and save training samples
  acronym_database.csv       The notebook: known terms, definitions, Include/Exclude rules
  config\                    Accuracy settings you can tune
     ocr_corrections.csv       "This misread means that" list (RFF means RFP)
     ocr_settings.json         Picture-reading settings (sharpness, resolution)
     app_settings.json         Whether Advanced tools start on, and whether users may switch them
     models\                   Optional replacement reading models (empty by default)
  README.txt                 Quick start
  OVERVIEW.md, SECURITY.md   This document and the detailed security statement
  CHECKSUM.txt               Fingerprint to confirm the program was not altered
  _internal\                 The engine: Python, libraries, reading models (do not edit)
  _local_sandbox\            Scratch space (created when the app runs, emptied when it closes)
  logs\                      Error notes (created only if something goes wrong)
  training_data\             Training samples you save in the Trainer (created on first save)
```

**Two packages from one build:**
- `AcronymHunter_Portable.zip`: the scanner only. This is the one to share.
- `AcronymHunter_WithTrainer.zip`: scanner plus Trainer, for whoever curates OCR fixes and training samples.

Both programs share the same engine in `_internal\`, so the Trainer adds only about 8 MB. In the scanner-only
package the Region Trainer button is hidden.

Nothing is installed. Nothing is added to the Start menu, Program Files, or Windows settings.
Unzip it, run it, delete it.

## 4. How it reads a document, step by step

```
 Your file  ->  1. Unpack  ->  2. Read text  ->  3. Read pictures  ->  4. Match terms  ->  5. Show results
```

1. **Unpack.** Word, PowerPoint, and Excel files are really zip folders of text and pictures.
   The app opens them like a zip and looks at every part: body text, tables, headers, footers, footnotes,
   comments, slide notes, charts, SmartArt, and embedded pictures. PDFs are opened page by page.
2. **Read the typed text.** Typed text is read exactly, letter for letter. No guessing.
3. **Read the pictures (OCR).** For pictures, scanned pages, and photos, the app first cleans up the image
   (enlarges small images, boosts contrast, removes speckles), then uses a reading model to turn the picture
   into text. Large images are read in overlapping sections so small labels are not lost.
   This is the only step that can make reading mistakes.
4. **Match terms.** The app checks the text three ways:
   - **Excluded words** you told it to ignore are dropped.
   - **Known terms** from your database are matched and given their definitions.
     Terms with two meanings are flagged "CHOOSE DEFINITION".
   - **New patterns** that look like acronyms, units, or abbreviations but are not in the database are
     listed as "NEW CANDIDATE" for you to review.
5. **Show results.** A table lists each term, its type, how many times it appears, its status,
   its definition, and exactly where it was found.

## 5. The tools inside (and what each one does)

| Tool | What it does in plain terms | Made by |
|---|---|---|
| Python 3.11 | The language the app is written in; bundled, nothing to install | Python Software Foundation |
| PyMuPDF (MuPDF) | Opens PDFs and reads their text and pictures | Artifex |
| lxml | Reads the text inside Word, PowerPoint, and Excel files | lxml project |
| openpyxl | Reads Excel cell values | openpyxl project |
| OpenCV | Cleans up pictures before reading (contrast, sharpening, enlarging) | OpenCV.org |
| ONNX Runtime | Runs the reading models on your computer's processor | Microsoft |
| RapidOCR + PP-OCRv4 models | The "reading glasses": find and read text in pictures | RapidAI community; models from Baidu PaddleOCR |
| RapidFuzz | Spots near-misses like a misread letter | RapidFuzz project |
| CustomTkinter / Tk | Draws the window, buttons, and table | CustomTkinter project; Tcl/Tk |
| PyInstaller | Packs everything into one folder with an .exe (used only when building) | PyInstaller project |

All are open-source libraries. All run inside the app's own process. None of them contact the internet.

## 6. How to use it

1. **Open:** unzip the folder and double-click `AcronymHunter.exe`. (If the zip came by email or download,
   right-click it > Properties > Unblock first.)
2. **Scan:** click **Select Files** for specific files or **Scan Folder** for everything in a folder.
3. **Read the results:** use **Text size** (A- / A+) to make the table larger, click any **column header** to sort,
   and use the **Type**, **Status**, and **Search** filters to narrow the list.
4. **Act on each row:**
   - "CHOOSE DEFINITION": pick the right meaning and click **Apply Choice**.
   - "NEW CANDIDATE": type its definition and click **Include in DB**, or click **Exclude** if it is noise.
   - A misread from a picture (RFF instead of RFP): type the correct term and click **Fix OCR** (Advanced).
   - Something the scan missed entirely: click **+ Add Item**, fill in the term, type, definition, and where
     you saw it. It is marked "Added manually", included in the export, and kept through rescans. Tick
     "Also save to the database" so future scans find it automatically.
   - "Not scanned": content the app could not open (for example a linked picture); the row says why.
5. **Export:** click **Export CSV** to save the results report wherever you choose.

**Projects: use it all the way through a program.** A project remembers a folder of documents between scans.
- **Project > New Project...**: pick the folder that holds the documents. The app saves `<folder name>.ahproj`
  in that folder and scans everything once.
- **Rescan Project**: reads only files that are new or changed since the last scan and reuses saved results for
  the rest, so a rescan takes seconds. New files dropped into the folder are picked up automatically.
- The **Change** column marks every term **New**, **Changed** (count or locations moved), **Unchanged**, or
  **No longer found**. Status filters isolate each group. "No longer found" rows stay until you clear them
  (**Project > Clear "No longer found" items**), so nothing disappears silently.
- Definition choices and **+ Add Item** entries are saved in the project and reapplied after every rescan.
- **Full Rescan** reads every file again; use it after changing OCR settings or models (the app also does this
  on its own when the engine changes).
- **One editor at a time.** If a colleague has the project open, you can open it read-only (view and export)
  or take over once they are done.
- The project file holds **terms only**: file names, sizes, dates, the term-like tokens found, your choices, and
  history. Ordinary words are removed before saving, so no sentence can be rebuilt from it. It is no more
  sensitive than the exported CSV.

**Vector graphics.** SVG, EMF, and WMF files, and diagrams pasted into Word, PowerPoint, or Excel (Visio, draw.io,
Office SVG icons), are read in two ways. Text stored in the drawing is read directly, exactly and instantly. If the
labels were converted to outlines, the drawing is rendered as a high-resolution picture and read by OCR. The
location shows which method found each term: "(Vector text)" or "(Image)".

**Advanced tools.** The **Advanced** switch (top right) shows Fix OCR, OCR Fixes, and Region Trainer.
It is off by default so everyday users see a simpler screen. Whoever prepares the package can set the
default or lock the switch in `config\app_settings.json`:

| Setting | Effect |
|---|---|
| `"advanced_features_default": false` | Advanced tools start hidden (the user's own choice is remembered after that) |
| `"allow_advanced_toggle": false` | The switch is removed; the default above applies to everyone |

## 7. The Trainer: point at what was missed

`AcronymHunterTrainer.exe` (or the **Region Trainer** button in the scanner) is a second program for the
cases where the scanner missed something in a picture. It ships only in `AcronymHunter_WithTrainer.zip`.

1. **Open File** and pick the document or image. The left list shows every page (PDF) or embedded picture
   (PowerPoint, Word, Excel) with its slide or section.
2. **Drag a box** around the text that was missed. The right panel shows every line the reader saw in the
   box, with a confidence score. Red lines are ones the scanner throws away as too uncertain.
3. Each line carries a number (matching its box on the picture) and a color. **Green**: the scanner keeps this
   reading. **Red**: low confidence, the scanner already drops it.
4. Pick a choice for each line, then **Save Choices**:
   - **Save as text**: real text; fix the spelling first. Teaches the reader to spell this style.
   - **Not text**: a diagram line, arrow, or speck the reader mistook for letters (sometimes Asian characters).
     Teaches the text finder that spot is background. A green one also goes on `config\ocr_ignore.csv`, so the
     scanner drops that exact reading from pictures on the next scan (typed text is never affected).
   - **Skip**: not used.
   If the reader found nothing, type the text under **Whole box as ONE line** and save that instead.
5. **Add OCR Fixes from Corrections** turns a corrected word (LI to LL) into a fix the scanner uses right away.
6. Samples collect in `training_data\` inside the folder. **Undo Last Save** removes the whole last save.
   **Prepare Training Package** and **How training works** lead to section 8 of TRAINING_GUIDE.md.

Each sample is a small cropped picture plus its correct text, usually 1 to 50 KB. A thousand samples take about
10 to 50 MB. They are never added to the shareable zip and never uploaded anywhere. When enough samples build up
(about 500 of the same kind of miss), they can train a better reading model on a separate machine
(`TRAINING_GUIDE.md`, section 8).

## 8. How it gets better over time

The app improves as you use it, without sending anything anywhere. Everything it learns is stored in files
inside its folder.

| What you do | What it learns | Where it is kept |
|---|---|---|
| Include in DB / Exclude | Your vocabulary and the noise to ignore | `acronym_database.csv` |
| Fix OCR | Misreads it keeps making and the right answer | `config\ocr_corrections.csv` (review or undo with **OCR Fixes**) |
| Trainer samples | Examples of text the reader got wrong, with the right answer | `training_data\` |
| Tune settings | Better picture cleanup for your kind of documents | `config\ocr_settings.json` |
| Swap or train a reading model | Better reading of your fonts and layouts | `config\models\` |

Each change is measured with a scoring tool (`tools\evaluate.py` in the project) that checks the app against
documents with known answers, so improvements are proven, not guessed. `TRAINING_GUIDE.md` in the project
explains every step.

**How the whole team gets the improvements.** One person trains; everyone benefits.

| Package | Who | Where it lives |
|---|---|---|
| Scanner (generic starter data only) | Everyone | GitHub Release |
| Scanner + Trainer | Colleagues who collect samples | GitHub Release |
| Training Kit, GPU or CPU version (offline, network-locked) | Whoever trains models | GitHub Release (no document data inside) |
| Knowledge Pack (models + database + fixes + ignore list) | Everyone | **Approved SharePoint folder only** |

Collectors send their `training_data\` folders to the trainer. The trainer runs the Training Kit (offline, usually
overnight), checks the new models with the scoring tool, and exports a Knowledge Pack to SharePoint. Everyone clicks
**Knowledge > Install Knowledge Pack**. The pack is verified file by file before anything changes, the user's own
database edits are never overwritten, and **Undo Last Knowledge Change** reverses an install.

## 9. What it needs to run

- A Windows 10 or 11 computer (64-bit). About 300 MB of disk space and 1 to 2 GB of free memory for large scans.
- **Nothing else.** No internet, no installation, no administrator rights, no Python, no Office,
  no account, no license server.

## 10. Why it works offline

Everything it needs is already inside the folder: the program, all libraries, and the three reading models.
It never downloads anything, never checks for updates, and never sends usage data.
As a second lock, the app blocks itself from opening any network connection while it runs.
It works the same with Wi-Fi off or the network cable unplugged.

## 11. Why it is safe for sensitive documents

- **Nothing leaves the computer.** No network connections, verified by monitoring.
- **Nothing leaves the folder.** Everything the app creates is written inside its own folder, verified by audit and live monitoring.
  The one exception is the results report you choose to export, saved where you put it.
- **Your documents are never changed.** They are only read.
- **Pictures are read in memory.** Pages and images being read are not saved to disk, with one deliberate
  exception: training samples you choose to save in the Trainer are small crops of your documents, kept in
  `training_data\` inside the folder. Treat that folder at the sensitivity of the documents it came from.
- **Delete the folder and it is gone.** No installer, no hidden files, no settings stored elsewhere.

**One honest limit:** Windows itself keeps general records of activity on every PC, such as recently used
file names and which programs ran. These come from Windows, not from the app, and hold names, not document
contents. Part 2, section 12 lists them and how IT normally controls them.

---

# Part 2: Security Assessment for IT and Security Teams

## 1. Posture summary

| Attribute | Answer |
|---|---|
| Deployment model | Portable folder; no installer, no services, no drivers. Standard package: scanner only. Optional WithTrainer package adds the Trainer, sharing the same engine |
| Network access | None. No outbound or inbound connections; runtime block on sockets and DNS |
| Data transmission | None |
| Data storage | Only inside the application folder; user-chosen export location for reports |
| Privileges | Standard user. Manifest `requestedExecutionLevel level="asInvoker"`; never requests elevation |
| Persistence | None. No registry writes, scheduled tasks, startup entries, or services |
| Telemetry / analytics | None. ONNX Runtime telemetry explicitly disabled |
| Auto-update | None. Updates are manual rebuilds |
| Authentication | None (runs under the signed-in Windows user; inherits that user's file permissions) |
| Third-party services / cloud | None |
| AI / ML | Local OCR inference only; no generative AI; no learning from user data unless the user runs offline training |
| Code signing | Not signed (see section 7). SHA-256 checksums published per build |
| Source code | Available (single file `app_gui.py`, private GitHub repository) |
| Known vulnerabilities (pip-audit, 2026-10-20) | None found in pinned Python dependencies |
| Removal | Delete the folder |

## 2. Architecture and data flow

```
                         +-------------------------------------------------------------+
 User-selected files --> |  AcronymHunter.exe  (single process, standard user)         |
 (read-only)             |                                                             |
                         |  Extraction: PyMuPDF, zipfile + hardened lxml, openpyxl     |
                         |  Image cleanup: OpenCV (in memory)                          |
                         |  OCR: ONNX Runtime + bundled RapidOCR PP-OCRv4 models       |
                         |  Matching: regex + RapidFuzz vs acronym_database.csv        |
                         |  UI: CustomTkinter / Tk                                     |
                         |                                                             |
                         |  Network guard: socket.connect, getaddrinfo, urllib blocked |
                         +---------------------------+---------------------------------+
                                                     |
                     writes only inside the app folder (section 3) + user-chosen export
```

- **Trust boundary:** the process boundary of `AcronymHunter.exe`. There is no network boundary because
  there is no network path.
- **Inputs:** files the user selects (PDF, DOCX, PPTX, XLSX, PNG, JPG, TIF, BMP, WEBP, GIF) and files in the app folder.
- **Outputs:** the results table on screen, an optional CSV export, and the app-folder files in section 3.

## 3. Data handling

| Question | Answer |
|---|---|
| What data does it process? | Text and images inside the documents the user selects |
| Where is document content held? | In process memory during the scan; released when the scan or app ends |
| Is document content written to disk? | Not by the scanner. Extracted text and images are never saved; only results the user chooses to keep (database entries, OCR fixes, CSV export, project files) and error logs. A project file (`.ahproj`, saved in the documents folder the user picks) stores a **terms-only** token list per file: term-like tokens and unit words kept, every run of ordinary words replaced by `~`. No sentence can be reconstructed from it. **Exception by design:** the Trainer saves cropped image regions and their text when the user clicks Save, into `training_data\` inside the app folder |
| What files does it write? | `acronym_database.csv`, `config\ocr_corrections.csv` (+ transient `.tmp` during atomic save), `logs\error.log`, `logs\selftest.txt` (diagnostic mode only), `_local_sandbox\settings.json`, `_local_sandbox\temp\*` (emptied at exit and start), `config\ocr_ignore.csv` (OCR readings marked Not text), and from the Trainer `training_data\images\*.png`, `labels.txt`, `regions\*.png`, `det_labels.txt`, `samples.csv` (source file name, location, box), `save_log.jsonl`, `package\*.txt`. All inside the app folder |
| What may those files contain? | Terms and definitions the user adds; file names and paths in error logs; last folder used in settings; **cropped document images and their text** in `training_data\` |
| Data at rest encryption | Not applied by the app. Relies on endpoint full-disk encryption (BitLocker) |
| Data in transit | None exists |
| Retention | User-controlled. Inside the app folder, deleting the folder removes all app data. Outside it, only files the user saves: CSV exports and project files (`.ahproj` plus a `.ahproj.lock` holding user name, computer name, and time while open). These sit with the documents and follow the documents' handling rules |
| Text encoding | Database and corrections files are read as UTF-8, UTF-16, or Windows-1252 and always written as UTF-8 with BOM (full Unicode). Document text and terms are NFC-normalized with look-alike folding before matching |
| Temporary files | `TEMP`, `TMP`, `TMPDIR` are redirected to `_local_sandbox\temp` before any library loads; folder emptied on exit and on next start |
| Source documents modified? | Never. Opened read-only |
| Clipboard, screenshots, keystrokes | Not accessed |

## 4. Network and connectivity

| Question | Answer |
|---|---|
| Does it require internet? | No |
| Does it make any connection? | No. Verified: 0 TCP connections, 0 UDP sockets during a full scan and while idle (100 ms polling of the process) |
| Is there network code? | Only the code that blocks networking. `socket.socket.connect` refuses any non-loopback address; `socket.getaddrinfo` refuses all DNS lookups; `urllib.request.urlopen` is replaced. Tested: raw socket, direct IP connect, DNS, urllib HTTPS, http.client HTTPS all refused |
| Licensing or activation calls? | None |
| Update checks? | None |
| Telemetry? | None. `onnxruntime.disable_telemetry_events()` is called at startup |
| Can IT enforce it? | Yes. Optional Windows Firewall rule (admin): `New-NetFirewallRule -DisplayName "Block Acronym Hunter" -Direction Outbound -Program "<folder>\AcronymHunter.exe" -Action Block` |

## 5. Installation, privileges, and persistence

| Question | Answer |
|---|---|
| Installer? | None. Unzip and run |
| Admin rights? | Not required. Executable manifest is `asInvoker`, `uiAccess="false"` |
| Services, drivers, scheduled tasks? | None |
| Registry writes by the app? | None. Verified: no registry keys created during a monitored run |
| Startup/autorun entries? | None |
| Child processes? | None during scanning (verified). On user click only: **Region Trainer** starts `AcronymHunterTrainer.exe` from the same folder; **Edit Database CSV** and **Open Training Folder** ask Windows to open a file or folder in its default program |
| Files outside the folder? | None, except the user-chosen CSV export. Verified by live file-system monitoring |
| Architecture | x64 Windows PE (machine 0x8664). Bundles its own Visual C++ runtime DLLs |
| Uninstall | Delete the folder. Verified: no app files remain afterward |

## 6. Software composition (bill of materials)

Runtime components bundled in `_internal\` (build tools such as PyInstaller are not shipped):

| Component | Version | License | Role | Origin |
|---|---|---|---|---|
| CPython | 3.11.9 | PSF-2.0 | Runtime | Python Software Foundation (US) |
| Tcl/Tk | 8.6 | BSD-style (Tcl license) | Window toolkit | Tcl Core Team |
| OpenSSL libcrypto/libssl | 3.x (bundled by CPython) | Apache-2.0 | Hashing (SHA-1 cache keys). No TLS used | OpenSSL Project |
| PyMuPDF / MuPDF | 2.0 | **AGPL-3.0 or Artifex commercial** | PDF parsing | Artifex Software (US) |
| lxml / libxml2 | 6.1.3 | BSD-3-Clause / MIT | Office XML parsing (hardened) | lxml project |
| defusedxml | 0.7.1 | PSF-2.0 | Safe XML parsing for openpyxl | Christian Heimes |
| openpyxl / et_xmlfile | 3.1.5 / 2.0.0 | MIT | Excel cell reading | openpyxl project |
| OpenCV (headless) | 5.0.0.93 | Apache-2.0 | Image preprocessing | OpenCV.org |
| NumPy (+ OpenBLAS) | 2.4.6 | BSD-3-Clause and others | Array math | NumPy project |
| ONNX Runtime | 1.31.0 | MIT | Model inference | Microsoft (US) |
| rapidocr-onnxruntime | 1.4.4 | Apache-2.0 | OCR pipeline wrapper | RapidAI open-source community (China) |
| PP-OCRv4 det/rec + v2.0 cls models | bundled | Apache-2.0 | Text detection, recognition, orientation | Baidu PaddleOCR project (China) |
| Shapely / GEOS, pyclipper | 2.2.0 / 1.4.0 | BSD-3-Clause / MIT, Boost | Text-box geometry for OCR | Open-source projects |
| PyYAML | 6.0.3 | MIT | OCR config file | PyYAML project |
| RapidFuzz | 3.14.6 | MIT | Fuzzy matching | RapidFuzz project |
| CustomTkinter, darkdetect | 6.0.0, 0.8.0 | MIT/CC0, BSD-3-Clause | UI | Open-source projects |
| Pillow | 13.0.0 | MIT-CMU | Image support library | Pillow project |
| psutil | 7.2.2 | BSD-3-Clause | Dependency of OCR wrapper | psutil project |

Full pinned list: `requirements.txt`. Bundled OCR model fingerprints (SHA-256):

| Model file | Size | SHA-256 |
|---|---|---|
| `ch_PP-OCRv4_det_infer.onnx` | 4.7 MB | `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9` |
| `ch_PP-OCRv4_rec_infer.onnx` | 10.9 MB | `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b` |
| `ch_ppocr_mobile_v2.0_cls_infer.onnx` | 0.6 MB | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |

**Licensing notes for legal review:**
- **PyMuPDF is dual-licensed AGPL-3.0 / Artifex commercial.** Internal use is common under AGPL; distribution
  outside the organization or modification without releasing source may require the commercial license.
  Have legal confirm before distributing beyond internal use.
- PyInstaller (GPL-2.0 with bootloader exception) is a build tool; its bootloader exception permits
  distributing the packaged app under any terms.

**Origin note:** the OCR models and the RapidOCR wrapper originate from projects based in China.
The models are static weight files (numbers, not executable code) run by Microsoft's ONNX Runtime.
The wrapper is Apache-2.0 open-source Python included in the bundle and reviewable. Neither has network
access in this app. Organizations with software-origin policies should review this; replacement models
can be dropped into `config\models\` (see `TRAINING_GUIDE.md`).

## 7. Supply chain and integrity

| Question | Answer |
|---|---|
| Where do components come from? | PyPI packages at exact pinned versions (`requirements.txt`), installed into an isolated build environment |
| Who builds it? | The developer, locally on Windows, with `build.ps1` (PyInstaller one-folder build) |
| Is the build scanned? | Yes. `build.ps1` runs Microsoft Defender against the finished folder and stops if anything is flagged |
| How is integrity verified? | SHA-256 of the exe (`CHECKSUM.txt` inside the folder) and of the zip (`AcronymHunter_SHA256.txt`). Send the zip hash separately from the zip |
| Is it code-signed? | No. Options: internal enterprise signing or allowlisting by IT (recommended), Azure Artifact Signing, or an OV certificate. Hash-based allowlists change with every build; publisher rules require signing |
| Is the source available? | Yes, `app_gui.py` (about 1,500 lines, single file), build spec, and pinned requirements in a private GitHub repository |
| Is compression/packing used? | No. UPX packing is disabled to avoid EDR false positives and binary tampering concerns |
| What reaches GitHub? | Only generic packages built from `base\` (starter terms, example fixes, settings). A leak check in `build.ps1` stops the build if any other data file, any changed data, or any model file would ship. Knowledge Packs and training data never go to GitHub |
| Training Kit components | Python 3.11.9 embeddable (python.org), PaddlePaddle 2.6.2 and pinned PyPI packages, PaddleOCR 2.8 (GitHub), PP-OCRv4 weights (PaddleOCR). Downloaded once by `build_training_kit.ps1`; SHA-256 of each download and every package version in `KIT_MANIFEST.txt` |
| Reproducibility | Same source + same `requirements.txt` + Python 3.11 produce a functionally identical build; binary hashes differ per build due to timestamps |

## 8. Vulnerability management

| Item | Status |
|---|---|
| Dependency scan | `pip-audit` against the PyPI advisory database, 2026-10-20: **no known vulnerabilities** in runtime dependencies or build tools |
| Not covered by pip-audit | CPython 3.11.9 runtime and native libraries bundled inside packages (MuPDF, libxml2, OpenSSL, Tcl/Tk) |
| Python runtime | 3.11.9 predates later 3.11 security releases. Recommendation: rebuild on the newest Python 3.11.x before wide distribution |
| Patch process | Update versions in the build environment, run the scorer (`tools\evaluate.py`) for regressions, rebuild, re-run section 15 checks, publish new checksums |
| Exposure | Low: no network listener or client, standard-user privileges. Main exposure is parsing untrusted files (section 9) |

## 9. Untrusted input handling (attack surface)

The app's real attack surface is the documents it opens. Controls:

| Risk | Control | Verified |
|---|---|---|
| Macros, scripts, embedded programs | Never executed. Office files are read as zip + XML; macros, OLE objects, and PDF JavaScript are ignored | By design (no execution path) |
| XML entity expansion ("billion laughs") | lxml parser with `resolve_entities=False`, `load_dtd=False`, `no_network=True`, `huge_tree=False`; openpyxl uses defusedxml | Bomb file expanded to 3 characters instead of 10,000 |
| XML external entities (XXE) | Same hardened parser; no DTD or network loading | Attempt to read `C:\Windows\win.ini` returned nothing |
| Decompression bombs | Embedded images over 100 MB uncompressed are skipped; OpenCV pixel limits apply; tiny images skipped | Code review |
| Path traversal from archives | Archive members are read into memory only; nothing is extracted to disk | Code review |
| Malformed or corrupt files | Each file, page, slide, and part is isolated; failures become "Could not read" / "Not scanned" rows and a log entry; the batch continues | Corrupt PDF test file in `test_samples` |
| Vector graphics (SVG, EMF, WMF) | SVG parsed with the same hardened lxml parser; EMF/WMF read with a bounds-checked record reader; rendering for OCR happens in memory (MuPDF for SVG, Pillow/GDI for EMF/WMF). External references inside SVG are never fetched | Vector test files in `test_samples` |
| Linked content (remote images) | Never fetched. Linked pictures are reported as "Not scanned" | 40-slide test deck with a linked picture |
| Native parser bugs (MuPDF, libxml2, OpenCV) | Mitigated by keeping libraries current (section 8), standard-user privileges, and endpoint protection | Ongoing |

## 10. AI and machine-learning specifics

| Question | Answer |
|---|---|
| What models are used? | Three small OCR models (text detection, recognition, orientation), 16 MB total, PP-OCRv4 family |
| Generative AI or LLMs? | None |
| Where does inference run? | Locally on the CPU via ONNX Runtime |
| Is user data used to train models? | No, never automatically. The Trainer only saves samples when the user clicks Save. Training on them is a separate, manual, offline process (`TRAINING_GUIDE.md`) on approved hardware; the result is a replacement `rec.onnx` in `config\models\` |
| Is output deterministic? | Yes. The same file gives the same result every run |
| Can models be changed? | Only by placing files in `config\models\` (falls back to bundled models if they fail). The scan log records which models were used |
| Model integrity | SHA-256 of bundled models listed in section 6 |

## 11. Logging, monitoring, and audit

| Question | Answer |
|---|---|
| What is logged? | `logs\error.log`: errors with stack traces and file paths, only when failures occur. `logs\selftest.txt`: results in diagnostic mode only |
| User activity logging? | None. No usernames, no keystrokes, no document contents |
| Central logging? | None (no network). Endpoint tools (EDR, Defender) observe the process like any other |
| Audit trail of database changes? | Not built in. Changes are visible by comparing CSV versions (Git history in the project repository) |

## 12. Residual risks and organizational responsibilities

| Residual item | Owner | Recommended control |
|---|---|---|
| Windows program-run history, file-dialog recent lists, thumbnail cache, Excel recent files | Organization (OS policy) | Standard OS privacy and retention policies; use List/Details view in the file picker |
| Memory paging / hibernation files can hold fragments of any program's memory | Organization | BitLocker full-disk encryption |
| Crash dumps (Windows Error Reporting) on a native crash | Organization | WER policy; none observed in testing |
| Exported reports and app-folder files contain sensitive terms | User | Store the folder and exports on encrypted, local, non-synced storage; mark exports per data classification |
| `training_data\` holds crops of real documents | User | Same storage rules; never copy it into the repository or a shared zip (excluded by `build.ps1` and `.gitignore`); delete it when no longer needed |
| Unsigned executable | Organization / developer | IT allowlisting or internal code signing |
| AGPL-licensed PDF component | Legal | Confirm internal-use terms or obtain commercial license |
| Software origin of OCR models | Security | Review against policy; swap models if required |
| Python runtime age | Developer | Rebuild on current Python 3.11.x |
| Single-developer maintenance, no vendor SLA | Organization | Treat as internal tool; source and build process are documented for handover |

## 13. Compliance alignment (CUI, ITAR, NIST SP 800-171)

The app is a local, offline utility. It does not store, process, or transmit data outside the endpoint, so it
inherits the endpoint's controls. How it relates to common requirements:

| Area | How the app aligns | Organization still provides |
|---|---|---|
| Boundary protection (800-171 3.13) | No external communication of any kind | Network controls for the endpoint |
| Media protection (3.8) | Writes only to its folder; deletion removes all app data | Encrypted storage, sanitization of media |
| Access control (3.1) | Runs as the signed-in user; no elevation; no new access paths | User accounts, folder permissions |
| Configuration management (3.4) | Fixed, pinned components; no auto-update; checksums per build | Software approval / allowlisting |
| System integrity (3.14) | Defender-scanned builds; hardened parsers; no code execution from documents | Endpoint protection, patching |
| Audit (3.3) | No logs of user actions by design | OS and EDR auditing |
| ITAR / export control | No transmission, so no transfer of technical data occurs through the app | Handling of exported reports per export rules |

This is an alignment summary, not a certification. Approval for CUI or ITAR use belongs to the organization's
security and compliance teams.

## 14. Recommended deployment controls

1. Approve by hash or sign internally; record the exe and zip SHA-256 values with the approval.
2. Place the folder on a BitLocker-encrypted, local, non-synced path; restrict folder access to the user.
3. Optional: add the outbound firewall block rule in section 4 for defense in depth.
4. Run as a standard user (no elevation is ever needed).
5. Re-review on each new version; the version and checksums are in the folder.

## 15. Verification evidence and how to repeat it

| Test (2026-10-20) | Result |
|---|---|
| Code audit of every file write and network call | Writes only inside the app folder plus user-chosen export; network code only blocks |
| Runtime network block test | Raw socket, direct IP, DNS, urllib, http.client all refused |
| Live monitoring, fresh unzip, 8-9 sample files + idle window | 0 TCP, 0 UDP, 0 child processes; no files outside the folder; no registry keys created |
| Deletion test | No app files remain in the user profile or ProgramData |
| XML hardening test | Entity bomb and XXE neutralized |
| pip-audit | No known vulnerabilities |
| Microsoft Defender scan (every build) | No threats found |
| Accuracy regression (tools\evaluate.py) | 93.2% recall on the test set; no change from hardening |
| Runtime self-check in the shipped exe (`--selftest`) | `Security: network guard=True, office XML entities disabled=True, openpyxl defusedxml=True` |

Step-by-step commands to repeat the network, file, deletion, and integrity checks are in `SECURITY.md`, section 8.

**One-line runtime check:** run `AcronymHunter.exe --selftest "C:\path\any_file.pdf"` and open `logs\selftest.txt`.
The `Security:` line confirms, from inside the running program, that the network guard and XML hardening are active.

## 16. Frequently asked questions

**Where do trained models and our acronym list live?** In Knowledge Packs on the approved SharePoint folder only. The
GitHub packages carry generic starter data; a build-time leak check enforces that. See SECURITY.md section 3.

**Does training need the internet?** No. The Training Kit is downloaded and assembled once by the maintainer. After
that it runs on any PC with its own network lockdown, which refuses and logs any connection attempt.

**Can it scan files in OneDrive or SharePoint without risk to them?** Yes, when the folder is synced to the PC.
The app opens every file read-only and never writes to, locks, or re-saves a source file (SHA-256 and modified
time verified unchanged after a scan). Cloud-only files are downloaded by the OneDrive client, inside the
organization's Microsoft 365, not by the app. Project files and CSV exports saved in a synced folder upload like
any file. Keep the app folder itself out of OneDrive. Details: SECURITY.md section 3.

**Does it phone home, check licenses, or send usage data?** No. There is no network path, and networking is blocked in code.

**Does it need administrator rights?** No. It is built to run as a standard user and never asks for elevation.

**Can it be used on an air-gapped machine?** Yes. It was designed for that.

**Does it store our documents anywhere?** The scanner does not; it reads them in memory. Only the terms you choose to save, error logs, and reports you export are written. The Trainer saves small crops only when you click Save, inside the app folder.

**What happens if we delete it?** All app files and data are gone. Windows' own general activity records (section 12) follow your normal OS policies.

**Can a malicious document make it run code?** It never runs macros, scripts, or embedded objects, and its XML parsing is hardened. Like any software that opens files, it depends on its parsing libraries being kept current.

**Can it update itself or change without us knowing?** No. It has no update mechanism. Any change requires a new build with new checksums.

**Who maintains it?** The developer. Source, build scripts, documentation, and tests are in the project repository so another engineer can take it over.

**Where is the source?** `app_gui.py` in the private repository, with `AcronymHunter.spec`, `build.ps1`, and `requirements.txt` to rebuild it.
