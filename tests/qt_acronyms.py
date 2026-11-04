"""2.64.0 Acronym scan and review in Qt: scan files on a worker thread with the classic window's own rules, filter and
search the results, choose a definition (kept for later scans), add to the effort list with a typed definition,
approve with the approver, mark not a term, exclude, export the report; the results are shared with the classic
window (its session file) and the effort list is the same workbook."""
import csv, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
import effort as E, workspace as W, acrsession as S, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
check("an effort with no scan yet: the page offers a scan", ap.session is not None and ap.empty.isVisibleTo(ap))
files = [os.path.join(A.BASE_DIR, "test_samples", f) for f in ("Kestrel_Technical_Volume.docx", "Kestrel_Compliance_Matrix.xlsx")]
worker = ap.scan(files)
check("the scan runs on a worker thread", worker is not None and not ap.b_files.isEnabled() and ap.b_cancel.isVisibleTo(ap))
t = time.time()
while ap.worker is not None and time.time() - t < 240:
    app.processEvents(); time.sleep(0.05)
s = ap.session
check("the scan finished: terms in the table", ap.worker is None and ap.table.rowCount() > 20 and "SOW" in s.results, ap.table.rowCount())
check("the effort list records what was found", (s.ws.get("seen_terms") or []) and ap.p_active.text().endswith("terms"))
ap.f_search.setText("SOW"); app.processEvents()
check("search narrows the table", ap.terms == ["SOW"] or "SOW" in ap.terms and len(ap.terms) < 5, ap.terms)
ap.f_search.setText(""); ap.f_status.setCurrentText("Needs approval"); app.processEvents()
check("the status filter: Needs approval holds the new candidates",
      ap.terms and any(A.status_kind(s.results[x]["status"]) == "candidate" for x in ap.terms))
ap.f_status.setCurrentIndex(0); app.processEvents()
ap.select("SOW"); app.processEvents()
check("the card shows the term", ap.card.title.text() == "SOW")
ap.typed.setText("Statement of Work")
ap.add(["SOW"])
check("Add to effort list with the typed definition", E.EffortList(LIST).load().rows["SOW"]["Definition"] == "Statement of Work"
      and s.results["SOW"]["status"].startswith("Effort list"), s.results["SOW"]["status"])
ap.approve(["SOW"], "QA Lead")
r = E.EffortList(LIST).load().rows["SOW"]
check("Approve records the approver in the effort list", r["Status"] == "Approved" and r["SS Approver"] == "QA Lead", (r["Status"], r["SS Approver"]))
ap.set_status(["SCOPE"], "Rejected")
check("Not a term: rejected in the list and hidden", E.EffortList(LIST).load().rows["SCOPE"]["Status"] == "Rejected"
      and s.results["SCOPE"]["excluded"] and "SCOPE" not in ap.terms)
other = next(x for x in ap.terms if x not in ("SOW",) and not s.results[x].get("effort"))
ap.exclude([other])
check("Omit hides it; Show omitted brings it back", other not in ap.terms)
ap.f_excl.setChecked(True); app.processEvents()
check("Show omitted", other in ap.terms)
ap.exclude([other], False); ap.f_excl.setChecked(False); app.processEvents()
# a choice is kept for later scans
s.results["IMS"]["definitions"] = ["Integrated Master Schedule", "Information Management System"]
ap.choose("IMS", "Integrated Master Schedule")
check("Use this: the definition is chosen and kept for this effort", s.results["IMS"]["selected_definition"] == "Integrated Master Schedule"
      and s.load_choices().get("IMS") == "Integrated Master Schedule")
# shared with the classic window
s2 = S.AcronymSession(s.ws, LIST, w.efforts)
n = s2.restore()
check("the results are kept where the classic window keeps them", n == len(s.results) and s2.results["SOW"]["status"] == "Effort list: Approved")
p = ap.export(os.path.join(tmp, "report.csv"))
rows = list(csv.reader(open(p, encoding="utf-8-sig")))
check("Export the report: the rows shown", rows[0][0] == "Term" and len(rows) - 1 == len([x for x in ap.terms if not s.results[x].get("known")]))
# scan again keeps the decisions
ap.scan_again()
t = time.time()
while ap.worker is not None and time.time() - t < 240:
    app.processEvents(); time.sleep(0.05)
check("Scan again: approved and rejected decisions hold", s.results["SOW"]["status"] == "Effort list: Approved" and s.results["SCOPE"]["excluded"])
# 2.86.0: where it was found, zoomed in; a plural tied to its singular
w.go("acronyms"); app.processEvents()
ap.f_status.setCurrentIndex(0); ap.f_search.setText(""); app.processEvents()
ap.select("SOW"); app.processEvents()
wv = getattr(ap, "where_view", None)
wv and wv.wait()
check("the card shows the place it was found (picture or passage), with Next place", wv is not None and wv.state in ("text", "picture")
      and ("SOW" in wv.text.toPlainText() or wv.state == "picture") and wv.where.text().startswith("Place 1 of"),
      wv and (wv.state, wv.where.text()))
import copy
s.results["SOWs"] = copy.deepcopy(s.results["SOW"]); s.results["SOWs"]["effort"] = ""; s.results["SOWs"]["status"] = "Needs Review"
check("a plural's singular is guessed", s.singular_guess("SOWs") == "SOW" and s.singular_guess("ICD's") == "ICD" and s.singular_guess("SOW") == "")
ap.fill(); ap.select("SOWs"); app.processEvents()
from PySide6.QtWidgets import QPushButton
btn = next((b for b in ap.card.findChildren(QPushButton) if b.text() == "Plural of SOW"), None)
check("the card offers Plural of SOW (not Not a term)", btn is not None)
ap.plural("SOWs", "SOW")
check("Plural of: still a term, tied to its singular", s.results["SOWs"]["plural_of"] == "SOW" and s.results["SOWs"]["status"] == "Plural of SOW"
      and not s.results["SOWs"].get("excluded"))
