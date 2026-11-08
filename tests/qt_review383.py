"""3.83.0 offscreen: the shared section panel on Review and on Setup is one set of records (guidance typed on one shows
on the other, saved as typed); Review shows it for the target section only; a quick note started on a selected section
points there, and a note can go to any section; notes pointed at a section follow it when it is renumbered; the Setup
panel has no Save button and the guidance layer is called Management guidance. Fictional content (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, outline_ops as O, sectionnotes as SN, setupmake as SM
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import quicknote as QNV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def spin(ms=0):
    t = time.time()
    while True:
        app.processEvents()
        if time.time() - t >= ms / 1000:
            break
        time.sleep(0.01)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); spin()
sp = w.setups_page
sp.use_headings("Volume I Technical\n  1 Ground Segment\n    1.1 Antenna Sites\n  2 Mission Operations"); spin()
LAB = "1.1 Antenna Sites"
b = sp.builder
b.btree.setCurrentItem(next(iter(b.btree.findItems(LAB, Qt.MatchExactly | Qt.MatchRecursive, 0)))); spin()
check("Setup's section shows the shared panel", sp.cur == LAB and sp.panel.label == LAB and sp.panel.isVisibleTo(w))
check("no Save this section button any more", not any(x.text() == "Save this section" for x in sp.who.findChildren(QPushButton)))
check("the guidance box's grey words", sp.panel.guide.placeholderText() == "Add Management Guidance Text")
check("the layer is called Management guidance", dict((k, t) for k, t, _x, _o in SM.LAYERS)["pm"] == "Management guidance")
sp.panel.guide.setFocus(); sp.panel.guide.insertPlainText("Lead with the second site."); spin(1000)
M = w.review.M
check("typed on Setup, saved on its own", SN.guidance(M, LAB) == "Lead with the second site.")
check("... and the preview shows it", "Lead with the second site." in sp.prev.text(), sp.prev.text())
sp.f_lead.setText("R. Diaz"); sp.f_lead.editingFinished.emit(); spin()
check("Lead saves as the box is left", SM.people(M, LAB)[0] == "R. Diaz")

w.go("assign"); spin()
ap = w.assign_page
ap.set_target(None); spin()
check("Review: no target, no section panel", not ap.section_panel.isVisibleTo(w))
ap.set_target(LAB); spin()
check("Review: the target's panel, with the guidance typed on Setup", ap.section_panel.isVisibleTo(w)
      and ap.section_panel.label == LAB and ap.section_panel.guide.toPlainText() == "Lead with the second site.")
ap.section_panel.add_note("Bring the site survey photos.")
check("a note for the authors on Review shows on Setup", any(r["note"] == "Bring the site survey photos." for r in SN.refs(M, LAB)))

d = QNV.open_note(w, run=False)
check("a quick note started on Review's section points at it", d.where.currentData() == "section:" + LAB, d.where.currentData())
check("every section is a place a note can go", d.where.findData("section:2 Mission Operations") >= 0)
QNV.open_note(w, "Ask about the backup power at site two.", "section:" + LAB)
check("sent, it shows under the section at once", any("backup power" in ap.section_panel.ctx.item(i).text()
                                                      for i in range(ap.section_panel.ctx.count())))
QNV.open_note(w, "Sort this later.", "later"); spin()
check("a note for later waits in the section's tray", ap.section_panel.tray.isVisibleTo(w) and ap.section_panel.tray.count() == 1)
O.relabel(M, {LAB: "1.2 Antenna Sites"})
rec = RR.Record(w.ws.root)
check("renumbered, the section's notes follow it", any("backup power" in c["text"] for c in SN.context(rec, "1.2 Antenna Sites")))
check("... and so do its guidance and references", SN.guidance(M, "1.2 Antenna Sites") and SN.refs(M, "1.2 Antenna Sites"))

print(f"QT REVIEW 383 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
