"""Branding in Qt (2.88.0): the effort banner on Effort home (the effort's picture, its name, its sensitivity, the due date
with a live countdown, the proposal manager, client, solicitation and the effort's own spots), the marking strip across
every page for a CUI or proprietary effort, the company logos at the top of the menu and the Stationkeeper mark at its
foot, Customize Home (a role's layout, then show, hide and order the sections) and the Branding card in Settings.
The rules are branding's. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)
import branding as BR
import diag
from . import design as D
from .adaptive import FlowLayout

PIC = 132                    # the effort picture on the banner, square


def asset(name):
    import app_gui
    return os.path.join(app_gui.BASE_DIR, "assets", name)


def rounded(path, w, h, radius=12, fit=False):
    """A picture scaled into w x h with rounded corners (fit: the whole picture, else cropped to fill)."""
    src = QPixmap(path)
    if src.isNull():
        return QPixmap()
    mode = Qt.KeepAspectRatio if fit else Qt.KeepAspectRatioByExpanding
    sc = src.scaled(w, h, mode, Qt.SmoothTransformation)
    out = QPixmap(w if not fit else sc.width(), h if not fit else sc.height())
    out.fill(Qt.transparent)
    p = QPainter(out); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
    path_ = QPainterPath(); path_.addRoundedRect(QRectF(0, 0, out.width(), out.height()), radius, radius)
    p.setClipPath(path_)
    p.drawPixmap((out.width() - sc.width()) // 2, (out.height() - sc.height()) // 2, sc)
    p.end()
    return out


class PictureBox(QToolButton):
    """The effort's picture: click to add one, or to change or remove it."""

    def __init__(self, banner):
        super().__init__()
        self.banner = banner
        self.setFixedSize(PIC, PIC)
        self.setIconSize(QSize(PIC, PIC))
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.menu)
        self.setAcceptDrops(True)                     # 3.0.3: drop a picture file on it to set or change it

    def dragEnterEvent(self, e):
        from .starteffort import PictureDrop
        if PictureDrop._picture_in(e):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        self.dragEnterEvent(e)

    def dropEvent(self, e):
        from .starteffort import PictureDrop
        p = PictureDrop._picture_in(e)
        if p:
            self.banner.choose_picture(p)
            e.acceptProposedAction()

    def show_path(self, path):
        t = D.tokens()
        if path and os.path.isfile(path):
            self.setIcon(rounded(path, PIC, PIC, 14)); self.setText("")
            self.setToolTip("The effort's picture. Click to change or remove it, or drop another picture on it.")
            self.setStyleSheet("QToolButton{border:none;background:transparent;}")
        else:
            from PySide6.QtGui import QIcon
            self.setIcon(QIcon()); self.setText("+\nEffort image\n\nclick or drop\na picture")
            self.setToolTip("Add a picture that stands for the effort (a mission patch, a logo or a cover image): click, or drop a picture file here")
            self.setStyleSheet(f"QToolButton{{border:2px dashed {t['border_strong']};border-radius:14px;background:{t['surface2']};"
                               f"color:{t['muted']};font-weight:600;}} QToolButton:hover{{border-color:{t['accent']};color:{t['accent']};}}")

    def menu(self):
        b = self.banner
        if not BR.has_picture(b.data_dir()):
            b.choose_picture()
            return
        m = QMenu(self)
        m.addAction("Change the picture...", b.choose_picture)
        m.addAction("Remove the picture", b.remove_picture)
        m.exec(self.mapToGlobal(self.rect().bottomLeft()))


