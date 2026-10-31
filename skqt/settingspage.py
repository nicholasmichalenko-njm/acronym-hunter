"""Settings in Qt (2.66.0): start a new effort (its acronym list workbook, the first-use rule, its customer documents
and volumes folders), change the open effort's folders and first-use rule, load a new master database, and choose
where backups go (Keep safe). The same files and settings the classic window uses. Nothing leaves the PC."""
import os, re
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)
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
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame)   # 2.76.0: more cards than fit
        inner = QWidget(); inner.setObjectName("page"); sc.setWidget(inner); outer.addWidget(sc)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        from .modes import ModeCard                      # 2.79.0: Secured or Connected
        self.mode = ModeCard(host)
        v.addWidget(self.mode)
        import tzones as TZ                              # 2.92.0: your own time zone (the submission's is the effort's)
        self.tz_card = D.Card("Your time zone", "Where you are. Effort Home shows a deadline in the customer's time zone and "
                              "in yours; calendar times show in yours too. Yours alone, on this PC.")
        trow = QHBoxLayout(); self.tz_card.body.addLayout(trow)
        self.tz = QComboBox()
        for k, text in TZ.choices():
            self.tz.addItem(text, k)
        self.tz_other = QLineEdit(); self.tz_other.setPlaceholderText("Elsewhere: UTC+01:00"); self.tz_other.setMaximumWidth(180)
        trow.addWidget(self.tz); trow.addWidget(self.tz_other)
        trow.addWidget(D.button("Save", "primary", lambda: self.save_zone())); trow.addStretch(1)
        self.tz_note = self.tz_card.add(D.label("", "muted"))
        v.addWidget(self.tz_card)
        self.fill_zone()
        self.eff = D.Card("Efforts", "One effort per proposal: its acronym list workbook, records and compliance files.",
                          actions=[D.button("Open effort folder", None, lambda: self.host.open_effort_folder(),
                                            "The open effort's folder in File Explorer"),
                                   D.button("Import effort package...", None, lambda: self.host.import_package()),
                                   D.button("New effort...", "primary", lambda: __import__("skqt.starteffort", fromlist=["x"]).start_dialog(host))])
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
        from .people import AuthorListCard               # 2.77.0: the one place names come from
        self.authors = AuthorListCard(host)
        v.addWidget(self.authors)
        from .processview import ProcessCard             # 2.93.0: the team's stages, gate choices and roles
        self.process_card = ProcessCard(host)
        v.addWidget(self.process_card)
        from .folderplanview import FolderPlanCard       # 2.95.0: the team's folders and file names
        self.folders_card = FolderPlanCard(host)
        v.addWidget(self.folders_card)
        from .doctypesview import DocTypesCard           # 2.94.0: customer document types and their initials
        self.doctypes_card = DocTypesCard(host)
        v.addWidget(self.doctypes_card)
        from .brandview import BrandingCard              # 2.88.0: the company logos at the top of the menu
        self.branding_card = BrandingCard(host)
        v.addWidget(self.branding_card)
        from .teamview import TeamCard                   # 2.89.0: one file sets up every PC the same way
        self.team_card = TeamCard(host)
        v.addWidget(self.team_card)
        self.scroll = sc
        from .adaptive import FlowLayout                 # 2.93.0: straight to a part of Settings
        self.jump_row = FlowLayout(None, D.SPACE["s"])
        jl = D.label("Go to:", "muted", wrap=False); self.jump_row.addWidget(jl)
        for text, card in (("Your time zone", self.tz_card), ("Efforts", self.eff), ("Author list", self.authors),
                           ("Stages, gates and roles", self.process_card),
                           ("Document types", self.doctypes_card), ("Folders and file names", self.folders_card), ("Branding", self.branding_card), ("Team pack", self.team_card)):
            self.jump_row.addWidget(D.button(text, "ghost", lambda _=False, c=card: self.jump(c)))
        v.insertLayout(0, self.jump_row)
        self.db = D.Card("Master database", "The company's acronyms, abbreviations, units and symbols, shared by every effort on this PC.",
                         actions=[D.button("Load a new version...", None, lambda: self.load_master())])
        self.db_text = self.db.add(D.label("", "muted"))
        v.addWidget(self.db)
        self.bk = D.Card("Backups (Keep safe)", "The open effort is copied to this folder automatically a few minutes after "
                         "changes and when it closes: the latest copy, and one a day for 30 days. Use the approved SharePoint "
                         "folder so progress is never only on this PC.",
                         actions=[D.button("Choose the folder...", None, lambda: self.set_backup()),
                                  D.button("Back up now", None, lambda: self.host.safety.backup_now(wait=True, force=True) and self.refresh()),
                                  D.button("Turn off", "ghost", lambda: self.set_backup(""))])
        self.bk_text = self.bk.add(D.label("", "muted"))
        v.addWidget(self.bk)
        self.data = D.Card("Your data", "Settings, the author list, the master database, knowledge and training lines live in "
                           "their own folder. Update packs and new downloads never change it.",
                           actions=[D.button("Move the data folder...", None, lambda: self.move_data())])
        self.data_text = self.data.add(D.label("", "muted")); self.data_text.setWordWrap(True)
        v.addWidget(self.data)
        self.tr = D.Card("The training team", "What this PC taught goes to the training team in one file; what they release "
                                              "comes back to everyone as a Knowledge Pack. Through the approved SharePoint folder only.",
                         actions=[D.button("Send training data...", None, lambda: self.send_training()),
                                  D.button("Install a Knowledge Pack...", None, lambda: self.install_pack())])
        self.tr_text = self.tr.add(D.label("", "muted"))
        import secure                                    # 2.97.0: SCIF-ready sends no training data
        if secure.ACTIVE:
            for b in self.tr.findChildren(QPushButton):
                if b.text().startswith("Send training data"):
                    b.setVisible(False)
        v.addWidget(self.tr)
        from . import updates as UP                      # 2.76.0: update packs, and why no admin password is needed
        self.up = UP.updates_card(host, on_close=self._before_restart, install=lambda: self.install_update(),
                                  undo=lambda: self.undo_update())
        self.up.lbl.setWordWrap(True)
        v.addWidget(self.up)
        self.sec = UP.security_card()
        v.addWidget(self.sec)
        from . import helpcenter as HC                   # 2.81.0
        self.help = HC.support_card(host)
        v.addWidget(self.help)
        v.addStretch(1)

    def data_where(self):
        import app_gui
        why = {"beside": "beside the program folder", "pointer": "where you moved it", "program folder":
               "in the program folder (the folder beside it could not be created, for example in Program Files)",
               "source": "in the source folder", "env": "set for this run"}.get(getattr(app_gui, "DATA_WHY", ""), "")
        return f"Your data is in {app_gui.DATA_DIR}" + (f" ({why})." if why else ".") + " New efforts go in its Efforts folder."

    def move_data(self, folder=None):
        """Copy the data folder to a new place and use it from the next start."""
        import app_gui, datahome
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "An empty folder for Stationkeeper's data")
            if not folder:
                return None
        try:
            new = datahome.set_location(app_gui.BASE_DIR, folder, app_gui.DATA_DIR)
        except OSError as e:
            self.host.status(str(e) if "empty folder" in str(e) else f"The data could not be copied ({type(e).__name__}).")
            return None
        diag.activity("data_folder_moved")
        self.host.status(f"Data copied to {new}. Restart Stationkeeper to use it; the old folder can be deleted afterwards.")
        return new

    def jump(self, card):
        self.scroll.ensureWidgetVisible(card, 0, 0)
        sb = self.scroll.verticalScrollBar()
        sb.setValue(min(sb.maximum(), card.mapTo(self.scroll.widget(), card.rect().topLeft()).y() - D.SPACE["m"]))
        return card

    def focus_process(self):
        self.process_card.fill()
        return self.jump(self.process_card)

    def focus_authors(self):
        self.authors.fill()
        self.scroll.ensureWidgetVisible(self.authors, 0, 0)
        self.authors.table.setFocus()

    def _before_restart(self):
        try:
            self.host.assign_page.save_notes()
        except Exception:
            diag.swallowed()
        self.host.close_effort()

    def install_update(self, path=None, answer=None, restart=None):
        from . import updates as UP
        r = UP.install_update(self.host, path, answer, on_close=self._before_restart, restart=restart)
        self.refresh()
        return r

    def undo_update(self, answer=None, restart=None):
        from . import updates as UP
        r = UP.undo_update(self.host, answer, on_close=self._before_restart, restart=restart)
        self.refresh()
        return r

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
        self.authors.fill()
        self.mode.fill()
        self.data_text.setText(self.data_where())
        try:
            from . import updates as UP
            self.up.lbl.setText(UP.version_text())
        except Exception:
            diag.swallowed()
        bd = self.backup_dir()
        self.bk_text.setText(self.host.safety.status_text())
        self.bk_text.setWordWrap(True)
        try:
            import secure
            if secure.ACTIVE:                                # 2.97.0
                self.tr_text.setText("SCIF-ready: no training data is kept or sent. Knowledge Packs still install.")
            else:
                n = sum(self._tp_gather(None, False, False)["counts"].values())
                self.tr_text.setText(f"{n} item(s) waiting to be sent." if n else "Nothing new to send.")
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ efforts
    def fill_zone(self):
        import tzones as TZ
        from .modes import settings
        k = TZ.my_zone(settings())
        i = self.tz.findData(k)
        self.tz.setCurrentIndex(max(0, i))
        self.tz_other.setText("" if i >= 0 else k)
        guessed = not (settings() or {}).get("my_zone")
        self.tz_note.setText(f"{TZ.name(k)}" + (" (from Windows; Save to keep it)" if guessed else "") + ".")
        return k

    def save_zone(self, key=None):
        import tzones as TZ
        from .modes import save
        key = key or (self.tz_other.text().strip().upper() or self.tz.currentData())
        if not TZ.valid(key):
            self.host.status("Write another time zone as UTC+01:00 or UTC-03:30.")
            return False
        save(my_zone=key)
        diag.activity("qt_my_zone_saved")
        self.fill_zone()
        self.host.toast(f"Your time zone: {TZ.name(key)}")
        return True

    def new_effort(self, values=None):
        """Create an effort and open it. values (tests): name, path, first_use, customer_dir, volumes_dir, client, solicitation,
        internal_no."""
        h = self.host
        if values is None:
            dlg = QDialog(self); dlg.setWindowTitle("New effort"); dlg.setMinimumWidth(640)
            form = QFormLayout(dlg)
            name = QLineEdit(); path = QLineEdit()
            cust, vols, client, sol, internal = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
            import app_gui, datahome                     # 2.80.0: new efforts live on this PC, in Stationkeeper Data\Efforts
            base = datahome.efforts_dir(app_gui.DATA_DIR)
            path.setText(os.path.join(base, "Effort_List.xlsx"))

            def named(t):
                n = re.sub(r"[^A-Za-z0-9 _.-]+", "", t).strip()
                if n:                                    # 2.95.0: the team's home folder and list name
                    import effortfolders as EF
                    path.setText(EF.new_list_path(base, n, {"Client": client.text(), "Solicitation": sol.text(),
                                                            "Internal": internal.text()})[0])
            name.textChanged.connect(named)
            pr = QHBoxLayout(); pr.addWidget(path, 1)
            pr.addWidget(D.button("Browse...", None, lambda: (lambda p: path.setText(p) if p else None)(
                QFileDialog.getSaveFileName(dlg, "Where should the effort list live?", path.text(), "Excel (*.xlsx)")[0])))
            rule = QComboBox()
            for k, lab in E.FIRST_USE_RULES.items():
                rule.addItem(lab, k)
            form.addRow("Effort name", name); form.addRow("List file", pr)
            form.addRow("", D.label("Efforts work best on this PC. Share them through packages and backups in the team "
                                    "folder: a live effort in a OneDrive folder can collide with the sync.", "muted"))
            form.addRow("First use", rule)
            cust.setPlaceholderText("Blank: the effort's own Customer Documents folder")
            vols.setPlaceholderText("Blank: the effort's own Volumes folder")
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
        import effortfolders as EF                       # 2.90.0: Customer Documents, Volumes, Response Setup, Exports
        import folderplan as FP                          # 2.95.0: the team's tree, with the list in its home folder
        import workspace as W
        home = FP.folder_path(FP.current().get("home", ""), {"Effort": name})
        if home and os.path.normpath(os.path.dirname(os.path.abspath(path))).split(os.sep)[-len(home):] == home:
            W.Workspace(W.data_dir_for(path), name).set("root_up", len(home))
        EF.create_all(path, {"Effort": name, "Client": values.get("client", ""), "Solicitation": values.get("solicitation", ""),
                             "Internal": values.get("internal_no", "")})
        values = dict(values)
        values["customer_dir"] = values.get("customer_dir") or EF.folder(path, "customer")
        values["volumes_dir"] = values.get("volumes_dir") or EF.folder(path, "volumes")
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
            import workmode as WM
            warn = WM.folder_warning(app_gui.load_settings() or {}, folder)
            if warn:
                self.host.status(warn)
        else:
            diag.activity("backup_location_off")
        self.refresh()
        return st["backup_dir"]


