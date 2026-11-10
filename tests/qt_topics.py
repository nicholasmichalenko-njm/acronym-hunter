"""3.28.0 topics in Review, offscreen: + Topic, Sort mode puts the selected sentences in topic 1 to 9 (again takes it
off), the page marks them and Show one topic dims the rest, the coverage says how far each has come, topics from the
RFP's headings, a topic mapped to a section takes its requirements there, a section for each topic, the topics
dialog; an RFI effort opens in Sort mode, with Customer interest (I) and RFI suggestions."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import compliance as C, effort as E, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
reg = E.Registry(os.path.join(cfg, "efforts.json")); reg.put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk\nVolume II Management\n2.1 Program Management")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]

app = QApplication([])
theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION)
w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the effort opens and is held", w.open_effort("Kestrel") and W.read_json(ws0.p("lock.json"), {}).get("pid") == os.getpid())
check("no matrix yet: Shred is the step (4.1.0: it lists the documents to extract)", w.stack.currentWidget() is w.assign_page)
out = os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx")
w.read_page.read(PDFS, out)
check("Read runs in the background and starts the matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
import effortrec as RR, excerpts as EX, pagemarks as PM
from PySide6.QtGui import QShortcut
rec = lambda: RR.Record(w.ws.root)


import topics as TP
check("the topic bar sits over the page, Sort mode off", pg.topic_bar.isVisible() and not pg.sort_on and "No topics yet" in pg.topic_cov.text())
check("keys 1 to 9 and Ctrl+T are there", {"1", "9", "Ctrl+T"} <= {s.key().toString() for s in pg.findChildren(QShortcut)})
t1 = pg.new_topic("Technical approach"); t2 = pg.new_topic("Risk")
check("+ Topic: chips for each topic", t1 and t2 and len(pg.topic_btns) == 2)
pg.toggle_sort(True); app.processEvents()
check("Sort mode numbers the chips", pg.sort_on and pg.topic_btns[0].text().startswith("1  "))
a = by("The Offeror shall describe its technical approach")
pg.select(a["id"]); app.processEvents()
on = pg.tag_topic(0)
check("1 puts the selected sentence in the first topic", on and [t["id"] for t in TP.of(rec(), a["id"])] == [t1])
check("the page marks it on the right", any(l.text() == "1" for l in pg.labels))
pg.tag_topic(1)
check("a sentence can carry several topics", {t["id"] for t in TP.of(rec(), a["id"])} == {t1, t2})
pg.tag_topic(1)
check("again takes it off", [t["id"] for t in TP.of(rec(), a["id"])] == [t1])
pg.topic_show.setCurrentIndex(pg.topic_show.findData(t1)); app.processEvents()
box = pg.view.boxes[a["id"]]
other = next(b for i, b in pg.view.boxes.items() if i != a["id"])
check("Show one topic dims the rest", box.opacity() == 1.0 and other.opacity() < 0.5)
check("its coverage: sentences, decided, open, in a section", "1 sentence(s): 0 decided, 1 open, 0 in a section" in pg.topic_cov.text(), pg.topic_cov.text())
pg.topic_show.setCurrentIndex(0); app.processEvents()
labels = pg.R.labels()
TP.update(rec(), t1, sections=[labels[1]])
pg.target = labels[0]
pg.select(a["id"]); pg.do_lm("L"); app.processEvents()
check("a topic mapped to a section takes its requirement there (over the target)", a.get("decision") == "Keep" and a.get("map") == labels[1], (a.get("map"), labels[1]))
pg.topic_show.setCurrentIndex(pg.topic_show.findData(t1)); app.processEvents()
check("... and the coverage counts it", "1 decided, 0 open, 1 in a section" in pg.topic_cov.text(), pg.topic_cov.text())
pg.topic_show.setCurrentIndex(0)
made = pg.topics_from_headings()
check("Topics from the RFP's headings: a topic per heading, the sentences under it carry it", len(TP.topics(rec())) >= 2, len(TP.topics(rec())))
n_before = len(pg.R.labels())
secs = pg.sections_from_topics()
check("a section for each topic not yet mapped, each topic mapped to its own", secs and len(pg.R.labels()) == n_before + len(secs)
      and all(TP.get(rec(), t["id"])["sections"] for t in TP.topics(rec())))
d = pg.manage_topics(run=False)
d.list.setCurrentRow(0); d.rename("Technical approach and tools")
check("the topics dialog renames", TP.topics(rec())[0]["name"] == "Technical approach and tools")
d.move(1)
check("... orders (the first nine are on the keys)", TP.topics(rec())[1]["name"] == "Technical approach and tools")
# an RFI effort
eff = dict(w.ws.get("prod_std", {}) or {}); eff["effort_type"] = "rfi"; w.ws.set("prod_std", eff)
pg.toggle_sort(False); pg.rfi = False
pg.load(); app.processEvents()
check("an RFI effort opens in Sort mode", pg.rfi and pg.sort_on)
import suggestrules as SR
it = {"id": "x", "text": "The Government is interested in approaches to space domain awareness.", "type": "Context"}
check("RFI suggestions: what the Government wants to learn is a Customer interest", SR.suggest(M, it, rfi=True)["cat"] == "I"
      and SR.suggest(M, it)["cat"] != "I")
b = by("The Offeror shall describe its technical approach")
pg.select(b["id"]); pg.do_lm("I"); app.processEvents()
check("I: a Customer interest", b.get("lm") == "I" and SD.LM_SHORT["I"] == "Customer interest (RFI)")
w.close()
n = sum(checks)
print(f"QT TOPICS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
