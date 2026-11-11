"""Place's pane (4.5.0; claude/stationkeeper-shred-place-plan-4.5.md, step 5; the Place board of the six-steps canvas).
For the selected piece: "Place <id> in" with the suggested section and its reason (homesuggest.home), else the target
section; the main button Place it (Enter); Another section... (the outline); Leave it out of the matrix...; and how many
are not placed yet, N for the next. Rules, dates and information are not placed: they stay in Shred and travel to Setup
and Submit. An evaluation piece links through L to M. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QHBoxLayout, QMenu

import diag
import homesuggest as HS
import shredtypes as ST
from . import design as D


def where(page, it):
    """(label, why) the piece would go to: the suggestion, else the target section, else ("", "")."""
    h = HS.home(page.M, it)
    if h and h.get("label"):
        return h["label"], h.get("why", "")
    if page.target:
        return page.target, "The section selected in the outline"
    return "", ""


def add(page, rows):
    it = rows[-1]
    ks = ST.types_of(it)
    page.place_btn = None
    if not ST.placed_any([k for k in ks if k != "evaluation"]):
        if "evaluation" in ks:
            page.add(D.label("An evaluation piece links through L to M, not a section.", "muted"))
        else:
            page.add(D.label("Rules, dates and information are not placed: they stay in Shred and travel to Setup and Submit."
                             if ks else "Not sorted yet: say what it is in Shred first.", "muted"))
        count(page)
        return None
    if it.get("left_out"):
        page.head("Left out of the matrix")
        page.add(D.label(str(it.get("left_out")), "muted"))
        from . import leaveoutview as LV
        page.add(D.button("Put back in the matrix", None, lambda: LV.put_back(page, rows)))
        count(page)
        return None
    label, why = where(page, it)
    now = it.get("map") or ""
    page.head(f"Place {it['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'} in")
    page.place_to = label or now
    page.place_label = page.add(D.label(label or (now and f"Now in {now}") or "Pick a section in the outline", "title"))
    if why and label:
        page.add(D.label(f"Suggested: {why}. Enter takes it.", "muted"))
    elif now:
        page.add(D.label("Already placed. Another section... moves it.", "muted"))
    row = QHBoxLayout(); row.setSpacing(D.SPACE["xs"])
    page.place_btn = D.button("Place it  Enter", "primary", lambda: place_it(page), "Put the selected pieces in this section")
    page.place_btn.setEnabled(bool(label))
    row.addWidget(page.place_btn)
    other = D.button("Another section...", None, None, "Pick the section in the outline")
    m = QMenu(other)
    for lab in page.R.labels():
        m.addAction(lab, lambda _=False, l=lab: place_it(page, l))
    other.setMenu(m); page.other_btn = other
    row.addWidget(other)
    from . import leaveoutview as LV
    page.leave_btn = D.button("Leave it out...", None, lambda: LV.leave_out(page, page.selected()),
                              "Out of the matrix, with a reason kept on the piece")
    row.addWidget(page.leave_btn)
    row.addStretch(1)
    page.body_add_layout(row)
    count(page)
    return page.place_btn


def count(page):
    try:
        n = len(HS.left(page.M)["unplaced"])
    except Exception:  # noqa: BLE001
        diag.swallowed()
        n = 0
    page.place_left = page.add(D.label(f"Not placed yet: {n}" + ("  ·  N for the next" if n else ""), "muted"))
    return n


def place_it(page, label=None):
    """Put the selected pieces in label (else where they would go). Returns how many."""
    rows = page.selected()
    if not rows or page.R is None:
        return 0
    label = label or where(page, rows[-1])[0]
    if not label:
        page.host.status("Pick a section in the outline first.")
        return 0
    rows = [it for it in rows if ST.placed_any([k for k in ST.types_of(it) if k != "evaluation"]) and not it.get("left_out")]
    if not rows:
        return 0
    with page.R.group():
        page.R.snap(f"placed in {label}")
        for it in rows:
            if it.get("map") and it.get("map") != label:
                page.R.remove_section(it, it["map"])
        n = page.R.req(rows, label) or 0
    try:
        page.placer.after_place(rows, label)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    diag.activity("placed", n=n)
    page.after(f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' pieces'}: in {label}")
    return n
