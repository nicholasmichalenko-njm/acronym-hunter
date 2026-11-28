"""Last changed by (4.86.0, step I4 of claude/stationkeeper-document-intake-direction-2026-11-24.md, section 6): for each
matrix row, the newest version of a customer document whose changes touched its words ("Amendment 0002").

Read from what What changed already keeps (changereview's review.json): each compared pair's labels, the rows its
changes touched ("changed", kept from 4.86.0, placed or not; before that the placed ones of 3.89.0's "touch"), and each
requirement's history (an update or removal taken from a change). Nothing new is saved for it. The newest is the one
whose version arrived last (its Arrived as date, else the day it was added). Rules only (No AI); nothing leaves the PC.
    of(rv, lib)            {item id: {"label", "when", "doc"}}
    for_host(host)         the same for the open effort, kept while review.json and the library are unchanged
    text(e)                "Amendment 0002" ; tip(e) "Amendment 0002 of Section L (2026-11-20) changed these words"
"""
import os

import diag

_CACHE = {}


def _when_of(lib, doc_id, vid):
    d = lib.doc(doc_id) if lib is not None and doc_id else None
    v = next((x for x in (d or {}).get("versions") or [] if x.get("id") == vid), None)
    if v is None:
        return "", ""
    return (v.get("arrived_on") or (v.get("added") or "")[:10]), (v.get("added") or "")


def of(rv, lib):
    """{item id: {"label", "when", "doc"}}: the newest change that touched each row."""
    best = {}

    def put(iid, label, when, order, doc):
        if not iid or not label:
            return
        cur = best.get(iid)
        if cur is None or order >= cur["_o"]:
            best[iid] = {"label": label, "when": when, "doc": doc, "_o": order}

    for _pk, p in (getattr(rv, "pairs", None) or {}).items():
        label = (p.get("labels") or ["", ""])[-1]
        ids = p.get("changed")
        if ids is None:
            ids = [i for t in (p.get("touch") or {}).values() for i in t.get("items", [])]
        when, added = _when_of(lib, p.get("doc"), p.get("to"))
        for iid in ids:
            put(iid, label, when, (when, added), p.get("name", ""))
    for iid, hist in (getattr(rv, "lineage", None) or {}).items():
        for e in hist or []:
            if e.get("kind") in ("update", "remove", "removed", "updated") or e.get("label"):
                w = (e.get("when") or "")[:10]
                put(iid, e.get("label", ""), w, (w, e.get("when") or ""), e.get("doc", ""))
    for e in best.values():
        e.pop("_o", None)
    return best


def for_host(host):
    """of() for the open effort; {} without one."""
    ws = getattr(host, "ws", None)
    if ws is None:
        return {}
    try:
        import changereview as CR
        import docversions as DV
        rv = CR.Review(ws.root)
        keys = []
        for path in (rv.path, os.path.join(ws.p("documents"), "index.json")):
            try:
                st = os.stat(path)
                keys.append((path, st.st_mtime_ns, st.st_size))
            except OSError:
                keys.append((path, 0, 0))
        k = tuple(keys)
        if _CACHE.get("k") != k:
            _CACHE.clear()
            lib = DV.Library(ws.p("documents")).load() if os.path.isdir(ws.p("documents")) else None
            _CACHE["k"], _CACHE["v"] = k, of(rv.load(), lib)
        return _CACHE["v"]
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return {}


def text(e):
    return (e or {}).get("label", "")


def tip(e):
    if not e:
        return ""
    return f"{e['label']}" + (f" of {e['doc']}" if e.get("doc") else "") + (f" ({e['when']})" if e.get("when") else "") \
        + " changed these words. Open What changed to see how."
