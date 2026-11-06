"""The compliance matrix exported, edited in Excel, and brought back (3.73.0, claude/stationkeeper-versions-decisions-2026-11-06.md).

Each export of the matrix is a version, kept with the effort (Matrix Versions) with the design it was written in. A
workbook brought back is read through that design: its headings say which column is which; rows are matched to the
effort's rows, an outline item by its number and title, a sentence by its Stationkeeper ID when the design shows it,
else by its reference and wording. What the team fills in comes back: on an outline item, assigned to, initial page
allocation and % complete; on a sentence, owner, proposal page, compliance status, notes and the team's own columns.
Each difference is a change against the version exported (base), and against the effort now: a value changed in the
workbook and also in the app since the export is "Changed in both" and waits for a pick. Rows added or removed in the
workbook are listed, never applied: requirements come and go in the app. Rules only; nothing leaves the PC."""
import datetime, difflib, os, re, shutil

KEY = "matrix_versions"
ITEM_FIELDS = ("assigned_to", "page_alloc", "pct_complete")
SENT_FIELDS = ("authors", "owner", "page", "status", "notes")
WORDS = {"authors": "author(s)", "assigned_to": "assigned to", "page_alloc": "page allocation", "pct_complete": "% complete", "owner": "owner",
         "page": "proposal page", "status": "compliance status", "notes": "notes"}


def _n(t):
    return " ".join(str(t if t is not None else "").casefold().split())


def _label_of_item(v):
    return " ".join(str(v or "").split())


# ------------------------------------------------------------------ reading a matrix workbook through its design
def read(path, design):
    """{"layout", "rows": [{key: value}]}: the first sheet's table under the design's headings."""
    import matrixdesign as MD
    from openpyxl import load_workbook
    design = MD.clean(design)
    heads = {_n(c["heading"]): c["key"] for c in design["columns"]}
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Compliance Matrix"] if "Compliance Matrix" in wb.sheetnames else wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    hi = next((i for i, r in enumerate(rows[:30]) if sum(1 for c in r if _n(c) in heads) >= max(2, len(heads) // 2)), None)
    if hi is None:
        raise ValueError("The workbook's headings are not this matrix's design: export the matrix again, or pick the right workbook.")
    keys = [heads.get(_n(c)) for c in rows[hi]]
    out = []
    for r in rows[hi + 1:]:
        if not any(v not in (None, "") for v in r):
            continue
        out.append({k: ("" if v is None else v) for k, v in zip(keys, r) if k})
    return {"layout": design["layout"], "rows": out, "keys": [k for k in keys if k]}


def now_rows(M, design, ctx=None):
    """The effort's matrix as the design writes it now, as {key: value} rows, each with its "_map" and "_id"."""
    import matrixdesign as MD
    design = MD.clean(design)
    items, data = MD.rows(M, design, ctx)
    keys = [c["key"] for c in design["columns"]]
    out = []
    for it, vals in zip(items, data):
        r = {k: ("" if v is None else v) for k, v in zip(keys, vals)}
        r["_map"], r["_id"], r["_kind"] = it.get("map", ""), it.get("id", ""), it.get("_kind", "")
        out.append(r)
    return out


# ------------------------------------------------------------------ matching
def _key(row, layout, ref_of=None):
    if layout == "outline":
        if row.get("item"):
            return ("item", _n(row["item"]))
        return ("item", _n(" ".join(str(row.get(k, "")) for k in ("section_no", "section_name"))))
    if row.get("id"):
        return ("id", str(row["id"]).strip())
    return ("ref", _n(row.get("ref") or row.get("reference") or row.get("rfp_ref") or ""), _n(row.get("text", ""))[:200])


def match(a, b, layout):
    """{index in a: index in b}: by item label, ID, else by reference and wording."""
    pairs, used = {}, set()
    kb = {}
    for j, r in enumerate(b):
        kb.setdefault(_key(r, layout), []).append(j)
    for i, r in enumerate(a):
        for j in kb.get(_key(r, layout), []):
            if j not in used:
                pairs[i] = j; used.add(j)
                break
    if layout != "outline":
        cands = []
        for i, r in enumerate(a):
            if i in pairs or not r.get("text"):
                continue
            for j, s in enumerate(b):
                if j in used or not s.get("text"):
                    continue
                rt = difflib.SequenceMatcher(None, _n(r["text"]), _n(s["text"])).ratio()
                if rt >= 0.9:
                    cands.append((rt, i, j))
        for _rt, i, j in sorted(cands, reverse=True):
            if i not in pairs and j not in used:
                pairs[i] = j; used.add(j)
    return pairs


def _fields(layout, keys):
    base = ITEM_FIELDS if layout == "outline" else SENT_FIELDS
    import matrixdesign as MD
    return [k for k in keys if k in base or (layout != "outline" and k.startswith(MD.CUSTOM))]


# ------------------------------------------------------------------ versions kept with the effort
def versions(M):
    import setupdoc as SD
    return list((SD.setup_of(M).get(KEY) or {}).get("versions") or [])


