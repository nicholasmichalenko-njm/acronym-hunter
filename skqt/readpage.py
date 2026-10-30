"""Read RFP in Qt (2.59.0): the effort's customer documents, ticked; Read starts the compliance matrix (or adds the
documents not read yet to the open one, keeping every decision). Reading runs in the background through
compliance_read, exactly as in the tkinter edition."""
import os, re
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                               QAbstractItemView, QVBoxLayout, QWidget)
from . import design as D
from .doctypeui import follow, type_box
from .progress import TaskPanel
import diag
import compliance_read as CR
import docversions as DV
import setupdoc as SD
import structstart as SS


class ReadWorker(QThread):
    """2.82.0: reports progress (fraction, text) and stops between files when asked."""
    done = Signal(object)
    progress = Signal(float, str)

    def __init__(self, paths, chunks_of, copies=""):
        super().__init__()
        self.paths, self.chunks_of, self.copies = paths, chunks_of, copies
        self.stop_asked = False
        self.abandoned = False                     # the effort closed: the result is thrown away

    def run(self):
        try:
            import ocrpdf
            res = CR.read_files(self.paths, self.chunks_of, progress=lambda f, t: self.progress.emit(float(f), t),
                                stop=lambda: self.stop_asked or self.abandoned,
                                page_copy=(lambda p, say: ocrpdf.page_copy(p, self.copies, say)) if self.copies else None)
        except Exception as ex:
            if not isinstance(ex, (CR.Stopped, CR.ReadFailed, CR.S.Spill)):
                diag.swallowed()
            res = ex
        self.done.emit(res)


class DocRow(QTreeWidgetItem):
    """2.82.0: one document in Read RFP's list: a tick, its initial, type, name, version and file; many can be selected
    and ticked together."""

    def __init__(self, tree, path, name, label, ident, role="matrix"):
        super().__init__(tree, [name, ident.get("initial", "") or "(needs one)", ident.get("type", "") or "(needs one)",
                                DV.ROLE_NAMES.get(role, ""), label, os.path.basename(path)])
        self.path = path
        self.dtype = ident.get("type", "")
        self.role = role
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(0, Qt.Checked if role == "matrix" else Qt.Unchecked)   # 2.83.0: the matrix documents ticked

    def isChecked(self):
        return self.checkState(0) == Qt.Checked

    def setChecked(self, on):
        self.setCheckState(0, Qt.Checked if on else Qt.Unchecked)

    def isEnabled(self):
        return not self.isDisabled()

    def setEnabled(self, on):
        self.setDisabled(not on)


_ORPHANS = []          # reads left running when their effort closed; kept until they end so Qt never loses them


