"""The Guide (3.0.2): how to use every page, in the order of the menu, with a picture of the real page.

F1 opens it at the page you are on; Help and support in Settings opens it at the start. Each topic says what the page
is for, when to use it, the steps with the real button names, and a few tips. Go to this page jumps there. The pictures
are made by tools/make_guide_shots.py from a fictional effort (Kestrel Thermal), with a neutral user and no personal
paths, and live in assets/help as guide_<topic>.png. A topic without its picture still reads well."""
import html
import os
import sys
from PySide6.QtCore import Qt, QUrl
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
  ["Open the menu on the left. Its groups follow an effort from start to finish: Effort, Compliance, Documents, "
   "Deliver, Response Quality, Effort Files.",
   "Start an effort on All Efforts, or open one you already have.",
   "Add the customer's documents in Library, read them in Read RFP, and decide every sentence in Review.",
   "Make the matrix and the Response Setup documents from your decisions, then check the volumes in Response Quality."],
  ["Press F1 on any page to open this Guide at that page.",
   "Press Ctrl+K to find a page, an effort, a sentence or a person from anywhere.",
   "Every decision saves as you make it. Closing the app never loses work."]),
 ("efforts", "Getting started", "All Efforts",
  "Every effort on this PC, a new one, and work not filed under an effort yet.",
  "You start a new proposal, switch efforts, or pick up an effort a teammate handed you.",
  ["Press + Add an Effort (or open Effort Home with no effort open). Type a name and press Create effort. The picture, "
   "client, solicitation, due date and proposal manager are optional; the effort's folders are made for you.",
   "Click an effort's card to open it. The menu then works on that effort.",
   "To pick up a teammate's effort, press Import effort package... and choose the .skpkg file they sent.",
   "To read documents before an effort exists, press Start without an effort: open Unfiled. Make it an effort... later "
   "keeps the work."],
  ["Each effort keeps its own decisions, lists and settings. Nothing crosses between efforts.",
   "The card shows the stage, the due date and what needs attention."]),
 ("mywork", "Getting started", "My Work",
  "One person's work in every effort on this PC, soonest first: tasks, questions for them, customer questions, "
  "deliverables and graphic needs they own, the requirements they answer, and the sections they lead with page budgets.",
  "Every morning, and when you work on several efforts at once.",
  ["Pick a name in Work for (yours shows first once Customize Home > I am is set).",
   "Read Soonest first: late items are red and on top; requirements are due when the current stage ends.",
   "Double-click a row to open that effort at the right page. By effort shows each effort's stage, due date and sections.",
   "Export... makes a workbook of the list for a status meeting."],
  ["My Work only reads the efforts; nothing changes until you open one.",
   "Refresh reads every effort again after teammates' changes come in."]),
 ("home", "Effort", "Effort Home",
  "The effort at a glance: stage, gate goals, tasks, questions, notes, the calendar, contacts, submission and "
  "formatting rules, customer questions, evaluation factors, and the graphics the response needs.",
  "Every day: see what is due, add tasks and questions, and move the effort to its next stage.",
  ["Read the banner: due date in your time zone and the submission's, countdown, and whether the effort is page-limited.",
   "Add work with + Task, + Question, + Note or + Goal. Assign... gives a question to a person.",
   "Click a day on the calendar to add a due date, an event or a task due that day.",
   "Schedule from due date... dates every stage backward from the due date (or fits them from a start date), skipping "
   "weekends and your holidays. Every date shows before Set the dates.",
   "When you open the effort, Since you last opened it lists what teammates did since your last visit. Got it hides it.",
   "When the team is ready, press Move stage... The stage's gate goals show what has to be done first."],
  ["Click the effort image, or drop a picture file on it, to set or change it.",
   "Customize Home... chooses which cards show.",
   "Cards such as Submission instructions and Evaluation and hot buttons fill in from what you capture in Review.",
   "Export tasks and questions... makes a workbook for a meeting.",
   "Win themes keeps the themes and discriminators agreed at kickoff, with their proof and sections. Check the drafts reads "
   "the Word files in the Volumes folder and says where each theme appears and where a linked section never says it.",
   "Graphic needs lists what was tagged as needing a graphic. Open goes to the sentence; click one to mark it In work or "
   "Done; Graphic on a note adds that note; Export... makes a workbook for the graphics team."]),
 ("deliverables", "Effort", "Deliverables",
  "Every deliverable of the effort on one board: volumes, forms, plans and CDRLs, with owner, status, pages against "
  "the limit and what is missing.",
  "You track what has to be turned in and who owns each piece.",
  ["Press + Deliverable... to add one, or capture one from a sentence in Review (More captures).",
   "Click a card to see its requirements, what a new customer version changed, its submission check and its files.",
   "Double-click a requirement to open it in Review."],
  ["A Volume deliverable links to its volume by name.",
   "View: List shows the same deliverables as a table."]),
 ("dashboard", "Effort", "Dashboard",
  "The whole effort on one screen: compliance progress, owners, changes to decide, and quality checks.",
  "You report status, or want to see what is behind.",
  ["Read the tiles. Each one says what it counts.",
   "Click a tile, or its button (Review, Prove, Response Setup), to go where the work is."],
  ["Requirements with no section or no owner show here first."]),
 ("record", "Effort", "Effort Record",
  "The effort's details, team and roles, stages and gates, status reports, the effort package and backups.",
  "You set up the effort, change its team or stages, hand it to someone, or report status.",
  ["Fill in the details and press Save details. Choose people... adds the team from the author list.",
   "Edit the stages and press Save stages. + Stage adds one; Up and Down reorder them.",
   "Effort status (Word)... and Effort summary (Word)... make reports for a meeting.",
   "Save effort package... makes one .skpkg file with everything, for a teammate or a backup."],
  ["Back up now makes a backup at once. Restore... brings one back.",
   "Open the readable copy shows every captured item as plain files you can open without the app."]),
 ("reviews", "Effort", "Color Reviews",
  "Color team review packets: a Word file with every requirement under its section, for reviewers to give a verdict "
  "and comments, read back onto each requirement.",
  "Red team, gold team, or any review where people mark up the response against the requirements.",
  ["Press Build the packet... and choose the stage. Send the Word file to the reviewers.",
   "When it comes back, press Read back a packet... Verdicts and Word comments land on each requirement.",
   "See the score by section, and open a requirement to read its comments."],
  ["Reviewers only need Word. The packet holds no app data beyond the requirements and sections."]),
 ("read", "Compliance", "Read RFP",
  "Brings the customer's documents into the review: every sentence is cut out of the page, scans and pictures are "
  "read with OCR, and nothing is dropped.",
  "A new solicitation arrives, or you add more documents to the review.",
  ["Press Add files..., or tick documents already in Library.",
   "Press Read. The progress panel shows each file and page.",
   "Press Go to Review to decide the sentences."],
  ["Scanned pages and pictures are read by the OCR reader (AI and ML), on this PC.",
   "Prove checks later that every word reached the review."]),
 ("structure", "Compliance", "Structure",
  "The sections of your response: volumes, headings and page limits, from the RFP, a Word outline, or built as you go.",
  "Before or while you place requirements, when you know how the response will be organized.",
  ["Choose how to start: What the RFP prescribes, RFP headings, RFP outline, Word outline..., or Blank.",
   "Press Apply. Edit the sections in place.",
   "Volumes... sets each volume's page limit. People... gives a section its writers. Page budget... splits a volume's "
   "page limit across its sections (evenly or by requirements) and shows the total against the limit and the draft."],
  ["You can also build the structure in Review as you read: + Volume and Copy RFP section."]),
 ("assign", "Compliance", "Review",
  "The customer's document as it looks, every sentence boxed. You decide each sentence, place it in your response, "
  "and capture what it holds. This is where an effort's review happens.",
  "From the first read until every sentence is decided, and again when a new version arrives.",
  ["Click a sentence. Press L (Instructions), E (M, Evaluation) or R (SOW, Work) to make it a requirement in the "
   "target section; C for context that supports the last requirement; G for the customer's own sentence; X to clear.",
   "Drag across words inside the sentence to pick just those words. Capture files them: a contact, submission or "
   "formatting rule, acronym, key date or customer question. More captures... adds evaluation factors, page limits, "
   "deliverables, effort details and hot buttons.",
   "Graphic need (P) tags a concept that needs a graphic, from the sentence or the words you picked; it lists on Effort Home.",
   "Several sentences at once: Ctrl+click, drag a box, Select undecided, or Ctrl+A. The bar above the page shows how many, "
   "with Decide all, Put all in section and Author for all.",
   "+ Task... and + Ask the team... put work and questions on the sentence.",
   "When a document is done, press Mark reviewed, then Next document."],
  ["J joins sentences; S splits one where you clicked (Split here).",
   "Ctrl+Z undoes. Ctrl+F finds a sentence by its words or number.",
   "On a later version, changed sentences are outlined in amber and new ones in green. Show the old page shows what it "
   "was."]),
 ("prove", "Compliance", "Prove",
  "Proof that every line of every customer document was read and decided.",
  "Before you call the review finished, and before a gate.",
  ["Press Run the text check. It compares every word of the documents with the review.",
   "If anything is missing, press Add the missing lines. They go in their place in the document.",
   "Search finds a sentence by its words or number and opens it in Review."],
  ["Nothing counts as done while a line is undecided."]),
 ("crosswalk", "Compliance", "L/M Crosswalk",
  "Each instruction (L), the evaluation factor (M) that scores it, and the work (SOW) it describes, side by side.",
  "You check that every evaluated factor has an instruction and a place in the response.",
  ["Read the rows. Gaps show where an instruction has no factor or a factor has no instruction.",
   "Press Export the crosswalk... for a review or the proposal manager."],
  ["The crosswalk fills in from your L, M and SOW decisions in Review."]),
 ("library", "Documents", "Library",
  "Every document of the effort: customer files and every version of them, categories, folders, tags and roles.",
  "Documents arrive: the RFP, amendments, Q&A rounds, forms, task orders.",
  ["Press Add files... or Add a folder... Stationkeeper suggests the type, its initial (R, A1, TO1) and whether it is "
   "a new version of a document you have.",
   "Watched folders... checks the customer folder for new, changed and missing files.",
   "Select a document and press Read it in Review, or Open in Review.",
   "For an amendment that says what to change, press Apply its instructions... to make the Conformed version."],
  ["Initial and type... and Rename... fix a document's details. The customer's files are never changed.",
   "A document marked above CUI is refused on a regular install. Follow your site's spill procedure."]),
 ("compare", "Documents", "Changes",
  "What a new version changed, what it touches in your review, and a decision on every change.",
  "An amendment or new version arrives.",
  ["Pick the old and new versions. The changed, added and removed sentences are listed.",
   "Decide each change: update the requirement, Not ours, or a question for the customer.",
   "Export (Word)..., Redline (Word)... or Change list (Excel)... share the changes."],
  ["Adding a new version says at once what it changed. Review the changes opens this page on that pair."]),
 ("requirements", "Documents", "Submission Rules",
  "What the customer requires of the submission: due date, delivery, copies, formats, file names, page limits and "
  "formatting, with the document that set each rule and what changed it.",
  "You plan the submission, or a new version changes a rule.",
  ["Read the rules. Each shows its source document and section.",
   "Press Add a requirement... for a rule you found yourself.",
   "Use the new due date takes a changed due date into the effort."],
  ["Capture > Submission and Capture > Formatting in Review fill this page from the customer's words."]),
 ("custqa", "Documents", "Customer Q&A",
  "The formal questions you submit to the customer: their exact words and where they are, your question, its status "
  "and the answer.",
  "Before the questions-due date, and when the answers come back.",
  ["In Review, select a sentence (or drag across words) and use Capture > Question. It quotes the customer and the "
   "place for you.",
   "Here, edit the question, its category and owner, and move it from Draft to Approved.",
   "Export to Word or Excel, or fill the customer's own Q&A form. Exporting can mark the questions Submitted.",
   "When answers arrive, add each answer and the document it came in."],
  ["Every exported question names the customer file it is about. Owner, status and notes never go out."]),
 ("matrix", "Deliver", "Matrix",
  "The compliance matrix as the customer will see it, built from your decisions in Review.",
  "You deliver the matrix, or share it with the team.",
  ["Choose the columns. Add a column... adds your own.",
   "Press Export the matrix..., or Export the compliance package... for the matrix with its reports.",
   "Save as the team default keeps this layout for new efforts."],
  ["The exported workbook is a dated copy. Exports are never overwritten."]),
 ("setup", "Deliver", "Response Setup",
  "The Word documents your writers start from: each section's headings with the RFP text placed under them, "
  "references on the same line, and management direction.",
  "Before writing starts, and after the review changes.",
  ["Check each section's requirements. Up and Down reorder; Take out of this section removes one.",
   "Press Export the setup... One Word file per volume.",
   "Export changes only... gives writers just what changed since the last setup."],
  ["The export is plain: RFP text in purple, direction in green, ready for your team's own styles."]),
 ("storyboards", "Deliver", "Storyboards",
  "One sheet per section before anyone drafts: the key message, the win themes it carries, the approach, features "
  "with benefits and proof, and its graphics, beside its requirements and page budget.",
  "After the Response Setup goes out and before the first draft; review them at a storyboard review.",
  ["Pick a volume, then a section on the left. Its lead, writers, page budget and requirements show at the top.",
   "Write the key message and the approach. Tick the win themes the section carries. + Feature adds a feature with its "
   "benefit and proof.",
   "Set the status as it moves: Drafting, Ready for review, Approved. It saves as you type.",
   "Export the volume... makes one Word file, a page per section, for the review. Export this section... makes one."],
  ["Win themes come from Effort Home (+ Theme...); a theme linked to the section is ticked for you.",
   "Graphic needs tagged in Review for the section list here too."]),
 ("postsub", "Deliver", "Post-Submission",
  "What the team does after the proposal goes in: owners, due dates and done.",
  "The proposal is submitted.",
  ["Press Mark submitted... The checklist appears.",
   "Give each item an owner and a due date. + Item adds one.",
   "Save as default... keeps this checklist for new efforts."],
  ["Export to Excel... shares the checklist."]),
 ("acronyms", "Response Quality", "Customer Terms",
  "The acronyms and terms the customer's documents use, offered to the effort list.",
  "At the start, so writers use the customer's own terms and definitions.",
  ["Press Scan the customer documents (or Scan files... or Scan a folder...).",
   "For each term: Use this (a definition), Add to effort list, Not a term, or Needs author.",
   "Export the report... shares the findings."],
  ["The customer's own definitions win over the master database."]),
 ("acrlist", "Response Quality", "Effort List",
  "The effort's glossary with approved definitions and who approved them.",
  "Throughout the effort, as terms are added and approved.",
  ["Edit a definition, or press Approve... to record the approver.",
   "Press Export the effort list... for the team or the proposal."],
  ["The effort list is an ordinary Excel workbook in the effort's folder."]),
 ("qa", "Response Quality", "Submission Check",
  "The volumes you will submit, checked against the effort list, first use, banned words and page limits.",
  "Before each gate and before submission.",
  ["Press Add volumes... and choose the Word files, then Check the submission volumes.",
   "Fix what it finds in Word. Add missing to the effort list adds terms the list does not have.",
   "Export report (Excel)... records the check."],
  ["First use of an acronym belongs in running text, not in a figure or table."]),
 ("lists", "Response Quality", "Lists to Submit",
  "The acronym list for each volume, built from what that volume actually uses.",
  "At the end, when the volumes are final.",
  ["Review each volume's list.",
   "Press Export the lists (Word)... or Export (Excel)...",
   "Record in the effort list notes which volume uses each term."],
  []),
 ("keywords", "Response Quality", "Keywords",
  "The effort's keywords for SharePoint: what the customer asked for and what you proposed, with reasons.",
  "Along the way, and after submission when the proposal is filed.",
  ["Press Suggest keywords. Each suggestion says why.",
   "Add selected keeps them; Not a keyword drops one.",
   "Export for SharePoint... makes the list to tag the submitted proposal."],
  []),
 ("exportall", "Effort Files", "Export All",
  "Every feature's outputs in one dated folder.",
  "At a gate, at submission, or to hand the effort's outputs to someone.",
  ["Press Export all... and choose where the dated folder goes."],
  ["Every export is dated and kept in the effort's folder. Nothing is overwritten."]),
 ("settings", "Effort Files", "Settings",
  "This PC's settings: work mode, time zone, efforts, author list, stages and roles, folders and file names, document "
  "types, custom dictionaries, branding, team pack, master database, backups, updates, and help.",
  "Setting up the app, joining a team, or installing an update.",
  ["Where Stationkeeper is used sets the work mode: Offline, Connected or SCIF-ready.",
   "Custom dictionaries keeps your team's words for Word: + Dictionary..., type words or Import a .dic..., Add the "
   "effort's acronyms, then Export for Word... and add the file in Word (File > Options > Proofing > Custom Dictionaries).",
   "Branding shows the company logos. They are built into Stationkeeper; nobody changes them from here.",
   "Install a team pack... takes your team's stages, document types, folders and author list in one step.",
   "In Updates, Install update pack... installs a new version from its .skupdate file. Undo last update goes back one step.",
   "Help and support opens this Guide, the shortcuts, what's new, and the support file."],
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


def shot_path(key):
    """assets/help/guide_<key>.png, in the program or beside the source."""
    name = f"guide_{key}.png"
    for base in (getattr(sys, "_MEIPASS", ""), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        p = os.path.join(base, "assets", "help", name)
        if base and os.path.isfile(p):
            return p
    return ""


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
    p = shot_path(k)
    if p:
        out.append(f"<p><a href='shot:{k}'><img src='{QUrl.fromLocalFile(p).toString()}' width='780'></a><br>"
                   "<span style='color:#6b7686;font-size:12px'>Click the picture to see it full size.</span></p>")
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
        self.view.anchorClicked.connect(self._link)
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

    def _link(self, url):
        """A picture clicked: the same picture full size, in its own window."""
        s = url.toString()
        if s.startswith("shot:"):
            p = shot_path(s[5:])
            if p:
                self.big = picture_window(self, p)

    def _step(self, d):
        order = [t[0] for t in TOPICS]
        self.show_topic(order[max(0, min(len(order) - 1, order.index(self.key) + d))])

    def _go(self):
        if self.key in getattr(self.host, "pages", {}):
            self.host.go(self.key)


def picture_window(parent, path):
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel, QScrollArea
    dlg = QDialog(parent); dlg.setWindowTitle("Stationkeeper Guide: picture")
    lay = QVBoxLayout(dlg); sa = QScrollArea(); lab = QLabel(); lab.setPixmap(QPixmap(path)); sa.setWidget(lab)
    lay.addWidget(sa); dlg.resize(1400, 900); dlg.show()
    return dlg


def current_key(host):
    """The menu key of the page showing, so F1 opens its topic."""
    try:
        cur = host.stack.currentWidget()
        for k, pg in host.pages.items():
            if pg is cur:
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
