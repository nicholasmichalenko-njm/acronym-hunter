STATIONKEEPER (Portable, Offline)
=================================

A TIDY PROGRAM FOLDER AND AN EFFORT FOLDER YOU CAN FIND YOUR WAY AROUND (2.90.0)
  - The download holds the program and one folder of read-me files, nothing else:
        Stationkeeper\
          _internal\               the program itself (leave it as it is)
          About Stationkeeper\     this README, the overview, the security notes and the exe's checksum
          Stationkeeper.exe        double-click to start
    The empty acronym database and the default settings no longer ship: Stationkeeper makes the master database the
    first time it starts, in Stationkeeper Data, and has its settings built in. While it runs, the program folder also
    holds logs\ and _local_sandbox\ (its own working files), and _update\ after an update pack (for Undo).
  - Why _internal\ stays as it is: copies from 2.76.0 on check that an update pack only changes the exe, _internal\ and
    the read-me files, so renaming it would stop update packs working, and a program that hides its own folders is the
    kind of thing antivirus software flags.
  - Copies brought up to date by an update pack get the same layout: the read-me files now live in the program
    (_internal\docs), the update takes the old ones off the top of the folder, and Stationkeeper fills About
    Stationkeeper from them each time it starts. A copy that still holds acronym_database.csv or config\ in its program
    folder (every download before 2.90.0 shipped them) has them moved into Stationkeeper Data\From the old program folder\; the
    copies Stationkeeper uses have been in the data folder since 2.80.0. Nothing is deleted. A program folder IT
    installed in Program Files (where the data lives in the program folder) is left exactly as it is.
  - Your work sits beside the program folder:
        Stationkeeper Data\
          Efforts\
            Kestrel\
              Customer Documents\      the RFP and attachments as the customer sent them
              Volumes\                 your Word volumes
              Response Setup\          the documents writers start from
              Exports\                 acronym lists, status reports, the calendar, reviews, Export all
              Kestrel_Compliance_Matrix.xlsx
              Kestrel_Effort_List.xlsx
              Kestrel_Effort_List - app data\   the app's working files for the effort (a note inside says not to
                                                 edit them; packages and backups carry it)
          acronym_database.csv          your master acronym database
          READ ME.txt                   one line on each item
          config\, feedback\, training_data\   settings, the author list and what you send to improve the reader
  - New effort makes the four folders and uses Customer Documents and Volumes as the effort's folders unless you pick
    others. Every save still asks where to put the file; the dialogs start in the effort's Exports folder (Response
    Setup in its own). An older effort keeps its files where they are; a folder appears the first time something is
    saved into it.
  - Open effort folder (Effort Home and Settings > Efforts) opens the effort's folder in File Explorer.

TEAM DEFAULTS (2.89.0)
  - Settings > Team defaults: one file (.skteam) sets up every PC on the team the same way. Make a team pack ticks
    what it carries: the author list, the team matrix design, banned words and phrases, default gate goals, company
    logos, Effort Home layouts by role, sensitivity markings and team topics.
  - Installing shows what changes, part by part, before anything does. Names, phrases, goals, markings and topics the
    PC lacks are added; nothing of the PC's own is changed or removed. The matrix design, logos and role layouts are
    taken only where the PC has none of its own.
  - Lock: the maker can lock the matrix design, logos, role layouts, default gate goals and markings. A locked part
    replaces each PC's own and stays as the team set it: Settings says so, and the controls that would change it are
    off until the pack is undone or a new pack arrives.
  - Undo puts back everything the last install changed and lifts its locks.
  - The pack is checked before anything is read from it: only the files a team pack holds, each matching its
    fingerprint, pictures that open as pictures. It holds names: keep it on the approved SharePoint folder, never on
    GitHub.
  - Customize Home > Save as the team's layout for this role: what is ticked, in that order, becomes the team's layout
    for the role on this PC, and a team pack carries it.
  - Team topics...: one topic per line. When you take context from a library document, the card offers each team
    topic as a one-click tag. Sensitivity markings...: the markings the team writes (CUI//SP-PROPIN, Proprietary),
    offered in Effort Home > Edit details.

BRANDED EFFORT HOME AND THE CALENDAR AS A FILE (2.88.0)
  - Effort Home opens with the effort's banner: the effort's picture (click the spot to add a mission patch, logo or
    cover image), its name, client and solicitation, the proposal manager, its sensitivity, and the effort's own spots
    (capture manager, contract vehicle, anything: Edit details...). On the right, the due date with a live countdown in
    days, hours, minutes and seconds; it turns amber inside ten days and red inside three.
  - What travels with the effort and what is yours: the banner's details, the picture and the calendar are kept in the
    effort, so everyone who opens it sees the same and packages and backups carry them. The layout of Effort Home is
    yours alone, kept in your settings on this PC.
  - Sensitivity: Not CUI, CUI, Proprietary, or the team's own words. CUI and every marking other than Not CUI show in a
    strip across the top of every page while the effort is open. Stationkeeper marks the screen; it does not decide or
    certify what is CUI.
  - Branding: Settings > Branding holds up to three company logos (a prime and its teammates), in order, shown on a
    light plate at the top of the menu on every page. The Stationkeeper mark and version sit at the foot of the menu.
    The menu, its groups and the page names are in Title Case (Effort Home, Effort Record, Lists to Submit).
  - Customize Home: My role picks a starting layout. Proposal Manager: stage, gate goals, questions, tasks, calendar.
    Production: deliverables, calendar, tasks. Author: My work, tasks, questions, calendar. Reviewer: stage, calendar,
    questions. Capture: stage, customer information, questions. Then tick what shows and set the order; half-width
    sections sit side by side. I am: your name, for My work and the tasks filter.
  - My work (for an author): the compliance requirements you answer, the ones a customer version changed that wait for
    you to confirm (first), your open tasks and the questions assigned to you. Open takes you to the requirement.
  - Calendar > Template...: an Excel workbook with Date, Start time, End time, Time zone, Kind, What, Owner, Stage,
    Location and Details, a Kind drop-down and a sheet that explains each column.
  - Calendar > Import... (.xlsx, .csv or an Outlook .ics): a preview lists every row and what it will do, and nothing
    changes until Apply. Proposal due sets the effort's due date and time to the minute, with its time zone. Stage
    start and Stage end set the planned dates of the stage named in Stage. Task adds a task with its owner and due date.
    Questions due, Review, Meeting, Orals, Milestone and Other go on the calendar with their times, place and details;
    pick a day to see them (Remove takes one off). Importing again updates what matches instead of adding copies, and
    Undo import puts the calendar back as it was before the last import.
  - Calendar > Export...: every date the effort has, with its details, to Excel in the template's columns (it imports
    back) or to an Outlook calendar file (.ics).

DELIVERABLES BOARD (2.87.0)
  - Deliverables moved to the EFFORT group, right after Effort home. It opens as a board: one card per deliverable,
    the ones that need action first (no owner, over the page limit), then the ones that need attention, then the ones
    on track.
  - A card shows the owner, status, pages against the limit (a bar), the volume it holds in the response structure,
    that volume's requirements and how many have an author, library context attached to its sections, and the first
    things missing: no owner, no working file, not linked to a volume, requirements with no author, requirements a
    customer version changed that wait for their owner, a newer customer form, acronym list entries to finish.
  - Click a card to see everything about it beside the board: what is missing, the volume (pick another to relink
    it), its requirements with their author and state (double-click one to open it in Assign), what changed, its
    latest Submission check, its context and its files. Edit..., Done for this stage and Check this volume are there.
  - A Volume deliverable links to the response volume with the same name or number (Volume II, Vol 2). Edit... has a
    Volume choice too.
  - Effort home has a line for the deliverables (click it for the board) and the dashboard counts the ones that need
    attention. View: List shows the table as before.

