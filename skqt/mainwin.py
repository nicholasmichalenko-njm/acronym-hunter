"""The Qt edition's main window (2.59.0): the effort (picked from the efforts on this PC, held with the same lock as
the tkinter edition), the steps of Compliance that are in Qt so far (Read RFP, Assign), the status line, and autosave
of the compliance matrix two seconds after each change."""
import os
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)
import diag
import compliance as C
import effort as E
import setupdoc as SD
import workspace as W
import assign_ops as AO
from .readpage import ReadPage
from .assign import AssignPage


class MainWindow(QMainWindow):
    def __init__(self, app, config_dir, version=""):
        super().__init__()
        self.app = app
        self.config_dir = config_dir
        self.version = version
        self.efforts = E.Registry(os.path.join(config_dir, "efforts.json"))
        self.ws = None
        self.effort_name = ""
        self.effort_path = ""
        self.review = None
        self.resize(1600, 1000)
        top = QWidget(); tv = QVBoxLayout(top); tv.setContentsMargins(0, 0, 0, 0); tv.setSpacing(0)
        bar = QWidget(); bh = QHBoxLayout(bar); bh.setContentsMargins(10, 6, 10, 6)
        bh.addWidget(QLabel("Effort:"))
        self.effort_box = QComboBox(); self.effort_box.setMinimumWidth(240)
        self.effort_box.activated.connect(lambda i: self.open_effort(self.effort_box.itemText(i)))
        bh.addWidget(self.effort_box)
        bh.addSpacing(24)
        self.steps = QButtonGroup(self)
        self.step_btns = {}
        for key, text in (("read", "1  Read RFP"), ("assign", "2  Assign")):
            b = QPushButton(text); b.setObjectName("step"); b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            self.steps.addButton(b); self.step_btns[key] = b
            bh.addWidget(b)
        later = QLabel("   Structure, Matrix and the rest of the app: in Stationkeeper (classic) until they move to Qt.")
        later.setObjectName("muted")
        bh.addWidget(later)
        bh.addStretch(1)
        tv.addWidget(bar)
        self.stack = QStackedWidget()
        self.read_page = ReadPage(self)
        self.assign_page = AssignPage(self)
        self.stack.addWidget(self.read_page)
        self.stack.addWidget(self.assign_page)
        tv.addWidget(self.stack, 1)
        self.setCentralWidget(top)
        self.save_timer = QTimer(self, singleShot=True, interval=2000, timeout=self.save_now)
        self.lock_timer = QTimer(self, interval=60000, timeout=lambda: self.ws.refresh_lock() if self.ws else None)
        self.lock_timer.start()
        self.fill_efforts()
        self.title()

    # ------------------------------------------------------------ efforts
    def fill_efforts(self):
        names = [n for n in self.efforts.names() if not (self.efforts.get(n) or {}).get("archived")]
        self.effort_box.clear()
        self.effort_box.addItems(names)
        cur = self.efforts.current
        if cur in names:
            self.effort_box.setCurrentText(cur)

    def open_effort(self, name, force=False):
        """Hold the effort (the same lock as the tkinter edition) and open its compliance matrix. Returns True."""
        info = self.efforts.get(name) or {}
        if not info.get("path"):
            return False
        self.close_effort()
        ws = W.Workspace(W.data_dir_for(info["path"]), name)
        if not ws.acquire_lock(force=force):
            who = ws.locked_by or {}
            QMessageBox.information(self, "Effort open elsewhere", f"{name} is open in another window"
                                    + (f" ({who.get('user', '')} on {who.get('computer', '')})" if who else "")
                                    + ". Close it there first: both editions work on the same files.")
            self.fill_efforts()
            return False
        self.ws, self.effort_name, self.effort_path = ws, name, info["path"]
        diag.activity("qt_effort_opened")
        p = ws.get("compliance_path") or ""
        if p and os.path.isfile(p):
            try:
                self.set_matrix(C.Matrix(p).load())
            except Exception:
                diag.swallowed()
                self.status("The compliance matrix could not be opened.")
        else:
            self.review = None
            self.assign_page.load()
        self.read_page.refresh()
        self.go("assign" if self.review is not None and self.review.M.items else "read")
        self.title()
        return True

    def close_effort(self):
        self.save_now()
        if self.ws is not None:
            try:
                self.ws.release_lock()
            except Exception:
                diag.swallowed()
        self.ws, self.review = None, None

    def set_matrix(self, M, new=False):
        self.review = AO.Review(M)
        SD.setup_of(M)
        if self.ws is not None:
            self.ws.set("compliance_path", M.path)
        if new:
            self.save_now()
        self.assign_page.load()
        self.title()

    def people(self):
        names = SD.people(self.review.M) if self.review else []
        return names

    # ------------------------------------------------------------ saving
    def changed(self):
        if self.review is not None:
            self.review.M.pending = True
            self.save_timer.start()
        self.title()

    def save_now(self):
        self.save_timer.stop()
        if self.review is not None and self.review.M.pending:
            try:
                self.review.M.save()
                self.review.M.pending = False
            except PermissionError:
                self.status("The matrix is open in Excel: close it there, and it is saved again in two seconds.")
                self.save_timer.start()
            except Exception:
                diag.swallowed()
                self.status("The matrix could not be saved.")
        self.title()

    # ------------------------------------------------------------ the rest
    def go(self, step):
        if step == "read":
            self.read_page.refresh()
        self.stack.setCurrentWidget(self.read_page if step == "read" else self.assign_page)
        self.step_btns[step].setChecked(True)

    def status(self, text):
        self.statusBar().showMessage(text, 9000)

    def title(self):
        dirty = self.review is not None and self.review.M.pending
        self.setWindowTitle(("* " if dirty else "") + (f"{self.effort_name}: " if self.effort_name else "")
                            + f"Stationkeeper (Qt) {self.version}".strip())

    def closeEvent(self, e):
        self.assign_page.save_notes()
        self.close_effort()
        e.accept()
