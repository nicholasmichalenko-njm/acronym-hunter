"""2.92.0 the readable copy, kept current by the Qt window, offscreen: a few seconds after a change the readable copy is
rewritten from the saved files (CSV files, READ ME FIRST, the calendar in Excel, CSV and Outlook, the post-submission
checklist, the banner's details, library documents, what was taken from documents), and with the Effort overview (Word)
when the effort closes or is backed up; Open the readable copy writes it first."""
import datetime, os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_READABLE_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effortrec as RR, readable as RD, branding as BR, effortcal as EC, postsub as PS, docversions as DV, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.show()
L = os.path.join(tmp, "Efforts", "Kestrel", "Kestrel_Effort_List.xlsx")
w.settings_page.new_effort({"name": "Kestrel", "path": L, "client": "USSF SSC", "solicitation": "FA8810-26-R-0042"})
B = os.path.join(A.BASE_DIR, "test_samples", "rfp")
w.read_page.read([os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(os.path.dirname(L), "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
w.save_now()
r = RR.Record(w.ws.root)
r.set_due("2026-12-15T14:00", "Eastern Time")
BR.set_identity(RR.Record(w.ws.root), pm="Dana Ruiz", sensitivity="CUI", fields=[{"label": "Capture manager", "value": "Sam Ortiz"}])
r = RR.Record(w.ws.root)
EC.add_entry(r, kind="Review", date="2026-11-20", start="09:00", end="16:00", zone="MT", title="Red team review", location="Room 2B")
EC.add_entry(RR.Record(w.ws.root), kind="Due", date="2026-11-18", start="17:00", zone="ET", title="Drafts to Production")
PS.data(RR.Record(w.ws.root))
lib = DV.Library(w.ws.p("documents")).load()
cd = shutil.copy2(os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx"), w.efforts.get("Kestrel")["customer_dir"])
lib.add(cd, [{"x": "The Offeror shall describe its approach.", "l": "p.1", "s": "L.3", "t": "Approach"}], doc_name="Kestrel RFP", initial="R", dtype="RFP")
folder = w.open_readable(open_it=False)
names = set(os.listdir(folder)) if folder else set()
check("Open the readable copy writes it beside the effort list", folder == RD.folder_for(L, "Kestrel") and "READ ME FIRST.txt" in names, sorted(names))
want = {"Effort summary.txt", "Effort details.csv", "Calendar.xlsx", "Calendar.csv", "Calendar.ics", "Post-submission checklist.xlsx",
        "Post-submission checklist.csv", "Library documents.csv", "Compliance assignments.csv", "Tasks.csv", "Team.csv", "Effort overview.docx"}
check("everything newer is in it, in Excel, Word, CSV and Outlook files", want <= names, sorted(want - names))
det = open(os.path.join(folder, "Effort details.csv"), encoding="utf-8-sig").read()
check("the banner's details and the submission's time zone", "Dana Ruiz" in det and "CUI" in det and "ET" in det and "Sam Ortiz" in det)
cal = open(os.path.join(folder, "Calendar.csv"), encoding="utf-8-sig").read()
check("the calendar: due dates and events with times and zones", "Red team review" in cal and "Drafts to Production" in cal and "Proposal due" in cal)
ics = open(os.path.join(folder, "Calendar.ics"), encoding="utf-8").read()
check("the Outlook file has exact times (UTC)", "DTSTART:20261215T190000Z" in ics and "DTSTART:20261120T160000Z" in ics)
rd = open(os.path.join(folder, "READ ME FIRST.txt"), encoding="utf-8-sig").read()
check("READ ME FIRST names every file", all(f in rd for f in ("Calendar.xlsx", "Post-submission checklist.xlsx", "Effort overview.docx", "Library documents.csv")))
summ = open(os.path.join(folder, "Effort summary.txt"), encoding="utf-8-sig").read()
check("the summary names the proposal manager and sensitivity", "Proposal manager: Dana Ruiz" in summ and "Sensitivity: CUI" in summ)
# kept current: a change, then quiet, then written in the background
before = os.path.getmtime(os.path.join(folder, "Tasks.csv"))
time.sleep(1.1)
RR.Record(w.ws.root).add_task("Draft volume I", owner="A. Lee", due="2026-11-10")
w.readable_tick(); started = w.readable_tick()
if w._rd_thread is not None:
    w._rd_thread.join(timeout=60)
check("a change is written a few seconds later, in the background", started and "Draft volume I" in open(os.path.join(folder, "Tasks.csv"), encoding="utf-8-sig").read()
      and os.path.getmtime(os.path.join(folder, "Tasks.csv")) > before)
check("nothing more to write until the next change", not w.readable_tick() and not w.readable_tick())
os.remove(os.path.join(folder, "Effort overview.docx"))
w.close_effort()
for th in [w._rd_thread]:
    if th is not None:
        th.join(timeout=60)
check("closing the effort writes the overview again", os.path.isfile(os.path.join(folder, "Effort overview.docx")))
n = sum(checks)
print(f"QT READABLE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT READABLE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
