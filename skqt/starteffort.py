"""Start an effort (3.0.3; 4.79.0 step E2): one short form between an idea and a working effort.

Effort Home shows it whenever no effort is open, and + Add an Effort (All Efforts) and Settings > New effort... open the
same form. It asks two things: Effort name, and Saved in, the folder the effort's own folder is made in (UX decision 184:
chosen by the person, never guessed; 185: never the Effort Backup folder). The effort's folders are made there in the
team's layout (Settings > Folders and file names). Everything else starts at its default and is set on Effort Settings.
After Create effort the effort is open on the Overview. PictureDrop is the effort's picture, used on the Overview banner."""
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QToolButton,
                               QVBoxLayout, QWidget)
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
            D.themed(self, lambda t: f"QToolButton{{border:2px dashed {t['border_strong']};border-radius:14px;background:{t['surface2']};"
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
                p = os.path.normpath(u.toLocalFile()) if u.toLocalFile() else ""
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


def backup_folder(host):
    """The Effort Backup folder ('' when none is chosen)."""
    try:
        return host.safety.backup_dir() or ""
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return ""


def _inside(path, folder):
    if not path or not folder:
        return False
    a, b = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def saved_in_problem(host, folder):
    """'' when the folder can hold a new effort, else one plain sentence (UX decisions 184, 185: chosen by the person,
    never guessed, and never the Effort Backup folder)."""
    f = (folder or "").strip()
    if not f:
        return "Choose where it is saved."
    if not os.path.isdir(f):
        return "That folder is not there. Choose another."
    if _inside(f, backup_folder(host)):
        return "That is the Effort Backup folder, which only mirrors efforts. Choose another folder."
    return ""


def list_path(folder, name):
    """The effort list's file for a new effort saved in folder: its own folder there, in the team's layout."""
    import effortfolders as EF
    try:
        return EF.new_list_path(folder, name, {"Client": "", "Solicitation": "", "Internal": ""})[0]
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return os.path.join(folder, name, f"{name}_Effort_List.xlsx")


class SavedIn(QWidget):
    """Saved in: a folder the person chooses (empty until then) and Choose..."""
    changed = Signal()

    def __init__(self, host):
        super().__init__()
        self.host = host
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
        self.edit = QLineEdit(); self.edit.setPlaceholderText("Choose a folder"); self.edit.setObjectName("savedIn")
        h.addWidget(self.edit, 1)
        self.choose_btn = D.button("Choose...", None, lambda: self.choose(), "The folder the effort's own folder is made in")
        h.addWidget(self.choose_btn)
        self.edit.textChanged.connect(lambda _t: self.changed.emit())

    def folder(self):
        return self.edit.text().strip()

    def choose(self, folder=None):
        """folder (tests): the folder picked. The window opens on the last folder chosen, which is not a choice made
        for the person: Saved in stays empty until a folder is picked."""
        if folder is None:
            import app_gui, datahome
            start = getattr(SavedIn, "_last", "") or datahome.efforts_dir(app_gui.DATA_DIR)
            folder = QFileDialog.getExistingDirectory(self, "Where is the effort saved?", start)
        if folder:
            SavedIn._last = folder
            self.edit.setText(os.path.normpath(folder))
        return self.folder()

    def clear(self):
        self.edit.clear()


class StartEffort(QFrame):
    """The form (4.79.0, step E2): Effort name and Saved in, and Create effort. Everything else starts at its default and
    is set on Effort Settings. On Create effort it makes the effort, opens it on the Overview and calls done(name)."""

    def __init__(self, host, done=None, inline=True):
        super().__init__()
        self.host = host
        self.done = done
        self.setObjectName("startEffort")
        D.themed(self, lambda t: f"QFrame#startEffort{{background:{t['surface']};border:1px solid {t['border']};border-radius:{D.RADIUS['card']}px;}}")
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); outer.setSpacing(D.SPACE["m"])
        head = QLabel("Start an effort"); head.setStyleSheet("font-size:20pt;font-weight:700;background:transparent;")
        outer.addWidget(head)
        form = QFormLayout(); form.setSpacing(D.SPACE["s"]); outer.addLayout(form)
        self.name = QLineEdit(); self.name.setPlaceholderText("Effort name")
        self.saved = SavedIn(host)
        form.addRow("Effort name", self.name)
        form.addRow("Saved in", self.saved)
        self.where = D.label("", "muted"); outer.addWidget(self.where)
        brow = QHBoxLayout(); brow.addStretch(1)
        if inline:
            brow.addWidget(D.button("Open an effort", None, lambda: host.go("efforts"), "Every effort on this PC"))
        self.create_btn = D.button("Create effort", "primary", lambda: self.create())
        brow.addWidget(self.create_btn)
        outer.addLayout(brow)
        self.err = D.label("", "muted"); outer.addWidget(self.err)
        self.name.textChanged.connect(self._named)
        self.saved.changed.connect(self._named)
        self.name.returnPressed.connect(lambda: self.create())
        self._named()

    def path(self):
        n, f = self.name.text().strip(), self.saved.folder()
        return list_path(f, n) if n and f else ""

    def _named(self, *_a):
        """Create effort waits for a name and a folder that can hold it; the line says where its folder will be."""
        n = self.name.text().strip()
        why = saved_in_problem(self.host, self.saved.folder())
        self.create_btn.setEnabled(bool(n) and not why)
        if not n or not self.saved.folder():
            self.where.setText("The effort gets its own folder there, with Customer Documents, Volumes, Response Setup and Exports.")
        elif why:
            self.where.setText(why)
        else:
            self.where.setText(f"Its folder: {os.path.dirname(self.path())}")
        return why

    def reset(self):
        self.name.clear(); self.saved.clear()
        self._named()

    def values(self):
        return {"name": self.name.text().strip(), "path": self.path(), "first_use": "volume"}

    def create(self, values=None):
        v = values or self.values()
        if not v.get("name"):
            self.err.setText("Give the effort a name.")
            self.name.setFocus()
            return None
        why = "" if values else saved_in_problem(self.host, self.saved.folder())
        if why:
            self.err.setText(why)
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
        if v.get("effort_type"):
            import prodrules as PRL
            et = PRL.effort_type_of(PRL.load(host.config_dir), v["effort_type"])
            if et:
                host.ws.set("prod_std", {"effort_type": et["id"], "type": et["default_profile"]})
        __import__("datum").record_start(host.ws, host.config_dir)        # 4.47.1: the Production Datum it was started on
        diag.activity("qt_effort_started", n=sum(1 for k in ("picture", "pm", "due", "client", "solicitation") if v.get(k)))
    except Exception:
        diag.swallowed()
    host.go("overview")
    try:
        host.toast(f"{name} is ready. Next: add the customer's documents in Documents.")
    except Exception:
        pass
    return name


class StartDialog(QDialog):
    """The same form, in a window: + Add an Effort when an effort is open, and Settings > New effort..."""

    def __init__(self, host):
        super().__init__(host)
        self.setWindowTitle("Start an effort")
        self.setMinimumWidth(640)
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
