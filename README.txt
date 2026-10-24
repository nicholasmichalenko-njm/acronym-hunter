ACRONYM HUNTER (Portable, Offline)
==================================

ONE PROGRAM (from v1.7.0)
  AcronymHunter_US.zip holds one program, AcronymHunter.exe. It reads text in pictures with Tesseract OCR
  (Apache 2.0; created at HP, developed by Google) and Google's English model.
  - Tesseract is built from its source without any network library, and it runs inside a Windows sandbox
    that has no network permission. No Chinese-origin code or models. No GPU, no internet, no separate kit.
  - The Trainer is a window inside the program (Advanced > Trainer, or right-click a result).
  - To give colleagues a copy with no training features: set "allow_training": false in
    config\app_settings.json before sharing. Nothing gets saved to training_data\ then.
  Older versions: v1.6.0 (two packages), v1.5.1 (RapidOCR + PaddleOCR models from Baidu).

SECOND READER: docTR (from v2.1.0)
  Every picture is now read twice: by Tesseract and by docTR, a neural text finder and reader (Mindee, France,
  Apache 2.0) running on ONNX Runtime (Microsoft, MIT). docTR finds text Tesseract misses: labels inside colored
  boxes, words touching diagram lines, photographed whiteboards, busy backgrounds, faint or low-resolution text.
  - In a test of 13 hard diagrams (146 labels), Tesseract alone found 56%; Tesseract + docTR found 97%.
  - Where Tesseract already read a word, its reading stands. docTR adds text Tesseract never found, and a longer
    reading only when it is at least 95% sure (TWTA where Tesseract read WTA). Nothing is counted twice.
  - Extra passes: large pictures are read in tiles, dark pictures also inverted, and pages with vertical labels
    also turned 90 and 270 degrees.
  - Cost: about 1 second more per picture (several seconds for very large drawings). Typed text is not affected.
  - The models were exported by this project from Mindee's official weights (vendor\doctr\SOURCE.txt has every
    SHA-256). They load from the app's own folder; nothing is downloaded.
  - To turn it off: set "doctr_enabled": 0 in config\ocr_settings.json.

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
  Project > New Project from a Folder... : pick the folder that holds the documents. The app creates
  <folder name>.ahproj in that folder. Click Scan Project to read everything the first time.
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

SAVING A ONE-OFF SCAN (reuse it later, no rescan)
  Scanned a document or folder with Select Files or Scan Folder and want to keep the results?
    Project > Save Current Results as Project...
  Nothing is read again. The project file stores what was just found. Later, Project > Open Project,
  then Rescan Project reads only files that are new or changed and reuses the rest.
  A saved set of files (not a whole folder) can grow: Project > Add Files to Project.
  New Project from a Folder does not scan by itself: click Scan Project when ready.

THE MAIN WINDOW (v1.9.0)
  Top bar: Project, Select Files, Scan Folder, Export CSV, + Add Item, Client Lists on the left.
  On the right: Improve Reading, Tools (Trainer, Knowledge, Edit Database CSV, OCR Fixes, preview on/off),
  and the Advanced switch (adds Fix OCR and the OCR Fixes list).

PREVIEW PANE: SEE WHAT PRODUCED A RESULT, AND FIX IT THERE
  Click any result. The pane on the right shows where it was found:
    [picture] or [page]  The picture or PDF page, read again, zoomed in on the term (yellow box).
                         Green = readings the scanner keeps, red = low confidence (ignored), orange = the
                         term in a PDF page's typed text. "Show whole picture" zooms out.
    [typed text]         Read exactly from the file: nothing to correct. Exclude it if it is not a real term.
  Pick another location from the list at the top of the pane. Click any box to select that reading.
  Fix it right there:
    Correct + Teach  Fix the spelling, then click. Saved as a corrected line for Improve Reading, and
                     single-word fixes (RFF > RFP) apply on the next scan right away.
    Not text         A diagram line or speck read as letters: ignored in pictures from the next scan.
    Exclude term     Not a real term: never reported again.
    Undo last save   Takes back the last Correct + Teach or Not text.

CODES AND DESIGNATORS (v1.9.0)
  Codes are reported whole as "Designator": PCU-28V, MIL-STD-1553B, RS-422, PN 4521-003A, ST-200X, J1-P3.
  Their pieces are no longer reported as stray units or letters ("V", "B", "A"). Mixed-case acronyms
  such as DoD, DoE, IoT are found too.

