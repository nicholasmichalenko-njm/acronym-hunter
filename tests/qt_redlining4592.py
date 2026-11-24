"""4.59.2 offscreen (decisions 189 and 226; Nicholas 2026-11-23 08:59, "Yes"): Redlining is a menu entry of its own,
below the steps, with no number. With no document marked it shows one line and one button, Choose a document..., and
none of its parts; picking a PDF marks it Redlined Deliverable, gives it its tile on Deliverables, lists it and shows
the parts. Redlining can be pinned in Quick tools. Fictional content (Kestrel)."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, workspace as W
import docreturn as DR, effortrec as RR
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, redlinechoose as RC, toolshome as TH
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
src = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
P = os.path.join(CD, "Kestrel_Section_L.pdf"); shutil.copy2(src, P)
lib0 = DV.Library(ws.p("documents")).load()
lib0.add(P, DI.read(P), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
dL = next(d["id"] for d in DV.Library(ws.p("documents")).load().all if d["name"] == "Section L")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()

rail = [t for _k, t in MW.RAIL[0][1]]
check("4.61.0: Redlining is an entry of its own, beside Deliverables", "redline" in w.step_btns and "deliverables" in w.step_btns
      and MW.RAIL_OF["redline"] == "redline")
check("... not indented under Documents any more", "redline" not in __import__("skqt.navrail", fromlist=["x"]).SUB)

w.go("redline"); app.processEvents()
pg = w.redline_page
check("with nothing marked: one line and one button, Choose a document...", pg.empty.isVisibleTo(w) and not pg.table.isVisibleTo(w)
      and "No document is marked Redlined Deliverable." in [l.text() for l in pg.empty.findChildren(__import__("PySide6.QtWidgets", fromlist=["x"]).QLabel)]
      and any(b.text() == "Choose a document..." for b in pg.empty.findChildren(__import__("PySide6.QtWidgets", fromlist=["x"]).QPushButton)))
check("... and not its other parts: only the list and the way in", w._tab_keys == ["redline"], w._tab_keys)
check("the page is Redlining, its menu entry lit (4.61.0)", w.page_title.text() == "Redlining" and w.step_btns["redline"].isChecked(),
      w.page_title.text())

rows = RC.candidates(w)
check("Choose a document... offers the effort's PDF", [r[0] for r in rows] == [dL], rows)
got = RC.choose(pg, pick="add")
check("Add a file goes to Documents", got is None and w.stack.currentWidget() is w.library_page)
w.go("redline"); app.processEvents()
got = RC.choose(pg, pick=dL); app.processEvents()
lib = DV.Library(ws.p("documents")).load()
check("picking it marks it Redlined Deliverable", got == dL and "redline" in lib.returns_of(lib.doc(dL)))
check("... gives it its tile on Deliverables", DR.tile_of(RR.Record(ws.root), dL) is not None)
check("... lists it in Redlining, with the parts shown", len(pg.rows) == 1 and pg.table.isVisibleTo(w) and not pg.empty.isVisibleTo(w)
      and w._tab_keys == ["redline", "rcheck", "exceptions"], w._tab_keys)
check("a marked document is not offered again", RC.candidates(w) == [])
check("picking something not offered does nothing", RC.choose(pg, pick="nope") is None)

check("Quick tools has Redline a document (4.60.0)", "redline" in TH.TOOLS and TH.TOOLS["redline"][0] == "Make a Word file from a PDF" and TH.TOOLS["redline"][2] == "file")
check("a file outside any effort is still prepared from Quick tools", any(k == "redline" for k, _t, _x in TH.USES))

print(f"REDLINING 4592 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
