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
            "exports": [], "context": [],
            "refmode": {},     # 2.38.0: {file: {"mode": "numbering"|"para"|"page"|"prefix", "name", "prefix"}}
            "owners": {},      # 2.38.0: {section label: {"lead": "", "with": ""}}
            "tables": False}   # 2.38.0: Response Setup includes each section's requirement table


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


# ------------------------------------------------------------------ references by the document itself (2.38.0)
_PARA = re.compile(r"\bpara (\d+)")
_PAGE = re.compile(r"\(p\.(\d+)")


def file_has_numbering(M, f):
    """Does this RFP file carry section numbers the reference can use?"""
    return any(it.get("section") for it in M.items if it.get("file", "") == f)


def files_needing_reference(M):
    """RFP files with no section numbering and no reference rule chosen yet."""
    S = setup_of(M)
    seen, out = set(), []
    for it in M.items:
        f = it.get("file", "")
        if f and f not in seen:
            seen.add(f)
            if not file_has_numbering(M, f) and f not in S["refmode"]:
                out.append(f)
    return out


def short_name(f):
    import docversions as DV
    return DV.display_name(f)


def set_refmode(M, f, mode, name="", prefix=""):
    S = setup_of(M)
    S["refmode"][f] = {"mode": mode, "name": (name or short_name(f)).strip(), "prefix": (prefix or "").strip()}
    _log(M, "(setup)", f"reference for {f}: {mode}")


def _doc_ref(M, it, rule):
    """A reference made from the document itself: 'Design Note, para 3', 'Design Note, p. 4, para 3' or 'SOW-3'."""
    f = it.get("file", "")
    loc = it.get("loc", "") or ""
    mode = rule.get("mode")
    if mode == "prefix" and rule.get("prefix"):
        n = next((k for k, x in enumerate((x for x in M.items if x.get("file", "") == f), 1) if x is it), 0)
        return f"{rule['prefix']}-{n}" if n else rule["prefix"]
    m = _PARA.search(loc)
    para = m.group(1) if m else ""
    name = rule.get("name") or short_name(f)
    if mode == "page":
        pg = it.get("page") or (_PAGE.search(loc).group(1) if _PAGE.search(loc) else "")
        return ", ".join(x for x in (name, f"p. {pg}" if pg else "", f"para {para}" if para else "") if x)
    return f"{name}, para {para}" if para else name


def ref_of(M, it, inherited=None):
    """(reference, where it came from). Typed > the file's own reference rule (2.38.0) > RFP numbering or inherited,
    with a file rule for numbers without a letter > nothing."""
    S = setup_of(M)
    if it["id"] in S["refs"]:
        v = S["refs"][it["id"]].strip()
        return (v, "Typed") if v else ("", "No reference found")
    rule = S["refmode"].get(it.get("file", ""))
    if rule and rule.get("mode") not in (None, "", "numbering"):
        return _doc_ref(M, it, rule), "The document itself"
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


def where_of(it):
    """Where a sentence is in its customer document (2.52.0): 'Section L.docx, p.3' (the page when known)."""
    f = it.get("file", "")
    p = it.get("page")
    if not p:
        m = _PAGE.search(it.get("loc", "") or "")
        p = m.group(1) if m else ""
    return ", ".join(x for x in (f, (f"p.{p}" if p else "")) if x)


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


# ------------------------------------------------------------------ people per section (2.38.0)
def _parents(M, label):
    """The section and its parents, nearest first."""
    import compliance as C
    labs = [(C.outline_label(o), o.get("level", 1)) for o in M.outline]
    i = next((k for k, (l, _v) in enumerate(labs) if l == label), None)
    if i is None:
        return [label] if label else []
    out, lvl = [labs[i][0]], labs[i][1]
    for l, v in reversed(labs[:i]):
        if v < lvl:
            out.append(l); lvl = v
    return out


def section_people(M, label):
    """{"lead", "with", "from"}: the section's people, else the nearest parent section's (inherited)."""
    S = setup_of(M)
    for l in _parents(M, label):
        p = S["owners"].get(l) or {}
        if p.get("lead") or p.get("with"):
            return {"lead": p.get("lead", ""), "with": p.get("with", ""), "from": l}
    return {"lead": "", "with": "", "from": ""}


def set_people(M, label, lead="", with_=""):
    S = setup_of(M)
    lead, with_ = " ".join((lead or "").split()), ", ".join(x.strip() for x in (with_ or "").split(",") if x.strip())
    if lead or with_:
        S["owners"][label] = {"lead": lead, "with": with_}
    else:
        S["owners"].pop(label, None)
    _log(M, "(setup)", f"people for {label}: {lead or '-'}" + (f"; with {with_}" if with_ else ""))


def owner_of(M, it):
    """Who writes this sentence: its own owner, else the lead of its section (or a parent section)."""
    return (it.get("owner") or "").strip() or section_people(M, it.get("map", "")).get("lead", "")


def people(M):
    """Everyone named as a lead, contributor or owner, sorted."""
    S = setup_of(M)
    names = set()
    for p in S["owners"].values():
        names.add(p.get("lead", ""))
        names |= {x.strip() for x in p.get("with", "").split(",")}
    names |= {(it.get("owner") or "").strip() for it in M.items}
    return sorted(n for n in names if n)


