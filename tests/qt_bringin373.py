"""3.73.0 offscreen (decision 11): Setup > Bring in a file... and a drop on the page. A Word template picked before
there are sections waits with the effort and becomes the setup's template once there are sections; a Word document with
headings gives the sections; a dropped Excel workbook opens What's in your workbook; a file it does not read is said so
in plain words. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, setupmake as SM, templatesetup as TS
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
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
from _tmplfixture import team_template
import test_outline371 as T
M0 = SM.start(os.path.join(tmp, "scratch", "m.xlsx"), "Kestrel", "1 Technical Approach\n  1.1 Ground Segment")
team = team_template(M0, os.path.join(tmp, "made"), cfg, os.path.join(tmp, "Kestrel Team Template.dotx"))
import docx
doc = docx.Document(); doc.add_heading("1 Technical Approach", 1); doc.add_heading("1.1 Ground Segment Architecture", 2)
doc.add_heading("2 Management Approach", 1); word = os.path.join(tmp, "Kestrel Outline.docx"); doc.save(word)
xl = T.make_outline(os.path.join(tmp, "Kestrel Outline.xlsx"))
odd = os.path.join(tmp, "notes.txt"); open(odd, "w").write("Kestrel")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
from PySide6.QtWidgets import QLabel
check("no sections yet: the card says to drop or bring in a file, and the template can come first", w.review is None
      and pg.start_card.isVisibleTo(pg) and any("Drop a file" in x.text() and "before or after" in x.text() for x in pg.start_card.findChildren(QLabel)))
check("the page takes a dropped file", pg.acceptDrops())
did = pg.bring_in(team, accept=False); app.processEvents()
td = pg.template_dialog
check("a Word template brought in with no sections yet opens the template", did == "template" and td.path == team)
td.save(); td.close(); app.processEvents()
check("... and waits with the effort", TS.waiting(w.ws).get("*") and "once there are sections" in pg.tmpl.text(), pg.tmpl.text())
said = []
w.status = lambda m, *a, **k: said.append(m)
check("a file it does not read is said so in plain words", pg.bring_in(odd) is None and any("Excel" in m and "PDF" in m for m in said), said)
check("a Word document with headings gives the sections", pg.bring_in(word) == "sections"
      and "1.1 Ground Segment Architecture" in pg.heads.toPlainText(), pg.heads.toPlainText())
M = pg.use_headings(); app.processEvents()
check("once there are sections, the waiting template is the setup's", M is not None and TS.choice(M).get("*")
      and not TS.waiting(w.ws) and "Made on your template" in pg.tmpl.text(), (TS.choice(M), pg.tmpl.text()))
check("with sections, a Word document brought in is the template", pg.bring_in(word, accept=False) == "template")
pg.template_dialog.close()
mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(xl)])
ev = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
pg.dropEvent(ev); app.processEvents()
wp = getattr(pg, "workbook_page", None)              # 3.91.0: a workbook opens Setup from a workbook, on the page
check("a dropped Excel workbook opens Setup from a workbook", wp is not None and os.path.normpath(wp.path) == os.path.normpath(xl)
      and "Heading" in wp.left.toPlainText())
wp.close()

print(f"QT BRING IN 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
