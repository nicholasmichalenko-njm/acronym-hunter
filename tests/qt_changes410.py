"""4.1.0 offscreen: Documents > Changes decides with three ways (claude/stationkeeper-shred-plan-4.1.md, step 7): No impact,
Re-shred (the passage joins Shred's queue with its old and new wording; the requirement built from it shows Changed by
the amendment until it is shredded again) and Ask a question (a question in the Q&A log citing both wordings); the
full list stays under More. Shred shows "N to re-shred"; each queued passage opens with its wording and Done takes it
off. Fictional content (Kestrel)."""
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
w.go("compare"); app.processEvents()
cp = w.compare_page
rows = cp.show(d["id"], None, v["id"])
ch = [i for i, r in enumerate(rows) if r["kind"] != "same"]
hit = next(i for i in ch if "40 pages" in rows[i]["new"])
cp.select(hit); app.processEvents()
bar = cp.decide_panel
check("three ways lead: No impact, Re-shred, Ask a question", [b.text() for b in bar.btns.values()] == ["No impact", "Re-shred", "Ask a question"],
      [b.text() for b in bar.btns.values()])
check("... the full list under More", [a.text() for a in bar.more_menu.actions()][:3] == ["Update our wording", "Add to a section", "Remove"])
dec = bar.decide("reshred")
q = RS.Queue(w.ws.root).load()
check("Re-shred: the passage joins Shred's queue with both wordings and the requirement built from it",
      dec and dec["kind"] == "reshred" and len(q.open_items()) == 1 and q.open_items()[0]["target"] == pages50["id"]
      and "50 pages" in q.open_items()[0]["old"] and "40 pages" in q.open_items()[0]["new"], q.items)
check("... the requirement says which version changed it", RS.flagged(w.ws.root) == {pages50["id"]: "Changed by Amendment 1"}, RS.flagged(w.ws.root))
from skqt import docstatus as DSx
check("Documents knows the document has a passage to re-shred", DSx._queued(w.library_page, d) == 1)
risk = next(i for i in ch if "ten highest" in rows[i].get("new", ""))
cp.select(risk); app.processEvents()
bar.decide("question")
qs = Q.items(RR.Record(w.ws.root))
check("Ask a question: a question in the Q&A log citing the new and the old wording", qs and "ten highest" in qs[-1]["quote"]
      and "five highest" in qs[-1]["quote"], qs[-1]["quote"] if qs else qs)
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.open_file("Kestrel_Section_L.pdf"); app.processEvents()
check("Shred shows 1 to re-shred", pg.reshred_btn.isVisibleTo(w) and pg.reshred_btn.text() == "1 to re-shred", pg.reshred_btn.text())
pg.reshred_btn.click(); app.processEvents()
check("... it opens the passage: its requirement selected, its old and new wording", pages50["id"] in [x["id"] for x in pg.selected()]
      and "Was:" in pg.note.text() and "40 pages" in pg.note.text() and "reshred-done" in pg.note.text(), pg.note.text())
pg.note.linkActivated.emit("reshred-done"); app.processEvents()
check("Done takes it off the queue and the flag off", not RS.Queue(w.ws.root).load().open_items() and not RS.flagged(w.ws.root)
      and not pg.reshred_btn.isVisibleTo(w))
w.go("compare"); app.processEvents()
cp.select(hit); app.processEvents()
d2 = bar.decide("reshred")
undone = bar.undo(d2["id"]) if d2 else False
check("undoing a Re-shred takes it off the queue", undone and not RS.Queue(w.ws.root).load().open_items())
w.close()
print(f"QT CHANGES 410 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
