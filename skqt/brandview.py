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
    return app_gui.asset_path(name) or ""          # 4.19.0: built, the assets are in _internal, not beside the exe


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
        self.stage_hex = ""
        self.gate_info = {}
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 46, 0); outer.setSpacing(0)   # 4.25.1: room for the fold button,
        # which sat over the due date in 4.24.0 (Nicholas's recording, 2026-11-12 20:25)
        # 3.12.0: the full banner, and the condensed line that keeps only the essentials on screen
        self.full = QWidget(); self.full.setObjectName("bannerFull"); outer.addWidget(self.full)
        h = QHBoxLayout(self.full); h.setContentsMargins(D.SPACE["l"], D.SPACE["l"], D.SPACE["l"], D.SPACE["m"]); h.setSpacing(D.SPACE["l"])
        self.pic = PictureBox(self); h.addWidget(self.pic, 0, Qt.AlignTop)
        mid = QVBoxLayout(); mid.setSpacing(6); h.addLayout(mid, 1)
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); mid.addLayout(top)
        self.name = QLabel(""); self.name.setObjectName("bannerName"); self.name.setWordWrap(True)
        top.addWidget(self.name, 1)
        self.sens = D.Pill("", "head"); top.addWidget(self.sens, 0, Qt.AlignTop)
        self.pagelim = D.Pill("", "head"); self.pagelim.setVisible(False)   # 3.12.0: page limits live in Submission requirements
        self.stage = QPushButton(""); self.stage.setObjectName("stagePill"); self.stage.setCursor(Qt.PointingHandCursor)
        self.stage.clicked.connect(lambda: self.page.show_gate_goals())
        top.addWidget(self.stage, 0, Qt.AlignTop)
        self.sub = D.label("", "muted"); mid.addWidget(self.sub)
        self.grid = QGridLayout(); self.grid.setHorizontalSpacing(D.SPACE["xl"]); self.grid.setVerticalSpacing(4)
        mid.addLayout(self.grid)
        acts = FlowLayout(None, D.SPACE["s"]); mid.addLayout(acts)
        self.edit_btn = D.button("Edit details...", None, lambda: self.edit_dialog(), "Proposal manager, client, sensitivity, the "
                                 "customer's due date and the effort's own spots. They travel with the effort.")
        acts.addWidget(self.edit_btn)
        self.edit_btn.setVisible(False)          # 3.75.0: Edit details, People, the overview and the folder are in the bar
        self.all_ov = self.edit_btn
        self.page_deliv = D.button("", "ghost", lambda: self.host.go("deliverables"), "The deliverables board")
        acts.addWidget(self.page_deliv)
        acts.addStretch(1)
        self.toggles = {}                                                       # 3.12.0: pinned strips and the condensed view
        tg = acts
        for key, text, tip in (("themes", "Win themes", "Show or hide the win themes under the header, on every stage"),
                               ("truth", "Wall of Truth", "Show or hide the approved facts, numbers and names under the header")):
            b = D.button(text, None, None, tip); b.setCheckable(True)
            b.toggled.connect(lambda on, k=key: self.page.set_strip(k, on))
            tg.addWidget(b); self.toggles[key] = b
        self.cond_btn = D.button("\u25B2", "ghost", lambda: self.set_condensed(True, animate=True), "Condense: keep only the "
                                 "essentials at the top")                 # 3.20.3: an arrow, and a smooth, slower fold
        self.cond_btn.setFixedWidth(36)
        tg.addWidget(self.cond_btn)
        self.cond_btn.setVisible(False)                  # 4.24.0: one fold button, in one place (fold_btn, top right)
        # the countdown
        right = QFrame(); right.setObjectName("countdown"); h.addWidget(right, 0, Qt.AlignTop)
        self.due_box = right
        rv = QVBoxLayout(right); rv.setContentsMargins(D.SPACE["l"], D.SPACE["m"] + 22, D.SPACE["l"], D.SPACE["m"]); rv.setSpacing(0)
        # 4.24.0 (Nicholas 17:00): the due date is set right here: click it (no trip through Edit details)
        right.setCursor(Qt.PointingHandCursor)
        right.setToolTip("Click to set the customer's due date and time")
        right.mouseReleaseEvent = lambda _e: self.due_dialog()
        self.due_head = QLabel("DUE IN"); self.due_head.setObjectName("cdHead"); rv.addWidget(self.due_head, 0, Qt.AlignRight)
        self.days = QLabel(""); self.days.setObjectName("cdDays"); rv.addWidget(self.days, 0, Qt.AlignRight)
        self.clock = QLabel(""); self.clock.setObjectName("cdClock"); rv.addWidget(self.clock, 0, Qt.AlignRight)
        self.due = QLabel(""); self.due.setObjectName("cdDue"); self.due.setWordWrap(True); self.due.setMaximumWidth(240)
        self.due.setAlignment(Qt.AlignRight); rv.addWidget(self.due, 0, Qt.AlignRight)
        self.right = right
        # 3.12.0: the condensed line: name, due in days, client, sensitivity, stage
        self.compact = QWidget(); self.compact.setObjectName("bannerCompact"); outer.addWidget(self.compact)
        ch = QHBoxLayout(self.compact); ch.setContentsMargins(D.SPACE["l"], D.SPACE["s"], D.SPACE["l"], D.SPACE["s"]); ch.setSpacing(D.SPACE["s"])
        self.c_name = QLabel(""); self.c_name.setObjectName("compactName"); ch.addWidget(self.c_name)
        self.c_stage = QPushButton(""); self.c_stage.setObjectName("stagePill"); self.c_stage.setCursor(Qt.PointingHandCursor)
        self.c_stage.clicked.connect(lambda: self.page.show_gate_goals())
        ch.addWidget(self.c_stage)
        self.c_sens = D.Pill("", "head"); ch.addWidget(self.c_sens)
        self.c_due = QLabel(""); self.c_due.setObjectName("compactDue"); ch.addWidget(self.c_due)
        self.c_client = D.label("", "muted", wrap=False); ch.addWidget(self.c_client, 1)
        self.c_toggles = {}
        for key, text in (("themes", "Win themes"), ("truth", "Wall of Truth")):
            b = D.button(text, "ghost", None); b.setCheckable(True)
            b.toggled.connect(lambda on, k=key: self.page.set_strip(k, on))
            ch.addWidget(b); self.c_toggles[key] = b
        self.exp_btn = D.button("\u25BC", "ghost", lambda: self.set_condensed(False, animate=True), "Expand: show the full header")
        self.exp_btn.setFixedWidth(36)
        ch.addWidget(self.exp_btn)
        self.exp_btn.setVisible(False)
        ch.addSpacing(40)                                # room for the one fold button
        # 4.24.0 (Nicholas 16:45): the button that folds and unfolds the header stays in one place, the top right corner
        # (it sat left of the middle when open and at the far right when folded)
        self.fold_btn = D.button("\u25B2", "ghost", lambda: self.set_condensed(not self.condensed, animate=True),
                                 "Fold or unfold the header")
        self.fold_btn.setParent(self); self.fold_btn.setFixedSize(34, 26); self.fold_btn.raise_()
        self.condensed = False
        self.compact.setVisible(False)
        self.timer = QTimer(self, interval=1000, timeout=self.tick)
        self.restyle()

    def set_condensed(self, on, save=True, animate=False):
        """3.12.0: the condensed header keeps the effort's name, days to the due date, client, sensitivity and stage.
        3.20.3: from the arrows it folds and unfolds smoothly (450 ms, eased) instead of jumping."""
        self.condensed = bool(on)
        if getattr(self, "fold_btn", None) is not None:
            self.fold_btn.setText("\u25BC" if self.condensed else "\u25B2")
            self.fold_btn.setToolTip("Unfold: show the full header" if self.condensed else "Fold: keep only the essentials at the top")
            self._place_fold()
        if animate and self.isVisible():
            self._fold(self.condensed)
        else:
            self.full.setMaximumHeight(16777215)
            self.full.setVisible(not self.condensed); self.compact.setVisible(self.condensed)
        if save:
            try:
                from .modes import save as _save
                _save(banner_condensed=self.condensed)
            except Exception:
                diag.swallowed()
            if self.condensed:
                diag.activity("qt_banner_condensed")
            else:
                diag.activity("qt_banner_expanded")
        return self.condensed

    def _place_fold(self):
        b = getattr(self, "fold_btn", None)
        if b is not None:
            b.move(max(0, self.width() - b.width() - 8), 6); b.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_fold()

    def due_dialog(self, answer=None):
        """4.24.0: the customer's due date and time, set from the header itself. answer (tests): an ISO date and time, or
        "" to clear it. Returns True when it was saved."""
        if self.host.ws is None:
            return False
        if answer is None:
            from PySide6.QtCore import QDate, QTime
            from PySide6.QtWidgets import QDateEdit, QTimeEdit
            import effortrec as _R
            due = self.due_iso or ""
            dd = _R.parse_date(due[:10]) if due else None
            d = QDialog(self); d.setWindowTitle("The customer's due date"); f = QFormLayout(d)
            date = QDateEdit(); date.setCalendarPopup(True); date.setDisplayFormat("MMM d, yyyy")
            date.setDate(QDate(dd.year, dd.month, dd.day) if dd else QDate.currentDate())
            time = QTimeEdit(); time.setDisplayFormat("h:mm AP")
            hm = due[11:16] if len(due) > 15 else "14:00"
            time.setTime(QTime(int(hm[:2]), int(hm[3:5])))
            row = QHBoxLayout(); row.addWidget(date); row.addWidget(time); row.addStretch(1)
            f.addRow("Due", row)
            f.addRow("", D.label("The official deadline, in the submission's time zone (Edit details sets the zone).", "muted"))
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            clear = bb.addButton("No due date yet", QDialogButtonBox.ResetRole)
            got = {"v": None}
            clear.clicked.connect(lambda: (got.update(v=""), d.accept()))
            bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
            if d.exec() != QDialog.Accepted:
                return False
            answer = got["v"] if got["v"] is not None else date.date().toPython().isoformat() + "T" + time.time().toString("HH:mm")
        return self.save_details({"due": answer})

    def _fold(self, condense):
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        old = getattr(self, "_fold_anim", None)
        if old is not None:
            old.stop()
        full_h = max(self.full.sizeHint().height(), self.full.height())
        if condense:
            a = QPropertyAnimation(self.full, b"maximumHeight", self)
            a.setStartValue(self.full.height()); a.setEndValue(0)

            def done():
                self.full.setVisible(False); self.full.setMaximumHeight(16777215); self.compact.setVisible(True)
        else:
            self.compact.setVisible(False)
            self.full.setMaximumHeight(0); self.full.setVisible(True)
            a = QPropertyAnimation(self.full, b"maximumHeight", self)
            a.setStartValue(0); a.setEndValue(full_h)

            def done():
                self.full.setMaximumHeight(16777215)
        a.setDuration(450); a.setEasingCurve(QEasingCurve.InOutCubic)
        a.finished.connect(done)
        self._fold_anim = a
        a.start()
        return a

    def show_toggle(self, key, on):
        for b in (self.toggles.get(key), self.c_toggles.get(key)):
            if b is not None and b.isChecked() != bool(on):
                b.blockSignals(True); b.setChecked(bool(on)); b.blockSignals(False)

    # ------------------------------------------------------------ look
    def restyle(self, tone_name="accent"):
        t = D.tokens()
        col = t.get(tone_name, t["accent"])
        stage = self.stage_hex or t["accent"]                                   # 3.12.0: the stage's color, gently
        self.setStyleSheet(
            f"QFrame#banner{{background:{t['surface']};border:1px solid {t['border']};border-top:4px solid {stage};"
            f"border-radius:{D.RADIUS['card'] + 4}px;}}"
            f"QFrame#banner QLabel{{background:transparent;}}"
            f"QWidget#bannerFull, QWidget#bannerCompact{{background:transparent;}}"
            f"QPushButton#stagePill{{background:{stage};color:#FFFFFF;border:none;border-radius:{D.RADIUS['chip']}px;"
            f"padding:3px 12px;font-weight:600;font-size:{D.TYPE['small']}pt;}}"
            f"QPushButton#stagePill:hover{{border:1px solid {t['text']};}}"
            f"QFrame#banner QPushButton:checked{{background:{t['accent_soft']};color:{t['accent']};border:1px solid {t['accent']};}}"
            f"QLabel#compactName{{font-size:14pt;font-weight:700;color:{t['text']};}}"
            f"QLabel#compactDue{{font-weight:700;color:{col};}}"
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
        # 3.15.0: Edit details is the one filled button while the proposal manager or the due date is still missing
        want = "primary" if not (self.ident.get("pm") and (rec.data.get("due") if hasattr(rec, "data") else True)) else None
        if self.edit_btn.property("kind") != want:
            self.edit_btn.setProperty("kind", want); self.edit_btn.style().unpolish(self.edit_btn); self.edit_btn.style().polish(self.edit_btn)
        self.pic.show_path(BR.picture_path(self.data_dir()))
        self.name.setText(h.effort_name)
        sens = self.ident["sensitivity"]
        self.sens.setText(sens or "Sensitivity not set"); self.sens.set_tone(BR.tone(sens))
        self.sens.setToolTip("How the effort is marked. CUI and Proprietary mark every page with a strip across the top.")
        import stagecolors as SC
        try:
            i = rec.index()
            cur = rec.stages[i]
            self.stage_hex = SC.color_of(cur, i)
        except Exception:
            diag.swallowed()
            self.stage_hex = ""
        gi = self.gate_info or {}
        label = stage + (f"  ·  {gi['gate']}" if gi.get("gate") else "") + \
            (f"  ·  {gi['open']} of {gi['total']} goals open" if gi.get("total") else "")
        import menufocus as MF                                                  # 3.61.0: stages, win themes, All overviews set aside
        from .modes import settings as _st
        aside = MF.hidden(_st())
        if "stages" in aside:
            self.stage_hex = ""
        self.all_ov.setVisible("alloverviews" not in aside)
        for k, key in (("themes", "winthemes"), ("truth", "truth")):
            for tg in (self.toggles, self.c_toggles):          # 3.71.0: the condensed line's copies too
                if k in tg:
                    tg[k].setVisible(key not in aside)
        for b in (self.stage, self.c_stage):
            b.setText(label); b.setVisible(bool(stage) and "stages" not in aside)
            b.setToolTip((gi.get("about") or "") + ("\n" if gi.get("about") else "") + "Click to see this stage's gate goals")
        self.restyle("accent" if getattr(self, "_tone", "head") == "head" else self._tone)
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
        self.c_name.setText(h.effort_name)
        self.c_sens.setText(sens or "Sensitivity not set"); self.c_sens.set_tone(BR.tone(sens))
        self.c_client.setText(self.client or "")
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
                             "No due date set yet. Click here to set it.")
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
        self.c_due.setText("No due date" if c is None else ("Due date passed" if c[0] == "passed" else
                                                              f"Due in {c[0]} day{'s' if c[0] != 1 else ''}"))
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
        self.client = QLineEdit(client); self.client.setPlaceholderText("Customer")
        self.sol = QLineEdit(solicitation); self.sol.setPlaceholderText("Opportunity Number (Client Issued)")
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
        f.addRow("Proposal manager", self.pm); f.addRow("Client", self.client); f.addRow("Opportunity Number (Client Issued)", self.sol)
        from PySide6.QtCore import QDate, QTime
        from PySide6.QtWidgets import QCheckBox, QDateEdit, QTimeEdit
        due = rec.data.get("due", "")
        dd = _R.parse_date(due[:10]) if due else None
        # 3.12.0: the customer's official due date, or "Not set yet"; no switch to find
        self.has_due = QCheckBox(); self.has_due.setChecked(dd is not None); self.has_due.setVisible(False)
        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True); self.due_date.setDisplayFormat("MMM d, yyyy")
        self.due_date.setMinimumDate(QDate(2000, 1, 1)); self.due_date.setSpecialValueText("Not set yet")
        self.due_date.setDate(QDate(dd.year, dd.month, dd.day) if dd else self.due_date.minimumDate())
        self.due_time = QTimeEdit(); self.due_time.setDisplayFormat("h:mm AP")
        hm = due[11:16] if len(due) > 15 else "14:00"
        self.due_time.setTime(QTime(int(hm[:2]), int(hm[3:5])))
        self.due_date.dateChanged.connect(lambda d: self.has_due.setChecked(d != self.due_date.minimumDate()))
        self.due_time.timeChanged.connect(lambda *_a: self.has_due.setChecked(True) if self.due_date.date() != self.due_date.minimumDate() else None)
        self.has_due.toggled.connect(lambda on: None if on or self.due_date.date() == self.due_date.minimumDate()
                                     else self.due_date.setDate(self.due_date.minimumDate()))
        clear_due = D.button("Clear", "ghost", lambda: self.due_date.setDate(self.due_date.minimumDate()), "No due date yet")
        drow = QHBoxLayout(); drow.addWidget(self.due_date); drow.addWidget(self.due_time); drow.addWidget(clear_due); drow.addStretch(1)
        f.addRow("Customer's due date", drow)
        f.addRow("", D.label("The official deadline the customer gave, in the submission's time zone. The countdown and "
                             "Schedule from due date use it.", "muted"))
        f.addRow("Submission time zone", self.zone)
        f.addRow("Sensitivity", self.sens)
        import formatreq as FR                                                  # 2.94.0
        self.pagelim = QComboBox()
        for k, t in FR.SETTINGS.items():
            self.pagelim.addItem(t, k)
        self.pagelim.setCurrentIndex(max(0, self.pagelim.findData(rec.data.get("page_limited", ""))))
        self.pagelim.setToolTip("Decide from the documents: page-limited when a page limit is found. Or say so yourself.")
        f.addRow("Page-limited", self.pagelim)
        extra = QWidget(); ev = QVBoxLayout(extra); ev.setContentsMargins(0, 0, 0, 0)       # 3.20.3: optional, folded away
        self.extra_btn = D.button("Extra details on the banner (optional)...", "ghost", lambda: extra.setVisible(not extra.isVisible()),
                                  "Lines of your own under the effort's name on the dashboard: capture manager, contract vehicle, "
                                  "value, place of performance")
        v.addWidget(self.extra_btn)
        ev.addWidget(D.label("Each line shows under the effort's name on the dashboard banner.", "muted"))
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Detail", "Shows as"])
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 180); self.table.setMinimumHeight(160)
        for fl in ident["fields"]:
            self.add_row(fl["label"], fl["value"])
        ev.addWidget(self.table)
        row = QHBoxLayout(); ev.addLayout(row)
        row.addWidget(D.button("+ Detail", None, lambda: self.add_row("", "")))
        row.addWidget(D.button("Remove", "ghost", lambda: self.table.removeRow(self.table.currentRow()) if self.table.currentRow() >= 0 else None))
        row.addStretch(1)
        v.addWidget(extra); extra.setVisible(bool(ident["fields"]))
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


