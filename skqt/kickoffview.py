"""Author kickoff packets in Qt (3.37.0): pick the authors (everyone who leads or writes a section), see how many
sections each has, and make one Word packet per author into a dated folder (kickoff.py). Rules only, no AI."""
import datetime, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QListWidget, QListWidgetItem, QVBoxLayout)
import diag
import kickoff as KO
from . import design as D


def marking_of(host):
    """The effort's marking for the top and bottom of every page, or None."""
    try:
        import branding as BR, effortrec as R
        mk = BR.marking(BR.identity(R.Record(host.ws.root))["sensitivity"])
        return (mk[0], "502B85" if mk[1] == "cui" else "9A4508") if mk else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def record_of(host):
    try:
        import effortrec as R
        return R.Record(host.ws.root) if host.ws is not None else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def make(host, folder=None, names=None):
    """Make the packets (names: the authors, else everyone). Returns [(name, path)]."""
    R = host.review
    if R is None or host.ws is None:
        host.status("Open an effort with a response structure first.")
        return []
    when = datetime.datetime.now()
    if folder is None:
        base = host.out_path("kickoff_packets") if host.effort_path else os.path.dirname(R.M.path)
        folder = QFileDialog.getExistingDirectory(host, "Folder for the kickoff packets", base if os.path.isdir(base or "") else os.path.dirname(base or ""))
        if not folder:
            return []
        folder = os.path.join(folder, f"Kickoff packets {when:%Y-%m-%d %H%M}")
    try:
        out = KO.write_all(folder, record_of(host), R.M, host.effort_name or "", marking_of(host), names=names, when=when)
    except PermissionError:
        host.status("A packet with that name is open in Word. Close it, then make them again.")
        return []
    diag.activity("kickoff_packets_made", n=len(out))
    host.toast(f"Kickoff packets made: {len(out)}")
    return out


class KickoffDialog(QDialog):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Author kickoff packets")
        self.resize(560, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("One Word file per author: for each section they lead or write, the customer's requirements word "
                            "for word with where each is, how it is scored, the objectives, hot buttons and key points captured "
                            "for it, its win themes, open meeting topics, the customer's answers, the page budget and the dates. "
                            "The effort's marking sits at the top and bottom of every page.", "muted"))
        self.list = QListWidget(); v.addWidget(self.list, 1)
        people = KO.authors(host.review.M) if host.review is not None else {}
        for name in sorted(people, key=str.casefold):
            d = people[name]
            it = QListWidgetItem(f"{name}  ·  leads {len(d['lead'])}, writes {len(d['with'])}")
            it.setData(Qt.UserRole, name)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked)
            self.list.addItem(it)
        if not people:
            v.addWidget(D.label("Nobody leads or writes a section yet. Set a section's people in Review (Assigned To) or the "
                                "Structure Builder first.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Make the packets..."); bb.button(QDialogButtonBox.Ok).setEnabled(bool(people))
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def chosen(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]


def open_dialog(host, run=True, folder=None):
    dlg = KickoffDialog(host)
    if run and dlg.exec() != QDialog.Accepted:
        return []
    return make(host, folder, dlg.chosen())