CHECK IN PICTURE AND IMPROVE READING (teach the reader your documents)
  1. Right-click a result > "Check in picture". The picture it came from opens in the Trainer, read
     again, with that term outlined in yellow. Typed-text results have nothing to check.
  2. Fix what is wrong: correct the spelling and pick "Save as text", or mark "Not text". Click Save Choices.
  3. Improve Reading (top bar, or the green bar when corrections pile up) opens one window with one
     action: Teach and Apply. A progress bar walks through 4 steps (prepare lines, measure the current
     reader, teach, measure the new reader). It shows the score before and after, for example
     "Words read correctly: 50% before, 93% after", plus lines it now reads correctly.
     It becomes your reader ONLY if it reads better. "Put back the previous reader" undoes it.
  4. Rescan when it offers (only files with pictures are read again).
  5. Share: "Share with team..." saves a Knowledge Pack (your reader + database + OCR fixes + ignore list)
     for colleagues to install. Improve Reading = better reader on THIS PC. Knowledge Pack = share it.
  Rescans after Improve Reading re-read only files that contain pictures; the rest reuse saved results.

WORDS AT THE END OF A SENTENCE (v1.8.0)
  "award." or "system." at a sentence end is no longer reported as an abbreviation: ordinary English words
  (a built-in list of common words, SCOWL) are skipped. Real abbreviations are still reported, including
  ones that are also words, such as "approx.", "Fig.", "No.", "Ref.", "temp.", "spec.". An all-caps term
  before a period ("CCB.") is reported once, as the acronym. Anything else wrong: select it and Exclude.

WHAT THE TRAINER SHOWS YOU
  Only what the scanner has to OCR: pictures inside Word, PowerPoint, and Excel files (including
  vector diagrams), image files, and PDF pages (shown whole, since a scanned page is one picture).
  Typed text on a slide or page is read exactly from the file, letter for letter, so it never needs
  training and never appears in the Trainer.

CANCEL A SCAN
  "Cancel Scan" (under the status line, shown while scanning) stops at the next page or slide.
  The table returns to the results from before that scan. In a project, files already read are kept,
  so the next rescan continues from there.

CLIENT ACRONYM LISTS (from an RFP or the customer)
  "Client Lists" adds the client's acronym list: CSV, TXT, Excel, Word, or PDF (a two-column table or
  lines such as "SOW - Statement of Work"). You see a preview of the pairs read before it is added.
  Client definitions take precedence over the database for defining and choosing between meanings:
    Purple row, "Client list"                    = found term matches the client list
    Pink row, "* Client list (database differs)" = the database has a different meaning too
  Every meaning appears in the choice list labeled [Client] or [Database]: pick either.
  Status filters "Client list" and "Client and database differ" show just those rows.
  With no client lists added, scans work exactly as before. In a project, the lists are saved with it.
  Client lists stay on this PC and in the project file: never in Knowledge Packs or GitHub.

FIRST USE OF EACH ACRONYM (where to define it)
  The "First Use (acronyms)" column shows, for each acronym, where it first appears in each file
  (reading order: pages, slides, Word sections, then headers/footers and pictures) and whether that
  first use is written the proposal way: Spelled Out Words (ACR).
    check defined         = first use is "Words (ACR)"
    X defined later       = first use is bare; "(ACR)" appears later. Move the definition up.
    X not defined         = never written as "(ACR)" in that file
    ? check               = found through an OCR correction; look at it yourself
  Each file counts on its own, since each volume must define its own acronyms.
  Units and abbreviations never get a First Use entry.
  Status > "Not defined at first use" lists every acronym to fix. Double-click a row for every file.
  "First found / Last found by a scan" (projects only) are scan dates, not places in the document.

EQUATIONS AND SYMBOLS (from v2.0.0)
  Every scan also finds equations and checks their symbols.
  - Word and PowerPoint equation-editor math is read exactly: subscripts, Greek letters, accents
    (m-dot, v-bar, x-hat), fractions, roots and sums.
  - Typed math in any file ("q = ½ ρ V²", "σ_b = M_b · c / I_x") is found in the text.
  - Equations in pictures are read by OCR, listed for review as "CHECK EQUATION PICTURE", and shown
    in the preview pane. OCR reads letters well but can miss subscripts, Greek letters and fraction bars.
  Each symbol gets one row with a status:
    Defined in document    a "where ṁ is the mass flow rate" sentence, a nomenclature list, or a
                           Symbol/Meaning table defines it
    SYMBOL NOT DEFINED     no file and no database entry defines it; fix before submission
  Each equation row lists its symbols and which ones are not defined. Status filters
  "Equations and symbols" and "Undefined symbols" show them. Select a symbol to see its meaning and
  every equation that uses it. "TRL = 6" and "cost = $4.2M" are not treated as equations.

