"""Help and support in Qt (2.81.0): the Settings card (Create a support file, Keyboard shortcuts, What's new), the
what's-new card after an update, the safe-start notice, and Ctrl+K, which finds pages, efforts, sentences and people
from anywhere."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QAbstractItemView)
import diag
import supportfile as SF
from . import design as D

SHORTCUTS = [("Anywhere", "Ctrl+K", "Find a page, an effort, a sentence or a person"),
             ("Anywhere", "Ctrl+F", "Find a sentence by its words or number"),
             ("Anywhere", "F1", "The Guide, open at the page you are on"),
             ("Review (on the page)", "R", "SOW (Work): the selected sentences go to the target section as requirements"),
             ("Review (on the page)", "C", "Context: support for the last requirement you clicked"),
             ("Review (on the page)", "G", "The customer's (counted, never answered)"),
             ("Review (on the page)", "L / E", "L (Instructions) / M (Evaluation): requirements with that designation"),
             ("Review (on the page)", "X or Delete", "Clear the decision"),
             ("Review (on the page)", "J / S", "Join the selected sentences / split one"),
             ("Review (on the page)", "Ctrl+Z", "Undo the last change"),
             ("Review (on the page)", "Ctrl+click", "Select several sentences"),
             ("Review (on the page)", "Escape", "Clear the selection, or stop drawing a box for missed text")]


def support_card(host):
    card = D.Card("Help and support", "Get help without sending any document content.",
                  actions=[D.button("Guide", "primary", lambda: __import__("skqt.guide", fromlist=["x"]).open_guide(host, "start")),
                           D.button("What's new", None, lambda: show_whats_new(host, last="2.75.0")),
                           D.button("Keyboard shortcuts", None, lambda: show_shortcuts(host)),
                           D.button("Create a support file...", None, lambda: make_support_file(host))])
    lab = card.add(D.label("The support file holds versions, the content-free logs and the checks, for whoever maintains "
                           "Stationkeeper. It holds no document text, terms, names, file names or folder paths. You save it "
                           "and decide who gets it.", "muted"))
    lab.setWordWrap(True)
    import secure
    if secure.ACTIVE:                                  # 2.97.0: SCIF-ready keeps no logs, so there is nothing to send
        for b in card.findChildren(type(D.button("x", None, None))):
            if b.text().startswith("Create a support file"):
                b.setVisible(False)
        lab.setText("SCIF-ready: Stationkeeper keeps no logs and makes no support files. Describe a problem to whoever "
                    "maintains Stationkeeper in words, without document content.")
    return card


def support_blocked():
    """2.97.0: why a support file cannot be made now ('' when it can)."""
    import secure
    if secure.ACTIVE:
        return "SCIF-ready: Stationkeeper makes no support files and keeps no logs."
    if not secure.feedback_ok():
        return "No support file while an effort marked above CUI is open. Close it first."
    return ""


def make_support_file(host, path=None):
    import app_gui
    import datetime
    why = support_blocked()
    if why:
        host.status(why)
        return None
    if path is None:
        name = f"Stationkeeper support {datetime.date.today().isoformat()}.zip"
        path, _ = QFileDialog.getSaveFileName(host, "Save the support file", os.path.join(os.path.expanduser("~"), name), "Zip (*.zip)")
        if not path:
            return None
    try:
        import updatepack as U
        from . import updates as UP
        pc = U.check_files(UP.app_dir())
    except Exception:
        diag.swallowed()
        pc = None
    try:
        from PySide6 import __version__ as qtv
    except Exception:
        qtv = ""
    res = SF.make(path, app_gui.APP_VERSION, app_gui.LOG_DIR, settings=app_gui.load_settings() or {}, program_check=pc,
                  health=getattr(host.safety, "issues", []) if hasattr(host, "safety") else [], data_why=getattr(app_gui, "DATA_WHY", ""),
                  qt_version=qtv)
    diag.activity("support_file_made", files=len(res["files"]))
    host.toast(f"Support file saved: {os.path.basename(path)}")
    return res


def show_shortcuts(host, run=True):
    d = QDialog(host); d.setWindowTitle("Keyboard shortcuts"); d.setMinimumSize(640, 460)
    v = QVBoxLayout(d)
    t = QTableWidget(len(SHORTCUTS), 3); t.setHorizontalHeaderLabels(["Where", "Keys", "What it does"])
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    for r, row in enumerate(SHORTCUTS):
        for c, val in enumerate(row):
            t.setItem(r, c, QTableWidgetItem(val))
    t.setColumnWidth(0, 160); t.setColumnWidth(1, 110); t.horizontalHeader().setStretchLastSection(True)
    v.addWidget(t)
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(d.reject); v.addWidget(bb)
    d.table = t
    if run:
        d.exec()
    return d


def show_whats_new(host, last=None, run=True):
    """The card after an update (last: the version before). Returns the dialog, or None when there is nothing new."""
    import app_gui
    notes = SF.whats_new(last, app_gui.APP_VERSION)
    if not notes:
        return None
    d = QDialog(host); d.setWindowTitle(f"What's new in Stationkeeper {app_gui.APP_VERSION}"); d.setMinimumWidth(560)
    v = QVBoxLayout(d)
    for ver, items in notes:
        v.addWidget(D.label(ver, "title"))
        for it in items:
            lab = D.label("•  " + it); lab.setWordWrap(True); v.addWidget(lab)
    bb = QDialogButtonBox(QDialogButtonBox.Ok); bb.accepted.connect(d.accept); v.addWidget(bb)
    d.notes = notes
    if run:
        d.exec()
    return d


def after_update(host, run=True):
    """At start: when the version changed since the last start, show what's new once."""
    import app_gui
    st = app_gui.load_settings() or {}
    last = st.get("last_version", "")
    st["last_version"] = app_gui.APP_VERSION
    app_gui.save_settings(st)
    if last and last != app_gui.APP_VERSION:
        return show_whats_new(host, last, run=run)
    return None


