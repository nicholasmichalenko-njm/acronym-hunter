"""4.23.0 offscreen: the acronym review, decide and move on (Nicholas 2026-11-12 13:51). Add to effort list moves to
the next term to decide, as Not a term does; the bar's main button is Add a term; Next to decide, In our drafts and the
report are off the face (In our drafts and the report in More); the counts row shows To decide and In the list, the
other filters are in More; no Copy button on the card; one export, the list (whole, or one per volume); Acros & Abs
Finder sends its list to an effort. Fictional content (the Kestrel program)."""
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
import effort as E, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import acrpage as P
from skqt import acrlayout as AL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
for nm in ("Kestrel", "Osprey"):
    d = os.path.join(tmp, nm); os.makedirs(d)
    L = E.EffortList(os.path.join(d, f"{nm}_Effort_List.xlsx"), nm); L.pending = True; L.save()
    E.Registry(os.path.join(cfg, "efforts.json")).put(nm, path=L.path)
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
# ---- the bar and the face
labels = ap.bar.labels()
check("the bar's main button is Add a term, once", ap.bar.main is ap.b_addterm and labels.count("Add a term") == 1 and "Add a term..." not in labels, labels)
check("Next to decide is off the bar", "Next to decide" not in labels and not hasattr(ap, "b_next"))
check("In our drafts and the report are in More, not on the face", ap.bar.action("In our drafts") is not None
      and ap.bar.action("Export the report...") is not None and "In our drafts" not in [b.text() for b in ap.bar.commands])
ex = [a.text() for a in ap.bar.export_menu.actions()]
check("one export: the list, whole or one per volume", ex == ["The list: the whole effort...", "The list: one per volume..."], ex)
shown = [n for n, b in ap.count_btns.items() if not b.isHidden()]
check("the counts row shows To decide and In the list only", shown == ["To decide", "In the list"], shown)
more = [a.text() for a in ap.bar.more_menu.actions()]
check("the other filters are in More, with their counts", all(any(m.startswith(f"Show only: {n} (") for m in more)
      for n in ("Needs a choice", "No definition yet", "On pictures", "Not a term")), more)
ap.count_acts["Not a term"].trigger(); app.processEvents()
check("a filter picked in More filters the list and is ticked", AL.current_count(ap) == "Not a term" and ap.count_acts["Not a term"].isChecked())
ap.count_acts["Not a term"].trigger(); app.processEvents()
check("... picked again, every term shows", AL.current_count(ap) is None and not ap.count_acts["Not a term"].isChecked())
# ---- decide and move on
AL.pick_count(ap, "To decide"); app.processEvents()
todo = [t for t in ap.terms if P.passes(s.results[t], "To decide", AL.kind_of(s.results[t]))]
check("there are terms to decide", len(todo) >= 4, len(todo))
ap.select(todo[0]); app.processEvents()
check("the card has no Copy button", "Copy" not in [b.text() for b in ap.card_area.findChildren(QPushButton)])
add_btn = [b for b in ap.card_area.findChildren(QPushButton) if b.text() == "Add to effort list"][0]
add_btn.click(); app.processEvents()
check("Add to effort list adds the term", todo[0] in s.effort.rows and s.effort.rows[todo[0]]["Status"] == "In the list")
check("... and moves to the next term to decide", ap.current() == todo[1], (ap.current(), todo[1]))
nt = [b for b in ap.card_area.findChildren(QPushButton) if b.text() == "Not a term"][0]
nt.click(); app.processEvents()
check("Not a term moves to the next one too", s.effort.rows[todo[1]]["Status"] == "Not a term" and ap.current() == todo[2], (ap.current(), todo[2]))
AL.add_current(ap); app.processEvents()
check("Enter adds and moves one term on, not two", todo[2] in s.effort.rows and ap.current() == todo[3], (ap.current(), todo[3]))
AL.not_term_current(ap); app.processEvents()
check("X says Not a term and moves one term on", s.effort.rows[todo[3]]["Status"] == "Not a term"
      and ap.current() == (todo[4] if len(todo) > 4 else ap.current()), ap.current())
# several at once stay where they are
many = [t for t in ap.terms if P.passes(s.results[t], "To decide", AL.kind_of(s.results[t]))][:2]
if len(many) == 2:
    ap.add(many); app.processEvents()
    check("several added at once: both in the list", all(t in s.effort.rows for t in many))
# ---- Acros & Abs Finder: its list into an effort
tw = w.open_tool("acronyms"); app.processEvents()
said = []
tw.host.status = lambda m: said.append(m)
check("the Finder has Send the list to an effort...", tw.b_send.text() == "Send the list to an effort...")
check("... and knows this PC's efforts", sorted(tw.efforts()) == ["Kestrel", "Osprey"], tw.efforts())
check("nothing to send before a scan", tw.send_to_effort("Osprey") is None and "scan files first" in said[-1], said[-1:])
tw.page.scan([os.path.join(S, "Kestrel_Technical_Volume.docx")])
while tw.page.worker is not None and tw.page.worker.isRunning():
    app.processEvents()
app.processEvents()
from skqt.acrtool import list_rows
rows = list_rows(tw.page.session)
n = tw.send_to_effort("Osprey")
O = E.EffortList(E.Registry(os.path.join(cfg, "efforts.json")).get("Osprey")["path"], "Osprey").load()
check("Send the list to an effort: its terms are in that effort's list", n and n["added"] == len(rows) > 3 and all(t in O.rows for t, _m in rows),
      (n, len(rows)))
check("... with their meanings", all((O.rows[t].get("Definition") or "") == m for t, m in rows if m), [(t, m, O.rows[t].get("Definition")) for t, m in rows if m][:2])
check("... and the message says how many", said and said[-1].startswith("Sent to Osprey: ") and "new" in said[-1], said[-1:])
n2 = tw.send_to_effort("Osprey")
check("sent again, nothing is added twice", n2 and n2["added"] == 0 and n2["same"] + n2["filled"] >= len(rows) - len(n2["review"]), n2)
check("an effort this PC does not know is refused", tw.send_to_effort("Heron") is None and "not on this PC" in said[-1])
k = sum(checks)
print(f"QT ACR DECIDE 4230 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if k == len(checks) else 1)
