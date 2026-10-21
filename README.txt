ACRONYM HUNTER (Portable, Offline)
==================================

RUN
  0. If you received the zip by email, Teams, or download: right-click the zip > Properties >
     check "Unblock" > OK, BEFORE unzipping. This clears the internet-download flag Windows adds.
  1. Unzip anywhere (Desktop, USB drive, network share).
  2. Open the AcronymHunter folder and double-click AcronymHunter.exe.
  3. Click "Select Files" or "Scan Folder".
  Supported: PDF, DOCX, XLSX, PPTX, PNG, JPG, TIF, BMP, WEBP, GIF, and vector graphics
  (SVG, EMF, WMF, including Visio and draw.io diagrams pasted into Office files).

VECTOR GRAPHICS (SVG, EMF, WMF)
  Text stored inside a diagram is read directly: exact, fast, no OCR. Diagrams whose labels were
  turned into outlines are drawn as a picture and read by OCR. Locations say "(Vector text)" or
  "(Image)" so you know which method found each term.

PROJECTS: SCAN A FOLDER AGAIN AS IT CHANGES
  Project > New Project... : pick the folder that holds the documents. The app creates
  <folder name>.ahproj in that folder and scans everything.
  Rescan Project : reads only new or changed files, reuses saved results for the rest (seconds,
              not minutes). New files in the folder are picked up automatically.
  The Change column shows New, Changed, Unchanged, or No longer found. Status filters
  "New since last scan", "Changed since last scan", and "No longer found" isolate them.
  "No longer found" rows stay until you choose Project > Clear "No longer found" items.
  Your definition choices and "+ Add Item" entries are saved in the project and reapplied.
  Full Rescan : reads every file again (use after changing OCR settings or models).
  One editor at a time: if a colleague has the project open, you can open it read-only
  (view and export) or take over once they have finished.
  The project file holds file names, sizes, dates, the terms found, your choices, and the
  history. It never holds sentences or document text: it is no more sensitive than the
  exported CSV. Treat it at the same classification as the documents' term list.

ADDING YOUR OWN ITEMS
  "+ Add Item" adds a term the scan did not find (type, definition, where you saw it). It appears
  marked "Added manually", is included in Export CSV, and stays through rescans until you select it and
  click "Remove Item". Tick "Also save to the database" so future scans find it on their own.

ADVANCED TOOLS
  The "Advanced" switch (top right) shows Fix OCR, OCR Fixes, and Region Trainer (Trainer package only).
  Off by default. Most users never need them.

READING THE RESULTS
  Text size:  A- / A+ buttons, Ctrl + / Ctrl - , Ctrl + mouse wheel. Ctrl 0 resets. Remembered next launch.
  Sort:       Click any column header. Click again to reverse. The arrow shows the sorted column.
  Select:     Ctrl+click or Shift+click selects several rows; Ctrl+A selects every row shown.
              With several selected, "Exclude N" excludes them all in one step (you confirm first).
  Filter:     Type (Acronym, Unit, Abbreviation...), Status (Needs choice, New candidates...),
              and Search (matches term or definition). "Clear" resets all filters.
  Scroll right with the bottom scrollbar to read long Locations.
  Locations:  PDF page, PowerPoint slide (plus notes/chart/SmartArt and the picture's name),
              Word section heading, header/footer, or Excel sheet.
  "Not scanned" rows list content the app could not open, such as linked pictures,
              and where they are. Use Status > "Errors / not scanned" to see them.

FIXING OCR MISREADS (Advanced switch on)
  If a term in a picture is misread (RFF instead of RFP): select the row, type the correct term
  in the box, click "Fix OCR". Future scans report it correctly.
  To review, edit, or undo fixes: click "OCR Fixes" (top right). "Undo Last Entry" reverses
  an accidental Fix OCR.

KNOWLEDGE UPDATES (trained models + team database)
  This download contains no terms: the acronym database starts empty. Your team's knowledge (trained OCR models, the
  shared acronym database, OCR fixes, ignore list) comes as a Knowledge Pack from the approved
  SharePoint folder:
    Knowledge > Install Knowledge Pack... > pick the newest AcronymHunter_Knowledge_<date>.zip
  The pack is checked first: any damaged or altered file and nothing is installed.
  Models are replaced. Database, fixes, and ignore list are merged add-only: your own rows,
  edits, and Exclude choices always win.
  Knowledge > Undo Last Knowledge Change puts back exactly what the last install replaced.
  With a project open, the app offers to rescan it with the new knowledge.
  Advanced (for whoever trains): Load Trained Models (Training Kit output) and Export Knowledge Pack.
  Knowledge Packs hold what was learned from internal documents: approved SharePoint ONLY,
  never GitHub, email, or personal storage.

