"""Full Text (3.51.0, brought back from the classic window): every word in the chosen files, typed text exactly and
picture text through the reader (equations in linear form), shown and saved as one .txt or one per file, or copied.
The same reader and sandbox as the scan. The text carries the source files' markings: save and handle it the same
way. In its own window, from the arrow beside Acronym Finder at the foot of the menu. Nothing leaves the PC."""
import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QMainWindow, QPlainTextEdit, QProgressBar, QVBoxLayout,
                               QWidget)

import diag
from . import design as D

_OPEN = []


def last_scan_files(config_dir):
    """The files of Acronym Finder's open list (the window when it is open, else the list it last had open)."""
    from . import acrtool as T
    for w in T._OPEN:
        s = w.page.session
        if s is not None and s.last_scan:
            return [p for p in s.last_scan.get("paths", []) if os.path.isfile(p)]
    import acrlists as AL
    import workspace as W
    root = os.path.join(config_dir, T.FOLDER)
    if not os.path.isdir(root):
        return []
    s = W.Workspace(AL.folder(root, AL.last(root))).load_session() or {}
    return [p for p in (s.get("last_scan") or {}).get("paths", []) if os.path.isfile(p)]


class ReadWorker(QThread):
    progress = Signal(float, str)
    one = Signal(str, str)
    finished_ok = Signal(str)

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        import app_gui as A
        n = len(self.files)
        try:
            for i, f in enumerate(self.files, 1):
                A.check_cancel()
                self.progress.emit((i - 1) / max(1, n), os.path.basename(f))
                t, _err = A.full_text_of(f, lambda m: (A.check_cancel(), self.progress.emit((i - 1) / max(1, n), str(m)[:90])), i, n)
                self.one.emit(f, t)
            self.finished_ok.emit(f"Done: {n} file(s).")
        except A.ScanCancelled:
            self.finished_ok.emit("Stopped.")
        except Exception as e:  # noqa: BLE001
            diag.error("full_text", "Full text failed", exc=(type(e), e, e.__traceback__))
            self.finished_ok.emit(f"The text could not be read ({type(e).__name__}).")


