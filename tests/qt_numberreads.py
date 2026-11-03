"""3.24.1 Production Standards > Heading numbering and List numbering, offscreen: Number reads shows the number as it
will look (1.1.1, Section A, I.1), never Word's %1 codes; what you type goes back as Word's codes, the last number this
level's own; a level that skips one stays as it was until you change it; changing a level's format changes how every
level below it reads; a bullet stays a bullet."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import numtext as NT
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


fm = ["decimal", "decimal", "decimal"]
check("Word's codes show as the number looks", NT.show("%1.%2.%3", fm) == "1.1.1" and NT.show("Section %1", ["upperLetter"]) == "Section A"
      and NT.show("%1.%2", ["upperRoman", "decimal"]) == "I.1")
check("what you type goes back as Word's codes, the last number this level's own",
      NT.parse("1.1.1", 3) == "%1.%2.%3" and NT.parse("Section A", 1) == "Section %1" and NT.parse("a)", 2) == "%2)"
      and NT.parse("Appendix A-1", 2) == "Appendix %1-%2")
check("a bullet and typed codes stay as typed", NT.parse("•", 1) == "•" and NT.parse("%1.%2", 2) == "%1.%2")
check("a level that skips one stays as it was until it is changed", NT.keep_or_parse("1.1", "%1.%3", fm, 3) == "%1.%3"
      and NT.keep_or_parse("1.1.1", "%1.%3", fm, 3) == "%1.%2.%3")

cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
spec = sp.tables["heading_levels"]; t = spec["w"]
col = next(c for c, (f, _h, _k) in enumerate(spec["cols"]) if f == "text")
fcol = next(c for c, (f, _h, _k) in enumerate(spec["cols"]) if f == "fmt")
shown = [t.cellWidget(i, col).text() for i in range(t.rowCount())]
check("no Number reads cell shows a % code", t.rowCount() > 0 and not any("%" in s for s in shown), shown)
levels = (sp.work.get("heading_numbering") or {}).get("levels") or []
check("each cell shows its level's codes as the number looks",
      all(shown[i] == NT.show(levels[i].get("text") or "", [l.get("fmt") or "decimal" for l in levels]) for i in range(len(levels))), shown)
check("the header names the column plainly", spec["w"].horizontalHeaderItem(col).text() == "Number reads")
# type a new text on level 2
c2 = t.cellWidget(1, col); c2.setText("Section 1.1"); c2.textEdited.emit("Section 1.1"); c2.editingFinished.emit(); app.processEvents()
lv = sp.work["heading_numbering"]["levels"]
check("typing 'Section 1.1' on level 2 keeps Word's 'Section %1.%2'", lv[1]["text"] == "Section %1.%2", lv[1])
# change level 1's format to I, II, III: level 2 reads I.1
e = t.cellWidget(0, fcol); e.setCurrentIndex(e.findData("upperRoman")); app.processEvents()
check("changing level 1 to I, II, III changes how level 2 reads", t.cellWidget(1, col).text() == "Section I.1"
      and sp.work["heading_numbering"]["levels"][1]["text"] == "Section %1.%2", t.cellWidget(1, col).text())
ls = sp.tables["listnum"]; lt = ls["w"]
lcol = next(c for c, (f, _h, _k) in enumerate(ls["cols"]) if f == "text")
check("List numbering shows no % code either", not any("%" in lt.cellWidget(i, lcol).text() for i in range(lt.rowCount())),
      [lt.cellWidget(i, lcol).text() for i in range(lt.rowCount())])
fcl = next(c for c, (f, _h, _k) in enumerate(ls["cols"]) if f == "fmt")
bi = next(i for i in range(lt.rowCount()) if lt.cellWidget(i, fcl).currentData() == "bullet" and i > 0)
cb = lt.cellWidget(bi, lcol); cb.setText("o"); cb.textEdited.emit("o"); cb.editingFinished.emit(); app.processEvents()
lv2 = [l for lst in sp.work["list_numbering"]["lists"] for l in lst["levels"]]
check("a bullet stays its character as typed (o is a bullet, not a number)", lv2[bi]["text"] == "o" and cb.text() == "o", lv2[bi])
# 3.32.1: a Symbol-font bullet (as Word stores it) shows as the bullet it is, not a box
sp.work["list_numbering"]["lists"][0]["levels"][0].update(text="\uf0b7", font="Symbol", fmt="bullet")
sp.load_tables(); app.processEvents()
lt = sp.tables["listnum"]["w"]
fcol2 = next(c for c, (f, _h, _k) in enumerate(ls["cols"]) if f == "font")
check("Word's Symbol bullet shows as a bullet, with no symbol font named", lt.cellWidget(0, lcol).text() == "\u2022"
      and lt.cellWidget(0, fcol2).text() == "", (lt.cellWidget(0, lcol).text(), lt.cellWidget(0, fcol2).text()))
w.close()
n = sum(checks)
print(f"NUMBER READS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