RESPONSE QUALITY (2.86.0)
  - The ACRONYMS and QUALITY groups are now one group, Response quality, in the order the work happens: Customer terms
    (start), Effort list (throughout), Submission check and Lists to submit (end). Each page says which end it serves.
  - Customer terms: Scan the customer documents reads the newest version of every customer document in the Library,
    with no picking. Their terms are offered to the effort list with the customer's definitions first.
  - Effort list: the glossary writers work from, not the list you submit. A filter shows the terms used in the
    submission volumes, or not used in any, from the latest Submission check.
  - Submission check: the Word volumes you will submit are marked once (and Deliverables' volumes with a Word file are
    included); Check the submission volumes checks them all. Check other Word files... stays for a one-off check.
  - Lists to submit: one list per volume, one master list, or both, set once for the effort. Each list holds only the
    terms that volume uses, with the effort list's definitions; terms that need a definition or approval are marked.
    Effort-list terms no volume uses are left out of every list and shown on a Left out tab. Export to Word (one file
    per list) and Excel (with the left-out terms).
  - Customer terms: a term's card shows where it was found, zoomed in: a picture of the lines around it on the PDF page
    (outlined), or the Word paragraph with the term highlighted and the paragraphs either side; Previous and Next
    place step through every use. A plural (CDRLs) is marked "Plural of CDRL": it stays a found term in every scan,
    counts for its singular, and never shows as its own row in the lists you submit ("Not a plural" undoes it). The
    separate Customer acronym lists button is gone: the customer's terms are every acronym in its documents, and a
    glossary in a customer document gives its definitions first.
  - Gate goals: click a goal's wording to change it, remove it, or (for a goal the app checks) tick it by hand.
    Defaults... saves the current stage's goals as the default for new efforts on this PC.
  - The window adapts to its size: button rows wrap onto a second line instead of cutting buttons off, and a page
    scrolls only when the window is smaller than it needs. Tables are compact; columns resize by dragging (double-click
    an edge to fit), long text ends in "..." with the full text on hover, and wide tables scroll left and right.

