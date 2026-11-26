"""4.81.0 (D2): a deliverable's file, and rows that act. After a mark in Shred > Deliverables the bar asks Its file (the
document the app suggests on Enter, another from Documents, Add a file now, None yet); each Deliverables row then says
what has to happen to it and does it: Make a Word file, Redline it, Open the form, Attach a file..., Open in Outline,
or "File is here". Fictional (Kestrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import deliverables as DL, delivnext as DN, docversions as DV, effortrec as RR
from skqt import shredselbar as SSB, delivpass as DP
pg = w.assign_page


def bar():
    SSB.refresh(pg); app.processEvents()
    return pg.sel_bar


def rec():
    return RR.Record(w.ws.root)


def lib():
    return DV.Library(w.ws.p("documents")).load()


def by_name(n):
    return next((d for d in DL.items(rec()) if d["name"] == n), None)


_r = rec(); _r.set_due("2027-04-02T17:00")
_lb = lib()
for _p, _n in zip(PDFS, ("Section L", "SOW")):                        # the customer's files, in Documents
    _lb.add(_p, [], doc_name=_n)
_lb.save()
docs = {d["name"]: d["id"] for d in lib().all}
sow = next((i for n, i in docs.items() if "sow" in n.lower()), None)
secl = next((i for n, i in docs.items() if "section" in n.lower()), None)
check("the customer's two documents are in Documents", sow and secl, docs)
w.go("delivpass"); app.processEvents()
rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]


def mark(it, key, name):
    pg.select(it["id"]); app.processEvents(); bar()
    QTest.keyClick(pg.view, key); app.processEvents(); f = bar()
    f.name_edit.setText(name)
    QTest.keyClick(f.name_edit, Qt.Key_Return); app.processEvents()
    return bar()


f = mark(rows[3], Qt.Key_4, "SOW")
check("a new row: the bar asks Its file, with the document the app suggests first (Enter)", f.file_sugg is not None
      and f.file_sugg.text().startswith("SOW") and f.file_sugg.text().endswith("Enter") and f.file_pick.text() == "A file in Documents..."
      and f.file_add.text() == "Add a file now..." and f.file_none.text() == "None yet" and not f.kinds, f.file_sugg and f.file_sugg.text())
QTest.keyClick(pg.view, Qt.Key_Return); app.processEvents(); f = bar()
d = by_name("SOW")
check("Enter attaches the suggestion: the customer's file of a redline, and the document is marked Redlined Deliverable",
      d["doc_id"] == sow and d["returns"] == "redline" and "redline" in lib().returns_of(lib().doc(sow)) and f.kinds and f.file_sugg is None, d)
f = mark(rows[4], Qt.Key_2, "Pricing Form")
check("no match in Documents: None yet takes Enter", f.file_sugg is None and f.file_none.text() == "None yet  Enter")
QTest.keyClick(pg.view, Qt.Key_Return); app.processEvents(); f = bar()
check("... and the row has no file; the bar is back to the four kinds", not DN.has_file(by_name("Pricing Form")) and f.kinds)
f = mark(rows[5], Qt.Key_1, "Technical Volume")
check("a document we write is asked too, with no suggestion", f.file_sugg is None and f.file_none is not None)
f.file_none.click(); app.processEvents()
cert = os.path.join(tmp, "Signed Certification.docx")
shutil.copy(os.path.join(A.BASE_DIR, "test_samples", next(n for n in sorted(os.listdir(os.path.join(A.BASE_DIR, "test_samples"))) if n.lower().endswith(".docx"))), cert)
f = mark(rows[7], Qt.Key_3, "Signed Certification")
check("Add a file now: the deliverable waits for the file by its name", DP.file_take(pg, "add", path=cert, intake=False) == "waiting"
      and by_name("Signed Certification")["file_wanted"] == "Signed Certification.docx")
check("a name already on the list attaches and is not asked again", (mark(rows[8], Qt.Key_2, "pricing form").file_sugg, pg._deliv_file) == (None, None))
w.go("deliverables"); app.processEvents()
dp = w.deliverables_page; dp.refresh(); app.processEvents()
cards = {c["name"]: c for c in dp.cards}
nx = {n: c["next"] for n, c in cards.items()}
check("each row names its kind the pass's way", nx["SOW"]["kind"] == "Redline We Return" and nx["Pricing Form"]["kind"] == "Form We Fill In"
      and nx["Technical Volume"]["kind"] == "Document We Write" and nx["Signed Certification"]["kind"] == "File We Submit", {n: x["kind"] for n, x in nx.items()})
check("one action each, worked out from the kind and the file", (nx["SOW"]["label"], nx["Pricing Form"]["label"], nx["Technical Volume"]["label"],
      nx["Signed Certification"]["label"]) == ("Make a Word file", "Attach a file...", "Open in Outline", "Attach a file..."), {n: x["label"] for n, x in nx.items()})
check("the line: Nothing yet, its file, the proposal's due date", DN.line(nx["SOW"]).startswith("Nothing yet  ·  Its file: ")
      and "Due 2027-04-02" in DN.line(nx["SOW"]) and "No file yet" in DN.line(nx["Pricing Form"]), DN.line(nx["SOW"]))
btns = {c: dp.board.cards[cards[c]["id"]].act for c in cards}
check("each card carries its one action as a button", btns["SOW"] is not None and btns["SOW"].text() == "Make a Word file"
      and btns["Technical Volume"].text() == "Open in Outline")
dp.view.setCurrentIndex(1); app.processEvents()
col = [dp.table.horizontalHeaderItem(i).text() for i in range(dp.table.columnCount())]
r = dp.ids.index(cards["Pricing Form"]["id"])
dp.table.selectRow(r); app.processEvents()
check("the List view has Its file and Next; the button under the list is the selected row's action", col[-2:] == ["Its file", "Next"]
      and dp.table.item(r, 7).text() == "No file yet" and dp.table.item(r, 8).text() == "Attach a file..."
      and dp.next_btn.isVisibleTo(dp) and dp.next_btn.text() == "Attach a file...", col)
dp.view.setCurrentIndex(0); app.processEvents()
lb = lib(); lb.add(cert, [], doc_name="Signed Certification"); lb.save()
dp.refresh(); app.processEvents()
c = next(x for x in dp.cards if x["name"] == "Signed Certification")
check("the waiting file is attached once it is in Documents: ours, and the row says File is here, with no button", by_name("Signed Certification").get("our_doc")
      and not by_name("Signed Certification").get("file_wanted") and c["next"]["action"] == "" and c["next"]["file_line"].endswith("File is here")
      and c["next"]["state"] == "In work" and dp.board.cards[c["id"]].act is None, c["next"])
did = by_name("Pricing Form")["id"]
check("Attach a file... picks from Documents: a form takes it as the customer's form", dp.act(did, choose=secl) == "attach"
      and by_name("Pricing Form")["doc_id"] == secl and by_name("Pricing Form")["returns"] == "fill")
c = next(x for x in dp.cards if x["id"] == did)
check("... a PDF form: Make a Word file", c["next"]["label"] == "Make a Word file", c["next"])
w.redline_page.to_look_at = lambda p: 0
out = dp.act(did)
c = next(x for x in dp.cards if x["id"] == did)
check("Make a Word file makes it in the Redlines folder, and the row then says Open the form, on that Word file", out == "word"
      and c["next"]["label"] == "Open the form" and c["next"]["path"].lower().endswith(".docx") and "Redlines" in c["next"]["path"]
      and c["next"]["state"] == "In work", c["next"])
check("Open the form opens it (no copy)", dp.act(did) == "form")
sid = by_name("SOW")["id"]
check("a redline's Make a Word file goes to Redlining's Prepare, on its row", dp.act(sid) == "word" and w.stack.currentWidget() is w.redline_page)
w.go("deliverables"); app.processEvents(); dp.refresh(); app.processEvents()
c = next(x for x in dp.cards if x["id"] == sid)
check("... then Redline it, on the Word copy", c["next"]["label"] == "Redline it" and dp.act(sid) == "redline", c["next"])
check("Open in Outline goes to the Outline", dp.act(by_name("Technical Volume")["id"]) == "outline" and w.stack.currentWidget() is w.outline_page)
w.go("deliverables"); app.processEvents(); dp.refresh(); dp.pick(did); app.processEvents()
names = [b.text() for b in dp.detail.findChildren(QPushButton)]
check("the panel beside the board leads with the same action; Prepare for Redline is that action now", names[:2] == ["Open the form", "Open its page"]
      and "Prepare for Redline" not in names, names)
print(f"{sum(checks)}/{len(checks)}")
if not all(checks):
    sys.exit(1)
print("ok qt_delivact4810")
