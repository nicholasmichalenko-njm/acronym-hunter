"""Setup Builder (2.13.0): place RFP text and management direction under the proposal outline, then write the setup
(first draft) as plain Word documents for the team to style by hand.

Export format (decided with the user): Word's built-in headings for the outline (every heading exports, even with no
RFP text), RFP text in Word's standard Purple (7030A0) with its reference on the same line ("L.4.2(a): ..."),
management direction in Word's standard Green (00B050) below the section's RFP text. No hidden text, no custom styles:
one formatting per kind, so Word's Select Text with Similar Formatting grabs every block for restyling in one click.

Placement shares the compliance matrix's Outline column (the map field): placing an item on the board maps it, and
mapping it in the Requirements tab places it. Extra copies (one item in two sections), the order inside each section,
typed references, file rules, management direction, context paragraphs and export snapshots are kept in matrix.setup
and saved in the workbook (Setup sheets). Pure Python, no network.
"""
import datetime, hashlib, os, re, zipfile
import cwords

PURPLE, GREEN = "7030A0", "00B050"
CONTEXT_BLUE = "2E74B5"                  # 2.29.0: RFP sentences decided Context (not requirements) print in blue
REF_FORMATS = {"colon": "{ref}: ", "brackets": "[{ref}] ", "rfp": "RFP {ref} - "}
REF_FORMAT_LABELS = {"colon": "L.4.2(a): text", "brackets": "[L.4.2(a)] text", "rfp": "RFP L.4.2(a) - text"}
MISSING = "[REFERENCE MISSING]"
_MARK = re.compile(r"^\s*(\((?:[a-z]|[ivx]{1,4}|\d{1,2})\))\s")
_NORM = re.compile(r"\W+")


def new_setup():
    return {"order": {}, "copies": {}, "mgmt": {}, "notes": {}, "refs": {}, "rules": {}, "ref_format": "colon",
            "exports": [], "context": []}


def setup_of(M):
    S = getattr(M, "setup", None)
    if not isinstance(S, dict):
        S = M.setup = new_setup()
    for k, v in new_setup().items():
        S.setdefault(k, v)
    return S


def _norm(t):
    return _NORM.sub(" ", (t or "").lower()).strip()


def _sig(*parts):
    return hashlib.sha1("␟".join(parts).encode("utf-8")).hexdigest()[:12]


def labels(M):
    import compliance as C
    return [C.outline_label(o) for o in M.outline]


def all_items(M):
    """Kept requirements (and evaluation rows), Context sentences (2.29.0) and context paragraphs, in matrix order."""
    return [it for it in M.items if it.get("decision") in ("Keep", "Context")] + list(setup_of(M)["context"])


def by_id(M):
    return {it["id"]: it for it in list(M.items) + list(setup_of(M)["context"])}


def kind_of(it):
    if it.get("kind") == "context" or it.get("decision") == "Context":
        return "Context"
    return "Evaluation" if it.get("type") == "Evaluation" else "Requirement"


# ------------------------------------------------------------------ references
def suggest_prefix(file_name):
    """A starting rule for a file whose paragraphs are numbered 1.2, 3.4 without a section letter."""
    n = file_name.lower()
    if re.search(r"instruction|section[ _-]?l\b|_l\.|proposal[ _-]prep", n):
        return "L"
    if re.search(r"evaluation|section[ _-]?m\b|_m\.|basis[ _-]of[ _-]award", n):
        return "M"
    if re.search(r"statement[ _-]of[ _-]work|\bsow\b|_sow|\bpws\b|_pws|performance[ _-]work", n):
        return "SOW"
    return ""


def inherited_sections(M):
    """{id: section} for rows without a number: the number of the row before them in the same file."""
    out, last = {}, {}
    for it in list(M.items) + list(setup_of(M)["context"]):
        f = it.get("file", "")
        if it.get("section"):
            last[f] = it["section"]
        elif last.get(f):
            out[it["id"]] = last[f]
    return out


