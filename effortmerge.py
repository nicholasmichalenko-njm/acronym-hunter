"""Merge another copy of an effort into this one (3.70.0; claude/stationkeeper-archive-merge-decisions-2026-11-06.md).
Two people can work on parts of the same effort, on one PC or two, and bring the work together. The source is only read:
another effort on this PC (archived ones too), an effort's folder, or an effort package (.skpkg, unpacked to a
temporary folder).

What merges, and how:
  documents  every customer document version, matched by content (sha256); a changed file is a new version of the same
             document; the files are copied into this effort's folders.
  acronyms   a new term is added; the same term with the same meaning fills empty fields, joins Found in, Used in
             volumes and Alt forms, and keeps the stronger status (Approved over Needs author over Proposed); the same
             term with another meaning keeps ours, adds theirs to Other definitions and is listed for review. Keywords
             are joined by keyword.
  files      the Volumes and Response Setup folders: an identical file is skipped; a different file with the same name
             is kept beside ours as "<name> (from <source>)".
  record     the effort record: items matched by id, then by name or title; new items added with their references
             rewritten to ours where we matched them; an item changed on both sides keeps ours and is listed for review
             with theirs beside it; the timeline joined in time order; dictionaries joined key by key; stages, the due
             date and other single values stay ours (theirs fills one we left empty).

resolve(registry, source) -> {"list", "data", "name", "root", "temp"}   (source: an effort name, a folder or a .skpkg)
merge(registry, target, source, parts=PARTS, who=None) -> report        review items kept in rec.data["merge_review"]
Rules only; nothing leaves the PC; nothing in the source is changed and nothing in this effort is deleted."""
import copy, datetime, hashlib, os, shutil, tempfile

PARTS = ("documents", "acronyms", "files", "record")
PART_NAMES = {"documents": "Customer documents", "acronyms": "Acronyms and keywords", "files": "Volumes and drafts",
              "record": "Topics, notes, deliverables, tasks and the rest of the record"}
STRENGTH = {"Approved": 3, "Needs author": 2, "Proposed": 1, "Rejected": 0, "": -1}
JOIN_FIELDS = ("Found in", "Used in volumes", "Alt forms")
RECORD_KEEP = {"v", "stages", "stage", "merge_review"}            # ours always
NAME_KEYS = ("name", "title", "text", "question", "term", "label")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- the source
def resolve(registry, source):
    """Where the source effort's files are. An effort package is unpacked into a temporary folder ("temp" is set; the
    caller removes it with cleanup)."""
    import effortrelink as ER
    import workspace as W
    info = registry.get(source) if isinstance(source, str) else None
    if info and info.get("path"):
        lst = info["path"]
        return {"list": lst, "data": W.data_dir_for(lst), "name": source, "root": os.path.dirname(lst), "temp": ""}
    if isinstance(source, str) and source.lower().endswith((".skpkg", ".ahpkg")) and os.path.isfile(source):
        import effortpkg as P
        tmp = tempfile.mkdtemp(prefix="sk_merge_")
        got = P.unpack(source, os.path.join(tmp, "effort"), W.data_dir_for)
        P.repoint(got["data"], got["customer_dir"], got["matrix"], got.get("moved"))
        return {"list": got["list"], "data": got["data"], "name": got["manifest"].get("effort") or "package",
                "root": os.path.dirname(got["list"]), "temp": tmp}
    lst = ER.find_list(source) if isinstance(source, str) else ""
    if lst:
        rl = ER.relink(lst)
        return {"list": lst, "data": W.data_dir_for(lst), "name": rl["name"], "root": os.path.dirname(lst), "temp": ""}
    return None


def cleanup(src):
    if src and src.get("temp"):
        shutil.rmtree(src["temp"], ignore_errors=True)


