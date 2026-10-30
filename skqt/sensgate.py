"""Sensitivity gates in Qt (2.97.0).

- spill_stop: a document marked above CUI on an install that is not SCIF-ready. Everything stops, nothing is copied,
  and the person is told to leave the file where it is and follow the site's spillage procedure.
- training_gate: before the Trainer opens a document or picture, or gathers a past compliance matrix. A file marked above
  CUI is refused. A file with no label or marking the app can read needs its level declared once (General business,
  Proprietary, CUI, or above CUI, which is refused); the answer is kept for those file contents on this PC.
Rules only (No AI); nothing leaves the PC.
"""
import json, os
from PySide6.QtWidgets import QButtonGroup, QDialog, QDialogButtonBox, QMessageBox, QRadioButton, QVBoxLayout
import diag
import sensitivity as S
from . import design as D

DECLARE = (("General business (not sensitive)", S.GB), ("Proprietary (company or business sensitive)", S.PROP),
           ("CUI (Controlled Unclassified Information)", S.CUI),
           ("Above CUI (Confidential, Secret, Top Secret)", S.CONF))


def spill_stop(host, ex):
    """Say it plainly; a box unless running tests. Returns the text."""
    text = ex.text() if hasattr(ex, "text") else S.spill_text(getattr(ex, "name", "This file"), getattr(ex, "info", {"level": S.CONF, "why": ""}))
    host.last_spill = text
    try:
        host.status(text)
    except Exception:
        diag.swallowed()
    if not os.environ.get("AH_TEST"):
        QMessageBox.critical(host if hasattr(host, "isVisible") else None, "Stop: marked above CUI", text)
    return text


# ------------------------------------------------------------------ levels declared for unmarked files (Trainer)
def _store():
    import app_gui
    return os.path.join(app_gui.CONFIG_DIR, "training_declared.json")


def declared(sha):
    try:
        with open(_store(), encoding="utf-8") as f:
            d = json.load(f)
        v = d.get(sha)
        return v if isinstance(v, int) else -1
    except (OSError, ValueError, AttributeError):
        return -1


def declare(sha, level):
    p = _store()
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except (OSError, ValueError):
        d = {}
    d[sha] = int(level)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, p)


class DeclareDialog(QDialog):
    def __init__(self, parent, fname):
        super().__init__(parent)
        self.setWindowTitle("What is this file's sensitivity?")
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"{fname} carries no sensitivity label or marking that Stationkeeper can read (pictures never "
                            "do). Training takes only General business, Proprietary and CUI. Choose what it is; your "
                            "answer is kept for this file on this PC.", "muted"))
        self.g = QButtonGroup(self)
        for k, (text, level) in enumerate(DECLARE):
            r = QRadioButton(text); r.setStyleSheet("QRadioButton { padding: 4px 0; }")
            self.g.addButton(r, level); v.addWidget(r)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def level(self):
        return self.g.checkedId() if self.g.checkedButton() is not None else -1


def training_gate(parent, path, answer=None, say=None):
    """True when training may use the file. answer (tests): the level to declare when one is asked for (-1: cancel).
    say(text): where the reason goes (the Trainer's status line)."""
    import secure
    say = say or (lambda _t: None)
    fname = os.path.basename(path)
    if secure.ACTIVE:
        say("SCIF-ready: Stationkeeper keeps no training data.")
        return False
    info = S.of_document(path)
    if info["level"] > S.TRAINING_MAX:
        diag.activity("training_refused_marked")
        say(f"Not opened for training: {fname} is marked {S.name(info['level']).upper()} ({info['why']}). Training never "
            "takes anything above CUI. Leave the file where it is and follow your site's spillage procedure.")
        return False
    if info["level"] >= 0:
        return True
    import docversions as DV
    try:
        sha = DV.sha256(path)
    except OSError:
        return False
    lv = declared(sha)
    if lv < 0:
        if answer is None:
            dlg = DeclareDialog(parent, fname)
            lv = dlg.level() if dlg.exec() == QDialog.Accepted else -1
        else:
            lv = answer
        if lv < 0:
            say(f"{fname} was not opened: its sensitivity was not chosen.")
            return False
        declare(sha, lv)
        diag.activity("training_level_declared")
    if lv > S.TRAINING_MAX:
        diag.activity("training_refused_declared")
        say(f"Not opened for training: {fname} is above CUI. Training never takes anything above CUI.")
        return False
    return True


def training_lines(lines, say=None):
    """The Trainer read words that carry a marking above CUI (a picture of a classified page): False, and why."""
    lv, why = S.markings(lines)
    if lv > S.TRAINING_MAX:
        diag.activity("training_refused_marked")
        (say or (lambda _t: None))(f"Stop: the words read here are marked {S.name(lv).upper()} ({why}). Nothing was kept. "
                                   "Training never takes anything above CUI.")
        return False
    return True
