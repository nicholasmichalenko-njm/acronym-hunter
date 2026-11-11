"""3.18.2 Undo everywhere, offscreen: the window's Undo (top bar and Ctrl+Z) undoes the last change on the page you are on
and says what it puts back: in Review a decision, a section added, renamed, moved or taken out; on the pages that change
the matrix (Structure, Coverage, Matrix, Response Setup) the matrix's steps; a page with nothing to undo says so. Every
decided sentence can go in the response structure (the customer's too, written for the writers, not answered); Put all in
section keeps decisions. The decide panel scrolls on its own, apart from the page."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, compliance as C, pagemarks as PM, suggestrules as SR
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Heron").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Heron")
w.read_page.read([PDF], os.path.join(ED, "Heron_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
pg = w.assign_page
M = w.review.M
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()

rows = [it for it in M.items if it.get("file") == "Section_L_print.pdf" and not it.get("decision") and it.get("type") != "Heading"
        and it["id"] in pg.view.boxes]
check("a document with undecided sentences to try", len(rows) >= 10, len(rows))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
import outline_ops as O, setupdoc as SD
# a decision
pg.select(rows[0]["id"]); pg.do_lm("L"); app.processEvents()
check("the top bar's Undo names the last change", w.undo_btn.isEnabled() and rows[0]["id"] in w.undo_text()
      and "Undo:" in w.undo_btn.toolTip(), w.undo_text())
w.undo_here(); app.processEvents()
check("Undo puts the decision back", rows[0].get("decision", "") == "" if pg.R.item(rows[0]["id"]) is rows[0]
      else pg.R.item(rows[0]["id"]).get("decision", "") == "", pg.R.item(rows[0]["id"]).get("decision"))
# a section added by mistake
n_out = len(M.outline)
lab = pg.new_section(title="Mistake section")
app.processEvents()
check("a section added ...", lab and len(M.outline) == n_out + 1 and pg.target == lab)
check("... Undo says so", "Section added" in w.undo_text(), w.undo_text())
w.activateWindow(); pg.view.setFocus(); app.processEvents()
QTest.keyClick(w, Qt.Key_Z, Qt.ControlModifier); app.processEvents()
if len(M.outline) != n_out:                   # offscreen windows are not always active: the shortcut's own action
    w.undo_here(); app.processEvents()
check("Ctrl+Z (or Undo) takes the section back out, and it is no longer the target", len(M.outline) == n_out and lab not in O.labels(M)
      and pg.target != lab, (len(M.outline), n_out, pg.target))
check("the structure list shows it gone", not pg.tree.findItems("Mistake section", Qt.MatchRecursive | Qt.MatchContains, 0))
# rename, move, delete
first = O.labels(M)[0]
title0 = M.outline[0].get("title", "")
pg.rename_section(first, "Renamed by mistake"); app.processEvents()
w.undo_here(); app.processEvents()
check("Undo puts a renamed section's title back", M.outline[0].get("title", "") == title0)
lab2 = pg.new_section(title="Second"); lab3 = pg.new_section(title="Third"); app.processEvents()
order = O.labels(M)
pg.set_target(lab3); pg.outline_op(O.move, -1); app.processEvents()
moved = O.labels(M)
w.undo_here(); app.processEvents()
check("Undo puts a moved section back", O.labels(M) == order and moved != order, (order, moved))
pg.set_target(lab2); pg.delete_section(); app.processEvents()
w.undo_here(); app.processEvents()
check("Undo brings a deleted section back", lab2 in O.labels(M))
# the pages that change the matrix share its steps
pg.select(rows[1]["id"]); pg.do_customer(); app.processEvents()
w.go("structure"); app.processEvents()
check("Structure: Undo offers the last matrix change", bool(w.undo_text()) and w.undo_btn.isEnabled(), w.undo_text())
w.undo_here(); app.processEvents()
check("... and undoes it there", not pg.R.item(rows[1]["id"]).get("decision"))
w.go("settings"); app.processEvents()
check("a page with nothing to undo says so", w.undo_text() == "" and not w.undo_btn.isEnabled()
      and w.undo_here() is None and "Nothing to undo" in w.statusBar().currentMessage())
w.go("assign"); app.processEvents()
# every decided sentence can go in the structure
sec = O.labels(M)[-1]
cust, sup, und, ign = rows[2], rows[3], rows[4], rows[5]
pg.select(cust["id"]); pg.do_customer(); app.processEvents()
pg.select(cust["id"]); app.processEvents()
check("the customer's card offers + Section", getattr(pg, "section_box", None) is not None and pg.section_box.count() > 1)
pg.act(pg.R.add_section, pg.R.item(cust["id"]), sec); app.processEvents()
cust = pg.R.item(cust["id"])
check("the customer's sentence goes in a section and stays the customer's", cust["decision"] == "Customer"
      and sec in SD.item_sections(M, cust))
check("... it is in the response structure for the writers", cust["id"] in SD.placed_in(M).get(sec, []) and SD.kind_of(cust) == "Customer")
out = os.path.join(tmp, "setup.docx")
try:
    d = SD.build_doc(M) if hasattr(SD, "build_doc") else None
except Exception:
    d = None
w.undo_here(); app.processEvents()
check("Undo takes it back out of the section", sec not in SD.item_sections(M, pg.R.item(cust["id"])))
pg.select(sup["id"]); pg.do_ctx(); app.processEvents()
pg.select(ign["id"]); pg.do_clear(); app.processEvents()
pg.select(cust["id"]); app.processEvents()
sc = pg.view.scene(); sc.clearSelection()
for x in (cust, sup, und, ign):
    pg.view.boxes[x["id"]].setSelected(True)
app.processEvents()
n = pg.bulk_section(sec); app.processEvents()
g = {k: pg.R.item(x["id"]) for k, x in (("cust", cust), ("sup", sup), ("und", und), ("ign", ign))}
check("Put all in section keeps decisions: support stays support, the customer's stays the customer's",
      g["cust"]["decision"] == "Customer" and g["sup"]["decision"] == "Context" and sec in SD.item_sections(M, g["cust"])
      and sec in SD.item_sections(M, g["sup"]), {k: (v["decision"], SD.item_sections(M, v)) for k, v in g.items()})
check("... an undecided one becomes a requirement there; an ignored one stays out", g["und"]["decision"] == "Keep"
      and sec in SD.item_sections(M, g["und"]) and g["ign"]["decision"] == "Drop" and not SD.item_sections(M, g["ign"]) and n == 3, n)
w.undo_here(); app.processEvents()
check("... one Undo puts all of it back", not SD.item_sections(M, pg.R.item(cust["id"])) and pg.R.item(und["id"]).get("decision", "") == "")
# page lengths for each section: the RFP's limit or the team's guideline
import pagebudget as PB, zipfile
secA, secB = O.labels(M)[1], O.labels(M)[-1]
check("a section's pages: the RFP's limit", pg.section_pages(secA, answer=(4, "rfp")) == "4 RFP" and PB.source(M, secA) == "rfp")
check("a section's pages: the team's guideline", pg.section_pages(secB, answer=(2.5, "team")) == "2.5 guide")
node = pg.tree.findItems(secA, Qt.MatchRecursive | Qt.MatchExactly, 0)
check("the structure list shows pages and who set them", node and node[0].text(3) == "4 RFP"
      and "RFP limit" in node[0].toolTip(3), node[0].text(3) if node else None)
w.undo_here(); app.processEvents()
check("Undo takes the last page length off", PB.pages(M, secB) is None and PB.pages(M, secA) == 4)
b = pg.budget_dialog(run=False)
b.spins[secA].setValue(5); b.save(); app.processEvents()
check("the Page budget keeps who set a section's pages", PB.pages(M, secA) == 5 and PB.source(M, secA) == "rfp"
      and b.bys[secA].currentData() == "rfp")
c2 = pg.R.item(cust["id"])
if c2.get("decision") != "Customer":
    pg.select(c2["id"]); pg.do_customer(); app.processEvents(); c2 = pg.R.item(cust["id"])
pg.R.add_section(c2, secA)
out = os.path.join(tmp, "setup"); os.makedirs(out)
SD.export(M, out)
txt = "".join(zipfile.ZipFile(os.path.join(r, f)).read("word/document.xml").decode("utf-8", "replace")
              for r, _d, fs in os.walk(out) for f in fs if f.endswith(".docx"))
check("Response Setup prints the RFP's page limit", "Page limit (the RFP): 5 pages" in txt)
check("... and the customer's sentence put in the section, marked not answered", "not answered" in txt)
w.go("structure"); app.processEvents()
sn = w.structure_page.tree.findItems(secA, Qt.MatchRecursive | Qt.MatchContains, 0)
check("Structure shows the pages too", sn and sn[0].text(3) == "5 RFP", sn[0].text(3) if sn else None)
w.go("assign"); app.processEvents()
# the decide panel scrolls on its own
w.resize(1280, 640); app.processEvents()
sa = pg.side_area
check("the decide panel and the structure scroll on their own", sa.widget() is not None and pg.dec_box.isAncestorOf(pg.dec_box)
      and sa.isAncestorOf(pg.tree) and not sa.isAncestorOf(pg.view) and sa.verticalScrollBar().maximum() > 0,
      sa.verticalScrollBar().maximum())
v0 = pg.view.verticalScrollBar().value()
sa.verticalScrollBar().setValue(sa.verticalScrollBar().maximum()); app.processEvents()
check("... scrolling it leaves the page where it was", pg.view.verticalScrollBar().value() == v0)
w.close()
n = sum(checks)
print(f"QT UNDO {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