def ref_of(M, it, inherited=None):
    """(reference, where it came from). Typed > RFP numbering or inherited, with a file rule for numbers without a
    letter > nothing."""
    S = setup_of(M)
    if it["id"] in S["refs"]:
        v = S["refs"][it["id"]].strip()
        return (v, "Typed") if v else ("", "No reference found")
    sec, src = it.get("section", ""), "RFP numbering"
    if not sec:
        sec = (inherited if inherited is not None else inherited_sections(M)).get(it["id"], "")
        src = "Inherited"
    if not sec:
        return "", "No reference found"
    prefix = S["rules"].get(it.get("file", ""), "")
    if prefix and sec[0].isdigit():
        sec = f"{prefix}-{sec}"
        src = f"File rule: {prefix}"
    m = _MARK.match(it.get("text", ""))
    if m and src != "Inherited" and not sec.endswith(")"):
        sec += m.group(1)
    return sec, src


def block_text(M, it, inherited=None):
    ref, _src = ref_of(M, it, inherited)
    body = ((it.get("lead") or "") + " " + it["text"]).strip() if it.get("lead") and not it["text"].startswith(it["lead"]) else it["text"]
    fmt = REF_FORMATS.get(setup_of(M)["ref_format"], REF_FORMATS["colon"])
    return (fmt.format(ref=ref) if ref else MISSING + " ") + body


# ------------------------------------------------------------------ placement
def placed_in(M):
    """{label: [ids in order]}: the order list first, then other items placed there, in matrix order."""
    S = setup_of(M)
    labs = labels(M)
    known = set(labs)
    out = {lab: [] for lab in labs}
    items = all_items(M)
    where = {}
    for it in items:
        sec = set()
        if it.get("map") in known:
            sec.add(it["map"])
        for lab, ids in S["copies"].items():
            if it["id"] in ids and lab in known:
                sec.add(lab)
        where[it["id"]] = sec
    for lab in labs:
        seen = set()
        for i in S["order"].get(lab, []):
            if lab in where.get(i, ()) and i not in seen:
                out[lab].append(i); seen.add(i)
        for it in items:
            if lab in where[it["id"]] and it["id"] not in seen:
                out[lab].append(it["id"]); seen.add(it["id"])
        # 2.33.0: a Context sentence prints right under the requirement it explains (unless the order was set by hand).
        # 2.35.0: one that explains several requirements prints under each of them, in every section they are in.
        import compliance as C
        byid = {it["id"]: it for it in items}
        ordered = set(S["order"].get(lab, []))
        ids = out[lab]
        here = set(ids)
        movers = []
        for it in items:
            i = it["id"]
            if it.get("decision") != "Context" or i in ordered:
                continue
            links = [r for r in C.cf_ids(it.get("context_for", "")) if r != i]
            if any(r in here for r in links):
                movers.append(i)
        if movers:
            res, used = [], set()
            for i in (x for x in ids if x not in movers):
                res.append(i)
                for m in movers:
                    if m not in used and i in C.cf_ids(byid[m].get("context_for", "")):
                        res.append(m); used.add(m)
            out[lab] = res
        # 2.36.0: Context for the section itself (no requirement) prints first, right under the heading
        top = [i for i in out[lab] if i not in ordered and byid.get(i, {}).get("decision") == "Context"
               and not byid[i].get("context_for")]
        if top:
            out[lab] = top + [i for i in out[lab] if i not in top]
    return out


def unplaced(M, kinds=("Requirement", "Evaluation", "Context")):
    P = placed_in(M)
    done = {i for ids in P.values() for i in ids}
    return [it for it in all_items(M) if it["id"] not in done and kind_of(it) in kinds]


def _log(M, iid, change):
    if hasattr(M, "log"):
        M.log(iid, change)


