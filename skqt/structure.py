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
import structstart as SS
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
        bar.addWidget(D.button("What the RFP prescribes", None, self.from_prescribed,
                               "The volumes and sections the RFP spells out (Volume II - Management, \"shall be organized as "
                               "follows:\"), whether or not it uses Sections L and M"))
        self.letter = QComboBox(); self.letter.addItems(["All headings", "Section L", "Section M", "Section C"])
        bar.addWidget(self.letter)
        self.doc = QComboBox(); self.doc.setMinimumWidth(180); self.doc.setToolTip("Headings from one document, or all")
        bar.addWidget(self.doc)
        bar.addWidget(D.button("RFP headings", None, self.from_headings, "The RFP's numbered headings (one section letter or all, one document or all)"))
        bar.addWidget(D.button("RFP outline", None, self.from_rfp_outline, "The RFP's own outline (the headers marked in Review)"))
        bar.addWidget(D.button("Word outline...", None, self.from_word, "Heading 1-6 paragraphs of a Word document"))
        bar.addWidget(D.button("Blank", None, self.blank, "Start with no sections: build them in Review as you read"))
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
        self.why = D.label("", "muted"); self.why.hide()
        v.insertWidget(2, self.why)
        self.preview_timer = QTimer(self, singleShot=True, interval=300, timeout=self.preview)

    def refresh(self):
        R = self.host.review
        self.setEnabled(R is not None)
        self.text.blockSignals(True)
        self.text.setPlainText(C.outline_text(R.M.outline) if R and R.M.outline else "")
        self.text.blockSignals(False)
        self.why.hide()
        keep = self.doc.currentData()
        self.doc.clear(); self.doc.addItem("All documents", "")
        for f in (SS.files_with_headings(R.M) if R else []):
            self.doc.addItem(f, f)
        self.doc.setCurrentIndex(max(0, self.doc.findData(keep)))
        self.preview()

    def set_text(self, ol, what):
        if not ol:
            self.host.status(f"No {what} to start from.")
            return False
        self.text.setPlainText(C.outline_text(ol))
        self.preview()
        self.host.status(f"{len(ol)} sections from {what}. Edit them, then Apply.")
        return True

    def from_prescribed(self):
        """2.69.0: what the RFP spells out, with where each part came from."""
        ol, why = SS.prescribed(self.host.review.M)
        diag.activity("compliance_outline_prescribed", n=len(ol))
        if ol:
            self.why.setText("From the RFP: " + "; ".join(w.strip() for w in why) + ". Edit it, then Apply.")
            self.why.show()
        return self.set_text(ol, "what the RFP prescribes (it names no volumes or organized list that rules can find)"
                             if not ol else "what the RFP prescribes")

    def blank(self):
        self.text.setPlainText("")
        self.why.setText("A blank structure: Apply, then build it in Review (+ Volume, + Heading, + Subheading, From "
                         "sentence, Copy RFP section) as you read.")
        self.why.show()
        self.preview()
        return True

    def offer_start(self):
        """2.69.0: a new matrix with no structure: show what the RFP prescribes (else its headings) to start from."""
        self.why.show()
        if self.from_prescribed():
            return "prescribed"
        self.letter.setCurrentText("All headings")
        if self.from_headings():
            self.why.setText("The RFP does not spell out a response structure that rules can find. These are its headings: "
                             "edit them and Apply, or press Blank and build the structure in Review as you read.")
            self.why.show()
            return "headings"
        self.blank()
        return "blank"

    def from_headings(self):
        letter = {"Section L": "L", "Section M": "M", "Section C": "C"}.get(self.letter.currentText(), "All")
        files = [self.doc.currentData()] if self.doc.currentData() else None
        ol = SS.from_headings(self.host.review.M, letter, files)
        diag.activity("compliance_outline_rfp", items=len(ol))
        return self.set_text(ol, f"the numbered headings ({self.letter.currentText()})")

    def from_rfp_outline(self):
        self.host.review.snap()
        ol = STR.from_rfp_outline(self.host.review.M)
        diag.activity("compliance_outline_from_rfp_outline", n=len(ol))
        return self.set_text(ol, "the RFP outline (press H on header lines in Review to mark them)")

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
