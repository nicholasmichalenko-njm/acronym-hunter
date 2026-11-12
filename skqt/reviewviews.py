"""Review's views beside the page (3.90.0, decision 13: the L/M Crosswalk and Coverage become views of Review's maps).

The lower right of Review shows one of three views of the same records, picked on the tabs above it:
    Our structure   the response structure and the section panel (as before)
    L to M          each Section L instruction with the Section M factors that evaluate it and the work it describes,
                    the gaps flagged (the crosswalk); a row shows its instruction's sentences on the page
    Coverage        every sentence of every file by decision, and the text check; a row opens its file on the page
The crosswalk and coverage widgets are the pages they were (crosswalkpage, prove), moved here: one home each.
go("crosswalk") and go("prove") open Review on their view. The lines between the page and Our structure show only
in Our structure. Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget, QTabBar, QVBoxLayout, QWidget

import diag

KEYS = (("structure", "Our structure"), ("lm", "L to M"), ("coverage", "Coverage"))
TIPS = {"structure": "The response structure and the target section's panel",
        "lm": "Each Section L instruction with the Section M factors that evaluate it, and the gaps (the L/M crosswalk)",
        "coverage": "Every piece of every file by decision, and the word-for-word text check"}


class ReviewViews(QWidget):
    def __init__(self, page, structure):
        super().__init__()
        self.pg = page
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
        self.tabs = QTabBar(); self.tabs.setDocumentMode(True); self.tabs.setExpanding(False)
        for k, t in KEYS:
            i = self.tabs.addTab(t)
            self.tabs.setTabToolTip(i, TIPS[k])
        self.tabs.currentChanged.connect(lambda i: self.show_view(KEYS[i][0]))
        v.addWidget(self.tabs)
        self.tabs.setVisible(False)                  # 3.96.0: See it as, in the header above the page, picks the view
        self.stack = QStackedWidget(); v.addWidget(self.stack, 1)
        self.stack.addWidget(structure)
        self.holders = {}
        for k in ("lm", "coverage"):
            h = QWidget(); hl = QVBoxLayout(h); hl.setContentsMargins(0, 0, 0, 0)
            self.stack.addWidget(h)
            self.holders[k] = h
        self.key = "structure"

    def widget_of(self, key):
        """The crosswalk or coverage widget, moved into its holder the first time it is shown."""
        host = self.pg.host
        w = {"lm": getattr(host, "crosswalk_page", None), "coverage": getattr(host, "prove_page", None)}.get(key)
        if w is None:
            return None
        h = self.holders[key]
        if w.parent() is not h:
            h.layout().addWidget(w)
            w.show()
            if key == "lm":
                w.table.itemSelectionChanged.connect(lambda: self.lm_row())
                from PySide6.QtWidgets import QSplitter
                for sp in w.findChildren(QSplitter):
                    sp.setOrientation(Qt.Vertical)           # the detail under the table: the view is narrow
                    sp.setSizes([320, 260])
            else:
                w.table.cellDoubleClicked.connect(lambda r, _c: self.open_file_row(r))
                w.table.setToolTip("Double-click a file to open it on the page")
        return w

    def show_view(self, key):
        key = key if key in dict(KEYS) else "structure"
        self.key = key
        st = getattr(self.pg.host, "stepper", None)          # 3.96.0: the header's See it as follows
        if st is not None and st.isVisibleTo(self.pg.host):
            st.show_for("assign")
        i = [k for k, _t in KEYS].index(key)
        if self.tabs.currentIndex() != i:
            self.tabs.blockSignals(True); self.tabs.setCurrentIndex(i); self.tabs.blockSignals(False)
        if key == "structure":
            self.stack.setCurrentIndex(0)
        else:
            w = self.widget_of(key)
            self.stack.setCurrentWidget(self.holders[key])
            if w is not None and hasattr(w, "refresh"):
                try:
                    w.refresh()
                except Exception:  # noqa: BLE001
                    diag.swallowed()
        try:
            self.pg.placer.gutter.update()
        except AttributeError:
            pass
        diag.activity("review_view")
        return key

    def current(self):
        return self.key

    # ------------------------------------------------------------ a row shows its place on the page
    def lm_row(self):
        w = self.pg.host.crosswalk_page
        num = w.current()
        return self.pg.show_heading(num) if num else None

    def open_file_row(self, r):
        w = self.pg.host.prove_page
        it = w.table.item(r, 0)
        f = it.text() if it is not None else ""
        if f and f != "Total":
            self.show_view("structure")
            self.pg.files.setCurrentText(f)
        return f
