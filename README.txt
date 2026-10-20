ACRONYM HUNTER (Portable, Offline)
==================================

RUN
  0. If you received the zip by email, Teams, or download: right-click the zip > Properties >
     check "Unblock" > OK, BEFORE unzipping. This clears the internet-download flag Windows adds.
  1. Unzip anywhere (Desktop, USB drive, network share).
  2. Open the AcronymHunter folder and double-click AcronymHunter.exe.
  3. Click "Select Files" or "Scan Folder".
  Supported: PDF, DOCX, XLSX, PPTX, PNG, JPG, TIF, BMP, WEBP, GIF.

READING THE RESULTS
  Text size:  A- / A+ buttons, Ctrl + / Ctrl - , Ctrl + mouse wheel. Ctrl 0 resets. Remembered next launch.
  Sort:       Click any column header. Click again to reverse. The arrow shows the sorted column.
  Filter:     Type (Acronym, Unit, Abbreviation...), Status (Needs choice, New candidates...),
              and Search (matches term or definition). "Clear" resets all filters.
  Scroll right with the bottom scrollbar to read long Locations.
  Locations:  PDF page, PowerPoint slide (plus notes/chart/SmartArt and the picture's name),
              Word section heading, header/footer, or Excel sheet.
  "Not scanned" rows list content the app could not open, such as linked pictures or
              vector diagrams, and where they are. Use Status > "Errors / not scanned" to see them.

FIXING OCR MISREADS
  If a term in a picture is misread (RFF instead of RFP): select the row, type the correct term
  in the box, click "Fix OCR". Future scans report it correctly.

WHAT STAYS IN THIS FOLDER
  acronym_database.csv   Master list. Include / Exclude rules. Edit in the app or in Excel.
  config\                OCR corrections (Fix OCR), OCR settings, optional replacement OCR models.
  _local_sandbox\        Scratch space, created on launch, cleared on exit.
  logs\error.log         Written only if something fails. Send this file when reporting a problem.

  The app makes no network connections and writes no files outside this folder
  (except an Export CSV report, saved where you choose). To remove it, delete the folder.
  Windows itself keeps generic records such as recently used file names; details in SECURITY.md
  in the project repository.

DATABASE FORMAT (acronym_database.csv)
  Term,Category,Definition,Action
  SOW,Acronym,Statement of Work,Include
  CEO,Acronym,Chief Executive Officer,Exclude
  Close the CSV in Excel before clicking Include or Exclude in the app.

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
