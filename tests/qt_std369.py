"""3.69.0 offscreen: the sections that lived only in Production Standards, in their new homes. Rules > Fix a Copy's
checks (graphics, Excel and PowerPoint, the words Fix a Copy reports and fixes) edits the global standard; Formatting
Standards > Allowed styles... (allowed styles, the styles the rules read); Effort Profiles > Content map, fields and font
rules... edits one profile in one effort type; a rule's values open where they live now; Production Standards is off the
menu and opens from Settings; its report finds nothing lost. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import prodrules as PRL, prodstdreport as PSR, rulebook as RB
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("Production Standards is off the menu", all(k != "prodstd" for _g, it in RAIL for k, _t in it) and "Advanced" not in [g for g, _i in RAIL])
w.go("settings"); app.processEvents()
from PySide6.QtWidgets import QPushButton
check("3.77.0: no door from Settings any more", not any("Production Standards" in b.text() for b in w.settings_page.findChildren(QPushButton)))
# ---- Rules > Fix a Copy's checks
w.go("rules"); app.processEvents()
rp = w.rules_page
rp.show_family(3); app.processEvents()
ed = rp.checks
check("Rules has Fix a Copy's checks: graphics, Excel and PowerPoint, the words", ed is not None and ed.sections == ["graphics", "office", "terms"]
      and rp.stack.currentWidget() is rp.checks_box and "Company Standards (Default)" in ed.where.text())
it = next(i for i in ed.binder.items if i["path"] == ("graphics", "min_ppi"))
it["w"].setValue(300)
check("a change shows Save", ed.dirty and ed.b_save.isEnabled() and it["label"].font().bold())
ed.tables[1].add({"find": "Kestrel Ground Segmnet", "replace": "Kestrel Ground Segment", "case": "match"})
ed.save()
data = PRL.load(cfg)
check("saved into the global standard", data["company"]["graphics"]["min_ppi"] == 300
      and data["company"]["terms"]["replace"][-1]["replace"] == "Kestrel Ground Segment" and not ed.dirty)
it = next(i for i in ed.binder.items if i["path"] == ("graphics", "min_ppi"))
it["w"].setValue(150); ed.reload()
check("Undo changes takes back what was not saved", ed.binder.value(it) == 300 and not ed.dirty)
# ---- Formatting Standards > Allowed styles
w.go("formatstd"); app.processEvents()
dlg = w.formatstd_page.style_rules(modal=False)
se = dlg.editor
data = PRL.load(cfg); data["company"].setdefault("style_defs", {})["Kestrel Body"] = {"font": "Arial"}; PRL.save(cfg, data); se.reload()
names = [se.allowed.item(i, 0).text() for i in range(se.allowed.rowCount())]
check("Allowed styles lists the standard's styles to tick", "Kestrel Body" in names)
se.allowed.item(names.index("Kestrel Body"), 0).setCheckState(Qt.Checked)
role = next(i for i in se.binder.items if i["path"] == ("style_roles", "a_number"))
role["w"].setEditText("Kestrel A Number"); role["w"].lineEdit().textEdited.emit("Kestrel A Number")
se.save()
c = PRL.load(cfg)["company"]
check("ticked styles and the styles the rules read are saved", c["styles"]["allowed"] == ["Kestrel Body"]
      and c["style_roles"]["a_number"] == "Kestrel A Number")
dlg.close()
# ---- Effort Profiles > Content map, fields and font rules
w.go("profiles"); app.processEvents()
pp = w.profiles_page
pp.refresh(); app.processEvents()
check("a profile is picked and the button is on", pp.cur is not None and pp.b_more.isEnabled())
dlg = pp.more(modal=False)
pe = dlg.editor
check("the profile's own window: font rules, content map, fields", pe.sections == ["fonts", "content_map", "fillins"]
      and pe.store.what and hasattr(pe, "content_map"))
hi = next(i for i in pe.binder.items if i["path"] == ("fonts", "body", "max_size"))
hi["w"].setValue(12)
pe.tables[0].add({"key": "volume_title", "name": "Volume title", "kind": "styleref", "style": "Kestrel Volume Title"})
pe.save()
d = PRL.load(cfg)
eid, pid = pp.cur
over = (PRL.effort_type_of(d, eid).get("profile_over") or {}).get(pid) or {}
check("saved as this profile's changes in its effort type only", over["fonts"]["body"]["max_size"] == 12
      and over["fill_ins"][0]["key"] == "volume_title" and (d["company"].get("fonts") or {}).get("body", {}).get("max_size") != 12, over)
check("... and the profile reads them", PRL.resolved_type(d, pid, eid)["fonts"]["body"]["max_size"] == 12)
dlg.close()
# ---- rules open where their values live now
r9 = next(r for r in RB.BUILTIN if r[0] == "9")
check("a rule's values open where they live now", r9[4] == ("formatstd", "styles") and all(r[4][0] != "prodstd" for r in RB.BUILTIN))
w.go("rules"); app.processEvents()
rp.open_where(("rules", "checks"))
check("the banned-phrase rule opens Fix a Copy's checks", rp.stack.currentWidget() is rp.checks_box)
rep = PSR.report(cfg)
check("Production Standards' report: nothing lost", rep["ready"] and rep["at_risk"] == 0)

print(f"QT STD 369 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