def place(M, iid, label, before=None, copy=False):
    """Put an item under an outline section (its Outline column), or add a second copy with copy=True."""
    S = setup_of(M)
    it = by_id(M)[iid]
    if copy and it.get("map") and it["map"] != label:
        lst = S["copies"].setdefault(label, [])
        if iid not in lst:
            lst.append(iid)
    else:
        old = it.get("map", "")
        if old and old != label:
            S["order"][old] = [i for i in S["order"].get(old, []) if i != iid]
        it["map"] = label
    order = [i for i in placed_in(M)[label] if i != iid]
    if before in order:
        order.insert(order.index(before), iid)
    else:
        order.append(iid)
    S["order"][label] = order
    _log(M, iid, f"setup: placed under {label}" + (" (copy)" if copy else ""))


def unplace(M, iid, label):
    S = setup_of(M)
    it = by_id(M).get(iid)
    if it is None:
        return
    if label in S["copies"] and iid in S["copies"][label]:
        S["copies"][label].remove(iid)
    elif it.get("map") == label:
        it["map"] = ""
    S["order"][label] = [i for i in S["order"].get(label, []) if i != iid]
    _log(M, iid, f"setup: removed from {label}")


def move(M, iid, label, delta):
    order = placed_in(M)[label]
    if iid not in order:
        return
    i = order.index(iid)
    j = max(0, min(len(order) - 1, i + delta))
    order.insert(j, order.pop(i))
    setup_of(M)["order"][label] = order


# ------------------------------------------------------------------ context paragraphs
def context_from_chunks(M, file_name, chunks, min_len=40):
    """Paragraphs of an RFP file that are not compliance rows (SOW text, evaluation criteria, background): placeable
    as Context. Returns the number added."""
    import compliance as C
    S = setup_of(M)
    have = {_norm(it["text"]) for it in M.items} | {_norm(c["text"]) for c in S["context"]}
    cur = ("", "")
    n = 0
    for label, text in chunks:
        for para in re.split(r"\n\s*\n|\n", text or ""):
            line = " ".join(para.split())
            if not line:
                continue
            got = C._section_from_line(line, cur)
            if got:
                sec, title, rest = got
                cur = (sec, title or cur[1])
                line = rest
                if not line:
                    continue
            if len(line) < min_len or _norm(line) in have or any(_norm(line) in h or h in _norm(line) for h in have if len(h) > 30):
                continue
            n += 1
            cid = f"X-{len(S['context']) + 1:03d}"
            S["context"].append({"id": cid, "kind": "context", "text": line, "lead": "", "file": file_name, "loc": label,
                                 "section": cur[0], "section_title": cur[1], "map": "", "decision": "Keep", "type": "Context"})
            have.add(_norm(line))
    return n


# ------------------------------------------------------------------ export
def volume_groups(M):
    """[(name, [outline entries])]: one group per 'Volume ...' entry (entries before the first go with it), else one."""
    groups, cur = [], None
    for o in M.outline:
        if (o.get("num") or "").lower().startswith("vol") or (o.get("title") or "").lower().startswith("volume") and o.get("level", 1) == 1:
            cur = (" ".join(x for x in (o.get("num", ""), o.get("title", "")) if x).strip(), [o])
            groups.append(cur)
        else:
            if cur is None:
                cur = (M.name or "Setup", [])
                groups.append(cur)
            cur[1].append(o)
    return groups or [(M.name or "Setup", [])]


def export_check(M):
    P = placed_in(M)
    inh = inherited_sections(M)
    ids = {i for v in P.values() for i in v}
    B = by_id(M)
    no_ref = sorted(i for i in ids if not ref_of(M, B[i], inh)[0])
    kept = [it for it in M.items if it.get("decision") in ("Keep", "Context")]
    unp = [it["id"] for it in kept if it["id"] not in ids]
    return {"unplaced": unp, "no_ref": no_ref, "blocks": len(ids)}


def _safe(s):
    return re.sub(r"[^A-Za-z0-9 _.-]+", "", s).strip().replace(" ", "_")[:60] or "Setup"


