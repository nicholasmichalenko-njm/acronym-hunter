"""The mouse wheel never changes a choice (2.85.0): over a drop-down, a number box, a date or a time box, or a slider,
the wheel scrolls the page (or the table the box sits in) instead of picking the next value. A value changes only when
the person opens the drop-down and picks, types, or uses the arrows. An open drop-down list still scrolls with the
wheel. Nothing else about the boxes changes."""
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox, QScrollBar


class NoWheel(QObject):
    def eventFilter(self, obj, ev):
        if ev.type() != QEvent.Wheel:
            return False
        if isinstance(obj, QScrollBar) or not isinstance(obj, (QComboBox, QAbstractSpinBox, QAbstractSlider)):
            return False
        if isinstance(obj, QComboBox) and obj.view().isVisible():
            return False                                   # the list is open: the wheel moves through it
        p = obj.parentWidget()
        while p is not None and not isinstance(p, QAbstractScrollArea):
            p = p.parentWidget()
        if p is not None:
            QApplication.sendEvent(p.viewport(), ev)       # scroll what the box sits in
        return True                                        # the box itself never sees the wheel


KINDS = (QComboBox, QAbstractSpinBox, QAbstractSlider)


def within(root, f=None):
    """4.59.3: put the filter on each drop-down, number box and slider under root that does not have it yet. The filter
    used to sit on the whole application, so every event of every object ran it (see adaptive.ViewTuner)."""
    f = f or getattr(QApplication.instance(), "_sk_nowheel", None)
    if f is None:
        return 0
    n = 0
    for kind in KINDS:
        for w in ([root] if isinstance(root, kind) else []) + root.findChildren(kind):
            if not w.property("sk_nowheel"):
                w.setProperty("sk_nowheel", True)
                w.installEventFilter(f)
                n += 1
    return n


def install(app):
    f = NoWheel(app)                                       # 4.59.3: no installEventFilter on the application
    app._sk_nowheel = f
    return f
