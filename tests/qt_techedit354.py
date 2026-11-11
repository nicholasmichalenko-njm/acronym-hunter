"""3.54.0 Technical Edit in its own space, offscreen: a draft reviewed on Unfiled; filters; the selected finding shown;
Accept, Skip here (kept for the next review), Skip in this effort (the rule off), Add to the style sheet (a term, a word);
Make the edited copy (tracked changes, the draft unchanged); readability by section; the style sheet's terms, rules and
words, exported for authors; Copy review from Your Tools; Technical Edit in the menu. Fictional content."""
import hashlib, os, sys, tempfile
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
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
import docxw, unfiled as UF, zipfile
d = docxw.Doc()
d.heading("2.1 Kestrel Operations", 2)
d.para("The the operations team staffs the ground station around the clock with 4 controllers.")
d.para("Telemetry reaches the web site within seconds, and the website archives it for the client.")
d.para("The anomly process was reviewed by the board, and the tracking tool logs each fault.")
draft = os.path.join(tmp, "Kestrel Volume II.docx"); d.save(draft)
before = hashlib.sha256(open(draft, "rb").read()).hexdigest()

from skqt import mainwin as MW
_write = [k for k, _t in MW.TABS["drafts"]]
check("Technical Edit is the Drafts step's Edit, after Status and Acronyms (4.4.0)", _write.index("techedit") == _write.index("draftacr") + 1 == _write.index("drafts") + 2)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
w.rail_go("techedit"); app.processEvents()
pg = w.techedit_page
check("from the menu with nothing open: Technical Edit on Unfiled", w.effort_name == UF.NAME and w.stack.currentWidget() is pg)
found = pg.add_files([draft], run=True)
rules = {f["rule"] for f in found}
check("Review: findings for the draft", {"doubled", "numbers_small", "variants", "passive", "customer_terms", "spelling"} <= rules, rules)
check("... the table lists them, Fix and Check", pg.t.rowCount() == len(found) and "Fix" in pg.sum.text())
check("readability by section", pg.st.rowCount() == 1 and pg.st.item(0, 0).text() == "2.1 Kestrel Operations")
pg.f_level.setCurrentText("Fix")
check("filter: Fix only", pg.t.rowCount() == sum(1 for f in found if f["level"] == "Fix") and pg.t.rowCount() > 0)
pg.f_level.setCurrentText("Fix and Check")


def row_of(rid):
    return next(i for i in range(pg.t.rowCount()) if next(f for f in pg.found if f["key"] == pg.t.item(i, 0).data(0x0100))["rule"] == rid)


pg.t.selectRow(row_of("doubled")); app.processEvents()
check("the selected finding: its sentence with the words marked, the suggestion", "The the" in pg.detail.toPlainText()
      and "Suggested: The" in pg.detail.toPlainText())
check("Accept", pg.mark("Accepted") == 1 and pg.b_copy.isEnabled())
pg.t.selectRow(row_of("numbers_small")); pg.mark("Accepted")
pg.t.selectRow(row_of("passive")); app.processEvents()
pkey = pg.selected()[0]["key"]
pg.mark("Skipped")
check("Skip here: kept for the next review", pkey in pg.sheet()["skips"] and not any(f["key"] == pkey for f in pg.run()))
pg.t.selectRow(row_of("customer_terms")); app.processEvents()
pg.rule_off()
check("Skip in this effort: the rule off, and off on the next review", "customer_terms" in pg.sheet()["off"]
      and not any(f["rule"] == "customer_terms" for f in pg.run()))
pg.t.selectRow(row_of("spelling")); app.processEvents()
word = pg.selected()[0]["hit"]
pg.to_sheet()
check("Add to the style sheet: a word the spelling check did not know is known", word in pg.sheet()["words"]
      and not any(f["rule"] == "spelling" and f["hit"] == word for f in pg.run()))
pg.t.selectRow(row_of("variants")); app.processEvents()
pg.to_sheet()
check("... a term: the written form flagged, the right one suggested", pg.sheet()["terms"].get("web site") == "website")
for f in pg.found:
    if f["rule"] in ("doubled", "numbers_small"):
        pg.status[f["key"]] = "Accepted"
out = pg.make_copy(os.path.join(tmp, "edited.docx"))
z = zipfile.ZipFile(out)
doc = z.read("word/document.xml").decode("utf-8")
check("Make the edited copy: tracked changes and comments", out and "<w:del " in doc and "<w:ins " in doc and "word/comments.xml" in z.namelist())
check("... the draft is unchanged", hashlib.sha256(open(draft, "rb").read()).hexdigest() == before)
pg.tabs.setCurrentIndex(1); pg.fill_sheet(); app.processEvents()
check("Style sheet: terms, rules and words", pg.terms.rowCount() == 1 and pg.words.count() == 1
      and any(pg.rules.item(i).checkState() == __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Unchecked for i in range(pg.rules.count())))
pg.add_term("Kestrel bus", "Kestrel spacecraft bus")
check("... Add a term", pg.sheet()["terms"].get("kestrel bus") == "Kestrel spacecraft bus" and pg.terms.rowCount() == 2)
it = next(pg.rules.item(i) for i in range(pg.rules.count()) if pg.rules.item(i).data(0x0100) == "customer_terms")
from PySide6.QtCore import Qt
it.setCheckState(Qt.Checked)
check("... ticking a rule turns it back on", "customer_terms" not in pg.sheet()["off"])
sp = pg.export_sheet(os.path.join(tmp, "Style sheet.docx"))
txt = zipfile.ZipFile(sp).read("word/document.xml").decode("utf-8")
check("Export the style sheet: a Word file for authors", "Kestrel spacecraft bus" in txt and "one to nine spelled out" in txt)
# Your Tools
from skqt import toolshome as TH
check("Copy review is offered for a Word file on Your Tools", "copyreview" in {k for k, _t in TH.uses_for([draft])}
      and "copyreview" not in {k for k, _t in TH.uses_for([os.path.join(tmp, "x.pdf")])})
w.go("tools"); app.processEvents()
pg.found = []
check("... and runs Technical Edit on it", w.tools_page.files_in([draft], use="copyreview") == "copyreview"
      and w.stack.currentWidget() is pg and pg.found)
check("Technical Edit has a Guide topic", "techedit" in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC)
w.close()
n = sum(checks)
print(f"QT TECHNICAL EDIT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
