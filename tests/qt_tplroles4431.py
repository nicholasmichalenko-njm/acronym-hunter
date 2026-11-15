"""4.43.1 offscreen (ST47, ST48): proposal managers and production leads build, change and archive templates; everyone
else opens Templates, looks inside one and exports it. Fictional (Osprey)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import namedtemplates as NT
import pagelayouts as PGL
import prodrules as PRL
import roleaccess as RA
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, mainwin as MW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


check("who builds: the proposal manager and Production", RA.BUILDERS == ("Proposal Manager", "Production")
      and RA.builds_templates("Production") and not RA.builds_templates("Author") and not RA.builds_templates("Reviewer"))
check("every role opens Templates", all(RA.allowed(p, "templates") for p in RA.PROFILES))
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("templates"); app.processEvents()
pg = w.named_page
role = ["Proposal Manager"]
w.profile = lambda: (role[0], "own")
lay = PGL.new(cfg, "layout", "Letter, 0.75 in", PRL.load(cfg)["company"])
b = pg.new(); b.name.setText("Page-limited RFP, Volume I"); b.set_pick("layout", lay["id"]); tid = b.save()
check("a proposal manager builds one", tid is not None and pg.b_new.isVisibleTo(w) and not pg.cards[tid].b_dup.isHidden())
pg._allowed = lambda: True

role[0] = "Author"
pg.fill(); app.processEvents()
check("an author sees the gallery, with no New template... and no Duplicate", len(pg.cards) == 1 and pg.b_new.isHidden() and pg.cards[tid].b_dup.isHidden()
      and not pg.cards[tid].b_export.isHidden() and "Proposal managers and production leads build and change templates" in pg.sum.text(), pg.sum.text())
check("... a right-click holds Look inside, Export and Open in Word only", [a.text() for a in pg.row_menu(run=False).actions() if a.text()] == ["Look inside", "Export", "Open in Word"])
check("New template... is refused, in words", pg.new() is None and "Proposal managers and production leads" in w.statusBar().currentMessage(), w.statusBar().currentMessage())
check("... and Duplicate, Rename, Archive and Remove", pg.duplicate(tid) is None and not pg.rename(tid, "Other") and not pg.archive(tid, ask=False) and not pg.remove(tid, ask=False)
      and [t["name"] for t in NT.every(cfg)] == ["Page-limited RFP, Volume I"] and not NT.get(cfg, tid).get("archived"))
v = pg.open_builder(tid)
check("Look inside opens the builder read only: no Save, the name fixed", v is not None and v.b_save.isHidden() and v.name.isReadOnly()
      and "look inside this one and export it" in v.said.text() and v.tiles["layout"].pick.text() == "Letter, 0.75 in")
check("... a tile's menu offers no pick", [a.text() for a in v.tile_menu("layout").actions()] == ["Proposal managers and production leads change what goes in"]
      and v.set_pick("layout", "") == lay["id"] and v.save() is None and NT.get(cfg, tid)["sets"]["layout"] == lay["id"])
job = v.export()
check("... and Export still writes the file", job is not None and os.path.isfile(job.copy) and NT.get(cfg, tid)["made"]["version"] == 1)
d = pg.layouts()
d.lists["layout"].setCurrentRow(0)
check("the page layouts window is read only for an author", not any(x.isEnabled() for x in d.btns["layout"].values()) and d.new("layout", "X", "Global Standards") is None
      and not d.remove("layout") and len(PGL.every(cfg, "layout")) == 1 and "Proposal managers and production leads change page layouts" in d.said.text())
d.close()

role[0] = "Production"
pg.fill(); app.processEvents()
check("a production lead builds and changes again", pg.b_new.isVisibleTo(w) and pg.duplicate(tid) is not None and len(pg.cards) == 2)
dup = [t for t in NT.every(cfg) if t["id"] != tid][0]
check("... and archives and restores", pg.archive(dup["id"], ask=False) and len(pg.cards) == 1 and pg.archive(dup["id"], on=False) and len(pg.cards) == 2)
role[0] = "Author"
NT.archive(cfg, dup["id"]); pg.fill(); pg.show_archived(True)
check("an author sees the Archived view, without Restore", list(pg.cards) == [dup["id"]]
      and [a.text() for a in pg.row_menu(run=False).actions()] == ["Proposal managers and production leads restore a template"])
w.close()
n = sum(checks)
print(f"QT TPLROLES 4431 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
