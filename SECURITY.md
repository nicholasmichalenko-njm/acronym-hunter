# Stationkeeper: Security and Data-Handling Statement

**Version covered:** 2.76.0 (exe SHA-256 recorded in `Stationkeeper_US_SHA256.txt` and `CHECKSUM.txt`; every program file's SHA-256 in `_internal\program_manifest.json`). Sections 10 and 11 added in 2.76.0
**Verified:** 2026-10-20 (v1.0.1 live test; v1.0.2 added tiled OCR and the OCR Fixes window; v1.0.3 hardened XML parsing and capped embedded image size; no new file locations or network code) on the developer's Windows PC, from a fresh unzip of the shipped zip
**Audience:** users, security and IT reviewers

---

## 1. Bottom line

- **No internet, ever.** The app makes no network connections. Nothing in its code calls out, its OCR models
  ship inside the folder, and it actively blocks outbound connections at runtime. Verified: 0 connections
  during a full scan and while idle.
- **Everything the app creates stays in its folder.** Results, logs, settings, the database, and temporary
  files are written only inside the `AcronymHunter` folder. Verified by code audit and by monitoring the
  file system during a live run.
- **Delete the folder and the app's data is gone.** No installer, no services, no files in AppData or
  Program Files, no registry keys created by the app. Verified by deleting the folder and searching for leftovers.
- **Your documents are never changed.** Files are opened read-only. Images and pages being OCR'd are processed
  in memory and never saved.

**What "100% local" does and does not cover.** The guarantee covers everything the **app** does. Windows and
Office keep their own records of activity on any PC, for every program: for example, recently opened file names
and which programs have run. Those records contain file names and paths, not document contents, and they exist
whether you use this app, Notepad, or Word. Section 6 lists them and how to minimize them. On a managed work PC
these are governed by the same IT controls as every other application.

---

## 2. How it works (architecture)

```
  Your documents (PDF, DOCX, PPTX, XLSX, images)          read-only
            |
            v
  +-----------------------  AcronymHunter.exe  (one Windows process)  ------------------------+
  |                                                                                           |
  |  1. Extraction      PDFium (PDF), zipfile + lxml (Word/PowerPoint/Excel XML), openpyxl    |
  |  2. Image cleanup   OpenCV in memory: enlarge, contrast, denoise                          |
  |  3. OCR             ONNX Runtime + RapidOCR models bundled in _internal\ (no download)    |
  |  4. Matching        regex + RapidFuzz against acronym_database.csv                        |
  |  5. Window          CustomTkinter / Tk                                                    |
  |                                                                                           |
  |  Network guard: socket connect + DNS lookup + urllib blocked (loopback only)              |
  +-------------------------------------------------------------------------------------------+
            |
            v
  Writes ONLY inside its own folder (see section 3). Export CSV goes where YOU choose.
```

Untrusted-file hardening (v1.0.3): Office XML is parsed with entity expansion, DTD loading, and network access
disabled (tested against an entity bomb and an XXE file read); openpyxl uses defusedxml; embedded images over
100 MB are skipped. Macros, embedded objects, and PDF scripts are never executed. Full detail: OVERVIEW.md Part 2.

There is no server, no cloud service, no account, no license check, no telemetry, and no auto-update. New versions
arrive only as signed update packs that the user picks and installs (section 11).
The app is a single process. It starts no child programs while scanning (verified: 0 child processes).

---

## 3. Every file the app writes

Complete list from a line-by-line audit of `app_gui.py` (every `open(... "w"/"a")`, `os.replace`,
`os.makedirs`, and `rmtree` call):

| Path (inside the app folder) | Contents | When | Sensitive? |
|---|---|---|---|
| `acronym_database.csv` | Terms and definitions | Include / Exclude buttons | Contains terms you add |
| `config\ocr_corrections.csv` | Misread to correct-term pairs | Fix OCR button, OCR Fixes window | Contains terms you add |
| `logs\events.jsonl` | Errors and quiet failures: fixed message, error type, code location (our file name, line, function), counts and file extensions. **Never** file names, paths, document text, terms or error messages. A build check (`tools\check_diag.py`) enforces it | When something fails | No |
| `logs\activity.jsonl` | Feature actions and clicks by internal control name (for example `btn_again`), time between actions, greyed-out clicks. Never on-screen text, rows clicked or anything typed. Off with `usage_logging: false` in `config\app_settings.json` | While the app is used | No |
| `logs\crash_raw.txt` | Python's crash dump (contains file paths) | Only after a hard crash; converted to a content-free line in events.jsonl at the next start, then deleted. Never exported | Paths, briefly |
| `config\choices.json` | Definition choices made with Apply Choice, reused on every later scan | Apply Choice | Terms and definitions |
| `config\efforts.json` | Effort names, list file locations, first-use rule, customer and volumes folders | Effort setup | Folder paths |
| Effort list `.xlsx` (where you choose) | Terms, definitions, customer document names and wording, statuses, SS approver names, history with Windows user names | Add to effort list, status changes | **Yes: customer content.** Keep on the PC or SharePoint |
| `feedback\reports\*.json` | Feedback reports you write (feature, title, description) | Feedback window | Only what you type; the content guard blocks text that matches your terms, definitions, file or folder names |
| `logs\selftest.txt` | Scan results | Only with `--selftest` | Terms found |
| `_local_sandbox\settings.json` | Text size, last folder used | When you change them | Folder path |
| `_local_sandbox\temp\` | Temporary files, incl. OCR engine config | During a scan; **emptied on exit and on next start** | No document content |
| `config\knowledge_installed.json` | Version, date, author, SHA-256 of the last Knowledge Pack installed | **Knowledge > Install Knowledge Pack** | Pack metadata |
| `config\knowledge_backups\<time>\` | Copies of the database, fixes, ignore list, and models replaced by an install or model load | Before every install or load (for Undo) | **Yes: same as the database and models** |
| `config\ocr_ignore.csv` | Exact OCR readings marked "Not text" (for example `III`, `一I`), with source file name and location | Trainer **Save Choices** on a "Not text" line | Readings and file names |
| `training_data\images\*.png`, `labels.txt`, `samples.csv` | **Cropped document images** + their text, source file name, location | Only when you click Save in the Trainer | **Yes: document content.** Never shipped in the zip or committed to Git |
| `training_data\regions\*.png`, `det_labels.txt`, `save_log.jsonl` | **The whole box drawn in the Trainer** + text box positions; save history for Undo | Trainer **Save Choices** | **Yes: document content.** Same handling as above |
| `training_data\package\*.txt` | Train/check lists of the sample file names, a short report | **Prepare Training Package** | File names and label text |
| `_update\staged\`, `_update\backup\`, `_update\journal.json` (2.76.0) | Program files of an update pack while it installs; the replaced program files (for Undo last update); the install's progress | **Install update pack**, **Undo last update** | No: program files only |
| `logs\update.txt` | One line per `--apply-update`, `--undo-update` or `--check-program` run: versions, counts, program file names | Only with those options | No |

**Writes outside the folder are yours to direct:**

| Path (outside the app folder) | Contents | When | Sensitive? |
|---|---|---|---|
| Report you name (`*.csv`) | Terms, definitions, counts, locations, change history | *Export CSV* | Terms and file names |
| `<documents folder>\<name>.ahproj` (v1.3.0+) | Relative file names, sizes, modified times; per file a **terms-only** token list (term-like tokens and the unit word after a number; every run of ordinary words replaced by `~`); findings, definition choices, manual items, first/last-seen history | *Project > New Project*, then after each scan or edit | Terms and file names. **No sentences or document text** (verified: test phrase absent, the word "shall" absent). Same classification as the exported CSV |
| `<name>.ahproj.lock` | Windows user name, computer name, time | While a project is open for editing; deleted on close or exit | User and computer name |
| `<name>.ahproj.tmp` | Same as `.ahproj` | A fraction of a second during each save (atomic replace) | As `.ahproj` |

The project file sits in the documents folder by design, so it travels with the documents and inherits that
folder's access controls. Deleting the app folder does not delete project files; delete the `.ahproj` with the documents.

**Actions that hand off to another program (user click only):** *Edit Database CSV* opens `acronym_database.csv` in your
default spreadsheet program (usually Excel), which then behaves like any Excel session (see section 6). *Region Trainer*
starts `AcronymHunterTrainer.exe` from the same folder; it shares the same network block and folder rules.
The Trainer and its button exist only in the optional `AcronymHunter_WithTrainer.zip` package; the standard
`AcronymHunter_Portable.zip` contains the scanner only.
*Open Training Folder* opens `training_data\` in File Explorer.

Temporary-file redirection: the app sets `TEMP`, `TMP`, and `TMPDIR` to `_local_sandbox\temp` before loading
any library, so libraries that create temp files create them inside the folder.

### OneDrive and SharePoint

| Question | Answer |
|---|---|
| Can it scan files in a synced OneDrive or SharePoint folder? | Yes. To the app they are ordinary local files. Browser-only links are not supported |
| Can it alter or corrupt them? | No. Every reader opens files read-only (`open(..., "rb")`, PDFium, `zipfile`, openpyxl read mode). The app never writes to, locks, or re-saves a source file. Verified 2026-10-20: SHA-256 and modified time of every test file identical before and after a scan |
| Does the app connect to Microsoft 365? | No. A cloud-only file is downloaded by the OneDrive sync client (a separate Microsoft process) when the app opens it, under the organization's tenant policy. The app's network block applies to the app's own process |
| What does reach the cloud? | Only what the user saves into a synced folder: project files (`.ahproj`, `.ahproj.lock`) and CSV exports. They upload like any file and inherit that library's permissions |
| Limits | The project lock is only as current as OneDrive sync between PCs; sync conflicts create a copy such as `Name-PCNAME.ahproj`. Files encrypted by a sensitivity label cannot be read (reported as "Could not read") |
| Do not | Put the AcronymHunter app folder itself in OneDrive: `_local_sandbox\`, `logs\`, and `training_data\` would sync to the cloud |
| Controlled data | Whether CUI/ITAR may be stored in a given OneDrive/SharePoint (for example a GCC High tenant) is the organization's decision; the app neither enables nor prevents it |

### Client acronym lists (v1.5.0)

| Question | Answer |
|---|---|
| Where do they go? | Read once from the file the user picks (read-only), then held in memory. With a project open, the term and definition pairs are saved in the `.ahproj` file. Without a project, nothing is written |
| What is stored? | Term, definition, list file name, date added. Never the list file's other text |
| Sensitivity | Treat the project file at the classification of the client list. Client lists are never put in Knowledge Packs, the database, or GitHub packages |
| Exports | Export CSV adds Possible definitions, Client list definition, Database definition, Author decision columns for the rows shown |

### Knowledge Packs (v1.4.0)

| Question | Answer |
|---|---|
| What is in a pack? | `knowledge/pack_info.json` (version, author, computer, notes, SHA-256 of every file), and any of: `acronym_database.csv`, `ocr_corrections.csv`, `ocr_ignore.csv`, `models/rec.onnx`, `models/det.onnx`, `models/cls.onnx`, `models/rec_keys.txt` |
| Sensitivity | Treat as the classification of the documents the knowledge came from. **Approved SharePoint folder only. Never GitHub, email, or personal storage** |
| How is a pack checked before install? | Only the files above are accepted (no paths, no executables); each file is at most 400 MB; every file's SHA-256 must match `pack_info.json`. Any failure installs nothing. Verified: a pack with one changed byte and a pack with an extra `../../payload.exe` were both refused |
| What does install change? | Models in `config\models\` are replaced. Database, fixes, and ignore list merge add-only; the user's own rows, edits, and Exclude choices win. A backup is taken first; **Knowledge > Undo Last Knowledge Change** restores it exactly |
| Can a model file run code? | No. ONNX files are loaded by ONNX Runtime as data (a computation graph); the app checks a model loads before using it |

### Data boundary for GitHub packages (v1.4.0)

The GitHub Release packages (`AcronymHunter_Portable.zip`, `AcronymHunter_WithTrainer.zip`) are built from `base\` only:
an empty acronym database (header only), an empty OCR fixes file (header only, since v1.5.0), settings, and a models README. The working
database and `config\` are ignored by Git and never packaged. `build.ps1` refuses to finish if any file outside the
approved list, any data file that differs from `base\`, or any model file other than RapidOCR's public models would ship.
Audit 2026-10-20: no document data, user paths, or trained knowledge in the packages or anywhere in Git history.

### Training Kit (v1.4.0)

| Question | Answer |
|---|---|
| What is it? | A separate folder for whoever trains models: portable Python 3.11, PaddlePaddle (CPU kit 2.6.2; GPU kit 3.4 with NVIDIA CUDA 12.9 libraries, plus a 2.6.2 export toolchain), PaddleOCR tools, PP-OCRv4 starting weights. No document data as distributed |
| GPU kit specifics | Uses the NVIDIA card through the installed NVIDIA driver; CUDA libraries are pip-distributed NVIDIA packages inside the kit (nothing installed on the PC). Both Pythons in the kit load the same network lockdown |
| Network | `kit\sitecustomize.py` loads before any other code in every kit process and refuses outbound TCP, UDP, and DNS (loopback allowed). Refusals are logged to `kit\logs\network_blocked.log`. `Train.cmd > 1` proves it on the current PC |
| Internet needed? | Only once, by the maintainer, to build the kit (`build_training_kit.ps1`). Every download's SHA-256 is in `KIT_MANIFEST.txt` |
| What it writes | Inside the kit folder only: `samples\` (collectors' crops), `work\` (merged data, checkpoints), `output\models\`, `kit\logs\`. All sensitive at the documents' level |
| Verified | Dry run 2026-10-20: both models trained, exported, converted, loaded by the scanner; 0 refused attempts and 0 non-loopback connections observed (250 ms polling) |

---

## 4. Why no internet is needed or possible

| Check | Result |
|---|---|
| Libraries with network features used by the app | None. PDFium, Skia, lxml, openpyxl, OpenCV, Tesseract, RapidFuzz, CustomTkinter have no network calls in the code paths used. `tools\network_audit.py` lists every shipped file that links a networking API |
| Vector graphics (SVG, EMF, WMF) | Parsed with the hardened lxml parser (no entities, no DTD, no network) or a built-in record reader. SVG references to external images or fonts are never fetched; Skia draws the SVG from the bytes in memory |
| OCR models | Tesseract: Google's eng.traineddata (SHA-256 checked at build). docTR (v2.1.0+): `_internal\doctr\doctr_det.onnx` and `doctr_reco.onnx`, exported by this project from Mindee's official weights; SHA-256 checked at build against `vendor\doctr\doctr_models.json`. Never downloaded |
| ONNX Runtime usage telemetry | Disabled in code (`disable_telemetry_events()`) |
| Runtime network block | `socket.connect` to any non-loopback address, all DNS lookups, and `urllib` are replaced with functions that refuse. Tested: raw socket, direct IP, DNS, urllib HTTPS, and http.client HTTPS all refused |
| Live monitoring of the exe (100 ms polling), full scan of 8 files + 20 s idle | **0 TCP connections, 0 UDP sockets, 0 child processes** |

The app works identically with the network cable unplugged or Wi-Fi off.

**Tesseract (v1.7.0+): three independent layers, no network possible.**
1. **No network code.** `tools\build_tesseract.ps1` builds Tesseract 5.5.3 from its official source with
   `-DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON`. `tesseract --version` lists no libcurl or libarchive.
2. **Operating-system sandbox.** Every Tesseract process (reading pictures, and the training tools behind Improve
   Reading) starts inside a Windows AppContainer with **no capabilities**. Windows denies every network operation,
   including loopback, to such a process. It can read only the folders the app grants (`_internal\tesseract`,
   `config\models`) and write only `training_data\model`. No admin rights are used. The self-test runs Windows' own
   `curl.exe` in the same sandbox as proof: result "BLOCKED (Could not resolve host)", while the same command
   outside the sandbox succeeds. If the sandbox cannot start (for example the app runs from a network share), the
   app logs it and runs Tesseract normally, unless `ocr_sandbox_required` is true in `config\app_settings.json`.
3. **Build gate.** `tools\network_audit.py` reads the import tables of every shipped .exe, .dll, and .pyd. A
   Tesseract file that links Winsock, WinHTTP, WinINet, DNS, or libcurl fails the build. (Run against the official
   v1.6.0 Windows build, it fails on 5 files, including libcurl-4.dll and tesseract.exe.)

The app sends image bytes on stdin and reads results on stdout: no file names, no URLs.

**No generative AI (2.55.0).** The optional math reader add-on (IBM Granite-Docling on PyTorch) is removed: the app
no longer looks for it, starts it or lists it, and the build no longer makes it. Equation pictures are read by the
text reader (Tesseract, ML) with position rules. An old `math_addon\` folder or `config\math_results.json` left on a
PC is never used; delete them.

**docTR second reader (v2.1.0+).**
- **What it is:** two ONNX models from Mindee's docTR (Paris, Apache 2.0), a DBNet text finder and a CRNN text
  reader. This project exported them itself from Mindee's official weights. The weight files' SHA-256 match the
  hash prefixes in Mindee's file names. No third-party conversion is used. `vendor\doctr\SOURCE.txt` records
  every hash.
- **Runtime:** ONNX Runtime 1.31.0 (Microsoft, MIT) in the app's own process, CPU only. The runner,
  `doctr_engine.py`, is this project's own code: about 250 lines of NumPy and OpenCV, with no OnnxTR or docTR
  package. OnnxTR was rejected because it imports Hugging Face's download client and HTTP libraries.
- **No network path:**
  - Models load from `_internal\doctr` by file path only.
  - ONNX Runtime telemetry is disabled in code.
  - The in-process network guard covers it like the rest of the app.
  - `tools\network_audit.py` found no networking imports in any ONNX Runtime or docTR file in the v2.1.0 build.
- **Build gate:** the origin check allows exactly two .onnx files, and only with the recorded SHA-256. It still
  refuses RapidOCR, PaddleOCR, pyclipper and shapely.
- **Turn it off:** set `"doctr_enabled": 0` in `config\ocr_settings.json`.

---

## 5. Verification performed (2026-10-20, v1.0.1)

Method: fresh unzip of `AcronymHunter_Portable.zip` into a new folder. A 45-second control period with the app
closed recorded background file activity from other programs. Then the app scanned all 8 test files
(PDF, 2x PowerPoint, Word, Excel, PNG, JPG, corrupt PDF) and its window stayed open 20 seconds.
File changes during the app run were compared against the control period.

| Test | Result |
|---|---|
| Network connections by the app | 0 |
| Files created or changed outside the app folder by the app | **None found.** Three `.tmp` files appeared in Windows Temp during the run; they were still locked by another running program after the app had exited, and 22 identical files existed from earlier in the day, so they belong to other software |
| Registry keys created by the run | None |
| `_local_sandbox\temp` after exit | Empty |
| Folder deleted, then user profile and ProgramData searched for app files | **No app files remain** |
| Scan result | 115 findings, self-test OK |

**How to repeat this yourself:** see section 8.

---

## 6. What Windows and Office record on their own (outside the app's control)

These exist for every program on a Windows PC. They hold names and paths, not the contents of your documents,
except where noted. The app does not create them and cannot remove them.

| Record | Created by | What it holds | When | How to minimize |
|---|---|---|---|---|
| Program-run history (MuiCache, Compatibility Assistant, taskbar usage, Prefetch) | Windows | Path and name of `AcronymHunter.exe` | Each launch | Normal for all software; cleared by Windows over time or by IT tools |
| File dialog history (Open/Save MRU) | Windows file picker | Last folders and file names chosen in Select Files / Scan Folder / Export | Using the picker | Clear with Windows privacy settings or IT tools |
| Thumbnail cache | Windows Explorer | Small previews of **images** shown in the picker in thumbnail view | Browsing images in thumbnail view | Use **List** or **Details** view in the picker |
| Excel recent files, AutoRecover | Excel | Database file name; recovery copies if Excel crashes | Only after *Edit Database CSV* | Edit the database inside the app instead |
| Memory paging / hibernation file | Windows | Can contain fragments of any program's memory, including text being scanned | Under memory pressure or hibernation | Full-disk encryption (BitLocker), standard on managed PCs |
| Crash reports (Windows Error Reporting) | Windows | Memory snapshot if the app process crashes hard | Only on a native crash (none observed) | Governed by IT policy; can be disabled organization-wide |
| Antivirus scanning | Microsoft Defender / EDR | Files the app reads are scanned like any file access | Always | Governed by IT policy |
| Cloud-synced folders | OneDrive, etc. | Anything **you** save into a synced folder, such as an exported report | When you save there | Export reports to a local, non-synced folder |

Verified on this PC: the only registry entries naming the app were Windows program-run history and Excel
recent-file entries from earlier manual use. None held document content.

---

## 7. Safe-use checklist for sensitive data

1. Keep the app folder on an encrypted drive (BitLocker) in a **local, non-synced** location
   (not OneDrive, Dropbox, or a network share that syncs to the cloud).
2. Save exported reports to a local, non-synced folder and handle them at the same sensitivity as the source documents.
3. Remember that `acronym_database.csv`, `config\ocr_corrections.csv`, and `logs\` can contain sensitive terms
   and file names. Treat the folder at the sensitivity of the data you scanned.
4. When sharing the app, share a fresh zip from `build.ps1`, never a folder you have used: the build ships
   only the curated database and settings and removes logs and scratch files.
5. To remove all app data: close the app, delete the folder. Optionally clear Windows recent-file history.
6. On company machines, get IT approval before use (the exe is not code-signed; see `PROJECT_GUIDE.txt`).

---

## 8. Verify it yourself

**Network (PowerShell, while a scan runs):**
```powershell
$p = Get-Process AcronymHunter
Get-NetTCPConnection -OwningProcess $p.Id    # expect: nothing
Get-NetUDPEndpoint  -OwningProcess $p.Id     # expect: nothing
```
Stronger: unplug the network or turn off Wi-Fi, then run a full scan. It works the same.

**Files:** note the time, run a scan, close the app, then list recent changes outside the folder:
```powershell
$t = Get-Date   # run this BEFORE starting the app
Get-ChildItem $env:LOCALAPPDATA, $env:APPDATA, $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue |
  Where-Object LastWriteTime -gt $t | Select-Object FullName, LastWriteTime
```
Background programs (browsers, sync tools) also appear here; anything the app wrote would be named for it or
created only while it ran.

**Deletion:** delete the folder, then search:
```powershell
Get-ChildItem $env:USERPROFILE, C:\ProgramData -Recurse -Force -Include *AcronymHunter* -ErrorAction SilentlyContinue
```

**Integrity:** `Get-FileHash .\AcronymHunter.exe` must match `CHECKSUM.txt` and the value from the sender.

**Code:** the full source is `app_gui.py` in this repository. The file-writing and network-blocking code is
at the top of the file, under "ZERO-FOOTPRINT FOLDER SANDBOX & OFFLINE NETWORK KILL-SWITCH".

---

## 9. Change control

Any change to `app_gui.py`, `trainer_gui.py`, `updatepack.py`, `edsign.py`, `Stationkeeper.spec`, `requirements.txt`, `build.ps1`, `base\`, or the
Training Kit (`build_training_kit.ps1`, `training_kit_src\`) can change this statement.
Before sharing a new build: re-run the network and file checks in section 8 and update the version and date at the top.

---

## 10. Why it runs without administrator rights (2.76.0)

**Short answer.** Windows asks for an administrator password only when a program declares that it needs one, or when it
writes to protected, machine-wide places. Stationkeeper does neither, so Windows has nothing to ask permission for.

| Question | Answer |
|---|---|
| When does Windows ask for admin rights? | When a program's manifest requests them (`requireAdministrator`), or when it writes to Program Files, the Windows folder, the machine-wide registry (HKLM), or installs services, drivers or machine-wide shell extensions. Installers (setup.exe, .msi) ask because they do these things |
| What does Stationkeeper declare? | Its exe's manifest says `asInvoker`: run with the rights of the person who started it (the PyInstaller default; `Stationkeeper.spec` sets no `uac_admin`). Windows' installer-detection guesswork does not apply to an exe that declares its level |
| Where does it write? | Only inside its own folder (section 3), which the person who unzipped it owns, plus files the user saves where they choose. No Program Files, no registry, no services, no AppData |
| Is it the Windows sandbox? | **No.** Only the OCR reader (Tesseract) runs in a Windows AppContainer, and that takes rights away: no network (not even loopback) and read access to two folders. Creating an AppContainer needs no admin rights, and a sandbox cannot grant them |
| Then why do other approved apps need admin? | They are installed for every user into protected places, often with services or auto-updaters. On managed PCs IT installs them through a deployment tool that has admin rights, which is also where approval happens |

**Does it make Stationkeeper less of a threat?** Its ceiling is lower, which helps: without admin rights it cannot change
Windows, install services or drivers, change security settings, or touch other users' files. It is not a clean bill of
health: a program running as you can read and write everything you can (documents, mapped drives, synced folders), and
most data-stealing malware runs without admin rights too. Stationkeeper's protection comes from what it does and does not
contain: no network code, a build that fails if any program file links a networking API (section 4), the OCR reader in
the no-network AppContainer, pinned third-party components listed in the SBOM and checked against the OSV advisory
database at every release, read-only document handling with hardened XML parsing, and signed update packs (section 11).

**Is it a security risk?** The honest list:

| Risk | What it means | What reduces it |
|---|---|---|
| **Policy** | Running without admin is not approval. It runs because the PC does not block unknown programs in user folders (AppLocker or Windows Defender Application Control). IT can enforce that at any time, and most companies require approval for any software, portable or not | Submit it to IT security with this file, the SBOM (`Stationkeeper_US_SBOM.cdx.json`) and the published checksums. A company code-signing certificate would let IT allow it by publisher |
| **Program files in a folder you can change** | Program Files is protected by admin rights; your own folder is not. Other malware running as you could change Stationkeeper's files (for example plant a DLL). This is the one way an IT-installed app is better protected | **Check program files** (Settings > Updates) compares every file with this version's list and names changed, missing and extra files. Update packs carry the publisher's signature. Keep the folder on a local, encrypted drive |
| **Not code-signed** | Windows cannot show a verified publisher; only the published SHA-256 proves which exe is genuine | Compare `Get-FileHash` with the release's checksum file; update packs are signed (section 11) |
| **The in-process network block** | The Python-level block (section 2) is defense in depth inside the app's own process, not an operating-system boundary | The app contains no network code (audited at every build); the OCR reader, which reads untrusted pictures, runs in the AppContainer, which is an operating-system boundary |

## 11. Update packs (2.76.0)

Install Stationkeeper once (2.76.0 or later); each new version then comes as one `.skupdate` file.

| Question | Answer |
|---|---|
| What can a pack change? | Program files only: `Stationkeeper.exe` (or `StationkeeperTraining.exe`), `_internal\`, `README.txt`, `OVERVIEW.md`, `SECURITY.md`, `CHECKSUM.txt`. Never `config\`, `acronym_database.csv`, efforts, logs or training data. A path outside these, a drive letter, `..`, a reserved device name, or a file in the zip that the signed list does not name, stops the install before anything changes |
| How is a pack proved genuine? | `update_info.json` lists every program file of the new version with its SHA-256. The publisher signs it with an Ed25519 private key that stays on the build PC (never in GitHub, never in a package). The app holds only the public key (`updatepack.PUBLIC_KEYS`) and refuses a pack whose signature does not match; every file is checked against its signed SHA-256 as it is unpacked. Verified: a pack signed with another key, a pack with one changed byte in its list, and a pack with a swapped file were all refused with nothing changed |
| Is it riskier than downloading a new copy? | No. A downloaded zip is trusted only if someone compares its SHA-256 by hand; a pack is checked by the app, automatically, against a key an attacker does not have. The new asset to protect is the signing key: whoever holds it can make packs every copy accepts. If it is lost or exposed, publish one full download with a new key |
| Does the app go online? | No. The person picks the file. There is still no update check, no download and no network code |
| Can it install an older version? | No. A pack must be newer than the copy. **Undo last update** goes back exactly one step, from the files kept in `_update\backup\` |
| What if it stops part-way? | Files are moved, not overwritten (Windows allows a running program's files to be renamed). Any failure moves everything back at once; a crash or power cut part-way is put back at the next start, before the program loads anything else |
| Admin rights? | None. It changes only the folder the person owns. If IT installed the program in a protected folder, the install fails safely and says so |
| What can IT automate? | `Stationkeeper.exe --apply-update <pack>`, `--undo-update`, `--check-program` with no window; results in `logs\update.txt` |
| How is it tested? | Every release build installs a signed test pack into a copy of the built program (replacing the running exe), starts it, checks every program file, undoes the update and starts it again |
