"""4.6.0 offscreen: Documents and Changes, as designed (claude/stationkeeper-documents-changes-plan-4.6.md, steps 1 and 2).
Documents: Customer and Ours tabs, Find / More / Add documents..., the columns with the progress chips, the panel with
the versions once. Changes: a card per change with No impact, Re-shred and Ask a question on it, Next change, Open in
Word as tracked changes, the footer to the re-shred queue, the page view and Any two files under More. Fictional
content (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, pdfmini, changereview as CR, homesuggest as HS, menufocus as MF
OP.available = lambda: False
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import amendflags as AF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CUST = os.path.join(EDIR, "Customer documents"); os.makedirs(CUST)
IN = os.path.join(tmp, "incoming"); os.makedirs(IN)
BASE = ["L.3 PROPOSAL VOLUMES",
        "Volume I Technical shall not exceed 50 pages.",
        "L.4 RISK MANAGEMENT",
        "The Offeror shall identify the five highest program risks.",
        "The Offeror shall provide a risk burn-down chart for each risk.",
        "The Offeror shall name an owner for each risk.",
        "L.5 TRANSITION",
        "The Offeror shall describe its transition approach in ninety days."]
AMD = ["L.3 PROPOSAL VOLUMES",
       "Volume I Technical shall not exceed 40 pages.",
       "L.4 RISK MANAGEMENT",
       "The Offeror shall identify the ten highest program risks.",
       "The offeror shall name an owner for each risk.",
       "The Offeror shall describe a mitigation plan for each high risk.",
       "L.5 TRANSITION",
       "The Offeror shall describe its transition approach in ninety days."]
P1 = os.path.join(IN, "Kestrel_Section_L.pdf"); pdfmini.write(P1, [BASE], size=9)
P2 = os.path.join(IN, "Kestrel_Section_L_Amd1.pdf"); pdfmini.write(P2, [AMD], size=9)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CUST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk Management\n1.3 Transition")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.go("docs"); app.processEvents()
w.docs_page.add([P1], choices=[{}])
C1 = os.path.join(CUST, "Kestrel_Section_L.pdf")
w.read_page.read([C1], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"), identities="suggested")
check("read", wait(lambda: w.review is not None))
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])                                           # noqa: E731
pages50, five, burn, owner = by("50 pages"), by("five highest"), by("burn-down"), by("owner for each")
w.review.req([pages50], "1.1 Technical Approach")
w.review.req([five, burn, owner], "1.2 Risk Management")
HS.map_heading(M, "L.4", "1.2 Risk Management")
w.changed(); w.save_now()
# the amendment comes in: decision 6 at once
w.go("docs"); app.processEvents()
d, v = w.docs_page.add([P2], choices=[{}])[0]
fl = AF.flags(w)
check("adding the amendment flags the placed sentences it touches, before Compare is opened",
      fl.get(pages50["id"], [{}])[0].get("text") == "Changed in Amendment 1" and fl.get(burn["id"], [{}])[0].get("text") == "Removed in Amendment 1", fl)
check("... the sentences keep their place", pages50["map"] == "1.1 Technical Approach" and burn["map"] == "1.2 Risk Management")
import reshred as RS, custqa as Q, effortrec as RR
from skqt import changecards as CC, docfocus as DF
# Documents: Customer and Ours
w.rail_go("library"); app.processEvents()
lp, op = w.library_page, w.ours_page
check("Documents' tabs: Customer, Ours, Changes, Data calls", [t for _k, t in __import__("skqt.mainwin", fromlist=["x"]).TABS["library"]]
      == ["Customer", "Ours", "Changes", "Data calls"])
check("Customer's header: Find, More, Add documents... (the main button)", lp.bar.main.text() == "Add documents..."
      and not lp.b_folder.isVisibleTo(w) and "Add a folder..." in lp.bar.labels() and "Watched folders..." in lp.bar.labels()
      and not lp.tree.isVisibleTo(w), lp.bar.labels())
__import__("skqt.navrail", fromlist=["x"]).refresh_steps(w, force=True); w.show_tabs("library")
ti = w._tab_keys.index("compare")
check("Changes' tab says how many changes are left to decide", w.page_tabs.tabText(ti).startswith("Changes (")
      and w.page_tabs.tabText(ti).endswith(")"), w.page_tabs.tabText(ti))
hdr = [lp.table.horizontalHeaderItem(c).text() for c in range(lp.table.columnCount())]
check("the columns: Document, Type, Governing version, Text, Shred, Terms", hdr == DF.COLUMNS, hdr)
names = {lp.table.item(r, 0).text(): r for r in range(lp.table.rowCount())}
row = next(r for n, r in names.items() if "versions" in n)
check("the document says how many versions it has", lp.table.item(row, 0).text().endswith("2 versions"), list(names))
check("its governing version is the amendment", lp.table.item(row, 2).text().startswith("Amendment 1"), lp.table.item(row, 2).text())
check("its Shred chip says where its shred stands", lp.table.item(row, 4).text() != "", lp.table.item(row, 4).text())
lp.table.selectRow(row); lp.show_doc(); app.processEvents()
check("the panel: what has been done, no Versions row, the versions listed once, one button",
      "Versions" not in [x[0] for x in lp.status_now] and lp.d_versions.count() == 2 and not lp.b_more.isVisibleTo(w)
      and not lp.b_taken2.isVisibleTo(w), [x[0] for x in lp.status_now])
w.go("ours"); op.refresh(); app.processEvents()
check("Ours holds none of the customer's documents (the empty state shows one way in)", op.table.rowCount() == 0
      and op.empty.isVisibleTo(w) and w._tab_keys[:3] == ["library", "ours", "compare"], op.table.rowCount())
# Rules & Dates: three groups, Used by, Add a rule... the main button
w.go("requirements"); rp = w.requirements_page; rp.refresh(); app.processEvents()
tops = [rp.tree.topLevelItem(i).text(0) for i in range(rp.tree.topLevelItemCount())]
check("Rules & Dates: Structure and page limits, Format, Submission and dates", [t.split(" (")[0] for t in tops[:3]]
      == ["Structure and page limits", "Format", "Submission and dates"], tops)
kids = [rp.tree.topLevelItem(i).child(j) for i in range(3) for j in range(rp.tree.topLevelItem(i).childCount())]
check("... each rule says what uses it", kids and all(k.text(4) for k in kids) and rp.tree.headerItem().text(4) == "Used by",
      [(k.text(0), k.text(4)) for k in kids][:4])
check("... and Add a rule... is the main button", rp.cbar.main.text() == "Add a rule..." and "Show the ones set aside" in rp.cbar.labels())
# Changes: a card per change
w.go("compare"); app.processEvents()
cp = w.compare_page
rows = cp.show(d["id"], None, v["id"]); app.processEvents()
ch = [i for i, r in enumerate(rows) if r["kind"] != "same"]
check("Changes shows a card per change, not the page view", cp.cards.isVisibleTo(w) and not cp.split.isVisibleTo(w)
      and len(cp.cards.boxes) == len(cp.shown) and len(ch) >= 3, (len(cp.cards.boxes), len(ch)))
check("the main button is Next change; Open in Word as tracked changes beside it; Any two files under More",
      cp.bar.main.text() == "Next change" and "Open in Word as tracked changes" in cp.bar.labels() and "Any two files..." in cp.bar.labels()
      and "Prev change" not in [b.text() for b in cp.bar.visible_commands()], cp.bar.labels())
check("the new versions on the left, with how many are left", cp.cards.versions.count() == 1
      and "to decide" in cp.cards.versions.item(0).text(), cp.cards.versions.item(0).text() if cp.cards.versions.count() else "")
hit = next(i for i in ch if "40 pages" in rows[i]["new"])
card = cp.cards.boxes[hit]
btns = [b.text() for b in card.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)]
check("a card: the wording inline and No impact, Re-shred, Ask a question, More", btns[:4] == ["No impact", "Re-shred", "Ask a question", "More"], btns)
dec = cp.cards.decide(hit, "reshred"); app.processEvents()
check("Re-shred on the card: into Shred's queue, and the next change to decide is selected", dec and len(RS.Queue(w.ws.root).load().open_items()) == 1
      and cp.i != hit and not cp.decided(cp.i), cp.i)
check("... the decided card turns pale and offers Undo", cp.cards.boxes[hit].property("done") is True)
check("the footer says a passage waits in Shred, with the link", "1 passage(s) wait in Shred" in cp.cards.foot.text() and cp.cards.foot.isVisibleTo(w),
      cp.cards.foot.text())
n0 = len([i for i in cp.shown if not cp.decided(i)])
cp.bar.main.click(); app.processEvents()
check("Next change goes to a change still to decide", cp.i is not None and not cp.decided(cp.i))
cp.cards.decide(cp.i, "none"); app.processEvents()
check("No impact on the card decides it", len([i for i in cp.shown if not cp.decided(i)]) == n0 - 1)
did = cp.review.decisions(cp.pk, rows[hit]["key"])[0]["id"]
cp.select(hit); cp.cards.undo(did); app.processEvents()
check("Undo on the card takes the decision back (and the passage off the queue)", not cp.decided(hit)
      and not RS.Queue(w.ws.root).load().open_items())
CC.set_page_view(cp, True); app.processEvents()
check("More > See the changes on the page shows the page view", cp.split.isVisibleTo(w) and not cp.cards.isVisibleTo(w))
CC.set_page_view(cp, False); app.processEvents()
CC.any_two(cp); app.processEvents()
check("More > Any two files opens it, with the way back", w.compare_space.tabs.currentIndex() == 1 and w.compare_space.tabs.tabBar().isHidden())
w.compare_space.tabs.setCurrentIndex(0)
p = CC.open_in_word(cp)
check("Open in Word as tracked changes writes the copy beside the new version", p and os.path.isfile(p) and p.endswith(".docx"), p)
w.close()
print(f"QT CHANGES 460 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
