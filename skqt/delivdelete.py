"""Delete a deliverable (4.12.0; claude/stationkeeper-capture-cards-plan-4.12.md, B1): Delete this deliverable... on its own
page, on a board card's right-click and in the List view. A confirmation names it and what goes with it, with Cancel
the default; after a delete, Undo (the top bar's, or Ctrl+Z on the Deliverables page) puts it back whole. The effort
record keeps the removed deliverable (deliverables_removed); its timeline says who removed it."""
from PySide6.QtWidgets import QMenu, QMessageBox

import deliverables as DL
import diag


def install(page):
    """The page's Undo (the top bar and Ctrl+Z ask the page first) and the board cards' right-click."""
    page.removed_now = []                      # this session's deletes, newest last
    page.undo_text = lambda: undo_text(page)
    page.undo_here = lambda: undo(page)
    page.card_menu = lambda did, pos: card_menu(page, did, pos)


def question(page, d):
    bits = DL.what_goes(d)
    goes = (" It goes with " + ", ".join(bits) + ".") if bits else ""
    return (f"Delete {d['name']}?{goes}\n\nUndo (Ctrl+Z on the Deliverables page) puts it back, with everything it held, "
            "until you close Stationkeeper.")


def delete(page, did, answer=None):
    """Ask, then delete. answer (tests): True deletes, False cancels. Returns True when deleted."""
    if page.ctx is None or not did:
        return False
    d = DL.get(page.ctx.rec, did)
    if d is None:
        return False
    if answer is None:
        box = QMessageBox(QMessageBox.Warning, "Delete this deliverable", question(page, d), parent=page)
        yes = box.addButton("Delete", QMessageBox.DestructiveRole)
        no = box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(no); box.setEscapeButton(no)
        box.exec()
        answer = box.clickedButton() is yes
    if not answer:
        return False
    if not DL.remove(page.ctx.rec, did):
        return False
    page.removed_now.append(did)
    diag.activity("deliverable_deleted")
    if page.stack.currentWidget() is page.one:
        page.close_deliverable()
    else:
        page.refresh()
    page.host.toast(f"Deleted {d['name']}. Undo (Ctrl+Z) puts it back.")
    _undo_btn(page)
    return True


def undo_text(page):
    if not page.removed_now or page.ctx is None:
        return ""
    gone = {d["id"]: d for d in DL.removed(page.ctx.rec)}
    did = page.removed_now[-1]
    return f"Delete {gone[did]['name']}" if did in gone else ""


def undo(page):
    """Put back the last deliverable deleted in this session. Returns what was undone, or None."""
    label = undo_text(page)
    if not label:
        page.host.status("Nothing to undo on this page.")
        return None
    did = page.removed_now.pop()
    if not DL.restore(page.ctx.rec, did):
        return None
    diag.activity("deliverable_put_back")
    page.refresh()
    page.host.status(f"Undone: {label}")
    return label


def _undo_btn(page):
    try:
        page.host.refresh_undo()
    except Exception:
        diag.swallowed()


def card_menu(page, did, pos, run=True):
    """A board card's right-click: Open and Delete this deliverable..."""
    m = QMenu(page)
    m.addAction("Open", lambda: page.open_deliverable(did))
    m.addSeparator()
    m.addAction("Delete this deliverable...", lambda: delete(page, did))
    if run:
        m.exec(pos)
    return m
