"""3.85.0 offscreen: Review and place. A line joins the selected sentence to its home in our structure (dotted while
suggested, solid once placed) and the structure scrolls to it; the home is suggested with the reason (a section with
the heading's title); Enter accepts what it is and where it goes; after a placement the offer sends the rest of the
customer heading (Map and place N, Map only, Just this one); Map this heading to the target on the sentence's menu;
what is left (not decided, not placed, headings answered) selects them; Lines for headings; the cross-reference table.
Fictional content (the Kestrel set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, homesuggest as HS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management Approach\n1.3 Past Performance")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf",)]
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("the matrix is read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
ap = w.assign_page
w.go("place"); app.processEvents()                 # 4.3.0: placing is Matrix & Outline > Place
wait(lambda: bool(ap.view.boxes), 30)
M = w.review.M
pl = ap.placer
check("a gutter sits between the page and our structure", pl.gutter.isVisibleTo(w) and pl.gutter.width() == 44)
tech = next(it for it in M.items if it.get("section") == "L.3.1" and it.get("type") != "Heading" and "technical approach" in it["text"].lower())
ap.select(tech["id"]); app.processEvents()
check("the home is suggested with the reason", "1.1 Technical Approach" in pl.home_lbl.text() and "matches" in pl.home_lbl.text(), pl.home_lbl.text())
got = pl.gutter.compute()
check("one dotted line from the sentence to its suggested home", len(got) == 1 and got[0][4] == "suggested", got)
ap.sg_on = True; ap._accepting = True
try:
    n = ap.place_reqs([tech])
finally:
    ap._accepting = False
ap.after("placed")
check("Enter takes the suggested home", n == 1 and tech["map"] == "1.1 Technical Approach")
ap.select(tech["id"]); app.processEvents()
got = pl.gutter.compute()
check("placed: the line is solid", got and got[0][4] == "placed", got)
check("the offer: the rest of L.3.1 to the same section", pl.offer_row.isVisibleTo(w) and "L.3.1" in pl.offer_lbl.text()
      and pl.b_place.text().startswith("Map and place"), pl.offer_lbl.text())
rest = list(pl.off["rest"])
check("Map and place: the heading is mapped and the rest placed", pl.take("place") == len(rest) > 0
      and all(ap.R.item(i)["map"] == "1.1 Technical Approach" for i in rest)
      and HS._S(M)["rfp_map"]["L.3.1"] == "1.1 Technical Approach")
check("the offer goes once taken", not pl.offer_row.isVisibleTo(w))
mg = next(it for it in M.items if it.get("section", "").startswith("L.3.2") and it.get("type") != "Heading")
ap.set_target("1.2 Management Approach")
ap.select(mg["id"]); app.processEvents()
menu = [a.text() for a in ap.sentence_menu(mg["id"]).actions()]
check("the sentence's menu maps its heading to the target", any(t.startswith("Map L.3.2") and t.endswith("1.2 Management Approach") for t in menu), menu)
check("Map to: the heading is mapped", pl.map_selected() == 1 and HS.home(M, mg)["label"] == "1.2 Management Approach"
      and HS.home(M, mg)["kind"] == "map")
pl.show_left()
check("what is left: not decided, not placed, headings answered", "not decided" in pl.left_lbl.text() and "not placed" in pl.left_lbl.text()
      and "customer headings answered" in pl.left_lbl.text(), pl.left_lbl.text())
check("a link selects them", pl.select_left("undecided") > 0)
more = [a.text() for a in ap.fill_more_menu().actions()]
check("More: Lines for headings and Export cross-reference table...", "Lines for headings" in more and "Export cross-reference table..." in more)
pl.toggle_heads(True)
out = pl.export_crossref(os.path.join(tmp, "xref.xlsx"))
from openpyxl import load_workbook
rows = [tuple(c.value for c in r) for r in load_workbook(out).active.iter_rows()]
check("the cross-reference table names where each heading is answered", rows[0] == ("Customer heading", "Title", "Where we answer it")
      and any(r[0] == "L.3.1" and "1.1 Technical Approach" in r[2] for r in rows), rows[:4])

print(f"QT PLACE 385 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