# ---------------------------------------------------------------- documents
def merge_documents(src, dst_info, who=None):
    import docintake as DI
    import docversions as DV
    import effortfolders as EF
    import workspace as W
    sl = DV.Library(os.path.join(src["data"], "documents")).load()
    dl = DV.Library(os.path.join(W.data_dir_for(dst_info["path"]), "documents")).load()
    cust = dst_info.get("customer_dir") or EF.folder(dst_info["path"], "customer")
    n = {"documents": 0, "versions": 0, "same": 0}
    for d in sl.all:
        made = next((x for x in dl.all if x.get("name") == d.get("name") and x.get("category", "customer") == d.get("category", "customer")), None)
        for v in d["versions"]:
            p = sl.path_of(v)
            if not p or not os.path.isfile(p):
                continue
            have = next((x for x in dl.all for y in x["versions"] if y.get("sha256") == v.get("sha256")), None)
            if have is not None:
                made = made or have
                n["same"] += 1
                continue
            cat = d.get("category", "customer")
            folder = cust if cat == "customer" else DI.library_dir(dl, cat, d.get("folder", ""))
            os.makedirs(folder, exist_ok=True)
            tp = os.path.join(folder, v.get("file") or os.path.basename(p))
            if os.path.exists(tp) and _sha(tp) != v.get("sha256"):
                stem, ext = os.path.splitext(tp)
                tp = f"{stem} ({v.get('label') or 'v'}, from {src['name']}){ext}"
            if not os.path.exists(tp):
                shutil.copy2(p, tp)
            doc, _ver = dl.add(tp, sl.text(v), doc_id=made["id"] if made else None, doc_name=d["name"], label=v.get("label", ""),
                               sha=v.get("sha256"), who=who, initial=d.get("initial", ""), dtype=d.get("type", ""), category=cat,
                               folder=d.get("folder", ""), tags=d.get("tags", []), role=d.get("role"), save=False,
                               role_confirmed=not (d.get("role_by") or {}).get("suggested"))
            if made is None:
                n["documents"] += 1
            made = doc
            n["versions"] += 1
    dl.save()
    return n


# ---------------------------------------------------------------- acronyms and keywords
def _norm(s):
    return " ".join(str(s or "").split()).casefold()


def _join(a, b, sep="; "):
    parts = [x.strip() for x in str(a or "").replace(",", ";").split(";") if x.strip()]
    for x in str(b or "").replace(",", ";").split(";"):
        if x.strip() and x.strip().casefold() not in (p.casefold() for p in parts):
            parts.append(x.strip())
    return sep.join(parts)


def merge_acronyms(src, dst_info, target):
    import effort as E
    S = E.EffortList(src["list"]).load()
    T = E.EffortList(dst_info["path"], target).load()
    n = {"added": 0, "filled": 0, "same": 0, "review": []}
    for t in S.order:
        theirs = S.rows[t]
        ours = T.rows.get(t)
        if ours is None:
            T.add_or_update(t, change_note=f"merged from {src['name']}", **{k: v for k, v in theirs.items() if k != "Term"})
            n["added"] += 1
            continue
        if _norm(ours.get("Definition")) and _norm(theirs.get("Definition")) and _norm(ours.get("Definition")) != _norm(theirs.get("Definition")):
            other = _join(ours.get("Other definitions"), theirs.get("Definition"))
            if other != (ours.get("Other definitions") or ""):
                T.add_or_update(t, change_note=f"another meaning from {src['name']}", **{"Other definitions": other})
            n["review"].append({"part": "Acronyms", "item": t, "ours": ours.get("Definition", ""), "theirs": theirs.get("Definition", ""),
                                "why": "Two meanings: ours kept, theirs added to Other definitions"})
            continue
        fields = {}
        for k, v in theirs.items():
            if k == "Term" or v in (None, ""):
                continue
            if k in JOIN_FIELDS:
                j = _join(ours.get(k), v)
                if j != (ours.get(k) or ""):
                    fields[k] = j
            elif k == "Status":
                if STRENGTH.get(v, -1) > STRENGTH.get(ours.get("Status", ""), -1):
                    fields["Status"] = v
                    for k2 in ("Approver", "Approved on"):
                        if theirs.get(k2):
                            fields[k2] = theirs[k2]
            elif ours.get(k) in (None, ""):
                fields[k] = v
        if fields:
            T.add_or_update(t, change_note=f"filled from {src['name']}", **fields)
            n["filled"] += 1
        else:
            n["same"] += 1
    have = {_norm(k.get("Keyword")) for k in T.keywords}
    for k in S.keywords:
        if _norm(k.get("Keyword")) and _norm(k.get("Keyword")) not in have:
            T.keywords.append(dict(k)); have.add(_norm(k.get("Keyword")))
            n["added"] += 1
    if n["added"] or n["filled"] or n["review"]:
        T.pending = True
        T.save()
    return n