def _doc_for(M, name, entries, P, inh, stamp):
    import docxw, compliance as C
    S = setup_of(M)
    B = by_id(M)
    d = docxw.Doc()
    cw = cwords.load()
    d.props = {"AcronymHunterMatrix": M.name or "", "AcronymHunterSetupExported": stamp, "AcronymHunterSetupPart": name}
    base = min((o.get("level", 1) for o in entries), default=1)
    for o in entries:
        lab = C.outline_label(o)
        d.heading(lab, o.get("level", 1) - base + 1)
        last_req = None
        for iid in P.get(lab, []):
            it = B.get(iid)
            if it is None:
                continue
            d.rich(cwords.docx_parts(block_text(M, it, inh), {"color": CONTEXT_BLUE if kind_of(it) == "Context" else PURPLE}, cw))
            if kind_of(it) == "Context":
                links = C.cf_ids(it.get("context_for", ""))
                others = [r for r in links if r != last_req]
                if len(links) > 1 and others:          # 2.35.0: shared Context names the other requirements it explains
                    d.para("Also context for " + ", ".join(others), color="6B7280")
            else:
                last_req = iid
            note = S["notes"].get(iid, "").strip()
            if note:
                d.para(note, color=GREEN)
        mg = S["mgmt"].get(lab, "").strip()
        if mg:
            d.para(mg, color=GREEN)
    return d


def snapshot(M):
    P = placed_in(M)
    inh = inherited_sections(M)
    B = by_id(M)
    S = setup_of(M)
    return {"blocks": {lab: [[i, _sig(block_text(M, B[i], inh), S["notes"].get(i, ""))] for i in ids] for lab, ids in P.items()},
            "mgmt": {lab: _sig(S["mgmt"].get(lab, "")) for lab in P}}


def export(M, folder, when=None):
    """Write one .docx per volume into folder. Returns the paths. Records a snapshot for Export changes only."""
    when = when or datetime.datetime.now()
    stamp = when.strftime("%Y-%m-%d %H:%M")
    tag = when.strftime("%Y-%m-%d_%H%M")
    P = placed_in(M)
    inh = inherited_sections(M)
    paths = []
    stem = _safe(os.path.splitext(os.path.basename(M.path))[0] if getattr(M, "path", "") else M.name)
    groups = volume_groups(M)
    for name, entries in groups:
        part = "" if len(groups) == 1 else "_" + _safe(name)
        p = os.path.join(folder, f"{stem}_Setup{part}_{tag}.docx")
        _doc_for(M, name, entries, P, inh, stamp).save(p)
        paths.append(p)
    S = setup_of(M)
    snap = snapshot(M)
    snap.update(time=stamp, files=[os.path.basename(p) for p in paths])
    S["exports"] = (S["exports"] + [snap])[-10:]
    _log(M, "(setup)", f"setup exported: {len(paths)} file(s)")
    return paths


def changes_since_last(M):
    """[(label, kind, id or '', text)] kind: Added, Changed, Removed, Direction changed, Direction added."""
    S = setup_of(M)
    if not S["exports"]:
        return None
    last = S["exports"][-1]
    now = snapshot(M)
    B = by_id(M)
    inh = inherited_sections(M)
    out = []
    for lab in labels(M):
        old = {i: s for i, s in last["blocks"].get(lab, [])}
        cur = {i: s for i, s in now["blocks"].get(lab, [])}
        for i, s in cur.items():
            if i not in old:
                out.append((lab, "Added", i, block_text(M, B[i], inh)))
            elif old[i] != s:
                out.append((lab, "Changed", i, block_text(M, B[i], inh)))
        for i in old:
            if i not in cur:
                it = B.get(i)
                out.append((lab, "Removed", i, block_text(M, it, inh) if it else i))
        if now["mgmt"].get(lab) != last["mgmt"].get(lab, _sig("")):
            txt = S["mgmt"].get(lab, "").strip()
            out.append((lab, "Direction changed" if txt else "Direction removed", "", txt))
    return out


