"""3.37.0 author kickoff packets and Everything for this section, offscreen: who leads and writes each section; one Word
packet per author with the customer's words and where each is, how it is scored, the objectives, hot buttons and key
points captured for the section, its win themes, open meeting topics, the customer's answers, the page budget, dates and
facts, with the effort's marking at the top and bottom of every page; Structure Builder's panel shows the same, with a
filter."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, setupdoc as SD, pagebudget as PB, effortrec as RR, kickoff as KO
import excerpts as EX, themes as TH, meetings as MT, custqa as Q, walloftruth as WT, branding as BR
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


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
M, R = w.review.M, w.review
TA = "1.1 Technical Approach"
a = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
R.req([a], TA); SD.set_lm(M, [a], "L")
SD.set_people(M, TA, "Dana Ruiz", "A. Lee"); SD.set_people(M, "1.2 Risk", "A. Lee")
PB.set_pages(M, TA, 6)
rec = RR.Record(w.ws.root)
EX.add(rec, "objective", [EX.part_of(a)], sections=[TA])
EX.add(rec, "hot", [EX.part_of(a, words="testing the spacecraft bus")], sections=[TA])
TH.add(rec, "Flight heritage", "Proven on 12 buses", discriminator="Only flight-proven bus", proof=["12 launches"], sections=[TA])
mid = MT.add_meeting(rec, "Kickoff", "2026-11-03"); MT.add_topic(rec, mid, "Confirm the test campaign scope", owner="Dana Ruiz", target=TA)
Q.add(rec, "Is environmental testing at the unit level required?", sid=a["id"])
qid = Q.items(rec)[0]["id"]; Q.update(rec, qid, answer="Yes, at the unit level.", answer_doc="Amendment 1", status="Answered")
WT.add(rec, "Buses delivered", "12")
BR.set_identity(rec, sensitivity="CUI")
w.changed(); app.processEvents()
people = KO.authors(M)
check("who leads and writes each section (a subsection inherits its parent's people unless it has its own)",
      TA in people["Dana Ruiz"]["lead"] and TA in people["A. Lee"]["with"] and "1.2 Risk" in people["A. Lee"]["lead"], people)
pack = KO.section_pack(RR.Record(w.ws.root), M, TA)
c = KO.count(pack)
check("the section's pack: requirement with its designation and source, objectives, hot buttons, themes, topics, answers",
      c["reqs"] >= 1 and pack["reqs"][0]["lm"] == "L" and "Section_L_print.pdf" in pack["reqs"][0]["where"]
      and pack["objectives"] and pack["hot"] and pack["themes"][0]["discriminator"] == "Only flight-proven bus"
      and pack["topics"][0]["text"].startswith("Confirm") and pack["qa"][0]["answer"].startswith("Yes") and pack["pages"] == 6, c)
folder = os.path.join(tmp, "packets")
out = w.structure_page.kickoff(run=False, folder=folder)
names = {n: p for n, p in out}
check("one Word packet per author", set(names) == {"Dana Ruiz", "A. Lee"} and all(os.path.isfile(p) for p in names.values()), names)
z = zipfile.ZipFile(names["Dana Ruiz"])
doc = z.read("word/document.xml").decode("utf-8")
hf = "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("word/header") or n.startswith("word/footer"))
check("the packet holds the customer's words, the objective, the theme, the topic, the answer, the pages and the fact",
      "describe its technical approach" in doc and "Flight heritage" in doc and "Confirm the test campaign scope" in doc
      and "Yes, at the unit level." in doc and "6 pages" in doc and "Buses delivered" in doc and "Lead" in doc)
check("the effort's marking at the top and bottom of every page", hf.count("CUI") >= 2, hf.count("CUI"))
lee = zipfile.ZipFile(names["A. Lee"]).read("word/document.xml").decode("utf-8")
check("each author's packet holds their own sections", "1.2 Risk" in lee and "Writer" in lee)
w.go("structure"); app.processEvents()
sp = w.structure_page
sp.sel = TA; sp.show_section(); app.processEvents()
txt = sp.ev_text.text()
check("Structure Builder: Everything for this section", "Hot buttons" in txt and "Flight heritage" in txt and "Dana Ruiz" in txt
      and "Confirm the test campaign scope" in txt)
sp.ev_filter.setText("heritage"); app.processEvents()
check("the filter keeps the lines that match", "Flight heritage" in sp.ev_text.text() and "Confirm the test" not in sp.ev_text.text())
w.close()
n = sum(checks)
print(f"QT KICKOFF PASS ({n}/{len(checks)})" if n == len(checks) else f"QT KICKOFF FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
