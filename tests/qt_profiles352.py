"""3.52.0 Effort Profiles and Templates, offscreen: each effort type's profiles listed; a new profile and a copy; volumes;
a part changed from the library, offered only the items tagged for its effort type (Show all lifts the filter); a newer
version waits until Use it; the RFP's size limits checked as you pick; Templates lists one row per profile and volume,
Blocked when a limit is broken, Not made yet, Ready once made and Needs review when the profile changes; Make all ready;
Production Standards under Advanced. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
import effortprofiles as EP, prodrules as PRL, templatelib as TL, templatesboard as TB, roleaccess as RA, libcats as LC


class Host:
    config_dir = cfg
    said = []

    def status(self, t):
        self.said.append(t)
    toast = status


from skqt.profilespage import EffortProfilesPage, ChangeDialog
from skqt.templatespage import TemplatesPage
host = Host()
pg = EffortProfilesPage(host); pg.refresh(); pg.show(); app.processEvents()
data = pg.data
ets = [e["id"] for e in data["effort_types"]]
heads = [pg.tree.topLevelItem(i).text(0) for i in range(pg.tree.topLevelItemCount())]
check("every effort type with its profiles", heads == [e["name"] for e in data["effort_types"]] and pg.cur is not None, heads)
eid = pg.cur[0]
pid = pg.new_profile("Kestrel Past Performance Volume")
check("New profile: in this effort type, selected", pid and pid in PRL.effort_type_of(pg.data, eid)["profiles"] and pg.cur == (eid, pid))
check("... a name already in it is refused", pg.new_profile("kestrel past performance volume") == "")
cp = pg.new_profile("Kestrel Orals", copy=True)
check("Copy: starts from the selected profile", cp and pg.cur == (eid, cp))
got = pg.save_volumes("Volume IV Orals; Volume V Slides; volume iv orals")
check("Volumes: one per name, each once", got == ["Volume IV Orals", "Volume V Slides"], got)
check("saved at once", EP.volumes(PRL.load(cfg), eid, cp) == got)
check("Rename", pg.rename("Kestrel Oral Presentation") and PRL.type_of(PRL.load(cfg), cp)["name"] == "Kestrel Oral Presentation")

# parts from the library, filtered by effort type
lib = TL.Library(cfg)
theme_v = {"name": "Kestrel Blue", "colors": {"accent1": "1F4E79"}}
mine, _ = lib.add("theme", "Kestrel Blue", theme_v)
other, _ = lib.add("theme", "Osprey Green", {"name": "Osprey Green", "colors": {"accent1": "2E7D32"}})
untagged, _ = lib.add("theme", "Heron Grey", {"name": "Heron Grey", "colors": {"accent1": "5F6B73"}})
gone, _ = lib.add("theme", "Old Theme", {"name": "Old Theme", "colors": {"accent1": "000000"}})
LC.set_effort_types(lib, [mine["id"]], [eid])
LC.set_effort_types(lib, [other["id"]], [x for x in ets if x != eid][:1])
LC.set_effort_types(lib, [gone["id"]], [eid]); LC.set_status(lib, [gone["id"]], "retired")
lib = TL.Library(cfg)
names = [i["id"] for i in EP.choices(lib, "theme", eid)]
check("Change offers this effort type's items and the untagged ones, not retired or another type's",
      mine["id"] in names and untagged["id"] in names and other["id"] not in names and gone["id"] not in names, names)
check("... Show all lifts the filter", {other["id"], gone["id"]} <= {i["id"] for i in EP.choices(lib, "theme", eid, show_all=True)})
dlg = ChangeDialog(pg, lib, "theme", eid)
n_f = dlg.list.count(); dlg.all.setChecked(True)
check("the dialog's Show all lists more", dlg.list.count() > n_f, (n_f, dlg.list.count()))
said = pg.change("theme", mine["id"])
std = EP.resolved(PRL.load(cfg), eid, cp)
check("Change: the part takes the item and is pinned to it", bool(said) and (std.get("library_pins") or {}).get("theme", {}).get("id") == mine["id"], std.get("library_pins"))
lib = TL.Library(cfg)
newer, st = lib.save_version(mine["id"], dict(theme_v, colors={"accent1": "123456"}), label="2027")
pg.fill_parts()
row = next(r for r in range(pg.t.rowCount()) if pg.t.item(r, 0).data(0x0100) == "theme")
check("a newer version waits, marked", pg.t.item(row, 3).text().startswith("v"), pg.t.item(row, 3).text())
pg.use_newer("theme")
check("Use it: the newer version is picked", (EP.resolved(pg.data, eid, cp).get("library_pins") or {}).get("theme", {}).get("id") == newer["id"])

# limits
lims = pg.set_limit("body", 14)
body = next(r for r in lims if r["scope"] == "body")
check("a limit over the profile's size: under the limit", body["min"] == 14 and body["ok"] is False, body)
row = next(r for r in range(pg.lt.rowCount()) if pg.lt.item(r, 0).text() == "Body text")
check("... shown as under the limit", pg.lt.item(row, 3).text() == "under the limit")

# templates
RA.set_preview(cfg, "template", True)
tp = TemplatesPage(host); tp.refresh()
rows = [r for r in tp.rows if r["pid"] == cp]
check("Templates: one row per volume of the profile", [r["volume"] for r in rows] == ["Volume IV Orals", "Volume V Slides"], rows)
check("... Blocked while a limit is broken, with why", all(r["state"] == TB.BLOCKED and "under the 14 pt limit" in r["why"] for r in rows))
check("... a blocked row cannot be made", tp.make(rows[0]) is None)
pg.set_limit("body", 10)
tp.refresh()
rows = [r for r in tp.rows if r["pid"] == cp]
check("limit met: Not made yet", all(r["state"] == TB.NEW for r in rows), [r["state"] for r in rows])
import prodcopy as PCY
PCY.output_folder = lambda *_a, **_k: os.path.join(tmp, "out")
job = tp.make(rows[0])
check("Make .dotx: the template in Templates\\<effort type>", job and os.path.isfile(job.copy)
      and os.path.basename(os.path.dirname(job.copy)) == rows[0]["ename"], job and job.copy)
r0 = next(r for r in tp.rows if r["pid"] == cp and r["volume"] == "Volume IV Orals")
check("... and the row says Ready, with its version", r0["state"] == TB.READY and "version 1" in r0["why"], r0)
pg.set_limit("table", 8)
tp.refresh()
r0 = next(r for r in tp.rows if r["pid"] == cp and r["volume"] == "Volume IV Orals")
check("the profile changes: Needs review", r0["state"] == TB.REVIEW and "changed" in r0["why"], r0)
tp.f_et.setCurrentIndex(tp.f_et.findData(eid))
made = tp.make_all()
check("Make all ready: every changed or new row of the effort type", len(made) >= 2
      and all(r["state"] in (TB.READY, TB.BLOCKED) for r in tp.shown()), [(r["name"], r["state"]) for r in tp.shown()])
check("the template's name counts up a version", "v2" in os.path.basename(next(j.copy for j in made if "Volume IV Orals" in j.copy)))

# take out
check("Take out: gone from this effort type", pg.take_out() is True and cp not in PRL.effort_type_of(PRL.load(cfg), eid)["profiles"])
from skqt import mainwin as MW
check("Production Standards is off the menu (3.69.0); Effort Profiles in the Team group, Templates its tab (3.75.0)",
      "prodstd" not in [k for _g, it in MW.RAIL for k, _t in it] and MW.GROUP_OF.get("profiles") == "Templates" and [k for k, _t in MW.TABS["templates"]] == ["templates", "profiles", "studio"])   # 4.28.0
n = sum(checks)
print(f"QT PROFILES 3.52 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
