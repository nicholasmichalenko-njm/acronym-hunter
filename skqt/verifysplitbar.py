"""Verify's bar, for a heading on the same line as its text (3.92.1): Split the heading off (the suggestion, or the
words you type or select), It has no heading (puts the suggestion away), and Undo the split. verifysplit holds the
rules; the split is kept with Verify's decisions and the reader follows it."""
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QWidget

import diag
import verifyroles as VR
import verifysplit as SPL
from . import design as D


def row(page):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
    page.split_lbl = D.label("", None, wrap=False); h.addWidget(page.split_lbl, 1)
    page.b_split = D.button("Split the heading off", "primary", lambda: split(page),
                            "The heading at the start of this block becomes a heading; the rest stays text")
    page.b_nosplit = D.button("It has no heading", None, lambda: no_split(page))
    page.b_unsplit = D.button("Undo the split", None, lambda: unsplit(page))
    for b in (page.b_split, page.b_nosplit, page.b_unsplit):
        h.addWidget(b)
    w.setVisible(False)
    return w


def show(page, b):
    """The row for one selected text block: offered when it starts with a heading, or already split."""
    m = VR.by_id(page.menu_now())
    textual = b is not None and m.get(b["role"], {}).get("acts") in ("text", "bullet", None)
    split_now = (b or {}).get("split")
    sug = (b or {}).get("split_suggest", "")
    on = b is not None and (bool(split_now) or (textual and (bool(sug) or split_now is None)))
    page.split_row.setVisible(on)
    if not on:
        return False
    if split_now:
        page.split_lbl.setText(f"Heading: {split_now[:60]}")
    elif sug:
        page.split_lbl.setText(f"Heading on the same line: {sug[:60]}")
    else:
        page.split_lbl.setText("")
    page.b_split.setVisible(not split_now)
    page.b_nosplit.setVisible(bool(sug) and not split_now)
    page.b_unsplit.setVisible(bool(split_now))
    return True


def _block(page):
    return next((x for x in page.v if page.sel and x["key"] == page.sel[0]), None)


def split(page, head=None):
    b = _block(page)
    if b is None:
        return None
    if head is None:
        guess = b.get("split_suggest") or ""
        head, ok = QInputDialog.getText(page, "Split the heading off", "The heading, as it starts the block:", text=guess)
        if not ok:
            return None
    head = " ".join((head or "").split())
    if not head or not SPL.at(b.get("text", ""), head):
        page.host.status("The heading has to be the words the block starts with.")
        return None
    page.store().set_split(page.doc, b["key"], head)
    diag.activity("verify_heading_split")
    keep = list(page.sel)
    page.show_page(); page.select(keep)
    return head


def no_split(page):
    b = _block(page)
    if b is None:
        return None
    page.store().set_split(page.doc, b["key"], "")
    keep = list(page.sel)
    page.show_page(); page.select(keep)
    return ""


def unsplit(page):
    b = _block(page)
    if b is None:
        return None
    page.store().set_split(page.doc, b["key"], None)
    keep = list(page.sel)
    page.show_page(); page.select(keep)
    return True
