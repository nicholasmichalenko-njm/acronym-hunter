"""2.84.0 read and assign any document, offscreen: a library document that does not build the matrix is in Assign's
file list; it opens on the same page beside the same structure with its own buttons; C attaches the selected sentence
as context for the target section (the structure counts it, the page tags it), F to a requirement (its card shows it),
N, Q and T make a note, a question and a task in the effort record quoting it, R makes it a compliance requirement in
the target section with its document, X takes attachments off; a renamed section keeps its context; Response Setup
carries the context under its section; Library lists what was taken, exports it and opens one in Assign."""
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
import compliance as C, effort as E, workspace as W, docversions as DV, docintake as DI, effortrec as R, ctxdocs as CX
import office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
B = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.read_page.read([os.path.join(B, "Section_L_print.pdf")], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
# the SOW as a context document in the library (a copy kept with the effort)
lib = DV.Library(ws.p("documents")).load()
sow = os.path.join(B, "SOW.pdf")
d, v = lib.add(sow, DI.read(sow), doc_name="Statement of Work", category="qa", role="context")
ap = w.assign_page
ap.load()
labs = [ap.files.itemText(i) for i in range(ap.files.count())]
lab = next((x for x in labs if x.startswith("Library: Statement of Work")), None)
check("the library document is in Assign's file list", lab is not None, labs)
ap.files.setCurrentText(lab); app.processEvents()
check("it opens on the page with its own buttons", ap.cx is not None and ap.ctx_grid.isVisibleTo(ap) and not ap.dec_grid.isVisibleTo(ap)
      and len(ap.view.boxes) > 10 and "From the library" in ap.target_lbl.text(), len(ap.view.boxes))
first = ap.cx.rows[3]["id"]
ap.set_target("1.1 Technical Approach")
ap.select(first); app.processEvents()
from PySide6.QtWidgets import QLabel
cardtext = " ".join(x.text() for x in ap.card.findChildren(QLabel))
check("a sentence's card: its document and version, not attached yet", "Not attached" in cardtext and "Document: Statement of Work" in cardtext)
ap.do_ctx()
st = CX.Store(ws.root).load()
check("C: context for the target section", len(st.for_section("1.1 Technical Approach")) == 1 and st.att[0]["iid"] == first)
node = ap.tree.findItems("1.1 Technical Approach", __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchRecursive | __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchContains, 0)[0]
check("the structure counts it", node.text(2) == "1", node.text(2))
check("the page tags it in the margin", any("CTX 1.1" in l.text() for l in ap.labels))
import teampack as TP                                      # 2.89.0: the team's topics, one click each
TP.save_topics(cfg, ["Thermal", "Schedule"])
ap.select(first); app.processEvents()
btns = getattr(ap.cx, "team_topic_btns", [])
check("the team's topics are offered on the card", [b.text() for b in btns] == ["+ Thermal", "+ Schedule"], [b.text() for b in btns])
btns[0].click(); app.processEvents()
check("one click tags the context with a team topic", "Thermal" in CX.Store(ws.root).load().att[0]["topics"])
# F to a requirement
M = w.review.M
w.assign_page.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
req = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
ap.select(req["id"]); ap.do_req(); app.processEvents()
ap.files.setCurrentText(lab); app.processEvents()
ap.select(ap.cx.rows[4]["id"])
check("F: context for a requirement", ap.cx.for_requirement(req["id"]) == 1)
ap.files.setCurrentText("Section_L_print.pdf"); app.processEvents(); ap.select(req["id"]); app.processEvents()
check("the requirement's card shows it, with its document", len(ap.lib_labels) == 1 and "Statement of Work" in ap.lib_labels[0].text())
# N, Q, T
ap.files.setCurrentText(lab); app.processEvents()
ap.select(ap.cx.rows[5]["id"])
rec0 = R.Record(ws.root)
n0, t0 = len(rec0.data["notes"]), len(rec0.data["tasks"])
ap.do_record("note"); ap.do_record("question"); ap.do_record("task")
rec = R.Record(ws.root)
qs = [n for n in rec.data["notes"] if n.get("question")]
check("N, Q, T: a note, a question and a task, quoting it", len(rec.data["notes"]) == n0 + 2 and len(rec.data["tasks"]) == t0 + 1 and qs
      and "Statement of Work" in qs[-1]["text"] and ap.cx.rows[5]["id"] in rec.data["tasks"][-1]["notes"])
# R: make it a requirement
ap.set_target("1.2 Risk")
ap.select(ap.cx.rows[6]["id"])
made = ap.do_req()
M = w.review.M
check("R: a compliance requirement in the target section, with its document", made and made[0]["decision"] == "Keep" and made[0]["map"] == "1.2 Risk"
      and "from the library" in made[0]["loc"] and made[0]["file"] == "SOW.pdf", (made[0].get("map"), made[0].get("loc")) if made else None)
check("and it stays a library document in the list", ap.files.currentText() == lab and ap.cx is not None)
# X
ap.select(ap.cx.rows[5]["id"])
check("X: its attachments come off", ap.do_clear() == 3 and not CX.Store(ws.root).load().of_row(d["id"], ap.cx.rows[5]["id"]))
# a renamed section keeps its context
ap.rename_section("1.1 Technical Approach", "Technical Approach and Design")
st = CX.Store(ws.root).load()
new = next(x for x in st.section_counts())
check("a renamed section keeps its context", new.endswith("Technical Approach and Design") and len(st.att) == 3, list(st.section_counts()))
# Response Setup carries it
out = os.path.join(tmp, "setup"); os.makedirs(out)
paths = w.setup_page.export(out) if hasattr(w.setup_page, "export") else []
xml = "".join(zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", "replace") for p in (paths or []))
check("Response Setup carries the context under its section", paths and "From Statement of Work" in xml, paths)
# Library: what was taken
w.go("library"); app.processEvents()
dlg = w.library_page.show_taken(run=False)
check("Library lists what was taken", dlg.fill() == 3 and dlg.table.item(0, 3).text() == "Statement of Work")
xp = dlg.export(os.path.join(tmp, "taken.xlsx"))
import openpyxl
check("and exports it for writers", xp and openpyxl.load_workbook(xp).active.max_row == 4)
dlg.table.selectRow(0)
check("and opens one in Assign", dlg.open_selected() and w.stack.currentWidget() is w.assign_page and ap.cx is not None and ap.cur)
w.go("library"); w.library_page.select(d["id"]); w.library_page.show_doc()
check("the document's panel counts what was taken", "3 sentence(s) taken" in w.library_page.d_taken.text(), w.library_page.d_taken.text())
w.close()
n = sum(checks)
print(f"QT CTXASSIGN PASS ({n}/{len(checks)})" if n == len(checks) else f"QT CTXASSIGN FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
