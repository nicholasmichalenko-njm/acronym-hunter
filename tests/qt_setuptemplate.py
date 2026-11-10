"""3.24.0 Make templates and setup, offscreen: Response Setup has the button; the dialog lists Ready to make and the
reference styles; making writes a template per volume and the setup on it into the effort's setup folder, records the
template on the effort, and keeps the chosen styles with the matrix."""
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
import setupdoc as SD, setuptemplate as ST, zipfile
from skqt.setuppage import MakeDialog
keep = [it for it in M.items if it.get("decision") == "Keep"] or M.items[:3]
for it in M.items[:4]:
    it["decision"] = "Keep"
SD.place(M, M.items[0]["id"], "1.1 Technical Approach")
SD.place(M, M.items[1]["id"], "2.1 Program Management")
w.go("setup"); app.processEvents()
sp = w.setup_page
d = MakeDialog(sp, ST.ready(M, None), ST.options(M))
check("the dialog lists Ready to make and a style for each kind of reference text", len(d.rows) == len(ST.KINDS)
      and d.rows["rfp"][0].text() == "SK RFP Requirement" and d.rows["rfp"][1].isChecked())
opts = d.values(); opts["pm"]["hidden"] = False
out = sp.make_on_templates(opts=opts, go=True)
check("a template per volume and the setup written on each", out and len(out) == 2 and all(os.path.isfile(x["setup"]) for x in out), out)
check("into the effort's folders, templates in their own folder", out and all(os.path.basename(os.path.dirname(x["template"])) == "Templates" for x in out)
      and os.path.dirname(os.path.dirname(out[0]["template"])) == os.path.dirname(out[0]["setup"]), out and out[0])
check("the effort records the templates it used", [u["name"] for u in w.ws.get("templates_used", [])][-2:] == [x["template_name"] for x in out])
pl_ = ST.plan(M, cfg, w.ws, w.effort_name or "", w.efforts.get(w.effort_name) or {})
check("the chosen styles are kept as this effort's content map (3.33.0)", ST.options(M, pl_[0]["std"])["pm"]["hidden"] is False
      and ((w.ws.get("prod_std", {}) or {}).get("over") or {}).get("content_map", {}).get("pm", {}).get("hidden") is False)
doc = zipfile.ZipFile(out[0]["setup"]).read("word/document.xml").decode()
check("the placed sentence is in the setup, in its hidden style", 'w:val="SKRFPRequirement"' in doc and M.items[0]["text"][:25] in doc.replace("&amp;", "&"))
print(f"QT SETUP ON TEMPLATE {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.stdout.flush()
w.close()
__import__("hangguard").end(0 if all(checks) else 1)
