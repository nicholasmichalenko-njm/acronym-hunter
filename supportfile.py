"""Help without sending data (2.81.0): the support file, the safe start and what's new.

Support file: one zip for whoever maintains Stationkeeper, made by the person and sent by the person. It holds versions
(the app, Python, Qt, Windows), the content-free logs (events and activity: fixed messages, code locations, counts),
the counts from Check program files, the effort health problems by kind, and which settings are switched on. It holds
no document text, terms, names, file names or folder paths: every value is checked before it goes in, and anything that
looks like a path, an e-mail address or a name is left out.

Safe start: each start is counted until the window has been up for a few seconds; after two starts in a row that did
not get that far, the next one opens without the last effort, and says why.

What's new: after an update, one card lists what changed in this version.
Standard library only; nothing leaves the PC except the zip the person saves.
"""
import datetime, json, os, platform, re, sys, zipfile

START_FILE = "start_state.json"
SAFE_AFTER = 2
_PATHLIKE = re.compile(r"([A-Za-z]:[\\/])|(\\\\)|(/[^ ]+/)|(@[A-Za-z0-9.-]+\.)")
_SETTINGS_KEEP = {"work_mode", "advanced", "usage_logging", "ocr_sandbox_required", "theme", "text_size"}

WHATS_NEW = {
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
               "global standards, for every volume or one, with the RFP's rules beside each value.",
               "Make it global sends an effort's value to the global standards (with Undo). Production Standards now edits "
               "the global standards only; Every setting opens it on the effort."],
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
              "on the page); with either one blank, headers and footers are left as they are. The global standards hold no "
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
    "2.99.0": ["More captures in Assign: evaluation factors with their importance, page limits, deliverables, effort details "
               "(NAICS, contract type, set-aside...) and hot buttons. Effort Home shows Evaluation and hot buttons.",
               "Tasks and team questions on a sentence, shown on its card and in the effort record.",
               "The Compliance pages sit right under Effort in the menu."],
    "2.98.0": ["Customer Q&A: the questions you submit to the customer, quoting their exact wording and where it is, with "
               "status and answers; Capture > Question in Assign; export to Word, Excel or the customer's own template.",
               "Capture > Key date puts questions due, site visits, orals and award on the calendar with their time zone.",
               "Adding an amendment says at once what it changed; Assign outlines the changed and new sentences, shows what "
               "each was, and opens the old page at the same spot."],
    "2.97.0": ["Three work modes: Offline (testing and everyday work, General business to CUI), Connected (SharePoint) and "
               "SCIF-ready (no logs, no training, no support files, locked once chosen). The chip in the top bar shows it.",
               "A document marked above CUI (by its sensitivity label or its banners and markings) stops Add documents, the "
               "Library and Read RFP on a regular install, with nothing copied.",
               "Training only takes work from efforts whose sensitivity is known and at most CUI; the Trainer refuses files "
               "marked above CUI and asks the level of an unmarked one."],
    "2.96.0": ["Every kind of customer file: pictures and scanned pages get their words laid over them so you select "
               "sentences exactly as on a typed PDF; old .doc, .xls and .ppt files are read; Excel opens in Sheet view (its "
               "cells as a grid).",
               "Assign: L (Instructions), M (Evaluation) and SOW (Work); drag across words to pick them; Capture files a "
               "contact, submission instructions (a due date can become the effort's), formatting rules or an acronym, each "
               "with where it came from. Effort Home has a Submission instructions card and contact cards.",
               "The documents as a queue: Document 2 of 5, Mark reviewed, Next document."],
    "2.95.0": ["Settings > Folders and file names: your effort folder tree as you keep it on SharePoint (fields like "
               "{Solicitation} in folder names), the folder each thing the app makes goes to, and its name pattern, with a "
               "sample of the exact path. New efforts get the whole tree; existing folders are never renamed or moved.",
               "Dates and spaces in names as your team writes them, your company's name for {Company}, and {Version} counting "
               "up. The effort list and its app data can sit in a folder of your tree. A team pack can carry and lock it all."],
    "2.94.0": ["Effort Home shows whether the effort is page-limited, front and center (PAGE-LIMITED: 50 pages, or Not "
               "page-limited when you say so in Edit details), and a Formatting requirements card: each rule required (what and "
               "where) or not specified.",
               "Settings > Document types: your own types with their initials; picking a type fills in the initial when "
               "adding customer documents.",
               "Watched folders: Customer Documents (and any folder you add, subfolders too) is checked for new, changed and "
               "missing files. A strip says what was found: Add them..., Not these, or Review missing... (find it, keep the "
               "record without it, or mark it withdrawn)."],
    "2.93.0": ["Settings > Stages, gates and roles: your team's default stages, gate choices (rename the built-in ones, add "
               "your own with what each does and means) and the roles offered for people on an effort. A team pack can carry them.",
               "Stage tables: pick a stage's start and end from a calendar, with an optional time; the Stage column is readable.",
               "Gate goals and tasks take a deadline (date and time) and an owner, accepted only inside the stage's dates; "
               "the app says the stage's dates when one falls outside.",
               "People and roles: a role drop-down per person (Effort Record, and People and roles... on Effort Home) that "
               "saves when you pick.",
               "Split in Assign shows on the page: a red line where it splits, the second part tinted, Split here and Cancel "
               "beside it, and both parts in the card."],
    "2.92.0": ["Time zones: yours in Settings, the submission's with the effort. Effort Home shows the deadline in both and the "
               "countdown is right across zones.",
               "Calendar: + Due date and + Event, with times, end times, zones, owners and places; your time shows beside theirs.",
               "The readable copy is kept current again: everything in the effort as Excel, Word, CSV and Outlook files.",
               "Export overview (Effort Home): your summary first, people's progress, newest documents, what is coming up.",
               "Export tasks and questions for one person or the full team; a picked person's name shows large. Edit stages "
               "on Effort Home; the due date in Effort Record needs no hidden switch."],
    "2.91.0": ["Home (All Efforts) shows every effort as a card: stage, days to due, open tasks and questions, who has it "
               "open. + Add an Effort is the way to start one.",
               "Start without an effort: Unfiled works with every tool. A strip reminds you to file the work; Make it an "
               "effort or Add to an effort files it.",
               "Post-Submission: a checklist with owners and due dates after submission, your own items, a default for new "
               "efforts and a formatted Excel export."],
    "2.90.0": ["The program folder holds Stationkeeper.exe, _internal and About Stationkeeper (the read-me files). No "
               "empty database or settings ship; Stationkeeper makes them in Stationkeeper Data.",
               "A new effort gets Customer Documents, Volumes, Response Setup and Exports folders, and saves start there.",
               "Open effort folder (Effort Home, Settings) shows the effort's folder in File Explorer."],
    "2.89.0": ["Team defaults (Settings): one file sets up every PC the same way: the author list, matrix design, banned "
               "words, default gate goals, company logos, Effort Home layouts by role, sensitivity markings and team topics.",
               "Installing adds what a PC lacks and keeps its own. Parts the team locks replace each PC's own and stay as the "
               "team set them. Undo puts everything back.",
               "Customize Home can save your layout as the team's layout for a role. Team topics are one-click tags when "
               "you take context from a library document."],
    "2.88.0": ["Effort Home opens with the effort's banner: its picture, name, client, solicitation, proposal manager, "
               "sensitivity and your own spots, with the due date and a live countdown. They travel with the effort.",
               "A CUI or proprietary effort shows its marking in a strip across the top of every page.",
               "Your company logos sit at the top of the menu (Settings > Branding); the Stationkeeper mark is at its foot. "
               "The menu and page names are in Title Case.",
               "Customize Home: pick your role (Proposal Manager, Production, Author, Reviewer, Capture) and show, hide and "
               "order the sections. It is yours alone, on this PC. Authors get My work.",
               "Calendar: Template... for people to fill in, Import... with a preview (the due date to the minute, stage "
               "dates, tasks, reviews and meetings), Undo import, and Export... to Excel or Outlook (.ics)."],
    "2.87.0": ["Deliverables moved up with the effort, right after Effort home, and opens as a board: one card per "
               "deliverable, the ones that need action first.",
               "Each card shows its owner, status, pages against the limit, the volume it holds in the response structure, "
               "its requirements and how many have an author, and what is missing.",
               "Click a card to see its requirements (double-click one to open it in Assign), what a customer version "
               "changed, its submission check, its library context and its files.",
               "A Volume deliverable links to its volume by name; pick another volume on the card to change it.",
               "Effort home and the dashboard say how the deliverables stand. The table is still there under View: List.",
               "Author list: Edit which efforts... With All efforts ticked every effort shows ticked; nothing changes until OK."],
    "2.86.0": ["Response quality: Customer terms (start), Effort list (the glossary), Submission check and Lists to submit "
               "(end), in one group; each page says which end it serves.",
               "Customer terms scans the Library's customer documents with one button. Submission volumes are marked once.",
               "Lists to submit holds only the terms each volume uses: one per volume, a master list, or both. Terms no "
               "volume uses are left out and listed, and the effort list can show them.",
               "A term's card shows where it was found, zoomed in. Plurals are marked Plural of ... and stay found.",
               "Click a gate goal to change, remove or tick it by hand. Button rows wrap and tables resize and scroll."],
    "2.85.0": ["Changes: Compare, Impact review and the requirements review are one page. A summary says what the new version "
               "touches; each change shows side by side in its place and gets a decision.",
               "Submission rules (was Requirements) shows what the customer requires now, with Was and Now in the row for "
               "anything a version changed.",
               "A requirement a version changed keeps its old wording and waits for its owner to confirm. Customer versions now "
               "lives in Library.",
               "The mouse wheel scrolls the page; it no longer changes a drop-down, number or date it passes over."],
    "2.84.0": ["Read and assign any document: library documents that do not build the matrix open in Assign beside the "
               "response structure (File list: Library: ...). Select text, then choose where it goes: context for a "
               "section (C), for a requirement (F), a note (N), a question (Q), a task (T), or make it a requirement (R).",
               "Context shows on the structure (Ctx column), on a requirement's card, and in Response Setup under its section.",
               "Library > Taken from documents lists everything taken, filters it by kind, document and topic, and exports it.",
               "Every start, after an update too, reopens the effort you last had open. Assign: Not used is now Ignore."],
    "2.83.0": ["Library: every document of the effort in one place: customer documents, the bidders library, Q&A, our "
               "documents and categories of your own, with folders, tags and search across the text of every document.",
               "Add a folder (or drag folders and files onto the Library): every document comes in with a progress bar, its "
               "category suggested from its folders and its folder names as tags, all checked in one table first.",
               "Every document has a role: Builds the matrix, Context, Reference only or Not needed, kept with who, when "
               "and why. Read RFP ticks the documents that build the matrix.",
               "Save effort package: all documents, or the customer documents and Q&A only; the package still carries "
               "every document's record and text."],
    "2.82.0": ["Moving between pages is fast with many documents: version changes and submission requirements are worked "
               "out once, in the background, and kept until something changes.",
               "Read shows its progress: the file and page, a running clock, Stop, and a clear message if a file cannot be "
               "read. Read is locked while it runs, so there is never a second read or a second matrix.",
               "Read RFP: tick all, tick selected, or tick one type; select several rows with Shift or Ctrl.",
               "After an update the new version shows each step while it reopens your work, so a pause never looks "
               "like lost work.",
               "Assign: the decision buttons (Requirement, L, M, Support, Customer's, Not used) sit beside the response "
               "structure, under the section they put sentences into."],
    "2.81.0": ["Help and support in Settings: create a support file (no document content), the keyboard shortcuts, and this card.",
               "Ctrl+K searches pages, efforts, sentences and people from anywhere.",
               "After two starts in a row that did not finish, Stationkeeper opens without the last effort and says why."],
    "2.80.0": ["Your data lives in 'Stationkeeper Data' beside the program folder; updates never touch it.",
               "Effort health is checked when an effort opens; a damaged list or matrix is put back from its newest good copy.",
               "Stationkeeper asks before overwriting a matrix another copy saved, and waits out OneDrive holding a file."],
    "2.79.0": ["Work modes: Secured (SCIF or closed network) or Connected (OneDrive team folder). Offline in both.",
               "Packages open where the sender was, with the same names, and say which copy is newer."],
    "2.78.0": ["Automatic backups, a recovery copy after a crash, Effort record > Restore, and each effort reopens where you were."],
    "2.77.0": ["One author list in Settings for every name, with the efforts each name shows in."],
    "2.76.0": ["Update packs: install once, then update with one signed file."],
}


