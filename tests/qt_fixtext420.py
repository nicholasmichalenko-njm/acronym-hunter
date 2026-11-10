"""4.2.0 offscreen: Fix text, a mode inside Shred (claude/stationkeeper-fix-text-decisions-2026-11-10.md, decisions 1
and 8). Documents has no Text check tab; go("verify") opens Shred in Fix text; F2 turns it on and off; pieces on two
pages combine into one (J); a banner is set aside, every line like it too, and Undo puts them back; a heading; Page
checked counts pages (kept where Text check kept them) and never holds the shred up; the page-by-page check stays under
More. Fictional (an Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C
import effort as E, workspace as W, pdfmini
import shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
P1L = ["L.2 PROPOSAL SUBMISSION",
       "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
       "Volume I shall not exceed 30 pages.",
       "Distribution D. Osprey proprietary draft 7 of 9.",
       "The Offeror shall describe its approach to the operation of the ground"]
P2L = ["station during the transition period.",
       "Distribution D. Osprey proprietary draft 8 of 9.",
       "The Government will evaluate the realism of the schedule."]
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report.",
         "The Government will evaluate the realism of the schedule.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [P1L, P2L], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
OUT = os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx")
w.read_page.read([PDF], OUT)
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
from skqt.mainwin import TABS
from skqt import fixtext as FX
import verifystate as VS
M = w.review.M
pg = w.assign_page
check("Documents has no Text check tab", "verify" not in [k for k, _t in TABS["library"]], TABS["library"])
w.go("verify"); app.processEvents()
check("go('verify') opens Shred in Fix text", w.stack.currentWidget() is pg and pg.fix_on and pg.fix_strip.isVisibleTo(w))
pg.open_file("Section_L.pdf"); app.processEvents()
check("... the strip counts the pages checked", "0 of 2 pages checked" in pg.fix_lbl.text(), pg.fix_lbl.text())
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
check("a sentence the page break split is one piece already (the reader joins it)",
      "transition period" in by("operation of the ground")["text"])
a, b = by("30 pages"), by("realism")
pg.select(a["id"]); app.processEvents()
pg.view.boxes[b["id"]][0].setSelected(True) if isinstance(pg.view.boxes[b["id"]], list) else pg.view.boxes[b["id"]].setSelected(True)
app.processEvents()
check("pieces on two pages selected together", sorted(x["id"] for x in pg.selected()) == sorted([a["id"], b["id"]]), [x["id"] for x in pg.selected()])
pg.fix_tools["Combine"].click(); app.processEvents()
one = [it for it in M.items if "30 pages" in it["text"] and "realism" in it["text"]]
check("Combine (J): one piece from pieces on two pages", len(one) == 1, [it["text"] for it in M.items if "30 pages" in it["text"] or "realism" in it["text"]])
ban = by("draft 7 of 9")
pg.select(ban["id"]); app.processEvents()
FX.set_aside(pg, every=True); app.processEvents()
bans = [it for it in M.items if "proprietary draft" in it["text"]]
check("Set aside, every line like it: out of the shred, still there", len(bans) == 2 and all(it["decision"] == "Drop"
      and FX.ASIDE_NOTE in it.get("notes", "") for it in bans), [(it["decision"], it.get("notes")) for it in bans])
pg.do_undo(); app.processEvents()
check("... Undo puts them back", all(not it.get("decision") for it in M.items if "proprietary draft" in it["text"]))
FX.page_checked(pg, 1); app.processEvents()
check("Page checked: counted, kept where Text check keeps it", FX.checked(pg) == (1, 2) and "1 of 2 pages checked" in pg.fix_lbl.text()
      and "1" in VS.Store(w.ws.root).doc("Section_L.pdf")["verified"])
FX.toggle(pg); app.processEvents()
check("F2 turns it off; the shred goes on", not pg.fix_on and not pg.fix_strip.isVisibleTo(w))
FX.page_by_page(pg); app.processEvents()
check("the page-by-page check stays under More", w.stack.currentWidget() is w.verify_page)
w.close()
print(f"QT FIXTEXT 420 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
