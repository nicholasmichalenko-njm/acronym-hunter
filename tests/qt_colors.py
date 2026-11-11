"""3.18.1 every choice in Review has its own color on the page, offscreen: L, M and SOW requirements, support, the
customer's and ignored each fill with their own color; undecided stays plain; Ignore (X) is a decision of its own (grey,
IGNORED in the margin, counted as decided, skipped by Select undecided) and Delete takes a decision off; a sentence
something was captured from (a key date, a task) gets the capture outline and says what in the margin, kept with the
effort; an accepted Ignore suggestion is ignored; the decide buttons and the legend carry the same colors."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, compliance as C, pagemarks as PM, suggestrules as SR
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Heron").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Heron")
w.read_page.read([PDF], os.path.join(ED, "Heron_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
pg = w.assign_page
M = w.review.M
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
rows = [it for it in M.items if it.get("file") == "Section_L_print.pdf" and not it.get("decision") and it.get("type") != "Heading"
        and it["id"] in pg.view.boxes]
check("a document with undecided sentences to try", len(rows) >= 10, len(rows))
far = rows[-1]["id"]


def decide(it, fn):
    pg.select(it["id"]); app.processEvents(); fn(); app.processEvents()


def fill(iid):
    pg.select(far); app.processEvents()             # nothing of the sentence selected: its own color shows
    c = pg.view.boxes[iid].brush().color()
    return c.name(), c.alpha()


decide(rows[0], lambda: pg.do_lm("L"))
decide(rows[1], lambda: pg.do_lm("M"))
decide(rows[2], pg.do_sow)
decide(rows[3], pg.do_ctx)
decide(rows[4], pg.do_customer)
decide(rows[5], pg.do_clear)
got = {k: fill(rows[i]["id"]) for i, k in enumerate(("L", "M", "SOW", "Support", "Customer's", "Ignored"))}
names = [v[0] for v in got.values()]
check("every decision fills with its own color", len(set(names)) == 6 and all(a > 0 for _n, a in got.values()), got)
check("... L, M and SOW in their designation's colors", got["L"][0] == D.PAGE_LM["L"].lower() and got["M"][0] == D.PAGE_LM["M"].lower()
      and got["SOW"][0] == D.PAGE_LM["C"].lower(), got)
check("undecided stays plain", fill(rows[6]["id"])[1] == 0)
ign = rows[5]
check("X: Ignore is a decision of its own (Not used in the matrix)", ign["decision"] == "Drop" and C.progress([ign])["decided"] == 1)
check("... grey on the page with IGNORED in the margin", got["Ignored"][0] == D.PAGE_DEC["Drop"].lower()
      and any(l.text().startswith("IGNORED") for l in pg.labels))
pg.select_undecided(); app.processEvents()
sel = {it["id"] for it in pg.selected()}
check("Select undecided skips ignored sentences", ign["id"] not in sel and rows[6]["id"] in sel)
decide(ign, pg.do_undecide)
check("Delete takes a decision off: undecided and plain again", ign["decision"] == "" and fill(ign["id"])[1] == 0)
decide(ign, pg.do_clear)
# captures mark the sentence
cap = rows[7]
pg.select(cap["id"]); app.processEvents()
pg.do_capture("keydate", answer={"kind": "Orals", "title": "Orals", "date": "2026-12-01", "start": "10:00", "zone": "ET"})
pg.select(far); app.processEvents()
b = pg.view.boxes[cap["id"]]
check("a capture marks its sentence: the capture outline and a light fill", b.pen().color().name() == D.CAPTURE_COLOR.lower()
      and b.brush().color().name() == D.CAPTURE_COLOR.lower() and b.brush().color().alpha() > 0)
check("... and says what in the margin", any(l.text() == "DATE" for l in pg.labels), [l.text() for l in pg.labels][:12])
pg.add_work("task", cap["id"], answer={"text": "Plan the orals rehearsal", "owner": "", "due": ""}); app.processEvents()
check("a task on the sentence adds to it", any(l.text() == "DATE, TASK" for l in pg.labels))
decide(cap, lambda: pg.do_lm("L"))
pg.select(far); app.processEvents()
b = pg.view.boxes[cap["id"]]
check("decided and captured: its decision's fill, the capture outline", b.brush().color().name() == D.PAGE_LM["L"].lower()
      and b.pen().color().name() == D.CAPTURE_COLOR.lower())
check("marks are kept with the effort", PM.load(w.ws).get(cap["id"]) == ["keydate", "task"], PM.load(w.ws))
pg.marks = {}
check("... and found again when Review opens (tasks from the record too)", pg.load_marks().get(cap["id"]) == ["keydate", "task"])
# an accepted Ignore suggestion is ignored
z = rows[8]
pg.sg_on = True
pg.sg[z["id"]] = {"cat": "ignore", "why": "test", "clear": False, "rule": "", "state": "shown"}
pg.accept_suggestions(rows=[z]); app.processEvents()
check("an accepted Ignore suggestion is ignored, and agrees", z["decision"] == "Drop" and SR.category(z, pg.sg[z["id"]]) == "ignore"
      and pg.sg[z["id"]]["state"] == "accepted")
pg.sg_btn.click(); pg.sg_btn.click(); app.processEvents()
# headings are not shown as ignored
h = next((it for it in M.items if it.get("type") == "Heading" and it.get("decision") == "Drop" and it["id"] in pg.view.boxes), None)
if h is not None:
    pg.select(far); app.processEvents()
    check("an RFP heading is not shown as ignored", pg.view.boxes[h["id"]].brush().color().name() == D.PAGE_DEC["Heading"].lower())
# the buttons and the legend
check("the decide buttons carry the colors", pg.keys["M"].property("kind") == "lmM" and pg.keys["Requirement"].property("kind") == "lmS"
      and pg.keys["Ignore"].property("kind") == "drop" and pg.cap_keys["keydate"].property("kind") == "cap")
check("the legend names every color", all(n in pg.legend.text() for n, _c in D.LEGEND) and "Not decided" in pg.legend.text())
w.close()
n = sum(checks)
print(f"QT COLORS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
