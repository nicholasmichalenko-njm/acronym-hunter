"""4.56.0 offscreen: Acronyms under the hand (UX decisions 19 with Q7, 20, 61, 107, 108's mark, 109, 110; his answers 8,
9, 10 and 12). The card opens in a right margin of 320 pixels, level with the find, never over the page; Enter, X, N and
L decide (or pass) and move to the next find to decide, then the next page with finds; Later is a mark with a reason and
a note, kept with the effort and with the Acronym Finder's list; a read fixed in the Candidate box is kept with any of
the four, whose words then read Fix and...; Not a term is for the whole effort, this page only is the second choice;
Page done is gone. Fictional (the Kestrel set) and invented terms."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP
OP.available = lambda: False
from PySide6.QtGui import QFontInfo, QShortcut
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
import pictures as PIC
from skqt import design as D
from skqt.mainwin import MainWindow
from skqt import acrselbar as SB, acrmargin as MG, acrmove as MV, acrdecide as DC, acrlayout as AL, acrpart as APT
import acrlater as LT
import acrpages as AG
import acrmore as AM
import acrplace as AP
import efftrain as ET

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.OCR_FIXES_FILE = os.path.join(tmp, "ocr_corrections.csv")
LINES = [((40, 40, 300, 80), "TT8C ANTENNA", 0.05), ((40, 140, 520, 180), "MISSION OPERATIONS CENTER (MOC)", 0.97),
         ((40, 240, 300, 280), "GEP / SITE B", 0.96), ((40, 340, 520, 380), "trace each site in the DC-RVM", 0.97)]
A.scan_readings = lambda b: [(bx, t, c, "read") for bx, t, c in LINES]
PIC.read_region_lines = lambda crop: [((0, 0, crop.width, crop.height), "GEP / SITE B", 0.93)]
import picreadings as PR
PR.get = lambda key: None; PR.put = lambda *a, **k: None; PR.flush = lambda *a, **k: None
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.open_effort("Kestrel")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
op = ap.onpage
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
ap.scan([os.path.join(SAMPLES, n) for n in ("Kestrel_Technical_Volume.docx", "Kestrel_Program_Manual.pdf", "Kestrel_System_Diagram.png")])
t0 = time.time()
while ap.worker is not None and time.time() - t0 < 300:
    app.processEvents(); time.sleep(0.05)
s = ap.session
PKEY = "Kestrel_System_Diagram.png (Image)"
for t in ("TT8C", "DC", "DC-RVM"):
    if t not in s.results:
        AM.add_manual(s, t, "Acronym", "", document=PKEY, to=("results",))
ap.fill(); app.processEvents()
said = []
w.status = lambda text, *a, **k: said.append(str(text))


def said_text():
    return " | ".join(said[-6:]) + " | " + str(getattr(op, "said", ""))


def labels(bar):
    return [b.text() for b in bar.findChildren(QPushButton)] if bar is not None else []


def open_finds():
    return [i for i in range(len(op.items)) if MV._open_here(op, i)]


def show(key):
    op.go(key); op.wait(); app.processEvents()
    return op.state


def first_open():
    idx = sorted(open_finds(), key=lambda i: MV.order_of(op.items[i]))
    return idx[0] if idx else None


def pick(idx):
    op.select(idx); app.processEvents()
    if op.bar is not None and op.bar.kind != "decide":
        SB.keep_part(op); app.processEvents()
    return op.bar


def wait_move():
    op.wait(); app.processEvents(); op.wait(); app.processEvents()
    if op.bar is not None and op.bar.kind != "decide":           # a read with doubt or a part: decide it as a term here
        SB.keep_part(op); app.processEvents()


keys = [op.list.item(i).data(0x0100) for i in range(op.list.count()) if op.list.item(i).data(0x0100)]
pdf6 = next(k for k in keys if k.endswith("(p.6)"))
text_page = next(k for k in keys if "SCOPE OF WORK" in k)

# ---- 1. the card in the right margin
check("On the page is shown: the page keeps a right margin of 320 and a gap, on both views", ap.tabs.currentIndex() == 0
      and op.view.viewportMargins().right() == MG.margin() and op.text.viewportMargins().right() == MG.margin() and MG.CARD_W == 320,
      (op.view.viewportMargins().right(), MG.margin()))
ap.tabs.setCurrentIndex(1); app.processEvents()
check("... Everything found: the margin is given back", op.view.viewportMargins().right() == 0 and op.text.viewportMargins().right() == 0)
ap.tabs.setCurrentIndex(0); app.processEvents()
check("... On the page again: the margin is back", op.view.viewportMargins().right() == MG.margin())
show(pdf6)
i = first_open()
b = pick([i])
vp = op.view.viewport().geometry()
check("a picture page: the card is a child of the view (not of its viewport) and 320 wide", b is not None and b.parentWidget() is op.view
      and b.width() == MG.CARD_W, (b.parentWidget() if b else None, b.width() if b else None))
check("... it lies wholly to the right of the page, inside the view", b.geometry().left() > vp.right() and b.geometry().right() <= op.view.width(),
      (b.geometry(), vp))
top = vp.top() + op.sel_rect().top()
check("... level with the find (or held inside the view's height)", abs(b.geometry().top() - top) <= 1
      or b.geometry().top() in (vp.top(), op.view.height() - MG.GAP - b.height()), (b.geometry().top(), top))
op.view.verticalScrollBar().setValue(op.view.verticalScrollBar().value() + 40); app.processEvents()
top2 = vp.top() + op.sel_rect().top()
check("... and follows the page when it scrolls", abs(b.geometry().top() - top2) <= 1 or b.geometry().top() in (vp.top(), op.view.height() - MG.GAP - b.height())
      , (b.geometry().top(), top2))
order = labels(b)
check("one column: the four decisions one per row, each with its key, then Not a term on this page only",
      [x for x in order if x.split("  ")[0] in ("Add to effort list", "Not a term", "Skip", "Later")] == ["Add to effort list  Enter", "Not a term  X", "Skip  N", "Later  L"]
      and order.index("Later  L") < order.index("Not a term on this page only") and (b.b_here.ensurePolished(), b.main.ensurePolished()) and QFontInfo(b.b_here.font()).pointSizeF() < QFontInfo(b.main.font()).pointSizeF(), order)
check("... the Candidate box holds the term as read; the Definition box is there", b.cand is not None and b.cand.text() == b.terms[0] and b.typed is not None)
b.cand.setText(b.terms[0] + "Q"); app.processEvents()
fixed = [b.four[k].text() for k in DC.ORDER]
check("the Candidate differs: the four read Fix and..., keys the same", fixed == ["Fix and add to effort list  Enter", "Fix and mark Not a term  X",
                                                                               "Fix and skip  N", "Fix and mark Later  L"], fixed)
check("... the longest label fits the card", max(b.four[k].sizeHint().width() for k in DC.ORDER) <= MG.room() + 2,
      (max(b.four[k].sizeHint().width() for k in DC.ORDER), MG.room()))
check("... no separate Fix button; this page only waits while a fix is typed", not any(x.startswith("Fix the") or x == "Fix" for x in labels(b))
      and not b.b_here.isEnabled())
b.cand.setText(b.terms[0]); app.processEvents()
check("... the same as the read again: the words go back", [b.four[k].text() for k in DC.ORDER] == ["Add to effort list  Enter", "Not a term  X", "Skip  N", "Later  L"]
      and b.b_here.isEnabled())
show(text_page)
k0 = first_open()
b = pick([k0]); tv = op.text.viewport().geometry()
check("a text page: the card is a child of the text view, wholly to its right, 320 wide", b is not None and b.parentWidget() is op.text
      and b.geometry().left() > tv.right() and b.width() == MG.CARD_W, (b.geometry(), tv))
op.resize(op.width(), 300); app.processEvents(); MG.place(op)
check("a card taller than the view scrolls inside itself", b.height() <= op.text.height() and b.scroll.widget() is b.inner, (b.height(), op.text.height()))
op.resize(op.width(), 800); app.processEvents()

# ---- 2. Enter adds and moves on; with no definition too
show(pdf6)
i = first_open(); x = op.items[i]; t_add = x["term"]; at = MV.order_of(x)
pick([i])
SB.key(op, "enter"); wait_move()
nxt = op.selected()
check("Enter adds the term to the effort list", s.results[t_add].get("effort") == "In the list")
check("... and the next find to decide after it is selected, its card open", nxt and op.bar is not None and nxt[0]["term"] != t_add
      and AG.state_of(s.results[nxt[0]["term"]]) == "decide" and (op.key != pdf6 or MV.order_of(nxt[0]) > at), [y["term"] for y in nxt])
check("... one line with Undo says what happened", op.undo_lab.text().startswith(f"{t_add} added to the effort list.") and "Undo" in op.undo_lab.text(), op.undo_lab.text())
op.undo_last(); wait_move()
check("Undo takes it back and selects that find again", AG.state_of(s.results[t_add]) == "decide" and op.selected()
      and op.selected()[0]["term"] == t_add, s.results[t_add].get("effort"))
SB._pick(op.bar, 0); op.bar.typed.clear()
SB.key(op, "enter"); wait_move()
check("Enter on a term with no definition adds it with none and moves on", s.results[t_add].get("effort") == "In the list"
      and not (s.effort.rows[t_add].get("Definition") or "").strip() and op.selected() and op.selected()[0]["term"] != t_add)
check("... the count of terms with no definition stays in view", "no definition yet" in op.foot.text(), op.foot.text())

# ---- X: Not a term for the whole effort; this page only
t_x = op.selected()[0]["term"]
SB.key(op, "X"); wait_move()
check("X marks Not a term for the whole effort and moves on", s.results[t_x].get("effort") == "Not a term" or s.results[t_x].get("excluded"))
check("... its line", op.undo_lab.text().startswith(f"{t_x} marked Not a term in this effort. It will not be offered here again."), op.undo_lab.text())
check("... and the next find is selected", op.selected() and op.selected()[0]["term"] != t_x)
t_h = op.selected()[0]["term"]; key_h = op.key
s.results[t_h].setdefault("locations", []).append("Elsewhere.docx (para 4)")
op.bar.b_here.click(); wait_move()
check("Not a term on this page only does what X did before: off this page, still a find elsewhere", not AP.here(s, t_h, key_h)
      and AG.state_of(s.results[t_h]) == "decide" and "Elsewhere.docx (para 4)" in s.results[t_h]["locations"])
check("... its line, and the move on", op.undo_lab.text().startswith(f"{t_h} marked Not a term on this page only.") and op.selected()
      and op.selected()[0]["term"] != t_h, op.undo_lab.text())

# ---- Skip
t_n = op.selected()[0]["term"]; before = dict(s.results[t_n])
SB.key(op, "N"); wait_move()
check("Skip changes nothing and moves on", s.results[t_n].get("effort") == before.get("effort") and op.selected()
      and op.selected()[0]["term"] != t_n and (key_h, t_n) in MV.skipped(op) or (op.key, t_n) in MV.skipped(op))

# ---- Later
t_l = op.selected()[0]["term"]
SB.key(op, "L"); app.processEvents()
check("the first L opens the two reasons and a note on the card", op.bar.later_w.isVisible() and op.bar.later_btns["come"].text() == "Come back to it  L"
      and op.bar.later_btns["author"].text() == "For author review  R")
SB.key(op, "Escape"); app.processEvents()
check("Esc closes them without marking", not op.bar.later_w.isVisible() and t_l not in LT.marks(s))
SB.key(op, "L"); SB.key(op, "L"); wait_move()
check("L then L: marked for later, Come back to it, and the move on", LT.reason_of(s, t_l) == "come" and op.selected()
      and op.selected()[0]["term"] != t_l, LT.marks(s).get(t_l))
check("... its line", op.undo_lab.text().startswith(f"{t_l} marked for later: come back to it."), op.undo_lab.text())
t_r = op.selected()[0]["term"]
SB.key(op, "L"); op.bar.note.setText("ask the thermal lead"); SB.key(op, "R"); wait_move()
check("L then R: For author review, with the note and when", LT.reason_of(s, t_r) == "author" and LT.marks(s)[t_r]["note"] == "ask the thermal lead"
      and LT.marks(s)[t_r]["when"], LT.marks(s).get(t_r))
check("... its line", op.undo_lab.text().startswith(f"{t_r} marked for later: for author review."), op.undo_lab.text())
op.undo_last(); wait_move()
check("Undo takes the mark back off and selects that find", t_r not in LT.marks(s) and op.selected() and op.selected()[0]["term"] == t_r)
SB.key(op, "L"); SB.key(op, "enter"); wait_move()
check("Enter with the reasons open takes Come back to it", LT.reason_of(s, t_r) == "come", LT.marks(s).get(t_r))
LT.mark(s, [t_r], "author", "ask the thermal lead")
op.fill(); app.processEvents()
pgs = op.pages()
check("a term marked Later is not to decide; the line counts it by reason", "for author review" in op.progress_lab.text()
      and "for later" in op.progress_lab.text() and op.progress_lab.text().split(",")[0].endswith("to decide"), op.progress_lab.text())
check("... the page list too", all(t_l not in [t for t, st in p["terms"].items() if st == "decide"] or p["later"] for p in pgs))
ap.tabs.setCurrentIndex(1); app.processEvents()
check("Everything found: To decide leaves them out; For later and For author review count them", ap.count_btns["For later"].text() == "For later 1"
      and ap.count_btns["For author review"].text() == "For author review 1", [b_.text() for b_ in ap.count_btns.values()])
AL.pick_count(ap, "For later"); app.processEvents()
check("... For later is its own filter", ap.terms == [t_l], ap.terms)
check("... its row says for later", any("(for later)" in (ap.table.item(r, 5).text() if ap.table.item(r, 5) else "") for r in range(ap.table.rowCount())))
AL.pick_count(ap, "For author review"); app.processEvents()
check("... For author review is its own filter", ap.terms == [t_r], ap.terms)
AL.pick_count(ap, "To decide"); app.processEvents()
check("... To decide does not list them", t_l not in ap.terms and t_r not in ap.terms)
AL.pick_count(ap, "To decide"); ap.tabs.setCurrentIndex(0); app.processEvents()
key_l = AG.place_of(s.results[t_l]["locations"][0])
show(key_l)
il = [i for i, x in enumerate(op.items) if x["term"] == t_l and not x.get("behind")]
check("on the page a Later find is marked as such (its own colour)", il and op.kind(op.items[il[0]]) == "later")
check("Enter, X, Skip and Later step past it", all(op.items[i]["term"] not in (t_l, t_r) for i in open_finds()))
pick(il[:1])
check("its card has Take the mark off", op.bar.b_take_off is not None and op.bar.b_take_off.text() == "Take the mark off")
op.bar.b_take_off.click(); app.processEvents()
check("Take the mark off: to decide again", t_l not in LT.marks(s) and AG.state_of(s.results[t_l]) == "decide")
LT.mark(s, [t_l], "come")
op.fill(); pick(il[:1]); SB.key(op, "enter"); wait_move()
check("a Later term can be decided at any time; deciding takes the mark off", s.results[t_l].get("effort") == "In the list"
      and t_l not in LT.marks(s) and t_l not in LT._all(s))

# ---- a Later term never reaches the effort list export or the custom dictionary
import openpyxl, effortdata as EDT
from skqt import acrtool as TL
s.add([t_r], "Kestrel invented meaning")             # in the list first, then back to undecided and marked Later
s.list_remove([t_r]); LT.mark(s, [t_r], "author")
out = os.path.join(tmp, "lists"); os.makedirs(out)
made = s.export_effort_lists(folder=out, scope="whole") or []
cells = set()
for p_ in made:
    if str(p_).endswith(".xlsx"):
        for row in openpyxl.load_workbook(p_).active.iter_rows(values_only=True):
            cells |= {str(c) for c in row if c}
check("the effort list export leaves a Later term out", made and t_r not in cells and t_add in cells, (made, t_r))
s.list_definition(t_add, "Kestrel invented meaning two")
from skqt import acrfast as AF
AF.flush(ap)
check("... and the custom dictionary for Word", t_r not in EDT.dictionary_words(cfg, LIST) and t_add in EDT.dictionary_words(cfg, LIST))
check("... and the Acronym Finder's list", t_r not in [t for t, _m in TL.list_rows(s)])

# ---- a page whose finds to decide are not boxed (the page reader did not find the term where the scan did)
MV.clear_pass(op)
pgs_open = [p["key"] for p in MV._pages(op) if MV._open_page(op, p)]
if len(pgs_open) >= 2:
    blind = pgs_open[0]
    real_next = MV.next_here
    MV.next_here = lambda o, after=None, later=False: None if o.key == blind else real_next(o, after, later)
    try:
        MV.go_then(op, blind); wait_move()
        for _ in range(100):
            if op.key != blind and op.state != "reading":
                break
            app.processEvents(); time.sleep(0.05)
        op.wait(); app.processEvents()
    finally:
        MV.next_here = real_next
    check("a page with finds to decide and none boxed is passed: the move never ends on a page with no card",
          op.key != blind and blind in MV.unboxed(op), (op.key, blind))
    check("... and one line says so and where they are", "could not be boxed on the page" in said_text() and "Everything found" in said_text(),
          said_text())
    MV.clear_pass(op)
else:
    check("a page with finds to decide and none boxed is passed (not enough pages left to try)", True)

# ---- 3. the fix is kept with any of the four
show(PKEY)
it = [i for i, x in enumerate(op.items) if x["term"] == "TT8C"]
op.select(it); app.processEvents()
check("a read with doubt, Candidate untouched: the card asks what the picture says first (Read as, It says)", op.bar.kind == "doubt"
      and op.bar.says.text() == "TT8C")
SB.keep_part(op); app.processEvents()
op.bar.cand.setText("TQ8Z"); app.processEvents()
SB.key(op, "enter"); wait_move()
samples = ET.load(ET._root(s))
check("Fix and add to effort list: the corrected term is in the list, the misread is Not a term", s.results.get("TQ8Z", {}).get("effort") == "In the list"
      and AG.state_of(s.results["TT8C"]) == "not")
check("... the corrected read is saved on this PC and in the training data", "TT8C" in open(A.OCR_FIXES_FILE, encoding="utf-8").read()
      and any(x_["kind"] == "misread" and x_["read"] == "TT8C" and x_["right"] == "TQ8Z" for x_ in samples))
check("... the line says both things, and no question was asked", op.undo_lab.text().startswith("TQ8Z added to the effort list. The corrected read is saved on this PC and in the training data."),
      op.undo_lab.text())
op.undo_last(); wait_move()
check("Undo takes back both: the term, the misread rule and the training sample; the find is selected again", "TQ8Z" not in s.effort.rows
      and "TQ8Z" not in s.results and AG.state_of(s.results["TT8C"]) == "decide" and "TT8C" not in open(A.OCR_FIXES_FILE, encoding="utf-8").read()
      and not any(x_["right"] == "TQ8Z" for x_ in ET.load(ET._root(s))) and op.selected() and op.selected()[0]["term"] == "TT8C",
      (op.selected(), s.results.get("TT8C", {}).get("effort")))
SB.keep_part(op); app.processEvents(); op.bar.cand.setText("TQ8Y"); SB.key(op, "X"); wait_move()
check("Fix and mark Not a term: the corrected term is Not a term, the fix kept, at once", AG.state_of(s.results.get("TQ8Y", {})) == "not"
      and "TQ8Y" in open(A.OCR_FIXES_FILE, encoding="utf-8").read() and op.undo_lab.text().startswith("TQ8Y marked Not a term in this effort."))
op.undo_last(); wait_move()
SB.keep_part(op); app.processEvents(); op.bar.cand.setText("TQ8X"); SB.key(op, "N"); wait_move()
check("Fix and skip: the correction is saved and nothing is decided; the corrected term stands to decide", AG.state_of(s.results.get("TQ8X", {})) == "decide"
      and "TQ8X" not in s.effort.rows and "TQ8X" in open(A.OCR_FIXES_FILE, encoding="utf-8").read() and "stands as a find to decide" in op.undo_lab.text())
op.undo_last(); wait_move()
SB.keep_part(op); app.processEvents(); op.bar.cand.setText("TQ8W"); SB.key(op, "L"); SB.key(op, "enter"); wait_move()
check("Fix and mark Later: the correction saved, the corrected term marked for later", LT.reason_of(s, "TQ8W") == "come"
      and "TQ8W" in open(A.OCR_FIXES_FILE, encoding="utf-8").read() and op.undo_lab.text().startswith("TQ8W marked for later: come back to it."))
op.undo_last(); wait_move()
SB.keep_part(op); app.processEvents(); op.bar.cand.setText(t_add); SB.key(op, "enter"); wait_move()
check("the corrected term is already in the list: said so, the fix saved, the find counts for it", op.undo_lab.text().startswith(f"{t_add} is already in the effort list.")
      and PKEY in [AG.place_of(l_) for l_ in s.results[t_add]["locations"]] and s.results[t_add].get("effort") == "In the list", op.undo_lab.text())
op.undo_last(); wait_move()

# ---- 4 and 5. words; Page done is gone
words = labels(op.bar) + [a.text() for a in ap.on_bar.more_menu.actions()] + ap.on_bar.labels() + [op.undo_lab.text(), op.progress_lab.text(),
        op.foot.text(), op.left_lab.text()] + [op.list.item(i).text() for i in range(op.list.count())]
bad = [x for x in words if any(b_ in x for b_ in ("Ignore", "ignore", "Page done")) or " done" in x or x.endswith("decided")]
check("no Ignore, ignored, done or Page done on the tab, its bar, its card or its Undo line", not bad, bad)
check("Next page with finds is the bar's main button", ap.on_bar.main is ap.b_nextpage and ap.b_nextpage.text() == "Next page with finds")
AG.set_done(s.ws, PKEY, True); op.fill(); app.processEvents()
items = {op.list.item(i).data(0x0100): op.list.item(i).text() for i in range(op.list.count())}
check("a saved done mark is ignored (the page shows what it holds) and nothing is deleted", PKEY in AG.done_set(s.ws)
      and "done" not in items[PKEY] and (items[PKEY].strip().endswith("to decide") or "Nothing to decide, as of the last scan" in items[PKEY]
                                         or "for" in items[PKEY]), items[PKEY])

# ---- the move crosses to the next page with finds and selects its first
MV.clear_pass(op)
for src in [p["key"] for p in op.shown_pages() if p["to_decide"] and p["key"] != PKEY]:
    show(src)
    here = sorted(open_finds(), key=lambda i: MV.order_of(op.items[i]))
    if here:
        break
for t in {op.items[i]["term"] for i in here} - {op.items[here[0]]["term"]}:
    s.add([t], "")
op.fill(); app.processEvents()
last = open_finds()
want = MV.next_page(op)
pick(last[:1])
SB.key(op, "enter"); wait_move()
check("the last find on a page: the next page with finds shows, its first find to decide selected", op.key == want and want != src
      and op.selected() and AG.state_of(s.results[op.selected()[0]["term"]]) == "decide", (op.key, want, op.selected()))

# ---- skip does not loop; only Later left; nothing left
LT.unmark(s, list(LT.marks(s)))
pages_all = op.shown_pages()
open_terms = sorted({t for p in pages_all for t, st in p["terms"].items() if st == "decide"})
last_t = open_terms[0]
for t in open_terms[1:]:
    s.add([t], "")
LT.unmark(s, list(LT.marks(s)))
MV.clear_pass(op)
op.fill(); app.processEvents()
show(AG.place_of(s.results[last_t]["locations"][0]))
pick([i for i, x in enumerate(op.items) if x["term"] == last_t and op.visible(i) and not x.get("behind")][:1])
for _k in range(40):                                  # the same term on other pages is another find: each is passed once
    SB.key(op, "N"); wait_move()
    if op.said.startswith("You have been through every find.") or op.bar is None:
        break
check("Skip on the last find left: no loop; the pass ends and says so", op.said.startswith("You have been through every find.") and not MV.skipped(op), op.said)
LT.mark(s, [last_t], "author"); op.fill(); app.processEvents()
MV.move_on(op, (0, 0, 0)); wait_move()
check("only Later finds left: the first of them is selected and the line says so", op.said == MV.ONLY_LATER and op.selected()
      and op.selected()[0]["term"] == last_t, op.said)
LT.unmark(s, [last_t]); op.fill(); app.processEvents()
pick([i for i, x in enumerate(op.items) if x["term"] == last_t and op.visible(i) and not x.get("behind")][:1])
SB.key(op, "enter"); wait_move()
check("nothing left: the page stays and says Nothing to decide, as of the last scan", op.said == MV.NOTHING
      and op.progress_lab.text() == MV.NOTHING, (op.said, op.progress_lab.text()))

# ---- keys: not while typing; N, L and R clash with nothing
show(text_page)
pick([i for i in range(len(op.items)) if op.visible(i) and not op.items[i].get("behind")][:1])
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    w.activateWindow(); QApplication.setActiveWindow(w)
op.bar.cand.setFocus(); app.processEvents()
n_sc = next(k for k in op.keys if k.key().toString() == "N")
t_now = op.selected()[0]["term"] if op.selected() else None
n_sc.activated.emit(); app.processEvents()
check("keys do not fire while typing in a box", AL._typing() and op.bar is not None and op.selected() and op.selected()[0]["term"] == t_now
      and not MV.skipped(op))
mine = [k.key().toString() for k in op.keys]
others = [k for k in w.findChildren(QShortcut) if k.key().toString() in ("N", "L", "R") and k not in op.keys
          and k.isEnabled() and k.parent() is not None and k.parent().isVisible()]
check("N, L and R clash with nothing on this page (each once; no other shortcut on screen)", all(mine.count(k) == 1 for k in ("N", "L", "R"))
      and not others and not ({"N", "L", "R"} & {"A", "B", "U", "S", "1", "2", "X"}), [(k.key().toString(), k.parent()) for k in others])

# ---- the Later mark kept across close and reopen: in an effort
show(text_page)
keep_t = "KQXV"
AM.add_manual(s, keep_t, "Acronym", "", document=text_page, to=("results",))
LT.mark(s, [keep_t], "author", "kept across a reopen")
w.close(); app.processEvents()
w2 = MainWindow(app, cfg, A.APP_VERSION); w2.resize(1600, 980); w2.show()
w2.open_effort("Kestrel"); w2.go("acronyms"); app.processEvents()
s2 = w2.acronym_page.session
check("in an effort: the Later mark is there after the page is closed and opened again", LT.reason_of(s2, keep_t) == "author"
      and LT.marks(s2)[keep_t]["note"] == "kept across a reopen", LT.marks(s2))
w2.close(); app.processEvents()

# ---- and in the Acronym Finder
from skqt.acrtool import AcronymToolWindow
tw = AcronymToolWindow(cfg); tw.show(); app.processEvents()
tw.page.scan([os.path.join(SAMPLES, "Kestrel_Technical_Volume.docx")])
t0 = time.time()
while tw.page.worker is not None and time.time() - t0 < 300:
    app.processEvents(); time.sleep(0.05)
fs = tw.page.session
ft = next(t for t, d in fs.results.items() if AG.state_of(d) == "decide" and not t.startswith("["))
APT.later(tw.page, [ft], "author")
check("the Acronym Finder has a workspace of its own for the mark", fs.ws is not None and LT.reason_of(fs, ft) == "author")
check("... and its exported list leaves the Later term out", ft not in [t for t, _m in TL.list_rows(fs)])
tw.page.session.save(); tw.close(); app.processEvents()
tw2 = AcronymToolWindow(cfg); tw2.show(); app.processEvents()
check("in the Acronym Finder: the Later mark is there after the window is closed and opened again", LT.reason_of(tw2.page.session, ft) == "author",
      LT.marks(tw2.page.session))
tw2.close(); app.processEvents()

print(f"{sum(checks)}/{len(checks)} passed")
print(f"QT ACR 4560 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)

