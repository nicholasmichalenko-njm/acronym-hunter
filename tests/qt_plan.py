"""3.1.0 planning, offscreen: Schedule from due date... on Effort Home previews every stage's dates and sets them;
opening an effort shows what the others did since your last visit (toast and Effort Home card, Got it hides it); Page
budget... in Review and Structure splits a volume's limit across its sections and saves with the structure, and the
Response Setup documents print it; My work lists one person's work across efforts and opens a row in its effort."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, effortrec as RR, pagebudget as PB, sincelast as SL, setupdoc as SD
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
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
r0 = RR.Record(ws0.root); r0.data["due"] = (datetime.date.today() + datetime.timedelta(days=60)).isoformat() + "T14:00"; r0.save()
SL.mark_opened(ws0.root, SL.me(), "2026-01-01T08:00")                      # an earlier visit by this person
r0 = RR.Record(ws0.root); r0.log("task", "Task added: Draft the risk section", who="alee"); r0.save()
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf",)]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
toasts = []
_t = w.toast
w.toast = lambda text: (toasts.append(text), _t(text))


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the effort opens", w.open_effort("Kestrel"))
check("since your last visit: a toast says who changed what", any("1 change by alee" in t for t in toasts), toasts)
w.go("home"); app.processEvents()
hp = w.home_page
check("... and Effort Home lists it", hp.since_card.isVisibleTo(w) and "1 change by alee" in hp.since_card.title.text(), hp.since_card.title.text())
hp.since_done(); app.processEvents()
check("Got it hides it", not hp.since_card.isVisibleTo(w) and w.since is None)
# schedule
dlg = hp.schedule_dialog(run=False)
plan = dlg.preview()
due = RR.parse_when(RR.Record(w.ws.root).data["due"]).date()
check("Schedule from due date: every stage dated before anything changes", len(plan) == 7 and plan[-1][2] == due
      and dlg.table.item(6, 3).text().endswith(str(due.year)) and not RR.Record(w.ws.root).stages[0].get("planned_end"))
dlg.spins[1][1].setValue(15); app.processEvents()
check("... changing a stage's days moves the dates before it", dlg.plan[0][1] < plan[0][1])
dlg.fitr.setChecked(True); app.processEvents()
check("... Fit between today and the due date starts today (or the next working day)", dlg.plan[0][1] >= datetime.date.today()
      and (dlg.plan[0][1] - datetime.date.today()).days <= 3, dlg.plan[0])
n = dlg.apply()
rec = RR.Record(w.ws.root)
check("Set the dates writes every stage's planned start and end", n == 7 and all(s.get("planned") and s.get("planned_end") for s in rec.stages)
      and rec.stages[-1]["planned_end"] == due.isoformat())
dlg2 = hp.schedule_dialog(run=False)
dlg2.save_defaults()
check("Save as the team's defaults keeps the days for the next effort", os.path.isfile(os.path.join(cfg, "schedule_defaults.json")))
# page budget
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("the matrix starts", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
labs = SD.labels(M)
b = w.assign_page.budget_dialog(run=False)
check("Page budget...: one table per volume, from the structure", b.vol.count() == 2 and b.table.rowCount() == 3, (b.vol.count(), b.table.rowCount()))
b.limit.setValue(30)
got = b.split("even")
check("Split evenly: the limit across the sections under the volume heading", got == {"1.1 Technical Approach": 15.0, "1.2 Risk": 15.0}, got)
check("... the total against the limit", "every page given" in b.totals.text(), b.totals.text())
b.spins["1.2 Risk"].setValue(17)
check("... over the limit says so", "2 over the limit" in b.totals.text(), b.totals.text())
b.spins["1.2 Risk"].setValue(15)
b.save()
check("saved with the structure, and the typed limit", PB.pages(M, "1.1 Technical Approach") == 15 and PB.limit_for(M, labs[0]) == (30, "set here"))
w.review.undo_last()
check("one Undo takes the budget back", PB.pages(M, "1.1 Technical Approach") is None)
b = w.assign_page.budget_dialog(run=False); b.limit.setValue(30); b.split("even"); b.save()
from PySide6.QtWidgets import QPushButton
check("Structure has Page budget... too", any(x.text() == "Page budget..." for x in w.structure_page.findChildren(QPushButton)))
SD.set_people(M, "1.1 Technical Approach", "A. Lee", "")
out = os.path.join(tmp, "setup"); os.makedirs(out)
SD.export(M, out)
txt = ""
for root, _d, fs in os.walk(out):
    for f in fs:
        if f.endswith(".docx"):
            import zipfile
            txt += zipfile.ZipFile(os.path.join(root, f)).read("word/document.xml").decode("utf-8", "replace")
check("the Response Setup documents print each section's page budget", "Page budget: 15 pages" in txt, len(txt))
w.save_now()
# my work
w.people = lambda: ["A. Lee"]
r1 = RR.Record(w.ws.root); r1.add_task("Draft 1.1", owner="A. Lee", due="2020-01-01", who="x"); r1.save()
w.go("mywork"); app.processEvents()
pg = w.mywork_page
pg.who.clear(); pg.who.addItems(["A. Lee", "K. Park"]); pg.who.setCurrentText("A. Lee")
rows = pg.load()
check("My work: one person's work across efforts", pg.rows and any(r["kind"] == "task" and r["late"] for r in pg.rows)
      and True, [(r["kind"], r["text"]) for r in pg.rows])
sec = [x for w_ in pg.work for x in w_["sections"]]
check("... with the sections they lead and their page budgets", any(x["label"] == "1.1 Technical Approach" and x["role"] == "lead" and x["pages"] == 15 for x in sec), sec)
check("... late items on top, in red, and counted", pg.rows[0]["late"] and "1 late" in pg.summary.text(), pg.summary.text())
w.go("settings")
check("double-click opens the item in its effort", pg.open_row(0) and w.stack.currentWidget() is w.home_page)
x = pg.export(os.path.join(tmp, "mw.xlsx"))
check("Export: a workbook", os.path.isfile(x))
w.close()
t = sum(checks)
print(f"QT PLAN {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
