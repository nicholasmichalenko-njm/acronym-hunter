"""What changed in each version, in the user's words (Help > What's new; read through supportfile.WHATS_NEW).
Moved out of supportfile.py in 4.30.1 to keep that file under its size limit. Text only."""

WHATS_NEW = {
    "4.82.0": ["Shred has a new first tab, Submission Formatting Requirements. Select the customer's words that set a date and press 4, Key Date (or D): the bar shows the date, time and time zone the app read, to change before Enter, and asks one thing, its kind: Proposal due, Questions due, Answers expected, Intent to bid due, Site visit or industry day, Oral presentations, or Other (named, and offered again in the effort). The app's reading is the suggestion Enter takes; 1 to 7 pick another.",
               "A key date is on Overview > Calendar at once, with its kind. Proposal due and Questions due also fill Customer information: one value in both places, and a value already there is never replaced without asking. A different date for the same kind from another piece (an amendment) asks Replace or Keep the earlier; the calendar shows the newer date and says what it replaced. The calendar's day list has a way back to the customer's words each date came from.",
               "Key date is no longer on the Deliverables bar. A piece typed Key Date before says Marked Key Date before, kind not said. Press 4 again on a marked piece to take the mark off. How to Submit, Submission Formatting Requirement and Page Limit Requirement come to this tab in later releases."],
    "4.81.0": ["Each deliverable says what has to happen to it next, with one button for it: Make a Word file (a customer's PDF to redline or fill in), Redline it, Open the form, Attach a file..., or Open in Outline. A file we submit that is there says File is here. The card shows its kind (Document We Write, Form We Fill In, File We Submit, Redline We Return), its file or No file yet, the customer's reference and the due date. The List view has Its file and Next.",
               "In Shred > Deliverables, once a deliverable is on the list the bar asks Its file: the document in Documents whose name matches (Enter), another one from Documents, Add a file now (it goes into Documents and is attached once it is in), or None yet.",
               "Attach a file... picks from Documents. A form or a redline takes it as the customer's file and marks it Filled-in or Redlined Deliverable there. Open the form opens the file where it is; no copy is made."],
    "4.80.0": ["Effort Settings > Stages and reviews opens with the stages in a line across the top: each one with its planned dates, the current one outlined, and a passed gate with the date it was passed. Click a stage to pick it in the table.",
               "The table shows Stage, Planned start, Planned end and Gate (None, Soft or Hard). Double-click a name to rename it; drag a stage still ahead to move it. A stage already passed and the current stage keep their places. Removing a stage with dates or a passed gate asks first.",
               "Add stage adds a blank stage, or one of the standard reviews (Blue, Pink, Red, Green and Gold team, White glove) with a line on what each is for. It goes after the stage you picked.",
               "When the effort names a proposal manager, only the proposal manager changes the stages, here and in Edit stages... on the Overview. With none named, anyone can."],
    "4.79.0": ["Start an effort asks two things: its name, and Saved in, the folder its own folder is made in. Nothing is guessed, and the Effort Backup folder cannot be picked. Effort Settings > Effort has Effort type and Response type, kept as you pick them; Effort Formatting no longer shows them. The effort types include RFQ response and Other. Files and sources has Template (Change... opens Setup's Templates for the volumes) and Acronym sources."],
    "4.78.0": ["Effort Settings is four plain groups: Effort, People, Stages and reviews, and Files and sources. There is no Save button: each field is kept as you change it.",
               "Customer, Solicitation number and Proposal due are one value each. Change one on Effort Settings, on Customer information or in Shred, and every place shows the new value.",
               "Customer information has a Customer row at the top. Proposal due typed there sets the effort's due date; words with no date in them change nothing.",
               "Files and sources shows where the effort is saved, with Open folder."],
    "4.77.0": ["Shred > Deliverables: a kind's key shows the name the app suggests on the bar. Change it, then Enter puts the row on the Deliverables list.",
               "A name already on the list attaches the piece to that row. A near name asks once: Attach to it, or Add as new. Pieces marked together are one deliverable.",
               "The bar names the deliverable a piece is on; a click opens its row. The row keeps the customer's reference from the Customer heading above the piece.",
               "A piece marked Deliverable the older way says \"kind not said\" and waits for you to pick one. Taking a mark off a deliverable that has work on it asks whether the deliverable stays.",
               "A deliverable with no due date of its own shows the proposal's due date."],
    "4.76.0": ["Shred has a tab, Deliverables: mark what the customer asks us to hand in as Document We Write, Form We Fill In, File We Submit or Redline We Return (1 to 4). Each mark is a row of the Deliverables list at once, named from the customer's words, with those words attached. The same button again takes it off.",
               "Key date (D) on that tab sends a date the customer sets to the effort's calendar at once.",
               "Customer heading, Send to Outline, More, Not needed, Ask a question and For the setup are on that tab as they are on Compliance."],
    "4.75.0": ["Overview has a tab, Customer information: the people at the customer, each with a role, and the facts about the customer and the buy. Type a fact there, or take it from the customer's words in Shred.",
               "Shred > Compliance: More (M) has four captures: Customer info, Objective, Hot button, Graphic need. A fact already filled asks before it is replaced.",
               "An empty fact shows where it usually is in the customer's documents."],
    "4.74.0": ["Shred > Compliance: Customer heading (H) marks a section or heading of the customer's document. The app proposes its number and title; Enter takes it. It is never added to our outline.",
               "Every piece under a customer heading says so: the bar shows Under, and the matrix has a Customer reference column you can turn on in Design.",
               "Send to Outline: the piece waits on the Outline page to be marked there, and the shred is not interrupted."],
    "4.73.0": ["Our response structure is decided on the Outline page. It asks one question, Does the customer tell us how to structure our response?, with three answers: The customer tells us, We build it, Start from a saved outline.",
               "The customer tells us opens the customer's document beside the outline (Outline's second tab): mark the volumes and headings as before. This marking left Shred.",
               "We build it keeps why, and offers a start: the evaluation factors, the customer's headings, or type it. Change how the outline starts is under More; it deletes nothing."],
    "4.72.0": ["Shred has a second tab, Compliance. Select a piece and press 1, 2 or 3: Work Requirement (SOW), Response Instruction (L), Evaluation Criterion (M). It is a row of the matrix at once.",
               "The bar says In Matrix under, with the section the app suggests: Enter takes it and goes on, or pick another, or decide later. X is Not needed, A asks a question, S is For the setup.",
               "The Requirements tab is as it was, until the other passes are built."],
    "4.71.0": ["Shred > Response Structure: the tab's count is right as you mark. For the setup (S) sends a piece into a section as text for the author; A asks a question.",
               "Not required by the customer closes the pass in one click. Drag a heading on the outline tree to fix its level or place."],
    "4.70.0": ["Shred has a first tab, Response Structure. Select a piece of the customer's text and press 1 to 4 (Volume, Heading 1, Heading 2, Heading 3): the outline beside the page fills at once, under the volume or heading marked above it.",
               "A heading already in the outline is attached to, never replaced; a near match asks once: Same as ...? Enter takes a suggestion and goes to the next; N goes on; X is Not needed.",
               "Each document shows its state in the pass: Not looked at, Has finds, or Nothing of this kind here. The other Shred tabs are as they were."],
    "4.69.0": ["Matrix has a switch on the page: By section or By requirement. It is the same choice as Design > Rows; the other layout starts from its own columns.",
               "The L/M crosswalk is under Matrix > More. Nothing in it changed. Matrix's tabs are Assign, Check, Matrix."],
    "4.68.0": ["Each assigned requirement and criterion has a mark you set: Not started, Drafted or Addressed. Set it on Assign (right-click the rows, or More), or press Mark Addressed on Check. The app never sets it.",
               "Check has a fourth list: Assigned, not yet addressed. The mark is the matrix's Compliance status column, so it is in the export when that column is."],
    "4.67.0": ["Matrix has Check: the requirements not assigned, the evaluation criteria not assigned, and the sections with nothing in them. Double-click a row to open it in Assign, already picked.",
               "Coverage (how much of the customer's files was shredded) is under More on Check."],
    "4.66.0": ["Matrix opens on Assign: the requirements and criteria you kept in Shred on the left, the outline on the right. Pick pieces, pick a section, Assign to section. Take the suggestions places every piece that has a suggested section.",
               "Place on the customer's page is under More on Assign. The links are the same ones the matrix and the setup read."],
    "4.65.0": ["Drafts opens on Acronyms: each volume's draft against the acronym list. Status, Edit and the rest are the tabs after it."],
    "4.64.0": ["Setup opens on a preview: the volume as Make the setup will write it, each piece of text in its style's look with the style's name after it, and a slim list of headings beside it to move around. The order you set under each heading shows there at once.",
               "The sections, with who writes each and when, are one click away: Sections, beside Preview."],
    "4.63.0": ["Setup has Order under each heading...: put the kinds of text a section holds (the RFP text, management guidance, notes and the rest) in the order you want them written, for the whole setup or for one heading that differs. Each kind shows the style it is written in.",
               "Two buttons on Setup are named for what they bring: Bring in an outline... and Choose the Word template...."],
    "4.62.0": ["A page with nothing on it yet is one sentence and one button, in the middle of the page: Documents, Graphics, Deliverables, Redlining, Matrix and Outline. The bar, Find and the filters come back when there is something to list.",
               "Documents no longer shows the panel on the right. Right-click a document and choose Details to open it; everything it offered is on that same menu."],
    "4.61.0": ["Redlining is in the menu with the effort's other work, after Deliverables: Prepare, Check and Exceptions.", "Overview is one page with Calendar, Tasks and Meetings beside it. Effort settings opens from a link on Overview. Effort Activity and Effort Backup are at the foot of the menu, by Settings.", "Effort Backup shows where the backups go, backs up now, changes the folder and puts an earlier copy back.", "When you add a document you can mark it Redlined Deliverable or Filled-in Deliverable there and then.", "Quick tools has Make a Word file from a PDF and Reviewer markups.", "Submit is named Submission Check. The readable copy is no longer written beside the effort, and the Effort health card is gone; the effort is still checked when it opens."],
    "4.60.0": ["The menu on the left is laid out again, and it is the same with or without an effort open. Quick tools is first. Then the effort's pages, with no numbers: Overview, Documents, Graphics, Deliverables, Shred, Matrix, Outline, Setup, Drafts, Submit. Then Standards and Formatting: Global Standards, Rules, Team References, Templates, Page Layout, Styles, Quick Parts, Check a Draft. Settings is last.", "Calendar and Tasks are tabs of Overview. Matrix and Outline are two pages. Deliverables is in the menu, and Redlining opens from it (Prepare a redline, Check a redline, Exceptions). The Team entry is gone: what it held is listed under Standards and Formatting, and Team defaults is in Settings, under Team data and training.", "With no effort open, an effort's page says in one sentence what it is for and has one button, Open or create an effort.", "Quick tools has Redline a document: choose a PDF or a picture and get a Word file beside it to mark up and return, with no effort needed."],
    "4.59.4": ["Stationkeeper starts much faster. Its window is now put together first and given its look once at the end; before, the look was worked out again for every part as it was put in place.", "Counting which buttons are used no longer runs on everything the window does, so the window stays quick while a document is read in the background. A menu that opens on a right-click and closes again may not be counted.", "An update, or rolling one back, now saves and closes your work before the program's files are changed, not after.", "Bringing in a document as parts (one per Word section) is quicker: each part is made without copying the whole document first."],
    "4.59.3": ["Stationkeeper starts faster and stays quicker while it reads in the background. Two of its helpers (the one that sets up tables, and the one that keeps the mouse wheel from changing a choice) ran on every single thing the window did; they now look only at what is on screen.", "Reading a large customer document no longer freezes the window for a minute when its pieces are linked: the same links are found without reading every instruction again for every piece.", "If Stationkeeper stops soon after it reopens your last effort, the next start does not reopen that effort and says so. Open it from the Effort box.", "A file that comes into the effort's folder by itself is no longer taken as a new version of another document because its words or its name are alike; it is added as a document of its own. A Word copy that Prepare made is not added to Documents at all.", "Page Layout: New, Rename and Remove work (they gave an error). Double-click on a find's picture zooms in again."],
    "4.59.2": ["Redlining is in the menu again, below the steps with no number: redlining can happen at any point. It lists the documents marked Redlined Deliverable, with its three parts, Prepare, Check and Exceptions. A document's tile on Deliverables and its right-click still open it.", "With no document marked, Redlining shows one line and one button, Choose a document...: it lists the effort's PDFs and pictures; the one you pick is marked Redlined Deliverable, gets its tile on Deliverables and is listed. Add a file... goes to Documents.", "Redlining can be pinned in Quick tools. A file outside any effort is still prepared from Quick tools: drop it, then Prepare it for redline."],
    "4.59.1": ["A line a table type's look takes away (none in the workbook) is now left off the table in Word, as the Stationkeeper Macros do. Before, the app drew the line from the look below it: the Figure table showed lines around a figure, and an effort's header that took away its bottom line still had one. A line the look does not mention is still the one below it."],
    "4.59.0": ["Global Standards.xlsx and an effort's workbook now say what they are on a Read me tab, the first tab: This workbook is Global Standards, Effort Standards or Program Standards, and who it belongs to, with the same text the Stationkeeper Macros write. The About tab is gone; the format number is at the bottom of Read me. A Read me tab already there is kept as it is.", "An effort's workbook is now named <effort> Effort Standards.xlsx, and a program's <program> Program Standards.xlsx. One under the earlier name, <effort> Effort Formatting.xlsx, is renamed once (while it is open in Excel it is renamed the next time). If you pointed the Stationkeeper Macros at the old file, point them at the new one.", "A workbook that says it is the other kind is not read and never written over: an Effort Standards workbook in the team's folder is not taken as the Global Standards, and the Global Standards is not taken as an effort's. The line at the bottom says why."],
    "4.58.0": ["Global Standards.xlsx and an effort's formatting workbook are now written the plain way, the same as the Stationkeeper Macros' New Workbook: each column says what it holds and its unit (Number format, Left indent (in), Top margin (in), Edge above), every column is always there, and a choice is written in Word's own words (Justified, Exactly, 1, 2, 3, Portrait) with a drop-down to pick from.", "A table type's kinds of row are yes or no columns (Has header row). Where a type has a look of its own for a kind of row, that look is a row of its own on Table looks, named after the type and the kind of row (Shaded header), and the type names it. Two types with the same look share one row.", "Fonts allowed is one row per font, with what it is used for. Rows you wrote yourself, with their own sizes and notes, stay as you wrote them until a change in Stationkeeper touches that use.", "Before Stationkeeper first writes the new way over a workbook written the old way, it keeps a copy of the workbook as it was, once, in its own data folder (Workbooks as they were before 4.58). A PC on 4.57.0 will not read a workbook written by 4.58.0 and says to update first; 4.56.2 and earlier must not open it."],
    "4.57.0": ["Global Standards.xlsx and an effort's formatting workbook can now name their columns the plain way (Number format, Top margin (in), Edge above) or the way Stationkeeper writes them today. Stationkeeper reads both and gets the same values. It also reads Word's own words in a cell (Justified, Exactly, 1, 2, 3), an edge typed as a width and a color, and a table type's rows and looks as plain columns.", "A phrase marked Draft or Retired on the Phrases sheet is no longer checked for, and stays on the sheet.", "A workbook written by a newer Stationkeeper is not read and is never written over: the line at the bottom says to update this PC first. Stationkeeper still writes the column names it wrote before."],
    "4.56.2": ["Global Standards.xlsx and an effort's formatting workbook: a sheet Stationkeeper does not know (a Read me, a list the Stationkeeper Macros keep, a sheet of your own) is still there after Stationkeeper writes the workbook. Before, only columns of your own were kept.", "When the workbook changed in Excel or from Word while a change of yours was waiting, Stationkeeper reads it first: both changes are kept. A row changed in both places keeps the workbook's values and the line at the bottom names it. A changed workbook that cannot be read is not written over."],
    "4.56.1": ["Acronym Finder and Acronyms: when the acronym list file is open in another program (Excel, a sync tool or a virus scanner) and cannot be saved, your decisions and the terms you add by hand are kept and come back when you open the window again, and the file is saved as soon as it is free. Before, they came back undecided. The line beside the tabs says when a save had to wait, and NOT SAVED shows only when it did."],
    "4.56.0": ["Acronyms > On the page: a decision moves on by itself. Enter adds the term to the effort list (with a definition or without one), X marks it Not a term for the whole effort, N skips it and L marks it for later; each selects the next find to decide, then goes to the next page with finds. Not a term on this page only stays on the card as a smaller second choice.", "Later asks why: Come back to it (L or Enter) or For author review (R), with an optional note. A term marked for later is not counted as to decide; the counts name it (12 to decide, 3 for author review, 1 for later), Everything found has a filter for each reason, and the mark is kept with the effort and with the Acronym Finder's list. Deciding the term takes the mark off; Take the mark off is on its card.", "The card opens in a margin to the right of the page, 320 pixels wide, level with the find. It never covers the page.", "Fix a wrong read in the Candidate box and the four buttons read Fix and add to effort list, Fix and mark Not a term, Fix and skip and Fix and mark Later: one press saves the corrected read and decides the corrected term. The line under the page says both things, with Undo.", "Page done is gone: Next page with finds is the main button, and a page with nothing left says Nothing to decide, as of the last scan. The word ignore leaves the Acronyms page: Not a term is the one word."],
    "4.55.0": ["Matrix & Outline > Outline lists the pieces typed Structure in Shred, and the pieces that only look like they set the structure (marked Suggested), each in the customer's words with where it is. Use it reads one piece into headings to check before they go in; Show on its page opens it in Shred. With none, Outline says so and offers Go to Shred.", "When our outline already has a structure, Use it asks first: Add to our outline, or Replace our outline, with how many headings each adds or replaces and which placed requirements would lose their place. Those requirements stay in the matrix, not placed. The start card leaves once a start is chosen.", "Place shows the document picker and Fit width, and nothing else from Shred's document row.", "The Matrix page opens on the matrix. Design... opens the view, the columns and the rows beside it, with Save as a view... at the foot.", "Make the setup shows what is ready and Make, and one line saying how many kinds of reference text go in the file and how many are hidden. Their styles are set in Effort Formatting > More > Reference text in the setup...; an open line in the ready list links to the page where it is fixed."],
    "4.54.0": ["Shred is one page with two views, chosen at the top under See it as: On the page and As a table. The table has a row for each piece: its ID, type, section, page, the word that makes it a requirement, and the piece. Click a column heading to sort by it. Filter by document, by type, or Not shredded only. A suggestion waiting shows its type with a question mark.", "A type set in the table is the same as one set on the page, with the same keys: a type's letter, Enter to take the suggestion and go to the next row not shredded, N for the next. Set type, Take the suggestion and Open on the page are on the table's bar; Ctrl+Z undoes in either view. Switching views keeps your place.", "Export > Draft compliance matrix... is on the table. It writes the rows shown, in the order shown, with an About sheet that names the documents, the date and the Production Datum.", "Quick shred is no longer a page of its own. On Quick tools a customer document now goes to Shred to setup, the same as the Overview's door: it asks which effort, adds the file to Documents and opens Shred. A pin to Quick shred opens Shred."],
    "4.53.0": ["Shred: Enter takes the suggestion and goes to the next piece not shredded, where its bar opens. With no suggestion waiting Enter does nothing. A chip or a type letter sets a type and stays; N still goes to the next piece not shredded. Ctrl+Z after Enter takes the type back and selects that piece again.", "The bar at the selection opens beside the piece, in the page's right margin, level with it, in one column: the suggested type first, then the other types, Capture, Ask a question, Combine or Split when they apply, and Take the suggestion. The page keeps that margin on Shred, so the bar never covers the text. The bar can no longer be dragged.", "The piece pane says how many pieces of the document are not shredded yet, and the keys: Enter takes the suggestion and goes on, N for the next."],
    "4.52.0": ["The app opens on the Overview. With nothing open it shows a place to drop a document and three doors: Acronyms, Shred to setup and Check a document. Each asks where the work goes in the same step: the open effort or program first, another one, a new effort or a new program.", "With an effort open the doors are a row under your next step. A program shows Acronyms and Check a document. Check a document is today's Audit against the standards, and it changes nothing. Shred to setup adds the customer's document to the effort's Documents, then goes to Shred.", "The menu shows the effort's steps only while an effort is open. Calendar and Tasks appear once an effort exists and read across every effort, each line naming its effort.", "Ctrl+K lists only what can be done right now, and can start a door, a new effort or a new program."],
    "4.51.0": ["A file dropped on Quick tools now asks where it goes in the same step as what to do with it: the open effort or program first, another one, a new effort or a new program. A new one needs only a name, filled in from the file's name.", "Unfiled takes no new work. Work it already holds stays where it is, can be opened, and is shown as Unfiled, from before; the app offers once, at start, to name it as an effort or a program.", "With nothing open, a page that needs an effort says so; it no longer opens Unfiled."],
    "4.50.0": ["Programs are a second kind of home beside Efforts, for program documents. All Efforts > Programs lists them; + New program asks for a name only.", "A program opens on its Overview and shows Overview and Documents. It has no steps, Calendar or Tasks.", "Program deliverables is no longer offered when an effort is started. An effort of that type is offered a move on All Efforts > Programs, which changes nothing until you say so."],
    "4.48.1": ["For whoever keeps the Production Datum: six smaller lists Stationkeeper carries inside the program join the part Values once built in the next time a change you save becomes a version: the days each stage takes by default, the field recipes, the after-submission checklist, the cover's property names, the default front matter, and the section-title synonyms. A Datum already made on 4.48.0 gains them and keeps every value it holds. Nothing on any page changes, and nothing has left the program."],
    "4.48.0": ["For whoever keeps the Production Datum: the next time a change you save becomes a version, the rules, effort folders, stages, phrase list, topics, effort types and page numbering scheme that Stationkeeper has carried inside the program are written into the Datum as one more part, exactly as they are. It happens once, by itself. Nothing changes on screen and nothing has left the program yet; this makes sure the Datum holds them first."],
    "4.47.1": ["Where something is made, the app says which Production Datum it worked from: in Make the setup's Ready to make list, on the template builder's line, and as a Working from line in the Final Checks (a person's look when none is installed).", "A new effort remembers the Production Datum it was started on; Edit details... shows it. Efforts started earlier say nothing, since nothing is guessed."],
    "4.47.0": ["The Production Datum: the name for what a PC installs to work the way the team does (the Global Standards, the acronym database and the custom dictionaries). A mark in the top bar, on every page, says which one this PC is on: No Production Datum installed, Production Datum 14, or Production Datum 14, 15 is ready.", "Click the mark for one small panel: with nothing installed, one sentence and Connect; installed, its number, when, and what it holds with counts; a newer one ready, which parts will change and Install Production Datum 15. Connect is two actions: Connect from a file... and Connect to a folder... Settings has the same two.", "Nothing is restricted without one. The number is the Global Standards version number, continued. The exported acronym list names the Production Datum it was made from."],
    "4.46.0": ["One word for one thing, from the UX review. Documents > Amendments is now What changed, and every button and sentence that points to it says so. The menu group Templates is now Formatting; its pages keep their names.", "Acronyms: a find's status is said in plain words on Everything found, the card, Details and the acronym lists (New, no definition on record; Choose a definition; In the acronym database; Added to effort list; Ignored). Exports use the same words, and the exported Excel list has a second sheet, About this list, naming the effort, when it was made and the files scanned. Nothing saved in an effort changes.", "Styles and Quick Parts: the button says what comes in (Bring in styles..., Bring in parts...) and shows once: in the empty page, or at the top when the page has content. The chips under Shred's title have no numbers."],
    "4.45.0": ["Templates: point at a part of a sample page in the builder to see which pick made it; a click picks another. Once Word's pages are kept, one button goes between them and the sample pages."],
    "4.44.0": ["Templates: Draw with Word in the builder shows the exported file's own pages, labelled Exact. Word can take a minute or more; the pages are kept until a pick changes."],
    "4.43.1": ["Proposal managers and production leads build, change and archive templates; everyone else looks inside one and exports it.", "Saving acronym and matrix decisions runs in the background again.", "The program's record of problems now notes Qt's warnings, a window that stops answering, and cleanup errors: fixed words only."],
    "4.43.0": ["Templates opens a gallery: one card for each template, with what it is made of. A card has Export and " "Duplicate; its right-click has Archive, and the Archived view brings a template back.", "New template... opens the builder with nothing picked. A double-click on a card opens the same builder on " "that template. The builder picks what goes in; it never changes a piece.", "The builder shows sample pages drawn from the picks, so a pick is seen at once. They are the app's own " "drawing, labelled Approximate.", "Every export is checked: the app reads the file back and says whether it holds the page, the page " "numbers, the styles and the Quick Parts that were picked.", "The menu reads Templates, Page Layout, Styles, Quick Parts."],
    "4.42.0": ["Page layouts and numbering are named components a template picks, beside its style sets and Quick Part set. "
               "Template > More > Page layouts and numbering... keeps them.",
               "New... takes a page layout or a numbering from the Global Standards or from a profile, so nothing is typed "
               "twice. Change the page... sets a page layout's paper and four margins.",
               "What goes in has two new picks: Page layout and Numbering. With no pick the template reads the Global "
               "Standards, as before.",
               "Setup > Templates for the volumes says when a volume's template and the volume's own standards differ on "
               "margins, paper or numbering, since the checks read the volume's standards."],
    "4.41.0": ["An effort type names its templates. In Effort types..., Templates... sets the template each of its profiles "
               "starts with: style sets, Quick Part set and starting pages come together.",
               "Start an effort says what the chosen effort type starts with, before you create it.",
               "Setup > Templates for the volumes offers the effort type's templates for the volumes with none picked; "
               "one button picks them, and a volume can still pick another."],
    "4.40.0": ["Quick Parts keep versions the way styles do. Change a Quick Part and every set that uses it gets the change; "
               "until now each set kept the version it had.",
               "Versions... on a Quick Part's row lists every version with its date and the sets that use it. Restore this "
               "version puts an earlier one on top as a new version; nothing is removed.",
               "Create another version... makes another Quick Part of the same name for the part sets you tick. The row "
               "then has one tab for each, named for its sets.",
               "A set left on an earlier version is named on Parts; More > Use the latest Quick Parts in every set moves it."],
    "4.39.0": ["Template shows the selected template whole: five rows under the list, one for each component (styles, "
               "Quick Parts, page layout, numbering, starting pages), with where it comes from, what it holds and "
               "whether it fits the others, in color.",
               "One line says the template is ready to make, or names the component to look at first.",
               "Double-click a component to open the page that changes it."],
    "4.38.0": ["Parts: a Quick Part set goes with a style set (More > This set goes with a style set...). With the set "
               "picked, each Quick Part's styles show green when the style set has them and red when it does not, and a "
               "line above the rows says how the set fits.",
               "One button adds the styles you already have to that style set.",
               "Bring in from a document offers the styles the Quick Parts use that you do not have, so parts and styles "
               "arrive together, into the style set the part set goes with.",
               "Make templates warns when a template uses a Quick Part set without the style set it goes with."],
    "4.37.0": ["Parts: each Quick Part's row names the styles it uses. A style that is not among your styles shows in "
               "red, and the selected part says what a template would do about it.",
               "Make templates checks the Quick Parts against the style sets: it names each style a Quick Part uses that "
               "the template's style sets lack. Until now such a style came in from the Quick Part's own file, unseen."],
    "4.36.0": ["Effort Formatting shows where the effort's standards differ from the Global Standards: each difference on "
               "its own row, in color, with this effort's value and the Global value side by side.",
               "The effort's own value is the one in use. Choose Global on a row to use the Global value there, and "
               "This effort to go back. Neither value is lost, so each choice is made and unmade in one click.",
               "See the changes..., Take for this effort and Send to the Global Standards are gone from the effort."],
    "4.35.1": ["Create another version... on a style's row makes another style of the same name for the sets you tick, "
               "such as a tighter Body for Page-limited RFP. A set holds one style of a name, and the two are told apart "
               "by their sets. Each has its own history; a change reaches the sets on that version and only those.",
               "Bring in from a file on Styles shows each value a document would change in a style you have, before "
               "anything changes. Two ways: Only what differs (your style keeps everything else) or Everything the "
               "document has (your style becomes the document's).",
               "A style brought in over one you have is that style's new latest version, for every set that uses it. "
               "Keep both and Skip stay on the row; Bring in no longer waits for an answer on each."],
    "4.35.0": ["A style has one history. Each saved change is a new version, and the latest is the one in use in every "
               "set that uses the style. For a different look in one set, use Duplicate...",
               "Versions... on a style's row lists every version, latest first, with when, who and what changed. "
               "Restore this version puts an earlier one on top as a new version; nothing is removed.",
               "More > Restore every style as of... takes every style back to a time you pick, after showing which "
               "would change. More > Undo the restore puts back what was latest."],
    "4.34.0": ["Global Standards has its own page, in the menu beside Settings. It opens whether or not an effort is open "
               "and always changes the Global Standards; an open effort keeps its own standards.",
               "A change saved there reaches everyone at once: no Update button. Other PCs get it the next time they "
               "open Stationkeeper. The number is in the window's title on every PC.",
               "Who has it: each PC that reads the linked folder leaves its own line, with the version it is on.",
               "Save a file to share... writes the Global Standards in one file for a PC with no shared folder."],
    "4.33.1": ["A style's form names its numbering: a heading level's style says Heading numbering and its level, a list "
               "level's style says which list. Change the numbering... opens that scheme in the standards, where every "
               "level of it is set; your saved schemes stay in the library."],
    "4.33.0": ["Global Standards: Install a file... on Settings > Global Standards takes a version on a PC with no linked "
               "folder. Each update writes the version's file (Global Standards version N.skgs) beside its folder. The "
               "file is checked whole before anything on the PC changes.",
               "After a version is taken, the card says what it changed on this PC. What changed... lists each change "
               "with who updated and when; Mark as seen closes it.",
               "A PC with no linked folder and no version says it runs on the built-in starter, with the two ways in."],
    "4.32.0": ["An effort's standards are its own set. The first time an effort opens it is given the Global Standards as "
               "they are on this PC; from then on a change on a standards page while the effort is open changes that "
               "effort only. The line under the page's title says which set a change goes to.",
               "Effort Formatting has an Effort Standards card: where the set came from, what the effort changed, and "
               "when the Global Standards have changed since. See the changes... lists each value; Take for this effort takes "
               "them, and nothing is taken until you say so.",
               "A change made in an effort reaches the Global Standards only by name: See the changes... > Send to the Global "
               "Standards. With no effort open, the standards pages change the Global Standards as before."],
    "4.31.0": ["Global Standards, step 2: Settings > Global Standards has Link a folder... (a SharePoint library synced to this PC, "
               "or any folder). A PC takes a newer version when the app opens, or at once with Use it now. What the PC itself "
               "had changed is kept in a dated backup and named once.",
               "Someone who can write to that folder sees Update Global Standards...: the changes waiting on the PC, each "
               "with the version's value and this PC's, Put back to drop one, a note, and Update to version N... It needs no "
               "effort open.",
               "One name: Company Standards (Default) is Global Standards on every page. The workbook is Global "
               "Standards.xlsx; the one you have is renamed once."],
    "4.30.8": ["Acronyms: capital-letter terms written together with a slash, an ampersand, a hyphen, a period or an underscore "
               "are offered once: the joined term, or its pieces when each piece is a term of its own. Never both.",
               "More on the card: These are separate terms (on a joined term) and This is one term (on a piece). The answer is "
               "kept with the effort and holds on every later scan.",
               "A term of nine capitals or more is found. A Roman numeral (Volume III) is not offered. A term that starts with a "
               "digit is one term, not a unit."],
    "4.30.7": ["Acronyms, The list: the card no longer piles up as you decide (buttons and boxes from earlier cards stayed behind).",
               "The card's two lines are Candidate and Definition. Words selected on the page show on the card, with As the candidate "
               "and As the definition; the second text box under the page is gone.",
               "A term clicked on the page is selected in the list too. Each suggested definition is listed once. Sources and "
               "timeline is under More.",
               "Styles: a paragraph style's own form (double-click it) sets line spacing, indents and tabs, and says which list "
               "level a numbered style is."],
    "4.30.5": ["Fixed: the program could end by itself while you decided acronyms quickly. The next term's picture is no longer "
               "drawn ahead on a second thread.",
               "Bringing styles into a set: where the set already has a style of that name with other values, the row says "
               "Duplicate style with different values detected, with Keep both, Replace and Skip.",
               "Keep both brings the file's style in under a numbered name (Body Text 2). A set never holds two styles of the same name.",
               "Bring in waits until each flagged row is answered."],
    "4.30.4": ["Large documents, Shred: selecting a piece, putting a type on it, typing thousands at once and Undo no longer wait "
               "on the size of the document. Saving a large matrix is several times faster.",
               "Acronyms, The list: click a boxed reading on the page to decide the term in it; click a row of the list to go back.",
               "Acronyms: a search fills the list once, a moment after your last key, and no small windows flash.",
               "If the program ever ends by itself, the record kept for support now names the part that failed."],
    "4.30.3": ["Large documents: a decision on Acronyms no longer freezes the window, with thousands of finds. Decide one or many, "
               "add one or many to the effort list, or switch between Undecided, Added and Ignored.",
               "Your decisions are saved by themselves a moment after the last one: Saving your decisions, then Decisions saved, "
               "shows beside the tabs. There is no step to take.",
               "Reading a file says the page it is on, the picture on that page, the time so far and the time left.",
               "Documents no longer takes the app's own published files (Stationkeeper Data) as documents."],
    "4.30.2": ["Styles: a set owns its styles. Two sets can each have a style of the same name with its own values; neither replaces the other.",
               "An identical style used by several sets is one style, shown once with the sets that use it.",
               "Bringing styles into a set asks only where that set already has the name with other values: keep the set's, take the "
               "file's, or keep both. A v1 / v2 switch shows only where a set keeps both.",
               "Changing a style from inside a set changes it for that set only, unless you pick every set that uses it.",
               "A set can say what it is used for (RFP, RFI, program documents): More > What this set is used for."],
    "4.30.1": ["The app's own working folders are out of sight in File Explorer: each effort's app data folder and the program's "
               "_local_sandbox. The folders you work in are untouched.",
               "Effort Record > More > Open the backups folder reaches the effort's backups whatever File Explorer shows.",
               "Hidden is not locked: File Explorer's Hidden items still shows them."],
    "4.30.0": ["Global Standards: the foundation every effort starts from is one set with a version number (Settings > Team data).",
               "A small window says Stationkeeper is opening while it starts, so there is no need to click again.",
               "Styles: double-click a style to see or change it. Right-click > Duplicate. Paragraph and character styles are told apart.",
               "Bringing styles in: every style is ticked, one box sets the set, and a style you already have joins the set."],
    "4.29.3": ["The Overview shows the effort's picture, its name in large type and the large due date again.",
               "Shred: the bar at the selection wraps and can be dragged by its grip. Capture and Ask a question are on it.",
               "Acronyms: how many finds are left shows large and follows each decision. Scan again is on the bar.",
               "Fixed: correcting a reading to a term already added no longer sends that term back to undecided."],
    "4.29.2": ["The marks read Redlined Deliverable and Filled-in Deliverable. The mark and its tile on Deliverables stay in step.",
               "A file dropped in the customer's folder is added by itself, For the shred. Redlines sits under 01_proposal.",
               "Graphics lists every picture the reader saw. A graphic need links to the picture that answers it.",
               "The Effort list shows the customer's page beside the selected term."],
    "4.29.1": ["Acronyms: Ignore here on the page, Ignore in this effort on the lists. No Next bar under a step.",
               "Settings > Appearance > Colors: Station navy, Slate and teal, or My colors by hex value, with Reset.",
               "Calendar has Add a date. Template Studio is a tab of Setup. Making a template is on for everyone.",
               "Add files once an amendment is in and one question asks which package brought them."],
    "4.29.0": ["Names: the Dashboard is the Overview. Rules & Dates is Submission Checklist. L to M is Crosswalk.",
               "Changes is Amendments. Acros & Abs is Acronyms. Theme tags is Themes. Evaluation is Evaluation Criteria.",
               "Piece types: Content Instruction, Format & Submission, Key Date, Evaluation Criterion, Response Structure."],
    "4.28.2": ["A template is its own named thing: Templates > Template. Name it, pick what goes in, make it.",
               "An effort picks a template for each volume: Setup > More > Templates for the volumes...",
               "Team defaults moved from Settings to the Team page."],
    "4.28.1": ["Styles: every row has a preview box of one size, the style drawn in it at its true size, its size beside it.", "The details lie across the width. A drag carries every selected style to a set."],
    "4.28.0": ["Templates is its own group in the menu: Styles, Quick Parts, Page Layout, Template.",
               "Formatting and Layout are one screen, Page Layout. Parts is named Quick Parts.",
               "Team keeps Rules, Check a Draft and Team References."],
    "4.27.3": ["Light and dark change every page at once. The menu is one navy in both.", "Settings > People: each person's role on the open effort is on their row of the author list."],
    "4.27.2": ["The top bar's button is Quick note. Undo left the bar: Ctrl+Z, a line at the foot, and History.",
               "Quick tools is at the bottom of the menu.",
               "Unfiled is a list on Quick tools, not an effort to switch to."],
    "4.27.1": ["Tasks is in the menu: this effort's tasks by gate, and yours across efforts as Late, Today, This week, Later.",
               "Calendar is in the menu: the month, the day's list, and what is coming up.",
               "Activity is a tab of the Dashboard: what happened, by day, with filters; a row opens its thing."],
    "4.27.0": ["The Dashboard entry opens the Overview: the effort on one screen.",
               "Your next step and the path, up to four counts that open where each is fixed, the deliverables, the Wall of Truth line.",
               "The calendar's next dated things, the customer, and the last three things that happened.",
               "The cards the Dashboard had are the next tab, All cards."],
    "4.26.1": ["Acros & Abs: select finds side by side and the bar combines them into one term, said before you press.",
               "Not a term is for this page only; everywhere in this effort is the second choice.",
               "The tabs are On the page, Everything found and Effort list. The page shows beside the list.",
               "On the page has a document picker that follows the document open in Shred."],
    "4.26.0": ["Shred: select pieces and a bar shows above them with the types, Combine, Split and Take the selected suggestions.",
               "This document is shredded is a checkbox. Add missed text: drag a box, right-click inside it.",
               "A piece typed Rule or Date has Make it checked... on its pane. Counts say not shredded.",
               "The compliance bar moved from the Dashboard to Shred. Next: Matrix & Outline is gone from Shred."],
    "4.25.5": ["Graphics is a page of its own, under Documents: one row per graphic, the customer's and ours.",
               "Each row says, for its current version, whether its words are read and its acros and abs are swept.",
               "A graphic need tagged in Shred is a row there too, with its status."],
    "4.25.4": ["Documents is in packages once an amendment is in: As issued, each amendment in the order issued, then Internal.",
               "A document's earlier versions sit on lines under it.",
               "Right-click a customer document > Package to say which amendment brought it."],
    "4.25.3": ["A document marked Redlined Deliverable or Filled-in Deliverable gets a tile on Deliverables, linked both ways, with no owner until someone takes it.",
               "Prepare for Redline left the menu: it opens from that tile and lists only documents marked Redlined Deliverable.",
               "Pages still to look at stop a redline and nothing else. Right-click the row: Prepare it anyway.",
               "An amendment shows on the tile: the source changed, the old redline is kept, prepare a new one.",
               "Drafts > Reviewer markups: a reviewer's commented PDF of a draft, into a copy of your Word file."],
    "4.25.2": ["Documents: Used for. Right-click a document > Used for and tick For the shred, Reference, Redlined Deliverable, Filled-in Deliverable. Several may be ticked.",
               "The marks take the place of Role. Shred extracts only what is marked For the shred.",
               "The filter beside Find shows what is For the shred or Returned to the customer, or one folder.",
               "Source (Customer or Internal) comes from the folder and can be changed for one file. Folders took the place of categories.",
               "Add a folder... keeps its nested folders and takes every kind of file."],
    "4.25.1": ["Put a file into the effort's folder and it is added to Documents by itself, for reference, where it sits. Any kind of file. A line says what came in.",
               "Documents names the effort's folder above the list; click the path to open it.",
               "The Trash is a folder you can see: Deleted, in the effort's folder. Only Empty the Trash, in the app, removes anything from it.",
               "A pasted picture is saved in the effort's folder, with its graphics.",
               "Left out of the watch: our volumes, Response Setup, Exports, Redlines, Deleted. The customer's folder keeps its table."],
    "4.25.0": ["Documents is one list. All, Customer and Internal (the new word for Ours) are chips above it; the two tabs are gone.",
               "The columns: Document, Type, Source, Version, Status. Status is empty unless a document needs you.",
               "Pages to look at no longer stand before the shred: the panel offers Shred it first.",
               "The panel says Not shredded, Shred in progress, Shredded."],
    "4.24.0": ["All Efforts: Efforts and Archived are two buttons. An archived effort can be deleted from Stationkeeper (right-click); its files stay unless you tick the box.",
               "Dashboard: click the due date to set it. The fold button stays in one place.",
               "Settings is in sections by subject: Appearance, General, Efforts, People, Document types, Shred and responses, Team data and training, Updates and help. Stages, gates and roles and Roles and Preview tools are not shown for now.",
               "One work setting, the team folder (Settings > General). Nothing is asked at first start.",
               "A new effort gets eleven numbered folders (Settings > Efforts > Folders and file names changes them). An effort made before keeps its folders.",
               "Document types: the initial is the type's short name (RFP, Sec L, Amd). Add a type... is the first line of every type box. Numbering is by itself.",
               "The scan finds four more shapes: 5G, mA with no number, Wi-Fi, xApp.",
               "Prepare for Redline: a cover's large lines are plain paragraphs, not headings."],
    "4.23.3": ["The scan finds three shapes it passed over: one letter and digits given in brackets (C2), initials with periods (U.S.), and a small letter before capitals (eMASS).", "Two wrong finds are gone: the word after a designator read as a unit (F-35 feed), and a unit with the sentence's period listed a second time (dB.).", "A document deleted from the effort leaves Acros & Abs too: its page and the terms found only there.", "Watched folders: Stop watching and Check now answer in the window, with how many files were looked at.", "Documents no longer shows the roles to confirm count."],
    "4.23.2": ["Drafts > Acros & Abs: a term our drafts use that is not in the list is decided right there, on its row: type what it means, then Add to effort list, or Not a term. No jump to Shred.", "Acros & Abs: Scan files... is on the bar, for a file handed to you.", "What's new fits the screen and scrolls, and sits on Settings > Updates.", "Check program files is now Verify program files. Undo last update is now Roll back the update: it asks first, names both versions and lists what goes away.", "Fixed: deleting a document stopped with an error when its file could not be moved to the Trash; the delete now finishes and the Trash says which file was not kept.", "Fixed: Shred's document list still offered a document after it was deleted."],
    "4.23.1": ["The acronym card has two lines. Reads as is the term: fix it there if it was read wrong, and the list gets what you type, with or without a meaning.", "Means is the definition: pick one, type one, or leave it empty.", "Gone from the card: Read here, Use as the definition, The picture says something else. Words selected on the page go to either line (Put in Reads as, Put in Means).", "More: Add to the Wall of Truth, for a term this customer uses in its own way.", "On the page, a plural of a term in capitals is marked (RFPs marks RFP).", "Fixed: an error on every repaint of the line between the page and the card in Acros & Abs Finder; two errors the program recovered from (Effort home's drafts, the readable copy)."],
    "4.23.0": ["Acros & Abs, decide and move on: Add to effort list moves to the next term to decide, as Not a term does.", "Add a term is the main button. Next to decide and the Copy button are gone; In our drafts and the report are under More.", "The counts row shows To decide and In the list; the other filters are under More as Show only.", "One export: the list, the whole effort or one per volume.", "Acros & Abs Finder: Send the list to an effort... puts its terms and meanings into an effort's acronym list."],
    "4.22.0": ["Prepare for Redline, under Documents: every PDF and picture in Documents is a row with one Prepare button; no More menu.", "The Word file reads like the PDF: its pictures, its headers and footers as Word's own, each paragraph's font, tables, and text that flows from page to page with no text boxes.", "A reviewer's comments on the PDF come in where they were made: tracked changes for cross-outs, inserts and replacements, Word comments for highlights and notes.", "Put its comments into my Word file...: the PDF's comments into a dated copy of a Word file you already have; the comments it holds are kept.", "A picture or a scanned PDF is prepared from the words read on it, its figure kept. Your Tools: Prepare it for redline, for a file outside the effort.", "A picture with no background (a see-through PNG) is read and shown on white; it was black where it had no background."],
    "4.21.0": ["Shred's pane says where a piece goes: Goes to names the pages that read each type.", "A page limit on a required heading is the section's pages: the Matrix's page allocation and Drafts > Status show it.", "Submit > Report checks the required structure: a required heading renamed, taken out or moved.", "Rules & Dates says Listed here for a piece typed Rule or Date; only a rule the reader found or one you add checks Effort Formatting and Submit."],
    "4.20.1": ["The Guide (F1) reads in the menu's order and its pages for Documents, Shred, Outline and Coverage describe the app as it is.", "Messages that named steps that are gone (read into Review, Verify, Bins) now say what to do today."],
    "4.20.0": ["One word for one thing: a piece is anything the shred holds, a piece with a type is shredded, and the count reads the same in the menu, on Shred, in the List, on Documents and on the Dashboard.", "Old page names are gone from the screens: Shred (not Review), Documents (not Library), Changes (not Compare), Acros & Abs on every page name, Team (not Production).", "Effort Formatting says Company Standards and Make it a standard; Effort Profiles and Template Studio say Sections and Sections and numbering.", "Your Tools' tiles carry today's page names; the quick shred is Quick shred."],
    "4.19.0": ["Start our structure: type the customer's structure pieces Structure (O) in Shred and read them into our outline with Required by, or draft headings from the customer's headings, the SOW or PWS, or the evaluation factors.", "Shred's List shows the shred under the customer's headings with what is decided; the quick shred, accuracy and theme tags moved to Your Tools."],
    "4.18.0": ["Shred: drag over any words and right-click for Compliance language: just here, everywhere (the compliance words list), or not here. The piece keeps its type; the words come out in the compliance style in the matrix, the outline and the setup.", "Levels are H1 to H9 in the Setup builder and Shred's outline, as in Fix text's headings."],
    "4.17.0": ["Documents: Replace the file... and Read it again keep the document and its version and read it again into the shred, decisions kept; Delete... and Delete this version... move everything to the effort's Trash, with Undo and Restore.", "Shred > Fix text > Heading: H1 to H9, or Not a heading; the pieces below take its number and title, and unnumbered headings go into the RFP's own outline with their pages."],
    "4.16.0": ["Redline brings the comments reviewers left on the PDF in Acrobat into the Word copy: cross-outs, inserts and replacements as tracked changes, highlights and notes as Word comments on exactly their words, replies and Completed kept.", "Check lists every comment and says which were placed by position; Exceptions makes a row of each."],
    "4.15.0": ["Redline makes a deck saved as PDF into slides: one Word page a slide, the slide's pictures, charts and shapes behind, each box of text where it sits, editable and checked word for word.", "Tables with no borders and no tags come from the gaps between their columns; a table drawn inside a cell stays inside it."],
    "4.14.0": ["Redline reads the tags Word writes into a PDF: a table with no borders and a table inside a cell come out as Word tables.", "A table that runs across pages is one table, its header row kept once and repeated by Word; lists and paragraphs inside a cell stay apart; turned header text stays turned."],
    "4.13.0": ["Redline's copy reads tables from the borders the PDF draws: merged cells, empty cells, wrapped cells, shading, rules-only tables and rotated headers come out cell for cell.", "The copy keeps each page's size, orientation and margins, the body font and size, the space between paragraphs, indents, centering and headings as set."],
    "4.12.0": ["On Shred, Capture > Contact, Key date or Effort detail opens a card in the pane that stays open: pick words on any page and Take them into a field; several phones, e-mails and addresses, each labelled.", "Captured from this piece lists each capture with Open (edit it in place) and Take out; a Deliverable piece picks which deliverable it describes.", "Delete a deliverable from its page, a card's right-click or the List: it asks first, and Undo (Ctrl+Z) puts it back.", "Redline sits in the menu under Documents.", "Fixed: a rare close with no message as a background job finished (Full Text, Read, adding documents)."],
    "4.11.0": ["Redline's Word copy makes real Word tables from where the PDF's columns sit; a cell that wrapped stays in its cell.", "Check compares a table's words cell by cell and says how many tables it made, to look at beside the PDF."],
    "4.10.0": ["Suggestion rules are one team list in Company Standards.xlsx, with how often each was kept or not right; Not right and Make it a team rule... on Shred.", "The workbook has a Theme sheet (colors and fonts); an effort's workbook a Volume column; Settings > Team library has Read it now."],
    "4.9.0": ["Each effort's folder holds Stationkeeper Data, the read-only snapshot Stationkeeper Macros reads: rules, the effort's template and dictionary.", "Published within seconds of a change: only changed parts, each renamed into place, the manifest last; the revision only goes up."],
    "4.8.0": ["Redline, below the six steps: Prepare makes a clean Word copy of a customer PDF (real headings, the numbers as typed, no running headers).", "Check compares the copy with its PDF word for word, and finds a returned redline's edits made with Track Changes off.", "Exceptions makes a table of every tracked change with the customer's number, both texts and the comment; Excel or Word."],
    "4.7.1": ["The small lists are sheets of Company Standards.xlsx: Phrases, Authors, Compliance words, Piece types, Document types.", "The master acronym list is Lists\\Acronyms.csv and each dictionary a Word .dic in Lists\\Dictionaries, both ways."],
    "4.7.0": ["The Company Standards (Default), was global standards: their values in Company Standards.xlsx in the team library, edited in Excel or here.", "Organizing columns, grouped property columns, Other Word settings; only Approved rows reach templates; your own columns kept.", "The Word files beside it in Content, both ways; each effort's Effort Formatting.xlsx with only its changes.", "Field recipes show what a field gives while you type it (Table 2-2)."],
    "4.6.0": ["Documents: Customer and Ours tabs, Add documents..., Type, Governing version and Text, Shred and Terms progress marks; one panel.", "Changes: a card per change with No impact, Re-shred and Ask a question; Next change; Open in Word as tracked changes.", "The menu shows what is left on every step; Acros & Abs scans documents as they arrive; the Acro List is Acros & Abs > Every term.", "Rules & Dates in three groups with Used by; Outline asks whether the solicitation prescribes it; PDF reading one call at a time."],
    "4.5.0": ["Shred has one job: type chips that toggle in the piece pane; a piece can be several things; the suggestion dashed, Enter takes it.", "Capture is one menu; Ask a question cites the piece; Mark this document shredded opens the next one; the rest is in More.", "Place, L to M and Coverage show none of Shred's controls; Place it (Enter), Another section..., Leave it out....", "Changed by on the pane; running headers in Suspects; a prescribed outline marked as the customer's with its page limits."],
    "4.4.0": ["Drafts by volume: More > Volume folders... gives each volume its folder (a synced library); Read the drafts reads the newest Word file in each, a table of volumes, a volume clicked shows its sections.", "Drafts > Acronyms: each volume's draft against the acronym list; a term not in the list goes back to Acros & Abs marked From our drafts until it is decided there. In our drafts on Acros & Abs opens it.", "Settings > You shows Appearance: Follow Windows, Light or Dark."],
    "4.3.0": ["Matrix & Outline: Outline, Place, Matrix, L to M and Coverage. Shred says what each piece is; Place puts it in our outline.", "Outline asks once whether the solicitation prescribes the outline or we build our own; the builder moved here from Setup.", "On Place, right-click Leave out of the matrix... with a reason; the export lists left-out pieces on their own sheet."],
    "4.2.0": ["Adding a customer document extracts it for the shred at once; a new version keeps the pieces that did not change. The matrix keeps a dated copy each day in Matrix history.", "Fix text (F2) is a mode inside Shred: combine, split, a heading, set aside a header or footer, missed text, Suspects (F3) and pages checked. Text check left Documents.", "A sentence the page break split is joined and marked; Shred's page draws as you scroll, and a drag at its edge scrolls on."],
    "4.1.0": ["Shred says what each piece is: Requirement, Instruction, Rule, Date, Evaluation, Deliverable, Information or Not applicable, each with its key.", "Pick a customer document in Shred: it is extracted at once and opens when done. Shred's tabs are Requirements, Rules & Dates, Evaluation and Acros & Abs (with the Acro List).", "The Q&A log is a drawer on Shred, Matrix & Outline and Drafts. Changes decides each change: No impact, Re-shred or Ask a question."],
    "4.0.0": ["The menu is the effort's six steps: Documents, Shred, Matrix & Outline, Setup, Drafts, Submit.", "Documents: click a document to see what has been done to it and its one next thing; right-click to open it, set its type, add a newer version, leave it out or show it in its folder. Changes and Text check are its tabs.", "Shred holds Extract, Requirements, Acros & Abs and the Acro List; Drafts holds Status and Edit."],
    "3.98.0": ["Parts lists Quick Parts by what they are: Tables, Callouts, Headers and footers. The Quick Parts tab is gone from Standards; a part's details open from its row.", "Right-click a Quick Part, Change it...: the style first (Let the styles decide), Make a variant (padding, widths, row height, table style, a style swapped), or Open in Word and Bring back. Each is a new version.", "Paragraph and character styles are on Styles only; Every value... opens Formatting on one."],
    "3.97.1": ["A workbook brought into Setup takes the compliance words list, as an outline built in the app does. One order decides each piece: what you selected, then a rule saved with the layout, then the words list, then the column's own style.", "Select words in the workbook, right-click: Compliance language (Just this, Everywhere it looks like this, This word everywhere).", "The setup styles live in Styles, in the Setup set: a look changed on the setup screen is saved there and every setup takes it."],
    "3.97.0": ["Make templates > What goes in: style sets in order (the lower one wins), the Setup styles (hidden) and a Quick Part set, picked from the libraries; nothing is edited there.", "The document starts with: pages from Parts in order (a cover, a CUI page, a title page, contents, acronyms), each in its own Word section before the body and also in the Quick Parts gallery unless its switch is off.", "Each style goes into the template exactly as Word wrote it. The checks before it is made say what is missing."],
    "3.96.0": ["The menu is the effort's path: Dashboard, 1 Customer files, 2 Review, 3 Setup, 4 Write, 5 Submit, then Team and Settings; each step says what is left. The effort switcher at the top holds another effort, All Efforts and Your Tools; Ctrl+K goes to any page.", "Review's tabs are steps with counts (Verify, Read, Compare, Place), and See it as shows Our structure, Requirements, Sort, Matrix, L to M or Coverage. Every page in a step ends with its next step.", "The Dashboard is the map: five step cards, Your next step and this week. Team is one page of tiles by role."],
    "3.95.0": ["Team > Standards > Parts (was Section designs): covers, CUI pages, title pages, front matter, back covers and Quick Parts, each kind a tab; one row per part with its versions as tabs and the part sets it is in.", "Bring in from a document reads a Word file once: its pages (one per Word section, each said to be a cover, a CUI page, a title page...) and its Quick Parts gallery; tick what you keep and pick the part set.", "Open in Word, then Bring back as a new version: the first version stays, what fills it carries over. Part sets hold one version of each part."],
    "3.94.0": ["Team > Standards > Styles: every style you keep, one row each with its font, paragraph and character treatment and a preview; its versions are tabs on the row.", "Sets group styles by use, each with a color: drag rows onto a set. A set holds one version of each style and says when a newer one comes in.", "Bring in from a document reads only the styles of a Word file: New, Different from yours (a new version) or Already have it, side by side. Each style keeps Word's own definition."],
    "3.93.0": ["Acronyms has two tabs. On the page: the customer's pages one at a time, every find boxed (yellow to decide, green in the list, orange read with doubt); click a box or drag around finds to select them, and decide in the bar under them. Page done goes on to the next page.", "The drag box is gone when you let go. Drag around words the scan never found to add them as the reader sees them now; a find read with doubt can be fixed in place; DC inside DC-RVM offers Use DC-RVM.", "Not a term takes every place of the term off the page at once; Undo puts it back. The list: the effort's terms, In our drafts as the main button, and Show on the page on each card."],
    "3.92.2": ["Setup from a workbook: a left click selects text, a column's tag or a paragraph (Ctrl or Shift adds more); click a style in the Styles row to give it to what is selected. A right click opens the menu.", "Drag a paragraph on the Word page above or below another to move its kind of text, in every section or that section only. Drag a column's tag onto another to change the order."],
    "3.92.1": ["Verify: a heading on the same line as its text (L.4.2.1 Title. The Offeror shall...) is flagged; Split the heading off makes it a heading and leaves the rest as text for Review. It has no heading puts the suggestion away.", "Notes on a calendar event: Notes beside each meeting in the Effort Dashboard's day list opens its notes (made from the event the first time); Action, Decision and Topic lines become topics you keep and mark done."],
    "3.92.0": ["Acronyms on the page: the terms on the left (click a count to filter), the customer's page where the term was found in the middle, the card on the right. Keys: 1 to 4 pick a definition, Enter adds it to the list, X says Not a term.", "The card says when a find sits inside a longer term (DC in DC-RVM), shows the row it adds to the A to Z Acronyms table, and its sources. More: letters joined by a hyphen are one term.", "In our drafts: a volume's draft against the list (used before it is spelled out, spelled out again, not in the list, its Acronyms table); every fix goes into a copy as tracked changes."],
    "3.91.0": ["Setup from a workbook, on the page: your outline workbook on the left, the page Word gets on the right. Click a column's tag to say what it is and its place in the order; click any text to give it a character style.", "Guidance goes right after each heading; the source is written as typed, at the start of the text when it is short. Make the setup in Word writes it on your template with every style.", "Settings > Appearance: Follow Windows, Light or Dark."],
    "3.90.0": ["Review's tabs follow the work: Verify, Read, Compare, Review. The L/M Crosswalk and Coverage are views beside Review's page (L to M, Coverage).", "When Verify changes a file after it was read, Review says so with read it again; Verify's last page offers the next step.", "Covers, title pages and back covers live in Section designs. An outline workbook with Section L and M side by side, or a column saying L or M, comes in with L and M set."],
    "3.89.0": ["Compare shows the customer's new version on its own page, each change marked, beside our response; a line joins the selected change to the placed sentences it touches.", "A bar beside the change suggests what it means, with the reason (Update our wording, Add to a section, Remove, No action); Enter takes it and goes on. Editorial changes take No action together.", "A placed sentence an amendment changed says so in Review and Setup (Changed in Amendment 1) and keeps its place until the change is decided. Storyboards is off the menu for now."],
    "3.88.0": ["Acronyms: a term's card lists what it could mean in a stated order (the effort's list, the customer's documents, client lists, this PC), each with its source and why; two customer meanings say Needs a choice.", "One link adds every term the customer spells out once with nothing that disagrees, and names them. A table or figure number (L-3) is suggested as Not a term.", "First use check: a tab for each volume's own Acronyms table, terms listed but not used and used but not listed."],
    "3.87.1": ["Make the setup places the picked Section designs inside the volume itself, each in its own Word section: the cover and front matter before the response, the back cover after it.", "Setup: a section a design fills (cover, title page, Table of Contents, Acronyms, Units, back cover) has a Design row. Section designs shows Word's picture of each page, or a sketch; Draw with Word on the row.", "A format rule prints in a box in the setup; Review suggests a support sentence's home where the requirement it supports was placed."],
    "3.87.0": ["Production > Section designs: a library of covers, title pages and front matter sections you build in Word; Bring in from Word... puts a file on its shelf (a file with several Word sections comes in as one design each).", "Each design shows what fills it (set once per styled paragraph), the text headers and footers read, and a check that speaks only when a source is missing or in a text box.", "Setup > More > Section designs... picks a design per section (None leaves an optional one out); Make the setup writes each one filled beside the setup."],
    "3.86.0": ["Make the setup puts each section's references and notes for authors on its heading as Word comments (by Stationkeeper); Strip setup takes them out and keeps your own comments.", "Final Check names any left as Reference for authors.", "Setup lists what the selected section will print, in order: right-click a block for Earlier, Later, Move to another section..., Print the reference only, or Show it in Review."],
    "3.85.0": ["Review: a line joins the selected sentence to its home in your structure (dotted while suggested, solid once placed), and the structure scrolls to it.", "Each sentence's home is suggested with the reason; Enter accepts what it is and where it goes. After a placement, Review offers to send the rest of that customer heading too.", "Map a customer heading to the target from the sentence's right-click; More > Lines for headings and Export cross-reference table...; the line under Decide says what is left."],
    "3.84.0": ["Review > Verify: each customer page as the PDF page; every block gets a role (H1 to H6, Text, Bullet, Figure, Table, their captions, Footnote, Running, Not needed) before Review reads it.", "Flags first: a suggestion the rules were not sure of, a caption to confirm, a scanned line to check; Enter verifies the page and opens the next. The strip, Next to look at and the document menu move around.", "Menu roles... renames, hides, keys and adds roles; the reader follows Verify the next time a document is read."],
    "3.83.0": ["Review and Setup share one section panel: Management guidance saved as you type, References and notes for authors, and the notes, meeting topics and captures on the section.", "Copy a note into the guidance or send it to the authors; a quick note can go to any section, and notes waiting for one show under it to point there.", "Setup saves each section as you leave a box: no Save this section button."],
    "3.82.0": ["Effort Dashboard: Move to the next stage is the main button; Effort Record's stages are edited one at a time beside the list.", "An effort type hides and shows Review's captures as well as its decisions; Scan files... on Acronyms asks which Library folder each new file goes to.", "Draft Status > Drift report... checks every draft against its dated copies at once; the old For approval export is gone."],
    "3.81.0": ["The Library folder sits at the effort's top folder, beside Customer Documents, even when the list is deeper.", "An older effort's kept files: one line on the Effort Library moves them into the Library folders, with a list of every move.", "Settings > Our data and backups > Effort values beyond Effort Formatting... counts what efforts set outside its list."],
    "3.80.0": ["The acronym preview draws the scan's own readings at once (kept with the effort), and draws the next term's picture ahead.", "Drag a box on the picture: the readings inside it are highlighted; Read this area again; Add as a term... for a term the scan missed.", "Every fix keeps the picture's part with its training sample."],
    "3.79.0": ["Check a Draft > Apply in Word > Drift report...: how far a draft has moved from the copies made of it.", "Each change in a copy: taken up, still to take, or in a passage that changed; make the copy again once a fifth of the draft changed."],
    "3.78.0": ["The Effort Library: every file of the effort in real folders on disk (Bidders Library, Our Documents, Graphics, Q&A).", "New folder..., and moving a document moves its file; More > Move kept files into the Library folders... for older efforts.", "Acronyms: Scan files... offers to add the files to the library first; Scan the library... scans the folders you tick."],
    "3.77.0": ["Settings is in sections: pick one in the list on the left.", "Custom dictionaries and this PC's acronym database are in Team References only.", "Matrix, Compare and Customer Q&A: one bar each, with More and Export."],
    "3.76.0": ["Adding a term to the acronym list is the decision: In the list or Not a term (no approval); No definition yet shows on its own.", "The term card: Add to effort list, Not a term, The picture says something else... (part of a longer term, misread letters, not text) and More.", "Acronym List > Import a list... merges any Excel or CSV list; every fix saves a training sample with the effort."],
    "3.75.0": ["The menu in nine groups; pages that belong together are tabs of one item.", "The bar on every screen: Undo and Note (Issue or idea inside it); click the effort's card to switch efforts.", "Effort Dashboard, Review, Effort Formatting, Effort Record and After Submission: one bar each, the rest in More and Export, row actions on the row."],
    "3.74.0": ["Setup is one page: the Structure Builder's sections, who writes each and when, the template, and Make the setup, with one bar (More and Export hold the rest).", "Right-click a section for what the style buttons did; the tree shows each section's lead and due date.", "Settings > Our data > Button use on this PC... counts which buttons you press, on this PC only."],
    "3.73.0": ["Setup > Outline layouts... sets an outline's column names and formatting rules ahead of time.", "A new version of the outline is compared before anything changes; changes in both wait for your pick; Outline versions... compares any two and writes the workbook back out in its own layout.", "Compliance matrix: Bring the edited matrix back... and Merge another copy's matrix... bring the team's values in after you look.", "Setup: Bring in a file..., or drop one on the page (Excel, Word or PDF); the template can be picked before the sections.", "What's in your workbook: one list of each kind of text in each column (red text, black italic) with one pick for what it is; click a piece of a cell to change it. Red text starts as the requirement.", "Symbols: a clicked symbol goes in where your cursor is, in any box, also from inside a dialog."],
    "3.72.0": ["Setup > Use a template file... makes the setup on a Word template your team already made: blank in its look by default, with its cover, title page, front matter, Quick Parts and headers as you tick them; headings numbered by the template's own numbering; the file read back and checked before you get it.", "A setup made on the app's own template no longer shows heading numbers twice."],
    "3.71.0": ["Setup > From an outline workbook... reads the team's outline Excel into the setup: the sections, each requirement with its reference, customer and supporting text by their formatting, guidance and authors, with a preview in each setup style's look. Setup > Setup styles... sets each setup style's font, size, color, bold, italic and hidden, for this effort, every effort or the effort's template.", "Acronyms: while a scan runs, a bar shows the file it is on, how much is done and about how long is left.", "The Effort Dashboard's condensed header no longer shows Win themes and Wall of Truth while they are set aside.", "In a preview, a mouse's side wheel moves the picture left and right instead of zooming out; the picture drags at any zoom, a little past its edges; scrolling in the preview never scrolls the panel around it."],
    "3.70.0": ["Right-click an effort on All Efforts to archive it (it asks first) or add to it; Show archived lists archived efforts to restore. Nothing deletes an effort. Add to this effort... merges another copy of the same effort (someone else's, an earlier one, a folder or a package): documents, acronyms, volumes and drafts, and the record, with one summary of what to review."],
    "3.69.0": ["What lived only in Production Standards has new homes: Rules > Fix a Copy's checks (graphics, Excel and PowerPoint, the words Fix a Copy fixes), Formatting Standards > Allowed styles..., and Effort Profiles > Content map, fields and font rules.... Production Standards left the menu; Settings opens it for one more release."],
    "3.68.0": ["An effort whose folder moved is found again instead of opening empty, and Efforts > Open an effort from its folder... opens one from its folder, its Effort List or the marker file kept in its folder. A Customer form part in Template Studio is kept as it is: Fix a Copy and Apply in Word leave it alone, Final Check finds its pages and checks its marking. Save the part asks where it goes, with what a broader save would change. Production Standards > What retiring this would lose lists what still lives only there."],
    "3.67.0": ["Template Studio > Read back sets a template or volume made from the Studio against its parts and numbering and the field recipes, part by part, and Word draws the first page of each part. The template check adds a web-safe check. Production > Apply in Word (Beta) puts the team's banned phrases into a draft as tracked changes with a comment each: on a dated copy, or, once allowed for the session, live in the document open in Word, never saved or closed by Stationkeeper and every change logged. A fixed copy from Fix a Copy can reach the author as tracked changes too."],
    "3.66.0": ["Rules > Field recipes holds your field codes as data you change: the table of contents, captions, header titles and page numbers, with appendices on Heading 7 to 9, and an effort's own code when one effort differs. Read a template... lists a file's fields against them. Production > Template Studio shows a volume's template part by part with the RFP's rule beside each, and its parts and numbering (cover, front matter in i, response in 1, appendices in A-1, foldouts) that Final Check counts by."],
    "3.65.0": ["Sort suggests a topic for each unsorted requirement from the topic's words (Keywords... count most) and says why; Take the suggestions files them. Sort > Structure puts each topic beside the response outline: Map to it, Make subsections under it, Place their requirements, rate our fit per topic, and see what is still missing. For an RFI or sources sought, Make the response from the topics builds a Response volume with a section per topic."],
    "3.64.0": ["Shred > Sort: name the big areas of what is being bought and file every requirement under one. Unsorted is pinned on top; Start from... the RFP's headings, the evaluation factors or a starter list; select rows and press 1 to 9 or File; Also under adds a cross-reference; subtopics, rename (the old name kept), merge, Split a compound sentence, Overview (shall, should and may; L, M and SOW by area), and Read back from Excel for a matrix edited there. The same topics as Review's Sort mode; the path strip counts what is sorted."],
    "3.63.0": ["The Effort Dashboard has a path strip under the header: the request type (RFP, RFI, sources sought, RFQ or task order, draft RFP), how and when the proposal is sent, Notes to sort, and the steps (Read, Requirements, Structure, Setup, Check) with a count each; any step opens its page, and Steps... switches one on or off. Note in the top bar (Ctrl+Shift+N) catches a quick note on any page: send it now or keep it in Notes to sort. Meeting notes sit near the top; Evaluation Criteria is a page in the Effort space, with factors tied to the deliverables they judge; the deliverables list shows parts, people and compliance; All Efforts shows the request type and the factors."],
    "3.62.0": ["Each deliverable has its own page: double-click it on the board or in the list for its overview, type (a customer's own file too), owner, due date and guidelines; format and submission from its format group, with its own values where it differs; parts and people (a volume deliverable's Structure sections, and parts of its own); requirements; attachments from the customer or ours and references; a discussion board with dated notes, filter by person and pins; and its dates on the calendar. Arrange sets the team's order. Every name picker has Add a person...; People and roles is now People."],
    "3.61.0": ["Acronym Findings: the preview boxes exactly what the scan read, pages through every page or picture of the file, centers each find, and a click on a box shows what it read, to fix the reading or use as the meaning. The card is lighter: the meaning, the find as text, the definition box and the actions on top, details folded. Why is a term missing? gives the reasons for a term you expected. The Effort Dashboard sets aside stages, gate goals, win themes, All overviews and the Evaluation card; the calendar keeps the mouse wheel for the page, has Jump to today, lists one person's day and shows section due dates with their lead."],
    "3.60.0": ["Plan > Setup > Strip setup... (and Your Tools) makes a clean copy of a volume with the setup's reference text, styles and file properties taken out, bookmarks and section breaks kept. Compare > Any two files > Tracked changes (Word)... saves the changes as real tracked changes; two Word files are compared by Word itself, formatting kept."],
    "3.59.0": ["Shred > Accuracy measures the shred on your own set of public RFPs: label one by deciding it in Review, save the answer keys, and see recall, precision and the kind against the 95% target, release by release. Read into Review lists what it set aside (headers, footers, repeated lines), and an amendment added to the Library adds its acknowledgment row to the matrix."],
    "3.58.0": ["Check and Submit > Final Check: one ready-to-send report per volume on its Word file and its PDF, with Pass, Fail or Needs a person on every line: compliance, page limits (every page counts until you tick one out), format rules, structure and the TOC's page numbers, acronyms, leftovers, the proprietary legend and page marking, and the PDF as the portal takes it. Export records it in the effort record. Submission Check and Final Checks are its tabs."],
    "3.57.0": ["The menu focuses on production: My Work, Draft Status, Wall of Truth, Storyboards, Data calls, Color Reviews and Kickoff packets are set aside for now (Settings > Roles shows them again). Final Checks > Leftovers finds the setup's reference text, hidden and white text, comments, tracked changes and placeholders before a volume goes out. Files in OneDrive or SharePoint folders, open in Word or holding others' tracked changes say so when read; Stationkeeper never saves over a file it read."],
    "3.56.0": ["Plan > Setup: the starting draft each author writes in. Start from headings typed, a Word outline or an RFP, no Review needed; set each section's lead, contributors, due date, pages and PM direction; choose what fills the sections; make it on each volume's template, and give authors already writing just their changes."],
    "3.55.0": ["Shred > Requirements: every requirement in one file, labelled by kind, exported as a draft matrix or filed to an effort. Compare is one space: customer versions with decisions, or any two files with the redline."],
    "3.54.0": ["Technical Edit: copy review of a Word draft by rules (Chicago with one to nine spelled out, plain language, the customer's words, leftovers, banned phrases, spelling), accept or skip each finding, and make an edited copy with tracked changes and comments. The style sheet keeps each effort's own decisions."],
    "3.53.0": ["The menu is spaces named for the job. Home opens on Your Tools: drop any file and pick what to do with it, your pinned tools, recent files and efforts. Working on (top right) is an effort or Unfiled. Team References gathers the shared lists. Acronyms: Paste a picture and Found in pictures."],
    "3.52.0": ["Production > Effort Profiles builds each effort type's profiles by picking from the libraries, with the RFP's size limits checked as you pick; Production > Templates lists every template the profiles make (ready, needs review, blocked) and makes one or all. Production Standards moved under Advanced. The acronym list's approver column is Approver."],
    "3.51.0": ["The acronym toolset is back: Omit holds on every scan, the Exclusion List, Add to the database, Add a term, meaning from context, customer acronym lists, fixes for misread text, another way of writing, sorting, right-click and Details; the Acronym List's exports and imports; pick the place that is the first use (contents entries never count); Acronym Finder keeps several lists; Full Text in its own window."],
    "3.50.0": ["Where an acronym was found is shown again: the picture or page with every find boxed, or the passage highlighted. Acronym Finder opens in its own window (its button at the foot of the menu): scan any files, export the list, check first use. First Use Check checks any Word file on its own. Symbols are back beside every definition box: Greek, subscripts, superscripts, math, accents and units.", "Production > Quick Parts and Layout: every Quick Part by its category with the pages it fills, and covers, headers and footers, sections, table looks, captions and the TOC, each with its picture and every value. Draw with Word shows items as they will print."],
    "3.49.0": ["Production > Formatting Standards: the fundamentals as a library, each item named, tagged by effort type and fully editable. Import from a Word file keeps everything at once or nothing, and can be taken back. Your standards are brought in as library items."],
    "3.48.0": ["Quick Parts take the template's fonts unless you keep their own. Insert a field lists header and footer fields by name. Drag a library item onto a section. Effort Formatting's footer box sets Rule 7's team line."],
    "3.47.0": ["Pictures are prepared for reading by this program's own code instead of OpenCV. It reads the same words, and the program is about 86 MB smaller."],
    "3.46.1": ["The program comes with a complete, cited record of what it is built from: every package and bundled library, its license, who maintains it and from where. Nothing you use changes."],
    "3.46.0": ["My Work lists the data calls you owe and your sections' draft status (not started, over budget, requirements "
               "removed). The Effort Dashboard has a Drafts and data calls card. New efforts' Author drafts stage has the gate "
               "goal Every section drafted, from Draft Status."],
    "3.45.0": ["Production Standards goes by layer: Building blocks, Components, Document sections, Checks, Library. Document "
               "sections (Document parts before): each section's page setup and what it starts with (response elements, Quick "
               "Parts, placeholders), put in by Make templates and kept in the setup. Sections in order edits your own sections too."],
    "3.44.0": ["Import from a file is one browser of the file: by layer (building blocks, components, sections), each item "
               "New, Same as the library or Differs (saying what differs), with a picture; take items from every group at "
               "once. Each Word section of a file can be kept. The template library is a page of Production Standards with "
               "pictures, a search, layers and where each item is used."],
    "3.43.0": ["Writing > Draft Status reads a volume's draft back by the response structure's headings: each section's "
               "status (Not started, Under way, Near budget, Over budget), its words and pages against its page budget, the "
               "requirements whose text was removed or moved, and the styles pasted text brought in. Nothing is changed."],
    "3.42.0": ["Headers and footers built here as tables: columns at inch widths, lines of words and fields (each with its "
               "alignment, size and bold) and logos. Rule 7's footer (the A number, the marking and the team's line, the page "
               "number) is the default, and templates now check Rule 7. Save a built header or footer as a Quick Part."],
    "3.41.0": ["Captures from meetings (select words in the notes), capture files (Word, PDF or text: tick the paragraphs) and "
               "the customer's answers, each with its source type: Customer document, Meeting, Capture intel or Customer Q&A answer."],
    "3.40.0": ["Covers, title pages and back covers: Word draws the preview on a PC with Word; each page keeps its kind (flow, "
               "table or placed) and is never converted; Edit in Word keeps what you save as a new version; the layout "
               "editor lists Text on the page with Add text and Add a field."],
    "3.39.0": ["Data calls (beside Customer Q&A): ask experts for what a section needs, with how much and an example; one Word "
               "file per person; answers read back and placed in the section for its author.",
               "Color Reviews: every reviewer comment, from the packet or Word comments in the drafts, gets Accept, Reject with a "
               "reason, or Done, with an owner and a due date; the recovery gates hold until every comment has one."],
    "3.38.1": ["Guardrails for the program itself: every release is checked to open what earlier versions saved, to use only "
               "approved packages, to stay offline, and to read the test documents as well as before."],
    "3.38.0": ["Production > Rules: every production rule in one list (Rule 1 to 13 and your own), how each is kept, on or off "
               "for every effort, and where its values live. Audit and Fix a Copy report each finding under its rule.",
               "Rule 6: Fix a Copy puts every heading level's number at 0 and its text at one position; templates follow it. "
               "Styles get a Used on column; an effort's response type renames styles (Rule 4)."],
    "3.37.0": ["Kickoff packets: one Word file per author with everything for the sections they lead or write: the customer's "
               "words with their source, how each is scored, objectives, hot buttons, themes, topics, answers, pages and dates.",
               "Structure Builder shows Everything for this section. Lists to Submit is now part of the Acronym List."],
    "3.36.0": ["Effort > Effort Formatting: this effort's fonts, sizes, margins, headings and header and footer on top of the "
               "Company Standards (Default), for every volume or one, with the RFP's rules beside each value.",
               "Make it global sends an effort's value to the Company Standards (Default) (with Undo). Production Standards now edits "
               "the Company Standards (Default) only; Every setting opens it on the effort."],
    "3.35.0": ["Matrix starts as the outline matrix: one row per outline item with Assigned To, Initial Page Allocation, "
               "% Complete, and Section L beside Section M. Review's bottom bar sets an item's values.",
               "Matrix views: save the columns and rows as a named, versioned view; each effort picks one; an effort type "
               "can start with one.",
               "Styles: Based on and Next style from a list. Previews fit their space, hold still, widen with a drag and open "
               "larger with a click."],
    "3.34.1": ["A new effort opens with no error and shows in the effort box and All Efforts at once. Switching efforts no "
               "longer errors, and every page shows only the open effort's work.",
               "Review: the deciding and capturing tools sit along the bottom, so the right side has room for the selected "
               "text and the response structure.",
               "Acronyms: the place found shows again; Found in tells Customer from Ours; Use FY (a form of it) ties FY27 to FY "
               "so it stops coming up; plurals and forms leave the list once decided; a short status filter."],
    "3.34.0": ["Covers, title pages and back covers built here: New from a blank page, a background picture (full bleed or "
               "inside the margins) and text blocks that show the volume's fields in their own size, color and font. The "
               "page is drawn as it will look.",
               "Save as a cover layout keeps a page's structure apart from its look; From a saved cover layout builds a new "
               "page from it. The title page is a page of its own after the cover, with its own shelf in the library."],
    "3.33.0": ["Production Standards > Template profile: each part of a profile (cover, headers and footers, fonts, numbering, "
               "pagination, table looks) from a version in the template library, pinned; a newer version waits until you choose "
               "Use it. Save as a new version keeps what a part holds now.",
               "The Content map: the style each kind of placed item takes, hidden or shown, in the file or not; captures go in "
               "hidden by default. The template library keeps versions of everything, labelled, with Compare."],
    "3.32.1": ["Bullets show as bullets in Production Standards (not empty squares), and templates write them the way Word "
               "does, so they show on every PC.",
               "Import from a file no longer breaks the table rules when it takes Table looks: the file's look goes over the "
               "standard's, and a standard an earlier import broke is repaired when it opens."],
    "3.32.0": ["Structure Builder > Preview > Exact preview in Word: Word lays out a dated copy of the volume's template and "
               "setup and shows its own pages with the true page count. Click a page to select its section.",
               "Quick Parts measure their pages (Word on this PC) or take pages you type; the page plan, the page budget and "
               "a prepaginated setup use them. Final Checks > Response elements: what the RFP names that a volume lacks, "
               "and the RFP's order."],
    "3.31.0": ["The Structure Builder's Preview tab: the volume's pages as they will run, each part numbered its way, with "
               "headers, footers and the marking, element pages with their entries, landscape pages turned. Click a page to "
               "select its section.",
               "Elements take their pages into the page budget and keep them when a limit is spread. Settings > Units of "
               "measurement and a Unit capture fill the Units of Measurement table."],
    "3.30.1": ["Make templates builds what you set in the Structure Builder: the TOC, List of Figures, Tables and Appendices "
               "as fields, Acronyms and Abbreviations filled from the effort's approved acronyms, the compliance matrix, "
               "divider and placeholder pages, unnumbered headings, landscape Word sections and placed Quick Parts.",
               "Appendices go on their own heading styles (Appendix Heading 1 to 9), so the response keeps all nine levels."],
    "3.30.0": ["The Structure Builder: its own place under Compliance. Volume tabs; the structure with a tag on each section (H1 "
               "to H9 and deeper, unnumbered, divider, placeholder, element, Word section); a toolbar like Word's style buttons; "
               "Enter, Tab and Shift+Tab; drag a section to move it; library items placed in a section; everything in each "
               "section in order (Response Setup lives here now); what is not placed yet.",
               "Settings > Response elements: Table of Contents, the lists of figures, tables and appendices, Acronyms and "
               "Abbreviations, Units of Measurement, the Appendices section and your own, with kits by effort type; Add "
               "elements puts them into a volume in one tick list.",
               "Fixed: a capture made after another one opened the problem window. The problem window has Save a report..."],
    "3.29.1": ["Review: every capture can sit in a section of the structure: Into the target section, and one click to move it "
               "(the card, a right-click, the Captured list). Captures follow their section when it is renamed or renumbered.",
               "The menus across the top stand out: a blue band, the page you are on solid blue."],
    "3.29.0": ["Settings > Review: decisions and captures: name, key, color and showing of every decision and capture, the "
               "bar or More..., the order, what each effort type hides (an RFI shows Interest), and the team's own captures.",
               "Review: one capture bar (bins are captures now), More... for the rest, and the Captured list as its own button."],
    "3.28.1": ["Review: drag over words across sentences to pick them; Extract (Shift+S) makes them one sentence, split from "
               "where they were. Rename a volume and number the volumes I, II, III; 1, 2, 3; or A, B, C.",
               "Settings > Stages, gates and roles: Put back the built-in ones is gone."],
    "3.28.0": ["Review: topics and Sort mode (keys 1 to 9), topics from the RFP's headings, a topic mapped to a section takes "
               "its requirements there; RFI efforts open in Sort mode with Customer interest (I) and RFI suggestions.",
               "Everything Review takes flows out: matrix columns (Topic, Customer objective, Key points, Source excerpt), the "
               "setup per section, the Wall of Truth, Final Checks' written rules and the dashboard."],
    "3.27.0": ["Document parts > Cover and Back cover > Edit the layout: move and resize the pictures, text boxes and tables "
               "of a kept page in inches, and set which field each line of text shows; saved as a new copy.",
               "Make templates: each volume can continue the page and chapter numbers of the volume before, suggested "
               "from its draft."],
    "3.26.0": ["Production Standards > Document parts: Cover, Front matter, Response, Appendices and Back cover, each with "
               "what applies to it (numbering, header and footer, its page, TOC or captions, what it shares) over the same "
               "values as the other menus, a drawn preview, and Save this part as a design to use on any part."],
    "3.25.0": ["Production Standards: a menu across the top in the order a document is built (Pages, Styles, Numbering, "
               "Tables, Content, Check), plain names, and the checks inside the sections they check.",
               "Editing is two boxes, Effort type and Volume (a profile is now a volume), and This effort only.",
               "One Import from a file: take one item, some or all, into what you are editing and the library; each section "
               "has its own Import for its items. Allowed styles are ticked from a list, sorted by type, group or use case.",
               "Headers and footers as a one-row table at inch widths, or from one of your Quick Parts kept as built.",
               "Fill-ins are Fields. Make templates shows each template in full before any file is written."],
    "3.24.0": ["Response Setup > Make templates and setup: for each planned volume, its template from Production Standards "
               "(named for the effort and the volume, the next version, the volume on its cover) and the setup written on "
               "it: the template's styles, cover, pagination and TOC stay, its sample pages go, and the RFP's words, support, "
               "the customer's sentences, library context, your direction and notes each go in their own style, hidden text "
               "unless you say otherwise. Ready to make lists what is still open first.",
               "Header and footer designs kept whole: collect them from any template or document and put one on a part; its "
               "tables, tab stops, pictures and fields come in exactly as built.",
               "Quick Parts with list numbering now come in, their list definitions renumbered.",
               "Production Standards: heading and list numbering show the number as it will look (1.1.1, Section A), typed "
               "the same way; Learn from a file is Import from a file; the .dotx button is Make a .dotx template; no default "
               "profile or effort type (you pick each time you start an effort); Export for review is gone."],
    "3.23.0": ["Fill-ins (Production Standards): type a value once and it shows everywhere: a cover style that headers, "
               "footers and Quick Parts read through STYLEREF (as the team works today), or a document property (DOCPROPERTY). "
               "Fields carry no MERGEFORMAT, so each takes the formatting where it sits.",
               "Caption schemes: each caption rule numbers by sequence only or chapter then sequence, and shows its number "
               "as 1, I, i, A or a.",
               "Every template gets a validation report beside it (styles used but not defined, broken STYLEREF and "
               "DOCPROPERTY fields, MERGEFORMAT, list numbers with no definition, direct formatting inside Quick Parts, "
               "fonts not installed, hidden text styles) and, when Word is on the PC, Word's own check: each Quick Part put "
               "in, its fields and styles confirmed.",
               "Templates have a name and a version (counting up), carried in the file; the effort records the one it used.",
               "Template library: kits (a named set of items to start a standard from) and previews (a style in its font, "
               "size and color; a font; a theme's colors)."],
    "3.22.0": ["Our data (Settings): one Stationkeeper Data file (.skdata) carries the team's foundational data: the master "
               "acronym list, custom dictionaries, banned phrases, Production Standards with covers and Quick Parts, the "
               "template library and the team lists. Import shows what each part adds, merges add-only, and Undo puts it "
               "back. Nothing about one effort goes in it, and it never goes on GitHub.",
               "Template library (Production Standards > Collect into the library): read any template, Word document or "
               ".thmx theme, confirm what it carries card by card (styles, hidden text styles, pages, headers and footers, "
               "numbering, tables, covers, Quick Parts, fonts, theme colors), open a sample in Word, and keep it on shelves. "
               "New style, Edit, Rename, Use cases, and Use in this standard.",
               "Production Standards > Quick Parts: the Quick Parts every template carries, all in Word's Quick Parts gallery "
               "in your numbered categories. Their styles follow the template's, and landscape and tabloid pages keep their "
               "section and headers.",
               "Styles can be hidden text (Show/Hide), with their color. Table types set their width in percent or in "
               "inches, with column widths in inches; learning a file keeps inches as inches."],
    "3.21.0": ["Excerpts and bins: every capture keeps the customer's exact words and where they sit (document, page, "
               "paragraph, numbering, heading). In Review, Objective (O) and Key point (K) put the picked words in a bin; "
               "Bins (B) holds Other submission detail, Written formatting rule, your own bins (Alt+1 to Alt+9) and Every "
               "excerpt. Sentences that are not next to each other make one excerpt.",
               "A sentence keeps one decision and can sit in any number of bins. Its card lists them to edit or take out.",
               "Submission Rules show the customer's words under each rule, and list Other submission detail and written "
               "formatting rules (a phrase check when they quote the words, else a Final Checks item).",
               "Make a bin for the effort (a color, where it feeds) and Share with team: it travels in the team pack."],
    "3.20.3": ["Review fits the window: the document scrolls, the right panel scrolls on its own with the decisions on top, "
               "and the wheel glides. Drag across words and press Extract (Shift+S) to make them a sentence of their own; "
               "Split with no word clicked asks exactly where.",
               "A sentence's card lists what was captured from it, with its value to fix in place (a mistyped e-mail).",
               "Effort Dashboard: every card fits half width (its buttons wrap), a tile's number shrinks rather than cut "
               "off its words, and a Questions due tile shows the days left and the questions not yet submitted.",
               "Meetings: room between the list and the meeting, a larger notes box, and Make a topic of the selection.",
               "Library: right-click a document for everything you can do with it; Read it in Review never stops at the role.",
               "Opportunity Number (Client Issued) and Internal A Number; Condense is an arrow and glides."],
    "3.20.2": ["Every download names its version: Stationkeeper_US_3.20.2.zip opens to a Stationkeeper_US_3.20.2 folder (the "
               "Training and SCIF downloads and the SBOM files too), so there is no doubt which version you have. Unzip a "
               "new one beside the old: your data in Stationkeeper Data is picked up as before."],
    "3.20.1": ["Appendices and the page limit: the first appendix asks whether the RFP counts the appendices; Part rules and "
               "page limits changes it for all of them, and a section's Pages... sets one on its own (counts, does not "
               "count, or as its part). The Page budget follows.",
               "A section's page length now follows it when its number or name changes."],
    "3.20.0": ["Meetings (Effort Record > Meetings): the meeting, its date and time, participants and notes, and the topics "
               "to follow up. A topic points at a section or a requirement and can name an owner; it stays open until "
               "someone marks it Considered or Not needed, with who and when.",
               "Topics from notes offers the notes' bullet lines (and Topic:, Action:, Decision: lines) to keep as topics. "
               "Open topics show on the Effort Dashboard, in My Work for their owner, and on the Review card of what they "
               "point at; the gate goal Every meeting topic considered can hold a stage. Export to Word saves a meeting."],
    "3.19.0": ["The response structure has parts: cover, title page, front matter, the response, appendices and back cover, "
               "in order in each volume. Review's Parts button adds them (front matter from a list: cover letter, table of "
               "contents, lists of figures and tables, acronyms, compliance matrix, executive summary, or your own) and "
               "moves a section to another part.",
               "Cover, title page and front matter carry no section numbers; appendices are lettered (Appendix A, A.1). "
               "Each part shows the rules it follows from Production Standards: page numbering, header, footer marking "
               "and the heading style that starts it. Response Setup prints them where each part starts.",
               "Part rules and page limits... says which parts count toward the page limit (the response by default); "
               "the Page budget counts and splits only those.",
               "Add missed text: text whose words are not in the PDF's own text (a scanned page read by OCR, wording you "
               "fixed, a header or footer band) now gets a box from the area you dragged, and it selects. The area is "
               "kept in the matrix."],
    "3.18.2": ["Undo everywhere: an Undo button in the top bar and Ctrl+Z undo the last change on the page you are on, and "
               "say what they put back. In Review that includes the structure: a section added, renamed, moved or taken out "
               "comes back as it was. Structure, Coverage, Matrix and Response Setup share the matrix's steps; library "
               "documents undo their own.",
               "Pages for each section: set a section's page length in the structure list (Pages column, or Pages...) and "
               "say who set it, the RFP's limit or the team's guideline. Response Setup prints it under the section.",
               "Every decided sentence can go in the response structure: the customer's too (printed for the writers, not "
               "answered). Put all in section keeps each sentence's decision. The decide panel scrolls on its own.",
               "Effort types: RFI response is one of the starters. Effort types... (Start an effort, Production Standards) "
               "adds, renames, orders and takes out effort types and chooses the default."],
    "3.18.1": ["Review: every choice has its own color on the page. L green, M orange, SOW teal, support blue, the "
               "customer's purple, ignored grey; only sentences nobody has decided stay plain. A legend sits above the "
               "decide buttons, and the buttons carry the same colors.",
               "Ignore (X) is now a decision of its own: grey with IGNORED in the margin, counted as decided, skipped by "
               "Select undecided, and Not used in the matrix. Delete takes a decision off.",
               "A sentence something was captured from (a contact, a rule, an acronym, a question, a key date, a graphic "
               "need, the More captures) or had a task or team question made on it gets a pink outline, and the margin says "
               "what. Library documents too: made a requirement, support, a question, a note or a task, and ignored."],
    "3.18.0": ["Review: Suggest shows what each sentence most likely is, from rules you can read (who acts, the verb, the RFP "
               "section), not AI. Suggestions show dashed on the page with their reason; nothing is decided until you accept "
               "one (Enter), the clear ones, or all shown.",
               "Accepted suggestions stay marked until someone checks them (Select unchecked). The score counts kept, "
               "changed, not right and missed.",
               "Teach it: Make a rule... on a sentence's card turns a correction into a rule for the team or this effort; "
               "Settings > Suggestion rules lists them, and a team pack shares the team's."],
    "3.17.0": ["Production Standards shows what you set: a preview beside every section draws what its values make, and "
               "every value set at the layer you edit says what it was. A list above the preview names every change in "
               "the section.",
               "Graphics standards: picture types, resolution where placed, the widest a figure may be, fonts and the "
               "smallest text in drawings, charts and text boxes, captions, alt text, RGB only and file size. Fix a Copy "
               "and Audit check every figure; a picture is never changed.",
               "Production > Audit: check Word, Excel and PowerPoint files against every standard that applies to them, "
               "read only, and export every finding."],
    "3.16.0": ["One place per job. The Library is where reading starts: a Review column says where each document stands (Not "
               "read yet, Needs reviewing, Reviewed) in color, the first button moves it on, and new files in the watched "
               "folders show at the top with Add and Ignore.",
               "A menu item with several pages shows them as tabs under its title: Review (Review, Structure, Coverage), "
               "Matrix (Matrix, L/M Crosswalk), Library (Documents, Read into Review), Effort Dashboard (Dashboard, "
               "Submission Rules) and Acronyms (Scan, Acronym List, Lists to Submit).",
               "Reading never stops for the structure: build it beside the page in Review, or Start from... Volumes, people "
               "and the page budget are on the Effort Dashboard.",
               "Changes is Compare; Prove is Coverage. The matrix can show Evaluated by (Section M) from the crosswalk.",
               "Fix a Copy is last in Production, marked Beta. Post-Submission is its own group: Checklist and Keywords."],
    "3.15.1": ["Watched folders: a file that leaves a watched folder outside the effort is reported missing; each document "
               "remembers where its file came from; a file saved again with the same words (SharePoint and OneDrive do this) "
               "is recognized and never added twice. After adding, the Library shows every new document, selected.",
               "Read it in Review always works: with no compliance matrix yet, it offers to read the documents that build it, "
               "then opens yours. A document whose role is Not needed says how to read it.",
               "Review: pan the page with the Pan tool (H), by holding Space and dragging, or with a middle-button drag.",
               "Authors: add names right from Review when the effort has none; choose one or more authors for many sentences "
               "at once; the field says why when a sentence needs a decision first."],
    "3.15.0": ["The menu is easier to scan: each tool is in one place (the separate stage group is gone), group names are in "
               "capitals with a line above, and the page you are on is marked by a bar at its left. A dot in the stage's color "
               "marks the tools the effort's stage needs, and each group shows how many it holds.",
               "The open effort and its stage sit at the top of the menu; click it for the Effort Dashboard.",
               "Customer documents is now Solicitation: the RFP, its changes, the submission rules and our questions to the "
               "customer, together.",
               "Every page names its group above its title. Cards have a header row, and the main card on a page is tinted. "
               "Status (Saved, No matrix, the mode) shows as small pills, not button shapes, and each card has at most one "
               "filled button."],
    "3.14.3": ["Closing Stationkeeper ends its background work cleanly. A PDF page copy that Word, Excel or PowerPoint is "
               "making stops at once, the Office it started is closed, and no half-made copy is kept (it is made again "
               "next time). Any other job still running is asked to stop and finished first, so nothing is cut off "
               "mid-file and Stationkeeper no longer ends with an error when closed during that work."],
    "3.14.2": ["No demo content: the button that made a practice effort is gone, the Guide is text only, and every example "
               "in an empty box is generic (Effort name, Customer, Solicitation number). A practice effort you already "
               "made stays until you archive it."],
    "3.14.1": ["A leaner program: parts it never used are gone (the OpenSSL library, Qt's software OpenGL, Qt's translations, "
               "SVG and spare Qt plugins, AVIF pictures, a second copy of Tesseract's libraries, and old help pictures). "
               "Nothing you use changes, and every build now refuses to finish if any of them come back."],
    "3.14.0": ["The classic window is retired: Stationkeeper is the Qt window only. Nothing you use changes; the program is "
               "smaller, starts with fewer parts, and no longer ships the old tkinter and customtkinter libraries.",
               "The rules the classic window held (acronym lists, QA/QC, the Trainer's package) now live in their own engine "
               "files, checked by the regular tests."],
    "3.13.0": ["Roles: each person's role decides which tools open. Tools for another role stay in the menu, greyed, and say "
               "who they are for; Settings can hide them. The proposal manager sets roles in People and roles; with none set, "
               "your own choice in Customize... counts.",
               "Preview tools: Fix a Copy and Make a .dotx template are off for the team until the proposal manager turns them on "
               "(Settings > Roles and Preview tools, carried by a team pack).",
               "The menu is grouped by job, groups fold away, and For this stage lists the tools the effort's stage needs."],
    "3.12.0": ["Effort Home and Dashboard are one page, the Effort Dashboard: the numbers on top, then your cards. The header "
               "stays put while you scroll, shows the stage with its gate and open goals, and condenses to one line. Each stage "
               "has a color that tints the header and the stage track.",
               "Move stage says what is not done before it moves. Open goals carry into the next stage, marked, and count at its "
               "gate; only the proposal manager overrides a hard gate. All Efforts shows each effort's gate.",
               "Win themes and Wall of Truth show under the header on any stage, and hide. Submission requirements is one card "
               "(how and when, formatting, page limits) with Edit on each. Every overview is kept in All overviews."],
    "3.11.0": ["Fix a Copy checks Excel workbooks and PowerPoint decks against the profile: fonts and sizes, the header row, "
               "frozen panes, print setup, number formats, hidden sheets and formula errors; slide size, fonts, small text, "
               "things off the slide, the marking, empty placeholders and missing titles. These files are read only: "
               "you fix what Check finds in Excel or PowerPoint.",
               "Production Standards > Excel and PowerPoint holds the values each profile checks."],
    "3.10.0": ["Profiles carry Word table styles whole (borders, shading, the header row, banding) and each table type can "
               "use one: Fix a Copy checks and sets them, Import from a file reads them, Make a .dotx template writes them.",
               "Profiles keep their cover and back cover pages, learned from a template or a finished volume (pictures "
               "included). Make a .dotx template puts them in; Check reports a draft whose cover or back cover is built "
               "differently, and never changes it."],
    "3.9.0": ["Issues and ideas: write down a bug, an improvement or an idea from any page (Issue or idea in the top bar, "
              "or Ctrl+Shift+I). Reports stay on this PC and a guard keeps document words out; Export... saves a text-only zip.",
              "Fix a Copy: Check every draft reads each draft against its own profile (Format Check is now part of Fix a Copy), "
              "Export findings... makes a workbook, Make it a rule turns a table answer into a rule, and list numbering "
              "(bullets and numbers by level) is checked and set from the profile."],
    "3.8.0": ["Production Standards: effort types (RFP response, page-limited RFP response, white paper, program "
              "deliverables to start) hold the document profiles their deliverables use, rules every profile in them follows, "
              "and changes for one profile. Start an effort asks for its effort type; a draft takes the profile whose words "
              "are in its name. Make templates for every profile of an effort type in one step.",
              "Styles also carry tab stops, paragraph borders and shading: checked, set, learned and edited like the rest."],
    "3.7.0": ["Production Standards: each document profile is a full template. Learn from a file... reads your master "
              "template or a finished volume and takes its styles (each one whole), table looks, page setups, headers and "
              "footers, heading numbering and TOC into the profile. The Style library section shows and edits every "
              "style property.",
              "Make a template... writes a Word template with every value of the profile to the output folder; it "
              "passes its own check. Fix a Copy checks and sets every style property of the library, uses each deliverable's "
              "own profile, and compares Word's page count with the deliverable's page limit."],
    "3.6.1": ["Fix a Copy: headers take this effort's solicitation and the volume's name (from the Deliverables board, or typed "
              "on the page); with either one blank, headers and footers are left as they are. The Company Standards (Default) hold no "
              "sample names, products or numbers.",
              "Fix a Copy: terms come from the team's Banned Phrases, the custom dictionaries, the author list and the "
              "effort's approved acronyms. Copies go in the effort's own folder in the output folder, and the effort's "
              "record notes each one. Fill from the RFP also reads line spacing."],
    "3.6.0": ["Production > Fix a Copy: fixes a Word draft to the production standard in a dated copy in the output folder; "
              "the original is never changed, and a file someone has open is not copied. Tables by row role, captions and "
              "numbering, TOC, pages, headers and footers, lists, fonts and styles, then Word updates the fields.",
              "Production > Production Standards: every rule, value by value, for the team, each document type and this effort."],
    "3.5.0": ["Production > Format Check: Word drafts read against the production standard (fonts by kind of text, margins and "
              "page size, captions, the table of contents, typed lists, page numbers), each finding with where it is and why. "
              "The files are only read, never changed.",
              "Production > Production Standards: the team's document types, and each effort's own rules filled from the RFP."],
    "3.4.0": ["Deliver > Final Checks: the final PDF package (page limits, page size, embedded fonts, searchable text, file size "
              "and names, every volume and form there), cross-references and numbering in the drafts, and Compare two drafts "
              "with a Word redline."],
    "3.3.0": ["Deliver > Wall of Truth: one approved value for every fact and number, names and terms; Check the drafts finds "
              "every number that disagrees, every old value still in use and every wrong form, by volume and section.",
              "The team's wall carries company facts to every effort; Export the wall makes the page to post."],
    "3.2.0": ["Win themes on Effort Home: themes and discriminators with proof and sections; Check the drafts says where each "
              "is said and where it is missing.",
              "Deliver > Storyboards: one sheet per section before the first draft, exported to Word for the review."],
    "3.1.0": ["Schedule from due date... on Effort Home dates every stage backward from the due date, skipping weekends and "
              "holidays; you see every date before it is set.",
              "Opening an effort says what your teammates did since your last visit, on Effort Home too.",
              "Page budget... (Review and Structure) splits each volume's page limit across its sections; the Response Setup "
              "documents print each section's budget.",
              "Home > My Work: one person's work in every effort, soonest first, late items on top."],
    "3.0.4": ["Review: select several sentences (or Select undecided, or Ctrl+A) and one bar decides them all, puts them all in "
              "a section or gives them all one author.",
              "Graphic needs: press P in Review (or Graphic on a note) to tag what needs a graphic; Effort Home lists them for the "
              "graphics team, with an Excel export.",
              "Settings > Custom dictionaries: your team's words for Word, imported from a .dic, from the effort's acronyms or typed, "
              "and exported as a .dic for Word.",
              "Effort Home fits a 1440-pixel screen with no sideways scroll."],
    "3.0.3": ["Start an effort in one short form: a name is all it needs. Effort Home shows it whenever no effort is open, "
              "and + Add an Effort opens it too. Add the picture (click or drop one), client, solicitation, due date and proposal "
              "manager now or later; the folders are made for you.",
              "Drop a picture on the effort image on Effort Home to set or change it.",
              "The company logos are built into Stationkeeper: no more Add your company logo."],
    "3.0.2": ["The Guide: how to use every page, in the order of the menu, with a picture of each page. F1 opens it at the "
              "page you are on; Go to this page jumps there; search finds a topic. Settings > Help and support opens it too."],
    "3.0.1": ["Assign is now Review: the page where you read every sentence, decide it and capture what it holds. Reviews "
              "(color team packets) is now Color Reviews.",
              "Customer Q&A in Word: one Reference column (the document, then section, page and paragraph), the customer's "
              "words, your question and a Government Response column. Nothing internal goes out.",
              "SCIF-ready: the administrator self test keeps only a content-free result and never creates a logs folder."],
    "3.0.0": ["Amendments that say what to change (delete and insert, replace or delete a paragraph, add one) are applied to "
              "the document they change: Library > Apply its instructions makes its Conformed version and says what did not apply.",
              "Task orders and delivery orders are document types of their own, filed under the base contract or RFP in Library."],
}

from whatsnew2 import OLDER  # noqa: E402  the 2.x versions live in their own file (4.59.1, size limit)
WHATS_NEW.update(OLDER)
