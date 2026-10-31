"""Page budget by section (3.1.0): split each volume's page limit across its sections, so each author knows how many
pages they have before writing. Kept with the response structure (the matrix's setup), shown in Review and Structure,
printed under each section in the Response Setup documents, listed in My Work, and compared with the volume's draft
(the page count Word saved in it). A section's pages include its subsections: the total counts each budgeted section
once, at the highest level budgeted. Rules only."""
import setupdoc as SD

STEP = 0.5


def _b(M):
    S = SD.setup_of(M)
    b = S.get("budget")
    if not isinstance(b, dict):
        b = S["budget"] = {}
    b.setdefault("pages", {}); b.setdefault("limits", {})
    return b


def pages(M, label):
    v = _b(M)["pages"].get(label)
    return float(v) if v not in (None, "") else None


def set_pages(M, label, n):
    b = _b(M)["pages"]
    n = _round(n)
    if not n:
        b.pop(label, None)
    else:
        b[label] = n
    if hasattr(M, "pending"):
        M.pending = True


def set_limit(M, volume, n):
    lim = _b(M)["limits"]
    if n:
        lim[volume or ""] = int(n)
    else:
        lim.pop(volume or "", None)
    if hasattr(M, "pending"):
        M.pending = True


def _round(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return 0
    return max(0.0, round(n / STEP) * STEP)


def fmt(n):
    if n is None:
        return ""
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def volumes(M):
    """[(volume name, [section labels])]: each volume of the structure; one entry with every section when there are none."""
    import outline_ops as O
    mode, name, heads = SD.volumes_of(M)
    if mode == "several" and heads:
        return [(h, O.in_volume(M, h)) for h in heads]
    return [(name or "", SD.labels(M))]


def limit_for(M, volume, rows=(), delivs=()):
    """(pages, where it came from): typed here, else the customer's page limit for the volume (Submission Rules), else the
    volume deliverable's limit, else (None, '')."""
    import subreq as SR
    typed = _b(M)["limits"].get(volume or "")
    if typed:
        return int(typed), "set here"
    single = len(volumes(M)) == 1
    for r in rows:
        if r.get("kind") == "Page limit" and ((volume and SR.match_volume(r.get("subject", ""), volume))
                                              or (single and (r.get("subject", "").lower() in ("proposal", "technical volume") or not volume))):
            n = SR._limit_n(r.get("value", ""))
            if n:
                return n, f"{r.get('doc', '')}, {r.get('version', '')}".strip(", ") or "Submission Rules"
    for d in delivs:
        if (volume and SR.match_volume(d.get("name", ""), volume) or d.get("name", "") == volume) and SR._limit_n(d.get("limit", "")):
            return SR._limit_n(d["limit"]), f"deliverable {d['name']}"
    return None, ""


def total(M, labels):
    """Pages budgeted across labels: each budgeted section counted once, at its highest budgeted level."""
    have = {l for l in labels if pages(M, l)}
    out = 0.0
    for l in have:
        if not any(p in have for p in SD._parents(M, l)[1:]):
            out += pages(M, l)
    return out


def children_total(M, label):
    """Pages budgeted in a section's subsections (each at its highest budgeted level below the section)."""
    import compliance as C
    labs = [(C.outline_label(o), o.get("level", 1)) for o in M.outline]
    i = next((k for k, (l, _v) in enumerate(labs) if l == label), None)
    if i is None:
        return 0.0
    lvl, under = labs[i][1], []
    for l, v in labs[i + 1:]:
        if v <= lvl:
            break
        under.append(l)
    return total(M, under)


def parts(M, volume_labels):
    """The sections a volume's limit is split across: the level just under the volume's heading (or the top level)."""
    import compliance as C
    lv = {C.outline_label(o): o.get("level", 1) for o in M.outline}
    labs = [l for l in volume_labels if l in lv]
    if not labs:
        return []
    top = min(lv[l] for l in labs)
    tops = [l for l in labs if lv[l] == top]
    if len(tops) == 1 and len(labs) > 1:                    # a volume heading: split across what is under it
        nxt = min((lv[l] for l in labs if lv[l] > top), default=top)
        return [l for l in labs if lv[l] == nxt]
    return tops


def req_counts(M, labels):
    """Compliance requirements placed in each section, its subsections included."""
    P = SD.placed_in(M)
    import compliance as C
    labs = [(C.outline_label(o), o.get("level", 1)) for o in M.outline]
    out = {}
    for l in labels:
        i = next((k for k, (x, _v) in enumerate(labs) if x == l), None)
        if i is None:
            out[l] = 0
            continue
        ids, lvl = set(P.get(l, [])), labs[i][1]
        for x, v in labs[i + 1:]:
            if v <= lvl:
                break
            ids |= set(P.get(x, []))
        byid = {it["id"]: it for it in M.items}
        out[l] = sum(1 for k in ids if (byid.get(k) or {}).get("decision") == "Keep")
    return out


def split(M, labels, limit, by="even"):
    """Spread limit pages across labels (evenly, or by how many requirements each holds), in half pages, every page
    used. Returns {label: pages}; sets them."""
    if not labels or not limit:
        return {}
    w = req_counts(M, labels) if by == "reqs" else {l: 1 for l in labels}
    if not sum(w.values()):
        w = {l: 1 for l in labels}
    tot = sum(w.values())
    units = int(round(limit / STEP))
    exact = {l: units * w[l] / tot for l in labels}
    got = {l: int(exact[l]) for l in labels}
    for l in sorted(labels, key=lambda l: exact[l] - got[l], reverse=True)[:units - sum(got.values())]:
        got[l] += 1
    out = {l: got[l] * STEP for l in labels}
    for l, n in out.items():
        set_pages(M, l, n)
    return out


def draft_pages(volume, delivs):
    """The page count Word saved in the volume's draft (its deliverable's file), or None."""
    import os
    import subreq as SR
    for d in delivs:
        if (SR.match_volume(d.get("name", ""), volume) or d.get("name", "") == volume) and d.get("file", "").lower().endswith(".docx") \
                and os.path.isfile(d["file"]):
            return SR.word_pages(d["file"])
    return None
