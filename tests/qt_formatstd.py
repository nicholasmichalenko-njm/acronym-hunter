"""3.49.0 Formatting Standards, offscreen: the first library screen. The standards become items the first time it opens;
categories with counts; an item's every value with where it comes from; Save changes, Save as a new version, effort
types, status, compare, Put in a standard; Import from a Word file lands items in their categories and Undo takes them
back. And the two import failures of 3.44 to 3.48 cannot happen again: an import never starts Word, and a second
measuring never drops the first while it runs. Fictional content."""
import os, shutil, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import templatelib as TL, libcats as LC, prodrules as PRL, prodtemplate as PT
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
d = PRL.load(cfg)
d["company"]["style_defs"]["Body Text"] = {"type": "paragraph", "font": "Arial", "size": 11}
d["company"]["style_defs"]["Heading 1"] = {"type": "paragraph", "font": "Arial", "size": 14, "bold": True, "based_on": "Body Text"}
d["types"][0]["style_defs"] = {"Body Text": {"size": 12}}
PRL.save(cfg, d)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("Formatting Standards is first under Production", [k for g, it in RAIL if g == "Production" for k, _l in it][0] == "formatstd")
w.go("formatstd"); app.processEvents()
fp = w.formatstd_page
check("the first time it opens, the standards become library items", fp.converted and fp.converted["new"] > 5 and "library items" in fp.note.text())
cats = [fp.cats.item(r).text() for r in range(fp.cats.count())]
check("the categories, each with its count", [c.split(" (")[0] for c in cats] == [t for _k, t, _ks in LC.CATEGORIES["formatting"]]
      and any(c.startswith("Paragraph styles (") and not c.endswith("(0)") for c in cats), cats)
fp.select_category("para_styles"); app.processEvents()
names = [fp.t.item(r, 0).text() for r in range(fp.t.rowCount())]
check("a category lists its items with effort types, status, version and where each came from",
      any(n.startswith("Heading 1") for n in names) and fp.t.item(0, 1).text() == "Every effort type" and fp.t.item(0, 2).text() == "Approved"
      and fp.t.item(0, 4).text(), names)
h1 = next(i for i in fp.lib.items if i["kind"] == "style" and fp.lib.base_of(i) == "Heading 1")
fp.select(h1["id"]); app.processEvents()
se = fp.editor.style_ed
check("a style shows every property with where it comes from", se.isVisibleTo(fp) and se.where("font") == "From Body Text"
      and se.where("size") == "Set here" and "Body Text" in se.chain_lab.text(), (se.where("font"), se.where("size")))
check("the picture shows the selected style", fp.picture.it and fp.picture.it["name"] == "Heading 1" and not fp.picture.grab().isNull())
se.reset("size"); app.processEvents()
check("Reset puts the base style's value back, and Save becomes possible", se.values["size"] == 11 and se.where("size") == "From Body Text"
      and fp.save_btn.isEnabled())
fp.save_changes(); app.processEvents()
check("Save changes keeps the edit in this version", TL.Library(cfg).values(TL.Library(cfg).get(h1["id"]))["size"] == 11)
fp.select(h1["id"]); se = fp.editor.style_ed
w_size = se.widgets["size"][0]; w_size.setText("16"); w_size.editingFinished.emit(); app.processEvents()
new = fp.save_version(label="Kestrel 16 pt")
check("Save as a new version: the next version, Draft, labelled; the first stays", new and new["version"] == 2 and new["status"] == "draft"
      and TL.Library(cfg).values(TL.Library(cfg).get(h1["id"]))["size"] == 11 and fp.lib.values(new)["size"] == 16)
rows = fp.compare(run=False)
check("Compare: the selected item and its previous version", any(k == "size" for k, _a, _b in rows), rows)
n = fp.tag_effort_types(["rfi"])
check("Effort types...: the item is for that effort type only", n == 1 and LC.effort_types(fp.lib.get(new["id"])) == ["rfi"])
fp.et_box.setCurrentIndex(fp.et_box.findData("rfp")); app.processEvents()
check("the Effort type box hides items not for it", new["id"] not in [fp.t.item(r, 0).data(0x0100) for r in range(fp.t.rowCount())])
fp.et_box.setCurrentIndex(0); app.processEvents(); fp.select(new["id"])
fp.set_status("approved")
check("Status: Approved", LC.status(TL.Library(cfg).get(new["id"])) == "approved")
fp.set_status("retired"); app.processEvents()
check("a Retired item is not listed unless asked for", new["id"] not in [fp.t.item(r, 0).data(0x0100) for r in range(fp.t.rowCount())])
fp.st_box.setCurrentIndex(fp.st_box.findData("retired")); app.processEvents()
check("Status Retired lists it", [fp.t.item(r, 0).data(0x0100) for r in range(fp.t.rowCount())] == [new["id"]])
fp.st_box.setCurrentIndex(0); app.processEvents()
pg = next(i for i in fp.lib.items if i["kind"] == "page_setup")
fp.select(pg["id"]); app.processEvents()
te = fp.editor.tree_ed
check("anything else shows every value as a tree", te.isVisibleTo(fp) and te.topLevelItemCount() > 2)
top_key = next(k for k, v in fp.lib.values(pg).items() if isinstance(v, (int, float)) and not isinstance(v, bool))
te.edit_path((top_key,), "1.25"); app.processEvents()
check("a plain value edits in place and Save keeps it", fp.save_btn.isEnabled() and fp.save_changes()
      and TL.Library(cfg).values(TL.Library(cfg).get(pg["id"]))[top_key] == 1.25)
