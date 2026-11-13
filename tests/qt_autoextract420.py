"""4.2.0 offscreen: adding a document starts the shred (claude/stationkeeper-fix-text-decisions-2026-11-10.md, decisions 2,
3, 4, 9, 10). Every customer document not left out is extracted in the background, whatever its role, with no page
change and no question; the matrix saves itself and keeps the day's copy in Matrix history; a new version is extracted
at once: the same sentences keep their pieces and decisions (moved onto its pages), new sentences arrive as new pieces,
changed ones wait for Changes, nothing appears twice. Fictional (an Osprey Section L)."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_AUTO_EXTRACT_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import docintake as DI, docversions as DV, effort as E, workspace as W, pdfmini, matrixhistory as MH
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
asked = []
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.Yes)
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: asked.append(a) or ("", ""))
from skqt import design as D
from skqt import shredpick as SP
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
V1 = ["L.3 PROPOSAL VOLUMES", "Volume I Technical shall not exceed 50 pages.", "L.4 RISK MANAGEMENT",
      "The Offeror shall identify the five highest program risks.", "The Offeror shall name an owner for each risk.",
      "L.5 TRANSITION", "The Offeror shall describe its transition approach in ninety days."]
V2 = ["L.3 PROPOSAL VOLUMES", "Volume I Technical shall not exceed 40 pages.", "L.4 RISK MANAGEMENT",
      "The Offeror shall identify the five highest program risks.", "The Offeror shall name an owner for each risk.",
      "The Offeror shall describe a mitigation plan for each high risk.",
      "L.5 TRANSITION", "The Offeror shall describe its transition approach in ninety days."]
P1 = os.path.join(CD, "Osprey_Section_L.pdf"); pdfmini.write(P1, [V1], size=9)
P2 = os.path.join(CD, "Osprey_Section_L_Amd1.pdf"); pdfmini.write(P2, [V2], size=9)
PS = os.path.join(CD, "Osprey_SOW.pdf"); pdfmini.write(PS, [["C.1 SCOPE", "The contractor shall operate the ground station."]], size=9)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
lib0 = DV.Library(ws.p("documents")).load()
dL, _v = lib0.add(P1, DI.read(P1), doc_name="Section L", role="matrix", initial="L", dtype="Section L")
dS, _v = lib0.add(PS, DI.read(PS), doc_name="Statement of Work", role="context", initial="S", dtype="SOW")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey"); app.processEvents()
w.go("library"); app.processEvents()
SP.auto_tick(w)
check("adding starts the shred: the documents are extracted in the background, no page change", w.read_page.running()
      and w.stack.currentWidget() is w.library_page)
check("4.25.2: ... the one marked For the shred (Section L); the SOW, marked Reference, waits for its mark",
      wait(lambda: w.review is not None and not w.read_page.running())
      and sorted(w.review.files()) == ["Osprey_Section_L.pdf"], w.review.files() if w.review else None)
import docversions as _DV4252
_lib = _DV4252.Library(w.ws.p("documents")).load()
_sow = _lib.doc_of_file("Osprey_SOW.pdf")
check("4.25.2: mark it For the shred and it is extracted too", _lib.set_role(_sow["id"], "matrix") and SP.auto_tick(w) is not None
      and wait(lambda: not w.read_page.running() and sorted(w.review.files()) == ["Osprey_SOW.pdf", "Osprey_Section_L.pdf"]),
      w.review.files() if w.review else None)
check("... with no question asked", not asked, asked)
check("nothing is extracted twice", SP.auto_tick(w) is None and not SP.pending(w))
M = w.review.M
by = lambda s, f="Osprey_Section_L.pdf": [it for it in M.items if s in it["text"] and it["file"] == f]       # noqa: E731
owner, pages50 = by("owner for each")[0], by("50 pages")[0]
w.review.req([owner], "")
owner_id, owner_dec = owner["id"], owner.get("decision")
w.changed(); w.save_now(); app.processEvents()
today = datetime.date.today().isoformat()
hist = MH.copies(M.path)
check("the matrix saved itself, and the day's copy is in Matrix history, named and dated", os.path.isfile(M.path)
      and [d.isoformat() for d, _p in hist] == [today] and os.path.basename(hist[0][1]).endswith(f"_{today}.xlsx")
      and os.path.basename(os.path.dirname(hist[0][1])) == MH.FOLDER, hist)
# a new version comes in
lib = DV.Library(ws.p("documents")).load()
lib.add(P2, DI.read(P2), doc_id=dL["id"], label="Amendment 1")
SP.auto_tick(w)
check("a new version is extracted at once", wait(lambda: not w.read_page.running() and "Osprey_Section_L_Amd1.pdf" in w.review.files()),
      w.review.files())
M = w.review.M
new_file = "Osprey_Section_L_Amd1.pdf"
kept = next(it for it in M.items if it["id"] == owner_id)
check("the same sentence keeps its piece and decision, now on the new version's page", kept["file"] == new_file
      and kept.get("decision") == owner_dec and len([it for it in M.items if "owner for each" in it["text"]]) == 1)
mit = [it for it in M.items if "mitigation plan" in it["text"]]
check("a new sentence arrives as a new piece, not sorted, marked new", len(mit) == 1 and mit[0]["file"] == new_file
      and not mit[0].get("decision") and mit[0].get("new", "").startswith("New in Section L"), mit)
check("a changed sentence waits for Changes: its piece stays, the new wording is not a second piece",
      pages50["file"] == "Osprey_Section_L.pdf" and not [it for it in M.items if "40 pages" in it["text"]])
check("nothing appears twice", len([it for it in M.items if "five highest" in it["text"]]) == 1
      and len([it for it in M.items if "transition approach" in it["text"]]) == 1)
w.close()
print(f"QT AUTOEXTRACT 420 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