class _TrainingHelper:
    """The classic window's gathering of what this PC taught (every effort's matrix, compliance words, choices,
    keywords, banned words), without a window."""

    def __init__(self, efforts, matrix=None):
        self.efforts, self.matrix = efforts, matrix


def _helper(host):
    from trainpack_ui import TrainPackMixin
    cls = type("TrainingHelper", (_TrainingHelper, TrainPackMixin), {})
    return cls(host.efforts, host.review.M if host.review is not None else None)


def _tp_gather(self, areas, everything, text):
    import app_gui
    import trainpack as TP
    return TP.gather(config_dir=app_gui.CONFIG_DIR, **_helper(self.host).tp_args(areas, everything, text))


def send_training(self, out=None, areas=None, everything=False, text=False, acknowledged=None):
    """Save the training data pack. With out and acknowledged (tests) it saves at once.
    2.97.0: never in SCIF-ready; efforts above CUI or of unknown sensitivity are left out, and the dialog says which."""
    import app_gui
    import secure
    import trainpack as TP
    from PySide6.QtWidgets import QCheckBox
    if secure.ACTIVE:
        self.host.status("SCIF-ready: Stationkeeper keeps no training data and sends none.")
        return None
    hp = _helper(self.host)
    hp.tp_args()
    left = list(getattr(hp, "tp_left_out", []))
    self.tp_left_out = left
    if out is None or acknowledged is None:
        dlg = QDialog(self); dlg.setWindowTitle("Send training data to the training team"); dlg.setMinimumWidth(640)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("What this PC taught, in one file for Stationkeeper Training. The next Knowledge Pack brings it back to everyone.", "muted"))
        boxes = {}
        for a, title in TP.AREAS:
            cb = QCheckBox(title); cb.setChecked(True); boxes[a] = cb; v.addWidget(cb)
        ev = QCheckBox("Everything, not only what is new since the last send"); v.addWidget(ev)
        tv = QCheckBox("Include the sentence text (RFP sentences and section titles)"); v.addWidget(tv)
        v.addWidget(D.label("Left out always: customer information, team names, file paths, user and PC names.", "muted"))
        if left:                                      # 2.97.0
            v.addWidget(D.label(f"Also left out: {len(left)} effort(s) marked above CUI or with no sensitivity set "
                                "(set it in Effort Home > Edit details): " + ", ".join(left[:6]) + (" ..." if len(left) > 6 else ""), "muted"))
        warn = D.label(TP.WARNING); t = D.tokens()
        warn.setStyleSheet(f"background:{t['warn_soft']};color:{t['warn']};border-radius:6px;padding:8px;")
        v.addWidget(warn)
        ack = QCheckBox("I have read this. I am responsible for what this pack holds."); v.addWidget(ack)
        lbl = D.label("", "muted"); v.addWidget(lbl)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); v.addWidget(bb)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)

        def chosen():
            return [a for a, cb in boxes.items() if cb.isChecked()]

        def refresh():
            try:
                c = self._tp_gather(chosen(), ev.isChecked(), tv.isChecked())["counts"]
            except Exception:
                diag.swallowed(); c = {}
            total = sum(c.get(a, 0) for a in chosen())
            for a, title in TP.AREAS:
                boxes[a].setText(f"{title}  ({c.get(a, 0)} waiting)" if boxes[a].isChecked() else f"{title}  (left out)")
            lbl.setText(("Nothing new to send." if not total else f"{total} item(s) to send.") + ("" if ack.isChecked() else "  Tick the box above to save."))
            bb.button(QDialogButtonBox.Save).setEnabled(bool(ack.isChecked() and total))
        for w in list(boxes.values()) + [ev, tv, ack]:
            w.toggled.connect(lambda _on: refresh())
        refresh()
        if dlg.exec() != QDialog.Accepted:
            return None
        areas, everything, text, acknowledged = chosen(), ev.isChecked(), tv.isChecked(), ack.isChecked()
        if out is None:
            import datetime, getpass
            name = (f"Stationkeeper_Training_Data_{re.sub(r'[^A-Za-z0-9]+', '', getpass.getuser()) or 'user'}_"
                    f"{datetime.datetime.now():%Y.%m.%d-%H%M}{TP.EXT}")
            out, _ = QFileDialog.getSaveFileName(self, "Save to the APPROVED SHAREPOINT folder only", name, f"Training data (*{TP.EXT})")
            if not out:
                return None
    if not acknowledged:
        return None
    r = TP.build(out, app_gui.CONFIG_DIR, app_version=app_gui.APP_VERSION, acknowledged=True,
                 **_helper(self.host).tp_args(areas, everything, text))
    c = r["counts"]
    diag.activity("training_data_sent", n=sum(c.values()), items=1 if text else 0)
    self.host.toast("Nothing new to send." if not r["path"] else f"Saved {os.path.basename(out)}: "
                    + ", ".join(f"{n} {a}" for a, n in c.items() if n))
    self.refresh()
    return r