def vt(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


# ---------------------------------------------------------------- safe start
def _start_path(folder):
    return os.path.join(folder, START_FILE)


def begin(folder):
    """Count this start. Returns True when this start should be safe (the last two never finished starting)."""
    p = _start_path(folder)
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    pending = int(d.get("pending", 0) or 0)
    safe = pending >= SAFE_AFTER
    try:
        os.makedirs(folder, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"pending": pending + 1, "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
    except OSError:
        pass
    return safe


def started(folder):
    """The window has been up for a few seconds: this start counts as good."""
    try:
        with open(_start_path(folder), "w", encoding="utf-8") as f:
            json.dump({"pending": 0, "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
    except OSError:
        pass


# ---------------------------------------------------------------- what's new
def whats_new(last, current):
    """The notes for the versions after last up to current, newest first ([] when nothing new or a first start)."""
    if not last or vt(last) >= vt(current):
        return []
    out = []
    for v in sorted(WHATS_NEW, key=vt, reverse=True):
        if vt(last) < vt(v) <= vt(current):
            out.append((v, WHATS_NEW[v]))
    return out


# ---------------------------------------------------------------- the support file
def _clean(v):
    """A value that may go in: numbers, booleans, short words without paths, names or addresses; else None."""
    if isinstance(v, bool) or isinstance(v, (int, float)) or v is None:
        return v
    if isinstance(v, str) and len(v) <= 60 and not _PATHLIKE.search(v):
        return v
    return None


def _scrub_line(line):
    """A log line kept only when every string value in it is clean (the logs are content-free by design; this checks)."""
    try:
        d = json.loads(line)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    out = {}
    for k, v in d.items():
        if isinstance(v, list):
            v = [x for x in (_clean(i) if not isinstance(i, (list, dict)) else None for i in v) if x is not None]
            out[k] = v
            continue
        if isinstance(v, dict):
            continue
        c = _clean(v)
        if c is not None or v is None:
            out[k] = c
    return json.dumps(out, ensure_ascii=True)


def make(out_path, app_version, log_dir, settings=None, program_check=None, health=None, data_why="", qt_version="", extra=None):
    """Write the support file. Returns {"path", "files"} (the names inside). extra (3.30.0): {name: dict} more files of
    content-free values (problem.json: the error at the moment it happened)."""
    info = {"app_version": app_version, "python": platform.python_version(), "qt": qt_version or "",
            "windows": platform.release() + " " + platform.version() if sys.platform == "win32" else platform.platform(terse=True),
            "made": datetime.datetime.now().isoformat(timespec="minutes"), "data_location": data_why or "",
            "settings_on": sorted(k for k, v in (settings or {}).items() if k in _SETTINGS_KEEP and v not in (None, "", False)),
            "work_mode": (settings or {}).get("work_mode", "") if (settings or {}).get("work_mode", "") in ("secured", "connected") else "",
            "backups_on": bool((settings or {}).get("backup_dir")),
            "health": sorted({i.get("kind", "") for i in (health or []) if _clean(i.get("kind", ""))})}
    if program_check is not None:
        info["program_files"] = {"version": _clean(program_check.get("version", "")), "ok": program_check.get("ok", 0),
                                 "changed": len(program_check.get("changed", [])), "missing": len(program_check.get("missing", [])),
                                 "extra": len(program_check.get("extra", []))}
    files = ["about.json"]
    tmp = out_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("about.json", json.dumps(info, indent=1))
        for name in ("events.jsonl", "activity.jsonl"):
            p = os.path.join(log_dir or "", name)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    lines = [x for x in (_scrub_line(l) for l in f.readlines()[-5000:]) if x]
                z.writestr("logs/" + name, "\n".join(lines) + "\n")
                files.append("logs/" + name)
        for name, val in (extra or {}).items():       # 3.30.0: every value cleaned the same way as the logs
            clean = {k: (_clean(v) if not isinstance(v, list) else [x for x in (_clean(i) for i in v) if x is not None])
                     for k, v in (val or {}).items()}
            z.writestr(name, json.dumps(clean, indent=1))
            files.append(name)
        z.writestr("READ ME.txt", "Stationkeeper support file\r\n\r\nVersions, content-free logs and checks, for whoever maintains "
                                  "Stationkeeper. It holds no document text, terms, names, file names or folder paths.\r\n")
        files.append("READ ME.txt")
    os.replace(tmp, out_path)
    return {"path": out_path, "files": files}
