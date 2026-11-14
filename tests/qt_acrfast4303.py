"""4.30.3 (Nicholas 2026-11-13 16:23: with nearly 2,500 candidates every decision froze the window). A decision no longer
writes the whole session, rebuilds the whole list or looks at every cell of the table: the file is written a moment
later (and on leaving, switching tabs, closing), the list is built when it is shown, and only changed rows are drawn.
What is decided and shown is the same. Fictional effort."""
import os, sys, tempfile, time, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp(); os.environ.setdefault("SK_DATA_DIR", os.path.join(tmp, "d"))
import app_gui as A, effort as E
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from skqt import design as D, acrselbar as SB, acrfast as AF, adaptive as AD
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


random.seed(11)
terms = set()
while len(terms) < 220:
    terms.add("".join(random.choice("BCDFGHJKLMNPQRSTVWXZ") for _ in range(random.choice((3, 4, 5)))))
terms = sorted(terms)
from docx import Document
d = Document()
for i in range(400):
    d.add_paragraph(f"The Osprey unit {i} uses the {terms[i % len(terms)]} to do its work for the program in this paragraph of text.")
path = os.path.join(tmp, "Osprey Big.docx"); d.save(path)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(ED)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Osprey"); w.go("acronyms"); app.processEvents()
pg = w.acronym_page
t0 = time.time(); pg.scan([path])
while pg.worker is not None and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
s, op = pg.session, pg.onpage
sess = s.ws.p("session.json")
check("the scan found the terms and wrote the session at once (it saves from its own thread)", len(s.results) > 150 and os.path.isfile(sess) and not getattr(s, "unsaved", False), len(s.results))
pg.tabs.setCurrentIndex(0); app.processEvents(); op.fill(); app.processEvents()


def table_now():
    return [[pg.table.item(r, c).text() for c in range(pg.table.columnCount())] for r in range(pg.table.rowCount())]


# ---- on the page: a decision
here = [x["term"] for x in op.items if x.get("term")][:1]
m0 = os.path.getmtime(sess); built = []
orig = pg.table.setItem
pg.table.setItem = lambda *a: (built.append(1), orig(*a))
SB.not_term(op, here, everywhere=True); app.processEvents()
check("a decision on the page does not build the list behind it", built == [] and pg.list_stale is True, len(built))
check("... and does not write the session file there and then", os.path.getmtime(sess) == m0 and s.unsaved is True)
check("... the decision itself is made, and the count on the page follows", (s.results[here[0]].get("excluded") or "Not a term" in str(s.results[here[0]].get("status")))
      and "finds left to decide" in op.progress_lab.text())
t0 = time.time()
while (getattr(s, "unsaved", False) or (getattr(pg, "_saver", None) is not None and pg._saver.isRunning())) and time.time() - t0 < 10:
    app.processEvents(); time.sleep(0.05)
app.processEvents()
on_disk = json.load(open(sess, encoding="utf-8"))["results"][here[0]]
check("a moment after the last decision it is written", not s.unsaved and os.path.getmtime(sess) > m0 and (on_disk.get("excluded") or "Not a term" in str(on_disk.get("status"))), time.time() - t0)
# several decisions in a row: one write
here2 = [t for t in s.results if t != here[0]][:4]
m1 = os.path.getmtime(sess); writes = []
real = s.save_now
s.save_now = lambda: (writes.append(1), real())[1]
for t in here2:
    s.set_status([t], "Not a term") if s.effort is not None else s.exclude([t], True)
    op.decided(); app.processEvents()
check("four decisions in a row have written nothing yet", writes == [] and s.unsaved)
pg.tabs.setCurrentIndex(1); app.processEvents()
check("opening The list writes what was waiting, once", writes == [1] and not s.unsaved)
check("... and builds the list that was left unbuilt", pg.list_stale is False and pg.table.rowCount() == len(pg.terms) and all(x not in pg.terms or pg.table.item(pg.terms.index(x), 0).text().startswith(x) for x in here2))
pg.table.setItem = orig
# ---- in the list: only what changed is drawn, and the result is what a full build gives
before = table_now()
victim = pg.terms[5]; built = []
pg.table.setItem = lambda *a: (built.append(a[:2]), orig(*a))
s.set_status([victim], "Not a term") if s.effort is not None else s.exclude([victim], True)
pg.fill(); app.processEvents()
pg.table.setItem = orig
fast = table_now()
pg._row_terms = None; pg._row_sigs = None; pg.__dict__.pop("_found", None)
pg.fill(); app.processEvents()
full = table_now()
check("a decision in the list draws only the rows that changed", 0 <= len(built) <= 2 * pg.table.columnCount(), len(built))
check("... and the list reads exactly as a full build of it does", fast == full and fast != before and len(full) == len(pg.terms))
check("the row count follows the filter", pg.table.rowCount() == len(pg.terms))
# leaving the page writes
s.set_status([pg.terms[0]], "Not a term") if s.effort is not None else s.exclude([pg.terms[0]], True)
check("a decision is waiting", s.unsaved)
w.go("home"); app.processEvents()
check("leaving the page writes what was waiting", not s.unsaved)
s.later = None; s.unsaved = False; s.save()
check("a session with no page saves at once, as before", not s.unsaved)

