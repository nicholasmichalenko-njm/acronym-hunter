"""The deliverables board (2.87.0): every deliverable the effort owes at a glance, and everything about one.

For each deliverable: its owner, status and the due date; pages against its limit; the response volume it holds (a
Volume deliverable is linked to its volume in the response structure, by name or by the person); the compliance
requirements placed in that volume's sections (how many have an author, how many a customer version changed and are
waiting for their owner); context attached to its sections from library documents; what the latest Submission check
found in its file (first-use problems, banned words, acronym list entries that still need a definition or approval);
and what is missing (no owner, no file, over the limit, a newer customer form, no linked volume, requirements with no
author). Health: ok, attention or critical, so the board shows where to look first.
Reads only: the effort record, the matrix, the library, Change review, the library context and the last check.
Rules only (No AI); nothing leaves the PC.
"""
import os, re
import deliverables as DL

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8}


def _vol_num(text):
    m = re.search(r"vol(?:ume)?[\s_.-]*(viii|vii|vi|iv|v|iii|ii|i|[1-8])(?![a-z0-9])", (text or "").lower())
    if not m:
        return None
    t = m.group(1)
    return int(t) if t.isdigit() else ROMAN.get(t)


def link_volume(d, heads):
    """The response volume a deliverable holds: the one the person linked, else one with the same name or number."""
    if d.get("volume") in heads:
        return d["volume"]
    if (d.get("kind") or "") != "Volume":
        return ""
    name = (d.get("name") or "").lower().strip()
    for h in heads:
        if h.lower().strip() == name or h.lower().startswith(name) or name.startswith(h.lower()):
            return h
    n = _vol_num(name)
    if n:
        for h in heads:
            if _vol_num(h) == n:
                return h
    return ""


def card(d, rows=(), lib=None, vols=(), rec=None, M=None, ctx_counts=None, awaiting=(), report=None):
    """Everything the board shows for one deliverable (a dict)."""
    st = DL.state(d, rows, lib, vols, rec)
    out = {"id": d["id"], "name": d.get("name", ""), "kind": d.get("kind", ""), "owner": d.get("owner", ""),
           "status": d.get("status", "Not started"), "limit": st["limit"], "pages": st["pages"], "over": st["over"],
           "changed": list(st["changed"]), "form": st["form"], "file": d.get("file", ""), "done_here": st["done_here"],
           "volume": "", "sections": [], "reqs": 0, "owned": 0, "awaiting": [], "changed_reqs": [], "context": 0,
           "first_use": 0, "banned": 0, "list_open": 0, "checked": False, "missing": []}
    if M is not None:
        import outline_ops as O
        import setupdoc as SD
        heads = O.volume_heads(M)
        vol = link_volume(d, heads)
        out["volume"] = vol
        if vol:
            labs = O.in_volume(M, vol)
            out["sections"] = labs
            P = SD.placed_in(M)
            ids = []
            for lab in labs:
                for i in P.get(lab, []):
                    if i not in ids:
                        ids.append(i)
            by = {it["id"]: it for it in M.items}
            reqs = [by[i] for i in ids if i in by and by[i].get("decision") == "Keep"]
            out["reqs"] = len(reqs)
            out["owned"] = sum(1 for it in reqs if SD.owner_of(M, it))
            wait = set(awaiting or ())
            out["awaiting"] = [it["id"] for it in reqs if it["id"] in wait]
            out["changed_reqs"] = [it["id"] for it in reqs if str(it.get("new", "")).startswith(("Changed by", "New in", "Removed by"))]
            out["req_rows"] = [{"id": it["id"], "section": it.get("map", ""), "text": it.get("text", ""),
                                "owner": SD.owner_of(M, it), "awaiting": it["id"] in wait, "new": it.get("new", "")} for it in reqs]
            out["context"] = sum((ctx_counts or {}).get(lab, 0) for lab in labs)
    if report and out["file"]:
        v = os.path.basename(out["file"])
        if v in report.get("volumes", []):
            out["checked"] = True
            out["first_use"] = sum(1 for r in report.get("first_use", []) if r.get("volume") == v and r.get("level") in ("bad", "warn"))
            out["banned"] = sum(1 for r in report.get("banned", []) if r.get("volume") == v and r.get("level") == "bad")
            out["list_open"] = sum(1 for x in report.get("lists", {}).get(v, []) if x.get("status") != "Approved" or not x.get("definition"))
    m = out["missing"]
    if not out["owner"]:
        m.append(("crit", "No owner"))
    if out["over"]:
        m.append(("crit", f"Over its page limit ({out['pages']} of {out['limit']})"))
    if out["kind"] == "Volume" and not out["file"]:
        m.append(("warn", "No working file linked (pages and the submission check need it)"))
    if out["kind"] == "Volume" and M is not None and not out["volume"]:
        m.append(("warn", "Not linked to a volume of the response structure"))
    if out["volume"] and out["reqs"] and out["owned"] < out["reqs"]:
        m.append(("warn", f"{out['reqs'] - out['owned']} requirement(s) with no author"))
    if out["awaiting"]:
        m.append(("warn", f"{len(out['awaiting'])} requirement(s) a customer version changed, waiting for their owner"))
    for c in out["changed"]:
        m.append(("warn", c[0].upper() + c[1:]))
    if out["checked"] and out["list_open"]:
        m.append(("warn", f"{out['list_open']} acronym list entr(ies) need a definition or approval"))
    if out["checked"] and out["first_use"]:
        m.append(("warn", f"{out['first_use']} first-use problem(s) to fix"))
    if out["checked"] and out["banned"]:
        m.append(("warn", f"{out['banned']} banned word(s) or phrase(s)"))
    if out["kind"] == "Volume" and out["file"] and not out["checked"]:
        m.append(("info", "Not in the latest Submission check"))
    out["health"] = "crit" if any(k == "crit" for k, _t in m) else "warn" if any(k == "warn" for k, _t in m) else "ok"
    return out


def board(rec, rows=(), lib=None, vols=(), M=None, data_dir="", report=None):
    """[card] for every deliverable, the ones needing attention first, then in their order."""
    ctx_counts, awaiting = {}, []
    if data_dir:
        try:
            import ctxdocs as CX
            ctx_counts = CX.Store(data_dir).load().section_counts()
        except Exception:
            ctx_counts = {}
        try:
            import changereview as CR
            awaiting = CR.Review(data_dir).load().awaiting()
        except Exception:
            awaiting = []
    cards = [card(d, rows, lib, vols, rec, M, ctx_counts, awaiting, report) for d in DL.items(rec)]
    rank = {"crit": 0, "warn": 1, "ok": 2}
    order = {c["id"]: k for k, c in enumerate(cards)}
    return sorted(cards, key=lambda c: (rank[c["health"]], order[c["id"]]))


def summary_line(cards):
    """'4 deliverables: 1 over its page limit, 2 need attention, 1 ready' for Effort home and the dashboard."""
    if not cards:
        return "No deliverables yet."
    over = sum(1 for c in cards if c["over"])
    crit = sum(1 for c in cards if c["health"] == "crit")
    warn = sum(1 for c in cards if c["health"] == "warn")
    ok = sum(1 for c in cards if c["health"] == "ok")
    parts = [f"{len(cards)} deliverable(s)"]
    bits = []
    if over:
        bits.append(f"{over} over its page limit")
    if crit - over > 0:
        bits.append(f"{crit - over} critical")
    if warn:
        bits.append(f"{warn} need attention")
    if ok:
        bits.append(f"{ok} on track")
    return parts[0] + (": " + ", ".join(bits) if bits else "")
