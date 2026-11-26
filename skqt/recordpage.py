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
        # 4.78.0 (E1, claude/stationkeeper-effort-settings-direction-2026-11-25.md): Effort Settings is four plain groups
        # of labels and values, kept as each is changed (no Save button). Customer, Solicitation number and Proposal due
        # are one value each with Customer information. The files the effort makes stay under Export.
        from .commandbar import CommandBar
        from PySide6.QtCore import QTimer
        self.bar = CommandBar()
        self.bar.export("Effort status (Word)...", lambda: self.status_export(), "Where the effort stands, for leadership")
        self.bar.export("Effort summary (Word)...", lambda: self.status_export(final=True), "The effort with its complete history")
        self.bar.export("Save effort package...", lambda: self.save_package(), "The whole effort in one .skpkg file for a hand-off")
        self.a_team = self.bar.export("Save to the team folder", lambda: self.save_to_team(),
                                      "Connected mode: the package goes to the team's OneDrive-synced SharePoint folder")
        v.addWidget(self.bar)
        self.kept_note = D.label("Kept as you change it.", "muted")
        v.addWidget(self.kept_note)

        def heading(text):
            v.addSpacing(D.SPACE["s"])
            v.addWidget(D.label(text, "title"))

        def form():
            f = QFormLayout(); f.setSpacing(D.SPACE["s"]); f.setLabelAlignment(Qt.AlignLeft)
            f.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
            holder = QWidget(); holder.setMaximumWidth(760); holder.setLayout(f); v.addWidget(holder)
            return f

        # 1. Effort
        heading("Effort")
        form1 = form()
        self.name = D.label("", None)
        self.internal = QLineEdit(); self.internal.setPlaceholderText("Not set")
        self.client = QLineEdit(); self.client.setPlaceholderText("Not set")
        self.sol = QLineEdit(); self.sol.setPlaceholderText("Not set")
        for w, tip in ((self.internal, "Your company's internal number for this effort"),
                       (self.client, "The same value as Customer on Customer information"),
                       (self.sol, "The same value as on Customer information")):
            w.setToolTip(tip)
            w.editingFinished.connect(self.save_details)
        due = QHBoxLayout(); due.setSpacing(D.SPACE["s"])
        self.has_due = QCheckBox("Due on")
        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True); self.due_date.setDisplayFormat("MMM d, yyyy")
        self.due_time = QTimeEdit(); self.due_time.setDisplayFormat("h:mm AP")
        self.zone = QLineEdit(); self.zone.setMaximumWidth(140)
        self.has_due.setVisible(False)                          # 3.12.0: the date is the customer's deadline, or "Not set"
        self.due_date.setMinimumDate(QDate(2000, 1, 1)); self.due_date.setSpecialValueText("Not set")
        self.due_date.dateChanged.connect(lambda d: None if getattr(self, "_filling_due", False) else
                                          self.has_due.setChecked(d != self.due_date.minimumDate()))
        self.due_time.timeChanged.connect(lambda *_a: None if getattr(self, "_filling_due", False) or
                                          self.due_date.date() == self.due_date.minimumDate() else self.has_due.setChecked(True))
        self.has_due.toggled.connect(lambda on: None if on or self.due_date.date() == self.due_date.minimumDate()
                                     else self.due_date.setDate(self.due_date.minimumDate()))
        self.zone.setPlaceholderText("Time zone")
        self.zone.setToolTip("The customer's time zone: ET, CT, MT, PT, UTC...")
        self.clear_due = D.button("Clear", "ghost", lambda: self.due_date.setDate(self.due_date.minimumDate()), "No due date yet")
        for w in (self.due_date, self.due_time, self.zone, self.clear_due):
            due.addWidget(w)
        due.addStretch(1)
        self._due_timer = QTimer(self); self._due_timer.setSingleShot(True); self._due_timer.setInterval(700)
        self._due_timer.timeout.connect(lambda: self.save_details(quiet=True))
        for sig in (self.due_date.dateChanged, self.due_time.timeChanged):
            sig.connect(lambda *_a: None if getattr(self, "_filling_due", False) else self._due_timer.start())
        self.zone.editingFinished.connect(self.save_details)
        form1.addRow("Effort name", self.name)
        form1.addRow("A number", self.internal)
        form1.addRow("Customer", self.client)
        form1.addRow("Solicitation number", self.sol)
        form1.addRow("Proposal due", due)
        self.found_box = QWidget(); self.found_row = QHBoxLayout(self.found_box); self.found_row.setContentsMargins(0, 0, 0, 0)
        self.found = D.label("", "muted"); self.found_row.addWidget(self.found, 1)
        self.use_found = D.button("Use it", None, lambda: self.use_customer_due() and self.save_details()); self.found_row.addWidget(self.use_found)
        form1.addRow("", self.found_box)
        self.details = None

        # 2. People
        heading("People")
        prow = QHBoxLayout()
        prow.addWidget(D.label("Names come from Settings > Author list. A role is a label; it limits nothing.", "muted"), 1)
        prow.addWidget(D.button("Choose people...", None, lambda: self.choose_team()))
        v.addLayout(prow)
        from .rolesview import TeamRoles                     # 2.93.0: a role drop-down per person that saves when picked
        self.team_roles = TeamRoles(host)
        v.addWidget(self.team_roles)
        self.team_table, self.team_note = self.team_roles.table, self.team_roles.note
        self.team = None

        # 3. Stages and reviews
        heading("Stages and reviews")
        ed = self.stage_editor()                             # 3.82.0: one row at a time, edited in the panel beside it
        self.stage_table.setMinimumHeight(240)
        self.stage_table.setContextMenuPolicy(Qt.CustomContextMenu)            # 3.75.0: act on the row
        self.stage_table.customContextMenuRequested.connect(lambda pos: self.stage_menu().exec(self.stage_table.viewport().mapToGlobal(pos)))
        srow = QHBoxLayout()
        self.stage_note = D.label("Pick a stage to change it beside the list. Right-click to move it or remove it. "
                                  "The current stage moves on Overview.", "muted")
        srow.addWidget(self.stage_note, 1)
        srow.addWidget(D.button("+ Stage", None, lambda: self.add_stage(), "Add a stage after the last one"))
        v.addLayout(srow)
        v.addWidget(ed)
        self._stage_timer = QTimer(self); self._stage_timer.setSingleShot(True); self._stage_timer.setInterval(700)
        self._stage_timer.timeout.connect(self.keep_stages)
        self.stages = None

        # 4. Files and sources
        heading("Files and sources")
        form4 = form()
        frow = QHBoxLayout(); frow.setSpacing(D.SPACE["s"])
        self.saved_in = D.label("", None); self.saved_in.setTextInteractionFlags(Qt.TextSelectableByMouse)
        frow.addWidget(self.saved_in, 1)
        frow.addWidget(D.button("Open folder", "ghost", lambda: self.open_folder(), "Open the effort's folder"))
        form4.addRow("Saved in", frow)
        srow2 = QHBoxLayout(); srow2.setSpacing(D.SPACE["s"])
        srow2.addWidget(D.label("Effort Standards, over Global Standards", None), 1)
        srow2.addWidget(D.button("Open", "ghost", lambda: self.host.go("effortfmt"), "Effort Formatting"))
        form4.addRow("Standards", srow2)
        v.addSpacing(D.SPACE["m"])

        # 2.80.0 effort health
        self.readable = D.Card("Readable copy", "Everything in the effort as plain files (Excel, Word, CSV, text) in its folder, "
                               "rewritten a few seconds after every change, so the effort can carry on without Stationkeeper "
                               "(More > Open the readable copy).")
        self.readable_text = self.readable.add(D.label("", "muted"))
        self.readable.setVisible(False)                # 4.61.0: no longer shown or rewritten on its own
        self.health = D.Card("Effort health", "Checked each time the effort opens. A damaged list or matrix is put back from its "
                             "newest good copy automatically.")
        self.health_box = QVBoxLayout(); self.health.body.addLayout(self.health_box)
        self.health.setVisible(False)                  # 4.61.0: still checked when the effort opens; a problem found is said then
        # reports, package, backup: under Export and More (3.75.0)
        self.out = D.Card("Backups")
        self.team_btn = self.a_team
        self.backup_text = self.out.add(D.label("", "muted"))
        self.out.setVisible(False)                     # 4.61.0: the Effort Backup page
        v.addStretch(1)

    def stage_menu(self):
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction("Earlier", lambda: self.move_row(-1))
        m.addAction("Later", lambda: self.move_row(1))
        m.addSeparator()
        m.addAction("Remove this stage", lambda: self.remove_stage())
        return m

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
        self.flush()
        self.setEnabled(h.ws is not None)
        if h.ws is None:
            return
        from . import sharedfacts as SF
        r = self.rec
        self.L = L = self.effort_list()
        self.name.setText(__import__("homes").shown_name(h.efforts, h.effort_name))   # 4.51.0: Unfiled, from before
        self.internal.setText((L.internal_no if L else "") or "")
        for w, lab in ((self.client, "Customer"), (self.sol, "Solicitation number")):   # 4.78.0: one value with Customer information
            w.setText(SF.CI.fact(r, lab, L)["value"] if L is not None else "")
        self._fill_due(r)
        st = ES.State(h.ws, h.effort_path, None)
        import subreq as SR
        sm = SR.summary(st.rows)
        self.customer_due = sm["due"]["value"] if sm.get("due") else ""
        iso, _z = R.parse_due_text(self.customer_due) if self.customer_due else (None, "")
        differs = bool(self.customer_due) and (not iso or iso != (r.data.get("due") or ""))
        self.found.setText(f"The customer's documents say: {self.customer_due}" if differs else "")
        self.use_found.setVisible(differs); self.found_box.setVisible(differs)
        try:
            self.saved_in.setText(EF.root(h.effort_path) or "Not set")
        except Exception:  # noqa: BLE001
            diag.swallowed(); self.saved_in.setText("Not set")
        self.fill_team(r)
        self.fill_stages(r)
        t = self.stage_table                                  # 4.78.0: every stage shows without scrolling the table
        t.setMinimumHeight(max(240, t.horizontalHeader().height() + sum(t.rowHeight(i) for i in range(t.rowCount()))
                               + t.horizontalScrollBar().sizeHint().height() + 8))
        self.fill_health(self.host.safety.issues)
        self.backup_text.setText(self.host.safety.status_text())     # 2.78.0: automatic, with the last time
        import workmode as WM
        from .modes import settings
        self.team_btn.setVisible(bool(WM.team_dir(settings())))

    def _fill_due(self, r):
        due = r.data.get("due", "")
        d = R.parse_date(due[:10]) if due else None
        self._filling_due = True
        self.has_due.setChecked(d is not None)
        self.due_date.setDate(QDate(d) if d else self.due_date.minimumDate())
        hm = due[11:16] if len(due) > 15 else ""
        self.due_time.setTime(QTime(int(hm[:2]), int(hm[3:5])) if hm[:2].isdigit() and hm[3:5].isdigit() else QTime(14, 0))
        self.zone.setText(r.data.get("zone", ""))
        self._filling_due = False

    def flush(self):
        """4.78.0: keep anything changed a moment ago before the page is filled again or left."""
        if self._due_timer.isActive():
            self._due_timer.stop(); self.save_details(quiet=True)
        if self._stage_timer.isActive():
            self._stage_timer.stop(); self.keep_stages()

    def open_folder(self):
        import subprocess, sys
        p = self.saved_in.text()
        if not p or not os.path.isdir(p):
            self.host.status("The effort's folder was not found.")
            return False
        if os.environ.get("AH_TEST"):
            return True
        try:
            if sys.platform.startswith("win"):
                os.startfile(p)                                   # noqa: S606
            else:
                subprocess.Popen(["xdg-open", p])
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return False
        return True

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

    def save_details(self, quiet=False):
        """4.78.0: kept as each field is changed (no Save button). Customer and Solicitation number go through the one
        value they share with Customer information; the A number stays in the effort list; Proposal due is the record's."""
        h = self.host
        if h.ws is None:
            return False
        from . import sharedfacts as SF
        r, L = self.rec, self.L
        kept = []
        if L is not None:
            val = " ".join(self.internal.text().split())
            if (L.internal_no or "") != val:
                L.internal_no = val
                try:
                    L.pending = True
                    L.save()
                    h.efforts.put(h.effort_name, client=L.client, solicitation=L.solicitation, internal_no=L.internal_no)
                except Exception:
                    diag.swallowed()
                    h.status("The effort list is open in Excel: close it, then change it again.")
                    return False
                r.log("effort", f"A number: {val or '(none)'}", save=True)
                kept.append("A number")
            for w, lab in ((self.client, "Customer"), (self.sol, "Solicitation number")):
                out = SF.set_fact(h, lab, w.text(), "typed", replace=True, L=L)
                if out in SF.MESSAGES:
                    return False
                if out in ("set", "cleared"):
                    kept.append(lab)
        iso = ""
        if self.has_due.isChecked():
            iso = self.due_date.date().toPython().isoformat() + "T" + self.due_time.time().toString("HH:mm")
        zone = " ".join(self.zone.text().split()) if iso else ""
        r = self.rec
        if iso != r.data.get("due", "") or zone != r.data.get("zone", ""):
            r.set_due(iso, zone, who=SF.who() or None)
            kept.append("Proposal due")
        if kept:
            diag.activity("qt_effort_details_saved")
            h.status(", ".join(kept) + " kept.")
        elif not quiet:
            pass
        return True

    def _stages_changed(self):
        """4.78.0: a stage changed in the table or the panel is kept a moment later (no Save stages button)."""
        self._stage_timer.start()

    def keep_stages(self):
        """Keep the stages as the table shows them, without filling the page again (the row being changed stays put).
        A time not understood, or a stage that ends before it starts, is said on the line under the heading."""
        h = self.host
        if h.ws is None:
            return False
        bad = self.stage_problems()
        if bad:
            self.stage_note.setText("Not kept yet: " + "; ".join(bad) + ".")
            return False
        r = self.rec
        rows, gates, colors, at = [], [], [], []
        for i in range(self.stage_table.rowCount()):
            sid, name, (ds, ts), (de, te), gate = self._stage_values(i)
            if not (name or "").strip():
                continue
            rows.append((sid, name, ds, de, ts if ds else "", te if de else ""))
            gates.append(gate); colors.append(self._stage_color(i)); at.append(i)
        try:
            new = r.edit_stages(rows)
        except ValueError as e:
            self.stage_note.setText(str(e))
            return False
        for s, g, c in zip(new, gates, colors):
            r.set_gate(s["id"], g)
            r.set_stage_color(s["id"], c)
        was = self._loading
        self._loading = True
        for i, s in zip(at, new):
            it = self.stage_table.item(i, 0)
            if it is not None and it.data(Qt.UserRole) != s["id"]:
                it.setData(Qt.UserRole, s["id"])
        self._loading = was
        self.stage_note.setText("Pick a stage to change it beside the list. Right-click to move it or remove it. "
                                "The current stage moves on Overview.")
        diag.activity("qt_stages_saved")
        h.status("Stages kept.")
        return True

    # ------------------------------------------------------------ team (2.77.0: from the author list)
    def fill_team(self, r=None):
        self.team_roles.fill()
        t = self.team_table                                   # 4.78.0: as tall as its people, not a fixed block
        rows = max(1, t.rowCount())
        t.setMinimumHeight(0)
        t.setFixedHeight(t.horizontalHeader().height() + sum(t.rowHeight(i) for i in range(t.rowCount())) + (0 if t.rowCount() else 34) + 6)

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
        try:                                                     # 3.12.0: every overview kept, with the summary written for it
            stage = (st.rec.stage() or {}).get("name", "")
        except Exception:
            stage = ""
        st.rec.data.setdefault("overviews", []).insert(0, {"at": st.rec.data["overview_last"], "stage": stage,
                                                           "summary": st.rec.data.get("pm_summary", ""), "file": os.path.abspath(path),
                                                           "final": bool(final)})
        del st.rec.data["overviews"][200:]
        st.rec.log("effort", ("Effort summary" if final else "Effort status") + f" exported: {os.path.basename(path)}", save=True)
        diag.activity("qt_status_exported")
        h.toast(("Effort summary" if final else "Effort status") + " written")
        return path

    def overviews(self):
        """3.12.0: the overviews exported for this effort, newest first: [{at, stage, summary, file, final}]."""
        r = self.rec
        return list((r.data.get("overviews") if r is not None else None) or [])

    def overviews_dialog(self, run=True):
        """3.12.0: All overviews: each exported overview with its date, stage and the summary written for it; Open opens
        its Word file. run=False (tests): the dialog."""
        from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QPlainTextEdit, QTableWidget, QTableWidgetItem
        if self.host.ws is None:
            return None
        rows = self.overviews()
        dlg = QDialog(self); dlg.setWindowTitle("All overviews"); dlg.resize(860, 520)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("Every overview exported for this effort, newest first. The summary is what the proposal manager wrote "
                            "for it: where the effort stood.", "muted"))
        t = QTableWidget(len(rows), 3); t.setHorizontalHeaderLabels(["Exported", "Stage", "Summary"])
        t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setColumnWidth(0, 150); t.setColumnWidth(1, 150); t.horizontalHeader().setStretchLastSection(True)
        for i, o in enumerate(rows):
            for c, val in enumerate((o.get("at", "").replace("T", " ") + ("  (final)" if o.get("final") else ""), o.get("stage", ""),
                                     (o.get("summary") or "No summary written").split("\n")[0][:160])):
                t.setItem(i, c, QTableWidgetItem(val))
        v.addWidget(t, 1)
        full = QPlainTextEdit(); full.setReadOnly(True); full.setMaximumHeight(140); v.addWidget(full)
        t.currentCellChanged.connect(lambda r_, *_a: full.setPlainText(rows[r_].get("summary") or "No summary written") if 0 <= r_ < len(rows) else None)
        if not rows:
            full.setPlainText("No overviews yet. Export overview... on Overview writes the first.")
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        open_btn = bb.addButton("Open", QDialogButtonBox.ActionRole)

        def open_it():
            r_ = t.currentRow()
            f = rows[r_].get("file", "") if 0 <= r_ < len(rows) else ""
            if not f or not os.path.isfile(f):
                self.host.status("That overview's file is no longer where it was saved.")
                return
            if not os.environ.get("AH_TEST"):
                from PySide6.QtCore import QUrl
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(f))
        open_btn.clicked.connect(open_it)
        t.cellDoubleClicked.connect(lambda *_a: open_it())
        bb.rejected.connect(dlg.reject); bb.accepted.connect(dlg.accept); v.addWidget(bb)
        if rows:
            t.selectRow(0)
        dlg.api = {"table": t, "summary": full, "open": open_it, "rows": rows}
        if not run:
            return dlg
        dlg.exec()
        return dlg

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

    def open_backups(self, open_it=True):
        """4.30.1: the effort's backups in File Explorer (their folder is hidden with the app's data). Returns the folder."""
        import hidefolders as HF
        if self.host.ws is None:
            self.host.status("Open an effort first.")
            return ""
        d = HF.backups_folder(self.host.ws.root)
        if open_it and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        diag.activity("qt_backups_folder_opened")
        self.host.status("The effort's backups are in " + d)
        return d

    def backup_now(self, folder=None):
        """Back up the open effort to the backup folder set in Keep safe (folder: tests)."""
        import keepsafe as K
        h = self.host
        bd = folder or self.backup_dir()
        if h.ws is not None:
            pass                                                # 4.61.0: no readable copy beside the effort
        if h.ws is None or not bd:
            h.status("Backups are off. Choose the backup folder on Effort Backup.")
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
