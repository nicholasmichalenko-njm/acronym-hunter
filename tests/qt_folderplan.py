"""2.95.0 Settings > Folders and file names, offscreen: the tree with jobs (one folder per job), subfolders, folder and
name per output with a live sample, options (dates, spaces, company, where the effort list sits); a new effort gets
the tree and its list in the chosen folder; saves start in the right folder under the right name; Make the folders in
this effort adds what is missing; a team pack carries it."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import folderplan as FP, effortfolders as EF, teampack as TP, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
fc = w.settings_page.folders_card
check("Settings: Folders and file names with the built-in tree", [fc._path(i) for i in fc._items()] == ["Customer Documents", "Volumes", "Response Setup", "Exports"])
check("every output listed with a sample", fc.places.rowCount() == len(FP.OUTPUTS)
      and any(fc.places.item(i, 3).text() == "Exports/Kestrel_Compliance_Matrix_2026-11-03.xlsx" for i in range(fc.places.rowCount())),
      [fc.places.item(i, 3).text() for i in range(4)])
# build the team's tree
items = fc._items()
items[0].setText(0, "01 Customer Documents")
fc.tree.setCurrentItem(items[0]); amd = fc.add_folder("Amendments", sub=True)
items[1].setText(0, "05 Volumes"); items[3].setText(0, "07 Deliverables")
fc.tree.setCurrentItem(items[3]); rep = fc.add_folder("Reports", sub=True)
fc.tree.setCurrentItem(items[3]); sk = fc.add_folder("99 Stationkeeper")
check("subfolders and folders added", "01 Customer Documents/Amendments" in [t["path"] for t in fc.tree_rows()]
      and "07 Deliverables/Reports" in [t["path"] for t in fc.tree_rows()])
fc.tree.itemWidget(rep, 1).setCurrentIndex(fc.tree.itemWidget(rep, 1).findData("exports"))
check("a job belongs to one folder: giving it to Reports takes it off 07 Deliverables",
      fc.tree.itemWidget(items[3], 1).currentData() == "" and fc.tree.itemWidget(rep, 1).currentData() == "exports")
fc.tree.setCurrentItem(rep)
check("a folder with a job cannot be removed", not fc.remove())
fc.tree.itemWidget(items[3], 1).setCurrentIndex(fc.tree.itemWidget(items[3], 1).findData("exports"))
row = next(i for i in range(fc.places.rowCount()) if fc.places.item(i, 0).data(0x0100) == "effort_status")
fc.places.cellWidget(row, 1).setCurrentIndex(fc.places.cellWidget(row, 1).findData("07 Deliverables/Reports"))
fc.places.item(row, 2).setText("{Client} {Effort} Status {Date}")
fc.company.setText("Acme Space"); fc.space.setCurrentIndex(fc.space.findData("-"))
fc.home.setCurrentIndex(fc.home.findData("99 Stationkeeper"))
fc.refresh_samples()
check("the sample follows the folder and the name", fc.places.item(row, 3).text() == "07 Deliverables/Reports/USSF-SSC-Kestrel-Status-2026-11-03.docx",
      fc.places.item(row, 3).text())
check("Save", fc.save())
if os.environ.get("SHOT_DIR"):
    w.go("settings"); w.settings_page.jump(fc); app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "fp_tree.png"))
    fc.tabs.setCurrentIndex(1); app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "fp_places.png")); fc.tabs.setCurrentIndex(0)
P = FP.load(cfg)
check("... kept", P["home"] == "99 Stationkeeper" and P["places"]["effort_status"] == "07 Deliverables/Reports" and P["company"] == "Acme Space"
      and next(t for t in P["tree"] if t["role"] == "customer")["path"] == "01 Customer Documents")
# a new effort under the plan
import datahome
base = datahome.efforts_dir(A.DATA_DIR) if hasattr(A, "DATA_DIR") else os.path.join(tmp, "Efforts")
path, up = EF.new_list_path(os.path.join(tmp, "Efforts"), "Kestrel", {"Client": "USSF SSC"})
w.settings_page.new_effort({"name": "Kestrel", "path": path, "client": "USSF SSC", "solicitation": "FA8810-26-R-0042"})
root = EF.root(w.effort_path)
check("a new effort: its list in 99 Stationkeeper, the root above it", os.path.basename(os.path.dirname(w.effort_path)) == "99 Stationkeeper"
      and root == os.path.join(tmp, "Efforts", "Kestrel"), (w.effort_path, root))
check("... the whole tree made", all(os.path.isdir(os.path.join(root, *p.split("/"))) for p in ("01 Customer Documents/Amendments", "05 Volumes",
                                                                                            "07 Deliverables/Reports")))
check("... Customer Documents is the effort's customer folder", (w.efforts.get("Kestrel") or {}).get("customer_dir") == os.path.join(root, "01 Customer Documents"))
st = w.out_path("effort_status")
check("a save starts in its folder under its name", st.startswith(os.path.join(root, "07 Deliverables", "Reports"))
      and os.path.basename(st).startswith("USSF-SSC-Kestrel-Status-"), st)
check("an output with no rule goes to the exports folder by the built-in name", w.out_path("keywords") == os.path.join(root, "07 Deliverables", "Kestrel_Keywords.xlsx"),
      w.out_path("keywords"))
import shutil
shutil.rmtree(os.path.join(root, "05 Volumes"))
made = fc.make_here()
check("Make the folders in this effort puts back what is missing", os.path.isdir(os.path.join(root, "05 Volumes")))
import readable as RD
check("the readable copy sits in the effort's root", os.path.dirname(RD.folder_for(w.effort_path, "Kestrel")) == root)
# team pack
pk = os.path.join(tmp, "team.zip")
TP.make(cfg, pk, ["folders"], lock=["folders"], name="Proposal Center")
cfgB = os.path.join(tmp, "pcB"); os.makedirs(cfgB)
info, data = TP.read(pk)
TP.install(cfgB, info, data)
check("a team pack carries the folders and file names, locked", FP.load(cfgB)["home"] == "99 Stationkeeper" and TP.locked(cfgB, "folders"))
FP.apply(cfg)
fc.reset(answer=True)
check("Put back the built-in ones (not saved until Save)", [fc._path(i) for i in fc._items()] == ["Customer Documents", "Volumes", "Response Setup", "Exports"]
      and FP.load(cfg)["home"] == "99 Stationkeeper")
n = sum(checks)
print(f"QT FOLDER PLAN {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
