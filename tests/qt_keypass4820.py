"""4.82.0 (K1): the Submission Formatting Requirements pass on the screen. Shred's first tab; Key Date (4 or D) asks the
kind with the app's reading suggested; Proposal due and Questions due fill Customer information; the other kinds go on
the calendar; an amendment's date asks Replace or Keep; Other is named and offered again; the calendar's way back to the
sentence; Key date off the Deliverables bar. Fictional (Kestrel); the pieces' words are changed in memory for the test."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
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
import compmark as CM, custinfo as CI, effortrec as RR, keydatemark as KM
from skqt import comppass as CP, keypass as KP, shredselbar as SSB
pg = w.assign_page


def bar():
    SSB.refresh(pg); app.processEvents()
    return pg.sel_bar


def rec():
    return RR.Record(w.ws.root)


def key(k):
    QTest.keyClick(pg.view, k); app.processEvents()


check("Shred's tabs start with Submission Formatting Requirements (his order of the passes)", [k for k, _t in MW.TABS["assign"]] ==
      ["subpass", "comppass", "delivpass", "assign", "requirements", "evalcrit", "acronyms"]
      and dict(MW.TABS["assign"])["subpass"] == "Submission Formatting Requirements")
w.go("subpass"); app.processEvents()
check("the tab opens the Shred page in the pass, titled Shred", w.stack.currentWidget() is pg and pg.focus == "subm" and w.page_title.text() == "Shred")
check("nothing is beside the page; the row above says the document's state", not pg.page_side.isVisibleTo(pg) and pg.comp_state.isVisibleTo(pg)
      and "Not looked at" in pg.comp_state.text() and "key date" in pg.comp_none.toolTip(), pg.comp_state.text())
check("the tab's count starts at none marked", w.stepper.chips["subpass"].ct.text() == "none marked", w.stepper.chips["subpass"].ct.text())
M = pg.R.M
rows = [it for it in pg.R.rows_of(pg.file) if it.get("type") != "Heading"]
q, p, p2, sv, aw, nd, x_ = rows[2], rows[3], rows[4], rows[5], rows[6], rows[7], rows[8]
q["text"] = "Questions are due no later than March 1, 2027 at 2:00 PM Eastern Time."
p["text"] = "Proposals shall be received by 4:00 p.m. MT on December 15, 2026."
p2["text"] = "Amendment 1: proposals shall now be received by 4:00 p.m. MT on December 22, 2026."
sv["text"] = "A site visit will be held on January 20, 2027 at 10:00 AM CT."
aw["text"] = "Contract award is expected by June 1, 2027."
nd["text"] = "Answers will be posted to the website after the question period closes."

pg.select(q["id"]); app.processEvents(); f = bar()
check("one button of the four is built: 4 Key Date", f.keyd is not None and f.keyd.text().startswith("4") and len(f.kinds) == 1
      and getattr(f, "lead", None) is None and f.head is not None and f.x is not None and f.ask is not None, f.keyd.text() if f.keyd else None)
check("the bar says what the words read as before anything is marked", f.reads is not None and "Mar 1, 2027, 2:00 p.m. ET" in f.reads.text()
      and "Questions due" in f.reads.text(), f.reads.text() if f.reads else None)
key(Qt.Key_4); f = bar()
check("4 asks one thing, the kind, with the date read and editable", f.key_edit is not None and f.key_edit.text() == "Mar 1, 2027, 2:00 p.m. ET"
      and len(f.key_kinds) == 7 and f.key_kinds["questions"].text().endswith("Enter") and "Questions due" in f.key_kinds["questions"].text(),
      f.key_edit.text() if f.key_edit else None)
key(Qt.Key_Return); f = bar()
fq = CI.fact(rec(), "Questions due")
check("Enter takes the suggestion: Questions due is in Customer information, captured from the piece", fq["value"] == "Mar 1, 2027, 2:00 p.m. ET"
      and fq["how"] == "captured" and fq["source"].get("sid") == q["id"], fq)
cal = w.calendar_page.load(datetime.date(2026, 12, 1))
check("... and on the calendar at once, from the one value", any(k == "questions" and t == "2:00 p.m. ET" for k, t in cal.get(datetime.date(2027, 3, 1), [])),
      cal.get(datetime.date(2027, 3, 1)))
check("the bar names where it went; the count follows", f.cal_link is not None and "in Customer information" in f.cal_line.text() and f.keyd.isChecked()
      and w.stepper.chips["subpass"].ct.text() == "1 on the calendar" and "Has finds (1)" in pg.comp_state.text(),
      (f.cal_line.text() if f.cal_line else None, w.stepper.chips["subpass"].ct.text()))

pg.select(p["id"]); app.processEvents(); bar()
key(Qt.Key_Return); f = bar()
check("Enter on a piece with a date starts Key Date, Proposal due suggested", f.key_edit is not None and f.key_kinds["proposal"].text().endswith("Enter"))
key(Qt.Key_Return)
r = rec()
check("Proposal due is the effort's due date and Customer information's, one value", r.data.get("due") == "2026-12-15T16:00" and r.data.get("zone") == "MT"
      and CI.fact(r, "Proposal due")["how"] == "captured", (r.data.get("due"), r.data.get("zone")))
pg.select(p2["id"]); app.processEvents(); bar()
key(Qt.Key_Return); key(Qt.Key_Return); f = bar()
check("an amendment's different date asks once: Replace (Enter) or Keep the earlier", f.replace is not None and f.keep is not None and rec().data.get("due") == "2026-12-15T16:00")
key(Qt.Key_Return)
r = rec()
cal = w.calendar_page.load(datetime.date(2026, 12, 1))
check("Replace: the newer date, and the calendar says what it replaced", r.data.get("due") == "2026-12-22T16:00"
      and any(k == "due" and "replaces Dec 15, 2026" in t for k, t in cal.get(datetime.date(2026, 12, 22), [])), cal.get(datetime.date(2026, 12, 22)))

pg.select(sv["id"]); app.processEvents(); bar()
key(Qt.Key_D); f = bar()
check("D is Key Date in this pass too; Site visit suggested", f.key_edit is not None and f.key_kinds["visit"].text().endswith("Enter"))
key(Qt.Key_Return)
ev = [e for e in rec().data.get("events", []) if e.get("key_sid") == sv["id"]]
check("a site visit is a calendar entry that keeps the piece", len(ev) == 1 and ev[0]["kind"] == "Meeting" and ev[0]["key_kind"] == "visit", ev)

pg.select(aw["id"]); app.processEvents(); bar()
key(Qt.Key_4); key(Qt.Key_7); f = bar()
check("Other (7) asks its name", f.key_name is not None)
f.key_name.setText("Award"); key(Qt.Key_Return)
check("named Other is on the calendar; the name is kept for the effort", any(e.get("title") == "Award" for e in rec().data.get("events", []))
      and KM.own_names(rec()) == ["Award"])
pg.select(x_["id"]); app.processEvents(); bar()
x_["text"] = "Debriefings will be offered by July 1, 2027."
key(Qt.Key_4); key(Qt.Key_7); f = bar()
names = [f.col.itemAt(i).widget().text() for i in range(f.col.count()) if f.col.itemAt(i).widget() is not None]
check("a name given to Other is offered again", "Award" in names, names)
KP.cancel(pg); app.processEvents()
x_["text"] = "The Government will hold no discussions."

pg.select(nd["id"]); app.processEvents(); bar()
key(Qt.Key_4); f = bar()
check("no date in the words: the date is typed on the bar", f.key_edit is not None and f.key_edit.text() == "")
f.key_edit.setText("Feb 2, 2027"); key(Qt.Key_3)
ev = [e for e in rec().data.get("events", []) if e.get("key_sid") == nd["id"]]
check("3 while it asks: Answers expected, on the typed date", len(ev) == 1 and ev[0]["date"] == "2027-02-02" and ev[0]["title"] == "Answers expected", ev)

pg.select(sv["id"]); app.processEvents(); bar()
key(Qt.Key_X)
check("Not needed is refused on a key date", CM.state(M, sv, "subm_marks") == KM.KEYDATE)
key(Qt.Key_4)
check("4 again takes the mark off, and the entry it made", not [e for e in rec().data.get("events", []) if e.get("key_sid") == sv["id"]] and KM.of_piece(M, sv) is None)
key(Qt.Key_X)
check("X: Not needed in this pass only", CM.state(M, sv, "subm_marks") == "x" and CM.state(M, sv) == "")
import shredtypes as STX
o_ = rows[9]
__import__("skqt.shredbar", fromlist=["x"]).capture_types(pg, "keydate", [o_["id"]]); app.processEvents()
pg.select(o_["id"]); app.processEvents(); f = bar()
check("an older Key Date mark says so and is given no kind", f.before is not None and "kind not said" in f.before.text() and not f.keyd.isChecked(),
      STX.types_of(o_))

w.go("calendar"); app.processEvents()
w.calendar_page.pick(datetime.date(2027, 3, 1)); app.processEvents()
back = getattr(w.calendar_page, "back", [])
check("the calendar's day has a way back to the words", len(back) == 1 and "Questions due" in back[0].text(), [b.text() for b in back])
back[0].click(); app.processEvents()
check("... which opens the pass on the sentence", w.stack.currentWidget() is pg and pg.focus == "subm" and [it["id"] for it in pg.selected()] == [q["id"]])

w.go("delivpass"); app.processEvents()
pg.select(q["id"]); app.processEvents(); f = bar()
seen = []
real = w.status
w.status = lambda m, *a, **k: seen.append(m)
key(Qt.Key_D)
w.status = real
check("Key date is off the Deliverables bar; D there points to its pass", getattr(f, "keydate", None) is None and any("Submission Formatting Requirements" in m for m in seen), seen)
w.go("comppass"); app.processEvents()
pg.select(q["id"]); app.processEvents(); f = bar()
check("Compliance keeps its own bar", pg.focus == "comp" and len(f.kinds) == 3)
print(f"{sum(checks)}/{len(checks)}")
if not all(checks):
    sys.exit(1)
print("ok qt_keypass4820")
