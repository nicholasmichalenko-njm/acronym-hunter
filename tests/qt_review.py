"""2.96.0 the review panel in Assign, offscreen: the decisions L (Instructions), M (Evaluation) and SOW (Work) (keys L, E,
R; the card's buttons take one off when clicked again); dragging across words inside the selected sentence picks them
(a click still sets the split point); Capture files what the words or the sentence hold: a point of contact (guessed
pieces, new or added to one filed, fields of your own) into Customer information, submission instructions (a due date
can become the effort's, with its time zone) into Effort Home's Submission instructions, formatting rules into
Formatting requirements, an acronym into the effort list; each says where it came from; the readable copy has the
contacts."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, effortrec as RR, office_pdf as OP, pdfmini, readable as RD
OP.available = lambda: False
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from PySide6.QtTest import QTest
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow
from skqt import captureview as CV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically through PIEE no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "Questions shall be sent to the Contracting Officer, Jane Doe, at jane.doe@us.af.mil or (310) 653-1234.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Technical\n1.1 Technical Approach\nVolume II Management\n2.1 Schedule")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
w.read_page.read([PDF], os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None))
M = w.review.M
pg = w.assign_page
w.go("assign"); app.processEvents()
by = lambda s: next(it for it in M.items if s in it["text"])
due_s, poc, ims, fmt, sow = by("PIEE"), by("Jane Doe"), by("(IMS)"), by("12-point"), by("monthly status")
# the decisions
labels = [pg.keys[k].text() for k in ("L", "M", "Requirement")]
check("the decision buttons say L (Instructions), M (Evaluation), SOW (Work)", labels == ["L (Instructions)  L", "M (Evaluation)  E", "SOW (Work)  R"], labels)
import compliance as C
pg.set_target(C.outline_label(M.outline[1]))
pg.select(sow["id"]); app.processEvents()
QTest.keyClick(pg.view, Qt.Key_R); app.processEvents()
check("R: a SOW (Work) requirement", by("monthly status")["decision"] == "Keep" and by("monthly status")["lm"] == "C")
pg.select(sow["id"]); app.processEvents()
btn = next(b for b in pg.card.findChildren(type(pg.keys["L"])) if b.text() == "SOW (Work)")
btn.click(); app.processEvents()
check("the card's SOW (Work), clicked again, takes it off (a requirement, neither L, M nor SOW)", by("monthly status")["lm"] == ""
      and by("monthly status")["decision"] == "Keep")
pg.select(ims["id"]); QTest.keyClick(pg.view, Qt.Key_L); app.processEvents()
check("L: an L (Instructions) requirement", by("(IMS)")["lm"] == "L")
import setupdoc as SD
check("SOW requirements reference as C", SD.LM_SHORT["C"] == "SOW (Work)" and "C" in SD.LM)
# dragging across words
pg.select(poc["id"]); app.processEvents()
words = pg.view.words[poc["id"]]
import re
ws_ = [m.group(0) for m in re.finditer(r"[A-Za-z0-9]+", poc["text"])]
a, b = ws_.index("Jane"), ws_.index("1234")


def mouse(kind, rect, buttons=Qt.LeftButton):
    p = QPointF(pg.view.mapFromScene(rect.center()))
    ev = QMouseEvent(kind, p, pg.view.viewport().mapToGlobal(p), Qt.LeftButton if kind != QEvent.MouseMove else Qt.NoButton,
                     buttons, Qt.NoModifier)
    app.sendEvent(pg.view.viewport(), ev)
    app.processEvents()


pg.view.ensureVisible(pg.view.boxes[poc["id"]]); app.processEvents()
mouse(QEvent.MouseButtonPress, words[a])
mouse(QEvent.MouseMove, words[a + 2])
check("dragging tints the words as you go", len(pg._grab_items) == 3)
mouse(QEvent.MouseMove, words[b])
mouse(QEvent.MouseButtonRelease, words[b], Qt.NoButton)
check("letting go picks them, the card says so, and no split point is set", pg.grab is not None and pg.grab["text"].startswith("Jane Doe")
      and pg.grab["text"].endswith("1234") and pg.split_at is None
      and any("Picked words" in l.text() for l in pg.card.findChildren(QLabel)), pg.grab)
if os.environ.get("SHOT_DIR"):
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "review_grab.png"))
mouse(QEvent.MouseButtonPress, words[a + 1]); mouse(QEvent.MouseButtonRelease, words[a + 1], Qt.NoButton)
check("a click (no drag) still sets the split point", pg.split_at is not None)
pg.clear_split(); pg.show_grab(poc["id"], a, b)
# Contact
text, src = pg.capture_source()
d = CV.ContactDialog(pg, text, [])
g = {k: e.text() for k, e in d.ed.items()}
check("Contact: the pieces are guessed from the picked words", g["name"] == "Jane Doe" and g["email"] == "jane.doe@us.af.mil"
      and g["phone"] == "(310) 653-1234", g)
d.ed["title"].setText("Contracting Officer"); d.add_field("Office symbol", "SSC/PKA")
vals = d.values(); d.deleteLater()
cid = pg.do_capture("contact", answer=vals)
c = RR.Record(w.ws.root).contact(cid)
check("... filed with where it came from", c and c["name"] == "Jane Doe" and c["title"] == "Contracting Officer"
      and c["other"] == [{"label": "Office symbol", "value": "SSC/PKA"}] and c["sources"][0]["doc"] == "Section_L.pdf", c)
cid2 = pg.do_capture("contact", answer=({"address": "483 N. Aviation Blvd, El Segundo, CA 90245"}, cid))
check("... and a second capture adds to the same contact", cid2 == cid and RR.Record(w.ws.root).contact(cid)["address"].startswith("483")
      and len(RR.Record(w.ws.root).contacts()) == 1 and len(RR.Record(w.ws.root).contact(cid)["sources"]) == 2)
# Submission, with the due date
pg.select(due_s["id"]); app.processEvents()
text, src = pg.capture_source()
rd = CV.RuleDialog(pg, text, "submit")
check("Submission: the due date and delivery are found, and the due date offered as the effort's", rd.t.rowCount() == 2 and rd.due == ("2026-12-15T14:00", "ET")
      and rd.set_due.isChecked(), (rd.t.rowCount(), rd.due))
got = pg.do_capture("submit", answer=rd.values()); rd.deleteLater()
r = RR.Record(w.ws.root)
check("... filed, and the effort's due date and time zone set", len(got) == 2 and r.data["due"] == "2026-12-15T14:00" and r.zone_key() == "ET")
w.go("home"); app.processEvents()
hp = w.home_page
check("Effort Home: Submission instructions shows them with where they came from", any(x["label"] == "Proposal due" and "Section_L" in x["where"]
      for x in hp.sub_now) and any(x["label"] == "Delivery" and x["value"] == "PIEE" for x in hp.sub_now), [(x["label"], x["value"], x["where"]) for x in hp.sub_now])
check("... the card is on the proposal manager's Effort Home", "submission" in hp.shown)
# Formatting
w.go("assign"); app.processEvents()
pg.select(fmt["id"]); app.processEvents()
text, src = pg.capture_source()
fd = CV.RuleDialog(pg, text, "format")
found = [(fd.t.cellWidget(i, 1).currentText(), fd.t.item(i, 2).text()) for i in range(fd.t.rowCount())]
check("Formatting: the font and margins are found", ("Font", "12-point Times New Roman") in found and ("Margins", "1-inch margins") in found, found)
pg.do_capture("format", answer=fd.values()); fd.deleteLater()
w.go("home"); app.processEvents()
lines = {x["label"]: x for x in hp.fmt_now["lines"]}
check("Effort Home: Formatting requirements shows them, as captured from the document", lines["Font"]["required"] and lines["Font"]["value"] == "12-point Times New Roman"
      and "Section_L.pdf" in lines["Font"]["where"], lines["Font"])
# Acronym
w.go("assign"); app.processEvents()
pg.select(ims["id"]); app.processEvents()
ad = CV.AcronymDialog(pg, pg.capture_source()[0])
check("Acronym: the abbreviation and its long form are found", ad.values() == ("IMS", "Integrated Master Schedule"), ad.values())
pg.do_capture("acronym", answer=ad.values()); ad.deleteLater()
Lx = E.EffortList(LIST, "Osprey").load()
check("... into the effort list, with the customer document", "IMS" in Lx.rows and Lx.rows["IMS"]["Definition"] == "Integrated Master Schedule"
      and Lx.rows["IMS"]["Customer document"] == "Section_L.pdf")
check("nothing selected: capture says what to do", pg.view.scene().clearSelection() or pg.do_capture("contact") is None)
files = RD.more(RR.Record(w.ws.root), None, w.ws.root, {}) if hasattr(RD, "more") else {}
check("the readable copy has the contacts", "Customer contacts.csv" in files and files["Customer contacts.csv"][1][0][0] == "Jane Doe")
w.go("home"); app.processEvents()
from PySide6.QtWidgets import QFrame
check("Effort Home: Customer information shows the contact card", any(f.objectName() == "contact" for f in hp.info.findChildren(QFrame))
      and "1 contact(s)" in hp.info.title.text())
# the documents as a queue
w.go("assign"); app.processEvents()
check("the queue: which document this is and how many are not reviewed", pg.queue_lbl.text() == "Document 1 of 1  ·  1 not reviewed yet", pg.queue_lbl.text())
pg.mark_reviewed()
check("Mark reviewed: kept with the effort", pg.queue_lbl.text().endswith("all reviewed") and "Section_L.pdf" in w.ws.get("assign_reviewed", {})
      and pg.done_btn.text().startswith("Reviewed"))
pg.mark_reviewed()
check("... and taken off again", "Section_L.pdf" not in w.ws.get("assign_reviewed", {}))
n = sum(checks)
print(f"QT REVIEW {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
