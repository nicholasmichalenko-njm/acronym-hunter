"""Impact review (2.42.0): what one new customer document version touched across the effort.

One review per incoming version (Amendment 3 of the RFP, a revised form...), compared with the version before it:
- Text: changed, added and removed sentences (docversions.compare).
- Submission requirements: each requirement this version changed, added or removed, was and now.
- Deliverables: a page limit or requirement behind one changed, a newer form version arrived, our file is now over
  its limit; deliverables this version names for the first time (suggested; add or not ours).
- Compliance: matrix sentences this version changed or removed, with their section and owner; new sentences not in
  the matrix yet.
- Acronyms: capitalized terms new in this version or no longer in it, and whether the effort list and the master
  database already hold them.
- Structure: RFP headings renamed, added or removed, and our response sections named like the old heading.
- Keywords: customer phrases new in this version, used at least twice, not in the keyword list yet.
- People: who it touches (owners of changed compliance sentences and deliverables).
Nothing changes until a person acts on it: every item is a suggestion with a way to open it. Rules only (No AI);
nothing leaves the PC.
"""
import collections, re
import docversions as DV

ACR = re.compile(r"(?<![\w-])([A-Z][A-Z0-9&]{1,7})(?:s|'s)?(?![\w-])")
ROMAN = re.compile(r"^[IVXLC]+$")
SKIP = {"THE", "AND", "FOR", "NOT", "ALL", "ANY", "SHALL", "WILL", "MUST", "MAY", "ARE", "THIS", "THAT", "WITH", "FROM", "EACH",
        "PART", "SECTION", "VOLUME", "PAGE", "NOTE", "OR", "OF", "TO", "IN", "ON", "BY", "AN", "AS", "AT", "IS", "IT", "BE", "NO",
        "US", "ID", "OK"}


def _version(lib, doc_id, vid):
    d = lib.doc(doc_id)
    if d is None:
        return None, None, None
    vs = d["versions"]
    i = next((k for k, v in enumerate(vs) if v["id"] == vid), None)
    if i is None:
        return d, None, None
    return d, vs[i], (vs[i - 1] if i else None)


def find_version(lib, vid):
    """(doc, version, previous version) for a version id, or (None, None, None)."""
    for d in lib.docs:
        if any(v["id"] == vid for v in d["versions"]):
            return _version(lib, d["id"], vid)
    return None, None, None


def pending(lib):
    """Versions with a version before them whose impact is not reviewed yet, newest first: [(doc, version)]."""
    out = [(d, v) for d in lib.docs for v in d["versions"][1:] if not v.get("reviewed")]
    out.sort(key=lambda x: x[1].get("added", ""), reverse=True)
    return out


def reviewable(lib):
    """Every version that has a version before it, newest first: [(doc, version)]."""
    out = [(d, v) for d in lib.docs for v in d["versions"][1:]]
    out.sort(key=lambda x: x[1].get("added", ""), reverse=True)
    return out


# ------------------------------------------------------------------ parts
def requirements(rows, vid):
    """Submission requirements this version changed, added or removed: [{key, kind, subject, change, was, now, sentence,
    to_review}]."""
    out = []
    for r in rows:
        if r.get("manual") or r.get("hidden"):
            continue
        hist = r.get("history") or []
        for k, h in enumerate(hist):
            if h.get("version_id") != vid:
                continue
            ch = h["change"]
            if ch == "same":
                break
            if ch == "first":
                ch = "new"
            was = next((x["value"] for x in reversed(hist[:k]) if x["value"]), "")
            out.append({"key": r["key"], "kind": r["kind"], "subject": r["subject"], "change": ch, "was": was,
                        "now": h["value"] if ch != "removed" else "", "sentence": h.get("sentence", ""),
                        "to_review": bool(r.get("to_review"))})
            break
    order = {"changed": 0, "removed": 1, "new": 2}
    out.sort(key=lambda x: order.get(x["change"], 3))
    return out


