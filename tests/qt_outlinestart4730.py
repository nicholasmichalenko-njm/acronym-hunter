"""4.73.0: our response structure is decided on the Outline page. With no outline it asks one question with three
answers: The customer tells us (opens the customer's document beside the outline, to mark), We build it (a reason, and
a start), Start from a saved outline. The answer can be changed and deletes nothing. Fictional (Kestrel)."""
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
import setupdoc as SDZ, structmark as SM
from skqt import outlinepage as OP
op = w.outline_page
St = SDZ.setup_of(M)
M.outline[:] = []; St.pop("outline_from", None); St.pop("outline_auto", None)
w.go("outline"); app.processEvents()
check("Outline has two tabs: Outline, From the customer's document", w._tab_keys == ["outline", "structpass"] and w.page_title.text() == "Outline", w._tab_keys)
check("with no outline the page asks the one question", op.start.isVisibleTo(op) and op.start.title.text() == OP.QUESTION if hasattr(op.start, "title")
      else op.start.isVisibleTo(op))
check("... with three answers and nothing else to press", [b.text() for b in (op.b_pres, op.b_ours, op.b_file)] ==
      ["The customer tells us", "We build it", "Start from a saved outline..."] and all(b.isVisibleTo(op) for b in (op.b_pres, op.b_ours, op.b_file))
      and not op.bar.isVisibleTo(op) and not op.build.isVisibleTo(op))
op.b_ours.click(); app.processEvents()
check("We build it: the answer, a reason and today's date are kept", St.get("outline_from") == "ours" and St.get("outline_reason") == "No structure given"
      and St.get("outline_reason_on") == __import__("datetime").date.today().isoformat())
check("... the question gives way to Why and three starts", not op.start.isVisibleTo(op) and op.build.isVisibleTo(op)
      and [b.text() for b in (op.b_factors, op.b_heads, op.b_blank)] == ["Mirror the evaluation factors", "Mirror the customer's headings", "Type it"]
      and [op.reason.itemText(i) for i in range(op.reason.count())] == list(OP.REASONS))
op.reason.setCurrentIndex(2); op.reason.activated.emit(2); app.processEvents()
check("the reason can be changed", St.get("outline_reason") == "A page limit only" and "a page limit only" in op.said.text(), op.said.text())
check("... Change the answer is there, and the bar of outline tools is not (nothing to use it on)", op.back.isVisibleTo(op) and not op.bar.isVisibleTo(op))
op.b_heads.click(); app.processEvents()
check("Mirror the customer's headings gives sections to edit", (op.builder().isVisibleTo(op) or bool(M.outline)) and not op.build.isVisibleTo(op) or bool(M.outline))
op.builder().show_text(False); M.outline[:] = []
op.ask(force=True); app.processEvents()
check("More > Change how the outline starts... asks again", op.start.isVisibleTo(op) and "outline_from" not in St
      and "Change how the outline starts..." in [a.text() for a in op.bar.more_menu.actions()])
op.b_pres.click(); app.processEvents()
pg = w.assign_page
check("The customer tells us: the customer's document opens beside the outline, in the marking", St.get("outline_from") == "prescribed"
      and w.stack.currentWidget() is pg and pg.focus == "struct" and pg.struct_panel.isVisibleTo(pg) and w.step_btns["outline"].isChecked()
      and w.page_title.text() == "Outline", (pg.focus, w.page_title.text()))
w.go("outline"); app.processEvents()
check("back on the Outline tab with nothing marked: one sentence and one way in", op.wait.isVisibleTo(op) and not op.builder().isVisibleTo(op)
      and not op.bar.isVisibleTo(op) and op.back.isVisibleTo(op) and not op.start.isVisibleTo(op))
w.go("structpass"); app.processEvents()
rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]
rows[0]["text"] = "Volume I Technical"; rows[0]["lead"] = ""
pg.select(rows[0]["id"]); app.processEvents()
from skqt import structpass as SP
SP.press(pg, "volume"); app.processEvents()
w.go("outline"); app.processEvents()
check("a mark made there is on the Outline tab: the builder shows, the question does not", [C.outline_label(o) for o in M.outline] == ["Volume I Technical"]
      and not op.start.isVisibleTo(op) and op.builder().isVisibleTo(op) and op.bar.isVisibleTo(op), [C.outline_label(o) for o in M.outline])
check("... the page says how the structure is decided", op.said.text().startswith("The customer tells us"), op.said.text())
check("... the heading is not marked the customer's wholesale: it keeps the piece that required it", M.outline[0].get("req") == rows[0]["id"] and St.get("prescribed_marked") is True)
op.ask(force=True); app.processEvents()
check("changing the answer deletes nothing", [C.outline_label(o) for o in M.outline] == ["Volume I Technical"] and M.outline[0].get("req") == rows[0]["id"])
op.answer("ours"); app.processEvents()
check("... a marked heading keeps Required by under We build it", St.get("outline_from") == "ours" and M.outline[0].get("req") == rows[0]["id"])
w.go("comppass"); app.processEvents()
check("Shred is about the customer's documents: Compliance first, no Response Structure", w.page_title.text() == "Shred" and pg.focus == "comp"
      and [k for k, _t in MW.TABS["assign"]][0] == "comppass")
w.close()
print(f"QT OUTLINE START 4730 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
