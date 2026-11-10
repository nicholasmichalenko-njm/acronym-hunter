"""Shred's re-shred queue on the page (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 7). A button over the page says
"N to re-shred" while Documents > Changes has passages queued (reshred.Queue). It opens the next one: the requirement
built from it is selected on the page, and the line under the bar gives the old and the new wording, with Done to take
it off the queue (and the Changed by flag off the requirement). Rules only (No AI); nothing leaves the PC."""
import html

from PySide6.QtCore import Qt

import diag
import reshred as RS
from . import design as D


def install(page, bar):
    page.reshred_btn = D.button("", "danger", lambda: open_next(page), "Passages a new version changed, queued in Documents > "
                                "Changes to shred again: each opens with its old and new wording")
    page.reshred_btn.setVisible(False)
    bar.addWidget(page.reshred_btn)
    page.reshred_cur = None
    page.note.linkActivated.connect(lambda h: done(page) if h == "reshred-done" else None)


def _queue(page):
    ws = page.host.ws
    return RS.Queue(ws.root).load() if ws is not None else None


def refresh(page):
    if not hasattr(page, "reshred_btn"):
        return 0
    q = _queue(page)
    n = len(q.open_items()) if q is not None else 0
    page.reshred_btn.setText(f"{n} to re-shred")
    page.reshred_btn.setVisible(bool(n) and page.R is not None)
    return n


def open_next(page):
    """The next queued passage: its requirement selected, its old and new wording under the bar. Returns the entry."""
    q = _queue(page)
    items = q.open_items() if q is not None else []
    if not items:
        refresh(page)
        return None
    e = items[0]
    page.reshred_cur = e["id"]
    if e.get("target") and page.R is not None and page.R.item(e["target"]) is not None:
        try:
            page.select(e["target"])
        except Exception:  # noqa: BLE001
            diag.swallowed()
    t = D.tokens()
    old = f"<span style='color:{t['crit']};text-decoration:line-through'>{html.escape(e['old'])}</span>" if e.get("old") else ""
    new = f"<b style='color:{t['ok']}'>{html.escape(e['new'])}</b>" if e.get("new") else "<i>(removed)</i>"
    who = f" Changed by {html.escape(e['label'])}" + (f": {html.escape(e['target'])}" if e.get("target") else "") + "."
    page.note.setTextFormat(Qt.RichText)
    page.note.setText(f"<b>Re-shred</b> {html.escape(e['doc'])}, {html.escape(e['label'])}.{who} Was: {old or '(new)'} "
                      f"Now: {new} &nbsp;<a href='reshred-done'>Done: take it off the queue</a>")
    diag.activity("reshred_opened")
    return e


def done(page, qid=None):
    qid = qid or page.reshred_cur
    q = _queue(page)
    e = q.done(qid) if q is not None and qid else None
    page.reshred_cur = None
    page.note.setText("")
    n = refresh(page)
    if e is not None:
        page.host.status(f"Re-shredded: {e['doc']} {e['label']}." + (f" {n} left to re-shred." if n else ""))
    return e