def deliverables(rec, rows, lib, doc, version, volumes=()):
    """Deliverables this version affects: [{id, name, owner, why: [text], over}] and new suggestions [{key, subject}]."""
    import deliverables as D
    hits, sugg = [], []
    if rec is None:
        return hits, sugg
    byk = {r["key"]: r for r in rows}
    vid = version["id"]
    latest = doc["versions"][-1]["id"] == vid

    def changed_here(r):
        return r is not None and any(h.get("version_id") == vid and h["change"] in ("changed", "removed") for h in r.get("history", []))
    for d in D.items(rec):
        why = []
        st = D.state(d, rows, lib, volumes, rec)
        lr = D.limit_row(d, rows, volumes)
        if changed_here(lr):
            prev = next((h["value"] for h in reversed(lr["history"]) if h.get("version_id") != vid and h["value"]), "")
            why.append(f"Page limit {('was ' + prev + ', now ') if prev else 'now '}{lr['value'] or 'removed'}" +
                       (f"; our file is {st['pages']} pages" if st["pages"] is not None else ""))
        src = byk.get(d.get("req_key", ""))
        if changed_here(src):
            why.append(f"Its requirement changed: {src['value'] or 'no longer in the document'}")
        if d.get("doc_id") == doc["id"] and latest and d.get("form_version") != vid:
            why.append(f"New form version {version['label']}: fill it; the one you have stays for the record")
        if why:
            hits.append({"id": d["id"], "name": d["name"], "owner": d.get("owner", ""), "why": why, "over": st["over"]})
    for r in D.suggestions(rec, rows):
        hist = r.get("history") or []
        if hist and next((h for h in hist if h["change"] != "removed"), hist[0]).get("version_id") == vid:
            sugg.append({"key": r["key"], "subject": r["subject"]})
    return hits, sugg


def _item_index(items):
    import compliance as C
    idx = {}
    for it in items:
        idx.setdefault(C.text_key(it["text"]), it)
        if it.get("lead"):
            idx.setdefault(C.text_key(it["lead"] + " " + it["text"]), it)
    return idx


def compliance(matrix, rows_cmp, owner_of=None):
    """Matrix sentences this version touches: {"changed": [...], "removed": [...], "added": [...], "in_matrix": bool}.
    changed/removed: {id, map, owner, decision, old, new, diff}; added: {text, section, id, decision} (id empty when the
    sentence is not in the matrix yet)."""
    import compliance as C
    out = {"changed": [], "removed": [], "added": [], "in_matrix": False, "unmatched": 0}
    if matrix is None or not matrix.items:
        return out
    idx = _item_index(matrix.items)
    owner_of = owner_of or (lambda it: it.get("owner", ""))

    def row(it, r):
        return {"id": it.get("id", ""), "map": it.get("map", ""), "owner": owner_of(it), "decision": it.get("decision", ""),
                "old": r["old"], "new": r["new"], "diff": r.get("diff", []), "section": r.get("section", "")}
    for r in rows_cmp:
        if r["kind"] == "same":
            if C.text_key(r["new"]) in idx:
                out["in_matrix"] = True
            continue
        if r["kind"] in ("changed", "removed"):
            it = idx.get(C.text_key(r["old"])) or (idx.get(C.text_key(r["new"])) if r["new"] else None)
            if it is None:
                out["unmatched"] += 1
                continue
            out["in_matrix"] = True
            out[r["kind"]].append(row(it, r))
        else:
            it = idx.get(C.text_key(r["new"]))
            out["added"].append({"text": r["new"], "section": r.get("section", ""), "id": it.get("id", "") if it else "",
                                 "decision": it.get("decision", "") if it else "", "map": it.get("map", "") if it else "",
                                 "owner": owner_of(it) if it and it.get("map") else ""})
            if it is not None:
                out["in_matrix"] = True
    return out