said = fp.put_in("etype:" + PRL.load(cfg)["effort_types"][0]["id"])
check("Put in a standard carries the item into an effort type", said and PRL.load(cfg)["effort_types"][0].get("page_setups"), said)

# ---- import from a Word file: into the categories, all at once, Undo
std = PRL.for_effort(tempfile.mkdtemp()); std["variables"]["marking"] = "Kestrel restriction"
SRC = os.path.join(tmp, "Kestrel Volume.dotx")
shutil.copyfile(PT.make(std, tempfile.mkdtemp(), "").copy, SRC)
before = len(TL.Library(cfg).items)
ib = fp.import_file(SRC, run=False)
check("the import opens on this library, without Use here", ib.tree.currentItem().data(0, 0x0100) == "lib:formatting" and not ib.use_here.isVisibleTo(ib))
check("an import never measures anything (Word is never started)", not hasattr(ib, "measure_kept") and not hasattr(ib, "qp_ids"))
ib.ets.set(["rfp"])
got = ib.take(); fp.library_changed(); app.processEvents()
lib = TL.Library(cfg)
added = ib.report["added"] if ib.report else []
check("Take the ticked: new items land in their categories, Draft, for the effort type chosen", added and len(lib.items) == before + len(added) + len(ib.report["versions"])
      and all(LC.status(lib.get(i)) == "draft" and LC.effort_types(lib.get(i)) == ["rfp"] for i in added), (ib.note.text(), len(lib.items), before, len(added)))
check("the screen shows them at once", sum(int(fp.cats.item(r).text().split("(")[-1].rstrip(")")) for r in range(fp.cats.count())) >= 1)
ib.reject()
fp.fill_more()
undo_menu = next(a.menu() for a in fp.more_menu.actions() if a.menu())
check("More > Undo an import lists it", undo_menu.actions() and "Kestrel Volume.dotx" in undo_menu.actions()[0].text())
n = fp.undo_import(ib.report["id"])
check("Undo an import takes its items out", n == len(added) + len(ib.report["versions"]) and len(TL.Library(cfg).items) == before)
rep = fp.convert_again()
check("Bring in my standards again adds only what changed", rep is not None and rep["new"] == 0)

# ---- the crash after an import, reproduced: a second measuring while the first runs
from skqt import qpjobs
gate = threading.Event()
qp = TL.Library(cfg); item, _s = qp.add("quickpart", "Kestrel Callout", {"entry": "Kestrel Callout", "category": "05 Callouts", "source": "x.dotx"})
done = []
j1 = qpjobs.start(cfg, [item["id"]], after=done.append, fn=lambda _p, _s: (gate.wait(10), {item["id"]: 3})[1])
j2 = qpjobs.start(cfg, [item["id"]], after=done.append, fn=lambda _p, _s: {item["id"]: 9})
check("a second measuring while one runs is refused, and the first keeps running", j1 is not None and j2 is None and j1 in qpjobs.RUNNING
      and j1.isRunning() and "already" in qpjobs.why_not())
TL.Library(cfg).add("style", "Kestrel kept meanwhile", {"type": "paragraph", "size": 10})
gate.set()
t0 = time.time()
while (qpjobs.RUNNING or not done) and time.time() - t0 < 10:
    app.processEvents(); time.sleep(0.02)
lib = TL.Library(cfg)
check("the pages are kept by the window, and nothing kept meanwhile is lost", lib.get(item["id"]).get("pages") == 3
      and any(i["name"] == "Kestrel kept meanwhile" for i in lib.items) and done and not qpjobs.RUNNING)

w.close()
n = sum(checks)
print(f"QT FORMATTING STANDARDS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
