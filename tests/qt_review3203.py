"""3.20.3 the review layout and the issues of 2026-11-02, offscreen: Review lays itself out in the window (no page
scroll at 1280x800; the right panel scrolls on its own, decisions on top); Make a sentence (Shift+S, was Extract) makes dragged words a
sentence of their own, one Undo step; Split asks where when no word is clicked; the wheel glides; a captured rule's value
is fixed from the sentence's card; dashboard cards fit half width (their buttons wrap) and a tile's number never runs
past its edge; Questions due shows on the dashboard; a meeting's selected notes become a topic; the new labels; the
Condense arrows."""
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
from PySide6.QtWidgets import QScrollArea, QSplitter
from PySide6.QtGui import QShortcut, QFontMetrics, QFont

# ---------------------------------------------------------------- Review fits the window
w.resize(1280, 800); app.processEvents(); app.processEvents()
sa = next(x for x in w.stack.findChildren(QScrollArea) if getattr(x, "page", None) is pg)
check("Review lays itself out in the window: the page never scrolls as a whole", sa.verticalScrollBar().maximum() == 0
      and sa.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff, sa.verticalScrollBar().maximum())
check("decisions at the bottom; the right panel: the card, then the structure, each scrolling on its own",
      pg.bottom_split.indexOf(pg.decide_area) == 1 and pg.right.indexOf(pg.card_area) == 0 and pg.right.indexOf(pg.views) == 1
      and pg.views.stack.indexOf(pg.side_area) == 0)   # 3.34.1: decide tools at the bottom; 3.90.0: the structure is the first view

# ---------------------------------------------------------------- Extract
a = by("The Offeror shall describe its technical approach")
n0, text = len(M.items), a["text"]
s0 = text.index("technical approach"); e0 = s0 + len("technical approach")
mid = pg.do_extract({"iid": a["id"], "s": s0, "e": e0})
check("Extract: the dragged words are a sentence of their own, between the parts before and after", mid is not None
      and mid["text"] == "technical approach" and len(M.items) == n0 + 2 and pg.selected() and pg.selected()[0]["id"] == mid["id"],
      mid)
check("Extract is one Undo step", w.review.undo_label().startswith("extract"), w.review.undo_label())
w.review.undo_last(); pg.build_boxes(); app.processEvents()
check("Undo puts the sentence back whole", len(M.items) == n0 and any(it["text"] == text for it in M.items))
check("Make a sentence has its button and Shift+S", "Make" in pg.keys and any(k.key().toString() == "Shift+S" for k in pg.findChildren(QShortcut)))
check("whole sentence: nothing to extract", pg.do_extract({"iid": a["id"], "s": 0, "e": len(text)}) is None)

# ---------------------------------------------------------------- Split where you click
a = next(it for it in M.items if it["text"] == text)
pg.select(a["id"]); pg.split_at = None
pg.ask_split_at = lambda it, answer=None: text.index("technical")
n0 = len(M.items)
pg.do_split()
check("Split with no word clicked splits where you click in the text", len(M.items) == n0 + 1
      and any(it["text"].startswith("technical approach") for it in M.items))
w.review.undo_last(); pg.build_boxes(); app.processEvents()

# ---------------------------------------------------------------- the wheel glides
v = pg.view
v.verticalScrollBar().setValue(0)
t1 = v.smooth_scroll(120); t2 = v.smooth_scroll(120)
check("the wheel glides, and quick notches add up", t2 > t1 > 0 and v._glide.duration() == 200, (t1, t2))
wait(lambda: v._glide.state() != v._glide.State.Running, 3)
check("the glide ends where it aimed", v.verticalScrollBar().value() == t2, v.verticalScrollBar().value())

# ---------------------------------------------------------------- a captured value fixed on the card
import docversions as DV, subreq as SR
a = next(it for it in M.items if it["text"] == text)
reg = SR.Register(DV.Library(w.ws.p("documents")).load())
key = reg.add("Contact", "Contracting officer", "jane.doe@exmaple.gov",
              source={"doc": "Section_L_print.pdf", "loc": "p1", "text": a["text"], "sid": a["id"]})
pg.select(a["id"]); pg.show_card(pg.selected()); app.processEvents()
check("the card lists what was captured from the sentence, with its value to fix", key in pg.capture_edits
      and pg.capture_edits[key].text() == "jane.doe@exmaple.gov", list(pg.capture_edits))
