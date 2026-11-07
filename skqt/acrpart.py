"""The term card's two menus (3.76.0): The picture says something else... and More.

The picture says something else: Part of a longer term..., Misread letters... (Fix a misread, this PC), Not text (not a
term in this effort; the reading goes to Training with the effort's samples). More: Plural of, A form of, Another way of
writing, Part of a longer term, the way back from each, Add to this PC's database, Remove from the list.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QInputDialog, QMenu
import acrparts as AP
import efftrain as ET
from . import acrextras as AX


def _show(page, m, run):
    if run:
        b = getattr(page, "more_btn", None)
        m.exec(b.mapToGlobal(b.rect().bottomLeft()) if b is not None else page.mapToGlobal(page.rect().center()))
    return m


def part_of(page, term, whole=None):
    """Part of a longer term...: the longer forms found around it, or a typed one."""
    s = page.session
    if whole is None:
        offers = AP.longer_forms(s.results, term)
        if offers:
            whole, ok = QInputDialog.getItem(page, "Part of a longer term", f"{term} is part of:", offers + ["Type another..."], 0, True)
            if ok and whole == "Type another...":
                whole, ok = QInputDialog.getText(page, "Part of a longer term", f"{term} is part of:")
        else:
            whole, ok = QInputDialog.getText(page, "Part of a longer term", f"{term} is part of (the whole term, as written):")
        if not ok:
            return False
    whole = " ".join(str(whole or "").split())
    ok = AP.set_part(s, term, whole)
    if ok:
        ET.add(s, "part", term, whole, (s.results.get(whole) or {}).get("locations", [])[:1])
        page.host.toast(f"{term} is part of {whole} where they sit together: {whole} takes the row.")
        page.fill()
        page.select(whole)
    return ok


def not_text(page, term):
    """The picture holds no text there: Not a term in this effort, and a sample for Training."""
    s = page.session
    ET.add(s, "not text", term, "", (s.results.get(term) or {}).get("locations", [])[:1])
    return page.set_status([term], "Not a term")


def misread(page, term, right=None):
    ok = AX.fix_misread(page, term, right)
    if ok:
        ET.add(page.session, "misread", term, right or "", (page.session.results.get(term) or {}).get("locations", [])[:1])
    return ok


def picture_menu(page, term, run=True):
    m = QMenu(page)
    m.addAction("Part of a longer term...").triggered.connect(lambda: part_of(page, term))
    m.addAction("Misread letters...").triggered.connect(lambda: misread(page, term))
    m.addAction("Not text").triggered.connect(lambda: not_text(page, term))
    return _show(page, m, run)


def more_menu(page, terms, run=True):
    s = page.session
    m = QMenu(page)
    if len(terms) == 1:
        t = terms[0]
        d = s.results.get(t) or {}
        if d.get("plural_of"):
            m.addAction("Not a plural").triggered.connect(lambda: page.not_plural(t))
        elif d.get("form_of"):
            m.addAction(f"Not a form of {d['form_of']}").triggered.connect(lambda: page.not_form(t))
        elif d.get("alt_of"):
            m.addAction(f"Not another way of writing {d['alt_of']}").triggered.connect(lambda: AX.unmake_alt(page, t))
        else:
            g = s.singular_guess(t)
            m.addAction(f"Plural of {g}" if g else "Plural of...").triggered.connect(lambda: page.plural(t, g or None))
            fg = s.form_guess(t)
            m.addAction(f"A form of {fg}" if fg else "A form of...").triggered.connect(lambda: page.form(t, fg or None))
            if s.effort is not None:
                m.addAction("Another way of writing...").triggered.connect(lambda: AX.make_alt(page, t))
        if t in (getattr(s, "parts", None) or {}):
            m.addAction(f"Not part of {s.parts[t]['whole']}").triggered.connect(lambda: (AP.clear_part(s, t), page.fill()))
        else:
            m.addAction("Part of a longer term...").triggered.connect(lambda: part_of(page, t))
        m.addSeparator()
    m.addAction("Add to this PC's database").triggered.connect(lambda: AX.add_to_db(page, terms))
    if s.effort is not None and any(t in s.effort.rows for t in terms):
        m.addAction("Remove from the list").triggered.connect(lambda: AX.remove_from_list(page, terms))
    return _show(page, m, run)
