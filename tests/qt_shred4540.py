"""4.54.0 offscreen: one Shred, two views (UX decisions 5 and 62; Nicholas 2026-11-17 13:52: flat rows that sort). See it
as names On the page and As a table. The table is flat (one row per piece, no heading rows) with ID, Type, Section, Page,
Words and Piece; Page sorts by number and Section in natural order; the document's own order is the start; the three
filters; a suggestion shows its type with "?". A type set from Set type or by its letter is the same act as on the page
and Undo takes it back; Enter takes the suggestion and goes to the next row not shredded, and does nothing with no
suggestion; N goes to the next; two documents' pieces are refused. Switching keeps the place both ways; Open on the page
works without a double-click. Export > Draft compliance matrix... writes the rows shown in the order shown with an About
sheet, and never over a file read. Quick shred is gone (no page, role, tile or Ctrl+K line) and an old pin opens Shred;
Quick tools' Shred to setup asks for a home and lands the file in the effort picked. Fictional (Kestrel, Heron)."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import docversions as DV, effort as E, workspace as W, pdfmini, openpyxl
import roleaccess as RA, shredquick as SQ, shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
SUBJ = ["Integrated Master Schedule", "risk register", "staffing plan", "ground segment design", "test campaign",
        "quality program", "configuration control", "security plan", "transition plan", "training approach", "logistics support"]
SECL = os.path.join(tmp, "Section_L.pdf")
pdfmini.write(SECL, [[f"The Offeror shall describe its {s}.", f"Proposals shall include the {s} in Volume {'I' if k % 2 else 'II'}."]
                     for k, s in enumerate(SUBJ, 1)], size=9)                 # eleven pages: Page 10 and 11 sort after 9
SOW = os.path.join(tmp, "SOW.pdf")
pdfmini.write(SOW, [["The contractor shall deliver a monthly status report.", "The contractor shall maintain the ground station.",
                     "The Government intends to award a single contract."]], size=9)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def pump(n=3):
    for _ in range(n):
        app.processEvents(); time.sleep(0.01)


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


msgs = []
_status = w.status
w.status = lambda m, *a, **k: (msgs.append(m), _status(m, *a, **k))[1]
w.open_effort("Kestrel")
w.read_page.read([SECL, SOW], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
check("extracted: two documents", wait(lambda: w.review is not None and not w.read_page.running() and len(w.review.files()) == 2),
      w.review.files() if w.review else None)
from skqt import shredlist as SL, typechips as TC, toolshome as TH, helpcenter as HC
M = w.review.M
R = w.review
by = lambda s: next(it for it in M.items if s in (it.get("text") or ""))      # noqa: E731
done = lambda it: bool(ST._keys(it.get(ST.FIELD)) or it.get("decision"))      # noqa: E731
# pdfmini writes no headings: the Section L pieces get their sections here (page k is L.3.k), as the reader would give them
for it in M.items:
    if it.get("file") == "Section_L.pdf":
        it["section"], it["section_title"] = f"L.3.{it.get('page')}", SUBJ[int(it.get("page")) - 1].title()

# ---- the views
w.go("assign"); pump()
pg = w.assign_page
check("See it as: On the page and As a table", [b.text() for b in w.stepper.views.values()] == ["On the page", "As a table"]
      and list(w.stepper.views) == ["assign", "shredlist"])
w.stepper.see("shredlist"); pump()
lp = w.shredlist_page
ids = lambda: lp.ids()                                                          # noqa: E731
shown = lambda: [it["id"] for it in lp.rows]                                    # noqa: E731
row_of = lambda iid: shown().index(iid)                                         # noqa: E731
check("As a table is Shred's second view: the menu stays on Shred", w.stack.currentWidget() is lp and w.step_btns["assign"].isChecked()
      and w.page_title.text() == "Shred")
heads = [lp.t.horizontalHeaderItem(c).text() for c in range(lp.t.columnCount())]
check("six columns: ID, Type, Section, Page, Words, Piece", heads == ["ID", "Type", "Section", "Page", "Words", "Piece"], heads)
want = [it["id"] for it in M.items if it.get("header") != "Yes" and it.get("type") != "Heading"]
check("flat: one row per piece, in the document's own order, no heading rows", shown() == want and lp.t.rowCount() == len(want)
      and lp.t.rowCount() == len(SL.pieces(M)), (len(shown()), len(want)))
check("... the muted line says how much is shredded, with nothing about double-clicking", "shredded" in lp.say.text()
      and "ouble" not in lp.say.text(), lp.say.text())
r0 = row_of(by("risk register.")["id"])
check("... a row: its section in the customer's words, its page, its trigger word, its text", lp.t.item(r0, 2).text() == "L.3.2 Risk Register"
      and lp.t.item(r0, 3).text() == "2" and lp.t.item(r0, 4).text() == "shall" and "risk register" in lp.t.item(r0, 5).text(),
      [lp.t.item(r0, c).text() for c in range(6)])

# ---- a suggestion waiting
ims = by("describe its Integrated Master Schedule")
sug = TC.suggested(pg, ims)
c1 = lp.t.item(row_of(ims["id"]), 1)
check("a suggestion shows its type with ? in muted italic", sug and c1.text() == ST.load(cfg)[sug]["name"] + "?" and c1.font().italic()
      and c1.toolTip() == "Suggested. Not set yet.", (sug, c1.text()))

# ---- sorting
lp.sort_by(3); pump()
pages = [int(lp.t.item(r, 3).text()) for r in range(lp.t.rowCount())]
check("Page sorts by number (10 and 11 after 9)", pages == sorted(pages) and pages[-1] == 11 and pages.index(10) > pages.index(9), pages)
lp.sort_by(3); pump()
pages = [int(lp.t.item(r, 3).text()) for r in range(lp.t.rowCount())]
check("... again, the other way", pages == sorted(pages, reverse=True), pages)
lp.sort_by(2); pump()
secs = [lp.t.item(r, 2).text().split(" ")[0] for r in range(lp.t.rowCount()) if lp.t.item(r, 2).text()]
check("Section sorts in natural order (L.3.2 before L.3.10)", secs.index("L.3.2") < secs.index("L.3.10")
      and secs.index("L.3.9") < secs.index("L.3.11"), secs)
lp.sort_by(1); pump()
check("Type sorts", lp.t.rowCount() == len(want))
lp.sort_col, lp.desc = None, False; lp.fill(); pump()
check("... and the document's order is back", shown() == want)

# ---- the filters
lp.doc.setCurrentText("SOW.pdf"); pump()
check("filter: the document", lp.t.rowCount() == 3 and all(it.get("file") == "SOW.pdf" for it in lp.rows))
lp.doc.setCurrentText(SL.ALL); pump()

# ---- Set type: the same act as on the page; Undo
rep = by("monthly status report")
lp.select_ids([rep["id"]]); pump()
acts = lp.fill_type_menu()
check("Set type: a menu of the shown types, nothing ticked yet", set(acts) == {k for k in ST.KEYS if ST.load(cfg)[k].get("shown", True)}
      and not any(a.isChecked() for a in acts.values()))
acts["deliverable"].trigger(); pump()
rep = by("monthly status report")
check("Set type > Deliverable sets it on the piece", ST.has(rep, "deliverable") and ids() == [rep["id"]])
check("... the page shows the same piece selected, with the same type", pg.file == "SOW.pdf" and [x["id"] for x in pg.selected()] == [rep["id"]]
      and ST.has(R.item(rep["id"]), "deliverable"))
check("... the row says it", "Deliverable" in lp.t.item(row_of(rep["id"]), 1).text())
check("... and the menu ticks it", lp.fill_type_menu()["deliverable"].isChecked())
lp.kind.setCurrentIndex(lp.kind.findData("deliverable")); pump()
check("filter: the type", shown() == [rep["id"]])
lp.kind.setCurrentIndex(0); pump()
lp.only.setChecked(True); pump()
check("filter: Not shredded only", rep["id"] not in shown() and all(not done(it) for it in lp.rows) and lp.t.rowCount() == len(want) - 1)
lp.only.setChecked(False); pump()
lp.select_ids([rep["id"]]); pump()
check("the window's Undo on the table says what it puts back", bool(w.undo_text()), w.undo_text())
w.undo_here(); pump()
check("Ctrl+Z (the window's Undo) takes it back", not ST.has(R.item(rep["id"]), "deliverable") and not done(R.item(rep["id"])),
      R.item(rep["id"]).get(ST.FIELD))

# ---- a type's letter
stn = by("maintain the ground station")
lp.select_ids([stn["id"]]); pump()
QTest.keyClick(lp.t, Qt.Key_U); pump()
check("a type's letter (U, as the page reads it) sets the type and stays", ST.has(R.item(stn["id"]), "rule") and ids() == [stn["id"]]
      and lp.type_keys().get("U") == "rule")
w.undo_here(); pump()
check("... and Undo takes it back", not ST.has(R.item(stn["id"]), "rule"))

# ---- Enter
lp.sort_by(3); pump()                    # in the table's own order (by page)
rows = lp.rows
c = by("include the staffing plan")
at = row_of(c["id"])
nxt = next(it["id"] for it in rows[at + 1:] if not done(it))
lp.select_ids([c["id"]]); pump()
QTest.keyClick(lp.t, Qt.Key_Return); pump()
check("Enter takes the suggestion", done(R.item(c["id"])) and R.item(c["id"]).get("lm") == "L", R.item(c["id"]).get("decision"))
check("... and selects the next row not shredded in the table's order", ids() == [nxt], (ids(), nxt))
w.undo_here(); pump()
check("... Undo takes it back", not done(R.item(c["id"])))
nos = by("award a single contract")
check("the fixture has a piece with no suggestion", not TC.suggested(pg, nos) and not done(nos))
lp.select_ids([nos["id"]]); pump()
before = [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in M.items]
QTest.keyClick(lp.t, Qt.Key_Return); pump()
check("Enter with no suggestion changes nothing and stays", ids() == [nos["id"]]
      and before == [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in w.review.M.items])
lp.sort_col, lp.desc = None, False; lp.fill(); pump()

# ---- N
lp.select_ids([shown()[0]]); pump()
first_open = next(it["id"] for it in lp.rows[1:] if not done(it))
QTest.keyClick(lp.t, Qt.Key_N); pump()
check("N goes to the next row not shredded", ids() == [first_open], (ids(), first_open))
check("Take the suggestion is a button too (Enter)", lp.b_take.text() == "Take the suggestion" and lp.b_take.isVisibleTo(w))

# ---- two documents
lp.select_ids([ims["id"], stn["id"]]); pump()
msgs.clear()
before = [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in M.items]
got = lp.set_type("requirement")
check("pieces of two documents: refused with the sentence, nothing changed", got is None and "Select pieces of one document." in msgs
      and before == [(it["id"], it.get("decision"), it.get(ST.FIELD)) for it in M.items], msgs)

# ---- switching keeps the place
lp.select_ids([by("security plan.")["id"]]); pump()
w.stepper.see("assign"); pump()
check("table to page: the document opens with the table's piece selected", w.stack.currentWidget() is pg
      and [x["id"] for x in pg.selected()] == [by("security plan.")["id"]] and w.stepper.views["assign"].isChecked())
w.stepper.see("shredlist"); pump()
lp.doc.setCurrentText("SOW.pdf"); pump()
w.stepper.see("assign"); pump()
pg.select(by("training approach.")["id"]); pump()
w.stepper.see("shredlist"); pump()
check("page to table: the page's piece is selected, its document shown", ids() == [by("training approach.")["id"]]
      and lp.doc.currentText() == "Section_L.pdf", (ids(), lp.doc.currentText()))
lp.doc.setCurrentText(SL.ALL); pump()
lp.select_ids([rep["id"]]); pump()
lp.b_open.click(); pump()
check("Open on the page, with no double-click", lp.b_open.text() == "Open on the page" and w.stack.currentWidget() is pg
      and [x["id"] for x in pg.selected()] == [rep["id"]])
w.stepper.see("shredlist"); pump()

# ---- Export
check("Export holds Draft compliance matrix...", lp.bar.action("Draft compliance matrix...") is not None and lp.bar.b_export.isVisibleTo(w))
check("the bar holds five commands at most", len(lp.bar.visible_commands()) <= 5, [b.text() for b in lp.bar.visible_commands()])
lp.doc.setCurrentText("Section_L.pdf"); lp.sort_by(3); lp.sort_by(3); pump()
out = os.path.join(tmp, "Kestrel draft matrix.xlsx")
got = lp.export(out)
wb = openpyxl.load_workbook(out)
ws = wb["Requirements"]
hdr = [x.value for x in ws[1]]
got_ids = [ws.cell(r, 1).value for r in range(2, ws.max_row + 1)]
check("Export writes the rows shown, in the order shown", got == out and got_ids == shown() and len(got_ids) == 22, got_ids[:5])
check("... with the matrix's columns (Type, was Kind)", hdr == list(SQ.TABLE_COLUMNS) and hdr[1] == "Type", hdr)
about = {r[0]: r[1] for r in wb["About"].iter_rows(values_only=True)}
check("... and an About sheet: the documents, the date and time, the rows, the Production Datum", about.get("Documents") == "Section_L.pdf"
      and about.get("Rows") == 22 and len(str(about.get("Made"))) == 16 and about.get("Working from") == "No Production Datum installed", about)
src = R.M.path_of("Section_L.pdf")
size = os.path.getsize(src)
msgs.clear()
check("... never over a file the shred reads", src and lp.export(src) is None and os.path.getsize(src) == size and msgs, msgs)
check("shredquick's own export still writes Kind", SQ.COLUMNS[1] == "Kind")
lp.doc.setCurrentText(SL.ALL); lp.sort_col = None; lp.fill(); pump()

# ---- Quick shred is gone
check("shredreq is no page: not in the pages, the roles, Quick tools' tiles or the role pins", "shredreq" not in w.pages
      and not any("shredreq" in s for s in RA.TOOLS.values()) and "shredreq" not in RA.MENU and "shredreq" not in TH.TOOLS
      and not any("shredreq" in p for p in TH.ROLE_PINS.values()))
f = HC.open_finder(w, run=False)
check("... nor a Ctrl+K line", not any(e[3] == ("page", "shredreq") or "Quick shred" in e[1] for e in f.entries))
f.close()
with open(os.path.join(cfg, TH.PINS_FILE), "w", encoding="utf-8") as fh:
    json.dump({"pins": ["shredreq", "library", "assign"]}, fh)
check("an old pin to Quick shred reads as Shred, once (4.60.0: and Redline a document is offered once)", TH.load_pins(cfg) == ["assign", "library", "redline"], TH.load_pins(cfg))
w.go("tools"); pump()
ok = w.go("shredreq"); pump()
check("... and an old key opens Shred without an error", ok is not False and w.stack.currentWidget() is pg)

# ---- Quick tools: Shred to setup
uses = dict(TH.uses_for([SOW]))
check("Quick tools' use is Shred to setup, in the door's words", uses.get("shred", "").startswith("Shred to setup: The customer's document")
      and "shred" in TH.NEEDS_HOME and "shred" in TH.EFFORT_ONLY and "Quick shred" not in " ".join(uses.values()), uses)
w.go("tools"); pump()
d = TH.UseDialog(w.tools_page, [SOW], w)
row = next(i for i in range(d.list.count()) if d.list.item(i).data(Qt.UserRole) == "shred")
d.list.setCurrentRow(row); pump()
check("... it asks where, in the same step", not d.where.isHidden())
d.close()
L2 = os.path.join(tmp, "Heron", "Heron_Effort_List.xlsx"); os.makedirs(os.path.dirname(L2))
H = E.EffortList(L2, "Heron"); H.pending = True; H.save()
w.efforts.put("Heron", path=L2); W.Workspace(W.data_dir_for(L2), "Heron")
NEW = os.path.join(tmp, "Heron_SOW.pdf")
pdfmini.write(NEW, [["The contractor shall test the Heron antenna.", "The contractor shall report each test."]], size=9)
w.go("tools"); pump()
got = w.tools_page.files_in([NEW], use="shred", home=("home", "Heron"), choices={})
landed = wait(lambda: w.effort_name == "Heron" and w.stack.currentWidget() is pg, 120)
lib = DV.Library(w.ws.p("documents")).load()
doc = next((x for x in lib.all if x.get("versions") and x["versions"][-1].get("file") == os.path.basename(NEW)), None)
check("Shred to setup on Quick tools lands the file in the effort picked, as the customer's, then Shred", got == "shred" and landed
      and doc is not None and doc.get("category", "customer") == "customer", (got, w.effort_name, [x.get("name") for x in lib.all]))
w.close()
print(f"QT SHRED 4540 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
