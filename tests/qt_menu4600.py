"""4.60.0 offscreen (Nicholas 2026-11-23, Layout 1): the menu is Quick tools, the effort's pages with no numbers,
Standards and Formatting, Settings; the same with and without an effort open. With nothing open an effort's page is one
sentence and one button. Calendar and Tasks are tabs of Overview; Matrix and Outline are apart; Deliverables holds
Redlining; Team defaults is on Settings. Quick tools pins Redline a document. A file the watch adds by itself is never
a version of another document because it is like it, and a redline copy Prepare made is not added. Fictional (Kestrel)."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, workspace as W, watch as WA, redlinecopy as RC
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, noeffort as NE, toolshome as TH, navrail as NR
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


MENU = ["Quick tools", "Overview", "Documents", "Graphics", "Deliverables", "Redlining", "Shred", "Matrix", "Outline", "Setup", "Drafts", "Submission Check",
        "Global Standards", "Rules", "Team References", "Templates", "Page Layout", "Styles", "Quick Parts", "Check a Draft", "Effort Activity", "Effort Backup", "Settings"]   # 4.61.0
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
src = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
P = os.path.join(CD, "Kestrel_Section_L.pdf"); shutil.copy2(src, P)
lib0 = DV.Library(ws.p("documents")).load()
sents = DI.read(P)
lib0.add(P, sents, doc_name="Section L", role="matrix", initial="L", dtype="Section L")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()


def menu():
    return [b.text().replace("&&", "&") for b in w.step_btns.values()]


def hidden():
    return [k for k, b in w.step_btns.items() if b.isHidden()]


check("the menu, in order", menu() == MENU, menu())
check("nothing is hidden with no effort open", w.ws is None and hidden() == [], hidden())
check("no entry carries a number", all(b.n is None and not b.circle.isVisibleTo(w) for b in w.step_btns.values()))
check("no heading says the effort's path", not any("PATH" in (h.text() if h is not None else "") for h in w.group_heads.values()))
check("Standards and Formatting is the one heading", [h.text() for h in w.group_heads.values() if h is not None] == ["STANDARDS AND FORMATTING"])
check("no Team, Calendar or Tasks entry", not {"team", "calendar", "tasks"} & set(w.step_btns))

w.go("assign"); app.processEvents()
pg = w.noeffort_page
check("Shred with no effort open: one sentence and one button, no tabs", w.stack.currentWidget() is pg and pg.say.text() == NE.SAY["assign"]
      and pg.btn.text() == "Open or create an effort" and w._tab_keys == [] and not w.stepper.isVisibleTo(w), w._tab_keys)
check("... the entry stays lit and the page is named", w.step_btns["assign"].isChecked() and w.page_title.text() == "Shred", w.page_title.text())
for k in NE.SAY:
    w.go(k); app.processEvents()
check("every effort page but Overview says so with nothing open", all(NE.wanted(w, k) for k in NE.SAY) and not NE.wanted(w, "home")
      and set(NE.SAY) == ({k for k, _t in MW.RAIL[1][1]} - {"home"}) | {"activity"})
pg.btn.click(); app.processEvents()
check("the button goes to the efforts", w.stack.currentWidget() is w.efforts_page)
w.go("globalstd"); app.processEvents()
check("a standards page needs no effort", w.stack.currentWidget() is w.globalstd_page)

w.open_effort("Kestrel"); app.processEvents()
check("with an effort open: the same menu, nothing hidden", menu() == MENU and hidden() == [], hidden())
w.go("assign"); app.processEvents()
check("Shred opens with an effort", w.stack.currentWidget() is not w.noeffort_page)
w.rail_go("home"); app.processEvents()
check("Calendar and Tasks are tabs of Overview", w._tab_keys == ["overview", "calendar", "tasks", "meetings"], w._tab_keys)
w.go("calendar"); app.processEvents()
check("... and Calendar lights Overview", w.step_btns["home"].isChecked() and w.page_title.text() == "Overview", w.page_title.text())
w.go("matrix"); app.processEvents()
check("Matrix: its own tabs, no Outline", w._tab_keys == ["assignto", "linkcheck", "matrix"] and w.page_title.text() == "Matrix", w._tab_keys)   # 4.66.0: Assign first, Place under its More
w.go("outline"); app.processEvents()
check("Outline is a page of its own", w.step_btns["outline"].isChecked() and w._tab_keys == [] and w.page_title.text() == "Outline", (w._tab_keys, w.page_title.text()))
w.go("deliverables"); app.processEvents()
check("Deliverables is the list alone (4.61.0)", w.step_btns["deliverables"].isChecked() and w._tab_keys == [], w._tab_keys)
w.go("redline"); app.processEvents()
check("Redlining is its own entry (4.61.0)", w.step_btns["redline"].isChecked() and w.stack.currentWidget() is w.redline_page and w._tab_keys == [], w._tab_keys)
for d in DV.Library(ws.p("documents")).load().all:
    DV.Library(ws.p("documents")).load().set_returns(d["id"], ["redline"])
w.go("redline"); app.processEvents()
check("a document marked: Check and Exceptions show", w._tab_keys == ["redline", "rcheck", "exceptions"], w._tab_keys)
w.go("settings"); app.processEvents()
sp = w.settings_page
check("Team defaults is on Settings", "team_card" in dict(sp.SECTIONS)["Team data and training"] and sp.MOVED == ())

# Quick tools
check("Quick tools pins Redline a document for every role", all("redline" in p for p in TH.ROLE_PINS.values())
      and TH.TOOLS["redline"][0] == "Make a Word file from a PDF" and TH.TOOLS["redline"][2] == "file")
pf = os.path.join(cfg, TH.PINS_FILE)
json.dump({"pins": ["acrfinder"]}, open(pf, "w"))
check("pins saved before 4.60.0 gain it once", TH.load_pins(cfg) == ["acrfinder", "redline", "markups"], TH.load_pins(cfg))
TH.save_pins(cfg, ["acrfinder"])
check("... and unpinning it stays", TH.load_pins(cfg) == ["acrfinder"], TH.load_pins(cfg))
made = []
w.redline_page.prepare = lambda path=None, **k: made.append(path) or path
out = w.tools_page.open("redline", paths=[P])
check("Redline a document hands the file to Prepare, with no question about an effort", made == [P], (made, out))

# the watch: no version by likeness
lib = DV.Library(ws.p("documents")).load()
other = os.path.join(ED, "Kestrel Section L notes.docx")
open(other, "wb").write(b"not the same bytes")
like = lambda p: sents + [{"x": "One more line the customer added."}]          # noqa: E731
e1 = DI.plan(lib, [other], like)[0]
e2 = DI.plan(lib, [other], like, by_likeness=False)[0]
check("Add files still offers a file like a document as its new version", e1["choice"] == "version" and e1["doc"], e1["choice"])
check("a file the watch adds by itself is a document of its own", e2["choice"] == "new" and not e2["doc"], (e2["choice"], e2["doc"]))
copy = os.path.join(ED, RC.copy_name(P))
open(copy, "wb").write(b"a prepared copy")
check("a file merely named like a redline copy is still a file that came in", not WA._made_here(copy))
json.dump({"source": "Kestrel_Section_L.pdf"}, open(copy + RC.SIDE, "w"))
check("a redline copy Prepare made is not one", WA._made_here(copy))

print(f"MENU 4600 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
