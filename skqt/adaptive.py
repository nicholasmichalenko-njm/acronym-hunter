"""The window adapts to its size (2.86.0): button rows wrap onto a second line instead of cutting buttons off; a page
scrolls only when the window is smaller than the page needs; every table and tree is compact, its columns resize by
dragging (double-click a column edge to fit it), long text ends in "..." with the full text on hover, and a table
wider than its space scrolls left and right. Nothing here changes what a page does."""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCalendarWidget, QComboBox, QFrame, QHeaderView, QLayout, QScrollArea, QStackedWidget, QTableWidget,
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
            if it.hasHeightForWidth():                # 3.20.3: wrapped text (a tile's caption) gets the height it needs
                hint = QSize(hint.width(), max(hint.height(), it.heightForWidth(hint.width())))
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
    setCurrentWidget(), indexOf() and widget() speak in pages, so the rest of the app does not see the scroll areas."""

    def addWidget(self, page):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setWidget(page)
        sa.page = page
        if getattr(page, "fixed_page", False):    # 3.20.3: a page that lays itself out in the window (Review): its toolbar
            sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)       # and panels stay put; its parts scroll inside
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
    """Every table and tree, when it first shows: columns resized by dragging (a column that filled the space keeps its
    width as a starting point; the last column fills what is left), "..." for text that does not fit with the full text
    on hover, and smooth scrolling left and right."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show and isinstance(obj, QAbstractItemView) and not obj.property("sk_tuned"):
            obj.setProperty("sk_tuned", True)
            if _inside_calendar(obj) or isinstance(obj.parentWidget(), QComboBox) or obj.objectName().startswith("qt_"):
                return False                                # a calendar's days and a drop-down's list keep Qt's own layout
            try:
                tune(obj)
            except Exception:
                pass
        return False


def _inside_calendar(w):
    p = w.parentWidget()
    while p is not None:
        if isinstance(p, (QCalendarWidget, QComboBox)):
            return True
        p = p.parentWidget()
    return False


def tune(view):
    view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    view.setTextElideMode(Qt.ElideRight)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    hh = view.header() if isinstance(view, QTreeView) else getattr(view, "horizontalHeader", lambda: None)()
    if hh is not None and hh.count() > 1:
        hh.setMinimumSectionSize(36)
        widths = [hh.sectionSize(i) for i in range(hh.count())]
        for i in range(hh.count()):
            mode = hh.sectionResizeMode(i)
            if mode == QHeaderView.Stretch:
                hh.setSectionResizeMode(i, QHeaderView.Interactive)
                hh.resizeSection(i, max(widths[i], 160))
            elif mode != QHeaderView.Interactive:
                hh.setSectionResizeMode(i, QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.setToolTip("Drag a column edge to resize it; double-click the edge to fit the column")
    if isinstance(view, QTableWidget):
        vh = view.verticalHeader()
        sized_to_text = vh.count() > 0 and vh.sectionResizeMode(0) == QHeaderView.ResizeToContents
        if not sized_to_text and not view.property("sk_rows_fixed"):     # 2.93.0: tables of pickers keep their row height
            vh.setDefaultSectionSize(ROW_H)                 # rows a table sizes to their text keep that size
        _hover_text(view)


def _hover_text(view):
    """The full text of a long cell on hover, without changing a cell's own tooltip. 4.30.3: only the cells that changed
    are looked at. It used to look at every cell of the table each time one cell was set, so filling a list of 2,500
    terms looked at hundreds of millions of cells and the window froze after every decision."""
    def cells(r0, r1, c0, c1):
        try:
            for r in range(max(0, r0), min(view.rowCount(), r1 + 1)):
                for c in range(max(0, c0), min(view.columnCount(), c1 + 1)):
                    it = view.item(r, c)
                    if it is not None and not it.toolTip() and len(it.text()) > 30:
                        it.setToolTip(it.text())
        except Exception:
            pass
    view.model().rowsInserted.connect(lambda _p, first, last: cells(first, last, 0, view.columnCount() - 1))
    view.model().dataChanged.connect(lambda a, b, *_r: cells(a.row(), b.row(), a.column(), b.column()))
    cells(0, view.rowCount() - 1, 0, view.columnCount() - 1)


def install(app):
    t = ViewTuner(app)
    app.installEventFilter(t)
    app._sk_tuner = t
    return t
