"""4.30.2 (Nicholas 2026-11-13 14:34, 14:43), as 4.35.0 and 4.35.1 changed it (ST24, ST25: one style, one history; a
change and a style brought in reach every set that uses the style). Was: a set owns its styles. The same name with other values in two sets is two
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

# 4.35.1 (ST24, ST25): one style, one history. The RFI set brings in Body 10 (other values) and the identical Caption 9
r = SO.against(lib, [st("Body", 10), st("Caption", 9)], rfi["id"])
body, cap = r
check("the same name with other values: the row says your style is updated, for the set that uses it",
      body["state"] == "variant" and not body["clash"] and "your style is updated, as its new latest version" in body["words"] and "RFP" in body["words"], body["words"])
check("an identical style is one style, and the row names the set that uses it already", cap["state"] == "same" and not cap["clash"] and "RFP" in cap["words"], cap["words"])
import stylehistory as SH
check("before anything changes, the row's plan says each value that would change", SH.plan(lib, body, SH.MERGE) == [("Size", "11 pt", "10 pt")], SH.plan(lib, body, SH.MERGE))
c = SL.bring_in(lib, r, path, set_of={x["name"]: rfi["id"] for x in r})
b_rfp = SO.held(lib, rfp["id"], SO.fam(body["mine"]))[0]; b_rfi = SO.held(lib, rfi["id"], SO.fam(body["mine"]))[0]
check("Body is one style: both sets hold its new latest version, and the earlier one is kept", b_rfp["id"] == b_rfi["id"] and lib.values(b_rfp)["size"] == 10
      and b_rfp["version"] == 2 and [lib.values(x)["size"] for x in lib.family(b_rfp["id"])] == [10, 11] and c["variant"] == 1, c)
check("its history says where the change came from", SH.history(lib, b_rfp["id"])[0]["note"] == "Brought in from Osprey.docx: only what differs")
caps = [i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Caption"]
check("the identical Caption is kept once and both sets use it", len(caps) == 1 and SO.used_in(lib, caps[0]["id"]) == ["RFP", "RFI"], SO.used_in(lib, caps[0]["id"]))
check("no set is behind", SO.newer(lib, rfp["id"]) == [] and SO.newer(lib, rfi["id"]) == [] and SH.behind(lib) == [])

# the rows
allr = SO.rows(lib)
names = [lib.base_of(lib.get(x["shown"])) for x in allr]
check("Every style: one Body row and one Caption row", names == ["Body", "Caption"], names)
inr = SO.rows(lib, rfi["id"])
check("in a set: one row per style it holds", [x["shown"] for x in inr if lib.base_of(lib.get(x["shown"])) == "Body"] == [b_rfi["id"]])
page.fill_sets(); page.pick_set(None)
check("the list shows two rows and no v tabs", page.rows.count() == 2 and not tabs(page), page.rows.count())

# the set shown already uses the style: Update the style is the start, Keep both and Skip are there (4.30.5, as 4.35.1 has it)
r = SO.against(lib, [st("Body", 12), st("Caption", 9), st("Quote", 10)], rfp["id"])
body, cap, quo = r
check("the set has Body with other values: that row carries the choice and starts on Update the style", body["clash"] and body["clash"]["id"] == b_rfp["id"] and body["choice"] == "replace", body["choice"])
check("... the identical Caption and the new Quote carry none", not cap["clash"] and not quo["clash"])
page.pick_set(rfp["id"])
dlg = SI.StyleImport(page, path, r)
from PySide6.QtWidgets import QLabel
ch = [w for w in dlg.table.findChildren(QComboBox, "clashChoice")]
flags = [x.text() for x in dlg.table.findChildren(QLabel, "clashFlag")]
check("the dialog shows the choice once: Update the style, Keep both, Skip, with what would change", len(ch) == 1
      and [ch[0].itemText(i) for i in range(3)] == ["Update the style", "Keep both", "Skip"] and flags == ["Size: 10 pt to 12 pt"], flags)
check("the two ways are offered before anything changes, starting on Only what differs", [dlg.mode.itemText(i) for i in range(2)] == ["Only what differs", "Everything the document has"]
      and dlg.mode.currentData() == SH.MERGE and "keeps everything else" in dlg.mode_say.text())
check("Bring in does not wait", dlg.b_go.isEnabled() and "still need" not in dlg.n_lab.text(), dlg.n_lab.text())
ch[0].setCurrentIndex(ch[0].findData("skip")); app.processEvents()
check("Skip is counted at the foot", dlg.b_go.isEnabled() and "1 skipped" in dlg.n_lab.text(), dlg.n_lab.text())
c = dlg.go()
check("Skip: the file's Body is left out; the style stays", c.get("skipped") == 1 and [x["id"] for x in SO.held(lib, rfp["id"], SO.fam(b_rfp))] == [b_rfp["id"]]
      and not any(lib.values(i).get("size") == 12 for i in lib.items if i["kind"] == "style"))
r = SO.against(lib, [st("Body", 12)], rfp["id"]); r[0]["choice"] = "both"
c = SL.bring_in(lib, r, path, set_of={"Body": rfp["id"]})
names = sorted(lib.base_of(lib.get(i)) for i in lib.kit(rfp["id"])["items"])
b2 = next(i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Body 2")
check("Keep both: the file's comes in beside the set's under a numbered name", c.get("both") == 1 and names.count("Body") == 1 and "Body 2" in names
      and lib.values(b2)["size"] == 12 and lib.values(SO.held(lib, rfp["id"], SO.fam(b_rfp))[0])["size"] == 10, names)
check("... no set holds two styles of the same name", all(len(set(n)) == len(n) for n in ([lib.base_of(lib.get(i)) for i in k["items"]] for k in SL.sets(lib))))
page.pick_set(rfp["id"])
check("... and no row carries a v switch", not tabs(page))
r = SO.against(lib, [st("Body", 13)], rfp["id"]); r[0]["choice"] = "both"
SL.bring_in(lib, r, path, set_of={"Body": rfp["id"]})
check("a second one kept beside takes the next number", "Body 3" in [lib.base_of(lib.get(i)) for i in lib.kit(rfp["id"])["items"]])
r = SO.against(lib, [st("Body", 14)], rfi["id"])
SL.bring_in(lib, r, path, set_of={"Body": rfi["id"]})
now = SO.held(lib, rfi["id"], SO.fam(b_rfp))
check("Update the style: Body's latest is the file's, for both sets", len(now) == 1 and lib.values(now[0])["size"] == 14 and lib.values(SO.held(lib, rfp["id"], SO.fam(b_rfp))[0])["size"] == 14)
r = SO.against(lib, [st("Body", 15)], rfi["id"]); r[0]["choice"] = "skip"
check("a skipped row is never brought in", SL.bring_in(lib, r, path, set_of={"Body": rfi["id"]}).get("skipped") == 1
      and lib.values(SO.held(lib, rfi["id"], SO.fam(b_rfp))[0])["size"] == 14)
SO.retarget(lib, r2 := SO.against(lib, [st("Body", 9.5)], None), rfi["id"])
check("picking the set in the dialog judges the rows against it", r2[0]["clash"] is not None and r2[0]["choice"] == "replace")
# everything the document has, against only what differs (ST25)
tabbed = lib.latest(now[0]["id"]); tv = dict(lib.values(tabbed), tabs=[[36.0, "left", "none"]])
tb = SH._on_top(lib, tabbed, tv, note="a tab of its own"); SH._move(lib, tabbed["family"], tb["id"])
doc = SO.against(lib, [st("Body", 16)], rfi["id"])[0]
check("Only what differs plans the size alone; Everything the document has also says the tab goes",
      SH.plan(lib, doc, SH.MERGE) == [("Size", "14 pt", "16 pt")] and ("Tabs", "0.5 left", "none") in SH.plan(lib, doc, SH.REPLACE), SH.plan(lib, doc, SH.REPLACE))
SL.bring_in(lib, [doc], path, set_of={"Body": rfi["id"]}, mode=SH.MERGE)
top = lib.latest(tb["id"])
check("Only what differs: the size is the document's and the tab stays", lib.values(top)["size"] == 16 and lib.values(top).get("tabs") == [[36.0, "left", "none"]])
doc = SO.against(lib, [st("Body", 17)], rfi["id"])[0]
SL.bring_in(lib, [doc], path, set_of={"Body": rfi["id"]}, mode=SH.REPLACE)
top = lib.latest(tb["id"])
check("Everything the document has: the style is the document's, and the tab is gone", lib.values(top)["size"] == 17 and not lib.values(top).get("tabs")
      and SH.history(lib, top["id"])[0]["note"] == "Brought in from Osprey.docx: everything the document has")
now = SO.held(lib, rfi["id"], SO.fam(b_rfp))
from skqt import styleedit as SE2
check("a copy cannot take a name the library has", SE2.duplicate(page, b_rfp["id"], "Body 2") is None)

# 4.35.0 (ST24): one style, one history. A change made inside a set is the style's new Latest for every set that uses it
cap_id = caps[0]["id"]
page.pick_set(rfi["id"])
from skqt import styleedit as SE
new = SE.review(page, cap_id, {"size": 8})
check("changing a shared style inside a set changes it for every set that uses it", new is not None and SO.used_in(lib, new["id"]) == ["RFP", "RFI"] and SO.used_in(lib, cap_id) == [], host.said[-1])
check("... the toast names the sets", "changed for RFP, RFI" in host.said[-1], host.said[-1])
check("... and no set is left on the earlier one", SO.newer(lib, rfp["id"]) == [] and SO.newer(lib, rfi["id"]) == [])
dlg = SE.StyleEdit(page, lib.get(now[0]["id"]), lib.values(now[0]))
check("a style only this set uses offers no choice of sets", dlg.scope is None)
page.pick_set(rfp["id"])
quote = next(i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == "Quote")
SL.add_to_set(lib, rfi["id"], [quote["id"]])
dlg = SE.StyleEdit(page, quote, lib.values(quote))
from PySide6.QtWidgets import QLabel
said = " ".join(x.text() for x in dlg.findChildren(QLabel))
check("a style two sets use: the form offers no choice and names the sets that get the change (4.35.0)", dlg.scope is None and "RFP, RFI get the change" in said
      and "Duplicate..." in said, said)
new = SE.review(page, quote["id"], {"size": 13}, every=True)
check("Every set that uses it: both move", SO.used_in(lib, new["id"]) == ["RFP", "RFI"] and SO.used_in(lib, quote["id"]) == [])
page.pick_set(None)
ids = [page.rows.item(i).data(0x0100) for i in range(page.rows.count())]
check("a version no set uses is off the rows, and reached from the row's Earlier versions", quote["id"] not in ids and any(x["id"] == quote["id"] for x in page.earlier.get(new["id"], [])))
n3 = SE.review(page, new["id"], {"size": 15})
check("a change saved from Every style is the Latest for every set that uses the style (4.35.0)", SO.used_in(lib, n3["id"]) == ["RFP", "RFI"] and SO.newer(lib, rfp["id"]) == [])

# what the set is used for
page.pick_set(rfp["id"]); page.used_for("RFP")
check("a set carries what it is used for, shown under its name", SL.get_set(lib, rfp["id"]).get("used_for") == "RFP" and any("\nRFP" in page.sets.item(i).text() for i in range(page.sets.count())))
lib2 = TL.Library(d)
check("it is kept with the set, and a library saved before opens the same", lib2.kit(rfp["id"]).get("used_for") == "RFP" and len(lib2.kit(rfp["id"])["items"]) == len(lib.kit(rfp["id"])["items"]))
n = sum(checks)
print(f"QT STYLEOWN 4302 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
