"""Home (2.91.0): every effort in progress at a glance, the way in to a new one, and Unfiled work.

One card per effort (picture, name, client, sensitivity, stage, days to the due date, open tasks and questions,
deliverables with no owner, who has it open), the soonest due first; click a card to open the effort. + Add an Effort
is the main way to start one (its folders are made with it). Unfiled work has its own card while it holds anything:
Open it, Make it an effort, or Add to an effort. The rules are effortsummary's and unfiled's. Rules only (No AI);
nothing leaves the PC."""
import datetime, getpass, os, platform
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QProgressBar, QScrollArea, QVBoxLayout, QWidget)
import diag
import effortsummary as ES
import unfiled as UF
from . import design as D
from .adaptive import FlowLayout


class EffortCard(QFrame):
    def __init__(self, page, s, current=False):
        super().__init__()
        self.page, self.s = page, s
        self.setObjectName("ecard"); self.setFixedWidth(330); self.setCursor(Qt.PointingHandCursor)
        t = D.tokens()
        self.setStyleSheet(f"QFrame#ecard{{background:{t['surface']};border:1px solid {t['accent'] if current else t['border']};"
                           f"border-radius:{D.RADIUS['card'] + 2}px;}} QFrame#ecard QLabel{{background:transparent;}}")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"]); v.setSpacing(6)
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        pic = QLabel(); pic.setFixedSize(56, 56)
        if s["picture"]:
            from .brandview import rounded
            pic.setPixmap(rounded(s["picture"], 56, 56, 10))
        else:
            pic.setText(s["name"][:1].upper()); pic.setAlignment(Qt.AlignCenter)
            pic.setStyleSheet(f"background:{t['accent_soft']};color:{t['accent']};border-radius:10px;font-size:20pt;font-weight:700;")
        top.addWidget(pic)
        col = QVBoxLayout(); col.setSpacing(0); top.addLayout(col, 1)
        nm = D.label(s["name"], "title"); nm.setWordWrap(True); col.addWidget(nm)
        col.addWidget(D.label("  ·  ".join(x for x in (s["client"], s["solicitation"]) if x) or "Client not set", "muted"))
        pills = QHBoxLayout(); pills.setSpacing(6); v.addLayout(pills)
        if s["missing"]:
            pills.addWidget(D.Pill("Its folder is not on this PC", "crit"))
        else:
            pills.addWidget(D.Pill(ES.days_text(s["days"]), ES.days_tone(s["days"])))
            if s["sensitivity"]:
                import branding as BR
                pills.addWidget(D.Pill(s["sensitivity"], BR.tone(s["sensitivity"])))
            if current:
                pills.addWidget(D.Pill("Open now", "ok"))
            elif s["open_by"]:
                pills.addWidget(D.Pill("Open elsewhere", "warn"))
        pills.addStretch(1)
        if not s["missing"]:
            if s["stages"]:
                bar = QProgressBar(); bar.setRange(0, max(1, s["stages"] - 1)); bar.setValue(s["stage_i"]); bar.setTextVisible(False)
                bar.setMaximumHeight(6)
                bar.setStyleSheet(f"QProgressBar{{background:{t['surface2']};border:none;border-radius:3px}} QProgressBar::chunk{{background:{t['accent']};border-radius:3px}}")
                v.addWidget(bar)
                v.addWidget(D.label(f"Stage: <b>{s['stage']}</b>" + (f"  ·  PM {s['pm']}" if s["pm"] else ""), None))
            bits = [f"{s['tasks']} open task(s)" + (f", {s['late']} late" if s["late"] else ""), f"{s['questions']} open question(s)"]
            if s["deliverables"]:
                bits.append(f"{s['deliverables']} deliverable(s)" + (f", {s['no_owner']} with no owner" if s["no_owner"] else ""))
            lab = D.label("  ·  ".join(bits), "muted"); v.addWidget(lab)
            if s["open_by"] and not current:
                v.addWidget(D.label(f"Open by {s['open_by']}", "warn"))
            if s["last"]:
                v.addWidget(D.label("Last worked on " + s["last"][:10], "muted"))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and not self.s["missing"]:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda n=self.s["name"], p=self.page: p.open(n))
            e.accept()
            return
        super().mouseReleaseEvent(e)


class FileDialog(QDialog):
    """Add Unfiled work to an effort: which effort, which documents, and the terms."""

    def __init__(self, parent, names, docs):
        super().__init__(parent)
        self.setWindowTitle("Add Unfiled work to an effort"); self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.target = QComboBox(); self.target.addItems(names); f.addRow("Effort", self.target)
        v.addWidget(D.label("Documents (every version goes, with its role, tags and text):", "muted"))
        self.list = QListWidget()
        for did, name, cat, nv in docs:
            it = QListWidgetItem(f"{name}  ({nv} version{'s' if nv != 1 else ''})"); it.setData(Qt.UserRole, did)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked); self.list.addItem(it)
        v.addWidget(self.list)
        self.terms = QCheckBox("Add Unfiled's acronyms to that effort's effort list (none of its own are replaced)")
        self.terms.setChecked(True); v.addWidget(self.terms)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel); bb.addButton("Add to the effort", QDialogButtonBox.AcceptRole)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)

    def values(self):
        ids = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]
        return {"target": self.target.currentText(), "docs": ids, "terms": self.terms.isChecked()}


