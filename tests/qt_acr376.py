"""3.76.0 acronym review, offscreen: no approval (a term is in the list or Not a term; one with no definition shows No
definition yet); the card keeps Add to effort list and Not a term, The picture says something else... for picture finds,
and the rest under More (no Approve, Needs author, Omit or Exclusion List); a term omitted before becomes Not a term;
Part of a longer term, held where it sits; Import a list... with any headings, merged; every fix saves a training
sample with the effort, and the Training app learns from an effort once. Fictional content (the Kestrel set)."""
import csv, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
os.environ["AH_OCR_ENGINE"] = "tesseract"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
import skqt.acrfast as _AF; _AF.AT_ONCE = True     # 4.30.3: these checks read the files straight after a decision
from skqt.mainwin import MainWindow

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
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
files = [os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]
ap.scan(files)
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 240:
    app.processEvents(); time.sleep(0.05)
s = ap.session
terms = sorted(t for t in s.results if not t.startswith("[") and not s.results[t].get("known"))
check("the scan found terms", len(terms) > 5, len(terms))


def labels(page):
    return [b.text() for b in page.findChildren(QPushButton) if b.isVisibleTo(page)]


a, b, c = terms[0], terms[1], terms[2]
ap.tabs.setCurrentIndex(1); app.processEvents()                    # 3.93.0: the card is in The list
ap.select(a); app.processEvents()
got = labels(ap)
check("the card: Add to effort list and Not a term", "Add to effort list" in got and "Ignore in this effort" in got, got)
check("... no Approve, Needs author, Omit or Exclusion List", not {"Approve...", "Needs author", "Omit", "Exclusion List",
                                                                  "Exclusion List...", "Back to Proposed"} & set(got), got)
check("... the rest under More", "More" in got)
check("... Read here and Use as the definition", ap.use_sel.text() == "Use as the definition")
check("the status filters: To decide, In the list, No definition yet, Not a term",
      [ap.f_status.itemText(i) for i in range(ap.f_status.count())][:4] == ["All statuses", "To decide", "In the list", "No definition yet"])

ap.add([a])
r = E.EffortList(LIST).load().rows[a]
check("Add to effort list is the decision: In the list", r["Status"] == "In the list" and "Approver" not in r, r)
ap.f_status.setCurrentText("No definition yet"); app.processEvents()
nodef = not (E.EffortList(LIST).load().rows[a].get("Definition") or "").strip()
check("... No definition yet holds it only when it has no definition", (a in ap.terms) == nodef, (nodef, ap.terms[:5]))
d0 = next((t for t in terms if t not in (a, b, c) and not s.results[t].get("selected_definition")), None)
if d0:
    ap.add([d0]); ap.f_status.setCurrentText("No definition yet"); app.processEvents()
    check("... a term added with no definition shows No definition yet", d0 in ap.terms, ap.terms[:5])
ap.f_status.setCurrentIndex(0); app.processEvents()
ap.f_status.setCurrentIndex(0); app.processEvents()
ap.set_status([b], "Not a term")
check("Not a term: in the list as Not a term, and hidden", E.EffortList(LIST).load().rows[b]["Status"] == "Not a term"
      and s.results[b]["excluded"] and b not in ap.terms)
ap.f_status.setCurrentText("Ignored"); app.processEvents()
check("... the Not a term filter shows it", b in ap.terms, ap.terms)
ap.select(b); app.processEvents()
check("... and its card offers Put back in the list", "Put back in the list" in labels(ap))
ap.f_status.setCurrentIndex(0); app.processEvents()

# a term omitted before 3.76.0 becomes Not a term
s.omitted = {c: True}; s.results[c]["excluded"] = True; s.save()
from skqt import acrpart as APT
n = s.omitted_to_list()
check("an omitted term becomes Not a term in the effort's list", n == 1 and E.EffortList(LIST).load().rows[c]["Status"] == "Not a term"
      and not s.omitted)

# More menu
m = APT.more_menu(ap, [a], run=False)
acts = [x.text() for x in m.actions() if x.text()]
check("More: Plural of, A form of, Another way of writing, Part of a longer term", any(x.startswith("Plural of") for x in acts)
      and any(x.startswith("A form of") for x in acts) and "Another way of writing..." in acts and "Part of a longer term..." in acts, acts)
pm = APT.picture_menu(ap, a, run=False)
check("The picture says something else: Part of a longer term, Misread letters, Not text",
      [x.text() for x in pm.actions()] == ["Part of a longer term...", "Misread letters...", "Not text"])

