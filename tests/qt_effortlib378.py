"""3.78.0 the Effort Library, offscreen: the menu heading is Effort Library; a file that is not a customer document is
copied into <effort>\\Library\\<top folder>\\<folders> (pictures to Graphics), so what the app shows is on disk; New
folder... makes a real folder, shown in the tree even when empty; moving a document to another category or folder moves
its file on disk; the effort opens the same after its folder moves; files an older version kept in the app's working
folder move into the Library folders when asked, with a list of every move; Scan files... on the Acronyms page offers
to add the files to the library first; Scan the library... scans the ticked folders. Fictional content (Heron)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, docversions as DV, docintake as DI
import effortlib as EL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer Documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
IN = os.path.join(tmp, "intake"); os.makedirs(IN)
for n in ("Win themes.docx", "Radiator.png"):
    open(os.path.join(IN, n), "wb").write(n.encode() * 30)


def reader(p):
    return [{"x": f"Our flight-proven radiator lowers risk ({os.path.basename(p)}).", "l": "1", "s": "", "t": ""}]


app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
check("the menu heading is Effort Library", "Effort Library" in [g for g, _i in RAIL] and "Customer Documents" not in [g for g, _i in RAIL])
w.go("library"); app.processEvents()
pg = w.library_page
check("the Effort Library's bar: at most five, Add files... the main one", len(pg.bar.visible_commands()) <= 5
      and pg.bar.main.text() == "Add files..." and "New folder..." in pg.bar.labels(), pg.bar.labels())
lib = pg.lib
check("the library knows its effort's folder", os.path.normcase(lib.effort_root) == os.path.normcase(ED)
      and os.path.normcase(lib.library_root) == os.path.normcase(os.path.join(ED, "Library")))
plan = DI.plan(lib, [os.path.join(IN, "Win themes.docx"), os.path.join(IN, "Radiator.png")], reader=reader, category=None)
cats = {os.path.basename(e["path"]): e["category"] for e in plan}
check("a picture goes to Graphics", cats["Radiator.png"] == "graphics", cats)
for e in plan:
    if e["path"].endswith(".docx"):
        e["category"] = "ours"; e["folder"] = "Themes"
made = DI.apply(lib, plan, CD)
check("a file that is not a customer document is copied into Library\\<top>\\<folders>",
      os.path.isfile(os.path.join(ED, "Library", "Our Documents", "Themes", "Win themes.docx"))
      and os.path.isfile(os.path.join(ED, "Library", "Graphics", "Radiator.png")), [lib.path_of(v) for _d, v in made])
d_doc = next(d for d, _v in made if d["name"].startswith("Win"))
check("... kept relative to the effort's folder", d_doc["versions"][-1].get("erel") == "Library/Our Documents/Themes/Win themes.docx",
      d_doc["versions"][-1])
pg.refresh(); app.processEvents()
pg.cat, pg.folder = "graphics", ""
sub = pg.new_folder("Figures")
check("New folder... makes a real folder", sub == "Figures" and os.path.isdir(os.path.join(ED, "Library", "Graphics", "Figures")))
names = []
it = pg.tree.invisibleRootItem()
stack = [it]
while stack:
    x = stack.pop()
    for i in range(x.childCount()):
        names.append(x.child(i).text(0)); stack.append(x.child(i))
check("... and the tree shows it while it is empty", "Figures" in names, names)
pg.lib = DV.Library(w.ws.p("documents")).load()
lib = pg.lib
d_pic = next(d for d in lib.all if d["name"].startswith("Radiator"))
moves = EL.move_doc(lib, d_pic["id"], "graphics", "Figures")
check("moving a document to a folder moves its file on disk", moves and os.path.isfile(os.path.join(ED, "Library", "Graphics", "Figures", "Radiator.png"))
      and not os.path.isfile(os.path.join(ED, "Library", "Graphics", "Radiator.png")), moves)
lib2 = DV.Library(w.ws.p("documents")).load()
d2 = lib2.doc(d_pic["id"])
check("... and the library says where it is now", d2["folder"] == "Figures" and lib2.has_original(d2["versions"][-1]), d2)
# the effort folder moves: the files are found again
w.close()
ED2 = os.path.join(tmp, "Heron moved"); shutil.copytree(ED, ED2)
lib3 = DV.Library(os.path.join(W.data_dir_for(os.path.join(ED2, "Heron_Effort_List.xlsx")), "documents")).load()
v3 = lib3.doc(d_pic["id"])["versions"][-1]
check("after the effort's folder moves, its Library files are found where they are now",
      os.path.normcase(lib3.path_of(v3)).startswith(os.path.normcase(ED2)) and lib3.has_original(v3), lib3.path_of(v3))
# a file kept in the app's working folder (before 3.78.0) moves when asked
old_dir = os.path.join(lib3.data_dir, "library", "bidders"); os.makedirs(old_dir)
oldf = os.path.join(old_dir, "MIL-STD-1540E.pdf"); open(oldf, "wb").write(b"%PDF-1.4 fictional" * 10)
lib3.library_root = ""                                    # as an older version added it
d_old, v_old = lib3.add(oldf, [{"x": "Thermal vacuum cycling.", "l": "1", "s": "", "t": ""}], category="bidders", folder="Standards")
lib3.library_root = os.path.join(ED2, "Library")
pl = EL.plan_moves(lib3)
check("an older file kept in the working folder is listed to move", len(pl) == 1 and pl[0][2] == oldf, pl)
n, note = EL.do_moves(lib3, pl, os.path.join(ED2, "Heron_Effort_List.xlsx"))
check("... moved into Library\\Bidders Library\\Standards, with a list of the move in the effort's folder",
      n == 1 and os.path.isfile(os.path.join(ED2, "Library", "Bidders Library", "Standards", "MIL-STD-1540E.pdf"))
      and os.path.isfile(note) and "MIL-STD-1540E.pdf" in open(note, encoding="utf-8").read(), note)
# the Acronyms page: the bridge and Scan the library...
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron2", path=os.path.join(ED2, "Heron_Effort_List.xlsx"), customer_dir=os.path.join(ED2, "Customer Documents"))
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron2"); w.go("acronyms"); app.processEvents()
ap = w.acronym_page
from skqt import acrbridge as AB
src = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Interface_Diagram.svg")
pic = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Large_Diagram.png")
n = AB.add_first(ap, [pic], answer=True)
lib4 = DV.Library(w.ws.p("documents")).load()
check("Scan files... offers to add them to the Effort Library first: a picture goes to Graphics", n == 1
      and any(d["category"] == "graphics" and d["name"].startswith("Kestrel Large") for d in lib4.all)
      and os.path.isfile(os.path.join(ED2, "Library", "Graphics", "Kestrel_Large_Diagram.png")))
check("... and a file already there is not offered again", AB.add_first(ap, [pic], answer=True) == 0)
check("Scan the library...: Customer Documents and Graphics ticked at first", AB.FIRST == ("customer", "graphics")
      and AB.scan_library(ap, run=False) is None and ap._scan_lib_dialog is not None)
paths = AB.library_paths(lib4, {"graphics"})
check("... the ticked folders' files", any(p.endswith("Kestrel_Large_Diagram.png") for p in paths), paths)
check("the Acronyms page shows Scan the library... in an effort", ap.b_lib.isVisibleTo(ap) and not ap.b_folder.isVisibleTo(ap))
w.close()
n = sum(checks)
print(f"QT EFFORT LIBRARY 378 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
