"""4.18.0 offscreen: in Shred, drag over words of a piece and right-click: Compliance language: just here, everywhere,
or Not compliance language here. The piece keeps its decision; the piece pane shows the words in the compliance style;
everywhere adds them to the compliance words list; Undo takes a mark back. Fictional (Kestrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import cwords as CW, docintake as DI, docversions as DV, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
src = os.path.join(tmp, "Section L.pdf"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "docs4170", "C01v1.pdf"), src)
lib = DV.Library(w.ws.p("documents")).load()
DI.apply(lib, DI.plan(lib, [src]), customer_dir=CD)
w.read_page.read([os.path.join(CD, "Section L.pdf")], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while (w.review is None or w.read_page.running()) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pg = w.assign_page
w.go("assign"); pg.load_files_keep(); pg.open_file("Section L.pdf"); app.processEvents()
it = next(x for x in M.items if "submit two copies" in (x.get("text") or ""))
it["decision"] = "Keep"
pg.select(it["id"]); app.processEvents()
import re
ws_ = [m.group(0) for m in re.finditer(r"\S+", it["text"])]
a = ws_.index("two")
pg.show_grab(it["id"], a, a + 1); app.processEvents()
check("the dragged words are picked", pg.grab and pg.grab["text"].startswith("two copies"), pg.grab)
m = pg.sentence_menu(it["id"])
acts = {x.text(): x for x in m.actions()}
check("the right-click offers Compliance language: just here, everywhere, and Not compliance language here",
      "Compliance language: just here" in acts and "Compliance language: everywhere (add it to the compliance words list)" in acts
      and "Not compliance language here" in acts, list(acts))
acts["Compliance language: just here"].trigger(); app.processEvents()
check("just here: the words are marked on the piece, its decision kept", (it.get("cl") or {}).get("add") == ["two copies"]
      and it["decision"] == "Keep", it.get("cl"))
from skqt import complmark as CLM
check("the piece pane shows them in the compliance style", "two copies</span>" in CLM.card_html(it, cfg))
pg.do_undo(); app.processEvents()
it = next(x for x in M.items if "submit two copies" in (x.get("text") or ""))
check("Undo takes the mark back", not it.get("cl"))
pg.select(it["id"]); pg.show_grab(it["id"], a, a + 1); app.processEvents()
m = pg.sentence_menu(it["id"])
next(x for x in m.actions() if x.text().startswith("Compliance language: everywhere")).trigger(); app.processEvents()
check("everywhere: the compliance words list has them", "two copies" in CW.load(cfg)["words"], CW.load(cfg)["words"][-3:])
k = sum(checks)
print(f"QT COMPLMARK 4180 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
w.close(); app.quit()
sys.exit(0 if k == len(checks) else 1)
