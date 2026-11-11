"""3.29.0 Review, offscreen: Add missed text keeps every glyph it takes in ("2)" with its bracket, on the first try) and
the added sentence is boxed where it was read, never on the same words elsewhere; a press on the opening bracket of
"(CUI)" or past the full stop reaches the sentence's first and last words, and the picked words carry the bracket and
the full stop; the selection bar stays in place; a right-click on a decided sentence takes the decision off, takes a
capture off, or clears the selection; in the structure only a left double-click renames and a right-click opens a
menu with Rename; a list's items captured as objectives are one objective each, each with the
list's lead-in."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, pdfmini, capture as CAP, excerpts as EX, effortrec as RR
OP.available = lambda: False
from PySide6.QtCore import Qt, QEvent, QPointF, QRectF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Plover"); os.makedirs(EDIR)
LINES = ["L.4 PROPOSAL INSTRUCTIONS",
         "The Offeror shall provide 2 copies of the technical volume.",
         "The Government's objectives for this effort are to:",
         "1) Reduce the cost of sustaining the ground system.",
         "2) Shorten the time to field new capability.",
         "3) Improve the availability of the mission network.",
         "(CUI) The Offeror shall mark every page of the proposal.",
         "The Offeror shall describe its quality plan."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=10)
LIST = os.path.join(EDIR, "Plover_Effort_List.xlsx")
L = E.EffortList(LIST, "Plover"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Plover", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Plover").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Plover")
w.read_page.read([PDF], os.path.join(EDIR, "Plover_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page; v = pg.view
pg.files.setCurrentText("Section_L.pdf"); app.processEvents()
by = lambda s: next((it for it in M.items if it["text"].startswith(s)), None)

# ---------------------------------------------------------------- Add missed text: "2)" where it was read
import pypdfium2 as pdfium
doc = pdfium.PdfDocument(PDF); page = doc[0]; _pw, ph = page.get_size(); tp = page.get_textpage()
full = tp.get_text_range()
k2 = full.index("2) Shorten")
cb = [tp.get_charbox(i) for i in (k2, k2 + 1)]
tp.close(); doc.close()
area = (cb[0][0] - 0.5, ph - max(c[3] for c in cb) - 0.5, cb[1][2] - 1.0, ph - min(c[1] for c in cb) + 0.5)
txt, how = CAP.text_in(PDF, 0, area)
check("an area over a list number keeps its bracket, even with the edge of the box on it", (txt, how) == ("2)", "pdf"), (txt, how))
place = CAP.area_place(PDF, 1, area, txt)
check("its place is the words it took in, on this page", place.startswith("1:"), place)
from skqt import assign as AS
rect = QRectF(area[0] + AS.MARGIN, area[1] + pg.tops[0], area[2] - area[0], area[3] - area[1])
it2 = pg.capture_area(rect, text="2)", how="pdf")
check("added on the first try, as read", it2 is not None and it2["text"] == "2)" and it2.get("place") == place, it2 and (it2["text"], it2.get("place")))
box = v.boxes.get(it2["id"]) if it2 else None
zone = QRectF(rect).adjusted(-3, -3, 3, 3)
check("its box is where it was read, not on the 2 in the sentence above", box is not None and zone.intersects(box.boundingRect())
      and abs(box.boundingRect().center().y() - rect.center().y()) < 6, box and box.boundingRect())
check("... it is the one selected", [x["id"] for x in pg.selected()] == [it2["id"]])

# ---------------------------------------------------------------- the edges of a sentence
cui = by("(CUI) The Offeror shall mark")
check("the (CUI) sentence is read whole", cui is not None and cui["text"].startswith("(CUI)"), cui and cui["text"])
iid = cui["id"]
words = v.words[iid]
br = v.boxes[iid].boundingRect()
check("its box takes in the opening bracket before its first word and the full stop after its last",
      br.left() < words[0].left() - 1 and br.right() > words[-1].right() + 1, (br, words[0], words[-1]))


def ev(kind, pt):
    p = QPointF(v.mapFromScene(pt))
    btn = Qt.LeftButton if kind != QEvent.MouseMove else Qt.NoButton
    return QMouseEvent(kind, p, v.viewport().mapToGlobal(p.toPoint()), btn,
                       Qt.LeftButton if kind != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier)


pg.select(iid); app.processEvents()
start = QPointF(br.left() + 1.0, words[0].center().y())               # on the "(" before CUI
end = QPointF(words[-1].right() + 30, words[-1].center().y())          # past the full stop
check("a press on the opening bracket is on the first word", v.word_at(v.mapFromScene(start))[1] == 0)
v.mousePressEvent(ev(QEvent.MouseButtonPress, start)); app.processEvents()
v.mouseMoveEvent(ev(QEvent.MouseMove, end)); app.processEvents()
v.mouseReleaseEvent(ev(QEvent.MouseButtonRelease, end)); app.processEvents()
g = pg.grab or {}
check("a drag from the bracket to past the end picks every word", g.get("iid") == iid and g.get("text") == cui["text"], g.get("text"))
check("... with the ( at the front and the full stop at the end", (g.get("text") or "").startswith("(CUI)")
      and (g.get("text") or "").endswith("proposal."))

# ---------------------------------------------------------------- the selection bar does not jump
pg.view.scene().clearSelection(); app.processEvents()
h0, y0 = pg.bulk.height(), pg.view.geometry().top()
check("the selection bar is in place with nothing selected", pg.bulk.isVisibleTo(w) and not pg.bulk_dec.isEnabled())
items = [by("Reduce"), by("Shorten")]
items = [x for x in items if x]
pg._guard = True
for x in items:
    v.boxes[x["id"]].setSelected(True)
pg._guard = False; pg.on_select(); app.processEvents()
check("two selected: the bar fills in, the page stays where it was", pg.bulk_lbl.text() == "2 sentences selected"
      and pg.bulk.height() == h0 and pg.view.geometry().top() == y0, (pg.bulk.height(), h0, pg.view.geometry().top(), y0))

# ---------------------------------------------------------------- objectives: one per item, each with its lead-in
lead = by("The Government").get("text")
li = [it for it in M.items if it.get("lead") == lead]
check("the list's items carry their lead-in", len(li) == 3, [it["text"] for it in li])
pg._guard = True; v.scene().clearSelection()
for x in li:
    v.boxes[x["id"]].setSelected(True)
pg._guard = False; pg.on_select(); app.processEvents()
got = pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": "", "sections": []})
rec = RR.Record(w.ws.root)
objs = EX.excerpts(rec, "objective")
check("three items: three objectives", isinstance(got, list) and len(got) == 3 and len(objs) == 3, got)
check("each carries the lead-in, then its own item", all(EX.text_of(x).startswith(lead + " ") and x["parts"][0].get("intro")
      for x in objs) and sorted(EX.text_of(x)[len(lead) + 1:][:10] for x in objs) == sorted(it["text"][:10] for it in li),
      [EX.text_of(x) for x in objs])
lsent = next((it for it in M.items if it["text"] == lead), None)
for x in list(objs):
    EX.remove(rec, x["id"])
if lsent:
    pg._guard = True; v.scene().clearSelection()
    for x in [lsent] + li[:2]:
        v.boxes[x["id"]].setSelected(True)
    pg._guard = False; pg.on_select(); app.processEvents()
    pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": "", "sections": []})
    objs = EX.excerpts(RR.Record(w.ws.root), "objective")
    check("the lead-in selected with two items: two objectives, not three", len(objs) == 2
          and all(EX.text_of(x).startswith(lead) for x in objs), [EX.text_of(x) for x in objs])
one = by("The Offeror shall describe its quality plan")
pg.select(one["id"]); app.processEvents()
x1 = pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": "", "sections": []})
check("a sentence that is not in a list: one objective, its words only", isinstance(x1, str)
      and EX.text_of(EX.get(RR.Record(w.ws.root), x1)) == one["text"])

# ---------------------------------------------------------------- right-click
pg.select(one["id"]); app.processEvents()
pg.do_lm("L"); app.processEvents()
check("decided L", pg.R.item(one["id"]).get("decision") == "Keep")
m = pg.sentence_menu(one["id"])
acts = [a.text() for a in m.actions() if a.text()]
check("right-click a decided sentence: Take the decision off, with its name", any(t.startswith("Take the decision off: Instruction") for t in acts), acts)
check("... and each capture from it, and Clear selection", any("Take off the capture Objective" in t for t in acts)
      and "Clear selection" in acts, acts)
next(a for a in m.actions() if a.text().startswith("Take the decision off")).trigger(); app.processEvents()
check("Take the decision off: the sentence is undecided again", not pg.R.item(one["id"]).get("decision"))
m = pg.sentence_menu(one["id"])
next(a for a in m.actions() if a.text().startswith("Take off the capture")).trigger(); app.processEvents()
check("Take off the capture: gone", EX.get(RR.Record(w.ws.root), x1) is None)
other = by("The Offeror shall provide 2 copies")
m = pg.sentence_menu(other["id"])
check("right-click a sentence outside the selection: it becomes the selection", [x["id"] for x in pg.selected()] == [other["id"]])
next(a for a in m.actions() if a.text() == "Clear selection").trigger(); app.processEvents()
check("Clear selection", not pg.selected())
# ---------------------------------------------------------------- the structure: left double-click renames, right-click menu
from PySide6.QtCore import QPoint
tr = pg.tree
it0 = next(tr.topLevelItem(i) for i in range(tr.topLevelItemCount()) if tr.topLevelItem(i).data(0, Qt.UserRole))
lab0 = it0.data(0, Qt.UserRole)
asked = []
pg._ask = lambda *a, **k: (asked.append(a), "Technical and Management")[1]
pt = QPointF(tr.visualItemRect(it0).center())
dbl = lambda btn: QMouseEvent(QEvent.MouseButtonDblClick, pt, tr.viewport().mapToGlobal(pt.toPoint()), btn, btn, Qt.NoModifier)
tr.mouseDoubleClickEvent(dbl(Qt.RightButton)); app.processEvents()
check("a right double-click on a section does not rename it", not asked)
m = pg.structure_menu(lab0)
acts = [a.text() for a in m.actions() if a.text()]
check("right-click a section: its menu, starting with Rename...", acts[:2] == ["Rename...", "Pages..."] and "Delete" in acts
      and "Move to a part..." in acts and pg.target == lab0, acts)
next(a for a in m.actions() if a.text() == "Rename...").trigger(); app.processEvents()
check("Rename... from the menu renames it", asked and pg.target and pg.target.endswith("Technical and Management"), pg.target)
w.close()
n = sum(checks)
print(f"QT REVIEW GRAB {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
