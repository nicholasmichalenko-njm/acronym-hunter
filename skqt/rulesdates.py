"""Shred > Rules & Dates (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 4). One home for the customer's rules: the
submission rules found in the documents (what Submission Rules was, on the Dashboard), the other submission detail and
written formatting rules captured in the shred, and now the shred's own Rule and Date pieces and its key dates, each with
the document and the place it came from and a way back to it on the page.

This module adds the shred's groups to the page (custdocs.RequirementsPage) and shows one of them in its side card.
Rules only (No AI); nothing leaves the PC."""
import diag
import shredtypes as ST

GROUPS = (("rule", "Rules from the shred", "Pieces the shred said are a Rule (U)"),
          ("date", "Dates from the shred", "Pieces the shred said are a Date (D), and key dates captured"))


def rows(host):
    """{"rule": [row], "date": [row]}; a row: {"key", "id", "text", "file", "where", "how"}."""
    out = {"rule": [], "date": []}
    M = host.review.M if host.review is not None else None
    seen = set()
    if M is not None:
        for it in M.items:
            for t in [x for x in ST._keys(it.get(ST.FIELD)) if x in out]:                # 4.5.0: a piece can be both
                out[t].append({"key": "p:" + str(it.get("id", "")), "id": str(it.get("id", "")), "text": it.get("text", ""),
                               "file": it.get("file", ""), "where": _where(it), "how": "Shred"})
                seen.add(str(it.get("id", "")))
    try:
        import excerpts as EX
        import effortrec as R
        rec = R.Record(host.ws.root) if host.ws is not None else None
        for x in (EX.excerpts(rec, "keydate") if rec is not None else []):
            sid = next((p.get("sid") for p in x.get("parts") or [] if p.get("sid")), "")
            if sid and sid in seen:
                continue
            out["date"].append({"key": "x:" + x["id"], "id": sid, "text": EX.text_of(x), "file": "",
                                "where": EX.where_of(x), "how": "Key date" + (f": {x['value']}" if x.get("value") else "")})
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return out


def _where(it):
    bits = [it.get("file", ""), ("p." + str(it["page"])) if it.get("page") else "", it.get("section", "")]
    return ", ".join(b for b in bits if b)


def add_groups(page, keep=None):
    """Add the shred's groups to the page's tree. Returns the item to select (keep) or None."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidgetItem
    page.shred_rows = {}
    sel = None
    got = rows(page.host)
    for key, label, tip in GROUPS:
        mine = got[key]
        g = QTreeWidgetItem([f"{label} ({len(mine)})", "none yet" if not mine else "", "", ""])
        f = g.font(0); f.setBold(True); g.setFont(0, f); g.setToolTip(0, tip)
        page.tree.addTopLevelItem(g)
        for r in mine:
            words = r["text"]
            it = QTreeWidgetItem([words[:60] + ("..." if len(words) > 60 else ""), words[:200], r["how"], r["where"][:120]])
            it.setData(0, Qt.UserRole, r["key"]); it.setToolTip(1, words[:1500])
            g.addChild(it)
            page.shred_rows[r["key"]] = r
            if r["key"] == keep:
                sel = it
    return sel


import re

_STRUCT = re.compile(r"\bpages?\b.*\b(limit|exceed|maximum|no more than)\b|\b(limit|exceed|maximum|no more than)\b.*\bpages?\b|"
                     r"\bvolumes?\b|\bsections?\b.*\b(order|organi[sz]e|structure)", re.I)
_FORMAT = re.compile(r"\bfont|\bpoint\b|\bpt\b|margin|spacing|single[- ]spaced|line spacing|\bpaper\b|8\.5|letter size|"
                     r"\bheader|\bfooter|page number|\bfile (name|format|type)|\.pdf\b|\bpdf\b|\bword\b|\bexcel\b", re.I)
USED_BY = {"structure": "Matrix & Outline, Setup", "format": "Setup, Submit", "submission": "Submit, Dashboard"}


def bucket(text):
    """4.6.0: which of the three groups a rule the shred found belongs to, by its words (rules only)."""
    t = text or ""
    if _STRUCT.search(t):
        return "structure"
    if _FORMAT.search(t):
        return "format"
    return "submission"


def regroup(page):
    """4.6.0 (the six-steps board 3): three groups only. The excerpts, the written formatting rules and the shred's own
    Rule and Date pieces move under Structure and page limits, Format, or Submission and dates, each with what uses it."""
    from .custdocs import REQ_GROUPS
    t = page.tree
    tops = [t.topLevelItem(i) for i in range(t.topLevelItemCount())]
    main = {gk: tops[k] for k, (gk, _l, _kinds) in enumerate(REQ_GROUPS) if k < len(tops)}
    if len(main) < 3:
        return 0
    moved = 0
    for g in tops[3:]:
        label = g.text(0).split(" (")[0]
        while g.childCount():
            it = g.takeChild(0)
            if label in ("Other submission detail", "Dates from the shred"):
                gk = "submission"
            elif label == "Written formatting rules":
                gk = "format"
            else:
                gk = bucket(it.toolTip(1) or it.text(1) or it.text(0))
            from . import design as D
            if label in ("Rules from the shred", "Dates from the shred"):     # 4.21.0: a typed piece is listed here; only a
                it.setText(4, "Listed here")                                 # rule the reader found checks other pages
                it.setToolTip(4, "A piece typed Rule or Date in Shred is listed here. Add a rule... makes it one that "
                                 "Effort Formatting and Submit check.")
            else:
                it.setText(4, USED_BY[gk])
                it.setForeground(4, D.color("accent"))
            main[gk].addChild(it)
            moved += 1
        t.takeTopLevelItem(t.indexOfTopLevelItem(g))
    for gk, g in main.items():
        lab = g.text(0).split(" (")[0]
        g.setText(0, f"{lab} ({g.childCount()})")
        if g.childCount():
            g.setText(1, "")
    return moved


def show(page, key):
    """The side card for a row of the shred's groups. True when it was one."""
    r = getattr(page, "shred_rows", {}).get(key or "")
    if r is None:
        return False
    from PySide6.QtWidgets import QHBoxLayout, QWidget
    from . import design as D
    page.card.title.setText("Date" if key.startswith("x:") or _type(page, r) == "date" else "Rule")
    page.body.addWidget(D.label("“" + r["text"] + "”"))
    page.body.addWidget(D.label(r["where"] or "", "muted"))
    page.body.addWidget(D.label(r["how"], "muted"))
    row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
    if r["id"]:
        row.addWidget(D.button("Show it on the page", "primary", lambda: open_piece(page.host, r["id"]),
                               "Opens Shred > Requirements at this piece"))
    row.addStretch(1)
    w = QWidget(); w.setLayout(row); page.body.addWidget(w)
    page.body.addStretch(1)
    return True


def _type(page, r):
    M = page.host.review.M if page.host.review is not None else None
    it = next((x for x in (M.items if M is not None else []) if str(x.get("id", "")) == r["id"]), None)
    return ST.type_of(it or {}) if it else ""


def open_piece(host, iid):
    host.go("assign")
    try:
        host.assign_page.select(iid)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False
    return True
