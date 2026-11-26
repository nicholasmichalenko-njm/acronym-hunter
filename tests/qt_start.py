"""4.79.0 (E2): the window asks Effort name and Saved in only, never guesses the folder and refuses the Effort Backup
folder; effort type and response type are on Effort Settings, kept as picked; Files and sources has Template and
Acronym sources. From 3.0.3: starting an effort, offscreen: with no effort open, Effort Home is the Start an effort form; a name alone makes
a working effort (its folders made in the team's layout, opened on Effort Home); the picture (chosen or dropped), the
client, solicitation, due date with its time zone and the proposal manager land where Effort Home shows them; the
effort picture on Effort Home also takes a dropped file; + Add an Effort with an effort open uses the same form."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, branding as BR
from PIL import Image
from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QFormLayout, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import starteffort as SE

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
patch = os.path.join(tmp, "patch.png"); Image.new("RGB", (800, 800), (15, 30, 70)).save(patch)
patch2 = os.path.join(tmp, "patch2.jpg"); Image.new("RGB", (600, 600), (160, 40, 40)).save(patch2)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def drop(widget, path):
    md = QMimeData(); md.setUrls([QUrl.fromLocalFile(path)])
    ev = QDropEvent(QPointF(10, 10), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    widget.dropEvent(ev)
    app.processEvents()


w.go("home"); app.processEvents()
hp = w.home_page; f = hp.start
check("no effort open: Effort Home is the Start an effort form", f.isVisibleTo(w) and not hp.scroll.isVisibleTo(w))
check("... Create effort waits for a name", not f.create_btn.isEnabled())
f.name.setText("Kestrel Thermal"); app.processEvents()
check("4.79.0: a name alone is not enough; Saved in is never guessed", not f.create_btn.isEnabled() and f.saved.folder() == ""
      and f.path() == "", (f.saved.folder(), f.path()))
fields = sorted(f.findChild(QFormLayout).itemAt(i, QFormLayout.LabelRole).widget().text() for i in range(f.findChild(QFormLayout).rowCount()))
check("4.79.0: the window asks two things, Effort name and Saved in", fields == ["Effort name", "Saved in"], fields)
check("... with one button that does the job, Create effort", f.create_btn.text() == "Create effort"
      and not [b for b in f.findChildren(QPushButton) if b.text() in ("More options", "Effort types...")])
where = os.path.join(tmp, "My efforts"); os.makedirs(where)
f.saved.choose(where); app.processEvents()
check("a folder chosen: Create effort is ready and the line says where the effort's own folder goes", f.create_btn.isEnabled()
      and f.path().endswith(".xlsx") and os.path.normcase(f.path()).startswith(os.path.normcase(where)) and "Kestrel" in f.path()
      and where in f.where.text(), (f.path(), f.where.text()))
bk = os.path.join(tmp, "Backups"); os.makedirs(os.path.join(bk, "inner"))
w.safety.backup_dir = lambda: bk
f.saved.choose(os.path.join(bk, "inner")); app.processEvents()
check("4.79.0 (185): the Effort Backup folder, or a folder in it, cannot be picked", not f.create_btn.isEnabled()
      and "Effort Backup" in f.where.text() and f.create() is None and "Effort Backup" in f.err.text(), f.where.text())
f.saved.choose(os.path.join(tmp, "not there")); app.processEvents()
check("... nor a folder that is not there", not f.create_btn.isEnabled() and "not there" in f.where.text())
f.saved.choose(where); app.processEvents()
name = f.create()
app.processEvents()
check("Create effort makes it and opens it on the Overview", name == "Kestrel Thermal" and w.effort_name == "Kestrel Thermal"
      and w.stack.currentWidget() is w.overview_page)       # 4.61.0: a new effort opens on the Overview
w.go("home"); app.processEvents()
check("... and the cards page shows the effort, not the form", hp.scroll.isVisibleTo(w) and not hp.start_wrap.isVisibleTo(w))
root = w.ws.root
rec = RR.Record(root)
import datum as DT
from skqt import datummark as DM
lab = DM.started_label(w)
check("the effort remembers the Production Datum it was started on, and its details say so (4.47.1)",
      w.ws.get(DT.STARTED_KEY, None) == 0 and DT.started(w.ws) == "Started with no Production Datum installed" and lab.text() == DT.started(w.ws) and not lab.isHidden(),
      (w.ws.get(DT.STARTED_KEY, None), lab.text()))
check("Make the setup's readiness list names what this PC works from, and never blocks on it", DM.ready_row(w) == (True, "Production Datum: none installed", 0), DM.ready_row(w))
reg = w.efforts.get("Kestrel Thermal")
check("... its own folders, made in the folder chosen", os.path.isdir(reg.get("customer_dir", "")) and os.path.isdir(reg.get("volumes_dir", ""))
      and os.path.normcase(reg.get("customer_dir", "")).startswith(os.path.normcase(where)), reg.get("customer_dir"))
check("... everything else at its default: no type, no due date, no customer", not (w.ws.get("prod_std", {}) or {}).get("effort_type")
      and not rec.data.get("due") and not reg.get("client") and not reg.get("solicitation"))
check("... and Effort Home shows it", "Kestrel Thermal" in hp.banner.name.text())
check("the form is empty again for the next one, Saved in too", f.name.text() == "" and f.saved.folder() == "")
drop(hp.banner.pic, patch2)
check("the effort picture on Effort Home takes a dropped picture", Image.open(BR.picture_path(root)).convert("RGB").getpixel((5, 5))[0] > 120)
# + Add an Effort with an effort open: the same form, in a window
dlg = SE.StartDialog(w)
dlg.form.name.setText("Osprey"); dlg.form.saved.choose(where)
made = dlg.form.create()
app.processEvents()
check("+ Add an Effort with one open: the same form in a window; a name and a folder", made == "Osprey" and dlg.made == "Osprey"
      and w.effort_name == "Osprey" and "Osprey" in w.efforts.names())
bad = SE.StartDialog(w); bad.form.name.setText("Osprey"); bad.form.saved.choose(where)
check("a name already used is refused, and says why", bad.form.create() is None and bad.form.err.text() != "", bad.form.err.text())
w.close_effort(); app.processEvents()
w.go("home"); app.processEvents()
check("closing the effort brings the form back on Effort Home", hp.start_wrap.isVisibleTo(w))
check("All Efforts' + Add an Effort, with none open, goes to the form", w.efforts_page.add_effort() is None and w.stack.currentWidget() is hp)
# 4.79.0: effort type and response type are on Effort Settings, kept as picked
w.open_effort("Osprey"); app.processEvents()
w.go("record"); app.processEvents()
rp = w.record_page; tr = rp.types
names = [tr.etype.itemText(i) for i in range(tr.etype.count())]
check("4.79.0: Effort type is on Effort Settings, Not set at first, with RFI and RFQ responses and Other, and no Program deliverables",
      tr.etype.currentData() == "" and tr.etype.currentText() == "Not set" and {"RFI response", "RFQ response", "Other"} <= set(names)
      and "Program deliverables" not in names, names)
fl = rp.findChildren(QFormLayout)[0]
order = [fl.itemAt(i, QFormLayout.LabelRole).widget().text() for i in range(4) if fl.itemAt(i, QFormLayout.LabelRole)]
check("... in the Effort group after the A number, with Response type below it", order == ["Effort name", "A number", "Effort type", "Response type"], order)
rfi = tr.etype.itemData(names.index("RFI response"))
check("picking a type keeps it at once and writes it to Effort Activity", tr.type_picked(rfi)
      and (w.ws.get("prod_std", {}) or {}).get("effort_type") == rfi and any("Effort type: RFI response" in (e.get("text") or "")
      for e in RR.Record(w.ws.root).data.get("timeline", [])), (w.ws.get("prod_std"), RR.Record(w.ws.root).data.get("timeline", [])[-2:]))
check("... the Response type follows the type until one is picked", tr.resp.itemText(0).startswith("From the effort type") and tr.resp.currentData() == "")
w.go("effortfmt"); app.processEvents()
ef = w.effortfmt_page
check("... and Effort Formatting no longer shows the two boxes, but reads the same type", not ef.etype.isVisibleTo(w) and not ef.resp.isVisibleTo(w)
      and ef.etype.currentData() == rfi and "RFI response" in ef.inherits.text(), ef.inherits.text())
w.go("record"); app.processEvents()
check("Files and sources: Template says the effort's own formatting with no volumes, and Change... opens Setup's window",
      rp.sources.template.text() in ("No volumes yet: the Outline sets them", "No template: the effort's own formatting")
      and rp.sources.change_tpl.text() == "Change...", rp.sources.template.text())
check("Files and sources: Acronym sources names the acronym database, and says no program has a list yet",
      rp.sources.acr.text() == "Acronym database, read for every effort" and "No program" in rp.sources.acr_note.text()
      and rp.sources.open_db.text() == "Open")
rp.sources.open_db.click(); app.processEvents()
check("... Open goes to Team References", w.stack.currentWidget() is w.refs_page)
n = sum(checks)
print(f"QT START {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
