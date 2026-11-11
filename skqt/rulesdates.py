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
