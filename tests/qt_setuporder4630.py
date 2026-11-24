"""4.63.0 offscreen: Setup > Order under each heading... The window lists the kinds with the style each is written in;
Up and Down move a row; Use this order keeps it for the whole setup or for one heading; the button beside it puts it
back. The two buttons are named for what they bring. Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, setupdoc as SD, setuporder as SO
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, setuporderview as SV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


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
sp = w.setups_page
check("with nothing shredded the window does not open, and says why", SV.open_order(sp, run=False) is None)
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
w.go("setups"); app.processEvents()
names = [b.text() for b in sp.bar.commands if b.isVisibleTo(w)]
check("Setup's bar: the outline, the template, the order, and Make the setup", names[:3] == ["Bring in an outline...", "Choose the Word template...",
      "Order under each heading..."] and "Make the setup" in names and len(names) <= 5, names)
d = SV.open_order(sp, run=False)
M = w.review.M; S = SD.setup_of(M)
labs = SD.labels(M)
check("the window: For the whole setup first, then each heading", d is not None and d.where.itemText(0) == "The whole setup"
      and [d.where.itemData(i) for i in range(1, d.where.count())] == labs, labs)
rows = [d.rows.item(i).text() for i in range(d.rows.count())]
check("each kind is a row, with the style it is written in", len(rows) == len(SO.ROWS) and rows[4].startswith("RFP text, with its support text")
      and "style: SK RFP Requirement" in rows[4] and any("Management guidance" in r and "SK PM Direction" in r for r in rows), rows)
check("no order set: it says each piece is written where it always was, and there is nothing to put back", "always was" in d.said.text()
      and not d.b_back.isEnabled() and d.b_back.text() == "As it was written before", d.said.text())
d.rows.setCurrentRow(d.order().index("pm"))
while d.order().index("pm") > 0:
    d.move(-1)
check("Up moves a row; the first cannot go higher", d.order()[0] == "pm" and d.move(-1)[0] == "pm")
d.move(1)
check("Down moves it back one", d.order()[1] == "pm")
check("nothing is kept until Use this order", "kind_order" not in S)
got = d.use()
check("Use this order keeps it for the whole setup, and the matrix has a change to save", SO.own(S, "")[1] == "pm" and got[1] == "pm"
      and SO.order_for(S, labs[-1])[1] == "pm" and d.b_back.isEnabled())
d.where.setCurrentIndex(d.where.count() - 1); app.processEvents()
lab = labs[-1]
check("a heading shows the whole setup's order until it has its own", d.order() == SO.own(S, "") and "follows the whole setup" in d.said.text()
      and d.b_back.text() == "Same as the whole setup" and not d.b_back.isEnabled(), d.said.text())
d.rows.setCurrentRow(d.order().index("library"))
while d.order().index("library") > 0:
    d.move(-1)
d.use()
check("its own order is kept for that heading alone, and the list says so", SO.own(S, lab)[0] == "library" and SO.own(S, "")[0] != "library"
      and "(its own order)" in d.where.currentText() and "its own order" in d.said.text(), d.where.currentText())
d.back()
check("Same as the whole setup takes it away", SO.own(S, lab) is None and "(its own order)" not in d.where.currentText())
d.where.setCurrentIndex(0); app.processEvents()
d.back()
check("As it was written before takes the whole setup's order away", SO.order_for(S, lab) is None and "always was" in d.said.text())
w.close()
print(f"QT SETUP ORDER 4630 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
