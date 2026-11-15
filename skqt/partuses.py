"""The styles a Quick Part uses, on the Parts page (4.37.0; ST27 of 2026-11-14, step 1): one line on the row naming
them, a style this PC's styles do not hold in the alert color, and one sentence for the selected part saying what a
template would do about it. partstyles reads them from the part's kept file; nothing is saved, nothing leaves the PC."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

import partstyles as PS
from . import design as D


def line(lib, it):
    """A label: 'Uses: Callout Text, Body Text' (a style not among this PC's styles in the alert color)."""
    st = PS.state(lib, it, PS.library_names(lib))
    t = D.tokens()
    bits = [html.escape(n) if ok else f"<span style='color:{t['crit']};font-weight:600'>{html.escape(n)}</span>" for n, ok in st]
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
