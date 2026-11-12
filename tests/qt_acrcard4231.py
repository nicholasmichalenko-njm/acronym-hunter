"""4.23.1 offscreen: the acronym card has two lines (Nicholas 2026-11-12 13:51). Reads as: the term, typable; a wrong
reading is fixed there and the list gets what was typed, with or without a meaning. Means: the definition. Gone from
the card: Read here, Use as the definition, The picture says something else... (Not text and Part of a longer term are
under More). What is selected on the page goes to either line. More: Add to the Wall of Truth... A plural of a term in
capitals is marked on the page. Fictional content (the Kestrel program)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP, effortrec as R, walloftruth as WT
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import acrpage as P, acrpages as PG
from skqt import acrlayout as AL, acrpart as APT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
d0 = os.path.join(tmp, "Kestrel"); os.makedirs(d0)
L = E.EffortList(os.path.join(d0, "Kestrel_Effort_List.xlsx"), "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=L.path)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
S = os.path.join(A.BASE_DIR, "test_samples")
ap.scan([os.path.join(S, "Kestrel_Technical_Volume.docx"), os.path.join(S, "Kestrel_Program_Manual.pdf")])
while ap.worker is not None and ap.worker.isRunning():
    app.processEvents()
app.processEvents()
s = ap.session
ap.tabs.setCurrentIndex(1); app.processEvents()
AL.pick_count(ap, "To decide"); app.processEvents()
todo = [t for t in ap.terms if P.passes(s.results[t], "To decide", AL.kind_of(s.results[t]))]
ap.select(todo[0]); app.processEvents()
texts = [x.text() for x in ap.card_area.findChildren(QLabel)]
btns = [b.text() for b in ap.card_area.findChildren(QPushButton) if not b.isHidden()]
check("the card has two lines: Reads as (the term) and Means", "Reads as" in texts and "Means" in texts and ap.reads.text() == todo[0]
      and not ap.reads.isReadOnly() and ap.typed.text() == "")
check("Read here and Use as the definition are gone from the card", "Read here" not in texts and "Use as the definition" not in btns
      and "Copy" not in btns, btns)
check("The picture says something else... is gone", "The picture says something else..." not in btns)
# a meaning typed, the reading left: as before
ap.typed.setText("Kestrel test meaning")
[b for b in ap.card_area.findChildren(QPushButton) if b.text() == "Add to effort list"][0].click(); app.processEvents()
check("a meaning typed goes in with the term", s.effort.rows[todo[0]]["Definition"] == "Kestrel test meaning" and ap.current() == todo[1])
# the reading fixed, no meaning
t1 = todo[1]
right = t1[:-1] + ("X" if t1[-1] != "X" else "Y")
ap.reads.setText(right)
[b for b in ap.card_area.findChildren(QPushButton) if b.text() == "Add to effort list"][0].click(); app.processEvents()
check("a reading fixed in Reads as: the list gets what was typed, with no definition", right in s.effort.rows
      and s.effort.rows[right]["Status"] == "In the list" and not (s.effort.rows[right].get("Definition") or "").strip(), s.effort.rows.get(right))
check("... what was read is Not a term here", s.effort.rows.get(t1, {}).get("Status") == "Not a term", s.effort.rows.get(t1))
check("... it keeps the places it was found", s.results[right].get("locations") == s.results[t1].get("locations") and s.results[right]["locations"])
check("... and the card moves to the next term", ap.current() == todo[2], (ap.current(), todo[2]))
# only part of the term was found: the longer one, with a meaning
t2 = todo[2]
whole = t2 + "-II"
ap.reads.setText(whole); ap.typed.setText("Kestrel second meaning")
AL.add_current(ap); app.processEvents()
check("part of a longer term typed in Reads as: the longer term is in the list with its meaning", whole in s.effort.rows
      and s.effort.rows[whole]["Definition"] == "Kestrel second meaning", s.effort.rows.get(whole))
check("... and the part is tied to it, not thrown out", (getattr(s, "parts", None) or {}).get(t2, {}).get("whole") == whole
      or s.effort.rows.get(t2, {}).get("Status") == "Not a term", (getattr(s, "parts", None) or {}).get(t2))
# More
t3 = [t for t in ap.terms if P.passes(s.results[t], "To decide", AL.kind_of(s.results[t]))][0]
ap.select(t3); app.processEvents()
more = [a.text() for a in APT.more_menu(ap, [t3], run=False).actions()]
check("More has Part of a longer term and Add to the Wall of Truth", "Part of a longer term..." in more and "Add to the Wall of Truth..." in more, more)
ap.typed.setText(""); ap.add([t3], "Kestrel meaning for the wall"); app.processEvents()
tid = APT.to_wall(ap, t3, answer={})
rec = R.Record(w.ws.root)
tr = WT.get(rec, tid) if tid else None
check("Add to the Wall of Truth: a Term truth, how to write it and what it means here", tr is not None and tr["kind"] == "Term" and tr["label"] == t3
      and tr["value"] == t3 and tr["notes"] == "Means here: Kestrel meaning for the wall" and tr["source"] == "Acros & Abs", tr)
w.go("truth"); app.processEvents()
check("... and it shows on Drafts > Wall of Truth", any(t3 == x["label"] for x in WT.items(R.Record(w.ws.root))))
# the page: what is selected goes to either line (the Finder keeps the page beside the card)
tw = w.open_tool("acronyms"); app.processEvents()
tw.page.scan([os.path.join(S, "Kestrel_Technical_Volume.docx")])
while tw.page.worker is not None and tw.page.worker.isRunning():
    app.processEvents()
app.processEvents()
tp = tw.page
tt = [t for t in tp.terms if tp.session.results[t].get("locations")][0]
tp.select(tt); app.processEvents()
wv = tp.where_view
check("beside the page: Selected on the page, Put in Reads as, Put in Means", wv is not None and wv.read_lab.text() == "Selected on the page"
      and wv.b_fixread.text() == "Put in Reads as" and wv.b_usemean.text() == "Put in Means")
wv.reading.setText("  Kestrel   Ground Station ")
wv.b_usemean.click(); app.processEvents()
check("Put in Means fills Means", tp.typed.text() == "Kestrel Ground Station", tp.typed.text())
wv.reading.setText("KGS-2"); wv.b_fixread.click(); app.processEvents()
check("Put in Reads as fills Reads as", tp.reads.text() == "KGS-2", tp.reads.text())
# marks on the page
check("a plural of a term in capitals is marked: RFPs, the SOW's, CDRLs.", PG.spans("The RFPs and the SOW's terms; CDRLs.", "RFP") == [(4, 7)]
      and PG.spans("The RFPs and the SOW's terms; CDRLs.", "SOW") == [(17, 20)] and PG.spans("CDRLs.", "CDRL") == [(0, 4)])
check("... not letters inside a word", PG.spans("RFPsx and sRFP and cats", "RFP") == [] and PG.spans("cats", "cat") == [])
k = sum(checks)
print(f"QT ACR CARD 4231 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if k == len(checks) else 1)