check("4.30.4: the write is on the window's thread unless THREADED is turned on", AF.THREADED is False and getattr(pg, "_saver", None) is None)
AF.THREADED = True                                      # the other-thread path stays tested for when it is turned back on
# ---- adding to the effort list: nothing is written per decision; one write, off the window's thread, a moment later
w.go("acronyms"); app.processEvents(); pg.tabs.setCurrentIndex(1); app.processEvents()
AF.watch(pg)
L = s.effort
lm0 = os.path.getmtime(L.path); list_writes = []
real_l = s._save_list_now
s._save_list_now = lambda *a, **k: (list_writes.append(1), real_l(*a, **k))[1]
todo = [t for t in s.results if t not in L.rows and not s.results[t].get("file_error")][:60]
t0 = time.time()
s.add(todo[:1], "A made-up definition"); pg.fill(); app.processEvents()
s.add(todo[1:], ""); pg.fill(); app.processEvents()
check("adding one term, then 59 at once, writes no workbook while you decide", list_writes == [] and os.path.getmtime(L.path) == lm0 and s.list_unsaved and L.pending, time.time() - t0)
check("... they are in the effort list at once", all(t in L.rows for t in todo) and L.rows[todo[0]].get("Definition") == "A made-up definition")
t0 = time.time(); seen_saving = False
while (s.list_unsaved or s.unsaved or (getattr(pg, "_saver", None) is not None and pg._saver.isRunning())) and time.time() - t0 < 20:
    app.processEvents(); time.sleep(0.03)
    seen_saving = seen_saving or pg.progress.text().startswith("Saving your decisions")
app.processEvents()
check("a moment later both are written with no step to take, and the page says so", os.path.getmtime(L.path) > lm0 and not s.list_unsaved and not L.pending
      and pg.progress.text().startswith("Decisions saved"), pg.progress.text())
check("... it said Saving your decisions while it wrote, on another thread (no write on the window's)", seen_saving and list_writes == [])
check("4.30.4: what follows the write runs on the window's thread, never the writing one (the 4.30.3 crash)", AF.DONE_ON is True, AF.DONE_ON)
# typing in the search box: one fill after the last key; rows go without a card drawn for each
fills, cards = [], []
real_fill, real_card = pg.fill, pg.show_detail
pg.fill = lambda: (fills.append(1), real_fill())[1]
pg.show_detail = lambda *a: (cards.append(1), real_card(*a))[1]
try:
    pg.table.itemSelectionChanged.disconnect()
except (RuntimeError, TypeError):
    pass
pg.table.itemSelectionChanged.connect(pg.show_detail)
for ch_ in "ZQXW":
    pg.f_search.setText(pg.f_search.text() + ch_); app.processEvents()
check("four keys typed: nothing is filled yet", fills == [])
t0 = time.time()
while not fills and time.time() - t0 < 5:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
check("a moment after the last key the list is filled once", fills == [1] and pg.table.rowCount() == len(pg.terms), fills)
check("... and the term's card was drawn at most twice, not once per row that left", len(cards) <= 2, len(cards))
pg.f_search.setText(""); t0 = time.time()
while len(fills) < 2 and time.time() - t0 < 5:
    app.processEvents(); time.sleep(0.02)
check("clearing the search brings every row back", pg.table.rowCount() == len(pg.terms) and len(pg.terms) > 50)
pg.fill, pg.show_detail = real_fill, real_card
import effort as E2
back = E2.EffortList(L.path, "Osprey"); back.load()
check("the workbook on disk holds every one of them", all(t in back.rows for t in todo) and back.rows[todo[0]].get("Definition") == "A made-up definition", len(back.rows))
on_disk = json.load(open(sess, encoding="utf-8"))["results"]
check("... and so does the session file", all(on_disk[t].get("effort") or on_disk[t].get("status") for t in todo[:5]))
# the workbook looks as it always did
s.set_status([todo[3]], "Not a term"); AF.flush(pg)
from openpyxl import load_workbook
wb = load_workbook(L.path); sh = wb[wb.sheetnames[0]]
by = {sh.cell(row=r, column=1).value: r for r in range(2, sh.max_row + 1)}
c_in, c_not = sh.cell(row=by[todo[2]], column=3), sh.cell(row=by[todo[3]], column=3)
check("every cell is wrapped and top-aligned; a Not a term row is grey and the others are not",
      c_in.alignment.wrap_text and c_in.alignment.vertical == "top" and c_not.alignment.wrap_text and c_not.fill.fgColor.rgb.endswith("EEEEEE")
      and not str(c_in.fill.fgColor.rgb).endswith("EEEEEE") and sh.max_row == len(back.order) + 1, (c_not.fill.fgColor.rgb, c_in.fill.fgColor.rgb))
