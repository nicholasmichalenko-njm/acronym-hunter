"""2.83.0 the document library in Qt, offscreen: Add a folder reads every document in it and its subfolders in the
background (a progress bar; Stop adds nothing), suggests each file's category from its folders (customer documents,
bidders library, Q&A, ours), its role and its tags (every folder name), and one review table sets many rows at once;
customer documents go to the customer documents folder and the rest are copied into the effort; the categories and
folders tree, search across names, tags and text, roles confirmed with who and why (many at once), a category of one's
own, a missing original reported; Read RFP lists only customer documents and ticks the ones that build the matrix."""
import os, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, docversions as DV, docintake as DI, effortrec as R
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.librarypage import IntakeDialog
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
IN = os.path.join(tmp, "Heron intake")
TEXT = {"Section L Instructions.docx": "The Offeror shall describe the thermal design in five pages.",
        "Attachment J-1 ICD.pdf": "Radiator panels shall reject 450 W at 40 C.",
        "MIL-STD-1540E.pdf": "Thermal vacuum cycling per this standard.",
        "QA Round 1.xlsx": "Q: Is the page limit firm? A: Yes.",
        "Win themes.docx": "Our flight-proven radiator lowers risk."}
for rel, name in (("Customer", "Section L Instructions.docx"), ("Customer/Attachments", "Attachment J-1 ICD.pdf"),
                  ("Bidders Library/Standards", "MIL-STD-1540E.pdf"), ("Q&A/Round 1", "QA Round 1.xlsx"), ("Proposal drafts", "Win themes.docx")):
    os.makedirs(os.path.join(IN, rel), exist_ok=True)
    open(os.path.join(IN, rel, name), "wb").write(name.encode() * 20)
gate = threading.Event(); slow = {"on": False}


def reader(p):
    if slow["on"]:
        gate.wait(20)
    return [{"x": TEXT[os.path.basename(p)], "l": "1", "s": "", "t": ""}]


app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
w.go("library"); app.processEvents()
pg = w.library_page
check("an empty library says how to fill it", pg.empty.isVisible() and pg.p_docs.text() == "0 documents")


def wait(cond, secs=30):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


# Stop while reading
slow["on"] = True; gate.clear()
pg.add_folder(IN, reader=reader, choices={})
app.processEvents()
check("reading runs in the background with a progress bar; the buttons wait", pg.panel.state == "running" and not pg.b_folder.isEnabled())
pg.panel.stop_btn.click(); gate.set()
wait(lambda: pg.worker is None)
check("Stop: nothing added", pg.panel.state == "stopped" and DV.Library(ws.p("documents")).load().all == [])
# the review table, many rows at once
slow["on"] = False
lib = DV.Library(ws.p("documents")).load()
found = DI.walk(IN)
plan = DI.plan(lib, [p for p, _r in found], reader, folders=dict(found))
cats = {os.path.basename(e["path"]): e["category"] for e in plan}
check("categories suggested from the folders", cats == {"Section L Instructions.docx": "customer", "Attachment J-1 ICD.pdf": "customer",
                                                      "MIL-STD-1540E.pdf": "bidders", "QA Round 1.xlsx": "qa", "Win themes.docx": "ours"}, cats)
tags = {os.path.basename(e["path"]): e["tags"] for e in plan}
check("every folder name is a tag", tags["MIL-STD-1540E.pdf"] == ["Heron intake", "Bidders Library", "Standards"], tags["MIL-STD-1540E.pdf"])
roles = {os.path.basename(e["path"]): e["role"] for e in plan}
check("roles from category and type", roles["Section L Instructions.docx"] == "matrix" and roles["Attachment J-1 ICD.pdf"] == "context"
      and roles["MIL-STD-1540E.pdf"] == "reference" and roles["QA Round 1.xlsx"] == "context", roles)
