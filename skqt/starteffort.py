"""Start an effort (3.0.3): one short form, with as few steps as possible between an idea and a working effort.

Effort Home shows it whenever no effort is open, and + Add an Effort (All Efforts) and Settings > New effort... open the
same form. The only thing it needs is a name: the picture (click, or drag a file onto it), client, solicitation, due
date and proposal manager are all optional and can be filled in later on Effort Home. The folders are made for you,
in your team's layout (Settings > Folders and file names) under Stationkeeper Data\\Efforts; More options holds the
rest (where the effort list lives, other customer or volume folders, first use, internal number). After Create effort
the effort is open on Effort Home, with the next step offered: add the customer's documents."""
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QToolButton, QVBoxLayout, QWidget)
import diag
from . import design as D

PIC = 132
PIC_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")


class PictureDrop(QToolButton):
    """The effort's picture: click to choose one, or drag a picture file onto it."""
    changed = Signal(str)

    def __init__(self, size=PIC):
        super().__init__()
        self.size_ = size
        self.path = ""
        self.setFixedSize(size, size)
        self.setIconSize(self.size())
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)
        self.clicked.connect(lambda: self.choose())
        self.show_path("")

    def show_path(self, path):
        t = D.tokens()
        self.path = path if path and os.path.isfile(path) else ""
        if self.path:
            pm = QPixmap(self.path).scaled(self.size_, self.size_, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setIcon(QIcon(pm)); self.setText("")
            self.setToolTip("The effort's picture. Click, or drop another picture, to change it.")
            self.setStyleSheet("QToolButton{border:none;background:transparent;}")
        else:
            self.setIcon(QIcon()); self.setText("+\nEffort image\n\nclick or drop\na picture here")
            self.setToolTip("A picture that stands for the effort: a mission patch, a logo or a cover image")
            self.setStyleSheet(f"QToolButton{{border:2px dashed {t['border_strong']};border-radius:14px;background:{t['surface2']};"
                               f"color:{t['muted']};font-weight:600;}} QToolButton:hover{{border-color:{t['accent']};color:{t['accent']};}}")

    def choose(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "The effort's picture", "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path and os.path.splitext(path)[1].lower() in PIC_EXTS and os.path.isfile(path):
            self.show_path(path)
            self.changed.emit(path)
            return True
        return False

    @staticmethod
    def _picture_in(event):
        md = event.mimeData()
        if md.hasUrls():
            for u in md.urls():
                p = u.toLocalFile()
                if p and os.path.splitext(p)[1].lower() in PIC_EXTS:
                    return p
        return ""

    def dragEnterEvent(self, e):
        if self._picture_in(e):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if self._picture_in(e):
            e.acceptProposedAction()

    def dropEvent(self, e):
        p = self._picture_in(e)
        if p:
            self.choose(p)
            e.acceptProposedAction()


class StartEffort(QFrame):
    """The form. host: the main window. On Create effort it makes the effort, opens it and calls done(name)."""

    def __init__(self, host, done=None, inline=True):
        super().__init__()
        self.host = host
        self.done = done
        self.setObjectName("startEffort")
        t = D.tokens()
        self.setStyleSheet(f"QFrame#startEffort{{background:{t['surface']};border:1px solid {t['border']};border-radius:{D.RADIUS['card']}px;}}")
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); outer.setSpacing(D.SPACE["m"])
        head = QLabel("Start an effort"); head.setStyleSheet("font-size:20pt;font-weight:700;background:transparent;")
        outer.addWidget(head)
        outer.addWidget(D.label("Give it a name and press Create effort. Everything else is optional and can be filled in later "
                                "on Effort Home.", "muted"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["xl"]); outer.addLayout(row)
        self.pic = PictureDrop(); row.addWidget(self.pic, 0, Qt.AlignTop)
        form = QFormLayout(); form.setSpacing(D.SPACE["s"]); row.addLayout(form, 1)
        self.name = QLineEdit(); self.name.setPlaceholderText("Kestrel Thermal")
        self.client = QLineEdit(); self.client.setPlaceholderText("U.S. Space Force, Space Systems Command")
        self.sol = QLineEdit(); self.sol.setPlaceholderText("FA8810-26-R-0042")
        self.due = QLineEdit(); self.due.setPlaceholderText("December 15, 2026, 2:00 PM")
        self.zone = QComboBox()
        import tzones as TZ
        self.zone.addItem("Time zone as written, or mine", "")
        for k in ("ET", "CT", "MT", "AZ", "PT", "AK", "HI", "UTC"):
            if k in TZ.ZONES:
                self.zone.addItem(f"{TZ.ZONES[k][0]} ({k})", k)
        drow = QHBoxLayout(); drow.addWidget(self.due, 1); drow.addWidget(self.zone)
        self.pm = QComboBox(); self.pm.setEditable(True)
        try:
            import authorlist as AL
            self.pm.addItems([""] + AL.load(host.config_dir).names())
        except Exception:
            diag.swallowed()
        self.pm.setCurrentText("")
        form.addRow("Effort name", self.name)
        form.addRow("Client", self.client)
        form.addRow("Solicitation number", self.sol)
        form.addRow("Proposals due", drow)
        form.addRow("Proposal manager", self.pm)
        # More options
        self.more_btn = D.button("More options", "ghost", self.toggle_more)
        outer.addWidget(self.more_btn, 0, Qt.AlignLeft)
        self.more = QWidget(); mf = QFormLayout(self.more); mf.setContentsMargins(0, 0, 0, 0)
        self.path = QLineEdit(); self.path.setReadOnly(False)
        prow = QHBoxLayout(); prow.addWidget(self.path, 1)
        prow.addWidget(D.button("Change...", None, self.choose_path))
        self.cust, self.vols, self.internal = QLineEdit(), QLineEdit(), QLineEdit()
        self.cust.setPlaceholderText("Blank: the effort's own Customer Documents folder")
        self.vols.setPlaceholderText("Blank: the effort's own Volumes folder")
        self.rule = QComboBox()
        import effort as E
        for k, lab in E.FIRST_USE_RULES.items():
            self.rule.addItem(lab, k)
        mf.addRow("Effort list file", prow)
        mf.addRow("Customer documents folder", self._folder(self.cust, "Customer documents folder"))
        mf.addRow("Volumes folder", self._folder(self.vols, "Volumes folder"))
        mf.addRow("First use of an acronym", self.rule)
        mf.addRow("Internal number", self.internal)
        self.more.setVisible(False)
        outer.addWidget(self.more)
        self.where = D.label("", "muted"); outer.addWidget(self.where)
        brow = QHBoxLayout(); brow.addStretch(1)
        if inline:
            brow.addWidget(D.button("Open an effort", None, lambda: host.go("efforts"), "Every effort on this PC"))
        self.create_btn = D.button("Create effort", "primary", lambda: self.create())
        brow.addWidget(self.create_btn)
        outer.addLayout(brow)
        self.err = D.label("", "muted"); outer.addWidget(self.err)
        self._path_set_by_hand = False
        self.name.textChanged.connect(self._named)
        self.client.textChanged.connect(self._named)
        self.sol.textChanged.connect(self._named)
        self.path.textEdited.connect(lambda _t: setattr(self, "_path_set_by_hand", True))
        self.name.returnPressed.connect(lambda: self.create())
        self._named()

    def _folder(self, edit, title):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.addWidget(edit, 1)
        h.addWidget(D.button("Browse...", None, lambda: (lambda p: edit.setText(p) if p else None)(
            QFileDialog.getExistingDirectory(self, title, edit.text()))))
        return w

    def toggle_more(self):
        self.more.setVisible(not self.more.isVisible())
        self.more_btn.setText("Fewer options" if self.more.isVisible() else "More options")

    def base(self):
        import app_gui, datahome
        return datahome.efforts_dir(app_gui.DATA_DIR)

    def _named(self, *_a):
        """The effort list's place follows the name, in the team's folder layout, unless chosen by hand."""
        n = self.name.text().strip()
        self.create_btn.setEnabled(bool(n))
        if self._path_set_by_hand:
            return
        if not n:
            self.path.setText("")
            self.where.setText("The effort gets its own folder with Customer Documents, Volumes, Response Setup and Exports.")
            return
        try:
            import effortfolders as EF
            p = EF.new_list_path(self.base(), n, {"Client": self.client.text(), "Solicitation": self.sol.text(),
                                                  "Internal": self.internal.text()})[0]
        except Exception:
            diag.swallowed()
            p = os.path.join(self.base(), n, f"{n}_Effort_List.xlsx")
        self.path.setText(p)
        self.where.setText(f"Its folder: {os.path.dirname(p)}  (More options to change)")

    def choose_path(self):
        p, _ = QFileDialog.getSaveFileName(self, "Where should the effort list live?", self.path.text(), "Excel (*.xlsx)")
        if p:
            self.path.setText(p); self._path_set_by_hand = True
            self.where.setText(f"Its folder: {os.path.dirname(p)}")

    def reset(self):
        for e in (self.name, self.client, self.sol, self.due, self.cust, self.vols, self.internal):
            e.clear()
        self.pm.setCurrentText(""); self.zone.setCurrentIndex(0); self.pic.show_path("")
        self._path_set_by_hand = False
        self._named()

    def values(self):
        return {"name": self.name.text().strip(), "path": self.path.text().strip(), "first_use": self.rule.currentData(),
                "customer_dir": self.cust.text().strip(), "volumes_dir": self.vols.text().strip(),
                "client": self.client.text().strip(), "solicitation": self.sol.text().strip(),
                "internal_no": self.internal.text().strip(), "picture": self.pic.path,
                "pm": self.pm.currentText().strip(), "due": self.due.text().strip(), "zone_key": self.zone.currentData() or ""}

    def create(self, values=None):
        v = values or self.values()
        if not v.get("name"):
            self.err.setText("Give the effort a name.")
            self.name.setFocus()
            return None
        name = start_effort(self.host, v)
        if not name:
            self.err.setText(self.host.statusBar().currentMessage() or "The effort was not created.")
            return None
        self.err.setText("")
        self.reset()
        if self.done:
            self.done(name)
        return name


def _noop():
    pass


def start_effort(host, v):
    """Make the effort (folders, list, registry), open it, then put in what was given: picture, proposal manager, due
    date. Returns the name, or None."""
    name = host.settings_page.new_effort({k: v.get(k, "") for k in ("name", "path", "first_use", "customer_dir",
                                                                     "volumes_dir", "client", "solicitation", "internal_no")})
    if not name:
        return None
    try:
        import branding as BR, effortrec as RR
        root = host.ws.root
        if v.get("picture"):
            BR.set_picture(root, v["picture"])
        rec = RR.Record(root)
        if v.get("pm"):
            BR.set_identity(rec, pm=v["pm"])
        if v.get("due"):
            iso, zone = RR.parse_due_text(v["due"])
            if iso:
                rec.set_due(iso, zone, zone_key=v.get("zone_key") or None)
            else:
                host.status("The due date was not understood; set it on Effort Home.")
        diag.activity("qt_effort_started", n=sum(1 for k in ("picture", "pm", "due", "client", "solicitation") if v.get(k)))
    except Exception:
        diag.swallowed()
    host.go("home")
    try:
        host.toast(f"{name} is ready. Next: add the customer's documents in Library.")
    except Exception:
        pass
    return name


class StartDialog(QDialog):
    """The same form, in a window: + Add an Effort when an effort is open, and Settings > New effort..."""

    def __init__(self, host):
        super().__init__(host)
        self.setWindowTitle("Start an effort")
        self.setMinimumWidth(820)
        self.made = None
        lay = QVBoxLayout(self)
        self.form = StartEffort(host, done=self._done, inline=False)
        lay.addWidget(self.form)

    def _done(self, name):
        self.made = name
        self.accept()


def start_dialog(host):
    dlg = StartDialog(host)
    dlg.form.name.setFocus()
    dlg.exec()
    return dlg.made
