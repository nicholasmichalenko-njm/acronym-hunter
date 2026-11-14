"""4.35.0, offscreen (ST15, ST16, ST24): a style's versions on screen. Versions... on the row lists every version,
Latest first, with what changed in words; Restore this version puts an earlier one on top; Restore every style as
of... lists what would change before anything does; Undo the restore puts back what was latest. Fictional styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
import stylehistory as SH, stylelib as SL
from skqt import stylespage as SP, styleedit as SE, styleversions as SV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


class Host:
    def __init__(self, d):
        self.config_dir, self.said = d, []
    def status(self, t): self.said.append(t)
    def toast(self, t): self.said.append(t)
    def go(self, *_a): pass


host = Host(tempfile.mkdtemp()); page = SP.StylesPage(host); lib = page.lib
h2, _ = lib.add("style", "Osprey Heading 2", {"type": "paragraph", "size": 13.0, "bold": True})
body, _ = lib.add("style", "Osprey Body", {"type": "paragraph", "size": 11.0})
for it in (h2, body):
    it["at"] = "2026-11-10T09:00"
tech = SL.new_set(lib, "Technical volume"); SL.add_to_set(lib, tech["id"], [h2["id"], body["id"]])
lib.save(); page.fill_sets(); page.fill_rows()
v2 = SE.review(page, h2["id"], {"size": 14.0}); v2["at"] = "2026-11-11T10:00"
v3 = SE.review(page, v2["id"], {"size": 15.0, "italic": True}); v3["at"] = "2026-11-12T11:00"
b2 = SE.review(page, body["id"], {"size": 12.0}); b2["at"] = "2026-11-13T12:00"
lib.save()
check("a change says which sets got it", "changed for Technical volume" in host.said[-1], host.said[-1])
page.select(v3["id"]); app.processEvents()
acts = [a.text() for a in page.row_menu(run=False).actions()]
check("the row's menu has Versions..., and keeps Name this version...", "Versions..." in acts and "Name this version..." in acts and "Earlier versions" not in acts, acts)
dlg = page.versions(v3["id"], run=False)
cell = lambda r, c: dlg.table.item(r, c).text()
check("Versions... lists every version, Latest first and marked", [cell(r, 0) for r in range(3)] == ["3  Latest", "2", "1"], [cell(r, 0) for r in range(3)])
check("each row says when, and what changed in words", cell(0, 1) == "2026-11-12 11:00" and cell(0, 3) == "Size: 14 pt to 15 pt; Italic: off to on"
      and cell(1, 3) == "Size: 13 pt to 14 pt" and cell(2, 3) == "The first version", [cell(r, 3) for r in range(3)])
check("the head says Latest is the one in use and a restore removes nothing", "latest version is the one in use" in dlg.head.text() and "nothing is removed" in dlg.head.text())
dlg.table.selectRow(0); app.processEvents()
check("Restore this version is off on the Latest", not dlg.b_restore.isEnabled())
dlg.table.selectRow(2); app.processEvents()
check("... and on for an earlier one", dlg.b_restore.isEnabled())
dlg.b_restore.click(); app.processEvents()
top = lib.latest(h2["id"])
check("Restore this version: version 1's values are version 4, the Latest, and the list shows it", top["version"] == 4 and lib.values(top)["size"] == 13.0
      and cell(0, 0) == "4  Latest" and cell(0, 3).startswith("Restored from version 1") and dlg.table.rowCount() == 4, cell(0, 3))
check("the set uses it, the person is told, and the row shows it", [lib.get(i)["version"] for i in lib.kit(tech["id"])["items"] if lib.get(i)["family"] == h2["family"]] == [4]
      and "version 1 is the latest again, as version 4" in host.said[-1] and top["id"] in [page.rows.item(i).data(0x0100) for i in range(page.rows.count())], host.said[-1])
top["at"] = "2026-11-13T13:00"; lib.save()

dlg2 = SV.restore_all(page, run=False)
check("Restore every style as of... offers the times styles changed, newest first", dlg2.pick.count() >= 4 and dlg2.pick.itemText(0) == SH.moments(lib)[0], dlg2.pick.itemText(0))
dlg2.pick.setCurrentIndex(dlg2.pick.findData("2026-11-12 11:00")); app.processEvents()
rows = [[dlg2.table.item(r, c).text() for c in range(3)] for r in range(dlg2.table.rowCount())]
check("it lists which styles would change before anything does", rows == [["Osprey Body", "version 2", "version 1"], ["Osprey Heading 2", "version 4", "version 3"]]
      and dlg2.b_go.text() == "Restore 2 styles" and lib.latest(body["id"])["version"] == 2, rows)
dlg2.b_go.click(); app.processEvents()
check("Restore: each is a new Latest with the values of that time", lib.values(lib.latest(body["id"]))["size"] == 11.0 and lib.values(lib.latest(h2["id"]))["size"] == 15.0
      and lib.latest(h2["id"])["version"] == 5 and "2 styles restored to 2026-11-12 11:00" in host.said[-1] and "Undo the restore" in host.said[-1], host.said[-1])
check("Undo the restore puts back what was latest, as new versions", SV.undo_restore(page) == 2 and lib.values(lib.latest(body["id"]))["size"] == 12.0
      and lib.values(lib.latest(h2["id"]))["size"] == 13.0 and lib.latest(h2["id"])["version"] == 6 and len(lib.family(h2["id"])) == 6, host.said[-1])
check("with nothing to undo it says so", SV.undo_restore(page) == 0 and "no restore to undo" in host.said[-1])
check("a time at which nothing differs restores nothing and says so", SV.restore_all(page, when=SH.moments(lib)[0]) == 0 and "already as it was" in host.said[-1], host.said[-1])
words = " ".join(host.said).lower()
check("the words: no publish, no draft, no revert", not any(x in words for x in ("publish", "draft", "revert")))

n = sum(checks)
print(f"QT STYLE VERSIONS 4350 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
