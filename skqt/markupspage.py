"""Drafts > Reviewer markups (4.25.3; answer 2: "a second entry in Drafts for reviewer markups"). A reviewer marked up
a PDF of one of our drafts in Acrobat. Two ways to bring the marks into Word, both the same work Prepare for Redline
does for a customer's document (redlineprep): a Word file made from the PDF with each mark where it was made, or the
marks put into a dated copy of the Word file the draft was printed from. Nothing is added to Documents: a draft of
ours is not a customer document. Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

import diag
from . import design as D
from .commandbar import CommandBar


class MarkupsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.bar.primary("Put a PDF's comments into my Word file...", lambda: self.into_word(),
                         "Pick the reviewer's PDF, then the Word file it was printed from. The comments go into a dated copy "
                         "of your file, as tracked changes and Word comments. Your file is not changed.")
        self.bar.add("Make a Word file from the PDF...", lambda: self.from_pdf(),
                     "When you do not have the Word file: a Word file that reads like the PDF, with each comment where it was made")
        v.addWidget(self.bar)
        self.card = D.Card("A reviewer's markups on one of our drafts",
                           "A reviewer returned a PDF of a draft with cross-outs, inserts, highlights and notes made in Acrobat. "
                           "Each cross-out, insert and replacement becomes a tracked change; each highlight and note becomes a "
                           "Word comment; replies stay threaded.")
        self.last = self.card.add(D.label("Nothing brought in yet.", "muted")); self.last.setWordWrap(True)
        v.addWidget(self.card); v.addStretch(1)

    def refresh(self):
        return None

    def _pdf(self, pdf):
        if pdf is None:
            pdf, _f = QFileDialog.getOpenFileName(self, "The reviewer's PDF", "", "PDF (*.pdf)")
        return pdf or ""

    def from_pdf(self, pdf=None):
        """A Word file beside the PDF, with its comments placed. Returns its path, or None."""
        pdf = self._pdf(pdf)
        if not pdf:
            return None
        out = self.host.redline_page.prepare(path=pdf)
        if out:
            self.last.setText(f"Made {os.path.basename(out)} beside the PDF, in {os.path.dirname(out)}.")
            diag.activity("qt_markups_from_pdf")
        return out

    def into_word(self, pdf=None, docx=None):
        """The PDF's comments into a dated copy of the Word file, beside that file. Returns redlineprep's result, or None."""
        import redlineprep as RP
        pdf = self._pdf(pdf)
        if not pdf:
            return None
        if docx is None:
            docx, _f = QFileDialog.getOpenFileName(self, "The Word file the PDF was printed from", os.path.dirname(pdf), "Word (*.docx)")
            if not docx:
                return None
        try:
            res = RP.into_word(pdf, docx, os.path.dirname(docx), "")
        except ValueError as e:
            self.host.status(str(e))
            return None
        except PermissionError:
            self.host.status("Today's copy of that Word file is open in Word: close it, then try again.")
            return None
        if not res["comments"]:
            self.host.status("This PDF has no comments to put into a Word file.")
            self.last.setText(f"{os.path.basename(pdf)} has no comments.")
            return res
        pdf_w, got = res["words"]
        self.last.setText(f"{len(res['comments'])} comment(s) from {os.path.basename(pdf)} put into {os.path.basename(res['path'])}: "
                          f"{res['changes']} tracked change(s), {res['word_comments']} Word comment(s)"
                          + (f", {res['listed']} listed only" if res["listed"] else "")
                          + f". The Word file holds {got} of the PDF's {pdf_w} words.")
        self.host.toast(f"{len(res['comments'])} comment(s) put into a copy of {os.path.basename(docx)}")
        diag.activity("qt_markups_into_word", n=len(res["comments"]))
        return res
