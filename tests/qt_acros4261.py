"""4.26.1 offscreen: Acros & Abs (the recording of 2026-11-12, 02:05 to 05:25; the sixth answers, 3; answer 19). Several
finds side by side combine into one term, said before the button is pressed; Not a term is for this page only, with
everywhere in this effort (n) second; the choices More held are on the bar; the tabs are On the page, Everything found
and Effort list; the chips read Undecided and Added to effort list; the page shows beside the list; a letter read apart
inside a word is joined back; On the page has a document picker that follows Shred. Fictional (the Kestrel program)."""
import io, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "dark"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP
OP.available = lambda: False
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
import pictures as PIC
from skqt import design as D
from skqt.mainwin import MainWindow
from skqt import acrselbar as SB
import acrpages as AG
import acrmore as AM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.OCR_FIXES_FILE = os.path.join(tmp, "ocr_corrections.csv")
PNG = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_System_Diagram.png")
PW, PH = Image.open(PNG).size
LINES = [((40, 40, 300, 80), "TT8C ANTENNA", 0.05), ((40, 140, 520, 180), "MISSION OPERATIONS CENTER (MOC)", 0.97),
         ((40, 240, 300, 280), "GEP / SITE B", 0.96), ((40, 340, 520, 380), "trace each site in the DC-RVM", 0.97)]
A.scan_readings = lambda b: [(bx, t, c, "read") for bx, t, c in LINES]
PIC.read_region_lines = lambda crop: [((0, 0, crop.width, crop.height), "GEP / SITE B", 0.93)]
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
op = ap.onpage
check("before a scan: one way in, no tabs", ap.empty.isVisible() and not ap.head_w.isVisible())
S = os.path.join(A.BASE_DIR, "test_samples")
ap.scan([os.path.join(S, n) for n in ("Kestrel_Technical_Volume.docx", "Kestrel_Program_Manual.pdf", "Kestrel_System_Diagram.png")])
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 300:
    app.processEvents(); time.sleep(0.05)
s = ap.session
PKEY = "Kestrel_System_Diagram.png (Image)"
for t in ("TT8C", "DC", "DC-RVM"):                                   # the picture's terms (the scan here reads no pictures)
    if t not in s.results:
        AM.add_manual(s, t, "Acronym", "", document=PKEY, to=("results",))
import acrplace as AP, ocrjoin as OJ
from PySide6.QtWidgets import QPushButton
from skqt import acrlayout as AL


def labels(bar):
    return [b.text() for b in bar.findChildren(QPushButton)]


ap.fill(); app.processEvents()


# ---- a single letter read apart inside a word (the engine)
L = [(10, 10, 110, 40, "DEFEN", .9), (114, 10, 134, 40, "S", .8), (138, 10, 158, 40, "E", .95),
     (300, 10, 400, 40, "Volume", .9), (420, 10, 432, 40, "I", .9), (450, 10, 560, 40, "Technical", .9),
     (10, 100, 40, 130, "5", .9), (44, 100, 64, 130, "A", .9), (70, 100, 150, 130, "max", .9),
     (10, 200, 90, 230, "Phase", .9), (94, 200, 110, 230, "B", .9)]
J = OJ.join_split_letters(L)
texts = [x[4] for x in J]
check("DEFEN, S, E read apart on one line is one word, DEFENSE", "DEFENSE" in texts and "S" not in texts and "E" not in texts, texts)
check("... its box is the three boxes together and it keeps the lowest confidence", J[0][:4] == (10, 10, 158, 40) and J[0][5] == .8, J[0])
check("a letter with a word space each side stays (Volume I Technical)", "I" in texts and "Volume" in texts)
check("a letter after a number stays (5 A)", "A" in texts and "5" in texts)
check("a letter at the end of a line stays (Phase B)", "B" in texts and "Phase" in texts)
check("the scan's reader runs it", "join_split_letters" in open(os.path.join(os.path.dirname(HERE), "app_gui.py"), encoding="utf-8").read())

