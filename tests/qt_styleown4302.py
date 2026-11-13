"""4.30.2 (Nicholas 2026-11-13 14:34, 14:43): a set owns its styles. The same name with other values in two sets is two
styles; an identical style in several sets is one; a choice is asked only where the set has the name with other values;
a v switch shows only where a set keeps both; a change made inside a set is that set's alone. Fictional styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
app = QApplication.instance() or QApplication([])
import stylelib as SL, styleown as SO, templatelib as TL
from skqt import stylespage as SP, styleimport as SI

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def tabs(page):
    """The v tabs on the rows now in the list (rows taken away linger until Qt deletes them)."""
    return [b for i in range(page.rows.count()) for b in page.rows.itemWidget(page.rows.item(i)).findChildren(QPushButton, "verTab")]


class Host:
    def __init__(self, d):
        self.config_dir, self.said = d, []
    def status(self, t): self.said.append(t)
    def toast(self, t): self.said.append(t)
    def go(self, *_a): pass


def st(name, size, typ="paragraph", **kw):
    v = dict({"type": typ, "font": "Arial", "size": size}, **kw)
    return {"name": name, "type": typ, "values": v, "xml": ""}


d = tempfile.mkdtemp()
host = Host(d); page = SP.StylesPage(host); lib = page.lib
rfp = SL.new_set(lib, "RFP"); rfi = SL.new_set(lib, "RFI")
path = os.path.join(d, "Osprey.docx")

# the RFP set takes Body 11 and Caption 9
r = SO.against(lib, [st("Body", 11), st("Caption", 9)], rfp["id"])
check("into an empty set nothing is asked; each row says it comes in, in that set", all(not x["clash"] and x["keep"] for x in r) and "in RFP" in r[0]["words"], r[0]["words"])
SL.bring_in(lib, r, path, set_of={x["name"]: rfp["id"] for x in r})

# the RFI set takes Body 10 (other values) and the identical Caption 9
r = SO.against(lib, [st("Body", 10), st("Caption", 9)], rfi["id"])
body, cap = r
check("the same name with other values in another set is not asked about: the set gets its own, theirs stays",
      body["state"] == "variant" and not body["clash"] and "RFI gets its own" in body["words"] and "RFP" in body["words"], body["words"])
check("an identical style is one style, and the row names the set that uses it already", cap["state"] == "same" and not cap["clash"] and "RFP" in cap["words"], cap["words"])
c = SL.bring_in(lib, r, path, set_of={x["name"]: rfi["id"] for x in r})
b_rfp = SO.held(lib, rfp["id"], SO.fam(body["mine"]))[0]; b_rfi = SO.held(lib, rfi["id"], SO.fam(body["mine"]))[0]
check("each set holds its own Body; the RFP set's is untouched", b_rfp["id"] != b_rfi["id"] and lib.values(b_rfp)["size"] == 11 and lib.values(b_rfi)["size"] == 10)
caps = [i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Caption"]
check("the identical Caption is kept once and both sets use it", len(caps) == 1 and SO.used_in(lib, caps[0]["id"]) == ["RFP", "RFI"], SO.used_in(lib, caps[0]["id"]))
check("no set is told another set's style is a newer version of its own", SO.newer(lib, rfp["id"]) == [] and SO.newer(lib, rfi["id"]) == [])

# the rows
allr = SO.rows(lib)
names = [(lib.base_of(lib.get(x["shown"])), len(x["versions"])) for x in allr]
check("Every style: two Body rows, one Caption row, and no version switch on any", names == [("Body", 0), ("Body", 0), ("Caption", 0)], names)
inr = SO.rows(lib, rfi["id"])
check("in a set: one row per style it holds, its own Body, no switch", [x["shown"] for x in inr if lib.base_of(lib.get(x["shown"])) == "Body"] == [b_rfi["id"]] and all(not x["versions"] for x in inr))
page.fill_sets(); page.pick_set(None)
check("the list shows three rows and no v tabs", page.rows.count() == 3 and not tabs(page))

# the set already has the name with other values: the one question
r = SO.against(lib, [st("Body", 12), st("Caption", 9), st("Quote", 10)], rfp["id"])
body, cap, quo = r
check("the set has Body with other values: that row asks, and starts on Keep the set's", body["clash"] and body["clash"]["id"] == b_rfp["id"] and body["choice"] == "mine" and "choose" in body["words"])
check("... the identical Caption and the new Quote ask nothing", not cap["clash"] and not quo["clash"])
page.pick_set(rfp["id"])
dlg = SI.StyleImport(page, path, r)
ch = [w for w in dlg.table.findChildren(QComboBox, "clashChoice")]
check("the dialog shows one choice, with the three answers", len(ch) == 1 and [ch[0].itemText(i) for i in range(3)] == ["Keep the set's", "Take the file's", "Keep both"])
check("the foot says one is to choose and it keeps the set's", "1 to choose (1 keep the set's)" in dlg.n_lab.text(), dlg.n_lab.text())
c = dlg.go()
check("Keep the set's: the file's Body is not brought in; the set's stays", c.get("kept") == 1 and [x["id"] for x in SO.held(lib, rfp["id"], SO.fam(b_rfp))] == [b_rfp["id"]]
      and not any(lib.values(i).get("size") == 12 for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Body"))
r = SO.against(lib, [st("Body", 12)], rfp["id"]); r[0]["choice"] = "both"
SL.bring_in(lib, r, path, set_of={"Body": rfp["id"]})
both = SO.held(lib, rfp["id"], SO.fam(b_rfp))
check("Keep both: the set holds the two", len(both) == 2 and {lib.values(x)["size"] for x in both} == {11, 12})
page.pick_set(rfp["id"])
check("... and only then does the row carry a v switch", len(tabs(page)) == 2)
page.pick_set(rfi["id"])
check("... the other set's rows carry none", not tabs(page))
r = SO.against(lib, [st("Body", 14)], rfi["id"]); r[0]["choice"] = "file"
SL.bring_in(lib, r, path, set_of={"Body": rfi["id"]})
now = SO.held(lib, rfi["id"], SO.fam(b_rfp))
check("Take the file's: the set moves to the file's Body; the RFP set keeps both of its own", len(now) == 1 and lib.values(now[0])["size"] == 14 and len(SO.held(lib, rfp["id"], SO.fam(b_rfp))) == 2)
SO.retarget(lib, r2 := SO.against(lib, [st("Body", 9.5)], None), rfi["id"])
check("picking the set in the dialog judges the rows against it", r2[0]["clash"] is not None and r2[0]["choice"] == "mine")

# a change made inside a set is that set's alone
cap_id = caps[0]["id"]
page.pick_set(rfi["id"])
from skqt import styleedit as SE
new = SE.review(page, cap_id, {"size": 8})
check("changing a shared style inside a set changes it for that set only", new is not None and SO.used_in(lib, new["id"]) == ["RFI"] and SO.used_in(lib, cap_id) == ["RFP"], host.said[-1])
check("... the toast names the set", "changed for RFI" in host.said[-1], host.said[-1])
check("... and the other set is not nagged about it", SO.newer(lib, rfp["id"]) == [])
dlg = SE.StyleEdit(page, lib.get(now[0]["id"]), lib.values(now[0]))
check("a style only this set uses offers no choice of sets", dlg.scope is None)
page.pick_set(rfp["id"])
quote = next(i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Quote")
SL.add_to_set(lib, rfi["id"], [quote["id"]])
dlg = SE.StyleEdit(page, quote, lib.values(quote))
check("a style two sets use: the form asks, and starts on this set only", dlg.scope is not None and dlg.scope.currentData() is False and dlg.scope.itemText(0) == "RFP only")
new = SE.review(page, quote["id"], {"size": 13}, every=True)
check("Every set that uses it: both move", SO.used_in(lib, new["id"]) == ["RFP", "RFI"] and SO.used_in(lib, quote["id"]) == [])
page.pick_set(None)
ids = [page.rows.item(i).data(0x0100) for i in range(page.rows.count())]
check("a version no set uses is off the rows, and reached from the row's Earlier versions", quote["id"] not in ids and any(x["id"] == quote["id"] for x in page.earlier.get(new["id"], [])))
n3 = SE.review(page, new["id"], {"size": 15})
check("a change saved from Every style moves no set; each set that uses the style is told once", SO.used_in(lib, n3["id"]) == [] and len(SO.newer(lib, rfp["id"])) == 1)

# what the set is used for
page.pick_set(rfp["id"]); page.used_for("RFP")
check("a set carries what it is used for, shown under its name", SL.get_set(lib, rfp["id"]).get("used_for") == "RFP" and any("\nRFP" in page.sets.item(i).text() for i in range(page.sets.count())))
lib2 = TL.Library(d)
check("it is kept with the set, and a library saved before opens the same", lib2.kit(rfp["id"]).get("used_for") == "RFP" and len(lib2.kit(rfp["id"])["items"]) == len(lib.kit(rfp["id"])["items"]))
n = sum(checks)
print(f"QT STYLEOWN 4302 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