# ---------------------------------------------------------------- volumes and drafts
def merge_files(src, dst_info):
    import effortfolders as EF
    n = {"copied": 0, "same": 0, "beside": 0}
    for kind in ("volumes", "setup"):
        sdir = EF.folder(src["list"], kind, make=False)
        if not sdir or not os.path.isdir(sdir):
            continue
        ddir = EF.folder(dst_info["path"], kind)
        for d, _subs, files in os.walk(sdir):
            for f in files:
                if f.startswith("~$"):
                    continue                              # Word's lock files
                sp = os.path.join(d, f)
                tp = os.path.join(ddir, os.path.relpath(sp, sdir))
                os.makedirs(os.path.dirname(tp), exist_ok=True)
                if not os.path.exists(tp):
                    shutil.copy2(sp, tp); n["copied"] += 1
                elif _sha(tp) == _sha(sp):
                    n["same"] += 1
                else:
                    stem, ext = os.path.splitext(tp)
                    alt = f"{stem} (from {src['name']}){ext}"
                    if not os.path.exists(alt) or _sha(alt) != _sha(sp):
                        shutil.copy2(sp, alt); n["beside"] += 1
                    else:
                        n["same"] += 1
    return n


# ---------------------------------------------------------------- the record
def _label(it):
    return next((str(it[k]) for k in NAME_KEYS if isinstance(it, dict) and it.get(k)), "")


def _remap(obj, ids):
    """Their references to items we matched, rewritten to our ids."""
    if isinstance(obj, dict):
        return {ids.get(k, k) if isinstance(k, str) else k: _remap(v, ids) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_remap(x, ids) for x in obj]
    if isinstance(obj, str):
        return ids.get(obj, obj)
    return obj


def _match_ids(ours, theirs):
    """{their id: our id} for list items matched by name or title when their ids differ."""
    out = {}
    for key, tl in theirs.items():
        ol = ours.get(key)
        if not (isinstance(tl, list) and isinstance(ol, list)):
            continue
        oid = {x.get("id") for x in ol if isinstance(x, dict)}
        byname = {(_norm(_label(x))): x.get("id") for x in ol if isinstance(x, dict) and x.get("id") and _label(x)}
        for x in tl:
            if isinstance(x, dict) and x.get("id") and x["id"] not in oid:
                hit = byname.get(_norm(_label(x)))
                if hit:
                    out[x["id"]] = hit
    return out


