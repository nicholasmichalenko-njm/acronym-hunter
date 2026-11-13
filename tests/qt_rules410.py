"""4.1.0 offscreen: Shred > Rules & Dates and Shred > Evaluation (claude/stationkeeper-shred-plan-4.1.md, step 4). Rules &
Dates is the Dashboard's Submission Rules, moved, with the shred's Rule and Date pieces in groups of their own, each
with where it came from and a way back to it on the page; Evaluation (moved from Matrix & Outline) lists every piece the
shred said is an Evaluation. Acros & Abs holds the Acro List (step 5): The list's More opens it and the lists to submit,
its Export makes the acro lists. Fictional (an Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C
import effort as E, workspace as W, pdfmini
import shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report.",
         "The Government will evaluate the realism of the schedule.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
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
from skqt.mainwin import TABS, HEAD_OF
from skqt import navrail as NR
check("Shred's four tabs: Requirements, Submission Checklist, Evaluation, Acronyms",
      [t for _k, t in TABS["assign"]] == ["Requirements", "Submission Checklist", "Evaluation Criteria", "Acronyms"], TABS["assign"])
check("... the Overview has no Submission Rules; Matrix & Outline no Evaluation", "requirements" not in [k for k, _t in TABS["home"]]
      and "evalcrit" not in [k for k, _t in TABS["matrix"]] and HEAD_OF["requirements"] == "assign" and HEAD_OF["evalcrit"] == "assign")
M = w.review.M
pg = w.assign_page
w.go("assign"); app.processEvents()
by = lambda s: next(it for it in M.items if s in it["text"])


def key(s, k):
    pg.select(by(s)["id"]); app.processEvents()
    QTest.keyClick(pg.view, k); app.processEvents()
    return by(s)


key("12-point", Qt.Key_U); key("December 15", Qt.Key_D); key("realism", Qt.Key_E)
w.go("requirements"); app.processEvents()
rp = w.requirements_page
check("Submission Checklist opens inside Shred, its title Submission Checklist", w.stack.currentWidget() is rp and w.page_title.text() == "Shred"
      and w.step_btns["assign"].isChecked(), w.page_title.text())
tops = {rp.tree.topLevelItem(i).text(0): rp.tree.topLevelItem(i) for i in range(rp.tree.topLevelItemCount())}
kids = [g.child(j) for g in tops.values() for j in range(g.childCount())]
r = next((k for k in kids if "12-point" in k.text(1)), None)
dt = next((k for k in kids if "December 15" in k.text(1)), None)
check("... the shred's rule and date sit in the three groups (4.6.0): the 12-point rule in Format, the date in Submission and dates",
      r is not None and dt is not None and r.parent().text(0).startswith("Format") and dt.parent().text(0).startswith("Submission and dates")
      and r.text(4) == "Listed here", (list(tops), r.text(4) if r else None))      # 4.21.0: a typed piece checks no other page
check("... the rule's words and where it came from", "12-point" in r.text(1) and "Section_L.pdf" in r.text(3), (r.text(1), r.text(3)))
rp.tree.setCurrentItem(r); app.processEvents()
btn = [b for b in rp.card.findChildren(QPushButton) if b.text() == "Show it on the page"]
check("... its card offers Show it on the page", btn and rp.card.title.text() == "Rule", rp.card.title.text())
btn[0].click(); app.processEvents()
check("... which opens Shred > Requirements at the piece", w.stack.currentWidget() is pg and by("12-point")["id"] in [it["id"] for it in pg.selected()])
w.go("evalcrit"); app.processEvents()
ep = w.evalcrit_page
rows = [ep.mtab.item(i, 1).text() for i in range(ep.mtab.rowCount())]
check("Evaluation lists the piece the shred said is an Evaluation", any("realism" in t for t in rows)
      and w.stepper.isVisibleTo(w), rows)
check("... and says what the shred said it is", any(ep.mtab.item(i, 2).text() == "Evaluation Criterion" for i in range(ep.mtab.rowCount())))
check("the stepper counts them", w.stepper.chips["requirements"].ct.text() == "2 from the shred"
      and w.stepper.chips["evalcrit"].ct.text() == "1 from the shred",
      (w.stepper.chips["requirements"].ct.text(), w.stepper.chips["evalcrit"].ct.text()))
# step 5: the Acro List folded into Acros & Abs
bar = w.acronym_page.bar
check("Acronyms > The list: More opens the whole acro list and the lists to submit; Export makes the acro lists",
      bar.action("The whole acro list...") is not None and bar.action("Lists to submit, by volume") is not None
      and bar.action("Import a list...") is not None and bar.action("The list: the whole effort...") is not None)
bar.action("The whole acro list...").trigger(); app.processEvents()
check("... the whole list opens inside Acronyms", (w.stack.currentWidget() is w.acronym_page and w.acronym_page.tab_stack.currentWidget() is w.acrlist_page) and w.step_btns["assign"].isChecked()
      and w.stepper.chips["acronyms"].styleSheet().count("2px solid") == 1 and "acrlist" not in w.stepper.chips)
# 4.29.4 (the capture audit): a Hot button captured in Shred is read on Evaluation Criteria
import custfocus as CF, effortrec as RRx
rx = RRx.Record(w.ws.root)
hid = CF.add_hot(rx, "Schedule certainty matters most", quote="The Government places great weight on schedule.", source={"doc": "Section M", "loc": "page 4"})
w.go("evalcrit"); app.processEvents(); ep.refresh(); app.processEvents()
check("Evaluation Criteria lists the hot buttons with where each was said", "Schedule certainty matters most" in ep.hot_list.text()
      and "Section M page 4" in ep.hot_list.text() and "Remove" in ep.hot_list.text(), ep.hot_list.text())
check("... Remove takes it off, there and in the effort record", ep.remove_hot(hid) and CF.hot_buttons(RRx.Record(w.ws.root)) == []
      and "None yet" in ep.hot_list.text(), ep.hot_list.text())
w.close()
print(f"QT RULES 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
