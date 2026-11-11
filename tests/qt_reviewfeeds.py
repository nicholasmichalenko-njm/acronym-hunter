"""3.29.0 everything Review takes flows out, offscreen: the matrix's Topic, Customer objective, Key points and Source
excerpt columns; the setup with each section's topics, the objectives mapped to it and the key points taken there;
an objective on the Wall of Truth; the RFP's written rules on Final Checks (a phrase looked for in the drafts, the rest
ticked by a person); the dashboard says what review still owes."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
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


import topics as TP, excerpts as EX, matrixdesign as MD, walloftruth as WT, zipfile
labels = pg.R.labels()
a = by("The Offeror shall describe its technical approach")
t1 = pg.new_topic("Technical approach")
pg.select(a["id"]); pg.toggle_sort(True); pg.tag_topic(0)
TP.update(rec(), t1, sections=[labels[1]])
pg.select(a["id"]); pg.do_lm("L"); app.processEvents()
xo = pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": "", "sections": [labels[1]]})
xk = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "lead with our digital twin", "sections": []})
d = MD.default("sentences")
d["columns"] += [{"key": k, "heading": MD.heading_of(k)} for k in ("topic", "objective", "keypoints", "excerpt")]
path = os.path.join(tmp, "matrix.xlsx")
res = MD.export(M, path, d, "Kestrel", ctx=MD.effort_ctx(w.ws))
from openpyxl import load_workbook
wb = load_workbook(path); sh = wb["Compliance Matrix"]
rows = [[c.value for c in r] for r in sh.iter_rows()]
hdr = next(r for r in rows if "Topic" in [str(x) for x in r])
row = next(r for r in rows if r and any(a["text"][:30] in str(x or "") for x in r))
col = lambda h: row[[str(x) for x in hdr].index(h)]
check("the matrix's Topic column", col("Topic") == "Technical approach", col("Topic"))
check("Customer objective: the objective mapped to its section, verbatim with where it sits", a["text"][:30] in str(col("Customer objective"))
      and "Section_L_print.pdf" in str(col("Customer objective")))
check("Key points: taken from the sentence, with the note", "digital twin" in str(col("Key points")))
check("Source excerpt and location", "Section_L_print.pdf" in str(col("Source excerpt and location")))
sp = w.setup_page
os.makedirs(os.path.join(tmp, "setup"), exist_ok=True)
outs = SD.export(M, os.path.join(tmp, "setup"), bins=SD.review_bins(w.ws.root))
txt = " ".join(zipfile.ZipFile(p).read("word/document.xml").decode("utf-8") for p in outs)
check("the setup: the section's topics", "Topics: Technical approach" in txt)
check("... the objective mapped to it", "Customer objective" in txt)
check("... and the key point taken there", "Key point: " in txt and "digital twin" in txt)
tid = pg.promote_excerpt(xo)
check("an objective on the Wall of Truth, its words verbatim with where they sit", tid and WT.get(rec(), tid)["kind"] == "Fact"
      and a["text"][:30] in WT.get(rec(), tid)["value"] and "Section_L_print.pdf" in WT.get(rec(), tid)["source"])
check("promoting again keeps the one truth", pg.promote_excerpt(xo) == tid and len(WT.items(rec())) == 1)
# written rules
b2 = M.items[3]
pg.select(b2["id"])
xw1 = pg.do_bin("format", answer={"bin": "format", "value": "", "note": "", "sections": []}, written=True)
EX.update(rec(), xw1, check="phrase")
x = EX.get(rec(), xw1); x["parts"][0]["text"] = 'Mark each page "CUI//SP-PROPIN" in the header.'; r_ = rec(); r_.data["excerpts"] = [y if y["id"] != xw1 else x for y in r_.data["excerpts"]]; r_.save()
pg.select(M.items[4]["id"])
xw2 = pg.do_bin("format", answer={"bin": "format", "value": "", "note": "", "sections": []}, written=True)
EX.update(rec(), xw2, check="final")
import docx
dr = docx.Document(); dr.sections[0].header.paragraphs[0].text = "CUI//SP-PROPIN"; dr.add_paragraph("Body")
p1 = os.path.join(tmp, "Volume I.docx"); dr.save(p1)
dr2 = docx.Document(); dr2.add_paragraph("No marking"); p2 = os.path.join(tmp, "Volume II.docx"); dr2.save(p2)
cp = w.checks_page
cp.refresh()
wr = EX.written_rules(rec())
check("Final Checks lists the RFP's written rules", cp.w_table.rowCount() == len(wr) == 2)
res = cp.check_written([p1])
check("a phrase rule found in every draft is ticked", res[xw1].startswith("found in every draft") and EX.get(rec(), xw1)["done"])
res = cp.check_written([p1, p2])
check("... and one missing in a draft says which", res[xw1] == "missing in Volume II.docx")
row2 = next(i for i in range(cp.w_table.rowCount()) if cp.w_table.item(i, 0).data(Qt.UserRole) == xw2)
cp.w_table.item(row2, 0).setCheckState(Qt.Checked); app.processEvents()
check("the rest a person ticks, kept with who and when", EX.get(rec(), xw2)["done"] and EX.get(rec(), xw2)["done_by"])
w.go("dashboard"); app.processEvents()
dp = w.dash_page if hasattr(w, "dash_page") else None
txt = dp.review_feed_text() if dp else ""
check("the dashboard says what review still owes", "every customer objective is mapped" in txt and "reviewed: " in txt, txt)
w.close()
n = sum(checks)
print(f"QT REVIEW FEEDS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
