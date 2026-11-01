"""3.9.0 Issues and ideas, offscreen: opened from the top bar on the page you are on (feature filled in); a report with
words from the open effort (its name, solicitation, a deliverable, a draft's file name, an acronym in its list, an
author's name) is not saved and the words to take out are shown; a clean report is saved with content-free context
(version, page, the last action names); edit, status and delete; Export makes a text-only zip and checks every report
again; SCIF-ready and an effort above CUI keep no reports."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import issuelog as IL
import effortfolders as EF
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey Lancer"); f.sol.setText("FA8810-26-R-0042"); f.client.setText("Space Systems Command")
f.create(); app.processEvents()
import authorlist as AL
al = AL.load(cfg); al.add("Dana Whitfield"); al.save()
vol = os.path.join(EF.folder(w.effort_path, "volumes"), "Kestrel Thermal Technical.docx")
shutil.copy2(os.path.join(HERE, "pefix", "data", "small.docx"), vol)
w.go("fixcopy"); app.processEvents()
check("an Issue or idea button in the top bar", w.issue_btn.isVisibleTo(w) and w.issue_btn.text() == "Issue or idea")
d = w.open_issues(run=False)
check("opened on the page you are on: the feature is filled in", d.feature.currentText() == "Fix a Copy" and d.page_key == "fixcopy")
for words, label in (("The Osprey Lancer effort fails", "effort name"), ("FA8810-26-R-0042 header is wrong", "solicitation"),
                     ("Kestrel Thermal Technical will not copy", "draft file name"), ("Dana Whitfield saw it", "author"),
                     ("Space Systems Command volume", "client")):
    d.type.setCurrentText("Bug"); d.title.setText("Copy step"); d.text.setPlainText(words)
    path = d.save()
    check(f"a report holding the {label} is not saved, and says what to take out", path is None and "Take these out" in d.msg.text(), d.msg.text())
check("nothing was kept", IL.reports() == [])
d.type.setCurrentText("Bug"); d.importance.setCurrentText("High")
d.title.setText("Make the fixed copy stops on a large volume")
d.text.setPlainText("Pressed Make the fixed copy with Update fields in Word on. The progress stayed at Updating fields for ten minutes.")
p1 = d.save()
items = IL.reports()
r = items[0][1] if items else {}
check("a clean report is saved with content-free context", p1 and len(items) == 1 and r["type"] == "Bug" and r["importance"] == "High"
      and r["context"]["page"] == "fixcopy" and r["context"]["version"] == A.APP_VERSION and "time" in r["context"]
      and isinstance(r["context"]["recent_actions"], list), r)
check("it is listed", d.table.rowCount() == 1 and d.table.item(0, 4).text().startswith("Make the fixed copy"))
d.type.setCurrentText("Idea"); d.feature.setCurrentText("Production Standards"); d.title.setText("Copy a profile from another")
d.text.setPlainText("A button to start a new profile from any existing one."); d.save()
d.table.selectRow(1 if d.table.item(0, 1).text() == "Idea" else 0)
d.edit_selected()
d.status.setCurrentText("Done"); d.save()
check("edit and mark done", sorted(x["status"] for _p, x in IL.reports()) == ["Done", "Open"] and len(IL.reports()) == 2)
z = os.path.join(tmp, "issues.zip")
n = d.export(z)
names = zipfile.ZipFile(z).namelist() if os.path.isfile(z) else []
md = zipfile.ZipFile(z).read("REPORT.md").decode() if names else ""
check("Export saves a text-only zip of every report", n == 2 and sorted(names) == ["REPORT.md", "reports.json"]
      and "Make the fixed copy stops" in md and "Copy a profile" in md, (n, names))
check("the export holds nothing from the effort", all(x not in md for x in ("Osprey", "Lancer", "FA8810", "Kestrel", "Whitfield")))
bad = os.path.join(IL.reports_dir(), "zz.json")
json.dump({"type": "Bug", "title": "Osprey Lancer note", "text": "", "context": {}}, open(bad, "w"))
z2 = os.path.join(tmp, "issues2.zip")
n2 = d.export(z2)
check("a report changed by hand to hold effort words stops the export", n2 == 0 and not os.path.exists(z2) and "Edit it first" in d.msg.text())
d.table.selectRow(0)
os.remove(bad); d.load()
d.table.selectRow(0); d.delete_selected()
check("delete a report", len(IL.reports()) == 1 and d.table.rowCount() == 1)
import secure, sensitivity as S
secure.EFFORT_LEVEL = S.CUI + 1
d2 = w.open_issues(run=False)
check("an effort above CUI: no reports kept, and it says so", "not kept" in d2.msg.text(), d2.msg.text())
secure.EFFORT_LEVEL = S.CUI
w.go("settings"); app.processEvents()
from skqt import helpcenter as HC
card = HC.support_card(w)
check("Settings help card offers Issues and ideas", any(b.text() == "Issues and ideas..." for b in card.findChildren(type(w.issue_btn))))
check("the shortcut is listed", any(k == "Ctrl+Shift+I" for _a, k, _t in HC.SHORTCUTS))
n = sum(checks)
print(f"QT ISSUES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