check("leaving wrote the last decision at once", not s.list_unsaved and (lambda b: (b.load(), b.rows[todo[3]].get("Status") == "Not a term")[1])(E2.EffortList(L.path, "Osprey")))
s._save_list_now = real_l
AF.THREADED = False

# ---- 4.30.4: a term clicked on the page beside the list is the one decided; a click in the list goes back
from skqt import acrpick as PK, acrlayout as AL2
pg.f_status.setCurrentIndex(0); pg.f_search.setText(""); pg.fill(); app.processEvents()
loc0 = next(l for t in pg.terms for l in (s.results[t].get("locations") or []) if sum(1 for u in pg.terms if l in (s.results[u].get("locations") or [])) >= 2)
here_terms = [t for t, d_ in s.results.items() if loc0 in (d_.get("locations") or []) and t in pg.terms]
a_t, b_t = here_terms[0], here_terms[1]
pg.select(a_t); app.processEvents()
check("the list's term is on the card", pg.card.title.text() == a_t and pg.current() == a_t and pg.where_view is not None)
check("a reading that holds another of the scan's terms at this place names it; one that holds none names nothing",
      PK.term_in(s, f"with the {b_t} in it", loc0, but=a_t) == b_t and PK.term_in(s, "with the thing in it", loc0, but=a_t) is None
      and PK.term_in(s, f"x{b_t}y", loc0, but=a_t) is None and PK.term_in(s, f"the {b_t} here", "Somewhere else (p.9)", but=a_t) is None)
c_t = here_terms[2]
line2 = f"{b_t} sits at the start and at the far end sits {c_t}"
check("a reading with two terms gives the one nearest the click", PK.term_in(s, line2, loc0, but=a_t, at=0.02) == b_t and PK.term_in(s, line2, loc0, but=a_t, at=0.98) == c_t)
rows_before = list(pg.terms)
pg.where_view.on_pick(f"Here is the {b_t} and more", loc0); app.processEvents()
check("a click on that reading puts the clicked term on the card and selects it in the list (4.30.7: one focus)",
      pg.card.title.text() == b_t and pg.selected_terms() == [b_t] and pg.terms == rows_before and getattr(pg, "pinned", None) is None)
check("... the page stays on the place it was clicked at", pg.where_view is not None and pg.where_view.locs[pg.where_view.k] == loc0)
check("... and the keys act on it", pg.current() == b_t)
in_t = a_t
out_t = next(t for t in here_terms if t != in_t and in_t not in t)
AF.TYPE_AFTER = 0
pg.f_search.setText(in_t); app.processEvents()             # the list as filtered leaves out_t out
pg.select(in_t); app.processEvents()
pg.where_view.on_pick(f"and here {out_t} sits", loc0); app.processEvents()
check("a clicked term the filter leaves out goes on the card alone; the list keeps its rows, with none selected",
      pg.card.title.text() == out_t and pg.pinned == out_t and pg.selected_terms() == [] and out_t not in pg.terms and pg.current() == out_t)
pg.select(in_t); app.processEvents()
check("a click on a row of the list goes back to the list's term", pg.card.title.text() == in_t and pg.pinned is None and pg.current() == in_t)
pg.f_search.setText(""); app.processEvents(); AF.TYPE_AFTER = 250
pg.select(a_t); app.processEvents()
pg.where_view.on_pick("no term in these words", loc0); app.processEvents()
check("a click on a reading with no term in it changes nothing", pg.card.title.text() == a_t and pg.pinned is None)

# ---- the table's hover text looks only at what changed
t = QTableWidget(300, 6); t.show(); app.processEvents()
looked = []
real_item = t.item
t.item = lambda r, c: (looked.append(1), real_item(r, c))[1]
AD._hover_text(t)
looked.clear()
for r in range(300):
    for c in range(6):
        t.setItem(r, c, QTableWidgetItem("x" * 40 if c == 0 else "short"))
check("filling 1,800 cells looks at a few thousand cells, not millions", len(looked) < 3 * 1800 + 100, len(looked))
check("... and a long cell still shows its full text on hover; a short one has none", real_item(7, 0).toolTip() == "x" * 40 and real_item(7, 1).toolTip() == "")
n = sum(checks)
print(f"QT ACRFAST 4303 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
w.close()
sys.exit(0 if n == len(checks) else 1)
