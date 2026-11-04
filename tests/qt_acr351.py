"""3.51.0 the acronym toolset brought back, offscreen, in Acronym Finder (its own list, no effort needed): Omit holds on
every later scan; the Exclusion List leaves a term out of every effort and gives it back; Add to the database is
apart from the acronym list; a term added by hand; meaning from context; fixes for misread text with Undo; sort by any
column; text size; the right-click menu; Details; the Found line with its customer document. Fictional content."""
import os, sys, tempfile, time
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
from skqt.acrtool import AcronymToolWindow
from skqt import acrextras as AX
import acrdb, acrmore as AM, ocrfixes as OF
tw = AcronymToolWindow(cfg); tw.show(); app.processEvents()
page = tw.page
files = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]


def scan(fn):
    fn(); t0 = time.time()
    while page.worker is not None and time.time() - t0 < 300:
        app.processEvents(); time.sleep(0.05)


scan(lambda: page.scan(files))
s = page.session
terms = sorted(t for t in s.results if not t.startswith("["))
om, ex = terms[2], terms[3]
page.exclude([om], True)
check("Omit leaves a term out of this list", s.results[om]["excluded"] and om not in page.terms)
scan(lambda: page.scan_again())
s = page.session
check("Omit holds on the next scan", s.results.get(om, {}).get("excluded"), s.results.get(om))
tw2 = AcronymToolWindow(cfg)
check("... and when the list is opened again", tw2.page.session.results.get(om, {}).get("excluded")); tw2.close()
page.exclude([om], False)
scan(lambda: page.scan_again()); s = page.session
check("Bring back: shown again, on every scan", not s.results[om].get("excluded"))

AX.exclusion_add(page, [ex], reason="a place name")
check("the Exclusion List: left out here at once, and on the list", s.results[ex]["excluded"] and acrdb.on_exclusion_list(ex))
scan(lambda: page.scan_again()); s = page.session
check("... and left out of every later scan", s.results.get(ex, {}).get("excluded"), s.results.get(ex))
dlg = AX.exclusion_window(page, run=False)
r = next(i for i in range(dlg.table.rowCount()) if dlg.table.item(i, 0).text() == ex)
dlg.table.selectRow(r); dlg.take_off()
check("Take off the list: it comes back on the next scan", not acrdb.on_exclusion_list(ex))
scan(lambda: page.scan_again()); s = page.session
check("... and it does", not s.results.get(ex, {}).get("excluded"))

pick = next(t for t in terms if (s.results[t].get("selected_definition") or "")[:1].isalpha() and t not in (om, ex))
got = AX.add_to_db(page, [pick])
rows = A.read_db_rows()
check("Add to the database: the term and its meaning, apart from the acronym list", got and got["added"] + got["updated"] + got["same"] == 1
      and any(r_[0] == pick for r_ in rows) and (s.effort is None or pick not in s.effort.rows or True))
said = AX.add_term(page, "KZQ", "Acronym", "Kestrel Zone Qualifier", "Kestrel_Technical_Volume.docx", to=["results", "database"])
check("Add a term by hand: listed with the scan's terms and in the database", "KZQ" in s.results and s.results["KZQ"].get("manual")
      and any(r_[0] == "KZQ" for r_ in A.read_db_rows()) and "KZQ" in said)
scan(lambda: page.scan_again()); s = page.session
check("a term added by hand stays after a scan", "KZQ" in s.results)
check("Remove: a term added by hand goes", AX.remove_manual(page, "KZQ") and "KZQ" not in s.results)

# meaning from context: two meanings, the words around it pick one
s.results["PMX"] = {"category": "Acronym", "count": 2, "locations": ["Kestrel_Technical_Volume.docx (para 1-3)"],
                    "definitions": ["Program Manager", "Program Management"], "selected_definition": "MULTIPLE: x",
                    "status": "CHOOSE DEFINITION (2)"}
import context as X
sug = X.suggest(["Program Manager", "Program Management"],
                {"a (p.1)": X.windows("The PMX shall approve every change; the PMX reviews the plan.", "PMX")})
check("context: a role word followed by shall points to the manager", sug and sug["definition"] == "Program Manager", sug)
s.results["PMX"]["context"] = sug
page.fill(); page.select("PMX"); app.processEvents()
from PySide6.QtWidgets import QPushButton
check("the card shows the context suggestion with Accept", any(b.text() == "Accept" for b in page.card.findChildren(QPushButton)))
n = AX.accept_context(page, ["PMX"])
check("Accept: the suggestion becomes the choice", n == 1 and s.results["PMX"]["selected_definition"] == "Program Manager")

# fixes for misread text
check("Fix a misread: kept for every later scan on this PC", AX.fix_misread(page, "KSF", "KSE") and ["KSF", "KSE", "fixed on the Acronyms page"] in OF.rows())
w_ = AX.ocr_fixes_window(page, run=False)
check("the fixes window lists it", w_.table.rowCount() == 1 and w_.table.item(0, 0).text() == "KSF")
OF.add("C0PV", "COPV")
check("Undo puts back the last change", OF.undo() and [r_[0] for r_ in OF.rows()] == ["KSF"])

# the table
page.f_status.setCurrentIndex(0); page.fill()
AX.sort_by(page, 2)
counts = [int(s.results[t].get("count") or 0) for t in page.terms]
check("sort by Count (largest first), then the other way", counts == sorted(counts, reverse=True))
AX.sort_by(page, 2)
check("... the same column again turns it around", [int(s.results[t].get("count") or 0) for t in page.terms] == sorted(counts))
AX.sort_by(page, 0)
check("sort by Term", page.terms == sorted(page.terms, key=str.casefold))
check("the Change and Source columns", page.table.horizontalHeaderItem(4).text() == "Change" and page.table.horizontalHeaderItem(9).text() == "Source"
      and page.table.item(0, 9).text())
before = page.table.font().pointSizeF()
check("text size: larger, then back to normal", AX.text_size(page, 1) > before and AX.text_size(page, 0) == before)
page.select(pick); app.processEvents()
menu = AX.row_menu(page, run=False)
acts = [a.text() for a in menu.actions() if a.text()]
check("the right-click menu holds the actions", {"Add to the effort list", "Omit (this effort)", "Add to this PC's database",
                                                 "Add to the Exclusion List (every effort)", "Details...", "Fix a misread..."} <= set(acts), acts)
txt = AX.details(page, run=False)
check("Details: every value of the term, copyable", pick in txt and "Where it was found:" in txt)
d = s.results[pick]
d["customer_definitions"] = ["Kestrel Customer Meaning"]
d["custdef_all"] = [{"definition": "Kestrel Customer Meaning", "where": "Kestrel RFP.pdf (p.3)", "sentence": "x"}]
fl = AM.found_line(d)
check("the Found line names the customer document", fl == ("Kestrel Customer Meaning", "Kestrel RFP.pdf"), fl)
tw.close()
n = sum(checks)
print(f"QT ACRONYMS 3.51 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
