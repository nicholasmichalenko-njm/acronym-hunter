"""4.27.2 offscreen: the top bar and Quick tools (Nicholas's recording 2026-11-12 05:25 to 07:30; answer 4). The top bar's
button is Quick note and opens the note; Undo is off the bar: Ctrl+Z, a line at the foot that says what it would put
back, and History for the steps a page can still undo. Quick tools is at the bottom of the menu, out of the effort
switcher. Unfiled is a list under Quick tools, not an effort to switch to. Fictional (an Osprey Section L)."""
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
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report.",
         "The Government will evaluate the realism of the schedule.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=9)
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
from PySide6.QtWidgets import QMenu
from skqt import frame as FR, undoline as UL
from skqt.mainwin import RAIL, TITLES
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731

# ---- the top bar
check("the top bar's button is Quick note and opens the note (no menu under it)", w.note_btn.text() == "Quick note" and w.note_btn.menu() is None
      and w.note_btn.isVisibleTo(w))
check("Issue or idea is off the top bar (it is in Help, Ctrl+Shift+I)", not w.issue_btn.isVisibleTo(w))
check("Undo is off the top bar", not w.undo_btn.isVisibleTo(w))
check("... with nothing to undo the foot says nothing", not w.undo_line.isVisibleTo(w))
a = by("Integrated Master Schedule")
pg.select(a["id"]); app.processEvents()
pg.type_chips["requirement"].click(); app.processEvents()
w.refresh_undo()
check("after a change the foot says what Undo would put back", w.undo_line.isVisibleTo(w) and "Undo: " in w.undo_line.text()
      and "Requirement" in w.undo_line.text(), w.undo_line.text())
check("... one step: no History yet", "History" not in w.undo_line.text() and len(UL.steps(w)) == 1, UL.steps(w))
b = by("Text shall be no smaller")
pg.select(b["id"]); app.processEvents()
pg.type_chips["rule"].click(); app.processEvents()
w.refresh_undo()
st = UL.steps(w)
check("a second change: History is offered, newest first", "History" in w.undo_line.text() and len(st) == 2 and "Rule" in st[0] and "Requirement" in st[1], st)
check("History, pick the second line: both are undone", UL.history(w, pick=2) == 2 and not by("Text shall be no smaller").get("piece")
      and not by("Integrated Master Schedule").get("piece"))
check("... and the foot is quiet again", not w.undo_line.isVisibleTo(w) and UL.steps(w) == [])
pg.select(by("Text shall be no smaller")["id"]); app.processEvents()
pg.type_chips["rule"].click(); app.processEvents()
w.undo_here(); app.processEvents()
check("Ctrl+Z still undoes the last change", not by("Text shall be no smaller").get("piece"))

# ---- Quick tools
keys = [k for _g, items in RAIL for k, _t in items]
check("Quick tools is in the menu, at the bottom, before Team and Settings", keys[-3:] == ["tools", "team", "settings"]
      and w.step_btns["tools"].text() == "Quick tools" and TITLES["tools"][0] == "Quick tools", keys)
acts = [x.text() for x in FR.effort_menu(w).actions() if x.text()]
check("... and out of the effort switcher, which holds no Unfiled to switch to either", "Quick tools" not in acts and not any("Unfiled" in x for x in acts), acts)
w.rail_go("tools"); app.processEvents()
tl = w.pages["tools"]
check("the entry opens Quick tools and stays lit", w.stack.currentWidget() is tl and w.step_btns["tools"].isChecked() and w.page_title.text() == "Quick tools")
rows = [tl.uf_list.item(i).text() for i in range(tl.uf_list.count())]
check("Unfiled is a list on Quick tools; with nothing unfiled it says so and its buttons wait", tl.uf_card.isVisibleTo(tl)
      and rows == ["Nothing unfiled. A tool used with no effort open keeps its work here."] and not tl.uf_make.isEnabled(), rows)
effs = [tl.eff.item(i).text() for i in range(tl.eff.count())]
check("Your efforts lists efforts only", any(x.startswith("Osprey") for x in effs) and not any("Unfiled" in x for x in effs), effs)
w.go("efforts"); app.processEvents()
check("All Efforts has no Unfiled card", not w.efforts_page.uf_card.isVisibleTo(w) and not w.efforts_page.start_btn.isVisibleTo(w))
w.close()
print(f"QT TOPBAR 4272 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
