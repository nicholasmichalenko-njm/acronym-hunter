"""2.60.0 Structure and Prove in Qt, and finding a sentence: start the structure from the RFP headings or a Word
outline, see it as it will be (with what is already in each section), Apply keeps assignments valid (a removed section
clears its assignments); Prove counts every sentence per file and the text check adds any missing line in its place;
the search box finds a sentence by words or ID and opens it in Assign."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import compliance as C, effort as E, setupdoc as SD, workspace as W, office_pdf as OP, docxw
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.read_page.read([os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")], os.path.join(EDIR, "K_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
sp = w.structure_page
w.go("structure"); app.processEvents()
check("Structure shows the matrix's structure", sp.text.toPlainText().strip() == C.outline_text(M.outline).strip() and sp.tree.topLevelItemCount() > 0)
sp.letter.setCurrentText("Section L")
check("start from the RFP headings", sp.from_headings() and "L.3.1" in sp.text.toPlainText())
sp.text.setPlainText(sp.text.toPlainText().rstrip() + "\nL.9 Added Section\n"); sp.preview()
check("an edit not applied yet: Apply is on", sp.apply_btn.isEnabled() and "Not applied" in sp.state.text())
n, lost = sp.apply(); app.processEvents()
check("Apply sets it", n == len(M.outline) and any(C.outline_label(o).startswith("L.3.1") for o in M.outline))
labs = [C.outline_label(o) for o in M.outline]
pg = w.assign_page
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
a = by("The Offeror shall describe its technical approach")
target = next(l for l in labs if l.startswith("L.3.1"))
pg.set_target(target); pg.select(a["id"]); pg.do_req(); app.processEvents()
w.go("structure"); app.processEvents()
row = sp.tree.findItems(target, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchRecursive)[0]
check("as it will be: the requirement counted in its section", row.text(1) == "1", row.text(1))
docx = os.path.join(tmp, "outline.docx")
d = docxw.Doc(); d.heading("Volume I Technical", 1); d.heading("1.1 Technical Approach", 2); d.heading("Volume II Management", 1); d.save(docx)
check("start from a Word outline", sp.from_word(docx) and "1.1 Technical Approach" in sp.text.toPlainText())
check("Apply would clear the assignment in a section no longer there", "clears the assignments in 1 section" in sp.state.text(), sp.state.text())
n, lost = sp.apply(); app.processEvents()
check("Apply clears it", lost == 1 and not a.get("map"), (n, lost, a.get("map")))
w.go("prove"); app.processEvents()
pv = w.prove_page
check("Prove: coverage per file and a total", pv.table.rowCount() == 2 and pv.table.item(1, 0).text() == "Total"
      and pv.table.item(0, 2).text() == "1", [pv.table.item(0, c).text() for c in range(pv.table.columnCount())])
res = pv.run_check()
check("the text check: every word in the review", res and sum(r["missing"] for r in res) == 0 and "all" in pv.check_line.text())
drop = next(it for it in M.items if sum(1 for x in M.items if x["key"] == it["key"]) == 1 and len(it["text"].split()) > 8
            and it is not a)
M.items.remove(drop)
res = pv.run_check()
check("a line missing from the review is listed", pv.missing.rowCount() >= 1 and pv.add_btn.isEnabled())
added = pv.add_missing(); app.processEvents()
check("Add the missing lines puts it back in its place", added and any(it["key"] == drop["key"] for it in M.items)
      and sum(r["missing"] for r in pv.results) == 0)
w.save_now()
w.search.setText("stand-alone basis"); w.find_go(); app.processEvents()
sel = pg.selected()
check("search by words opens the sentence in Assign", w.stack.currentWidget() is pg and sel and "stand-alone" in sel[0]["text"])
w.search.setText(a["id"].lower()); w.find_go(); app.processEvents()
check("search by ID", pg.selected() and pg.selected()[0]["id"] == a["id"])
w.close()
n = sum(checks)
print(f"QT STRUCTURE PROVE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT STRUCTURE PROVE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
