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
    "3.50.0": ["Where an acronym was found is shown again: the picture or page with every find boxed, or the passage highlighted. Acronym Finder opens in its own window (its button at the foot of the menu): scan any files, export the list, check first use. First Use Check checks any Word file on its own. Symbols are back beside every definition box: Greek, subscripts, superscripts, math, accents and units.",
               "Production > Quick Parts and Layout: every Quick Part by its category with the pages it fills, and covers, headers and footers, sections, table looks, captions and the TOC, each with its picture and every value. Draw with Word shows items as they will print."],
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
