"""3.92.0 offscreen: Acronyms on the page. Three panes (the terms, the customer's page where the term was found, the
card); the filters as counts you click; one command bar (Next to decide, Add a term, In our drafts, More with every scan
and tool, Export); keys 1 to 4, Enter and X; the line from the spelled-out words to the definition picked; Where it goes
(the A to Z rows); Sources and the timeline; a find inside a longer term; the hyphen rule; In our drafts with fixes as
tracked changes in a copy. Fictional content (the Kestrel set)."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "dark"
os.environ["AH_OCR_ENGINE"] = "tesseract"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import acrpage as P

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
check("one command bar: Next to decide, Add a term, In our drafts", ap.bar.main is ap.b_next and len(ap.bar.commands) <= 5
      and "In our drafts" in ap.bar.labels(), ap.bar.labels())
check("every scan and tool is in More", all(ap.bar.action(x) is not None for x in ("Scan the customer documents", "Scan files...",
      "Scan the library...", "Customer acronym lists...", "Letters joined by a hyphen are one term")))
files = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]
ap.scan(files)
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 240:
    app.processEvents(); time.sleep(0.05)
s = ap.session
check("the scan is noted on the effort's timeline", P.timeline(s.ws) and P.timeline(s.ws)[-1]["what"] == "Scan", P.timeline(s.ws))
c = P.count_of(s.results, lambda d: "excluded" if d.get("excluded") else A.status_kind(d.get("status", "")))
check("the counts on the page", ap.count_btns["To decide"].text() == f"To decide {c['To decide']}" and c["To decide"] > 0,
      [b.text() for b in ap.count_btns.values()])
ap.count_btns["To decide"].click(); app.processEvents()
check("a count clicked filters the list", ap.f_status.currentText() == "To decide" and ap.count_btns["To decide"].isChecked())
check("the list shows the term, its state and its definition only", [c_ for c_ in range(ap.table.columnCount()) if not ap.table.isColumnHidden(c_)] == [0, 5, 6])
t = ap.b_next.click() or ap.current(); app.processEvents()
t = ap.current()
check("Next to decide selects a term to decide", t is not None and P.passes(s.results[t], "To decide", "other"), t)
check("the customer's page is in the middle, not in the card", ap.where_view is not None and ap.where_view.parentWidget() is ap.mid
      if s.results[t].get("locations") else True)
# a term with suggestions: keys
s.results["GSaaS"] = {"count": 2, "category": "Acronym", "status": "Needs Review", "locations": ["Kestrel_Technical_Volume.docx para 2"],
                      "custdef_all": [{"definition": "Ground Station as a Service", "where": "RFP p. 41"}],
                      "customer_definitions": ["Ground Station as a Service"], "definitions": ["Ground Station as a Service"]}
ap.fill(); app.processEvents()
cand = next((x for x in ap.terms if __import__("acrsuggest").suggestions(s.results[x])), None)
if cand:
    ap.select(cand); app.processEvents()
    sug = ap.suggest_rows
    from skqt import acrlayout as AL
    got = AL.pick_suggestion(ap, 1)
    check("key 1 picks the first definition", got == sug[0]["definition"] and ap.typed.text() == got)
    check("the picked definition is framed", ap.suggest_widgets and ap.pick == 1)
    check("the line goes from the spelled-out words when the passage shows them", isinstance(AL.links(ap), list))
    n0 = sum(1 for d in s.results.values() if d.get("effort") == "In the list")
    AL.add_current(ap); app.processEvents()
    check("Enter adds it to the list with that definition", s.results[cand].get("effort") == "In the list"
          and sum(1 for d in s.results.values() if d.get("effort") == "In the list") == n0 + 1)
else:
    check("a term with a suggestion to try the keys on", False, ap.terms[:10])
nt = ap.current()
from skqt import acrlayout as AL
AL.not_term_current(ap); app.processEvents()
check("X says Not a term", s.results[nt].get("effort") == "Not a term" or s.results[nt].get("excluded"), nt)
# where it goes
ap.select(cand); app.processEvents()
check("Where it goes shows the A to Z rows with this term", any(r[0] == cand for r in ap.where_rows), ap.where_rows)
AL.sources_window(ap, cand, run=False)
check("Sources lists where its meaning comes from", ap.sources_dialog is not None)
# a longer term and the hyphen rule
s.results["DC"] = {"count": 2, "category": "Acronym", "status": "Needs Review", "locations": ["Kestrel_Technical_Volume.docx para 3", "Kestrel_Technical_Volume.docx para 7"]}
s.results["DC-RVM"] = {"count": 2, "category": "Acronym", "status": "Needs Review", "locations": ["Kestrel_Technical_Volume.docx para 3", "Kestrel_Technical_Volume.docx para 7"]}
ap.f_status.setCurrentIndex(0); ap.fill(); ap.select("DC"); app.processEvents()
check("a find inside a longer term says so on the card", ap.longer_line and ap.longer_line["whole"] == "DC-RVM", ap.longer_line)
n = AL.set_hyphen(ap, True); app.processEvents()
check("the hyphen rule joins DC to DC-RVM and is kept", n >= 1 and s.results["DC"].get("part_of") == "DC-RVM" and P.hyphen_whole(s), s.results["DC"])
AL.set_hyphen(ap, False)
# In our drafts
import docxw
d = docxw.Doc()
d.para(f"Our design pairs two sites with a commercial {cand} option.")
dfn = s.results[cand].get("list_definition") or s.results[cand].get("selected_definition")
d.para(f"We contract {dfn} ({cand}) passes at two sites.")
draft = os.path.join(tmp, "Kestrel_VolII_draft_v4.docx"); d.save(draft)
raw = open(draft, "rb").read()
from skqt.acrdrafts import open_drafts
dw = open_drafts(ap, draft); app.processEvents()
check("In our drafts finds the term used before it is spelled out", any(f["term"] == cand and f["kind"] == "before" for f in dw.rows),
      [(f["term"], f["kind"]) for f in dw.rows])
f0 = next(f for f in dw.rows if f["term"] == cand)
dw.list.setCurrentRow(dw.rows.index(f0)); dw.take(); app.processEvents()
with zipfile.ZipFile(dw.copy_path()) as z:
    xml = z.read("word/document.xml").decode()
check("Fix in the copy writes tracked changes into a copy; the draft is not changed", "<w:ins " in xml and "<w:del " in xml
      and open(draft, "rb").read() == raw)
check("the volume's uses are kept for Where it goes", (s.ws.get("acronym_volume_use") or {}).get(cand, {}).get("Kestrel_VolII_draft_v4") == 2)
dw.undo(); app.processEvents()
check("Undo takes the fix back out of the copy", not dw.taken and not os.path.exists(dw.copy_path()))
dw.close()
print(f"QT ACRONYMS 392 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
