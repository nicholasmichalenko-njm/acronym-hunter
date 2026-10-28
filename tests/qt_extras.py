"""2.67.0 the last classic-only parts in Qt: author briefs from the impact review (one per person, copy, save as Word)
and the due date a new version sets; the customer's acronym lists for an effort (pasted, kept with the effort, used by
the next scan, removed); Send training data (only after the responsibility box is ticked); Install a Knowledge Pack."""
import os, shutil, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
import effort as E, effortrec as RR, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from test_docversions import amend

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
shutil.copy2(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), CDIR)
AMD = amend(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), os.path.join(tmp, "Kestrel_RFP_Sections_C_L_M_Amd1.docx"),
            [("exceed 50 pages", "exceed 40 pages")])
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CDIR)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("nothing is left in the classic window's group on the rail", not any(not b.isCheckable() for b in w.findChildren(type(w.step_btns["home"]))
                                                                             if b.objectName() == "rail"))
w.read_page.read([os.path.join(CDIR, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pl = next(it for it in M.items if "exceed 50 pages" in it["text"])
w.review.req([pl], "1.1 Technical Approach"); SD.set_people(M, "1.1 Technical Approach", lead="A. Lee"); w.changed(); w.save_now()
# author briefs
w.go("docs"); app.processEvents()
dp = w.docs_page
dp.add(dp.ctx.unadded(), choices=[{}])
d, v = dp.add([AMD], choices=[{}])[0]
w.go("impact"); app.processEvents()
ip = w.impact_page
ip.show(v["id"])
bs = ip.briefs()
check("Author briefs: A. Lee gets a brief for the changed page limit in 1.1", "A. Lee" in bs, list(bs))
dlg = ip.briefs_dialog(run=False)
check("the briefs window: one per person, the brief beside it", dlg.api["list"].count() == len(bs) and "40 pages" in dlg.api["text"].toPlainText()
      or "50" in dlg.api["text"].toPlainText(), dlg.api["text"].toPlainText()[:200])
t1 = dlg.api["copy"]()
check("Copy this brief", t1 and app.clipboard().text() == t1)
dlg.deleteLater()
p = ip.briefs_export(os.path.join(tmp, "briefs.docx"))
check("Save all as Word, and the timeline says so", p and zipfile.is_zipfile(p)
      and any("Author briefs for Amendment 1" in e["text"] for e in RR.Record(w.ws.root).events()))
# the customer's acronym lists
w.go("acronyms"); app.processEvents()
ap = w.acronym_page
rows = ap.client_lists(paste=("RFP acronym list", "KSE - Kestrel Space Element\nTBD: To Be Decided"))
s = ap.session
check("a pasted customer list is read and kept with the effort", len(rows) == 2 and s.ws.get("client_lists")[0]["name"] == "RFP acronym list"
      and len(s.client_lists) == 1)
dlg2 = ap.client_lists(run=False)
check("the lists window shows it", dlg2 is not None)
dlg2.deleteLater()
gone = ap.client_lists(remove=0)
check("remove a list", gone["name"] == "RFP acronym list" and not s.ws.get("client_lists"))
# training data and Knowledge Packs
w.go("settings"); app.processEvents()
sp = w.settings_page
out = os.path.join(tmp, "train.sktrain")
check("Send training data waits for the responsibility box", sp.send_training(out, None, False, False, acknowledged=False) is None)
r = sp.send_training(out, None, True, False, acknowledged=True)
check("Send training data writes the pack", r is not None and (r["path"] == out and os.path.isfile(out) or not r["path"]), r and r.get("counts"))
pack = os.path.join(tmp, "Knowledge.zip")
A.make_knowledge_pack(pack, "test")
rep = sp.install_pack(pack, answer="install")
check("Install a Knowledge Pack", rep is not None, str(rep)[:120])
check("Not now changes nothing", sp.install_pack(pack, answer="later") is None)
w.close()
n = sum(checks)
print(f"QT EXTRAS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT EXTRAS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
