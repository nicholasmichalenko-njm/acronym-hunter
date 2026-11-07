"""The term card's two menus (3.76.0): The picture says something else... and More. 3.80.0: a box drawn in the
preview gives each fix its crop and corrected text, and a term the scan missed is added from the box (missed).

The picture says something else: Part of a longer term..., Misread letters... (Fix a misread, this PC), Not text (not a
term in this effort; the reading goes to Training with the effort's samples). More: Plural of, A form of, Another way of
writing, Part of a longer term, the way back from each, Add to this PC's database, Remove from the list.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QInputDialog, QMenu
import acrparts as AP
import efftrain as ET
from . import acrextras as AX


def _box(page):
    """3.80.0: (what the scan read in the drawn box, what It read says now, the crop) when a box is drawn, else Nones."""
    wv = getattr(page, "where_view", None)
    if wv is None or getattr(wv.view, "area", None) is None:
        return None, None, None
    return wv.area_read, " ".join(wv.reading.text().split()), wv.area_crop()


def missed(page, text, loc, read="", crop=None):
    """3.80.0: a term the scan missed, from a box drawn in the preview: listed with the scan's terms and added to this
    effort's list with the place it was found; a training sample (the crop and the right text) is kept with the effort."""
    import acrmore as AM
    s = page.session
    to = ("results", "list") if s.effort is not None else ("results",)
    said = AM.add_manual(s, text, document=loc, to=to)
    ET.add(s, "missed", read or "", text, [loc], crop=crop)
    page.host.toast(said or "Nothing was added.")
    page.fill(); page.select(" ".join(text.split()))
    return said


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
    _r, _t, crop = _box(page)
    ok = AP.set_part(s, term, whole)
    if ok:
        ET.add(s, "part", term, whole, (s.results.get(whole) or {}).get("locations", [])[:1], crop=crop)
        page.host.toast(f"{term} is part of {whole} where they sit together: {whole} takes the row.")
        page.fill()
        page.select(whole)
    return ok


def not_text(page, term):
    """The picture holds no text there: Not a term in this effort, and a sample for Training."""
    s = page.session
    _r, _t, crop = _box(page)
    ET.add(s, "not text", term, "", (s.results.get(term) or {}).get("locations", [])[:1], crop=crop)
    return page.set_status([term], "Not a term")


def misread(page, term, right=None):
    read, now, crop = _box(page)
    if right is None and now and now != term and now != (read or ""):
        right = now                                        # 3.80.0: the box's text, corrected in It read
    ok = AX.fix_misread(page, term, right)
    if ok:
        ET.add(page.session, "misread", term, right or "", (page.session.results.get(term) or {}).get("locations", [])[:1],
               crop=crop)
    return ok


def picture_menu(page, term, run=True):
    m = QMenu(page)
    m.addAction("Part of a longer term...").triggered.connect(lambda: part_of(page, term))
    m.addAction("Misread letters...").triggered.connect(lambda: misread(page, term))
    m.addAction("Not text").triggered.connect(lambda: not_text(page, term))
    _r, now, _c = _box(page)
    if now and now != term:                               # 3.80.0: the box says the term is written otherwise
        m.addSeparator()
        wv = page.where_view
        loc = wv.locs[wv.k] if wv.locs else ""
        m.addAction(f"This is the term: {now}").triggered.connect(lambda: missed(page, now, loc, term, _box(page)[2]))
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