dlg = IntakeDialog(w, plan, lib)
names = [os.path.basename(e["path"]) for e in plan]
r_std, r_win = names.index("MIL-STD-1540E.pdf"), names.index("Win themes.docx")
check("the table: one row per file, customer rows ask for an initial", dlg.table.rowCount() == 5
      and dlg.rows[names.index("Section L Instructions.docx")]["ini"].isEnabled() and not dlg.rows[r_std]["ini"].isEnabled())
dlg.set_rows(role="context", rows=[r_std, r_win])
check("Set many rows at once", dlg.rows[r_std]["role"].currentData() == "context" and dlg.rows[r_win]["role"].currentData() == "context")
dlg.set_rows(skip=True, rows=[r_win])
res = dlg.result_plan()
check("skipped rows are not added; the rest keep their choices", res[r_win]["choice"] == "skip" and res[r_std]["role"] == "context"
      and dlg.count.text() == "4 to add")
# add a folder, through the page
pg.add_folder(IN, reader=reader, choices={"MIL-STD-1540E.pdf": {"role": "reference"}})
wait(lambda: pg.worker is None and pg.panel.state == "done")
lib = DV.Library(ws.p("documents")).load()
by = {d["name"]: d for d in lib.all}
check("five documents in four categories", len(lib.all) == 5 and lib.counts_by_category()["customer"] == 2 and lib.counts_by_category()["bidders"] == 1, list(by))
check("customer documents went to the customer documents folder", sorted(os.listdir(CD)) == ["Attachment J-1 ICD.pdf", "Section L Instructions.docx"])
std = by["MIL-STD-1540E"]
p_std = lib.path_of(std["versions"][0])
check("the rest are copied into the effort, by category and folder", os.path.isfile(p_std) and
      os.path.normpath(p_std).endswith(os.path.normpath("library/bidders/Heron intake/Bidders Library/Standards/MIL-STD-1540E.pdf")), p_std)
check("the done panel says what went where", "Bidders library" in pg.panel.detail.text() and "added" in pg.panel.detail.text(), pg.panel.detail.text())
tl = [e["text"] for e in R.Record(ws.root).events()]
check("the effort record has the paper trail", any(t.startswith("Library:") for t in tl) and any("Section L Instructions added" in t for t in tl), tl[:4])
check("adding the same folder again adds nothing", DI.plan(lib, [p for p, _r in found], reader, folders=dict(found))[0]["dup"])
# the page
check("the tree: every category with its count, and the folders", pg.tree.topLevelItemCount() == 5
      and pg.tree.topLevelItem(2).text(0) == "Bidders library" and pg.tree.topLevelItem(2).text(1) == "1" and pg.tree.topLevelItem(2).childCount() == 1)
pg.pick_place("bidders", "")
check("a category shows its documents", pg.table.rowCount() == 1 and pg.table.item(0, 0).text() == "MIL-STD-1540E")
pg.pick_place("all", "")
pg.search.setText("radiator"); pg.fill()
got = sorted(pg.table.item(r, 0).text() for r in range(pg.table.rowCount()))
check("search finds the text in any document", got == ["Attachment J-1 ICD (J)", "Win themes"], got)
pg.select(by["Win themes"]["id"]); pg.show_doc()
check("with the sentence it found", pg.d_hits.isVisible() and "radiator" in pg.d_hits.item(0).text().lower())
pg.search.clear(); pg.fill()
check("roles to confirm are counted", "to confirm" in pg.p_und.text(), pg.p_und.text())
ids = [by["MIL-STD-1540E"]["id"], by["Win themes"]["id"]]
n = pg.set_role("context", "Thermal background for writers", ids=ids)
lib = DV.Library(ws.p("documents")).load()
check("a role for many at once, with who and why", n == 2 and all(lib.doc(i)["role"] == "context" and lib.doc(i)["role_by"]["why"] == "Thermal background for writers"
                                                                  and not lib.doc(i)["role_by"]["suggested"] for i in ids))