ONEDRIVE AND SHAREPOINT
  Works on files in a OneDrive or SharePoint folder synced to this PC (it shows in File Explorer).
  Browser-only SharePoint links do not work: click "Sync" or "Add shortcut to My files" first.
  Your files are safe: the app opens them read-only and never changes, locks, or re-saves them.
  Cloud-only files (cloud icon) are downloaded by the OneDrive app when opened. That download is
  OneDrive's own traffic inside your organization's Microsoft 365, not this app's. For a big
  folder, right-click it > "Always keep on this device" first; scans run faster.
  A project file, its lock, and CSV exports saved in a synced folder upload like any other file,
  so everyone with access to that folder sees them (terms and file names, no document text).
  Across PCs the project lock only works as fast as OneDrive syncs. On a shared folder, have one
  person run the project. If OneDrive makes a conflict copy (Name-PCNAME.ahproj), keep the newer one.
  Files with an encryption sensitivity label cannot be read; they show as "Could not read".
  Keep the AcronymHunter app folder itself OUT of OneDrive: its scratch files and Trainer samples
  would sync to the cloud.
  Whether controlled documents (CUI, ITAR) may live in that OneDrive or SharePoint is your
  organization's decision. The app does not change it. When in doubt, scan local copies.

REGION TRAINER (AcronymHunterTrainer.exe, only in the "WithTrainer" package)
  Not included in the standard AcronymHunter_Portable.zip. Open a file, drag a box around text in a
  picture. Each line OCR found gets a number (matching the box on the picture) and a color:
    GREEN = the scanner keeps this reading (it can appear in results).
    RED   = low confidence; the scanner already ignores it.
  Pick one choice per line, then click Save Choices:
    Skip          Leave it out.
    Save as text  It is real text. Fix the spelling in the box first (typing picks this choice).
    Not text      Diagram lines, arrows, or specks read as letters or Asian characters. Teaches the
                  model that spot is background. If the line was GREEN, that exact reading also goes on
                  config\ocr_ignore.csv so the scanner drops it from pictures on the next scan.
                  Typed document text is never affected. "Ignore List" opens the file to review.
  "Add OCR Fixes from Corrections" makes the scanner fix a misread word right away.
  "Undo Last Save" removes everything the last save added, including ignore-list entries.
  "How training works" explains how samples become a better model. "Prepare Training Package"
  gets them ready for training (TRAINING_GUIDE.md section 8).
  Samples go to training_data\ in this folder (crops of your documents; handle them accordingly).

WHAT STAYS IN THIS FOLDER
  acronym_database.csv   Master list. Include / Exclude rules. Edit in the app or in Excel.
  config\                OCR corrections (Fix OCR), OCR ignore list (Not text), OCR settings,
                         optional replacement OCR models.
  training_data\         Trainer samples (WithTrainer package only; created when you save one).
  config\knowledge_*     Installed pack record and backups for Undo (created on first install).
  _local_sandbox\        Scratch space, created on launch, cleared on exit.
  logs\error.log         Written only if something fails. Send this file when reporting a problem.

  The app makes no network connections and writes no files outside this folder
  (except an Export CSV report and project files, saved where you choose). To remove it, delete the folder.
  Windows itself keeps generic records such as recently used file names; details in SECURITY.md.

MORE INFORMATION (in this folder)
  OVERVIEW.md   How the app works in plain language, plus the full security assessment for IT.
  SECURITY.md   Detailed security statement and the steps to verify it yourself.
  Both are plain text; open them in Notepad or any Markdown viewer.

DATABASE FORMAT (acronym_database.csv)
  Term,Definition,Category,Action
  SOW,Statement of Work,Acronym,Include
  CEO,Chief Executive Officer,Acronym,Exclude
  Columns can be in any order. The app finds them by header name and keeps your order, your header
  names, and any extra columns (Notes, Source...) when it saves. Accepted header names:
    Term: Term, Item, Acronym, Abbreviation   Definition: Definition, Meaning, Description, Expansion
    Category: Category, Type                   Action: Action, Rule, Include/Exclude
  Close the CSV in Excel before clicking Include or Exclude in the app.
  Symbols (°, µ, Ω, Δ, Cyrillic, math letters) are fully supported. In Excel, save with
  File > Save As > "CSV UTF-8 (Comma delimited)". Avoid plain "CSV (Comma delimited)": it turns
  symbols into "?". The app also reads "Unicode Text" (UTF-16) files, and re-saves them as UTF-8.

VERIFY YOUR COPY (optional)
  CHECKSUM.txt holds the exe fingerprint. In PowerShell:
    Get-FileHash .\AcronymHunter.exe
  The Hash must match CHECKSUM.txt and the value the sender gave you.
  The app is not code-signed. Right-click > Properties > Details shows the publisher and version.

TROUBLESHOOTING
  "Windows protected your PC": click More info > Run anyway (the app is unsigned).
  Nothing happens or "blocked by your administrator": your organization's policy blocks
  unsigned programs. Ask IT to approve it; do not try to bypass the policy.
  First launch takes 5 to 15 seconds while files load from disk.