pg.edit_capture(key, "jane.doe@example.gov")
row = next((r for r in SR.Register(DV.Library(w.ws.p("documents")).load()).rows() if r.get("key") == key), {})
check("Save keeps the fixed value", row.get("value") == "jane.doe@example.gov", row)

# ---------------------------------------------------------------- the dashboard at half width
import branding as BR
w.go("home"); app.processEvents()
hp = w.home_page
hp.customize({"role": "Proposal Manager", "order": list(BR.KEYS), "hidden": [], "widths": {k: "half" for k in BR.KEYS}})
app.processEvents(); app.processEvents()
half = (hp.scroll.viewport().width() - 2 * theme.SPACE["xl"] - theme.SPACE["m"]) // 2
big = [(k, c.minimumSizeHint().width()) for k, c in hp.cards.items() if c.minimumSizeHint().width() > half]
check("every dashboard card fits half width at 1280 (its buttons wrap)", not big, (half, big))
t = w.dash_page.tiles["placed"]
t.set("1240 of 1500", "requirements placed in a section"); app.processEvents()
f = QFont(t.value.font()); f.setPointSizeF(t._pt[0]); f.setWeight(QFont.DemiBold)
check("a tile's number gets smaller rather than run past the edge", t._pt[0] < theme.TYPE["display"] + 4
      and QFontMetrics(f).horizontalAdvance("1240 of 1500") <= t.width() - 2 * theme.SPACE["l"], t._pt)
t.set("7", "requirements placed in a section"); app.processEvents()
check("a short number stays large", t._pt[0] == theme.TYPE["display"] + 4, t._pt)

# ---------------------------------------------------------------- Questions due
import datetime, effortrec as RR, effortcal as EC, custqa as CQ
day = datetime.date.today() + datetime.timedelta(days=5)
EC.add_entry(RR.Record(w.ws.root), kind="Questions due", date=day.isoformat(), title="Questions due to the contracting officer")
CQ.add(RR.Record(w.ws.root), "Is the page limit per volume?")
w.dash_page.refresh(); app.processEvents()
q = w.dash_page.tiles["qdue"]
check("the dashboard shows when questions are due and how many are not submitted", q.value.text() == "5"
      and "questions are due" in q.caption.text() and "1 not submitted" in q.caption.text(), (q.value.text(), q.caption.text()))
check("Questions due sits with the effort health numbers", hp.health.isAncestorOf(q))

# ---------------------------------------------------------------- a meeting topic from selected notes
import meetings as MT
mp = w.meetings_page
w.go("meetings"); app.processEvents()
mid_ = mp.new_meeting("Pink team debrief")
mp.notes.setPlainText("We agreed the transition plan needs a risk table. Also check staffing."); app.processEvents()
words = "the transition plan needs a risk table"
cur = mp.notes.textCursor(); s = mp.notes.toPlainText().index(words)
cur.setPosition(s); cur.setPosition(s + len(words), cur.MoveMode.KeepAnchor); mp.notes.setTextCursor(cur)
app.processEvents()
check("selecting words in the notes turns on Make a topic of the selection", mp.sel_btn.isEnabled())
tid = mp.topic_from_selection(ask=False)
tp = MT.topic(RR.Record(w.ws.root), mid_, tid) if tid else None
check("the selected words become a topic to follow up", tp is not None and tp["text"] == words and tp["status"] == "open", tp)
check("the notes box is large, with room between it and the meeting list", mp.notes.minimumHeight() >= 220
      and mp.findChild(QSplitter).handleWidth() >= theme.SPACE["l"])

# ---------------------------------------------------------------- labels and the header arrows
from skqt import starteffort as SE
here = os.path.dirname(SE.__file__)
src = "".join(open(os.path.join(here, n), encoding="utf-8").read() for n in ("starteffort.py", "recordpage.py", "brandview.py"))
check("Opportunity Number (Client Issued) and Internal A Number", "Opportunity Number (Client Issued)" in src and "Internal A Number" in src)
w.go("home"); app.processEvents()
bn = hp.banner
check("Condense and Expand are arrows", bn.cond_btn.text() == "▲" and bn.exp_btn.text() == "▼")
bn.set_condensed(True, save=False, animate=True)
check("condensing glides (an animation, not a jump)", getattr(bn, "_fold_anim", None) is not None)
bn.set_condensed(False, save=False)

print(f"QT REVIEW 3.20.3 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
w.close()
sys.stdout.flush(); __import__("hangguard").end(0 if all(checks) else 1)
