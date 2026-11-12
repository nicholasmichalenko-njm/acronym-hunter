"""3.86.0 offscreen: Setup shows each block the selected section will print, in print order, with its kind and where it
came from; act on the row: Earlier, Later, Move to another section..., Print the reference only (and the words again),
Show it in Review; a move here is a move in Review too; the reference only prints in the setup. Fictional content
(the Kestrel set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, setupdoc as SD
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management Approach")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read([os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("the matrix is read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
ap = w.assign_page
M = w.review.M
reqs = [it for it in M.items if it.get("section") == "L.3.1" and it.get("type") != "Heading"][:3]
ap.R.req(reqs, "1.1 Technical Approach")
LAB = "1.1 Technical Approach"
w.go("setups"); app.processEvents()
sp = w.setups_page
b = sp.builder
b.btree.setCurrentItem(next(iter(b.btree.findItems(LAB, Qt.MatchExactly | Qt.MatchRecursive, 0)))); app.processEvents()
bl = sp.blocks
check("the section's printed blocks, in print order", bl.isVisibleTo(w) and bl.count() == 3
      and [bl.item(i).data(Qt.UserRole) for i in range(3)] == [it["id"] for it in reqs])
check("each says its kind and where it came from", bl.item(0).text().startswith("1. Requirement") and "p." in bl.item(0).text(), bl.item(0).text())
bl.setCurrentRow(0)
check("act on the row", [a.text() for a in bl.menu(run=False).actions() if a.text()] ==
      ["Earlier", "Later", "Move to another section...", "Print the reference only", "Show it in Shred"])
first = reqs[0]["id"]
check("Later moves it down", bl.move(first, 1) and SD.placed_in(M)[LAB][1] == first and bl.item(1).data(Qt.UserRole) == first)
check("Earlier moves it back", bl.move(first, -1) and SD.placed_in(M)[LAB][0] == first)
check("Print the reference only", bl.toggle_ref(first) and SD.block_text(M, reqs[0]).endswith("(see the RFP)")
      and "(reference only)" in bl.item(0).text())
check("... and the words again", bl.toggle_ref(first) is False and not SD.block_text(M, reqs[0]).endswith("(see the RFP)"))
check("Move to another section: one set of records", bl.move_to(reqs[2]["id"], "1.2 Management Approach")
      and reqs[2]["id"] in SD.placed_in(M)["1.2 Management Approach"] and bl.count() == 2
      and ap.R.item(reqs[2]["id"])["map"] == "1.2 Management Approach")
check("Show it in Review opens Review on the sentence", bl.show_source(first) and w.stack.currentWidget() is ap
      and [it["id"] for it in ap.selected()] == [first])

print(f"QT SETUP 386 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
