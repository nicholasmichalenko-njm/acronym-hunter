"""In-app guide: the "?" button (and F1). Short, direct pages with small screenshots of the real tools.

Pictures live in assets\\help\\ (bundled into _internal\\assets\\help by the build). Each page is a list of blocks:
    ("h", "Heading")          section heading
    ("p", "text")             one short paragraph
    ("img", "file.png", w)    screenshot, shown w logical pixels wide (files are stored at 2x for sharp text)
    ("rows", [(label, text)]) label/text pairs: What / When / Why
    ("table", [row, ...])     first row is the header
"""
import os, sys
import diag
import tkinter as tk
import customtkinter as ctk

_win = [None]
_imgs = {}

def _asset(name):
    for base in (getattr(sys, "_MEIPASS", ""), os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))):
        p = os.path.join(base, "assets", "help", name)
        if os.path.isfile(p):
            return p
    return None

def _img(name, w):
    key = (name, w)
    if key not in _imgs:
        p = _asset(name)
        if not p:
            return None
        from PIL import Image
        im = Image.open(p)
        _imgs[key] = ctk.CTkImage(light_image=im, dark_image=im, size=(w, max(1, round(im.height * w / im.width))))
    return _imgs[key]

PAGES = {
"Start here": [
    ("h", "What Acronym Hunter does"),
    ("p", "It reads your files and lists every acronym, abbreviation, unit, designator, symbol and equation, with its "
          "definition and where it appears. It reads typed text and the text inside pictures, scans and diagrams. "
          "Everything runs on this PC. Nothing is sent anywhere."),
    ("h", "Four steps"),
    ("img", "sidebar.png", 220),
    ("rows", [("1. Scan", "Select Files or Scan Folder. Word, PowerPoint, Excel, PDF, pictures and drawings. "
                         "Scan Again repeats the last scan after you change a definition or a choice."),
              ("2. Review", "The results table lists every term found, with its status and where it appears."),
              ("3. Resolve", "Click a row. Pick a definition, add it to the database, or exclude it."),
              ("4. Export", "Export CSV gives you the acronym list for the proposal.")]),
    ("p", "Everyday actions sit in the sidebar on the left; every command is also in the menu bar. Drag the sidebar's edge to "
          "resize it, or hide it with View > Sidebar (Ctrl+B). Effort keeps one list per proposal and checks finished volumes. "
          "Compliance builds the compliance matrix from the RFP."),
    ("h", "Where to get help on each tool"),
    ("p", "Use the tabs above. Each page says what a tool does, when to use it, and why it is worth it."),
],
"Results": [
    ("h", "The results table"),
    ("img", "results.png", 640),
    ("rows", [("Term / Type", "What was found and what kind it is: acronym, abbreviation, unit, symbol, equation."),
              ("Status", "In DB = known. NEW CANDIDATE = not in your database yet. CHOOSE DEFINITION = several meanings."),
              ("First Use", "Whether the document defines the acronym the first time it uses it."),
              ("Locations", "Every file, page, sheet or picture where it appears. Click a row to see it.")]),
    ("h", "Filters"),
    ("img", "filters.png", 560),
    ("p", "Show one type or status, or search. Show Excluded brings back terms you excluded."),
    ("h", "The action bar (bottom)"),
    ("img", "actionbar.png", 560),
    ("rows", [("Apply Choice", "Pick one meaning when a term has several."),
              ("Include in DB", "Type the definition and save it. Every future scan knows it."),
              ("Fix OCR", "The term is a misreading. Type the correct term. See the Fix OCR vs Training tab."),
              ("Exclude", "Not a real term (a heading word, a part number). Hidden from now on, everywhere."),
              ("Context", "When a term has several meanings, the words around it suggest one: words it shares with a "
                          "meaning, a role (\"the PM shall\" is a person), a document word (\"PM plan\"), or the long form "
                          "spelled out in the same files. The Definition column says \"Context: ...\" and why, Apply Choice "
                          "starts on it, and the Source preview says what it likely means at each place. When places "
                          "disagree, the row says \"meaning differs by place\". Nothing is applied until you choose: "
                          "right-click > Accept context suggestion, or Edit > Accept context suggestions. Rules only, "
                          "typed text only."),
              ("Heading words", "Ordinary words in all-capital headings (EVALUATION FACTORS FOR AWARD) are set aside, not "
                                "listed as acronyms. Show Excluded lists them; a word also used in running text stays."),
              ("Omit list", "Company names, locations and other terms you want found and recognized but never on the final "
                            "list. Right-click > Add to omit list (say what it stands for and why), or Edit > Omit list to add, "
                            "paste many (TERM, stands for, why) and remove. Rows say \"Found in omit list: <why>\"; they are "
                            "never flagged for first use and stay off the CSV export and the volume acronym lists. Saved in "
                            "the company database, so every scan and every effort recognizes them."),
              ("Several meanings", "One acronym may have several entries when the meanings differ: Add Item gives a listed "
                                   "term another meaning, and the database and omit list take a new row. The same meaning "
                                   "twice is flagged and not added."),
              ("Exclude instance", "In the Source preview: drop only the place shown (a misreading, a stray heading word). The "
                                   "term stays wherever else it appears, stays excluded there on later scans in this effort, "
                                   "and Restore instances (or right-click > Restore excluded instances) brings it back.")]),
    ("p", "Fix OCR appears when the Advanced switch (top right) is on."),
],
"Fix OCR vs Training": [
    ("h", "Two ways to fix a misreading"),
    ("p", "A misreading is the scanner reading RFP as RRP, or SE&I as SE8I, inside a picture or scan. "
          "You have two tools. Use both."),
    ("table", [["", "Fix OCR", "Training"],
               ["What it is", "An auto-correct rule", "Lessons that make the reader better"],
               ["What changes", "The label after reading", "How the scanner reads"],
               ["Helps with", "That exact misreading", "Similar letters and words never corrected"],
               ["When it works", "Next scan", "When the training team ships a new reader"],
               ["Best for", "Fixing today's results", "Fewer misreads from now on"]]),
    ("h", "Fix OCR: the instant fix"),
    ("img", "fixocr.png", 110),
    ("rows", [("What", "Saves a rule: when the scanner says RRP, it means RFP."),
              ("How", "Click the wrong row, type the correct term in the bottom box, click Fix OCR, then rescan."),
              ("When", "A misreading you see now, or one that keeps coming back."),
              ("Why", "No waiting and no setup. Every later scan, and every teammate with your Knowledge Pack, gets it right."),
              ("Careful", "Exact match only. Add a rule only for a reading that is always wrong.")]),
    ("h", "Report misreading: collect lessons"),
    ("img", "teach.png", 300),
    ("rows", [("What", "In the picture preview, fix the reading and click Report misreading. It saves the picture line and the right text."),
              ("When", "Any time a picture is misread. It takes two seconds."),
              ("Why", "Each one is a lesson. Lessons are how the reader gets better over time.")]),
    ("h", "Send corrections: the training team teaches the reader"),
    ("rows", [("What", "Tools > Send corrections (or the green bar) saves your lessons as one corrections pack."),
              ("Where", "The approved SharePoint folder for the training team only. Never email, GitHub or USB."),
              ("Then", "The training team imports everyone's packs in Acronym Hunter Training, checks each line, trains a "
                       "better reader and tests it. Only a reader that reads better ships."),
              ("Back to you", "It comes back as a numbered Knowledge Pack: Tools > Knowledge Packs > Install. Undo puts the "
                              "previous one back.")]),
],
"Effort list": [
    ("h", "One list per proposal"),
    ("p", "The effort list is an Excel file that keeps every term found, chosen and approved for one proposal. "
          "It starts on your desktop and can live in a synced SharePoint folder so the team sees the same list."),
    ("img", "effort_setup.png", 460),
    ("img", "effort_line.png", 560),
    ("rows", [("Start", "Effort > New effort. Name it, pick where the list lives, choose the first-use rule, and point to the "
                        "customer documents folder."),
              ("Customer first", "Every scan reads the customer documents' own definitions: \"Spelled Out (ACR)\" and acronym "
                                 "tables. The customer's definition beats the database. Two different ones: you choose."),
              ("Add", "Select rows and click Add to effort list. A definition typed in the bottom box goes in too."),
              ("Approve", "Right-click > Effort list > Approve. Enter the SS approver; several names are fine, separated by ;."),
              ("Not a term", "Right-click > Effort list > Not a term in this effort. Hidden for this proposal only."),
              ("Scan Again", "Approved definitions win on every later scan. Edits made in Excel are read too."),
              ("Export", "Effort > Export for approvals: sheets for Needs author, Conflicts, Approved and All."),
              ("Excel open", "If the list is open in Excel, the app asks you to close it and keeps your change until it can save.")]),
    ("p", "The Add to effort list button sits in the bottom bar:"),
    ("img", "effort_add.png", 150),
    ("h", "Which definition wins"),
    ("p", "Effort list (approved) > customer documents > client lists > company database."),
    ("h", "Check a volume before it ships"),
    ("p", "Effort > Check volumes. Pick the final volumes; the file names set the submission order (Vol 2 before Vol 10)."),
    ("img", "volume_check.png", 600),
    ("rows", [("First use", "Acronyms only. Each must first appear as \"Spelled Out Words (ACR)\", per volume or across the "
                            "submission (the effort's first-use rule). Red: not defined. Amber: the words differ from the list."),
              ("Not in effort list", "Terms the volume uses that the list does not have. One click adds them as Proposed."),
              ("Not approved", "In the list, but still Proposed or Needs an author."),
              ("Definition differs", "The volume spells a term out differently from the list."),
              ("Unused", "List entries no volume uses: keep them out of the volume's acronym list."),
              ("Jump", "Double-click any row: the results table selects the term and the preview opens at that spot."),
              ("Acronym lists", "One Word file per volume (and one for all volumes): a Term and Definition table, sorted."),
              ("Record", "Writes Used in volumes and First use into the effort list.")]),
    ("h", "Start an effort"),
    ("p", "Effort > Start a new effort (or Start an effort at the top) opens six short steps: the master database, the effort and client (short name, solicitation number, your internal "
          "number), the customer's own acronym lists, the customer documents, how the list ships (one list, one per volume, or "
          "both; the first-use rule), and ready. The documents are copied into the effort's Customer documents folder and read "
          "for a jump start; Review new terms adds what they hold in one click."),
    ("rows", [("Customer documents later", "Effort > Add customer documents: copies the files in, reads only new or changed "
                                           "ones, and opens Review new terms."),
              ("Every scan", "Updates Found in, First found, Last found and Scan status in the effort list. Terms a rescan no "
                             "longer finds say \"No longer found in <file>\"; nothing is removed."),
              ("Activity", "Effort > Activity: what was added, from which document, by whom, newest first.")]),
    ("h", "Master database and Known in"),
    ("rows", [("Load it first", "The first step of Start an effort loads the company's master database (CSV or Excel with "
                                "Term, Category, Definition, Action, or a plain acronym list). It is shared by every effort on this PC."),
              ("Known in", "Every result says where the term is known: Customer docs, Customer list, Master database only, or "
                           "Not found in any source. Status > Known in filters by it; the CSV export has the column."),
              ("A newer version", "File > Load master database. Each load is a numbered version. Rows added on this PC stay; "
                                  "rows the new version dropped are removed; new rows are added."),
              ("Update the results", "After a new version the app offers to update the results. Nothing is removed: rows the "
                                     "database changes say Database update (Status > Database update), and your decisions, "
                                     "picked definitions and effort list stay. File > Update results against the master database "
                                     "does it any time.")]),
    ("h", "Effort list (home) and Scan review"),
    ("p", "With an effort open, the main window has two views. Effort list (home) shows every decision for the effort, "
          "where each term came from and which volumes use it; it reopens exactly as you left it. Every scan lands in Scan "
          "review, where you decide on what the scan found."),
    ("rows", [("Home", "Counts at the top (terms, approved, need a definition, no longer found). Show: needs a definition, a "
                       "status, no longer found, or one volume. Double-click to edit a definition. Approve, Needs author, "
                       "Not a term, Volumes, Where from (documents, imports and every change), Show in Scan review."),
              ("Scan review", "Keep (Add to effort list), Not a term, Omit, Exclude, Exclude instance in the preview, and Fix "
                              "OCR or Report misreading for a misreading (sent to the training team)."),
              ("Use as definition", "Select words in the Source preview (the passage, or the recognized text of a picture) "
                                    "and click Use as definition, or right-click. When the documents, the customer's list or "
                                    "the nearby words already give a long form, the preview shows \"Found: ...\" with a Use "
                                    "button. The definition is kept for later scans in this effort and goes into the effort "
                                    "list when you Keep the term.")]),
    ("h", "Keywords for SharePoint"),
    ("p", "Collect the keywords for tagging the submission while you work, not after. The Keywords view (next to Effort "
          "list and Scan review) keeps them in the effort list's Keywords sheet."),
    ("rows", [("Capture", "Ctrl+K in the app (selected preview text or the clipboard fills it in), right-click a result, "
                          "preview text or a home row > Add as keyword, or Ctrl+Alt+K anywhere in Windows after copying a phrase."),
              ("Suggest", "Suggest keywords reads the customer documents and your volumes and lists phrases with the reasons: "
                          "how often and where, in a heading, near requirement or evaluation wording, only in our volumes. "
                          "Rules and counts only (No AI). Not a keyword keeps a phrase from coming back."),
              ("Decide", "Keep, Reject, Edit (category, why, SharePoint field) or Remove. Every change is in the History sheet."),
              ("Smarter", "Past proposals: build a baseline from a folder of past submissions; phrases every proposal uses score "
                          "lower, phrases new to this one higher. Keep and Reject teach later suggestions in every effort. Both "
                          "keep hashed phrases with counts only, never the text."),
              ("Show in document", "Double-click a suggestion, or Show in document: the passage it came from, highlighted."),
              ("Team", "Knowledge Packs carry the offerings catalog and the Keep/Reject learning, so the whole team gets them."),
              ("More capture", "Right-click a compliance row (its outline section), selected words in the requirement text, or a "
                               "Setup outline heading > Add as keyword."),
              ("Offerings", "Offerings catalog: Sierra Space offerings kept once on this PC (name, other names, group, "
                            "description). Import a list, export it to share. Attach offerings adds them to an effort's keywords "
                            "in one step; suggestions mark an offering when the documents name it; Add to catalog turns a keyword "
                            "into an offering."),
              ("Export", "Excel or CSV in the SharePoint columns: Keep only, or Keep and Proposed. The app never connects to "
                         "SharePoint.")]),
    ("h", "Volumes and export"),
    ("rows", [("Name volumes", "Home > Name volumes (or Effort > Name volumes): Vol I Technical, Vol II Management... and tick "
                               "the files in each. Terms get their volumes from the files they were found in."),
              ("Assign by hand", "Select terms on the home view, Volumes..., tick the volumes. A term can belong to several. "
                                 "Your ticks stay when a rescan finds it elsewhere; Automatic goes back to the files."),
              ("Import a list", "Home > Import a list: an acronym list exported earlier or written by an author (CSV, Excel, "
                                "Word, PDF, text). Say which volume it is for. New terms join as Proposed; a different "
                                "definition is kept under Other definitions."),
              ("Export", "Home > Export: tick the columns (Term and Definition by default), one file or one per volume, the "
                         "volumes to include, approved only, and CSV, Excel or Word. Rejected terms and the omit list are "
                         "left out. Your last choice is remembered for this effort.")]),
    ("h", "Several efforts at once"),
    ("p", "Each effort keeps its own work: results, choices, compliance matrix, volume check and where you left off. "
          "Nothing from one effort shows up in another."),
    ("rows", [("Switch", "Pick an effort in the Effort box at the top of the window. Your work is already saved, so switching "
                         "takes one click and puts you back where you were in that effort."),
              ("Resume", "The app opens the effort you used last and says so: \"Resumed Kestrel, last worked yesterday 4:12 PM.\" "
                         "The effort's name stays in the title bar."),
              ("Its folder", "Each effort has a folder named \"<list name> - app data\" next to its effort list. Copy the list "
                             "and that folder together to move the whole effort."),
              ("One window", "If an effort is open in another window, on this PC or a teammate's through SharePoint, the app "
                             "says who has it and asks before opening it."),
              ("Archive", "Effort > Archive this effort hides a finished effort. Effort > Archived efforts brings it back. "
                          "Nothing is deleted.")]),
    ("h", "If the app closes unexpectedly"),
    ("rows", [("Saved as you go", "Every choice, approval and compliance decision is written to disk within seconds."),
              ("Recover", "Changes that could not be saved (the app closed, or Excel had the file open) come back the next time "
                          "you open the effort: the app asks \"Recover them now?\""),
              ("Earlier versions", "File > Restore an earlier version lists dated copies of the effort list and compliance "
                                   "matrix (kept every 10 minutes while you work, plus one per day for two weeks). The current "
                                   "file is copied first, so a restore can be undone.")]),
],
"Compliance matrix": [
    ("h", "Every requirement in the RFP, with its source"),
    ("p", "Compliance (top bar) > New from RFP files. Pick the instructions, evaluation criteria, SOW and attachments. Rules "
          "list every sentence that asks for something (shall, must, will, should, may, describe, provide, page limits, "
          "fonts, due dates), each with its file, page or section, and the passage it came from. No AI writes anything."),
    ("img", "compliance.png", 620),
    ("rows", [("Decide", "K keeps, D drops, U undoes; the next row comes up. Select many rows to decide them together."),
              ("Suggested", "Government statements are suggested Drop, 'may' is Review, offeror and contractor duties are Keep. "
                            "Accept suggestions applies them to the undecided rows shown; Review rows stay for you."),
              ("Split", "S splits a compound requirement (two 'shall's, or items joined by ';') into separate rows."),
              ("Type and actor", "Instruction (L), Evaluation (M), SOW (C), Format, Information; Offeror, Contractor or Government."),
              ("Links", "Evaluation and SOW items link to the instructions they concern, by section number or shared wording."),
              ("Outline", "Outline tab: start from the Section L headings, import a Word outline's headings, or type one. "
                          "Map kept rows to a section; Suggest sections fills only clear matches, then learns from rows you mapped."),
              ("Merge", "Select two or more rows and press M (or Merge) to join a requirement that the rules split."),
              ("Learned", "The app learns from your Keep and Drop decisions (Learn from decisions, and after every save). The Learned "
                          "column shows how likely the team is to keep a row; Accept suggestions uses it once it has enough decisions. "
                          "It stores numbered word buckets and counts, never RFP text, and travels in Knowledge Packs."),
              ("Source page", "Show page opens a PDF row's page with the sentence highlighted. Open file opens any source document."),
              ("Amendments", "Re-read RFP keeps decisions, mapping and notes for unchanged sentences. Amendment changes pairs changed "
                             "sentences and shows the word differences: [-removed-] {+added+}; export it to Excel."),
              ("Outputs", "The matrix is an Excel workbook (edits made in Excel count). Word outline makes the proposal outline "
                          "with each section's requirements in a table.")]),
    ("p", "The matrix holds customer content: keep it on this PC or SharePoint."),
    ("h", "Setup: the first draft for authors"),
    ("p", "The Setup tab puts the RFP text under the proposal outline and writes the setup documents: every heading of the "
          "outline, with the RFP text that section must answer and the proposal lead's direction."),
    ("rows", [("Place", "Drag RFP text from the left onto a section on the right. Shift+drag adds a copy to a second section. "
                        "Drag inside the outline to reorder, or back to the left to remove. Accept suggestions places what the "
                        "rules and your earlier mapping suggest. Placing a row also fills its Outline column, and the other way round."),
              ("Context", "Add context from RFP keeps the RFP's other paragraphs (SOW text, evaluation criteria) so you can place "
                          "them too."),
              ("References", "Each RFP block starts with its reference on the same line: L.4.2(a): text. The app takes it from the "
                             "RFP's numbering, from the heading above, or from a rule you set per file in References "
                             "(Attachment 3 = L gives L-3.2). Type one, or use Fill down for several rows. Orange rows have none."),
              ("Direction", "Select a section and type the management direction below the outline. Select a row to add a note for "
                            "that one requirement."),
              ("Export", "Export setup writes one Word file per volume: built-in headings, RFP text in purple, direction in green. "
                         "No hidden text and no styles of yours: click one purple paragraph, Home > Select > Select Text with "
                         "Similar Formatting, and apply your style; the same for green."),
              ("Changed later", "The setup stays in the matrix, so you can export again any time. Export changes only writes just "
                                "what was added, changed or removed since the last export. Compare a setup document checks a "
                                "styled setup against the matrix and lists anything missing or under the wrong heading.")]),
],
"Pictures": [
    ("h", "The picture preview (right side)"),
    ("img", "preview.png", 340),
    ("rows", [("Source", "Pick a source location. Pictures and PDF pages show boxes; Word, PowerPoint and Excel typed "
                                     "text shows the passage with the term highlighted."),
              ("Find ◀ ▶", "Step through every find of the term, then on to its next location."),
              ("Zoom", "Mouse wheel or + / -. Drag to move around. Whole shows the whole page or picture."),
              ("Enlarge", "Opens the picture in a big window. Click boxes there too."),
              ("Click a box", "Every box is something the scanner read. Click one to check or fix it."),
              ("Report misreading", "Fix the spelling and save a lesson for the training team (see Fix OCR vs Training)."),
              ("Not text", "A line, arrow or speck read as text. The scanner ignores it from now on."),
              ("Exclude term", "A real reading, but not a term you want listed, anywhere (a database rule)."),
              ("Exclude instance", "Only this place is wrong: the term stays in its other places. Saved for this effort."),
              ("Undo last save", "Takes back your last save in this panel.")]),
    ("p", "Tools > Show preview pane turns this panel on or off."),
],
"Symbols": [
    ("h", "Symbol picker: no more copy and paste"),
    ("img", "picker.png", 380),
    ("rows", [("Open", "The Ω button next to a text box, Ctrl+Shift+Space, or right-click a text box."),
              ("Insert", "Click a symbol. It goes into the box you were typing in."),
              ("Find", "Search by name: sigma, dot, sub 2, degree, arrow."),
              ("Sub / Sup", "Select text (Isp: select sp) and click Sub to get Iₛₚ. Normal turns it back."),
              ("Accents", "Put the cursor after the letter, then click the accent: m + dot gives ṁ."),
              ("Recent", "Your last 24 symbols, ready to reuse.")]),
],
"Equations": [
    ("h", "Equations and symbols"),
    ("p", "Typed equations are read automatically. Their symbols (Isp, g₀, Δv) are listed as Symbols, with the "
          "definition when the document gives one."),
    ("h", "Math reader (optional add-on)"),
    ("img", "math.png", 440),
    ("rows", [("What", "Reads an equation picture and writes out the whole equation, 96-98% of symbols right."),
              ("How", "Click an Equation (picture) row, then Read this equation with the math reader. "
                      "Select several rows and right-click to read them all."),
              ("When", "Pictures of equations. Without it, the scanner reads them as loose letters."),
              ("Speed", "About 5 seconds per small equation. Results are remembered."),
              ("Install", "Unzip AcronymHunter_MathAddon.zip next to the app. It runs only in the no-network sandbox.")]),
],
"Sharing": [
    ("h", "Work as a team"),
    ("img", "menubar.png", 420),
    ("rows", [("Knowledge Pack", "Tools > Knowledge Packs. The training team ships the reader, database, OCR fixes and "
                                 "ignore list in one numbered file. Install it; Undo puts the previous one back."),
              ("Corrections", "Tools > Send corrections. Your lessons for the training team, in one file."),
              ("Where", "Your approved local SharePoint folder only. Never GitHub, email or USB."),
              ("Client Lists", "Load the client's own acronym list. Its definitions win over the database."),
              ("Projects", "Project > Save. A rescan reads only files that changed."),
              ("Full Text", "Tools > Full Text. All typed and picture text, saved as .txt.")]),
    ("h", "Feedback: bugs, improvements, ideas"),
    ("rows", [("Open", "The Feedback button, or Ctrl+Shift+F."),
              ("Write", "Pick Bug, Improvement or Idea and the feature. Describe the feature, never your documents."),
              ("Guard", "The app will not save text that matches your terms, definitions, file or folder names."),
              ("Export", "Export for Claude shows everything first, then saves one text-only zip."),
              ("Logs", "The app also logs errors and which controls are clicked, by internal name only. "
                       "No file names, terms or document text, ever.")]),
    ("h", "Good team habit"),
    ("p", "Everyone reports misreadings and sends corrections. The training team runs Acronym Hunter Training, ships a "
          "Knowledge Pack, and everyone installs it. The whole team gets the better reader."),
],
"AI and ML": [
    ("h", "What runs each part"),
    ("p", "Every sidebar section shows what runs it. Click its ? to see each part and its job. Everything runs on this PC, "
          "with no network."),
    ("table", [["Label", "Meaning", "Examples"],
               ["No AI", "Fixed rules, counting and file reading. Same input, same output.", "Typed text, Effort list, volume check, compliance rules"],
               ["ML", "A trained model that recognizes or scores. Outputs letters, boxes or numbers, never sentences.",
                "Text in pictures (Tesseract, docTR), learned compliance suggestions, Improve Reading"],
               ["Gen AI", "A model that writes text. Separate add-on, runs in the no-network sandbox.", "Math reader add-on"]]),
    ("h", "The AI and ML switch"),
    ("rows", [("Where", "Top right of the window. The ? next to it explains AI vs ML."),
              ("Per effort", "Each effort keeps its own setting. New efforts start with AI and ML on."),
              ("Off", "Every ML and Gen AI part stops: the model code refuses to run, and its buttons grey out. Typed text in "
                      "Word, PowerPoint, Excel and PDFs is still read. Text inside pictures and scanned pages is not."),
              ("Logged", "Each change goes into the effort list's History sheet (date, Windows user, setting) and the usage "
                         "log (the effort appears as a number, never its name)."),
              ("Team learning", "In the compliance window. Off: this effort's decisions are not learned and the Learned column "
                                "stays empty. AI and ML off turns it off too.")]),
    ("h", "For your security team"),
    ("p", "Help > What runs where lists every part and saves a one-page summary to hand to reviewers. The line at the "
          "bottom of the window always shows the effort and whether AI and ML are on."),
],
}

