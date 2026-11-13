"""The Guide (3.0.2): how to use every page, in the order of the menu.

F1 opens it at the page you are on; Help and support in Settings opens it at the start. Each topic says what the page
is for, when to use it, the steps with the real button names, and a few tips. Go to this page jumps there. 3.14.2: text
only; no pictures and no sample content."""
import html
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)
from . import design as D

# (key, group, title, what it is for, use it when, [steps], [tips]); key matches the menu's page key where there is one
from .guidetopics import TOPICS                   # 3.53.0
TOPIC = {t[0]: t for t in TOPICS}


def MUTED():
    from . import design as D           # 4.27.3: the colors in use, light or dark
    return D.tokens()["muted"]


def topic_html(key):
    t = TOPIC.get(key) or TOPIC["start"]
    k, group, title, what, when, steps, tips = t
    e = html.escape
    out = [f"<p style='color:{MUTED()};font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin:0'>{e(group)}</p>",
           f"<h1 style='margin:2px 0 8px 0;font-size:24px'>{e(title)}</h1>",
           f"<p style='font-size:15px;margin:0 0 10px 0'>{e(what)}</p>",
           f"<p style='margin:0 0 12px 0'><b>Use it when:</b> {e(when)}</p>"]
    if k == "keys":
        from .helpcenter import SHORTCUTS
        out.append("<table cellpadding='5' style='border-collapse:collapse'>")
        for where, key_, does in SHORTCUTS:
            out.append(f"<tr><td style='color:{MUTED()}'>{e(where)}</td><td><b>{e(key_)}</b></td><td>{e(does)}</td></tr>")
        out.append("</table>")
    if steps:
        out.append("<h3 style='margin:14px 0 6px 0'>Steps</h3><ol style='margin-top:0'>")
        out += [f"<li style='margin-bottom:6px'>{e(s)}</li>" for s in steps]
        out.append("</ol>")
    if tips:
        out.append("<h3 style='margin:14px 0 6px 0'>Tips</h3><ul style='margin-top:0'>")
        out += [f"<li style='margin-bottom:6px'>{e(s)}</li>" for s in tips]
        out.append("</ul>")
    return "".join(out)


class GuideWindow(QDialog):
    """Topics on the left (grouped as the menu, with search), the topic on the right, Go to this page."""
    def __init__(self, host, key="start"):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Stationkeeper Guide")
        self.resize(1180, 820)
        lay = QHBoxLayout(self)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search the Guide")
        self.search.textChanged.connect(self._filter)
        self.list = QListWidget(); self.list.setMinimumWidth(250)
        self.list.currentItemChanged.connect(lambda cur, _old: self.show_topic(cur.data(Qt.UserRole)) if cur and cur.data(Qt.UserRole) else None)
        lv.addWidget(self.search); lv.addWidget(self.list, 1)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(False); self.view.setOpenLinks(False)
        row = QHBoxLayout()
        self.prev = D.button("< Previous", None, lambda: self._step(-1))
        self.next = D.button("Next >", None, lambda: self._step(1))
        self.go_btn = D.button("Go to this page", "primary", self._go)
        row.addWidget(self.prev); row.addWidget(self.next); row.addStretch(1); row.addWidget(self.go_btn)
        rv.addWidget(self.view, 1); rv.addLayout(row)
        lay.addWidget(left); lay.addWidget(right, 1)
        self.key = ""
        self._fill()
        self.show_topic(key if key in TOPIC else "start")

    def _fill(self, words=""):
        self.list.blockSignals(True)
        self.list.clear()
        words = words.lower().split()
        group = None
        import menufocus as MF
        for t in TOPICS:
            if t[0] in MF.OFF:                       # 3.89.0: a page turned off has no topic in the Guide
                continue
            if words and not all(w in " ".join([t[2], t[3], t[4], *t[5], *t[6]]).lower() for w in words):
                continue
            if t[1] != group:
                group = t[1]
                h = QListWidgetItem(group.upper()); h.setFlags(Qt.NoItemFlags)
                f = h.font(); f.setPointSizeF(f.pointSizeF() * 0.85); f.setBold(True); h.setFont(f)
                self.list.addItem(h)
            it = QListWidgetItem("   " + t[2]); it.setData(Qt.UserRole, t[0])
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._select(self.key)

    def _filter(self, text):
        self._fill(text)
        keys = self.shown()
        if keys and self.key not in keys:
            self.show_topic(keys[0])

    def shown(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]

    def _select(self, key):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == key:
                self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
                return

    def show_topic(self, key):
        self.key = key
        self.view.setHtml(topic_html(key))
        self._select(key)
        pages = getattr(self.host, "pages", {}) or {}
        self.go_btn.setVisible(key in pages)
        order = [t[0] for t in TOPICS]
        i = order.index(key)
        self.prev.setEnabled(i > 0); self.next.setEnabled(i < len(order) - 1)

    def _step(self, d):
        order = [t[0] for t in TOPICS]
        self.show_topic(order[max(0, min(len(order) - 1, order.index(self.key) + d))])

    def _go(self):
        if self.key in getattr(self.host, "pages", {}):
            self.host.go(self.key)


def current_key(host):
    """The menu key of the page showing, so F1 opens its topic."""
    try:
        cur = host.stack.currentWidget()
        for k, pg in host.pages.items():
            if pg is cur:
                if k not in TOPIC:                     # 3.16.0: a tab's page opens its menu item's topic
                    from .mainwin import HEAD_OF
                    k = HEAD_OF.get(k, k)
                return k if k in TOPIC else "start"
    except Exception:
        pass
    return "start"


def open_guide(host, key=None):
    g = getattr(host, "_guide", None)
    if g is None:
        g = host._guide = GuideWindow(host, key or current_key(host))
    else:
        g.show_topic(key or current_key(host))
    g.show(); g.raise_(); g.activateWindow()
    return g
