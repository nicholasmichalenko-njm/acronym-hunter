# Acronym Hunter: Security and Data-Handling Statement

**Version covered:** 1.0.1 (exe SHA-256 recorded in `AcronymHunter_SHA256.txt` and `CHECKSUM.txt`)
**Verified:** 2026-10-20 on the developer's Windows PC, from a fresh unzip of the shipped zip
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
  |  1. Extraction      PyMuPDF (PDF), zipfile + lxml (Word/PowerPoint/Excel XML), openpyxl   |
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

There is no server, no cloud service, no account, no license check, no telemetry, and no auto-update.
The app is a single process. It starts no child programs while scanning (verified: 0 child processes).

---

## 3. Every file the app writes

Complete list from a line-by-line audit of `app_gui.py` (every `open(... "w"/"a")`, `os.replace`,
`os.makedirs`, and `rmtree` call):

| Path (inside the app folder) | Contents | When | Sensitive? |
|---|---|---|---|
| `acronym_database.csv` | Terms and definitions | Include / Exclude buttons | Contains terms you add |
| `config\ocr_corrections.csv` | Misread to correct-term pairs | Fix OCR button | Contains terms you add |
| `logs\error.log` | Error messages and **file paths** | Only when something fails | File names/paths |
| `logs\selftest.txt` | Scan results | Only with `--selftest` | Terms found |
| `_local_sandbox\settings.json` | Text size, last folder used | When you change them | Folder path |
| `_local_sandbox\temp\` | Temporary files, incl. OCR engine config | During a scan; **emptied on exit and on next start** | No document content |

**The one write outside the folder is yours to direct:** *Export CSV* saves the results report wherever you
choose in the save dialog.

**One action hands a file to another program:** *Edit Database CSV* opens `acronym_database.csv` in your
default spreadsheet program (usually Excel), which then behaves like any Excel session (see section 6).

Temporary-file redirection: the app sets `TEMP`, `TMP`, and `TMPDIR` to `_local_sandbox\temp` before loading
any library, so libraries that create temp files create them inside the folder.

---

## 4. Why no internet is needed or possible

| Check | Result |
|---|---|
| Libraries with network features used by the app | None. PyMuPDF, lxml, openpyxl, OpenCV, ONNX Runtime, RapidOCR, RapidFuzz, CustomTkinter have no network calls in the code paths used |
| OCR models | Bundled inside `_internal\rapidocr_onnxruntime\models` (3 ONNX files). Never downloaded |
| ONNX Runtime usage telemetry | Disabled in code (`disable_telemetry_events()`) |
| Runtime network block | `socket.connect` to any non-loopback address, all DNS lookups, and `urllib` are replaced with functions that refuse. Tested: raw socket, direct IP, DNS, urllib HTTPS, and http.client HTTPS all refused |
| Live monitoring of the exe (100 ms polling), full scan of 8 files + 20 s idle | **0 TCP connections, 0 UDP sockets, 0 child processes** |

The app works identically with the network cable unplugged or Wi-Fi off.

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

Any change to `app_gui.py`, `AcronymHunter.spec`, or `requirements.txt` can change this statement.
Before sharing a new build: re-run the network and file checks in section 8 and update the version and date at the top.
