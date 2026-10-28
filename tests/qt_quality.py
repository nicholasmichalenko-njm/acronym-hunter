"""2.66.0 QA/QC, Keywords, Export all and Settings in Qt: a new effort from Settings; QA/QC checks a Word volume on a
worker thread with the classic window's rules (first use, missing, not approved, banned words), adds the missing terms
and records use in the effort list, exports the report and the lists; keywords added, kept, rejected, suggested and
exported; Export all writes every available part into one folder; the effort's folders and first-use rule; backups."""
import os, shutil, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
CDIR = os.path.join(tmp, "customer"); os.makedirs(CDIR)
shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx"), CDIR)
VDIR = os.path.join(tmp, "volumes"); os.makedirs(VDIR)
VOL = shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx"), VDIR)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("the rail: QA/QC, Keywords, Export all, Settings", all(k in w.step_btns for k in ("qa", "keywords", "exportall", "settings")))
# a new effort from Settings
w.go("settings"); app.processEvents()
sp = w.settings_page
LIST = os.path.join(tmp, "Osprey", "Osprey_Effort_List.xlsx")
name = sp.new_effort({"name": "Osprey", "path": LIST, "first_use": "volume", "customer_dir": CDIR, "volumes_dir": VDIR,
                      "client": "USSF SSC", "solicitation": "FA8810-26-R-0099", "internal_no": ""})
check("New effort creates the list and opens it", name == "Osprey" and os.path.isfile(LIST) and w.effort_name == "Osprey"
      and E.EffortList(LIST).load().client == "USSF SSC")
check("a second effort with the same name is refused", sp.new_effort({"name": "Osprey", "path": LIST}) is None)
w.go("settings"); app.processEvents()
sp.rule.setCurrentIndex(sp.rule.findData("submission")); sp.save_effort()
check("the first-use rule is saved for the effort", w.efforts.get("Osprey")["first_use"] == "submission"
      and E.EffortList(LIST).load().first_use == "submission")
check("backups: a folder, then off", sp.set_backup(os.path.join(tmp, "bk")) and A.load_settings().get("backup_dir") and sp.set_backup("") == "")
# QA/QC
w.go("qa"); app.processEvents()
qp = w.qa_page
check("no check yet: the page offers one", qp.empty.isVisibleTo(qp))
qp.check([VOL, os.path.join(tmp, "notes.pdf")])
t = time.time()
while qp.worker is not None and time.time() - t < 240:
    app.processEvents(); time.sleep(0.05)
s = w.acronym_page.session
r = s.volume_report
check("QA/QC ran on the Word file only and made the report", r and r["volumes"] == ["Kestrel_Technical_Volume.docx"] and qp.tabs.count() >= 5, r and r["summary"])
check("first use under the effort's rule (the whole submission)", r["summary"]["rule"] == "submission" and "First use" in qp.tabs.tabText(0))
check("the tiles count what is missing from the effort list", qp.tiles["missing"].value.text() == str(r["summary"]["missing"]) and r["summary"]["missing"] > 5)
check("the report is kept in the effort's session (the classic window reads it)", (W.Workspace(W.data_dir_for(LIST), "Osprey").load_session() or {}).get("volume_report"))
n = qp.add_missing()
check("Add missing to the effort list (Proposed)", n == r["summary"]["missing"] and len(E.EffortList(LIST).load().rows) == n)
check("Record in the effort list", qp.record() >= 0)
p = qp.export(os.path.join(tmp, "qa.xlsx")); made = qp.lists(os.path.join(tmp, "lists"))
check("export the report and the volume's acronym list", p and os.path.isfile(p) and made and made[0].endswith("_Acronym_List.docx"))
# keywords
w.go("keywords"); app.processEvents()
kp = w.keywords_page
kp.add("thermal margin", "Customer emphasis"); kp.add("integrated master schedule", "Shared language")
check("+ Keyword", kp.words == ["thermal margin", "integrated master schedule"] or set(kp.words) == {"thermal margin", "integrated master schedule"})
kp.set_status("Keep", ["thermal margin"]); kp.set_status("Reject", ["integrated master schedule"])
kws = {k["Keyword"]: k["Status"] for k in E.EffortList(LIST).load().keywords}
check("Keep and Reject are saved in the workbook", kws == {"thermal margin": "Keep", "integrated master schedule": "Reject"}, kws)
items = kp.suggest(wait=True)
check("Suggest keywords from the customer documents and our volume", items and kp.s_table.rowCount() == len(kp.sugg), len(items or []))
got = kp.add_suggested([0])
check("add a suggestion", got == 1 and len(E.EffortList(LIST).load().keywords) == 3)
pk = kp.export(os.path.join(tmp, "kw.xlsx"))
check("export for SharePoint (Keep only)", pk and os.path.isfile(pk))
# export all
w.go("exportall"); app.processEvents()
xp = w.exportall_page
av = xp.available()
check("Export all knows what is available", av["acronyms"][0] and av["qaqc"][0] and av["keywords"][0] and not av["matrix"][0], {k: v[0] for k, v in av.items()})
sub, files, problems = xp.export(os.path.join(tmp, "out"))
names = sorted(os.path.basename(f) for f in files)
check("Export all writes the parts into one dated folder", os.path.isdir(sub) and any("Effort_Status" in n for n in names)
      and any("QAQC_Report" in n for n in names) and any("Keywords" in n for n in names) and not problems, (names, problems))
w.close()
n = sum(checks)
print(f"QT QUALITY PASS ({n}/{len(checks)})" if n == len(checks) else f"QT QUALITY FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
