"""Settings in Qt (2.66.0): start a new effort (its acronym list workbook, the first-use rule, its customer documents
and volumes folders), change the open effort's folders and first-use rule, load a new master database, and choose
where backups go (Keep safe). The same files and settings the classic window uses. Nothing leaves the PC."""
import os, re
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QVBoxLayout,
                               QWidget)
import diag
import effort as E
from . import design as D


def _folder_row(edit, parent, title):
    row = QHBoxLayout(); row.addWidget(edit, 1)
    row.addWidget(D.button("Browse...", None, lambda: (lambda d: edit.setText(d) if d else None)(QFileDialog.getExistingDirectory(parent, title))))
    return row


class SettingsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.eff = D.Card("Efforts", "One effort per proposal: its acronym list workbook, records and compliance files.",
                          actions=[D.button("New effort...", "primary", lambda: self.new_effort())])
        f = QFormLayout(); self.eff.body.addLayout(f)
        self.cust = QLineEdit(); self.vols = QLineEdit()
        self.rule = QComboBox()
        for k, lab in E.FIRST_USE_RULES.items():
            self.rule.addItem(lab, k)
        f.addRow("Customer documents folder", _folder_row(self.cust, self, "Customer documents folder"))
        f.addRow("Volumes folder (our Word files)", _folder_row(self.vols, self, "Volumes folder"))
        f.addRow("First use of an acronym", self.rule)
        self.eff.body.addWidget(D.button("Save for this effort", None, lambda: self.save_effort()))
        v.addWidget(self.eff)
        self.db = D.Card("Master database", "The company's acronyms, abbreviations, units and symbols, shared by every effort on this PC.",
                         actions=[D.button("Load a new version...", None, lambda: self.load_master())])
        self.db_text = self.db.add(D.label("", "muted"))
        v.addWidget(self.db)
        self.bk = D.Card("Backups (Keep safe)", "Every open effort is backed up to this folder: the latest, and one copy a day.",
                         actions=[D.button("Choose the folder...", None, lambda: self.set_backup()), D.button("Turn off", "ghost", lambda: self.set_backup(""))])
        self.bk_text = self.bk.add(D.label("", "muted"))
        v.addWidget(self.bk)
        v.addStretch(1)

    def refresh(self):
        h = self.host
        info = (h.efforts.get(h.effort_name) or {}) if h.ws is not None else {}
        for w in (self.cust, self.vols, self.rule):
            w.setEnabled(h.ws is not None)
        self.cust.setText(info.get("customer_dir", "")); self.vols.setText(info.get("volumes_dir", ""))
        self.rule.setCurrentIndex(max(0, self.rule.findData(info.get("first_use", "volume"))))
        try:
            import master_db as MD
            self.db_text.setText(MD.info_text())
        except Exception:
            diag.swallowed()
        bd = self.backup_dir()
        self.bk_text.setText(f"Backups go to {bd}." if bd else "Backups are off.")

    # ------------------------------------------------------------ efforts
    def new_effort(self, values=None):
        """Create an effort and open it. values (tests): name, path, first_use, customer_dir, volumes_dir, client, solicitation,
        internal_no."""
        h = self.host
        if values is None:
            dlg = QDialog(self); dlg.setWindowTitle("New effort"); dlg.setMinimumWidth(640)
            form = QFormLayout(dlg)
            name = QLineEdit(); path = QLineEdit()
            desk = os.path.join(os.path.expanduser("~"), "Desktop")
            base = desk if os.path.isdir(desk) else os.path.expanduser("~")
            path.setText(os.path.join(base, "Effort_List.xlsx"))

            def named(t):
                n = re.sub(r"[^A-Za-z0-9 _.-]+", "", t).strip().replace(" ", "_")
                if n:
                    path.setText(os.path.join(base, n, f"{n}_Effort_List.xlsx"))
            name.textChanged.connect(named)
            pr = QHBoxLayout(); pr.addWidget(path, 1)
            pr.addWidget(D.button("Browse...", None, lambda: (lambda p: path.setText(p) if p else None)(
                QFileDialog.getSaveFileName(dlg, "Where should the effort list live?", path.text(), "Excel (*.xlsx)")[0])))
            rule = QComboBox()
            for k, lab in E.FIRST_USE_RULES.items():
                rule.addItem(lab, k)
            cust, vols, client, sol, internal = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
            form.addRow("Effort name", name); form.addRow("List file", pr)
            form.addRow("", D.label("Tip: a OneDrive-synced SharePoint folder lets the team see the same list.", "muted"))
            form.addRow("First use", rule)
            form.addRow("Customer documents folder", _folder_row(cust, dlg, "Customer documents folder"))
            form.addRow("Volumes folder", _folder_row(vols, dlg, "Volumes folder"))
            form.addRow("Client (short name)", client); form.addRow("Solicitation number", sol); form.addRow("Internal number", internal)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Create effort")
            bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); form.addRow(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            values = {"name": name.text().strip(), "path": path.text().strip(), "first_use": rule.currentData(), "customer_dir": cust.text().strip(),
                      "volumes_dir": vols.text().strip(), "client": client.text().strip(), "solicitation": sol.text().strip(),
                      "internal_no": internal.text().strip()}
        name, path = values.get("name", ""), values.get("path", "")
        if not name or not path.lower().endswith(".xlsx"):
            h.status("Give the effort a name and an .xlsx file for its list.")
            return None
        if name in h.efforts.names():
            h.status("An effort with that name already exists. Pick it in the Effort box.")
            return None
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            L = E.EffortList(path, name, values.get("first_use", "volume")).load()
            L.name = name
            L.client, L.solicitation, L.internal_no = values.get("client", ""), values.get("solicitation", ""), values.get("internal_no", "")
            if not os.path.isfile(path):
                L.pending = True
                L.save()
        except Exception as ex:
            diag.swallowed()
            h.status(f"Could not create the list: {type(ex).__name__}")
            return None
        h.efforts.put(name, path=path, first_use=values.get("first_use", "volume"),
                      **{k: values.get(k, "") for k in ("customer_dir", "volumes_dir", "client", "solicitation", "internal_no")})
        diag.activity("qt_effort_created")
        h.fill_efforts()
        h.open_effort(name)
        h.effort_box.setCurrentText(name)
        return name

    def save_effort(self):
        h = self.host
        if h.ws is None:
            return False
        rule = self.rule.currentData()
        h.efforts.put(h.effort_name, customer_dir=self.cust.text().strip(), volumes_dir=self.vols.text().strip(), first_use=rule)
        try:
            L = E.EffortList(h.effort_path, h.effort_name).load()
            if L.first_use != rule:
                L.first_use = rule; L.pending = True; L.save()
        except Exception:
            diag.swallowed()
            h.status("The effort list is open in Excel: the first-use rule is saved when it closes.")
        s = h.acronym_page.session
        if s is not None and s.effort is not None:
            s.effort.first_use = rule
        diag.activity("qt_effort_settings_saved")
        h.toast("Saved for this effort")
        return True

    # ------------------------------------------------------------ master database
    def load_master(self, path=None):
        import master_db as MD
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, MD.MASTER_NAME, "", "Database (*.csv *.xlsx);;Acronym lists (*.docx *.pdf *.txt);;All files (*.*)")
            if not path:
                return None
        try:
            info = MD.load_master(path)
        except ValueError:
            self.host.status(f"No terms were found in {os.path.basename(path)}. The file needs a column headed Term (or Acronym), "
                             "with Definition beside it.")
            return None
        except PermissionError:
            self.host.status(f"{os.path.basename(path)} is open in Excel. Close it and try again.")
            return None
        diag.activity("master_loaded", rows=info["rows"], added=info["added"], removed=info["removed"])
        self.refresh()
        self.host.toast(f"Master database version {info['version']}: {info['added']} new, {info['removed']} removed. Scan again to use it.")
        return info

    # ------------------------------------------------------------ backups
    def backup_dir(self):
        try:
            import app_gui
            return (app_gui.load_settings() or {}).get("backup_dir", "") or ""
        except Exception:
            diag.swallowed()
            return ""

    def set_backup(self, folder=None):
        import app_gui
        import keepsafe as K
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for backups", self.backup_dir() or K.default_backup_dir())
            if not folder:
                return None
        st = app_gui.load_settings() or {}
        if folder:
            os.makedirs(folder, exist_ok=True)
        st["backup_dir"] = os.path.abspath(folder) if folder else ""
        app_gui.save_settings(st)
        if folder:
            diag.activity("backup_location_set")
        else:
            diag.activity("backup_location_off")
        self.refresh()
        return st["backup_dir"]
