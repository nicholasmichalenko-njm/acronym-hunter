"""2.59.0 the Qt edition, offscreen: open an effort (held with the classic app's lock), Read RFP starts the matrix in
the background (headers and footers left out), Assign: click, Ctrl+click two sentences far apart, R into the target
section, C support for the last requirement, the card (source with page and paragraph, chips, authors, relationships),
+ Section and its x, J combine, S split at a clicked word, Ctrl+Z, autosave to the matrix file, and reopening the
effort brings it all back. Another window holding the effort keeps the Qt edition out."""
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
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
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
check("no matrix yet: Read RFP is the step", w.stack.currentWidget() is w.read_page)
out = os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx")
w.read_page.read(PDFS, out)
check("Read runs in the background and starts the matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
check("the matrix is saved where asked, with the effort's structure", os.path.isfile(out) and [C.outline_label(o) for o in M.outline][:2]
      == ["Volume I Technical", "1.1 Technical Approach"] and w.ws.get("compliance_path") == out)
check("no running header in the review", not any("FA8811-26-R-0099" in it["text"] or "Statement of Work Spacecraft Bus" in it["text"]
                                                  for it in M.items), len(M.items))
pg = w.assign_page
app.processEvents()
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
check("Page view: every sentence of the page is a box", len(pg.view.boxes) >= 40 and pg.pdf.endswith("Section_L_print.pdf"), len(pg.view.boxes))
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
a, b, c = by("The Offeror shall describe its technical approach"), by("Each volume shall be written"), by("Information provided")


def click(iid, ctrl=False):
    box = pg.view.boxes[iid]
    pg.view.ensureVisible(box)
    app.processEvents()
    r = box.path().boundingRect()
    pt = pg.view.mapFromScene(r.left() + 6, r.top() + 4)
    QTest.mouseClick(pg.view.viewport(), Qt.LeftButton, Qt.ControlModifier if ctrl else Qt.NoModifier, pt)
    app.processEvents()


click(a["id"])
check("a click selects the sentence and the card shows it", [x["id"] for x in pg.selected()] == [a["id"]] and "Not used" in pg.kind_label.text())
src = pg.source_label.text()
check("the card: file, page and paragraph, RFP section", "File: Section_L_print.pdf" in src and "Where: p.1, para" in src
      and "RFP: L.3.1 Technical Approach" in src, src)
pg.set_target("1.1 Technical Approach")
QTest.keyClick(pg.view, Qt.Key_R); app.processEvents()
check("R: compliance requirement in the target", a["decision"] == "Keep" and a["map"] == "1.1 Technical Approach")
check("the structure counts it", pg.tree.topLevelItem(0).child(0).text(1) == "1")
click(b["id"]); pg.set_target("2.1 Program Management"); QTest.keyClick(pg.view, Qt.Key_R); app.processEvents()
click(a["id"]); click(c["id"]); QTest.keyClick(pg.view, Qt.Key_C); app.processEvents()
check("C: support for the last requirement clicked", c["decision"] == "Context" and C.cf_ids(c["context_for"]) == [a["id"]], c.get("context_for"))
click(c["id"])
cb = pg.card.findChildren(type(pg.files))
plus = next(x for x in cb if x.itemText(0) == "+ Requirement")
k = next(i for i in range(plus.count()) if plus.itemData(i) == b["id"])
plus.activated.emit(k); app.processEvents()
check("+ Requirement: it supports two requirements, both as chips", C.cf_ids(c["context_for"]) == [a["id"], b["id"]]
      and len(pg.chips) == 2, c.get("context_for"))
click(a["id"])
plus = next(x for x in pg.card.findChildren(type(pg.files)) if x.itemText(0) == "+ Section")
plus.activated.emit(next(i for i in range(plus.count()) if plus.itemText(i) == "1.2 Risk")); app.processEvents()
check("+ Section: in a second section", SD.item_sections(M, a) == ["1.1 Technical Approach", "1.2 Risk"])
pg.chips[1].remove.click(); app.processEvents()
check("the chip's x takes it out", SD.item_sections(M, a) == ["1.1 Technical Approach"])
w.authors.merge([("A. Lee", None), ("K. Park", None)], default=["Kestrel"])     # 2.77.0: names come from the author list
pg.authors.choose(answer=["A. Lee", "K. Park", "Not Listed"]); app.processEvents()
check("several authors, from the author list only", a["owner"] == "A. Lee, K. Park", a["owner"])
check("relationships say where the support is in the RFP", any("(L.1, p.1)" in l.text() for l in pg.rel_labels), [l.text()[:60] for l in pg.rel_labels])
x1, x2 = by("Pages shall be"), by("Each page shall be numbered")
click(x1["id"]); click(x2["id"], ctrl=True)
check("Ctrl+click adds a sentence far from the first", [x["id"] for x in pg.selected()] == [x1["id"], x2["id"]])
QTest.keyClick(pg.view, Qt.Key_J); app.processEvents()
check("J combines them (2.68.0: M is the M designation); both parts boxed", x2 not in M.items and len(pg.view.boxes[x1["id"]].path().toFillPolygons()) >= 2)
click(x1["id"])
k = [m.group(0) for m in __import__("re").finditer(r"[A-Za-z0-9]+", x1["text"])].index("Each")
r = pg.view.words[x1["id"]][k]
QTest.mouseClick(pg.view.viewport(), Qt.LeftButton, Qt.NoModifier, pg.view.mapFromScene(r.center()))
app.processEvents()
QTest.keyClick(pg.view, Qt.Key_S); app.processEvents()
parts = [it for it in M.items if it["id"].startswith(x1["id"])]
check("a click on a word, then S, splits there", len(parts) == 2 and parts[1]["text"].startswith("Each page"), [p["text"][:20] for p in parts])
QTest.keyClick(pg.view, Qt.Key_Z, Qt.ControlModifier); app.processEvents()
check("Ctrl+Z undoes the split", not any(it["id"] == x1["id"] + "a" for it in M.items) and any(it["id"] == x1["id"] for it in M.items))
check("autosave writes the matrix", wait(lambda: not M.pending, 6))
M2 = C.Matrix(out).load()
a2 = next(it for it in M2.items if it["id"] == a["id"])
check("the file holds the decisions", a2["decision"] == "Keep" and a2["owner"] == "A. Lee, K. Park"
      and C.cf_ids(next(it for it in M2.items if it["id"] == c["id"])["context_for"]) == [a["id"], b["id"]])
d = pg.volumes_dialog(); d._api["several"].setChecked(True)
for lab, box in d._api["boxes"]:
    box.setChecked(lab.startswith("Volume"))
d._api["save"](); app.processEvents()
check("Volumes...: the person's answer", SD.volumes_of(M)[0] == "several")
w.close_effort()
check("closing releases the effort", not os.path.isfile(ws0.p("lock.json")))
other = W.Workspace(W.data_dir_for(LIST), "Kestrel")
W.write_json(other.p("lock.json"), {"user": "someone", "computer": "OTHER-PC", "pid": 1, "time": "2099-01-01T00:00:00"})
check("an effort held elsewhere stays closed", not w.open_effort("Kestrel") and w.review is None)
os.remove(other.p("lock.json"))
check("reopening brings everything back", w.open_effort("Kestrel") and w.stack.currentWidget() is w.assign_page
      and w.review.item(a["id"])["owner"] == "A. Lee, K. Park")
w.close()
# 2.82.0: the decision buttons sit beside the response structure (where they land); sentence edits stay by the page
pgA = w.assign_page
col = pgA.tree.parentWidget()
check("decisions beside the response structure, the target named above them",
      all(pgA.keys[k].parentWidget() is pgA.dec_box for k in ("Requirement", "L", "M", "Support", "Customer's", "Not"))
      and pgA.dec_box.parentWidget() is col and pgA.keys["Combine"].parentWidget() is not pgA.dec_box
      and (pgA.target or "Click a section") and ("into" in pgA.target_lbl.text() or "Click a section" in pgA.target_lbl.text()), pgA.target_lbl.text())

n = sum(checks)
print(f"QT ASSIGN PASS ({n}/{len(checks)})" if n == len(checks) else f"QT ASSIGN FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