def sections_of(M, person):
    """Section labels where person is the lead or a contributor (directly or through a parent)."""
    import compliance as C
    out = []
    for o in M.outline:
        lab = C.outline_label(o)
        p = section_people(M, lab)
        if person and (p["lead"] == person or person in [x.strip() for x in p["with"].split(",")]):
            out.append(lab)
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


def item_sections(M, it):
    """2.56.0: every proposal section a sentence is in: its Outline column first, then its extra copies."""
    out = [it["map"]] if it.get("map") else []
    for lab, ids in setup_of(M)["copies"].items():
        if it.get("id") in ids and lab not in out:
            out.append(lab)
    return out


def add_section(M, it, label):
    """2.56.0: put a sentence in one more section (it keeps the ones it is in). Returns True when it was added."""
    if label in item_sections(M, it):
        return False
    if not it.get("map"):
        it["map"] = label
    else:
        lst = setup_of(M)["copies"].setdefault(label, [])
        lst.append(it["id"])
    return True


def remove_section(M, it, label):
    """2.56.0: take a sentence out of one of its sections; when that was its Outline column, its next section takes
    that place. Returns True when it was removed."""
    S = setup_of(M)
    secs = item_sections(M, it)
    if label not in secs:
        return False
    if it.get("map") == label:
        rest = [x for x in secs if x != label]
        it["map"] = rest[0] if rest else ""
        if rest:
            S["copies"][rest[0]] = [i for i in S["copies"].get(rest[0], []) if i != it["id"]]
    else:
        S["copies"][label] = [i for i in S["copies"].get(label, []) if i != it["id"]]
    S["order"][label] = [i for i in S["order"].get(label, []) if i != it["id"]]
    return True


def clear_sections(M, it):
    """No section at all (the sentence is cleared or decided another way)."""
    S = setup_of(M)
    for lab in list(S["copies"]):
        S["copies"][lab] = [i for i in S["copies"][lab] if i != it.get("id")]
    it["map"] = ""


def expand(M, items):
    """2.56.0: one copy of each sentence per section it is in (dict copies with map set; the first is the sentence's
    own section), for outputs that list a sentence once per section."""
    out = []
    for it in items:
        secs = item_sections(M, it)
        if len(secs) <= 1:
            out.append(it)
        else:
            out += [dict(it, map=lab, _also=k > 0) for k, lab in enumerate(secs)]
    return out


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
    d.props = {"StationkeeperMatrix": M.name or "", "StationkeeperSetupExported": stamp, "StationkeeperSetupPart": name}
    base = min((o.get("level", 1) for o in entries), default=1)
    for o in entries:
        lab = C.outline_label(o)
        d.heading(lab, o.get("level", 1) - base + 1)
        pp = S["owners"].get(lab) or {}
        if pp.get("lead") or pp.get("with"):                      # 2.38.0: who writes this section
            d.para("Lead: " + (pp.get("lead") or "-") + (f"   Contributors: {pp['with']}" if pp.get("with") else ""), color="1E3A8A")
        if S.get("tables"):                                       # 2.38.0: the requirement table of the old Word outline
            rows = [B[i] for i in P.get(lab, []) if B.get(i) is not None and B[i].get("decision") == "Keep"]
            if rows:
                d.table(["Reference", "Requirement", "Owner"],
                        [[ref_of(M, it, inh)[0] or it["id"], cwords.docx_parts(((it.get("lead") or "") + " " + it["text"]).strip(), None, cw),
                          owner_of(M, it)] for it in rows], [1900, 5860, 1600])
        last_req = None
        for iid in P.get(lab, []):
            it = B.get(iid)
            if it is None:
                continue
            where = where_of(it)
            if kind_of(it) == "Context":
                # 2.52.0: support language from the RFP: indented under the requirement it supports, a line down its left
                # edge, and where it is in the customer document
                links = C.cf_ids(it.get("context_for", ""))
                lead_in = [("Support" + (f" for {links[0]}" if links else "") + (f" ({where})" if where else "") + ": ",
                            {"color": CONTEXT_BLUE, "bold": True})]
                d.rich(lead_in + cwords.docx_parts(block_text(M, it, inh), {"color": CONTEXT_BLUE}, cw), indent=720, border=CONTEXT_BLUE)
                others = [r for r in links if r != last_req]
                if len(links) > 1 and others:          # 2.35.0: shared Context names the other requirements it explains
                    d.rich([("Also support for " + ", ".join(others), {"color": "6B7280"})], indent=720)
            else:
                d.rich(cwords.docx_parts(block_text(M, it, inh), {"color": PURPLE}, cw)
                       + ([(f"  ({where})", {"color": "6B7280"})] if where else []))
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
        p = os.path.join(folder, f"{stem}_Response_Setup{part}_{tag}.docx")
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
    d.props = {"StationkeeperMatrix": M.name or "", "StationkeeperSetupChangesSince": M.setup["exports"][-1]["time"]}
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