def open_guide(parent, page=None):
    if _win[0] is not None and _win[0].winfo_exists():
        w = _win[0]
        w.deiconify(); w.lift(); w.focus_force()
        if page:
            w._show(page)
        return w
    win = ctk.CTkToplevel(parent); _win[0] = win
    win.title("How Acronym Hunter works"); win.geometry("820x680"); win.minsize(640, 420)
    win.transient(parent); win.after(150, win.lift)
    head = ctk.CTkFrame(win, fg_color="transparent"); head.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(head, text="How Acronym Hunter works", font=("Arial", 17, "bold")).pack(side="left")
    ctk.CTkButton(head, text="Close", width=80, fg_color="#475569", command=win.withdraw).pack(side="right")
    tab = tk.StringVar(value=page or "Start here")
    seg = ctk.CTkSegmentedButton(win, values=list(PAGES), variable=tab, command=lambda v: show(v))
    seg.pack(fill="x", padx=12, pady=4)
    body = ctk.CTkScrollableFrame(win, fg_color=("#F8FAFC", "#1E1E1E")); body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
    WRAP = 740

    def show(name):
        tab.set(name)
        for c in body.winfo_children():
            c.destroy()
        for blk in PAGES[name]:
            kind = blk[0]
            if kind == "h":
                ctk.CTkLabel(body, text=blk[1], font=("Arial", 15, "bold"), anchor="w").pack(fill="x", padx=10, pady=(14, 4))
            elif kind == "p":
                ctk.CTkLabel(body, text=blk[1], font=("Arial", 13), anchor="w", justify="left", wraplength=WRAP).pack(fill="x", padx=10, pady=2)
            elif kind == "img":
                im = _img(blk[1], blk[2])
                if im is not None:
                    ctk.CTkLabel(body, text="", image=im, anchor="w").pack(anchor="w", padx=10, pady=6)
            elif kind == "rows":
                g = ctk.CTkFrame(body, fg_color="transparent"); g.pack(fill="x", padx=10, pady=2)
                g.grid_columnconfigure(1, weight=1)
                for r, (lab, txt) in enumerate(blk[1]):
                    ctk.CTkLabel(g, text=lab, font=("Arial", 13, "bold"), anchor="w", width=150, justify="left",
                                 wraplength=150).grid(row=r, column=0, sticky="w", pady=3)
                    ctk.CTkLabel(g, text=txt, font=("Arial", 13), anchor="w", justify="left",
                                 wraplength=WRAP - 170).grid(row=r, column=1, sticky="w", padx=(8, 0), pady=3)
            elif kind == "table":
                t = ctk.CTkFrame(body, fg_color=("#E2E8F0", "#2B2B2B"), corner_radius=8); t.pack(fill="x", padx=10, pady=6)
                for c in range(len(blk[1][0])):
                    t.grid_columnconfigure(c, weight=1 if c else 0)
                for r, row in enumerate(blk[1]):
                    for c, cell in enumerate(row):
                        bold = r == 0 or c == 0
                        ctk.CTkLabel(t, text=cell, font=("Arial", 13, "bold" if bold else "normal"), anchor="w", justify="left",
                                     wraplength=250).grid(row=r, column=c, sticky="w", padx=10, pady=4)
        try:
            body._parent_canvas.yview_moveto(0)
        except Exception:
            diag.swallowed()
            pass
    win._show = show
    diag.register(win, "guide")
    diag.register(seg, "guide.tabs")
    win.bind("<Escape>", lambda e: win.withdraw())
    show(tab.get())
    return win
