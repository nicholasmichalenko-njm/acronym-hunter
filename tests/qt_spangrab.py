"""3.28.1 Review, offscreen: a drag over words grabs them across sentences, whatever was selected before: the sentences
they sit in are selected; Extract (Shift+S) makes the picked words one sentence, split from the sentences they came
from (the words before and after stay there), in one Undo step; a capture or bin takes just those words; a drag inside
one sentence still picks words in it, and a click still selects. Volumes: Rename keeps the number; numbered I, II, III;
1, 2, 3; or A, B, C, with everything in them following; a new volume takes the style."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import compliance as C, effort as E, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
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
reg = E.Registry(os.path.join(cfg, "efforts.json")); reg.put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk\nVolume II Management\n2.1 Program Management")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]

app = QApplication([])
theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION)
w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the effort opens and is held", w.open_effort("Kestrel") and W.read_json(ws0.p("lock.json"), {}).get("pid") == os.getpid())
check("no matrix yet: Shred is the step (4.1.0: it lists the documents to extract)", w.stack.currentWidget() is w.assign_page)
out = os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx")
w.read_page.read(PDFS, out)
check("Read runs in the background and starts the matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
import effortrec as RR, excerpts as EX, pagemarks as PM
from PySide6.QtGui import QShortcut
rec = lambda: RR.Record(w.ws.root)


from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QMouseEvent
v = pg.view


def ev(kind, iid, k, buttons=Qt.LeftButton):
    r = v.words[iid][k]
    p = QPointF(v.mapFromScene(r.center()))
    btn = Qt.LeftButton if kind != QEvent.MouseMove else Qt.NoButton
    return QMouseEvent(kind, p, v.viewport().mapToGlobal(p.toPoint()), btn, buttons if kind != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier)


def drag(a, ka, b, kb):
    v.mousePressEvent(ev(QEvent.MouseButtonPress, a, ka)); app.processEvents()
    v.mouseMoveEvent(ev(QEvent.MouseMove, b, kb)); app.processEvents()
    v.mouseReleaseEvent(ev(QEvent.MouseButtonRelease, b, kb)); app.processEvents()


ids = [i for i in v.order if len(v.words.get(i, [])) >= 6]
s1, s2, s3 = ids[2], ids[3], ids[5]
t1, t2 = pg.R.item(s1)["text"], pg.R.item(s2)["text"]
pg.select(s3); app.processEvents()
check("another sentence is selected first", [it["id"] for it in pg.selected()] == [s3])
n1, n2 = len(v.words[s1]), len(v.words[s2])
drag(s1, n1 - 3, s2, 2)
gm = pg.grab_multi or []
check("a drag over words in two sentences picks them, whatever was selected", [p["iid"] for p in gm] == [s1, s2], gm)
check("... and selects the sentences they sit in", sorted(it["id"] for it in pg.selected()) == sorted([s1, s2]))
check("the picked words are the end of one and the start of the next", t1.endswith(gm[0]["text"]) and t2.startswith(gm[1]["text"]), gm)
parts = pg.excerpt_parts()
check("a capture or bin takes just those words, part by part", [p["text"] for p in parts] == [gm[0]["text"], gm[1]["text"]])
before = len(M.items)
new = pg.do_extract()
check("Extract: the picked words are one sentence", new is not None and new["text"].startswith(gm[0]["text"]) and gm[1]["text"] in new["text"], new and new["text"])
rest1 = [it for it in M.items if it["id"].startswith(s1) and it["id"] != new["id"]]
check("... split from where they were: the words before stay a sentence", any(t1.startswith(it["text"]) and it["text"] != t1 for it in rest1),
      [it["text"][:40] for it in rest1])
check("... and the rest of the next sentence stays a sentence", any(t2.endswith(it["text"]) and it["text"] != t2 for it in M.items))
check("the new sentence is selected, ready to decide", [it["id"] for it in pg.selected()] == [new["id"]])
pg.do_undo(); app.processEvents()
check("one Undo puts both sentences back", pg.R.item(s1) is not None and pg.R.item(s1)["text"] == t1 and pg.R.item(s2)["text"] == t2 and len(M.items) == before)
pg.build_boxes(); app.processEvents()
pg.select(s1); app.processEvents()
drag(s1, 1, s1, 3)
check("a drag inside one sentence still picks words in it", pg.grab is not None and pg.grab["iid"] == s1 and not pg.grab_multi)
v.mousePressEvent(ev(QEvent.MouseButtonPress, s2, 0)); v.mouseReleaseEvent(ev(QEvent.MouseButtonRelease, s2, 0)); app.processEvents()
check("a click on another sentence selects it", [it["id"] for it in pg.selected()] == [s2] and not pg.grab_multi)
# ---------------------------------------------------------------- volumes: rename and numbering
import outline_ops as O
heads = list(SD.volumes_of(M)[2])
check("two volumes to start", len(heads) == 2 and heads[0].startswith("Volume I "), heads)
reqs = [it for it in M.items if it.get("map") and it["map"] in O.in_volume(M, heads[0])]
pg.pick_volume(heads[0])
new = pg.rename_volume("Technical and Management Approach")
check("Rename: the volume's title changes, its number stays", new == "Volume I Technical and Management Approach" and pg.active_volume == new
      and new in SD.volumes_of(M)[2], new)
mp = pg.set_volume_style("number")
heads2 = list(SD.volumes_of(M)[2])
check("Numbered 1, 2, 3: every volume follows", heads2[0] == "Volume 1 Technical and Management Approach" and heads2[1].startswith("Volume 2 "), heads2)
check("... the style shows in the box", pg.vol_style.currentData() == "number")
cnt = len(O.in_volume(M, heads2[0]))
mp = pg.set_volume_style("alpha")
heads3 = list(SD.volumes_of(M)[2])
check("Lettered A, B, C", heads3[0].startswith("Volume A ") and heads3[1].startswith("Volume B "), heads3)
check("the sections in a volume stay in it", cnt > 1 and len(O.in_volume(M, heads3[0])) == cnt, cnt)
lab = pg.new_volume("Cost")
check("a new volume takes the style: Volume C", lab == "Volume C Cost", lab)
pg.set_volume_style("roman")
check("back to I, II, III", list(SD.volumes_of(M)[2])[2] == "Volume III Cost")
w.close()
n = sum(checks)
print(f"QT SPAN GRAB {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