MATH READER ADD-ON (from v2.2.0, optional)
  Equations that are pictures can be read exactly with the math reader: IBM's Granite-Docling-258M (Apache 2.0)
  on PyTorch, in its own program. In a test of 50 aerospace equations it read 96-98% of symbols (subscripts,
  Greek letters, dots, fractions) where the text reader managed about 10%.
  Install: unzip AcronymHunter_MathAddon.zip into the AcronymHunter folder, so math_addon\ sits next to
  AcronymHunter.exe. Restart the app. (About 1.4 GB on disk. Without it, everything else works as before.)
  Use (only the pictures you choose are read, so scans stay fast):
  - Select one or many "Equation (picture)" rows, right-click > Read equation pictures with the math reader.
  - Or click "Read this equation with the math reader" in the preview pane.
  - Or Tools > Read all equation pictures.
  About 5 seconds per small equation on a laptop CPU; whole figures take longer. A progress window shows each
  picture and has a Stop button. Each equation becomes an Equation row with its symbols, and the OCR pieces of
  that picture (stray "units" and "symbols") are removed. Results are saved by picture fingerprint in
  config\math_results.json, so a picture is read only once; delete that file to forget them.
  Security: the math reader runs only inside the same no-network Windows sandbox as Tesseract. If the sandbox
  cannot start, it does not run. It loads IBM's model only from safetensors files, after checking every file's
  SHA-256 (math_addon\math_models.json).

SYMBOL PICKER (from v2.3.0)
  Type Greek letters, subscripts, superscripts, math operators, accents and units without leaving the app.
  - Click the Ω button next to a correction field (preview pane, Trainer, the Definition / Fix OCR field,
    Add Item, OCR Fixes), right-click any of those fields > Symbols..., or press Ctrl+Shift+Space.
  - The Symbols window stays open and inserts into the field you clicked last, so you can fix several readings.
  - Tabs: Recent, Greek, Subscript, Superscript, Operators, Accents, Units, Arrows/sets.
  - Search by name: "sigma", "dot", "sub 2", "degree", "ohm".
  - Accents attach to the letter before the cursor: type m, click the dot accent, get ṁ.
  - x₂ Sub / x² Sup / Normal turn the selected text (or the character before the cursor) into subscript,
    superscript or normal text: select "sp" in "Isp", click Sub, get Iₛₚ. Also on the right-click menu.

FULL TEXT MODE (from v2.0.0)
  Tools > Full Text pulls out every word the scanner reads: typed text exactly, picture text through
  the same sandboxed OCR reader, and equations in linear form with their symbols. Choose files, a
  folder, or the files from the last scan, click Read All Text, then Save as one .txt, Save one .txt
  per file, or Copy. Sections read by OCR are marked "[read by OCR: check spelling]".
  The text carries the same classification and markings as the source files. Handle it the same way.

