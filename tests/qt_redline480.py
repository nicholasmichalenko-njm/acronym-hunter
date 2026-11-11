"""4.8.0 offscreen: Redline in the window. A menu item below the six steps with no number; its tabs Prepare, Check and
Exceptions; Prepare lists the customer PDFs and makes the Word copy in the Redlines folder; Check finds nothing to
report on a fresh copy and lists an untracked edit in a returned redline; Exceptions reads the tracked changes and
exports them; Documents' row menu opens Prepare on the document; every role sees it. Fictional content (Kestrel)."""
import os, re, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, workspace as W, roleaccess as RA
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docstatus as DS
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
src = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
P = os.path.join(CD, "Kestrel_Section_L.pdf"); shutil.copy2(src, P)
lib0 = DV.Library(ws.p("documents")).load()
dL, _v = lib0.add(P, DI.read(P), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
check("Redline is in the menu below the six steps, with no step number", "redline" in w.step_btns and "redline" not in MW.STEP_KEYS
      and [k for k, _t in MW.RAIL[0][1]][-1] == "redline")
w.rail_go("redline"); app.processEvents()
check("its tabs: Prepare, Check, Exceptions", w._tab_keys == ["redline", "rcheck", "exceptions"] and w.page_title.text() == "Redline",
      (w._tab_keys, w.page_title.text()))
check("every role sees it", all(RA.allowed(r, k) for r in ("Production", "Author", "Reviewer", "Capture") for k in ("redline", "rcheck", "exceptions")))
pp = w.redline_page
pp.refresh(); app.processEvents()
check("Prepare lists the customer PDFs, none copied yet", pp.table.rowCount() == 1 and pp.table.item(0, 2).text() == "not yet"
      and pp.bar.main.text() == "Make the Word copy")
copy = pp.make(); app.processEvents()
check("Make the Word copy writes it in the effort's Redlines folder", copy and os.path.isfile(copy)
      and os.path.basename(os.path.dirname(copy)) == "Redlines" and " - redline copy - " in copy, copy)
check("... and the list says when", pp.table.item(0, 2).text() != "not yet")
w.go("rcheck"); cp = w.rcheck_page; cp.refresh(); app.processEvents()
res = cp.check_copy()
check("Check: a fresh copy holds every word of its PDF", res and not res["differences"] and "every word" in cp.say.text(), cp.say.text())
with zipfile.ZipFile(copy) as z:
    data = {n: z.read(n) for n in z.namelist()}
x = data["word/document.xml"].decode("utf-8").replace("cautioned", "warned", 1)
A_ = 'w:author="Pat Writer" w:date="2026-11-10T09:00:00Z"'
x = re.sub(r'(<w:r><w:t xml:space="preserve">Pages shall be 8.5 by 11 inches)', lambda m: (
    f'<w:del w:id="91" {A_}><w:r><w:delText xml:space="preserve">Pages shall be 8.5 by 11 inches</w:delText></w:r></w:del>'
    f'<w:ins w:id="92" {A_}><w:r><w:t xml:space="preserve">Pages shall be A4</w:t></w:r></w:ins><w:r><w:t xml:space="preserve">'), x, count=1)
back = os.path.join(tmp, "returned redline.docx")
with zipfile.ZipFile(back, "w") as z:
    for n, b in data.items():
        z.writestr(n, x.encode("utf-8") if n == "word/document.xml" else b)
r2 = cp.check_returned(back)
check("Check the returned redline: the edit made with Track Changes off is listed with the heading above it",
      r2 and len(r2["differences"]) == 1 and cp.table.item(0, 1).text() == "cautioned" and cp.table.item(0, 4).text() == "L.1 General Instructions",
      r2["differences"] if r2 else None)
check("... double-click shows it on the page in Shred", cp.show_on_page(0) and w.stack.currentWidget() is w.assign_page)
w.go("exceptions"); ep = w.exceptions_page; app.processEvents()
rows = ep.read(back)
check("Exceptions: each tracked change a row with the customer's number", rows and rows[0]["Kind"] == "Replaced" and rows[0]["Number"] == "L.2"
      and ep.table.rowCount() == 1, rows)
xl = ep.export("xlsx")
check("... exported to Excel in the Redlines folder", xl and os.path.isfile(xl) and " - exceptions - " in xl, xl)
w.go("library"); lp = w.library_page; lp.refresh(); lp.select(dL["id"]); app.processEvents()
m = DS.row_menu(lp, run=False)
act = next((a for a in m.actions() if a.text() == "Prepare a redline copy"), None)
rows_now = {r[0]: r for r in lp.status_now} if hasattr(lp, "status_now") else {}
check("Documents: the panel says when the redline copy was made", rows_now.get("Redline copy", ("", ""))[1].startswith("Made "), rows_now.get("Redline copy"))
act.trigger() if act else None; app.processEvents()
check("... and the row's menu opens Redline > Prepare on the document", act is not None and w.stack.currentWidget() is pp
      and pp.table.currentRow() == 0)
w.close()
print(f"QT REDLINE 480 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
