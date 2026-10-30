"""The effort record in Qt (2.63.0): effort details (client, solicitation, internal number, due date and time), the
team, the stages with their planned dates and gates (none, soft, hard), the effort status report (Word), the effort
package and Back up now. The record is the effort's record.json, shared with the classic window; the details are also
kept in the effort's acronym list workbook, as the classic window keeps them. Rules only; nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
                               QDialog, QDialogButtonBox, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import effortrec as R
import effortstate as ES
from . import design as D
from .stagesedit import StageTableMixin


def _table(cols):
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSelectionMode(QTableWidget.SingleSelection)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return t


class RecordPage(StageTableMixin, QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.L = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget(); inner.setObjectName("page"); scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        # details
        self.details = D.Card("Effort details", "Who it is for, its numbers, and when it is due. The countdown uses this PC's clock.",
                              actions=[D.button("Save details", "primary", lambda: self.save_details())])
        form = QFormLayout(); form.setSpacing(D.SPACE["s"]); self.details.body.addLayout(form)
        self.name = D.label("", "title")
        self.client = QLineEdit(); self.client.setPlaceholderText("USSF SSC")
        self.sol = QLineEdit(); self.sol.setPlaceholderText("FA8810-26-R-0042")
        self.internal = QLineEdit()
        due = QHBoxLayout(); due.setSpacing(D.SPACE["s"])
        self.has_due = QCheckBox("Due on")
        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True); self.due_date.setDisplayFormat("MMM d, yyyy")
        self.due_time = QTimeEdit(); self.due_time.setDisplayFormat("h:mm AP")
        self.zone = QLineEdit(); self.zone.setPlaceholderText("MT"); self.zone.setMaximumWidth(140)
        self.has_due.setText("Due date set")                    # 2.92.0: the boxes always work; changing one sets the due date
        self.has_due.setToolTip("Untick to clear the due date")
        for w_ in (self.due_date, self.due_time):
            sig = w_.dateChanged if w_ is self.due_date else w_.timeChanged
            sig.connect(lambda *_a: None if getattr(self, "_filling_due", False) else self.has_due.setChecked(True))
        self.zone.setPlaceholderText("ET, CT, MT, PT, UTC...")
        for w in (self.has_due, self.due_date, self.due_time, self.zone):
            due.addWidget(w)
        due.addStretch(1)
        form.addRow("Effort", self.name); form.addRow("Client", self.client); form.addRow("Solicitation or opportunity number", self.sol)
        form.addRow("Internal number", self.internal); form.addRow("Due date and time", due)
        self.found_row = QHBoxLayout()
        self.found = D.label("", "muted"); self.found_row.addWidget(self.found, 1)
        self.use_found = D.button("Use it", None, lambda: self.use_customer_due()); self.found_row.addWidget(self.use_found)
        self.details.body.addLayout(self.found_row)
        v.addWidget(self.details)
        # team
        self.team = D.Card("People and roles", "The names from the author list that show in this effort, offered wherever an "
                                               "author, lead or owner is picked, with each person's role here. Every name lives in "
                                               "Settings > Author list.",
                           actions=[D.button("Choose people...", "primary", lambda: self.choose_team())])
        from .rolesview import TeamRoles                     # 2.93.0: a role drop-down per person that saves when picked
        self.team_roles = TeamRoles(host)
        self.team.add(self.team_roles)
        self.team_table, self.team_note = self.team_roles.table, self.team_roles.note
        v.addWidget(self.team)
        # stages and gates
        self.stages = D.Card("Stages and gates", "When each stage starts and ends (click a date to pick it; the time is optional), "
                                                 "and its gate. The gate choices are your team's: Settings > Stages, gates and roles.",
                             actions=[D.button("Up", None, lambda: self.move_row(-1)), D.button("Down", None, lambda: self.move_row(1)),
                                      D.button("+ Stage", None, lambda: self.add_stage()), D.button("Remove", "ghost", lambda: self.remove_stage()),
                                      D.button("Save stages", "primary", lambda: self.save_stages())])
        from .stagesedit import stage_table                  # 2.93.0: date pickers and times, a readable Stage column
        self.stage_table = stage_table()
        self.stage_table.setMinimumHeight(300)
        self.stages.add(self.stage_table)
        srow = QHBoxLayout()
        self.stage_note = D.label("Double-click a stage's name to rename it. The current stage cannot be removed.", "muted")
        srow.addWidget(self.stage_note, 1)
        srow.addWidget(D.button("Gate choices and default stages...", "ghost",
                                lambda: (self.host.go("settings"), self.host.settings_page.focus_process())))
        self.stages.body.addLayout(srow)
        v.addWidget(self.stages)
        # 2.80.0 effort health
        self.readable = D.Card("Readable copy", "Everything in the effort as plain files (Excel, Word, CSV, text) in its folder, "
                               "rewritten a few seconds after every change, so the effort can carry on without Stationkeeper.",
                               actions=[D.button("Open the readable copy", "primary", lambda: self.host.open_readable())])
        self.readable_text = self.readable.add(D.label("", "muted"))
        v.addWidget(self.readable)
        self.health = D.Card("Effort health", "Checked each time the effort opens. A damaged list or matrix is put back from its "
                             "newest good copy automatically.", actions=[D.button("Check now", None, lambda: self.check_health())])
        self.health_box = QVBoxLayout(); self.health.body.addLayout(self.health_box)
        v.addWidget(self.health)
        # reports, package, backup
        self.out = D.Card("Status, package and backup")
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.button("Effort status (Word)...", "primary", lambda: self.status_export(), "Where the effort stands, for leadership"))
        row.addWidget(D.button("Effort summary (Word)...", None, lambda: self.status_export(final=True), "The effort with its complete history"))
        row.addWidget(D.button("Save effort package...", None, lambda: self.save_package(), "The whole effort in one .skpkg file for a hand-off"))
        self.team_btn = D.button("Save to the team folder", None, lambda: self.save_to_team(),
                                 "Connected mode: the package goes to the team's OneDrive-synced SharePoint folder")
        row.addWidget(self.team_btn)
        row.addWidget(D.button("Back up now", None, lambda: self.backup_now()))
        row.addWidget(D.button("Restore...", None, lambda: self.restore_dialog(), "Put back an earlier copy of this effort"))
        row.addStretch(1)
        self.out.body.addLayout(row)
        self.backup_text = self.out.add(D.label("", "muted"))
        v.addWidget(self.out)
        v.addStretch(1)

    # ------------------------------------------------------------ the effort
    @property
    def rec(self):
        h = self.host
        return R.Record(h.ws.root) if h.ws is not None else None

    def effort_list(self):
        import effort as E
        h = self.host
        try:
            return E.EffortList(h.effort_path, h.effort_name).load()
        except Exception:
            diag.swallowed()
            return None

    def refresh(self):
        h = self.host
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            return
        r = self.rec
        self.L = L = self.effort_list()
        self.name.setText(h.effort_name)
        for w, val in ((self.client, L.client if L else ""), (self.sol, L.solicitation if L else ""), (self.internal, L.internal_no if L else "")):
            w.setText(val or "")
        due = r.data.get("due", "")
        d = R.parse_date(due[:10]) if due else None
        self._filling_due = True
        self.has_due.setChecked(d is not None)
        self.due_date.setDate(QDate(d) if d else QDate.currentDate().addDays(30))
        hm = due[11:16] if len(due) > 15 else ""
        self.due_time.setTime(QTime(int(hm[:2]), int(hm[3:5])) if hm[:2].isdigit() and hm[3:5].isdigit() else QTime(14, 0))
        self.zone.setText(r.data.get("zone", ""))
        self._filling_due = False

        st = ES.State(h.ws, h.effort_path, None)
        import subreq as SR
        sm = SR.summary(st.rows)
        self.customer_due = sm["due"]["value"] if sm.get("due") else ""
        self.found.setText(f"The customer documents say: {self.customer_due}" if self.customer_due else "")
        self.use_found.setVisible(bool(self.customer_due))
        self.fill_team(r)
        self.fill_stages(r)
        self.fill_health(self.host.safety.issues)
        self.backup_text.setText(self.host.safety.status_text())     # 2.78.0: automatic, with the last time
        import readable as RD
        rf = RD.folder_for(h.effort_path, h.effort_name)
        self.readable_text.setText(f"{rf}" + (f"\nLast written {h.rd_written}." if getattr(h, "rd_written", "") else
                                   ("\nWritten after the next change." if not os.path.isdir(rf) else "")))
        import workmode as WM
        from .modes import settings
        self.team_btn.setVisible(bool(WM.team_dir(settings())))

    # ------------------------------------------------------------ details
    def use_customer_due(self):
        iso, zone = R.parse_due_text(self.customer_due)
        if not iso:
            self.host.status("The customer documents' due date was not understood.")
            return False
        self.has_due.setChecked(True)
        self.due_date.setDate(QDate.fromString(iso[:10], "yyyy-MM-dd"))
        if len(iso) > 15:
            self.due_time.setTime(QTime(int(iso[11:13]), int(iso[14:16])))
        self.zone.setText(zone or "")
        return True

    def save_details(self):
        r, L, h = self.rec, self.L, self.host
        changed = []
        if L is not None:
            for attr, w, word in (("client", self.client, "client"), ("solicitation", self.sol, "solicitation number"),
                                  ("internal_no", self.internal, "internal number")):
                val = " ".join(w.text().split())
                if getattr(L, attr) != val:
                    setattr(L, attr, val); changed.append(f"{word} {val or '(none)'}")
            if changed:
                try:
                    L.pending = True
                    L.save()
                    h.efforts.put(h.effort_name, client=L.client, solicitation=L.solicitation, internal_no=L.internal_no)
                except Exception:
                    diag.swallowed()
                    h.status("The effort list is open in Excel: close it, then save the details again.")
                    return False
                r.log("effort", "Effort details: " + "; ".join(changed), save=True)
        iso = ""
        if self.has_due.isChecked():
            iso = self.due_date.date().toPython().isoformat() + "T" + self.due_time.time().toString("HH:mm")
        if iso != r.data.get("due", "") or " ".join(self.zone.text().split()) != r.data.get("zone", ""):
            r.set_due(iso, self.zone.text() if iso else "")
        diag.activity("qt_effort_details_saved")
        h.toast("Effort details saved")
        self.refresh()
        return True

    # ------------------------------------------------------------ team (2.77.0: from the author list)
    def fill_team(self, r=None):
        self.team_roles.fill()

    def choose_team(self, answer=None):
        """Tick the names (from the whole author list) that show in this effort. answer (tests): the names."""
        from .people import effort_names
        L, here = self.host.authors, self.host.effort_name
        if not L.people:
            self.host.status("The author list is empty. Add names in Settings > Author list.")
            if answer is None:
                self.host.go("settings"); self.host.settings_page.focus_authors()
            return None
        if answer is None:
            d = QDialog(self); d.setWindowTitle(f"People on {here}"); d.setMinimumSize(420, 460)
            v = QVBoxLayout(d)
            v.addWidget(D.label("Tick who shows in this effort. A name set to all efforts shows here too; untick it to keep "
                                "it in the other efforts only.", "muted"))
            lw = QListWidget(); v.addWidget(lw, 1)
            for p in sorted(L.people, key=lambda p: p["name"].casefold()):
                it = QListWidgetItem(p["name"] + ("  (all efforts)" if p["efforts"] == "all" else "")); it.setData(Qt.UserRole, p["name"])
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if L.shows_in(p, here) else Qt.Unchecked)
                lw.addItem(it)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = [lw.item(i).data(Qt.UserRole) for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked]
        want = {n.casefold() for n in answer}
        effs = effort_names(self.host)
        n = 0
        for p in list(L.people):
            n += L.show_in(p["name"], here, p["name"].casefold() in want, effs)
        diag.activity("qt_team_chosen", n=len(want))
        self.host.toast(f"{len(L.for_effort(here))} people show in {here}")
        self.fill_team()
        return L.for_effort(here)

    def save_team(self):
        t = self.team_table
        rows = [((t.item(i, 0).text() if t.item(i, 0) else ""), (t.cellWidget(i, 1).currentText() if t.cellWidget(i, 1) else ""))
                for i in range(t.rowCount())]
        new = self.rec.set_team(rows)
        diag.activity("qt_team_saved")
        self.host.toast(f"Team roles saved: {len(new)} people")
        self.refresh()
        return new

    # ------------------------------------------------------------ stages and gates
    # ------------------------------------------------------------ status, package, backup
    def pm_summary(self, answer=None):
        """2.92.0: the proposal manager's summary for the overview, in their own words; kept for next time. answer
        (tests): the text. None when cancelled."""
        r = self.rec
        if answer is None:
            from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout
            dlg = QDialog(self); dlg.setWindowTitle("The proposal manager's summary"); dlg.resize(620, 380)
            v = QVBoxLayout(dlg)
            v.addWidget(D.label("In your own words: where the effort stands, what worries you, what you need. It prints first in the "
                                "overview and is kept for next time. Leave it empty to leave it out.", "muted"))
            ed = QPlainTextEdit(r.data.get("pm_summary", "")); v.addWidget(ed, 1)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Write the overview")
            bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = ed.toPlainText()
        r.data["pm_summary"] = (answer or "").strip()[:6000]
        r.save()
        return r.data["pm_summary"]

    def status_export(self, path=None, final=False, summary=None):
        import statusdoc as SDOC
        h = self.host
        if h.ws is None:
            return None
        if path is None or summary is not None:                  # 2.92.0: the proposal manager's words first
            if self.pm_summary(summary) is None:
                return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save the effort summary" if final else "Save the effort status",
                                                  h.out_path("effort_summary" if final else "effort_status"), "Word (*.docx)")
            if not path:
                return None
        st = ES.State(h.ws, h.effort_path, h.review.M if h.review is not None else None)
        try:
            import tzones as TZ
            from .modes import settings
            SDOC.build(ES.status_snapshot(st, final=final, app_version=h.version, name=h.effort_name, my_zone=TZ.my_zone(settings())),
                       path, final=final)
        except PermissionError:
            h.status("That file is open in Word. Close it, then save again.")
            return None
        st.rec.data["overview_last"] = datetime.datetime.now().isoformat(timespec="minutes")   # NEW marks count from here
        st.rec.log("effort", ("Effort summary" if final else "Effort status") + f" exported: {os.path.basename(path)}", save=True)
        diag.activity("qt_status_exported")
        h.toast(("Effort summary" if final else "Effort status") + " written")
        return path

    def _package_args(self):
        h = self.host
        h.save_now()
        info = dict(h.efforts.get(h.effort_name) or {})
        L = self.L or self.effort_list()
        r = self.rec
        return dict(effort_name=h.effort_name, list_path=h.effort_path, data_dir=h.ws.root,
                    matrix_path=h.ws.get("compliance_path", "") or "", customer_dir=info.get("customer_dir", ""),
                    volumes_dir=info.get("volumes_dir", ""),
                    extra_files=[dl.get("file") for dl in r.data.get("deliverables", []) if dl.get("file")],
                    info={**info, "name": h.effort_name, "client": L.client if L else "", "solicitation": L.solicitation if L else "",
                          "internal_no": L.internal_no if L else "", "first_use": L.first_use if L else "volume"},
                    stage=r.stage()["name"], app_version=h.version)

    def library_choice(self, answer=None):
        """2.83.0: all documents, or the customer documents and Q&A only, when the library holds others. answer
        (tests): 'all' or 'customer'. None when cancelled."""
        import docversions as DV
        lib = DV.Library(self.host.ws.p("documents")).load()
        others = [d for d in lib.all if d.get("category", "customer") not in ("customer", "qa")]
        if not others:
            return "all"
        if answer is not None:
            return answer
        size = 0
        for d in others:
            for v in d["versions"]:
                p = lib.path_of(v)
                if p and os.path.isfile(p):
                    size += os.path.getsize(p)
        box = QMessageBox(self)
        box.setWindowTitle("Save effort package")
        box.setText(f"The library holds {len(others)} document(s) besides the customer documents and Q&A "
                    f"({size / 1e6:.0f} MB of original files).")
        box.setInformativeText("Either way the package carries every document's record, text, tags and role, so search and "
                               "the library still work; only the original files of the left-out documents stay behind, "
                               "marked 'original not here' for the person who opens it.")
        b_all = box.addButton("All documents", QMessageBox.AcceptRole)
        b_cust = box.addButton("Customer documents and Q&A only", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(b_all)
        box.exec()
        return "all" if box.clickedButton() is b_all else "customer" if box.clickedButton() is b_cust else None

    def save_package(self, path=None, customer=True, volumes=True, library=None):
        import effortpkg as P
        h = self.host
        if h.ws is None:
            return None
        library = self.library_choice(library if library is not None else ("all" if path is not None else None))
        if library is None:
            return None
        a = self._package_args()
        if path is None:
            fname = "_".join(x for x in (h.effort_name, a["stage"], datetime.date.today().isoformat()) if x).replace(" ", "_") + P.EXT
            folder = os.path.dirname(a["customer_dir"] or h.effort_path)
            path, _ = QFileDialog.getSaveFileName(self, "Save effort package (this PC or the approved SharePoint folder only)",
                                                  os.path.join(folder, fname), f"Stationkeeper effort package (*{P.EXT})")
            if not path:
                return None
        try:
            man = P.save(path, a["effort_name"], a["list_path"], a["data_dir"], info=a["info"], matrix_path=a["matrix_path"],
                         customer_dir=a["customer_dir"] if customer else "", volumes_dir=a["volumes_dir"] if volumes else "",
                         customer=customer and bool(a["customer_dir"]), volumes=volumes and bool(a["volumes_dir"]), stage=a["stage"],
                         app_version=a["app_version"], extra_files=a["extra_files"], extra=self.package_extra(), library=library)
        except (OSError, PermissionError) as e:
            diag.swallowed()
            h.status(f"The package could not be written ({type(e).__name__}).")
            return None
        self.rec.log("effort", f"Effort package saved: {os.path.basename(man['path'])} ({a['stage']}, {len(man['files'])} files)", save=True)
        diag.activity("qt_package_saved", files=len(man["files"]))
        h.toast(f"Effort package saved: {os.path.basename(man['path'])}")
        return man

    # ------------------------------------------------------------ 2.80.0 effort health
    def fill_health(self, issues):
        import effortcheck as EC
        while self.health_box.count():
            w = self.health_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.health_box.addWidget(D.label(EC.summary(issues), "muted"))
        labels = {"find_customer": "Find the folder...", "find_volumes": "Find the folder...", "move_local": "Move to this PC",
                  "restore_package": "Restore...", "restore_list": "Put back a copy", "restore_matrix": "Put back a copy"}
        for i in issues:
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0)
            lab = D.label(("Problem: " if i["severity"] == "error" else "") + i["text"], "crit" if i["severity"] == "error" else "")
            lab.setWordWrap(True); h.addWidget(lab, 1)
            if i["fix"] in labels:
                h.addWidget(D.button(labels[i["fix"]], None, lambda _=False, f=i["fix"]: self.fix(f)))
            self.health_box.addWidget(row)

    def check_health(self):
        issues, fixed = self.host.safety.health()
        for f in fixed:
            self.host.toast(f)
        self.fill_health(issues)
        diag.activity("qt_health_checked", n=len(issues))
        return issues

    def fix(self, what, folder=None):
        h = self.host
        if what in ("find_customer", "find_volumes"):
            if folder is None:
                folder = QFileDialog.getExistingDirectory(self, "Where is the folder now?")
                if not folder:
                    return None
            h.efforts.put(h.effort_name, **({"customer_dir": folder} if what == "find_customer" else {"volumes_dir": folder}))
        elif what == "move_local":
            return h.safety.move_to_pc(folder)
        elif what in ("restore_package", "restore_list", "restore_matrix"):
            return self.restore_dialog()
        return self.check_health()

    def package_extra(self):
        """2.79.0: what the receiver needs from this PC's settings: the author-list names that show in this effort, and
        the revision (so the receiver's copy can be compared)."""
        h = self.host
        h.safety.save_view()
        h.safety.revise()
        out = {"authors": [{"name": n} for n in h.authors.for_effort(h.effort_name)]}
        try:
            import lineage as LG
            out["revision"] = LG.current(LG.read(h.ws.root))
        except Exception:
            diag.swallowed()
        return out

    def save_to_team(self):
        """Connected mode: the package goes to the team folder, named with the effort, stage, who and when."""
        import workmode as WM
        from .modes import settings
        team = WM.team_dir(settings())
        if not team or self.host.ws is None:
            self.host.status("Choose the team folder first (Settings > Where Stationkeeper is used).")
            return None
        import getpass, effortpkg as P
        a_stage = self.rec.stage()["name"]
        name = " ".join(x for x in (self.host.effort_name, a_stage, getpass.getuser(),
                                    datetime.datetime.now().strftime("%Y-%m-%d %H%M")) if x)
        folder = WM.packages_dir(team, self.host.effort_name)
        os.makedirs(folder, exist_ok=True)
        return self.save_package(os.path.join(folder, WM._safe(name) + P.EXT))

    def backup_dir(self):
        try:
            import app_gui
            return (app_gui.load_settings() or {}).get("backup_dir", "") or ""
        except Exception:
            diag.swallowed()
            return ""

    def restore_dialog(self, pick=None):
        """2.78.0 Restore points: the effort's dated copies and its backup packages, newest first. pick (tests): an index."""
        sf = self.host.safety
        pts = sf.points()
        if not pts:
            self.host.status("No earlier copies yet: they appear after the first saves and backups.")
            return None
        if pick is None:
            from .safety import _nice
            d = QDialog(self); d.setWindowTitle("Restore an earlier copy"); d.setMinimumSize(560, 420)
            v = QVBoxLayout(d)
            v.addWidget(D.label("Pick the copy to put back. What you have now is kept as a copy first, so this can be undone "
                                "the same way.", "muted"))
            lw = QListWidget(); v.addWidget(lw, 1)
            for pt in pts:
                lw.addItem(f"{_nice(pt['when'])}    {pt['label']}")
            lw.setCurrentRow(0)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Put it back")
            bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); v.addWidget(bb)
            if d.exec() != QDialog.Accepted or lw.currentRow() < 0:
                return None
            pick = lw.currentRow()
        ok = sf.restore(pts[pick])
        self.refresh() if self.host.ws is not None else None
        return pts[pick] if ok else None

    def backup_now(self, folder=None):
        """Back up the open effort to the backup folder set in Keep safe (folder: tests)."""
        import keepsafe as K
        h = self.host
        bd = folder or self.backup_dir()
        if h.ws is not None:
            h.readable_now(overview=True, wait=False)           # 2.92.0: the readable copy, with the overview, too
        if h.ws is None or not bd:
            h.status("Backups are off. Choose the backup folder in Settings.")
            return None
        a = self._package_args()
        try:
            import app_gui
            out = K.backup_effort(bd, a["effort_name"], a["list_path"], a["data_dir"], matrix_path=a["matrix_path"],
                                  customer_dir=a["customer_dir"], volumes_dir=a["volumes_dir"], extra_files=a["extra_files"],
                                  info=a["info"], stage=a["stage"], app_version=a["app_version"],
                                  config_dir=getattr(app_gui, "CONFIG_DIR", "") if folder is None else "",
                                  settings_file=getattr(app_gui, "SETTINGS_FILE", "") if folder is None else "")
        except Exception as e:
            diag.swallowed()
            h.status(f"The backup could not be written ({type(e).__name__}).")
            return None
        diag.activity("qt_backup_done")
        h.toast("Backed up")
        return out
