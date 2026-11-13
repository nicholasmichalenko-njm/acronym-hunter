"""4.25.5 offscreen: the Graphics page (Nicholas's recording 2026-11-12; the Documents board, step E). One row per
graphic: a picture in Documents, a picture inside a document that the scan found terms in, a graphic need. Each row
says, for its current version, whether its words are read and its acros and abs swept; both marks are kept by the
file's name, so a new version starts with neither. Fictional (Osprey)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import acrpages as AG, docintake as DI, docversions as DV, effort as E, effortrec as RR, graphiclog as GL, graphics as GX, workspace as W, pdfmini
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL, STEP_KEYS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
PL = os.path.join(CD, "Osprey_Section_L.pdf"); pdfmini.write(PL, [["L.3 VOLUMES", "Volume I shall not exceed 50 pages."]], size=9)
G1 = os.path.join(CD, "ops_concept_v1.png"); Image.new("RGB", (200, 120), "white").save(G1)
G2 = os.path.join(CD, "ops_concept_v2.png"); Image.new("RGB", (220, 120), "white").save(G2)
GO = os.path.join(ED, "org_chart.png"); Image.new("RGB", (180, 100), "white").save(GO)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
lib = DV.Library(ws.p("documents")).load()
dL, _v = lib.add(PL, DI.read(PL), doc_name="Section L", role="matrix", initial="Sec L", dtype="Section L")
dG, _v = lib.add(G1, [], doc_name="Operations concept", role="reference", initial="Att", dtype="Attachment")
dO, _v = lib.add(GO, [], doc_name="Org chart", category="graphics")

# ---- the rules, with no window
f1 = "ops_concept_v1.png"
pg1 = {"key": f1 + " (Image)", "name": f1, "label": "Image", "terms": {"GCS": "decide"}, "to_decide": 1, "done": False}
ins = {"key": "Osprey_Deck.pptx (Slide 4, image 'Picture 2' image1.png)", "name": "Osprey_Deck.pptx", "label": "Slide 4, image 'Picture 2' image1.png",
       "terms": {"IMS": "list"}, "to_decide": 0, "done": False}
rs = GL.rows(lib, [pg1], [G1], (), (), ())
by = {r["name"]: r for r in rs}
check("a picture in Documents and a document filed as a graphic each get a row; a text document does not",
      sorted(by) == ["Operations concept", "Org chart"], sorted(by))
check("... whose it is comes from the document", by["Operations concept"]["side"] == "customer" and by["Org chart"]["side"] == "ours")
check("... scanned with a find to decide: read, not confirmed; 1 to decide", by["Operations concept"]["words"] == "Read, not confirmed"
      and by["Operations concept"]["acros"] == "1 to decide", by["Operations concept"])
check("... never scanned: Not read, Not scanned", by["Org chart"]["words"] == "Not read" and by["Org chart"]["acros"] == "Not scanned", by["Org chart"])
rs = GL.rows(lib, [pg1], [G1, GO], [pg1["key"]], [pg1["key"]], ())
by = {r["name"]: r for r in rs}
check("the page marked done and the words confirmed: Swept, Confirmed, nothing left to do",
      by["Operations concept"]["acros"] == "Swept" and by["Operations concept"]["words"] == "Confirmed" and not GL.todo(by["Operations concept"]))
check("scanned and nothing found is still to mark swept (a person says the sweep is done)",
      by["Org chart"]["acros"] == "None found, not marked swept" and GL.todo(by["Org chart"]), by["Org chart"])
lib.add(G2, [], doc_id=dG["id"], label="Amd1")
rs = GL.rows(lib, [pg1], [G1], [pg1["key"]], [pg1["key"]], ())
r2 = next(r for r in rs if r["name"] == "Operations concept")
check("a new version starts with neither mark, and says it has 2 versions", r2["words"] == "Not read" and r2["acros"] == "Not scanned"
      and r2["versions"] == 2 and r2["version"] == "Amd1", r2)
deck = {"id": "dk", "name": "Briefing", "category": "customer", "versions": [{"file": "Osprey_Deck.pptx", "label": "As issued"}]}


class FakeLib:
    all = [deck]


ri = GL.rows(FakeLib(), [ins], ["Osprey_Deck.pptx"], (), (), ())
check("a picture inside a document that the scan found terms in gets a row, under its document",
      len(ri) == 1 and ri[0]["kind"] == "inside" and ri[0]["where"] == "Briefing" and ri[0]["acros"] == "Decided, not marked swept", ri)
need = {"id": "n1", "concept": "Transition timeline", "kind": "Process flow", "section": "Volume I, 3.2", "owner": "Dana", "status": "Needed"}
rn = GL.rows(FakeLib(), [], [], (), (), [need])
check("a graphic need is a row with its section, owner and status", rn[0]["kind"] == "need" and rn[0]["where"] == "Volume I, 3.2"
      and rn[0]["owner"] == "Dana" and rn[0]["status"] == "Needed" and GL.todo(rn[0]))
allr = ri + rn + rs
check("the filters: Customer, Internal, Needs, Left to do, and Find", len(GL.shown(allr, "need")) == 1
      and all(r["side"] == "customer" and r["kind"] != "need" for r in GL.shown(allr, "customer"))
      and [r["name"] for r in GL.shown(allr, "ours")] == ["Org chart"] and [r["name"] for r in GL.shown(allr, "", "timeline")] == ["Transition timeline"])
check("the count line's numbers", GL.counts(allr) == (3, 3, 3, 1), GL.counts(allr))

# ---- the page
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Osprey"); app.processEvents()
check("Graphics is in the menu under Documents, with no step number", ("graphics", "Graphics") in RAIL[0][1]
      and RAIL[0][1].index(("graphics", "Graphics")) == RAIL[0][1].index(("library", "Documents")) + 1 and "graphics" not in STEP_KEYS
      and w.step_btns["graphics"].n is None)
steps = [k for k in STEP_KEYS]
check("... the six steps keep their numbers", steps == ["home", "library", "assign", "matrix", "setups", "drafts", "finalcheck"], steps)
GX.add(RR.Record(w.ws.root), "Transition timeline", kind="Process flow", section="Volume I, 3.2", owner="Dana")
ok = w.go("graphics"); app.processEvents()
gp = w.graphics_page
names = [gp.table.item(r, 0).text() for r in range(gp.table.rowCount())]
check("the page lists the two pictures and the need", ok is not False and w.stack.currentWidget() is gp and len(names) == 3
      and any(n.startswith("Operations concept") for n in names) and any(n.startswith("Transition timeline") for n in names), names)
check("... with the count line", "2 graphics" in gp.count.text() and "1 graphic need open" in gp.count.text(), gp.count.text())
gp.select("doc:" + dG["id"])
g = gp.current()
m = gp.menu(None)
check("right-click a graphic: open it, show its document, the two marks, scan it now",
      [a.text() for a in m.actions() if a.text()] == ["Open it in Acros & Abs", "Show its document", "Words read: confirmed",
                                                      "Acros and abs: swept", "Find acros and abs in it now"], [a.text() for a in m.actions()])
gp.set_words(True); gp.set_swept(True)
g = gp.current()
check("tick both marks: Confirmed and Swept, kept with the effort", g["words"] == "Confirmed" and g["acros"] == "Swept"
      and set(g["keys"]) <= GL.words_ok(w.ws) and set(g["keys"]) <= AG.done_set(w.ws), g)
gp.flt.setCurrentIndex(gp.flt.findData("todo")); app.processEvents()
names = [gp.table.item(r, 0).text() for r in range(gp.table.rowCount())]
check("Left to do hides it", not any(n.startswith("Operations concept") for n in names) and len(names) == 2, names)
gp.flt.setCurrentIndex(0)
gp.set_swept(False, g)
check("untick: to sweep again", gp.current() is not None and gp.current()["acros"] != "Swept")
gp.select(next(r["id"] for r in gp.rows if r["kind"] == "need"))
mn = gp.menu(None)
check("right-click a need: Needed, In work, Done", [(a.text(), a.isChecked()) for a in mn.actions()] == [("Needed", True), ("In work", False), ("Done", False)])
gp.set_status("Done")
check("... Done is saved in the effort record and the count drops", GX.items(RR.Record(w.ws.root))[0]["status"] == "Done"
      and "0 graphic needs open" in gp.count.text(), gp.count.text())
gp.select("doc:" + dO["id"])
check("Show its document opens Documents on it", gp.open_file() and w.stack.currentWidget() is w.library_page
      and w.library_page.current_id() == dO["id"])
w.close()
print(f"QT GRAPHICS 4255 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
