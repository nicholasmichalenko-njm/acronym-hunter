"""The styles a Quick Part uses, on the Parts page (4.37.0; ST27 of 2026-11-14, step 1): one line on the row naming
them, a style this PC's styles do not hold in the alert color, and one sentence for the selected part saying what a
template would do about it. partstyles reads them from the part's kept file; nothing is saved, nothing leaves the PC.

4.38.0 (ST27 step 2): a Quick Part set goes with a style set. With such a set picked, the row's styles are held against
that style set (in it: the good color; not in it: the alert color), a line above the rows says how the set fits and one
button adds the styles you have to the style set. More > This set goes with a style set... makes the tie."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QWidget

import partstyles as PS
from . import design as D


def line(lib, it, part_sid=None):
    """A label: 'Uses: Callout Text, Body Text'. With a part set that goes with a style set, each style is held against
    that set (the good color in it, the alert color not in it); otherwise against every style of this PC."""
    names, tied = PS.names_for(lib, part_sid)
    st = PS.state(lib, it, names)
    t = D.tokens()
    def bit(n, ok):
        if ok and not tied:
            return html.escape(n)
        return f"<span style='color:{t['ok'] if ok else t['crit']};font-weight:600'>{html.escape(n)}</span>"
    bits = [bit(n, ok) for n, ok in st]
    lab = QLabel(("Uses: " + ", ".join(bits)) if bits else "Uses no style of its own")
    lab.setTextFormat(Qt.RichText); lab.setProperty("role", "muted"); lab.setObjectName("partUses"); lab.setWordWrap(True)
    lab.setProperty("lacking", [n for n, ok in st if not ok])
    return lab


def said(lib, it):
    """What to know about the selected Quick Part's styles; '' when every one is among this PC's styles."""
    lost = [n for n, ok in PS.state(lib, it, PS.library_names(lib)) if not ok]
    if not lost:
        return ""
    one = len(lost) == 1
    return (f"{'This style is' if one else 'These styles are'} not among your styles: {', '.join(lost)}. A template made with this "
            f"Quick Part takes {'it' if one else 'them'} from the Quick Part's own file. Bring {'it' if one else 'them'} in on "
            "Styles to keep the look in your standards.")


# ------------------------------------------------------------------ 4.38.0: the set's fit, above the rows
def add_fit(page, layout):
    """The line above the rows and its one button; hidden until a part set that goes with a style set is picked."""
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
    page.fit_line = D.label("", None); page.fit_line.setObjectName("fitLine")
    page.fit_add = D.button("", None, lambda: add_missing(page))
    h.addWidget(page.fit_line, 1); h.addWidget(page.fit_add)
    page.fit_box = w
    layout.addWidget(w)
    w.setVisible(False)
    return w


def fit_words(lib, part_sid):
    """(the sentence, the button's words or '', 'ok' or 'crit' or '') for the picked part set."""
    k = lib.kit(part_sid) if part_sid else None
    if k is None:
        return "", "", ""
    f = PS.fit(lib, part_sid)
    g = f["style_set"]
    if g is None:
        return f"{k['name']} goes with no style set yet. More > This set goes with a style set... ties them.", "", ""
    n = len(f["can_add"]) + len(f["absent"])
    if not n:
        return f"{k['name']} goes with the style set {g['name']}. Every style its Quick Parts use is in it.", "", "ok"
    said = f"{k['name']} goes with the style set {g['name']}. {n} style{'' if n == 1 else 's'} its Quick Parts use {'is' if n == 1 else 'are'} not in it: " \
        + ", ".join([page_name(lib, i) for i in f["can_add"]] + f["absent"]) + "."
    if f["absent"]:
        said += f" Not among your styles: {', '.join(f['absent'])}. Bring {'it' if len(f['absent']) == 1 else 'them'} in on Styles."
    m = len(f["can_add"])
    return said, (f"Add {m} style{'' if m == 1 else 's'} to {g['name']}" if m else ""), "crit"


def page_name(lib, it):
    return lib.base_of(it)


def refresh_fit(page):
    said, btn, tone = fit_words(page.lib, page.sid)
    page.fit_line.setText(said)
    t = D.tokens()
    page.fit_line.setStyleSheet(f"QLabel#fitLine{{color:{t[tone]};font-weight:600}}" if tone else "")
    page.fit_add.setText(btn); page.fit_add.setVisible(bool(btn))
    page.fit_box.setVisible(bool(said))
    return said


def add_missing(page):
    n = PS.add_missing(page.lib, page.sid)
    g = PS.goes_with(page.lib, page.sid)
    if n and g:
        page.host.toast(f"{n} style{'' if n == 1 else 's'} added to {g['name']}.")
    page.fill_rows()
    return n


def tie(page, style_sid=None, ask=True):
    """More > This set goes with a style set...: pick the style set (or none). Returns True when the tie changed."""
    import stylelib as SL
    k = page.lib.kit(page.sid) if page.sid else None
    if k is None:
        page.host.status("Pick a part set on the left first.")
        return False
    if ask:
        sets = SL.sets(page.lib, "style")
        if not sets:
            page.host.status("There is no style set yet. Make one on Styles first.")
            return False
        names = ["No style set"] + [s["name"] for s in sets]
        cur = PS.goes_with(page.lib, page.sid)
        pick, ok = QInputDialog.getItem(page, "This set goes with a style set", f"The Quick Parts in {k['name']} are written in the styles of:",
                                        names, names.index(cur["name"]) if cur else 0, False)
        if not ok:
            return False
        style_sid = next((s["id"] for s in sets if s["name"] == pick), "")
    ok = PS.set_goes_with(page.lib, page.sid, style_sid)
    page.fill_sets(); page.fill_rows()
    return ok
