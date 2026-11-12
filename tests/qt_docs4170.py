"""4.17.0 offscreen: Nicholas's case, 2026-11-11 17:42. A PDF is added and extracted; it is edited where it sits in
Customer documents and added again. Before 4.17.0 it became Amendment 1 with the same file and was never read again (the
shred kept the old sentences over the new pages). Now it is the same document and version, read again into the shred:
the new sentences are pieces, the old decisions stay. Replace the file... and Read it again are on the right-click;
Delete... asks first and moves the document and its pieces to the Trash; Undo puts them back; the Trash restores;
Fix text's Heading offers the levels and the pieces below take the reference. Fictional (Kestrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, doctrash as T, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import docmanage as DM, docstatus as DS, fixtext as FX

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


FIX = os.path.join(A.BASE_DIR, "test_samples", "docs4170")
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
toasts = []
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
w.toast = lambda msg, *a, **k: toasts.append(msg)


def wait(cond, secs=120):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()
    return cond()


def lib():
    return DV.Library(w.ws.p("documents")).load()


src = os.path.join(tmp, "Section L.pdf"); shutil.copy2(os.path.join(FIX, "C01v1.pdf"), src)
DI.apply(lib_ := lib(), DI.plan(lib_, [src]), customer_dir=CD)
w.read_page.read([os.path.join(CD, "Section L.pdf")], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
M = w.review.M
by = lambda s: next((it for it in M.items if s in (it.get("text") or "")), None)        # noqa: E731
first = by("deliver the Kestrel test plan")
first["decision"], first["owner"] = "Keep", "Pat Writer"
inside = os.path.join(CD, "Section L.pdf")
shutil.copy2(os.path.join(FIX, "C01v2.pdf"), inside)            # edited where it sits
w.go("library"); lp = w.library_page; lp.refresh(); app.processEvents()
d = lib().docs[0]
lp.select(d["id"]); app.processEvents()
menu = [a.text() for a in DS.row_menu(lp, run=False).actions()]
check("the right-click offers Replace the file..., Read it again (edited) and Delete...", "Replace the file..." in menu
      and "Read it again (the file was edited)" in menu and "Delete..." in menu, menu)
plan = DI.plan(lib(), [inside], edited="replace")
check("added again, the edited file is the same document (replace), not Amendment 1", plan[0]["choice"] == "replace", plan[0]["choice"])
DI.apply(l2 := lib(), plan, customer_dir=CD)
check("... still one version", len(lib().docs[0]["versions"]) == 1)
wk = DM.reread(w)
check("the shred reads it again", wk is not None and wait(lambda: not w.read_page.running()))
check("... the new sentences are pieces", by("Late proposals") is not None and by("fixed by the contracting officer") is not None)
first = by("deliver the Kestrel test plan")
check("... the old decisions stay", first["decision"] == "Keep" and first["owner"] == "Pat Writer")
check("... no longer marked to read again", not lib().docs[0]["versions"][0].get("reread"))
w.go("assign"); pg = w.assign_page; pg.load_files_keep(); app.processEvents()
check("Shred lists the one file", [pg.files.itemText(i) for i in range(pg.files.count())][:1] == ["Section L.pdf"])
pg.open_file("Section L.pdf"); app.processEvents()
late = by("Late proposals")
check("... its new piece is on the page to shred", late["id"] in pg.view.boxes)
# Fix text: headings with levels
FX.toggle(pg) if not pg.fix_on else None
names = [a.text() for a in FX.heading_menu(pg, run=False).actions() if a.text()]
check("Fix text's Heading: H1 to H9, Not a heading", names == [f"H{n}" for n in range(1, 10)] + ["Not a heading"], names)
sub = by("Volume I holds the technical approach")
pg.select(sub["id"]); app.processEvents()
FX.heading(pg, 3); app.processEvents()
_i = M.items.index(sub)
after = next((it for it in M.items[_i + 1:] if it.get("file") == sub.get("file") and it.get("header") != "Yes"), None)
check("a H3 heading with no number: the pieces below read under its parent", sub["type"] == "Heading" and sub["hlevel"] == 3
      and after["section_title"].endswith("> " + sub["text"].strip(" .:")) and after["section"] == sub["section"],
      (after and (after["text"][:40], after["section"], after["section_title"]), sub["section"], sub["section_title"]))
import rfpoutline as RO, structure_ops as SO
ro = RO.as_outline(M)
mine = next((o for o in ro if o["title"].startswith("Volume I holds")), None)
check("... the RFP's own outline (Start from) holds it at H3, with its page, and no number", mine is not None
      and mine["level"] == 3 and mine["num"] == "" and mine.get("page"), mine)
check("... and Start from the customer's headings puts it under its section", any(o["title"].startswith("Volume I holds")
      for o in SO.from_headings(M, "L")), [o["title"][:20] for o in SO.from_headings(M, "L")])
pg.do_undo(); app.processEvents()
check("... and Undo takes it back", by("Volume I holds the technical approach").get("type") != "Heading")
# delete, undo, the Trash
w.go("library"); lp.refresh(); lp.select(d["id"]); app.processEvents()
n = len(M.items)
eid = DM.delete(lp, lib().docs[0], answer=True); app.processEvents()
M = w.review.M
check("Delete...: the document and its pieces go to the Trash", eid and not lib().docs and not os.path.isfile(inside)
      and not any(it.get("file") == "Section L.pdf" for it in M.items) and "Trash" in toasts[-1], toasts[-1:])
check("... Undo is offered", lp.undo_text().startswith("Delete Section L"))
lp.undo_here(); app.processEvents(); M = w.review.M
check("... Undo puts it all back", lib().docs and os.path.isfile(inside) and sum(1 for it in M.items if it.get("file") == "Section L.pdf") > 0
      and by("deliver the Kestrel test plan")["owner"] == "Pat Writer")
eid = DM.delete(lp, lib().docs[0], answer=True); app.processEvents()
dlg = DM.show_trash(lp, run=False)
check("Documents > More > Trash... lists it", any("Section L" in dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount()))
      and "Trash..." in [a.text() for a in lp.bar.more_menu.actions()])
row = next(r for r in range(dlg.table.rowCount()) if dlg.table.item(r, 1).text() == "Document")
dlg.restore(row); app.processEvents()
check("... Restore puts it back", lib().docs and os.path.isfile(inside))
check("Empty the Trash... asks, and Cancel keeps it", dlg.empty(answer=False) == 0 and T.entries(w.ws))
# 4.23.2: Shred's document list follows a delete; a file that cannot be moved does not stop the delete
w.go("assign"); pg.load_files_keep(); app.processEvents()
names = lambda: [pg.files.itemText(i) for i in range(pg.files.count())]   # noqa: E731
check("Shred lists the document while it is there", "Section L.pdf" in names(), names())
w.go("library"); lp.refresh(); app.processEvents()
import shutil as _sh
real_move, real_copy = _sh.move, _sh.copy2
def _gone(*a, **k):
    raise FileNotFoundError(2, "No such file or directory")
_sh.move = _gone; _sh.copy2 = _gone
try:
    eid = DM.delete(lp, lib().docs[0], answer=True); app.processEvents(); err = None
except Exception as e:  # noqa: BLE001
    eid, err = None, e
_sh.move, _sh.copy2 = real_move, real_copy
ent = T.entry(w.ws, eid) if eid else None
check("a file that cannot be moved to the Trash: the delete finishes, nothing is raised", err is None and eid and not lib().docs, err)
check("... the Trash entry says which file was not kept", ent and any(f.get("lost") for f in ent["files"]), ent and ent["files"])
check("... and Shred no longer offers the deleted document", "Section L.pdf" not in names(), names())
got = DM.restore(lp, eid); app.processEvents()
check("Restore still brings the record back, without the lost file, and Shred lists what is back", got is not None and lib().docs, got)
k = sum(checks)
print(f"QT DOCS 4170 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
w.close(); app.quit()
sys.exit(0 if k == len(checks) else 1)
