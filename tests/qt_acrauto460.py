"""4.6.0 offscreen: the customer's documents are scanned for acros and abs as soon as they are in and extracted (steps
decision 10; claude/stationkeeper-documents-changes-plan-4.6.md, step 4): on the same timer as extraction, in the
background, never twice for the same documents, and again when a new document arrives. Fictional (Osprey)."""
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
V1 = ["L.3 PROPOSAL VOLUMES", "Volume I Technical shall not exceed 50 pages. The Integrated Master Schedule (IMS) shall be current.", "L.4 RISK MANAGEMENT",
      "The Offeror shall identify the five highest program risks.", "The Offeror shall name an owner for each risk.",
      "L.5 TRANSITION", "The Offeror shall describe its transition approach in ninety days."]
V2 = ["L.3 PROPOSAL VOLUMES", "Volume I Technical shall not exceed 40 pages.", "L.4 RISK MANAGEMENT",
      "The Offeror shall identify the five highest program risks.", "The Offeror shall name an owner for each risk.",
      "The Offeror shall describe a mitigation plan for each high risk.",
      "L.5 TRANSITION", "The Offeror shall describe its transition approach in ninety days."]
P1 = os.path.join(CD, "Osprey_Section_L.pdf"); pdfmini.write(P1, [V1], size=9)
P2 = os.path.join(CD, "Osprey_Section_L_Amd1.pdf"); pdfmini.write(P2, [V2], size=9)
PS = os.path.join(CD, "Osprey_SOW.pdf"); pdfmini.write(PS, [["C.1 SCOPE", "The contractor shall operate the Ground Control Segment (GCS) and report to the COR."]], size=9)
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
check("... 4.25.2: only what is marked For the shred (Section L); the SOW is Reference and is not extracted",
      wait(lambda: w.review is not None and not w.read_page.running())
      and sorted(w.review.files()) == ["Osprey_Section_L.pdf"], w.review.files() if w.review else None)
check("... with no question asked", not asked, asked)
# 4.6.0: the acronym scan follows, on the same timer
ap = w.acronym_page
before = w.stack.currentWidget()
wk = SP.auto_scan(w)
check("4.6.0: once the documents are extracted, Acronyms scans them, in the background, no page change",
      (wk is not None or (ap.session and ap.session.last_scan)) and w.stack.currentWidget() is before)   # the timer may be first
check("... and finds their terms, the Reference document's too (GCS)", wait(lambda: ap.worker is None) and ap.session.results
      and {"IMS", "GCS"} <= set(ap.session.results.keys() if hasattr(ap.session.results, "keys") else []), list(ap.session.results)[:10] if ap.session.results else None)
check("... the same documents are not scanned again", SP.auto_scan(w) is None)
w._acr_seen = None
check("... not even after the window forgets (the last scan holds them)", SP.auto_scan(w) is None)
lib1 = DV.Library(ws.p("documents")).load()
P3 = os.path.join(CD, "Osprey_CDRL.pdf"); pdfmini.write(P3, [["A001 MONTHLY STATUS", "The Program Management Review (PMR) is monthly."]], size=9)
lib1.add(P3, DI.read(P3), doc_name="CDRL", role="matrix", initial="A", dtype="Attachment")
check("a new document marked For the shred waits for its extraction first", SP.auto_scan(w) is None)
ap.worker = object()
check("... and extraction waits while a scan runs (one reader at a time)", SP.auto_tick(w) is None)
ap.worker = None
SP.auto_tick(w); wait(lambda: not w.read_page.running() and not SP.pending(w))
SP.auto_scan(w)
check("... then the scan runs again with it", wait(lambda: ap.worker is None and P3 in ((ap.session.last_scan or {}).get("paths") or []))
      and "PMR" in set(ap.session.results.keys()), list(ap.session.results)[:12])
w.close()
print(f"QT ACRAUTO 460 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
