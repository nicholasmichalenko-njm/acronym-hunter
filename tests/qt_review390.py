"""3.90.0 Review's tabs and views, offscreen (decision 13): Review's tabs are Verify, Read, Compare, Review in the order of
the work (Compare left the Effort Library group; the Library is one page); L to M and Coverage are views beside Review's
page, not pages (go("crosswalk") and go("prove") open them there); an L to M row shows its instruction's sentence on the
page; a Coverage row opens its file; the lines go to Our structure only; Verify's last page, verified, offers Read for a
file not read yet; a Verify change after the read says so on Review, and read it again ticks that file on the Read tab;
Layout says covers moved to Section designs. Fictional content (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, pdfmini, verifystate as VS
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, TABS, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CUST = os.path.join(EDIR, "Customer documents"); os.makedirs(CUST)
IN = os.path.join(tmp, "incoming"); os.makedirs(IN)
L_ = ["L.3 PROPOSAL VOLUMES", "Volume I Technical shall not exceed 50 pages.",
      "L.4 RISK MANAGEMENT", "The Offeror shall identify the five highest program risks.",
      "M.2 EVALUATION OF RISK", "The Government will evaluate the realism of the risk approach."]
P1 = os.path.join(IN, "Kestrel_Section_LM.pdf"); pdfmini.write(P1, [L_], size=9)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
Lst = E.EffortList(LIST, "Kestrel"); Lst.pending = True; Lst.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CUST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk Management")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("Review's tabs: Verify, Read, Compare, Review", [k for k, _t in TABS["assign"]] == ["verify", "read", "compare", "assign"]
      and "compare" not in dict(dict(RAIL)["Effort Library"]) and "library" not in TABS and "matrix" not in TABS)
w.open_effort("Kestrel")
w.go("docs"); app.processEvents()
w.docs_page.add([P1], choices=[{}])
C1 = os.path.join(CUST, "Kestrel_Section_LM.pdf")
# Verify first: the last page, verified, offers Read
w.go("verify"); app.processEvents()
vp = w.verify_page
vp.open_doc(C1); app.processEvents()
vp.store().verify(vp.doc, 1); vp.show_page(); app.processEvents()
check("Verify's last page, verified: the next step is Read", "Next: read it into Review" in vp.line.text(), vp.line.text())
check("... and it ticks the file on the Read tab", vp.read_next() == 1 and w.stack.currentWidget() is w.read_page
      and [w.page_tabs.tabText(i) for i in range(w.page_tabs.count())] == ["Verify", "Read", "Compare", "Review"]
      and w.page_tabs.tabText(w.page_tabs.currentIndex()) == "Read")
w.read_page.read([C1], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"), identities="suggested")
check("read", wait(lambda: w.review is not None))
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.open_file("Kestrel_Section_LM.pdf"); app.processEvents()
check("Review opens on Our structure", pg.views.current() == "structure" and pg.views.tabs.tabText(0) == "Our structure")
# L to M is a view of Review, not a page
w.go("crosswalk"); app.processEvents()
check("go(crosswalk): Review with the L to M view", w.stack.currentWidget() is pg and pg.views.current() == "lm"
      and w.crosswalk_page.isVisibleTo(pg) and w.step_btns["assign"].isChecked())
cw = w.crosswalk_page
row = next(i for i, r in enumerate(cw.rows) if r["num"] == "L.4")
cw.table.selectRow(row); app.processEvents()
risk = next(it for it in w.review.M.items if "five highest" in it["text"])
check("an L to M row shows its instruction's sentence on the page", pg.cur == risk["id"] or risk["id"] in [b for b, x in pg.view.boxes.items() if x.isSelected()],
      pg.cur)
check("the lines go to Our structure only", pg.placer.gutter.compute() == [])
w.go("prove"); app.processEvents()
check("go(prove): Review with the Coverage view", w.stack.currentWidget() is pg and pg.views.current() == "coverage" and w.prove_page.isVisibleTo(pg))
pv = w.prove_page
r0 = next(r for r in range(pv.table.rowCount()) if pv.table.item(r, 0).text() == "Kestrel_Section_LM.pdf")
check("a Coverage row opens its file on the page", pg.views.open_file_row(r0) == "Kestrel_Section_LM.pdf" and pg.views.current() == "structure"
      and pg.file == "Kestrel_Section_LM.pdf")
# Verify changes the file after the read
pg.placer.show_left()
check("nothing changed since the read: no line", "read it again" not in pg.placer.left_lbl.text())
st = vp.store()
st.doc("Kestrel_Section_LM.pdf")["changed"] = "2999-01-01T00:00"; st.save()
pg.placer.show_left()
check("Verify changed the file after the read: Review says so", "Verify changed this file after it was read" in pg.placer.left_lbl.text()
      and "href='reread'" in pg.placer.left_lbl.text(), pg.placer.left_lbl.text())
check("... read it again ticks only that file on the Read tab", pg.placer.select_left("reread") == 1 and w.stack.currentWidget() is w.read_page
      and w.read_page.chosen() == [C1], w.read_page.chosen())
check("Verify stamps a change", VS.changed_after(st, "Kestrel_Section_LM.pdf", "2026-01-01 00:00") and not VS.changed_after(st, "Kestrel_Section_LM.pdf", "2999-12-31 00:00"))
# Layout says where covers went
w.go("layoutstd"); app.processEvents()
lay = w.layoutstd_page
check("Layout: covers, title pages and back covers are in Section designs", lay.moved_note.isVisibleTo(lay)
      and "Parts" in lay.moved_note.text()
      and not any(lay.cats.item(r).text().startswith(("Covers", "Title pages", "Back covers")) for r in range(lay.cats.count())))
if os.environ.get("SHOT_DIR"):
    w.go("crosswalk"); app.processEvents()
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "review_lm_view.png"))
w.close()
n = sum(checks)
print(f"QT REVIEW 390 PASS ({n}/{len(checks)})" if n == len(checks) else f"QT REVIEW 390 FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
