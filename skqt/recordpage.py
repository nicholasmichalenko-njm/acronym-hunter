"""The effort record in Qt (2.63.0): effort details (client, solicitation, internal number, due date and time), the
team, the stages with their planned dates and gates (none, soft, hard), the effort status report (Word), the effort
package and Back up now. The record is the effort's record.json, shared with the classic window; the details are also
kept in the effort's acronym list workbook, as the classic window keeps them. Rules only; nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
                               QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget)
import diag
import effortrec as R
import effortstate as ES
from . import design as D


def _table(cols):
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSelectionMode(QTableWidget.SingleSelection)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return t


class RecordPage(QWidget):
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
        self.has_due.toggled.connect(lambda on: (self.due_date.setEnabled(on), self.due_time.setEnabled(on), self.zone.setEnabled(on)))
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
        self.team = D.Card("Team", "The people on this effort, offered wherever a lead, author or owner is picked.",
                           actions=[D.button("+ Person", None, lambda: self.add_person()), D.button("Remove", "ghost", lambda: self.remove_person()),
                                    D.button("Save team", "primary", lambda: self.save_team())])
        self.team_table = _table(["Name", "Role"]); self.team_table.setColumnWidth(1, 260); self.team_table.setMinimumHeight(180)
        self.team.add(self.team_table)
        v.addWidget(self.team)
        # stages and gates
        self.stages = D.Card("Stages and gates", "Planned dates for each stage, and its gate: none; soft (moving on with open goals "
                                                 "is logged); hard (held until the goals are met, or overridden with a reason).",
                             actions=[D.button("Up", None, lambda: self.move_row(-1)), D.button("Down", None, lambda: self.move_row(1)),
                                      D.button("+ Stage", None, lambda: self.add_stage()), D.button("Remove", "ghost", lambda: self.remove_stage()),
                                      D.button("Save stages", "primary", lambda: self.save_stages())])
        self.stage_table = _table(["Stage", "Planned start", "Planned end", "Gate"])
        for i, w in enumerate((0, 150, 150, 300)):
            if i:
                self.stage_table.setColumnWidth(i, w)
        self.stage_table.setMinimumHeight(300)
        self.stages.add(self.stage_table)
        self.stage_note = self.stages.add(D.label("Dates as Nov 3, 2026 or 2026-11-03. The current stage cannot be removed.", "muted"))
        v.addWidget(self.stages)
        # reports, package, backup
        self.out = D.Card("Status, package and backup")
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.button("Effort status (Word)...", "primary", lambda: self.status_export(), "Where the effort stands, for leadership"))
        row.addWidget(D.button("Effort summary (Word)...", None, lambda: self.status_export(final=True), "The effort with its complete history"))
        row.addWidget(D.button("Save effort package...", None, lambda: self.save_package(), "The whole effort in one .skpkg file for a hand-off"))
        row.addWidget(D.button("Back up now", None, lambda: self.backup_now()))
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
        self.has_due.setChecked(d is not None)
        self.due_date.setDate(QDate(d) if d else QDate.currentDate().addDays(30))
        hm = due[11:16] if len(due) > 15 else ""
        self.due_time.setTime(QTime(int(hm[:2]), int(hm[3:5])) if hm[:2].isdigit() and hm[3:5].isdigit() else QTime(14, 0))
        self.zone.setText(r.data.get("zone", ""))
        for w in (self.due_date, self.due_time, self.zone):
            w.setEnabled(d is not None)
        st = ES.State(h.ws, h.effort_path, None)
        import subreq as SR
        sm = SR.summary(st.rows)
        self.customer_due = sm["due"]["value"] if sm.get("due") else ""
        self.found.setText(f"The customer documents say: {self.customer_due}" if self.customer_due else "")
        self.use_found.setVisible(bool(self.customer_due))
        self.team_table.setRowCount(0)
        for m in r.team():
            self._team_row(m["name"], m.get("role", ""))
        self.fill_stages(r)
        bd = self.backup_dir()
        self.backup_text.setText(f"Backups go to {bd}." if bd else "Backups are off. Choose the backup folder in Settings.")

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

    # ------------------------------------------------------------ team
    def _team_row(self, name, role):
        t = self.team_table
        i = t.rowCount(); t.insertRow(i)
        t.setItem(i, 0, QTableWidgetItem(name)); t.setItem(i, 1, QTableWidgetItem(role))
        return i

    def add_person(self, name="", role=""):
        i = self._team_row(name, role)
        self.team_table.setCurrentCell(i, 0)
        if not name:
            self.team_table.editItem(self.team_table.item(i, 0))
        return i

    def remove_person(self):
        i = self.team_table.currentRow()
        if i >= 0:
            self.team_table.removeRow(i)

    def save_team(self):
        t = self.team_table
        rows = [((t.item(i, 0).text() if t.item(i, 0) else ""), (t.item(i, 1).text() if t.item(i, 1) else "")) for i in range(t.rowCount())]
        new = self.rec.set_team(rows)
        diag.activity("qt_team_saved")
        self.host.toast(f"Team saved: {len(new)} people")
        self.refresh()
        return new

    # ------------------------------------------------------------ stages and gates
    def fill_stages(self, r):
        t = self.stage_table
        t.setRowCount(0)
        for s in r.stages:
            self._stage_row(s["id"], s["name"], s.get("planned", ""), s.get("planned_end", ""), r.gate_of(s), s["id"] == r.data["stage"])

    def _stage_row(self, sid, name, start, end, gate, current=False, at=None):
        t = self.stage_table
        i = t.rowCount() if at is None else at
        t.insertRow(i)
        it = QTableWidgetItem(name); it.setData(Qt.UserRole, sid)
        if current:
            it.setToolTip("The current stage"); it.setForeground(D.color("accent"))
        t.setItem(i, 0, it)
        for c, val in ((1, start), (2, end)):
            d = R.parse_date(val) if val else None
            t.setItem(i, c, QTableWidgetItem(R.short_date(d.isoformat()) + f", {d.year}" if d else (val or "")))
        cb = QComboBox()
        for k, text in R.GATES.items():
            cb.addItem(text, k)
        cb.setCurrentIndex(max(0, cb.findData(gate)))
        t.setCellWidget(i, 3, cb)
        return i

    def _stage_values(self, i):
        t = self.stage_table
        it = t.item(i, 0)
        return (it.data(Qt.UserRole) if it else None, it.text() if it else "", t.item(i, 1).text() if t.item(i, 1) else "",
                t.item(i, 2).text() if t.item(i, 2) else "", t.cellWidget(i, 3).currentData())

    def move_row(self, d):
        t = self.stage_table
        i = t.currentRow()
        j = i + d
        if i < 0 or not (0 <= j < t.rowCount()):
            return False
        vals = self._stage_values(i)
        cur = t.item(i, 0).toolTip() == "The current stage"
        t.removeRow(i)
        self._stage_row(vals[0], vals[1], vals[2], vals[3], vals[4], cur, at=j)
        t.setCurrentCell(j, 0)
        return True

    def add_stage(self, name="New stage"):
        i = self._stage_row(None, name, "", "", "")
        self.stage_table.setCurrentCell(i, 0)
        return i

    def remove_stage(self):
        t = self.stage_table
        i = t.currentRow()
        if i < 0:
            return False
        if t.item(i, 0).toolTip() == "The current stage":
            self.host.status("The current stage cannot be removed.")
            return False
        t.removeRow(i)
        return True

    def save_stages(self):
        r = self.rec
        rows, gates, bad = [], [], []
        for i in range(self.stage_table.rowCount()):
            sid, name, start, end, gate = self._stage_values(i)
            ds, de = (R.parse_date(start) if start.strip() else None), (R.parse_date(end) if end.strip() else None)
            if (start.strip() and ds is None) or (end.strip() and de is None):
                bad.append(name)
            rows.append((sid, name, ds.isoformat() if ds else "", de.isoformat() if de else ""))
            gates.append(gate)
        if bad:
            self.host.status("Dates not understood for: " + ", ".join(bad) + ". Write them like Nov 3, 2026.")
            return False
        try:
            new = r.edit_stages(rows)
        except ValueError as e:
            self.host.status(str(e))
            return False
        for s, g in zip(new, gates):
            r.set_gate(s["id"], g)
        diag.activity("qt_stages_saved")
        self.host.toast("Stages saved")
        self.refresh()
        return True

    # ------------------------------------------------------------ status, package, backup
    def status_export(self, path=None, final=False):
        import statusdoc as SDOC
        h = self.host
        if h.ws is None:
            return None
        if path is None:
            kind = "Effort_Summary" if final else "Effort_Status"
            fname = f"{h.effort_name}_{kind}_{datetime.date.today().isoformat()}.docx".replace(" ", "_")
            path, _ = QFileDialog.getSaveFileName(self, "Save the effort summary" if final else "Save the effort status",
                                                  os.path.join(os.path.dirname(h.effort_path), fname), "Word (*.docx)")
            if not path:
                return None
        st = ES.State(h.ws, h.effort_path, h.review.M if h.review is not None else None)
        try:
            SDOC.build(ES.status_snapshot(st, final=final, app_version=h.version, name=h.effort_name), path, final=final)
        except PermissionError:
            h.status("That file is open in Word. Close it, then save again.")
            return None
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

    def save_package(self, path=None, customer=True, volumes=True):
        import effortpkg as P
        h = self.host
        if h.ws is None:
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
                         app_version=a["app_version"], extra_files=a["extra_files"])
        except (OSError, PermissionError) as e:
            diag.swallowed()
            h.status(f"The package could not be written ({type(e).__name__}).")
            return None
        self.rec.log("effort", f"Effort package saved: {os.path.basename(man['path'])} ({a['stage']}, {len(man['files'])} files)", save=True)
        diag.activity("qt_package_saved", files=len(man["files"]))
        h.toast(f"Effort package saved: {os.path.basename(man['path'])}")
        return man

    def backup_dir(self):
        try:
            import app_gui
            return (app_gui.load_settings() or {}).get("backup_dir", "") or ""
        except Exception:
            diag.swallowed()
            return ""

    def backup_now(self, folder=None):
        """Back up the open effort to the backup folder set in Keep safe (folder: tests)."""
        import keepsafe as K
        h = self.host
        bd = folder or self.backup_dir()
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
