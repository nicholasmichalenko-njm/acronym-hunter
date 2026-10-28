"""Structure in Qt (2.60.0): the response structure, one section per line (indent with four spaces or number it),
started from the RFP's headings, the RFP outline or a Word outline; Apply sets it and keeps every assignment valid.
Beside it, the structure as it will be, with the requirements and context already in each section."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QPlainTextEdit, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)
import diag
import compliance as C
import structure_ops as STR
from . import design as D


class StructurePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        v.addWidget(D.label("The sections of your response. Sentences you assign go into these sections; the matrix and the "
                            "Response Setup follow this order.", "muted"))
        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"]); v.addLayout(bar)
        bar.addWidget(D.label("Start from:", wrap=False))
        self.letter = QComboBox(); self.letter.addItems(["Section L", "Section M", "Section C", "All headings"])
        bar.addWidget(self.letter)
        bar.addWidget(D.button("RFP headings", None, self.from_headings, "The RFP's numbered headings in that section"))
        bar.addWidget(D.button("RFP outline", None, self.from_rfp_outline, "The RFP's own outline (the headers marked in Assign)"))
        bar.addWidget(D.button("Word outline...", None, self.from_word, "Heading 1-6 paragraphs of a Word document"))
        bar.addStretch(1)
        bar.addWidget(D.button("Volumes...", None, lambda: self.host.assign_page.volumes_dialog()))
        bar.addWidget(D.button("People...", None, lambda: self.host.assign_page.people_dialog()))
        self.apply_btn = D.button("Apply", "primary", self.apply, "Set the structure (assignments to removed sections are cleared)")
        bar.addWidget(self.apply_btn)
        split = QSplitter(Qt.Horizontal)
        left = D.Card("Edit", "One section per line: 1.2 Management Approach, Volume I - Technical, or indent with 4 spaces.")
        self.text = QPlainTextEdit()
        self.text.setFont(QFont(D.MONO_FONT, 10))
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.textChanged.connect(lambda: self.preview_timer.start())
        left.add(self.text)
        right = D.Card("As it will be", "Requirements and context in each section now.")
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Section", "Req.", "Context"])
        self.tree.setColumnWidth(0, 360); self.tree.setAlternatingRowColors(True)
        right.add(self.tree)
        self.state = D.label("", "muted")
        right.add(self.state)
        split.addWidget(left); split.addWidget(right); split.setSizes([620, 560])
        v.addWidget(split, 1)
        self.preview_timer = QTimer(self, singleShot=True, interval=300, timeout=self.preview)

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        self.text.blockSignals(True)
        self.text.setPlainText(C.outline_text(R.M.outline) if R and R.M.outline else "")
        self.text.blockSignals(False)
        self.preview()

    def set_text(self, ol, what):
        if not ol:
            self.host.status(f"No {what} to start from.")
            return False
        self.text.setPlainText(C.outline_text(ol))
        self.preview()
        self.host.status(f"{len(ol)} sections from {what}. Edit them, then Apply.")
        return True

    def from_headings(self):
        letter = {"Section L": "L", "Section M": "M", "Section C": "C"}.get(self.letter.currentText(), "All")
        ol = STR.from_headings(self.host.review.M, letter)
        diag.activity("compliance_outline_rfp", items=len(ol))
        return self.set_text(ol, f"the numbered headings ({self.letter.currentText()})")

    def from_rfp_outline(self):
        self.host.review.snap()
        ol = STR.from_rfp_outline(self.host.review.M)
        diag.activity("compliance_outline_from_rfp_outline", n=len(ol))
        return self.set_text(ol, "the RFP outline (press H on header lines in Assign to mark them)")

    def from_word(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Word outline (headings become sections)", "", "Word (*.docx)")
            if not path:
                return False
        try:
            ol = STR.from_word(path)
        except Exception:
            diag.swallowed()
            self.host.status("The headings could not be read from that document.")
            return False
        diag.activity("compliance_outline_word", items=len(ol))
        return self.set_text(ol, "the Word outline")

    def apply(self):
        R = self.host.review
        if R is None:
            return None
        R.snap()
        n, lost = STR.apply(R.M, self.text.toPlainText())
        diag.activity("compliance_outline_applied", items=n, removed=lost)
        self.host.changed()
        self.host.assign_page.fill_tree()
        self.preview()
        self.host.toast(f"Structure set: {n} sections" + (f"; {lost} assignments to removed sections cleared" if lost else ""))
        return n, lost

    def preview(self):
        self.tree.clear()
        R = self.host.review
        if R is None:
            return
        ol = C.parse_outline(self.text.toPlainText())
        counts = STR.section_counts(R.M)
        stack = []
        for o in ol:
            lab = C.outline_label(o)
            k, c = counts.get(lab, (0, 0))
            node = QTreeWidgetItem([lab, str(k or ""), str(c or "")])
            lvl = o.get("level", 1)
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            (stack[-1][1].addChild(node) if stack else self.tree.addTopLevelItem(node))
            stack.append((lvl, node))
        self.tree.expandAll()
        now = {C.outline_label(o) for o in R.M.outline}
        new = {C.outline_label(o) for o in ol}
        gone = [lab for lab in counts if lab not in new]
        changed = now != new
        self.state.setText(("Not applied yet. " if changed else "Applied. ")
                           + (f"Apply clears the assignments in {len(gone)} section(s) that are no longer in it." if gone else ""))
        self.apply_btn.setEnabled(changed)
