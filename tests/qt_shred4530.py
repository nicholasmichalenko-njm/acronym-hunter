"""4.53.0 offscreen: Shred's keys and bar (UX decisions 11, 12 and 61). Enter takes the suggestion and goes to the next
piece not shredded; with no suggestion it does nothing; a chip or a type letter sets a type and stays; N goes to the next;
Undo after Enter puts the type back and selects that piece again. The bar at the selection opens in the right margin,
level with the first selected piece, the suggested type first, in one column, and never over the page. Fictional (an
Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, pdfmini
import shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
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
from skqt import shredselbar as SBR, shredfocus as SF, typechips as TC
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
ids = lambda: [it["id"] for it in pg.selected()]                      # noqa: E731
shredded = lambda it: bool(ST._keys(it.get(ST.FIELD)) or it.get("decision"))   # noqa: E731
v = pg.view

# ---- the margin
check("Shred keeps a right margin for the bar", v.viewportMargins().right() == SBR.GUTTER)
SBR.gutter(pg, False); v.fit(); app.processEvents()
z0 = v.zoom
SBR.gutter(pg, True); app.processEvents()
check("... a page at Fit width is fitted again to the narrower viewport", v.zoom < z0 and SBR.fitted(v), (z0, v.zoom))
check("no drag grip and no remembered place", not hasattr(SBR, "Grip") and not hasattr(SBR, "move_to")
      and not hasattr(pg, "sel_bar_pos"))

# ---- the bar
ims = by("Integrated Master Schedule")
sug = TC.suggested(pg, ims)
check("the fixture's piece has a suggestion waiting", bool(sug), sug)
pg.select(ims["id"]); app.processEvents()
bar = SBR.refresh(pg)
vp = v.viewport().geometry()
check("the bar is a child of the view, not of the page's viewport", bar is not None and bar.parentWidget() is v)
check("... entirely to the right of the viewport, never over the text", bar.x() > vp.right() and bar.y() >= 0
      and bar.y() + bar.height() <= v.height() + 1, (bar.geometry(), vp))
top = SBR.first_top(pg)
want = max(vp.top(), min(vp.top() + top, vp.bottom() + 1 - bar.height()))
check("... level with the piece (within clamping)", abs(bar.y() - want) <= 1, (bar.y(), want))
shown = [k for k in ST.KEYS if ST.load(w.config_dir)[k].get("shown", True)]
first = bar.layout().itemAt(0).widget()
check("the suggested type is the first button, the primary one", first is bar.lead and bar.lead is bar.chips[sug]
      and bar.lead.property("kind") == "primary" and "Enter takes it" in bar.lead.toolTip())
check("... the others follow in their order", list(bar.chips) == [sug] + [k for k in shown if k != sug], list(bar.chips))
check("every shown type, Capture, Ask a question and Take the suggestion are on the bar", set(bar.chips) == set(shown)
      and bar.capture is not None and bar.ask is not None and bar.take is not None and bar.combine is None)
check("one column", type(bar.layout()).__name__ == "QVBoxLayout")
check("... that fits the margin", bar.width() <= SBR.GUTTER - 2 * SBR.GAP and bar.x() + bar.width() <= vp.right() + 1 + SBR.GUTTER, (bar.width(), bar.sizeHint()))
v.verticalScrollBar().setValue(v.verticalScrollBar().maximum()); app.processEvents()
check("scrolled away: the bar stays in the margin, inside the view", bar.x() > vp.right() and bar.y() >= 0
      and bar.y() + bar.height() <= v.height() + 1, bar.geometry())
v.verticalScrollBar().setValue(0); app.processEvents()
a, b = by("Text shall be no smaller"), by("monthly status report")
pg.select(a["id"]); v.boxes[b["id"]].setSelected(True); app.processEvents()
bar = SBR.refresh(pg)
top = SBR.first_top(pg)
vp = v.viewport().geometry()
check("two pieces: Combine is on the bar, level with the first", bar.combine is not None and len(pg.selected()) == 2
      and abs(bar.y() - max(vp.top(), min(vp.top() + top, vp.bottom() + 1 - bar.height()))) <= 1)

# ---- Enter
nxt_expected = next(it["id"] for it in SF.open_rows(pg) if M.items.index(it) > M.items.index(by("Integrated Master Schedule")))
pg.select(ims["id"]); app.processEvents()
SF.enter(pg); app.processEvents()
ims = by("Integrated Master Schedule")
check("Enter takes the suggestion", shredded(ims) and ims.get("lm") == "L", (ims.get("decision"), ims.get("lm")))
check("... and selects the next piece not shredded", ids() == [nxt_expected], (ids(), nxt_expected))
SBR.refresh(pg); app.processEvents()
check("... where its bar opens", pg.sel_bar is not None)
check("the pane says Shred's keys in one line", "Not shredded yet:" in pg.shred_left.text()
      and "Enter takes the suggestion and goes on, N for the next" in pg.shred_left.text(), pg.shred_left.text())
pg.do_undo(); app.processEvents()
ims = by("Integrated Master Schedule")
check("Undo puts the type back and selects that piece again", not shredded(ims) and ids() == [ims["id"]], (ids(), ims.get("decision")))

# ---- no suggestion: Enter does nothing
nos = next(it for it in SF.open_rows(pg) if not TC.suggested(pg, it))
pg.select(nos["id"]); app.processEvents()
before = [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in M.items]
SF.enter(pg); app.processEvents()
check("Enter with no suggestion changes nothing and stays", ids() == [nos["id"]]
      and before == [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in w.review.M.items])

# ---- a chip and a letter set a type and stay
pg.select(nos["id"]); app.processEvents()
bar = SBR.refresh(pg)
bar.chips["requirement"].click(); app.processEvents()
check("a chip sets the type and stays", ST.has(by(nos["text"][:30]), "requirement") and ids() == [nos["id"]])
c = by("Text shall be no smaller")
pg.select(c["id"]); app.processEvents()
QTest.keyClick(v, Qt.Key_U); app.processEvents()
check("a type letter sets the type and stays", ST.has(by("Text shall be no smaller"), "rule") and ids() == [c["id"]])

# ---- N
left = SF.open_rows(pg)
got = SF.next_open(pg)
check("N still goes to the next piece not shredded", got in [it["id"] for it in left] and ids() == [got], got)

# ---- Enter on the last piece not shredded
f0 = pg.file
for it in SF.open_rows(pg):
    if not TC.suggested(pg, it):
        pg.select(it["id"]); app.processEvents()
        pg.type_chips["information"].click() if pg.sel_bar is None else SBR.refresh(pg).chips["information"].click()
        app.processEvents()
last = SF.open_rows(pg)
check("only suggested pieces are left", last and all(TC.suggested(pg, it) for it in last), [it["id"] for it in last])
for it in last[:-1]:
    pg.select(it["id"]); app.processEvents(); SF.enter(pg); app.processEvents()
lid = last[-1]["id"]
pg.select(lid); app.processEvents()
msgs = []
old = w.status
w.status = lambda m, *a, **k: (msgs.append(m), old(m, *a, **k))[1]
SF.enter(pg); app.processEvents()
w.status = old
check("Enter on the last piece not shredded keeps the selection", ids() == [lid] and not SF.open_rows(pg), ids())
check("... says every piece has a type", "Every piece in this document has a type." in msgs, msgs)
check("... and does not mark the document shredded", f0 not in pg.reviewed() and not pg.shred_check.isChecked())

# ---- Place
w.go("place"); app.processEvents()
check("Place gives the margin back", v.viewportMargins().right() == 0 and pg.sel_bar is None)
w.go("assign"); app.processEvents()
check("... and Shred takes it again", v.viewportMargins().right() == SBR.GUTTER)
w.close()
print(f"QT SHRED 4530 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
