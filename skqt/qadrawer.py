"""The Q&A log as a drawer (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 6; decisions 2026-11-10). One log of the
questions for the customer (custqa; the page that was Documents > Customer Q&A) opens from a Q&A button with its count
in the title bar of Shred, Matrix & Outline and Drafts, and slides in on the right beside the page. Asking a question on
a piece (Q, or Capture > Question) fills in the citation and opens the drawer on it. go("custqa") opens it too.

Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

import diag
from . import design as D

STEPS = ("assign", "matrix", "drafts")         # the steps whose title bar shows Q&A
WIDTH = 620
LABEL = "Q&&A"                                  # && shows one ampersand on a button


def label(n):
    return f"{LABEL} ({n})" if n else LABEL


class Drawer(QFrame):
    def __init__(self, w):
        super().__init__()
        self.w = w
        self.setObjectName("qaDrawer")
        t = D.tokens()
        self.setStyleSheet(f"QFrame#qaDrawer{{background:{t['surface']};border-left:1px solid {t['border_strong']};}}")
        self.setFixedWidth(WIDTH)
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"]); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.head = D.label("Questions for the customer", "title", wrap=False); top.addWidget(self.head, 1)
        self.close_btn = D.button("Close", "ghost", lambda: close(w), "Close the Q&A log (it keeps everything)")
        top.addWidget(self.close_btn)
        self.body = v
        self.hide()


def install(w):
    """Wrap the page stack so the drawer sits beside it; move the Q&A page into it; add the title bar's button."""
    cv = w.stack.parentWidget().layout()
    i = cv.indexOf(w.stack)
    cv.removeWidget(w.stack)
    body = QWidget(); h = QHBoxLayout(body); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
    h.addWidget(w.stack, 1)
    w.qa_drawer = Drawer(w); h.addWidget(w.qa_drawer)
    cv.insertWidget(i, body, 1)
    w.stack.removeWidget(w.custqa_page)
    w.qa_drawer.body.addWidget(w.custqa_page, 1)
    w.custqa_page.show()
    bh = w.undo_btn.parentWidget().layout()
    w.qa_btn = D.button(LABEL, None, lambda: toggle(w), "Questions for the customer: ask, track and answer them")
    w.qa_btn.setCheckable(True)
    bh.insertWidget(bh.indexOf(w.undo_btn), w.qa_btn)
    w.qa_btn.setVisible(False)


def count(w):
    """Questions not answered yet."""
    try:
        import custqa as Q
        import effortrec as R
        if w.ws is None:
            return 0
        return sum(1 for q in Q.items(R.Record(w.ws.root)) if q.get("status") != "Answered")
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return 0


def on_page(w, step, rail_of):
    """After a page opens: the button shows on Shred, Matrix & Outline and Drafts, with its count; elsewhere the drawer closes."""
    if not hasattr(w, "qa_btn"):
        return
    w._qa_step = step
    here = rail_of.get(step, step) in STEPS
    w.qa_btn.setVisible(here)
    if here:
        n = count(w)
        w.qa_btn.setText(label(n))
    elif w.qa_drawer.isVisible():
        close(w)


def open_(w, qid=None):
    if w.ws is None:
        return False
    w.custqa_page.refresh()
    w.qa_drawer.show(); w.qa_btn.setChecked(True); w.qa_btn.setText(label(count(w)))
    if qid:
        w.custqa_page.select_id(qid)
    diag.activity("qa_drawer_opened")
    return True


def close(w):
    w.qa_drawer.hide()
    if hasattr(w, "qa_btn"):
        w.qa_btn.setChecked(False)
        n = count(w)
        w.qa_btn.setText(label(n))
    return True


def toggle(w):
    return close(w) if w.qa_drawer.isVisible() else open_(w)


def go(w, from_rail):
    """go("custqa"): on a step that has the drawer, open it there; elsewhere open Shred with it."""
    cur = getattr(w, "_qa_step", "")
    if from_rail.get(cur, cur) not in STEPS:
        w.go("assign")
    return open_(w)