def _caps_ratio(s):
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0


def terms(sents, common=()):
    """Capitalized terms (acronym-like) in a version's sentences, with counts. All-capital headings are skipped."""
    c = collections.Counter()
    for s in sents:
        x = s["x"] if isinstance(s, dict) else s
        if _caps_ratio(x) > 0.6:
            continue
        for m in ACR.finditer(x):
            t = m.group(1)
            if t in SKIP or ROMAN.match(t) or sum(ch.isalpha() for ch in t) < 2 or (t.lower() in common and len(t) > 3):
                continue
            c[t] += 1
    return c


def acronyms(old_sents, new_sents, in_list=lambda t: False, in_master=lambda t: False, common=()):
    """{"new": [{term, count, in_list, in_master}], "gone": [{term, in_list}]}."""
    a, b = terms(old_sents, common), terms(new_sents, common)
    new = [{"term": t, "count": n, "in_list": bool(in_list(t)), "in_master": bool(in_master(t))}
           for t, n in sorted(b.items(), key=lambda x: (-x[1], x[0])) if t not in a]
    gone = [{"term": t, "in_list": bool(in_list(t))} for t in sorted(a) if t not in b]
    return {"new": new, "gone": gone}


def _heads(sents):
    out = {}
    for s in sents:
        n, t = (s.get("s") or "").strip(), " ".join((s.get("t") or "").split())
        if n and n not in out:
            out[n] = t
    return out


def structure(old_sents, new_sents, outline=()):
    """RFP headings renamed, added or removed: [{num, change, was, now, ours}] where ours names our response section
    titled like the old heading (rename it to match?)."""
    import compliance as C
    a, b = _heads(old_sents), _heads(new_sents)
    titles = {(o.get("title") or "").casefold(): C.outline_label(o) for o in outline}
    out = []
    for n, t in b.items():
        if n in a:
            if a[n] and t and a[n].casefold() != t.casefold():
                out.append({"num": n, "change": "renamed", "was": a[n], "now": t, "ours": titles.get(a[n].casefold(), "")})
        else:
            out.append({"num": n, "change": "added", "was": "", "now": t, "ours": ""})
    for n, t in a.items():
        if n not in b:
            out.append({"num": n, "change": "removed", "was": t, "now": "", "ours": titles.get(t.casefold(), "") if t else ""})
    out.sort(key=lambda x: C.sec_key(x["num"]))
    return out


def keywords(old_sents, new_sents, rows_cmp, have=(), limit=6):
    """Customer phrases new in this version (not in the version before), used at least twice: [{phrase, count}]."""
    import keywords as K
    def count(sents):
        c = collections.Counter()
        surf = {}
        for s in sents:
            for key, surface, _at in K.phrases(s["x"] if isinstance(s, dict) else s):
                c[key] += 1
                surf.setdefault(key, surface)
        return c, surf
    a, _ = count(old_sents)
    b, surf = count(new_sents)
    touched, _ = count([r["new"] for r in rows_cmp if r["kind"] in ("changed", "added")])
    have = {h.casefold() for h in have}
    cand = [(k, n) for k, n in b.items() if n >= 2 and k not in a and k in touched and not any(k in h for h in have)]
    cand.sort(key=lambda x: (-x[1], -len(x[0].split()), x[0]))
    full = " ".join(re.sub(r"\W+", " ", (s["x"] if isinstance(s, dict) else s).lower()) for s in new_sents)
    out = []                                     # [[key, surface, count]]
    for k, n in cand:
        if any(k in o[0] for o in out):          # inside a longer phrase already kept
            continue
        merged = False
        for o in out:                            # overlapping pieces of one longer phrase: join them when it is used as often
            for a, b, sa, sb in ((o[0], k, o[1], surf[k]), (k, o[0], surf[k], o[1])):
                aw, bw = a.split(), b.split()
                for m in range(min(len(aw), len(bw)) - 1, 0, -1):
                    if aw[-m:] == bw[:m]:
                        key = " ".join(aw + bw[m:])
                        if full.count(" " + key + " ") + full.startswith(key + " ") >= min(n, o[2]):
                            o[0], o[1], o[2] = key, " ".join(sa.split() + sb.split()[m:]), min(n, o[2])
                            merged = True
                        break
                if merged:
                    break
            if merged:
                break
        if not merged:
            out.append([k, surf[k], n])
        if len(out) >= limit:
            break
    return [{"phrase": s, "count": n} for k, s, n in out if k not in have]