class EffortBanner(QFrame):
    """The top of Effort home: who the effort is for, how it is marked, and how long is left."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.host = page.host
        self.setObjectName("banner")
        self.ident = {"pm": "", "sensitivity": "", "fields": []}
        self.due_iso = ""
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["l"], D.SPACE["l"], D.SPACE["l"], D.SPACE["l"]); h.setSpacing(D.SPACE["l"])
        self.pic = PictureBox(self); h.addWidget(self.pic, 0, Qt.AlignTop)
        mid = QVBoxLayout(); mid.setSpacing(6); h.addLayout(mid, 1)
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); mid.addLayout(top)
        self.name = QLabel(""); self.name.setObjectName("bannerName"); self.name.setWordWrap(True)
        top.addWidget(self.name, 1)
        self.sens = D.Pill("", "head"); top.addWidget(self.sens, 0, Qt.AlignTop)
        self.pagelim = D.Pill("", "head"); top.addWidget(self.pagelim, 0, Qt.AlignTop)    # 2.94.0: page-limited, front and center
        self.stage = D.Pill("", "accent"); top.addWidget(self.stage, 0, Qt.AlignTop)
        self.sub = D.label("", "muted"); mid.addWidget(self.sub)
        self.grid = QGridLayout(); self.grid.setHorizontalSpacing(D.SPACE["xl"]); self.grid.setVerticalSpacing(4)
        mid.addLayout(self.grid)
        acts = FlowLayout(None, D.SPACE["s"]); mid.addLayout(acts)
        self.edit_btn = D.button("Edit details...", None, lambda: self.edit_dialog(), "Proposal manager, client, sensitivity and "
                                 "the effort's own spots. They travel with the effort.")
        acts.addWidget(self.edit_btn)
        acts.addWidget(D.button("People and roles...", None, lambda: self.people_roles(),     # 2.93.0
                                "Who works on this effort and in what role; a role saves when picked"))
        acts.addWidget(D.button("Open effort folder", None, lambda: self.host.open_effort_folder(),
                                "The effort's folder in File Explorer: customer documents, volumes, Response Setup, exports"))
        acts.addWidget(D.button("Export overview...", None, lambda: self.host.record_page.status_export(),
                                "The effort as it stands now, in Word: your summary, stages, people and how far along they are, "
                                "open questions, the newest customer documents, what is coming up"))
        acts.addWidget(D.button("Readable copy", None, lambda: self.host.open_readable(),
                                "Everything in the effort as plain files that open without Stationkeeper"))
        self.page_deliv = D.button("", "ghost", lambda: self.host.go("deliverables"), "The deliverables board")
        acts.addWidget(self.page_deliv)
        acts.addStretch(1)
        # the countdown
        right = QFrame(); right.setObjectName("countdown"); h.addWidget(right, 0, Qt.AlignTop)
        rv = QVBoxLayout(right); rv.setContentsMargins(D.SPACE["l"], D.SPACE["m"], D.SPACE["l"], D.SPACE["m"]); rv.setSpacing(0)
        self.due_head = QLabel("DUE IN"); self.due_head.setObjectName("cdHead"); rv.addWidget(self.due_head, 0, Qt.AlignRight)
        self.days = QLabel(""); self.days.setObjectName("cdDays"); rv.addWidget(self.days, 0, Qt.AlignRight)
        self.clock = QLabel(""); self.clock.setObjectName("cdClock"); rv.addWidget(self.clock, 0, Qt.AlignRight)
        self.due = QLabel(""); self.due.setObjectName("cdDue"); self.due.setWordWrap(True); self.due.setMaximumWidth(240)
        self.due.setAlignment(Qt.AlignRight); rv.addWidget(self.due, 0, Qt.AlignRight)
        self.right = right
        self.timer = QTimer(self, interval=1000, timeout=self.tick)
        self.restyle()

    # ------------------------------------------------------------ look
    def restyle(self, tone_name="accent"):
        t = D.tokens()
        col = t.get(tone_name, t["accent"])
        self.setStyleSheet(
            f"QFrame#banner{{background:{t['surface']};border:1px solid {t['border']};border-radius:{D.RADIUS['card'] + 4}px;}}"
            f"QFrame#banner QLabel{{background:transparent;}}"
            f"QLabel#bannerName{{font-size:22pt;font-weight:700;color:{t['text']};}}"
            f"QFrame#countdown{{background:{t.get(tone_name + '_soft', t['accent_soft'])};border-radius:{D.RADIUS['card']}px;border:none;}}"
            f"QLabel#cdHead{{color:{col};font-size:{D.TYPE['label']}pt;font-weight:700;letter-spacing:1.2px;}}"
            f"QLabel#cdDays{{color:{col};font-size:30pt;font-weight:700;}}"
            f"QLabel#cdClock{{color:{col};font-size:13pt;font-weight:600;font-family:'{D.MONO_FONT}';}}"
            f"QLabel#cdDue{{color:{t['muted']};font-size:{D.TYPE['small']}pt;padding-top:4px;}}"
            f"QLabel[role='spotlab']{{color:{t['muted']};font-size:{D.TYPE['label']}pt;font-weight:700;letter-spacing:0.6px;}}"
            f"QLabel[role='spotval']{{color:{t['text']};font-weight:600;}}")

    def data_dir(self):
        return self.host.ws.root if self.host.ws is not None else ""

    # ------------------------------------------------------------ fill
    def fill(self, rec, effort_list=None, stage=""):
        h = self.host
        self.ident = BR.identity(rec)
        self.pic.show_path(BR.picture_path(self.data_dir()))
        self.name.setText(h.effort_name)
        sens = self.ident["sensitivity"]
        self.sens.setText(sens or "Sensitivity not set"); self.sens.set_tone(BR.tone(sens))
        self.sens.setToolTip("How the effort is marked. CUI and Proprietary mark every page with a strip across the top.")
        self.stage.setText(stage); self.stage.setVisible(bool(stage))
        try:                                                                    # 2.94.0
            import docversions as DV
            import formatreq as FR
            self.fmt = FR.for_effort(DV.Library(h.ws.p("documents")).load(), rec)
        except Exception:
            diag.swallowed()
            import formatreq as FR
            self.fmt = FR.card([], rec.data.get("page_limited", ""))
        pl = self.fmt["page_limited"]
        self.pagelim.setText(FR.flag_text(self.fmt))
        self.pagelim.set_tone("warn" if pl else ("ok" if pl is False else "head"))
        self.pagelim.setToolTip({"set": "Set by the proposal manager (Edit details).", "found": "Page limits found in the customer documents "
                                 "(Submission rules). Edit details can set it."}.get(self.fmt["how"], "No page limit found in the customer "
                                 "documents yet. Edit details can say the effort is page-limited or not."))
        L = effort_list
        self.client = (L.client if L else "") or ""
        self.solicitation = (L.solicitation if L else "") or ""
        self.sub.setText("  ·  ".join(x for x in (self.client, self.solicitation) if x) or "Client and solicitation not set yet")
        spots = [("PROPOSAL MANAGER", BR.proposal_manager(rec, self.ident) or "Not set")]
        spots += [("CLIENT", self.client or "Not set"), ("SOLICITATION", self.solicitation or "Not set")]
        spots += [("PAGE-LIMITED", FR.spot_text(self.fmt))]                    # 2.94.0
        spots += [(f["label"].upper(), f["value"] or "-") for f in self.ident["fields"]]
        self.spots = spots
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        per_row = 4
        for i, (lab, val) in enumerate(spots):
            r, c = divmod(i, per_row)
            a = D.label(lab, "spotlab", wrap=False); b = D.label(val, "spotval")
            self.grid.addWidget(a, r * 2, c); self.grid.addWidget(b, r * 2 + 1, c)
        self.due_iso = rec.data.get("due", "")
        import effortrec as R
        import tzones as TZ
        from .modes import settings
        self.zone_key = rec.zone_key()
        self.my_zone = TZ.my_zone(settings())
        if self.due_iso and self.zone_key and len(self.due_iso) > 10:          # 2.92.0: the customer's zone and yours
            import datetime as _dt
            first, mine = TZ.both(_dt.datetime.fromisoformat(self.due_iso), self.zone_key, self.my_zone)
            self.due.setText("Due " + first + (f"\n{mine}" if mine else ""))
            self.due.setToolTip(f"The submission's time zone: {TZ.name(self.zone_key)}. Yours: {TZ.name(self.my_zone)} "
                                "(Settings > Your time zone).")
        else:
            self.due.setText(("Due " + R.due_text(self.due_iso, rec.data.get("zone", ""))) if self.due_iso else
                             "No due date set yet. Set it in Edit details.")
        self.tick()
        if self.due_iso and not self.timer.isActive():
            self.timer.start()
        elif not self.due_iso:
            self.timer.stop()

    def tick(self, now=None):
        c = BR.countdown(self.due_iso, now, getattr(self, "zone_key", ""))
        self.cd = c
        if c is None:
            self.due_head.setText("DUE DATE"); self.days.setText("-"); self.clock.setText("")
        elif c[0] == "passed":
            self.due_head.setText("DUE DATE"); self.days.setText("Passed"); self.clock.setText(f"{c[1]} day(s) ago" if c[1] else "today")
        else:
            d, hh, mm, ss = c
            self.due_head.setText("DUE IN"); self.days.setText(f"{d} day{'s' if d != 1 else ''}"); self.clock.setText(f"{hh:02d}:{mm:02d}:{ss:02d}")
        tn = BR.countdown_tone(c)
        if getattr(self, "_tone", None) != tn:
            self._tone = tn
            self.restyle("accent" if tn == "head" else tn)

    # ------------------------------------------------------------ the picture
    def choose_picture(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "The effort's picture", "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return False
        try:
            BR.set_picture(self.data_dir(), path)
        except Exception:
            diag.swallowed()
            self.host.status("That picture could not be read. Try a PNG or JPG.")
            return False
        diag.activity("qt_effort_picture_set")
        self.pic.show_path(BR.picture_path(self.data_dir()))
        self.host.toast("Effort picture saved with the effort")
        return True

    def remove_picture(self):
        BR.clear_picture(self.data_dir())
        self.pic.show_path("")
        return True

    # ------------------------------------------------------------ details
    def people_roles(self, run=True):
        from .rolesview import PeopleRolesDialog
        d = PeopleRolesDialog(self.host, self)
        if not run:
            return d
        d.exec()
        self.host.home_page.refresh() if hasattr(self.host.home_page, "refresh") else None
        return d

    def edit_dialog(self, answer=None):
        """Edit the effort's identity. answer (tests): {pm, sensitivity, fields, client, solicitation}."""
        if self.host.ws is None:
            return False
        if answer is None:
            dlg = DetailsDialog(self, self.ident, self.client, self.solicitation)
            if dlg.exec() != QDialog.Accepted:
                return False
            answer = dlg.values()
        return self.save_details(answer)

    def save_details(self, v):
        import effortrec as R
        h = self.host
        rec = R.Record(h.ws.root)
        BR.set_identity(rec, pm=v.get("pm"), sensitivity=v.get("sensitivity"), fields=v.get("fields"))
        if "due" in v and v["due"] != rec.data.get("due", ""):                  # 2.92.0: the due date and time, here too
            import tzones as TZ
            zk = v.get("zone_key", rec.zone_key()) or ""
            rec.set_due(v["due"], (zk if zk in TZ.ZONES else zk) if v["due"] else "", zone_key=zk if v["due"] else "")
            rec = R.Record(h.ws.root)
        if "zone_key" in v and v["zone_key"] != rec.zone_key():                  # 2.92.0: the submission's time zone
            import tzones as TZ
            rec.data["zone_key"] = v["zone_key"] or ""
            if v["zone_key"]:
                rec.data["zone"] = v["zone_key"] if v["zone_key"] in TZ.ZONES else v["zone_key"]
            rec.log("effort", f"Submission time zone: {TZ.name(v['zone_key']) or 'not set'}", save=True)
        if "page_limited" in v and (v["page_limited"] or "") != rec.data.get("page_limited", ""):    # 2.94.0
            import formatreq as FR
            rec.data["page_limited"] = v["page_limited"] or ""
            rec.log("effort", f"Page-limited: {FR.SETTINGS.get(rec.data['page_limited'], '').lower()}", save=True)
        if "client" in v or "solicitation" in v:
            L = h.record_page.effort_list()
            if L is not None:
                cl = " ".join(str(v.get("client", L.client) or "").split()); so = " ".join(str(v.get("solicitation", L.solicitation) or "").split())
                if (cl, so) != (L.client, L.solicitation):
                    L.client, L.solicitation = cl, so
                    try:
                        L.pending = True; L.save()
                        h.efforts.put(h.effort_name, client=L.client, solicitation=L.solicitation, internal_no=L.internal_no)
                        rec.log("effort", "Effort details: client and solicitation", save=True)
                    except Exception:
                        diag.swallowed()
                        h.status("The effort list is open in Excel: close it, then save the details again.")
        diag.activity("qt_effort_identity_saved")
        h.apply_marking()
        self.page.refresh()
        h.toast("Effort details saved with the effort")
        return True