CHANGES: ONE PLACE FOR WHAT A NEW VERSION CHANGED (2.85.0)
  - Compare, Impact review and the review part of Requirements are now one page, Changes. Documents in the rail is:
    Library, Changes, Submission rules, Deliverables. Customer versions now lives in Library (versions, Initial and
    type, Rename); Impact review is the summary on Changes.
  - The summary strip on top says what the version touches: compliance requirements (and their owners), sentences
    not in the matrix yet, submission rules, deliverables, new terms, and how many changes are left to decide. Click
    one to show only those changes. Each change is tagged REQ, NEW, RULE, DELIV or TERM.
  - Each change shows in its place in both versions, side by side (WAS and NOW, two sentences either side): removed
    words struck through in red, new words in green. A strip beside the list marks where every change sits.
  - Every change gets a decision; several can apply, each with who, when and why: Updates a requirement (new wording;
    the old wording goes to its history; "owner to confirm"), New requirement (into the section picked), Updates a
    submission rule (the rule takes the new value; a new due date becomes the effort's), Context for a requirement,
    Removes a requirement (marked, never deleted), Task, Question, Note, or No action (with a reason). Taking a
    decision off undoes what it did.
  - "8 of 23 decided"; Only undecided; the version is marked reviewed when every change is decided; decisions stay
    with their change. Author briefs come from the same page. Requirement history lists every requirement a version
    changed, removed or added; the owner confirms the answer still fits there or on Assign's card.
  - Submission rules (was Requirements) is a reference: what the customer requires now. A rule a version changed shows
    Was and Now in its row, in color, and "Open the change in Changes" goes straight to it.
  - The mouse wheel never changes a choice: over a drop-down, a number box, a date or time box, the wheel scrolls the
    page (or the table the box is in). A value changes only when you open the drop-down and pick, type, or use the
    arrows. An open drop-down list still scrolls with the wheel.

READ AND ASSIGN ANY DOCUMENT (2.84.0)
  - Every start, after an update too, reopens the effort you last had open, with its documents and work; with one
    effort on the PC it opens that one. (Before, the Qt window did not remember it, so an effort could look empty
    until you picked it in the Effort box.)
  - Assign: "Not used" is now "Ignore" (X).
  - Library documents that do not build the matrix (attachments, ICDs, Q&A, standards, past proposals) are in Assign's
    File list under "Library: ...", or open them with Library > Read it in Assign. They open on the same page, beside
    the same response structure. The rule is the same: select text, then choose where it goes.
  - The buttons beside the structure change for a library document: Context for section (C) into the target section;
    For a requirement (F), one of the target section's requirements; Note (N), Question (Q) and Task (T) in the effort
    record, quoting the sentence; Make it a requirement (R), into the matrix in the target section with its document
    and place; Not needed (X) takes its attachments off. Topics can be added on the card.
  - Where it shows: the structure's Ctx column counts each section's context; the page tags it in the margin; a
    requirement's card lists what was attached to it; Response Setup prints the context under its section, with the
    document and place; renaming a section keeps its context.
  - Library > Taken from documents... lists every sentence taken and what it is attached to, filters by kind,
    document and topic, opens one in Assign, and exports it all to Excel for writers.
  - Each attachment keeps the quoted text and the version it came from, so it reads the same if the file moves or is
    left out of a package.

THE DOCUMENT LIBRARY (2.83.0)
  - Documents > Library holds every document of the effort: Customer documents, Bidders library, Q&A, Our effort
    documents, and categories you add (New category...). The left side lists the categories and their folders; the
    table shows each document's category, versions, tags and role; search finds names, tags and the text of every
    document, with the sentences it found.
  - Add a folder... (or drag folders and files from File Explorer onto the Library) reads every document in it and its
    subfolders in the background, with a progress bar and Stop (nothing is added until you accept). One table shows
    each file's suggested category (from its folder names), role, tags (every folder name is a tag), and whether it is
    a new version of a document already here; select rows to set many at once. Customer documents still need an
    initial and type.
  - Customer documents still go to the customer documents folder; the others are copied into the effort's library
    folder, so the effort is complete wherever it goes. Requirements, Compare, Impact review and Read RFP work on the
    customer documents only.
  - Every document has a role: Builds the matrix, Context, Reference only or Not needed. It is suggested from the
    category and type; setting it keeps who, when and why. Read RFP ticks the customer documents that build the
    matrix and shows each one's role.
  - Save effort package asks, when the library holds other documents: All documents, or Customer documents and Q&A
    only. Either way every document's record, text copy, tags and role go, so search and the library work for the
    person who opens it; a left-out original shows as "original not here".
  - Automatic backups keep every document's record, text, tags and role, and the customer and Q&A originals. The other
    library originals are copies of files you added from your own folders, so backups leave them out to stay fast;
    a saved effort package with All documents carries them.
  - The Documents page is now called Customer versions.

FASTER MOVING BETWEEN PAGES (2.82.0)
  - Documents, Requirements, Effort home and the dashboard no longer work everything out again on every visit. What
    changed between two versions, the submission requirements each version sets and the fingerprints of the customer
    folder's files are worked out once (in the background when an effort opens) and kept: in memory, with each version,
    and in the effort's documents\found folder for the next start.
  - Kept results follow every change: a new version, a renamed document or an edited file is worked out again, so a
    page never shows something stale.
  - Measured with 40 documents of 3 versions and a 2,800-sentence matrix: Requirements went from about 3 seconds to
    0.01; every page opens in under 0.2 seconds.
  - Read RFP shows its progress: the file and the page within it, a running clock, and Stop (stops after the file being
    read; nothing is written). A step quiet for a minute says it is still working. A file that cannot be read stops
    the read in red, names the file, says nothing was written and what to do. The window's status bar shows the bar
    from any page.
  - Read RFP's documents are a table (initial, type, version, file): Tick all, Untick all, Tick selected, Untick
    selected and Tick only one type; Shift+click or Ctrl+click selects several, and Space or a tick on a selected row
    ticks them all. A count shows how many are ticked.
  - One read at a time: Read, Add files, the start choice and the ticks are locked while it runs, so there is never a
    second read or a second matrix. Switching effort or closing the window during a read asks first, then throws the
    read away without writing anything.
  - No blank pause after an update: the version being updated shows "Updated to X. Starting the new version" until
    the new window is up (from 2.82 on), and the new version reopens your last effort under a cover that shows each
    step (checking the files, loading the matrix, setting up the pages, back where you were) and that nothing is lost.
    Normal starts show the same cover while the last effort opens.
  - Assign: the decision buttons (Requirement R, L, M E, Support C, Customer's G, Not used X) sit beside the response
    structure, under a line naming the section R, L and M put sentences into. Combine, Split and Undo stay by the page.

HELP WITHOUT SENDING DATA (2.81.0)
  - Settings > Help and support > Create a support file: one zip with versions, the content-free logs and the checks
    (Check program files, effort health by kind, which settings are on), for whoever maintains Stationkeeper. It holds
    no document text, terms, names, file names or folder paths; every value is checked before it goes in. You save it
    and decide who gets it.
  - Ctrl+K finds a page, an effort, a sentence (by its words or number) or a person, from anywhere. F1 lists the
    keyboard shortcuts.
  - After an update, one card says what changed (also Settings > Help and support > What's new).
  - Safe start: after two starts in a row that did not finish, Stationkeeper opens without the last effort and says
    why, so one damaged effort cannot keep the program from starting.

YOUR DATA IN ITS OWN FOLDER, AND EFFORT HEALTH (2.80.0)
  - Your settings, author list, master acronym database, OCR fixes, knowledge, training lines and feedback now live in
    "Stationkeeper Data", a folder beside the Stationkeeper program folder. The first start copies them there from the
    program folder (nothing is deleted). Update packs and new downloads never touch it; unzip a new download beside it
    and it picks your data up. Delete both folders to remove everything. Settings > Your data shows where it is and
    can move it.
  - If the folder beside cannot be created (a program folder IT installed in Program Files), the data stays in the
    program folder as before.
  - New efforts are created in Stationkeeper Data\Efforts on this PC. Share them through packages and backups in the
    team folder: a live effort in a OneDrive folder can collide with the sync.
  - Effort health is checked each time an effort opens (Effort record > Effort health): a damaged effort list or
    matrix is put back from its newest good copy automatically, with the damaged file kept beside it; a moved customer
    documents folder, a live effort in a synced folder (Move to this PC), long paths, low disk space and sync conflict
    copies are flagged with a fix where there is one.
  - Before saving the matrix, Stationkeeper checks whether another copy saved it meanwhile and asks: keep yours (theirs
    is kept as a dated copy) or open theirs (yours is kept beside it).
  - Saves wait a moment when OneDrive or a virus scanner holds a file, instead of failing.

WORK MODES AND HAND-OFFS EXACTLY AS YOU SEE THEM (2.79.0)
  - At first start Stationkeeper asks where the PC is used; Settings > Where Stationkeeper is used changes it. The
    title bar shows the mode. Stationkeeper works offline and never connects in either mode.
  - Secured (a SCIF or any closed network): backups and packages go to a local folder or your site's approved transfer
    location; a folder OneDrive uploads is flagged; move packages only through your site's approved transfer process.
    The mode certifies nothing: your site's security officer approves software for a classified system.
  - Connected (Microsoft 365 with OneDrive): choose the team's OneDrive-synced SharePoint folder once. Backups go to its
    Backups folder; Effort record > Save to the team folder writes the package to Packages\<effort>. A marker in
    "Working on" shows who has which effort open, and opening one someone else has open asks first.
  - Packages now carry where you were (page, sentence, structure target), the author-list names that show in the
    effort (added on the receiver's PC, never removed) and the effort's revision history.
  - Importing an effort that is already on the PC says which copy is newer ("6 saves newer than your copy", "older",
    or "you both changed it") and what differs in the compliance matrix, before you replace or keep both.
  - A package saved by a newer Stationkeeper asks for the update pack first.

NEVER LOSE WORK (2.78.0)
  - Automatic backups are back: a few minutes after changes and when the effort closes, the whole effort is copied to
    the backup folder (Settings > Backups) as "<effort> - latest.skpkg", plus one copy a day kept 30 days and the app's
    settings and team lists. Choose the approved SharePoint folder so progress is never only on this PC. (From 2.74.0 to
    2.77.0 only Back up now copied it.)
  - The effort's own folder keeps dated copies of the compliance matrix and the effort list (the last 10 and one a day
    for 14 days).
  - Every change writes a recovery copy. If Stationkeeper or Windows stops before a save, the next opening offers to
    put the changes back.
  - Effort record > Restore... lists every copy, newest first, and puts one back; what you have now is kept as a copy
    first.
  - The effort reopens where you were: the page, the sentence, the volume and the structure target.
  - On an unexpected error your work is saved first, then a plain message offers Keep working or Restart.

ONE AUTHOR LIST FOR EVERY NAME (2.77.0)
  - Settings > Author list is the only place names come from. Author(s) in Assign, a section's lead and contributors,
    a task's owner, a question's answerer and a deliverable's owner all pick from it; names are never typed there.
  - Each name shows in All efforts or in the efforts named next to it: Joe G. set to Effort A shows in Effort A's
    drop-downs and not in Effort B's. Shows in... sets the efforts; Show in this effort and Not in this effort change
    the open effort only.
  - Add names (one per line), or Import a list (.txt one name per line; .csv or .xlsx with a Name column and an
    optional Efforts column: All efforts, or effort names separated by semicolons). An import adds only names that are
    not on the list yet; names already there stay exactly as they are, efforts included. Export the list to hand an
    updated list to the rest of the team.
  - With no effort, the list and the pickers say to select or create an effort first.
  - First start of 2.77.0: the list starts from every effort's team, so nobody disappears. A name already assigned
    that is not on the list stays on its sentences, marked "(not on the author list)".
  - Effort record > Team shows the names from the list for this effort with their roles; Choose people ticks who
    shows in the effort.

UPDATE PACKS: INSTALL ONCE, THEN UPDATE WITH ONE FILE (2.76.0)
  - 2.76.0 is the last full download. Each later version also comes as one update pack, for example
    Stationkeeper_US_Update_2.77.0.skupdate (and Stationkeeper_US_Training_Update_2.77.0.skupdate for Training).
  - Settings > Updates > Install update pack... (or double-click the .skupdate file): Stationkeeper shows what changes,
    saves your work, closes, updates its program files and opens again. Stationkeeper Training: Build > Updates.
  - Only program files change (Stationkeeper.exe, _internal\ and the documents). Efforts, settings (config\), the
    acronym database, logs and training data are never touched. Unzipping a new copy over an old one overwrote
    acronym_database.csv and the settings; an update pack never does.
  - One pack serves every copy from 2.76.0 on, so you can skip versions. It holds only the files that changed, usually a
    few MB instead of the 220 MB zip.
  - Signed: the publisher signs each pack; Stationkeeper refuses a pack that someone else made or that changed after it
    was made, and checks every file before anything changes. No internet: you pick the file, nothing checks online.
  - Undo last update goes back to the version before. Check program files compares every program file with this
    version's list and names any that are changed, missing or not part of it.
  - IT can push a pack with no window: Stationkeeper.exe --apply-update <pack> (also --undo-update, --check-program);
    the result goes to logs\update.txt.
  - Get packs only from the approved SharePoint folder.

WHY IT RUNS WITHOUT AN ADMINISTRATOR PASSWORD
  - Windows asks for an admin password only when a program declares that it needs one, or when it writes to protected,
    machine-wide places: Program Files, the Windows folder, the machine-wide registry, services and drivers. Installers
    ask because they write there.
  - Stationkeeper has no installer. Its exe declares "run as the person who started me" (asInvoker), and it writes only
    inside its own folder, which you own. Windows has nothing to ask permission for.
  - The Windows sandbox is not the reason. Only the OCR reader (Tesseract) runs in a Windows AppContainer, and that
    takes rights away: no network, no files beyond two folders. A sandbox cannot grant or skip admin rights.
  - Not an approval: it can read and write what you can, as any program you run can. Its protection comes from having no
    network code (checked at every build), the no-network sandbox for the OCR reader, pinned and checked components
    (SBOM, known-advisory check), read-only documents and signed update packs.
  - Running does not mean approved. It runs because this PC does not block programs in your own folders (AppLocker or
    WDAC); IT can turn that on at any time. Give IT security SECURITY.md, the SBOM and the checksums.
  - The full explanation is in SECURITY.md (section 10) and in Settings > About and security.

ONE PROGRAM: THE CLASSIC WINDOW IS RETIRED (2.75.0)
  - Stationkeeper_US.zip holds Stationkeeper.exe, the Qt window; Stationkeeper_US_Training.zip holds
    StationkeeperTraining.exe, Stationkeeper Training in Qt with the Trainer. StationkeeperClassic.exe and
    StationkeeperTrainingClassic.exe are no longer included.
  - Nothing changes in your files: every effort, matrix, list, setting, training line and Knowledge Pack made in either
    window opens in Stationkeeper.exe.
  - When you unzip 2.75.0 over 2.74.0, delete StationkeeperClassic.exe (and StationkeeperTrainingClassic.exe) if they
    are still in the folder: they belong to the older version.

STATIONKEEPER.EXE IS THE QT WINDOW (2.74.0)
  - Stationkeeper.exe now opens the Qt window (it was StationkeeperQt.exe), and StationkeeperTraining.exe opens
    Stationkeeper Training in Qt (it was StationkeeperTrainingQt.exe). Your shortcuts keep working and open the Qt window.
  - The classic window shipped beside it in 2.74.0 only, as StationkeeperClassic.exe (and
    StationkeeperTrainingClassic.exe); 2.75.0 retires it.
  - Double-click an effort package (.skpkg) or a Knowledge Pack (.skknow) and the Qt window opens it. Settings >
    Import effort package... opens a package someone handed over: keep both, or use the package (this PC's copy is
    backed up first).

THE TRAINER IN QT (2.73.0)
  - Stationkeeper Training (Qt) has the Trainer as a page (rail: Teach by hand > Trainer; or Train > Trainer): open a
    document or picture, pick a page or picture, and drag a box around text the reader missed (or Select the whole
    picture). The box is read in the background; each line shows with its confidence and a numbered box on the picture.
  - For each line: Skip, Save as text (fix the spelling first; typing picks it) or Not text (lines, arrows or specks read
    as letters). Save choices keeps one tight picture per text line and the region; a Not text reading the scanner
    keeps today goes on the ignore list.
  - Whole box as one line, Add OCR fixes from corrections, Undo last save, the ignore list and the training folder,
    How training works.

STATIONKEEPER TRAINING (QT) (2.72.0)
  - Stationkeeper_US_Training.zip now also holds StationkeeperTrainingQt.exe: the Training Studio in the Qt window,
    next to StationkeeperTraining.exe. Same training data, config and Knowledge Packs.
  - 1 Gather: import training data packs (.sktrain, older .zip) and add past compliance matrices.
  - 2 Review: every corrected line with its picture; filter (taught, rejected, test set, from packs, saved here) and
    search; Accept, Reject (never taught) and Fix the text (or double-click).
  - 3 Train: Improve Reading runs in the background with its progress; the new reader is kept only if it reads the
    held-out lines better. Put back the previous reader. Prepare the docTR Training Kit package. The Trainer (box text
    in pictures) opens in the Training program's window.
  - 4 Measure: the scorecard; an area that got worse is left out, and double-click leaves an area out or puts it back.
  - 5 Build the pack: one .skknow file; load trained models, export a Knowledge Pack, undo the last knowledge change.
    Knowledge Packs and training data go to the approved SharePoint folder only, never GitHub.

OFFICE COPIES CLEAN UP AFTER THEMSELVES (2.71.0)
  - Page view makes a PDF copy of a Word, Excel or PowerPoint file through Office on this PC. When a copy takes too
    long, Stationkeeper now ends the hidden Office program that copy started (only that one: Office windows you
    opened are never touched). Before, a hidden Word stayed running and could hold up the next copies.
  - A password-protected Word or Excel file now fails at once with a reason, instead of waiting on a hidden password
    prompt.

NOTHING THE READER MISSES STAYS MISSED (2.70.0)
  - A list's lead-in, the sentence ending in a colon just before bullets ("The description shall address the
    following:"), is a sentence of its own: it has a box on the page and is assigned like any other. Its bullets still
    carry it in the matrix. It used to live only inside its bullets, so it could not be clicked, and the text check
    counted it as read.
  - Matrices read before 2.70 get their lead-ins as sentences when they open (decisions are kept).
  - Assign: Add missed text. Press it, drag a box around text the reader missed, and Stationkeeper reads what is
    inside: the PDF's own text first, the built-in OCR when the page is a picture. Check or type the text, tick
    "Make it a compliance requirement" if it is one, and it is added as a sentence in its place, with a box. Esc
    cancels.
  - A digital signature on a PDF does not stop reading: it only blocks changes to the file.

HOW THE RESPONSE STRUCTURE STARTS, AND RFPS WITHOUT SECTIONS L AND M (2.69.0)
  - Read RFP asks how the structure starts: Choose after reading (the default when no outline was typed for the
    effort), What the RFP prescribes, The RFP's headings, The outline typed for this effort, or Blank.
  - What the RFP prescribes: the volumes it names in its headings or text (Volume 2 - Price Proposal, TECHNICAL
    VOLUME), the sections under each volume heading, and any list after "shall be organized as follows:". Structure
    shows where each part came from; edit it, then Apply. Nothing depends on the RFP using Sections L and M.
  - Structure: What the RFP prescribes, RFP headings from one document or all (any numbering), RFP outline, Word
    outline, Blank. Indented lines are subsections, so sections under a volume keep their place.
  - Assign: Copy RFP section puts the RFP section of the selected sentence (and its subsections, if you want) under
    the target, titled as the RFP titles it. Its requirements with no section yet go into it, and its other sentences
    suggest it. Rename or move it to say it your way.
  - L and M are our labels (Shipley); most RFPs do not use them. Stationkeeper suggests one from a Section L or M
    number, the RFP section's title (Proposal Preparation Instructions, Evaluation Criteria, Basis for Award), the
    sentence's wording (the Offeror shall describe... / the Government will evaluate...) and the document type, and
    says why on the card. SOW, PWS and SOO work gets no suggestion. A suggestion goes into the matrix only once you
    set it (Section L or M numbering counts as set). A requirement with no L or M is fine: its reference is R-4.2.1.
  - Sections made in Assign keep numbering themselves after the matrix is saved and reopened, and a new section never
    takes a number already used.

DOCUMENT INITIALS, L AND M, AND THE STRUCTURE BUILT AS YOU READ (2.68.0)
  - Every customer document needs an initial and a type (RFP, Amendment, SOW, SOO, PWS, Section L, Section M, Q&A,
    Attachment, CDRL, DD 254, Other) before it is read. Customer Documents suggests both and shows them; Read RFP asks
    for any that are missing. No two documents share an initial; every version of a document keeps its initial.
  - In Assign, a requirement is L (Instructions, Conditions and Notices to Offerors) or M (Evaluation Factors for
    Award): the L and M buttons, or the L and E keys. Stationkeeper suggests it from the section (L.4.2, M.2) and the
    document type. Support (context) can serve as many L and M requirements as needed. Combine moved to J.
  - The matrix has Reference (R-L-4.2.1: document initial, L or M, section), Doc, L/M and Section columns, and a
    tab for each volume next to the full Compliance Matrix tab. The Response Setup is one file per volume, as before.
  - Assign no longer waits for a structure: R keeps a sentence as a requirement with no section yet. Beside the page:
    + Volume, + Heading, + Subheading (as many levels deep as needed), From sentence (a section named with the RFP's
    words), Rename (or double-click), up, down, indent, outdent, Delete. Sections made here number themselves (1,
    1.1, 1.1.1 ...), restarting in each volume, and every requirement follows its section when numbers change.
  - The volume switcher above the structure picks the volume you are working in: the structure shows its sections
    and new sections go into it. A sentence in more than one volume shows each volume on its card and in the margin.

STATIONKEEPER (QT) (from 2.59.0)
  Stationkeeper is moving to a new window system (Qt, through PySide6: The Qt Company, Finland, LGPL 3; its libraries
  ship as separate files). StationkeeperQt.exe sits next to Stationkeeper.exe and shares its config and every effort
  file. It holds Effort home, the effort dashboard (2.62.0), the effort record and color team reviews (2.63.0), acronym scan and review and the effort list (2.64.0), Customer Documents (2.65.0), QA/QC, Keywords, Export all and Settings (2.66.0), author briefs, customer acronym lists, training data and
  Knowledge Packs (2.67.0), and all of Compliance (L and M, document initials and building the structure while assigning in 2.68.0; how the structure starts in 2.69.0): Read RFP, Structure, Assign,
  Prove, the L/M crosswalk, Matrix and Response Setup (2.61.0); Training in Qt (2.72.0) and the Trainer (2.73.0).
  From 2.74.0 Stationkeeper.exe is the Qt window; 2.75.0 retires the classic window.
  - Open an effort in one program at a time: the other says the effort is open elsewhere.
  - Qt runs fully offline; no Qt network or web parts are included.

NEW NAME (from 2.44.0)
  Acronym Hunter is now Stationkeeper: it runs a whole proposal effort (customer documents and their versions,
  submission requirements, deliverables, compliance, the impact of every new version, author briefs, gates, the
  paper trail), and acronyms are one feature among many.
  - Stationkeeper_US.zip holds Stationkeeper.exe; Stationkeeper_US_Training.zip holds StationkeeperTraining.exe.
  - Effort packages are .skpkg files. Packages saved as .ahpkg by Acronym Hunter still open.
  - Projects, team knowledge packs and corrections packs from Acronym Hunter still open.
  - Moving from an Acronym Hunter folder: copy its config folder into the new Stationkeeper folder to keep your
    settings and lists. Efforts keep their work next to their effort list, so they open as they were.

ONE PROGRAM (from v1.7.0)
  Stationkeeper_US.zip holds one program, Stationkeeper.exe (AcronymHunter_US.zip and AcronymHunter.exe before 2.44.0). It reads text in pictures with Tesseract OCR
  (Apache 2.0; created at HP, developed by Google) and Google's English model.
  - Tesseract is built from its source without any network library, and it runs inside a Windows sandbox
    that has no network permission. No Chinese-origin code or models. No GPU, no internet, no separate kit.
  - From 2.15.0 the Trainer and Improve Reading live in a second program, Stationkeeper Training (see TRAINING IS
    ITS OWN PROGRAM at the end). Stationkeeper only saves corrections and sends them to the training team.
  - To give colleagues a copy that saves no corrections: put config\app_settings.json in the program folder before
    sharing, holding {"allow_training": false} (from 2.90.0 the download ships no config folder; the first start copies
    it into Stationkeeper Data). Nothing gets saved to training_data\ then.
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
  2. Open the Stationkeeper folder and double-click Stationkeeper.exe.
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
  On the right: Tools (Send corrections, Knowledge Packs, Edit Database CSV, OCR Fixes, preview on/off),
  and the Advanced switch (adds Fix OCR and the OCR Fixes list).

PREVIEW PANE: SEE WHAT PRODUCED A RESULT, AND FIX IT THERE
  Click any result. The pane on the right shows where it was found:
    [picture] or [page]  The picture or PDF page, read again, zoomed in on the term (yellow box).
                         Green = readings the scanner keeps, red = low confidence (ignored), orange = the
                         term in a PDF page's typed text. "Show whole picture" zooms out.
    [typed text]         Read exactly from the file: nothing to correct. Exclude it if it is not a real term.
  Pick another location from the list at the top of the pane. Click any box to select that reading.
  Fix it right there:
    Report misreading  Fix the spelling, then click. Saved as a corrected line for the training team
                     (Tools > Send corrections), and single-word fixes (RFF > RFP) apply on the next scan.
    Not text         A diagram line or speck read as letters: ignored in pictures from the next scan.
    Exclude term     Not a real term: never reported again.
    Undo last save   Takes back the last Report misreading or Not text.

CODES AND DESIGNATORS (v1.9.0)
  Codes are reported whole as "Designator": PCU-28V, MIL-STD-1553B, RS-422, PN 4521-003A, ST-200X, J1-P3.
  Their pieces are no longer reported as stray units or letters ("V", "B", "A"). Mixed-case acronyms
  such as DoD, DoE, IoT are found too.

CHECK IN PICTURE AND IMPROVE READING (Stationkeeper Training from 2.15.0; Stationkeeper sends corrections)
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

EQUATION PICTURES (2.55.0; the math reader add-on is gone)
  Equation pictures are read by the text reader (ML, on this PC), which learns math and unit characters (Greek,
  operators, degrees, micro, ohm). Position rules turn smaller lowered characters into subscripts, raised ones into
  superscripts, and a short line between text into a fraction (a/b). No generative AI is in the program.

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
    Knowledge > Install Knowledge Pack... > pick the newest Stationkeeper_Knowledge_<date>.zip (or AcronymHunter_Knowledge_ from before 2.44.0)
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
  Keep the Stationkeeper app folder itself OUT of OneDrive: its scratch files and Trainer samples
  would sync to the cloud.
  Whether controlled documents (CUI, ITAR) may live in that OneDrive or SharePoint is your
  organization's decision. The app does not change it. When in doubt, scan local copies.

TRAINER (a window inside Stationkeeper.exe: Advanced > Trainer, or right-click > Check in picture)
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
  About Stationkeeper\CHECKSUM.txt holds the exe fingerprint. In PowerShell:
    Get-FileHash .\Stationkeeper.exe
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
- Each release ships a Software Bill of Materials per edition (Stationkeeper_US_SBOM.cdx.json, CycloneDX 1.5): every
  bundled Python package with version, license and PyPI identifier, the native parts (Python, Tcl/Tk, Tesseract,
  eng.traineddata, docTR models, PDFium), and the SHA-256 of every program and model file. Made by tools\make_sbom.py
  at build time from what actually ships.

EFFORT PROFILES, SAVING AND RECOVERY (2.11.0)
- Each effort keeps its own work: scan results, Apply Choice decisions, compliance matrix, volume check and where you
  left off (filters, selected row, open compliance window). Nothing from one effort shows up in another.
- The Effort box at the top of the window switches efforts; the window title shows the open effort. The app resumes
  the last effort at start and says so ("Resumed Kestrel, last worked yesterday 4:12 PM").
- Each effort's saved work lives in a folder named "<list name> - app data" next to its effort list: settings,
  choices, session, resume, recovery and backups. New efforts get their own folder (Desktop\<Name>\). It holds
  customer content: keep it on this PC or SharePoint, like the effort list.
- Saved as you go: results and choices within seconds of each change. Unsaved Effort List and compliance matrix
  changes (the app closed, or Excel had the file open) come back the next time the effort opens.
- File > Restore an earlier version: dated copies of the effort list and compliance matrix (at most every 10 minutes,
  the last 10 plus one per day for 14 days). The current file is copied first, so a restore can be undone.
- One window per effort: if another window or a teammate has it open, the app says who and asks first.
- Effort > Archive this effort hides a finished effort; Effort > Archived efforts reopens it.
- Upgrade: choices and the compliance matrix location were shared by the whole PC. The effort open when you upgrade
  gets a copy of them; scans with no effort keep the originals; other efforts start fresh.

AI AND ML LABELS AND SWITCH (2.12.0)
- Every sidebar section shows what runs it: No AI (rules, counting, file reading), ML (a trained model on this PC that
  recognizes or scores; outputs letters, boxes or numbers, never sentences) or Gen AI (a model that writes text; the
  math reader add-on only, in the no-network sandbox). The ? next to each section lists the parts and their jobs.
- The AI and ML switch (top right) is per effort and on by default. Off stops every ML and Gen AI part: text inside
  pictures and scanned pages (Tesseract, docTR), learned compliance suggestions, Improve Reading, Trainer, the math
  reader. The model code refuses to run while it is off; typed text is still read everywhere. Turning it back on
  re-reads the pictures on the next scan.
- Each change is recorded in the effort list's History sheet and in the usage log (the effort as a number, not a name).
- The line at the bottom of the window always shows: offline, the effort, AI and ML on or off, generative AI installed.
- Help > What runs where lists every part and saves a one-page summary for the security team.
- Compliance window: Team learning (per effort, on by default). Off: the effort's decisions are not learned and the
  Learned column stays empty.

SETUP BUILDER (2.13.0)
- Compliance window > Setup tab: the RFP text not placed yet on the left, the proposal outline on the right. Drag RFP
  text onto a section (Shift+drag adds a copy to a second section), drag inside the outline to reorder, drag back to
  remove. Accept suggestions places rows by section number, title words and rows you mapped before. Placement is the
  same as the Outline column in the Requirements tab.
- Add context from RFP keeps the RFP's other paragraphs (SOW text, evaluation criteria) as Context items to place.
- References: each RFP block starts with its section reference on the same line (L.4.2(a): text). It comes from the
  RFP's numbering (with list markers), the heading above, a rule per file for numbers without a letter (References >
  Attachment 3 = L gives L-3.2), or what you type (Set, Fill down). Formats: "L.4.2(a): ", "[L.4.2(a)] ",
  "RFP L.4.2(a) - ".
- Management direction per section, and a note per RFP row, typed below the outline.
- Export setup: one Word file per volume. Word's built-in headings for every outline entry (empty ones too), RFP text in
  Word's standard Purple, direction and notes in standard Green. No hidden text and no custom styles, so each kind can be
  selected at once (Select Text with Similar Formatting) and given the team's own style.
- The setup is saved in the matrix workbook (Setup and Setup direction sheets, plus a hidden Setup data sheet), with the
  matrix's autosave, recovery copy and backups. Export changes only writes what changed since the last export; Compare a
  setup document lists RFP text missing from a styled setup, under a different heading, or not in the setup.
- Exclude instance (Source preview): removes only the location shown, for a misreading or a stray word in one place.
  The term stays wherever else it was found. Saved per effort (excluded_instances.json in the effort folder) and
  applied after every scan; excluding every instance hides the term without a database rule. Restore instances (or
  right-click > Restore excluded instances) brings them back. Exclude term is unchanged: a database rule, everywhere.
- Omit list (right-click > Add to omit list, or Edit > Omit list): company names, locations and other terms that are
  found and recognized but left off the final lists. Saved in the database (Action "Omit", with what it stands for
  and an "Omit reason" column: company or organization, location, program or product, person or role, other).
  Rows say "Found in omit list: <reason>", are never flagged for first use, and stay out of the CSV export, the volume
  acronym lists and the Not in effort list filter. The Omit list window adds, pastes many (TERM, stands for, why),
  and removes. Status > Found in omit list shows them.
- Several meanings of one acronym: the database, the omit list and Add Item accept another row for a term when the
  meaning differs (compared without case, spacing or punctuation). The same meaning twice is flagged and nothing is
  added. Add Item on a term already in the results adds the meaning, so the row asks you to choose.
- Meaning from context: when a term has several possible meanings (database, client list or customer documents), the
  words around each place it appears suggest one: shared words, a role ("the PM shall"), a document word ("PM plan"),
  or the long form spelled out in the same files. Rules only (No AI), typed text only, run in the background after
  each scan. The Definition column shows "Context: ..." with the reason, Apply Choice starts on it, the Source
  preview says what it likely means at each place, and rows whose places disagree say "meaning differs by place".
  Nothing changes until you accept: right-click > Accept context suggestion, or Edit > Accept context suggestions
  (saved like Apply Choice). Status > Context suggests a meaning; the CSV export has a Context suggests column.

EFFORT START, HOME AND VOLUMES (2.14.0)
- Master database: the first step of Start an effort, or File > Load master database. CSV or Excel (Term, Category,
  Definition, Action) or a plain acronym list, merged into this PC's database: rows added on this PC stay (no Origin),
  rows from the previous master the new one dropped are removed, new rows get Origin "Master database". Each load is a
  numbered version (config\master_database.json: file, date, rows, SHA-256; a copy in config\master). The bottom line
  shows the version.
- Known in column: Customer docs, Customer list, Master database only, or Not found in any source. Status filters
  Known in: ..., and the CSV export carries it.
- Update results against the master database (offered after each load; also in the File menu): matches the results
  again, reusing the text already read this session for unchanged files. Nothing is removed: rows not found again
  stay, changed rows say Database update, decisions, picked definitions and the effort list stay.
- Effort > Start a new effort: master database, effort and client (short name, solicitation number, internal number), the customer's
  acronym lists (remembered by the effort and used on every scan), customer documents (copied into the effort's
  Customer documents folder and read for a jump start), how the list ships (one list, one per volume, or both; the
  first-use rule). The first start with no efforts opens it.
- Effort > Add customer documents: copies files in, reads only new or changed ones, opens Review new terms (one click
  adds terms as Proposed with the documents they came from; or omit list; or Not a term in this effort).
- Every scan updates the effort list: Found in, First found, Last found, Scan status (Found, No longer found in
  <file>). Each row carries Effort, Client and Solicitation. Activity shows the History sheet, newest first.
- Effort list (home) and Scan review: two views in the main window while an effort is open. Home lists every term
  with its definition, status, volumes, Found in and scan status; filters (needs a definition, status, no longer
  found, volume); edit definition, approve, needs author, not a term, volumes, where from, show in Scan review.
  Reopening restores the view, filter, search and selection. Every scan lands in Scan review, which adds an Effort
  decision row under the action bar: Add to effort list, Not a term, Omit.
- Use as definition: select words in the Source preview (typed passage or a picture's recognized text) and click Use
  as definition or right-click. A "Found: <long form>" line offers the definition the documents, customer list,
  database or nearby words give. Kept per effort (picked_definitions in the effort settings) and applied after every
  scan; written into the effort list.
- Named volumes (Name volumes): each volume lists its files; terms get volumes from Found in; a term can belong to
  several; Volumes... assigns by hand and survives rescans (Automatic undoes it). Written to Used in volumes.
- Import a list: a volume's acronym list (CSV, Excel, Word, PDF, text) joins the effort list with its volume and
  "Imported list: <file>"; different definitions go to Other definitions.
- Export: choose columns (Term and Definition by default), one file or one per volume, which volumes, approved only;
  CSV, Excel or Word. Rejected terms and the omit list are left out. Effort > Export all efforts writes every effort
  in one workbook.

TRAINING IS ITS OWN PROGRAM (2.15.0)
- Releases ship two zips. Stationkeeper_US_Classic.zip (no docTR) is built only on request (build.ps1 -Classic).
- Two programs from the same code: Stationkeeper (Stationkeeper_US.zip, the program everyone uses) and Stationkeeper
  Training (Stationkeeper_US_Training.zip, for the training team). Both run fully offline with the same engine,
  sandbox and network guard.
- Stationkeeper no longer trains. It has no Trainer, no Improve Reading, no Load Trained Models and no Export Knowledge
  Pack, and its package carries no Tesseract training tools (lstmtraining, lstmeval, combine_tessdata). The build
  refuses to finish if they are there (SPLIT CHECK). It keeps: Fix OCR rules, Not text (ignore list), Report misreading
  (was Correct + Teach: saves the line picture and the right text in training_data), Undo last save, and Tools >
  Knowledge Packs (install, undo).
- Tools > Send corrections (also on the green bar): saves the lessons not sent yet as a corrections pack
  (Stationkeeper_Corrections_<user>_<date>.zip: line and region pictures, labels, samples.csv, and a manifest with the
  SHA-256 of every file). Approved SharePoint folder for the training team only. Sent lessons are remembered
  (training_data\sent.json) and not sent twice.
- Stationkeeper Training:
  - Corrections: Import corrections packs. Each pack is checked before anything is copied: format, only picture,
    label and sample files with safe names, the SHA-256 of every file, real PNG pictures, size limits. A lesson already
    imported is skipped. Every line shows with its picture; Accept, Reject (never taught, training_data\review.json)
    or Fix the text. Filters: taught, rejected, from packs, saved on this PC.
  - Teach the reader: Improve Reading (fine-tunes Tesseract on the taught lines, tests on held-out lines, keeps the new
    reader only if it reads better), the Trainer, and the package for the docTR Training Kit.
  - Knowledge Pack: export a numbered Knowledge Pack (reader, database, OCR fixes, ignore list), load trained models
    from the Training Kit, undo. Stationkeeper installs the pack.
- Build: build.ps1 -App training makes Stationkeeper_US_Training.zip (StationkeeperTraining.exe), with the same gates.

KEYWORD HARVEST (2.16.0)
- Keywords view (with an effort open, next to Effort list and Scan review): the effort's SharePoint keywords with
  Category (Customer emphasis, Our solution, Differentiator, Offering, Acronym, Other), Status (Proposed, Keep,
  Reject), Source, Why, Added by, Date and SharePoint field. Saved in the effort list workbook (Keywords sheet), with
  History lines and the recovery copy. The same words in any case or spacing are one keyword.
- Capture: Ctrl+K (selected preview text, else a short clipboard text, fills it in); right-click a result, preview text
  or a home row > Add as keyword; Ctrl+Alt+K anywhere in Windows. The system-wide key is one RegisterHotKey
  combination (not a keyboard hook), reads the clipboard only when pressed, and is released when the app closes. If
  another program owns Ctrl+Alt+K, Ctrl+K in the app still works.
- Suggest keywords: reads the typed text of the effort's customer documents and of our volumes and scanned files.
  Candidates are 2 to 4 word phrases (no small word at either end, no RFP boilerplate such as Statement of Work or
  Table of Contents). Scored by count and spread, headings, requirement or evaluation wording nearby, where they appear
  (only in our volumes = Our solution or Differentiator), and everyday words score lower; approved effort-list
  acronyms are offered with their long forms. Rules and counts only (No AI). Each suggestion shows why and up to three
  sample sentences. Add selected adds them as Proposed; Not a keyword adds them as Reject so they are not suggested
  again.
- Export: Excel or CSV (Keyword, Category, SharePoint field, Why, Source, Status, Added by, Date), Keep only or Keep and
  Proposed. The app never writes to SharePoint.

OFFERINGS CATALOG (2.17.0)
- SharePoint keywords are free text, with no fixed count; BD and Production pick them. The offerings catalog keeps
  Sierra Space's offerings once on this PC for every effort: Offering, Other names (separated by ; or ,), Group,
  Description. Stored in config\offerings.csv (company offering names, not proposal content).
- Keywords > Offerings catalog (or Effort > Offerings catalog): add or update, remove, Import list (our catalog CSV
  keeps every column; any other list in CSV, Excel, Word, PDF or text is read as offering and description pairs; names
  already there are skipped), Export to share (a CSV others import).
- Keywords > Attach offerings: search the catalog, select, and they join the effort's keywords as category Offering
  with source "Offerings catalog" and the description as Why.
- Suggest keywords lists catalog offerings named in the documents (by name or another name) as Offering, first, with
  how often and where; those names are not suggested again under another kind.
- Add to catalog: selected keywords go into the catalog and become Offering in this effort.

SMARTER KEYWORD SUGGESTIONS (2.18.0)
- Keywords > Past proposals: build a baseline from a folder of past submissions (one Word, PDF or PowerPoint file per
  proposal; 5 to 20 is a good start; typed text only). With 3 or more, suggestions score a phrase lower when half or
  more of the past proposals use it ("common in past proposals (n of N)") and higher when none do ("new compared with
  N past proposals"; only in our volumes and new = Differentiator). Saved in config\keyword_baseline.json as hashed
  phrases with counts, never the text. Clear removes it.
- Keep and Reject (and Not a keyword) teach later suggestions in every effort: "kept in other efforts (n)" scores higher,
  "rejected before (n)" lower. config\keyword_learning.json, hashed phrases with counts only.
- More capture: right-click a compliance requirement > Add outline section as keyword; select words in the requirement
  text and right-click > Add as keyword; right-click a Setup outline heading > Add heading as keyword.

TEAM KNOWLEDGE IN KNOWLEDGE PACKS, SHOW IN DOCUMENT (2.19.0)
- Knowledge Packs now also carry the offerings catalog (offerings.csv) and the keyword Keep/Reject learning
  (keyword_learning.json, hashed phrases with counts). Installing adds offerings this PC does not have (its own stay as
  they are) and keeps the larger count for each hashed phrase, so installing the same pack twice counts nothing twice.
  Undo Last Knowledge Change puts both back.
- Suggest keywords > Show in document (or double-click a suggestion): the passage it came from, with the phrase
  highlighted.
- After a restart, "Resumed <effort>" stays on the status line for a few seconds before the result counts replace it.

HEADING WORDS IN CAPITALS (2.20.0, known gap F6)
- An ordinary English word in capitals that only ever appears inside an all-capital heading or title (SECTION M -
  EVALUATION FACTORS FOR AWARD, 3. THERMAL DESIGN, 1. SCOPE OF WORK) is no longer reported as a new acronym. It is set
  aside as "EXCLUDED: heading word in capitals" (Show Excluded, or Status > Excluded, lists it).
- Ordinary means: in the common English words list (2 to 6 letters), or 7 or more letters with a common English ending
  (-tion, -ment, -ing, -ance, -al...). A heading run is the word next to another all-capital word on its line, or alone on
  its line apart from section numbering (M.1, 3., C.1).
- Kept as candidates: real acronyms in headings (PCU, MIL), and any word that also appears on its own in running text
  ("The SOW tasks", "The REVIEW board"), so a reviewer still decides. Database entries are never affected.
- On the sample set: 18 heading words set aside, known false alarms 4 of 8 down to 1 of 8, recall unchanged.

LAST KNOWN FALSE ALARMS, SHARPER TRAINING TABLE, GUIDE PICTURES (2.21.0)
- Document structure words in capitals (APPENDIX, ATTACHMENT, EXHIBIT, ANNEX, SECTION, GLOSSARY, INTRODUCTION...) are
  set aside as heading words even when they also appear alone in running text ("see APPENDIX B").
- A capitalized ordinary word right after a number ("2 Add", "3 Remove") is no longer read as a unit.
- On the sample set: known false alarms 1 of 8 down to 0 of 8, recall unchanged.
- Stationkeeper Training: the corrections table rows and text scale with the display, so lines are no longer clipped
  at 150% and 200% scaling.
- Help > User Guide shows pictures of the effort list, Scan review, the Keywords view, Suggest keywords, the Effort box
  and Stationkeeper Training. tools\make_guide_shots.py makes them again from the fictional samples.

FIRST USE PER SECTION, MATH READS KEPT, LINE-REMOVAL PASS, OSV CHECK (2.22.0)
- First use rule "Restarts in each section of each volume" (Effort settings, and step 5 of Start an effort). Sections
  come from Word headings: numbered headings group by their first number or letter (2, 2.1 and 2.3 are section 2; C.3
  and "Section C" are section C); other headings are their own section; text before the first heading is "(start)".
  PDFs and slides have no headings, so the whole file is one section. The volume check report and its Excel export add
  a Section column. Results saved before 2.22.0 fall back to the volume and the report says to rescan.
- Math reader results are kept: in the .ahproj file for a project, otherwise in the effort's folder (settings.json).
  After a rescan or reopening, pictures in unchanged files show what the math reader read without running it again.
  A changed file drops its saved reads. With AI and ML off nothing is put back.
- Pictures with table rules or box edges are read a second time with the lines painted out (OpenCV rules, no model);
  only readings the first pass lacked are added. Hard diagram set: 142 to 143 of 146 labels (lines touching text 13 to
  14 of 14), about 15% more picture time. Turn off with "line_removal_pass": 0 in config\ocr_settings.json.
- Build PC: tools\osv_check.py checks every Python package in the release SBOMs against the OSV database (package names
  and versions only). 2.22.0: 16 packages, no known advisories. The app itself never connects to anything.
- User Guide: pictures of the Setup tab, Help > What runs where and a ? panel.

FIRST USE IN TEXT ONLY; FIGURES AND TABLES REPORTED APART (2.23.0)
- First use is judged in the running text only. Tables, figures (pictures, diagrams, charts, SmartArt, text boxes),
  captions ("Figure 3." / "Table 2:" or the Caption style), headers and footers, comments and speaker notes never count
  as a first use, before or after the text.
- Word tables, text boxes and captions are now their own passages: "(section '2. Approach', table, para 4-9)",
  "(..., text box, ...)", "(..., caption, ...)".
- Volume check: "First use in text" plus a new "In figures or tables" column (Table, Figure, Caption, Header or footer,
  with the first place). A term used only in figures or tables is listed in blue: "Only in figures or tables; not in
  the text, so no first use to check". The Excel report has the same columns.
- Results table: the First Use column and details say "only in a table: ..." or add "in a figure" lines.

QA/QC VIEW FOR OUR DELIVERABLES (2.24.0)
- First use matters only in what we write (the response to the RFP), so it moved out of the scan results into a QA/QC
  view next to Effort list, Scan review and Keywords. The results table no longer has a First Use column or a "Not
  defined at first use" filter, its CSV export and details no longer list first use, and adding a term to the effort
  list no longer copies first use from customer documents.
- QA/QC > Check Word deliverables (also the sidebar button QA/QC Deliverables and Effort > QA/QC). Word documents
  (.docx) only: a PDF export loses the difference between running text, tables, captions, figures and headings, so
  first-use results on a PDF would not be accurate. A PDF you pick is left out with that note.
- Check column on every first-use row: a check mark "OK" (green) for defined at first use, a cross "Fix" (red) for
  not defined or never defined, "! Check" (amber) when the words differ from the effort list or no spelled-out words
  come before (ACR), "i Note" (blue) for defined again later or used only in figures or tables. The top line counts
  each. The Excel report has the Check column and the count of OK rows.
- Double-click a row: Scan review opens at that place in the preview; click QA/QC to come back.

QA/QC: USED ONCE AND THE VOLUME'S OWN ACRONYM LIST (2.25.0)
- An acronym defined at first use but never used again in the volume gets "! Check": spell it out and leave out the
  (ACR). Uses in tables and figures count; the volume's own acronym list does not.
- New Acronym list tab. The volume's own list is found as a table of acronym and definition, or as lines of
  acronym<tab>definition (three or more in a row, or any under an Acronyms / Abbreviations / Glossary heading).
  - Cross "Fix": an acronym or abbreviation used in the volume but not in its list.
  - "! Check": in the list but not used anywhere else in the volume; the list's definition differs from the effort list;
    or the effort list marks it Not a term.
  - Check mark "OK": listed, used and matching the effort list. "i Note": listed but not in the effort list yet, or the
    volume has no acronym list.
- The top line adds the Acronym list counts and "defined but never used again". The Excel report adds an "Acronym list
  check" sheet and both counts on the Summary sheet.

ALT FORMS AND THE MASTER DATABASE ACROSS EFFORTS (2.26.0)
- Alt forms: another way of writing a term (TTC for TT&C) is kept in the primary's Alt forms column, in the effort
  list and in the master database, never as a row of its own. Lists the app writes show "TT&C (TTC)".
  - Assign: Scan review > right-click > Effort list > Make an alt form of... Change: Effort list > Alt forms...
  - Found: the scanner looks for the master's alt forms; a find keeps its own row, "Alt form of TT&C", with TT&C's
    definition. Status > Alt forms lists them.
  - Read: "TT&C (TTC)" in any list the app reads (master, effort list typed in Excel, imported list, a volume's own
    acronym list) is primary TT&C with alt form TTC. "Statement of Work (SOW)" is never split.
  - QA/QC: an alt form counts as a use of its primary, has no first use of its own, and is listed with it.
- Effort > Add this effort to the master database: the effort list's Approved terms go into the master file, one row
  per term and meaning. Same term and definition: the effort is added to Used in efforts, Times used goes up, Last used
  is today, new alt forms are added. New columns: Alt forms, Used in efforts, Times used, Last used. The app shows the
  new and changed rows, writes a new version of the master file, keeps the earlier one in "Master database backups"
  beside it, and loads the new version. Adding the same effort twice changes nothing.

QA/QC: BANNED WORDS AND PHRASES (2.27.0)
- QA/QC lists every banned word or phrase candidate in the Word volumes we write: what it found, the list entry,
  where (text, table, caption, header or footer), the sentence around it, what to use instead and why. A cross "Fix"
  for Banned entries, "! Check" for Avoid entries. Comments are skipped; text inside pictures is not checked.
- Double-click a row: the whole passage with the word highlighted, and Open in Word.
- QA/QC > Banned words list...: the team's list (Phrase, Level, Use instead, Why) in config\banned_words.csv. Add,
  edit, remove, import a CSV, Excel or text list, export, or go back to the starter list of common proposal style rules
  (unsupported claims, weak commitments, vague words, placeholders such as TBD). Knowledge Packs carry the list; on a PC
  with no list of its own, the team's list replaces the starter list.
- Matching: not case sensitive; hyphen or space alike ("state of the art" finds "state-of-the-art"); a single word also
  finds -s, -ed and -ing; * stands for any letters (utiliz*); capitals up to 5 letters (TBD) match capitals only.
- The QA/QC top line counts them; the Excel report adds a "Banned words" sheet.
- The master database is named in full where you load or update it: "Acronyms, Abbreviations, Units and Symbols
  Master Database" (Start an effort step 1, File menu, Effort menu, its windows and the User Guide).

CUSTOMER LISTS PASTED OR TYPED, RESPONSE STRUCTURE, ONE EXCLUDE BUTTON (2.28.0)
- Customer lists: Paste or type... (Client Lists, and step 3 of Start an effort). Paste a list copied from Excel, Word,
  a PDF or an email, or type one term per line ("ACR - definition", "ACR: definition", "ACR<tab>definition"); sentences
  with "Spelled Out Words (ACR)" work too.
- Every term found, from a file or pasted, is shown with a tick to confirm: untick what is wrong, double-click to
  correct a term or definition, then add the ticked ones.
- A scanned PDF list (no typed text) or a picture of a list (PNG, JPG, TIF, BMP) is read with the picture reader, then
  confirmed the same way. With AI and ML off for the effort, pictures are not read.
- Start an effort has a Response structure step (5 of 7). It suggests the volumes the instructions name ("Volume I
  Technical, Volume II Management, and Volume III Cost"), their page limits, the whole proposal's page limit, and the
  Section L headings under each volume, numbered 1.1, 1.2 with the RFP reference in brackets. Edit it or type your own.
  The compliance matrix starts its outline from it, and a section with an [L.4.1] reference gets the requirements from
  L.4.1 suggested under it.
- The preview's "Exclude term" button is gone: Exclude in the bottom bar does the same (everywhere); Exclude instance
  in the preview excludes only the place shown; Not a term excludes it from this effort only.