EXPORTING FOR AUTHORS
  Export CSV exports exactly the rows showing (current Type, Status, and Search filters, current sort).
  The file name says which view, for example Acronym_Report_Needs-choice_2026-10-21.csv.
  Columns include Possible definitions (every meaning, client first), Client list definition,
  Database definition, a blank Author decision column for authors to fill in, and
  First use (acronyms: define here).

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
  Locations wrap onto up to 3 lines. Double-click any row to see every location and meaning in full.
  Locations:  PDF page, PowerPoint slide (plus notes/chart/SmartArt and the picture's name),
              Word section heading, header/footer, or Excel sheet.
  "Not scanned" rows list content the app could not open, such as linked pictures,
              and where they are. Use Status > "Errors / not scanned" to see them.

FIXING OCR MISREADS (Advanced switch on)
  If a term in a picture is misread (RFF instead of RFP): select the row, type the correct term
  in the box, click "Fix OCR". Future scans report it correctly. The download ships with no fixes.
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

TRAINER (a window inside AcronymHunter.exe: Advanced > Trainer, or right-click > Check in picture)
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
  training_data\         Trainer samples (created when you save one; never with allow_training false).
  config\knowledge_*     Installed pack record and backups for Undo (created on first install).
  _local_sandbox\        Scratch space, created on launch, cleared on exit.
  logs\                  Content-free diagnostics: errors and which controls are clicked, never file names,
                         terms or document text. Feedback > Export for Claude bundles them with your reports.
  feedback\              Feedback reports you write (Feedback button, Ctrl+Shift+F).
  config\choices.json    Definition choices made with Apply Choice, reused on every later scan.

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

HOW IT WORKS GUIDE (2.3.1)
Click ? in the top bar (or press F1) for a short guide with screenshots: scanning, the results table,
Fix OCR vs Training (Correct + Teach and Improve Reading), the picture preview, symbols, equations, sharing.

2.3.2: SCAN AGAIN, STICKY CHOICES, BETTER PREVIEW, FEEDBACK
- Scan Again rescans the same files (or the same folder, including new files) with one click.
- Apply Choice is remembered for every later scan on this PC (config\choices.json); an open project's choices win.
- Preview: Find < > steps through every find of the term, across all its locations. Zoom with the wheel or + / -,
  drag to move, Whole shows the whole page, Enlarge opens a big window. Typed text in Word, PowerPoint and Excel is
  shown with every match highlighted. Words only the second reader found get cyan boxes.
- Feedback button (Ctrl+Shift+F): bugs, improvements and ideas about features, plain text only. A content guard
  blocks text that matches your documents' terms, definitions, file or folder names. Export for Claude makes one
  text-only zip after showing you everything in it.
- Logs are content-free: fixed messages, error types, code locations, counts. Usage logging records which controls
  are clicked (by internal name), to improve the app; turn it off with "usage_logging": false in config\app_settings.json.

EFFORT LIST AND CUSTOMER DEFINITIONS (2.4.0 / 2.5.0)
- Effort button: one Excel list per proposal (Effort List, History and About sheets). New effort asks for a name,
  where the list lives (desktop or a synced SharePoint folder), the first-use rule (per volume or the whole
  submission), and the customer documents folder.
- Add to effort list (bottom bar), and right-click > Effort list: Approve (SS approver names, several allowed),
  Needs an author, Not a term in this effort, Back to Proposed, Remove.
- Every scan reads the list (edits made in Excel included): approved definitions win; rejected terms are hidden for
  this effort only. Status filters: In effort list, Not in effort list, Effort: needs author, Effort: approved.
- Customer documents: every scan reads definitions written in the customer documents folder ("Spelled Out (ACR)",
  "ACR (Spelled Out)", acronym tables and glossaries). The customer's definition beats the database; two different
  customer definitions ask you to choose. Filters: Customer documents, Customer and database differ.
- Effort > Export for approvals: a workbook with Needs author, Conflicts, Approved and All sheets.
- If Excel has the list open, the app asks you to close it and keeps the change until it can save.
- The list holds customer content: keep it on this PC or SharePoint, never in GitHub or email outside the team.

TRAINED READER FROM THE TRAINING KIT (2.6.0)
- The docTR Training Kit trains the second reader on your own Trainer samples, fully offline. Two downloads:
  AcronymHunter_TrainingKit_docTR.zip (any PC, processor only) and the GPU version for NVIDIA RTX 50 / RTX PRO
  cards (two parts: put both in one folder and run Join_AcronymHunter_TrainingKit_docTR_GPU.cmd, which checks
  the fingerprint).
- Copy Trainer samples (training_data\<name>) into the kit's samples folder and run Train.cmd. The kit keeps 10% of
  your samples aside, measures before and after, and exports a model only when it reads them better.
- Install: Tools > Knowledge > Load Trained Models, pick the kit's output\models folder. The app checks every model
  file's SHA-256; a changed file is refused and the bundled models stay in use. Undo returns to the bundled models.
- Export Knowledge Pack now carries trained docTR models, so one person trains and the team installs the pack
  (approved SharePoint folder only).
- The kit blocks every network connection and logs any attempt to kit\logs\network_blocked.log. On an 8 GB card,
  set AH_GPU_MEM_GB=8 before Train.cmd to cap graphics memory.

VOLUME CHECK AND FIRST USE (2.7.0)
- Effort > Check volumes: pick the final volumes. File names set the submission order (Vol 2 before Vol 10).
- First use (acronyms only): each acronym must first appear as "Spelled Out Words (ACR)", restarting in each volume
  or running across the submission (the effort's first-use rule). The report flags: not defined, spelled out later,
  defined with words that differ from the effort list, defined again later, and first uses inside pictures.
- Not in effort list, Not approved, Definition differs (the volume spells it out differently), and Unused (list
  entries no volume uses) each have a tab. Double-click a row to jump to it in the results table and preview.
- Acronym lists for Word: one .docx per volume plus one for all volumes, a sorted Term / Definition table built from
  the effort list. Entries not approved yet are counted so you can clear them first.
- Add missing to the effort list (as Proposed) and Record volumes and first use (fills Used in volumes and First use).
- Export report (Excel): Summary, First use, Not in effort list, Not approved, Definition differs, Unused, and one
  list sheet per volume. Reports and lists hold customer content: keep them on this PC or SharePoint.

COMPLIANCE MATRIX (2.8.0)
- Compliance (top bar) > New from RFP files: pick the RFP documents (Word, PDF, Excel, PowerPoint). Rules list every
  candidate requirement: shall, must, will, should, may, is required to, imperatives (describe, provide, submit...),
  evaluation language (will be evaluated / assessed) and format rules (page limits, fonts, margins, due dates). Each
  row keeps its file, page or section, section title and source passage. No language model is used.
- Each row gets a rule-based Type (Instruction, Evaluation, SOW, Format, Information), Actor (Offeror, Contractor,
  Government), Strength (Mandatory, Desired, Optional), cross-references (C.3.4, Attachment J-2, CDRL A003, FAR) and a
  suggestion: Keep, Drop (Government statements) or Review ('may').
- Triage: K keep, D drop, U undecided, S split a compound requirement. Accept suggestions applies them to the undecided
  rows shown. Filters: Decision, Type, Suggested, Outline, Search.
- Outline tab: start from the Section L headings, import the headings of a Word outline, or type one (1.2 Title,
  Volume I - Technical). Map kept rows; Suggest sections fills only clear matches (same section number, or most of the
  section title's words).
- Re-read RFP (amendment): decisions, mapping and notes stay with unchanged sentences; new ones are marked [New] and
  removed ones [Gone].
- The matrix is one Excel workbook (Compliance Matrix, Outline, Sources with SHA-256, RFP headings, History, About),
  saved a few seconds after each change; edits made in Excel count. Word outline exports the proposal outline with each
  section's kept requirements in a table, then kept requirements not mapped yet.
- The matrix holds customer content: keep it on this PC or SharePoint.

LAYOUT (2.9.0)
- Menu bar: File (Select Files Ctrl+O, Scan Folder Ctrl+Shift+O, Scan Again F5, Project, Export CSV Ctrl+E),
  Edit (Add Item, Client Lists, Find Ctrl+F, Clear filters), Effort, Compliance (Ctrl+M), Tools, View (Sidebar Ctrl+B,
  Preview pane, Advanced, text size Ctrl + / Ctrl - / Ctrl 0) and Help (Guide F1, Feedback, About).
- Sidebar on the left: Scan, Review filters, Effort (Check Volumes), Compliance, Export and More, with text size,
  Advanced, Guide and Feedback at the bottom. Drag its edge to resize; hide it with View > Sidebar or Ctrl+B. The app
  remembers the width and whether it is shown.
- The preview pane is titled Source; locations are listed as Text, Image or PDF page. The results table scales with
  Windows display scaling (A+ / A- still adjust it).

COMPLIANCE MATRIX: LEARNING AND COMPLEMENTS (2.10.0)
- Learn from decisions (and automatically after each save): the app learns which rows the team keeps or drops. The
  Learned column shows the result (Keep / Drop / Review with a percentage) once there are at least 5 Keep and 3 Drop
  decisions; Accept suggestions uses it first, then the rule suggestion. A check on the current matrix reports how often
  the learned model agrees with your decisions, next to the rule suggestions' agreement.
- Privacy: words are turned into numbered buckets before anything is stored. config\compliance_learned.json holds bucket
  numbers and counts only, never RFP text. It travels in Knowledge Packs and installs add-only.
- Suggest sections also learns from rows already mapped: a kept row goes to the section of the most similar mapped rows
  when the rules find no clear match.
- Merge (M) joins rows the rules split. Show page opens a PDF row's page with the sentence highlighted; Open file opens
  any source document (the Sources sheet now records each file's path on this PC).
- Amendment changes (after Re-read RFP) pairs changed sentences with their earlier version and shows the word
  differences as [-removed-] {+added+}, plus added and removed sentences; export to Excel.
- Each release ships a Software Bill of Materials per edition (AcronymHunter_US_SBOM.cdx.json, CycloneDX 1.5): every
  bundled Python package with version, license and PyPI identifier, the native parts (Python, Tcl/Tk, Tesseract,
  eng.traineddata, docTR models, PDFium), and the SHA-256 of every program and model file. Made by tools\make_sbom.py
  at build time from what actually ships.
