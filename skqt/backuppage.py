"""Effort Backup (4.61.0; Nicholas 2026-11-23: "you click on that, and that's where you can view the current backup",
"change the file location"). One page at the foot of the menu: where the backups go and when the last one was, with
Back up now as the main button, then Change the folder, Open the folder and Put back an earlier copy. It does nothing
of its own: the folder is the one Settings keeps (settingspage.set_backup), the backup is safety.backup_now, and
putting a copy back is the record page's list of earlier copies. Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtWidgets import QVBoxLayout, QWidget

import diag
from . import design as D
from .commandbar import CommandBar


class BackupPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.bar.primary("Back up now", lambda: self.backup_now(), "Copy the open effort to the backup folder now")
        self.bar.add("Change the folder...", lambda: self.change_folder(), "Where every effort's backup is kept")
        self.bar.add("Open the folder", lambda: self.open_folder(), "The backup folder in File Explorer")
        self.bar.add("Put back an earlier copy...", lambda: self.host.record_page.restore_dialog(),
                     "What you have now is kept as a copy first")
        self.bar.more("Open the backups folder", lambda: self.host.record_page.open_backups(),      # 4.30.1: the app data folder is hidden
                      "The copies kept in this effort's own data, opened in File Explorer (that folder is hidden there)")
        v.addWidget(self.bar)
        self.card = D.Card("Where the backup is")
        self.where = self.card.add(D.label("", "body")); self.where.setWordWrap(True)
        self.text = self.card.add(D.label("", "muted")); self.text.setWordWrap(True)
        v.addWidget(self.card); v.addStretch(1)

    def folder(self):
        return self.host.safety.backup_dir()

    def refresh(self):
        d = self.folder()
        self.where.setText(d or "No backup folder is chosen.")
        self.text.setText(self.host.safety.status_text())
        return d

    def backup_now(self):
        if not self.folder():
            self.host.status("Choose the backup folder first.")
            return None
        out = self.host.safety.backup_now(wait=True, force=True)
        diag.activity("qt_backup_page_now")
        self.refresh()
        return out

    def change_folder(self, folder=None):
        """folder (tests): the folder picked."""
        out = self.host.settings_page.set_backup(folder)
        self.refresh()
        return out

    def open_folder(self, open_it=True):
        d = self.folder()
        if not d or not os.path.isdir(d):
            self.host.status("No backup folder is chosen." if not d else "The backup folder is not there: " + d)
            return ""
        if open_it and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        return d
