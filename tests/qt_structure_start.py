"""2.69.0 in Qt, offscreen: Read RFP asks how the response structure starts; Choose after reading opens Structure with
what the RFP prescribes (its volumes and the sections under them) and where each part came from; Apply sets it; RFP
headings from one document; Blank; in Assign, Copy RFP section puts an RFP section and its subsections under the target
and places its requirements; the card says why L or M is suggested and that the RFP need not use them; a SOW sentence
gets no suggestion."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import compliance as C, effort as E, setupdoc as SD, office_pdf as OP, outline_ops as O, rfpoutline as RO
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([])
theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION)
w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
rp = w.read_page
rp.refresh()
opts = [rp.start.itemData(i) for i in range(rp.start.count())]
check("Read RFP asks how the structure starts (no typed outline: choose after reading)", rp.start.isVisibleTo(rp)
      and opts == ["choose", "prescribed", "headings", "blank"] and rp.start.currentData() == "choose", opts)
rp.read(PDFS, os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx"), start="choose")
check("after reading: Structure, with nothing set yet", wait(lambda: w.review is not None and w.stack.currentWidget() is w.structure_page)
      and w.review.M.outline == [])
M = w.review.M
sp = w.structure_page
txt = sp.text.toPlainText()
check("it shows what the RFP prescribes: three volumes and the sections under them", "Volume I Technical" in txt
      and "Volume III Cost" in txt and "    1 Technical Approach" in txt, txt)
check("and where each part came from", sp.why.isVisibleTo(sp) and "L.3 Volume I - Technical" in sp.why.text(), sp.why.text()[:160])
n, lost = sp.apply()
check("Apply sets it, volumes and all", n == 7 and SD.volumes_of(M)[0] == "several" and len(SD.volumes_of(M)[2]) == 3, (n, SD.volumes_of(M)))
sp.doc.setCurrentIndex(sp.doc.findData("SOW.pdf")); sp.letter.setCurrentText("All headings")
sp.from_headings()
check("RFP headings from one document (the SOW)", sp.text.toPlainText().splitlines()[0] == "2.1 Design", sp.text.toPlainText()[:80])
sp.blank()
check("Blank empties it, and says how to build it in Assign", sp.text.toPlainText() == "" and "Copy RFP section" in sp.why.text())
sp.from_prescribed(); sp.apply()
# Assign: copy an RFP section in, with its subsections
w.go("assign"); app.processEvents()
pg = w.assign_page
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
a = by("The Offeror shall describe its technical approach")
pg.select(a["id"]); app.processEvents()
pg.do_req(); app.processEvents()
check("a requirement with no section yet", a["decision"] == "Keep" and not a.get("map"))
vols = SD.volumes_of(M)[2]
pg.pick_volume(vols[1]); pg.target = None
pg.select(a["id"]); app.processEvents()
made = pg.copy_rfp_section(with_subs=True)
check("Copy RFP section: L.3.1 under the volume being worked, titled as the RFP titles it", made and made[0] == "3 Technical Approach"
      and O.volumes_of_item(M, {"map": made[0], "id": "x"}) == [vols[1]], made)
check("its requirement with no section goes into it, and the RFP section maps to it", a["map"] == made[0] and RO.mapped(M, "L.3.1") == made[0])
pg.select(a["id"]); app.processEvents()
check("the card says why L is suggested, and that the RFP need not use L and M", "Section L numbering" in pg.lm_why.text()
      and "need not use them" in pg.lm_why.text(), pg.lm_why.text())
s = next(it for it in M.items if it.get("file") == "SOW.pdf" and "shall" in it["text"])
check("a SOW sentence gets no L or M suggestion", SD.lm_suggest(M, s) == "", SD.lm_why(M, s))
w.save_now()
M2 = C.Matrix(M.path).load()
check("sections made here keep their numbering when the matrix is reopened", any(o.get("auto") for o in M2.outline)
      and any(o.get("from") == "L.3.1" for o in M2.outline))
w.close()
n = sum(checks)
print(f"QT STRUCTURE START PASS ({n}/{len(checks)})" if n == len(checks) else f"QT STRUCTURE START FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
