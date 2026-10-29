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
                               QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)
import branding as BR
import diag
from . import design as D

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

    def show_path(self, path):
        t = D.tokens()
        if path and os.path.isfile(path):
            self.setIcon(rounded(path, PIC, PIC, 14)); self.setText("")
            self.setToolTip("The effort's picture. Click to change or remove it.")
            self.setStyleSheet("QToolButton{border:none;background:transparent;}")
        else:
            from PySide6.QtGui import QIcon
            self.setIcon(QIcon()); self.setText("+\nEffort image")
            self.setToolTip("Add a picture that stands for the effort: a mission patch, a logo or a cover image")
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
        self.stage = D.Pill("", "accent"); top.addWidget(self.stage, 0, Qt.AlignTop)
        self.sub = D.label("", "muted"); mid.addWidget(self.sub)
        self.grid = QGridLayout(); self.grid.setHorizontalSpacing(D.SPACE["xl"]); self.grid.setVerticalSpacing(4)
        mid.addLayout(self.grid)
        acts = QHBoxLayout(); acts.setSpacing(D.SPACE["s"]); mid.addLayout(acts)
        self.edit_btn = D.button("Edit details...", None, lambda: self.edit_dialog(), "Proposal manager, client, sensitivity and "
                                 "the effort's own spots. They travel with the effort.")
        acts.addWidget(self.edit_btn)
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
        self.due_iso = rec.data.get("due", "")
        import effortrec as R
        self.due.setText(("Due " + R.due_text(self.due_iso, rec.data.get("zone", ""))) if self.due_iso else "No due date set yet. Set it in Edit details.")
        self.tick()
        if self.due_iso and not self.timer.isActive():
            self.timer.start()
        elif not self.due_iso:
            self.timer.stop()

    def tick(self, now=None):
        c = BR.countdown(self.due_iso, now)
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
        self.sens = QComboBox(); self.sens.setEditable(True); self.sens.addItems(["", *BR.MARKINGS]); self.sens.setCurrentText(ident["sensitivity"])
        self.sens.setToolTip("CUI and Proprietary mark every page with a strip across the top. Type your own marking if the team uses another.")
        f.addRow("Proposal manager", self.pm); f.addRow("Client", self.client); f.addRow("Solicitation", self.sol)
        f.addRow("Sensitivity", self.sens)
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
        return {"pm": self.pm.currentText(), "client": self.client.text(), "solicitation": self.sol.text(),
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
        self.add = QToolButton(); self.add.setText("+ Add your company logo"); self.add.setObjectName("logoAdd")
        self.add.setCursor(Qt.PointingHandCursor); self.add.clicked.connect(lambda: host.go_branding())
        self.v.addWidget(self.add)
        self.refresh()

    def refresh(self):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        paths = BR.logos(self.host.config_dir)
        self.paths = paths
        self.plate.setStyleSheet("QFrame#logoPlate{background:#FFFFFF;border-radius:10px;}")
        self.add.setStyleSheet("QToolButton#logoAdd{color:#7F91AA;border:1px dashed #3A4B66;border-radius:8px;padding:8px;background:transparent;}"
                               "QToolButton#logoAdd:hover{color:#FFFFFF;border-color:#7F91AA;}")
        self.plate.setVisible(bool(paths)); self.add.setVisible(not paths)
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
            lab.setToolTip("Company logos: Settings > Branding")
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

    def __init__(self, parent, lay, names, me):
        super().__init__(parent)
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
        self.role_says.setText(BR.ROLE_SAYS.get(r, ""))
        self.fill(BR.preset(r))

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
        super().__init__("Branding", f"Your company logos at the top of the menu: up to {BR.LOGO_MAX} (a prime and its teammates), "
                         "in order. Kept on this PC for every effort; the team pack in a coming release shares them.",
                         actions=[D.button("Add logo...", "primary", lambda: self.add_logo())])
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
            br = QHBoxLayout(); bv.addLayout(br)
            for text, fn in (("<", lambda _=False, p=p: self.move(p, -1)), (">", lambda _=False, p=p: self.move(p, 1)),
                             ("Remove", lambda _=False, p=p: self.remove(p))):
                b = D.button(text, "ghost", fn); br.addWidget(b)
            self.row.addWidget(box)
        self.row.addStretch(1)
        self.note.setText("" if paths else "No logo yet. Add a PNG or JPG; a logo on a clear background looks best.")

    def changed(self):
        self.refresh()
        self.host.rail_brand.refresh()

    def add_logo(self, path=None):
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
        BR.remove_logo(self.host.config_dir, p); self.changed()

    def move(self, p, step):
        BR.move_logo(self.host.config_dir, p, step); self.changed()
