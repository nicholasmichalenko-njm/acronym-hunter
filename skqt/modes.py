"""Work modes in Qt (2.79.0; three since 2.97.0): the first-start question, the Settings card (Offline, Connected or
SCIF-ready, the steps each mode follows, the team folder, who has which effort open), the badge in the window title and
the chip in the top bar, and the warning before opening an effort someone else has open. Stationkeeper never connects in
any mode.

SCIF-ready is chosen through a confirmation that names what it does and asks the person to type SCIF-READY; it writes the
seal (secure.seal), stops logging at once and, unless unticked, deletes the logs, training data and bug reports kept
before. After that the card is locked: nothing in the app switches it back."""
import os
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QRadioButton, QVBoxLayout)
import diag
import secure
import workmode as WM
from . import design as D

CONFIRM_WORD = "SCIF-READY"


def settings():
    import app_gui
    return app_gui.load_settings() or {}


def save(**kv):
    import app_gui
    st = app_gui.load_settings() or {}
    st.update(kv)
    app_gui.save_settings(st)
    return st


def mode():
    return WM.get(settings())


def badge():
    m = mode()
    return WM.NAMES.get(m, "")


def set_mode(host, m, team=None):
    if secure.ACTIVE and m != WM.SECURED:              # 2.97.0: SCIF-ready is never switched back
        host.status("SCIF-ready cannot be switched back.")
        return settings()
    st = save(work_mode=m, **({"team_dir": os.path.abspath(team)} if team else {}))
    if m == WM.CONNECTED:
        diag.activity("work_mode_set_connected")
    elif m == WM.OFFLINE:
        diag.activity("work_mode_set_offline")
    host.title()
    if m == WM.CONNECTED and host.ws is not None:
        host.safety.presence()
    return st


