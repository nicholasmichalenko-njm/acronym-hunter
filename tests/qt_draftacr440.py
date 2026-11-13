"""4.4.0 Drafts > Acronyms (claude/stationkeeper-drafts-plan-4.4.md, step 3; decision 7), offscreen, on a two-volume
fictional effort: Check the drafts reads each volume's newest draft against the effort's acronym list; the counts per
volume; a term not in the list goes back to Acros & Abs marked From our drafts: <volume>, once; it shows here until it is
decided there; Fix in a copy opens the 3.92.0 check on the selected volume; In our drafts on Acros & Abs opens this tab.
Fictional content only."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, docxw, draftvols as DV, acrmore as AM
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n"
                                                 "Volume II Management\n2.1 Management Plan")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M = w.review.M
vols = DV.volumes(M)
ap = w.acronym_page
w.go("acronyms"); app.processEvents()
s = ap.session
check("the effort's acronym session", s is not None)
AM.add_manual(s, "KPO", "Acronym", "Kestrel Program Office", "", ("results", "list"))
from skqt.acrlayout import list_entries
check("KPO is in the list", ("KPO", "Kestrel Program Office") in list_entries(s), list_entries(s))

F1, F2 = os.path.join(tmp, "lib1"), os.path.join(tmp, "lib2"); os.makedirs(F1); os.makedirs(F2)
d1 = docxw.Doc(); d1.heading(vols[0], 1); d1.heading("1.1 Technical Approach", 2)
d1.rich([("The KPO reviews each design. The Kestrel Program Office (KPO) leads the work. The ZQX bench runs nightly.", None)])
p1 = os.path.join(F1, "Tech.docx"); d1.save(p1)
d2 = docxw.Doc(); d2.heading(vols[1], 1); d2.heading("2.1 Management Plan", 2)
d2.rich([("The ZQX bench and the WVR log are kept weekly.", None)])
p2 = os.path.join(F2, "Mgmt.docx"); d2.save(p2)
DV.set_folder(w.ws, vols[0], F1); DV.set_folder(w.ws, vols[1], F2)

ap.b_drafts.trigger(); app.processEvents()
pg = w.draftacr_page
check("In our drafts on Acronyms opens Drafts > Acronyms", w.stack.currentWidget() is pg and w._tab_keys[:3] == ["drafts", "draftacr", "techedit"],
      w._tab_keys)
check("one main button, Check the drafts", pg.bar.main is pg.b_check and pg.table.rowCount() == 2)
rows = pg.check(); app.processEvents()
n1, n2 = DV.acr_counts(rows[0]["report"]), DV.acr_counts(rows[1]["report"])
check("each volume checked against the list", n1["before"] == 1 and n1["unlisted"] == 1 and n2["unlisted"] == 2, (n1, n2))
check("... the counts in the table", [pg.table.item(0, c).text() for c in (2, 3, 4)] == ["1", "0", "1"]
      and pg.table.item(1, 4).text() == "2", [[pg.table.item(i, c).text() for c in range(6)] for i in range(2)])
z = s.results.get("ZQX") or {}
check("a term not in the list goes back to Acronyms, marked From our drafts", z.get("from_drafts") == vols
      and z.get("locations") == [f"From our drafts: {vols[0]}"] and "WVR" in s.results, z)
check("... kept with the session", "ZQX" in (w.ws.load_session() or {}).get("manual_items", {}))
check("... shown here until it is decided", DV.pending(s) == {"WVR": [vols[1]], "ZQX": vols} and pg.pending_list.rowCount() == 2
      and pg.p_card.isVisibleTo(w))
check("... said in a sentence", "2 term(s) not in the list are below to decide" in pg.said.text(), pg.said.text())
pg.check()
check("checking again adds nothing twice", len([t for t in s.results if t == "ZQX"]) == 1 and "below to decide" not in pg.said.text(), pg.said.text())
# 4.23.2: decided here, on the term's row (no jump to Acros & Abs)
from PySide6.QtWidgets import QPushButton
check("4.23.2: no Decide them in Acronyms; each term has its meaning line and two buttons", pg.bar.action("Decide them in Acronyms") is None
      and pg.pending_terms == ["WVR", "ZQX"] and [b.text() for b in pg.pending_list.cellWidget(0, 3).findChildren(QPushButton)]
      == ["Add to effort list", "Not a term"])
pg.pending_list.cellWidget(0, 2).setText("Wide View Radiometer")
pg.pending_list.cellWidget(0, 3).findChildren(QPushButton)[0].click(); app.processEvents()
check("Add to effort list on the row: in the list with the meaning typed", s.effort.rows["WVR"]["Status"] == "In the list"
      and s.effort.rows["WVR"]["Definition"] == "Wide View Radiometer" and pg.pending_terms == ["ZQX"], s.effort.rows.get("WVR"))
pg.pending_list.cellWidget(0, 3).findChildren(QPushButton)[1].click(); app.processEvents()
check("Not a term on the row: decided, and the card folds away", s.effort.rows["ZQX"]["Status"] == "Not a term" and DV.pending(s) == {}
      and not pg.p_card.isVisibleTo(w), DV.pending(s))
check("it is the same decision on Acronyms", ap.session is s and s.results["WVR"].get("effort") == "In the list")
pg.table.selectRow(0)
dlg = pg.fix(); app.processEvents()
check("Fix in a copy: the 3.92.0 check on the selected volume's draft", dlg is not None and dlg.path == p1
      and any(f["term"] == "KPO" and f["kind"] == "before" for f in dlg.report["findings"]))
dlg.close()
w.close()
n = sum(checks)
print(f"QT DRAFTACR 440 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
