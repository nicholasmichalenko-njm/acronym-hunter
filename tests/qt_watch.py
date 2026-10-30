"""2.94.0 document types and watched folders, offscreen: Settings > Document types (your own types with initials,
numbered types, file name words; a renamed type keeps its documents; Other stays); the initial follows the type when
adding customer documents until you type your own; the effort's Customer Documents folder (subfolders too) and added
folders are watched: new files show in a strip with Add them... and Not these, a changed file comes up as a new version,
a document whose file is gone is reported until you find it, keep the record without it or mark it withdrawn; Library >
Watched folders lists and adds folders; a team pack carries the document types."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, effortrec as RR, docversions as DV, docintake as DI, doctypes as DT, teampack as TP, watch as WA, workspace as W
import office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from skqt.custdocs import AddDialog

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CDIR = os.path.join(EDIR, "Customer Documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
for f in os.listdir(RFP):
    shutil.copy2(os.path.join(RFP, f), CDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CDIR)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


# ---- document types
dc = w.settings_page.doctypes_card
check("Settings: Document types lists the built-in ones", dc.table.rowCount() == len(DT.BUILT_IN)
      and [dc.table.item(i, 0).text() for i in range(3)] == ["RFP", "Amendment", "SOW"])
other = next(i for i in range(dc.table.rowCount()) if dc.table.item(i, 0).text() == "Other")
dc.table.setCurrentCell(other, 0)
check("Other always stays", not dc.remove() and dc.table.rowCount() == len(DT.BUILT_IN))
qa = next(i for i in range(dc.table.rowCount()) if dc.table.item(i, 0).text() == "Q&A")
dc.table.item(qa, 0).setText("Questions and Answers")
i = dc.add_type("Pricing Instructions", "PI")
dc.table.item(i, 4).setText("pricing, cost volume")
j = dc.add_type("Industry Day", "ID"); dc.table.cellWidget(j, 2).box.setChecked(True)
check("Save keeps them", dc.save())
check("... the library uses them", "Pricing Instructions" in DV.DOC_TYPES and DV.TYPE_INITIAL["Pricing Instructions"] == "PI"
      and "Questions and Answers" in DV.DOC_TYPES and "Q&A" not in DV.DOC_TYPES and "Industry Day" in DV.NUMBERED)
check("file name words pick a type of your own", DV.guess_type("Kestrel_Cost_Volume_Instructions.pdf") == "Pricing Instructions"
      and DV.guess_type("Kestrel RFP.docx") == "RFP")
check("a renamed type keeps the old name as an alias", DV.type_of("Q&A") == "Questions and Answers")
lib0 = DV.Library(os.path.join(tmp, "libtest")).load()
check("a numbered type of your own counts up", lib0.suggest_initial("Industry Day") == "ID1" and lib0.suggest_initial("Pricing Instructions") == "PI")
dup = dc.add_type("Proposal Instructions", "PI"); dc.save()
check("two types sharing an initial are allowed, with a note", "share PI" in dc.note.text(), dc.note.text())
dc.table.setCurrentCell(next(i for i in range(dc.table.rowCount()) if dc.table.item(i, 0).text() == "Proposal Instructions"), 0); dc.remove(); dc.save()
check("problems are refused", DT.problems([{"name": "A", "initial": ""}, {"name": "B", "initial": "B"}, {"name": "b", "initial": "C"}])
      == ["A needs an initial (letters and digits, up to 6)", "b is listed twice"])

# ---- the initial follows the type
w.open_effort("Kestrel")
w.go("docs"); app.processEvents()
dp = w.docs_page
lib = dp.ctx.lib
paths = sorted(os.path.join(CDIR, f) for f in os.listdir(CDIR))
plan = DI.plan(lib, paths)
dlg = AddDialog(dp, plan, lib)
cb, _n, _l, ini, ty = dlg.rows[0]
ty.setCurrentText("Pricing Instructions")
check("picking a type fills in its initial", ini.text() == "PI", ini.text())
ty.setCurrentText("Section M")
check("... and follows the next type picked", ini.text() == "M", ini.text())
ini.setText("RM"); ini.textEdited.emit("RM")
ty.setCurrentText("SOW")
check("an initial you typed stays when the type changes", ini.text() == "RM")
ini.setText(""); ini.textEdited.emit("")
ty.setCurrentText("PWS")
check("emptying it hands it back to the type", ini.text() == "P")
dlg.deleteLater()
made = dp.add(paths, choices=[{}, {}])
check("the customer folder's files added", len(made) == 2)
d_ids = [d["id"] for d, _v in made]

# ---- the watched folders
check("nothing new at first", not WA.summary(w.watch_now()) and not w.watch_strip.isVisible())
os.makedirs(os.path.join(CDIR, "Amendments"))
amd = os.path.join(CDIR, "Amendments", "Kestrel Amendment 01.txt")
open(amd, "w").write("Amendment 01. The page limit for Volume I changes to 40 pages.")
f = w.watch_now()
if os.environ.get("SHOT_DIR"):
    app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "watch_strip.png"))
check("a new file in a subfolder of Customer Documents shows in the strip", [os.path.basename(p) for p, _c in f["new"]] == ["Kestrel Amendment 01.txt"]
      and w.watch_strip.isVisible() and w.watch_strip.add_btn.isVisible() and "1 new file(s)" in w.watch_strip.text.text(), w.watch_strip.text.text())
w.watch_set_aside()
check("Not these: the strip goes and the file is not offered again", not w.watch_strip.isVisible() and not w.watch_now()["new"])
time.sleep(1.1); open(amd, "w").write("Amendment 01, revised. The page limit for Volume I changes to 45 pages.")
f = w.watch_now()
check("... until it changes", [os.path.basename(p) for p, _c in f["new"]] == ["Kestrel Amendment 01.txt"])
w.watch_add(choices={})
wait(lambda: not w.library_page.running())
lib = DV.Library(w.ws.p("documents")).load()
check("Add them...: read and added from where it is, its folder as a tag", any(v.get("file") == "Kestrel Amendment 01.txt" for d in lib.all for v in d["versions"])
      and not os.path.exists(os.path.join(CDIR, "Kestrel Amendment 01.txt"))
      and any("Amendments" in d.get("tags", []) for d in lib.all), [(d["name"], d.get("tags")) for d in lib.all])
check("... and it is no longer new", not w.watch_now()["new"])
# a changed file: a new version
d0 = lib.doc(d_ids[0]); src = lib.path_of(d0["versions"][-1])
time.sleep(1.1)
if src.lower().endswith(".docx"):
    from test_docversions import amend
    tmpc = os.path.join(tmp, "changed.docx"); amend(src, tmpc, [("exceed 50 pages", "exceed 30 pages")]); shutil.copy2(tmpc, src)
else:
    open(src, "a").write("\nOne more sentence was added by the customer.")
f = w.watch_now()
check("the file a document was read from changed: shown as changed", [d["id"] for _p, d, _v in f["changed"]] == [d_ids[0]]
      and "1 changed file(s)" in w.watch_strip.text.text(), w.watch_strip.text.text())
pl = DI.plan(DV.Library(w.ws.p("documents")).load(), [src])
check("... offered as a new version of its document", pl[0]["choice"] == "version" and pl[0]["doc"] == d_ids[0], (pl[0]["choice"], pl[0].get("doc")))
w.watch_add(choices={})
wait(lambda: not w.library_page.running())
lib = DV.Library(w.ws.p("documents")).load()
check("Add them... adds it as the next version", len(lib.doc(d_ids[0])["versions"]) == 2 and not w.watch_now()["changed"])
# a missing file
gone = lib.path_of(lib.doc(d_ids[1])["versions"][-1])
os.remove(gone)
f = w.watch_now()
check("a document's file removed: reported in red, with Review missing", [d["id"] for d, _v, _p in f["missing"]] == [d_ids[1]]
      and w.watch_strip.miss_btn.isVisible() and "missing" in w.watch_strip.text.text())
md = w.watch_missing(run=False)
check("Review missing lists it with Find it, Keep without it, Withdrawn", md.t.rowCount() == 1 and md.t.item(0, 0).text() == lib.doc(d_ids[1])["name"])
moved = os.path.join(tmp, "moved_" + os.path.basename(gone))
open(moved, "w").write("not the same")
check("Find it: other contents are not taken as the file", md.find(d_ids[1], moved) is False)
check("Keep without it: the record stays, the check stops asking", md.keep(d_ids[1]) and not w.watch_now()["missing"])
md.deleteLater()
w.go("library"); w.library_page.refresh(); app.processEvents()
names = [w.library_page.table.item(r, 0).text() for r in range(w.library_page.table.rowCount())]
check("the Library says original missing", any("(original missing)" in n for n in names), names)
ev = RR.Record(w.ws.root).events()
check("it is on the timeline", any("record kept without it" in e["text"] for e in ev))
lib = DV.Library(w.ws.p("documents")).load()
lib.doc(d_ids[1])["versions"][-1].pop("missing_kept"); lib.save()
md = w.watch_missing(run=False) if w.watch_now()["missing"] else None
check("Withdrawn: the document stays, marked withdrawn, not building the matrix", md is not None and md.withdrawn(d_ids[1])
      and DV.Library(w.ws.p("documents")).load().doc(d_ids[1]).get("withdrawn") and not w.watch_now()["missing"])
md.deleteLater()
# Library > Watched folders
extra = os.path.join(tmp, "Bidders Library"); os.makedirs(os.path.join(extra, "Standards"))
open(os.path.join(extra, "Standards", "MIL-STD-1540E.txt"), "w").write("Test requirements for launch vehicles.")
fd = w.watch_folders(run=False)
check("Watched folders: Customer Documents always", fd.t.rowCount() == 1 and "always watched" in fd.t.item(0, 0).text())
fd.add(extra, "bidders")
check("+ Folder: watched, with where its new files go, and checked at once", fd.t.rowCount() == 2
      and [os.path.basename(p) for p, c in w.watch_found["new"]] == ["MIL-STD-1540E.txt"] and w.watch_found["new"][0][1] == "bidders")
fd.t.setCurrentCell(0, 0)
check("the Customer Documents folder cannot be removed", not fd.remove())
fd.t.setCurrentCell(1, 0)
check("Stop watching", fd.remove() and fd.t.rowCount() == 1)
fd.deleteLater()
# background check
w.watch_found = None
th = w.watch_start(force=True)
th.join(30); w.watch_tick()
check("the background check shows what it found", w.watch_found is not None)
# ---- formatting requirements and page-limited
w.go("home"); app.processEvents()
hp = w.home_page; bn = hp.banner
check("Effort Home: PAGE-LIMITED front and center when the documents set a limit", bn.pagelim.text().startswith("PAGE-LIMITED")
      and "50" in bn.pagelim.text() and "found" in bn.pagelim.toolTip(), bn.pagelim.text())
if os.environ.get("SHOT_DIR"):
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "home_fmt.png"))
    from PySide6.QtWidgets import QScrollArea
    sa = hp.findChild(QScrollArea)
    if sa: sa.ensureWidgetVisible(hp.fmt_card, 0, 0)
    app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "home_fmt2.png"))
check("the Formatting requirements card is on the proposal manager's Effort Home", "formatting" in hp.shown and hp.fmt_card.isVisibleTo(hp))
lines = {x["label"]: x for x in hp.fmt_now["lines"]}
check("each rule: required with what and where, or not specified", set(lines) >= {"Font", "Margins", "Page size", "Line spacing", "File format", "File naming"}
      and all((x["value"] and x["where"]) if x["required"] else not x["value"] for x in lines.values()), {k: (v["required"], v["value"]) for k, v in lines.items()})
from PySide6.QtWidgets import QLabel
texts = [l.text() for l in hp.fmt_card.findChildren(QLabel)]
check("... in words on the card", any(t.startswith("Required: ") for t in texts) or any(t == "Not specified in the documents" for t in texts), texts[:12])
k = hp.format_dialog(("Headers and footers", "Solicitation number in every header"))
check("+ Add: a rule of your own", k and any(x["label"] == "Headers and footers" and x["required"] for x in hp.fmt_now["lines"]))
hp.format_remove(k)
check("... and Remove", not any(x["label"] == "Headers and footers" for x in hp.fmt_now["lines"]))
bn.save_details({"page_limited": "no"})
check("Edit details: Not page-limited wins, and is on the timeline", bn.pagelim.text() == "Not page-limited" and "Set by the proposal manager" in bn.pagelim.toolTip()
      and any(e["text"] == "Page-limited: not page-limited" for e in RR.Record(w.ws.root).events()))
dlg = __import__("skqt.brandview", fromlist=["DetailsDialog"]).DetailsDialog(bn, bn.ident, bn.client, bn.solicitation)
check("the details dialog offers the three choices", [dlg.pagelim.itemText(i) for i in range(3)] == ["Decide from the documents", "Page-limited", "Not page-limited"]
      and dlg.values()["page_limited"] == "no")
dlg.deleteLater()
bn.save_details({"page_limited": ""})
import formatreq as FR
check("with nothing found and nothing set it never says not page-limited", FR.flag_text(FR.card([], "")) == "Page limits: none found yet")
import effortstate as ES, readable as RD
snap = ES.status_snapshot(ES.State(w.ws, w.effort_path, None), name="Kestrel")
check("the overview carries it", snap["formatting"]["flag"].startswith("PAGE-LIMITED") and snap["formatting"]["lines"])
files = RD.build(rec=RR.Record(w.ws.root), lib=DV.Library(w.ws.p("documents")).load())
check("the readable copy carries it", "Formatting requirements.csv" in files and files["Formatting requirements.csv"][1][0][2].startswith("PAGE-LIMITED"))
# team pack
pk = os.path.join(tmp, "team.zip")
TP.make(cfg, pk, ["doctypes"], name="Proposal Center")
cfgB = os.path.join(tmp, "pcB"); os.makedirs(cfgB)
info, data = TP.read(pk)
TP.install(cfgB, info, data)
check("a team pack carries the document types", any(t["name"] == "Pricing Instructions" for t in DT.load(cfgB)["types"]))
DT.apply(cfg)
n = sum(checks)
print(f"QT WATCH {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
