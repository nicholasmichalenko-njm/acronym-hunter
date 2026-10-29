"""2.87.0 the deliverables board, offscreen: Deliverables sits with the effort; one card per deliverable, the ones that
need action first (no owner, over the limit), each with its owner, status, pages against its limit, the volume it holds
in the response structure (linked by name, or by the person), its requirements and how many have an author, what a
customer version changed and is waiting for its owner, and what is missing; click a card for everything about it
(requirements, changes, checks, files) and open a requirement in Assign; Effort home and the dashboard say how the
deliverables stand."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, effortrec as RR, workspace as W, deliverables as DL, changereview as CR, office_pdf as OP, delivboard as DB
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management\nVolume II Past Performance\n2.1 Contracts")
VOL = shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), EDIR)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("Deliverables sits with the effort, after Effort home", list(w.step_btns)[1:3] == ["home", "deliverables"])
B = os.path.join(A.BASE_DIR, "test_samples", "rfp")
w.read_page.read([os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
keeps = [it for it in M.items if "shall" in it["text"]][:3]
w.review.req(keeps[:2], "1.1 Technical Approach"); w.review.req(keeps[2:3], "2.1 Contracts")
import setupdoc as SD
SD.set_people(M, "1.1 Technical Approach", lead="A. Lee")
w.changed(); w.save_now()
rec = RR.Record(w.ws.root)
d1 = DL.add(rec, "Volume I Technical", "Volume", owner="A. Lee", limit="2 pages", file=VOL)
d2 = DL.add(rec, "Volume II Past Performance", "Volume")
d3 = DL.add(rec, "SF 33", "Form", owner="K. Park")
rv = CR.Review(w.ws.root).load(); rv.add_history(keeps[0]["id"], "updated", "old words", keeps[0]["text"], "RFP", "Amendment 1")
w.go("deliverables"); app.processEvents()
dp = w.deliverables_page
cards = dp.cards
byname = {c["name"]: c for c in cards}
check("one card per deliverable, the ones needing action first", len(cards) == 3 and cards[0]["health"] == "crit", [(c["name"], c["health"]) for c in cards])
c1, c2 = byname["Volume I Technical"], byname["Volume II Past Performance"]
check("a Volume deliverable is linked to its volume by name", c1["volume"] == "Volume I Technical" and c2["volume"] == "Volume II Past Performance",
      (c1["volume"], c2["volume"]))
check("its requirements, and how many have an author (the section lead)", c1["reqs"] == 2 and c1["owned"] == 2 and c2["reqs"] == 1 and c2["owned"] == 0,
      (c1["reqs"], c1["owned"], c2["reqs"], c2["owned"]))
check("pages against the limit: within it", c1["pages"] == 1 and not c1["over"] and not any("Over its page limit" in t_ for _k, t_ in c1["missing"]))
import subreq as SR
_wp = SR.word_pages; SR.word_pages = lambda f: 5
check("pages against the limit: over, and it says so", DB.card(DL.get(rec, d1), M=M)["over"] and any("Over its page limit" in t_ for _k, t_ in DB.card(DL.get(rec, d1), M=M)["missing"]))
SR.word_pages = _wp
check("a requirement a version changed, waiting for its owner", c1["awaiting"] == [keeps[0]["id"]])
check("what is missing: no owner, requirements with no author, no file", any(t_ == "No owner" for _k, t_ in c2["missing"])
      and any("no author" in t_ for _k, t_ in c2["missing"]) and any("No working file" in t_ for _k, t_ in c2["missing"]))
check("the board shows a card for each", len(dp.board.cards) == 3)
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
QTest.mouseClick(dp.board.cards[d1], Qt.LeftButton); app.processEvents()
check("click a card: everything about it", dp.picked == d1 and dp.detail.c["id"] == d1 and dp.detail.req_table.rowCount() == 2)
check("open a requirement in Assign from it", dp.open_requirement(keeps[0]["id"]) and w.stack.currentWidget() is w.assign_page)
w.go("deliverables"); app.processEvents()
dp.link_volume(d3, "Volume II Past Performance")
check("link a deliverable to a volume by hand", DL.get(RR.Record(w.ws.root), d3)["volume"] == "Volume II Past Performance"
      and next(c for c in dp.cards if c["id"] == d3)["reqs"] == 1)
dp.view.setCurrentIndex(1); app.processEvents()
check("the list is still there", dp.list_box.isVisibleTo(dp) and dp.table.rowCount() == 3)
dp.view.setCurrentIndex(0)
check("one line for Effort home and the dashboard", DB.summary_line(dp.cards).startswith("3 deliverable(s)") and "need attention" in DB.summary_line(dp.cards))
w.go("home"); app.processEvents()
check("Effort home says how the deliverables stand", "deliverable(s)" in w.home_page.deliv.text(), w.home_page.deliv.text())
w.go("dashboard"); app.processEvents()
check("the dashboard counts the deliverables that need attention", w.dash_page.tiles["deliv"].value.text() == "3", w.dash_page.tiles["deliv"].value.text())
w.close()
n = sum(checks)
print(f"QT BOARD PASS ({n}/{len(checks)})" if n == len(checks) else f"QT BOARD FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