# ------------------------------------------------------------------ the review
def build(lib, vid, rows=(), rec=None, matrix=None, owner_of=None, in_list=lambda t: False, in_master=lambda t: False,
          common=(), keyword_list=(), volumes=()):
    """The impact review of one version. Returns None when the version is unknown or has no version before it."""
    doc, v, prev = find_version(lib, vid)
    if v is None or prev is None:
        return None
    old, new = lib.text(prev), lib.text(v)
    cmp_rows = DV.compare(old, new)
    dl, sugg = deliverables(rec, rows, lib, doc, v, volumes)
    out = {"doc": doc["name"], "doc_id": doc["id"], "version": v["label"], "version_id": v["id"], "prev": prev["label"],
           "prev_id": prev["id"], "file": v.get("file", ""), "added": v.get("added", ""), "who": v.get("who", ""),
           "sha256": v.get("sha256", ""), "reviewed": v.get("reviewed", ""), "text": DV.summary(cmp_rows), "rows": cmp_rows,
           "requirements": requirements(rows, vid), "deliverables": dl, "suggested": sugg,
           "compliance": compliance(matrix, cmp_rows, owner_of),
           "acronyms": acronyms(old, new, in_list, in_master, common),
           "structure": structure(old, new, matrix.outline if matrix is not None else ()),
           "keywords": keywords(old, new, cmp_rows, keyword_list)}
    out["people"] = people(out, matrix, owner_of)
    out["counts"] = counts(out)
    return out


def people(r, matrix=None, owner_of=None):
    """{person: [what touches them]}: the same people the author briefs go to (2.43.0): owners, leads and contributors
    of the sections touched, and deliverable owners."""
    import briefs as BR
    people_of = None
    if matrix is not None:
        import setupdoc
        people_of = lambda label: setupdoc.section_people(matrix, label)        # noqa: E731
    out = {}
    for name, b in BR.build(r, matrix, owner_of, people_of).items():
        if name == BR.EVERYONE:
            continue
        out[name] = [f"{label}: {x}" for label, xs in b["sections"].items() for x in xs] + list(b["deliverables"])
    return out


def counts(r):
    c = r["compliance"]
    return {"requirements": len(r["requirements"]), "deliverables": len(r["deliverables"]) + len(r["suggested"]),
            "compliance": len(c["changed"]) + len(c["removed"]) + sum(1 for a in c["added"] if not a["decision"]),
            "acronyms": len(r["acronyms"]["new"]) + len(r["acronyms"]["gone"]), "structure": len(r["structure"]),
            "keywords": len(r["keywords"]), "people": len(r["people"])}


def headline(r):
    """One line: 'Amendment 3 of RFP: 14 changed, 5 added, 2 removed; 3 requirements, 2 deliverables, 6 compliance'."""
    c = r["counts"]
    parts = [f"{c[k]} {lab}" for k, lab in (("requirements", "submission requirement(s)"), ("deliverables", "deliverable(s)"),
                                           ("compliance", "compliance sentence(s)"), ("structure", "heading(s)"),
                                           ("acronyms", "acronym(s)"), ("keywords", "phrase(s)")) if c[k]]
    t = r["text"]
    return (f"{r['version']} of {r['doc']}: {t['changed']} changed, {t['added']} added, {t['removed']} removed" +
            (f". It touches {', '.join(parts)}" if parts else ". It touches nothing else in the effort") +
            (f"; {c['people']} owner(s)." if c["people"] else "."))