# Part of a longer term, where it sits
import acrparts as PT
part = next(t for t in terms if t not in (a, b, c) and len(s.results[t].get("locations", [])) >= 1)
locs = list(s.results[part]["locations"])
whole = f"MOC-{part}"
ok = APT.part_of(ap, part, whole)
check("Part of a longer term: the whole term takes the row", ok and whole in s.results
      and set(locs) <= set(s.results[whole]["locations"]) and s.results[part].get("part_of") == whole, s.results.get(whole))
s.results[part]["locations"] = locs + ["Elsewhere.docx (para 99)"]; s.results[part]["count"] = len(locs) + 1
s.results[part].pop("part_of", None)
PT.apply_parts(s)                                           # what every later scan does
check("... held where it sits: the part found on its own elsewhere still shows", s.results[part]["locations"] == ["Elsewhere.docx (para 99)"]
      and not s.results[part].get("part_of"), s.results[part].get("locations"))
check("... and the decision is kept with the effort's scan", s.parts.get(part, {}).get("whole") == whole
      and (s.ws.load_session() or {}).get("parts", {}).get(part, {}).get("whole") == whole)
check("longer forms found around the part are offered", whole in PT.longer_forms(s.results, part))

# training samples with the effort
import efftrain as ET
APT.not_text(ap, terms[3])
smp = ET.load(s.ws.root)
check("every fix saves a training sample with the effort", {x["kind"] for x in smp} >= {"part", "not text"}, smp)
APT.misread(ap, terms[4], "K" + terms[4][1:] if terms[4][0] != "K" else "Q" + terms[4][1:])
check("... misread letters too", any(x["kind"] == "misread" for x in ET.load(s.ws.root)))
from skqt.trainingwin import TrainingWindow
tw = TrainingWindow(app)
got = tw.learn_effort(s.ws.root, ask=False)
check("Training: Learn from an effort takes the samples", got and got["new"] >= 3 and got["fixes"] >= 1, got)
again = tw.learn_effort(s.ws.root, ask=False)
check("... and the same effort twice adds nothing twice", again["new"] == 0, again)
tw.close()

# Import a list, any headings, merged
w.go("acrlist"); app.processEvents()
lp = w.acrlist_page
lp.refresh(); app.processEvents()
check("the list page: one bar of at most five, Import a list... in it", len(lp.bar.visible_commands()) <= 5
      and "Import a list..." in lp.bar.labels(), lp.bar.labels())
check("... no Approve, Needs author or Proposed", not {"Approve...", "Needs author", "Proposed", "For approval..."} & set(labels(lp)))
src = os.path.join(tmp, "Their list.csv")
with open(src, "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f)
    wr.writerow(["Abbrev.", "Spelled Out", "Comments"])
    wr.writerow([a, "Kestrel Alpha Thing", "from the team"])
    wr.writerow(["KZQ", "Kestrel Zulu Quebec", ""])
    wr.writerow([b, "", ""])
import acrimport as AI
book = AI.read(src)
check("Import a list: the columns are guessed from the headings", book["guess"].get("Term") == 0 and book["guess"].get("Definition") == 1
      and book["guess"].get("Notes") == 2 and not book["ours"], book["guess"])
from skqt import acrimportview as IV
rep = IV.import_list(lp, src, columns=book["guess"])
L2 = E.EffortList(LIST).load()
check("... merged: a new term comes in the list, the same term fills empty fields", rep and rep["added"] == 1 and "KZQ" in L2.rows
      and L2.rows["KZQ"]["Status"] == "In the list" and L2.rows[a]["Definition"] == "Kestrel Alpha Thing", rep)
check("... a term no scan found shows not found in this effort's documents yet",
      any(lp.table.item(i, 0).text() == "KZQ" and "not found" in lp.table.item(i, 4).text() for i in range(lp.table.rowCount())))
src2 = os.path.join(tmp, "Their list 2.csv")
with open(src2, "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["Acronym", "Definition"]); wr.writerow([a, "Another Meaning Entirely"])
rep2 = IV.import_list(lp, src2, columns=AI.read(src2)["guess"])
L3 = E.EffortList(LIST).load()
check("... two meanings: ours kept, theirs under Other definitions, listed for review", rep2["review"]
      and L3.rows[a]["Definition"] == "Kestrel Alpha Thing" and "Another Meaning Entirely" in L3.rows[a]["Other definitions"])
w.close()
n = sum(checks)
print(f"QT ACRONYM REVIEW 376 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
