"""The path strip on the Effort Dashboard (3.63.0): the request type, how and when it is submitted, Notes to sort, and
the effort's moves with a live count each. Every step opens its page; nothing is locked. effortpath holds the rules."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QPushButton, QVBoxLayout
import diag
import effortpath as EP
from . import design as D


class PathStrip(QFrame):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("pathStrip")
        t = D.tokens()
        D.themed(self, lambda t: f"QFrame#pathStrip{{background:{t['surface']};border:1px solid {t['border']};border-radius:{D.RADIUS['card']}px;}}"
                           f"QFrame#pathStrip QLabel{{background:transparent;}}")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["s"], D.SPACE["m"], D.SPACE["s"]); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.type = QComboBox(); self.type.addItems(EP.TYPE_NAMES)
        self.type.setToolTip("The kind of request sets which steps matter and their words, never the rules")
        self.type.activated.connect(lambda _i: self.set_type(self.type.currentText()))
        top.addWidget(self.type)
        self.sub = D.label("", None); self.sub.setMinimumWidth(80); top.addWidget(self.sub, 1)   # wraps: never widens the window
        self.inbox_btn = D.button("Notes to sort", "ghost", lambda: self.open_inbox())
        top.addWidget(self.inbox_btn)
        # 3.75.0: Steps... is in the Effort Dashboard's More
        self.row = QHBoxLayout(); self.row.setSpacing(D.SPACE["s"]); v.addLayout(self.row)
        self.note = D.label("", "muted"); v.addWidget(self.note)
        self.btns, self.now = {}, []
        self.compact = False

    def _ctx(self):
        h = self.host
        if h.ws is None:
            return None, None, 0, []
        try:
            from .custdocs import Ctx
            c = Ctx(h)
            return c.rec, c.lib, len(c.unadded()), c.reg.rows()
        except Exception:  # noqa: BLE001
            diag.swallowed()
            import effortrec as R
            return R.Record(h.ws.root), None, 0, []

    def refresh(self):
        rec, lib, unadded, rows = self._ctx()
        self.setVisible(rec is not None)
        if rec is None:
            return []
        M = self.host.review.M if self.host.review is not None else None
        p = EP.path_of(rec)
        self.type.setCurrentText(p["type"])
        self.sub.setText(EP.submission_line(rec, rows) or "How and when it is sent: not found in the customer documents yet")
        import quicknote as QN
        n = len(QN.inbox(rec))
        self.inbox_btn.setText(f"Notes to sort ({n})" if n else "Notes to sort")
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
        self.now = EP.steps(rec, lib, M, unadded)
        nxt = EP.next_step(self.now)
        t = D.tokens()
        for s in self.now:
            b = QPushButton(f"{s['label']}\n{s['count']}")
            b.setCursor(Qt.PointingHandCursor); b.setMinimumHeight(48); b.setMinimumWidth(60)
            from PySide6.QtWidgets import QSizePolicy
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            edge = t["ok"] if s["done"] and s["on"] else (t["accent"] if nxt is s else t["border"])
            b.setStyleSheet(f"QPushButton{{text-align:left;padding:6px 10px;border:1px solid {t['border']};border-left:4px solid {edge};"
                            f"border-radius:6px;background:{t['surface2'] if not s['on'] else t['surface']};color:{t['muted'] if not s['on'] else t['text']};}}")
            b.setToolTip(f"{s['what']}. {EP.STATE_WORDS[s['state']]} for {p['type']}." + ("" if s["on"] else " Switched off for this effort."))
            b.clicked.connect(lambda _=False, pg=s["page"]: self.host.go(pg))
            self.btns[s["key"]] = b
            self.row.addWidget(b, 1)
            b.setVisible(not self.compact)              # 3.96.0: the map above shows the steps
        self.note.setText(EP.TYPES[p["type"]]["note"] + ("" if self.compact else f"  Next: {nxt['label']}." if nxt else
                                                         "  Every step is done or not needed."))
        return self.now

    def set_type(self, t):
        rec, *_r = self._ctx()
        if rec is None:
            return False
        EP.set_type(rec, t)
        diag.activity("request_type_set")
        self.refresh()
        return True

    def steps_dialog(self, answer=None):
        """Steps...: on or off for this effort. answer (tests): {key: bool}."""
        rec, *_r = self._ctx()
        if rec is None:
            return None
        if answer is None:
            d = QDialog(self); d.setWindowTitle("Steps for this effort"); v = QVBoxLayout(d)
            v.addWidget(D.label("A step switched off shows as not needed. The request type sets the starting choice.", "muted"))
            boxes = {}
            for s in self.now or EP.steps(rec):
                cb = QCheckBox(s["label"]); cb.setChecked(s["on"]); v.addWidget(cb); boxes[s["key"]] = cb
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return None
            answer = {k: cb.isChecked() for k, cb in boxes.items()}
        for k, on in answer.items():
            EP.set_step(rec, k, on)
        self.refresh()
        return answer

    def open_inbox(self, run=True):
        from .quicknote import inbox_dialog
        d = inbox_dialog(self.host, run=run)
        self.refresh()
        return d
