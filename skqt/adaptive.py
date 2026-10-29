"""The window adapts to its size (2.86.0): button rows wrap onto a second line instead of cutting buttons off; a page
scrolls only when the window is smaller than the page needs; every table and tree is compact, its columns resize by
dragging (double-click a column edge to fit it), long text ends in "..." with the full text on hover, and a table
wider than its space scrolls left and right. Nothing here changes what a page does."""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView, QLayout, QScrollArea, QStackedWidget, QTableWidget,
                               QTreeView, QTreeWidget, QWidgetItem)


class FlowLayout(QLayout):
    """A row of controls that wraps onto the next line when the window is too narrow. addStretch is accepted (it ends a
    group: the next controls start after a wider gap) so a QHBoxLayout can be swapped for it."""

    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self._gap_after = set()
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    # the QHBoxLayout calls the pages use
    def addStretch(self, _n=0):
        if self._items:
            self._gap_after.add(len(self._items) - 1)

    def addSpacing(self, _n):
        self.addStretch()

    def insertWidget(self, i, w, *_a):
        self.addChildWidget(w)
        self._items.insert(max(0, min(i, len(self._items))), QWidgetItem(w))
        self.invalidate()

    def addWidget(self, w, *_a):
        super().addWidget(w)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        if 0 <= i < len(self._items):
            it = self._items.pop(i)
            self._gap_after = {g - 1 if g > i else g for g in self._gap_after if g != i}
            return it
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._lay(QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._lay(rect, False)

    def sizeHint(self):
        w = sum(it.sizeHint().width() for it in self._items if not it.isEmpty()) + self.spacing() * max(0, len(self._items) - 1)
        h = max((it.sizeHint().height() for it in self._items), default=0)
        return QSize(w, h)

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        return s

    def _lay(self, rect, test):
        x, y, line = rect.x(), rect.y(), 0
        sp = self.spacing()
        for k, it in enumerate(self._items):
            if it.isEmpty():
                continue
            hint = it.sizeHint()
            nx = x + hint.width()
            if nx > rect.right() + 1 and line > 0:
                x, y, line = rect.x(), y + line + sp, 0
                nx = x + hint.width()
            if not test:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x = nx + sp + (sp * 2 if k in self._gap_after else 0)
            line = max(line, hint.height())
        return y + line - rect.y()


class PageStack(QStackedWidget):
    """Pages sit in scroll areas that scroll only when the window is smaller than the page needs. currentWidget(),
    setCurrentWidget() and indexOf() speak in pages, so the rest of the app does not see the scroll areas."""

    def addWidget(self, page):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setWidget(page)
        sa.page = page
        return super().addWidget(sa)

    def _wrap(self, page):
        for i in range(self.count()):
            w = super().widget(i)
            if getattr(w, "page", None) is page:
                return w
        return page

    def currentWidget(self):
        w = super().currentWidget()
        return getattr(w, "page", w)

    def setCurrentWidget(self, page):
        super().setCurrentWidget(self._wrap(page))

    def indexOf(self, page):
        return super().indexOf(self._wrap(page))

    def widget(self, i):
        w = super().widget(i)
        return getattr(w, "page", w)


ROW_H = 24


class ViewTuner(QObject):
    """Every table and tree, when it first shows: compact rows, columns resized by dragging (a column that filled the
    space keeps its width as a starting point; the last column fills what is left), "..." for text that does not fit
    with the full text on hover, and smooth scrolling left and right."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show and isinstance(obj, QAbstractItemView) and not obj.property("sk_tuned"):
            obj.setProperty("sk_tuned", True)
            try:
                tune(obj)
            except Exception:
                pass
        return False


def tune(view):
    view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    view.setTextElideMode(Qt.ElideRight)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    hh = view.header() if isinstance(view, QTreeView) else getattr(view, "horizontalHeader", lambda: None)()
    if hh is not None:
        hh.setMinimumSectionSize(36)
        hh.setSectionsMovable(False)
        widths = [hh.sectionSize(i) for i in range(hh.count())]
        for i in range(hh.count()):
            if hh.sectionResizeMode(i) == QHeaderView.Stretch:
                hh.setSectionResizeMode(i, QHeaderView.Interactive)
                hh.resizeSection(i, max(widths[i], 160))
            elif hh.sectionResizeMode(i) not in (QHeaderView.Interactive,):
                hh.setSectionResizeMode(i, QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.setToolTip("Drag a column edge to resize it; double-click the edge to fit the column")
    if isinstance(view, QTableWidget):
        vh = view.verticalHeader()
        if not view.wordWrap() or vh.sectionResizeMode(0) != QHeaderView.ResizeToContents:
            vh.setDefaultSectionSize(ROW_H)
    if isinstance(view, (QTableWidget, QTreeWidget)):
        _hover_text(view)


def _hover_text(view):
    """The full text of a cut-off cell on hover, without changing what a cell's own tooltip says."""
    def fill(*_a):
        try:
            if isinstance(view, QTableWidget):
                for r in range(view.rowCount()):
                    for c in range(view.columnCount()):
                        it = view.item(r, c)
                        if it is not None and not it.toolTip() and len(it.text()) > 30:
                            it.setToolTip(it.text())
        except Exception:
            pass
    model = view.model()
    model.rowsInserted.connect(fill)
    model.dataChanged.connect(fill)
    fill()


def install(app):
    t = ViewTuner(app)
    app.installEventFilter(t)
    app._sk_tuner = t
    return t
