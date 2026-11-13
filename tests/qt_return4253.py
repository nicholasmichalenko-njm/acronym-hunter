"""4.25.3 offscreen: a customer document that goes back to the customer (Documents board 2026-11-12, step C; answers
2, 25, 32). Marking a document Redlined Deliverable makes a tile on Deliverables with no owner, linked both ways; a
deliverable filled on a customer document marks that document; Prepare for Redline lists only what is marked, opens
from the tile, and is off the menu; asking for it on a document marks it; pages still to look at stop a redline and
nothing else, with Prepare it anyway on the row; an amendment says the source changed and keeps the old redline;
Drafts > Reviewer markups puts a reviewer's PDF comments into a copy of our Word file. Fictional content."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import deliverables as DL, docintake as DI, docreturn as DR, docversions as DV, effort as E, effortrec as RR, redlineprep as RP, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docstatus as DS, usedfor as UF
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


S = os.path.join(A.BASE_DIR, "test_samples")
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
P = os.path.join(CD, "Kestrel_Model_Contract.pdf"); shutil.copy2(os.path.join(S, "comments", "C01_prose_commented.pdf"), P)
F = os.path.join(CD, "Kestrel_Pricing_Form.pdf"); shutil.copy2(os.path.join(S, "rfp_walk", "Section_L_print.pdf"), F)
lib0 = DV.Library(ws.p("documents")).load()
dC, _v = lib0.add(P, DI.read(P), doc_name="Model contract", role="reference", initial="Con", dtype="Contract")
dF, _v = lib0.add(F, DI.read(F), doc_name="Pricing form", role="reference", initial="Att", dtype="Attachment")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
said = []
w.open_effort("Kestrel"); app.processEvents()
w.status = lambda msg, *a, **k: said.append(msg)
w.go("redline"); pp = w.redline_page; pp.refresh(); app.processEvents()
check("nothing marked: Prepare for Redline lists nothing and says how to mark one", pp.table.rowCount() == 0 and pp.empty.isVisibleTo(w)
      and "Redlined Deliverable" in pp.empty.findChildren(type(pp.say))[0].text() + " ".join(x.text() for x in pp.empty.findChildren(type(pp.say))))
w.go("library"); lp = w.library_page; lp.refresh(); lp.select(dC["id"]); app.processEvents()
UF.toggle(lp, "redline"); app.processEvents()
rec = RR.Record(ws.root)
t = DR.tile_of(rec, dC["id"])
check("Redlined Deliverable makes a tile on Deliverables: a customer file, linked to the document, with no owner", t is not None
      and t["kind"] == "Customer file" and t["name"] == "Model contract" and t["owner"] == "" and t["returns"] == "redline"
      and t["form_version"] == dC["versions"][-1]["id"], t)
# 4.29.2 (answer 4 of 2026-11-13): the mark and the tile stay in step
tiles = lambda: [x for x in DL.items(RR.Record(ws.root)) if x.get("doc_id") == dC["id"]]   # noqa: E731
check("the mark reads Redlined Deliverable (not Return it)", dict(UF.MARKS)["redline"] == "Redlined Deliverable" and dict(UF.MARKS)["fill"] == "Filled-in Deliverable"
      and UF._tiles_lost(lp, lp.lib, [dC["id"]], "redline") == ["Model contract"])
check("untick it and answer Cancel: the mark and the tile both stay", UF.toggle(lp, "redline", answer=False) == 0
      and "redline" in lp.lib.returns_of(lp.lib.doc(dC["id"])) and len(tiles()) == 1)
check("untick it and Proceed: the mark is off and the tile leaves Deliverables", UF.toggle(lp, "redline", answer=True) == 1
      and not lp.lib.returns_of(lp.lib.doc(dC["id"])) and tiles() == [] and any(x["id"] == t["id"] for x in DL.removed(RR.Record(ws.root))))
UF.toggle(lp, "redline"); UF.toggle(lp, "fill"); app.processEvents()
check("tick it again: one tile again; a second mark makes no second tile", len(tiles()) == 1)
check("untick one of two marks: nothing to ask, the tile stays and says the mark left", UF._tiles_lost(lp, lp.lib, [dC["id"]], "fill") == []
      and UF.toggle(lp, "fill") == 1 and len(tiles()) == 1 and tiles()[0]["returns"] == "redline")
w.go("deliverables"); app.processEvents()
import skqt.delivdelete as DD
dpg = w.deliverables_page
tid = tiles()[0]["id"]
check("delete the tile on Deliverables: the question says the document loses its mark", "no longer marked as a deliverable" in DD.question(dpg, DL.get(dpg.ctx.rec, tid)))
check("... and the document's mark comes off with it", DD.delete(dpg, tid, answer=True) and not DV.Library(ws.p("documents")).load().returns_of(DV.Library(ws.p("documents")).load().doc(dC["id"])))
check("Undo puts the tile back, and the mark with it", DD.undo(dpg) and len(tiles()) == 1
      and DV.Library(ws.p("documents")).load().returns_of(DV.Library(ws.p("documents")).load().doc(dC["id"])) != [])
w.go("library"); app.processEvents()
lp.refresh(); app.processEvents()
if "redline" not in lp.lib.returns_of(lp.lib.doc(dC["id"])):
    lp.lib.set_returns(dC["id"], ["redline"])
rec = RR.Record(ws.root)
t = DR.tile_of(rec, dC["id"])
lp.select(dC["id"]); app.processEvents()
acts = [a.text() for a in DS.row_menu(lp, run=False).actions() if a.text()]
check("the document's right-click opens its deliverable", "Open its deliverable" in acts and UF.open_tile(lp, lp.lib.doc(dC["id"])) == t["id"]
      and w.stack.currentWidget() is w.deliverables_page and w.deliverables_page.picked == t["id"], acts)
dp = w.deliverables_page; dp.refresh(); c = dp.pick(t["id"]); app.processEvents()
from PySide6.QtWidgets import QPushButton
btns = [b.text() for b in dp.detail.findChildren(QPushButton)]
check("the tile offers Prepare for Redline and Open its document; it has no owner, and says so", "Prepare for Redline" in btns
      and "Open its document" in btns and ("crit", "No owner") in c["missing"] and c["returns"] == "redline", (btns, c["missing"]))
check("Prepare for Redline, from the tile: the document is the row", dp.prepare_redline(dC["id"]) and w.stack.currentWidget() is pp
      and pp.table.rowCount() == 1 and pp.table.item(0, 0).text() == "Model contract")
check("only what is marked is listed (the form is not)", [r[1] for r in RP.sources(DV.Library(ws.p("documents")).load())] == ["Model contract"]
      and len(RP.sources(DV.Library(ws.p("documents")).load(), marked=False)) == 2)
pp.to_look_at = lambda path: 3
check("pages still to look at stop a redline, and say what to do", pp.prepare(0) is None and "3 page(s) to look at first" in said[-1]
      and "Prepare it anyway" in said[-1], said[-1:])
out = pp.row_menu(0, pick="Prepare it anyway (pages still to look at)")
check("Prepare it anyway, on the row, prepares it as read", out and os.path.isfile(out) and os.path.basename(os.path.dirname(out)) == "Redlines", out)
w.go("library"); lp.refresh(); lp.select(dF["id"]); app.processEvents()
DS.prepare_redline(lp, lp.lib.doc(dF["id"])); app.processEvents()
check("asking for Prepare for redline on a document marks it and opens it there", "redline" in DV.Library(ws.p("documents")).load().returns_of(
      DV.Library(ws.p("documents")).load().doc(dF["id"])) and w.stack.currentWidget() is pp and pp.table.rowCount() == 2)
# a deliverable filled on a customer document marks the document
lib = DV.Library(ws.p("documents")).load()
lib.set_returns(dF["id"], [])
rec = RR.Record(ws.root)
for x in list(DL.items(rec)):
    if x.get("doc_id") == dF["id"]:
        DL.items(rec).remove(x)
rec.save()
did = DL.add(rec, "Pricing form, filled", kind="Form", doc_id=dF["id"], form_version=dF["versions"][-1]["id"])
check("both ways: a deliverable filled on a customer document marks it Filled-in Deliverable", DR.sync(rec, lib) == (0, 1)
      and lib.returns_of(lib.doc(dF["id"])) == ["fill"] and DR.sync(rec, lib) == (0, 0))
# an amendment
P2 = os.path.join(CD, "Kestrel_Model_Contract_A1.pdf"); shutil.copy2(os.path.join(S, "rfp_walk", "Section_L_print.pdf"), P2)
lib.add(P2, DI.read(P2), doc_id=dC["id"], label="Amendment 1")
st = DL.state(DR.tile_of(rec, dC["id"]), (), lib, (), rec)
check("an amendment: the tile says the source changed, the old redline is kept, prepare a new one", any("the source changed: Amendment 1" in x
      and "is kept" in x and "prepare a new one" in x for x in st["changed"]), st["changed"])
st2 = DL.state(DL.get(rec, did), (), lib, (), rec)
check("... a form keeps its own words (fill the new one) only when its document changes", not st2["changed"])
# Drafts > Reviewer markups
check("Drafts has Reviewer markups; Prepare for Redline is off the menu", ("markups", "Reviewer markups") in MW.TABS["drafts"]
      and "redline" not in [k for k, _t in MW.RAIL[0][1]] and "redline" not in w.step_btns)
w.go("markups"); mp = w.markups_page; app.processEvents()
mine = os.path.join(tmp, "Our draft.docx"); shutil.copy2(os.path.join(S, "comments", "C01_prose.docx"), mine)
res = mp.into_word(pdf=P, docx=mine)
check("a reviewer's PDF comments go into a dated copy of our Word file, beside it; our file is not changed", res and res["comments"]
      and os.path.dirname(res["path"]) == tmp and os.path.isfile(res["path"]) and res["path"] != mine
      and "tracked change" in mp.last.text() and w.stack.currentWidget() is mp, mp.last.text())
check("... one main button and one more on the page", mp.bar.main is not None and len(mp.bar.labels()) == 2, mp.bar.labels())
n_docs = len(DV.Library(ws.p("documents")).load().all)
made = mp.from_pdf(pdf=os.path.join(tmp, "missing.pdf")) if False else mp.from_pdf(pdf=shutil.copy2(P, os.path.join(tmp, "Reviewer copy.pdf")))
check("a Word file made from the reviewer's PDF sits beside the PDF; nothing is added to Documents", made and os.path.dirname(made) == tmp
      and len(DV.Library(ws.p("documents")).load().all) == n_docs, made)
w.close()
n = sum(checks)
print(f"QT RETURN 4253 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