def merge_record(src, dst_data, who=None):
    import effortrec as R
    import workspace as W
    theirs = W.read_json(os.path.join(src["data"], "record.json"), None) or {}
    rec = R.Record(dst_data)
    ours = rec.data
    ids = _match_ids(ours, theirs)
    theirs = _remap(theirs, ids)
    n = {"added": 0, "same": 0, "review": []}
    for key, tv in theirs.items():
        if key in RECORD_KEEP:
            continue
        ov = ours.get(key)
        if ov in (None, "", [], {}):
            if tv not in (None, "", [], {}):
                ours[key] = copy.deepcopy(tv)
                n["added"] += len(tv) if isinstance(tv, (list, dict)) else 1
            continue
        if isinstance(tv, list) and isinstance(ov, list):
            if key == "timeline":
                seen = {(e.get("at"), e.get("kind"), e.get("text")) for e in ov if isinstance(e, dict)}
                new = [e for e in tv if isinstance(e, dict) and (e.get("at"), e.get("kind"), e.get("text")) not in seen]
                ours[key] = sorted(ov + new, key=lambda e: str(e.get("at", "")))
                n["added"] += len(new)
                continue
            by = {x.get("id"): x for x in ov if isinstance(x, dict) and x.get("id")}
            for x in tv:
                if isinstance(x, dict) and x.get("id"):
                    o = by.get(x["id"])
                    if o is None:
                        ov.append(copy.deepcopy(x)); n["added"] += 1
                    elif o == x:
                        n["same"] += 1
                    else:
                        n["review"].append({"part": key.replace("_", " ").capitalize(), "item": _label(o) or x["id"],
                                            "ours": _brief(o), "theirs": _brief(x), "why": "Changed in both copies: ours kept"})
                elif x not in ov:
                    ov.append(copy.deepcopy(x)); n["added"] += 1
                else:
                    n["same"] += 1
            continue
        if isinstance(tv, dict) and isinstance(ov, dict):
            for k, v in tv.items():
                if k not in ov or ov[k] in (None, "", [], {}):
                    ov[k] = copy.deepcopy(v); n["added"] += 1
                elif isinstance(ov[k], list) and isinstance(v, list) and all(not isinstance(a, dict) for a in v):
                    extra = [a for a in v if a not in ov[k]]
                    ov[k] = ov[k] + extra
                    n["added" if extra else "same"] += 1
                elif ov[k] == v:
                    n["same"] += 1
                else:
                    n["review"].append({"part": key.replace("_", " ").capitalize(), "item": str(k), "ours": _brief(ov[k]),
                                        "theirs": _brief(v), "why": "Different in each copy: ours kept"})
            continue
        if ov != tv:
            n["review"].append({"part": key.replace("_", " ").capitalize(), "item": key, "ours": _brief(ov), "theirs": _brief(tv),
                                "why": "Different in each copy: ours kept"})
        else:
            n["same"] += 1
    rec.save()
    return n


def _brief(v, k=160):
    import json
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= k else s[:k - 3] + "..."


# ---------------------------------------------------------------- all of it
def merge(registry, target, source, parts=PARTS, who=None):
    """Merges the chosen parts of source into the effort named target. Returns {"source", part: counts, "review": [...]}."""
    import effortrec as R
    import workspace as W
    dst = registry.get(target) or {}
    if not dst.get("path"):
        return {"ok": False, "why": "The effort to merge into is not on this PC."}
    src = resolve(registry, source)
    if src is None:
        return {"ok": False, "why": "No effort was found there."}
    try:
        if os.path.normcase(os.path.abspath(src["list"])) == os.path.normcase(os.path.abspath(dst["path"])):
            return {"ok": False, "why": "That is this effort."}
        out = {"ok": True, "source": src["name"], "review": []}
        if "documents" in parts:
            out["documents"] = merge_documents(src, dst, who)
        if "acronyms" in parts:
            out["acronyms"] = merge_acronyms(src, dst, target)
            out["review"] += out["acronyms"].pop("review")
        if "files" in parts:
            out["files"] = merge_files(src, dst)
        ddata = W.data_dir_for(dst["path"])
        if "record" in parts:
            out["record"] = merge_record(src, ddata, who)
            out["review"] += out["record"].pop("review")
        rec = R.Record(ddata)
        when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        rec.data.setdefault("merge_review", []).extend(dict(r, source=src["name"], when=when) for r in out["review"])
        rec.log("effort", f"Merged from {src['name']}: " + summary(out), who=who)
        rec.save()
        return out
    finally:
        cleanup(src)


def summary(out):
    """One line: what was added, what was the same, what needs review."""
    bits = []
    d = out.get("documents")
    if d:
        bits.append(f"{d['documents']} new document(s), {d['versions']} new version(s)")
    a = out.get("acronyms")
    if a:
        bits.append(f"{a['added']} new term(s) or keyword(s), {a['filled']} term(s) filled in")
    f = out.get("files")
    if f:
        bits.append(f"{f['copied']} file(s) copied" + (f", {f['beside']} kept beside ours" if f["beside"] else ""))
    r = out.get("record")
    if r:
        bits.append(f"{r['added']} record item(s) added")
    bits.append(f"{len(out.get('review') or [])} to review")
    return "; ".join(bits)