def install_pack(self, path=None, answer=None):
    """The Knowledge Pack card: what it improves and adds, then Install. answer (tests): 'install' at once."""
    import app_gui
    import studio as ST
    if path is None:
        path, _ = QFileDialog.getOpenFileName(self, "Install Knowledge Pack (from the approved SharePoint folder)", "",
                                              f"Knowledge Pack (*{ST.EXT} *.zip)")
        if not path:
            return None
    try:
        info, _data = app_gui.read_knowledge_pack(path)
    except Exception as e:
        diag.swallowed()
        self.host.status(f"Not a Knowledge Pack: {type(e).__name__}. Nothing was changed.")
        return None
    if answer is None:
        counts = info.get("counts") or {}
        words = {"database_rows": "acronym database rows (added only when new)", "ocr_fixes": "OCR fixes", "ignored_readings": "ignored readings"}
        adds = [f"{n} {words.get(k, k.replace('_', ' '))}" for k, n in counts.items() if isinstance(n, int) and n]
        dlg = QDialog(self); dlg.setWindowTitle("Install Knowledge Pack"); dlg.setMinimumWidth(600)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label(f"Install Knowledge Pack {info.get('created', info.get('version', ''))[:10]}?", "title"))
        v.addWidget(D.label(f"From the training team ({info.get('created_by', '?')}), made {info.get('created', '?')}"
                            + (f" with Stationkeeper {info['app_version']}" if info.get("app_version") else "") + ".", "muted"))
        tested = ST.card_lines(info)
        if tested:
            v.addWidget(D.SectionTitle("Tested before release"))
            for t in tested:
                v.addWidget(D.label("\u2713  " + t))
        if adds:
            v.addWidget(D.SectionTitle("Adds")); v.addWidget(D.label(", ".join(adds)))
        if info.get("notes"):
            v.addWidget(D.label("Notes: " + info["notes"]))
        v.addWidget(D.label("Your own corrections, decisions and database rows stay. A backup is taken first, so it can be undone.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Install")
        bb.button(QDialogButtonBox.Cancel).setText("Not now")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        answer = "install" if dlg.exec() == QDialog.Accepted else "later"
    if answer != "install":
        return None
    try:
        rep = app_gui.install_knowledge_pack(path)
    except PermissionError:
        self.host.status(app_gui.DB_LOCKED_MSG)
        return None
    except Exception as e:
        app_gui.log_error("Knowledge Pack install failed")
        self.host.status(f"Not installed: {type(e).__name__}. Nothing was changed.")
        return None
    diag.activity("knowledge_installed_card")
    self.host.toast("Knowledge Pack installed")
    self.refresh()
    return rep


SettingsPage._tp_gather = _tp_gather
SettingsPage.send_training = send_training
SettingsPage.install_pack = install_pack
