"""Programs in the window (4.50.0): what changes while a program is open, and the Programs view of All Efforts.

A program (programs.py) opens on its Overview, which shows the program's name, a Program pill, how many program
documents it holds, Add documents and (4.52.0) the doors a program has as a row: Acronyms and Check a document; nothing
of an effort's. The menu leaves out the effort's steps, the Calendar and Tasks (programs.OUT); the Working on box lists
the efforts, then the programs after a line. On All Efforts, the Programs view shows one card per program, + New program
(a name only), and one row for each effort of the type Program deliverables, which offers the move and waits: nothing
moves until the person says so. Every function that would ask takes the answer (tests). Rules only (No AI); nothing
leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QInputDialog, QMenu, QMessageBox, QVBoxLayout, QWidget

import diag
import programs as PG
from . import design as D

OFFER = "This effort's type is Program deliverables. All Efforts > Programs offers to make it a program."


def _who(w):
    return getattr(w, "my_name", None) or None


def is_open(w):
    """A program is open in window w."""
    return getattr(w, "ws", None) is not None and PG.is_program(w.efforts, getattr(w, "effort_name", ""))


def on_open(w, name):
    """The page a home opens on: the Overview for a program, Shred for an effort (as before). An effort of the type
    Program deliverables still offered the move says so once, in a toast."""
    if PG.is_program(w.efforts, name):
        return "overview"
    try:
        if name in PG.candidates(w.efforts):
            w.toast(OFFER)
    except Exception:  # noqa: BLE001  the effort opens whatever happens to the toast
        diag.swallowed()
    return "assign"


def hidden_head(w, head):
    """A menu entry a program never shows (its pages show no effort tabs or step title while a program is open)."""
    return head in PG.OUT and is_open(w)


def tabs_for(w, head, step, tabs):
    """The page tabs to show: none on a program's Overview, and none of an effort step's while a program is open."""
    if is_open(w) and (head == "home" or head in PG.OUT):
        return None
    return tabs


def hidden_page(w, page):
    """A page where-you-were does not go back to while a program is open: an effort step's page, or an Overview tab."""
    if not is_open(w):
        return False
    from .mainwin import HEAD_OF, RAIL_OF
    return RAIL_OF.get(page, HEAD_OF.get(page, page)) in PG.OUT or (HEAD_OF.get(page) == "home" and page != "overview")


def fill_box(box, registry, names):
    """The Working on box: the efforts (and Unfiled while it holds work from before) first, then a line, then the programs."""
    box.clear()
    progs = [n for n in names if PG.is_program(registry, n)]
    box.addItems([n for n in names if n not in progs])
    if progs:
        box.insertSeparator(box.count())
        box.addItems(progs)


class ProgramPanel(QWidget):
    """What the Overview shows while a program is open."""

    def __init__(self, host):
        super().__init__()
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        head = QHBoxLayout(); head.setSpacing(D.SPACE["m"]); v.addLayout(head)
        self.name = D.label("", "title", wrap=False); head.addWidget(self.name)
        self.pill = D.Pill("Program", "head"); head.addWidget(self.pill); head.addStretch(1)
        self.count = D.label("", "muted"); v.addWidget(self.count)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); v.addLayout(row)
        self.add_btn = D.button("Add documents", "primary", lambda: host.go("library"), "The program documents: add, read and keep their versions")
        row.addWidget(self.add_btn); row.addStretch(1)
        from .landing import DoorRow                             # 4.52.0: the doors a program has, as a row (decision 80)
        self.doors = DoorRow(host, "program"); v.addWidget(self.doors)
        v.addStretch(1)

    def refresh(self):
        h = self.host
        s = PG.summary(h.efforts, h.effort_name)
        self.name.setText(h.effort_name)
        self.count.setText(PG.count_text(s["documents"]))
        return s


# ------------------------------------------------------------------ All Efforts: the Programs view
class ProgramCard(QFrame):
    def __init__(self, page, s, current=False):
        super().__init__()
        self.page, self.s = page, s
        self.setObjectName("pcard"); self.setFixedWidth(330); self.setCursor(Qt.PointingHandCursor)
        t = D.tokens()
        self.setStyleSheet(f"QFrame#pcard{{background:{t['surface']};border:1px solid {t['accent'] if current else t['border']};"
                           f"border-radius:{D.RADIUS['card'] + 2}px;}} QFrame#pcard QLabel{{background:transparent;}}")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"]); v.setSpacing(6)
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        nm = D.label(s["name"], "title"); nm.setWordWrap(True); top.addWidget(nm, 1)
        top.addWidget(D.Pill("Program", "head"), 0, Qt.AlignTop)
        if s["missing"]:
            v.addWidget(D.Pill("Its folder is not on this PC", "crit"))
        else:
            v.addWidget(D.label(PG.count_text(s["documents"]), "muted"))
        self.more = None
        if s["was_effort"]:                                  # the right-click's action, also in sight
            self.more = D.button("More", "ghost", lambda: self.menu().exec(self.more.mapToGlobal(self.more.rect().bottomLeft())))
            row = QHBoxLayout(); row.addStretch(1); row.addWidget(self.more); v.addLayout(row)

    def menu(self):
        m = QMenu(self)
        host, name = self.page.host, self.s["name"]
        m.addAction("Open", lambda: open_program(host, name))
        if self.s["was_effort"]:
            m.addAction("Make it an effort again...", lambda: make_effort(host, name))
        return m

    def contextMenuEvent(self, e):
        self.menu().exec(e.globalPos())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and not self.s["missing"]:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda n=self.s["name"], h=self.page.host: open_program(h, n))
            e.accept()
            return
        super().mouseReleaseEvent(e)