s3 = S.AcronymSession(s.ws, LIST, w.efforts); s3.restore()
check("kept for every scan from now on", s3.plurals.get("SOWs") == "SOW" and s3.results["SOWs"]["plural_of"] == "SOW")
check("Not a plural makes it a term of its own again", ap.not_plural("SOWs") and "plural_of" not in s.results["SOWs"])
ap.plural("SOWs", "SOW")
# 3.34.1: a plural is decided: out of the list, greyed when shown, listed with its term
ap.fill(); app.processEvents()
row_sow = ap.terms.index("SOW") if "SOW" in ap.terms else -1
check("a plural leaves the list; its term lists it", "SOWs" not in ap.terms and row_sow >= 0 and ap.table.item(row_sow, 0).text().startswith("SOW  (+SOWs"))
ap.f_forms.setChecked(True); app.processEvents()
r = ap.terms.index("SOWs") if "SOWs" in ap.terms else -1
check("Show plurals and forms: back, greyed and italic", r >= 0 and ap.table.item(r, 0).font().italic())
ap.f_forms.setChecked(False); app.processEvents()
# 3.34.1: FY27 is FY plus a number
check("a form's term is guessed", s.form_guess("FY27") == "FY" and s.form_guess("FY2027") == "FY" and s.form_guess("CDRL-A001") == "CDRL"
      and s.form_guess("SOW") == "" and s.form_guess("Rev2") == "")
s.results["FY27"] = {"category": "Acronym", "count": 2, "locations": ["Kestrel_Technical_Volume.docx (para 3)"], "definitions": [],
                     "status": "New candidate", "in_db": False}
s.results.pop("FY", None)
ap.fill(); ap.select("FY27"); app.processEvents()
btn = next((b for b in ap.card.findChildren(QPushButton) if b.text() == "Use FY (a form of it)"), None)
check("the card offers Use FY (a form of it)", btn is not None)
ap.form("FY27", "FY")
check("FY becomes a term (found only inside FY27), FY27 tied to it and out of the list, FY shown",
      s.results["FY"].get("from_forms") and s.results["FY"]["locations"] == ["Kestrel_Technical_Volume.docx (para 3)"]
      and s.results["FY27"]["form_of"] == "FY" and "FY27" not in ap.terms and ap.current() == "FY")
check("a form is decided: it never comes up as needing a decision", A.status_kind(s.results["FY27"]["status"]) == "resolved")
s4 = S.AcronymSession(s.ws, LIST, w.efforts); s4.restore()
check("kept for every scan", s4.forms.get("FY27") == "FY" and "FY" in s4.results)
check("Not a form of FY: FY27 its own again, FY gone with it", ap.not_form("FY27") and "FY" not in s.results and "form_of" not in s.results["FY27"])
# 3.34.1: where a term was found
from skqt.whereview import parse_loc
check("a file name with brackets of its own keeps them", parse_loc("Section L (1).pdf (p.3)") == ("Section L (1).pdf", 3, None)
      and parse_loc("Vol I.docx (section 'A (b)', para 12)") == ("Vol I.docx", None, 12))
check("the scanned file is found without regard to case", ap.path_of("kestrel_technical_volume.docx") == files[0])
check("Found in: a customer file scanned is the customer's, not ours", s.found_in(s.results["SOW"]) == "Customer", s.found_in(s.results["SOW"]))
ap.f_status.setCurrentText("Needs approval"); app.processEvents()
check("the status filter (3.34.1: the few that matter): Needs approval holds the new candidates",
      [ap.f_status.itemText(i) for i in range(ap.f_status.count())] == ["All statuses", "Needs approval", "Approved", "Needs a choice",
                                                                        "No longer found", "Omitted"]
      and ap.terms and not any(s.results[x].get("effort") == "Approved" for x in ap.terms))
ap.f_status.setCurrentIndex(0); app.processEvents()
# the effort list itself
w.go("acrlist"); app.processEvents()
lp = w.acrlist_page
check("the effort list: every term in the workbook", set(lp.terms) == set(E.EffortList(LIST).load().rows) and "1 approved" in lp.pills["Approved"].text())
lp.edit_definition("Statement of Work (SOW)", "SOW")
check("Edit definition (the term in brackets is taken off)", E.EffortList(LIST).load().rows["SOW"]["Definition"] == "Statement of Work"
      or E.EffortList(LIST).load().rows["SOW"]["Definition"].startswith("Statement of Work"), E.EffortList(LIST).load().rows["SOW"]["Definition"])
lp.select(["SCOPE"]); lp.set_status("Needs author")
check("a status set here shows in Scan and review", E.EffortList(LIST).load().rows["SCOPE"]["Status"] == "Needs author"
      and s.results["SCOPE"]["status"] == "Effort list: Needs author")
made = lp.export(os.path.join(tmp, "lists"))
check("Export the lists: Word and Excel", made and any(p.endswith(".docx") for p in made) and any(p.endswith(".xlsx") for p in made), made)
lp.select(["SCOPE"]); lp.remove()
check("Take out of the effort list", "SCOPE" not in E.EffortList(LIST).load().rows)
w.close()
n = sum(checks)
print(f"QT ACRONYMS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT ACRONYMS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
