"""4.3.0 offscreen: Matrix & Outline (claude/stationkeeper-matrix-outline-plan-4.3.md). Its tabs are Outline, Place,
Matrix, L to M, Coverage; Shred types (no outline beside its page), Place places (the Shred page with our outline);
Outline holds the builder and asks once whether the solicitation prescribes the outline; on Place a requirement is
left out of the matrix with a reason (right-click), kept on the piece, off the not-placed count, on the export's Left out
sheet, and put back; evaluation pieces link through L to M and are not asked to be placed. Fictional (an Osprey L)."""
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
from skqt.mainwin import TABS
import homesuggest as HS, matrixdesign as MD, openpyxl
from skqt import leaveoutview as LOV
check("Matrix & Outline's tabs", [k for k, _t in TABS["matrix"]] == ["outline", "place", "matrix", "crosswalk", "prove"], TABS["matrix"])
pg = w.assign_page
M = w.review.M
w.go("assign"); app.processEvents()
check("Shred types: no outline beside its page", not pg.place_mode and not pg.views.isVisibleTo(w))
w.go("place"); app.processEvents()
check("Place places: the Shred page with our outline, in Matrix & Outline", w.stack.currentWidget() is pg and pg.place_mode
      and pg.views.isVisibleTo(w) and w.step_btns["matrix"].isChecked() and w.page_title.text() == "Matrix & Outline")
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
ims, rep, ev = by("(IMS)"), by("monthly status"), by("realism")
w.review.req([ims, rep, ev], "")
ev["piece"] = "evaluation"
lf = HS.left(M)
check("not placed: the requirements, never the evaluation piece (it links through Crosswalk)",
      ims["id"] in lf["unplaced"] and rep["id"] in lf["unplaced"] and ev["id"] not in lf["unplaced"], lf)
pg.select(rep["id"]); app.processEvents()
acts = [a.text() for a in pg.sentence_menu(rep["id"]).actions()]
check("right-click on Place: Leave out of the matrix...", "Leave out of the matrix..." in acts, acts)
check("... Other needs a note", LOV.leave_out(pg, [rep], answer=("Other", "")) == 0 and not rep.get("left_out"))
n = LOV.leave_out(pg, [rep], answer=("Covered elsewhere", "in the SOW volume"))
check("Leave out: the reason and note kept on the piece, off the not-placed count", n == 1
      and rep["left_out"] == "Covered elsewhere: in the SOW volume" and rep["id"] not in HS.left(M)["unplaced"])
w.review.req([ims], "1.1 Technical Approach")
wb_path = os.path.join(tmp, "m.xlsx")
rows_ = MD.rows(M, MD.default())[0]
check("the matrix rows leave it out", all(r.get("id") != rep["id"] and all(x.get("id") != rep["id"] for x in r.get("_L", []) + r.get("_M", []))
                                          for r in rows_))
res = w.matrix_page.export(wb_path)
wb = openpyxl.load_workbook(wb_path)
check("the export: a Left out sheet with the reason", "Left out" in wb.sheetnames
      and any(row[2] == "Covered elsewhere: in the SOW volume" for row in wb["Left out"].iter_rows(values_only=True)), wb.sheetnames)
acts = [a.text() for a in pg.sentence_menu(rep["id"]).actions()]
check("... and Put back in the matrix", "Put back in the matrix" in acts)
LOV.put_back(pg, [rep])
check("put back", not rep.get("left_out"))
w.go("assign"); app.processEvents()
check("Shred's right-click has no Leave out", "Leave out of the matrix..." not in [a.text() for a in pg.sentence_menu(ims["id"]).actions()])
# Outline: the builder, and the start question
M.outline = []
w.go("outline"); app.processEvents()
op = w.outline_page
check("Outline: an empty outline asks how it starts", w.stack.currentWidget() is op and op.start.isVisibleTo(w)
      and w.step_btns["matrix"].isChecked())
op.prescribed(); app.processEvents()
import setupdoc as SD
check("... prescribed: the text panel with the solicitation's sections; the answer kept", SD.setup_of(M).get("outline_from") == "prescribed"
      and op.builder().text_panel.isVisibleTo(w) and not op.start.isVisibleTo(w))
w.go("setups"); app.processEvents()
check("Setup shows the same builder", w.setups_page.builder.parent() is w.setups_page)
w.close()
print(f"QT PLACE 430 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