# ---------------------------------------------------------------- Ctrl+K
class Finder(QDialog):
    """Type to find a page, an effort, a sentence or a person; Enter goes there."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.setWindowTitle("Find"); self.setMinimumSize(680, 460)
        v = QVBoxLayout(self)
        self.box = QLineEdit(); self.box.setPlaceholderText("A page, an effort, a sentence's words or number, a person")
        v.addWidget(self.box)
        self.list = QListWidget(); v.addWidget(self.list, 1)
        v.addWidget(D.label("Enter opens it. Esc closes.", "muted"))
        self.box.textChanged.connect(self.fill)
        self.box.returnPressed.connect(self.go)
        self.list.itemActivated.connect(lambda _i: self.go())
        self.entries = self.collect()
        self.fill("")

    def collect(self):
        from .mainwin import TITLES
        h = self.host
        out = [("Page", t, sub, ("page", k)) for k, (t, sub) in TITLES.items()]
        out += [("Effort", n, "Open this effort", ("effort", n)) for n in h.efforts.names()
                if not (h.efforts.get(n) or {}).get("archived")]
        if h.review is not None:
            out += [("Sentence", f"{it['id']}  {it['text'][:90]}", (it.get("decision") or "Undecided") + (f" · {it['map']}" if it.get("map") else ""),
                     ("sentence", it["id"])) for it in h.review.M.items]
        try:
            out += [("Person", n, "Sentences assigned to them", ("person", n)) for n in h.people()]
        except Exception:
            diag.swallowed()
        return out

    def fill(self, text):
        q = (text or "").casefold().split()
        self.list.clear()
        shown = 0
        for kind, title, sub, act in self.entries:
            hay = f"{kind} {title} {sub}".casefold()
            if all(w in hay for w in q):
                it = QListWidgetItem(f"{kind:<9}{title}    {sub}"); it.setData(Qt.UserRole, act)
                self.list.addItem(it)
                shown += 1
                if shown >= 200:
                    break
        if self.list.count():
            self.list.setCurrentRow(0)

    def go(self, act=None):
        if act is None:
            it = self.list.currentItem()
            if it is None:
                return None
            act = it.data(Qt.UserRole)
        h = self.host
        kind, val = act
        if kind == "page":
            h.go(val)
        elif kind == "effort":
            h.open_effort(val)
        elif kind == "sentence":
            h.go("assign"); h.assign_page.select(val)
        elif kind == "person":
            h.go("assign")
            h.status(f"Sentences assigned to {val}: " + str(sum(1 for x in h.review.M.items if val in (x.get("owner") or "")))
                     if h.review is not None else f"{val}")
        diag.activity("finder_used")
        self.accept()
        return act


def open_finder(host, run=True):
    f = Finder(host)
    if run:
        f.exec()
    return f
