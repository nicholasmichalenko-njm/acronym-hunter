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
      list(rows)[:2] == ["Text check", "Shred"] and "Used for" in rows and "Versions" not in rows, list(rows))
check("... not extracted yet; it feeds the matrix", rows["Shred"][1] == "Not extracted yet"
      and rows["Used for"][1] == "For the shred", rows)
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
check("4.25.2: a document that is not for the shred says Reference", rows["Used for"][1] == "Reference", rows["Used for"])
m = DS.row_menu(lp, run=False)
acts = [a.text() for a in m.actions() if a.text()]
check("the right-click menu: the things about the file, then what left the panel (4.6.0), then Delete... (4.17.0)", acts[:6] == ["Open", "Used for", "Source",
      "Add a newer version...", "Replace the file...", "Show in folder"] and [a for a in acts[6:] if a != "Prepare for redline"]
      == ["Initial and type...", "More about this document...", "Delete..."], acts)   # 4.8.0: Prepare a redline copy for a PDF
check("4.25.2: Used for holds the four marks; Source holds Customer and Internal", [a.text() for a in m.actions()[1].menu().actions() if a.text()]
      == ["For the shred", "Reference", "Return it, redlined", "Return it, filled in"]
      and [a.text() for a in m.actions()[2].menu().actions()] == ["Customer", "Internal"]
      and [a.text() for a in m.actions()[1].menu().actions() if a.isChecked()] == ["Reference"])
check("... Open and Show in folder find the file", os.path.isfile(DS.open_file(lp, lp.lib.doc(dS["id"])))
      and os.path.isdir(DS.show_in_folder(lp, lp.lib.doc(dS["id"]))))
from skqt import usedfor as UF
UF.toggle(lp, "reference"); app.processEvents()
check("4.25.2: unticking its only mark leaves it with no mark: left out of the shred", lp.lib.role_of(lp.lib.doc(dS["id"])) == "not_needed"
      and lp.lib.marks_of(lp.lib.doc(dS["id"])) == [])
lp.select(dS["id"]); lp.show_doc()
rows = {r[0]: r for r in lp.status_now}
check("... the panel says Left out, and offers nothing to do", rows["Shred"][1] == "Left out" and not lp.b_read.isVisibleTo(w), (rows, lp.b_read.text()))
UF.toggle(lp, "reference"); UF.toggle(lp, "redline"); app.processEvents()
check("4.25.2: ticking Reference brings it back; a document may carry several marks", lp.lib.role_of(lp.lib.doc(dS["id"])) == "reference"
      and lp.lib.marks_of(lp.lib.doc(dS["id"])) == ["Reference", "Return it, redlined"] and lp.lib.returns_of(lp.lib.doc(dS["id"])) == ["redline"])
from skqt import docfocus as DF4252
from PySide6.QtCore import Qt
row = next(r for r in range(lp.table.rowCount()) if lp.table.item(r, 0).data(Qt.UserRole) == dS["id"])
def _only(key):
    lp.type_f.setCurrentIndex(lp.type_f.findData(key)); app.processEvents()
    return [lp.table.item(r, 4).text() for r in range(lp.table.rowCount())]
check("... the list's Used for column says so, and the filter shows what is returned, or what is for the shred", lp.table.item(row, 4).text() == "Reference, Return it, redlined"
      and _only("use:returned") == ["Reference, Return it, redlined"] and _only("use:shred") and all("For the shred" in t for t in _only("use:shred"))
      and len(_only("")) == len(lp.lib.all) and DF4252.COLUMNS[4] == "Used for")
UF.toggle(lp, "redline"); lp.select(dS["id"])
check("... Source: Internal and back to Customer changes whose it is; no file moves", UF.set_source(lp, "ours") == 1
      and lp.lib.doc(dS["id"])["category"] == "ours" and os.path.isfile(lp.lib.path_of(lp.lib.doc(dS["id"])["versions"][-1]))
      and (lp.select(dS["id"]) or True) and UF.set_source(lp, "customer") == 1 and lp.lib.doc(dS["id"])["category"] in ("customer", "bidders"))
more = [a.text() for a in lp.doc_menu(run=False).actions() if a.text()]
check("4.25.2: More about this document: tags and its name (Used for and Source are on the row; folders took the place of categories)", more[:1] == ["Tags..."]
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
check("... which opens Documents > Amendments", w.stack.currentWidget() is w.compare_space and w.step_btns["library"].isChecked(), (w.stack.currentWidget(), lp.lib.doc(dL["id"])["versions"][-1]))
w.close()
print(f"QT DOCS 400 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
