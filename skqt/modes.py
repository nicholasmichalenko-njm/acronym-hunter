"""Work modes in Qt (2.79.0): the first-start question, the Settings card (Secured or Connected, the steps each mode
follows, the team folder, who has which effort open), the badge in the window title, and the warning before opening an
effort someone else has open. Stationkeeper never connects in either mode."""
import os
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                               QRadioButton, QVBoxLayout)
import diag
import workmode as WM
from . import design as D


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
    st = save(work_mode=m, **({"team_dir": os.path.abspath(team)} if team else {}))
    if m == WM.SECURED:
        diag.activity("work_mode_set_secured")
    else:
        diag.activity("work_mode_set_connected")
    host.title()
    if m == WM.CONNECTED and host.ws is not None:
        host.safety.presence()
    return st


def ask_mode(host, answer=None):
    """First start: where is this PC used? answer (tests): 'secured' or 'connected'. Returns the mode or ''."""
    if answer is None:
        d = QDialog(host); d.setWindowTitle("Where is Stationkeeper used on this PC?"); d.setMinimumWidth(560)
        v = QVBoxLayout(d)
        v.addWidget(D.label("Stationkeeper works offline in both. The choice sets where your backups and packages go and "
                            "which steps the app shows. You can change it in Settings.", "muted"))
        sec = QRadioButton("Secured: a SCIF or any closed network. Files stay on this PC or go through your site's "
                           "approved transfer process.")
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
        answer = WM.CONNECTED if con.isChecked() else WM.SECURED
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


class ModeCard(D.Card):
    def __init__(self, host):
        super().__init__("Where Stationkeeper is used", "Offline in both. The mode sets where backups and packages go, what "
                         "the app warns about and which steps it shows.")
        self.host = host
        row = QHBoxLayout()
        self.sec = QRadioButton("Secured (SCIF or closed network)"); self.con = QRadioButton("Connected (Microsoft 365 with OneDrive)")
        g = QButtonGroup(self); g.addButton(self.sec); g.addButton(self.con)
        self.sec.toggled.connect(lambda on: on and self.choose(WM.SECURED))
        self.con.toggled.connect(lambda on: on and self.choose(WM.CONNECTED))
        row.addWidget(self.sec); row.addWidget(self.con); row.addStretch(1)
        self.body.addLayout(row)
        self.steps = self.add(D.label("")); self.steps.setWordWrap(True)
        trow = QHBoxLayout()
        self.team_lbl = D.label("", "muted"); self.team_lbl.setWordWrap(True); trow.addWidget(self.team_lbl, 1)
        self.team_btn = D.button("Choose the team folder...", None, lambda: self.choose_team()); trow.addWidget(self.team_btn)
        self.body.addLayout(trow)
        self.working = self.add(D.label("", "muted")); self.working.setWordWrap(True)
        self.fill()

    def fill(self):
        m = mode()
        for r, want in ((self.sec, WM.SECURED), (self.con, WM.CONNECTED)):
            r.blockSignals(True); r.setChecked(m == want); r.blockSignals(False)
        self.steps.setText("\n".join("•  " + s for s in WM.steps(m)))
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

    def choose(self, m):
        set_mode(self.host, m)
        self.fill()
        self.host.toast(f"{WM.NAMES[m]} mode")

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
