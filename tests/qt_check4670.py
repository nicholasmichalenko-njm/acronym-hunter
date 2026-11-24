"""4.67.0: Matrix > Check. What Assign has left as three lists (requirements not assigned, evaluation criteria not
assigned, sections that hold nothing); a row opens in Assign already picked; Coverage under More. Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import assignlinks as AL, compliance as C, effort as E, workspace as W, setupdoc as SD
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# the lists themselves
def item(i, text, **kw):
    it = {"id": i, "text": text, "decision": "Keep", "suggest": "Keep", "file": "Kestrel_Section_L.pdf", "section": "L.4",
          "type": "Requirement", "map": "", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


d = tempfile.mkdtemp()
M0 = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M0.outline = C.parse_outline("Volume I Technical\n1 Approach\n1.1 Thermal Design\n1.2 Risk\n2 Management\n2.1 Team")
M0.items = [item("K-1", "The Offeror shall describe the thermal design."), item("K-2", "The Offeror shall name the risk owner."),
            item("K-3", "The Government will evaluate the approach.", type="Evaluation")]
g = AL.gaps(M0)
check("nothing assigned: every piece is left, and every section but the volume's own heading holds nothing",
      [r["id"] for r in g["requirements"]] == ["K-1", "K-2"] and [r["id"] for r in g["criteria"]] == ["K-3"]
      and g["empty"] == ["1 Approach", "1.1 Thermal Design", "1.2 Risk", "2 Management", "2.1 Team"] and AL.gap_count(M0) == 8, g["empty"])
AL.assign(M0, ["K-1"], "1.1 Thermal Design")
g = AL.gaps(M0)
check("a section holding something under it is not empty; its empty neighbor is", g["empty"] == ["1.2 Risk", "2 Management", "2.1 Team"]
      and [r["id"] for r in g["requirements"]] == ["K-2"], g["empty"])
AL.assign(M0, ["K-2"], "1.2 Risk"); AL.assign(M0, ["K-3"], "2 Management")
g = AL.gaps(M0)
check("a section with a piece of its own is not empty though the one under it is", g["empty"] == ["2.1 Team"] and not g["requirements"] and not g["criteria"], g)
AL.also(M0, ["K-3"], "2.1 Team")
check("nothing left", AL.gap_count(M0) == 0)

# on the screen
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
check("Matrix's tabs: Assign, Check, Matrix, Crosswalk", [t for _k, t in MW.TABS["matrix"]] == ["Assign", "Check", "Matrix", "Crosswalk"])
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pg = w.linkcheck_page
w.go("linkcheck"); app.processEvents()
check("with nothing kept: one sentence and Open Shred", w.stack.currentWidget() is pg and w.step_btns["matrix"].isChecked() and pg.none.isVisibleTo(w)
      and not pg.body.isVisibleTo(w) and [b.text() for b in pg.findChildren(QPushButton) if b.isVisibleTo(w)] == ["Open Shred"])
kept = [it for it in M.items if it.get("suggest") != "Drop"][:8]
for it in kept:
    it["decision"] = "Keep"
kept[3]["type"] = "Evaluation"
labs = SD.labels(M)
AL.assign(M, [kept[0]["id"]], labs[1])
w.go("linkcheck"); app.processEvents()
n = {k: pg.lists[k].count() for k in pg.lists}
check("the three lists", pg.body.isVisibleTo(w) and n == {"requirements": 6, "criteria": 1, "empty": 1} and pg.lists["empty"].item(0).text() == labs[2], n)
check("each card's title has its count", pg.cards["requirements"].title.text() == "Requirements not assigned: 6"
      and pg.cards["empty"].title.text() == "Sections with nothing assigned: 1", pg.cards["requirements"].title.text())
check("Open in Assign waits for a row", not pg.b_open.isEnabled())
pg.lists["requirements"].setCurrentRow(1); app.processEvents()
pg.lists["empty"].setCurrentRow(0); app.processEvents()
check("one row is picked across the three lists", not pg.lists["requirements"].selectedItems() and pg.picked() == ("empty", labs[2]) and pg.b_open.isEnabled())
pg.open_row(); app.processEvents()
ap = w.assignto_page
check("a section opens in Assign, picked in the outline, with what is not assigned listed", w.stack.currentWidget() is ap and ap.section() == labs[2]
      and ap.show_box.currentData() == "unplaced" and ap.table.rowCount() == 7, (ap.section(), ap.table.rowCount()))
w.go("linkcheck"); app.processEvents()
pg.lists["criteria"].setCurrentRow(0); app.processEvents()
pg.open_row(); app.processEvents()
check("a piece opens in Assign, picked in the list", w.stack.currentWidget() is ap and ap.picked() == [kept[3]["id"]], ap.picked())
AL.assign(M, [it["id"] for it in kept], labs[1]); AL.also(M, [kept[0]["id"]], labs[2])
w.go("linkcheck"); app.processEvents()
check("nothing left: it says so, and offers the matrix", pg.done.isVisibleTo(w) and not pg.body.isVisibleTo(w) and not pg.bar.isVisibleTo(w)
      and [b.text() for b in pg.findChildren(QPushButton) if b.isVisibleTo(w)] == ["Open the matrix"])
check("Coverage is under More, and still opens under Matrix", pg.bar.action("How much of the customer's files was shredded...") is not None)
w.go("prove"); app.processEvents()
check("... the Shred page's coverage view", w.stack.currentWidget() is w.assign_page and w.step_btns["matrix"].isChecked())
w.close()
print(f"QT CHECK 4670 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
