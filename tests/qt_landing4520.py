"""4.52.0 The landing page and the menu, offscreen. Nothing open: the Overview is the landing (a place to drop a document,
three door cards, no steps) and the menu shows no step, no Calendar and no Tasks. A door asked with a new effort makes
it and lands on Acronyms; the menu then shows the steps, Calendar and Tasks, and the Overview the next step with the
doors' row under it. Shred to setup adds the document to Documents as the customer's and lands on Shred; with a program
picked it is refused and nothing is added. Check a document lands on Audit with the file. A program shows only the doors
a program has. Closing everything brings the landing and the short menu back, while Calendar and Tasks stay. Calendar
and Tasks with nothing open read across efforts, with nothing that needs the open effort. Ctrl+K lists only what can run
now. Fictional (Kestrel, Heron, Osprey)."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
A.CONFIG_DIR = os.path.join(A.DATA_DIR, "config"); os.makedirs(A.CONFIG_DIR, exist_ok=True)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import docversions as DV, doors as DR, effortcal as EC, effortrec as R, programs as PG, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, doorsview as DVW, helpcenter as HC, programsview as PV
from skqt import mainwin as MW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


app = QApplication([]); D.apply(app)


def pump(n=5):
    for _ in range(n):
        app.processEvents(); time.sleep(0.01)


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        pump(1)
    return cond()


w = MW.MainWindow(app, A.CONFIG_DIR, A.APP_VERSION); w.resize(1500, 950); w.show(); pump()
statuses = []
_status = w.status
w.status = lambda t, *a, **k: (statuses.append(t), _status(t, *a, **k))
docx = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
pdf = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Program_Manual.pdf")
STEPS = ("library", "graphics", "assign", "matrix", "setups", "drafts", "finalcheck")


def shown(key):
    b = w.step_btns.get(key)
    return b is not None and not b.isHidden()


# ---- 1. nothing open, no effort yet
w.go("overview"); pump()
ov = w.overview_page
check("nothing open: the Overview shows the landing, no effort blocks", w.stack.currentWidget() is ov and ov.landing.isVisibleTo(w)
      and not ov.body.isVisibleTo(w) and not ov.program.isVisibleTo(w) and w.page_title.text() == "Overview")
check("... three door cards, in order, of one size", list(ov.landing.cards) == ["acronyms", "shred", "check"]
      and len({c.width() for c in ov.landing.cards.values()}) == 1
      and [c.name.text() for c in ov.landing.cards.values()] == ["Acronyms", "Shred to setup", "Check a document"])
check("... a place to drop a document and Choose a file...", ov.landing.drop.isVisibleTo(w) and ov.landing.drop.acceptDrops()
      and ov.landing.choose_btn.text() == "Choose a file..." and ov.landing.choose_btn.isVisibleTo(w))
check("... All tools shows; All Efforts waits until an effort or program exists", ov.landing.tools_btn.isVisibleTo(w)
      and not ov.landing.efforts_btn.isVisibleTo(w))
check("... no path, no step, no counts", not ov.next_card.isVisibleTo(w) and not ov.door_row.isVisibleTo(w))
check("the menu (4.60.0): every step shows with nothing open; Calendar and Tasks are not entries", all(shown(k) for k in STEPS)
      and not {"calendar", "tasks"} & set(w.step_btns))
check("... it shows Overview, Quick tools, the Standards and Formatting entries and Settings",
      all(shown(k) for k in ("home", "tools", "templates", "formatstd", "styles", "designs", "globalstd", "rules", "refs", "audit", "settings")))
check("... there is no EFFORT'S PATH heading", w.group_heads["Effort"] is None)
chosen = []
_choose = DVW.choose
DVW.choose = lambda host, door=None, paths=None, answer=None: chosen.append(door)
card = ov.landing.cards["shred"]
card.setFocus(); QTest.keyClick(card, Qt.Key_Return); QTest.keyClick(card, Qt.Key_Space)
ov.landing.cards["check"].click()
check("a card is reached by keyboard (Enter, Space) and opens its door's file choice", card.focusPolicy() == Qt.StrongFocus
      and chosen == ["shred", "shred", "check"], chosen)
DVW.choose = _choose
check("a file no door reads: refused with a plain sentence", DVW.ask(w, [os.path.join(tmp, "x.zzz")], answer=("acronyms", ("new_effort", "Zed"))) is None
      and statuses[-1] == DVW.CANNOT_READ and w.efforts.get("Zed") is None)

# ---- 2. Acronyms, into a new effort
scans = []
w.acronym_page.scan = lambda paths, folder=None: scans.append(list(paths)) or "scan"
got = DVW.ask(w, [docx], answer=("acronyms", ("new_effort", "Kestrel bid")))
pump()
check("Acronyms with a new effort: made, opened, and it lands on Acronyms scanning the file", got == "Kestrel bid" and w.effort_name == "Kestrel bid"
      and w.stack.currentWidget() is w.acronym_page and scans and docx in scans[-1], (got, w.effort_name, scans))
check("the menu shows the steps, as it did before (4.60.0)", all(shown(k) for k in STEPS))
w.go("overview"); pump()
check("the Overview: the next step, and the doors' row with three doors under it", ov.body.isVisibleTo(w) and ov.next_card.isVisibleTo(w)
      and not ov.landing.isVisibleTo(w) and ov.door_row.isVisibleTo(w) and list(ov.door_row.btns) == ["acronyms", "shred", "check"]
      and ov.door_row.tools_btn.text() == "All tools" and ov.door_row.acceptDrops())
check("... the row sits directly under the next step", ov.door_row.y() > ov.next_card.y()
      and ov.door_row.y() - (ov.next_card.y() + ov.next_card.height()) < 40, (ov.next_card.geometry(), ov.door_row.geometry()))
d = DVW.DoorDialog(w, w, [docx])
labels = [d.where.combo.itemText(i) for i in range(d.where.combo.count())]
check("the door window: the doors that take the file, the open effort first and picked", d.picked() == "acronyms" and d.list.count() == 3
      and labels[0] == "Kestrel bid (open now)" and d.where.picked() == ("home", "Kestrel bid") and d.ok_btn.isEnabled())
d.list.setCurrentRow(1)
labels = [d.where.combo.itemText(i) for i in range(d.where.combo.count())]
check("... Shred to setup lists no program", d.picked() == "shred" and not any("program" in x for x in labels), labels)
d.where.combo.setCurrentIndex(labels.index("A new effort")); d.where.name.setText("kestrel BID")
check("... OK waits while a new name cannot be used", not d.ok_btn.isEnabled())
d.close()
d = DVW.DoorDialog(w, w, [pdf], door="shred")
check("... a PDF: Acronyms and Shred to setup, the door given picked; All tools... is there", d.list.count() == 2 and d.picked() == "shred"
      and d.all_btn.text() == "All tools...")
d.close()

# ---- 3. Shred to setup and Check a document
got = DVW.run(w, "shred", [pdf], ("home", "Kestrel bid"), choices={})
ok = wait(lambda: w.stack.currentWidget() is w.assign_page, 90)
lib = DV.Library(w.ws.p("documents")).load()
doc = next((x for x in lib.all if x.get("versions") and x["versions"][-1].get("file") == os.path.basename(pdf)), None)
check("Shred to setup: added to Documents as the customer's document, for the shred, then on Shred", got == "Kestrel bid" and ok
      and doc is not None and doc.get("category", "customer") == "customer" and lib.role_of(doc) == "matrix",
      (got, w.stack.currentWidget().objectName(), [(x.get("name"), x.get("category")) for x in lib.all]))
check("... Documents' hook is used once and cleared", getattr(w.library_page, "then", None) is None)
n_docs = len(lib.all)
PV.new_program(w, "Osprey"); pump()
w.open_effort("Kestrel bid"); w.effort_box.setCurrentText("Kestrel bid"); pump()
got = DVW.ask(w, [pdf], answer=("shred", ("home", "Osprey")))
got2 = DVW.ask(w, [pdf], answer=("shred", ("new_program", "Heron archive")))
check("Shred to setup with a program picked: refused with the sentence, nothing added, nothing made", got is None and got2 is None
      and statuses[-1] == "Shred to setup works in an effort. Pick an effort, or a new one." and w.effort_name == "Kestrel bid"
      and len(DV.Library(w.ws.p("documents")).load().all) == n_docs and w.efforts.get("Heron archive") is None)
w.audit_page.files.clear()
got = DVW.ask(w, [docx], answer=("check", ("home", "Kestrel bid")))
pump()
check("Check a document: lands on Audit with the file", got == "Kestrel bid" and w.stack.currentWidget() is w.audit_page
      and docx in w.audit_page.paths())

# ---- 4. a program open
root = os.path.dirname(w.efforts.get("Osprey")["path"])
before = sorted(os.listdir(root))
got = DVW.ask(w, [docx], answer=("check", ("home", "Osprey")))
pump()
check("Check a document in a program: on Audit with the file, and no folder made in the program", got == "Osprey"
      and PV.is_open(w) and w.stack.currentWidget() is w.audit_page and docx in w.audit_page.paths() and sorted(os.listdir(root)) == before,
      (got, sorted(os.listdir(root)), before))
w.audit_page.run(wait=True)
check("... it runs against the Global Standards with no error", docx in w.audit_page.results and "Nothing was changed" in w.audit_page.status.text())
w.go("overview"); pump()
pp = ov.program
check("a program's Overview shows the row with the doors a program has, and none other", pp.isVisibleTo(w)
      and list(pp.doors.btns) == list(DR.for_home("program")) and pp.doors.isVisibleTo(w)
      and pp.add_btn.text() == "Add documents" and not hasattr(pp, "acr_btn"))
f = HC.Finder(w)
pages = {a[1] for k, _t, _s, a in f.entries if k == "Page"}
out = {k for k in pages if MW.RAIL_OF.get(k, MW.HEAD_OF.get(k, k)) in PG.OUT}
check("Ctrl+K in a program: no page of the effort's steps, Calendar or Tasks", not out and "overview" in pages
      and not any(MW.HEAD_OF.get(k) == "home" and k != "overview" for k in pages), out)
dos = [t for k, t, _s, _a in f.entries if k == "Do"]
check("... the doors a program has", "Open a document with Acronyms" in dos and "Check a document" in dos
      and "Shred a customer document to setup" not in dos, dos)
f.close()

# ---- 5. close everything
w.close_effort(); w.go("overview"); pump()
check("closing brings the landing back", ov.landing.isVisibleTo(w) and not ov.body.isVisibleTo(w) and not ov.program.isVisibleTo(w))
check("... and the menu stays as it was (4.60.0: no entry comes or goes)", all(shown(k) for k in STEPS))
check("... All Efforts now shows on the landing", ov.landing.efforts_btn.isVisibleTo(w))

# ---- 6. Calendar and Tasks with nothing open
w.efforts_page.add_effort({"name": "Heron", "path": os.path.join(A.DATA_DIR, "Efforts", "Heron", "Heron_Effort_List.xlsx")})
pump(); w.close_effort(); pump()
today = datetime.date.today()
for name, title, days in (("Kestrel bid", "Pink team", 4), ("Heron", "Kickoff", 9)):
    import workspace as W
    rec = R.Record(W.data_dir_for(w.efforts.get(name)["path"]))
    EC.add_entry(rec, kind="Meeting", title=title, date=(today + datetime.timedelta(days=days)).isoformat())
w.go("calendar"); pump()
cp = w.calendar_page if hasattr(w, "calendar_page") else w.pages["calendar"]
rows = cp.across.rows
check("Calendar with nothing open: one list across efforts, both efforts' dates with their names", cp.across.isVisibleTo(w)
      and not cp.body.isVisibleTo(w) and any(r["effort"] == "Kestrel bid" and "Pink team" in r["what"] for r in rows)
      and any(r["effort"] == "Heron" and "Kickoff" in r["what"] for r in rows)
      and cp.across.table.item(0, 2).text() in ("Kestrel bid", "Heron"), rows)
check("... no add control shows (never greyed)", not cp.bar.isVisibleTo(w) and not cp.add_btn.isVisibleTo(w))
check("... no program in it", not any(r["effort"] == "Osprey" for r in rows))
k = next(i for i, r in enumerate(rows) if r["effort"] == "Heron")
cp.across.open_row(k); pump()
check("... a row's Open opens that effort on its Calendar, the others under it", w.effort_name == "Heron" and w.stack.currentWidget() is cp
      and cp.body.isVisibleTo(w) and cp.others.isVisibleTo(w) and {r["effort"] for r in cp.others.rows} == {"Kestrel bid"})
w.close_effort(); pump()
w.go("tasks"); pump()
tp = w.pages["tasks"]
check("Tasks with nothing open: Mine, across efforts only; nothing that needs the open effort", tp.view == "mine"
      and not tp.bar.isVisibleTo(w) and not any(b.isVisibleTo(w) for b in tp.view_btns.values()) and tp.who.isVisibleTo(w))
check("... set_view cannot pick This effort with nothing open", tp.set_view("effort") is not None and tp.view == "mine")

# ---- 7. Ctrl+K
f = HC.Finder(w)
kinds = {}
for kk, t, _s, a in f.entries:
    kinds.setdefault(kk, []).append((t, a))
pages = {a[1] for _t, a in kinds.get("Page", [])}
dos = [t for t, _a in kinds.get("Do", [])]
check("Ctrl+K with nothing open: no step page, no piece, no person", not pages & set(STEPS + ("matrix", "outline", "drafts"))
      and "Piece" not in kinds and "Person" not in kinds, sorted(pages))
check("... only pages that need no effort, Overview, Calendar and Tasks", pages <= (set(MW.MainWindow.NO_EFFORT) | {"overview", "calendar", "tasks"})
      and {"overview", "calendar", "tasks", "tools"} <= pages, sorted(pages))
check("... the three doors, New effort, New program and Connect", dos[:3] == ["Open a document with Acronyms", "Shred a customer document to setup",
      "Check a document"] and {"New effort", "New program", "Connect"} <= set(dos), dos)
check("... the efforts and the program to open", {t for t, _a in kinds.get("Effort", [])} >= {"Kestrel bid", "Heron"}
      and "Osprey" in {t for t, _a in kinds.get("Program", [])})
f.fill("new program")
check("... the placeholder names what it finds now, and nothing is shown disabled", "door" in f.box.placeholderText()
      and all(f.list.item(i).flags() & Qt.ItemIsEnabled for i in range(f.list.count())))
made = []
import skqt.programsview as PVM
_np = PVM.new_program
PVM.new_program = lambda host, name=None: made.append("program") or None
f.go(("do", "new_program"))
PVM.new_program = _np
check("... a Do line runs (New program)", made == ["program"])
w.open_effort("Heron"); pump()
f2 = HC.Finder(w)
pages = {a[1] for k, _t, _s, a in f2.entries if k == "Page"}
check("Ctrl+K with an effort open: the steps are there", {"assign", "library", "matrix", "calendar", "tasks"} <= pages)
f2.close()

n = sum(checks)
print(f"QT LANDING 4520 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
