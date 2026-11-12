"""Compliance language in Shred (4.18.0; asked 2026-11-11 17:51): drag over any words of a piece, right-click, and say
they are compliance language: just here (kept on the piece), everywhere (they join the compliance words list, the
library every effort's outputs read), or not compliance language here (the list's mark taken off this piece). The piece
keeps its type and decision. The words come out in the compliance style in the Excel matrix, the Word outline, the
coverage report and the setup documents (cwords.docx_parts and xlsx_value read the piece's marks). The piece pane
shows the piece's words in that style, so the list's catch is visible while shredding. Rules only (No AI)."""
import diag


def add_actions(page, m, iid):
    """The right-click's Compliance language part, when words of this piece are dragged over (page.grab)."""
    g = getattr(page, "grab", None)
    it = page.R.item(iid) if page.R is not None else None
    if it is None:
        return
    if g and g.get("iid") == iid and g.get("text"):
        words = g["text"].strip(" .,;:")
        m.addSeparator()
        m.addSection(f'"{words[:40]}"  ·  Compliance language')
        m.addAction("Compliance language: just here", lambda: mark(page, it, words, "here"))
        m.addAction("Compliance language: everywhere (add it to the compliance words list)", lambda: mark(page, it, words, "everywhere"))
        m.addAction("Not compliance language here", lambda: mark(page, it, words, "not"))
    elif (it.get("cl") or {}):
        m.addSeparator()
        m.addAction("Clear this piece's compliance language marks", lambda: clear(page, it))


def mark(page, it, words, how):
    """how: "here", "everywhere" or "not". Returns True when marked."""
    import cwords as CW
    page.R.snap("compliance language")
    if how == "everywhere":
        added = CW.add_words([words], page.host.config_dir)
        CW.mark(it, words, True)
        msg = (f'"{words}" is in the compliance words list now: every outline, matrix and setup marks it.' if added
               else f'"{words}" was in the compliance words list already; marked here too.')
    else:
        CW.mark(it, words, how == "here")
        msg = f'"{words}" is compliance language in this piece.' if how == "here" else f'"{words}" is not compliance language in this piece.'
    page.M.log(it.get("id", ""), f"compliance language: {words} ({how})")
    page.M.pending = True
    page.host.changed()
    diag.activity("compliance_language_marked")
    page.host.status(msg)
    try:
        page.show_card(page.selected())
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return True


def clear(page, it):
    import cwords as CW
    page.R.snap("compliance language cleared")
    CW.clear(it)
    page.M.pending = True
    page.host.changed()
    try:
        page.show_card(page.selected())
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return True


def card_html(it, config_dir=None):
    """The piece's words for its card, compliance language in the user's style."""
    import cwords as CW
    try:
        return CW.html(it.get("text", ""), CW.load(config_dir), it)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        import html
        return html.escape(it.get("text", ""))
