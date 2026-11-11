"""4.12.0 offscreen: deliverables (claude/stationkeeper-capture-cards-plan-4.12.md, part B). On Shred, a piece typed
Deliverable with none on the board says No deliverables yet and Go to Dashboard > Deliverables, whose button opens it;
with deliverables there, Which deliverable lists them and attaches the piece (it shows under From the solicitation on
the deliverable's page; picking another moves it). Delete this deliverable... asks first with Cancel the default; Cancel
keeps it; Delete removes it from the List view, a board card's right-click and its own page; Undo (Ctrl+Z on the page)
puts it back, piece and all. Fictional (an Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, pdfmini
import deliverables as DL, effortrec as RR, shredtypes as ST
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import delivdelete as DD, piececaptures as PC

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["F.3 DELIVERABLES",
         "The Contractor shall deliver the Program Management Plan (CDRL A001) within 30 days after award.",
         "The Contractor shall deliver a monthly status report.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_F.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
OUT = os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx")
w.read_page.read([PDF], OUT)
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
rec = lambda: RR.Record(w.ws.root)                                       # noqa: E731
pmp, rpt = by("CDRL A001"), by("monthly status report")
pg.select(pmp["id"]); app.processEvents()
pg.do_capture("deliverable")
check("Capture > Deliverable types the piece and shows Which deliverable", ST.has(by("CDRL A001"), "deliverable")
      and pg.deliv_pick is not None)
check("with none, the drop-down says so", not pg.deliv_pick.isEnabled() and pg.deliv_pick.currentText() == PC.NONE)
lab = [l.text() for l in pg.card.findChildren(type(theme.label("x"))) if PC.GO in l.text()]
check("and says Go to Dashboard > Deliverables to add a deliverable", bool(lab) and pg.deliv_go is not None)
pg.deliv_go.click(); app.processEvents()
dp = w.deliverables_page
check("its button opens Dashboard > Deliverables", w.stack.currentWidget() is not pg and dp.isVisible())
a = DL.add(rec(), "Program Management Plan (CDRL A001)", "Plan")
b = DL.add(rec(), "Monthly status report", "Other")
w.go("assign"); app.processEvents()
pg.select(pmp["id"]); app.processEvents()
names = [pg.deliv_pick.itemText(i) for i in range(pg.deliv_pick.count())]
check("Which deliverable lists the board's deliverables", pg.deliv_pick.isEnabled()
      and names == ["Not attached yet", "Program Management Plan (CDRL A001)  (Plan)", "Monthly status report  (Other)"], names)
check("picking one attaches the piece", PC.attach(pg, a) and DL.of_piece(rec(), pmp["id"])["id"] == a
      and DL.pieces_of(rec(), a)[0]["text"].startswith("The Contractor shall deliver the Program"))
check("the drop-down shows it", pg.deliv_pick.currentData() == a)
PC.attach(pg, b)
check("picking another moves it", DL.of_piece(rec(), pmp["id"])["id"] == b and not DL.pieces_of(rec(), a))
PC.attach(pg, a)
pg.select(rpt["id"]); app.processEvents()
check("a piece not typed Deliverable shows no drop-down", pg.deliv_pick is None)
w.go("deliverables"); app.processEvents()
dp.open_deliverable(a, "Requirements"); app.processEvents()
check("From the solicitation on the deliverable's page", dp.one.piece_table is not None and dp.one.piece_table.rowCount() == 1
      and dp.one.piece_table.item(0, 0).text() == pmp["id"])
check("the deliverable's page has Delete this deliverable...", dp.one.delete_btn.isVisibleTo(w))
q = DD.question(dp, DL.get(rec(), a))
check("the question names it and what goes with it", "Program Management Plan" in q and "1 piece of the solicitation" in q, q)
check("Cancel keeps it", not dp.remove(a, answer=False) and DL.get(rec(), a) is not None)
check("Delete on its page removes it and goes back to the board", dp.remove(a, answer=True) and DL.get(rec(), a) is None
      and dp.stack.currentWidget() is dp.all_box)
check("Undo is offered", w.undo_text() == "Delete Program Management Plan (CDRL A001)", w.undo_text())
w.undo_here(); app.processEvents()
check("Undo puts it back, piece and all", DL.get(rec(), a) is not None and DL.of_piece(rec(), pmp["id"])["id"] == a
      and [d["id"] for d in DL.items(rec())] == [a, b])
m = DD.card_menu(dp, b, None, run=False)
check("a board card's right-click: Open and Delete this deliverable...", [x.text() for x in m.actions() if x.text()]
      == ["Open", "Delete this deliverable..."] and dp.board.cards[b].on_menu is not None)
dp.view.setCurrentIndex(1); app.processEvents()
dp.table.selectRow(dp.ids.index(b))
check("the List view's Delete... removes the selected one", dp.remove(answer=True) and DL.get(rec(), b) is None
      and b not in dp.ids)
check("the record keeps it", [d["id"] for d in DL.removed(rec())] == [b])
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
