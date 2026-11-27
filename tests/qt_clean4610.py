"""4.61.0 offscreen (Nicholas 2026-11-23 17:19): Redlining is an entry of the effort's list; Overview's tabs are Overview,
Calendar, Tasks and Meetings; Effort settings opens from a link on Overview; Effort Activity and Effort Backup are at the
foot of the menu; Submit is Submission Check; the readable copy and the Effort health card are off the screen and the
readable copy is no longer rewritten; a document added can be marked a Redlined Deliverable there and then; Reviewer
markups is a Quick tool."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, docreturn as DR, effort as E, effortrec as RR, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, toolshome as TH
import skqt.mainwin as MW
from skqt.mainwin import MainWindow
from skqt.pagetitles import TITLES

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
src = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
P = os.path.join(CD, "Heron_Section_L.pdf"); shutil.copy2(src, P)
lib0 = DV.Library(ws.p("documents")).load()
lib0.add(P, DI.read(P), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Heron"); app.processEvents()

effort = [k for k, _t in MW.RAIL[1][1]]
check("Redlining is in the effort's list, after Deliverables", effort.index("redline") == effort.index("deliverables") + 1, effort)
check("the last entry reads Submission Check", w.step_btns["finalcheck"].text() == "Submission Check" and TITLES["finalcheck"][0] == "Submission Check")
foot = [k for k, _t in MW.RAIL[3][1]]
check("the foot of the menu: Effort Activity, Effort Backup, Settings", foot == ["activity", "backup", "settings"], foot)

w.rail_go("home"); app.processEvents()
check("Overview opens the one page, with Calendar, Tasks and Meetings beside it", w.stack.currentWidget() is w.overview_page
      and [w.page_tabs.tabText(i) for i in range(w.page_tabs.count())] == ["Overview", "Customer information", "Calendar", "Tasks", "Meetings"],   # 4.75.0
      [w.page_tabs.tabText(i) for i in range(w.page_tabs.count())])
ov = w.overview_page
check("Overview has the link Effort settings", ov.settings_link.text() == "Effort settings" and ov.settings_link.isVisibleTo(w))
ov.settings_link.click(); app.processEvents()
rp = w.record_page
check("... which opens the effort's settings, lit under Overview, with no tabs", w.stack.currentWidget() is rp and w.page_title.text() == "Effort Settings"
      and w.step_btns["home"].isChecked() and w._tab_keys == [], (w.page_title.text(), w._tab_keys))
check("no Readable copy, Effort health or Backups card there", not rp.readable.isVisibleTo(w) and not rp.health.isVisibleTo(w) and not rp.out.isVisibleTo(w))
more = [a.text() for a in rp.bar.more_menu.actions()] if getattr(rp.bar, "more_menu", None) is not None else []
check("... and nothing about them under More", not any("readable" in t.lower() or "health" in t.lower() or "back up" in t.lower() or "restore" in t.lower() for t in more), more)

w.go("activity"); app.processEvents()
check("Effort Activity is its own entry", w.step_btns["activity"].isChecked() and w.stack.currentWidget() is w.activity_page
      and w.page_title.text() == "Effort Activity" and w._tab_keys == [], (w.page_title.text(), w._tab_keys))
w.go("backup"); app.processEvents()
bp = w.backup_page
check("Effort Backup is its own entry", w.step_btns["backup"].isChecked() and w.stack.currentWidget() is bp and w.page_title.text() == "Effort Backup")
check("with no folder chosen it says so, and Back up now does nothing", bp.where.text() == "No backup folder is chosen." and bp.backup_now() is None, bp.where.text())
bk = os.path.join(tmp, "Backups")
w.safety.test_dir = bk; os.makedirs(bk)
bp.refresh()
check("the folder is shown", bp.where.text() == bk and bp.open_folder() == bk, bp.where.text())
out = bp.backup_now()
check("Back up now writes the effort's backup there", out is not None and os.path.isdir(os.path.join(bk, "Heron")), (out, os.listdir(bk)))
check("... and no readable copy is written beside the effort", not [n for n in os.listdir(tmp) + os.listdir(ED) if "readable copy" in n], os.listdir(ED))
check("the readable copy is no longer rewritten on a timer", "readable_tick" not in open(MW.__file__, encoding="utf-8").read().split("self.rd_timer = QTimer")[1].split("\n")[0])

# Redlining
w.go("redline"); app.processEvents()
check("Redlining: its own entry and title", w.step_btns["redline"].isChecked() and w.page_title.text() == "Redlining" and w._tab_keys == [], w._tab_keys)
w.go("deliverables"); app.processEvents()
check("Deliverables is the list alone", w.step_btns["deliverables"].isChecked() and w._tab_keys == [])

# a document added as a Redlined Deliverable
check("the Add table's Purpose offers the deliverable purposes (4.83.0)", [k for k, _n in DV.ADD_USES] == ["matrix", "reference", "fill", "submit", "redline"])
P2 = os.path.join(tmp, "Heron_Terms.pdf"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "SOW.pdf"), P2)
w.go("library"); app.processEvents()
lp = w.library_page
lp.add(paths=[P2], choices={"Heron_Terms.pdf": {"choice": "new", "role": "redline", "name": "Terms", "category": "customer", "initial": "T", "type": "Other"}})
t0 = time.time()
while lp.worker is not None and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
lib = DV.Library(ws.p("documents")).load()
d = lib.doc_of_file("Heron_Terms.pdf")
check("added marked Redlined Deliverable: the document carries the mark and reads as Reference", d is not None and lib.returns_of(d) == ["redline"]
      and DV.use_key(lib.role_of(d)) == "reference", (d and lib.returns_of(d), d and lib.role_of(d)))
check("... and has its tile on Deliverables", d is not None and DR.tile_of(RR.Record(ws.root), d["id"]) is not None)
w.go("redline"); app.processEvents()
check("... so Redlining shows Prepare, Check and Exceptions", w._tab_keys == ["redline", "rcheck", "exceptions"]
      and [w.page_tabs.tabText(i) for i in range(w.page_tabs.count())] == ["Prepare", "Check", "Exceptions"], w._tab_keys)

# Quick tools
check("Reviewer markups is a Quick tool, pinned for every role", TH.TOOLS["markups"][0] == "Reviewer markups" and all("markups" in p for p in TH.ROLE_PINS.values()))
w.tools_page.open("markups"); app.processEvents()
check("... and opens the page", w.stack.currentWidget() is w.markups_page)
w.close()
print(f"QT CLEAN 4610 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
