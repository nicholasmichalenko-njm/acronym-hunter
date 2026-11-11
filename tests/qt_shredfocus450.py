"""4.5.0 offscreen: Shred, as designed (claude/stationkeeper-shred-place-plan-4.5.md, steps 3 and 4). Shred shows one job:
the document row with More and the main button Mark this document shredded; the piece pane with What it is (type chips
that toggle and combine, the decision following; the suggestion dashed, Enter takes it), Capture and Ask a question; no
selection bar, topic bar, bottom decide and capture panel, authors or sections. N goes to the next piece not sorted.
Fictional (an Osprey Section L)."""
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
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLineEdit, QTabBar
import skqt.shredfocus as SF
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
vis = lambda x: x.isVisibleTo(w) and x.isVisible()                     # noqa: E731


def controls():
    n = sum(1 for b in pg.findChildren(QAbstractButton) if vis(b) and not isinstance(b.parent(), QTabBar))
    n += sum(1 for c in pg.findChildren(QComboBox) if vis(c))
    return n + sum(1 for f in pg.findChildren(QLineEdit) if vis(f) and not isinstance(f.parent(), QComboBox))


check("Shred is in its focus: one job", pg.focus == "shred" and not vis(pg.decide_area) and not vis(pg.bulk)
      and not vis(pg.topic_bar) and not vis(pg.sg_btn) and not vis(pg.next_btn))
check("the main button: Mark this document shredded; More holds the rest", vis(pg.shred_main) and vis(pg.focus_more)
      and all(k in pg.more_acts for k in ("Fix text", "Take every suggestion", "Add missed text", "Fit width", "Pan", "Captured list")))
it = by("Integrated Master Schedule")
pg.select(it["id"]); app.processEvents()
n_ctl = controls()
check("with a piece selected: about 14 controls (38 in 4.4.0)", n_ctl <= 16, n_ctl)
check("What it is: the eight types as chips", list(pg.type_chips) == list(ST.KEYS), list(getattr(pg, "type_chips", {})))
check("... no authors, no sections, no decision line on Shred", pg.authors is None and not vis(pg.kind_label))
sug = getattr(pg, "sug_label", None)
check("the suggestion shows dashed on its chip and says why", sug is not None and "Enter takes it" in sug.text()
      and "dashed" in pg.type_chips["instruction"].styleSheet(), sug.text() if sug else None)
SF.enter(pg); app.processEvents()
it = by("Integrated Master Schedule")
check("Enter takes the suggestion", it.get("decision") == "Keep" and it.get("lm") == "L", (it.get("decision"), it.get("lm")))
t = by("Text shall be no smaller")
pg.select(t["id"]); app.processEvents()
pg.type_chips["requirement"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("a chip puts a type on; the decision follows (a requirement)", t["piece"] == "requirement" and t["decision"] == "Keep")
pg.type_chips["rule"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("a second type joins it: a requirement that is also a rule", t["piece"] == "requirement;rule" and t["decision"] == "Keep"
      and pg.type_chips["rule"].isChecked() and pg.type_chips["requirement"].isChecked())
pg.type_chips["requirement"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("clicked again it comes off: a rule alone is the customer's", t["piece"] == "rule" and t["decision"] == "Customer")
pg.do_undo(); app.processEvents()
t = by("Text shall be no smaller")
check("Undo puts the type and the decision back in one step", t["piece"] == "requirement;rule" and t["decision"] == "Keep",
      (t["piece"], t["decision"]))
pg.select(t["id"]); app.processEvents()
pg.type_chips["not_applicable"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("Not applicable clears the others (Ignore)", t["piece"] == "not_applicable" and t["decision"] == "Drop")
pg.type_chips["not_applicable"].click(); app.processEvents()
t = by("Text shall be no smaller")
check("... and off again: not sorted, not decided", t["piece"] == "" and not t.get("decision"))
import skqt.typechips as TC
names = TC.fill_capture(pg, pg.capture_menu)
check("Capture: one menu, without what the types cover", names and not any(n.startswith(x) for n in names
      for x in ("Submission", "Formatting", "Key date", "Acronym", "Question")), names)
check("Ask a question beside it", vis(pg.ask_btn) and pg.ask_btn.text() == "Ask a question")
first = by("Proposals shall be submitted")
pg.select(first["id"]); app.processEvents()
got = SF.next_open(pg)
check("N: the next piece not sorted", got and not by("Proposals shall be submitted")["id"] == got
      and not M.items[[x["id"] for x in M.items].index(got)].get("decision"), got)
f0 = pg.file
SF.shredded(pg); app.processEvents()
check("Mark this document shredded marks it", f0 in pg.reviewed())
w.close()
n = sum(checks)
print(f"QT SHREDFOCUS 450 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
