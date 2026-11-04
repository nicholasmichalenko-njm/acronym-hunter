"""3.33.0 Production Standards > Template profile, offscreen: Parts and versions (every part, its version in use, Pick
from the library, Save as a new version, a newer version waiting and Use it, Own values); the Content map (each kind's
style, hidden, in the file; a capture of its own; this effort's change kept on the effort); Make templates' content map
with In the file; the template library listing versions, labelling one and comparing two."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, office_pdf as OP, templatelib as TL, templateprofile as TP, setuptemplate as ST, outline_ops as O, setupdoc as SD
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
E.EffortList(LIST, "Kestrel").save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
check("Template profile is the first menu: Parts and versions, Content map; it still opens on the cover",
      sp.group_bar.tabText(0) == "Template profile" and sp.section_key() == "part_cover")
sp.nav.setCurrentRow(sp.section_index("profile_parts")); app.processEvents()
pp = sp.profile_parts
check("every part listed, with what it holds", pp.t.rowCount() >= 12 and pp.t.item(0, 1).text() == "Cover page"
      and any(pp.t.item(r, 2).text() == "the profile's own values" for r in range(pp.t.rowCount())))
r_var = next(r for r in range(pp.t.rowCount()) if pp.t.item(r, 1).text() == "Base fonts and sizes")
item = pp.save_version("variables", name="Team base", label="11 pt body")
check("Save as a new version: kept in the library, the part pinned to it", item is not None and pp.t.item(r_var, 2).text() == "Team base v1: 11 pt body"
      and sp.work["library_pins"]["variables"]["id"] == item["id"] and sp.state.text() == "Not saved")
lib = TL.Library(cfg)
v = dict(lib.values(item)); v["body_size"] = 12
v2, _st = lib.save_version(item["id"], v, label="12 pt body")
pp.refresh()
check("a newer version waits, with Use v2", pp.t.item(r_var, 3).text() == "v2 saved" and sp.work["variables"].get("body_size") != 12)
pp.use_newer("variables")
check("Use v2: the newer values, pinned, shown in Base fonts and sizes", sp.work["variables"]["body_size"] == 12
      and pp.t.item(r_var, 2).text() == "Team base v2: 12 pt body" and pp.t.item(r_var, 3).text() == "")
pp.pick("variables", item["id"])
check("Pick: back to v1", sp.work["variables"].get("body_size") != 12 and sp.work["library_pins"]["variables"]["version"] == 1)
pp.unpin("variables")
check("Own values: the pin comes off", "variables" not in sp.work.get("library_pins", {}) and pp.t.item(r_var, 2).text() == "the profile's own values")
pp.pick("variables", v2["id"])
sp.save(quiet=True)
import prodrules as PRL
check("pins are saved with the profile", (PRL.load(cfg)["company"].get("library_pins") or {}).get("variables", {}).get("version") == 2)
if os.environ.get("SK_SHOT"):
    sp.grab().save(os.environ["SK_SHOT"])
pp.unpin("variables")
# ---------------------------------------------------------------- the content map
sp.nav.setCurrentRow(sp.section_index("content_map")); app.processEvents()
cm = sp.content_map
keys = cm.keys
check("each kind, then each capture of its own", keys[:2] == ["rfp", "support"] and "capture" in keys and "cap:hot" in keys and "cap:objective" not in keys)
cm.set_row("capture", include=False)
cm.set_row("cap:hot", style="Hot Button Note", hidden=False)
check("set: captures left out, the hot button its own style, shown", sp.work["content_map"]["capture"]["include"] is False
      and sp.work["content_map"]["cap:hot"] == {"style": "Hot Button Note", "hidden": False, "include": True})
img = sp.std_preview.grab()
check("the preview draws the map", not img.isNull())
# ---------------------------------------------------------------- an effort: Make templates shows the map, keeps its change on the effort
w.open_effort("Kestrel")
w.read_page.read([os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None))
M = w.review.M
vol = O.add_volume(M, "Technical"); O.add(M, "Approach", parent=vol)
SD.set_volumes(M, "several", "", [vol])
from skqt.maketemplates import MakeTemplatesDialog
md = MakeTemplatesDialog(sp, start="effort"); app.processEvents()
check("Make templates: each kind with Hidden and In the file", "capture" in md.ref_rows and len(md.ref_rows["rfp"]) == 3)
e, cb, inc = md.ref_rows["pm"]
e.setText("PM Note"); inc.setChecked(False)
ST.set_options(M, md.ref_options(), w.ws)
md.close()
over = (w.ws.get("prod_std", {}) or {}).get("over") or {}
check("... kept as this effort's change to the profile's map", over.get("content_map", {}).get("pm") == {"style": "PM Note", "hidden": True, "include": False})
pl = ST.plan(M, cfg, w.ws, "Kestrel", w.efforts.get("Kestrel") or {})
check("the volume's map has this effort's change", ST.options(M, pl[0]["std"])["pm"]["include"] is False)
# ---------------------------------------------------------------- the library: versions
d = sp.library(run=False)
d.shelves.setCurrentRow([k for k, _t in TL.SHELVES].index("variables")); app.processEvents()
check("the library lists each version", sorted(d.t.item(r, 0).text() for r in range(d.t.rowCount())) == ["Team base v1: 11 pt body", "Team base v2: 12 pt body"])
d.t.selectRow(0)
vd = d.versions(run=False)
check("Versions: the family newest first", vd.t.rowCount() == 2 and vd.t.item(0, 0).text() == "v2")
vd.t.selectRow(1)
check("Label... names a version", vd.label("Team 2025") and TL.Library(cfg).get(item["id"])["label"] == "Team 2025")
rows = vd.compare(item["id"], v2["id"])
check("Compare: every value that differs", ("body_size", lib.values(item).get("body_size"), 12) in rows and vd.diff.rowCount() == len(rows), rows)
vd.close(); d.close()
w.close()
n = sum(checks)
print(f"QT PROFILE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
