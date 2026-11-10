"""Setup from a workbook's two panes (3.92.2; claude/stationkeeper-setup-tweaks-3.92.2.md): the clicks people expect.

LeftView   the workbook. A left click selects a column's tag or a piece of text (Ctrl or Shift adds to the selection);
           a right click opens the menu for what is selected; a column's tag dragged onto another tag takes its place
           in the order (every section).
PageList   the page Word gets, one block per paragraph, drawn in its styles' looks. A left click selects a paragraph;
           a right click opens its menu; a paragraph dragged above or below another moves its kind of text there,
           for every section or that section only (asked on the drop).
The page (skqt/workbookpage.py) holds what each gesture does."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QAbstractItemView, QLabel, QListWidget, QListWidgetItem, QTextBrowser


class LeftView(QTextBrowser):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setOpenLinks(False); self.setOpenExternalLinks(False)
        self.setStyleSheet("QTextBrowser{background:#FFFFFF;color:#000000}")
        self._press = None

    def mousePressEvent(self, e):
        href = self.anchorAt(e.position().toPoint())
        if e.button() == Qt.LeftButton and href:
            self._press = href
            self._at = e.position().toPoint()
            if href.startswith("tag:"):
                self.viewport().setCursor(Qt.ClosedHandCursor)
                e.accept()
                return
            super().mousePressEvent(e)                       # 3.97.1: text can be dragged over to select words
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        href = self.anchorAt(e.position().toPoint())
        start, self._press = self._press, None
        self.viewport().unsetCursor()
        moved = start and (e.position().toPoint() - getattr(self, "_at", e.position().toPoint())).manhattanLength() > 4
        if e.button() == Qt.LeftButton and start and start.startswith("run:") and moved and self.textCursor().hasSelection():
            super().mouseReleaseEvent(e)                     # words selected: right-click says what they are
            return
        if e.button() == Qt.LeftButton and start:
            add = bool(e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier))
            if start.startswith("tag:") and href.startswith("tag:") and href != start:
                self.page.drop_tag(int(start[4:]), int(href[4:]))
            else:
                self.page.pick(start, add=add)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def selected_words(self):
        """3.97.1: (the selected text, its column, its look, its workbook row) or None."""
        c = self.textCursor()
        text = " ".join(c.selectedText().replace("\u2029", " ").split())
        if not text:
            return None
        from PySide6.QtGui import QTextCursor
        at = QTextCursor(self.document()); at.setPosition(c.selectionStart() + 1)
        href = at.charFormat().anchorHref()
        tbl = at.currentTable()
        if not href.startswith("run:") or tbl is None:
            return None
        i, _, lk = href[4:].partition(":")
        r = tbl.cellAt(at).row() - 1
        rows = self.page.book["rows"]
        return (text, int(i), lk, rows[r]["row"]) if 0 <= r < len(rows) else None

    def contextMenuEvent(self, e):
        sw = self.selected_words()
        if sw is not None:
            self.page.words_menu(*sw)
            e.accept()
            return
        href = self.anchorAt(e.pos())
        if href:
            self.page.left_menu(href)
            e.accept()


class PageList(QListWidget):
    """One block per paragraph; the blocks are labels drawn by the page (block_html)."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setStyleSheet("QListWidget{background:#FFFFFF;color:#111111;border:1px solid #D3DBE6}"
                           "QListWidget::item{border:0;padding:0}"
                           "QListWidget::item:selected{background:#E2ECF8}")
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True); self.setAcceptDrops(True); self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setWordWrap(True)
        self.itemClicked.connect(lambda it: self.page.pick(f"para:{self.row(it)}"))

    def fill(self, blocks):
        """blocks: [(html, tooltip)] in page order."""
        keep = self.verticalScrollBar().value()
        self.clear()
        w = max(200, self.viewport().width() - 12)
        for html_, tip in blocks:
            it = QListWidgetItem(self)
            lab = QLabel(html_); lab.setWordWrap(True); lab.setTextFormat(Qt.RichText)
            lab.setAttribute(Qt.WA_TransparentForMouseEvents)
            lab.setContentsMargins(8, 3, 8, 3); lab.setFixedWidth(w)
            lab.adjustSize()
            it.setSizeHint(lab.sizeHint())
            it.setToolTip(tip)
            self.setItemWidget(it, lab)
        self.verticalScrollBar().setValue(keep)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = max(200, self.viewport().width() - 12)
        for i in range(self.count()):
            lab = self.itemWidget(self.item(i))
            if lab is not None and lab.width() != w:
                lab.setFixedWidth(w); lab.adjustSize(); self.item(i).setSizeHint(lab.sizeHint())

    def dropEvent(self, e):
        """The paragraph dropped above or below another: the page moves its kind of text; the list is drawn again."""
        src = self.currentRow()
        at = self.indexAt(e.position().toPoint())
        pos = self.dropIndicatorPosition()
        e.setDropAction(Qt.IgnoreAction); e.accept()          # the page redraws; nothing moves on its own
        if src < 0 or not at.isValid():
            return
        below = pos == QAbstractItemView.BelowItem
        self.page.drop_para(src, at.row(), below)

    def contextMenuEvent(self, e):
        it = self.itemAt(e.pos())
        if it is not None:
            self.setCurrentItem(it)
            self.page.right_click(f"para:{self.row(it)}")
            e.accept()

    # what the tests and Find read, as the old view gave it
    def toPlainText(self):
        return "\n".join(self.itemWidget(self.item(i)).text() and _plain(self.itemWidget(self.item(i)).text())
                         for i in range(self.count()))

    def toHtml(self):
        return "\n".join(self.itemWidget(self.item(i)).text() for i in range(self.count()))


def _plain(h):
    from PySide6.QtGui import QTextDocument
    d = QTextDocument(); d.setHtml(h)
    return d.toPlainText()


def ask_scope(parent, section):
    """Every section or this section only, asked where the paragraph was dropped. Returns "every", "one" or None."""
    from PySide6.QtWidgets import QMenu
    m = QMenu(parent)
    m.addSection("Move it in")
    a = m.addAction("Every section"); a.setData("every")
    b = m.addAction(f"{section or 'This section'} only"); b.setData("one")
    got = m.exec(QCursor.pos())
    return got.data() if got is not None else None