# ------------------------------------------------------------------ export (Word)
def export_word(path, r, effort_name=""):
    import docxw
    d = docxw.Doc()
    GRAY, INK, AMBER = "64748B", "0F172A", "B45309"
    d.rich([(f"IMPACT REVIEW  |  {effort_name}" if effort_name else "IMPACT REVIEW", {"color": GRAY, "size": 18, "bold": True})])
    d.rich([(f"{r['version']} of {r['doc']}", {"bold": True, "size": 36, "color": INK})])
    d.rich([(f"Compared with {r['prev']}. File {r['file']}, added {r['added'].replace('T', ' ')} by {r['who']}. "
             f"Fingerprint (SHA-256) {DV.short_sha(r['sha256'])}.", {"color": GRAY, "size": 18})])
    d.para(headline(r))
    if r["reviewed"]:
        d.rich([(f"Impact reviewed {r['reviewed']}.", {"color": "15803D", "bold": True})])
    if r["requirements"]:
        d.heading("Submission requirements", 2)
        d.table(["Requirement", "Change", "Was", "Now"],
                [[f"{x['kind']}, {x['subject']}", x["change"], x["was"], x["now"]] for x in r["requirements"]], [2800, 1100, 2700, 2760])
    if r["deliverables"] or r["suggested"]:
        d.heading("Deliverables", 2)
        if r["deliverables"]:
            d.table(["Deliverable", "Owner", "What changed"], [[x["name"], x["owner"] or "nobody yet", "; ".join(x["why"])]
                                                               for x in r["deliverables"]], [2600, 1600, 5160])
        if r["suggested"]:
            d.rich([("Named for the first time, not added yet: ", {"bold": True, "color": AMBER}),
                    (", ".join(x["subject"] for x in r["suggested"]), {})])
    c = r["compliance"]
    if c["changed"] or c["removed"] or c["added"]:
        d.heading("Compliance", 2)
        rows = [[x["id"], "Changed", x["map"] or "not placed", x["owner"], x["new"]] for x in c["changed"]] + \
               [[x["id"], "Removed", x["map"] or "not placed", x["owner"], x["old"]] for x in c["removed"]] + \
               [[x["id"] or "", "Added" + ("" if x["decision"] else ", not assigned"), x["section"], "", x["text"]] for x in c["added"]]
        d.table(["ID", "Change", "Our section", "Owner", "Sentence"], rows, [1100, 1300, 1900, 1300, 3760])
    if r["structure"]:
        d.heading("RFP headings", 2)
        d.table(["Heading", "Change", "Was", "Now", "Our section like it"],
                [[x["num"], x["change"], x["was"], x["now"], x["ours"]] for x in r["structure"]], [1100, 1100, 2400, 2400, 2360])
    a = r["acronyms"]
    if a["new"] or a["gone"]:
        d.heading("Acronyms", 2)
        if a["new"]:
            d.para("New in this version: " + ", ".join(x["term"] + (" (in the effort list)" if x["in_list"] else " (in the master database)"
                                                                     if x["in_master"] else "") for x in a["new"]))
        if a["gone"]:
            d.para("No longer in this document: " + ", ".join(x["term"] for x in a["gone"]))
    if r["keywords"]:
        d.heading("Keywords", 2)
        d.para("New customer phrases: " + ", ".join(f"{x['phrase']} ({x['count']})" for x in r["keywords"]))
    if r["people"]:
        d.heading("Who it touches", 2)
        d.table(["Owner", "What"], [[o, "; ".join(w)] for o, w in r["people"].items()], [2200, 7160])
    d.rich([("Made by Acronym Hunter on this PC. Rules only, no AI. It holds customer content: share it the way you share "
             "the proposal.", {"color": GRAY, "size": 16})])
    d.save(path)
    return path