def default_chunks(path, say=None):
    import app_gui
    return app_gui.rfp_chunks(path, say)


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
        self.panel = TaskPanel(self.stop, host); v.addWidget(self.panel)   # 2.82.0: running, how far, how it ended
        card = D.Card("Customer documents", "The latest version of each, from Customer Documents. Click, Shift+click or "
                      "Ctrl+click to select several; Space or a tick on a selected row ticks them all.")
        trow = QHBoxLayout(); trow.setSpacing(D.SPACE["s"]); card.body.addLayout(trow)     # 2.82.0: tick many at once
        self.tick_all = D.button("Tick all", None, lambda: self.tick(True), "Tick every document"); trow.addWidget(self.tick_all)
        self.tick_none = D.button("Untick all", None, lambda: self.tick(False), "Untick every document"); trow.addWidget(self.tick_none)
        self.tick_sel = D.button("Tick selected", None, lambda: self.tick(True, selected=True), "Tick the selected rows (Space)")
        trow.addWidget(self.tick_sel)
        self.untick_sel = D.button("Untick selected", None, lambda: self.tick(False, selected=True), "Untick the selected rows")
        trow.addWidget(self.untick_sel)
        self.only = QComboBox(); self.only.setToolTip("Tick only the documents of one type")
        self.only.activated.connect(lambda _i: self.tick_type(self.only.currentData()))
        trow.addWidget(self.only)
        trow.addStretch(1)
        self.count = D.label("", "muted", wrap=False); trow.addWidget(self.count)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Document", "Initial", "Type", "Role", "Version", "File"])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setRootIsDecorated(False); self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 340); self.tree.setColumnWidth(1, 90); self.tree.setColumnWidth(2, 110); self.tree.setColumnWidth(3, 110)
        self.tree.itemChanged.connect(self._ticked)
        self.tree.installEventFilter(self)
        card.add(self.tree)
        self.area = QScrollArea(); self.area.setWidgetResizable(True)
        self.inner = QWidget(); self.list = QVBoxLayout(self.inner); self.list.setAlignment(Qt.AlignTop)
        self.area.setWidget(self.inner); self.area.hide()
        card.add(self.area)
        v.addWidget(card, 1)
        srow = QHBoxLayout(); v.addLayout(srow)                     # 2.69.0: how the response structure starts
        self.start_lbl = D.label("Start the response structure from", "label", wrap=False); srow.addWidget(self.start_lbl)
        self.start = QComboBox(); self.start.setMinimumWidth(360); srow.addWidget(self.start)
        self.start.setToolTip("Choose after reading: Structure shows what the RFP prescribes and its headings to pick from. "
                              "Blank: build it in Review as you read.")
        srow.addStretch(1)
        row = QHBoxLayout(); v.addLayout(row)
        self.add_btn = D.button("Add files...", None, self.pick, "Read files that are not in Customer Documents"); row.addWidget(self.add_btn)
        row.addStretch(1)
        self.go_btn = D.button("Go to Review", None, lambda: self.host.go("assign")); row.addWidget(self.go_btn)
        self.read_btn = D.button("Read", "primary", self.read, "Read the ticked documents into the review"); row.addWidget(self.read_btn)
        self.boxes = []
        self._guard = False

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
            self.info.setText("The effort's customer documents (latest version of each). The ones whose role is Builds the matrix "
                              "are ticked (set roles in Library); tick any others to read into the matrix too. Read starts "
                              "the compliance matrix.")
        known = self.identities_known()
        lib = self.library()
        self._guard = True
        self.tree.clear()
        for name, label, path in docs:
            d = lib.doc_of_file(path) if lib is not None else None
            role = lib.role_of(d) if d is not None else "matrix"
            self.boxes.append(DocRow(self.tree, path, name, label, known.get(os.path.basename(path)) or {}, role))
        self._guard = False
        empty = not docs and R is None
        if empty:
            self.list.addWidget(D.EmptyState("No customer documents yet", "Add the RFP files in Library (Customer documents): every "
                                             "version is kept, and new ones are compared.", "Go to Library", lambda: self.host.go("library")))
        self.area.setVisible(empty); self.tree.setVisible(not empty)
        self.fill_only()
        self.show_count()
        self.fill_start()
        self.go_btn.setEnabled(R is not None and bool(R.M.items))
        self.lock_controls()

    def running(self):
        return self.worker is not None or getattr(self, "_busy", False)

    def lock_controls(self):
        """2.82.0: while a read runs, Read, Add files, the start choice and the ticks are locked, so a second read can
        never start and the files being read cannot change under it."""
        busy = self.running()
        self.read_btn.setEnabled(any(r.isChecked() for r in self.boxes) and not busy)
        self.read_btn.setText("Reading..." if busy else "Read")
        self.read_btn.setToolTip("Reading is running: wait for it or press Stop." if busy else "Read the ticked documents into the review")
        self.add_btn.setEnabled(not busy)
        self.start.setEnabled(not busy)
        for b in (self.tick_all, self.tick_none, self.tick_sel, self.untick_sel, self.only):
            b.setEnabled(not busy)
        for cb in self.boxes:
            cb.setEnabled(not busy)

    def stop(self):
        """Stop after the file being read now; nothing is written."""
        if self.worker is not None:
            self.worker.stop_asked = True
            diag.activity("compliance_read_stop_asked")

    def abandon(self):
        """The effort is closing while a read runs: stop it and throw the result away (it belongs to that effort)."""
        wk = self.worker
        if wk is None:
            return False
        wk.abandoned = True
        try:
            wk.done.disconnect(); wk.progress.disconnect()
        except (RuntimeError, TypeError):
            pass
        _ORPHANS.append(wk)
        wk.finished.connect(lambda wk=wk: _ORPHANS.remove(wk) if wk in _ORPHANS else None)
        self.worker = None; self._busy = False
        self.panel.stopped("Reading stopped", "The effort closed while it read. Nothing was written to the matrix.",
                           "Open the effort and press Read again.")
        diag.activity("compliance_read_abandoned")
        self.lock_controls()
        return True

    def confirm_stop(self, answer=None):
        """Before the effort or the window closes during a read. answer: True/False (tests). Returns True to go on."""
        if not self.running():
            return True
        if answer is None:
            if os.environ.get("AH_TEST"):
                answer = True
            else:
                from PySide6.QtWidgets import QMessageBox
                answer = QMessageBox.question(self, "Reading is running", "Reading the customer documents is still running.\n\n"
                                              "Stop it and go on? Nothing is written to the matrix; you can Read again later.",
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
        if answer:
            self.abandon()
        return bool(answer)

    START = (("choose", "Choose after reading (see what the RFP prescribes and its headings)"),
             ("prescribed", "What the RFP prescribes (volumes and sections it spells out)"),
             ("headings", "The RFP's headings"),
             ("typed", "The outline typed for this effort"),
             ("blank", "Blank: build it in Review as I read"))

    def fill_start(self):
        new = self.host.review is None
        self.start_lbl.setVisible(new); self.start.setVisible(new)
        if not new:
            return
        typed = bool((self.host.ws.get("outline_text") or "").strip()) if self.host.ws else False
        keep = self.start.currentData()
        self.start.clear()
        for key, text in self.START:
            if key == "typed" and not typed:
                continue
            self.start.addItem(text, key)
        want = keep or ("typed" if typed else "choose")
        self.start.setCurrentIndex(max(0, self.start.findData(want)))

    def _start_structure(self, M, choice):
        """Set the new matrix's starting structure. Returns a line for the status bar."""
        if choice in (None, "auto", "typed"):
            return ""
        if choice == "prescribed":
            ol, _why = SS.prescribed(M)
            SS.apply(M, ol)
            return (f"Structure: {len(ol)} sections the RFP prescribes." if ol else
                    "The RFP does not spell out a response structure that rules can find: the structure is blank.")
        if choice == "headings":
            ol = SS.from_headings(M, "L") or SS.from_headings(M, "All")
            SS.apply(M, ol)
            return f"Structure: {len(ol)} RFP headings."
        SS.apply(M, [])
        return "" if choice == "choose" else "Blank structure: build it beside the page in Review."

    def pick(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "RFP documents", "", "RFP documents (*.docx *.pdf *.xlsx *.pptx *.doc *.xls *.ppt *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.webp)")
        self._guard = True
        for p in paths:
            self.boxes.append(DocRow(self.tree, p, os.path.basename(p), "added here", {}))
        self._guard = False
        if paths:
            self.area.hide(); self.tree.show()
        self.fill_only(); self.show_count()
        self.lock_controls()

    # 2.82.0: ticking many at once
    def tick(self, on, selected=False):
        rows = [r for r in self.boxes if r.isSelected()] if selected else list(self.boxes)
        self._guard = True
        for r in rows:
            r.setChecked(on)
        self._guard = False
        self.show_count()
        return len(rows)

    def tick_type(self, dtype):
        if not dtype:
            return 0
        self._guard = True
        for r in self.boxes:
            r.setChecked(r.dtype == dtype)
        self._guard = False
        self.only.setCurrentIndex(0)
        self.show_count()
        return sum(r.isChecked() for r in self.boxes)

    def _ticked(self, item, col):
        """A tick on a selected row ticks (or unticks) every selected row."""
        if self._guard or col != 0 or not isinstance(item, DocRow):
            return
        if item.isSelected():
            on = item.isChecked()
            self._guard = True
            for r in self.boxes:
                if r.isSelected() and r is not item:
                    r.setChecked(on)
            self._guard = False
        self.show_count()

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is getattr(self, "tree", None) and ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Space and not self.running():
            sel = [r for r in self.boxes if r.isSelected()]
            if sel:
                self.tick(not all(r.isChecked() for r in sel), selected=True)
                return True
        return super().eventFilter(obj, ev)

    def fill_only(self):
        types = sorted({r.dtype for r in self.boxes if r.dtype})
        self.only.blockSignals(True)
        self.only.clear(); self.only.addItem("Tick only type...", "")
        for t in types:
            self.only.addItem(t, t)
        self.only.blockSignals(False)
        self.only.setVisible(len(types) > 1)

    def show_count(self):
        n = sum(r.isChecked() for r in self.boxes)
        self.count.setText(f"{n} of {len(self.boxes)} ticked" if self.boxes else "")
        if not self.running():
            self.read_btn.setEnabled(n > 0)

    def chosen(self):
        return [cb.path for cb in self.boxes if cb.isChecked()]

    # ------------------------------------------------------------ 2.68.0: every document has an initial and a type
    def library(self):
        return DV.Library(self.host.ws.p("documents")).load() if self.host.ws is not None else None

    def identities_known(self):
        """{file name: {"initial", "type"}} from Customer Documents and the open matrix."""
        out = dict(SD.docs_of(self.host.review.M)) if self.host.review is not None else {}
        lib = self.library()
        if lib is not None:
            for f, ident in lib.identity_map().items():
                if ident.get("initial") or f not in out:
                    out[f] = ident
        return out

    def unidentified(self, paths):
        known = self.identities_known()
        return [p for p in paths if not (known.get(os.path.basename(p)) or {}).get("initial")
                or not (known.get(os.path.basename(p)) or {}).get("type")]

    def suggest(self, paths):
        """[(path, initial, type)] suggested for files with none yet."""
        lib = self.library() or DV.Library(os.path.join(os.path.dirname(paths[0]), ".none"))
        taken = {i.get("initial") for i in self.identities_known().values() if i.get("initial")}
        out = []
        for p in paths:
            d = lib.doc_of_file(os.path.basename(p))
            dtype = (d or {}).get("type") or DV.guess_type(os.path.basename(p))
            ini = lib.suggest_initial(dtype, taken)
            taken.add(ini)
            out.append((p, ini, dtype))
        return out

    def ask_identity(self, sugg):
        """The person gives each file its initial and type. Returns {path: (initial, type)} or None (cancelled)."""
        dlg = QDialog(self); dlg.setWindowTitle("Initial and type for each document"); dlg.setMinimumWidth(720)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("Every customer document needs an initial and a type before it is read. The initial starts each "
                            "requirement's reference in the matrix (R-L-4.2.1), so sections with the same number in different "
                            "documents never get mixed up.", "muted"))
        t = QTableWidget(len(sugg), 3); t.setHorizontalHeaderLabels(["File", "Type", "Initial"])
        t.verticalHeader().setVisible(False); t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        t.setColumnWidth(1, 170); t.setColumnWidth(2, 90)
        rows = []
        lib = self.library() or DV.Library(os.path.join(os.path.dirname(sugg[0][0]), ".none")) if sugg else None
        for i, (p, ini, dtype) in enumerate(sugg):
            t.setItem(i, 0, QTableWidgetItem(os.path.basename(p)))
            e = QLineEdit(ini); e.setMaxLength(6)
            c = type_box(dtype)

            def sug(ty, me=e):                                     # 2.94.0: the initial follows the type until typed
                taken = {x[1].text().strip().upper() for x in rows if x[1] is not me} | \
                        {i2.get("initial") for i2 in self.identities_known().values() if i2.get("initial")}
                return lib.suggest_initial(ty, taken) if lib is not None else DV.TYPE_INITIAL.get(ty, "X")
            follow(e, c, sug)
            t.setCellWidget(i, 1, c); t.setCellWidget(i, 2, e)
            rows.append((p, e, c))
        v.addWidget(t)
        prob = D.label("", "crit"); prob.hide(); v.addWidget(prob)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Set and read")
        got = {}

        def ok():
            ans = {p: (e.text(), c.currentText()) for p, e, c in rows}
            why = self.identity_problems(ans)
            if why:
                prob.setText(" ".join(why)); prob.show()
                return
            got.update(ans)
            dlg.accept()
        bb.accepted.connect(ok); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        return got if dlg.exec() == QDialog.Accepted else None

    def identity_problems(self, ans):
        known = self.identities_known()
        out, seen = [], {}
        names = {os.path.basename(p) for p in ans}
        for f, i in known.items():
            if i.get("initial") and f not in names:
                seen.setdefault(i["initial"], i.get("doc") or f)
        lib = self.library()
        for p, (ini, dtype) in ans.items():
            f = os.path.basename(p)
            d = lib.doc_of_file(f) if lib is not None else None
            ini = DV.clean_initial(ini)
            if not ini:
                out.append(f"{f}: give it an initial.")
            elif ini in seen and seen[ini] != ((d or {}).get("name") or f):
                out.append(f"{f}: {ini} is already used.")
            if dtype not in DV.DOC_TYPES:
                out.append(f"{f}: pick its type.")
            seen[ini] = (d or {}).get("name") or f
        return out

    def identify(self, ans):
        """Keep the initials and types: in Customer Documents for its documents, else with the matrix when it is read."""
        lib = self.library()
        self._pending_ids = {}
        for p, (ini, dtype) in ans.items():
            f = os.path.basename(p)
            d = lib.doc_of_file(f) if lib is not None else None
            if d is not None:
                lib.set_identity(d["id"], ini, dtype)
            else:
                self._pending_ids[f] = (DV.clean_initial(ini), dtype)
        diag.activity("compliance_documents_identified", n=len(ans))

    def _apply_pending(self, M):
        for f, (ini, dtype) in (getattr(self, "_pending_ids", None) or {}).items():
            SD.set_doc(M, f, ini, dtype)
        self._pending_ids = {}
        lib = self.library()
        if lib is not None:
            SD.sync_docs(M, lib)

    def read(self, paths=None, out=None, identities=None, start=None):
        """identities: {path: (initial, type)} for files with none yet, or "suggested" (tests); else the person is asked.
        start (a new matrix): choose, prescribed, headings, typed, blank; tests that give none keep the 2.68 start."""
        if self.running():                          # 2.82.0: one read at a time, never two copies of a matrix
            self.host.status("Reading is already running. Wait for it to finish, or press Stop.")
            return None
        paths = paths or self.chosen()
        if not paths:
            return None
        self._busy = True
        try:
            return self._read(paths, out, identities, start)
        finally:
            if self.worker is None:
                self._busy = False
                self.lock_controls()

    def _read(self, paths, out, identities, start):
        self._start = start or ("auto" if os.environ.get("AH_TEST") else self.start.currentData())
        need = self.unidentified(paths)
        if need:
            if identities is None and os.environ.get("AH_TEST"):
                identities = "suggested"
            if identities == "suggested":
                identities = {p: (i, t) for p, i, t in self.suggest(need)}
            elif identities is None:
                identities = self.ask_identity(self.suggest(need))
                if identities is None:
                    self.host.status("Not read: every document needs an initial and a type.")
                    return None
            why = self.identity_problems({p: identities.get(p, ("", "")) for p in need})
            if why:
                self.host.status("Not read: " + " ".join(why))
                return None
            self.identify({p: identities[p] for p in need})
        if self.host.review is None:
            if out is None:
                ef = self.host.effort_name or "RFP"
                base = os.path.dirname(self.host.effort_path) if self.host.effort_path else os.path.expanduser("~")
                stem = re.sub(r"[^A-Za-z0-9_-]+", "_", ef)
                out, _ = QFileDialog.getSaveFileName(self, "Where should the compliance matrix live?",
                                                     self.host.out_path("compliance_matrix") if self.host.effort_path
                                                     else os.path.join(base, f"{stem}_Compliance_Matrix.xlsx"), "Excel (*.xlsx)")
                if not out:
                    return None
        self._out = out
        self._root = self.host.ws.root if self.host.ws is not None else None
        self._new = self.host.review is None
        self.host.status(f"Reading {len(paths)} file(s)...")
        if self.host.review is None:
            diag.activity("compliance_new", files=len(paths))
        else:
            diag.activity("compliance_files_added", files=len(paths))
        self.worker = ReadWorker(paths, self.chunks_of, self.host.ws.p("page copies") if self.host.ws is not None else "")
        self.worker.done.connect(self.read_done)
        self.worker.progress.connect(self.panel.step)
        self.panel.start(("Starting the compliance matrix" if self._new else "Adding documents to the compliance matrix")
                         + f": {len(paths)} file(s)", "Getting ready")
        self.lock_controls()
        self.worker.start()
        return self.worker

    def read_done(self, res):
        self.worker = None; self._busy = False
        try:
            self._finish(res)
        except Exception as ex:                     # 2.82.0: an error after reading is shown, never silent
            diag.swallowed()
            self.panel.failed("The read did not finish", f"Building the matrix stopped with an error ({type(ex).__name__}). "
                              + ("No compliance matrix was made." if self._new else "Your matrix is as it was before Read."),
                              "Press Read to try again. If it happens again, Help > Create a support file and send it in.")
            self.host.status("The read did not finish. See the message on Read RFP.")
        finally:
            self.lock_controls()
            try:
                self.refresh()
            except Exception:
                diag.swallowed()

    def _finish(self, res):
        if self.host.ws is None or self.host.ws.root != getattr(self, "_root", None):
            self.panel.stopped("Reading stopped", "The effort changed while it read. Nothing was written.", "Press Read again.")
            return
        if isinstance(res, CR.S.Spill):                 # 2.97.0: marked above CUI: stop, nothing written or kept
            from .sensgate import spill_stop
            self.panel.failed("Stopped: a document is marked above CUI", res.text(),
                              "Nothing was written to the matrix and no page copy was kept. Leave the file where it is and "
                              "tell your security officer.")
            spill_stop(self.host, res)
            return
        if isinstance(res, CR.Stopped):
            self.panel.stopped("Reading stopped", "You pressed Stop. Nothing was written to the matrix.",
                               "Press Read when you are ready.")
            self.host.status("Reading stopped. Nothing was written.")
            diag.activity("compliance_read_stopped")
            return
        if isinstance(res, CR.ReadFailed):
            self.panel.failed("A file could not be read", f"{res.name} stopped the read ({type(res.cause).__name__}). "
                              + ("No compliance matrix was made." if self._new else "Your matrix is as it was before Read."),
                              "Open the file to check it, save it again (or as PDF), then Read again; or untick it and Read "
                              "the others.")
            self.host.status(f"Not read: {res.name} could not be read.")
            diag.activity("compliance_read_failed")
            return
        if isinstance(res, Exception):
            raise res
        items, heads, src, empty = res
        if self.host.review is None:
            M = CR.new_matrix(self._out, items, heads, src, (self.host.ws.get("outline_text") or "") if self.host.ws else "")
            fixed = CR.complete(M)
            self._apply_pending(M)
            start_msg = self._start_structure(M, getattr(self, "_start", "auto"))
            self.host.set_matrix(M, new=True)
            msg = f"{len(items)} sentences from {len(src)} file(s). {start_msg}".strip()
        else:
            add = CR.add_read(self.host.review.M, items, heads, src)
            fixed = CR.complete(self.host.review.M)
            self._apply_pending(self.host.review.M)
            self.host.changed()
            msg = f"{len(add)} sentences added."
        if fixed:
            msg += f" {fixed} line(s) the reader did not split out were added in their place."
        if empty:
            msg += f" {len(empty)} file(s) have no typed text (scanned pages?)."
        diag.activity("compliance_read", files=len(src), items=len(items))
        self.host.status(msg + " " + CR.text_check_line(CR.text_check(self.host.review.M)))
        self.panel.done("Read", msg)
        self.refresh()
        if getattr(self, "_start", "") == "choose" and not self.host.review.M.outline:
            self.host.go("structure")
            self.host.structure_page.offer_start()
            return
        self.host.go("assign")
