"""4.28.1 offscreen: the style list (answer 22; Nicholas 2026-11-12 10:53). Every row has a preview box of one size,
beside the style, with the style drawn in it at its true size; a style too big is cut off and its real size is written
beside the box. The details lie across the width. A press anywhere on a row selects it, and a drag carries every
selected row to a set. Fictional styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QWidget
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, stylespage as SPG
from skqt.mainwin import MainWindow
import stylelib as SL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("styles"); app.processEvents()
sp = w.styles_page
sp.new_style(name="Body Text", look={"font": "Arial", "size": 11})
sp.new_style(name="Heading 1", look={"font": "Georgia", "size": 16, "bold": True, "color": "1F3864"})
sp.new_style(name="Cover Title", look={"font": "Arial", "size": 44, "bold": True})
sp.new_style(name="Table Note", look={"font": "Courier New", "size": 8, "italic": True, "hidden": True})
app.processEvents()
rows = sp.rows
name_of = {rows.item(i).data(Qt.UserRole): sp.lib.base_of(sp.lib.get(rows.item(i).data(Qt.UserRole))) for i in range(rows.count())}
row_of = {v: i for i, v in enumerate(name_of.values())}
boxes = {n: rows.itemWidget(rows.item(i)).findChild(SPG.PreviewBox) for n, i in row_of.items()}
check("four rows, each with a preview box", len(boxes) == 4 and all(b is not None for b in boxes.values()))
check("every box is the same size", {(b.width(), b.height()) for b in boxes.values()} == {SPG.BOX})
check("the style is drawn at its true size", [boxes[n].font_of().pointSizeF() for n in ("Body Text", "Heading 1", "Cover Title", "Table Note")] == [11.0, 16.0, 44.0, 8.0]
      and boxes["Heading 1"].font_of().bold() and boxes["Table Note"].font_of().italic())
check("a 44 pt style is cut off at the box's edge; an 11 pt one is not", boxes["Cover Title"].cut_off() and not boxes["Body Text"].cut_off()
      and not boxes["Heading 1"].cut_off())
sizes = {n: rows.itemWidget(rows.item(i)).findChild(QLabel, "styleSize").text() for n, i in row_of.items()}
check("the real size is written beside the box", sizes["Body Text"] == "11 pt" and sizes["Cover Title"] == "44 pt\ncut off" and sizes["Table Note"] == "8 pt", sizes)
check("a style with no size of its own says so", SPG.size_words({}) == "As its base")
pm = boxes["Cover Title"].grab()
img = pm.toImage()
dark = sum(1 for x in range(0, img.width(), 3) for y in range(0, img.height(), 3) if img.pixelColor(x, y).lightness() < 90)
check("the box draws the text on white (and a big one fills it)", dark > 40 and img.pixelColor(img.width() // 2, 1).lightness() > 150, dark)
rw = rows.itemWidget(rows.item(row_of["Body Text"]))
box, name = boxes["Body Text"], rw.findChildren(QLabel)[0]
check("the preview sits beside the style, before the details", name.mapTo(rw, QPoint(0, 0)).x() < box.mapTo(rw, QPoint(0, 0)).x()
      < rw.findChild(QLabel, "styleSize").mapTo(rw, QPoint(0, 0)).x())
det = [l for l in rw.findChildren(QLabel) if l.text() in ("Arial 11", "As its base", "black", "Based on Normal")]
xs = sorted(l.mapTo(rw, QPoint(0, 0)).x() for l in det)
check("the details lie across the width, each with a share of it", len(det) == 4 and xs[0] > box.mapTo(rw, QPoint(0, 0)).x() + SPG.BOX[0]
      and min(b - a for a, b in zip(xs, xs[1:])) >= 60 and xs[-1] > rw.width() * 0.75, (xs, rw.width()))
check("rows are one height, a big style no taller", len({rows.sizeHintForRow(i) for i in range(rows.count())}) == 1 and rows.sizeHintForRow(0) <= 90,
      [rows.sizeHintForRow(i) for i in range(rows.count())])
fl = next(l for l in det if l.text() == "Arial 11")
check("the font is named in itself", 'font-family:"Arial"' in fl.styleSheet(), fl.styleSheet())

# ---- a drag carries every selected row
loose = [c for c in rw.findChildren(QWidget) if not isinstance(c, QPushButton) and not c.findChildren(QPushButton)
         and not c.testAttribute(Qt.WA_TransparentForMouseEvents)]
check("a row's words do not take the mouse (a press lands on the row)", not loose, [type(c).__name__ for c in loose][:5])
got = []
SPG.Rows.startDrag = lambda self, _a: got.append(list(self.page.selected_ids()))
rows.clearSelection()
for n in ("Body Text", "Heading 1", "Table Note"):
    rows.item(row_of[n]).setSelected(True)
app.processEvents()
p = QPoint(SPG.NAME_W + 40, 20)
QTest.mousePress(rw, Qt.LeftButton, Qt.NoModifier, p); app.processEvents()
check("a press on a selected row keeps the others selected", len(sp.selected_ids()) == 3, len(sp.selected_ids()))
for d in (10, 30, 60):
    QTest.mouseMove(rw, p + QPoint(d, d)); app.processEvents()
QTest.mouseRelease(rw, Qt.LeftButton, Qt.NoModifier, p + QPoint(60, 60)); app.processEvents()
check("the drag starts with every selected style", got and len(got[0]) == 3 and set(got[0]) == {i for i, n in name_of.items() if n != "Cover Title"}, got)
rfp = sp.new_set(name="RFP volume")
md = QMimeData(); md.setData(SPG.MIME, ",".join(got[0] if got else []).encode())
ids = bytes(md.data(SPG.MIME)).decode().split(",")
sp.add_to_set(rfp["id"], ids); app.processEvents()
check("dropped on a set, all of them are in it", len(SL.get_set(sp.lib, rfp["id"])["items"]) == 3)
check("the set shows its count", "RFP volume" in sp.sets.item(1).text() and "3" in sp.sets.item(1).text(), sp.sets.item(1).text())
w.close()
n = sum(checks)
print(f"QT STYLES 4281 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