def export_changes(M, path):
    """A short Word file with only what changed since the last export, under its headings."""
    import docxw
    ch = changes_since_last(M)
    if ch is None:
        return None
    d = docxw.Doc()
    cw = cwords.load()
    d.props = {"AcronymHunterMatrix": M.name or "", "AcronymHunterSetupChangesSince": M.setup["exports"][-1]["time"]}
    d.para(f"Setup changes since the export of {M.setup['exports'][-1]['time']}. Paste the purple and green paragraphs "
           "under the same headings in the styled setup.")
    S = setup_of(M)
    cur = None
    for lab, kind, iid, text in ch:
        if lab != cur:
            d.heading(lab, 2); cur = lab
        if kind in ("Added", "Changed"):
            d.para(f"{kind}:", bold=True)
            d.rich(cwords.docx_parts(text, {"color": PURPLE}, cw))
            if S["notes"].get(iid, "").strip():
                d.para(S["notes"][iid].strip(), color=GREEN)
        elif kind == "Removed":
            d.para("Removed (delete it from the setup):", bold=True)
            d.para(text)
        else:
            d.para(f"{kind}:", bold=True)
            if text:
                d.para(text, color=GREEN)
    if not ch:
        d.para("No changes.")
    d.save(path)
    S["exports"][-1].update(snapshot(M))          # changes handed over: the next comparison starts here
    S["exports"][-1]["changes_exported"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return ch


# ------------------------------------------------------------------ compare a styled setup document
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_paragraphs(path):
    """[(text, style id, outline level or None)] from a .docx, hidden text included."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
    out = []
    for p in root.iter(_W + "p"):
        text = "".join(t.text or "" for t in p.iter(_W + "t"))
        st = p.find(f"{_W}pPr/{_W}pStyle")
        ol = p.find(f"{_W}pPr/{_W}outlineLvl")
        out.append((text, st.get(_W + "val") if st is not None else "", int(ol.get(_W + "val")) if ol is not None else None))
    return out


def compare(M, path):
    """Rows [(section, problem, id, text)] for a styled setup document: missing RFP text, text under a different
    heading, text that is not in the setup, headings not found."""
    import compliance as C
    paras = docx_paragraphs(path)
    labs = labels(M)
    keys = {}
    for o in M.outline:
        lab = C.outline_label(o)
        keys[_norm(lab)] = lab
        if o.get("title"):
            keys.setdefault(_norm(o["title"]), lab)
    P = placed_in(M)
    B = by_id(M)
    probes = [(it["id"], _norm(it["text"])) for it in all_items(M) if len(_norm(it["text"])) >= 12]
    found, seen_heads = {}, set()
    cur = ""
    for text, _style, _lvl in paras:
        n = _norm(text)
        if not n:
            continue
        if n in keys and len(n) < 200:
            cur = keys[n]; seen_heads.add(cur); continue
        for iid, k in probes:
            if k in n:
                found.setdefault(iid, set()).add(cur)
    rows = []
    expected = {}
    for lab, ids in P.items():
        for i in ids:
            expected.setdefault(i, set()).add(lab)
    # a document may hold one volume: check only the volumes whose headings it contains
    groups = [[C.outline_label(o) for o in entries] for _n, entries in volume_groups(M)]
    in_doc = [g for g in groups if any(lab in seen_heads for lab in g)] or groups
    scope = [lab for g in in_doc for lab in g]
    where_txt = lambda ws: ", ".join(sorted(w or "(before the first heading)" for w in ws))
    for lab in scope:
        if lab not in seen_heads:
            rows.append((lab, "Heading not found", "", ""))
        for i in P.get(lab, []):
            where = found.get(i, set())
            if not where:
                rows.append((lab, "Missing", i, B[i]["text"][:160]))
            elif lab not in where and not (where & expected.get(i, set())):
                rows.append((lab, "Under a different heading: " + where_txt(where), i, B[i]["text"][:160]))
    for i, where in found.items():
        exp = expected.get(i, set())
        for w in sorted(where - exp, key=str):
            if exp and w in scope and not (w == "" and exp):
                if any(r[2] == i and r[1].startswith("Under a different heading") for r in rows):
                    continue
                rows.append((w or "(before the first heading)", "Not in the setup under this heading", i, B[i]["text"][:160]))
            elif not exp:
                rows.append((w or "(before the first heading)", "Not in the setup", i, B[i]["text"][:160]))
    return rows
