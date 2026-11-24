"""Setup's preview (4.64.0; Nicholas 2026-11-23: Setup "should be a preview of the items in the shred exactly as it
will be in the word export ... preview the doc with the text in their styles"; 22:21 "Yes to the slim list"). What
Setup opens on: a slim list of the volume's headings on the left, and on the right the volume as it will be written,
each piece of text in its kind's look with its style's name after it. Click a heading to go to it. Nothing here is
edited: the pieces come from Shred, the headings from Outline, the order from Order under each heading. The drawing is
the app's (setuppreview); Word's own pages are More > Exact preview in Word. The page's switch shows Sections (who
writes each and when) instead."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QListWidget, QListWidgetItem, QSplitter, QTextBrowser,
                               QVBoxLayout, QWidget)

import diag
import setuporder as SO
import setuppreview as SP
from . import design as D

START = "preview"          # what Setup opens on; a test of the sections view sets "sections"


class PreviewPane(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.vols, self.bl, self.opts = [], [], {}
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.volume = QComboBox(); self.volume.setMinimumWidth(220)
        self.volume.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.volume)
        self.said = D.label("", "muted"); top.addWidget(self.said, 1)
        self.names = QCheckBox("Style names"); self.names.setChecked(True)
        self.names.setToolTip("After each piece of text, the name of the style it is written in")
        self.names.toggled.connect(lambda _on: self.draw())
        top.addWidget(self.names)
        split = QSplitter(Qt.Horizontal); v.addWidget(split, 1)
        self.heads = QListWidget(); self.heads.setMinimumWidth(170)
        self.heads.currentRowChanged.connect(self.goto)
        split.addWidget(self.heads)
        self.view = QTextBrowser(); self.view.setOpenLinks(False)
        split.addWidget(self.view)
        split.setStretchFactor(0, 0); split.setStretchFactor(1, 1); split.setSizes([240, 900])

    # ------------------------------------------------------------------ filling
    def refresh(self):
        """The volumes, then the one showing. Returns how many blocks are drawn."""
        pg = self.page
        M = pg._M()
        keep = self.volume.currentText()
        self.vols = []
        if M is not None and M.outline:
            try:
                info = pg.host.efforts.get(pg.host.effort_name) or {}
                self.vols = SP.volumes(M, pg.host.config_dir, pg.host.ws, pg.host.effort_name or "", info)
            except Exception:  # noqa: BLE001
                diag.swallowed()
        self.volume.blockSignals(True)
        self.volume.clear()
        for vname, _e, _s in self.vols:
            self.volume.addItem(vname or "The response")
        if keep and self.volume.findText(keep) >= 0:
            self.volume.setCurrentIndex(self.volume.findText(keep))
        self.volume.blockSignals(False)
        self.volume.setVisible(len(self.vols) > 1)
        return self.fill()

    def fill(self):
        pg = self.page
        M = pg._M()
        i = self.volume.currentIndex()
        self.bl, self.opts = [], {}
        if M is not None and 0 <= i < len(self.vols):
            vname, entries, std = self.vols[i]
            try:
                info = pg.host.efforts.get(pg.host.effort_name) or {}
                ctx = None
                if pg.host.ws is not None:
                    import ctxdocs as CX
                    ctx = CX.section_context(pg.host.ws.root)
                self.opts, self.bl = SP.blocks(M, vname, entries, std, pg.host.config_dir, pg.host.ws, info, ctx)
            except Exception:  # noqa: BLE001
                diag.swallowed()
                self.bl, self.opts = [], {}
        self.heads.blockSignals(True)
        self.heads.clear()
        self.rows = SP.headings(self.bl)
        base = min((lv for _i, lv, _t in self.rows), default=1)
        for _i, lv, text in self.rows:
            it = QListWidgetItem("    " * max(0, lv - base) + text); it.setToolTip(text)
            self.heads.addItem(it)
        self.heads.blockSignals(False)
        n = SP.counts(self.bl)
        S = getattr(M, "setup", None) or {} if M is not None else {}
        order = "in the order you set" if SO.order_for(S, "") else "in the usual order"
        self.said.setText((f"{len(self.rows)} heading(s), {sum(n.values())} piece(s) of text, {order}. As Make the setup will write it; "
                           "Word's own pages are More > Exact preview in Word.") if self.bl else
                          "Nothing to show yet: the setup is made from the outline and the pieces placed in Shred.")
        self.draw()
        return len(self.bl)

    def draw(self):
        at = self.view.verticalScrollBar().value()
        self.view.setHtml(SP.html(self.opts, self.bl, self.names.isChecked()) if self.bl else "")
        self.view.verticalScrollBar().setValue(at)

    def goto(self, row):
        if 0 <= row < len(getattr(self, "rows", [])):
            self.view.scrollToAnchor(f"h{self.rows[row][0]}")
            return self.rows[row][2]
        return None


def install(page, v, at):
    """The switch and the preview, put into the Setup page's layout at index at. Returns the pane."""
    row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
    page.view_btns = {}
    for key, text, tip in (("preview", "Preview", "The volume as it will be written, each piece in its style"),
                           ("sections", "Sections", "The sections: who writes each and when, and what is placed in it")):
        b = D.button(text, None, None, tip); b.setCheckable(True)
        b.clicked.connect(lambda _c=False, k=key: page.show_view(k))
        row.addWidget(b); page.view_btns[key] = b
    row.addStretch(1)
    page.view_row = QWidget(); page.view_row.setLayout(row); row.setContentsMargins(0, 0, 0, 0)
    v.insertWidget(at, page.view_row)
    page.preview_pane = PreviewPane(page)
    v.insertWidget(at + 1, page.preview_pane, 1)
    page.view = START
    return page.preview_pane


def apply(page, has, texting):
    """Which of the two is showing. Called by the Setup page's refresh. Returns the view."""
    view = page.view if has and not texting else "sections"
    page.view_row.setVisible(has and not texting)
    for k, b in page.view_btns.items():
        b.setChecked(k == view)
    page.preview_pane.setVisible(has and view == "preview")
    page.builder.setVisible((has or texting) and view == "sections")
    for x in (page.p_lead, page.p_due, page.fills):          # who writes what and what fills a section are the Sections view's
        x.setVisible(view == "sections")
    if has and view == "preview":
        page.preview_pane.refresh()
    return view
