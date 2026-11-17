"""3.55.0 Shred and Compare, offscreen. The quick shred (shredquick): one file in, every requirement out, each labelled
by kind (Requirement, Instruction (L), Evaluation (M), SOW task); the draft matrix in Excel. 4.54.0: it has no page of its
own (Shred's table is its view). Compare: one space with Customer versions and Any two files (sentence by sentence, changes by heading, the
redline in Word); Final Checks' Open in Compare and two files dropped on Quick tools open it. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
import docxw, openpyxl, shredquick as SQ
rfp = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
res = SQ.shred(rfp)
c = res["counts"]
check("the quick shred finds each kind", c["Requirement"] >= 3 and c["Instruction (L)"] >= 5 and c["Evaluation (M)"] >= 2, c)
k = {r["id"]: r["kind"] for r in res["rows"]}
check("... by where each sits and its words", k.get("C.1-01") == "Requirement" and k.get("L.4.1-01") == "Instruction (L)"
      and k.get("M.2-01") == "Evaluation (M)" and k.get("L.1-01") == "Instruction (L)", k)
check("... information the Government gives is not a requirement", "C.2.2-02" not in k)
xl = os.path.join(tmp, "draft.xlsx")
n = SQ.export(res, xl)
ws = openpyxl.load_workbook(xl).active
hdr = [x.value for x in ws[1]]
check("the draft compliance matrix: one row per requirement, the matrix's columns", n == len(res["rows"]) and ws.max_row == n + 1
      and hdr[:4] == ["ID", "Kind", "Section", "Section title"], (n, ws.max_row, hdr))

from skqt import mainwin as MW
check("the quick shred is no page of its own (4.54.0: Shred's table); the Matrix with Matrix & Outline", "shredreq" not in MW.RAIL_OF
      and "shredlist" in MW.REVIEW_VIEWS and MW.RAIL_OF["matrix"] == "matrix")
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
check("... and no Quick shred page in the window", "shredreq" not in w.pages and not hasattr(w, "shred_page"))

# Compare
def doc(path, paras):
    d = docxw.Doc(); d.heading("1.1 Kestrel Approach", 2)
    for p in paras:
        d.para(p)
    d.save(path)
    return path


a = doc(os.path.join(tmp, "Kestrel Volume I v1.docx"), ["The bus carries two batteries.", "Telemetry closes with margin.", "The team meets weekly."])
b = doc(os.path.join(tmp, "Kestrel Volume I v2.docx"), ["The bus carries three batteries.", "Archive retention lasts ninety days for every ground contact.", "Telemetry closes with margin."])
w.go("compare"); app.processEvents()
cs = w.compare_space
check("one Compare space: Customer versions and Any two files", w.stack.currentWidget() is cs and cs.tabs.count() == 2
      and cs.tabs.tabText(0) == "Customer versions" and cs.tabs.tabText(1) == "Any two files")
r = cs.show_files(a, b)
check("any two files: changed, added, removed", r and r["counts"]["changed"] == 1 and r["counts"]["added"] == 1 and r["counts"]["removed"] == 1
      and cs.tabs.currentIndex() == 1, r and r["counts"])
check("... only the changes listed, under their heading", cs.files.t.rowCount() == 3 and cs.files.t.item(0, 1).text() == "1.1 Kestrel Approach")
red = cs.files.export(os.path.join(tmp, "redline.docx"))
import zipfile
check("the redline in Word", red and "batteries" in zipfile.ZipFile(red).read("word/document.xml").decode("utf-8"))
from skqt import toolshome as TH
uses = [k_ for k_, _t in TH.uses_for([a, b])]
check("two files on Quick tools: Compare first; one file: Shred to setup (4.54.0: the door's route, which takes several)", uses[0] == "compare"
      and "shred" in [k_ for k_, _t in TH.uses_for([rfp])])
w.go("tools"); app.processEvents()
check("... Compare opens with both picked", w.tools_page.files_in([a, b], use="compare") == "compare" and w.stack.currentWidget() is cs
      and cs.files.older.currentData() == a and cs.files.newer.currentData() == b)
ck = w.checks_page
ck.pick_file(ck.older, a); ck.pick_file(ck.newer, b)
w.go("checks"); app.processEvents()
cs.tabs.setCurrentIndex(0)
got = ck.open_compare()
check("Final Checks: Open in Compare", got and w.stack.currentWidget() is cs and cs.tabs.currentIndex() == 1)
check("guide topics: Compare; no Quick shred topic (4.54.0)", "shredreq" not in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC
      and "compare" in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC)
w.close()
n = sum(checks)
print(f"QT SHRED AND COMPARE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
