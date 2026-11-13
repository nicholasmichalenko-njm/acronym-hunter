"""4.25.1 in Qt, offscreen (Nicholas 2026-11-12 16:49, 17:08; answers 8 and 9): Documents names the effort's folder and
opens it; a file put into the effort's folder is added by itself when the folders are checked, as one of our own
documents for reference, where it sits, and a line says what came in; a file tried once and not added is offered in the
strip, not tried again; a pasted picture is saved with the effort's graphics; a delete goes to the Deleted folder.
Fictional content."""
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
A.LOG_DIR = os.path.join(tmp, "logs")
import docversions as DV, doctrash as T, effortfolders as EF
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QImage
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import docfocus as DF, watchauto as WAU, acrextras as AX
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def wait(cond, secs=60):
    t = time.time()
    while time.time() - t < secs and not cond():
        app.processEvents(); time.sleep(0.02)
    return cond()


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
LIST = os.path.join(tmp, "Efforts", "Heron", "Heron_Effort_List.xlsx")
w.settings_page.new_effort({"name": "Heron", "path": LIST, "first_use": "volume"}); app.processEvents()
root = EF.root(w.effort_path)
w.go("library"); lp = w.library_page; lp.refresh(); app.processEvents()
check("Documents names the effort's folder, and the path opens it", root in lp.folder_lbl.text() and lp.folder_lbl.isVisibleTo(w)
      and "<a href" in lp.folder_lbl.text() and w.open_effort_folder() == root, lp.folder_lbl.text())
wh = WAU.where(w)
check("what is left out of the effort's folder: our volumes, Response Setup, Exports, Redlines, Deleted, the files beside the list",
      wh["effort_root"] == root and {os.path.basename(s) for s in wh["skip"]} >= {"01_proposal", "10_proposal management", "Exports", "Redlines", "Deleted"}
      and root in wh["not_in"], wh)
a = put(os.path.join(root, "06_cost and pricing", "Kestrel rates.txt"), "Labor rates for the Kestrel ground station are listed by year.")
b = put(os.path.join(root, "03_briefings and approvals", "Gate", "Kestrel gate brief.txt"), "The gate review approved the Kestrel bid.")
put(os.path.join(root, "01_proposal", "Volume I.txt"), "Our draft is not a document to add.")
found = w.watch_now()
check("a file put into the effort's folder is added by itself: a line says what came in", "2 file(s) came into the effort's folder" in w.last_came_in
      and "Kestrel rates.txt" in w.last_came_in and wait(lambda: not lp.running()), w.last_came_in)
lib = DV.Library(w.ws.p("documents")).load()
names = sorted(d["name"] for d in lib.all)
da = next((d for d in lib.all if d["name"].startswith("Kestrel rates")), None)
check("... as one of our own documents, for reference, where it sits", len(lib.all) == 2 and da is not None and da["category"] == "ours"
      and lib.role_of(da) == "reference" and os.path.normcase(w.library_page.lib.path_of(da["versions"][-1])) == os.path.normcase(a)
      and not os.path.isdir(os.path.join(root, "Library", "Our Documents")), names)
check("... with the folder it is in", da is not None and da["folder"] == "06_cost and pricing"
      and next(d for d in lib.all if d["name"].startswith("Kestrel gate"))["folder"] == "03_briefings and approvals/Gate")
check("... shown under Internal, tinted, with no status", DF.set_side(lp, "ours") == "ours" and lp.table.rowCount() == 2
      and lp.table.item(0, 2).text() == "Internal" and lp.table.item(0, 4).text() == "")
DF.set_side(lp, "all")
f2 = w.watch_now()
check("checked again: nothing more comes in, nothing offered", not f2["auto"] and not f2["new"] and len(DV.Library(w.ws.p("documents")).load().all) == 2, f2)
c = put(os.path.join(root, "09_contracts", "Kestrel terms.txt"), "Terms.")
w._wa_tried.add(os.path.normcase(c))
f3 = w.watch_now()
check("a file tried once and not added is offered in the strip, not tried again", [p for p, _c in f3["new"]] == [c] and w.watch_strip.isVisibleTo(w), f3)
img = QImage(40, 30, QImage.Format_RGB32); img.fill(0xFFFFFF)
got = AX.clipboard_pictures(w.acronym_page, image=img)
check("a pasted picture is saved in the effort's folder, with its graphics", got and os.path.dirname(got[0]) == os.path.join(root, "Library", "Graphics", "Pasted pictures")
      and os.path.isfile(got[0]), got)
from skqt import docmanage as DM
lp.refresh(); lp.select(da["id"]); app.processEvents()
DM.delete(lp, lp.lib.doc(da["id"]), answer=True) if "answer" in DM.delete.__code__.co_varnames else DM.delete(lp, lp.lib.doc(da["id"]))
check("a delete goes to the effort's Deleted folder, which a person can see; the file leaves its folder", os.path.isdir(os.path.join(root, "Deleted"))
      and len(T.entries(w.ws)) == 1 and not os.path.exists(a), os.listdir(root))
f4 = w.watch_now()
check("... and the watch does not bring it back from there", not any("Deleted" in p for p, _c in f4["auto"] + f4["new"]))
w.close()
n = sum(checks)
print(f"QT EFFORT FOLDER 4251 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