class FullTextWindow(QMainWindow):
    def __init__(self, config_dir=None):
        super().__init__()
        self.config_dir = config_dir
        self.setWindowTitle("Full Text - Stationkeeper")
        self.resize(1000, 760)
        self.files, self.texts, self.worker = [], {}, None
        root = QWidget(); v = QVBoxLayout(root); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"])
        v.addWidget(D.label("Full Text", "title"))
        v.addWidget(D.label("Pull out all the text: typed text exactly, picture text through the reader, equations in linear form.", "muted"))
        v.addWidget(D.label("The text carries the same classification and markings as the source files. Save and handle it the same way.", "crit"))
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Choose files...", None, lambda: self.pick_files()))
        row.addWidget(D.button("Choose a folder...", None, lambda: self.pick_folder()))
        self.b_last = D.button("Acronym Finder's files", "ghost", lambda: self.from_last_scan(), "The files Acronym Finder's open list scanned")
        self.b_last.setVisible(bool(config_dir))
        row.addWidget(self.b_last)
        self.lbl = D.label("No files chosen.", "muted"); row.addWidget(self.lbl, 1)
        bar = QHBoxLayout(); v.addLayout(bar)
        self.b_go = D.button("Read all the text", "primary", lambda: self.go()); self.b_go.setEnabled(False)
        self.b_stop = D.button("Stop", "danger", lambda: __import__("app_gui").CANCEL.set()); self.b_stop.setEnabled(False)
        self.prog = QProgressBar(); self.prog.setRange(0, 1000)
        self.stat = D.label("", "muted")
        for w in (self.b_go, self.b_stop, self.prog):
            bar.addWidget(w)
        bar.addWidget(self.stat, 1)
        self.box = QPlainTextEdit(); self.box.setReadOnly(True)
        v.addWidget(self.box, 1)
        bot = QHBoxLayout(); v.addLayout(bot)
        self.b_one = D.button("Save as one .txt...", None, lambda: self.save_one())
        self.b_each = D.button("Save one .txt per file...", None, lambda: self.save_each())
        self.b_copy = D.button("Copy", None, lambda: self.copy_all())
        for b in (self.b_one, self.b_each, self.b_copy):
            b.setEnabled(False); bot.addWidget(b)
        bot.addStretch(1)
        self.setCentralWidget(root)
        diag.activity("full_text_opened")

    def set_files(self, fps):
        import app_gui as A
        self.files = [f for f in fps if os.path.splitext(f)[1].lower() in A.SUPPORTED_EXTS and not os.path.basename(f).startswith("~$")]
        self.lbl.setText(f"{len(self.files)} file(s) chosen." if self.files else "No supported files chosen.")
        self.b_go.setEnabled(bool(self.files))
        return self.files

    def pick_files(self):
        fps, _ = QFileDialog.getOpenFileNames(self, "Choose files")
        if fps:
            self.set_files(fps)

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if d:
            self.set_files([os.path.join(r, f) for r, _d, fs in os.walk(d) for f in fs])

    def from_last_scan(self):
        got = self.set_files(last_scan_files(self.config_dir)) if self.config_dir else []
        if not got:
            self.lbl.setText("Acronym Finder has no scanned files on this PC yet.")
        return got

    def go(self, wait=False):
        import app_gui as A
        if not self.files or self.worker is not None:
            return None
        self.texts.clear(); self.box.clear(); self.prog.setValue(0)
        A.CANCEL.clear()
        self.worker = ReadWorker(list(self.files))
        self.worker.progress.connect(lambda f, t: (self.prog.setValue(int(f * 1000)), self.stat.setText(t)))
        self.worker.one.connect(self._one)
        self.worker.finished_ok.connect(self._done)
        self.b_go.setEnabled(False); self.b_stop.setEnabled(True)
        self.worker.start()
        if wait:
            import time
            t0 = time.time()
            while self.worker is not None and time.time() - t0 < 300:
                QApplication.processEvents(); time.sleep(0.05)
        return self.texts

    def _one(self, f, t):
        self.texts[f] = t
        self.box.appendPlainText(t)

    def _done(self, msg):
        self.worker = None
        self.prog.setValue(1000)
        self.stat.setText(msg)
        self.b_go.setEnabled(True); self.b_stop.setEnabled(False)
        for b in (self.b_one, self.b_each, self.b_copy):
            b.setEnabled(bool(self.texts))

    def all_text(self):
        return "\n".join(self.texts[f] for f in self.files if f in self.texts)

    def save_one(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save all the text as one file", "Full_Text.txt", "Text (*.txt)")
            if not path:
                return None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.all_text())
        self.stat.setText(f"Saved {os.path.basename(path)}")
        return path

    def save_each(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for one .txt per file")
            if not folder:
                return 0
        n = 0
        for f, t in self.texts.items():
            with open(os.path.join(folder, os.path.splitext(os.path.basename(f))[0] + "_fulltext.txt"), "w", encoding="utf-8") as fh:
                fh.write(t)
            n += 1
        self.stat.setText(f"Saved {n} file(s).")
        return n

    def copy_all(self):
        QApplication.clipboard().setText(self.all_text())
        self.stat.setText("Copied.")

    def closeEvent(self, e):
        import app_gui as A
        if self.worker is not None:
            A.CANCEL.set()
        if self in _OPEN:
            _OPEN.remove(self)
        super().closeEvent(e)


def open_tool(config_dir=None, paths=None):
    for w in _OPEN:
        w.show(); w.raise_(); w.activateWindow()
        if paths:
            w.set_files(paths)
        return w
    w = FullTextWindow(config_dir)
    _OPEN.append(w)
    if paths:
        w.set_files(paths)
    w.show()
    return w
