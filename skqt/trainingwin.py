"""Stationkeeper Training in Qt (2.72.0): the Training Studio's five steps in the Qt design system. 1 Gather (training
data packs and past compliance matrices), 2 Review (every corrected line with its picture: accept, reject, fix), 3 Train
(Improve Reading on a worker thread: it keeps the new reader only if it reads held-out lines better; put back the
previous reader; the docTR Training Kit package; the Trainer), 4 Measure (the scorecard: an area that got worse is left
out), 5 Build the pack (.skknow), with loading trained models, exporting and undoing Knowledge. The same engine as the
classic Training program (corrections, studio, trainpack, tess_train); nothing leaves the PC. No generative AI.
"""
import datetime, json, os
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
                               QPushButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import app_gui as eng
import diag
import corrections as CO
import studio as ST
from . import design as D

FILTERS = ["All lines", "Taught (not rejected)", "Rejected", "Test set (set aside)", "From packs", "Saved on this PC"]
STEPS = (("gather", "1 Gather"), ("review", "2 Review"), ("train", "3 Train"), ("measure", "4 Measure"), ("build", "5 Build the pack"))
TITLES = {"gather": ("Gather", "What the team learned: training data packs and past compliance matrices"),
          "review": ("Review", "Every corrected line with its picture: taught unless you reject it"),
          "train": ("Train", "Teach the reader on this PC's processor, offline"),
          "measure": ("Measure", "Did this training help? Each area is tested on what it did not learn from"),
          "build": ("Build the pack", "One .skknow file for the approved SharePoint folder"),
          "trainer": ("Trainer", "Box text the reader missed in a document or picture, and teach it")}


class TrainWorker(QThread):
    progress = Signal(str, float)
    done = Signal(object, str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            r = self.fn(lambda msg, frac=None: self.progress.emit(str(msg), -1.0 if frac is None else float(frac)))
            self.done.emit(r, "")
        except Exception as e:
            eng.log_error("Improve Reading failed")
            self.done.emit(None, f"{type(e).__name__}: {e}")


def _scroll(widget):
    outer = QVBoxLayout(widget); outer.setContentsMargins(0, 0, 0, 0)
    sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame)
    outer.addWidget(sc)
    inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner)
    v = QVBoxLayout(inner)
    v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
    return v


class TrainingWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.setWindowTitle(f"Stationkeeper Training {eng.APP_VERSION}: corrections in, a better reader out (100% local)")
        self.resize(1360, 880)
        self.score_rows, self.worker, self.train_fn = [], None, None
        root = QWidget(); rh = QHBoxLayout(root); rh.setContentsMargins(0, 0, 0, 0); rh.setSpacing(0)
        rail = QWidget(); rail.setObjectName("railbox"); rail.setFixedWidth(220)
        rv = QVBoxLayout(rail); rv.setContentsMargins(D.SPACE["s"], 0, D.SPACE["s"], D.SPACE["m"]); rv.setSpacing(2)
        brand = QLabel("Training"); brand.setObjectName("brand"); rv.addWidget(brand)
        h = QLabel("TRAINING STUDIO"); h.setObjectName("railhead"); rv.addWidget(h)
        self.group = QButtonGroup(self); self.step_btns = {}
        for key, text in STEPS:
            b = QPushButton(text); b.setObjectName("rail"); b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            self.group.addButton(b); self.step_btns[key] = b; rv.addWidget(b)
        h2 = QLabel("TEACH BY HAND"); h2.setObjectName("railhead"); rv.addWidget(h2)        # 2.73.0: the Trainer in Qt
        b = QPushButton("Trainer"); b.setObjectName("rail"); b.setCheckable(True)
        b.clicked.connect(lambda _=False: self.go("trainer"))
        self.group.addButton(b); self.step_btns["trainer"] = b; rv.addWidget(b)
        rv.addStretch(1)
        ver = QLabel(f"Offline. No AI. {eng.APP_VERSION}"); ver.setObjectName("railhead"); rv.addWidget(ver)
        rh.addWidget(rail)
        col = QWidget(); cv = QVBoxLayout(col); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)
        bar = QFrame(); bar.setProperty("bar", True)
        bh = QHBoxLayout(bar); bh.setContentsMargins(D.SPACE["xl"], D.SPACE["m"], D.SPACE["xl"], D.SPACE["m"])
        tcol = QVBoxLayout(); tcol.setSpacing(0)
        self.page_title = D.label("", "display", wrap=False); tcol.addWidget(self.page_title)
        self.page_sub = D.label("", "muted", wrap=False); tcol.addWidget(self.page_sub)
        bh.addLayout(tcol, 1)
        self.state = D.label("", "muted"); self.state.setAlignment(Qt.AlignRight | Qt.AlignVCenter); bh.addWidget(self.state)
        cv.addWidget(bar)
        self.stack = QStackedWidget(); cv.addWidget(self.stack, 1)
        foot = D.label("Offline: nothing leaves this PC. Training data and Knowledge Packs hold what was learned from internal "
                       "documents: approved SharePoint folder only, never GitHub.", "muted")
        foot.setContentsMargins(D.SPACE["xl"], D.SPACE["s"], D.SPACE["xl"], D.SPACE["s"]); cv.addWidget(foot)
        rh.addWidget(col, 1)
        self.setCentralWidget(root)
        self.toaster = D.Toast(self)
        self.pages = {}
        for key, build in (("gather", self._gather), ("review", self._review), ("train", self._train),
                           ("measure", self._measure), ("build", self._build)):
            w = QWidget(); w.setObjectName("page"); build(w); self.stack.addWidget(w); self.pages[key] = w
        from .trainerpage import TrainerPage
        self.trainer = TrainerPage(self)
        self.stack.addWidget(self.trainer); self.pages["trainer"] = self.trainer
        diag.activity("training_qt_started")
        self.refresh()
        self.go("gather")

    # ------------------------------------------------------------ shell
    def go(self, key):
        self.stack.setCurrentWidget(self.pages[key])
        self.step_btns[key].setChecked(True)
        t, sub = TITLES[key]
        self.page_title.setText(t); self.page_sub.setText(sub)
        if key == "measure" and not self.score_rows:
            self.lbl_measure.setText("Run the tests to see the scorecard.")

    def toast(self, text):
        self.toaster.show_text(text)

    def status(self, text):
        self.statusBar().showMessage(text, 9000)

    def _next(self, v, key, text):
        row = QHBoxLayout(); row.addStretch(1)
        row.addWidget(D.button(text, "primary", lambda: self.go(key)))
        v.addLayout(row)

    def refresh(self):
        all_ = CO.samples()
        rej = sum(s["rejected"] for s in all_)
        _n, regions, _junk, size = CO.training_stats()
        ks = eng.knowledge_status()
        self.state.setText(f"Training set: {len(all_) - rej} lines taught, {rej} rejected, {regions} regions, "
                           f"{size / 1024 / 1024:.1f} MB\n{ks.splitlines()[0] if ks else ''}")
        self.gather_refresh()
        self.fill()
        n, new = self.training_state()
        self.lbl_teach.setText(f"{n} lines to teach ({new} new since the reader was last improved).")
        self.lbl_know.setText(eng.knowledge_status() + f"\nBackups available for Undo: {len(eng.list_knowledge_backups())}")

    @staticmethod
    def training_state():
        import tess_train
        n = len(tess_train.read_samples(eng.TRAIN_DIR))
        try:
            with open(os.path.join(eng.TRAIN_DIR, "model", "training_report.json"), encoding="utf-8") as f:
                last = json.load(f).get("samples", 0)
        except (OSError, ValueError):
            last = 0
        return n, max(0, n - last)

    # ------------------------------------------------------------ 1 gather
    def _gather(self, w):
        v = _scroll(w)
        card = D.Card("Gather what the team learned", "Training data packs from the approved SharePoint folder (misread lines "
                      "with their pictures, OCR fixes, compliance decisions), and past compliance matrices: their Keep and "
                      "Drop decisions are learned as numbered word buckets and counts only, never their words.")
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.button("Import training data...", "primary", lambda: self.import_packs()))
        row.addWidget(D.button("Add past compliance matrices...", None, lambda: self.gather_matrices()))
        row.addStretch(1)
        card.body.addLayout(row)
        self.lbl_gather = card.add(D.label(""))
        v.addWidget(card)
        self._next(v, "review", "Next: 2 Review")
        v.addStretch(1)

    def gather_refresh(self):
        import complearn
        st = ST.load_state(eng.CONFIG_DIR)
        all_ = CO.samples()
        train, test = ST.split(all_)
        cs = complearn.Learner(eng.COMPLIANCE_LEARNED_FILE).summary()
        try:
            db, fx = len(eng.read_db_rows()), len(eng.read_ocr_fix_rows())
        except Exception:
            diag.swallowed(); db = fx = 0
        self.lbl_gather.setText(
            f"Corrected lines: {len(all_)} ({len(train)} to teach, {len(test)} set aside as the test set, "
            f"{sum(s['rejected'] for s in all_)} rejected)\n"
            f"Corrections packs imported: {len(CO.packs())}\n"
            f"Past compliance matrices gathered: {len(st['matrices'])}; compliance decisions learned: {cs['decisions']} "
            f"from {cs['matrices']} matrices\n"
            f"Acronyms database rows: {db}; OCR fixes: {fx}")

    def import_packs(self, paths=None, ask=True, confirm_old=None):
        """Training data packs (.sktrain), each area filed where it belongs; older corrections packs (.zip) still import.
        2.97.0: a pack marked above CUI is refused; one made before 2.97 (no sensitivity) only when the person confirms
        it holds nothing above CUI (confirm_old (tests): True or False)."""
        import trainpack as TP

        def old_ok(p):
            if confirm_old is not None:
                return confirm_old
            if not ask:
                return True
            return QMessageBox.question(self, "Sensitivity not stated", f"{os.path.basename(p)} was made before Stationkeeper 2.97 "
                                        "and does not say its sensitivity. Import it only if you know it holds nothing above CUI "
                                        "(no Confidential, Secret or Top Secret). Import it?") == QMessageBox.Yes
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Training data (from the approved SharePoint folder)", "",
                                                    "Training data (*.sktrain *.zip)")
        done, failed = [], []
        for p in paths or []:
            try:
                if p.lower().endswith(TP.EXT):
                    man, _d = TP.read(p)
                    why = TP.sensitivity_problem(man)
                    old = man.get("sensitivity") is None
                    if why and not (old and old_ok(p)):
                        raise TP.PackError(why)
                    r = TP.import_pack(p, os.path.join(getattr(eng, "DATA_DIR", eng.BASE_DIR), "training_data", "imported"),
                                       os.path.join(eng.CONFIG_DIR, "compliance_learned.json"),
                                       merge_fixes=eng.merge_pack_fixes, merge_ignore=eng.merge_pack_ignore, confirmed_old=old)
                    done.append(f"{os.path.basename(p)}: {r['reading']} misread lines and regions, {r['ocrfix']} OCR fixes, "
                                f"{r['compliance']} compliance decisions ({r['learned']} learned), {r['words']} word choices"
                                + (f" ({r['skipped']} already here)" if r["skipped"] else ""))
                    continue
                if not old_ok(p):                       # a corrections pack never says its sensitivity
                    raise TP.PackError("Not imported: its sensitivity was not confirmed (nothing above CUI is imported).")
                r = CO.import_pack(p)
                done.append(f"{os.path.basename(p)}: {r['lines']} lines, {r['regions']} regions"
                            + (f" ({r['skipped']} already here)" if r["skipped"] else ""))
            except (TP.PackError, CO.PackError) as ex:
                failed.append(f"{os.path.basename(p)}: {ex}")
            except Exception as ex:
                eng.log_error("Training data import failed")
                failed.append(f"{os.path.basename(p)}: {type(ex).__name__}")
        if done or failed:
            diag.activity("corrections_imported", files=len(done), errors=len(failed))
            self.refresh()
            if ask:
                QMessageBox.information(self, "Import", ("Imported:\n" + "\n".join(done) if done else "")
                                        + ("\n\nNot imported (nothing copied):\n" + "\n".join(failed) if failed else ""))
        return done, failed

    def gather_matrices(self, paths=None):
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Past compliance matrices (Excel)", "", "Compliance matrix (*.xlsx)")
        if not paths:
            return []
        from .sensgate import training_gate              # 2.97.0: nothing above CUI; an unmarked file is declared
        said = []
        paths = [p for p in paths if training_gate(self, p, getattr(self, "declare_answer", None), said.append)]
        if said:
            self.toast(said[-1])
        if not paths:
            return []
        res = ST.gather_matrices(list(paths), eng.COMPLIANCE_LEARNED_FILE, eng.CONFIG_DIR)
        diag.activity("studio_matrices_gathered", files=len(res), items=sum(n for _f, n in res))
        self.refresh()
        self.toast(f"{len(res)} matrices gathered")
        return res

    # ------------------------------------------------------------ 2 review
    def _review(self, w):
        v = QVBoxLayout(w); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        bar = QHBoxLayout(); bar.setSpacing(D.SPACE["s"])
        bar.addWidget(D.button("Import training data...", None, lambda: self.import_packs()))
        bar.addWidget(D.label("Show", "label", wrap=False))
        self.filter = QComboBox(); self.filter.addItems(FILTERS); self.filter.currentIndexChanged.connect(lambda _i: self.fill())
        bar.addWidget(self.filter)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search the text"); self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self.fill()); self.search.setMaximumWidth(260)
        bar.addWidget(self.search)
        bar.addStretch(1)
        self.lbl_packs = D.label("", "muted", wrap=False); bar.addWidget(self.lbl_packs)
        bar.addWidget(D.button("Next: 3 Train", "primary", lambda: self.go("train")))
        v.addLayout(bar)
        body = QHBoxLayout(); body.setSpacing(D.SPACE["m"]); v.addLayout(body, 1)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Correct text", "Read as", "Conf.", "From", "Saved", "State"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        for k, wd in enumerate((190, 160, 50, 220, 130, 80)):
            self.table.setColumnWidth(k, wd)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_picture)
        self.table.itemDoubleClicked.connect(lambda _i: self.fix_text())
        body.addWidget(self.table, 1)
        side = D.Card("Picture"); side.setFixedWidth(360)
        self.pic = QLabel(); self.pic.setMinimumHeight(140); self.pic.setAlignment(Qt.AlignCenter)
        self.pic.setStyleSheet("background:#F8FAFC;border-radius:6px;")
        side.add(self.pic)
        self.lbl_pic = side.add(D.label("Select a line."))
        for text, kind, fn in (("Accept (teach it)", "primary", lambda: self.set_rejected(False)),
                               ("Reject (never teach it)", "danger", lambda: self.set_rejected(True)),
                               ("Fix the text...", None, lambda: self.fix_text())):
            side.add(D.button(text, kind, fn))
        side.add(D.label("Every line is taught unless you reject it. Fix the text when the person who sent it spelled it "
                         "wrong. Double-click a row to fix it.", "muted"))
        side.body.addStretch(1)
        body.addWidget(side)

    def _rows(self):
        f, q = self.filter.currentText(), self.search.text().strip().casefold()
        out = []
        for s in CO.samples():
            if q and q not in s["text"].casefold() and q not in s["read"].casefold():
                continue
            if f == "Taught (not rejected)" and s["rejected"]:
                continue
            if f == "Rejected" and not s["rejected"]:
                continue
            if f == "Test set (set aside)" and (s["rejected"] or not ST.in_test_set(s["rel"])):
                continue
            if f == "From packs" and not s["source"].startswith("Pack from"):
                continue
            if f == "Saved on this PC" and s["source"].startswith("Pack from"):
                continue
            out.append(s)
        return out

    def fill(self):
        keep = set(self.selected())
        self.table.blockSignals(True)
        rows = self._rows()
        self.table.setRowCount(len(rows))
        grey = D.color("muted")
        for i, s in enumerate(rows):
            state = "Rejected" if s["rejected"] else "Test set" if ST.in_test_set(s["rel"]) else "Taught"
            for k, val in enumerate((s["text"], s["read"], str(s["conf"]), s["source"], s["date"], state)):
                it = QTableWidgetItem(val)
                it.setData(Qt.UserRole, s["rel"])
                if s["rejected"]:
                    it.setForeground(grey)
                self.table.setItem(i, k, it)
            if s["rel"] in keep:
                self.table.selectRow(i)
        self.table.blockSignals(False)
        ps = CO.packs()
        self.lbl_packs.setText(f"Packs imported: {len(ps)}" + (f" (last from {ps[-1]['from']})" if ps else ""))
        self.show_picture()

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows if self.table.item(r, 0)]

    def select(self, rels):
        self.table.clearSelection()
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.UserRole) in rels:
                self.table.selectRow(r)

    def set_rejected(self, on, rels=None):
        rels = rels or self.selected()
        if rels:
            CO.set_rejected(rels, on)
            if on:
                diag.activity("corrections_rejected", n=len(rels))
            else:
                diag.activity("corrections_accepted", n=len(rels))
            self.refresh()
            self.toast(f"{len(rels)} line(s) " + ("rejected: never taught" if on else "taught"))
        return len(rels)

    def fix_text(self, rel=None, text=None):
        rel = rel or (self.selected()[:1] or [None])[0]
        if not rel:
            return False
        cur = next((s["text"] for s in CO.samples() if s["rel"] == rel), "")
        if text is None:
            text, ok = QInputDialog.getText(self, "Fix the text", "Correct text for this line:", QLineEdit.Normal, cur)
            if not ok:
                return False
        if not text or text.strip() == cur:
            return False
        ok = CO.set_text(rel, text)
        if ok:
            diag.activity("corrections_fixed")
            self.refresh(); self.select([rel])
        return ok

    def show_picture(self):
        sel = self.selected()
        if len(sel) != 1:
            self.pic.clear()
            self.lbl_pic.setText(f"{len(sel)} lines selected." if sel else "Select a line.")
            return
        rel = sel[0]
        pm = QPixmap(os.path.join(CO.TRAIN_DIR, rel.replace("/", os.sep)))
        if not pm.isNull():
            self.pic.setPixmap(pm.scaled(330, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.pic.clear()
        s = next((x for x in CO.samples() if x["rel"] == rel), {"text": "", "read": ""})
        self.lbl_pic.setText(f"Correct text: {s['text']}\nRead as: {s['read']}")

    # ------------------------------------------------------------ 3 train
    def _train(self, w):
        v = _scroll(w)
        card = D.Card("Improve Reading", "Fine-tunes the Tesseract reader on the taught lines, on this PC's processor, offline. "
                      "It tests the new reader on lines it did not learn from and keeps it only if it reads them better; "
                      "otherwise nothing changes.")
        self.lbl_teach = card.add(D.label("", "title"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        self.btn_teach = D.button("Teach and Apply", "primary", lambda: self.improve())
        row.addWidget(self.btn_teach)
        row.addWidget(D.button("Put back the previous reader", None, lambda: self.undo_knowledge()))
        row.addStretch(1)
        card.body.addLayout(row)
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setValue(0); card.add(self.bar)
        self.stage = card.add(D.label("", "muted"))
        self.result = QPlainTextEdit(); self.result.setReadOnly(True); self.result.setMinimumHeight(200)
        card.add(self.result)
        self._last_report()
        v.addWidget(card)
        more = D.Card("More ways to teach")
        r2 = QHBoxLayout(); r2.setSpacing(D.SPACE["s"])
        r2.addWidget(D.button("Trainer", None, lambda: self.open_trainer(),
                              "Box text the reader missed in a document or picture, read a region, save lines or Not text "
                              "regions"))
        r2.addWidget(D.button("Prepare a package for the docTR Training Kit", None, lambda: self.prepare_package()))
        r2.addStretch(1)
        more.body.addLayout(r2)
        more.add(D.label("The Trainer: open a document or picture, box text the reader missed, read a region, and save lines "
                         "or Not text regions. The package splits the lines and regions into the train and check lists the "
                         "offline docTR Training Kit reads.", "muted"))
        v.addWidget(more)
        self._next(v, "measure", "Next: 4 Measure")
        v.addStretch(1)

    def _last_report(self):
        import tess_train
        try:
            with open(os.path.join(eng.TRAIN_DIR, "model", "training_report.json"), encoding="utf-8") as f:
                last = json.load(f)
            self.result.setPlainText(f"Last time ({last.get('date', '?')}):\n" + tess_train.describe(last))
        except (OSError, ValueError):
            self.result.setPlainText("No reader trained yet: the scanner uses Google's English reader.")

    def _default_train(self, say):
        import tess_train
        out_dir = os.path.join(eng.TRAIN_DIR, "model")
        current = os.path.join(eng.MODELS_DIR, eng.CUSTOM_TESS_MODEL + ".traineddata")
        return tess_train.train(eng.TESS_DIR, eng.TRAIN_DIR, out_dir, progress=say, current_model=current,
                                runner=lambda cmd, timeout=600: eng.run_tesseract_tool(cmd, b"", timeout, write_dirs=[out_dir]))

    def improve(self, wait=False):
        """Teach and Apply on a worker thread. wait (tests): return the result when it is done."""
        import tess_train
        if self.worker is not None:
            return None
        n, _new = self.training_state()
        if n < tess_train.MIN_SAMPLES and self.train_fn is None:
            self.stage.setText(f"{n} corrected lines: at least {tess_train.MIN_SAMPLES} are needed.")
            return None
        diag.activity("improve_reading_started")
        self.btn_teach.setEnabled(False); self.btn_teach.setText("Working...")
        self.bar.setRange(0, 0)
        self.worker = TrainWorker(self.train_fn or self._default_train)
        self.worker.progress.connect(self._progress)
        self.worker.done.connect(self._trained)
        self._result = None
        self.worker.start()
        if wait:
            self.worker.wait()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            return self._result
        return self.worker

    def _progress(self, msg, frac):
        self.stage.setText(msg)
        if frac < 0 or 0.3 <= frac < 0.95:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100); self.bar.setValue(int(frac * 100))

    def _trained(self, r, err):
        import tess_train
        self.worker = None
        self.btn_teach.setEnabled(True); self.btn_teach.setText("Teach and Apply")
        self.bar.setRange(0, 100); self.bar.setValue(100 if r else 0)
        self._result = r if r is not None else {"error": err}
        if err:
            self.stage.setText("Stopped. Your reader was not changed.")
            self.result.setPlainText(err)
        elif r.get("better"):
            try:
                eng.load_trained_models(os.path.dirname(r["model"]))
            except Exception:
                diag.swallowed()
            self.stage.setText("Applied: the scanner now reads pictures with the improved reader.")
            lines = ["APPLIED: the new reader read the held-out lines better.", "", tess_train.describe(r)]
            if r.get("fixed_examples"):
                lines += ["", "Now read correctly (was wrong before):"] + [f"  {t}    (was: {b})" for t, b in r["fixed_examples"]]
            if r.get("new_mistakes"):
                lines += ["", "New mistakes to watch:"] + [f"  {t}    (now: {a})" for t, a in r["new_mistakes"]]
            self.result.setPlainText("\n".join(lines))
            diag.activity("improve_reading_applied")
        else:
            self.stage.setText("Not applied: your current reader still reads these lines as well or better.")
            self.result.setPlainText("NOT APPLIED: the new reader did not beat the current one on held-out lines.\n\n"
                                     + tess_train.describe(r) + "\n\nSave more corrected lines (varied pictures and fonts), "
                                     "then try again.")
            diag.activity("improve_reading_not_applied")
        self.refresh()

    def undo_knowledge(self):
        what = eng.restore_last_knowledge_backup()
        msg = f"Put back the reader and knowledge from {what}." if what else "Nothing to undo."
        if what:
            diag.activity("knowledge_undone")
        else:
            diag.activity("knowledge_undo_nothing")
        self.status(msg)
        self.refresh()
        return what

    def prepare_package(self, show=True):
        import trainer_gui
        rep = trainer_gui.build_training_package()
        diag.activity("training_package_prepared")
        if show:
            QMessageBox.information(self, "Training package", rep)
        return rep

    def open_trainer(self, path=None):
        """2.73.0: the Trainer is a page of this window (it used to open the classic Training program)."""
        diag.activity("trainer_opened")
        self.go("trainer")
        if path:
            self.trainer.load_file(path)
        return self.trainer

    # ------------------------------------------------------------ 4 measure
    def _measure(self, w):
        v = QVBoxLayout(w); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout()
        top.addWidget(D.label("An area that got worse is left out of the pack automatically. Double-click a row to leave an "
                              "area out or put it back.", "muted"), 1)
        top.addWidget(D.button("Run the tests", "primary", lambda: self.measure()))
        v.addLayout(top)
        self.sc = QTableWidget(0, 6)
        self.sc.setHorizontalHeaderLabels(["Area", "Test", "Now", "After training", "Change", "In the pack"])
        self.sc.verticalHeader().setVisible(False)
        self.sc.setSelectionBehavior(QAbstractItemView.SelectRows); self.sc.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sc.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for k, wd in enumerate((260, 320, 80, 110, 80, 200)):
            self.sc.setColumnWidth(k, wd)
        self.sc.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sc.itemDoubleClicked.connect(lambda it: self.toggle_area(self.score_rows[it.row()]["area"]))
        v.addWidget(self.sc, 1)
        self.lbl_measure = D.label("Run the tests to see the scorecard.", "muted"); v.addWidget(self.lbl_measure)
        self._next(v, "build", "Next: 5 Build the pack")

    def measure(self):
        st = ST.load_state(eng.CONFIG_DIR)
        report = None
        try:
            with open(os.path.join(eng.TRAIN_DIR, "model", "training_report.json"), encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, ValueError):
            pass
        have = [n for n, _p in eng._knowledge_sources()]
        self.score_rows = ST.scorecard(CO.samples(), eng.load_ocr_fixes(), eng.load_ocr_ignore(), report,
                                       ST._matrices(st["matrices"]), have, left_out=st["left_out"])
        diag.activity("studio_measured", rows=len(self.score_rows))
        self.score_fill()
        return self.score_rows

    def score_fill(self):
        fmt = lambda x: "-" if x is None else f"{x}%"
        self.sc.setRowCount(len(self.score_rows))
        for i, r in enumerate(self.score_rows):
            ch = "" if r["change"] is None else (f"+{r['change']}" if r["change"] >= 0 else str(r["change"]))
            vals = (r["title"], r["test"] + (f" ({r['n']})" if r.get("n") else ""),
                    fmt(r["now"]) if r["after"] is not None else "", fmt(r["after"]) if r["after"] is not None else "",
                    ch, ("Yes" if r["include"] else "No") + ("" if r["why"] == "In the pack" else f": {r['why']}"))
            color = D.color("crit") if r["why"] == "Left out: got worse" else (D.color("muted") if not r["include"] else None)
            for k, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if color is not None:
                    it.setForeground(color)
                self.sc.setItem(i, k, it)
        n_in = len({r["area"] for r in self.score_rows if r["include"]})
        self.lbl_measure.setText(f"{n_in} area(s) go in the pack.")

    def toggle_area(self, area):
        st = ST.load_state(eng.CONFIG_DIR)
        st["left_out"] = [a for a in st["left_out"] if a != area] if area in st["left_out"] else st["left_out"] + [area]
        ST.save_state(eng.CONFIG_DIR, st)
        diag.activity("studio_area_toggled")
        self.measure()
        return area not in st["left_out"]

    # ------------------------------------------------------------ 5 build
    def _build(self, w):
        v = _scroll(w)
        card = D.Card("Build the pack", "One file (.skknow) with the areas kept and the scorecard. Put it in the approved "
                      "SharePoint folder. People open it (or Settings > Install a Knowledge Pack in Stationkeeper), read one "
                      "card that says what improves, and install it. Their own corrections, decisions and rows stay; Undo "
                      "puts everything back.")
        card.add(D.label("Notes for the install card (optional)", "label"))
        self.build_notes = QLineEdit(); self.build_notes.setPlaceholderText("For example: trained on the Kestrel and Osprey corrections")
        card.add(self.build_notes)
        row = QHBoxLayout(); row.addWidget(D.button("Build the pack...", "primary", lambda: self.build_pack())); row.addStretch(1)
        card.body.addLayout(row)
        self.lbl_build = card.add(D.label(""))
        v.addWidget(card)
        know = D.Card("Knowledge on this PC", "Load models trained with the offline Training Kit, export everything as a "
                      "Knowledge Pack, or undo the last change.")
        self.lbl_know = know.add(D.label(""))
        r2 = QHBoxLayout(); r2.setSpacing(D.SPACE["s"])
        r2.addWidget(D.button("Load trained models...", None, lambda: self.load_models()))
        r2.addWidget(D.button("Export Knowledge Pack...", None, lambda: self.export_knowledge()))
        r2.addWidget(D.button("Undo last knowledge change", None, lambda: self.undo_knowledge()))
        r2.addStretch(1)
        know.body.addLayout(r2)
        know.add(D.label("Knowledge Packs contain what was learned from internal documents. Save them only to the approved "
                         "SharePoint folder: never GitHub, email or personal storage.", "crit"))
        v.addWidget(know)
        from . import updates as UP                      # 2.76.0: update packs, and why no admin password is needed
        self.up = UP.updates_card(self)
        self.up.lbl.setWordWrap(True)
        v.addWidget(self.up)
        v.addWidget(UP.security_card())
        v.addStretch(1)

    def build_pack(self, path=None):
        if not self.score_rows:
            self.measure()
        if not any(r["include"] for r in self.score_rows):
            QMessageBox.information(self, "Build the pack", "Nothing to ship: every area is left out or empty.")
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the Knowledge Pack (approved SharePoint folder)",
                                                  ST.default_name(datetime.date.today()), f"Knowledge Pack (*{ST.EXT})")
            if not path:
                return None
        info = eng.make_knowledge_pack(path, self.build_notes.text(), include=ST.included_files(self.score_rows),
                                       scorecard=self.score_rows)
        diag.activity("studio_pack_built", files=len(info["files"]))
        kept = sorted({r["title"] for r in self.score_rows if r["include"]})
        out = sorted({r["title"] for r in self.score_rows if not r["include"] and r["files"]})
        self.lbl_build.setText(f"Built {os.path.basename(path)}.\nIn the pack: {', '.join(kept)}."
                               + (f"\nLeft out: {', '.join(out)}." if out else "")
                               + "\nIt holds what was learned from internal documents: approved SharePoint folder only.")
        self.toast("Knowledge Pack built")
        return info

    def load_models(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Training Kit output folder (docTR: output\\models; or acronym.traineddata)")
            if not folder:
                return None
        try:
            found = eng.load_trained_models(folder)
        except Exception as e:
            eng.log_error("Load trained models failed")
            QMessageBox.warning(self, "Not loaded", f"{e}\n\nNothing was changed.")
            return None
        diag.activity("trained_models_loaded", n=len(found))
        self.refresh()
        self.status("Loaded " + ", ".join(found) + ". Undo puts the old models back.")
        return found

    def export_knowledge(self, path=None, notes=None):
        notes = self.build_notes.text().strip() if notes is None else notes
        if path is None:
            name = f"Stationkeeper_Knowledge_{datetime.datetime.now():%Y.%m.%d-%H%M}.zip"
            path, _ = QFileDialog.getSaveFileName(self, "Save the Knowledge Pack to the APPROVED SHAREPOINT folder", name,
                                                  "Knowledge Pack (*.zip)")
            if not path:
                return None
        info = eng.make_knowledge_pack(path, notes)
        diag.activity("knowledge_exported", files=len(info.get("files", [])))
        self.status(f"Saved {os.path.basename(path)} (version {info['version']}, models: {', '.join(info['models']) or 'none'}).")
        return info
