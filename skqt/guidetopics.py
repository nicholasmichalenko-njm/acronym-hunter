"""The Guide's topics, in the menu's order (3.53.0: kept apart from guide.py so each stays under 800 lines).
Each: (key, menu group, title, what it is, when to use it, steps, tips). Text only."""
TOPICS = [
 ("start", "Getting started", "What Stationkeeper does",
  "Stationkeeper runs a proposal effort from the customer's first file to the submitted proposal: it reads the "
  "customer's documents, helps the team decide every requirement, and makes the matrix, the setup documents, the "
  "acronym lists and the submission checks. Everything stays on this PC.",
  "You are new to Stationkeeper, or want the big picture.",
  ["Open the menu on the left. Its groups are by job: Effort, Solicitation (the RFP, its changes and our questions about it), Compliance, Writing, Quality, "
   "Production, Post-Submission and Effort files. A tool with several pages shows them as tabs under its title (Review: "
   "Review, Structure, Coverage). Each tool is in one place. Click a group's name to fold it away. The open effort and "
   "its stage are at the top; a dot in the stage's color marks the tools this stage needs, and each group says how many "
   "it holds.",
   "Your role decides which tools open. A greyed tool is for another role: open it to see who it is for and how to get "
   "it. Settings > Roles and Preview tools can hide them.",
   "Start an effort on All Efforts, or open one you already have.",
   "Add the customer's documents in Library, then Read it into Review: decide every sentence and build the structure beside the page.",
   "Make the matrix and the Response Setup documents from your decisions, then check the volumes in Response Quality."],
  ["Press F1 on any page to open this Guide at that page.",
   "Press Ctrl+K to find a page, an effort, a sentence or a person from anywhere.",
   "Every decision saves as you make it. Closing the app never loses work."]),
 ("tools", "Home", "Your Tools",
  "The first screen: drop any file and pick what to do with it, your pinned tools, the files you opened from here, and your "
  "efforts and Unfiled.",
  "Whenever you start: a quick job on any document, or the effort you are working on.",
  ["Drop a file on the dashed box, or Choose files...: Stationkeeper lists the tools that take it (find acronyms, check first "
   "use, pull out all the text, add to the Library, audit). Pick one.",
   "Paste a picture: a screenshot or a copied figure, read in Acronym Finder.",
   "Pinned tools: one click each. Edit pins... picks them; your role's starting set is only a start.",
   "Recent files: double-click to open one again with any tool. Your efforts: double-click to work on one, or Unfiled."],
  ["Working on (top right) says what every space works on: an effort, or Unfiled (loose work kept until you file it).",
   "Ctrl+K finds any page, effort, sentence or person."]),
 ("mywork", "Home", "My Work",
  "One person's work in every effort on this PC, soonest first: tasks, questions for them, customer questions, "
  "deliverables and graphic needs they own, the requirements they answer, and the sections they lead with page budgets.",
  "Every morning, and when you work on several efforts at once.",
  ["Pick a name in Work for (yours shows first once Customize... > I am is set on the Effort Dashboard).",
   "Read Soonest first: late items are red and on top; requirements are due when the current stage ends.",
   "Double-click a row to open that effort at the right page. By effort shows each effort's stage, due date and sections.",
   "Export... makes a workbook of the list for a status meeting.",
   "3.46.0: the data calls you owe (with their code), and your sections whose newest Draft Status read says Not started or "
   "Over budget, or that requirements were removed. By effort shows each section's draft status."],
  ["My Work only reads the efforts; nothing changes until you open one.",
   "Refresh reads every effort again after teammates' changes come in."]),
 ("efforts", "Home", "All Efforts",
  "Every effort on this PC, a new one, and work not filed under an effort yet.",
  "You start a new proposal, switch efforts, or pick up an effort a teammate handed you.",
  ["Press + Add an Effort (or open the Effort Dashboard with no effort open). Type a name and press Create effort. The picture, "
   "client, solicitation, due date and proposal manager are optional; the effort's folders are made for you.",
   "Click an effort's card to open it. The menu then works on that effort.",
   "To pick up a teammate's effort, press Import effort package... and choose the .skpkg file they sent. An effort folder moved or copied: Open an effort from its folder... (pick the folder, its Effort List or its Open this effort.skeffort file). Right-click an effort: Archive... (Show archived restores it) or Add to this effort... to merge another copy of it.",
   "To read documents before an effort exists, press Start without an effort: open Unfiled. Make it an effort... later "
   "keeps the work."],
  ["Each effort keeps its own decisions, lists and settings. Nothing crosses between efforts.",
   "The card shows the stage, the due date and what needs attention."]),
 ("home", "Effort", "Effort Dashboard",
  "Where the effort stands, on one page: the numbers on top, the stage and its gate, submission requirements, gate "
  "goals, tasks, questions, the calendar, deliverables, compliance coverage, who has what, and the timeline. The header "
  "stays at the top while the cards scroll.",
  "Every day: see what is due and what is behind, add tasks and questions, and move the effort to its next stage.",
  ["Read the header: the stage with its gate and how many goals are open (click it for the goals), sensitivity, the "
   "countdown to the customer's due date in your time zone and the submission's. Condense keeps only the essentials.",
   "Win themes and Wall of Truth in the header show them under it on every stage; Hide or the button again folds them "
   "away. Your choice is kept for this effort.",
   "Read the numbers on top. Click one to go where the work is.",
   "Submission requirements: How and when, Formatting and Page limits, each with where it came from. Click one to open "
   "it in Submission Rules; Edit changes what it says.",
   "Add work with + Task, + Question, + Note or + Goal. Each card's Export... is on the card.",
   "Schedule from due date... dates every stage backward from the due date, skipping weekends and your holidays.",
   "When the team is ready, press Move stage... It lists what is not done, with owners. Ticked goals carry into the next "
   "stage, marked as carried, and count at its gate. A hard gate holds the move; only the proposal manager can override "
   "it, with a reason. Every move is in the timeline."],
  ["Click the effort image, or drop a picture file on it, to set or change it.",
   "Customize... picks which cards show, their order (drag them) and full or half width.",
   "Each stage has a color: the header's top line, the stage pill and the current stage on the track show it.",
   "Export overview... writes one Word file each time: due dates and your summary first. All overviews... lists every "
   "one with its stage and summary, and opens its file.",
   "New files in the watched folders show in a strip under the top bar: Review opens them in the Library; Ignore stops "
   "offering them until they change.",
   "Graphic needs lists what was tagged as needing a graphic; Export... makes a workbook for the graphics team."]),
 ("requirements", "Effort", "Submission Rules",
  "The Effort Dashboard's second tab. What the customer requires of the submission: due date, delivery, copies, formats, file names, page limits and "
  "formatting, with the document that set each rule and what changed it.",
  "You plan the submission, or a new version changes a rule.",
  ["Read the rules. Each shows its source document and section.",
   "Press Add a requirement... for a rule you found yourself.",
   "Use the new due date takes a changed due date into the effort."],
  ["Capture > Submission and Capture > Formatting in Review fill this page from the customer's words."]),
 ("deliverables", "Effort", "Deliverables",
  "Every deliverable of the effort on one board: volumes, forms, plans and CDRLs, with owner, status, pages against "
  "the limit and what is missing.",
  "You track what has to be turned in and who owns each piece.",
  ["Press + Deliverable... to add one, or capture one from a sentence in Review (More captures).",
   "Click a card to see its requirements, what a new customer version changed, its submission check and its files.",
   "Double-click a card (or a row in the list) to open the deliverable's own page: Overview (type, status, owner, due "
   "date, what it is, its guidelines), Format and submission, Parts and people, Requirements, Attachments and files, "
   "Discussion and Dates. < All deliverables goes back.",
   "Format groups...: set the formatting and submission once for deliverables of the same kind; type a value on a "
   "deliverable's page to set its own, clear it to use the group's again.",
   "A volume deliverable is its Structure volume: Make it a Structure volume adds it to Setup, and its "
   "sections, with their leads from Setup, are its parts. Any deliverable can have parts of its own.",
   "Discussion: dated notes with the writer's name; filter by person; pin the ones everyone needs. Each note is also in "
   "the effort's timeline. A deliverable's due date and its own dates show on the calendar.",
   "Double-click a requirement to open it in Review."],
  ["View: List shows the same deliverables as a table; Arrange: drag them into the team's order, and set the board to "
   "Your order to follow it.",
   "Every name picker ends with Add a person...: add someone once and every picker offers them after."]),
 ("evalcrit", "Shred", "Evaluation Criteria",
  "How the customer will judge the proposal: the evaluation factors and subfactors with their relative importance, and "
  "the deliverables each one judges.",
  "Right after the RFP is read, and whenever you decide what a section must prove.",
  ["Factors captured in Review (More captures > Evaluation factor) show here; Add puts one in by hand, as a factor or "
   "under one.",
   "Deliverables it judges... ties a factor to the deliverables it scores; the Effort Dashboard's Evaluation criteria "
   "card and All Efforts show them.",
   "Evaluation sentences in Review (Section M) are listed below: Make it a factor reads the factor's name and importance "
   "from the customer's words; Open in Review shows the sentence in place."],
  ["Set importance changes a factor's relative importance (Significantly more important to Pass/fail)."]),
 ("effortfmt", "Effort", "Effort Formatting",
  "This effort's formatting on top of the global standards: the values efforts change most up front, each with the "
  "global value, what the RFP says and Reset; every other setting in the full editor, on this effort only.",
  "An effort needs its own fonts, sizes, margins or header text, or the RFP sets formatting rules.",
  ["Changes apply to: Every volume, or one volume of the effort.",
   "Set a value, or press Use it beside what the RFP says. A value that breaks the RFP's rule shows in red.",
   "Make it global writes this effort's value into the global standard, a volume profile or the effort type; Undo the "
   "last Make it global puts it back.",
   "Every setting... opens Production Standards on this effort (an amber band says so); Back to Effort Formatting returns.",
   "Footer, the team's line (Rule 7) sets the line under the marking in every Rule 7 footer of this effort. Field, beside "
   "each header and footer box, puts a field (page number, A number, volume values, your fields) where the cursor is."],
  ["Library parts this effort uses lists each part's source: the global version, a version this effort chose, or its own copy.",
   "Production Standards itself edits only the global standards."]),
 ("record", "Effort", "Effort Record",
  "The effort's details, team and roles, stages and gates, status reports, the effort package and backups.",
  "You set up the effort, change its team or stages, hand it to someone, or report status.",
  ["Fill in the details and press Save details. Choose people... adds the team from the author list.",
   "Edit the stages and press Save stages. + Stage adds one; Up and Down reorder them.",
   "Effort status (Word)... and Effort summary (Word)... make reports for a meeting.",
   "Save effort package... makes one .skpkg file with everything, for a teammate or a backup."],
  ["Back up now makes a backup at once. Restore... brings one back.",
   "Open the readable copy shows every captured item as plain files you can open without the app. Settings > Efforts > "
   "Export the full effort... copies it into a dated folder named for the effort and its stage."]),
 ("meetings", "Effort", "Meetings",
  "Meetings for this effort: who was there, the notes, and the topics to follow up, each open until someone marks it "
  "considered.",
  "After a kickoff, a color team debrief, a customer call or a working session: anything said that must reach the response.",
  ["+ Meeting: give it a name, then set the date and time, the participants (Choose...) and the notes.",
   "+ Topic adds a topic: what it is, what it points at (a section of the structure or a requirement) and its owner. Topics "
   "from notes offers the notes' lines that start with -, * or Topic:, Action:, Decision: for you to tick.",
   "When a topic has been taken into account, select it and press Considered (who and when are kept). Not needed asks why.",
   "Select words in the notes and press Make a topic of the selection (or right-click): the topic box opens with them.",
   "Export to Word... saves the meeting, its notes and topics."],
  ["Open topics show on the Effort Dashboard, in My Work for their owner, and on the card of the sentence or section they "
   "point at in Review.",
   "A stage gate can hold until every topic is considered: add the goal Every meeting topic considered in Effort Record."]),
 ("library", "Effort Library", "Library",
  "Every document of the effort: customer files and every version of them, categories, folders, tags and roles.",
  "Documents arrive: the RFP, amendments, Q&A rounds, forms, task orders.",
  ["Press Add files... or Add a folder... Stationkeeper suggests the type, its initial (R, A1, TO1) and whether it is "
   "a new version of a document you have.",
   "Watched folders... checks the customer folder and any folder you add for new, changed and missing files. New files "
   "show at the top of the Library: Add to the Library... or Ignore. The same words are never added twice.",
   "The Review column says where each document stands: Not read yet, Needs reviewing (how many sentences are decided), "
   "or Reviewed. Select one and press its button: Read it into Review, Continue reviewing or Open in Review. Select "
   "several unread ones to read them together.",
   "For an amendment that says what to change, press Apply its instructions... to make the Conformed version."],
  ["Initial and type... and Rename... fix a document's details. The customer's files are never changed.",
   "A document marked above CUI is refused on a regular install. Follow your site's spill procedure."]),
 ("read", "Effort Library", "Read into Review",
  "The Library's second tab: several customer documents read into the compliance matrix at once. Every sentence is cut "
  "out of the page, scans and pictures are read with OCR, and nothing is dropped.",
  "A new solicitation arrives with many files, or you add files that are not in the Library yet.",
  ["Tick the documents (or press Add files...).",
   "Press Read. The progress panel shows each file and page; Review opens when it is done.",
   "One document at a time is simpler from the Documents tab: Read it into Review."],
  ["Scanned pages and pictures are read by the OCR reader (AI and ML), on this PC.",
   "Every read runs the text check: Coverage (in Review) shows it file by file."]),
 ("custqa", "Effort Library", "Customer Q&A",
  "The formal questions you submit to the customer: their exact words and where they are, your question, its status "
  "and the answer.",
  "Before the questions-due date, and when the answers come back.",
  ["In Review, select a sentence (or drag across words) and use Capture > Question. It quotes the customer and the "
   "place for you.",
   "Here, edit the question, its category and owner, and move it from Draft to Approved.",
   "Export to Word or Excel, or fill the customer's own Q&A form. Exporting can mark the questions Submitted.",
   "When answers arrive, add each answer and the document it came in."],
  ["Every exported question names the customer file it is about. Owner, status and notes never go out."]),
 ("datacalls", "Effort Library", "Data calls",
  "What the team needs from its own experts, asked so it gets answered: what is needed, the section or requirement it "
  "serves, how much (word-count guidance), an example of a good answer, the owner and the due date.",
  "When a section needs facts, numbers or a story only an expert has: past performance, staffing, technical detail.",
  ["+ Data call: say what you need, choose the section, add the requirement, how much and an example, then the owner and due date.",
   "Send Word files... writes one Word file per person with their open calls (they become Sent). Each call has a code (DC-1...).",
   "The person types in each Your answer box and sends the file back. Read answers... puts each answer back on its call.",
   "Place in the section puts an answer into the response structure as context: the section's author sees it in the setup, "
   "the kickoff packet and Everything for this section."],
  ["Show: Overdue lists calls past their due date with no answer. The Author drafts gate can hold until every call is answered."]),
 ("shredreq", "Shred", "Requirements",
  "Every requirement in one file, with no matrix to set up: an RFP, a draft RFP or a statement of work. Each one labelled "
  "Requirement, Instruction (L), Evaluation (M) or SOW task, with its section, page and the words that make it one.",
  "The day an RFP or draft RFP drops, before any effort exists; or any time you need a quick list.",
  ["Choose a file... (or drop it on Your Tools and pick Find the requirements).",
   "Filter by kind. Select a row: the sentence with its words in bold, and where it is.",
   "Export the matrix...: a draft compliance matrix in Excel, one row per requirement.",
   "File to an effort...: reads the file into that effort's Review, where each requirement gets its decision."],
  ["The same reader as Review; nothing is kept until you file it to an effort."]),
 ("assign", "Shred", "Review",
  "The customer's document as it looks, every sentence boxed. You decide each sentence, place it in your response, "
  "and capture what it holds. This is where an effort's review happens.",
  "From the first read until every sentence is decided, and again when a new version arrives.",
  ["Click a sentence. Press L (Instructions), E (M, Evaluation) or R (SOW, Work) to make it a requirement in the "
   "target section; C for context that supports the last requirement; G for the customer's own sentence; X to clear.",
   "Drag across words to pick just those words, inside one sentence or across several (3.28.1: whatever was selected "
   "before). Extract (Shift+S) makes them a sentence of their own; picked across sentences, they become one sentence, "
   "split from where they were. Rename (by the Volume box) renames the volume you work in; the box beside it numbers "
   "the volumes I, II, III; 1, 2, 3; or A, B, C. "
   "Split (S) splits at a clicked word, or asks exactly where. Capture files them: a contact, submission or "
   "formatting rule, acronym, key date or customer question. More captures... adds evaluation factors, page limits, "
   "deliverables, effort details and hot buttons.",
   "Captures (3.29.0: bins are captures now): one bar. Objective (O), Key point (K) and every capture put the picked words "
   "in it, verbatim with where they sit; Ctrl+click sentences far apart for one excerpt. A sentence keeps one decision "
   "and can be captured any number of times; its card lists them. More... (B) holds the rest, + Capture... (your own, "
   "Alt+1 to Alt+9) and Captures of this effort. Captured list (its own button) shows everything captured.",
   "Settings > Review: decisions and captures sets every decision's and capture's name, key, color and showing, which "
   "decisions each effort type hides (an RFI shows Interest instead of L, M and SOW), and the team's own captures.",
   "Topics (3.28.0): the bar over the page. + Topic, or Topics > from the RFP's headings. Sort mode (Ctrl+T): keys 1 to 9 "
   "put the selected sentences in the first nine topics (again takes it off); a sentence keeps its one decision. Show one "
   "topic dims the rest and says how many of its sentences are decided, open and in a section. Map a topic to sections "
   "(Topics of this effort...) and its requirements go there when you decide them; Make a section for each topic lays "
   "out an RFI response.",
   "RFI efforts open in Sort mode: I marks a Customer interest (in place of L and M), and Suggest marks the sentences that "
   "say what the Government wants to learn.",
   "On a sentence's card, To the Wall of Truth puts an objective or key point on the effort's Wall of Truth.",
   "Graphic need (P) tags a concept that needs a graphic, from the sentence or the words you picked; it lists on the Effort Dashboard.",
   "Several sentences at once: Ctrl+click, drag a box, Select undecided, or Ctrl+A. The bar above the page shows how many, "
   "with Decide all, Put all in section and Author for all.",
   "+ Task... and + Ask the team... put work and questions on the sentence.",
   "When a document is done, press Mark reviewed, then Next document.",
   "Parts (3.19.0) adds a cover, a title page, front matter items, appendices and a back cover to the volume, each in its "
   "place, and moves a section to another part. Each part shows the rules it follows from Production Standards; Part rules "
   "and page limits... sets which parts count toward the page limit.",
   "Undo (top bar) or Ctrl+Z undoes the last change on the page, the structure too: a section added by mistake comes "
   "back out. The Pages column of the structure (double-click) sets a section's pages: the RFP's limit or the team's guideline.",
   "Every choice has its own color on the page (3.18.1): L green, M orange, SOW teal, support blue, the customer's purple, "
   "ignored grey; only undecided sentences stay plain. X ignores (a decision); Delete takes a decision off. A sentence "
   "something was captured from has a pink outline, and the margin says what.",
   "Suggest (3.18.0) shows what each sentence most likely is, dashed on the page, from rules you can read (who acts, the "
   "verb, the RFP section; then the team's rules), not AI. Enter accepts the selected ones; Accept the clear ones takes "
   "only the sure ones; Not right drops one; any key decides otherwise. Accepted ones stay marked until someone presses "
   "Checked. Make a rule... on a card teaches it: a phrase and what such sentences are, for the team or this effort."],
  ["J joins sentences; S splits one where you clicked (Split here).",
   "Ctrl+Z undoes. Ctrl+F finds a sentence by its words or number.",
   "On a later version, changed sentences are outlined in amber and new ones in green. Show the old page shows what it "
   "was."]),
 ("prove", "Shred", "Coverage",
  "Review's third tab: every sentence of every customer file, by decision, and the text check, which reads each file "
  "word for word and finds text the reader missed (in tables, text boxes, headers and footers).",
  "Before you call the review finished, before a gate, and when someone asks whether every line was read.",
  ["Read the table: requirements, context, the customer's, ignored, and requirements with no section yet, per file.",
   "Press Run the text check. If anything is missing, press Add the missing lines: they go in their place in the document.",
   "The Library's Review column shows the same thing a document at a time."],
  ["Every read runs the text check too, and says the result in the status bar."]),
 ("sort", "Shred", "Sort",
  "Name the big areas of what is being bought (an architecture, a service, the parts of the work) and file every "
  "requirement under one, before the outline is built.",
  "After the requirements are read into Review, and whenever an amendment adds some.",
  ["Start from...: the RFP's headings (its own numbering), the evaluation factors, or the starter list. Rename a "
   "topic in your own words; its requirements stay with it.",
   "Unsorted, at the top, holds what has no topic yet. Select rows (Ctrl or Shift for more) and press 1 to 9 for the "
   "first nine topics, or pick a topic and File. Also under adds a cross-reference; the first topic stays the home.",
   "+ Subtopic puts one under the topic picked; Merge into... moves a topic's requirements to another and keeps its "
   "name as another name; Split... cuts a compound sentence into parts with the same words (IDs .a, .b).",
   "Overview: each area's requirements, how many are shall, should and may, and how many come from L, M and the SOW.",
   "Read back from Excel...: a matrix workbook edited in Excel (ID and Topic columns, topics separated by ';') files "
   "each sentence under the topics typed there.",
   "Suggested: in Unsorted, each requirement whose words point at one topic shows it and why (a topic's Keywords... "
   "count most, then the words of its name). Take the suggestions files the selected rows, or every row shown.",
   "View: Structure: each topic beside the response outline. Map to it (a topic fills a section), Make subsections "
   "under it (a section per selected topic, subtopics under it), Place their requirements (each kept one goes to its "
   "home topic's first section), and Our fit (Strong, Partial, Gap) per topic. For an RFI or sources sought, Make the "
   "response from the topics adds a Response volume with a section per topic. The line on top says what is still "
   "missing."],
  ["These are the same topics as Review's Sort mode and the matrix's Topic column.",
   "A topic can name its response sections (Review > Topics...): a requirement kept with no section goes to its "
   "topic's first section."]),
 ("matrix", "Shred", "Matrix",
  "The compliance matrix as the customer will see it, built from your decisions in Review.",
  "You deliver the matrix, or share it with the team.",
  ["Choose the columns. Add a column... adds your own.",
   "Press Export the matrix..., or Export the compliance package... for the matrix with its reports.",
   "Save as the team default keeps this layout for new efforts."],
  ["The exported workbook is a dated copy. Exports are never overwritten."]),
 ("shredacc", "Shred", "Accuracy",
  "How well the shred finds requirements, measured on your own set of public RFPs: recall (the real requirements it "
  "finds), precision (its flags that are real) and the kind, against the 95% target, release by release.",
  "Whenever you add an RFP to the set, and after each release.",
  ["Make a folder for the set (Choose the folder...; it starts as Stationkeeper Shred Set in your user folder) and save "
   "public RFPs in it: the RFP, Sections L and M, the SOW, any amendments.",
   "Read an RFP into Review in a test effort and decide every sentence: requirement (with its kind), context or drop.",
   "Back here, press Save this effort's Review as answer keys: a key is saved beside each RFP the effort read.",
   "Press Score the set. Each RFP shows its scores; the set's scores go in By release."],
  ["The set stays on this PC. The build scores it each release and logs the numbers only, never a file's name or text.",
   "The build stops when recall drops below the floor: the first run's score, raised as the shred gets better."]),
 ("crosswalk", "Shred", "L/M Crosswalk",
  "The Matrix's second tab. Section L says how to write the proposal, Section M says how the customer scores it, and "
  "Section C, the SOW or the PWS says the work. Each row is one instruction beside the factor that scores it and the work "
  "it describes; the gaps show instructions nobody scores and factors with no instruction.",
  "Right after the first read, while you build the structure: it shows which sections carry the score.",
  ["Read the rows. Gaps show where an instruction has no factor or a factor has no instruction.",
   "Press Export the crosswalk... for a review or the proposal manager."],
  ["The crosswalk fills in from your L, M and SOW decisions in Review."]),
 ("compare", "Effort Library", "Compare",
  "Two versions side by side. Customer versions: what a new version of a customer document changed, what it touches in "
  "your review, and a decision on every change. Any two files: our drafts or any files, sentence by sentence, with the "
  "redline in Word.",
  "An amendment or new version arrives; or you need to know what changed between two drafts.",
  ["Customer versions: pick the document and the old and new versions. Decide each change: update the requirement, Not "
   "ours, or a question for the customer. Export (Word)..., Redline (Word)... or Change list (Excel)... share the changes.",
   "Any two files: Choose... the earlier and the later file (Word, PDF, PowerPoint or Excel), then Compare. Only changes "
   "hides the sentences that stayed the same. Redline (Word)... exports the changes marked; Tracked changes (Word)... "
   "saves a Word file where each change is a tracked change to accept or reject. Two Word files are compared by Word "
   "itself (formatting kept) when Word is on this PC; other files as their text.",
   "Final Checks' Open in Compare, and dropping two files on Your Tools, open Any two files with both picked."],
  ["Adding a new version says at once what it changed. Review the changes opens this page on that pair."]),
 ("structure", "Plan", "Structure",
  "Review's second tab: start or replace the sections of your response from the RFP or a Word outline. Most teams "
  "build the structure beside the page in Review as they read; this tab is for starting it in one step.",
  "When the RFP spells out the response's organization, or you have an outline in Word.",
  ["Choose how to start: What the RFP prescribes, RFP headings, RFP outline, Word outline..., or Blank.",
   "Press Apply. Back in Review, the structure is beside the page: + Heading, + Subheading, From sentence and Copy RFP "
   "section add to it as you read."],
  ["Volumes, people and the page budget are set on the Effort Dashboard (Volumes, people and page budget)."]),
 ("setups", "Plan", "Setup",
  "One page for the response's sections and each author's starting draft: build the sections, say who writes each and "
  "when, pick the template, and make the setup: the volume's template with every section's heading, and under it the "
  "customer's words, how it is scored, the PM's direction, its pages, its lead and due date, in hidden reference styles.",
  "As soon as you have headings, even before the customer's documents are read; and again after the Review, a new "
  "template or new direction.",
  ["No sections yet: drop a file on the page or Bring in a file... (Excel, Word or PDF), or type the sections, then Use "
   "these sections. Use a template file... works before or after the sections.",
   "The sections: right-click one to rename it, make it a heading level, unnumbered, a divider or a placeholder, start a "
   "Word section, add one below or under it, move it or delete it. Enter adds one below, Tab and Shift+Tab change its "
   "level, F2 renames, Delete takes it out, and a drag moves it.",
   "Pick a section: type its Lead, Contributors, Due date, Pages and PM direction, then Save this section. What it prints "
   "shows what the setup will put there; the Preview tab shows the volume's pages.",
   "Add elements... puts the Table of Contents, the lists, Acronyms and Abbreviations and the rest in. Place library "
   "items and what is not placed yet from the right.",
   "Make the setup: each volume's template with the setup written on it. Export has Plain setup, Changes for authors, "
   "Kickoff packets and Strip setup; More has Edit as text / Start from, What fills each section, Setup styles, Outline "
   "versions and Outline layouts."],
  ["Show/Hide in Word shows the hidden reference text. The Structure Builder became part of this page in 3.74.0."]),
 ("storyboards", "Plan", "Storyboards",
  "One sheet per section before anyone drafts: the key message, the win themes it carries, the approach, features "
  "with benefits and proof, and its graphics, beside its requirements and page budget.",
  "After the Response Setup goes out and before the first draft; review them at a storyboard review.",
  ["Pick a volume, then a section on the left. Its lead, writers, page budget and requirements show at the top.",
   "Write the key message and the approach. Tick the win themes the section carries. + Feature adds a feature with its "
   "benefit and proof.",
   "Set the status as it moves: Drafting, Ready for review, Approved. It saves as you type.",
   "Export the volume... makes one Word file, a page per section, for the review. Export this section... makes one."],
  ["Win themes come from the Effort Dashboard (+ Theme... under Win themes); a theme linked to the section is ticked for you.",
   "Graphic needs tagged in Review for the section list here too."]),
 ("drafts", "Write", "Draft Status",
  "Read a volume's draft back by the response structure's headings and the setup's styles: where each section stands "
  "against its page budget, requirements an author removed, and styles pasted text brought in.",
  "While authors draft: before each color review, and whenever you want to know where the volume stands.",
  ["Pick the draft (the Volumes folder's Word files, or Other file...) and press Read the draft. Nothing in it changes.",
   "Sections: Not started (none of the author's own words), Under way, Near budget (half the page budget or more), Over "
   "budget. Pages are counted from words: set Pages from words to your team's figure.",
   "Requirements removed or moved: placed requirements whose text is gone from the draft, or under another heading.",
   "Styles brought in: styles the setup's template did not have. Fix a Copy maps them onto the standard's styles.",
   "Export... writes the report to Excel.",
   "My Work and the Effort Dashboard's Drafts and data calls card show the newest reads; the gate goal Every section drafted "
   "holds until every section read has words of its author's own."],
  ["The page budget comes from Structure > Page budget. Word's own page count from the last save is in the summary line."]),
 ("truth", "Write", "Wall of Truth",
  "The one approved way to state every fact the proposal repeats: cleared staff, years with the customer, square "
  "footage, contract values, names and the customer's terms. Check the drafts finds every place a draft disagrees.",
  "Start it at kickoff from the team's facts; check the drafts before every color review and before final.",
  ["Press + Truth... and fill in what it is, how to write it (142), the words it appears beside in a draft (cleared "
   "staff, cleared employees) and anything never to write. Name the owner who confirms it.",
   "Add the team's facts brings in the company facts every effort shares; Save to the team's wall shares one.",
   "When a fact changes, change its value: the old one is kept, and the check finds it wherever it is still written.",
   "Press Check the drafts. Each finding shows the volume, section and sentence. Right as written leaves one out next time.",
   "Export the wall... makes the page to post in the war room and hand to writers; Export... gives the editors the findings."],
  ["The drafts are the Word files in the effort's Volumes folder (and the deliverables' files).",
   "A date in amber in Confirmed means nobody has checked that truth for 30 days: press Confirm when it is still right."]),
 ("acronyms", "Write", "Acronyms",
  "One place for acronyms, abbreviations, units and symbols, in three tabs: Scan finds them in the customer's "
  "documents or your own drafts; Acronym List is the effort's list with its definitions, and (3.37.0) Show > "
  "Lists to submit, by volume, builds each volume's list from what it uses.",
  "At the start (scan the customer's documents), throughout (add terms and their definitions), and at the end (the lists you submit).",
  ["Scan: press Scan the customer documents, or Scan files... or Scan a folder... for your drafts.",
   "For each term: Add to effort list (adding it is the decision; there is no approval) or Not a term (this effort, on "
   "every later scan and new document version). A term in the list with no definition shows No definition yet.",
   "From a picture, The picture says something else... offers Part of a longer term... (VW in MOC-VW, held where they "
   "sit together), Misread letters... and Not text. Each fix also saves a training sample with the effort.",
   "More holds Plural of, A form of, Another way of writing, Part of a longer term, Add to this PC's database and Remove "
   "from the list. The Exclusion List (never in any effort on this PC) is in Team References.",
   "Add to the database keeps the term and its meaning in this PC's acronym database, apart from the effort's list "
   "(usually after submission). Add a term... adds one by hand: to this scan, the effort list, the database, or all three.",
   "The card: the meaning (other possibilities folded under Show other possibilities), Read here (the line it was read in), "
   "the definition box, the actions, then the preview. Show details opens the counts, the places and an equation's symbols.",
   "The preview boxes what the scan read. Page < and > go through every page or picture of the file. Click a box to see "
   "what it read: Fix the reading corrects it for every later scan on this PC; Use as the meaning puts the words in the "
   "definition box. Find < and > step through the finds and come back to the place.",
   "Drag on the picture to draw a box: the readings inside it light up with their text. Read this area again reads only "
   "the box; correct the text, then Add as a term... (a term the scan missed) or The picture says something else.... "
   "Right-drag, or hold Space and drag, to move the picture. The scan's readings are kept with the effort, so the preview "
   "opens at once.",
   "Why is a term missing? Type a term you expected: the Exclusion List, Not a term, a plural or form you set, the filters, or "
   "what the last scan read (with near misses in pictures). Save as the answer key... makes your decided scan the key of "
   "your acronym set (a folder outside the repository), scored by each build.",
   "The table: click a heading to sort (again to turn it around); Ctrl+wheel or Ctrl+plus and minus change the text size; "
   "right-click a row for every action; double-click for Details. Select several rows to act on them together.",
   "Fixes for misread text...: when the reader misreads a word in a picture (KSF for KSE), add the fix; it is used every "
   "time a picture is read on this PC. Undo puts back the last change.",
   "Acronym List: edit a definition in place. Export the list... for the team. Import a list... reads any Excel or CSV "
   "list and merges it (new terms come in the list; the same meaning fills empty fields; a second meaning is kept under "
   "Other definitions for review). Export... picks the columns, format and volumes; Every "
   "effort... puts every effort's list in one workbook; Import a volume's list... brings a volume's own list in; "
   "Volumes... says which volumes use the selected terms; Activity, New in the last scan, Show in scan, Open in Excel and "
   "Reload help run the list; Add to this PC's database... keeps chosen terms for every effort.",
   "First use in your volumes is checked in Quality > Submission Check (Check first use... on the Acronym List opens it)."],
  ["The customer's own definitions win over the master database.",
   "The list is kept in the effort's Excel workbook, in the effort's folder."]),
 ("lists", "Acronyms", "Lists to Submit",
  "In the Acronym List (Show > Lists to submit, by volume, 3.37.0): the acronym list for each volume from what that volume "
  "actually uses.",
  "At the end, when the volumes are final.",
  ["Review each volume's list.",
   "Press Export the lists (Word)... or Export (Excel)...",
   "Record in the effort list notes which volume uses each term."],
  []),
 ("acrtool", "Acronyms", "Acronym Finder (its own window)",
  "The acronym scan as a tool in its own window, for quick jobs with no effort: scan any files, check each term's meaning "
  "and where it was found, export the list, check first use in your own Word files.",
  "When you need a list of a document's acronyms and their meanings, or to check a submittal's first uses, fast.",
  ["Open it from Home (Your Tools: a pin, or drop a file and pick Find acronyms), from Acronyms > Open in its own window, or start the program with "
   "the acronyms switch (a shortcut to Stationkeeper.exe with /acronyms or the double-hyphen form opens only this window).",
   "Scan files... or Scan a folder...: every acronym, abbreviation, unit and symbol, in typed text and in pictures, with its "
   "meaning. Select a term: its card shows where it was found, the picture or page with every reading boxed (yellow is "
   "the term), or the passage with the term highlighted. Find < and > step through every find.",
   "Export the list...: each term and its meaning as a Word table, an Excel sheet or a CSV. Excluded terms, terms marked not "
   "a term, and plurals and forms tied to their term are left out.",
   "Check first use...: pick your Word files in submission order. For each acronym: where it first appears in running text, "
   "whether it is spelled out there, and the terms the list does not have yet. Export the report to Excel.",
   "Start a new list clears the window's results and list; the files you scanned are never changed.",
   "Lists: keep several scans side by side. New list... starts another with its own files, results and choices; pick one in "
   "List to open it; Rename... names it. Add files... scans the list's files again with more added. Clear no longer found "
   "takes off the terms the last scan did not find.",
   "Symbols: beside the definition box, Greek letters, subscripts, superscripts, math, accents, units and arrows. Right-click "
   "a box, or press Ctrl+Shift+Space, to make the selection subscript, superscript or normal text (H₂O, m²)."],
  ["Its list is its own, on this PC, apart from every effort; it reopens with the last scan."]),
 ("firstuse", "Acronyms", "First Use Check (its own window)",
  "One or more Word files checked on their own: where each acronym is first used, and every acronym used before it is "
  "defined, never defined, or spelled out more than once.",
  "Before a document goes out, or whenever you need to know a draft's first uses fast, with no effort open.",
  ["Open it from Home (Your Tools: a pin, or drop Word files and pick Check first use), from Submission Check, or start the program with "
   "the firstuse switch and the Word files after it.",
   "Add Word files (or drop them on the window) in the order they are read. First use restarts in each file, in each section "
   "of each file, or runs across all the files. Press Check.",
   "Problems lists every fix and check: used before it is defined (with where it is spelled out later), never defined, "
   "spelled out again (with where), defined but never used again, written as (ACR) without its words. Every acronym "
   "shows them all.",
   "Select a row: the place shows on the right, the passage with the acronym highlighted or the picture with it boxed.",
   "This place is the first use: when the first place it appears is not the one that counts (a heading or a figure, say), "
   "select the place in the list and press it; the check counts from there. Back to the first place it appears undoes it. "
   "Entries in a table of contents never count as a first use.",
   "Export the report to Excel."],
  ["Submission Check does the same for an effort's volumes and also compares each spell-out with the effort's acronym list."]),
 ("fulltext", "Acronyms", "Full Text (its own window)",
  "Every word in the files you choose, typed text exactly and picture text through the reader (equations in linear form), "
  "shown in one box and saved as text.",
  "When you need a document's words as plain text: to search it, compare it, or paste it somewhere else.",
  ["Open it from Home (Your Tools: a pin, or drop files and pick Pull out all the text), or start the program with the fulltext switch.",
   "Choose files..., Choose a folder..., or Acronym Finder's files (the files its open list scanned). Press Read all the text; "
   "Stop ends it.",
   "Save as one .txt..., Save one .txt per file... (each named after its file, with _fulltext), or Copy."],
  ["The text carries the same classification and markings as the source files. Save and handle it the same way.",
   "The same reader and sandbox as the scan; nothing leaves the PC."]),
 ("techedit", "Write", "Technical Edit",
  "Copy review: the editor's pass on the words of a Word draft, by rules: mechanics, consistency across authors, Chicago "
  "style (numbers one to nine spelled out), plain language (30 words a sentence, passive voice), the customer's words, "
  "claims without proof and leftovers from reused text. Every finding is a suggestion you accept or skip.",
  "Before a color review on a complete draft (Full copy review), after authors merge (Consistency and mechanics), and in "
  "the last hour before the PDFs (Last look).",
  ["Pick the draft (the effort's Volumes folder, or Add files... for any Word file) and the level, then press Review.",
   "Filter by group, Fix or Check, and status. Select a finding: its sentence shows with the words marked, the suggestion "
   "and why.",
   "Accept puts the fix in the edited copy. Skip here leaves this place alone on every later review. Skip in this effort "
   "turns the rule off for the effort. Add to the style sheet makes a term the effort's own, or a word known.",
   "Make the edited copy writes the accepted findings into a dated copy beside the draft, as tracked changes with a comment "
   "naming the rule. Open it in Word and use Review > Accept.",
   "Style sheet: the effort's terms, the rules on in this effort and the words known; Export the style sheet... gives "
   "authors a Word file."],
  ["The draft itself is never changed.",
   "Spelling uses an English word list and the team's custom dictionaries (Team References); banned phrases come from Team "
   "References; acronyms are read from the acronym list, and fixes to them stay in Acronyms.",
   "Drop a Word file on Your Tools and pick Copy review to use it with no effort open."]),
 ("reviews", "Write", "Color Reviews",
  "Color team review packets: a Word file with every requirement under its section, for reviewers to give a verdict "
  "and comments, read back onto each requirement.",
  "Red team, gold team, or any review where people mark up the response against the requirements.",
  ["Press Build the packet... and choose the stage. Send the Word file to the reviewers.",
   "When it comes back, press Read back a packet... Verdicts and Word comments land on each requirement.",
   "See the score by section, and open a requirement to read its comments."],
  ["Reviewers only need Word. The packet holds no app data beyond the requirements and sections."]),
 ("finalcheck", "Submit", "Final Check",
  "One ready-to-send report per submission volume, on its Word file and the PDF you will upload, with Pass, Fail or "
  "Needs a person on every line: compliance, page limits, format rules, structure, acronyms, leftovers, markings and "
  "files. Submission Check and Final Checks are its tabs.",
  "At gold team and before every upload; again after any late change.",
  ["The volumes are Submission Check's. Add volumes... adds Word files you will submit.",
   "Select a volume and Set the PDF... once: the PDF you will upload for it.",
   "Pages that do not count...: tick only what the RFP leaves out of the page limit (the cover, the TOC, the acronym "
   "list, resumes, dividers). Every page counts until you do.",
   "Press Check. Each volume shows its eight sections; a fail says where and what to do, and Needs a person asks what "
   "only a person can answer.",
   "Export... writes the report to Excel and records it in the effort record."],
  ["Markings checked: the proprietary legend on the cover and the page marking on every page (FAR 52.215-1(e)); the "
   "effort's own marking text when Effort Formatting sets one.",
   "Nothing is changed. The tabs hold each check in full: Submission Check for acronyms and banned words, Final Checks "
   "for the PDF package, leftovers, cross-references and Compare."]),
 ("qa", "Submit", "Submission Check",
  "The volumes you will submit, checked against the effort list, first use, banned words and page limits.",
  "Before each gate and before submission.",
  ["Press Add volumes... and choose the Word files, then Check the submission volumes.",
   "Fix what it finds in Word. Add missing to the effort list adds terms the list does not have.",
   "Double-click a first use row: every place the term appears, drawn. This place is the first use counts from the place "
   "you pick (not a heading or figure, say); entries in a table of contents never count.",
   "Export report (Excel)... records the check."],
  ["First use of an acronym belongs in running text, not in a figure or table."]),
 ("checks", "Submit", "Final Checks",
  "The last checks before the proposal goes out: the final PDF package, cross-references and numbering in the drafts, "
  "and what changed between two versions of a draft.",
  "At gold team and in the last hours before upload; Compare two drafts whenever a reviewer asks what changed.",
  ["Final PDF package: choose the folder with the PDFs you will upload, check the page size, the largest file allowed, "
   "the words every file name must hold and the volumes and forms that must be there, then press Check the package. "
   "Each PDF shows its pages against the limit, page size, fonts not embedded, pages with no searchable text and size.",
   "Leftovers (3.57.0): tick the drafts (Add files... for others) and press Check for leftovers. It finds the setup's "
   "reference text and file properties, hidden text, white text on a light page, comments, tracked changes and "
   "placeholders; each row says why it matters. Drop a Word file on Your Tools and pick Check for leftovers for the same.",
   "Cross-references and numbering: tick the drafts and press Check the drafts. It finds figures and tables out of "
   "order or repeated, mentions with no caption, captions never mentioned, pictures and tables with no caption, and "
   "Word's \u201cError! Reference source not found.\u201d",
   "Compare two drafts: pick the earlier and later version (Other file... for one outside the Volumes folder), press "
   "Compare, then Export the redline... for the reviewers."],
  ["Nothing here changes a file. Each check exports a workbook (or the redline) for the record.",
   "Page limits often leave out the cover, contents and acronym list: a page count over the limit says to check that."]),
 ("qpstd", "Team", "Quick Parts",
  "Every Quick Part in the library, by your numbered categories, with its gallery, whether it follows the template's fonts, the "
  "pages it fills and Word's picture of it.",
  "When Quick Parts come in from a template; before page planning; when a Quick Part changes.",
  ["The same three panes as Formatting Standards: categories (your Quick Parts' own, 01 Front matter and so on), the items with "
   "their effort types, status, version, where each came from and the pages each fills, and the picture with every value.",
   "Category... moves the selected Quick Parts to another category; Pages... types the pages one fills.",
   "Draw with Word: Word on this PC inserts each Quick Part from its kept file, counts its pages and keeps a picture of it, in the "
   "background, one Word job at a time. The picture stays until the Quick Part changes. Without Word the app shows its card.",
   "Keep its own fonts (the value as_built): yes keeps the Quick Part exactly as built; otherwise it follows the template's fonts "
   "and sizes when a template is made."],
  ["Word is never started by itself: only Draw with Word starts it."]),
 ("layoutstd", "Team", "Layout",
  "The pieces a template is assembled from: covers, title pages, back covers, headers and footers, sections and section designs, "
  "table looks, captions and the TOC.",
  "When a new cover or footer comes in; when a part's header or footer changes.",
  ["The same three panes as Formatting Standards. A cover, title page or back cover is drawn from its kept page; a header and "
   "footer on a page; a table look as a sample table; captions as sample captions; the TOC as entries.",
   "Draw with Word: Word draws covers, title pages, back covers, headers and footers and the TOC as they will print, and the "
   "picture is kept until the item changes."],
  ["Table looks (fills and borders by row role) are here; Word table styles are in Formatting Standards."]),
 ("profiles", "Team", "Effort Profiles",
  "Each effort type's profiles (Technical Volume, Management Volume, Orals...), built by picking from the libraries: one part "
  "per decision, filled from Formatting Standards, Quick Parts and Layout, with the RFP's size limits checked as you pick.",
  "When you set up how a kind of effort's volumes look, before templates are made; again when the library changes.",
  ["Pick a profile under its effort type on the left. New profile... adds one; Copy... starts one from the selected profile; "
   "Rename... names it; Take out removes it from this effort type.",
   "Volumes: the volumes this profile makes, separated by semicolons. Each becomes a row on Templates.",
   "Parts: Change... offers the items tagged for this effort type (or every effort type, or not tagged yet); Show all lifts "
   "the filter. A newer version of a picked item waits until you press Use it.",
   "RFP limits: the smallest size the RFP allows for each kind of text. The check says met or under the limit against the "
   "size the profile gives that text."],
  ["A profile in several effort types keeps its own parts and limits in each.",
   "An effort's own changes stay in Effort Formatting, on top of its profile."]),
 ("templates", "Team", "Templates",
  "Every Word template the Effort Profiles make, one row per effort type, profile and volume: Ready, Needs review, Blocked or "
  "Not made yet, and why.",
  "After changing a profile or the libraries, and before an effort's volumes are started.",
  ["Show narrows the list to one effort type.",
   "Make .dotx makes one template in the output folder's Templates folder, in a folder named for its effort type. Make all "
   "ready makes every template that nothing stops and that changed or was never made.",
   "Needs review: a newer library version waits on its profile, or the profile changed since the template was made. "
   "Blocked: a size is under the RFP's limit, or a value does not make a template; fix it on Effort Profiles.",
   "Open in Word opens the last one made; Open the folder shows them all."],
  ["Making templates is a Preview tool until it is turned on in Settings > Preview tools.",
   "Each template's name counts up a version every time it is made again."]),
 ("rules", "Team", "Rules",
  "Every rule the app follows and checks, in one list: the production rules for our documents (Rule 1 to 13 and the "
  "team's own) and the rules Review's Suggest reads the customer's documents by.",
  "To see which rules are on, how each is kept, and where to change a rule's values; to add a rule of your own.",
  ["Show: Our documents, or Reading the customer's documents.",
   "Each rule says how it is kept: checked by the app, checked with Word on this PC, or a checklist item for people.",
   "Untick On for every effort to turn a rule off everywhere. An effort departs from a rule on Effort Formatting only.",
   "Change it opens the page that holds the rule's values (Production Standards, Effort Formatting, the Acronym List).",
   "Add the rule adds one of your own (a checklist item). Phrase rules: a sentence holding the phrase gets that suggestion.",
   "Field recipes: your field codes, written and changed here (name, where used, the code one field per line, the text "
   "between, the bookmark it needs and what it spans, the style it reads). The starters are yours to change or remove. "
   "This effort's own code... sets a different one for the open effort only. Read a template... lists a file's fields "
   "against the recipes; Make a recipe from it adds one. Final Check's Structure section checks every field against them."],
  ["Audit and Fix a Copy report each finding under its rule.",
   "Make templates follows Rules 4 to 8; its footers are Rule 7's table unless you build another."]),
 ("audit", "Team", "Audit",
  "Checks Word, Excel and PowerPoint files against every standard that applies to them and lists every finding: styles, "
  "fonts, tables, captions, the TOC, cross-references, pages, headers and footers, lists, terms, sheets, slides and "
  "graphics. Read only: nothing is changed and no copy is made, so it is safe on a file others have open on SharePoint.",
  "Before each color review and before production, on every volume; and any time someone asks whether a file meets the standard.",
  ["Add the Volumes folder (or Add files...). Each file uses its volume in Production Standards, as Fix a Copy would.",
   "Press Audit. The results show what each area found, per file.",
   "Click a file to see its findings; pick an area to narrow them.",
   "Export findings... makes a workbook of every finding, for the editors."],
  ["Fix a Copy makes a dated copy with the fixes; Audit only reports."]),
 ("fixcopy", "Team", "Fix a Copy (Beta)",
  "Beta: still being proven on real documents, so check every copy it makes. Fixes a draft's formatting to the production standard in a dated copy. Your file is never changed: it is read once, "
  "and a file someone has open is not copied at all.",
  "Before each color review and for final production, on each volume.",
  ["The effort's type (set when you start it, or in Production Standards) decides which volumes its drafts use.",
   "Check the output folder (Change... sets it; the default is Production Copies in the Stationkeeper data folder). "
   "Each effort's copies go in a folder with the effort's name inside it. Copies never go beside the original.",
   "Check every draft reads every listed draft against its own volume and lists what each breaks, by area (what "
   "Format Check used to do); double-click one to see its fixes. Export findings... makes a workbook of every finding.",
   "Pick a draft from the Volumes folder, or Add a file.... Its volume name comes from the Deliverables board when the "
   "draft is a deliverable's file; otherwise type it. The solicitation comes from the effort's basics. Headers and "
   "footers are built only when both are set. Volume: the draft's own (kept on the Deliverables board for a "
   "deliverable), or the effort's. Press Check; each area shows what it found, each style that differs from the style "
   "library property by property.",
   "What to fix: every fix is listed under its area with what it found; untick any you do not want. Expand a fix to "
   "see each finding and where it is.",
   "Tables: pick a table to see every row's role. Rows in bold wait for your answer; one answer covers every row "
   "like it. Select rows and press C, H, 2, S, B, U, T, N or K to set their role; change the table type if needed.",
   "A table question: choose the role; Make it a rule saves it (for the draft's volume, or this effort only) so rows "
   "like these never ask again.",
   "Excel and PowerPoint: a workbook or a deck in the Volumes folder is listed too (Add a file... takes one from "
   "anywhere). Check reads it against the volume's Excel and PowerPoint values and lists what differs, sheet by sheet "
   "or slide by slide. These files are read only: fix what Check finds in Excel or PowerPoint, then Check again.",
   "Decisions: say whether a list restarts or continues, and point broken cross-references at a target.",
   "Leave Update fields in Word on so page numbers, caption numbers, the TOC and the lists of tables and figures "
   "renumber, then press Make the fixed copy.",
   "The result shows found before and left after by area, every fix that ran (or was refused, leaving the copy as it "
   "was before it), and that the original is unchanged. Open the copy, or the report beside it."],
  ["The copy is named <name> - COPY - Stationkeeper <date time> and carries a Stationkeeper copy property "
   "(File > Info > Properties).",
   "A file in a OneDrive or SharePoint folder: people editing it online can't be seen from here, so the copy is the "
   "version synced to this PC. Fix it when the writers are done.",
   "Each fix is one guarded change that may touch only what it declares; anything else is refused.",
   "Fix a Copy and Make a .dotx template are Preview tools: off for the team until the proposal manager turns them on in "
   "Settings > Roles and Preview tools."]),
 ("refs", "Team", "Team References",
  "Every list the team keeps, in one place: banned phrases, this PC's acronym database, the Exclusion List, fixes for misread "
  "text, the team's Wall of Truth and the custom dictionaries for Word.",
  "When a list needs a change that every effort and tool should use from then on.",
  ["Each card says what the list is, how many it holds and which spaces read it. Open... shows it.",
   "Banned phrases: Banned is always fixed, Avoid is checked by a person; Add a phrase, Remove, Save.",
   "This PC's acronym database: Load a database... brings in a provided one; Open in Excel opens the file.",
   "Custom dictionaries: the words Word should know, built here and exported for Word."],
  ["The lists stay where they are kept; this page only gathers them."]),
 ("postsub", "Submit", "Checklist",
  "What the team does after the proposal goes in: owners, due dates and done.",
  "The proposal is submitted.",
  ["Press Mark submitted... The checklist appears.",
   "Give each item an owner and a due date. + Item adds one.",
   "Save as default... keeps this checklist for new efforts."],
  ["Export to Excel... shares the checklist."]),
 ("keywords", "Submit", "Keywords",
  "The effort's keywords for SharePoint: what the customer asked for and what you proposed, with reasons, to file the "
  "submitted proposal.",
  "After submission, when the proposal is filed.",
  ["Press Suggest keywords. Each suggestion says why.",
   "Add selected keeps them; Not a keyword drops one.",
   "Export for SharePoint... makes the list to tag the submitted proposal."],
  []),
 ("exportall", "Effort", "Export All",
  "Every feature's outputs in one dated folder.",
  "At a gate, at submission, or to hand the effort's outputs to someone.",
  ["Press Export all... and choose where the dated folder goes."],
  ["Every export is dated and kept in the effort's folder. Nothing is overwritten."]),
 ("settings", "Settings", "Settings",
  "This PC's settings: work mode, time zone, efforts, author list, stages and roles, folders and file names, document "
  "types, custom dictionaries, branding, team pack, master database, backups, updates, and help.",
  "Setting up the app, joining a team, or installing an update.",
  ["Where Stationkeeper is used sets the work mode: Offline, Connected or SCIF-ready.",
   "Our data (3.22.0): Export our data... writes the team's foundational data (acronyms, dictionaries, phrases, "
   "standards, the template library, team lists) to one file; Import our data... brings it in on another PC, add-only, "
   "with Undo. Nothing about one effort goes in it, and it never goes on GitHub.",
   "Custom dictionaries keeps your team's words for Word: + Dictionary..., type words or Import a .dic..., Add the "
   "effort's acronyms, then Export for Word... and add the file in Word (File > Options > Proofing > Custom Dictionaries).",
   "Branding shows the company logos. They are built into Stationkeeper; nobody changes them from here.",
   "Roles and Preview tools: your role and where it comes from (People in the effort, or your own choice in "
   "Customize...), hide other roles' tools, and show the stage's tools at the top of the menu. The proposal manager turns "
   "Preview tools (Fix a Copy, Make a .dotx template) on or off for the team; a team pack carries the choice.",
   "Install a team pack... takes your team's stages, document types, folders and author list in one step.",
   "In Updates, Install update pack... installs a new version from its .skupdate file. Undo last update goes back one step.",
   "Help and support opens this Guide, the shortcuts, what's new, Issues and ideas, and the support file.",
   "Issues and ideas (Issue or idea in the top bar, or Ctrl+Shift+I, on any page): choose Bug, Improvement or Idea, "
   "the feature (the page you are on is filled in), the importance, a title and the details, then Save. Describe the "
   "feature, never document content: a report with a word from the effort or your lists is not saved, and the words "
   "to take out are shown. Mark a report Done when it is fixed. Export... saves every report (or the ones selected) as "
   "a text-only zip to give whoever maintains Stationkeeper."],
  ["SCIF-ready keeps no logs, no training data and no bug reports, and cannot be switched back.",
   "Your data folder can move: Move the data folder..."]),
 ("prodstd", "Advanced", "Production Standards",
  "Every rule Fix a Copy uses and every template is made from, in layers: the global standard, effort types, volumes, and this effort.",
  "Once to set the team's rules; for each volume; at the start of each effort to bring in the RFP's.",
  ["Editing (3.25.0): two boxes, Effort type and Volume. Any and Any is the global standard; a volume alone is that volume "
   "everywhere; an effort type alone is every volume in it; both is that volume in that effort type. This effort only "
   "edits the open effort's values. A value set at that layer shows in bold with what it was; Reset takes it back. "
   "3.36.0: Production Standards edits the global standards only (a blue band says so); one effort's formatting is in "
   "Effort > Effort Formatting, and its Every setting opens this editor on that effort (an amber band).",
   "Document sections (Document parts before 3.45.0): Cover, Front matter, Response, Appendices and Back cover. Each section "
   "shows what applies to it: where it starts and how its pages are numbered, its header and footer, its page, TOC or captions, "
   "and what every section shares. Page setup and contents: the page setup the section follows, and what it starts with, in "
   "order (+ Element..., + Quick Part..., + Placeholder...); Make templates puts them at its start. Each section has a drawn "
   "preview, Open a sample in Word, Save this section as a design (Template library > Section designs) and Use a saved design.",
   "Sections in order: the page scheme, your own sections among them (add a row: a key, a name, the style it starts at). Its "
   "card A section's page setup and contents does the same for any section, and builds its header or footer as a table.",
   "Library beside a section's contents (3.48.0): response elements, this standard's Quick Parts and the template library's "
   "Quick Parts. Drag one onto the section where it should sit (or double-click to add it at the end); a template library "
   "Quick Part comes into this standard as it lands. Drag the contents to reorder them.",
   "Cover, title page and Back cover (3.40.0): each page says its kind: a flow page (paragraphs), a table page, or a placed page "
   "(a background with text placed on it). Edit in Word opens a dated copy; what you save is kept as a new version and the page "
   "before it stays. On a PC with Word the preview is Word's own picture of the page; otherwise it is the app's sketch.",
   "Cover and Back cover > Edit the layout... (3.27.0; placed pages, 3.40.0): drag a picture, text box or table, or type its place and size "
   "in inches; set which field each line of text shows (its style becomes the field's cover style). Save keeps a new copy.",
   "The menu across the top goes by layer (3.45.0): Template profile; Building blocks (base fonts and sizes, styles, font "
   "rules, allowed styles, heading numbering, lists, page setups); Components (Quick Parts, table types, row looks, how rows "
   "are recognized, captions, headers and footers, table of contents, fields); Document sections (each section, and Sections "
   "in order); Checks (words to avoid and fix, graphics, Excel and PowerPoint); Library (the template library).",
   "Template library... shows the shelves; Use in this standard puts an item into what you are editing, and New style... "
   "adds your own (hidden text ones too).",
   "Allowed styles: tick Only the ticked styles are allowed, then tick the styles from this standard's and the library's; "
   "sort by any column (type, group, use case, where it came from) or show one kind. Off: any style is allowed.",
   "Headers and footers: Word's way puts the left, center and right text on tab stops. Type column widths in inches "
   "(2, 2.5, 2) to build a header or footer as a one-row table instead, with no borders, a line under or a grid. Use a "
   "Quick Part as a header or footer... takes one of this standard's Quick Parts as a section's header or footer, kept as built.",
   "Import from a file... opens a browser of the file by layer: tick items in any group (New, Same as the library, Differs, "
   "with what differs) and press Take the ticked. Each Word section of the file can be kept as a section.",
   "Library > Template library: the shelves as a page, with a Layer filter, a search, Pictures, and where each item is used.",
   "Build a header or footer as a table... (here or on a Document sections section): columns at inch widths, lines of words and "
   "fields with their alignment, size and bold, and a logo. Use Rule 7's footer puts the A number, the marking and the "
   "team's line, and the page number. Save as a Quick Part... keeps it in the standard's Quick Parts for every template. "
   "Insert a field lists the fields by name and puts one in the line chosen. The team's line comes from Base fonts and "
   "sizes (The team's line in the footer), or per effort from Effort Formatting.",
   "What Check reports: each section that has checks (Captions, Table of contents, Headers and footers, Page sizes and "
   "margins) lists them at the bottom. Check reads them; nothing is changed.",
   "Quick Parts: Add from a template or document... lists the Quick Parts every template from this standard carries, "
   "all in Word's Quick Parts gallery under your numbered categories. Their fonts and sizes follow this standard's styles "
   "(3.48.0): typed fonts and sizes inside them come off when a template is made, symbol fonts aside. Tick Keep its own "
   "fonts for a Quick Part that must stay exactly as built.",
   "Fields (called Fill-ins before 3.25.0): field codes for a value typed once that shows everywhere: a cover style read "
   "by STYLEREF, or a document property (DOCPROPERTY). Use one in a header or footer as {key}.",
   "Heading numbering and lists: the number shows as it will look (1.1.1, Section A); type it the same way.",
   "The Preview beside each section draws what its values make and lists every value this layer changes in the section.",
   "Make templates... (3.25.0): choose what you are editing, every volume of an effort type, or this effort's volumes with "
   "the setup written on each (each volume can continue the page and chapter numbers of the one before, suggested from "
   "its draft). Each template is listed and shown in full (styles, pages and margins, pagination by part, "
   "headers and footers, numbering, tables, captions, TOC, covers, Quick Parts, fields, theme and fonts, and what to fix "
   "first) before Make writes any file. Each one is named and versioned, with a validation report beside it and, with "
   "Word on the PC, Word's own check.",
   "Effort types: + Effort type... adds one (RFP response, page-limited RFP response, RFI response, white paper and "
   "program deliverables are there to start); Effort types... renames, orders and takes them out. You pick one each time "
   "you start an effort. A volume's Deliverables this volume fits: words in a deliverable's name (cost, price) that pick it.",
   "This effort: choose its volume, then Fill from the RFP's formatting rules lays the RFP's fonts, margins and page size "
   "over it for this effort only. Press Save."],
  ["Blank means not set: a rule nobody sets is not checked and not written."]),
 ("safe", "Keeping work safe", "Backups, packages and the readable copy",
  "Three ways your work is kept: automatic backups, effort packages, and a readable copy of everything.",
  "Always on. Use them when you hand off an effort or need to recover.",
  ["Backups run on their own. Set where they go in Settings > Backups (Keep safe).",
   "Save effort package... (Effort Record) makes one file with the whole effort.",
   "The readable copy beside the effort list holds every captured item as plain CSV, Word and Excel files."],
  ["After a crash, Stationkeeper reopens where you were.",
   "Restore... (Effort Record) brings back a backup."]),
 ("keys", "Keeping work safe", "Keyboard shortcuts",
  "The keys that save the most time.",
  "Any time.",
  [], []),
]

