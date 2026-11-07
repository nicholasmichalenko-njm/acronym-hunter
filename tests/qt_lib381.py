"""3.81.0 the Effort Library's place and older efforts, offscreen: when the team's folder plan keeps the effort list
deeper in the tree, the Library folder sits at the effort's top folder, beside Customer Documents; a file kept where it
was before is still found; an older effort that keeps files in the app's working folder shows one line on the Effort
Library, and moving them hides it. Fictional content (Heron)."""
import json, os, sys, tempfile
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
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
TOP = os.path.join(tmp, "Heron"); ADMIN = os.path.join(TOP, "05 Admin"); CD = os.path.join(TOP, "Customer Documents")
os.makedirs(ADMIN); os.makedirs(CD)
LIST = os.path.join(ADMIN, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
dd = W.data_dir_for(LIST); os.makedirs(dd, exist_ok=True)
json.dump({"root_up": 1}, open(os.path.join(dd, "settings.json"), "w"))
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
lib = DV.Library(os.path.join(dd, "documents")).load()
check("the Library sits at the effort's top folder, beside Customer Documents", os.path.normcase(lib.effort_root) == os.path.normcase(TOP)
      and os.path.normcase(lib.library_root) == os.path.normcase(os.path.join(TOP, "Library")), (lib.effort_root, lib.library_root))
IN = os.path.join(tmp, "intake"); os.makedirs(IN)
f1 = os.path.join(IN, "Win themes.docx"); open(f1, "wb").write(b"fictional win themes" * 20)
plan = DI.plan(lib, [f1], reader=lambda p: [{"x": "Our radiator lowers risk.", "l": "1", "s": "", "t": ""}], category=None)
for e in plan:
    e["category"] = "ours"; e["folder"] = ""
DI.apply(lib, plan, CD)
check("a new file goes into the top folder's Library", os.path.isfile(os.path.join(TOP, "Library", "Our Documents", "Win themes.docx")))
# a file a 3.78.0 Library kept beside the list: found where it was last seen
old = os.path.join(ADMIN, "Library", "Graphics"); os.makedirs(old)
pic = os.path.join(old, "Radiator.png"); open(pic, "wb").write(b"fictional png" * 20)
v = {"path": pic, "erel": "Library/Graphics/Radiator.png"}
check("a file kept where 3.78.0 put it is still found", os.path.normcase(lib.path_of(v)) == os.path.normcase(pic), lib.path_of(v))
# an older effort's kept file: one line on the Effort Library
kd = os.path.join(dd, "library", "bidders"); os.makedirs(kd)
kf = os.path.join(kd, "MIL-STD-1540E.pdf"); open(kf, "wb").write(b"%PDF-1.4 fictional" * 10)
lib.library_root = ""
lib.add(kf, [{"x": "Thermal vacuum cycling.", "l": "1", "s": "", "t": ""}], category="bidders", folder="Standards")
lib.save()
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron"); w.go("library"); app.processEvents()
pg = w.library_page
check("an older effort's kept files: one line on the Effort Library", pg.kept_box.isVisibleTo(pg) and pg.kept_lbl.text().startswith("1 file(s)"),
      pg.kept_lbl.text())
n = pg.move_into_folders(ok=True)
check("... Move them moves them into the Library folders and the line goes", n == 1 and not pg.kept_box.isVisibleTo(pg)
      and os.path.isfile(os.path.join(TOP, "Library", "Bidders Library", "Standards", "MIL-STD-1540E.pdf")))
check("... with the list of moves in the effort's top folder", any(x.startswith("Library moves") for x in os.listdir(TOP)), os.listdir(TOP))
w.close()
n = sum(checks)
print(f"QT LIBRARY 381 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