def record(M, path, design, effort_path=""):
    """An export kept as a version: a copy with the effort and the design it was written in."""
    import setupdoc as SD
    import matrixdesign as MD
    S = SD.setup_of(M)
    V = S.setdefault(KEY, {"versions": []})
    n = len(V["versions"]) + 1
    kept = ""
    if effort_path and os.path.isfile(path):
        import effortfolders as EF
        folder = os.path.join(EF.root(effort_path), "Matrix Versions")
        os.makedirs(folder, exist_ok=True)
        stem, ext = os.path.splitext(os.path.basename(path))
        dst = os.path.join(folder, f"{stem} v{n}{ext}")
        shutil.copyfile(path, dst)
        kept = os.path.relpath(dst, EF.root(effort_path)).replace(os.sep, "/")
    V["versions"].append({"v": n, "file": os.path.basename(path), "kept": kept, "design": MD.clean(design),
                          "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    SD._log(M, "(setup)", f"matrix version {n} exported")
    return V["versions"][-1]


def _base_rows(M, effort_path):
    vs = versions(M)
    if not vs or not vs[-1].get("kept") or not effort_path:
        return None, None
    import effortfolders as EF
    p = os.path.join(EF.root(effort_path), *vs[-1]["kept"].split("/"))
    if not os.path.isfile(p):
        return None, vs[-1]
    return read(p, vs[-1]["design"]), vs[-1]


# ------------------------------------------------------------------ comparing and bringing back
def compare(M, path, design=None, effort_path="", ctx=None, merge=False):
    """[change] for a matrix workbook brought back: {"i", "kind", "what", "field", "row", "old", "new", "both", "label", "id"}.
    The design is the last export's (else the one given). merge: another copy's matrix: no base; a difference keeps ours
    unless the person takes theirs."""
    import matrixdesign as MD
    base, last = (None, None) if merge else _base_rows(M, effort_path)
    design = MD.clean((last or {}).get("design") or design or {})
    theirs = read(path, design)
    lay = design["layout"]
    ours = now_rows(M, design, ctx)
    fields = _fields(lay, theirs["keys"])
    t_o = match(theirs["rows"], ours, lay)
    t_b = match(theirs["rows"], base["rows"], lay) if base else {}
    out = []
    add = lambda **c: out.append(dict(c, i=len(out)))
    for i, t in enumerate(theirs["rows"]):
        j = t_o.get(i)
        if j is None:
            add(kind="Row added in the workbook", what="row", field=None, row=i, label=str(t.get("item") or t.get("text") or "")[:120],
                old="", new=str(t.get("item") or t.get("text") or "")[:200], both=False, id="", map="")
            continue
        o = ours[j]
        b = base["rows"][t_b[i]] if base and i in t_b else None
        for f in fields:
            tv, ov = t.get(f, ""), o.get(f, "")
            bv = b.get(f, "") if b is not None else ov
            if _n(tv) == _n(bv) or _n(tv) == _n(ov):
                continue                                     # the workbook left it alone, or already agrees
            both = merge or (_n(ov) != _n(bv))
            add(kind="Changed", what=WORDS.get(f, f[len(MD.CUSTOM):] if f.startswith(MD.CUSTOM) else f), field=f, row=i,
                label=o.get("item") or o.get("ref") or o.get("_id"), old=str(bv if b is not None else ov), new=str(tv), both=both,
                ours=str(ov), id=o.get("_id", ""), map=o.get("_map", ""))
    matched = set(t_o.values())
    for j, o in enumerate(ours):
        if j not in matched and (o.get("_id") or lay == "outline") and o.get("_kind") != "empty":
            add(kind="Row left out of the workbook", what="row", field=None, row=None, label=str(o.get("item") or o.get("text") or "")[:120],
                old=str(o.get("item") or o.get("text") or "")[:200], new="", both=False, id=o.get("_id", ""), map=o.get("_map", ""))
    return out


def _num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", str(v or ""))
    return float(m.group(0)) if m else None


def _set(M, c):
    import matrixdesign as MD
    import setupdoc as SD
    import pagebudget as PB
    f, v, lab = c["field"], c["new"], c.get("map") or ""
    if f == "assigned_to":
        names = [x.strip() for x in re.split(r"[,;\n]", v) if x.strip()]
        SD.set_people(M, lab, names[0] if names else "", ", ".join(names[1:]))
    elif f == "page_alloc":
        n = _num(v)
        PB.set_pages(M, lab, n, "team") if n is not None else PB.set_pages(M, lab, None)
    elif f == "pct_complete":
        n = _num(v)
        SD.set_progress(M, lab, n)
    else:
        it = SD.by_id(M).get(c.get("id"))
        if it is None:
            return False
        if f in ("owner", "authors"):                   # a sentence's author(s) column is its owner
            it["owner"] = v
        elif f == "page":
            it["response_page"] = v
        elif f == "status":
            it["status"] = v
        elif f == "notes":
            it["notes"] = v
        elif f.startswith(MD.CUSTOM):
            it.setdefault("cols", {})[f[len(MD.CUSTOM):]] = v
    return True


def accept(M, changes, picks=None, path="", design=None, effort_path=""):
    """Each Changed the person takes is set in the effort. picks: {index: "ours" or "theirs"}; a change in both without a
    pick keeps ours. Rows added or left out are never applied. Returns how many values came in."""
    import setupdoc as SD
    picks = dict(picks or {})
    n = 0
    for c in changes:
        if c["kind"] != "Changed":
            continue
        take = picks.get(c["i"], "ours" if c["both"] else "theirs") == "theirs"
        if take and _set(M, c):
            n += 1
    if path:
        S = SD.setup_of(M)
        S.setdefault(KEY, {"versions": []}).setdefault("brought_back", []).append(
            {"file": os.path.basename(path), "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "values": n})
    M.pending = True
    SD._log(M, "(setup)", f"matrix workbook brought back: {n} value(s) in")
    return n
