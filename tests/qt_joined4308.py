"""4.30.8, offscreen (Nicholas 2026-11-13 21:33, Option A): one answer for a joined term, on the card's More menu.
"These are separate terms" on a joined term puts its pieces in its place; "This is one term" on a piece puts the joined
term back. The answer is kept with the effort and holds on the next scan. Made-up terms (the Heron set)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
os.environ["AH_OCR_ENGINE"] = "tesseract"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
import skqt.acrfast as _AF; _AF.AT_ONCE = True
from skqt.mainwin import MainWindow
from skqt import acrpart as APT
import acrjoined as J
from docx import Document

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
EDIR = os.path.join(tmp, "Heron"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
doc = Document()
for line in ["The QRXT/ZVBN board met.", "A second QRXT/ZVBN note.", "The KLPD-MNBW link is up.", "The KLPD group met."]:
    doc.add_paragraph(line)
src = os.path.join(tmp, "Heron_Notes.docx"); doc.save(src)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
w.go("acronyms"); app.processEvents()
ap = w.acronym_page


def scan():
    ap.scan([src])
    t0 = time.time()
    while ap.worker is not None and time.time() - t0 < 240:
        app.processEvents(); time.sleep(0.05)
    return ap.session


def acts(t):
    return [a.text() for a in APT.more_menu(ap, [t], run=False).actions()]


s = scan()
check("the scan offers each joined term once, whole", "QRXT/ZVBN" in s.results and "KLPD-MNBW" in s.results
      and "QRXT" not in s.results and "MNBW" not in s.results, sorted(s.results))
check("More on a joined term says These are separate terms", "These are separate terms" in acts("QRXT/ZVBN"), acts("QRXT/ZVBN"))
check("a term that is not joined has no such command", not [a for a in acts("KLPD") if "separate" in a or "one term" in a], acts("KLPD"))
places = sorted(s.results["QRXT/ZVBN"]["locations"])
got = APT.joined(ap, "QRXT/ZVBN", J.PIECES)
check("separate terms: the pieces take the joined term's places", got == ["QRXT", "ZVBN"] and "QRXT/ZVBN" not in s.results
      and sorted(s.results["QRXT"]["locations"]) == places and sorted(s.results["ZVBN"]["locations"]) == places, (got, sorted(s.results)))
check("the answer is kept with the effort", (s.rules_extra.get("joined") or {}).get("QRXT/ZVBN") == "pieces", s.rules_extra)
check("More on a piece says This is one term", "This is one term: QRXT/ZVBN" in acts("QRXT"), acts("QRXT"))
s = scan()
check("the next scan keeps the answer: the pieces, not the joined term", "QRXT/ZVBN" not in s.results and "QRXT" in s.results
      and "ZVBN" in s.results, sorted(s.results))
got = APT.joined(ap, "QRXT", J.WHOLE, "QRXT/ZVBN")
check("one term: the joined term is back with its places and the pieces leave", got == "QRXT/ZVBN" and "QRXT" not in s.results
      and "ZVBN" not in s.results and sorted(s.results["QRXT/ZVBN"]["locations"]) == places, (got, sorted(s.results)))
s = scan()
check("the next scan keeps that answer too", "QRXT/ZVBN" in s.results and "QRXT" not in s.results
      and (s.rules_extra.get("joined") or {}).get("QRXT/ZVBN") == "whole", sorted(s.results))
got = APT.joined(ap, "KLPD-MNBW", J.PIECES)
check("a piece that also stands alone keeps its own place and gains the joined term's",
      s.results["KLPD"]["count"] == 2 and "MNBW" in s.results and "KLPD-MNBW" not in s.results, s.results.get("KLPD"))
J.ANSWERS, J.KNOWN, J.HYPHEN_WHOLE = {}, set(), False
n = sum(checks)
print(f"QT JOINED 4308 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
w.close()
sys.exit(0 if n == len(checks) else 1)