class RailEffort(QFrame):
    """3.15.0: the open effort and its stage at the top of the menu, so you always know which effort the menu acts on.
    Click it for the Effort Dashboard. Hidden when no effort is open."""

    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("railEffort"); self.setCursor(Qt.PointingHandCursor)
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); v.setSpacing(2)
        self.cap = QLabel("Effort"); self.cap.setObjectName("railEffortCap")
        self.name = QLabel(""); self.name.setObjectName("railEffortName"); self.name.setWordWrap(True)
        self.stage = QLabel(""); self.stage.setObjectName("railEffortStage")
        v.addWidget(self.cap); v.addWidget(self.name); v.addWidget(self.stage, 0, Qt.AlignLeft)
        self.setToolTip("The open effort and its stage. Click for another effort, All Efforts, My Work or Quick tools.")
        self.setVisible(True)                                   # 3.96.0: the effort switcher, always there

    def set(self, name, stage="", color=""):
        self.effort = name or ""
        self.name.setText((name or "No effort open") + "  ▾")
        self.stage.setText(stage or "")
        self.stage.setVisible(bool(stage))
        c = QColor(color or "#5B9BEB")                      # rgba(): Qt reads an 8-digit hex as #AARRGGBB
        soft = f"rgba({c.red()},{c.green()},{c.blue()},0.30)"
        c = c.name()
        self.stage.setStyleSheet(f"QLabel#railEffortStage{{color:#FFFFFF;border:1px solid {c};background:{soft};"
                                 f"border-radius:9px;padding:1px 8px;font-size:{D.TYPE['small']}pt;font-weight:600;}}")
        self.setVisible(True)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:                         # 3.96.0: another effort, All Efforts, My Work, Quick tools
            from .frame import effort_menu
            effort_menu(self.host).exec(self.mapToGlobal(self.rect().bottomLeft()))
        super().mousePressEvent(e)


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
        self.setWindowTitle("Customize the Effort Dashboard")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Your Effort Dashboard on this PC. It is yours alone: it changes no one else's, and it is not saved in "
                            "the effort.", "muted"))
        f = QFormLayout(); v.addLayout(f)
        self.role = QComboBox(); self.role.addItems(list(BR.ROLE_NAMES)); self.role.setCurrentText(lay["role"])
        self.role_says = D.label(BR.ROLE_SAYS.get(lay["role"], ""), "muted")
        self.role.activated.connect(lambda _i: self.use_role())
        self.me = QComboBox(); self.me.setEditable(True); self.me.addItems([""] + list(names)); self.me.setCurrentText(me)
        self.me.setToolTip("My work and the tasks filter use this name")
        f.addRow("My role", self.role); f.addRow("", self.role_says); f.addRow("I am", self.me)
        v.addWidget(D.label("Tick what shows; drag, or Up and Down, to set the order. Half-width cards sit side by side; "
                            "Full or half width changes the card picked.", "muted"))
        self.list = QListWidget(); self.list.setDragDropMode(QAbstractItemView.InternalMove); self.list.setMinimumHeight(280)
        v.addWidget(self.list)
        self.fill(lay)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Up", None, lambda: self.move(-1))); row.addWidget(D.button("Down", None, lambda: self.move(1)))
        row.addWidget(D.button("Full or half width", None, lambda: self.toggle_width(), "The card picked: full width, or half width "
                               "beside another"))                                       # 3.12.0
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
        widths = lay.get("widths") or {}
        for k in lay["order"]:
            w = BR.width(k, widths)
            it = QListWidgetItem(BR.TITLE[k] + ("" if w == "wide" else "  (half width)"))
            it.setData(Qt.UserRole, k); it.setData(Qt.UserRole + 1, w)
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

    def toggle_width(self, row=None):
        it = self.list.item(self.list.currentRow() if row is None else row)
        if it is None:
            return None
        k = it.data(Qt.UserRole)
        w = "half" if it.data(Qt.UserRole + 1) == "wide" else "wide"
        it.setData(Qt.UserRole + 1, w)
        it.setText(BR.TITLE[k] + ("" if w == "wide" else "  (half width)"))
        return w

    def move(self, step):
        i = self.list.currentRow(); j = i + step
        if i < 0 or not 0 <= j < self.list.count():
            return
        it = self.list.takeItem(i); self.list.insertItem(j, it); self.list.setCurrentRow(j)

    def values(self):
        order, hidden, widths = [], [], {}
        for i in range(self.list.count()):
            it = self.list.item(i); k = it.data(Qt.UserRole); order.append(k)
            if it.data(Qt.UserRole + 1) and it.data(Qt.UserRole + 1) != BR.WIDTH[k]:
                widths[k] = it.data(Qt.UserRole + 1)
            if it.checkState() != Qt.Checked:
                hidden.append(k)
        return {"role": self.role.currentText(), "order": order, "hidden": hidden, "me": self.me.currentText().strip(), "widths": widths}
