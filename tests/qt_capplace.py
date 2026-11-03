"""3.29.1 Review, offscreen: every capture can be placed in a section of the structure, and it is easy: with Into the
target section on, a capture goes into the target as a requirement does; the sentence's card shows its sections with
Into the target and Section...; a right-click puts a sentence's captures in the target; the Captured list shows a
Section column and puts the selected rows in the target; the structure counts each section's captures; captures follow
their section when it is renamed, renumbered or taken out, and Undo puts them back; the Response Setup lists each
capture under its section."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, excerpts as EX, effortrec as RR, reviewitems as RI, setupdoc as SD
import outline_ops as O
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk\n1.3 Schedule")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page; v = pg.view
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
labs = pg.R.labels()
tech = next(l for l in labs if l.endswith("Technical Approach"))
risk = next(l for l in labs if l.endswith("Risk"))
sched = next(l for l in labs if l.endswith("Schedule"))
rec = lambda: RR.Record(w.ws.root)
ids = [i for i in v.order if len(v.words.get(i, [])) >= 6]

# ---------------------------------------------------------------- into the target by default
check("Into the target section is on to start", pg.into_target.isChecked())
pg.set_target(tech)
pg.select(ids[1]); app.processEvents()
x1 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "lead with the test campaign"})
check("a capture goes into the target, as a requirement does", EX.get(rec(), x1)["sections"] == [tech], EX.get(rec(), x1)["sections"])
pg.select(ids[2]); app.processEvents()
x2 = pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": ""})
check("... an objective too", EX.get(rec(), x2)["sections"] == [tech])
pg.into_target.setChecked(False); app.processEvents()
check("turned off: kept in Settings", RI.load(cfg)["into_target"] is False)
pg.select(ids[3]); app.processEvents()
x3 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": ""})
check("... and a capture then has no section", EX.get(rec(), x3)["sections"] == [])
pg.into_target.setChecked(True); app.processEvents()
check("on again", RI.load(cfg)["into_target"] is True)

# ---------------------------------------------------------------- one click to move
pg.set_target(risk)
pg.select(ids[3]); app.processEvents()
texts = [x.text() for x in pg.findChildren(type(pg.captured_btn)) if x.isVisible()]
check("the card offers Into the target and Section... for a capture", "Into the target" in texts and "Section..." in texts)
n = pg.place_captures([x3])
check("Into the target: the capture is in 1.2 Risk", n == 1 and EX.get(rec(), x3)["sections"] == [risk])
m = pg.section_menu_for(x3)
acts = {a.text(): a.isChecked() for a in m.actions()}
check("Section... lists the structure, its section ticked", acts.get(risk) is True and acts.get(tech) is False, acts)
next(a for a in m.actions() if a.text() == sched).trigger(); app.processEvents()
check("... a click puts it in another section too", EX.get(rec(), x3)["sections"] == [risk, sched])
pg.select(ids[1]); app.processEvents()
mm = pg.sentence_menu(ids[1])
a = next((a for a in mm.actions() if a.text().startswith("Put its captures in the target")), None)
check("right-click a sentence: Put its captures in the target", a is not None)
a.trigger(); app.processEvents()
check("... its key point is now in 1.2 Risk too", EX.get(rec(), x1)["sections"] == [tech, risk])
pg.fill_tree(); app.processEvents()
node = lambda lab: next((it for it in pg.tree.findItems(lab, Qt.MatchExactly | Qt.MatchRecursive, 0)), None)
check("the structure counts each section's captures", node(tech).text(4) == "2" and node(risk).text(4) == "2" and node(sched).text(4) == "1",
      (node(tech).text(4), node(risk).text(4), node(sched).text(4)))

# ---------------------------------------------------------------- the Captured list
d = pg.all_excerpts(run=False)
hdr = [d.t.horizontalHeaderItem(i).text() for i in range(d.t.columnCount())]
check("the Captured list has a Section column", "Section" in hdr, hdr)
col = hdr.index("Section")
row = next(r for r in range(d.t.rowCount()) if d.t.item(r, 0).data(Qt.UserRole) == x2)
check("... showing where each capture is", d.t.item(row, col).text() == tech)
d.t.selectRow(row)
pg.target = sched
d.into_target(); app.processEvents()
check("select rows, Into the target: they go in", EX.get(rec(), x2)["sections"] == [tech, sched])
d.reject()

# ---------------------------------------------------------------- captures follow the structure
pg.set_target(tech)
new = pg.rename_section(tech, "Technical and Test Approach")
check("rename a section: its captures follow", new and EX.get(rec(), x1)["sections"][0] == new and EX.get(rec(), x2)["sections"][0] == new,
      (new, EX.get(rec(), x1)["sections"]))
pg.do_undo(); app.processEvents()
check("Undo: they are back in the old name", EX.get(rec(), x1)["sections"][0] == tech, EX.get(rec(), x1)["sections"])
pg.set_target(tech)
a1 = pg.new_section(sub=True, title="Test Campaign"); a2 = pg.new_section(sub=False, title="Facilities")
pg.set_target(a1)
pg.select(ids[4]); app.processEvents()
x4 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": ""})
pg.set_target(a1); pg.outline_op(O.move, 1); app.processEvents()
moved = next(l for l in pg.R.labels() if l.endswith("Test Campaign"))
check("move a numbered subsection down: it is renumbered, and its capture follows", moved != a1 and EX.get(rec(), x4)["sections"] == [moved],
      (a1, moved, EX.get(rec(), x4)["sections"]))
risk2 = next(l for l in pg.R.labels() if l.endswith("Risk"))
pg.delete_section(risk2); app.processEvents()
x3s = EX.get(rec(), x3)["sections"]
check("take a section out: its captures go where its sentences go", risk2 not in x3s and all(s in pg.R.labels() for s in x3s), x3s)

# ---------------------------------------------------------------- the Response Setup
S_ = rec()
labs3 = pg.R.labels()
tech3 = next(l for l in labs3 if l.endswith("Technical Approach"))
groups = SD.volume_groups(M)
vname, entries = groups[0]
dd = SD._doc_for(M, vname, entries, SD.placed_in(M), SD.inherited_sections(M), "now", bins=SD.review_bins(w.ws.root))
body = "".join(dd.body)
words1 = EX.text_of(EX.get(rec(), x1))[:30]
at_h = body.find(tech3.split(" ", 1)[1])
import re as _re
plain = _re.sub(r"<[^>]+>", "", body)
at_h = plain.find(tech3)
kp = plain.find("Key points", at_h)
nxt = min([plain.find(l, at_h + len(tech3)) for l in labs3 if l != tech3 and plain.find(l, at_h + len(tech3)) > 0] or [len(plain)])
check("the Response Setup lists a key point under its section", 0 <= at_h < kp < nxt and words1[:15] in plain[kp:nxt],
      (at_h, kp, nxt, plain[kp:kp + 80]))
w.close()
n = sum(checks)
print(f"QT CAPTURE PLACE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
