"""Decision 6 (3.89.0): placed sentences an amendment changed, in Review and Setup. A placed sentence whose customer
sentence a newer version changed or removed (or whose customer heading gained text) carries "Changed in Amendment 1"
until that change is decided in Compare. It keeps its place. A click opens the change in Compare.
    flags(host)            {item id: [{"text", "pk", "key"}]}
    mark_page(page)        Review: the flag in the right margin of each flagged sentence on the page
    line(flag)             the words and the link for a card ("Changed in Amendment 1. Open the change")
    open_change(host, f)   Compare, on that pair and that change
Rules: comparemap.flags (from what Compare and Library recorded in changereview). Nothing leaves the PC."""
import os

import diag

_CACHE = {}


def _review(root):
    import changereview as CR
    rv = CR.Review(root)
    try:
        st = os.stat(rv.path)
        k = (rv.path, st.st_mtime_ns, st.st_size)
    except OSError:
        return rv
    if _CACHE.get("k") != k:
        _CACHE.clear()
        _CACHE["k"], _CACHE["rv"] = k, rv.load()
    return _CACHE["rv"]


def flags(host):
    """{item id: [{"text", "pk", "key"}]} for the open effort; {} without a matrix."""
    if getattr(host, "ws", None) is None or getattr(host, "review", None) is None:
        return {}
    try:
        import comparemap as CM
        return CM.flags(host.review.M, _review(host.ws.root))
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return {}


def mark_page(page):
    """Review: "Changed in Amendment 1" beside each flagged sentence on the page (amber); its tooltip names them all."""
    from PySide6.QtGui import QColor, QFont
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    from . import design as D
    fl = flags(page.host)
    changed = set(fl) != set(getattr(page, "amend_flags", None) or {})
    page.amend_flags = fl
    if changed and getattr(page, "placer", None) is not None:
        page.placer.show_left()                          # the Left line counts them
    if not fl:
        return 0
    sc = page.view.scene()
    n = 0
    for iid, box in page.view.boxes.items():
        f = fl.get(iid)
        if not f:
            continue
        r = box.boundingRect()
        lab = QGraphicsSimpleTextItem(f[0]["text"] + (f" (+{len(f) - 1})" if len(f) > 1 else ""))
        lab.setFont(QFont("Segoe UI", 7, QFont.Bold))
        lab.setBrush(QColor(D.tokens()["warn"]))
        lab.setPos(r.right() + 4, r.bottom() - 9)
        lab.setToolTip("\n".join(x["text"] for x in f) + "\nIt keeps its place. Decide the change in Amendments.")
        sc.addItem(lab)
        page.labels.append(lab)
        n += 1
    return n


def line(f):
    """Rich text for a card or a row: the flag, and the link that opens the change."""
    import html
    return (f"<span style='font-weight:600'>{html.escape(f['text'])}</span>. It keeps its place. "
            f"<a href='amend:{f['pk']}|{f['key']}'>Open the change in Amendments</a>")


def from_link(href):
    """The flag a link from line() names: {"pk", "key"} or None."""
    if not href.startswith("amend:") or "|" not in href:
        return None
    pk, key = href[6:].split("|", 1)
    return {"pk": pk, "key": key}


def open_change(host, flag):
    """Compare, on the pair and the change this flag came from."""
    import changereview as CR
    p = CR.Review(host.ws.root).load().pairs.get(flag["pk"]) or {}
    if not p.get("doc"):
        return False
    host.go("compare")
    cp = host.compare_page
    try:
        host.compare_space.tabs.setCurrentWidget(cp)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    cp.show(p["doc"], p.get("from"), p.get("to"))
    diag.activity("amend_flag_opened")
    return cp.open_key(flag["key"])