# ---- combine: what several finds side by side spell
check("two finds that touch spell one term: U, S is US", AP.combined([{"term": "U", "box": (10, 10, 30, 40)}, {"term": "S", "box": (32, 10, 52, 40)}]) == "US")
check("... two that stand apart keep a space", AP.combined([{"term": "DC", "box": (10, 10, 50, 40)}, {"term": "RVM", "box": (90, 10, 150, 40)}]) == "DC RVM")
check("... in typed text, by what lies between", AP.combined([{"term": "U", "span": (4, 5)}, {"term": "S", "span": (5, 6)}]) == "US"
      and AP.combined([{"term": "AB", "span": (0, 2)}, {"term": "CD", "span": (3, 5)}]) == "AB CD")

# ---- the tabs and the words
check("three tabs: On the page, Everything found, Effort list", [ap.tabs.tabText(i) for i in range(ap.tabs.count())]
      == ["On the page", "Everything found", "Effort list"])
check("the chips read Undecided, Added to effort list and Not a term", ap.count_btns["To decide"].text().startswith("Undecided ")
      and ap.count_btns["In the list"].text().startswith("Added to effort list ") and not ap.count_btns["Not a term"].isHidden())
check("the pages list says undecided", "undecided" in op.foot.text() and "to decide" not in op.foot.text(), op.foot.text())

# ---- the document picker, and following Shred's document
names = op.docs()
check("On the page has its own document picker, on Every document", len(names) >= 2 and op.doc_pick.currentData() == ""
      and [op.doc_pick.itemData(i) for i in range(1, op.doc_pick.count())] == names, names)
n_all = len([1 for i in range(op.list.count()) if op.list.item(i).data(Qt.UserRole)])
op.doc_pick.setCurrentIndex(op.doc_pick.findData(names[1])); app.processEvents()
keys = [op.list.item(i).data(Qt.UserRole) for i in range(op.list.count()) if op.list.item(i).data(Qt.UserRole)]
check("pick a document: only its pages are listed, and one of them shows", keys and len(keys) < n_all
      and all(k.startswith(names[1]) for k in keys) and op.key in keys, (keys, op.key))
nx = op.next_page()
check("... Next page with finds stays in that document", nx is None or nx.startswith(names[1]), nx)
w.assign_page.file = names[0]
got = op.follow(); app.processEvents()
check("it follows the document open in Shred when that document changes", got == names[0] and op.doc_pick.currentData() == names[0])
op.doc_pick.setCurrentIndex(op.doc_pick.findData(names[1])); app.processEvents()
check("... and a pick made after that stays until Shred's document changes again", op.follow() is None and op.doc_pick.currentData() == names[1])
op.doc_pick.setCurrentIndex(0); app.processEvents()

# ---- the bar: one find
op.fill(); op.go(PKEY); op.wait(); app.processEvents()
vis = [i for i in range(len(op.items)) if op.visible(i)]             # the PC's reader reads the picture; here it is not read,
op.select(vis[:1]); app.processEvents()                              # so take whatever find is first
SB.keep_part(op); app.processEvents()                    # it was read with doubt: "It reads right: decide it"
t1 = op.selected()[0]["term"]
labs = labels(op.bar)
check("one find: Add to effort list, Not a term here, and what More held on the bar", any(x.startswith("Add to effort list") for x in labs)
      and any(x.startswith("Ignore here") for x in labs) and all(x in labs for x in ("Plural of...", "A form of...", "Part of a longer term..."))
      and "More" not in labs, labs)
n_places = AP.places(s, t1)
check("... Not a term everywhere shows its count only when the term is found in other places too",
      (op.bar.b_everywhere is not None) == (n_places > len(AP.here(s, t1, op.key))), (n_places, AP.here(s, t1, op.key)))

# ---- Not a term here
s.results[t1].setdefault("locations", []).append("Elsewhere.docx (para 3)")
op.select(vis[:1]); app.processEvents()
SB.keep_part(op); app.processEvents()
check("found in another place too: Not a term everywhere in this effort (n)", op.bar.b_everywhere is not None
      and op.bar.b_everywhere.text() == f"Ignore in this effort ({AP.places(s, t1)})", labels(op.bar))
SB.key(op, "X"); app.processEvents()
check("X is Not a term here: off this page, still found elsewhere, not Not a term in the effort",
      not AP.here(s, t1, op.key) and "Elsewhere.docx (para 3)" in s.results[t1]["locations"] and s.results[t1].get("effort") != "Not a term"
      and not s.results[t1].get("excluded"), s.results[t1].get("locations"))