from .guidestudio import STUDIO, FORMATSTD, APPLYWORD, CHECKS369      # 3.66.0: kept apart so this file stays under 800 lines
TOPICS[next(i for i, t in enumerate(TOPICS) if t[0] == "qpstd"):0] = [STUDIO, FORMATSTD]
TOPICS.insert(next(i for i, t in enumerate(TOPICS) if t[0] == "fixcopy") + 1, APPLYWORD)   # 3.67.0
for _k, _line in CHECKS369:                     # 3.69.0: Production Standards' sections in their new homes
    for _t in TOPICS:
        if _t[0] == _k and isinstance(_t[5], list):
            _t[5].append(_line)
# 3.75.0: the Guide reads in the menu's order (nine groups; a tab's page after its menu item)
_ORDER = ("tools mywork efforts home requirements deliverables effortfmt record meetings library read custqa datacalls compare "
          "impact shredreq shredacc assign prove sort matrix crosswalk evalcrit setups structure storyboards drafts truth acronyms "
          "acrlist techedit reviews finalcheck qa checks postsub keywords formatstd qpstd layoutstd profiles templates studio "
          "rules audit applyword fixcopy refs settings exportall").split()
_pos, _last = {}, -1.0
for _n, _t in enumerate(TOPICS):
    _last = float(_ORDER.index(_t[0])) if _t[0] in _ORDER else _last + 0.001
    _pos[id(_t)] = _last
TOPICS.sort(key=lambda t: _pos[id(t)])