key = pg.new_category("Competitor intel")
check("a category of one's own", key and pg.tree.topLevelItemCount() == 6)
pg.select(by["Win themes"]["id"]); pg.show_doc()
pg.set_category(key, "Kestrel")
check("moving a document to it, with a folder", DV.Library(ws.p("documents")).load().doc(by["Win themes"]["id"])["category"] == key)
os.remove(p_std); pg.refresh()
check("a missing original is reported", "1 original(s) not here" in pg.p_miss.text(), pg.p_miss.text())
# Read RFP sees only customer documents, the matrix ones ticked
w.go("read"); app.processEvents()
rows = {r.text(0): (r.isChecked(), r.text(3)) for r in w.read_page.boxes}
check("Read RFP: only customer documents, the ones that build the matrix ticked", rows == {"Section L Instructions": (True, "Builds the matrix"),
                                                                                       "Attachment J-1 ICD": (False, "Context")}, rows)
w.go("docs"); app.processEvents()
check("Customer versions, Requirements and Compare see only customer documents",
      [d["name"] for d in w.docs_page.ctx.lib.docs] == ["Section L Instructions", "Attachment J-1 ICD"] and w.docs_page.tree.topLevelItemCount() == 2)
# drag and drop: a folder and a file together
extra = os.path.join(tmp, "dropped"); os.makedirs(os.path.join(extra, "Bidders Library")); 
open(os.path.join(extra, "Bidders Library", "NASA-STD-5001.pdf"), "wb").write(b"nasa" * 30)
lone = os.path.join(tmp, "Win themes.docx"); open(lone, "wb").write(b"win v2" * 30)
TEXT["NASA-STD-5001.pdf"] = "Structural design factors of safety."
w.go("library"); app.processEvents()
pg.add_dropped([os.path.join(extra, "Bidders Library"), lone], reader=reader, choices={})
wait(lambda: pg.worker is None and pg.panel.state in ("done", "failed"))
lib = DV.Library(ws.p("documents")).load()
check("dropping a folder and a file adds both", any(d["name"] == "NASA-STD-5001" and d["category"] == "bidders" for d in lib.all)
      and pg.panel.state == "done", pg.panel.detail.text())

w.go("dashboard"); app.processEvents()
check("the dashboard counts library roles to confirm", w.dash_page.tiles["library"].value.text() == str(len(DV.Library(ws.p("documents")).load().undecided())))

# a package: all documents, or customer documents and Q&A only, and it still works
import effortpkg as P, zipfile
QM = __import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox
pk_all = w.record_page.save_package(os.path.join(tmp, "all.skpkg"))
pk_c = w.record_page.save_package(os.path.join(tmp, "cust.skpkg"), library="customer")
na = zipfile.ZipFile(pk_all["path"]).namelist(); nc = zipfile.ZipFile(pk_c["path"]).namelist()
check("All documents: every original goes", any("library/ours" in a or "library/qa" in a for a in na) and pk_all["has"]["library"] == "all")
check("Customer and Q&A only: the Q&A originals go, the others stay behind", any("data/library/qa/" in a for a in nc)
      and not any("data/library/c_" in a or "data/library/ours/" in a for a in nc) and pk_c["has"]["library"] == "customer")
check("and every document's record and text still go", "data/documents/index.json" in nc
      and all(f"data/documents/{d['versions'][0]['id']}.json" in nc for d in DV.Library(ws.p("documents")).load().all))
dest = os.path.join(tmp, "received"); os.makedirs(dest)
out = P.unpack(pk_c["path"], dest, W.data_dir_for)
L2 = DV.Library(os.path.join(out["data"], "documents")).load()
qa = next(d for d in L2.all if d["category"] == "qa"); win = next(d for d in L2.all if d["name"] == "Win themes")
check("the receiver: Q&A original here, the left-out one marked, still searchable", L2.has_original(qa["versions"][0])
      and not L2.has_original(win["versions"][0]) and L2.search("radiator") and len(L2.all) == 6, len(L2.all))
w.close()
n = sum(checks)
print(f"QT LIBRARY PASS ({n}/{len(checks)})" if n == len(checks) else f"QT LIBRARY FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
