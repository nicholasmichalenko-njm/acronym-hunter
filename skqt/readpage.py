"""Read RFP in Qt (2.59.0): the effort's customer documents, ticked; Read starts the compliance matrix (or adds the
documents not read yet to the open one, keeping every decision). Reading runs in the background through
compliance_read, exactly as in the tkinter edition."""
import os, re
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget)
from . import design as D
import diag
import compliance_read as CR


class ReadWorker(QThread):
    done = Signal(object)

    def __init__(self, paths, chunks_of):
        super().__init__()
        self.paths, self.chunks_of = paths, chunks_of

    def run(self):
        try:
            self.done.emit(CR.read_files(self.paths, self.chunks_of))
        except Exception as ex:
            diag.swallowed()
            self.done.emit(ex)


def default_chunks(path):
    import app_gui
    return app_gui.rfp_chunks(path)


class ReadPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.worker = None
        self.chunks_of = default_chunks
        self.setObjectName("page")
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        v.setSpacing(D.SPACE["m"])
        self.info = D.label("", "muted"); v.addWidget(self.info)
        card = D.Card("Customer documents", "The latest version of each, from Customer Documents.")
        self.area = QScrollArea(); self.area.setWidgetResizable(True)
        self.inner = QWidget(); self.list = QVBoxLayout(self.inner); self.list.setAlignment(Qt.AlignTop)
        self.area.setWidget(self.inner)
        card.add(self.area)
        v.addWidget(card, 1)
        row = QHBoxLayout(); v.addLayout(row)
        self.add_btn = D.button("Add files...", None, self.pick, "Read files that are not in Customer Documents"); row.addWidget(self.add_btn)
        row.addStretch(1)
        self.go_btn = D.button("Go to Assign", None, lambda: self.host.go("assign")); row.addWidget(self.go_btn)
        self.read_btn = D.button("Read", "primary", self.read, "Read the ticked documents into the review"); row.addWidget(self.read_btn)
        self.boxes = []

    def refresh(self):
        while self.list.count():
            w = self.list.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        self.boxes = []
        R = self.host.review
        docs = CR.effort_docs(self.host.ws)
        if R is not None:
            left = CR.unread_docs(R.M, docs)
            c = R.M.counts()
            self.info.setText(f"The compliance matrix holds {len(R.M.items)} sentences from {len(R.M.sources)} file(s): "
                              f"{c['Keep']} compliance requirements, {c['Context']} context. "
                              + (f"{len(left)} customer document(s) are not in it yet: tick them and Read adds them (decisions are kept)."
                                 if left else "Every customer document of this effort is in it."))
            docs = left
        else:
            self.info.setText("The effort's customer documents (latest version of each). Tick the ones to read: instructions, "
                              "evaluation criteria, SOW, attachments. Read starts the compliance matrix.")
        for name, label, path in docs:
            cb = QCheckBox(f"{name}   ({label})   {os.path.basename(path)}"); cb.setChecked(True)
            cb.path = path
            self.list.addWidget(cb)
            self.boxes.append(cb)
        if not docs and R is None:
            self.list.addWidget(D.EmptyState("No customer documents yet", "Add the RFP files in Customer Documents: every "
                                             "version is kept, and new ones are compared.", "Go to Documents", lambda: self.host.go("docs")))
        self.go_btn.setEnabled(R is not None and bool(R.M.items))
        self.read_btn.setEnabled(bool(self.boxes))

    def pick(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "RFP documents", "", "RFP documents (*.docx *.pdf *.xlsx *.pptx)")
        for p in paths:
            cb = QCheckBox(os.path.basename(p)); cb.setChecked(True); cb.path = p
            self.list.addWidget(cb)
            self.boxes.append(cb)
        self.read_btn.setEnabled(bool(self.boxes))

    def chosen(self):
        return [cb.path for cb in self.boxes if cb.isChecked()]

    def read(self, paths=None, out=None):
        paths = paths or self.chosen()
        if not paths or self.worker is not None:
            return None
        if self.host.review is None:
            if out is None:
                ef = self.host.effort_name or "RFP"
                base = os.path.dirname(self.host.effort_path) if self.host.effort_path else os.path.expanduser("~")
                stem = re.sub(r"[^A-Za-z0-9_-]+", "_", ef)
                out, _ = QFileDialog.getSaveFileName(self, "Where should the compliance matrix live?",
                                                     os.path.join(base, f"{stem}_Compliance_Matrix.xlsx"), "Excel (*.xlsx)")
                if not out:
                    return None
        self._out = out
        self.read_btn.setEnabled(False)
        self.host.status(f"Reading {len(paths)} file(s)...")
        if self.host.review is None:
            diag.activity("compliance_new", files=len(paths))
        else:
            diag.activity("compliance_files_added", files=len(paths))
        self.worker = ReadWorker(paths, self.chunks_of)
        self.worker.done.connect(self.read_done)
        self.worker.start()
        return self.worker

    def read_done(self, res):
        self.worker = None
        if isinstance(res, Exception):
            self.host.status(f"A file could not be read ({type(res).__name__}).")
            self.refresh()
            return
        items, heads, src, empty = res
        if self.host.review is None:
            M = CR.new_matrix(self._out, items, heads, src, (self.host.ws.get("outline_text") or "") if self.host.ws else "")
            fixed = CR.complete(M)
            self.host.set_matrix(M, new=True)
            msg = f"{len(items)} sentences from {len(src)} file(s)."
        else:
            add = CR.add_read(self.host.review.M, items, heads, src)
            fixed = CR.complete(self.host.review.M)
            self.host.changed()
            msg = f"{len(add)} sentences added."
        if fixed:
            msg += f" {fixed} line(s) the reader did not split out were added in their place."
        if empty:
            msg += f" {len(empty)} file(s) have no typed text (scanned pages?)."
        diag.activity("compliance_read", files=len(src), items=len(items))
        self.host.status(msg + " " + CR.text_check_line(CR.text_check(self.host.review.M)))
        self.refresh()
        self.host.go("assign")
