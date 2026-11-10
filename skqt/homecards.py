"""The Effort Dashboard's 3.63.0 parts, kept apart from homepage.py (at its size limit): the path strip under the header,
the Meeting notes and Evaluation criteria cards, and the deliverables list with parts, people and compliance."""
from PySide6.QtWidgets import QHBoxLayout
import diag
from . import design as D


def install(hp):
    """Called while the page is built: the strip goes under the header; the two cards join the page's cards."""
    from .pathstrip import PathStrip
    hp.path = PathStrip(hp.host)
    hp.path.compact = True                          # 3.96.0: the request type and how it is sent; the map shows the steps
    hp.head.layout().addWidget(hp.path)
    from .pathmap import PathMap                    # 3.96.0: the Dashboard as the map (canvas "Navigation", board 2)
    hp.map = PathMap(hp)
    hp.bar.parentWidget().layout().insertWidget(0, hp.map)
    hp.meet_card = D.Card("Meeting notes", "The latest meetings and the topics they left open. Notes are taken on Meetings "
                          "(+ Add > Meeting notes).")
    hp.eval_card = D.Card("Evaluation criteria", "How the customer will judge the proposal: the factors, their importance and "
                          "the deliverables they judge.")
    from PySide6.QtWidgets import QVBoxLayout
    hp.meet_box = QVBoxLayout(); hp.meet_box.setSpacing(D.SPACE["xs"]); hp.meet_card.body.addLayout(hp.meet_box)
    hp.eval_box = QVBoxLayout(); hp.eval_box.setSpacing(D.SPACE["xs"]); hp.eval_card.body.addLayout(hp.eval_box)
    return {"meetings": hp.meet_card, "evalcrit": hp.eval_card}


def _note(hp):
    from .quicknote import open_note
    return open_note(hp.host)


def _clear(lay):
    while lay.count():
        it = lay.takeAt(0)
        if it.widget() is not None:
            it.widget().setParent(None)
        elif it.layout() is not None:
            _clear(it.layout())


def refresh(hp):
    try:
        hp.path.refresh()
    except Exception:  # noqa: BLE001  the strip must never stop the page
        diag.swallowed()
    try:
        hp.map.refresh()
    except Exception:  # noqa: BLE001  the map must never stop the page
        diag.swallowed()
    r = hp.rec
    if r is None:
        return
    draw_meetings(hp, r)
    draw_eval(hp, r)


def draw_meetings(hp, r):
    import meetings as MT
    _clear(hp.meet_box)
    ms = MT.meetings(r)[:3]
    hp.meetings_now = [m.get("title", "") for m in ms]
    if not ms:
        hp.meet_box.addWidget(D.label("No meetings yet. + Meeting notes records one; Quick note (Ctrl+Shift+N) catches a line "
                                      "from any page.", "muted"))
        return
    for m in ms:
        open_t = [t for t in m.get("topics", []) if t.get("status", "open") == "open"]
        hp.meet_box.addWidget(D.label(f"<b>{m.get('title', '')}</b>  ·  {str(m.get('date', ''))[:10]}"
                                      + (f"  ·  {len(open_t)} open topic(s)" if open_t else ""), None))
        notes = " ".join((m.get("notes") or "").split())
        if notes:
            hp.meet_box.addWidget(D.label(notes[:220] + ("..." if len(notes) > 220 else ""), "muted"))


def draw_eval(hp, r):
    import custfocus as F
    import deliverables as DL
    _clear(hp.eval_box)
    fs = [f for f in F.factors(r) if not f.get("parent")]
    names = {d["id"]: d["name"] for d in DL.items(r)}
    hp.eval_now = [f["name"] for f in fs]
    if not fs:
        hp.eval_box.addWidget(D.label("None yet. Add them on Evaluation Criteria, or capture them in Review (More captures).", "muted"))
        return
    for f in fs[:6]:
        tied = ", ".join(names[x] for x in f.get("deliverables") or [] if x in names)
        imp = f.get("importance", "Not stated")
        hp.eval_box.addWidget(D.label(f"<b>{f['name']}</b>" + (f"  ·  {imp}" if imp != "Not stated" else "")
                                      + (f"  ·  judged on {tied}" if tied else ""), None))
    if len(fs) > 6:
        hp.eval_box.addWidget(D.label(f"and {len(fs) - 6} more", "muted"))


def draw_deliverables(hp):
    """Every deliverable in the team's order: its health, owner, parts and people, and its compliance line."""
    import delivboard as DB
    import deliverables as DL
    import delivmore as DM
    from .delivboardview import HEALTH, TONE
    _clear(hp.deliv_box)
    cards = getattr(hp, "cards_now", [])
    if not cards:
        hp.deliv_box.addWidget(D.label("No deliverables yet. Add them on the board.", "muted"))
        return
    hp.deliv_box.addWidget(D.label(DB.summary_line(cards), None))
    r = hp.rec
    order = {d["id"]: i for i, d in enumerate(DL.items(r))} if r is not None else {}
    M = hp.host.review.M if hp.host.review is not None else None
    hp.deliv_rows = []
    for c in sorted(cards, key=lambda x: order.get(x["id"], 0))[:10]:
        d = DL.get(r, c["id"]) if r is not None else None
        ppl = DM.people(d, M) if d else []
        parts = len(d.get("parts", [])) + len(DM.structure_parts(d, M)) if d else 0
        comp = f"{c['reqs']} requirements, {c['owned']} with an author" if c.get("volume") else ""
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.Pill(HEALTH[c["health"]], TONE[c["health"]]))
        bits = [x for x in (c.get("owner") and f"owner {c['owner']}", parts and f"{parts} part(s)",
                            ppl and ", ".join(ppl[:4]) + (" and more" if len(ppl) > 4 else ""), comp) if x]
        line = f"<b>{c['name']}</b>  " + "  ·  ".join(bits)
        if c["missing"]:
            line += f"  <span style='color:{D.tokens()['warn']}'>{c['missing'][0][1]}</span>"
        row.addWidget(D.label(line, None), 1)
        row.addWidget(D.button("Open", "ghost", lambda _=False, i=c["id"]: (hp.host.go("deliverables"), hp.host.deliverables_page.open_deliverable(i))))
        hp.deliv_box.addLayout(row)
        hp.deliv_rows.append({"id": c["id"], "text": line})
    if len(cards) > 10:
        hp.deliv_box.addWidget(D.label(f"and {len(cards) - 10} more on the board", "muted"))