def fill_view(page, current=""):
    """The Programs view's cards into page.flow; returns the names shown."""
    reg = page.host.efforts
    shown = []
    for n in PG.names(reg):
        c = ProgramCard(page, PG.summary(reg, n), current=(n == current))
        page.cards[n] = c
        page.flow.addWidget(c)
        shown.append(n)
    return shown


def offer_rows(page, lay, on=True):
    """One row per effort of the type Program deliverables still offered the move, into lay (cleared first). Returns
    the names offered."""
    while lay.count():
        it = lay.takeAt(0)
        if it.widget() is not None:
            it.widget().setParent(None)
    if not on:
        return []
    host = page.host
    names = PG.candidates(host.efforts)
    page.offer_btns = {}
    for n in names:
        f = QFrame(); f.setObjectName("offerRow")
        h = QHBoxLayout(f); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
        h.addWidget(D.label(f"{n} is an effort of the type Program deliverables.", None), 1)
        mk = D.button("Make it a program...", None, lambda _c=False, x=n: make_program(host, x))
        kp = D.button("Keep it as an effort", "ghost", lambda _c=False, x=n: keep(host, x))
        h.addWidget(mk); h.addWidget(kp)
        page.offer_btns[n] = (mk, kp)
        lay.addWidget(f)
    return names


def _refresh(host):
    host.fill_efforts()
    pg = getattr(host, "efforts_page", None)
    if pg is not None:
        pg.refresh()


def new_program(host, name=None):
    """+ New program: a name only (asked again, with the reason, until it can be used), then the program is made and
    opened. name (tests): the name typed. Returns the name, or None."""
    import app_gui
    if name is None:
        why, text = "", ""
        while True:
            text, ok = QInputDialog.getText(host, "New program", (why + "\n\n" if why else "") + "The program's name:", text=text)
            if not ok:
                return None
            why = PG.check_name(host.efforts, text)
            if not why:
                name = text
                break
    why = PG.check_name(host.efforts, name)
    if why:
        host.status(why)
        return None
    name = PG.create(host.efforts, app_gui.DATA_DIR, name)
    diag.activity("program_created")
    host.fill_efforts()
    open_program(host, name)
    host.toast(f"{name} is ready. Add its program documents in Documents.")
    return name


def open_program(host, name):
    if (host.ws is None or host.effort_name != name) and not host.open_effort(name):
        return False
    host.effort_box.setCurrentText(name)
    host.go("overview")
    return True


def _close_if_open(host, name):
    if host.ws is not None and host.effort_name == name:
        host.save_now()
        host.close_effort()


def make_program(host, name, answer=None):
    """Make it a program..., after a Yes. answer (tests): True or False instead of asking."""
    if answer is None:
        answer = QMessageBox.question(host, "Make it a program?", f"{name} moves from Efforts to Programs. Its files stay where they "
                                      "are and nothing in it is removed. A program shows no steps, calendar or tasks. You can make "
                                      "it an effort again from its card.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
    if not answer:
        return False
    _close_if_open(host, name)
    if not PG.make_program(host.efforts, name, _who(host)):
        return False
    diag.activity("program_made_from_effort")
    _refresh(host)
    host.toast(f"{name} is a program now.")
    return True


def keep(host, name):
    """Keep it as an effort: the answer is kept and the row leaves; the card's menu still offers the move."""
    ok = PG.keep_as_effort(host.efforts, name)
    diag.activity("program_offer_kept")
    _refresh(host)
    return ok


def make_effort(host, name, answer=None):
    """Make it an effort again..., after a Yes. answer (tests): True or False instead of asking."""
    if answer is None:
        answer = QMessageBox.question(host, "Make it an effort again?", f"{name} moves from Programs to Efforts. Its files stay where "
                                      "they are and nothing in it is removed. It shows the effort's steps again.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
    if not answer:
        return False
    _close_if_open(host, name)
    if not PG.make_effort(host.efforts, name, _who(host)):
        return False
    diag.activity("program_made_effort")
    _refresh(host)
    host.toast(f"{name} is an effort again.")
    return True
