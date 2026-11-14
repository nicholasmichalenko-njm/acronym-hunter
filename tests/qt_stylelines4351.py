"""4.35.1 (ST26, Nicholas 2026-11-14 16:36 and 16:45): two styles of one name, told apart by their sets. Create another
version... on a style makes another style of that name for the sets ticked; a set holds one style of a name; each has
its own history; a change reaches the sets on that version and only those. Fictional sets and styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication.instance() or QApplication([])
import stylehistory as SH, stylelib as SL, styleown as SO, templatelib as TL
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


d = tempfile.mkdtemp()
host = Host(d); page = SP.StylesPage(host); lib = page.lib
body, _ = lib.add("style", "Osprey Body", {"type": "paragraph", "size": 11.0, "after": 6.0})
head, _ = lib.add("style", "Osprey Heading 1", {"type": "paragraph", "size": 16.0, "bold": True})
rfp, pl, pd = (SL.new_set(lib, n) for n in ("RFP", "Page-limited RFP", "Program documents"))
for k in (rfp, pl, pd):
    SL.add_to_set(lib, k["id"], [body["id"], head["id"]])
page.fill_sets(); page.fill_rows()
bodies = lambda sid: [lib.get(i) for i in lib.kit(sid)["items"] if lib.base_of(lib.get(i)) == "Osprey Body"]
size = lambda sid: lib.values(bodies(sid)[0])["size"]

page.select(body["id"]); app.processEvents()
check("the row's menu has Create another version...", "Create another version..." in [a.text() for a in page.row_menu(run=False).actions()])
dlg = SV.another(page, body["id"], run=False)
check("the dialog lists the sets to tick and says which use this one now", [cb.text() for cb in dlg.boxes] ==
      ["RFP   (uses this one now)", "Page-limited RFP   (uses this one now)", "Program documents   (uses this one now)"], [cb.text() for cb in dlg.boxes])
said = " ".join(x.text() for x in dlg.findChildren(QLabel))
check("... and that a set holds one style of a name", "A set holds one style of a name" in said and "told apart by their sets" in said, said)

tight = SV.another(page, body["id"], set_ids=[pl["id"]])
check("another version of the name is made for the set ticked", tight is not None and lib.base_of(tight) == "Osprey Body" and tight["id"] != body["id"]
      and SH.line_of(tight) != SH.line_of(body) and "for Page-limited RFP" in host.said[-1], host.said[-1])
check("it starts with the values of the one it was made from", lib.values(tight)["size"] == 11.0)
check("no set holds two: the ticked set gave up the one it had, the others keep theirs", all(len(bodies(k["id"])) == 1 for k in (rfp, pl, pd))
      and bodies(pl["id"])[0]["id"] == tight["id"] and bodies(rfp["id"])[0]["id"] == body["id"] and bodies(pd["id"])[0]["id"] == body["id"])
page.pick_set(None); app.processEvents()
ids = [page.rows.item(i).data(0x0100) for i in range(page.rows.count())]
check("Every style shows both, each once", body["id"] in ids and tight["id"] in ids and len(ids) == 3, ids)
check("... told apart by their sets", SO.used_in(lib, body["id"]) == ["RFP", "Program documents"] and SO.used_in(lib, tight["id"]) == ["Page-limited RFP"])

t2 = SE.review(page, tight["id"], {"size": 10.0, "after": 3.0})
check("changing the page-limited one changes only that set", size(pl["id"]) == 10.0 and size(rfp["id"]) == 11.0 and size(pd["id"]) == 11.0
      and "changed for Page-limited RFP" in host.said[-1], host.said[-1])
b2 = SE.review(page, body["id"], {"size": 11.5})
check("changing the shared one reaches the sets on it and not the page-limited set", size(rfp["id"]) == 11.5 and size(pd["id"]) == 11.5 and size(pl["id"]) == 10.0
      and "changed for RFP, Program documents" in host.said[-1], host.said[-1])
check("no set is told it is behind: each is on the latest of its own", SO.newer(lib, pl["id"]) == [] and SO.newer(lib, rfp["id"]) == [] and SH.behind(lib) == [])

h_shared, h_tight = SH.history(lib, b2["id"]), SH.history(lib, t2["id"])
check("each has its own history, numbered from 1", [r["version"] for r in h_shared] == [2, 1] and [r["version"] for r in h_tight] == [2, 1]
      and h_tight[1]["note"].startswith("Another version, for Page-limited RFP") and h_tight[0]["changes"] == [("Size", "11 pt", "10 pt"), ("Space after", "6 pt", "3 pt")], h_tight)
dv = page.versions(t2["id"], run=False)
check("Versions... on the page-limited one lists only its own, and names the other", dv.table.rowCount() == 2 and "in Page-limited RFP" in dv.head.text()
      and "Another version of this name is for RFP, Program documents" in dv.head.text(), dv.head.text())
back, sets = SH.restore(lib, tight["id"])
check("restoring within it touches only its own set", sets == ["Page-limited RFP"] and size(pl["id"]) == 11.0 and size(rfp["id"]) == 11.5
      and back["note"] == "Restored from version 1" and SH.number(lib, back) == 3)

SL.add_to_set(lib, rfp["id"], [SH.top(lib, tight["id"])["id"]])
check("a set moved to the other version gives up the one it had", [x["id"] for x in bodies(rfp["id"])] == [SH.top(lib, tight["id"])["id"]]
      and SO.used_in(lib, SH.top(lib, tight["id"])["id"]) == ["RFP", "Page-limited RFP"])
none_ = SV.another(page, head["id"], set_ids=[])
check("made for no set, it is kept and says so", none_ is not None and SO.used_in(lib, none_["id"]) == [] and "in no set yet" in host.said[-1], host.said[-1])
pairs = SH.lines(lib, body["id"])
check("the versions of a name are listed with their sets", [sets for _t, sets in pairs] == [["Program documents"], ["RFP", "Page-limited RFP"]], [s_ for _t, s_ in pairs])

# bringing a document in for a set updates the version that set is on
doc = SO.against(lib, [{"name": "Osprey Body", "type": "paragraph", "values": {"type": "paragraph", "size": 9.0, "after": 3.0}, "xml": ""}], pl["id"])[0]
check("the plan is against the version the set picked is on", SH.plan(lib, doc, SH.MERGE)[0] == ("Size", "11 pt", "9 pt"), SH.plan(lib, doc, SH.MERGE))
SL.bring_in(lib, [doc], os.path.join(d, "Osprey.docx"), set_of={"Osprey Body": pl["id"]})
check("brought in for that set: its version is updated and the shared one is not", size(pl["id"]) == 9.0 and size(pd["id"]) == 11.5)

# the wide restore goes line by line
for x in lib.items:
    x["at"] = "2026-11-14T10:00"
later = SE.review(page, bodies(pd["id"])[0]["id"], {"size": 12.0}); later["at"] = "2026-11-14T12:00"; lib.save()
pr = SH.as_of(lib, "2026-11-14 11:00")
check("restoring every style to a time names only the version that changed since", [(lib.base_of(a), SO.used_in(lib, a["id"])) for a, _b in pr] == [("Osprey Body", ["Program documents"])], pr)
lib2 = TL.Library(d)
check("it is all kept on disk", SH.line_of(lib2.get(tight["id"])) == SH.line_of(tight) != "" and len(SH.lines(lib2, body["id"])) == 2)

n = sum(checks)
print(f"QT STYLE LINES 4351 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
