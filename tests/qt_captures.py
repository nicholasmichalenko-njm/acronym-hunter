"""3.41.0 captures from meetings, capture files and the customer's answers, each with its source type, offscreen, on an
effort read from the fictional RFP. A capture made in Review keeps Customer document; words selected in a meeting's notes
become a capture whose source is the meeting (title, date, who was there); paragraphs ticked in a capture file (Word, PDF
or text) become captures whose source is Capture intel, each with its file, page and heading; an answered customer
question becomes a capture whose source is the answer. The Captured list shows a Source column and filters by it; the
kickoff packet shows where each came from. A capture saved before 3.41 reads as Customer document. Fictional content."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, setupdoc as SD, effortrec as RR, kickoff as KO, docxw
import excerpts as EX, capturefiles as CF, meetings as MT, custqa as Q
OP.available = lambda: False
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import binsview as BV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M, Rv = w.review.M, w.review
TA = "1.1 Technical Approach"
a = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
Rv.req([a], TA)
rec = RR.Record(w.ws.root)

# Review's own capture keeps Customer document; an old capture with no source reads the same way
x0 = EX.add(rec, "objective", [EX.part_of(a)], sections=[TA])
check("a capture made in Review: source Customer document", EX.source_of(EX.get(RR.Record(w.ws.root), x0)) == "customer")
old = {"id": "old1", "bin": "keypoint", "parts": [EX.part_of(a)]}
check("a capture saved before 3.41 (no source) reads as Customer document", EX.source_of(old) == "customer")

# a meeting's notes
mrec = RR.Record(w.ws.root)
mid = MT.add_meeting(mrec, "Kickoff with the capture team", "2026-11-02", participants=["Dana Ruiz", "G. Park"],
                     notes="The customer worries most about schedule risk on the bus integration.\nThey liked our TVAC history.")
w.go("meetings"); app.processEvents()
mp = w.meetings_page
mp.refresh(); app.processEvents()
mp.show(mid); app.processEvents()
cur = mp.notes.textCursor(); cur.setPosition(0); cur.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor); mp.notes.setTextCursor(cur)
check("selecting words in the notes enables Capture the selection", mp.cap_btn.isEnabled())
xm = mp.capture_selection(answer={"bin": "hot", "sections": [TA], "value": "", "note": ""})
xr = EX.get(RR.Record(w.ws.root), xm)
check("the selected words become a capture whose source is the meeting", xr and EX.source_of(xr) == "meeting"
      and EX.text_of(xr).startswith("The customer worries most about schedule risk") and xr["bin"] == "hot", xr)
check("... with the meeting's title, date and who was there", "Meeting: Kickoff with the capture team" in EX.where_of(xr)
      and "2026-11-02" in EX.where_of(xr) and "Dana Ruiz" in xr["parts"][0]["loc"], EX.where_of(xr))

# a capture file (Word)
doc = docxw.Doc()
doc.rich([("Capture plan: Kestrel", {"bold": True, "size": 32})])
doc.rich([("The program office plans to award by March.", None)])
doc.rich([("Competitor Orbital Works bid a heritage bus last time.", None)])
cf = os.path.join(tmp, "Kestrel capture plan.docx"); doc.save(cf)
paras = CF.read(cf)
check("a capture file reads into numbered paragraphs", [p["text"] for p in paras][1:] == ["The program office plans to award by March.",
                                                                                         "Competitor Orbital Works bid a heritage bus last time."], paras)
ed = BV.ExcerptsDialog(w.assign_page, w.assign_page, RR.Record(w.ws.root))
ids = ed.from_file(cf, answer={"paras": [1, 2], "bin": "keypoint", "sections": [TA], "one_each": True})
xs = [EX.get(RR.Record(w.ws.root), i) for i in ids]
check("ticked paragraphs become captures, one each, source Capture intel", len(xs) == 2 and all(EX.source_of(x) == "intel" for x in xs)
      and "Capture file: Kestrel capture plan.docx" in EX.where_of(xs[0]), [EX.where_of(x) for x in xs])
txt = os.path.join(tmp, "call notes.txt"); open(txt, "w").write("First call: they want a 2027 launch.\n\nSecond: budget is tight.\n")
ids2 = ed.from_file(txt, answer={"paras": [0, 1], "bin": "keypoint", "one_each": False})
check("plain text works too; one capture can hold every ticked paragraph", len(ids2) == 1
      and len(EX.get(RR.Record(w.ws.root), ids2[0])["parts"]) == 2)
check("an unreadable file reads as nothing", CF.read(os.path.join(tmp, "nope.pdf")) == [])

# the customer's answer
qrec = RR.Record(w.ws.root)
qid = Q.add(qrec, "Is a heritage bus acceptable?", "The Offeror shall describe its technical approach.", doc="Section L", section="L.4.2")
Q.update(qrec, qid, answer="Yes, with a delta qualification plan.", answer_doc="Amendment 1")
w.go("custqa"); app.processEvents()
qp = w.custqa_page; qp.fill(); qp.select_id(qid)
xq = qp.capture_answer(answer={"bin": "keypoint", "sections": [TA], "value": "", "note": ""})
xqr = EX.get(RR.Record(w.ws.root), xq)
check("an answered question becomes a capture whose source is the customer's answer", xqr and EX.source_of(xqr) == "qa"
      and EX.text_of(xqr) == "Yes, with a delta qualification plan." and "Customer Q&A 1 answer (Amendment 1)" in EX.where_of(xqr))
q2 = Q.add(RR.Record(w.ws.root), "Unanswered?", "x"); qp.fill(); qp.select_id(q2)
check("a question with no answer cannot be captured", qp.capture_answer(answer={"bin": "keypoint"}) is None)

# the Captured list and the kickoff packet
ed.fill()
srcs = [ed.t.item(r, 6).text() for r in range(ed.t.rowCount())]
check("the Captured list shows each capture's source", {"Customer document", "Meeting", "Capture intel", "Customer Q&A answer"} <= set(srcs), srcs)
ed.source.setCurrentIndex(ed.source.findData("meeting")); app.processEvents()
check("... and filters by it", ed.t.rowCount() == 1 and ed.t.item(0, 6).text() == "Meeting")
pk = KO.section_pack(RR.Record(w.ws.root), M, TA)
hot = pk.get("hot") or []
caps = (pk.get("keypoints") or []) + (pk.get("captures") or []) + hot + (pk.get("objectives") or [])
check("the kickoff packet shows where each capture came from", any("Meeting: Kickoff" in r["where"] for r in hot)
      and any("Capture file:" in r["where"] for r in caps) and any("Customer Q&A 1 answer" in r["where"] for r in caps),
      [r["where"] for r in caps][:6])

w.close()
n = sum(checks)
print(f"QT CAPTURES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
