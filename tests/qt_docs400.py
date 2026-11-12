"""4.0.0 offscreen: Documents (canvas "Six Steps", board 1; claude/stationkeeper-six-steps-plan-4.0.md). Click a document:
the status panel says what has been done to it (text check, shred, changes from its last version, feeds the matrix,
versions) and its one next thing; the right-click menu holds five things about the file (Open, Set type, Add a newer
version, Leave out, Show in folder); the rest is under More. Fictional (the rfp_walk set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import docintake as DI
import docversions as DV
import effort as E
import workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import docstatus as DS
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
B = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")
lib0 = DV.Library(ws.p("documents")).load()
pL = os.path.join(B, "Section_L_print.pdf")
dL, _v = lib0.add(pL, DI.read(pL), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
pS = os.path.join(B, "SOW.pdf")
dS, _v = lib0.add(pS, DI.read(pS), doc_name="SOW", role="context", initial="S", dtype="SOW")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.rail_go("library"); app.processEvents()
lp = w.library_page
lp.refresh(); lp.select(dL["id"]); lp.show_doc(); app.processEvents()
check("Documents is step 1: its page and title", w.stack.currentWidget() is lp and w.page_title.text() == "Documents")
rows = {r[0]: r for r in lp.status_now}
check("the status panel: text check, shred, feeds the matrix (4.6.0: the versions are listed once, below)",
      list(rows)[:2] == ["Text check", "Shred"] and "Feeds the matrix" in rows and "Versions" not in rows, list(rows))
check("... not extracted yet; it feeds the matrix", rows["Shred"][1] == "Not extracted yet"
      and rows["Feeds the matrix"][1].startswith("Yes"), rows)
check("... one button: its next thing (4.1.0: Shred it)", lp.b_read.isVisibleTo(w) and lp.b_read.text() == "Shred it", lp.b_read.text())
check("... no question: the button extracts it at once and opens Shred (4.1.0)",
      bool(lp.review_selected()) and w.stack.currentWidget() is w.assign_page and w.step_btns["assign"].isChecked())
t0 = time.time()
while (w.read_page.running() or w.assign_page.file != "Section_L_print.pdf") and time.time() - t0 < 90:
    app.processEvents(); time.sleep(0.02)
check("... and it opens there when done", w.assign_page.file == "Section_L_print.pdf", w.assign_page.file)
w.rail_go("library"); app.processEvents()
lp.select(dS["id"]); lp.show_doc()
rows = {r[0]: r for r in lp.status_now}
check("a document that does not feed the matrix says No", rows["Feeds the matrix"][1] == "No")
m = DS.row_menu(lp, run=False)
acts = [a.text() for a in m.actions() if a.text()]
check("the right-click menu: the things about the file, then what left the panel (4.6.0), then Delete... (4.17.0)", acts[:6] == ["Open", "Set type",
      "Add a newer version...", "Replace the file...", "Leave out", "Show in folder"] and [a for a in acts[6:] if a != "Prepare a redline copy"]
      == ["Initial and type...", "More about this document...", "Delete..."], acts)   # 4.8.0: Prepare a redline copy for a PDF
check("... Set type holds the categories and Initial and type", "Initial and type..." in [a.text() for a in m.actions()[1].menu().actions()])
check("... Open and Show in folder find the file", os.path.isfile(DS.open_file(lp, lp.lib.doc(dS["id"])))
      and os.path.isdir(DS.show_in_folder(lp, lp.lib.doc(dS["id"]))))
next(a for a in m.actions() if a.text() == "Leave out").trigger(); app.processEvents()
check("Leave out: it is left out of the shred", lp.lib.role_of(lp.lib.doc(dS["id"])) == "not_needed")
lp.select(dS["id"]); lp.show_doc()
rows = {r[0]: r for r in lp.status_now}
check("... the panel says Left out, and offers nothing to do", rows["Shred"][1] == "Left out" and not lp.b_read.isVisibleTo(w), (rows, lp.b_read.text()))
m = DS.row_menu(lp, run=False)
check("... the menu offers Put it back", "Put it back" in [a.text() for a in m.actions()])
next(a for a in m.actions() if a.text() == "Put it back").trigger(); app.processEvents()
check("Put it back: back in, as context", lp.lib.role_of(lp.lib.doc(dS["id"])) == "context")
more = [a.text() for a in lp.doc_menu(run=False).actions() if a.text()]
check("More about this document: role, category, folder, tags, its name", more[:4] == ["Role", "Category", "Folder...", "Tags..."]
      and "Rename..." in more and not lp.b_more.isVisibleTo(w), more)
# a second version: changes from its last version
lib1 = DV.Library(ws.p("documents")).load()
pL2 = os.path.join(B, "Section_L.docx")
lib1.add(pL2, DI.read(pL2), doc_id=dL["id"], label="Amendment 1")
lp.refresh(); lp.select(dL["id"]); lp.show_doc()
rows = {r[0]: r for r in lp.status_now}
check("a second version: changes from its last version not reviewed yet", rows.get("Changes from its last version", ("", ""))[1]
      == "Not reviewed yet" and lp.d_versions.count() == 2, rows)
check("... its next thing: Review changes", lp.b_read.text().startswith("Review changes"), lp.b_read.text())
lp.review_selected(); app.processEvents()
check("... which opens Documents > Changes", w.stack.currentWidget() is w.compare_space and w.step_btns["library"].isChecked(), (w.stack.currentWidget(), lp.lib.doc(dL["id"])["versions"][-1]))
w.close()
print(f"QT DOCS 400 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
