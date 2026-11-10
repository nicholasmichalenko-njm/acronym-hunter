"""3.84.0 offscreen: Verify, Review's first tab. The page drawn as the PDF page with a box and a role for every block;
click, Shift+click and drag select, blank page clears; the bar opens beside the selection, never over it, with every
role in the menu; a key or a role button sets the role; moving to a page selects its first flag; Page verified waits on
the page's flags and moves on; the strip, Prev, Next, the page box, Next to look at; each document opens where it was
left; Menu roles... renames, hides and adds a role; a caption's link is confirmed or picked; one command bar with one
main button. Fictional content (the Kestrel set)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, docversions as DV, verifystate as VS, verifyroles as VR, pagesent as PS
from pdfmake import make_pdf
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.commandbar import MAX
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def spin(ms=0):
    t = time.time()
    while True:
        app.processEvents()
        if time.time() - t >= ms / 1000:
            break
        time.sleep(0.01)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("verify"); spin()
vp = w.verify_page
check("Text check (was Verify) is a tab of Documents (4.0.0)", w.stack.currentWidget() is vp and w.page_title.text() == "Documents")
check("no documents: one way in", vp.empty.isVisibleTo(w) and not vp.view.isVisibleTo(w))
SRC = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_walk")
lib = DV.Library(w.ws.p("documents")).load()
for f in ("SOW.pdf", "Section_L_print.pdf"):
    p = os.path.join(tmp, f); shutil.copy(os.path.join(SRC, f), p)
    lib.add(p, [], doc_name=f.rsplit(".", 1)[0])
cap = make_pdf(os.path.join(tmp, "Kestrel Staffing.pdf"), [["3 Staffing", "Table 1 Staffing by month", "Month Lead Analysts",
                                                            "The plan ramps to full staff in month three."]])
lib.add(cap, [], doc_name="Kestrel Staffing")
w.go("home"); w.go("verify"); spin(50)
check("documents: the page view, the strip and the bar", vp.view.isVisibleTo(w) and vp.strip.isVisibleTo(w) and not vp.empty.isVisibleTo(w))
check("one command bar: Page verified, next is the one main button", vp.bar.main.text() in ("Page verified, next",) or "to look at" in vp.bar.main.text()
      and len(vp.bar.commands) <= MAX)
check("Menu roles... is in More", vp.bar.action("Menu roles...") is not None and vp.bar.action("Reopen this page...") is not None)
docs = [a.text() for a in (vp.fill_docs() or vp.doc_menu.actions()) if a.text()]
check("the document menu: every document with its verified count", any(t.startswith("SOW.pdf") and "of 2 verified" in t for t in docs)
      and "All documents and work units" in docs, docs)
sow = next(p for _n, _l, p in vp.docs() if p.endswith("SOW.pdf"))
vp.open_doc(sow); spin()
check("the page drawn with a box for every block", len(vp.view.items) == len(vp.v) > 5)
unnum = next(b for b in vp.v if b["text"] == "STATEMENT OF WORK")
check("the first page's flag is first: an unsure heading", vp.b_ok.text().endswith("to look at") and not vp.b_ok.isEnabled())
vp.go(2); vp.go(1); spin()
check("moving to a page selects its first flag, and the bar opens on it", vp.sel == [unnum["key"]] and vp.rolebar.isVisible())
check("the bar never covers the selection", not vp.rolebar.geometry().intersects(vp.sel_rect()))
check("the bar holds every role in the menu", [b.text().split("  ")[0] for b in vp.role_btns] == [r["name"] for r in VR.defaults()])
check("the bar says what to look at", vp.bar_msg.text().startswith("Check this suggestion"), vp.bar_msg.text())


def click(key, mods=Qt.NoModifier):
    r = vp.view.mapFromScene(vp.view.items[key].rect().center())
    for t in (QMouseEvent.MouseButtonPress, QMouseEvent.MouseButtonRelease):
        e = QMouseEvent(t, QPoint(r), vp.view.viewport().mapToGlobal(QPoint(r)), Qt.LeftButton,
                        Qt.LeftButton if t == QMouseEvent.MouseButtonPress else Qt.NoButton, mods)
        if t == QMouseEvent.MouseButtonPress:
            vp.view.mousePressEvent(e)
        else:
            vp.view.mouseReleaseEvent(e)


check("a role button sets the role", vp.set_role("h1") == 1 and VS.Store(w.ws.root).doc("SOW.pdf")["roles"][unnum["key"]] == "h1")
check("the page has nothing left to look at: Page verified, next", vp.b_ok.isEnabled() and vp.b_ok.text() == "Page verified, next")
ks = vp.keys()
click(ks[3]); click(ks[5], Qt.ShiftModifier)
check("Shift+click selects the run", vp.sel == ks[3:6], vp.sel)
click(ks[2], Qt.ControlModifier)
check("Ctrl+click adds one", ks[2] in vp.sel and len(vp.sel) == 4)
vp.view.mousePressEvent(QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(5, 5), QPoint(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
vp.view.mouseReleaseEvent(QMouseEvent(QMouseEvent.MouseButtonRelease, QPoint(5, 5), QPoint(5, 5), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
check("a click on blank page clears the selection and closes the bar", vp.sel == [] and not vp.rolebar.isVisible())
t21 = next(b["key"] for b in vp.v if b["text"].startswith("The Contractor shall design"))
vp.select([t21]); vp.select_section()
check("Select all text in this section", len(vp.sel) == 2)
check("Enter: verified by you, and the next page opens", vp.verified_next() and vp.n == 2
      and VS.Store(w.ws.root).doc("SOW.pdf")["verified"].get("1"))
check("the strip shows page 1 verified", vp.strip.status[0] == "verified" and vp.strip.cur == 2)
check("Prev goes back; the page says who verified it", vp.go(1) and "Verified" in vp.line.text() and "by" in vp.line.text())
check("the page counts every word", "Every word on the page is in a block" in vp.line.text())
check("Reopen this page: amber again, with why", vp.reopen("2.3 looks like H3") and vp.strip.status[0] == "look" and "2.3 looks like H3" in vp.line.text())
vp.page_box.setValue(2); spin()
check("the page box goes to a page", vp.n == 2)
sl = next(p for _n, _l, p in vp.docs() if p.endswith("Section_L_print.pdf"))
vp.open_doc(sl); spin()
check("another document", vp.doc == "Section_L_print.pdf" and vp.n == 1)
vp.open_doc(sow); spin()
check("each document opens where it was left", vp.n == 2)

# captions
vp.open_doc(cap); spin()
c = next(b for b in vp.v if b["text"].startswith("Table 1"))
row = next(b for b in vp.v if b["text"].startswith("Month"))
vp.select([row["key"]]); vp.set_role("table")
vp.select([c["key"]]); spin()
check("a caption: the bar says what it names, suggested", vp.link_row.isVisible() and "(suggested)" in vp.link_lbl.text())
check("Confirm links them", vp.confirm_link() and next(b for b in vp.v if b["key"] == c["key"])["link"]["ok"])
vp.select([c["key"]]); vp.start_pick()
other = next(b for b in vp.v if b["text"].startswith("The plan ramps"))
check("Pick another: the next click names the object", vp.pick_object(other["key"])
      and VS.Store(w.ws.root).doc(os.path.basename(cap))["links"][c["key"]]["to"] == other["key"])

# the menu
d = vp.edit_menu(run=False)
d.t.cellWidget(6, 1).setText("Body text"); d.t.cellWidget(13, 0).setChecked(False)
rid = d.add("Evaluation note", "text")
st = VS.Store(w.ws.root); st.set_menu(d.result_menu()); vp.show_page(); spin()
names = [b.text().split("  ")[0] for b in vp.role_btns]
check("Menu roles: renamed, hidden and your own role on the bar", "Body text" in names and "Running" not in names and "Evaluation note" in names, names)
d.save_team()
check("Save as team default", VR.load_team(cfg) and any(r["name"] == "Evaluation note" for r in VR.load_team(cfg)))
check("the reader follows Verify for this effort", len(PS.OVERRIDES) == 1)

print(f"QT VERIFY 384 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
