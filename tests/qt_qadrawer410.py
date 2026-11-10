"""4.1.0 offscreen: the Q&A log as a drawer (claude/stationkeeper-shred-plan-4.1.md, step 6). A Q&A button with the count
of questions not answered sits in the title bar of Shred, Matrix & Outline and Drafts; it opens the log beside the
page. Asking a question on a piece fills in the citation and opens the drawer on it. go("custqa") opens it; Documents
has no Customer Q&A tab. Fictional (an Osprey Section L)."""
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
import custqa as Q, effortrec as RR
check("Documents has no Customer Q&A tab", "custqa" not in [k for k, _t in TABS["library"]])
w.go("assign"); app.processEvents()
check("Shred's title bar has Q&A; the drawer is closed", w.qa_btn.isVisibleTo(w) and w.qa_btn.text() == "Q&&A" and not w.qa_drawer.isVisible())
w.go("home"); app.processEvents()
check("... the Dashboard does not", not w.qa_btn.isVisibleTo(w))
w.go("assign"); app.processEvents()
M = w.review.M
pg = w.assign_page
it = next(x for x in M.items if "(IMS)" in x["text"])
pg.select(it["id"]); app.processEvents()
qid = pg.do_capture("question", answer={"question": "Is a resource-loaded IMS required?", "quote": it["text"],
                                         "doc": "Section_L.pdf", "category": "Technical"})
q = Q.get(RR.Record(w.ws.root), qid)
check("asking a question on a piece files it with its citation", q and q["sid"] == it["id"] and q["quote"] == it["text"], q)
check("... and opens the drawer on it, beside the page", w.qa_drawer.isVisible() and w.stack.currentWidget() is pg
      and [x["id"] for x in w.custqa_page.selected()] == [qid])
check("... the button counts it", w.qa_btn.text() == "Q&&A (1)" and w.qa_btn.isChecked(), w.qa_btn.text())
w.go("matrix"); app.processEvents()
check("Matrix & Outline keeps the drawer open", w.qa_drawer.isVisible() and w.qa_btn.isVisibleTo(w))
w.go("drafts"); app.processEvents()
check("Drafts has it too", w.qa_btn.isVisibleTo(w))
w.go("library"); app.processEvents()
check("Documents: the drawer closes, no button", not w.qa_drawer.isVisible() and not w.qa_btn.isVisibleTo(w))
w.go("custqa"); app.processEvents()
check("go('custqa') from elsewhere opens Shred with the log", w.qa_drawer.isVisible() and w.stack.currentWidget() is pg)
w.qa_drawer.close_btn.click(); app.processEvents()
check("Close closes it", not w.qa_drawer.isVisible() and not w.qa_btn.isChecked())
w.qa_btn.click(); app.processEvents()
check("the button opens it again", w.qa_drawer.isVisible() and w.custqa_page.table.rowCount() == 1)
w.close()
print(f"QT QA DRAWER 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
