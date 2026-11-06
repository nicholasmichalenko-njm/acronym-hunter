"""Outline and matrix versions (3.73.0, claude/stationkeeper-versions-decisions-2026-11-06.md).

Each outline workbook brought in is a version, kept with the effort and dated (v1, v2, v3): a copy of the file, what it
held row by row, and which items in the effort each row made. A new version is compared before anything changes: rows
matched by RFP reference first, then by wording (a reworded requirement still matches); sections by title, then by
number (a renumbered section is not a removed one). Each difference is one change: Added, Removed, Changed (wording,
reference, guidance, customer text, supporting text), Moved (to another section), Renumbered and Renamed (a section),
Section added, Section removed, Authors changed.

Work done in the app is protected: a row placed, edited or noted in the app that the new version also changes is
"Changed in both" and waits for the person's pick (ours or theirs); nothing is overwritten until then. An app edit the
new version does not touch stays. accept() brings the version in: matched rows keep their ids (so Changes for authors
sees what really changed), labels follow renumbered and renamed sections, and the new version is recorded.
Rules only; nothing leaves the PC."""
import copy, datetime, difflib, os, re, shutil
from collections import Counter

KEY = "outline_versions"
MATCH = 0.75
SAME_TEXT = 0.95                    # a row whose RFP reference changed: matched only when its words are nearly the same
FIELDS = (("req", "wording"), ("ref", "reference"), ("guidance", "guidance"), ("customer", "customer text"), ("support", "supporting text"))


def _n(t):
    return " ".join(str(t or "").casefold().split())


def _label(num, title):
    return f"{num} {title}".strip()


def rows_of(parsed):
    """One row per workbook row: {"row", "section", "num", "title", "ref", "req", "customer": [], "support": [], "guidance"}."""
    out = []
    for s in parsed["sections"]:
        lab, by = _label(s["num"], s["title"]), {}
        for b in s["blocks"]:
            r = by.get(b["row"])
            if r is None:
                r = by[b["row"]] = {"row": b["row"], "section": lab, "num": s["num"], "title": s["title"], "ref": "", "req": "",
                                    "customer": [], "support": [], "guidance": ""}
                out.append(r)
            if b["kind"] == "rfp":
                r["req"], r["ref"] = b["text"], b["ref"]
            elif b["kind"] in ("customer", "support"):
                r[b["kind"]].append(b["text"])
            elif b["kind"] == "pm":
                r["guidance"] = (r["guidance"] + "\n" + b["text"]).strip()
    return out


def sections_of(parsed):
    return [{"num": s["num"], "title": s["title"], "level": s["level"], "authors": list(s.get("authors") or [])} for s in parsed["sections"]]


# ------------------------------------------------------------------ matching
def match_sections(old, new):
    """{old index: new index}: by title first, then by number."""
    m, used = {}, set()
    for i, o in enumerate(old):
        j = next((j for j, s in enumerate(new) if j not in used and _n(s["title"]) == _n(o["title"])), None)
        if j is None and o["num"]:
            j = next((j for j, s in enumerate(new) if j not in used and s["num"] == o["num"]), None)
        if j is not None:
            m[i] = j; used.add(j)
    return m


def match_rows(old, new, smap_labels):
    """{old index: new index}: by RFP reference (one each side), then by wording (rows with two different references only
    when nearly word for word: a renumbered RFP paragraph), then a row without a requirement by its section and its other
    text."""
    pairs, used = {}, set()
    oc, nc = Counter(r["ref"] for r in old if r["ref"]), Counter(r["ref"] for r in new if r["ref"])
    for i, o in enumerate(old):
        if o["ref"] and oc[o["ref"]] == 1 and nc[o["ref"]] == 1:
            j = next(j for j, r in enumerate(new) if r["ref"] == o["ref"])
            pairs[i] = j; used.add(j)

    def greedy(cands):
        for _r, i, j in sorted(cands, reverse=True):
            if i not in pairs and j not in used:
                pairs[i] = j; used.add(j)
    def need(o, r):                                     # two different references: the same row only when nearly word for word
        return SAME_TEXT if o["ref"] and r["ref"] and o["ref"] != r["ref"] else MATCH
    greedy([(rt, i, j) for i, o in enumerate(old) if i not in pairs and o["req"] for j, r in enumerate(new) if j not in used and r["req"]
            for rt in [difflib.SequenceMatcher(None, _n(o["req"]), _n(r["req"])).ratio()] if rt >= need(o, r)])
    rest = lambda r: _n(" ".join([r["guidance"]] + r["customer"] + r["support"]))
    greedy([(difflib.SequenceMatcher(None, rest(o), rest(r)).ratio(), i, j)
            for i, o in enumerate(old) if i not in pairs and not o["req"] for j, r in enumerate(new)
            if j not in used and not r["req"] and smap_labels.get(o["section"]) == r["section"]
            and difflib.SequenceMatcher(None, rest(o), rest(r)).ratio() >= MATCH])
    return pairs


