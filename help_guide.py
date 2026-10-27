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
    ("h", "One feature at a time"),
    ("img", "shell.png", 640),
    ("p", "The dark list on the left holds the features in work order: Effort home, Compliance, Acronyms, QA/QC, Keywords. "
          "Click one and only its tools show. Across the top are its steps, in order: the current step is blue, steps with "
          "work done are green with a check mark. Click any step to go to it. Each feature ends in its own Export step; "
          "Effort home and File > Export all write everything at once. One status line runs along the bottom."),
    ("rows", [("Effort home", "The effort's stage, the goals for this gate, tasks, notes and open questions, the timeline, where "
                              "each feature stands, the next step to take, and Export all."),
              ("Submission", "Requirements (what to deliver and how, and how it changed), Deliverables (what we owe and where "
                             "each stands), Documents (every customer document "
                             "with its versions), Impact (what a new version touched across the effort), Compare (what changed between any two "
                             "versions), Export."),
              ("Compliance", "Read RFP, Structure (the response outline), Assign (each sentence a compliance requirement in "
                             "a section, context, or not used), Prove (nothing missed; owner, status and page), Export."),
              ("Acronyms", "Scan (Select Files, Scan Folder, Scan Again, Project), Review (the results, with their filters), "
                           "Define and approve (the effort list), Export."),
              ("QA/QC", "Check our Word deliverables (first use, banned words, acronym lists), Export the report."),
              ("Keywords", "Collect and decide the effort's keywords, Export them for SharePoint.")]),
    ("p", "The menu bar keeps what the team uses every day. File: New effort, Open effort, Save effort package, Import effort "
          "package, Effort details, Export all. Effort: Effort home, add customer documents, check our volumes, notes, tasks, "
          "stages, the timeline. View: sidebar (Ctrl+B), preview pane, text size. Help: the Guide, Submit an idea or report a "
          "problem, what runs where (AI and ML), the difference between AI and ML, and what Acronym Hunter is built on. "
          "Advanced: everything else (scanning files outside an effort, the results list, the master database, all effort "
          "list commands, reading and training)."),
    ("h", "The effort record: where the effort stands, and how it got there"),
    ("rows", [("Effort details", "File > Effort details (or the date in the top right corner): client, solicitation or "
                                 "opportunity number, internal number, and the due date and time. The top right corner then "
                                 "counts down the days and hours on every screen (amber inside a week, red inside three days). "
                                 "When the customer documents state a due date, Effort details offers it."),
              ("Stages", "The team's gates: Intake, Author drafts, Red team, Red team recovery, Gold team, Gold team recovery, "
                         "Final to pubs. Edit stages... renames, adds, removes and reorders them for this effort, each with a "
                         "planned date. Only the proposal manager moves the stage (Move to...); the open goals of the stage "
                         "being left can carry over."),
              ("Gate goals", "What must be true at each gate, with a progress bar. Goals the app can check tick themselves "
                             "(documents reviewed, every requirement in a section, page limits met, first use clean...); "
                             "written goals are ticked by hand, with who and when. + Goal adds one."),
              ("Notes", "+ Note on the effort, a stage, a customer document or a requirement. Tick Open question to keep it "
                        "open until someone resolves it with the answer."),
              ("Tasks and people", "+ Task: owner, due date, stage, status and notes; late tasks show red. Pick a person to "
                                   "see their sections, compliance requirements and tasks. In Assign, O gives one compliance "
                                   "requirement its own owner; People... sets a lead and contributors per section."),
              ("Timeline", "The paper trail, written as it happens: every customer document and version added (with what "
                           "changed), requirement reviews, stage moves, goals met, notes, tasks, owners, QA/QC checks. Full "
                           "timeline... shows all of it."),
              ("Effort status", "File > Effort status (Word)... (or Effort status on Effort home) answers \"Where are we?\" "
                                "for leadership in one Word file: the countdown, a stage track (done, current, ahead), tiles "
                                "for goals, requirements placed, open questions, late tasks and changes to review; what is "
                                "done, in progress and left in this stage; open questions and notes; the projected timeline; "
                                "people and assignments; tasks; what changed since this stage began; submission requirements; "
                                "each stage's goals; the customer documents. Effort summary, complete history (Word)... is the "
                                "same report with the whole timeline: the record of the proposal when it is done. Export all "
                                "includes the status."),
              ("Hand-off", "File > Save effort package... writes the whole effort into one .ahpkg file: stage, goals, notes, "
                           "tasks, timeline, customer document versions, submission requirements, the compliance matrix and "
                           "the acronym list, the customer files, our volumes and every file a deliverable points to (all "
                           "ticked at first). File > Import effort package... opens it on another PC where it was left, with "
                           "every link pointed at the new folder; Advanced > Make .ahpkg effort packages open in Acronym "
                           "Hunter lets a double-click open it (your Windows user only, no admin rights). Team-wide lists "
                           "(the master database, banned words, team keyword knowledge) stay with each PC; if the effort is already there, choose to "
                           "use the package (the old copy is backed up) or keep both. Save packages on this PC or in the "
                           "approved SharePoint folder only.")]),
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
    ("p", "The row above the results (Acronyms > Review): show one type or status, or search. Show excluded brings back "
          "terms you excluded."),
    ("h", "The action bar (bottom)"),
    ("img", "scanreview.png", 600),
    ("rows", [("Add, Not a term, Skip", "With an effort open: A adds the term to the effort list, X marks it Not a term, "
                                        "Space skips; the next term comes up. More holds Include in DB, Exclude, Omit and Fix OCR."),
              ("Apply Choice", "Pick one meaning when a term has several."),
              ("Include in DB", "Type the definition and save it. Every future scan knows it."),
              ("Fix OCR", "The term is a misreading. Type the correct term. See the Fix OCR vs Training tab."),
              ("Exclude", "Not a real term (a heading word, a part number). Hidden from now on, everywhere."),
              ("Context", "When a term has several meanings, the words around it suggest one: words it shares with a "
                          "meaning, a role (\"the PM shall\" is a person), a document word (\"PM plan\"), or the long form "
                          "spelled out in the same files. The Definition column says \"Context: ...\" and why, Apply Choice "
                          "starts on it, and the Source preview says what it likely means at each place. When places "
                          "disagree, the row says \"meaning differs by place\". Nothing is applied until you choose: "
                          "right-click > Accept context suggestion, or Advanced > Results list > Accept context suggestions. Rules only, "
                          "typed text only."),
              ("Heading words", "Ordinary words in all-capital headings (EVALUATION FACTORS FOR AWARD) are set aside, not "
                                "listed as acronyms. Show Excluded lists them; a word also used in running text stays."),
              ("Omit list", "Company names, locations and other terms you want found and recognized but never on the final "
                            "list. Right-click > Add to omit list (say what it stands for and why), or Advanced > Results list > Omit list to add, "
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
    ("rows", [("What", "Advanced > Reading, training and knowledge > Send corrections to the training team (or the green bar) saves your lessons as one corrections pack."),
              ("Where", "The approved SharePoint folder for the training team only. Never email, GitHub or USB."),
              ("Then", "The training team imports everyone's packs in Acronym Hunter Training, checks each line, trains a "
                       "better reader and tests it. Only a reader that reads better ships."),
              ("Back to you", "It comes back as a numbered Knowledge Pack: Advanced > Reading, training and knowledge > Knowledge... > Install. Undo puts the "
                              "previous one back.")]),
    ("img", "training.png", 480),
],
"Effort list": [
    ("h", "One list per proposal"),
    ("p", "The effort list is an Excel file that keeps every term found, chosen and approved for one proposal. "
          "It starts on your desktop and can live in a synced SharePoint folder so the team sees the same list."),
    ("img", "effort_setup.png", 460),
    ("img", "effort_line.png", 560),
    ("rows", [("Start", "File > New effort. Name it, pick where the list lives, choose the first-use rule, and point to the "
                        "customer documents folder."),
              ("Customer first", "Every scan reads the customer documents' own definitions: \"Spelled Out (ACR)\" and acronym "
                                 "tables. The customer's definition beats the database. Two different ones: you choose."),
              ("Add", "Select rows and click Add to effort list. A definition typed in the bottom box goes in too."),
              ("Approve", "Right-click > Effort list > Approve. Enter the SS approver; several names are fine, separated by ;."),
              ("Not a term", "Right-click > Effort list > Not a term in this effort. Hidden for this proposal only."),
              ("Scan Again", "Approved definitions win on every later scan. Edits made in Excel are read too."),
              ("Export", "Advanced > Effort list and all effort commands > Export for approvals: sheets for Needs author, Conflicts, Approved and All."),
              ("Excel open", "If the list is open in Excel, the app asks you to close it and keeps your change until it can save.")]),
    ("p", "The Add to effort list button sits in the bottom bar:"),
    ("img", "effort_add.png", 150),
    ("h", "Which definition wins"),
    ("p", "Effort list (approved) > customer documents > client lists > company database."),
    ("h", "QA/QC: check our deliverables before they ship"),
    ("p", "First use matters only in what we write: the response to the RFP. The QA/QC view (next to Effort list, Scan "
          "review and Keywords) checks our Word volumes; customer documents are never checked for first use. Open QA/QC in "
          "the feature list, click Check Word deliverables and pick the final volumes; the file names set the submission "
          "order (Vol 2 before Vol 10)."),
    ("p", "Word documents (.docx) only. Run it on the Word files, not on PDF exports: a PDF loses the difference between "
          "running text, tables, captions, figures and headings, so first-use results on a PDF would not be accurate. A PDF "
          "you pick is left out, with a note."),
    ("img", "qa.png", 600),
    ("rows", [("Fix list", "Rows are listed worst first: Fix, then Check, Note and OK. Next fix (N) jumps to the next red row "
                           "across First use, Banned words and Acronym list and says what to fix on the status line."),
              ("First use", "Acronyms only. Each must first appear as \"Spelled Out Words (ACR)\", per volume, per section "
                            "of each volume, or across the submission (the effort's first-use rule)."),
              ("Check column", "\u2713 OK (green): defined at first use. \u2717 Fix (red): not defined at first use, or never "
                               "defined. ! Check (amber): defined, but the words differ from the effort list or no spelled-out "
                               "words come before (ACR). i Note (blue): defined again later, or used only in figures or "
                               "tables. The line at the top counts each."),
              ("Used once", "An acronym defined at first use but never used again gets ! Check: spell it out and leave out "
                            "the (ACR). Uses in tables and figures count; the volume's own acronym list does not."),
              ("Banned words", "QA/QC also lists every banned word or phrase candidate in the volume: what it found, the "
                               "list entry, where (text, table, caption, header), the sentence, and what to use instead. "
                               "\u2717 Fix for Banned, ! Check for Avoid. Double-click a row for the whole passage with the word "
                               "highlighted and an Open in Word button. Banned words list... edits the team's list (add, edit, "
                               "remove, import a CSV or Excel list, export, back to the starter list); Knowledge Packs carry it. "
                               "Matching: not case sensitive, hyphen or space alike, -s/-ed/-ing found, * for any letters, "
                               "short capitals (TBD) match capitals only. Text inside pictures is not checked."),
              ("Acronym list", "The volume's own list (a table of acronym and definition, or lines of acronym<tab>definition) "
                               "is checked on its own tab: \u2717 used in the volume but not listed; ! listed but not used "
                               "anywhere else, or its definition differs from the effort list; \u2713 listed, used and "
                               "matching. A volume with no list gets a note."),
              ("Text, figures, tables", "First use is judged in the running text only. Tables, figures (pictures, diagrams, "
                                        "charts, text boxes), captions, headers and footers never count as a first use. "
                                        "The In figures or tables column shows where a term also appears in one; a term "
                                        "used only there is listed in blue with nothing to check."),
              ("Per section", "Sections come from Word headings. Numbered headings group by their first number or letter "
                              "(2, 2.1 and 2.3 are all section 2; C.3 is section C); other headings are their own section. "
                              "PDFs and slides have no headings, so the whole file counts as one section. Advanced > Effort list and all effort commands > Effort settings "
                              "changes the rule."),
              ("Not in effort list", "Terms the volume uses that the list does not have. One click adds them as Proposed."),
              ("Not approved", "In the list, but still Proposed or Needs an author."),
              ("Definition differs", "The volume spells a term out differently from the list."),
              ("Unused", "List entries no volume uses: keep them out of the volume's acronym list."),
              ("Jump", "Double-click any row: the results table selects the term and the preview opens at that spot."),
              ("Acronym lists", "One Word file per volume (and one for all volumes): a Term and Definition table, sorted."),
              ("Record", "Writes Used in volumes and First use into the effort list.")]),
    ("h", "Start an effort"),
    ("p", "File > New effort (or Start an effort at the top) opens seven short steps: the Acronyms, Abbreviations, Units and Symbols Master Database, the effort and client (short name, solicitation number, your internal "
          "number), the customer's own acronym lists, the customer documents, the response structure, how the list ships (one "
          "list, one per volume, or both; the first-use rule), and ready. The documents are copied into the effort's Customer documents folder and read "
          "for a jump start; Review new terms adds what they hold in one click."),
    ("rows", [("Customer lists", "Add files (Excel, Word, CSV, text, PDF, or a picture or scan of a list, read with the "
                                 "picture reader), or Paste or type...: paste a list copied from anywhere or type one term per "
                                 "line. Every term found is shown with a tick: untick what is wrong, double-click to correct it, "
                                 "then add the ticked ones. Client Lists does the same any time."),
              ("Response structure", "Suggested from the customer documents: the volumes the instructions name (\"Volume I "
                                     "Technical, Volume II Management...\"), their page limits, and the Section L headings under "
                                     "each volume, numbered 1.1, 1.2 with the RFP reference in brackets. Edit it or type your "
                                     "own. The compliance matrix starts its outline from it, and [L.4.1] references place "
                                     "those requirements under that section."),
              ("Customer documents later", "Effort > Add customer documents: copies the files in, reads only new or changed "
                                           "ones, and opens Review new terms."),
              ("Every scan", "Updates Found in, First found, Last found and Scan status in the effort list. Terms a rescan no "
                             "longer finds say \"No longer found in <file>\"; nothing is removed."),
              ("Activity", "Advanced > Effort list and all effort commands > Activity: what was added, from which document, by whom, newest first.")]),
    ("h", "Acronyms, Abbreviations, Units and Symbols Master Database and Known in"),
    ("rows", [("Load it first", "The first step of Start an effort loads the company's Acronyms, Abbreviations, Units and Symbols Master Database (CSV or Excel with "
                                "Term, Category, Definition, Action, or a plain acronym list). It is shared by every effort on this PC."),
              ("Known in", "Every result says where the term is known: Customer docs, Customer list, Master database only, or "
                           "Not found in any source. Status > Known in filters by it; the CSV export has the column."),
              ("A newer version", "Advanced > Master database > Load the Acronyms, Abbreviations, Units and Symbols Master Database. Each load is a numbered version. Rows added on this PC stay; "
                                  "rows the new version dropped are removed; new rows are added."),
              ("Update the results", "After a new version the app offers to update the results. Nothing is removed: rows the "
                                     "database changes say Database update (Status > Database update), and your decisions, "
                                     "picked definitions and effort list stay. Advanced > Master database > Update results against the master database "
                                     "does it any time.")]),
    ("h", "Effort list (home) and Scan review"),
    ("p", "Acronyms has two working steps. Define and approve (the effort list) shows every decision for the effort, "
          "where each term came from and which volumes use it; it reopens exactly as you left it. Every scan lands in Review, "
          "where you decide on what the scan found."),
    ("img", "home.png", 600),
    ("rows", [("Home", "Counts at the top (terms, approved, need a definition, no longer found). Show: needs a definition, a "
                       "status, no longer found, or one volume. Double-click to edit a definition. Approve, Needs author, "
                       "Not a term, Volumes, Where from (documents, imports and every change), Show in Scan review."),
              ("Found in", "With an effort open, Acronyms opens on Review. Until something is found, one button scans the "
                           "effort's documents (its customer documents and our volumes), no file picking. The Found in column "
                           "and filter say where each term was found: Customer, Ours or Both."),
              ("Review", "A adds the term to the effort list, X marks it Not a term, Space skips; the next term comes up "
                         "each time. More holds Include in the database, Exclude (all places), Omit and Fix OCR. In the preview: "
                         "Exclude instance, and Report misreading for a misreading (sent to the training team)."),
              ("Use as definition", "Select words in the Source preview (the passage, or the recognized text of a picture) "
                                    "and click Use as definition, or right-click. When the documents, the customer's list or "
                                    "the nearby words already give a long form, the preview shows \"Found: ...\" with a Use "
                                    "button. The definition is kept for later scans in this effort and goes into the effort "
                                    "list when you Keep the term.")]),
    ("img", "scanreview.png", 600),
    ("h", "Keywords for SharePoint"),
    ("p", "Collect the keywords for tagging the submission while you work, not after. Keywords in the feature list keeps "
          "them in the effort list's Keywords sheet."),
    ("img", "keywords.png", 600),
    ("rows", [("Capture", "Ctrl+K in the app (selected preview text or the clipboard fills it in), right-click a result, "
                          "preview text or a home row > Add as keyword, or Ctrl+Alt+K anywhere in Windows after copying a phrase."),
              ("Suggest", "Suggest keywords reads the customer documents and your volumes and lists phrases with the reasons: "
                          "how often and where, in a heading, near requirement or evaluation wording, only in our volumes. "
                          "Rules and counts only (No AI). Not a keyword keeps a phrase from coming back."),
              ("Both sides", "Suggestions come from three places, and Show picks one: From the customer (their emphasis, "
                             "marked when we have not used it yet), In both (Shared language: the customer's words used in our "
                             "answer, scored up), and From our volumes. A phrase only in our volumes is Our response when it sits "
                             "in our section that answers a customer ask, and the Answers column names it: the requirement the "
                             "compliance matrix placed in that section, else the customer's phrase that section uses. These are "
                             "the words we offer in reply that the customer never wrote, and they score up too. The list keeps a "
                             "share of each side, so neither crowds out the other."),
              ("Decide", "Keep (K), Reject (R), Space for the next one; Edit (category, why, SharePoint field) or Remove. Every "
                         "change is in the History sheet."),
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
    ("img", "suggest.png", 460),
    ("h", "Alt forms: one item, several ways of writing it"),
    ("p", "An alt form (TTC for TT&C, SatCom for SATCOM) is never a row of its own. It lives in the Alt forms column of its "
          "primary term, in the effort list and in the master database, and every list the app writes shows it in "
          "parentheses: TT&C (TTC)."),
    ("rows", [("Assign", "Scan review: right-click the alt form > Effort list > Make an alt form of..., and pick the primary "
                         "(the closest match is offered first). If the alt form had its own row in the effort list, it is "
                         "folded into the primary."),
              ("Change", "Effort list (home): select the term > Alt forms... (or right-click). Type the forms separated by "
                         "commas; clear the box to remove them. Right-click an alt form in Scan review > Not an alt form undoes it."),
              ("Found", "The scanner looks for every alt form in the master database. A find keeps its own row, labelled "
                        "\"Alt form of TT&C\" with TT&C's definition. Status > Alt forms lists them."),
              ("Read", "Any list the app reads (master database, effort list typed in Excel, an imported list, a volume's own "
                       "acronym list) takes \"TT&C (TTC)\" as primary TT&C with alt form TTC. A long form such as "
                       "\"Statement of Work (SOW)\" is never split."),
              ("QA/QC", "An alt form has no first use of its own, counts as a use of its primary, and is listed with it.")]),
    ("h", "The Acronyms, Abbreviations, Units and Symbols Master Database across efforts"),
    ("p", "When an effort is done: Advanced > Effort list and all effort commands > Add this effort to the Acronyms, Abbreviations, Units and Symbols Master "
          "Database. One master row per term and meaning; "
          "no repeat rows."),
    ("rows", [("What goes in", "The effort list's Approved terms with a definition, with their alt forms."),
              ("Same item", "A master row with the same term (or one of its alt forms) and the same definition gets this "
                            "effort added to Used in efforts, Times used goes up, Last used is today, and new alt forms are "
                            "added. CDR (Critical Design Review) and CDR (Call Detail Record) stay two rows."),
              ("New item", "Anything else becomes a new row. Adding the same effort again changes nothing."),
              ("Saving", "You see the new and changed rows first. The app writes a new version of the master file you "
                         "loaded, keeps the earlier one in a Master database backups folder beside it, and loads the new "
                         "version on this PC. Share the file as usual (the approved SharePoint folder).")]),
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
                         "left out. Your last choice is remembered for this effort."),
              ("Export all", "Home > Export all (or File > Export all for this effort) writes every feature's outputs into one "
                             "dated folder: customer document version history, compliance matrix, coverage report, Response Setup, acronym lists, "
                             "the QA/QC report and the keyword list. Tick what to include; everything available starts ticked. "
                             "Each feature keeps its own export too.")]),
    ("h", "Several efforts at once"),
    ("p", "Each effort keeps its own work: results, choices, compliance matrix, volume check and where you left off. "
          "Nothing from one effort shows up in another."),
    ("img", "topbar.png", 640),
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
    ("h", "Submission: customer documents and their versions"),
    ("p", "Customer documents keep arriving: amendments, questions and answers, revised attachments. Submission keeps every "
          "version and shows exactly what changed, so a changed page limit or format rule is not missed."),
    ("h", "Deliverables: what we owe and where each stands"),
    ("p", "Submission > Deliverables lists everything the effort must produce: volumes, attachments, forms, plans, slides. "
          "Deliverables the customer documents name are suggested at the bottom in blue: Add as a deliverable, or Not ours. "
          "Add a deliverable... types in any other."),
    ("img", "deliverables.png", 620),
    ("rows", [("Each one", "Format, limit and rules (from the page limits in Requirements when you leave it empty), owner, "
                           "status (Not started, Drafting, In review, Final, Submitted) and notes. Set our file... links our "
                           "working Word file: its page count (as Word last saved it) is checked against the limit, and red "
                           "means over."),
              ("What changed it", "Amber when the requirement or page limit behind it changed in a newer customer version and "
                                  "is not reviewed yet, or when the customer sent a newer version of its form."),
              ("Forms", "Link the customer's form or template (from Documents). Every version shows with its date and "
                        "fingerprint; the newest is marked CURRENT: FILL THIS and the old one stays for the record. Compare "
                        "versions shows what the customer changed."),
              ("By stage", "Done for <stage> marks it for the current gate. The gate goals check that every deliverable "
                           "has an owner and none is over its limit or changed without review."),
              ("Exports", "Checklist (Excel): every deliverable with its marks per stage; Export all and the effort status "
                          "include the deliverables.")]),
    ("h", "Impact: what a new customer version touched"),
    ("p", "When an amendment or a revised document is added, Submission > Impact opens on it: one review per new version, "
          "compared with the version before it. Nothing you decided changes until you act on it. The Version list at the "
          "top picks any other version; Documents has an Impact review button on each new version, and Effort home says "
          "when one waits."),
    ("img", "impact.png", 620),
    ("rows", [("Submission requirements", "Each due date, page limit, format rule, file rule or deliverable the version "
                                          "changed, added or removed, with was and now. Review in Requirements."),
              ("Deliverables", "A deliverable whose page limit or requirement changed (with our file's page count), or whose "
                               "form has a newer version to fill. Deliverables named for the first time: Add as a deliverable, "
                               "or Not ours."),
              ("Compliance", "Matrix sentences the version changed or removed, with their section and owner, and new "
                             "sentences not assigned yet. Update the matrix reads the new version in place of the old one: "
                             "decisions stay on unchanged sentences, new ones are marked [New] and removed ones [Gone]."),
              ("Structure", "RFP headings renamed, added or removed, and our section named like the old heading (rename it "
                            "to match on Compliance > Structure)."),
              ("Acronyms and keywords", "Terms new in this version or gone from it, and whether the effort list or the "
                                        "master database holds them; customer phrases new in this version used twice or "
                                        "more (Add puts one in the keyword list as Proposed)."),
              ("Who it touches", "The owners of the changed sentences and deliverables. Impact report (Word) holds it all, "
                                 "to share with the team."),
              ("Mark impact reviewed", "Marks the version reviewed and the requirement changes it made, and writes it in the "
                                       "timeline.")]),
    ("h", "Submission requirements: front and center"),
    ("p", "Requirements, the first Submission step, lists what to deliver and how, read from every version of every customer "
          "document: the due date and time, the deadline for questions, page limits for each volume, font and size, margins, "
          "page size, line spacing, file format, file naming, copies, delivery, and deliverables (volumes, attachments, forms). "
          "Rules only (No AI)."),
    ("img", "requirements.png", 620),
    ("rows", [("Card and bar", "The card at the top shows the due date with the days left, the page limits, format, files and "
                               "how many changes wait for review. The same line runs as a thin bar under the steps in every "
                               "feature (amber while a change waits); click it to come back here. Effort home shows it too."),
              ("History", "Click a requirement to see where it was found and each version's value, newest first. Previous and "
                          "Next step through the versions: the sentence, the file, who added it, when, and its fingerprint. Was "
                          "and Now show a change. Show the change opens Compare on that sentence."),
              ("Review", "A requirement that changed or disappeared in a new version stays amber (Changed: review) until "
                         "someone clicks Mark reviewed, which records who and when. A later change brings it back."),
              ("Your corrections", "Confirm what is right; Edit... when the rules read it wrong (what the documents say stays beside "
                                   "your wording); Not a requirement hides a false find; Add a requirement... types in one the "
                                   "rules missed. All of it is saved in the effort's folder."),
              ("Page limits in QA/QC", "When QA/QC checks our Word volumes, a Page limits tab compares each volume's page count (as Word "
                                       "last saved it) with the limit for that volume, matched by volume number or name, and all "
                                       "volumes together with a limit for the whole proposal. Open and save a file in Word if it "
                                       "has no page count yet."),
              ("Export", "Export (Excel) writes the requirements and their full history; Export all includes it.")]),
    ("img", "submission.png", 620),
    ("rows", [("Add", "Add customer documents... (or Add them... when new files appear in the customer documents folder) reads "
                      "each file and suggests what it is: a new version of a document already here, matched by name and by how "
                      "much of the text is the same, or a new document. You confirm or change each one. The same file twice is "
                      "skipped. Files are copied into the customer documents folder."),
              ("History", "Click a document to see its versions, newest first: when each arrived, who added it, the file, its "
                          "fingerprint (SHA-256) and what changed from the version before. A copy of each version's text is kept "
                          "in the effort's folder, so the history and Compare hold up even if a file is replaced or deleted."),
              ("Review", "A new version shows Not reviewed yet until someone clicks Mark reviewed, which records who and when. "
                         "The feature list shows how many changes wait for review."),
              ("Fix a match", "Rename a document or version, or Move to document... when a file belongs to another document's history.")]),
    ("img", "compare.png", 620),
    ("rows", [("Compare", "Pick a document and two versions (any two, not only neighbors). The two versions sit side by side, "
                          "lined up sentence by sentence: removed words are struck through in red on the left, added words are green "
                          "on the right. Amber rows touch submission requirements (format, page limits, due dates, files and copies)."),
              ("Filters", "Only changes (on at first) and Only submission requirements. Up and Down jump from change to change."),
              ("Exports", "Export redline (Word): the changes in reading order with both files' names, dates and fingerprints. "
                          "Export list (Excel): one row per change. Export > Version history (Excel): every document's versions "
                          "and a sheet of changes for each new version; Export all includes it."),
              ("Rules only", "No AI: the text is compared word by word. Nothing leaves this PC.")]),
    ("h", "Every sentence of the RFP, each with a decision and a home"),
    ("p", "Compliance > Read RFP > New from RFP files. Pick the instructions, evaluation criteria, SOW and attachments. Every "
          "sentence becomes a row, in reading order, with its file, page or section. Rules mark the ones that ask for "
          "something (shall, must, will, should, may, describe, provide, page limits, fonts, due dates) as requirements; "
          "every other sentence is a Context row, so nothing is skipped because it did not sound like a requirement. "
          "No AI writes anything."),
    ("p", "Text check (on Read RFP, and automatically after a read) proves that every piece of typed text reached the review. "
          "Each file is read again straight from its parts (body, tables, text boxes, headers, footers, footnotes, slides and "
          "speaker notes, cells, PDF pages) and compared word for word, in reading order, with the sentences in Assign. It "
          "lists anything not in the review and adds it for review in one click. Numbered headings show as section titles; an "
          "unnumbered capitalized line such as NOTE TO OFFERORS is also a sentence to assign. Text inside pictures is read "
          "by OCR (AI and ML) and is not part of this check."),
    ("img", "compliance.png", 620),
    ("rows", [("Assign", "The RFP reads like a page on the left; your response structure is always on the right (with no "
                         "structure yet, start it from the RFP headings there). Click any "
                         "sentence at any time to see how it is assigned and change it. Every choice counts at once and is "
                         "saved as you go (a crash or closing the app loses nothing); there is no commit step."),
              ("Compliance requirement", "R puts the sentence into a section. Click a section on the right to make it the "
                                         "target, then R for each sentence; with no target, R waits for you to click a "
                                         "section. 1, 2 and 3 pick the suggested sections (the rules' match and past "
                                         "proposals). The target section's sentences are underlined."),
              ("Context", "C makes the sentence Context for the nearest compliance requirement. To change that, click other "
                          "compliance requirements (green) to add or remove them, or click a section on the right to make it "
                          "context for that section or subsection itself. There is no Done step: clicking any other sentence, or "
                          "the next key, simply moves on. Pointing at a sentence lights up its links."),
              ("Clear, Split, Combine", "X clears a sentence (not used). S splits it where you clicked between two words. "
                                        "Drag across several sentences to assign them together, or M to combine them into one."),
              ("Not used", "A sentence you do not assign is not used. Prove and the coverage report count compliance "
                           "requirements, context and not used for every file, so you can see that every line was read."),
              ("The strip", "The thin strip beside the page maps the file: grey not used, green compliance requirement, blue "
                            "context. Click it to jump there."),
              ("In the outputs", "A compliance requirement goes in its section. Context for requirements prints under each "
                                 "requirement it supports, with \"Also context for\" naming the others; context for a section "
                                 "prints first in that section. The matrix's Context for column lists the requirements."),
              ("Setup board", "Arrange the setup... on the right opens the board for order, direction and references."),
              ("Prove", "The final check before export, as tiles to clear: Not used, unconfirmed; No section; Context not "
                        "attached; No owner; New in latest read; and All requirements. Click a tile to list those sentences with what to do: Open in Assign (or double-click), "
                        "Confirm not used, Mark checked, or set owner, status, response page and notes for several at once. "
                        "When nothing is left, Prove says ready to export. The coverage report is one button at the top."),
              ("People", "People... in Assign (or right-click a section) sets a lead and contributors for each section. "
                         "Requirements in a section and its subsections take its lead as owner unless they have their own. "
                         "The structure panel shows each lead; Show sections for lists one person's sections. The matrix's "
                         "Owner column and the Response Setup show the people."),
              ("References", "A sentence's reference is the RFP's own section number. For a file with no numbering, the app asks "
                             "once how to reference it: by the document name and paragraph (Design Note, para 3), name, page and "
                             "paragraph, or a prefix and number (SOW-3). Change it any time: How this file is referenced... in Assign."),
              ("Every line", "The count above the table says how many sentences are decided and shows a check mark when all "
                             "are. Filters show Context rows and Keep or Context rows that still need a home (no outline "
                             "section). Boilerplate and page headers are suggested Drop; Accept suggestions applies them."),
              ("Coverage report", "Coverage report... writes a Word file with every sentence of every RFP file in reading "
                                  "order, shaded by its decision (green Keep, blue Context, grey Drop, red undecided) and "
                                  "tagged with its ID and outline section. It opens with a table per file and a plain line "
                                  "saying whether every sentence has a decision: the proof that every line was considered. "
                                  "The workbook has the same table on its Coverage sheet."),
              ("Suggested", "Government statements are suggested Drop, 'may' is Review, offeror and contractor duties are Keep. "
                            "Accept suggestions applies them to the undecided rows shown; Review rows stay for you."),
              ("Split", "Click the sentence, then click between two of its words (or select the words to pull out) and press "
                        "S or Split: the sentence is cut there and each part becomes its own row with its own "
                        "decision and outline section. With no point chosen, S cuts where the rules see two requirements "
                        "('; ' or 'and shall'). Merge (M) joins rows back together."),
              ("Compliance words", "shall, must, will, should, may, required, not exceed, and order verbs such as describe or "
                                   "provide (at the start of a sentence or after shall) are bold, on screen and in the Excel "
                                   "matrix, Response Setup and coverage report. Compliance word style... (in the "
                                   "compliance window or the Compliance menu) adds italic, underline, a color or a highlight "
                                   "and edits the word list. Excel cannot highlight single words, so the matrix skips the highlight."),
              ("Type and actor", "Instruction (L), Evaluation (M), SOW (C), Format, Information; Offeror, Contractor or Government."),
              ("Links", "Evaluation and SOW items link to the instructions they concern, by section number or shared wording."),
              ("Outline", "Outline tab: start from the Section L headings, import a Word outline's headings, or type one. "
                          "Map kept rows to a section; Suggest sections fills only clear matches, then learns from rows you mapped."),
              ("Past proposals", "Every placed Keep and Context row teaches where the team puts sentences like it: their "
                                 "words linked to the words of the section title, its parent titles and the volume type, "
                                 "never section numbers, so it carries over to outlines numbered and titled differently. "
                                 "The detail pane shows the top 3 sections from past proposals (click one to map the row), or "
                                 "'no strong match'. Suggest sections uses a learned section only when it is a clear leader. "
                                 "Suggestions start after 30 placed rows; most help comes after 5 to 10 proposals. Older "
                                 "matrices count less (half after two years)."),
              ("Self-check", "Learn from decisions scores this matrix using only what the other matrices taught: how often "
                             "your section was in the top 3. The Outline tab shows the result and earlier checks, so you can "
                             "see whether it is getting better."),
              ("Synonyms", "Section word synonyms... (Outline tab) is the team's list of words that mean the same in "
                           "section titles, one group per line (solution, approach, methodology). It travels in Knowledge "
                           "Packs. Like the Keep and Drop learning, it stores numbered word buckets and counts, never RFP "
                           "or outline text."),
              ("Merge", "Select two or more rows and press M (or Merge) to join a requirement that the rules split."),
              ("Learned", "The app learns from your Keep and Drop decisions (Learn from decisions, and after every save). The Learned "
                          "column shows how likely the team is to keep a row; Accept suggestions uses it once it has enough decisions. "
                          "It stores numbered word buckets and counts, never RFP text, and travels in Knowledge Packs."),
              ("Source page", "Show page opens a PDF row's page with the sentence highlighted. Open file opens any source document."),
              ("Amendments", "Re-read RFP keeps decisions, mapping and notes for unchanged sentences. Amendment changes pairs changed "
                             "sentences and shows the word differences: [-removed-] {+added+}; export it to Excel."),
              ("Outputs", "The matrix is an Excel workbook (edits made in Excel count; type Keep, Context or Drop). Response "
                          "Setup (Word) holds every heading of the structure with who writes it, the RFP text it must answer "
                          "(context in blue) and the lead's direction; tick the option to add each section's requirement table "
                          "(reference, requirement, owner).")]),
    ("p", "The matrix holds customer content: keep it on this PC or SharePoint."),
    ("h", "Setup: the first draft for authors"),
    ("img", "setup.png", 620),
    ("p", "The setup board (Compliance > Assign > Arrange the setup...) puts the RFP text under the proposal outline and writes the setup documents: every heading of the "
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
              ("Report misreading", "The picture has real text but the reader got it wrong (RFF for RFP). Type the right "
                                    "reading: it is fixed now and saved as a lesson for the training team."),
              ("Not text", "The reader saw text where there is none: a line, arrow, logo edge or speck. The scanner ignores "
                           "that reading from now on and the spot is saved as a no-text lesson."),
              ("Exclude instance", "Only this place is wrong: the term stays in its other places. Saved for this effort. To "
                                   "exclude the term everywhere use Exclude in the bottom bar; for this effort only, Not a term."),
              ("Undo last save", "Takes back your last save in this panel.")]),
    ("p", "View > Preview pane turns this panel on or off."),
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
    ("rows", [("Knowledge Pack", "Advanced > Reading, training and knowledge > Knowledge.... The training team ships the reader, database, OCR fixes and "
                                 "ignore list in one numbered file. Install it; Undo puts the previous one back."),
              ("Corrections", "Advanced > Reading, training and knowledge > Send corrections to the training team. Your lessons for the training team, in one file."),
              ("Where", "Your approved local SharePoint folder only. Never GitHub, email or USB."),
              ("Client Lists", "Load the client's own acronym list (a file, a picture of one, or Paste or type...), then "
                               "confirm the terms found. Its definitions win over the database."),
              ("Projects", "Project > Save. A rescan reads only files that changed."),
              ("Full Text", "Advanced > Reading, training and knowledge > Full Text. All typed and picture text, saved as .txt.")]),
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
    ("p", "Next to each feature's name, the step strip shows what runs it. Click its ? to see each part and its job. Everything runs on this PC, "
          "with no network."),
    ("table", [["Label", "Meaning", "Examples"],
               ["No AI", "Fixed rules, counting and file reading. Same input, same output.", "Typed text, Effort list, volume check, compliance rules"],
               ["ML", "A trained model that recognizes or scores. Outputs letters, boxes or numbers, never sentences.",
                "Text in pictures (Tesseract, docTR), learned compliance suggestions, Improve Reading"],
               ["Gen AI", "A model that writes text. Separate add-on, runs in the no-network sandbox.", "Math reader add-on"]]),
    ("img", "stack.png", 380),
    ("h", "The AI and ML switch"),
    ("rows", [("Where", "Top right of the window. The ? next to it explains AI vs ML."),
              ("Per effort", "Each effort keeps its own setting. New efforts start with AI and ML on."),
              ("Off", "Every ML and Gen AI part stops: the model code refuses to run, and its buttons grey out. Typed text in "
                      "Word, PowerPoint, Excel and PDFs is still read. Text inside pictures and scanned pages is not."),
              ("Logged", "Each change goes into the effort list's History sheet (date, Windows user, setting) and the usage "
                         "log (the effort appears as a number, never its name)."),
              ("Team learning", "Compliance > Prove. Off: this effort's decisions are not learned and the Learned column "
                                "stays empty. AI and ML off turns it off too.")]),
    ("h", "For your security team"),
    ("p", "Help > What runs where lists every part and saves a one-page summary to hand to reviewers. The line at the "
          "bottom of the window always shows the effort and whether AI and ML are on."),
    ("img", "whatruns.png", 520),
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