def ask_mode(host, answer=None):
    """First start: where is this PC used? answer (tests): 'offline' or 'connected'. Returns the mode or ''."""
    if answer is None:
        d = QDialog(host); d.setWindowTitle("Where is Stationkeeper used on this PC?"); d.setMinimumWidth(560)
        v = QVBoxLayout(d)
        v.addWidget(D.label("Stationkeeper works offline in every mode. The choice sets where your backups and packages go "
                            "and which steps the app shows. You can change it in Settings, where SCIF-ready (no logs, no "
                            "training, locked) is also chosen.", "muted"))
        sec = QRadioButton("Offline: this PC on its own, for testing and everyday work on General business, Proprietary "
                           "and CUI documents.")
        con = QRadioButton("Connected: Microsoft 365 with OneDrive. Backups and packages go to the team's OneDrive-synced "
                           "SharePoint folder so the team can pick up the work.")
        for r in (sec, con):
            r.setStyleSheet("QRadioButton { padding: 6px 0; }"); v.addWidget(r)
        (con if WM.suggest() == WM.CONNECTED else sec).setChecked(True)
        v.addWidget(D.label("Suggested: " + WM.NAMES[WM.suggest()] + (" (OneDrive for work is set up on this PC)."
                                                                      if WM.suggest() == WM.CONNECTED else
                                                                      " (OneDrive for work is not set up on this PC)."), "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok); bb.accepted.connect(d.accept); v.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return ""
        answer = WM.CONNECTED if con.isChecked() else WM.OFFLINE
    set_mode(host, answer)
    if answer == WM.CONNECTED and not WM.team_dir(settings()):
        host.status("Connected mode: choose the team folder in Settings > Where Stationkeeper is used.")
    return answer


def warn_open(host, effort, answer=None):
    """Connected mode, before an effort opens: someone else has it open. answer (tests): 'open' or 'cancel'. True: open."""
    team = WM.team_dir(settings())
    other = WM.someone_else(team, effort) if team else None
    if not other:
        return True
    since = other.get("since", "")[11:16]
    text = (f"{other.get('user', 'Someone')} has {effort} open on {other.get('computer', 'another PC')} since {since}. "
            "If you both change it, one of you will have to merge the other's work later. Open it anyway, or ask them to "
            "save its package to the team folder first.")
    host.status(text)
    if answer is None:
        box = QMessageBox(host); box.setWindowTitle("Someone has this effort open"); box.setText(text)
        go = box.addButton("Open anyway", QMessageBox.AcceptRole); box.addButton(QMessageBox.Cancel)
        box.exec()
        answer = "open" if box.clickedButton() is go else "cancel"
    diag.activity("work_presence_warned")
    return answer == "open"


def seal_dialog(host, answer=None):
    """Make this install SCIF-ready for good. answer (tests): (typed text, delete the old logs and training data).
    Returns True when sealed."""
    if secure.ACTIVE:
        return True
    if answer is None:
        d = QDialog(host); d.setWindowTitle("Make Stationkeeper SCIF-ready"); d.setMinimumWidth(620)
        v = QVBoxLayout(d)
        t = D.tokens()
        head = D.label("This cannot be undone.", "title"); head.setStyleSheet(f"color:{t['crit']};"); v.addWidget(head)
        v.addWidget(D.label("SCIF-ready Stationkeeper:", "label"))
        for line in ("writes no logs, not even the content-free ones, from this moment on;",
                     "keeps no training data and sends none (Report misreading and Send training data go away);",
                     "makes no bug reports or support files;",
                     "reads documents at any marking, because the system it runs on is accredited for them;",
                     "cannot be switched back to Offline or Connected. Leaving it takes a fresh copy of the program and a "
                     "new data folder, as your security officer directs."):
            v.addWidget(D.label("\u2022  " + line))
        wipe = QCheckBox("Also delete the logs, training data and bug reports this PC kept before"); wipe.setChecked(True)
        v.addWidget(wipe)
        v.addWidget(D.label(f"Type {CONFIRM_WORD} to confirm:", "label"))
        typed = QLineEdit(); typed.setPlaceholderText(CONFIRM_WORD); v.addWidget(typed)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        go = bb.addButton("Make it SCIF-ready", QDialogButtonBox.AcceptRole); go.setEnabled(False)
        typed.textChanged.connect(lambda txt: go.setEnabled(txt.strip().upper() == CONFIRM_WORD))
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        v.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return False
        answer = (typed.text(), wipe.isChecked())
    text, clear = answer
    if (text or "").strip().upper() != CONFIRM_WORD:
        host.status(f"Not changed: type {CONFIRM_WORD} to make Stationkeeper SCIF-ready.")
        return False
    import app_gui
    base, data = getattr(host, "seal_dirs", None) or (app_gui.BASE_DIR, app_gui.DATA_DIR)
    diag.activity("work_mode_set_scif")                 # the last line this install ever logs
    secure.seal(base, data, clear=clear)
    save(work_mode=WM.SECURED)
    host.title()
    if hasattr(host, "show_mode_chip"):
        host.show_mode_chip()
    host.toast("SCIF-ready. No logs, no training data, no bug reports. This cannot be switched back.")
    return True


class ModeCard(D.Card):
    def __init__(self, host):
        super().__init__("Where Stationkeeper is used", "Offline in every mode. The mode sets where backups and packages go, "
                         "what the app keeps about itself and which steps it shows.")
        self.host = host
        row = QHBoxLayout()
        self.off = QRadioButton("Offline (testing and everyday work)")
        self.con = QRadioButton("Connected (Microsoft 365 with OneDrive)")
        self.sec = QRadioButton("SCIF-ready (no logs, no training, locked)")
        g = QButtonGroup(self)
        for r in (self.off, self.con, self.sec):
            g.addButton(r); row.addWidget(r)
        self.off.toggled.connect(lambda on: on and self.choose(WM.OFFLINE))
        self.con.toggled.connect(lambda on: on and self.choose(WM.CONNECTED))
        self.sec.toggled.connect(lambda on: on and self.choose(WM.SECURED))
        row.addStretch(1)
        self.body.addLayout(row)
        self.locked = self.add(D.label("")); self.locked.setWordWrap(True)
        self.steps = self.add(D.label("")); self.steps.setWordWrap(True)
        trow = QHBoxLayout()
        self.team_lbl = D.label("", "muted"); self.team_lbl.setWordWrap(True); trow.addWidget(self.team_lbl, 1)
        self.team_btn = D.button("Choose the team folder...", None, lambda: self.choose_team()); trow.addWidget(self.team_btn)
        self.body.addLayout(trow)
        self.working = self.add(D.label("", "muted")); self.working.setWordWrap(True)
        self.fill()

    def fill(self):
        m = mode()
        for r, want in ((self.off, WM.OFFLINE), (self.con, WM.CONNECTED), (self.sec, WM.SECURED)):
            r.blockSignals(True); r.setChecked(m == want); r.blockSignals(False)
            r.setEnabled(not secure.ACTIVE)
        self.locked.setVisible(secure.ACTIVE)
        if secure.ACTIVE:
            t = D.tokens()
            self.locked.setStyleSheet(f"background:{t['crit_soft']};color:{t['crit']};border-radius:6px;padding:8px;font-weight:600;")
            how = "This is the SCIF build of Stationkeeper." if secure.build_scif() else "This PC was made SCIF-ready (the seal is in the program folder and the data folder)."
            self.locked.setText(f"Locked: SCIF-ready. {how} It writes no logs, keeps no training data and makes no bug reports "
                                "or support files, and it cannot be switched back.")
        self.steps.setText("\n".join("\u2022  " + s for s in WM.steps(m)))
        team = WM.team_dir(settings())
        con = m == WM.CONNECTED
        self.team_btn.setVisible(con); self.team_lbl.setVisible(con); self.working.setVisible(con)
        if con:
            warn = WM.folder_warning(settings(), team) if team else ""
            self.team_lbl.setText((f"Team folder: {team}" + (f"  {warn}" if warn else "")) if team else
                                  "No team folder yet: choose the OneDrive-synced SharePoint folder the team shares.")
            ws = WM.working(team) if team else []
            self.working.setText(("Open now: " + "; ".join(f"{w.get('effort')} ({w.get('user')}, since {w.get('since', '')[11:16]})"
                                                          for w in ws)) if ws else "Nobody has an effort open from the team folder.")

    def choose(self, m, answer=None):
        """answer (tests): passed to seal_dialog for SCIF-ready."""
        if m == WM.SECURED:
            if not seal_dialog(self.host, answer):
                self.fill()
                return False
        else:
            set_mode(self.host, m)
            self.host.toast(f"{WM.NAMES[m]} mode")
        self.fill()
        if hasattr(self.host, "show_mode_chip"):
            self.host.show_mode_chip()
        return True

    def choose_team(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "The team's OneDrive-synced SharePoint folder")
            if not folder:
                return None
        os.makedirs(folder, exist_ok=True)
        save(team_dir=os.path.abspath(folder))
        diag.activity("work_team_folder_set")
        warn = WM.folder_warning(settings(), folder)
        self.fill()
        self.host.status(warn or "Team folder set. Backups and packages go there.")
        if self.host.ws is not None:
            self.host.safety.presence()
        return folder