class DetailsDialog(QDialog):
    def __init__(self, parent, ident, client, solicitation):
        super().__init__(parent)
        self.setWindowTitle("Effort details")
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.addWidget(D.label("These travel with the effort: everyone who opens it sees them, and packages and backups carry them.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        host = parent.host
        self.pm = QComboBox(); self.pm.setEditable(True)
        names = host.authors.for_effort(host.effort_name) if getattr(host, "authors", None) else []
        self.pm.addItems([""] + names); self.pm.setCurrentText(ident["pm"])
        self.client = QLineEdit(client); self.client.setPlaceholderText("USSF SSC")
        self.sol = QLineEdit(solicitation); self.sol.setPlaceholderText("FA8810-26-R-0042")
        import teampack as TP
        team_marks = TP.markings(host.config_dir)                    # 2.89.0: the team's markings
        marks = list(dict.fromkeys([*BR.MARKINGS, *team_marks])) if not TP.locked(host.config_dir, "markings") else ([BR.NOT_CUI] + team_marks)
        self.sens = QComboBox(); self.sens.setEditable(not TP.locked(host.config_dir, "markings")); self.sens.addItems(["", *marks])
        if ident["sensitivity"] and self.sens.findText(ident["sensitivity"]) < 0:
            self.sens.addItem(ident["sensitivity"])
        self.sens.setCurrentText(ident["sensitivity"])
        self.sens.setToolTip("CUI and Proprietary mark every page with a strip across the top. Type your own marking if the team uses another.")
        import tzones as TZ
        import effortrec as _R
        rec = _R.Record(host.ws.root)
        self.zone = QComboBox(); self.zone.addItem("Not set", "")
        for k, text in TZ.choices():
            self.zone.addItem(text, k)
        zk = rec.zone_key()
        if zk and self.zone.findData(zk) < 0:
            self.zone.addItem(zk, zk)
        self.zone.setCurrentIndex(max(0, self.zone.findData(zk)))
        self.zone.setToolTip("The time zone the customer's deadline is written in. Your own is in Settings.")
        f.addRow("Proposal manager", self.pm); f.addRow("Client", self.client); f.addRow("Solicitation", self.sol)
        from PySide6.QtCore import QDate, QTime
        from PySide6.QtWidgets import QCheckBox, QDateEdit, QTimeEdit
        due = rec.data.get("due", "")
        dd = _R.parse_date(due[:10]) if due else None
        self.has_due = QCheckBox("Due date set"); self.has_due.setChecked(dd is not None)
        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True); self.due_date.setDisplayFormat("MMM d, yyyy")
        self.due_date.setDate(QDate(dd.year, dd.month, dd.day) if dd else QDate.currentDate().addDays(30))
        self.due_time = QTimeEdit(); self.due_time.setDisplayFormat("h:mm AP")
        hm = due[11:16] if len(due) > 15 else "14:00"
        self.due_time.setTime(QTime(int(hm[:2]), int(hm[3:5])))
        self.due_date.dateChanged.connect(lambda *_a: self.has_due.setChecked(True))
        self.due_time.timeChanged.connect(lambda *_a: self.has_due.setChecked(True))
        drow = QHBoxLayout(); drow.addWidget(self.due_date); drow.addWidget(self.due_time); drow.addWidget(self.has_due); drow.addStretch(1)
        f.addRow("Proposal due", drow)
        f.addRow("Submission time zone", self.zone)
        f.addRow("Sensitivity", self.sens)
        import formatreq as FR                                                  # 2.94.0
        self.pagelim = QComboBox()
        for k, t in FR.SETTINGS.items():
            self.pagelim.addItem(t, k)
        self.pagelim.setCurrentIndex(max(0, self.pagelim.findData(rec.data.get("page_limited", ""))))
        self.pagelim.setToolTip("Decide from the documents: page-limited when a page limit is found. Or say so yourself.")
        f.addRow("Page-limited", self.pagelim)
        v.addWidget(D.label("The effort's own spots: anything the team wants on the banner (capture manager, contract vehicle, "
                            "value, place of performance).", "muted"))
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Spot", "Value"])
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 180); self.table.setMinimumHeight(160)
        for fl in ident["fields"]:
            self.add_row(fl["label"], fl["value"])
        v.addWidget(self.table)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Spot", None, lambda: self.add_row("", "")))
        row.addWidget(D.button("Remove", "ghost", lambda: self.table.removeRow(self.table.currentRow()) if self.table.currentRow() >= 0 else None))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def add_row(self, lab, val):
        i = self.table.rowCount(); self.table.insertRow(i)
        self.table.setItem(i, 0, QTableWidgetItem(lab)); self.table.setItem(i, 1, QTableWidgetItem(val))

    def values(self):
        fields = []
        for i in range(self.table.rowCount()):
            a, b = self.table.item(i, 0), self.table.item(i, 1)
            if a and a.text().strip():
                fields.append({"label": a.text(), "value": b.text() if b else ""})
        due = (self.due_date.date().toPython().isoformat() + "T" + self.due_time.time().toString("HH:mm")) if self.has_due.isChecked() else ""
        return {"pm": self.pm.currentText(), "client": self.client.text(), "solicitation": self.sol.text(), "zone_key": self.zone.currentData(),
                "due": due, "page_limited": self.pagelim.currentData() or "",
                "sensitivity": self.sens.currentText(), "fields": fields}


