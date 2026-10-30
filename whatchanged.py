"""What a new version changed (2.98.0), in two places:

- summary(): "What changed in Amendment 1", the moment a new version is added: how many sentences changed, were added or
  were removed; the submission rules it touches (page limits, due dates, formats); the compliance requirements it touches
  and who owns them; the new sentences not in the matrix yet; and how many changes are still to decide in Changes.
- marks(): the changes of the version a page shows, for Assign: each changed or added sentence of the new version with
  what it was before (the old wording and the word-level difference), and where the old sentence sits in the old
  version (its file), so the page can show the old page at the same spot.

Built on docversions.compare (the same comparison Changes uses) and docintake.link. Rules only (No AI); nothing leaves
the PC.
"""
import os, re
import docversions as DV


def _key(s):
    return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))


def versions_of(lib, file_name):
    """(document, version, the version before it) for a file of the library, or (None, None, None)."""
    d = lib.doc_of_file(file_name)
    if d is None:
        return None, None, None
    f = os.path.basename(file_name or "").lower()
    vs = d["versions"]
    i = next((k for k, v in enumerate(vs) if v.get("file", "").lower() == f), None)
    if i is None:
        return d, None, None
    return d, vs[i], (vs[i - 1] if i > 0 else None)


def rows_between(lib, va, vb):
    rows = DV.compare(lib.text(va), lib.text(vb))
    try:
        import changereview as CRV
        CRV.keyed(rows)
    except Exception:
        pass
    return rows


def summary(lib, d, vb, va=None, M=None, data_dir=""):
    """What vb changed against the version before it (or va). {"title", "doc", "from", "to", "changed", "added", "removed",
    "rules": [text], "requirements": [{id, owner, decision}], "owners": [names], "not_in_matrix": n, "to_decide": n,
    "text": one paragraph}. None when vb is the first version."""
    if va is None:
        vs = d["versions"]
        i = next((k for k, v in enumerate(vs) if v["id"] == vb["id"]), 0)
        if i == 0:
            return None
        va = vs[i - 1]
    rows = rows_between(lib, va, vb)
    c = DV.summary(rows)
    rules = []
    for r in rows:
        if r["kind"] != "same" and r.get("submission"):
            rules.append(r.get("new") or r.get("old"))
    reqs, owners, not_in = [], set(), 0
    if M is not None:
        import docintake as DI
        links = DI.link(M, rows)
        seen = set()
        for r, hits in zip(rows, links):
            if r["kind"] == "same":
                continue
            kept = [h for h in hits if h.get("decision") == "Keep"]
            for h in kept:
                if h["id"] not in seen:
                    seen.add(h["id"]); reqs.append(h)
                    if h.get("owner"):
                        owners.add(h["owner"])
            if r["kind"] == "added" and not hits:
                not_in += 1
    to_decide = sum(1 for r in rows if r["kind"] != "same")
    if data_dir:
        try:
            import changereview as CRV
            rv = CRV.Review(data_dir).load()
            done, total = rv.progress(CRV.pair_key(va, vb), rows)
            to_decide = total - done
        except Exception:
            pass
    title = f"What changed in {vb.get('label', 'the new version')}" + (f" of {d.get('name', '')}" if d.get("name") else "")
    parts = [f"{c['changed']} sentence(s) changed, {c['added']} added, {c['removed']} removed"]
    if rules:
        parts.append(f"{len(rules)} touch submission rules (page limits, dates, formats)")
    if M is not None:
        parts.append(f"{len(reqs)} compliance requirement(s) affected" + (f" (owners: {', '.join(sorted(owners)[:4])})" if owners else ""))
        if not_in:
            parts.append(f"{not_in} new sentence(s) not in the matrix yet")
    parts.append(f"{to_decide} change(s) to decide in Changes")
    return {"title": title, "doc": d, "from": va, "to": vb, "changed": c["changed"], "added": c["added"], "removed": c["removed"],
            "rules": rules, "requirements": reqs, "owners": sorted(owners), "not_in_matrix": not_in, "to_decide": to_decide,
            "text": "; ".join(parts) + "."}


def marks(lib, file_name):
    """The changes the version in file_name made: {"doc", "from", "to", "by": {text key of the new sentence: {"kind",
    "old", "new", "diff"}}, "removed": [old sentences]}; None when the file is not a later version in the library."""
    d, vb, va = versions_of(lib, file_name)
    if vb is None or va is None:
        return None
    rows = rows_between(lib, va, vb)
    by, removed = {}, []
    for r in rows:
        if r["kind"] in ("changed", "added") and r.get("new"):
            by[_key(r["new"])] = {"kind": r["kind"], "old": r.get("old", ""), "new": r["new"], "diff": r.get("diff", [])}
        elif r["kind"] == "removed":
            removed.append(r.get("old", ""))
    return {"doc": d, "from": va, "to": vb, "by": by, "removed": removed}


def mark_of(m, text):
    """The change for a sentence of the page (matched on its words), or None."""
    if not m:
        return None
    k = _key(text)
    if k in m["by"]:
        return m["by"][k]
    for kk, ch in m["by"].items():                   # a sentence the reader cut a little differently
        if k and (k in kk or kk in k) and min(len(k), len(kk)) > 0.8 * max(len(k), len(kk)):
            return ch
    return None


def find_on_pages(pdf, text):
    """(page index, [rects in PDF points (left, top, right, bottom) from the top of the page]) where text sits in a PDF,
    found by its first words; None when not found."""
    import pypdfium2 as pdfium
    words = " ".join((text or "").split())
    if not words:
        return None
    probes = [words[:80], words[:40], " ".join(words.split()[:5])]
    doc = pdfium.PdfDocument(pdf)
    try:
        for probe in probes:
            if len(probe) < 8:
                continue
            for i in range(len(doc)):
                page = doc[i]
                tp = page.get_textpage()
                try:
                    srch = tp.search(probe, match_case=False, match_whole_word=False)
                    hit = srch.get_next()
                    if hit:
                        start, count = hit
                        h = page.get_height()
                        rects = []
                        n = tp.count_rects(start, count)
                        for k in range(n):
                            l, b, r, t = tp.get_rect(k)
                            rects.append((l, h - t, r, h - b))
                        return i, rects
                finally:
                    tp.close()
    finally:
        doc.close()
    return None
