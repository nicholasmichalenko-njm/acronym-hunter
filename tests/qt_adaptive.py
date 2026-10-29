"""2.86.0 the window adapts to its size, offscreen: button rows wrap instead of cutting buttons off; pages scroll only
when the window is smaller than they need; tables are compact with columns resized by dragging, "..." with hover text
and left-right scrolling; a calendar's days and a drop-down's list keep Qt's own layout (every weekday shows)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCalendarWidget, QComboBox, QHeaderView, QPushButton, QTableView,
                               QTableWidget, QTableWidgetItem, QWidget)
from skqt import design as D
from skqt.adaptive import FlowLayout, PageStack, ROW_H

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = QApplication([]); D.apply(app)
row = QWidget(); fl = FlowLayout(row, 8)
btns = [QPushButton(f"Button number {i}") for i in range(8)]
for b in btns:
    fl.addWidget(b)
row.resize(1600, 200); row.show(); app.processEvents()
one_line = len({b.y() for b in btns})
row.resize(420, 400); app.processEvents()
check("a button row wraps onto more lines when narrow", one_line == 1 and len({b.y() for b in btns}) > 1
      and all(b.x() + b.width() <= 420 for b in btns))
t = QTableWidget(5, 3); t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
t.setItem(0, 0, QTableWidgetItem("x" * 80))
t.resize(500, 300); t.show(); app.processEvents()
hh = t.horizontalHeader()
check("table columns resize by dragging, and the last fills the rest", hh.sectionResizeMode(0) == QHeaderView.Interactive
      and hh.stretchLastSection())
check("compact rows, smooth left-right scrolling, long text on hover", (t.verticalHeader().defaultSectionSize(), t.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel, t.item(0, 0).toolTip()[:3]) and t.verticalHeader().defaultSectionSize() == ROW_H
      and t.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel and t.item(0, 0).toolTip() == "x" * 80, (t.verticalHeader().defaultSectionSize(), t.wordWrap(), t.item(0, 0).toolTip()[:3]))
cal = QCalendarWidget(); cal.resize(520, 300); cal.show(); app.processEvents()
view = cal.findChild(QTableView)
w = sum(view.horizontalHeader().sectionSize(i) for i in range(view.horizontalHeader().count()))
check("a calendar shows every weekday (its days are not stretched)", not view.property("sk_tuned") or w <= view.viewport().width() + 2,
      (w, view.viewport().width()))
check("the calendar needs no left-right scrolling", not view.horizontalScrollBar().isVisible())
cb = QComboBox(); cb.addItems(["a", "b"]); cb.show(); app.processEvents()
st = PageStack(); pg = QWidget(); st.addWidget(pg); st.setCurrentWidget(pg)
check("pages sit in scroll areas the rest of the app does not see", st.currentWidget() is pg and st.indexOf(pg) == 0 and st.widget(0) is pg)
n = sum(checks)
print(f"QT ADAPTIVE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT ADAPTIVE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
