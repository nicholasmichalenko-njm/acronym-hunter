"""The Guide (3.0.2): how to use every page, in the order of the menu.

F1 opens it at the page you are on; Help and support in Settings opens it at the start. Each topic says what the page
is for, when to use it, the steps with the real button names, and a few tips. Go to this page jumps there. 3.14.2: text
only; no pictures and no sample content."""
import html
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)
from . import design as D

# (key, group, title, what it is for, use it when, [steps], [tips]); key matches the menu's page key where there is one
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
 ("efforts", "Home", "All Efforts",
  "Every effort on this PC, a new one, and work not filed under an effort yet.",
  "You start a new proposal, switch efforts, or pick up an effort a teammate handed you.",
  ["Press + Add an Effort (or open the Effort Dashboard with no effort open). Type a name and press Create effort. The picture, "
   "client, solicitation, due date and proposal manager are optional; the effort's folders are made for you.",
   "Click an effort's card to open it. The menu then works on that effort.",
   "To pick up a teammate's effort, press Import effort package... and choose the .skpkg file they sent.",
   "To read documents before an effort exists, press Start without an effort: open Unfiled. Make it an effort... later "
   "keeps the work."],
  ["Each effort keeps its own decisions, lists and settings. Nothing crosses between efforts.",
   "The card shows the stage, the due date and what needs attention."]),
 ("mywork", "Home", "My Work",
  "One person's work in every effort on this PC, soonest first: tasks, questions for them, customer questions, "
  "deliverables and graphic needs they own, the requirements they answer, and the sections they lead with page budgets.",
  "Every morning, and when you work on several efforts at once.",
  ["Pick a name in Work for (yours shows first once Customize... > I am is set on the Effort Dashboard).",
   "Read Soonest first: late items are red and on top; requirements are due when the current stage ends.",
   "Double-click a row to open that effort at the right page. By effort shows each effort's stage, due date and sections.",
   "Export... makes a workbook of the list for a status meeting."],
  ["My Work only reads the efforts; nothing changes until you open one.",
   "Refresh reads every effort again after teammates' changes come in."]),
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
   "Double-click a requirement to open it in Review."],
  ["A Volume deliverable links to its volume by name.",
   "View: List shows the same deliverables as a table."]),
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
 ("reviews", "Effort", "Color Reviews",
  "Color team review packets: a Word file with every requirement under its section, for reviewers to give a verdict "
  "and comments, read back onto each requirement.",
  "Red team, gold team, or any review where people mark up the response against the requirements.",
  ["Press Build the packet... and choose the stage. Send the Word file to the reviewers.",
   "When it comes back, press Read back a packet... Verdicts and Word comments land on each requirement.",
   "See the score by section, and open a requirement to read its comments."],
  ["Reviewers only need Word. The packet holds no app data beyond the requirements and sections."]),
 ("library", "Solicitation", "Library",
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
 ("read", "Solicitation", "Read into Review",
  "The Library's second tab: several customer documents read into the compliance matrix at once. Every sentence is cut "
  "out of the page, scans and pictures are read with OCR, and nothing is dropped.",
  "A new solicitation arrives with many files, or you add files that are not in the Library yet.",
  ["Tick the documents (or press Add files...).",
   "Press Read. The progress panel shows each file and page; Review opens when it is done.",
   "One document at a time is simpler from the Documents tab: Read it into Review."],
  ["Scanned pages and pictures are read by the OCR reader (AI and ML), on this PC.",
   "Every read runs the text check: Coverage (in Review) shows it file by file."]),
 ("compare", "Solicitation", "Compare",
  "What a new version changed, what it touches in your review, and a decision on every change.",
  "An amendment or new version arrives.",
  ["Pick the old and new versions. The changed, added and removed sentences are listed.",
   "Decide each change: update the requirement, Not ours, or a question for the customer.",
   "Export (Word)..., Redline (Word)... or Change list (Excel)... share the changes."],
  ["Adding a new version says at once what it changed. Review the changes opens this page on that pair."]),
 ("custqa", "Solicitation", "Customer Q&A",
  "The formal questions you submit to the customer: their exact words and where they are, your question, its status "
  "and the answer.",
  "Before the questions-due date, and when the answers come back.",
  ["In Review, select a sentence (or drag across words) and use Capture > Question. It quotes the customer and the "
   "place for you.",
   "Here, edit the question, its category and owner, and move it from Draft to Approved.",
   "Export to Word or Excel, or fill the customer's own Q&A form. Exporting can mark the questions Submitted.",
   "When answers arrive, add each answer and the document it came in."],
  ["Every exported question names the customer file it is about. Owner, status and notes never go out."]),
 ("assign", "Compliance", "Review",
  "The customer's document as it looks, every sentence boxed. You decide each sentence, place it in your response, "
  "and capture what it holds. This is where an effort's review happens.",
  "From the first read until every sentence is decided, and again when a new version arrives.",
  ["Click a sentence. Press L (Instructions), E (M, Evaluation) or R (SOW, Work) to make it a requirement in the "
   "target section; C for context that supports the last requirement; G for the customer's own sentence; X to clear.",
   "Drag across words inside the sentence to pick just those words. Capture files them: a contact, submission or "
   "formatting rule, acronym, key date or customer question. More captures... adds evaluation factors, page limits, "
   "deliverables, effort details and hot buttons.",
   "Graphic need (P) tags a concept that needs a graphic, from the sentence or the words you picked; it lists on the Effort Dashboard.",
   "Several sentences at once: Ctrl+click, drag a box, Select undecided, or Ctrl+A. The bar above the page shows how many, "
   "with Decide all, Put all in section and Author for all.",
   "+ Task... and + Ask the team... put work and questions on the sentence.",
   "When a document is done, press Mark reviewed, then Next document."],
  ["J joins sentences; S splits one where you clicked (Split here).",
   "Ctrl+Z undoes. Ctrl+F finds a sentence by its words or number.",
   "On a later version, changed sentences are outlined in amber and new ones in green. Show the old page shows what it "
   "was."]),
 ("structure", "Compliance", "Structure",
  "Review's second tab: start or replace the sections of your response from the RFP or a Word outline. Most teams "
  "build the structure beside the page in Review as they read; this tab is for starting it in one step.",
  "When the RFP spells out the response's organization, or you have an outline in Word.",
  ["Choose how to start: What the RFP prescribes, RFP headings, RFP outline, Word outline..., or Blank.",
   "Press Apply. Back in Review, the structure is beside the page: + Heading, + Subheading, From sentence and Copy RFP "
   "section add to it as you read."],
  ["Volumes, people and the page budget are set on the Effort Dashboard (Volumes, people and page budget)."]),
 ("prove", "Compliance", "Coverage",
  "Review's third tab: every sentence of every customer file, by decision, and the text check, which reads each file "
  "word for word and finds text the reader missed (in tables, text boxes, headers and footers).",
  "Before you call the review finished, before a gate, and when someone asks whether every line was read.",
  ["Read the table: requirements, context, the customer's, ignored, and requirements with no section yet, per file.",
   "Press Run the text check. If anything is missing, press Add the missing lines: they go in their place in the document.",
   "The Library's Review column shows the same thing a document at a time."],
  ["Every read runs the text check too, and says the result in the status bar."]),
 ("crosswalk", "Compliance", "L/M Crosswalk",
  "The Matrix's second tab. Section L says how to write the proposal, Section M says how the customer scores it, and "
  "Section C, the SOW or the PWS says the work. Each row is one instruction beside the factor that scores it and the work "
  "it describes; the gaps show instructions nobody scores and factors with no instruction.",
  "Right after the first read, while you build the structure: it shows which sections carry the score.",
  ["Read the rows. Gaps show where an instruction has no factor or a factor has no instruction.",
   "Press Export the crosswalk... for a review or the proposal manager."],
  ["The crosswalk fills in from your L, M and SOW decisions in Review."]),
 ("matrix", "Compliance", "Matrix",
  "The compliance matrix as the customer will see it, built from your decisions in Review.",
  "You deliver the matrix, or share it with the team.",
  ["Choose the columns. Add a column... adds your own.",
   "Press Export the matrix..., or Export the compliance package... for the matrix with its reports.",
   "Save as the team default keeps this layout for new efforts."],
  ["The exported workbook is a dated copy. Exports are never overwritten."]),
 ("setup", "Compliance", "Response Setup",
  "The Word documents your writers start from: each section's headings with the RFP text placed under them, "
  "references on the same line, and management direction.",
  "Before writing starts, and after the review changes.",
  ["Check each section's requirements. Up and Down reorder; Take out of this section removes one.",
   "Press Export the setup... One Word file per volume.",
   "Export changes only... gives writers just what changed since the last setup."],
  ["The export is plain: RFP text in purple, direction in green, ready for your team's own styles."]),
 ("storyboards", "Writing", "Storyboards",
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
 ("truth", "Writing", "Wall of Truth",
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
 ("acronyms", "Writing", "Acronyms",
  "One place for acronyms, abbreviations, units and symbols, in three tabs: Scan finds them in the customer's "
  "documents or your own drafts; Acronym List is the effort's list with approved definitions; Lists to Submit builds "
  "each volume's list from what it uses.",
  "At the start (scan the customer's documents), throughout (approve definitions), and at the end (the lists you submit).",
  ["Scan: press Scan the customer documents, or Scan files... or Scan a folder... for your drafts.",
   "For each term: Use this (a definition), Add to the acronym list, Not a term, or Needs author.",
   "Acronym List: edit a definition, or press Approve... to record the approver. Export the list... for the team.",
   "First use in your volumes is checked in Quality > Submission Check (Check first use... on the Acronym List opens it)."],
  ["The customer's own definitions win over the master database.",
   "The list is kept in the effort's Excel workbook, in the effort's folder."]),
 ("lists", "Writing", "Lists to Submit",
  "The Acronyms tab that builds the acronym list for each volume from what that volume actually uses.",
  "At the end, when the volumes are final.",
  ["Review each volume's list.",
   "Press Export the lists (Word)... or Export (Excel)...",
   "Record in the effort list notes which volume uses each term."],
  []),
 ("qa", "Quality", "Submission Check",
  "The volumes you will submit, checked against the effort list, first use, banned words and page limits.",
  "Before each gate and before submission.",
  ["Press Add volumes... and choose the Word files, then Check the submission volumes.",
   "Fix what it finds in Word. Add missing to the effort list adds terms the list does not have.",
   "Export report (Excel)... records the check."],
  ["First use of an acronym belongs in running text, not in a figure or table."]),
 ("checks", "Quality", "Final Checks",
  "The last checks before the proposal goes out: the final PDF package, cross-references and numbering in the drafts, "
  "and what changed between two versions of a draft.",
  "At gold team and in the last hours before upload; Compare two drafts whenever a reviewer asks what changed.",
  ["Final PDF package: choose the folder with the PDFs you will upload, check the page size, the largest file allowed, "
   "the words every file name must hold and the volumes and forms that must be there, then press Check the package. "
   "Each PDF shows its pages against the limit, page size, fonts not embedded, pages with no searchable text and size.",
   "Cross-references and numbering: tick the drafts and press Check the drafts. It finds figures and tables out of "
   "order or repeated, mentions with no caption, captions never mentioned, pictures and tables with no caption, and "
   "Word's \u201cError! Reference source not found.\u201d",
   "Compare two drafts: pick the earlier and later version (Other file... for one outside the Volumes folder), press "
   "Compare, then Export the redline... for the reviewers."],
  ["Nothing here changes a file. Each check exports a workbook (or the redline) for the record.",
   "Page limits often leave out the cover, contents and acronym list: a page count over the limit says to check that."]),
 ("prodstd", "Production", "Production Standards",
  "Every rule Fix a Copy uses, in three layers: the team standard, document profiles, and this effort.",
  "Once to set the team's rules; for each profile; at the start of each effort to bring in the RFP's.",
  ["Editing: choose the team standard, a document profile (+ Profile... adds one, starting from the one shown), or "
   "this effort. A value set at that layer shows in bold with what it was and the layer it came from; Reset takes it "
   "back to the layer below.",
   "The Preview beside each section draws what its values make (a page with its fonts, spacing and margins; headings "
   "with their numbers; captions; the page scheme; headers and footers; the TOC; lists; a figure) and lists every value "
   "this layer changes in the section: what it was and what it is now.",
   "Graphics: the picture types allowed, the smallest resolution where a picture is placed (ppi), the widest a figure "
   "may be, the fonts and smallest text in drawings, charts and text boxes, captions, alt text, RGB only and the largest "
   "picture file. Fix a Copy and Audit check every figure against them; a picture is never changed.",
   "Effort types: + Effort type... adds one (RFP response, page-limited RFP response, white paper and program "
   "deliverables are there to start). Editing an effort type sets the profiles it holds, its default profile, and the "
   "rules every profile in it follows; Effort type > profile sets its changes for one profile. Make templates for every "
   "profile... writes one template per profile. Order: team, profile, effort type, effort type for the profile, the effort.",
   "A profile's Deliverables this profile fits: words in a deliverable's name (cost, price) that pick this profile for it "
   "in an effort type.",
   "Learn from a file...: pick your master template or a finished volume. Stationkeeper reads it (it is never changed) "
   "and lists what it carries: every style's whole definition, the format variables, table looks by row role, page "
   "setups, headers and footers, heading numbering and the TOC. Untick what you do not want; review; Save.",
   "Format variables: body, table and caption fonts and sizes, spacing, margins, paper and the restriction marking. "
   "Row looks and styles use them. Leave the volume name and solicitation blank: they come from the effort and the file.",
   "Font rules: the allowed fonts and the smallest and largest size for each kind of text. Blank is not checked.",
   "Styles and heading numbering: allowed styles, removing and hiding unused ones, a template to take styles from, and "
   "each heading level's number format, number text and positions.",
   "Style library: every style the profile defines, whole: font, size, bold, italic, underline, caps, color, "
   "alignment, spacing, line spacing, indents, keeps, page break before, widow control, based on and next style. Fix a "
   "Copy checks each draft's styles against it property by property and sets the ones that differ.",
   "Table rows: each row's tag style, font, size, bold, italic, colors, alignment, spacing, repeat, merge, and every "
   "border edge (on, width, color), with a preview. Applies to: all table types, or one type only.",
   "List numbering (in Bulleted and numbered lists): what each list style shows, level by level: the bullet and its "
   "font, or the number format and text, and where the number and the text start.",
   "Word table styles: Learn from a file takes the table styles a template uses, whole; a table type's Word table "
   "style (Table types section) makes its tables use one.",
   "Excel and PowerPoint: the font and size, header row, frozen header, and print setup Check expects in a workbook; "
   "the fonts allowed, smallest text and titles, slide size, marking on every slide and slide titles in a deck.",
   "Pages, cover and back cover: the cover and back cover pages Learn from a file took (pictures included). Make a "
   "template puts them in; Fix a Copy reports a draft whose cover or back cover is built differently. Clear removes one.",
   "Table types, row rules, captions and numbering, pages (the page scheme with cover and back cover), page setups, "
   "headers and footers, the TOC and its entry styles, lists, terms, Excel and PowerPoint, and check options each have their own section.",
   "This effort: choose its profile, then Fill from the RFP's formatting rules lays the RFP's fonts, margins and "
   "page size over it for this effort only. Press Save.",
   "Make a template...: a Word template (.dotx) with every value in force, from the Stationkeeper base (cover, front "
   "matter, a chapter with a sample table, an appendix) or starting from a template of yours (only read). It goes to "
   "the Templates folder in the output folder, dated, and is checked against the standard; Word updates its fields.",
   "Export for review... makes a workbook of every value and where it is set."],
  ["Blank means not set: a rule nobody sets is not checked and not written."]),
 ("audit", "Production", "Audit",
  "Checks Word, Excel and PowerPoint files against every standard that applies to them and lists every finding: styles, "
  "fonts, tables, captions, the TOC, cross-references, pages, headers and footers, lists, terms, sheets, slides and "
  "graphics. Read only: nothing is changed and no copy is made, so it is safe on a file others have open on SharePoint.",
  "Before each color review and before production, on every volume; and any time someone asks whether a file meets the standard.",
  ["Add the Volumes folder (or Add files...). Each file uses its profile in Production Standards, as Fix a Copy would.",
   "Press Audit. The results show what each area found, per file.",
   "Click a file to see its findings; pick an area to narrow them.",
   "Export findings... makes a workbook of every finding, for the editors."],
  ["Fix a Copy makes a dated copy with the fixes; Audit only reports."]),
 ("fixcopy", "Production", "Fix a Copy (Beta)",
  "Beta: still being proven on real documents, so check every copy it makes. Fixes a draft's formatting to the production standard in a dated copy. Your file is never changed: it is read once, "
  "and a file someone has open is not copied at all.",
  "Before each color review and for final production, on each volume.",
  ["The effort's type (set when you start it, or in Production Standards) decides which profiles its drafts use.",
   "Check the output folder (Change... sets it; the default is Production Copies in the Stationkeeper data folder). "
   "Each effort's copies go in a folder with the effort's name inside it. Copies never go beside the original.",
   "Check every draft reads every listed draft against its own profile and lists what each breaks, by area (what "
   "Format Check used to do); double-click one to see its fixes. Export findings... makes a workbook of every finding.",
   "Pick a draft from the Volumes folder, or Add a file.... Its volume name comes from the Deliverables board when the "
   "draft is a deliverable's file; otherwise type it. The solicitation comes from the effort's basics. Headers and "
   "footers are built only when both are set. Profile: the draft's own (kept on the Deliverables board for a "
   "deliverable), or the effort's. Press Check; each area shows what it found, each style that differs from the style "
   "library property by property.",
   "What to fix: every fix is listed under its area with what it found; untick any you do not want. Expand a fix to "
   "see each finding and where it is.",
   "Tables: pick a table to see every row's role. Rows in bold wait for your answer; one answer covers every row "
   "like it. Select rows and press C, H, 2, S, B, U, T, N or K to set their role; change the table type if needed.",
   "A table question: choose the role; Make it a rule saves it (for the draft's profile, or this effort only) so rows "
   "like these never ask again.",
   "Excel and PowerPoint: a workbook or a deck in the Volumes folder is listed too (Add a file... takes one from "
   "anywhere). Check reads it against the profile's Excel and PowerPoint values and lists what differs, sheet by sheet "
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
   "Fix a Copy and Make a template are Preview tools: off for the team until the proposal manager turns them on in "
   "Settings > Roles and Preview tools."]),
 ("postsub", "Post-Submission", "Checklist",
  "What the team does after the proposal goes in: owners, due dates and done.",
  "The proposal is submitted.",
  ["Press Mark submitted... The checklist appears.",
   "Give each item an owner and a due date. + Item adds one.",
   "Save as default... keeps this checklist for new efforts."],
  ["Export to Excel... shares the checklist."]),
 ("keywords", "Post-Submission", "Keywords",
  "The effort's keywords for SharePoint: what the customer asked for and what you proposed, with reasons, to file the "
  "submitted proposal.",
  "After submission, when the proposal is filed.",
  ["Press Suggest keywords. Each suggestion says why.",
   "Add selected keeps them; Not a keyword drops one.",
   "Export for SharePoint... makes the list to tag the submitted proposal."],
  []),
 ("exportall", "Effort files", "Export All",
  "Every feature's outputs in one dated folder.",
  "At a gate, at submission, or to hand the effort's outputs to someone.",
  ["Press Export all... and choose where the dated folder goes."],
  ["Every export is dated and kept in the effort's folder. Nothing is overwritten."]),
 ("settings", "Effort files", "Settings",
  "This PC's settings: work mode, time zone, efforts, author list, stages and roles, folders and file names, document "
  "types, custom dictionaries, branding, team pack, master database, backups, updates, and help.",
  "Setting up the app, joining a team, or installing an update.",
  ["Where Stationkeeper is used sets the work mode: Offline, Connected or SCIF-ready.",
   "Custom dictionaries keeps your team's words for Word: + Dictionary..., type words or Import a .dic..., Add the "
   "effort's acronyms, then Export for Word... and add the file in Word (File > Options > Proofing > Custom Dictionaries).",
   "Branding shows the company logos. They are built into Stationkeeper; nobody changes them from here.",
   "Roles and Preview tools: your role and where it comes from (People and roles in the effort, or your own choice in "
   "Customize...), hide other roles' tools, and show the stage's tools at the top of the menu. The proposal manager turns "
   "Preview tools (Fix a Copy, Make a template) on or off for the team; a team pack carries the choice.",
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
TOPIC = {t[0]: t for t in TOPICS}


def topic_html(key):
    t = TOPIC.get(key) or TOPIC["start"]
    k, group, title, what, when, steps, tips = t
    e = html.escape
    out = [f"<p style='color:#6b7686;font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin:0'>{e(group)}</p>",
           f"<h1 style='margin:2px 0 8px 0;font-size:24px'>{e(title)}</h1>",
           f"<p style='font-size:15px;margin:0 0 10px 0'>{e(what)}</p>",
           f"<p style='margin:0 0 12px 0'><b>Use it when:</b> {e(when)}</p>"]
    if k == "keys":
        from .helpcenter import SHORTCUTS
        out.append("<table cellpadding='5' style='border-collapse:collapse'>")
        for where, key_, does in SHORTCUTS:
            out.append(f"<tr><td style='color:#6b7686'>{e(where)}</td><td><b>{e(key_)}</b></td><td>{e(does)}</td></tr>")
        out.append("</table>")
    if steps:
        out.append("<h3 style='margin:14px 0 6px 0'>Steps</h3><ol style='margin-top:0'>")
        out += [f"<li style='margin-bottom:6px'>{e(s)}</li>" for s in steps]
        out.append("</ol>")
    if tips:
        out.append("<h3 style='margin:14px 0 6px 0'>Tips</h3><ul style='margin-top:0'>")
        out += [f"<li style='margin-bottom:6px'>{e(s)}</li>" for s in tips]
        out.append("</ul>")
    return "".join(out)


class GuideWindow(QDialog):
    """Topics on the left (grouped as the menu, with search), the topic on the right, Go to this page."""
    def __init__(self, host, key="start"):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Stationkeeper Guide")
        self.resize(1180, 820)
        lay = QHBoxLayout(self)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search the Guide")
        self.search.textChanged.connect(self._filter)
        self.list = QListWidget(); self.list.setMinimumWidth(250)
        self.list.currentItemChanged.connect(lambda cur, _old: self.show_topic(cur.data(Qt.UserRole)) if cur and cur.data(Qt.UserRole) else None)
        lv.addWidget(self.search); lv.addWidget(self.list, 1)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(False); self.view.setOpenLinks(False)
        row = QHBoxLayout()
        self.prev = D.button("< Previous", None, lambda: self._step(-1))
        self.next = D.button("Next >", None, lambda: self._step(1))
        self.go_btn = D.button("Go to this page", "primary", self._go)
        row.addWidget(self.prev); row.addWidget(self.next); row.addStretch(1); row.addWidget(self.go_btn)
        rv.addWidget(self.view, 1); rv.addLayout(row)
        lay.addWidget(left); lay.addWidget(right, 1)
        self.key = ""
        self._fill()
        self.show_topic(key if key in TOPIC else "start")

    def _fill(self, words=""):
        self.list.blockSignals(True)
        self.list.clear()
        words = words.lower().split()
        group = None
        for t in TOPICS:
            if words and not all(w in " ".join([t[2], t[3], t[4], *t[5], *t[6]]).lower() for w in words):
                continue
            if t[1] != group:
                group = t[1]
                h = QListWidgetItem(group.upper()); h.setFlags(Qt.NoItemFlags)
                f = h.font(); f.setPointSizeF(f.pointSizeF() * 0.85); f.setBold(True); h.setFont(f)
                self.list.addItem(h)
            it = QListWidgetItem("   " + t[2]); it.setData(Qt.UserRole, t[0])
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._select(self.key)

    def _filter(self, text):
        self._fill(text)
        keys = self.shown()
        if keys and self.key not in keys:
            self.show_topic(keys[0])

    def shown(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]

    def _select(self, key):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == key:
                self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
                return

    def show_topic(self, key):
        self.key = key
        self.view.setHtml(topic_html(key))
        self._select(key)
        pages = getattr(self.host, "pages", {}) or {}
        self.go_btn.setVisible(key in pages)
        order = [t[0] for t in TOPICS]
        i = order.index(key)
        self.prev.setEnabled(i > 0); self.next.setEnabled(i < len(order) - 1)

    def _step(self, d):
        order = [t[0] for t in TOPICS]
        self.show_topic(order[max(0, min(len(order) - 1, order.index(self.key) + d))])

    def _go(self):
        if self.key in getattr(self.host, "pages", {}):
            self.host.go(self.key)


def current_key(host):
    """The menu key of the page showing, so F1 opens its topic."""
    try:
        cur = host.stack.currentWidget()
        for k, pg in host.pages.items():
            if pg is cur:
                if k not in TOPIC:                     # 3.16.0: a tab's page opens its menu item's topic
                    from .mainwin import HEAD_OF
                    k = HEAD_OF.get(k, k)
                return k if k in TOPIC else "start"
    except Exception:
        pass
    return "start"


def open_guide(host, key=None):
    g = getattr(host, "_guide", None)
    if g is None:
        g = host._guide = GuideWindow(host, key or current_key(host))
    else:
        g.show_topic(key or current_key(host))
    g.show(); g.raise_(); g.activateWindow()
    return g