class EffortsHome(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); outer.setSpacing(D.SPACE["m"])
        top = FlowLayout(None, D.SPACE["s"]); outer.addLayout(top)
        self.add_btn = D.button("+ Add an Effort", "primary", lambda: self.add_effort(), "A new effort, with its own folder")
        self.add_btn.setMinimumHeight(36)
        top.addWidget(self.add_btn)
        top.addWidget(D.button("Import effort package...", None, lambda: self.host.import_package()))
        top.addStretch()
        self.count = D.label("", "muted", wrap=False); top.addWidget(self.count)
        # Unfiled work
        self.uf_card = D.Card("Unfiled work", "Documents and results not in an effort yet. File them when you know where they belong.")
        self.uf_text = self.uf_card.add(D.label("", None))
        ur = FlowLayout(None, D.SPACE["s"]); self.uf_card.body.addLayout(ur)
        ur.addWidget(D.button("Open Unfiled", None, lambda: self.open_unfiled()))
        self.mk_btn = D.button("Make it an effort...", "primary", lambda: self.host.make_unfiled_effort())
        self.add_to_btn = D.button("Add to an effort...", None, lambda: self.add_unfiled_to())
        ur.addWidget(self.mk_btn); ur.addWidget(self.add_to_btn)
        ur.addStretch()
        ur.addWidget(D.button("Clear Unfiled...", "ghost", lambda: self.clear_unfiled(), "Empty it (a copy is kept)"))
        outer.addWidget(self.uf_card)
        self.start_row = QHBoxLayout(); outer.addLayout(self.start_row)
        self.start_btn = D.button("Start without an effort: open Unfiled", "ghost", lambda: self.open_unfiled(),
                                  "Use any tool now; file the work into an effort later")
        self.start_row.addWidget(self.start_btn); self.start_row.addStretch(1)
        # the efforts
        self.grid_box = QWidget(); self.flow = FlowLayout(self.grid_box, D.SPACE["m"])
        outer.addWidget(self.grid_box)
        self.empty = D.EmptyState("No efforts yet", "+ Add an Effort starts one: its own folder with Customer Documents, Volumes, "
                                  "Response Setup and Exports. Or start without one: Unfiled works with every tool.")
        outer.addWidget(self.empty)
        outer.addStretch(1)
        self.cards = {}

    def refresh(self):
        h = self.host
        reg = h.efforts
        rows = ES.all_efforts(reg)
        self.rows = rows
        while self.flow.count():
            it = self.flow.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        self.cards = {}
        for s in rows:
            c = EffortCard(self, s, current=(s["name"] == h.effort_name))
            self.cards[s["name"]] = c
            self.flow.addWidget(c)
        self.empty.setVisible(not rows)
        self.count.setText(f"{len(rows)} effort(s)" if rows else "")
        c = UF.counts(reg)
        self.uf_counts = c
        has = not UF.empty(c)
        self.uf_card.setVisible(has)
        self.start_btn.setVisible(not has and not UF.is_unfiled(reg, h.effort_name))
        self.uf_text.setText("Holds " + UF.summary_text(c) + "." if has else "")
        self.add_to_btn.setEnabled(bool(rows))

    def open(self, name):
        h = self.host
        if h.effort_name != name and not h.open_effort(name):
            return False
        h.effort_box.setCurrentText(name)
        h.go("home")
        return True

    def add_effort(self, values=None):
        """The main way to start an effort (Settings keeps a link to the same)."""
        name = self.host.settings_page.new_effort(values)
        if name:
            self.host.go("home")
        return name

    def open_unfiled(self):
        import app_gui
        h = self.host
        UF.ensure(h.efforts, app_gui.DATA_DIR)
        h.fill_efforts()
        if h.effort_name != UF.NAME:
            h.open_effort(UF.NAME)
        h.effort_box.setCurrentText(UF.NAME)
        h.go("library")
        return True

    def clear_unfiled(self, confirm=None):
        from .unfiledview import clear_unfiled
        ok = clear_unfiled(self.host, confirm)
        self.refresh()
        return ok

    def add_unfiled_to(self, answer=None):
        h = self.host
        names = [r["name"] for r in self.rows if not r["missing"]]
        if not names:
            return None
        if answer is None:
            dlg = FileDialog(self, names, UF.documents(h.efforts))
            if dlg.exec() != QDialog.Accepted:
                return None
            answer = dlg.values()
        target = answer["target"]
        if (h.efforts.get(target) or {}).get("path") and h.effort_name == target:
            h.save_now()
        was = h.effort_name
        if was == UF.NAME:
            h.save_now()
        n = UF.add_to(h.efforts, target, answer.get("docs", []), answer.get("terms", True))
        diag.activity("qt_unfiled_added", n=n["documents"] + n["terms"])
        if was == target:
            h.open_effort(target)
        h.toast(f"Added to {target}: {n['documents']} document(s), {n['terms']} term(s). Unfiled keeps its copies until you clear it (Home).")
        self.refresh()
        return n
