"""4.83.0 offscreen (steps I1 and D3; Nicholas 2026-11-27 09:02 "Go"): Documents > Add is "Add documents" with Purpose
first; Version replaces What it is, the same file is said and cannot be changed, Skip is gone and a row's x takes it out;
Initial and Type only for a Customer document; a file given Form to fill in, File to submit or Redline to return shows
Deliverable with the app's suggestion; adding attaches it by the document it became; the Shred bar's Add a file now
presets the row; the right-click Purpose asks which deliverable; taking the purpose off never removes a deliverable
made in Shred; a File We Submit given a document marks it File to submit, both ways."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import deliverables as DL, delivdoor as DD, delivmark as DM, delivnext as DN, docintake as DI, docreturn as DR
import docversions as DV, effort as E, effortrec as RR, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, usedfor as UF
from skqt.intakedialog import IntakeDialog, COLS, C_DELIV, C_INI, C_PURPOSE, C_VERSION
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def wait(page):
    t0 = time.time()
    while page.worker is not None and time.time() - t0 < 120:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
SAMP = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")
P = os.path.join(CD, "Heron_Section_L.pdf"); shutil.copy2(os.path.join(SAMP, "Section_L_print.pdf"), P)
lib0 = DV.Library(ws.p("documents")).load()
lib0.add(P, DI.read(P), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
rec0 = RR.Record(ws.root)
d_price = DL.add(rec0, "Pricing Form", kind="Form")                    # a Form We Fill In already on the list
DL.get(rec0, d_price)["shred_kind"] = "form"; DL.get(rec0, d_price)["from_shred"] = "s1"; rec0.save()
d_cert = DL.add(rec0, "Signed Certification", kind="Attachment")       # a File We Submit
DL.get(rec0, d_cert)["shred_kind"] = "file"; rec0.save()
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Heron"); app.processEvents()
w.go("library"); app.processEvents()
lp = w.library_page
lib = DV.Library(ws.p("documents")).load()

# the window
F_PRICE = os.path.join(tmp, "Heron Pricing Form.pdf"); shutil.copy2(os.path.join(SAMP, "SOW.pdf"), F_PRICE)
F_REF = os.path.join(tmp, "Heron Reference Notes.txt")
open(F_REF, "w", encoding="utf-8").write("Background notes for the team. Nothing in here is a requirement.\n")
plan = DI.plan(lib, [P, F_PRICE, F_REF], DI.read)
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
names = [os.path.basename(e["path"]) for e in plan]
r_same, r_price, r_ref = names.index("Heron_Section_L.pdf"), names.index("Heron Pricing Form.pdf"), names.index("Heron Reference Notes.txt")
check("the window is Add documents, with Purpose first (251)", dlg.windowTitle() == "Add documents"
      and COLS[:4] == ["File", "Purpose", "Deliverable", "Version"], (dlg.windowTitle(), COLS))
check("no paragraph above the table (251)", not [x for x in dlg.findChildren(type(dlg.count)) if len(x.text()) > 80], [x.text() for x in dlg.findChildren(type(dlg.count))])
check("Purpose offers decision 216's five words that a page reads", [dlg.rows[r_price]["role"].itemText(k) for k in range(dlg.rows[r_price]["role"].count())]
      == ["Customer document", "Reference", "Form to fill in", "File to submit", "Redline to return"])
what = dlg.rows[r_same]["what"]
check("the same file is said by the app and cannot be changed", what.count() == 1 and what.currentText().startswith("Same file, already added: Section L")
      and not what.isEnabled() and dlg.kind(r_same) == "skip", what.currentText())
choices = [dlg.rows[r_price]["what"].itemText(k) for k in range(dlg.rows[r_price]["what"].count())]
check("Version: New document first; Skip is gone", choices[0] == "New document" and not any("Skip" in c for c in choices), choices)
check("Deliverable is hidden while no row has a purpose that goes back", dlg.table.isColumnHidden(C_DELIV))
dlg.rows[r_price]["role"].setCurrentIndex(dlg.rows[r_price]["role"].findData("fill")); app.processEvents()
dl = dlg.rows[r_price]["deliv"]
check("Form to fill in shows Deliverable, the matching one suggested", not dlg.table.isColumnHidden(C_DELIV)
      and dl.currentData() == d_price and dl.currentText().endswith("(suggested)")
      and [dl.itemData(k) for k in range(dl.count())][-1] == DD.NEW, [dl.itemText(k) for k in range(dl.count())])
check("... and the list holds only that kind (no File We Submit)", d_cert not in [dl.itemData(k) for k in range(dl.count())])
check("Initial and Type only for a Customer document (187)", not dlg.rows[r_price]["cells"][C_INI].control.isVisibleTo(dlg))
dlg.rows[r_ref]["role"].setCurrentIndex(dlg.rows[r_ref]["role"].findData("matrix")); dlg.rows[r_ref]["cat"].setCurrentIndex(dlg.rows[r_ref]["cat"].findData("customer"))
dlg.rows[r_ref]["role"].setCurrentIndex(dlg.rows[r_ref]["role"].findData("matrix")); app.processEvents()
ini_on = dlg.rows[r_ref]["cells"][C_INI].control.isVisibleTo(dlg)
dlg.rows[r_ref]["role"].setCurrentIndex(dlg.rows[r_ref]["role"].findData("reference")); app.processEvents()
check("... a customer's file as Reference hides them; as Customer document shows them", ini_on and not dlg.rows[r_ref]["cells"][C_INI].control.isVisibleTo(dlg))
check("the count says what will be added", dlg.count.text() == "2 to add", dlg.count.text())
dlg.take_out([r_ref])
res = dlg.result_plan()
check("x takes a row out: it is not added", res[r_ref]["choice"] == "skip" and dlg.table.isRowHidden(r_ref) and dlg.count.text() == "1 to add", dlg.count.text())
check("the row keeps its deliverable", res[r_price]["role"] == "fill" and res[r_price]["deliverable"] == d_price)
check("a hidden initial is never asked: the check passes", DI.check(lib, res) == [], DI.check(lib, res))

# through the page: the file is attached to the deliverable picked, by the document it became
lp.add(paths=[F_PRICE], choices={"Heron Pricing Form.pdf": {"choice": "new", "role": "fill", "deliverable": d_price, "name": "Pricing form, blank",
                                                              "category": "customer", "initial": "PF", "type": "Other"}})
wait(lp)
lib = DV.Library(ws.p("documents")).load(); rec = RR.Record(ws.root)
dp = lib.doc_of_file("Heron Pricing Form.pdf")
check("added as Form to fill in, renamed: attached to Pricing Form, no second deliverable", dp is not None and lib.returns_of(dp) == ["fill"]
      and DL.get(rec, d_price)["doc_id"] == dp["id"] and len(DL.items(rec)) == 2, [(x["name"], x.get("doc_id")) for x in DL.items(rec)])
check("... and the row's action follows (Make a Word file of the PDF)", DN.next_of(DL.get(rec, d_price), lib)["action"] == "word")

# the Shred bar's Add a file now: the row comes in with its purpose and deliverable
F_CERT = os.path.join(tmp, "cert final v2.txt")
open(F_CERT, "w", encoding="utf-8").write("We certify that the information in this proposal is current.\n")
lp.add(paths=[F_CERT], preset={"cert final v2.txt": {"role": "submit", "deliverable": d_cert}},
       choices={"cert final v2.txt": {"category": "ours", "name": "Certification, signed"}})
wait(lp)
lib = DV.Library(ws.p("documents")).load(); rec = RR.Record(ws.root)
dc = next((x for x in lib.all if x.get("name") == "Certification, signed"), None)
check("a preset row: File to submit, attached as ours to Signed Certification, however it is named", dc is not None and lib.returns_of(dc) == ["submit"]
      and DL.get(rec, d_cert).get("our_doc") == dc["id"], (dc and lib.returns_of(dc), DL.get(rec, d_cert)))
check("... and the deliverable says File is here", DN.next_of(DL.get(rec, d_cert), lib)["file_line"].endswith("File is here"))

# the right-click Purpose
lp.refresh(); app.processEvents()
dsec = lib.doc_of_file("Heron_Section_L.pdf")
n = UF.toggle(lp, "redline", ids=[dsec["id"]], deliverable=DD.NEW)
lib = DV.Library(ws.p("documents")).load(); rec = RR.Record(ws.root)
t = DR.tile_of(rec, dsec["id"], "redline")
check("Purpose > Redline to return with New: a Redline We Return for it", n == 1 and "redline" in lib.returns_of(lib.doc(dsec["id"]))
      and t is not None and DN.kind_key(t) == "redline", t)
lp.lib = DV.Library(ws.p("documents")).load()
win = UF.which_deliverable(lp, lp.lib, lp.lib.doc(dp["id"]), "fill", run=False)
check("the question for one document: the suggestion first, New last", win.cb.itemData(0) == d_price and win.cb.itemData(win.cb.count() - 1) == DD.NEW,
      [win.cb.itemText(k) for k in range(win.cb.count())])
UF.toggle(lp, "fill", ids=[dp["id"]], answer=True)
lib = DV.Library(ws.p("documents")).load(); rec = RR.Record(ws.root)
check("taking Form to fill in off keeps the deliverable made in Shred; it lets go of the file", DL.get(rec, d_price) is not None
      and not DL.get(rec, d_price).get("doc_id") and "fill" not in lib.returns_of(lib.doc(dp["id"])), DL.get(rec, d_price))
lp.lib = lib
UF.toggle(lp, "redline", ids=[dsec["id"]], answer=True)
rec = RR.Record(ws.root)
check("... while one made by the purpose leaves with it, as before", DR.tile_of(rec, dsec["id"], "redline") is None)

# both ways: a File We Submit attached on Deliverables marks its document
lib = DV.Library(ws.p("documents")).load(); rec = RR.Record(ws.root)
d_other = DL.add(rec, "Past Performance Volume", kind="Attachment")
DN.attach(rec, lib, d_other, dsec["id"])
check("attaching a document to a File We Submit gives it File to submit", "submit" in DV.Library(ws.p("documents")).load().returns_of(lib.doc(dsec["id"])))
check("the older saved marks read in the new words", DV.RETURN_NAMES["redline"] == "Redline to return" and DV.RETURN_NAMES["fill"] == "Form to fill in"
      and DV.ROLE_NAMES["matrix"] == "Customer document")
check("Amendment 0002 names match their document", DV.stem("Heron RFP Amendment 0002.pdf") == DV.stem("Heron_RFP.pdf"))
w.close()
print(f"QT DOOR 4830 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
