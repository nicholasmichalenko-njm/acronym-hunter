"""4.1.0 offscreen: the shred's decide bar says what each piece is (shredbar, shredtypes): Requirement R, Instruction L,
Rule U, Date D, Evaluation E, Deliverable V, Information G, Support C, Not applicable X. Each keeps the piece's type in
the same Undo step; Rule and Date are the customer's, kept as that type; a Deliverable is a requirement; the type is
saved in the matrix workbook's Piece column. Fictional (an Osprey Section L)."""
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
         "The Government intends to award a single contract.",
         "Oral presentations will be held on January 12, 2027."]
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
check("extracted", wait(lambda: w.review is not None))
M = w.review.M
pg = w.assign_page
w.go("assign"); app.processEvents()
by = lambda s: next(it for it in M.items if s in it["text"])
order = [pg.dec_lay.itemAt(i).widget().text() for i in range(pg.dec_lay.count()) if pg.dec_lay.itemAt(i).widget()]
check("the bar names the piece types, with their keys", order == ["Requirement  R", "Instruction  L", "Rule  U", "Date  D",
      "Evaluation  E", "Deliverable  V", "Information  G", "Support  C", "Not applicable  X"], order)


def key(s, k):
    pg.select(by(s)["id"]); app.processEvents()
    QTest.keyClick(pg.view, k); app.processEvents()
    return by(s)


it = key("(IMS)", Qt.Key_L)
check("L: an Instruction (a requirement designated L), its type kept", it["decision"] == "Keep" and it["lm"] == "L" and it["piece"] == "instruction")
it = key("12-point", Qt.Key_U)
check("U: a Rule: the customer's, kept as a Rule (Rules & Dates)", it["decision"] == "Customer" and it["piece"] == "rule"
      and ST.tab_of(ST.type_of(it)) == "rules" and not ST.placed("rule"))
it = key("December 15", Qt.Key_D)
check("D: a Date", it["piece"] == "date" and it["decision"] == "Customer")
it = key("monthly status", Qt.Key_V)
check("V: a Deliverable is a requirement (SOW), offered on Place", it["decision"] == "Keep" and it["lm"] == "C" and it["piece"] == "deliverable"
      and ST.placed("deliverable"))
it = key("realism", Qt.Key_E)
check("E: Evaluation", it["lm"] == "M" and it["piece"] == "evaluation")
it = key("single contract", Qt.Key_G)
check("G: Information", it["decision"] == "Customer" and it["piece"] == "information")
it = key("single contract", Qt.Key_X)
check("X: Not applicable (Ignore)", it["decision"] == "Drop" and it["piece"] == "not_applicable")
pg.do_undo(); app.processEvents()
check("Undo puts the type back with the decision, in one step", by("single contract")["piece"] == "information"
      and by("single contract")["decision"] == "Customer")
it = key("12-point", Qt.Key_R)
check("a Rule made a Requirement: the type follows the decision", it["decision"] == "Keep" and it["piece"] == "requirement")
import skqt.shredbar as SB
undecided = by("Oral presentations")
SB.capture_types(pg, "keydate", [undecided["id"]])
check("a capture that says what a piece is types it (a key date: a Date), when it has no type or decision",
      undecided.get("piece") == "date")
check("... never over a type or a decision already given", SB.capture_types(pg, "pagelimit", [by("realism")["id"]]) == 0
      and by("realism")["piece"] == "evaluation")
w.review.M.save(); app.processEvents()
M2 = C.Matrix(OUT); M2.load()
got = {x["text"][:20]: x.get("piece") for x in M2.items if x.get("piece")}
check("the types are saved in the workbook's Piece column", sorted(got.values()) ==
      sorted(["instruction", "date", "deliverable", "evaluation", "information", "requirement", "date"]), got)
w.close()
print(f"QT SHRED 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