# ------------------------------------------------------------------ the versions kept
def versions(M):
    import setupdoc as SD
    return list((SD.setup_of(M).get(KEY) or {}).get("versions") or [])


def current(M):
    v = versions(M)
    return v[-1] if v else None


def source(M, file_name=""):
    """The name the outline's items carry (the first version's file), so a later version replaces them."""
    import setupdoc as SD
    return (SD.setup_of(M).get(KEY) or {}).get("source") or file_name


def _ids_by_row(M, src):
    out = {}
    for it in M.items:
        if it.get("src") == "outline" and it.get("file") == src and str(it.get("loc", "")).startswith("Row "):
            r = int(it["loc"][4:])
            d = out.setdefault(r, {"req": "", "customer": [], "support": []})
            if it.get("decision") == "Keep":
                d["req"] = it["id"]
            elif it.get("decision") == "Customer":
                d["customer"].append(it["id"])
            elif it.get("decision") == "Context":
                d["support"].append(it["id"])
    return out


def record(M, parsed, path, effort_path="", headers=None, layout=""):
    """The version just brought in: a copy of its file kept with the effort, and what it held with the ids it made."""
    import setupdoc as SD
    S = SD.setup_of(M)
    V = S.setdefault(KEY, {"source": os.path.basename(path), "versions": []})
    src = V["source"]
    n = len(V["versions"]) + 1
    kept = ""
    if effort_path and path and os.path.isfile(path):
        import effortfolders as EF
        folder = os.path.join(EF.root(effort_path), "Outline Versions")
        os.makedirs(folder, exist_ok=True)
        stem, ext = os.path.splitext(os.path.basename(path))
        kept = os.path.join(folder, f"{stem} v{n}{ext}")
        if os.path.abspath(kept) != os.path.abspath(path):
            shutil.copyfile(path, kept)
        kept = os.path.relpath(kept, EF.root(effort_path)).replace(os.sep, "/")
    ids = _ids_by_row(M, src)
    rows = rows_of(parsed)
    for r in rows:
        r["ids"] = ids.get(r["row"], {"req": "", "customer": [], "support": []})
    secs = sections_of(parsed)
    mg = {}
    for s in parsed["sections"]:
        lab = _label(s["num"], s["title"])
        if S["mgmt"].get(lab):
            mg[lab] = S["mgmt"][lab]
    V["versions"].append({"v": n, "file": os.path.basename(path), "kept": kept, "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                          "headers": list(headers or []), "layout": layout, "sections": secs, "rows": rows, "mgmt": mg})
    SD._log(M, "(setup)", f"outline version {n} recorded")
    return V["versions"][-1]


# ------------------------------------------------------------------ comparing
def _app_state(M, row, lab_map):
    """What the effort holds now for an old row's requirement: {"req", "ref", "section", "guidance"} (None: no item)."""
    import setupdoc as SD
    iid = (row.get("ids") or {}).get("req")
    it = SD.by_id(M).get(iid) if iid else None
    if it is None:
        return None
    S = SD.setup_of(M)
    return {"req": it.get("text", ""), "ref": S["refs"].get(iid, ""), "section": it.get("map", ""), "guidance": S["notes"].get(iid, "")}


def compare(M, new_parsed, new_headers=None, old=None, new_record=None):
    """[change] between the current version and new_parsed: {"i", "kind", "what", "section", "old", "new", "both", "o", "n"}
    (o and n: the old and new row indexes, or None). new_record (version history): two kept versions, the app left out."""
    old = old or current(M)
    if old is None:
        return []
    if new_record is not None:
        new_rows, new_secs, new_headers = new_record["rows"], new_record["sections"], new_record.get("headers")
    else:
        new_rows, new_secs = rows_of(new_parsed), sections_of(new_parsed)
    smap = match_sections(old["sections"], new_secs)
    labs = {_label(old["sections"][i]["num"], old["sections"][i]["title"]): _label(new_secs[j]["num"], new_secs[j]["title"]) for i, j in smap.items()}
    out = []
    add = lambda **c: out.append(dict(c, i=len(out), both=c.get("both", False)))
    for i, o in enumerate(old["sections"]):
        if i not in smap:
            add(kind="Section removed", what="section", section=_label(o["num"], o["title"]), old=_label(o["num"], o["title"]), new="", o=None, n=None)
            continue
        s = new_secs[smap[i]]
        if s["num"] != o["num"]:
            add(kind="Renumbered", what="section", section=_label(s["num"], s["title"]), old=_label(o["num"], o["title"]), new=_label(s["num"], s["title"]), o=None, n=None)
        elif _n(s["title"]) != _n(o["title"]):
            add(kind="Renamed", what="section", section=_label(s["num"], s["title"]), old=o["title"], new=s["title"], o=None, n=None)
        if [_n(a) for a in s["authors"]] != [_n(a) for a in o["authors"]]:
            add(kind="Authors changed", what="authors", section=_label(s["num"], s["title"]), old=", ".join(o["authors"]), new=", ".join(s["authors"]), o=None, n=None)
    for j, s in enumerate(new_secs):
        if j not in smap.values():
            add(kind="Section added", what="section", section=_label(s["num"], s["title"]), old="", new=_label(s["num"], s["title"]), o=None, n=None)
    pairs = match_rows(old["rows"], new_rows, labs)
    import setupdoc as SD
    S = SD.setup_of(M) if new_record is None else {"mgmt": {}}
    for i, o in enumerate(old["rows"]):
        app = _app_state(M, o, labs) if new_record is None else None
        edited = set()
        if app is not None:
            edited = {k for k in ("req", "ref", "guidance") if _n(app[k]) != _n(o[k])}
            if app["section"] and app["section"] != labs.get(o["section"], o["section"]) and app["section"] != o["section"]:
                edited.add("section")
        elif new_record is None and not o["req"] and o["guidance"] and o["section"] in (old.get("mgmt") or {}):   # its direction
            if _n(S["mgmt"].get(labs.get(o["section"], o["section"]))) != _n(old["mgmt"][o["section"]]):
                edited.add("guidance")
                app = {"guidance": S["mgmt"].get(labs.get(o["section"], o["section"]), "")}
        if i not in pairs:
            add(kind="Removed", what="row", section=o["section"], old=o["req"] or o["guidance"] or " ".join(o["customer"] + o["support"]),
                new="", o=i, n=None, both=bool(edited))
            continue
        n = new_rows[pairs[i]]
        for f, words in FIELDS:
            a, b = o[f], n[f]
            if (_n(" ".join(a)) != _n(" ".join(b))) if isinstance(a, list) else (_n(a) != _n(b)):
                add(kind="Changed", what=words, field=f, section=n["section"], old=" ".join(a) if isinstance(a, list) else a,
                    new=" ".join(b) if isinstance(b, list) else b, o=i, n=pairs[i], both=f in edited,
                    ours=(app or {}).get(f, "") if f in edited else None)
        if labs.get(o["section"], o["section"]) != n["section"]:
            add(kind="Moved", what="section", field="section", section=n["section"], old=o["section"], new=n["section"], o=i, n=pairs[i],
                both="section" in edited, ours=(app or {}).get("section") if "section" in edited else None)
    for j, n in enumerate(new_rows):
        if j not in pairs.values():
            add(kind="Added", what="row", section=n["section"], old="", new=n["req"] or n["guidance"] or " ".join(n["customer"] + n["support"]), o=None, n=j)
    if new_headers is not None and old.get("headers"):
        import outlinelayouts as OL
        gone = [h for h in old["headers"] if h and OL.norm(h) not in {OL.norm(x) for x in new_headers}]
        came = [h for h in new_headers if h and OL.norm(h) not in {OL.norm(x) for x in old["headers"]}]
        for a, b in zip(gone, came):
            add(kind="Column renamed", what="column", section="", old=a, new=b, o=None, n=None)
    return out


def summary(changes):
    c = Counter(x["kind"] for x in changes)
    both = sum(1 for x in changes if x["both"])
    return ", ".join(f"{n} {k.lower()}" for k, n in c.items()) + (f"; {both} changed in both" if both else "") if changes else "No changes"


# ------------------------------------------------------------------ accepting a version
def _remap_ids(M, mapping):
    """Item ids renamed everywhere the setup keeps them."""
    import setupdoc as SD
    if not mapping:
        return
    S = SD.setup_of(M)
    for it in M.items:
        if it["id"] in mapping:
            it["id"] = mapping[it["id"]]
        if it.get("context_for") in mapping:
            it["context_for"] = mapping[it["context_for"]]
    for k in ("notes", "refs"):
        d = S.get(k) or {}
        moved = {a: d.pop(a) for a in list(d) if a in mapping}
        for a, v in moved.items():
            d[mapping[a]] = v
    for k in ("order", "copies"):
        for lab, lst in (S.get(k) or {}).items():
            S[k][lab] = [mapping.get(i, i) for i in lst]


def accept(M, new_parsed, path, picks=None, effort_path="", headers=None, layout="", who=None):
    """Bring the new version in. picks: {change index: "ours" or "theirs"}; every "Changed in both" needs one (a missing pick
    keeps ours: nothing is overwritten unasked). Returns {"changes", "version", "kept_ours"}."""
    import compliance as C
    import outline_ops as O
    import outlinexl as OX
    import setupdoc as SD
    picks = dict(picks or {})
    old = current(M)
    changes = compare(M, new_parsed, headers, old)
    ours = lambda c: picks.get(c["i"], "ours" if c["both"] else "theirs") == "ours"
    S = SD.setup_of(M)
    src = source(M, os.path.basename(path))
    new_rows, new_secs = rows_of(new_parsed), sections_of(new_parsed)
    smap = match_sections(old["sections"], new_secs)
    labs = {_label(old["sections"][i]["num"], old["sections"][i]["title"]): _label(new_secs[j]["num"], new_secs[j]["title"]) for i, j in smap.items()}
    pairs = match_rows(old["rows"], new_rows, labs)
    by = SD.by_id(M)
    saved = {i["id"]: copy.deepcopy(i) for i in M.items if i.get("src") == "outline" and i.get("file") == src}
    notes0, refs0 = dict(S["notes"]), dict(S["refs"])
    O.relabel(M, labs)                                           # placements, people and notes follow their sections
    app_mgmt = {}                                                # a section's direction written in the app
    for lab, txt in (old.get("mgmt") or {}).items():             # the direction the last version put in comes out first
        nl = labs.get(lab, lab)
        if _n(S["mgmt"].get(nl)) != _n(txt) and _n(S["mgmt"].get(nl)):
            app_mgmt[nl] = S["mgmt"][nl]
        S["mgmt"].pop(nl, None)
    for nl, txt in list(S["mgmt"].items()):                      # direction in a section the outline did not direct
        if nl in labs.values() and nl not in app_mgmt and _n(txt):
            app_mgmt[nl] = txt
            S["mgmt"].pop(nl, None)
    keep_req = {}                                                # old id -> {field: value} kept from the app
    for i, o in enumerate(old["rows"]):
        iid = (o.get("ids") or {}).get("req")
        if not iid or iid not in by:
            continue
        cur = {"req": saved.get(iid, by[iid]).get("text", ""), "ref": refs0.get(iid, ""), "guidance": notes0.get(iid, ""),
               "section": saved.get(iid, by[iid]).get("map", "")}
        cur["section"] = labs.get(cur["section"], cur["section"])
        mine = {}
        for f in ("req", "ref", "guidance"):
            if _n(cur[f]) != _n(o[f]):
                mine[f] = cur[f]                                 # edited in the app
        if cur["section"] and cur["section"] != labs.get(o["section"], o["section"]):
            mine["section"] = cur["section"]
        for c in changes:                                        # an app edit the new version leaves alone stays
            if c["o"] != i or c.get("field") not in cur:
                continue
            if ours(c):
                mine[c["field"]] = cur[c["field"]]               # ours: as the effort has it now
            else:
                mine.pop(c["field"], None)                       # theirs: the new version's value
        keep_req[iid] = {k: v for k, v in mine.items() if v is not None}
    OX.apply(M, new_parsed, src, who)
    # ---- ids: a matched row keeps its old ids; every other item gets an id no version has used
    new_by_row = _ids_by_row(M, src)
    old_ids = {x for r in old["rows"] for x in [(r.get("ids") or {}).get("req")] + list((r.get("ids") or {}).get("customer") or [])
               + list((r.get("ids") or {}).get("support") or []) if x}
    for v in versions(M):
        for r in v["rows"]:
            old_ids |= {x for x in [(r.get("ids") or {}).get("req")] + list((r.get("ids") or {}).get("customer") or []) + list((r.get("ids") or {}).get("support") or []) if x}
    tmp = {}
    for it in M.items:
        if it.get("src") == "outline" and it.get("file") == src:
            tmp[it["id"]] = f"~tmp~{len(tmp)}"
    _remap_ids(M, tmp)
    final, taken = {}, {it["id"] for it in M.items if not it["id"].startswith("~tmp~")} | old_ids
    for i, j in pairs.items():
        o_ids, n_ids = old["rows"][i].get("ids") or {}, new_by_row.get(new_rows[j]["row"]) or {}
        if o_ids.get("req") and n_ids.get("req"):
            final[tmp[n_ids["req"]]] = o_ids["req"]
        for k in ("customer", "support"):
            for a, b in zip(o_ids.get(k) or [], n_ids.get(k) or []):
                final[tmp[b]] = a
    stem = re.sub(r"[^A-Za-z0-9]+", "", os.path.splitext(src)[0])[:8] or "OUT"
    k = 1
    for t in tmp.values():
        if t in final:
            continue
        while f"OL{stem}-{k:03d}" in taken:
            k += 1
        final[t] = f"OL{stem}-{k:03d}"; taken.add(final[t])
    _remap_ids(M, final)
    # ---- what stays as the app had it
    by = SD.by_id(M)
    kept = 0
    for iid, mine in keep_req.items():
        it = by.get(iid)
        if it is None:
            continue
        if "req" in mine:
            it["text"] = mine["req"]; it["key"] = C.text_key(mine["req"])
        if "ref" in mine:
            S["refs"][iid] = mine["ref"]
        if "guidance" in mine:
            S["notes"][iid] = mine["guidance"]
        if "section" in mine and mine["section"] in SD.labels(M):
            SD.place(M, iid, mine["section"])
        kept += bool(mine)
    for c in changes:                                            # a removed row kept as ours comes back as it was
        if c["kind"] == "Removed" and ours(c):
            ids = old["rows"][c["o"]].get("ids") or {}
            for x in [ids.get("req")] + list(ids.get("customer") or []) + list(ids.get("support") or []):
                if x and x in saved and x not in by:
                    it = saved[x]; M.items.append(it)
                    if it.get("map") in SD.labels(M):
                        lab = it["map"]; it["map"] = ""; SD.place(M, x, lab)
                    if x in notes0:
                        S["notes"][x] = notes0[x]
                    if x in refs0:
                        S["refs"][x] = refs0[x]
            kept += 1
        elif c["kind"] == "Added" and ours(c):                   # an added row turned down
            ids = new_by_row.get(new_rows[c["n"]]["row"]) or {}
            gone = {final.get(tmp.get(x)) for x in [ids.get("req")] + list(ids.get("customer") or []) + list(ids.get("support") or []) if x}
            M.items = [it for it in M.items if it["id"] not in gone]
            for lab in S["order"]:
                S["order"][lab] = [x for x in S["order"][lab] if x not in gone]
    theirs = {c["section"] for c in changes if c.get("field") == "guidance" and c["o"] is not None
              and not old["rows"][c["o"]]["req"] and not ours(c)}
    for nl, txt in app_mgmt.items():                             # the section's direction written in the app stays, unless
        if nl not in theirs:                                     # the person took the new version's for it
            S["mgmt"][nl] = txt
    v = record(M, new_parsed, path, "", headers, layout)
    if effort_path:
        v.update(record_copy(M, path, effort_path, v["v"]))
    M.pending = True
    SD._log(M, "(setup)", f"outline version {v['v']} brought in: {summary(changes)}")
    return {"changes": changes, "version": v, "kept_ours": kept}


def record_copy(M, path, effort_path, n):
    import effortfolders as EF
    folder = os.path.join(EF.root(effort_path), "Outline Versions")
    os.makedirs(folder, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    kept = os.path.join(folder, f"{stem} v{n}{ext}")
    if os.path.abspath(kept) != os.path.abspath(path):
        shutil.copyfile(path, kept)
    return {"kept": os.path.relpath(kept, EF.root(effort_path)).replace(os.sep, "/")}
