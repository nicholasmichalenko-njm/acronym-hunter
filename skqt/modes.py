"""The team folder in Qt (work modes, 2.79.0; one setting since 4.24.0): the Settings card (the team folder, who has
which effort open), the badge in the window title and the chip in the top bar, and the warning before opening an effort
someone else has open. Stationkeeper never connects, with a team folder or without.

4.24.0: the first-start question (Offline or Connected) and the SCIF-ready switch are gone. A PC with a team folder is
Connected; one without is Offline. The SCIF edition is its own build; a copy sealed before 4.24.0 stays sealed
(secure.py), and its card stays locked."""
import os
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox
import diag
import secure
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
    """4.24.0: one setting, the team folder. With one, backups and packages go there and the app says who has an effort
    open; with none, everything stays on this PC. The Offline or Connected choice and the SCIF-ready switch are gone
    (the SCIF edition is its own build); a copy sealed before stays sealed."""

    def __init__(self, host):
        super().__init__("Team folder", "The folder the team shares (a OneDrive-synced SharePoint folder). With one, "
                         "backups and packages go there and Stationkeeper says who has an effort open. With none, "
                         "everything stays on this PC. Stationkeeper never connects to a network either way.")
        self.host = host
        self.locked = self.add(D.label("")); self.locked.setWordWrap(True)
        trow = QHBoxLayout()
        self.team_lbl = D.label(""); self.team_lbl.setWordWrap(True); trow.addWidget(self.team_lbl, 1)
        self.team_btn = D.button("Choose the team folder...", None, lambda: self.choose_team()); trow.addWidget(self.team_btn)
        self.none_btn = D.button("Stop using it", None, lambda: self.no_team()); trow.addWidget(self.none_btn)
        self.body.addLayout(trow)
        self.working = self.add(D.label("", "muted")); self.working.setWordWrap(True)
        self.fill()

    def fill(self):
        self.locked.setVisible(secure.ACTIVE)
        if secure.ACTIVE:
            t = D.tokens()
            self.locked.setStyleSheet(f"background:{t['crit_soft']};color:{t['crit']};border-radius:6px;padding:8px;font-weight:600;")
            how = "This is the SCIF build of Stationkeeper." if secure.build_scif() else "This PC was made SCIF-ready (the seal is in the program folder and the data folder)."
            self.locked.setText(f"Locked: SCIF-ready. {how} It writes no logs, keeps no training data and makes no bug reports "
                                "or support files, and it cannot be switched back.")
        team = WM.team_dir(settings())
        self.team_btn.setVisible(not secure.ACTIVE); self.team_lbl.setVisible(not secure.ACTIVE)
        self.none_btn.setVisible(bool(team)); self.working.setVisible(bool(team))
        warn = WM.folder_warning(settings(), team) if team else ""
        self.team_lbl.setText((f"Team folder: {team}" + (f"  {warn}" if warn else "")) if team else "Team folder: none")
        if team:
            ws = WM.working(team)
            self.working.setText(("Open now: " + "; ".join(f"{w.get('effort')} ({w.get('user')}, since {w.get('since', '')[11:16]})"
                                                          for w in ws)) if ws else "Nobody has an effort open from the team folder.")

    def _shown(self):
        self.fill()
        self.host.title()
        if hasattr(self.host, "show_mode_chip"):
            self.host.show_mode_chip()

    def no_team(self):
        """Stop using the team folder: backups and packages stay on this PC. The folder itself is not touched."""
        if secure.ACTIVE:
            return False
        save(team_dir="", work_mode=WM.OFFLINE)
        diag.activity("work_team_folder_cleared")
        self._shown()
        self.host.status("No team folder. Backups and packages stay on this PC; the folder itself was not touched.")
        return True

    def choose_team(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "The team's OneDrive-synced SharePoint folder")
            if not folder:
                return None
        os.makedirs(folder, exist_ok=True)
        if secure.ACTIVE:
            return None
        save(team_dir=os.path.abspath(folder), work_mode=WM.CONNECTED)
        diag.activity("work_team_folder_set")
        warn = WM.folder_warning(settings(), folder)
        self._shown()
        self.host.status(warn or "Team folder set. Backups and packages go there.")
        if self.host.ws is not None:
            self.host.safety.presence()
        return folder
