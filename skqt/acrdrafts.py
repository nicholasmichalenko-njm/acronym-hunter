"""In our drafts (3.92.0): one volume's Word draft against the effort's acronym list. The findings on the left (counts you
click: used before it is spelled out, spelled out again, not in the list), the fix on the right shown as it will be
tracked, Fix in the copy (Enter) or Leave it (X), and the volume's Acronyms table check. Every fix goes into a copy of the
draft as tracked changes (written again from the draft each time, so Undo is exact); the draft is never changed.
acrfix holds the rules. Rules only (No AI); nothing leaves the PC."""
import html, os

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QTextBrowser, QVBoxLayout

import acrfix as F
import acrpage as P
import diag
from . import design as D
from .commandbar import CommandBar

KIND = {"before": "Used before it is spelled out", "again": "Spelled out again", "unlisted": "Not in the list"}
COUNTS = ("To fix", "Used before it is spelled out", "Spelled out again", "Not in the list")


class DraftsCheck(QDialog):
    def __init__(self, page, path=None):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle("Acronyms: in our drafts")
        self.resize(1300, 820)
        self.path, self.report, self.taken, self.left, self.filter = None, None, [], [], "To fix"
        v = QVBoxLayout(self)
        top = QHBoxLayout(); v.addLayout(top)
        self.where = D.label("Pick a volume's draft to check it against the acronym list.", "muted"); top.addWidget(self.where, 1)
        self.bar = CommandBar(self)
        self.b_fix = self.bar.primary("Fix in the copy", lambda: self.take(), "This finding's fix, as tracked changes in the copy")
        self.bar.add("Leave it", lambda: self.leave())
        self.bar.add("Fix all of this kind", lambda: self.take_all())
        self.bar.add("Pick a draft...", lambda: self.pick())
        self.bar.more("Undo the last fix", lambda: self.undo())
        self.bar.more("Open the copy's folder", lambda: self.open_folder())
        top.addWidget(self.bar)
        crow = QHBoxLayout(); v.addLayout(crow)
        self.count_btns = {}
        for name in COUNTS:
            b = QPushButton(name); b.setCheckable(True); b.setObjectName("chip")
            b.clicked.connect(lambda _c=False, n=name: self.set_filter(n))
            crow.addWidget(b); self.count_btns[name] = b
        crow.addStretch(1)
        body = QHBoxLayout(); v.addLayout(body, 1)
        self.list = QListWidget(); self.list.setMinimumWidth(320); self.list.currentRowChanged.connect(lambda _r: self.show_card())
        body.addWidget(self.list, 1)
        self.card = QTextBrowser(); self.card.setOpenLinks(False)
        body.addWidget(self.card, 2)
        self.table_line = D.label("", "muted"); v.addWidget(self.table_line)
        self.copy_line = D.label("", "muted"); v.addWidget(self.copy_line)
        for seq, fn in ((Qt.Key_Return, self.take), (Qt.Key_Enter, self.take), ("X", self.leave)):
            sc = QShortcut(QKeySequence(seq), self); sc.activated.connect(fn)
        if path:
            self.load(path)

    # ------------------------------------------------------------ the draft
    def pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "A volume's draft", "", "Word (*.docx)")
        return self.load(path) if path else None

    def copy_path(self):
        stem, _ext = os.path.splitext(self.path)
        return f"{stem} (fixes).docx"

    def load(self, path):
        s = self.page.session
        from .acrlayout import list_entries
        try:
            self.report = F.check(path, list_entries(s) if s else [])
        except Exception:                                      # noqa: BLE001  not a Word file it can read
            diag.swallowed()
            self.host.status("That draft does not read as a Word file.")
            return None
        self.path, self.taken, self.left = path, [], []
        name = os.path.splitext(os.path.basename(path))[0]
        if s is not None and s.ws is not None:                 # each term's uses in this volume, for Where it goes
            use = dict(s.ws.get("acronym_volume_use", {}) or {})
            for t, n in self.report["use"].items():
                use.setdefault(t, {})[name] = n
            s.ws.set("acronym_volume_use", use)
            P.note(s.ws, f"{name} checked", to_fix=len([f for f in self.report["findings"] if f["kind"] != "unlisted"]))
        diag.activity("acronym_drafts_checked", items=len(self.report["findings"]))
        self.where.setText(f"{os.path.basename(path)}: checked against the list. Fixes go into "
                           f"{os.path.basename(self.copy_path())} as tracked changes; the draft is not changed.")
        tab = self.report["table"]
        self.table_line.setText("This volume's Acronyms table: " + (
            f"listed, not used: {', '.join(tab['listed_not_used']) or 'none'}; used, not listed: {', '.join(tab['used_not_listed']) or 'none'}."
            if tab["rows"] else "none found (a table whose first row says Acronym)."))
        self.fill()
        return self.report

    def open_folder(self):
        if self.path:
            import subprocess
            if os.name == "nt" and not os.environ.get("AH_TEST"):
                subprocess.Popen(["explorer", os.path.dirname(self.path)])
        return self.path

    # ------------------------------------------------------------ the list
    def open_findings(self):
        done = {id(f) for f in self.taken + self.left}
        return [f for f in (self.report or {}).get("findings", []) if id(f) not in done]

    def shown(self):
        out = []
        for f in self.open_findings():
            if self.filter == "To fix" and f["kind"] == "unlisted":
                continue
            if self.filter not in ("To fix",) and KIND[f["kind"]] != self.filter:
                continue
            out.append(f)
        return out

    def set_filter(self, name):
        self.filter = name
        self.fill()
        return name

    def fill(self):
        op = self.open_findings()
        n = {"To fix": sum(1 for f in op if f["kind"] != "unlisted")}
        for k, lab in KIND.items():
            n[lab] = sum(1 for f in op if f["kind"] == k)
        for name, b in self.count_btns.items():
            b.setText(f"{name} {n.get(name, 0)}"); b.setChecked(name == self.filter)
        self.rows = self.shown()
        self.list.blockSignals(True); self.list.clear()
        for f in self.rows:
            QListWidgetItem(f"{f['term']}   {KIND[f['kind']]} · paragraph {f['para']}", self.list)
        self.list.blockSignals(False)
        if self.rows:
            self.list.setCurrentRow(0)
        self.show_card()
        self.copy_line.setText(f"The copy so far: {len(self.taken)} fix(es), {len(self.left)} left as is."
                               + (f" {os.path.basename(self.copy_path())}" if self.taken else ""))

    def current(self):
        i = self.list.currentRow()
        return self.rows[i] if 0 <= i < len(getattr(self, "rows", [])) else None

    def show_card(self):
        f = self.current()
        if f is None:
            self.card.setHtml("<p style='color:gray'>Nothing to fix here.</p>" if self.report else "")
            return
        t, dfn = html.escape(f["term"]), html.escape(f["definition"])
        if f["kind"] == "before":
            fix = (f"<p>At its first use (paragraph {f['para']}): <span style='color:{D.tokens()['accent']};text-decoration:underline'>{dfn} (</span>"
                   f"{t}<span style='color:{D.tokens()['accent']};text-decoration:underline'>)</span></p>"
                   + ("<p>Where it is spelled out later: <span style='color:{D.tokens()['crit']};text-decoration:line-through'>"
                      f"{dfn} (</span>{t}<span style='color:{D.tokens()['crit']};text-decoration:line-through'>)</span></p>" if f["spelled"] else ""))
        elif f["kind"] == "again":
            fix = ("".join(f"<p>Paragraph {i + 1}: <span style='color:{D.tokens()['crit']};text-decoration:line-through'>{dfn} (</span>{t}"
                           f"<span style='color:{D.tokens()['crit']};text-decoration:line-through'>)</span></p>" for i, _a, _b in f["spelled"]))
        else:
            fix = "<p>Not in the effort's list. Add it on the Acronyms page (select its words there), or leave it.</p>"
        self.card.setHtml(f"<h2>{t}</h2><p><b>{KIND[f['kind']]}</b></p><p style='color:gray'>…{html.escape(f['where'])}…</p>"
                          f"<h3>The fix, in a copy</h3>{fix}<p style='color:gray'>Tracked changes: accept or reject them in Word.</p>")

    # ------------------------------------------------------------ fixes
    def write(self):
        if self.taken:
            F.fix(self.path, self.copy_path(), [f for f in self.taken])
        elif os.path.exists(self.copy_path()):
            os.remove(self.copy_path())
        return self.copy_path()

    def take(self, f=None):
        f = f or self.current()
        if f is None or f["kind"] == "unlisted":
            return None
        self.taken.append(f)
        try:
            self.write()
        except Exception as e:                                 # noqa: BLE001  the copy open in Word
            diag.swallowed()
            self.taken.pop()
            self.host.status(f"The copy was not written: {e}. Close it in Word if it is open.")
            return None
        self.fill()
        return f

    def take_all(self):
        f = self.current()
        if f is None:
            return 0
        same = [x for x in self.rows if x["kind"] == f["kind"] and x["kind"] != "unlisted"]
        self.taken += same
        self.write()
        self.fill()
        return len(same)

    def leave(self):
        f = self.current()
        if f is None:
            return None
        self.left.append(f)
        self.fill()
        return f

    def undo(self):
        if not self.taken:
            return None
        f = self.taken.pop()
        self.write()
        self.fill()
        return f


def open_drafts(page, path=None):
    dlg = DraftsCheck(page, path)
    page.drafts_window = dlg
    dlg.show()
    if path is None:
        dlg.pick()
    return dlg
