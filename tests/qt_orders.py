"""Amendments as instructions and task orders in the Library, offscreen: an amendment that says what to change shows
Apply its instructions; the dialog lists each instruction, ticks them all, picks the document it changes and says which
apply and which are not found; applying makes the base document's Conformed version and says at once what changed; a
task order is filed under the base contract, listed right under it, and can be moved out."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, office_pdf as OP, pdfmini, docversions as DV
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow
from skqt.librarypage import ConformDialog

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); CUST = os.path.join(EDIR, "Customer documents"); os.makedirs(CUST)
IN = os.path.join(tmp, "in"); os.makedirs(IN)
BASE = ["L.4.2 Volume II. Volume II shall not exceed twenty (20) pages.", "L.5.3 Risk. The Offeror shall describe its risk process.",
        "M.2.4 Past Performance. Past performance will be rated."]
AMD = ["AMENDMENT 0001. The solicitation is amended as follows:",
       "1. In paragraph L.4.2, delete \"twenty (20) pages\" and insert \"twenty-five (25) pages\".",
       "2. Paragraph M.2.4 is hereby deleted in its entirety.",
       "3. In paragraph L.9.9, delete \"foo\" and insert \"bar\"."]
P1 = os.path.join(IN, "RFP.pdf"); pdfmini.write(P1, [BASE], size=9)
PA = os.path.join(IN, "RFP_Amendment_0001.pdf"); pdfmini.write(PA, [AMD], size=9)
PC = os.path.join(IN, "IDIQ_Base_Contract.pdf"); pdfmini.write(PC, [["Section B. The contractor shall provide engineering services."]], size=9)
PT = os.path.join(IN, "Task_Order_0003.pdf"); pdfmini.write(PT, [["Task Order 0003. The contractor shall perform orbit analysis."]], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=CUST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
w.go("library"); app.processEvents()
pg = w.library_page
pg.add([P1], choices={"RFP.pdf": {"initial": "R", "type": "RFP"}}); wait(lambda: pg.worker is None and pg.panel.state == "done")
pg.add([PA], choices={"RFP_Amendment_0001.pdf": {"choice": "new", "initial": "A1", "type": "Amendment"}})
wait(lambda: pg.worker is None and pg.panel.state == "done")
lib = DV.Library(w.ws.p("documents")).load()
amend = next(d for d in lib.docs if d.get("type") == "Amendment")
check("adding it says it holds instructions and where to apply them", "3 change instruction(s)" in (getattr(w, "last_hint", "") or ""),
      getattr(w, "last_hint", ""))
base = next(d for d in lib.docs if d.get("type") == "RFP")
pg.select(amend["id"]); app.processEvents()
check("an amendment shows Apply its instructions", not pg.b_conform.isHidden())
import amendinst as AI
dlg = ConformDialog(pg, pg.lib, pg.lib.doc(amend["id"]), AI.instructions_of(pg.lib, pg.lib.doc(amend["id"])["versions"][-1]), base["id"])
check("the dialog lists each instruction, all ticked, and says what applies", dlg.list.count() == 3
      and all(dlg.list.item(k).checkState() == Qt.Checked for k in range(3)) and dlg.result.text().startswith("2 of 3 instruction(s) applied")
      and dlg.go.isEnabled(), dlg.result.text())
check("... the one not found says why", "L.9.9 is not in the document" in dlg.list.item(2).toolTip(), dlg.list.item(2).toolTip())
dlg.deleteLater()
v = pg.conform(base_id=base["id"], answer=True)
lib = DV.Library(w.ws.p("documents")).load()
check("applied: the RFP's Conformed version", v and v["label"] == "Conformed (A1)" and len(lib.doc(base["id"])["versions"]) == 2)
s = (getattr(w, "last_changes", None) or [None])[0]
check("... and what changed is said at once", s and s["title"].startswith("What changed in Conformed (A1)") and s["changed"] == 1 and s["removed"] == 1,
      s and s["text"])
# a task order under the contract
pg.add([PC], choices={"IDIQ_Base_Contract.pdf": {"choice": "new", "initial": "CT", "type": "Contract"}}); wait(lambda: pg.worker is None and pg.panel.state == "done")
pg.add([PT], choices={"Task_Order_0003.pdf": {"choice": "new"}}); wait(lambda: pg.worker is None and pg.panel.state == "done")
lib = DV.Library(w.ws.p("documents")).load()
to = next(d for d in lib.docs if d.get("type") == "Task order")
ct = next(d for d in lib.docs if d.get("type") == "Contract")
check("a task order is typed, numbered and filed under the contract", to["initial"] == "TO1" and to["under"] == ct["id"], (to.get("initial"), to.get("under")))
names = [pg.table.item(r, 0).text() for r in range(pg.table.rowCount())]
i_ct = next(i for i, n in enumerate(names) if n.startswith("IDIQ"))
check("... listed right under it", names[i_ct + 1].startswith("↳ Task_Order") or names[i_ct + 1].startswith("↳ Task Order"), names)
pg.select(to["id"]); app.processEvents()
check("... and says so", "under IDIQ" in pg.d_info.text() and pg.d_under.currentData() == ct["id"], pg.d_info.text())
pg.set_under("")
check("Filed under: taken out", "under" not in DV.Library(w.ws.p("documents")).load().doc(to["id"]))
w.close_effort()
n = sum(checks)
print(f"QT ORDERS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
