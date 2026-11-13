"""4.26.0 offscreen: Shred (answers 17, 18, 27, 29, 30; the recording of 2026-11-12). This document is shredded is a
checkbox; More holds two things; the bar at the selection; Add missed text from a dragged box; Make it checked... for a
piece typed Rule or Date; counts say not shredded; the compliance bar is Shred's; Next: Matrix & Outline is gone; Sort mode
and the Structure view are off the screen. Fictional (an Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C
import effort as E, workspace as W, pdfmini
import shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report.",
         "The Government will evaluate the realism of the schedule.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
OUT = os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx")
w.read_page.read([PDF], OUT)
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
from PySide6.QtCore import QPoint, QPointF, QRect
from PySide6.QtWidgets import QMenu
import shredwords as SW, subreq as SR, docversions as DV
from skqt import shredband as BD, shredselbar as SBR, shredprogress as PRG, makechecked as MK, shredfocus as SF
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
vis = lambda x: x.isVisibleTo(w) and x.isVisible()                     # noqa: E731

# ---- the document row (answer 17)
check("This document is shredded is a plain checkbox, not ticked", vis(pg.shred_check) and not pg.shred_check.isChecked()
      and type(pg.shred_check).__name__ == "QCheckBox")
check("More holds Fix text and Fit width; Next document, Pan, Add missed text, Take every suggestion and the Captured list are gone",
      sorted(pg.more_acts) == ["Fit width", "Fix text"])
f0 = pg.file
pg.shred_check.setChecked(True); app.processEvents()
check("tick it: the document is marked, and the same document stays open", pg.file == f0 and f0 in pg.reviewed() and pg.shred_check.isChecked())
pg.shred_check.setChecked(False); app.processEvents()
check("untick it: the mark is off", f0 not in pg.reviewed())
check("the Pan tool is off; Space and the middle button still move the page", not pg.view.pan_tool)
check("Shred has no bar under the page: Next: Matrix & Outline is gone (answer 18)", not w.next_bar.isVisibleTo(w))
w.go("matrix"); app.processEvents()
check("... the other steps keep theirs", w.next_bar.isVisibleTo(w))
w.go("assign"); app.processEvents()

# ---- counts say "not shredded" (answer 29)
check("the words: 28 not shredded; all shredded", SW.left(28) == "28 not shredded" and SW.left(0) == "all shredded")
n = PRG.refresh(pg)
check("the compliance bar is Shred's: one line under the document row, with the count in words", n is not None and vis(pg.progress_row)
      and pg.progress_lbl.text() == SW.progress(n["shredded"], n["total"]) + ", " + SW.left(n["left"]), pg.progress_lbl.text())
check("... its last part reads Not shredded", n["segments"][-1][2] == "Not shredded" and n["segments"][-1][0] == n["left"])
w.go("home"); app.processEvents()
check("... and the Overview no longer shows the Compliance review card", "compliance" not in w.home_page.shown and not w.dash_page.comp.isVisibleTo(w))
w.go("assign"); app.processEvents()

# ---- the bar at the selection
it = by("Integrated Master Schedule")
pg.select(it["id"]); app.processEvents()
bar = SBR.refresh(pg)
check("select a piece: a bar shows at the selection with the types as chips", bar is not None and bar.isVisible()
      and list(bar.chips) == [k for k in ST.KEYS if ST.load(w.config_dir)[k].get("shown", True)], list(bar.chips) if bar else None)
check("... inside the page, above or below the piece, never off it", bar.parentWidget() is pg.view.viewport() and bar.y() >= 0
      and bar.y() + bar.height() <= pg.view.viewport().height() + 1, bar.geometry())
check("... with Take the suggestion while one waits, and no Combine for one piece", bar.take is not None and bar.combine is None)
bar.chips["requirement"].click(); app.processEvents()
it = by("Integrated Master Schedule")
bar = SBR.refresh(pg)
check("a chip on the bar types the piece, as the pane's does", ST.has(it, "requirement") and it["decision"] == "Keep"
      and bar.chips["requirement"].isChecked() and pg.type_chips["requirement"].isChecked())
a, b = by("Text shall be no smaller"), by("monthly status report")
pg.select(a["id"]); pg.view.boxes[b["id"]].setSelected(True); app.processEvents()
bar = SBR.refresh(pg)
check("two pieces selected: Combine is on the bar", bar is not None and bar.combine is not None and len(pg.selected()) == 2)
pg.view.scene().clearSelection(); app.processEvents()
check("nothing selected: the bar goes", SBR.refresh(pg) is None and pg.sel_bar is None)

# ---- Add missed text from a dragged box (answer 17)
v = pg.view
r = QRect(20, 20, 200, 60)
v.rubberBandChanged.emit(r, v.mapToScene(r.topLeft()), v.mapToScene(r.bottomRight()))
v.rubberBandChanged.emit(QRect(), QPointF(), QPointF())
check("drag a box: it stays on the page", v._band is not None and v._band_item is not None)


class Ev:
    def __init__(self, p):
        self._p = p

    def pos(self):
        return self._p

    def globalPos(self):
        return self._p


m = BD.menu(pg, Ev(QPoint(60, 40)), show=False)
check("right-click inside the box: Add missed text", m is not None and [x.text() for x in m.actions()] == [BD.ADD])
check("right-click outside it: the piece's own menu, as before", BD.menu(pg, Ev(QPoint(600, 600)), show=False) is None)
n0 = len(M.items)
got = BD.add(pg, text="The Offeror shall also describe its staffing plan.")
check("Add missed text reads the box into a piece and the box goes", got is not None and len(w.review.M.items) == n0 + 1 and v._band is None
      and any("staffing plan" in x["text"] for x in w.review.M.items), got)
v.rubberBandChanged.emit(QRect(5, 5, 2, 2), v.mapToScene(QPoint(5, 5)), v.mapToScene(QPoint(7, 7)))
v.rubberBandChanged.emit(QRect(), QPointF(), QPointF())
check("a click that moved two pixels is no box", v._band is None)

# ---- Make it checked... (answer 27)
M = w.review.M
t = by("Text shall be no smaller")
pg.select(t["id"]); app.processEvents()
check("a piece with no Rule or Date type gets no offer", pg.checked_btn is None and pg.checked_date_btn is None)
pg.type_chips["rule"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("typed Rule: Make it checked... on its pane", pg.checked_btn is not None and pg.checked_btn.text() == MK.TEXT and pg.checked_btn.isVisibleTo(pg))
reg0 = len(MK.register(pg).state["manual"])
check("... nothing is made until the button is pressed", reg0 == 0)
k = MK.make_rule(pg, t, answer=("Format", "Font", "12-point Times New Roman, 1-inch margins"))
man = MK.register(pg).state["manual"]
check("press it: a rule that is checked, with the piece as its source", k and len(man) == 1 and man[0]["source"]["sid"] == t["id"]
      and man[0]["kind"] == "Format" and "Text shall be no smaller" in man[0]["source"]["text"], man)
pg.show_card(pg.selected()); app.processEvents()
check("... the button then says it is checked", pg.checked_btn is not None and pg.checked_btn.text().startswith("Checked"))
g = MK.guess("Volume I shall not exceed 25 pages.")
check("the dialog is filled from the words (a page limit read as one)", g[0] == "Page limit" and "25" in g[2], g)
check("... and words the reader has no rule for go in as Format, whole", MK.guess("Use blue ink.") == ("Format", "", "Use blue ink."))
d = by("no later than 2:00 p.m.")
pg.select(d["id"]); app.processEvents()
pg.type_chips["date"].click(); app.processEvents()
check("typed Date: Make it checked... opens the Key date card", pg.checked_date_btn is not None and pg.checked_date_btn.text() == MK.TEXT)
card = MK.make_date(pg, by("no later than 2:00 p.m."))
check("... the card is open on the pane", card is not None and pg.capture_card is card and card.kind == "keydate")
card.close_card(); app.processEvents()

# ---- Sort mode and the Structure view (answer 30)
check("Sort mode is off on Shred and its key does nothing", not pg.sort_on and not vis(pg.sort_btn))
w.go("sort"); app.processEvents()
sp = w.pages["sort"]
check("Themes: Sort and Overview; the Structure view is gone", [sp.view.itemText(i) for i in range(sp.view.count())] == ["Sort", "Overview"])

# ---- Rules & Dates with nothing in it; the menu's words
w.go("requirements"); app.processEvents()
rp = w.requirements_page
check("Submission Checklist with rules in it shows its groups and its bar", not rp.empty.isVisible() and rp.cbar.isVisibleTo(w))
w.close()
print(f"QT SHRED 4260 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