check("... it is kept with the effort, so the next scan leaves it off this page too", any(AG.place_of(l) == PKEY for l in s.ws.instance_excludes().get(t1, [])))
check("... and Undo is offered", "on this page" in op.undo_lab.text() and "Undo" in op.undo_lab.text(), op.undo_lab.text())
op.undo_last(); app.processEvents()
check("Undo puts it back on the page", AP.here(s, t1, op.key) and not s.ws.instance_excludes().get(t1))
op.select([i for i, x in enumerate(op.items) if x["term"] == t1][:1]); app.processEvents()
SB.keep_part(op); app.processEvents()
op.bar.b_everywhere.click(); app.processEvents()
check("Not a term everywhere: the whole effort, as before", s.results[t1].get("effort") == "Not a term" or s.results[t1].get("excluded"))
op.undo_last(); app.processEvents()

# ---- the bar: two finds, combined
seen_, vis = set(), []
for i in range(len(op.items)):
    if op.visible(i) and op.items[i]["term"] not in seen_ and len(vis) < 2:
        seen_.add(op.items[i]["term"]); vis.append(i)
op.select(vis); app.processEvents()
if op.bar is None or getattr(op.bar, "whole", None) is None:
    SB.keep_part(op); app.processEvents()
two = [x["term"] for x in op.selected()]
bar = op.bar
check("two finds: Combine into, with the one term they spell", getattr(bar, "whole", None) is not None and bar.whole.text() == AP.combined(op.selected())
      and bar.whole.text(), labels(bar))
check("... and it says what goes in the list before the button is pressed", "adds one term" in bar.says.text() and bar.whole.text() in bar.says.text(), bar.says.text())
check("... Add each as its own term is the other choice", "Add each as its own term" in labels(bar))
bar.whole.setText("KXQ"); bar.typed.setText("Kestrel Exchange Queue")
check("change the term: the sentence follows", "KXQ" in bar.says.text())
SB.key(op, "enter"); app.processEvents()
check("Enter adds one term to the effort list, with its definition", "KXQ" in s.effort.rows and s.effort.rows["KXQ"].get("Definition") == "Kestrel Exchange Queue",
      s.effort.rows.get("KXQ"))
check("... and the two finds on this page are part of it, not left undecided here",
      all((getattr(s, "parts", {}) or {}).get(t, {}).get("whole") == "KXQ" for t in two) and all(not AP.here(s, t, PKEY) or AG.state_of(s.results[t]) == "tied" for t in two),
      [(t, s.results[t].get("locations"), s.results[t].get("part_of")) for t in two])

# ---- the lists
ap.tabs.setCurrentIndex(1); app.processEvents()
ap.show_in_list("EPS"); app.processEvents()
check("Everything found: the page shows beside the list", ap.where_view is not None and not ap.mid.isHidden()
      and [c for c in range(ap.table.columnCount()) if not ap.table.isColumnHidden(c)] == list(AL.LIST_COLS))
w.go("acrlist"); app.processEvents()
lp = w.acrlist_page
check("Effort list opens on what was added", lp.f_status.currentText() == "Added to effort list" and "KXQ" in lp.terms
      and all(lp.status_of(lp.L.rows[t]) != "Not a term" for t in lp.terms), lp.terms[:8])
# 4.29.2 (answer 12 of 2026-11-13): the page beside the Effort list
check("the Effort list has the page beside it, with a hint until a term is picked", lp.split.count() == 2 and lp.where_view is None
      and "Select a term" in lp.side_hint.text())
found = next((t for t in lp.terms if (s.results.get(t) or {}).get("locations")), None)
lp.select([found]) if found else None
app.processEvents()
check("pick a term found in the customer's documents: its page shows beside the list", found is not None and lp.where_view is not None
      and lp.where_view.term == found and not lp.side_hint.isVisibleTo(lp), found)
lp.table.clearSelection(); app.processEvents()
check("nothing picked: the hint is back", lp.where_view is None and lp.side_hint.isVisibleTo(lp))
print(f"QT ACROS 4261 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
w.close()
sys.exit(0 if all(checks) else 1)
