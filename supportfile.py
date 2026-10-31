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
    "3.3.0": ["Deliver > Wall of Truth: one approved value for every fact and number, names and terms; Check the drafts finds "
              "every number that disagrees, every old value still in use and every wrong form, by volume and section.",
              "The team's wall carries company facts to every effort; Export the wall makes the page to post."],
    "3.2.0": ["Win themes on Effort Home: themes and discriminators with proof and sections; Check the drafts says where each "
              "is said and where it is missing.",
              "Deliver > Storyboards: one sheet per section before the first draft, exported to Word for the review.",
              "Try the sample effort: a fictional effort with its RFP read in, to learn on."],
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


def make(out_path, app_version, log_dir, settings=None, program_check=None, health=None, data_why="", qt_version=""):
    """Write the support file. Returns {"path", "files"} (the names inside)."""
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
        z.writestr("READ ME.txt", "Stationkeeper support file\r\n\r\nVersions, content-free logs and checks, for whoever maintains "
                                  "Stationkeeper. It holds no document text, terms, names, file names or folder paths.\r\n")
        files.append("READ ME.txt")
    os.replace(tmp, out_path)
    return {"path": out_path, "files": files}
