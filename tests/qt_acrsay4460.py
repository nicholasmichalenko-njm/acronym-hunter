"""4.46.0 offscreen, UX decision 64: a find's saved status and its placeholder definition are said in the page's words
on screen (the Everything found table, the card, Details) and in the files a person exports (the acronym report, the
Acronym Finder's list); what is saved stays as the scan wrote it. Fictional content (the Kestrel program)."""
import csv, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); D.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt.acrtool import AcronymToolWindow
from skqt import acrextras as AX
tw = AcronymToolWindow(cfg); tw.show(); app.processEvents()
page = tw.page
page.scan([os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")])
t0 = time.time()
while page.worker is not None and time.time() - t0 < 300:
    app.processEvents(); time.sleep(0.05)
s = page.session
NEW, PH = "NEW CANDIDATE", "[Not in Database — Definition omitted]"
term = next((t for t in page.terms if s.results[t].get("status") == NEW), None)
if term is None:                                     # the scan found none: one is made so, as the scan writes it
    term = page.terms[0]
    s.results[term].update(status=NEW, selected_definition=PH)
s.results[term]["selected_definition"] = PH
page.fill(); app.processEvents()
row = page.terms.index(term)
check("the Everything found table says the status in the page's words", page.table.item(row, 5).text() == "New, no definition on record",
      page.table.item(row, 5).text())
check("... and the definition placeholder too", page.table.item(row, 6).text() == "No definition on record", page.table.item(row, 6).text())
check("... while what is saved keeps the scan's words", s.results[term]["status"] == NEW and s.results[term]["selected_definition"] == PH,
      s.results[term])
check("... and the saved words still sort the finds", A.status_kind(s.results[term]["status"]) == "candidate")
s.results[term]["effort"] = "In the list"; page.fill(); app.processEvents()
r8 = page.table.item(page.terms.index(term), 8).text() if term in page.terms else "(row gone)"
check("the decision reads Added to effort list on the table, In the list where it is saved", r8 == "Added to effort list" and s.results[term]["effort"] == "In the list", r8)
s.results[term]["effort"] = ""; page.fill(); app.processEvents(); row = page.terms.index(term)
page.select(term); app.processEvents()
pills = [p.text() for p in page.card.findChildren(D.Pill)]
check("the card's pill says it the same way", "New, no definition on record" in pills and NEW not in pills, pills)
txt = AX.details(page, run=False)
check("Details says it the same way", "Status: New, no definition on record" in txt and "Meaning: No definition on record" in txt
      and NEW not in txt and "[Not in Database" not in txt)
# the acronym report (CSV): a person's file
rep = os.path.join(tmp, "report.csv")
page.export(rep)
with open(rep, encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))
got = next((r for r in rows[1:] if r[0] == term), [])
check("the acronym report says the status and placeholder in the page's words", got and got[4] == "New, no definition on record"
      and got[5] == "No definition on record", got)
check("... its headings unchanged", rows[0][:6] == ["Term", "Type", "Count", "Change", "Status", "Selected definition"], rows[0])
# the Acronym Finder's list (Word, Excel or CSV): a person's file
lp = os.path.join(tmp, "list.csv")
tw.export(lp)
with open(lp, encoding="utf-8-sig") as f:
    lrows = list(csv.reader(f))
got = next((r for r in lrows[1:] if r[0] == term), [])
check("the Acronym Finder's list says the placeholder in the page's words", got == [term, "No definition on record"], got)
check("... and the saved definition is unchanged", s.results[term]["selected_definition"] == PH)
tw.close()
n = sum(checks)
print(f"QT ACRSAY 4460 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
