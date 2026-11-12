"""4.19.0 offscreen: Shred's views are Page and List; List shows the shred under the customer's headings and opens a piece
on its page. A piece typed Structure (key O) feeds Start our structure: the card shows while the outline is empty and
recommends Door 1; the preview reads the headings, takes edits and puts them in with Required by; Check against the
required structure finds a rename. Door 2 drafts headings; Use it as our structure takes Draft off. Fictional (Kestrel)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, shredtypes as ST, structfrom as SF, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import structdoors as SDR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
src = os.path.join(tmp, "Section L.pdf"); shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "docs4170", "C01v1.pdf"), src)
lib = DV.Library(w.ws.p("documents")).load()
DI.apply(lib, DI.plan(lib, [src]), customer_dir=CD)
w.read_page.read([os.path.join(CD, "Section L.pdf")], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while (w.review is None or w.read_page.running()) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
by = lambda s: next(x for x in M.items if s in (x.get("text") or ""))          # noqa: E731
w.go("assign"); app.processEvents()
check("Shred's views are Page and List", list(w.stepper.views) == ["assign", "shredlist"])
vol = by("Volume I holds the technical approach")
pg = w.assign_page
pg.load_files_keep(); pg.open_file("Section L.pdf"); app.processEvents()
pg.select(vol["id"]); app.processEvents()
from skqt import shredbar as SB
SB.toggle_piece(pg, "structure"); app.processEvents()
check("a piece typed Structure", ST.has(vol, "structure"))
w.stepper.see("shredlist"); app.processEvents()
lp = w.shredlist_page
top = lp.t.topLevelItem(0)
check("List: the document, its headings and counts", top is not None and top.text(0).startswith("Section L.pdf") and "decided" in top.text(0)
      and top.childCount() >= 1, top.text(0) if top else None)


def find(item, iid):
    for i in range(item.childCount()):
        c = item.child(i)
        d = c.data(0, 0x0100)
        if d and d[1] == iid:
            return c
        got = find(c, iid)
        if got is not None:
            return got
    return None


late = by("shall not exceed 25 pages")
row = find(top, late["id"])
check("... each piece under its heading", row is not None)
lp.only.setChecked(True); app.processEvents()
check("... Undecided only leaves the Structure piece out", find(lp.t.topLevelItem(0), vol["id"]) is None)
lp.only.setChecked(False); app.processEvents()
ok = lp.open_piece(find(lp.t.topLevelItem(0), late["id"])); app.processEvents()
check("double-click opens the piece on its page", ok and w.stack.currentWidget() is pg and late["id"] in [x["id"] for x in pg.selected()])
w.go("structure"); bp = w.structure_page; bp.refresh(); app.processEvents()
check("Start our structure shows while our outline is still the app's start, Door 1 recommended", SF.untouched(M) and bp.start_card.isVisibleTo(w)
      and bp.door1.isEnabled() and "1 piece(s) typed Structure" in bp.door1_say.text(), bp.door1_say.text())
dlg = SDR.preview(bp, run=False)
heads = dlg.heads()
check("the preview reads the volumes", [h["title"] for h in heads][:3] == ["Volume I", "Volume II", "Volume III"], [h["title"] for h in heads])
dlg.t.cellWidget(0, 1).setText("Volume I Technical")
ents = SDR.put(bp, dlg.heads()); app.processEvents()
check("Put in our outline: the headings with Required by, in place of the app's start; the card goes", len(M.outline) == 3 and M.outline[0].get("req") == vol["id"]
      and not bp.start_card.isVisibleTo(w), [(o.get("title"), o.get("req")) for o in M.outline])
M.outline[1]["title"] = "Our Management"
got = SDR.check(bp, show=False)
check("Check against the required structure finds the rename", [k for k, _t in got] == ["renamed"], got)
names = []
m = __import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu(); SDR.more_items(bp, m)
names = [a.text() for a in m.actions() if a.text()]
check("Structure... holds both doors for later and the check", "Add the required headings (Structure pieces)..." in names
      and "Draft headings from" in names and "Check against the required structure" in names, names)
got = SDR.drafts(bp, "headings"); app.processEvents()
check("Door 2: draft headings go after the required frame, marked Draft", got and SF.draft_count(M) == len(got))
n = SDR.use_as_ours(bp)
check("Use it as our structure", n == len(got) and SF.draft_count(M) == 0)
k = sum(checks)
print(f"QT STRUCT 4190 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
w.close(); app.quit()
sys.exit(0 if k == len(checks) else 1)
