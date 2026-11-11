"""Place, Matrix & Outline's tab (4.3.0; claude/stationkeeper-matrix-outline-plan-4.3.md, steps 1 and 3): the Shred
page in place mode. Shred types; Place places. In place mode the page has our outline beside it (the Placer's lines,
the suggested home, Enter to accept), and L to M and Coverage show there too (Matrix & Outline's tabs); in Shred the
outline is hidden and the page only says what each piece is. Rules only (No AI); nothing leaves the PC."""
import diag

VIEW_OF = {"place": "structure", "crosswalk": "lm", "prove": "coverage"}


def apply(w, step):
    """After go(step) opened the Shred page: place mode for place, crosswalk and prove; Shred's own mode for the rest."""
    pg = w.assign_page
    on = step in VIEW_OF
    pg.place_mode = on
    try:
        pg.views.setVisible(on)
        if on:
            pg.show_view(VIEW_OF[step])
        g = getattr(getattr(pg, "placer", None), "gutter", None)
        if g is not None:
            g.setVisible(on and VIEW_OF.get(step) == "structure")
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return on
