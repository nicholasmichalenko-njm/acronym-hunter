"""3.93.0 offscreen: Acronyms in two tabs, On the page and The list. On the page: the pages with finds to decide, the page
with every find boxed, a click or a drag selects (the drag box is gone when you let go), the bar beside the selection
(found to decide, partly found, read with doubt, not found before), Enter adds, X says Not a term and takes it off the
page (Undo puts it back), the type keys, Page done. The list: In our drafts is its main button; Show on the page opens
the term's page with its finds selected. Fictional content (the Kestrel set); the picture reader is a stand-in."""
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
ap.fill(); app.processEvents()
check("4.26.1: three tabs: On the page, Everything found, Effort list", [ap.tabs.tabText(i) for i in range(ap.tabs.count())]
      == ["On the page", "Everything found", "Effort list"]
      and ap.head_w.isVisible())
check("it opens on On the page while finds are left to decide", ap.tabs.currentIndex() == 0 and ap.tab_stack.currentWidget() is op)
check("On the page has one main button, Page done, and at most five commands", ap.on_bar.main is ap.b_pagedone
      and len(ap.on_bar.commands) <= 5 and ap.bars.currentWidget() is ap.on_bar)
keys = [op.list.item(i).data(Qt.UserRole) for i in range(op.list.count()) if op.list.item(i).data(Qt.UserRole)]
check("the pages with finds are listed, by file", PKEY in keys and any("Program_Manual.pdf (p." in k for k in keys)
      and "undecided" in op.foot.text(), (keys, op.foot.text()))

# ---- a PDF page: the typed finds where they are written
pdf6 = next(k for k in keys if k.endswith("(p.6)"))
op.go(pdf6); op.wait(); app.processEvents()
terms6 = [x["term"] for x in op.items]
check("a PDF page shows as the page, every find boxed", op.state == "picture" and "EPS" in terms6 and len(op._drawn) >= 2, terms6)


