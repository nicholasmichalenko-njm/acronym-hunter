"""3.72.0 offscreen: Setup > Use a template file... (what the template holds in order with page numbers and headers, the
body always in, the Quick Parts with ticks, the heading numbering, the setup styles it has or gets), Save keeps the
choice and a copy with the effort, Make the setup makes it on the template and keeps the check, the Setup page says
which template it uses, and Use the app's own template goes back. Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, compliance as C, templatesetup as TS
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
import test_outline371 as T
from _tmplfixture import team_template
xl = T.make_outline(os.path.join(tmp, "Kestrel Outline.xlsx"))
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
pg.from_outline(xl, accept=True)
M = w.review.M
team = team_template(M, os.path.join(tmp, "made"), cfg, os.path.join(tmp, "Kestrel Team Template.dotx"))
dlg = pg.template_file(path=team, modal=False); app.processEvents()
parts = [dlg.parts.item(r, 1).text() for r in range(dlg.parts.rowCount())]
check("what it holds, in order", parts == ["Cover page", "Front matter", "Body", "Appendix"], parts)
body_cb = dlg.parts.cellWidget(2, 0)
check("the body is always in; the cover and front matter start out (blank by default)", body_cb.isChecked() and not body_cb.isEnabled()
      and not dlg.parts.cellWidget(0, 0).isChecked() and not dlg.parts.cellWidget(1, 0).isChecked())
check("page numbers in words", "i, ii, iii" in dlg.parts.item(1, 3).text() and "by chapter" in dlg.parts.item(2, 3).text(),
      [dlg.parts.item(r, 3).text() for r in range(4)])
check("the Quick Parts, unticked", dlg.qps.count() == 2 and all(dlg.qps.item(r).checkState() == Qt.Unchecked for r in range(2))
      and "Cover Pages: Kestrel Cover" in dlg.qps.item(0).text() + dlg.qps.item(1).text())
check("the heading numbering", "Heading 1: numbered 1" in dlg.heads.text() and "Heading 2: numbered 1.1" in dlg.heads.text(), dlg.heads.text())
check("the setup styles it has or gets", dlg.styles.rowCount() >= 4 and any("added (Setup styles)" in dlg.styles.item(r, 1).text()
      or "used as it is" in dlg.styles.item(r, 1).text() for r in range(dlg.styles.rowCount())))
dlg.parts.cellWidget(1, 0).setChecked(True)                          # keep the front matter
for r in range(dlg.qps.count()):
    if "Kestrel Cover" in dlg.qps.item(r).text():
        dlg.qps.item(r).setCheckState(Qt.Checked)
dlg.parts.cellWidget(1, 4).setChecked(False)                         # the front matter without its header and footer
check("the picks", dlg.picks_now() == {"keep": [1], "quick_parts": ["Kestrel Cover"], "no_hf": [1]}, dlg.picks_now())
dlg.save(); dlg.close()
check("Save: the choice for every volume and a copy kept with the effort",
      TS.choice(M)["*"]["file"] == "Templates/Kestrel Team Template.dotx" and os.path.isfile(os.path.join(ED, "Templates", "Kestrel Team Template.dotx")))
pg.refresh(); app.processEvents()
check("the Setup page says which template it uses", "Made on your template" in pg.tmpl.text() and "Kestrel Team Template.dotx" in pg.tmpl.text(),
      pg.tmpl.text())
out = pg.make(folder=os.path.join(tmp, "exports"))
check("Make the setup: made on the template and checked, nothing to look at", out and len(out) == 1 and os.path.isfile(out[0]["setup"])
      and not TS.problems(out[0]["check"]) and pg.last_check is out, [r for r in (out[0]["check"] if out else []) if not r["ok"]])
doc = zipfile.ZipFile(out[0]["setup"]).read("word/document.xml").decode()
check("the picks are in the file", "KESTREL GROUND SEGMENT PROPOSAL" in doc and "Table of Contents" in doc and "Ground Segment Architecture" in doc)
from skqt.templatefileview import CheckView
cv = CheckView(pg, out)
check("the check view lists every row", cv.table.rowCount() == len(out[0]["check"]) and cv.table.item(0, 2).text() in ("OK", "Look at this"))
cv.close()
dlg2 = pg.template_file(modal=False); app.processEvents()
check("opened again: the saved template and picks", dlg2.path.endswith("Kestrel Team Template.dotx") and dlg2.parts.cellWidget(1, 0).isChecked())
dlg2.clear(); dlg2.close(); app.processEvents()
check("Use the app's own template: back to the template built from the formatting standards", not TS.choice(M) and "Made on your template" not in pg.tmpl.text())

print(f"QT TEMPLATE FILE 372 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
