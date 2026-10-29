"""2.85.0 the mouse wheel never changes a choice, offscreen: over a drop-down, a number box or a date box the wheel
scrolls the page instead; the value stays; an open drop-down still scrolls with the wheel."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QDateEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from skqt import design as D

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = QApplication([]); D.apply(app)
sa = QScrollArea(); sa.setWidgetResizable(True); sa.resize(400, 300)
inner = QWidget(); v = QVBoxLayout(inner)
combo = QComboBox(); combo.addItems(["Keep", "Context", "Customer", "Heading"]); combo.setCurrentIndex(0)
spin = QSpinBox(); spin.setValue(5)
date = QDateEdit()
d0 = date.date()
v.addWidget(combo); v.addWidget(spin); v.addWidget(date)
for _ in range(40):
    v.addWidget(QComboBox())
sa.setWidget(inner); sa.show(); app.processEvents()


def wheel(w, dy=-120):
    pos = QPointF(5, 5)
    ev = QWheelEvent(pos, QPointF(w.mapToGlobal(QPoint(5, 5))), QPoint(0, 0), QPoint(0, dy), Qt.NoButton, Qt.NoModifier,
                     Qt.NoScrollPhase, False)
    QApplication.sendEvent(w, ev)
    app.processEvents()


before = sa.verticalScrollBar().value()
for _ in range(3):
    wheel(combo)
check("the wheel over a drop-down does not change it", combo.currentIndex() == 0, combo.currentText())
check("the page scrolls instead", sa.verticalScrollBar().value() > before, (before, sa.verticalScrollBar().value()))
wheel(spin); wheel(date)
check("number and date boxes keep their values", spin.value() == 5 and date.date() == d0)
combo.showPopup(); app.processEvents()
check("an open drop-down list is left to the wheel", combo.view().isVisible())
combo.hidePopup()
combo.setCurrentIndex(2)
check("picking from the list still changes it", combo.currentText() == "Customer")
n = sum(checks)
print(f"QT NOWHEEL PASS ({n}/{len(checks)})" if n == len(checks) else f"QT NOWHEEL FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
