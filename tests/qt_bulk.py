"""3.0.4 several sentences at once in Review, offscreen: Select undecided and Ctrl+A select the document's sentences; with
more than one selected a bar shows the count and what they are, and one decision, one section or one author applies to
all of them; Clear selection (and Esc) takes the bar away."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
reg = E.Registry(os.path.join(cfg, "efforts.json")); reg.put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("the matrix starts", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
pg = w.assign_page; app.processEvents()
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
check("one sentence selected: no bar", not pg.bulk.isVisibleTo(w))
n = pg.select_undecided()
rows = pg.selected()
check("Select undecided selects every undecided sentence on the page", n == len(rows) and n >= 10
      and all(not it.get("decision") for it in rows), n)
check("... and the bar shows how many", pg.bulk.isVisibleTo(w) and pg.bulk_lbl.text() == f"{n} sentences selected"
      and "undecided" in pg.bulk_info.text(), pg.bulk_info.text())
first = rows[:4]
pg._guard = True; pg.view.scene().clearSelection()
for it in first:
    pg.view.boxes[it["id"]].setSelected(True)
pg._guard = False; pg.on_select()
pg.bulk_section("1.2 Risk")
check("Put all in section: four requirements in 1.2 Risk at once", all(w.review.item(it["id"])["decision"] == "Keep"
      and w.review.item(it["id"])["map"] == "1.2 Risk" for it in first) and "4 requirement" in pg.bulk_info.text(), pg.bulk_info.text())
check("... the section list in the bar is the structure", [pg.bulk_sec.itemText(i) for i in range(1, pg.bulk_sec.count())]
      == w.review.labels())
w.people = lambda: ["A. Lee", "K. Park"]
pg.refresh_bulk(pg.selected())
i = pg.bulk_own.findData("K. Park")
check("Author for all offers the author list", i > 0)
pg.bulk_author("K. Park")
check("... one author on all four", all(w.review.item(it["id"])["owner"] == "K. Park" for it in first))
pg.bulk_decide("M")
check("Decide all: M on all four", all(w.review.item(it["id"]).get("lm") == "M" for it in first))
pg.bulk_decide("ignore")
check("Decide all: Ignore takes all four out", all(not w.review.item(it["id"]).get("decision") for it in first))
pg.do_undo(); app.processEvents()
check("one Ctrl+Z puts all four back", all(w.review.item(it["id"])["decision"] == "Keep" for it in first))
pg.bulk_author("")
check("... and (the section's lead) clears the author", all(not w.review.item(it["id"]).get("owner") for it in first))
k = pg.select_all()
check("Ctrl+A selects every sentence on the page", k == len(pg.selected()) and k >= n, k)
pg.view.scene().clearSelection(); app.processEvents()
check("Clear selection takes the bar away", not pg.bulk.isVisibleTo(w))
w.close()
t = sum(checks)
print(f"QT BULK {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
