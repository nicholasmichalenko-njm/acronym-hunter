"""Documents, cleaner (4.62.0; Nicholas 2026-11-23: "Even the right-side panel ... is not necessary. I don't even think
I'm looking at it ever"; an empty page "seems spread out ... it just needs to be cleaner"). Two things, applied each
time the list is filled:
- With no document in the effort the page is one thing: the sentence and the one button, Add documents.... The bar, the
  chips, Find and the count are not shown until there is something to list. Dropping files on the page still works.
- With documents, the panel on the right (what has been done to the selected document, its versions) is closed. A
  document's right-click has Details, which opens it for as long as it is wanted; everything the panel offers is on
  that same menu already.
Nothing is removed from the page's code: the panel is filled as before, so opening it shows the document picked."""


def _find_row(page):
    """The widgets on the row that holds Find: the chips, the box, the type filter."""
    out = [page.search]
    out += list(getattr(page, "side_btns", {}).values())
    if getattr(page, "type_f", None) is not None:
        out.append(page.type_f)
    return out


def apply(page, any_docs):
    """Called at the end of LibraryPage.fill. any_docs: the effort has at least one document."""
    if not getattr(page, "focus", True):             # the classic layout (SK_DOCS_CLASSIC) is left as it was
        return None
    for w in [page.bar, page.p_docs] + _find_row(page):
        w.setVisible(any_docs)
    page.side_area.setVisible(any_docs and bool(getattr(page, "details_open", False)))
    lbl = getattr(page, "folder_lbl", None)          # the effort's folder: above the list, or under the button when empty
    if lbl is not None:
        under = getattr(page, "empty_folder", None)
        if under is None or under.parentWidget() is not page.empty:
            from PySide6.QtCore import Qt
            from . import design as D
            under = page.empty_folder = D.label("", "muted"); under.setAlignment(Qt.AlignCenter); under.setWordWrap(True)
            under.setFixedWidth(560)
            under.linkActivated.connect(lambda _h: page.host.open_effort_folder())
            page.empty.layout().addWidget(under, 0, Qt.AlignCenter)
        under.setText(lbl.text())
        under.setMinimumHeight(under.heightForWidth(560) + 4)
        under.setVisible(not any_docs and bool(lbl.text())); lbl.setVisible(any_docs and bool(lbl.text()))
    return any_docs


def toggle_details(page, on=None):
    """Open or close the panel on the right. Returns whether it is open."""
    page.details_open = (not getattr(page, "details_open", False)) if on is None else bool(on)
    page.side_area.setVisible(page.details_open and page.lib is not None and bool(page.lib.all))
    return page.details_open


def menu_item(page, m):
    """Details, on a document's right-click: ticked while the panel is open."""
    a = m.addAction("Details", lambda: toggle_details(page))
    a.setCheckable(True); a.setChecked(bool(getattr(page, "details_open", False)))
    return a
