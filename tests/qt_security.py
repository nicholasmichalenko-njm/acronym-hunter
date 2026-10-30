"""2.97.0 security exactly as you see it, offscreen: the mode chip in the top bar (Offline, Connected, SCIF-ready) and
what it says about training; the effort's sensitivity decides whether training data may be kept; a document marked above
CUI stops Add documents, the Library and Read RFP with nothing copied; support files stop while an effort above CUI is
open; Send training data leaves out efforts with no sensitivity set; the Trainer refuses files marked above CUI and asks
the level of an unmarked one once; SCIF-ready needs SCIF-READY typed, seals both folders, stops logging, hides training
and support, reads documents at any marking, and cannot be switched back."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, effortrec as RR, branding as BR, office_pdf as OP, pdfmini, diag
import sensitivity as S, secure, workmode as WM, corrections as CO, docversions as DV
OP.available = lambda: False
CO.set_dir(os.path.join(tmp, "td"))
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow
from skqt import sensgate as SG, helpcenter as HC
from sensfiles import docx

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); CUST = os.path.join(EDIR, "Customer documents"); os.makedirs(CUST)
IN = os.path.join(tmp, "incoming"); os.makedirs(IN)
L_PDF = os.path.join(IN, "Section_L.pdf"); pdfmini.write(L_PDF, [["L.3 The Offeror shall describe its approach."]], size=9)
S_PDF = os.path.join(IN, "Annex S.pdf"); pdfmini.write(S_PDF, [["SECRET//NOFORN", "The Offeror shall support the mission.", "SECRET//NOFORN"]], size=9)
S_DOC = docx(os.path.join(IN, "Orbit annex.docx"), "The orbit is described here.", header="SECRET//NOFORN")
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=CUST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.seal_dirs = (os.path.join(tmp, "program"), os.path.join(tmp, "data"))


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
check("the chip: no mode chosen yet", w.mode_chip.text() == "Mode not set")
w.settings_page.mode.choose(WM.OFFLINE)
check("Offline: the chip says so", w.mode_chip.text() == "Offline" and "Offline" in w.windowTitle())
check("no sensitivity set: no training data, and the chip says why", secure.EFFORT_LEVEL == -1 and not A.corrections_on()
      and "sensitivity is not set" in w.mode_chip.toolTip(), w.mode_chip.toolTip())
BR.set_identity(RR.Record(w.ws.root), sensitivity="CUI"); w.apply_marking()
check("set to CUI: training data may be kept", secure.EFFORT_LEVEL == S.CUI and A.corrections_on() and "may be kept" in w.mode_chip.toolTip())
# the spill guard
w.go("docs"); app.processEvents()
got = w.docs_page.add([L_PDF, S_DOC], choices=[{}, {}])
check("Add documents: a file marked SECRET stops it, nothing copied", got is None and "Orbit annex.docx is marked SECRET" in (w.last_spill or "")
      and os.listdir(CUST) == [], os.listdir(CUST))
pg = w.library_page
w.go("library"); app.processEvents()
pg.add([S_PDF], choices={})
wait(lambda: pg.worker is None)
check("the Library: stopped, with what to do", pg.panel.state == "failed" and "above CUI" in pg.panel.title.text()
      and DV.Library(w.ws.p("documents")).load().all == [], pg.panel.title.text())
w.last_spill = ""
w.read_page.read([L_PDF, S_PDF], os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx"), identities="suggested")
wait(lambda: not w.read_page.running())
check("Read RFP: stopped, no matrix made", "Annex S.pdf is marked SECRET" in (w.last_spill or "") and w.review is None
      and "above CUI" in w.read_page.panel.title.text(), w.read_page.panel.title.text())
# support files and training
sp = os.path.join(tmp, "support.zip")
check("a support file for a CUI effort", HC.make_support_file(w, sp) is not None and os.path.isfile(sp))
secure.EFFORT_LEVEL = S.SECRET
check("none while an effort above CUI is open", HC.make_support_file(w, os.path.join(tmp, "s2.zip")) is None
      and not os.path.isfile(os.path.join(tmp, "s2.zip")))
w.refresh_level()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=os.path.join(tmp, "Heron", "Heron_Effort_List.xlsx"))
os.makedirs(os.path.join(tmp, "Heron")); Lh = E.EffortList(os.path.join(tmp, "Heron", "Heron_Effort_List.xlsx"), "Heron"); Lh.pending = True; Lh.save()
w.efforts = E.Registry(os.path.join(cfg, "efforts.json"))
w.settings_page.send_training(out=os.path.join(tmp, "t.sktrain"), acknowledged=True)
check("Send training data leaves out an effort with no sensitivity set", w.settings_page.tp_left_out == ["Heron"], w.settings_page.tp_left_out)
# the Trainer's gate
par = QWidget()
said = []
check("the Trainer refuses a file marked SECRET", not SG.training_gate(par, S_DOC, say=said.append) and "SECRET" in said[-1])
from PIL import Image
pic = os.path.join(IN, "chart.png"); Image.new("RGB", (80, 40), "white").save(pic)
pic2 = os.path.join(IN, "chart2.png"); Image.new("RGB", (90, 40), "white").save(pic2)
check("an unmarked picture: its level is asked (CUI) and it opens", SG.training_gate(par, pic, answer=S.CUI))
check("... the answer is kept for those file contents", SG.training_gate(par, pic, answer=-1))
check("declared above CUI: refused", not SG.training_gate(par, pic2, answer=S.CONF, say=said.append) and "above CUI" in said[-1])
check("words read in the Trainer marked above CUI are not kept", not SG.training_lines(["TOP SECRET//SCI", "orbit"], said.append))
# SCIF-ready
card = w.settings_page.mode
check("SCIF-ready needs SCIF-READY typed", card.choose(WM.SECURED, answer=("scif", True)) is False and not secure.ACTIVE
      and w.mode_chip.text() == "Offline")
os.makedirs(os.path.join(w.seal_dirs[1], "training_data")); open(os.path.join(w.seal_dirs[1], "training_data", "labels.txt"), "w").write("x")
check("typed: sealed in the program folder and the data folder", card.choose(WM.SECURED, answer=("SCIF-READY", True))
      and secure.ACTIVE and all(os.path.isfile(os.path.join(d, secure.SEAL)) for d in w.seal_dirs))
check("... the training data kept before is deleted, and logging stopped", not os.path.exists(os.path.join(w.seal_dirs[1], "training_data"))
      and diag.OFF and diag.LOG_DIR is None)
check("... the chip and the title say SCIF-ready", w.mode_chip.text() == "SCIF-ready" and "SCIF-ready" in w.windowTitle()
      and "no logs" in w.mode_chip.toolTip())
check("... the card is locked", not card.off.isEnabled() and not card.con.isEnabled() and not card.locked.isHidden()
      and "cannot be switched back" in card.locked.text())
card.choose(WM.OFFLINE)
check("it cannot be switched back", WM.get(A.load_settings()) == WM.SECURED and w.mode_chip.text() == "SCIF-ready" and secure.ACTIVE)
check("no support file, no training data, no Report misreading", HC.make_support_file(w, os.path.join(tmp, "s3.zip")) is None
      and w.settings_page.send_training(out=os.path.join(tmp, "t2.sktrain"), acknowledged=True) is None and not A.corrections_on())
w.go("docs"); app.processEvents()
got = w.docs_page.add([S_DOC], choices=[{}])
check("SCIF-ready reads a document at any marking", got and len(got) == 1 and os.listdir(CUST) == ["Orbit annex.docx"], os.listdir(CUST))
check("the Trainer keeps nothing in SCIF-ready", not SG.training_gate(par, pic, answer=S.GB))
if os.environ.get("SHOT_DIR"):
    w.go_mode(); app.processEvents()
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "security_scif.png"))
secure.ACTIVE = False
w.close_effort()
n = sum(checks)
print(f"QT SECURITY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