class MarkingStrip(QLabel):
    """The strip across every page for an effort marked CUI, Proprietary or the team's own marking."""

    def __init__(self):
        super().__init__("")
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)

    def show_marking(self, sens):
        m = BR.marking(sens)
        if not m:
            self.setVisible(False); self.setText("")
            return
        text, tn = m
        t = D.tokens()
        self.setText(text)
        self.setStyleSheet(f"background:{t.get(tn, t['warn'])};color:{t['accent_fg']};font-weight:700;letter-spacing:2px;"
                           f"padding:3px;font-size:{D.TYPE['small']}pt;")
        self.setToolTip("How this effort is marked (Effort Home > Edit details). Stationkeeper marks the screen; it does not "
                        "decide or certify what is CUI.")
        self.setVisible(True)


class RailBrand(QWidget):
    """The company logos at the top of the menu, on a light plate so any logo reads; a quiet prompt when none are set."""

    def __init__(self, host):
        super().__init__()
        self.host = host
        self.v = QVBoxLayout(self); self.v.setContentsMargins(D.SPACE["s"], D.SPACE["m"], D.SPACE["s"], D.SPACE["xs"]); self.v.setSpacing(0)
        self.plate = QFrame(); self.plate.setObjectName("logoPlate")
        self.row = QHBoxLayout(self.plate); self.row.setContentsMargins(10, 8, 10, 8); self.row.setSpacing(10)
        self.v.addWidget(self.plate)
        self.add = QToolButton(); self.add.setVisible(False)      # 3.0.3: no "Add your company logo": logos are built in
        self.refresh()

    def refresh(self):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        paths = BR.logos(self.host.config_dir)
        self.paths = paths
        self.plate.setStyleSheet("QFrame#logoPlate{background:#FFFFFF;border-radius:10px;}")
        self.plate.setVisible(bool(paths)); self.add.setVisible(False)
        if not paths:
            return
        w_each = max(40, (200 - 10 * (len(paths) - 1)) // len(paths))
        hgt = 44 if len(paths) == 1 else 34
        self.row.addStretch(1)
        for p in paths:
            pm = QPixmap(p)
            if pm.isNull():
                continue
            pm = pm.scaled(w_each, hgt, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lab = QLabel(); lab.setPixmap(pm); lab.setStyleSheet("background:transparent;")
            lab.setToolTip("Your company")
            self.row.addWidget(lab)
        self.row.addStretch(1)


class RailFooter(QWidget):
    """The Stationkeeper mark and name at the foot of the menu, with the version."""

    def __init__(self, version):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["s"], 0); h.setSpacing(D.SPACE["s"])
        mark = QLabel()
        p = asset("scanner_256.png")
        if os.path.isfile(p):
            mark.setPixmap(QPixmap(p).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        mark.setStyleSheet("background:transparent;")
        h.addWidget(mark, 0, Qt.AlignVCenter)
        col = QVBoxLayout(); col.setSpacing(0)
        self.word = QLabel("Stationkeeper"); self.word.setStyleSheet(f"color:#FFFFFF;font-weight:700;font-size:{D.TYPE['body'] + 1}pt;background:transparent;")
        self.sub = QLabel(f"{version}  ·  Offline, on this PC"); self.sub.setStyleSheet(f"color:#7F91AA;font-size:{D.TYPE['label']}pt;background:transparent;")
        col.addWidget(self.word); col.addWidget(self.sub)
        h.addLayout(col, 1)


class CustomizeDialog(QDialog):
    """Customize Home: a role's starting layout, then show, hide and order the sections. Kept for this person on this PC."""

    def __init__(self, parent, lay, names, me, team=None, config_dir=""):
        super().__init__(parent)
        self.team, self.config_dir = team or {}, config_dir
        self.setWindowTitle("Customize Home")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Your Effort Home on this PC. It is yours alone: it changes no one else's, and it is not saved in "
                            "the effort.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.role = QComboBox(); self.role.addItems(list(BR.ROLE_NAMES)); self.role.setCurrentText(lay["role"])
        self.role_says = D.label(BR.ROLE_SAYS.get(lay["role"], ""), "muted")
        self.role.activated.connect(lambda _i: self.use_role())
        self.me = QComboBox(); self.me.setEditable(True); self.me.addItems([""] + list(names)); self.me.setCurrentText(me)
        self.me.setToolTip("My work and the tasks filter use this name")
        f.addRow("My role", self.role); f.addRow("", self.role_says); f.addRow("I am", self.me)
        v.addWidget(D.label("Tick what shows; Up and Down set the order. Half-width sections sit side by side.", "muted"))
        self.list = QListWidget(); self.list.setDragDropMode(QAbstractItemView.InternalMove); self.list.setMinimumHeight(280)
        v.addWidget(self.list)
        self.fill(lay)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Up", None, lambda: self.move(-1))); row.addWidget(D.button("Down", None, lambda: self.move(1)))
        row.addStretch(1)
        row.addWidget(D.button("Reset to the role", "ghost", lambda: self.use_role()))
        import teampack as TP
        self.team_btn = D.button("Save as the team's layout for this role", "ghost", lambda: self.save_team(),
                                 "Kept on this PC; a team pack carries it to everyone (Settings > Team defaults)")
        self.team_btn.setEnabled(bool(config_dir) and not TP.locked(config_dir, "roles"))
        if config_dir and TP.locked(config_dir, "roles"):
            self.team_btn.setToolTip("The team pack set the role layouts")
        row.addWidget(self.team_btn)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def fill(self, lay):
        self.list.clear()
        for k in lay["order"]:
            it = QListWidgetItem(BR.TITLE[k] + ("" if BR.WIDTH[k] == "wide" else "  (half width)"))
            it.setData(Qt.UserRole, k)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked if k in lay["hidden"] else Qt.Checked)
            self.list.addItem(it)

    def use_role(self):
        r = self.role.currentText()
        self.role_says.setText(BR.ROLE_SAYS.get(r, "") + ("  (the team's layout)" if r in self.team else ""))
        self.fill(BR.preset(r, self.team))

    def save_team(self):
        """2.89.0: what is ticked, in this order, becomes the team's layout for the role on this PC."""
        import teampack as TP
        v = self.values()
        cur = TP.roles(self.config_dir)
        cur[v["role"]] = [k for k in v["order"] if k not in v["hidden"]]
        TP._write(os.path.join(self.config_dir, TP.FILES["roles"]), cur)
        self.team = cur
        diag.activity("qt_team_role_layout_saved")
        return cur

    def move(self, step):
        i = self.list.currentRow(); j = i + step
        if i < 0 or not 0 <= j < self.list.count():
            return
        it = self.list.takeItem(i); self.list.insertItem(j, it); self.list.setCurrentRow(j)

    def values(self):
        order, hidden = [], []
        for i in range(self.list.count()):
            it = self.list.item(i); k = it.data(Qt.UserRole); order.append(k)
            if it.checkState() != Qt.Checked:
                hidden.append(k)
        return {"role": self.role.currentText(), "order": order, "hidden": hidden, "me": self.me.currentText().strip()}


class BrandingCard(D.Card):
    """Settings > Branding: the company logos at the top of the menu (up to three, in order)."""

    def __init__(self, host):
        super().__init__("Branding", "The company logos at the top of the menu. 3.0.3: they are built into Stationkeeper, so "
                         "nobody changes them by accident; a new logo comes with a new version or the team pack.")
        self.host = host
        self.row = QHBoxLayout(); self.row.setSpacing(D.SPACE["m"]); self.body.addLayout(self.row)
        self.note = self.add(D.label("", "muted"))
        self.refresh()

    def refresh(self):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        paths = BR.logos(self.host.config_dir)
        t = D.tokens()
        for p in paths:
            box = QFrame(); box.setStyleSheet(f"QFrame{{background:#FFFFFF;border:1px solid {t['border']};border-radius:8px;}}")
            bv = QVBoxLayout(box); bv.setContentsMargins(8, 8, 8, 8)
            lab = QLabel(); lab.setPixmap(QPixmap(p).scaled(160, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lab.setAlignment(Qt.AlignCenter); lab.setStyleSheet("border:none;"); bv.addWidget(lab)
            self.row.addWidget(box)
        self.row.addStretch(1)
        import teampack as TP
        lk = TP.locks(self.host.config_dir).get("logos")
        self.locked = bool(lk)
        for b in self.findChildren(QPushButton):
            if b.text() in ("<", ">", "Remove", "Add logo..."):
                b.setEnabled(not lk)
        baked = bool(BR.baked_logos())
        self.note.setText("Built into this version of Stationkeeper." if baked else
                          f"Set by the team pack {lk}." if lk else
                          "Kept on this PC from an earlier version. A version with your company logo built in replaces them."
                          if paths else "No company logo in this version. It is built in by whoever builds Stationkeeper.")

    def changed(self):
        self.refresh()
        self.host.rail_brand.refresh()

    def add_logo(self, path=None):
        import teampack as TP
        if TP.locked(self.host.config_dir, "logos"):
            self.host.status("The team pack set the logos. They change when the team sends a new pack.")
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Company logo", "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return False
        try:
            BR.add_logo(self.host.config_dir, path)
        except ValueError as e:
            self.host.status(f"At most {BR.LOGO_MAX} logos: remove one first." if "most" in str(e) else "That file is not a picture.")
            return False
        except Exception:
            diag.swallowed()
            self.host.status("That picture could not be read. Try a PNG or JPG.")
            return False
        diag.activity("qt_logo_added")
        self.changed()
        return True

    def remove(self, p):
        if not getattr(self, "locked", False):
            BR.remove_logo(self.host.config_dir, p)
        self.changed()

    def move(self, p, step):
        if not getattr(self, "locked", False):
            BR.move_logo(self.host.config_dir, p, step)
        self.changed()
