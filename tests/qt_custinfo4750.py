"""4.75.0: Customer information on the screen, and More in the Compliance pass. Overview > Customer information lists
the people and the facts; a fact is typed there or taken in Shred (More > Customer info); a filled one asks before it is
replaced. More holds four captures. Fictional (Kestrel)."""
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
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import custinfo as CI, effortrec as RR
from skqt import comppass as CP, shredselbar as SSB
pg = w.assign_page
cp = w.custinfo_page
check("Overview's tabs: Overview, Customer information, Calendar, Tasks, Meetings", [t for _k, t in MW.TABS["home"]] ==
      ["Overview", "Customer information", "Calendar", "Tasks", "Meetings"])
w.go("custinfo"); app.processEvents()
check("the tab opens the page under the Overview", w.stack.currentWidget() is cp and w.step_btns["home"].isChecked() and w.page_title.text() == "Overview",
      w.page_title.text())
check("one main button, + Contact; People says no one yet; every fact is listed, empty, with where it usually is", cp.b_add.text() == "+ Contact"
      and cp.people_none.isVisibleTo(cp) and not cp.people.isVisibleTo(cp)
      and cp.facts.rowCount() == len(CI.LABELS) + len(CI.GROUPS) and "0 of" in cp.said.text(), (cp.facts.rowCount(), cp.said.text()))
r_sol = next(r for r in range(cp.facts.rowCount()) if cp.facts.item(r, 0).text() == "Solicitation number")
check("... an empty fact shows its usual place", cp.facts.item(r_sol, 2).text() == "Usually: SF 33 block 3, SF 1449 block 5" and cp.facts.item(r_sol, 1).text() == "")
check("... the groups are headings across the table", cp.facts.item(0, 0).text() == "Who the customer is" and cp.facts.columnSpan(0, 0) == 3)
cp.set_value("Solicitation number", "FA8811-26-R-0099"); app.processEvents()
rec = RR.Record(w.ws.root)
r_sol = next(r for r in range(cp.facts.rowCount()) if cp.facts.item(r, 0).text() == "Solicitation number")
check("typed on the page: kept at once, with who and when", CI.fact(rec, "Solicitation number")["value"] == "FA8811-26-R-0099"
      and cp.facts.item(r_sol, 2).text().startswith("typed") and "1 of" in cp.said.text(), cp.facts.item(r_sol, 2).text())
cid = cp.add_contact({"role": "Contracting Officer", "name": "Jordan Reyes", "title": "", "org": "NOIA", "email": "jordan.reyes@noia.example", "phone": ""})
check("+ Contact: the person is listed with a role", cid and cp.people.isVisibleTo(cp) and cp.people.rowCount() == 1
      and [cp.people.item(0, k).text() for k in range(2)] == ["Contracting Officer", "Jordan Reyes"])
check("a contact with no name is not added", cp.add_contact({"role": "", "name": " ", "title": "", "org": "", "email": "", "phone": ""}) is None and cp.people.rowCount() == 1)
# More, in the Compliance pass
w.go("comppass"); app.processEvents()
rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]
a = rows[6]
pg.select(a["id"]); app.processEvents(); SSB.refresh(pg); app.processEvents(); f = pg.sel_bar
check("the bar has More  M", f.more.text() == "More  M")
names = [x.text() for x in f.more_menu.actions()]
check("More holds four, numbered: Customer info, Objective, Hot button, Graphic need", names == ["&1  Customer info", "&2  Objective", "&3  Hot button", "&4  Graphic need"], names)
sub = [x.text() for x in f.more_menu.custinfo.actions() if x.text()]
check("Customer info: a contact, then every fact by group", sub[0] == "A contact..." and [x for x in sub if x in CI.LABELS] == list(CI.LABELS)
      and "Who the customer is" in sub, sub[:4])
QTest.keyClick(pg.view, Qt.Key_M); app.processEvents()
check("M opens it beside the piece", getattr(pg, "_more_menu", None) is not None and len(pg._more_menu.actions()) == 4)
pg._more_menu.close()
out = CP.fact(pg, "Submit to")
rec = RR.Record(w.ws.root)
check("a fact taken from the piece: the customer's words, with the document and where", out == "set" and CI.fact(rec, "Submit to")["value"] == " ".join(a["text"].split())[:300]
      and CI.fact(rec, "Submit to")["how"] == "captured" and CI.where(CI.fact(rec, "Submit to")) not in ("", "typed"), CI.where(CI.fact(rec, "Submit to")))
b_ = rows[7]
pg.select(b_["id"]); app.processEvents()
check("a fact already filled is not replaced unless he says so", CP.fact(pg, "Submit to", replace=False) is None or CP.fact(pg, "Submit to", replace=False) == "same")
rec = RR.Record(w.ws.root)
check("... it holds what it held", CI.fact(rec, "Submit to")["value"] == " ".join(a["text"].split())[:300])
check("... Replace takes the new words", CP.fact(pg, "Submit to", replace=True) == "set" and CI.fact(RR.Record(w.ws.root), "Submit to")["value"] == " ".join(b_["text"].split())[:300])
w.go("custinfo"); app.processEvents()
r_sub = next(r for r in range(cp.facts.rowCount()) if cp.facts.item(r, 0).text() == "Submit to")
check("back on the page: the captured fact, and where it came from", cp.facts.item(r_sub, 1).text() == " ".join(b_["text"].split())[:300]
      and cp.facts.item(r_sub, 2).text() == CI.where(CI.fact(RR.Record(w.ws.root), "Submit to")) and "2 of" in cp.said.text(), cp.facts.item(r_sub, 2).text())
w.close()
print(f"QT CUSTINFO 4750 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