def center(x):
    b = x["box"]
    return QPointF((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


i_eps = terms6.index("EPS")
op.clicked(center(op.items[i_eps])); app.processEvents()
check("a click selects the find; the bar opens", op.sel == [i_eps] and op.bar is not None and op.bar.kind == "decide")
r = op.sel_rect()
check("the bar sits beside the selection, never over it", op.bar.isVisible() and not op.bar.geometry().intersects(r),
      (op.bar.geometry(), r))
SB.key(op, "U"); app.processEvents()
check("a type key picks the type", SB.chosen_type(op.bar) == "Unit")
SB.key(op, "A"); SB.key(op, "enter"); app.processEvents()
check("Enter adds it to the list", s.results["EPS"].get("effort") == "In the list" and op.bar is None, s.results["EPS"].get("effort"))
check("... and its box turns green", op.kind(op.items[[x["term"] for x in op.items].index("EPS")]) == "list")


def mouse(kind, pt):
    vp = op.view.viewport()
    p = op.view.mapFromScene(pt)
    ev = QMouseEvent(kind, QPointF(p), QPointF(vp.mapToGlobal(p)), Qt.LeftButton,
                     Qt.NoButton if kind == QEvent.MouseButtonRelease else Qt.LeftButton, Qt.NoModifier)
    {QEvent.MouseButtonPress: op.view.mousePressEvent, QEvent.MouseMove: op.view.mouseMoveEvent,
     QEvent.MouseButtonRelease: op.view.mouseReleaseEvent}[kind](ev)
    app.processEvents()


def drag(a, b):
    mouse(QEvent.MouseButtonPress, a); mouse(QEvent.MouseMove, QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2))
    mouse(QEvent.MouseMove, b); mouse(QEvent.MouseButtonRelease, b)


op.fill(); op.go(pdf6); op.wait()
box = op.view.scene_.sceneRect()
drag(QPointF(box.left() + 1, box.top() + 1), QPointF(box.right() - 1, box.bottom() - 1))
check("a drag selects every find inside", len(op.sel) == len([i for i in range(len(op.items)) if op.visible(i)]) and op.sel, op.sel)
check("... and the drag box is gone when you let go", op.view._area_item is None and op.view.area is not None)
op.select([i for i, x in enumerate(op.items) if x["term"] == "kWh"] or op.sel[:1]); app.processEvents()
nt = op.selected()[0]["term"]
n_drawn = len(op._drawn)
SB.key(op, "X"); app.processEvents()
check("4.26.1: X says Not a term here: this page only, the term stays in the effort",
      not any(AG.place_of(l) == op.key for l in s.results[nt].get("locations", [])) and s.results[nt].get("effort") != "Not a term", nt)
check("... and takes it off the page at once", len(op._drawn) < n_drawn and "Undo" in op.undo_lab.text(), (len(op._drawn), n_drawn))
op.undo_last(); app.processEvents()
check("Undo puts it back as it was", any(AG.place_of(l) == op.key for l in s.results[nt].get("locations", [])) and not s.results[nt].get("excluded")
      and len(op._drawn) == n_drawn, s.results[nt].get("effort"))

# ---- a picture: read with doubt, partly found, never found
import picreadings as PR                     # the stand-in readings, never the scan's own (a PC with the reader keeps real ones)
PR.get = lambda key: None; PR.put = lambda *a, **k: None; PR.flush = lambda *a, **k: None
from skqt import acrpageview as APV
APV._PICS.pop(PKEY, None)
op.go(PKEY); op.wait(); app.processEvents()
pt = [x["term"] for x in op.items]
check("a picture shows with the reader's finds", op.state == "picture" and "TT8C" in pt and "DC" in pt, pt)
i = pt.index("TT8C")
check("a find read with doubt is orange", op.kind(op.items[i]) == "doubt", op.items[i])
op.select([i]); app.processEvents()
check("its bar: what it was read as, and how sure", op.bar.kind == "doubt" and op.bar.says.text() == "TT8C")
op.bar.says.setText("TT&C"); SB.key(op, "enter"); app.processEvents()
check("Fix the reading: the right term is listed here; the misreading is Not a term", "TT&C" in s.results
      and any(AG.place_of(l) == PKEY for l in s.results["TT&C"].get("locations", []))
      and (s.results["TT8C"].get("effort") == "Not a term" or s.results["TT8C"].get("excluded")))
check("... and this PC reads it right from the next scan", os.path.isfile(A.OCR_FIXES_FILE) and "TT8C" in open(A.OCR_FIXES_FILE, encoding="utf-8").read())
pt = [x["term"] for x in op.items]
i = pt.index("DC")
check("DC inside DC-RVM: DC is boxed, DC-RVM dashed behind it", op.items[i].get("whole") is not None
      and any(x.get("behind") and x["term"] == "DC-RVM" for x in op.items))
op.select([i]); app.processEvents()
check("its bar: part of a longer term", op.bar.kind == "partial" and op.bar.whole == "DC-RVM")
SB.key(op, "enter"); app.processEvents()
check("Use DC-RVM ties DC to it; DC-RVM takes the spot", s.results["DC"].get("part_of") == "DC-RVM"
      and any(x["term"] == "DC-RVM" and not x.get("behind") for x in op.items), s.results["DC"])
g = LINES[2][0]
drag(QPointF(g[0] - 10, g[1] - 10), QPointF(g[2] + 10, g[3] + 10))
check("a drag around words never found: Not found before, as the reader sees them now", op.bar is not None
      and op.bar.kind == "new" and "GEP / SITE B" in op.bar.seen.text() and op.bar.term.text() == "GEP", op.new_text)
check("... the words are selected, the drag box is gone", op.new_boxes == [g] and op.view._area_item is None)
SB.read_again(op, op.bar, op.new_area, wait=True)
check("Read this area again: what it reads now", op.bar.term.text() == "GEP")
op.bar.dfn.setText("Gateway Entry Point"); SB.key(op, "enter"); app.processEvents()
check("Add as a term: listed at this page, in the effort's list", "GEP" in s.results
      and any(AG.place_of(l) == PKEY for l in s.results["GEP"].get("locations", []))
      and s.results["GEP"].get("effort") == "In the list", s.results.get("GEP"))

# ---- typed text
doc = next(k for k in keys if "SCOPE OF WORK" in k)
op.go(doc); app.processEvents()
check("a passage of typed text shows with every find as a link", op.state == "text" and op.items
      and "href='f:" in op.text.toHtml().replace('"', "'"), op.state)
k0 = next(i for i in range(len(op.items)) if op.visible(i))
op.link(f"f:{k0}"); app.processEvents()
check("a click on a find selects it", op.sel == [k0] and op.bar is not None)
c = op.text.textCursor(); c.setPosition(0); c.setPosition(5, QTextCursor.KeepAnchor); op.text.setTextCursor(c)
op.text_selected(); app.processEvents()
check("words selected with no find: Not found before", op.bar is not None and op.bar.kind == "new", op.new_text)

# ---- Page done
op.go(PKEY); op.wait()
nxt = op.page_done(); app.processEvents()
check("Page done marks the page and shows the next page with finds", PKEY in AG.done_set(s.ws) and op.key == nxt and nxt != PKEY,
      (op.key, nxt))

# ---- The list
ap.tabs.setCurrentIndex(1); app.processEvents()
check("The list: Add a term is its main button (4.23.0; In our drafts is in More)", ap.bars.currentWidget() is ap.bar and ap.bar.main is ap.b_addterm
      and len(ap.bar.commands) <= 5, ap.bar.labels())
ap.show_in_list("EPS"); app.processEvents()
check("4.26.1: Everything found shows the page beside the list", getattr(ap, "where_view", None) is not None and ap.mid.isVisible())
ap.show_on_page(ap.current()); app.processEvents(); op.wait(); app.processEvents()
check("... it opens the term's page with its finds selected", ap.tabs.currentIndex() == 0
      and op.selected() and all(x["term"] == "EPS" for x in op.selected()), (op.key, op.sel))
labs = [b.text() for b in op.bar.findChildren(QPushButton)] if op.bar is not None else []
check("4.26.1: the bar holds what More held (Plural of, A form of, Part of a longer term); More and Show in the list are gone",
      all(x in labs for x in ("Plural of...", "A form of...", "Part of a longer term...")) and "More" not in labs
      and not hasattr(SB, "more"), labs)
check("... its buttons read Add to effort list and Not a term here", any(x.startswith("Add to effort list") for x in labs)
      and any(x.startswith("Ignore here") for x in labs), labs)

print(f"{sum(checks)}/{len(checks)} passed")
w.close()
sys.exit(0 if all(checks) else 1)
