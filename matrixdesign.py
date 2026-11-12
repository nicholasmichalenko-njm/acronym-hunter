"""The compliance matrix in Excel, designed in the app (2.48.0). Rules only (No AI); nothing leaves the PC.

The team picks which columns the matrix shows, in what order and under what headings, and which roles it lists
(compliance requirements, context; the customer's sentences on a sheet of their own). The design is kept with the
effort's matrix and can be saved as the team default. Rows follow our response structure: section by section in
outline order, then by RFP reference. One export can also write the matrix and the Response Setup together, from the
same decisions, into one dated folder.
"""
import copy, datetime, json, os

# key: (default heading, width)
COLUMNS = {
    "order": ("Order", 8),                          # 2.51.0: sort on it to get the original layout back
    "section_no": ("Response section no.", 14),     # 2.56.0: our proposal section, number and name apart
    "section_name": ("Response section name", 30),
    "reference": ("Reference", 16),                 # 2.68.0: document initial, L or M, section: R-L-4.2.1
    "doc": ("Doc", 7),                              # 2.68.0: the customer document's initial
    "lm": ("L/M", 6),                               # 2.68.0: Section L (instructions) or M (evaluation), Shipley
    "doc_type": ("Document type", 14),              # 2.68.0: RFP, SOW, SOO, Amendment ...
    "rfp_ref": ("Section", 30),                     # 2.56.0: the RFP's own section number and title, as written
    "authors": ("Author(s)", 24),                   # 2.56.0: the sentence's owner, else the section lead and contributors
    "ref": ("Section L No.", 16),                   # 2.51.0: the RFP section the sentence is in, else page and paragraph
    "rfp_section": ("Section L title", 28),
    "text": ("RFP text", 70),                       # 2.52.0: compliance and support rows in the one column
    "role": ("Compliance or support", 22),
    "volume": ("Volume", 22),                       # 2.51.0
    "section": ("Proposal section", 30),
    "deliverable": ("Deliverable", 22),             # 2.51.0: from the effort's deliverables
    "page_limit": ("Page limit", 10),               # 2.51.0
    "format": ("Format", 30),                       # 2.51.0: font, margins, page size, spacing, file format
    "far": ("FAR reference", 18),                   # 2.51.0: FAR, DFARS and NFS clauses named in the sentence
    "evaluated_by": ("Evaluated by (Section M)", 30),    # 3.16.0: from the L/M crosswalk: the factor that scores it
    "lead": ("Section lead", 18),
    "owner": ("Owner", 18),
    "page": ("Proposal page", 12),
    "status": ("Compliance status", 16),
    "notes": ("Notes", 30),
    "context_for": ("Context for", 18),
    "source": ("Source document", 28),
    "location": ("Location in the document", 20),
    "strength": ("Strength", 12),
    "type": ("Type", 14),
    "id": ("Stationkeeper ID", 14),
    "topic": ("Topic", 22),                         # 3.29.0: what review feeds: the sentence's topics
    "objective": ("Customer objective", 36),        # 3.29.0: the objectives mapped to its section, verbatim
    "keypoints": ("Key points", 36),                # 3.29.0: key points taken from the sentence
    "excerpt": ("Source excerpt and location", 40), # 3.29.0: the customer's words with where they sit
    # 3.35.0: the outline matrix (the user's default): one row per outline item, Section L and M side by side
    "item": ("Response Section No. Item", 34),      # the item's number and title, indented by its level
    "assigned_to": ("Assigned To", 20),             # the item's lead and contributors
    "page_alloc": ("Initial Page Allocation", 12),  # the item's page budget
    "pct_complete": ("% Complete", 10),             # typed by the team on the item
    "l_refs": ("RFP Solicitation Requirements (Section L)", 22),
    "l_content": ("Section L Content", 60),         # requirements (L, SOW, an RFI's interest, or not designated)
    "m_refs": ("Evaluation Section (Section M)", 22),
    "m_content": ("Evaluation Content", 60),        # sentences designated M
}
OUTLINE_KEYS = ("item", "assigned_to", "page_alloc", "pct_complete", "l_refs", "l_content", "m_refs", "m_content")
LAYOUTS = (("outline", "One row per outline item (Section L and M side by side)"), ("sentences", "One row per RFP piece"))
CUSTOM = "custom:"                                   # 2.51.0: a column of the team's own, filled in Excel
ROLES = (("Keep", "Compliance requirements"), ("Context", "Context"))
# 2.56.0 (the user's default): Volume, Response section no., Response section name, RFP section, RFP content (compliance
# requirements and their support, told apart by the row style), Author(s), Notes; every other column stays available.
# 2.68.0: Reference (R-L-4.2.1), Doc, L/M and Section (the customer document's own number and title)
SENTENCES = {"columns": [{"key": k, "heading": h} for k, h in
                         (("volume", "Volume"), ("section_no", "Response section no."), ("section_name", "Response section name"),
                          ("reference", "Reference"), ("doc", "Doc"), ("lm", "L/M"), ("rfp_ref", "Section"),
                          ("text", "RFP content"), ("authors", "Author(s)"), ("notes", "Notes"))],
             "v": 3, "layout": "sentences",
             "roles": ["Keep", "Context"], "customer_sheet": True, "title": "", "empty_sections": True,
             "order": "rfp",                        # 2.54.0: rows in the RFP's order (or "structure": our sections' order)
             "context": "cell"}                     # 2.58.0: support in its requirement's cell, each piece with its RFP place
                                                    # ("rows": a row of its own under the requirement)
# 3.35.0 (the user's default): one row per item of the response outline (section, headers, subheaders) with who it is
# assigned to, its initial page allocation, its % complete, and its Section L and Section M content side by side. A
# sentence assigned to several items is in each of their rows.
DEFAULT = dict(SENTENCES, columns=[{"key": k, "heading": COLUMNS[k][0]} for k in OUTLINE_KEYS], layout="outline",
               order="structure")
BUILTIN_VIEWS = (("Outline with L and M", "outline"), ("RFP pieces", "sentences"))
_FAR = __import__("re").compile(r"\b(?:FAR|DFARS|NFS|AFFARS|DFARS PGI)\s+(?:clause\s+)?\d{1,3}\.\d{2,4}(?:-\d+)?(?:\([a-z0-9]+\))*", __import__("re").I)


def width_of(key):
    return COLUMNS[key][1] if key in COLUMNS else 20


def heading_of(key):
    return COLUMNS[key][0] if key in COLUMNS else key[len(CUSTOM):] if key.startswith(CUSTOM) else key


def default(layout="outline"):
    return copy.deepcopy(SENTENCES if layout == "sentences" else DEFAULT)


_OLD_DEFAULT_KEYS = ["order", "ref", "text", "role", "volume", "section", "page_limit", "owner", "page", "status", "notes"]


def clean(d):
    """A design read from a file or the matrix: only known columns and roles, every heading a short plain string.
    2.56.0: a design that still has the old default columns, never changed, takes the new default."""
    out = default()
    if not isinstance(d, dict):
        return out
    # 3.35.0: a design kept before the outline matrix keeps its sentence rows
    layout = d.get("layout") if d.get("layout") in dict(LAYOUTS) else ("sentences" if d.get("columns") else "outline")
    out = default(layout)
    if not d.get("v") and [str(c.get("key")) for c in (d.get("columns") or []) if isinstance(c, dict)] == _OLD_DEFAULT_KEYS:
        d = dict(d, columns=out["columns"])
    cols = []
    for c in d.get("columns") or []:
        if not isinstance(c, dict):
            continue
        k = str(c.get("key") or "")
        if k.startswith(CUSTOM):
            k = CUSTOM + " ".join(k[len(CUSTOM):].split())[:40]
            if k == CUSTOM:
                continue
        elif k not in COLUMNS:
            continue
        if k in [x["key"] for x in cols]:
            continue
        h = " ".join(str(c.get("heading") or heading_of(k)).split())[:60] or heading_of(k)
        cols.append({"key": k, "heading": h})
    if cols:
        out["columns"] = cols
    roles = [r for r in (d.get("roles") or []) if r in dict(ROLES)]
    out["roles"] = roles or out["roles"]
    out["customer_sheet"] = bool(d.get("customer_sheet", True))
    out["title"] = " ".join(str(d.get("title") or "").split())[:120]
    out["empty_sections"] = bool(d.get("empty_sections", True))
    out["order"] = d.get("order") if d.get("order") in ("rfp", "structure") else out["order"]
    out["context"] = d.get("context") if d.get("context") in ("cell", "rows") else "cell"
    out["layout"] = layout
    v = d.get("view")
    if isinstance(v, dict) and v.get("id"):                 # 3.35.0: the saved view it came from
        out["view"] = {"id": str(v["id"])[:40], "name": " ".join(str(v.get("name") or "").split())[:80]}
    out["v"] = 3
    return out


def of_matrix(M):
    import setupdoc as SD
    return clean(SD.setup_of(M).get("matrix_design")) if SD.setup_of(M).get("matrix_design") else None


def set_matrix(M, design):
    import setupdoc as SD
    SD.setup_of(M)["matrix_design"] = clean(design)
    M.pending = True


def team_file(config_dir):
    return os.path.join(config_dir, "matrix design.json")


def load_team(config_dir):
    try:
        with open(team_file(config_dir), encoding="utf-8") as f:
            return clean(json.load(f))
    except (OSError, ValueError):
        return None


def save_team(config_dir, design):
    os.makedirs(config_dir, exist_ok=True)
    p = team_file(config_dir)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean(design), f, indent=1)
    os.replace(tmp, p)
    return p


def design_for(M, config_dir="", effort_type=""):
    """The matrix's own design, else its effort type's starting view (3.35.0), else the team default, else the built-in
    one (the outline matrix)."""
    own = of_matrix(M)
    if own:
        return own
    if config_dir and effort_type:
        v = type_view(config_dir, effort_type)
        if v:
            d = view_design(config_dir, v)
            if d:
                return d
    return (load_team(config_dir) if config_dir else None) or default()


# ------------------------------------------------------------------ 3.35.0: named matrix views in the template library
VIEW_KIND = "matrix_view"


def _lib(config_dir):
    import templatelib as TL
    return TL.Library(config_dir)


def _plain(design):
    d = clean(design)
    d.pop("view", None)
    return d


def view_summary(design):
    d = clean(design)
    lay = "one row per outline item" if d["layout"] == "outline" else "one row per RFP piece"
    return f"{lay}; " + ", ".join(c["heading"] for c in d["columns"])


def views(config_dir):
    """[(item id, shown name)] of the matrix views kept in the template library, newest version of a family first."""
    lib = _lib(config_dir)
    its = sorted(lib.shelf(VIEW_KIND), key=lambda i: (lib.base_of(i).casefold(), -int(i.get("version") or 1)))
    return [(i["id"], lib.shown_name(i)) for i in its]


def save_view(config_dir, name, design, who=None):
    """Keeps a design as a named matrix view (a new family, or a new version of the family with that name). Returns
    (item id, shown name, state)."""
    lib = _lib(config_dir)
    name = " ".join((name or "").split())[:80]
    if not name:
        return None, "", "no name"
    item, state = lib.add(VIEW_KIND, name, _plain(design), summary=view_summary(design), who=who)
    return item["id"], lib.shown_name(item), state


def save_view_version(config_dir, iid, design, label="", who=None):
    """A new version of a view's family with this design (the same values return the version that holds them)."""
    lib = _lib(config_dir)
    item, state = lib.save_version(iid, _plain(design), label=label, who=who)
    if item is None:
        return None, "", state
    return item["id"], lib.shown_name(item), state


def view_design(config_dir, iid):
    """The design a view holds, marked with where it came from; None when the library no longer has it."""
    lib = _lib(config_dir)
    it = lib.get(iid)
    v = lib.values(it) if it else None
    if not isinstance(v, dict):
        return None
    return clean(dict(v, view={"id": iid, "name": lib.shown_name(it)}))


def type_view(config_dir, effort_type):
    """The matrix view an effort type starts its efforts with ('' for none)."""
    import prodrules as PRL
    e = PRL.effort_type_of(PRL.load(config_dir), effort_type)
    return (e or {}).get("matrix_view", "")


def set_type_view(config_dir, effort_type, iid):
    """Efforts of this type start with this view ('' takes it off). Returns True when kept."""
    import prodrules as PRL
    data = PRL.load(config_dir)
    e = PRL.effort_type_of(data, effort_type)
    if e is None:
        return False
    if iid:
        e["matrix_view"] = iid
    else:
        e.pop("matrix_view", None)
    PRL.save(config_dir, data)
    return True


def _where(it, M=None):
    """'p.3, para 2' from where a sentence was found (for RFPs without section numbers). 2.58.0: a sentence read from
    the page (it has a place) says its page and its paragraph on that page, counted without headings."""
    import re
    if it.get("place"):
        pdf = ""
        if M is not None and str(it.get("file", "")).lower().endswith(".pdf"):
            pdf = M.path_of(it.get("file", ""))
        try:
            import pagesent as PS
            w = PS.where_text(pdf, it["place"])
        except Exception:
            w = ""
        if w:
            return w
    loc = it.get("loc", "")
    page = it.get("page") or (re.search(r"\bp\.?\s*(\d+)|page\s+(\d+)", loc, re.I) or [None])
    if not isinstance(page, (str, int)):
        m = re.search(r"\bp\.?\s*(\d+)|page\s+(\d+)", loc, re.I)
        page = (m.group(1) or m.group(2)) if m else ""
    para = re.search(r"\bpara(?:graph)?\.?\s*(\d+)", loc, re.I)
    return ", ".join(x for x in ((f"p.{page}" if page else ""), (f"para {para.group(1)}" if para else "")) if x)


def volume_map(M):
    """{proposal section label: its volume}: 2.56.1 what the person decided in Structure > Volumes... (one volume, or
    which headings start a volume); nothing is guessed from section or deliverable names."""
    import setupdoc as SD
    return SD.volume_of_sections(M)


def _deliv(ctx, vol):
    """The effort deliverable that matches a volume: {name, limit, format}, or None."""
    if not ctx or not vol:
        return None
    import subreq as SR
    for d in ctx.get("deliverables") or []:
        if SR.match_volume(vol, d["name"]) or SR.match_volume(d["name"], vol) or d["name"].lower() == vol.lower():
            return d
    return None


_XW = {}


def _crosswalk(M):
    """{Section L number: [(M number, title)]} from the crosswalk, worked out once per state of the matrix."""
    import json as _j
    import crosswalk as X
    import setupdoc as SD
    k = (id(M), len(M.items), _j.dumps(SD.setup_of(M).get("crosswalk") or {}, sort_keys=True))
    if k not in _XW:
        _XW.clear()
        try:
            _XW[k] = {r["num"]: [(m, t) for m, t, _h in r["m"]] for r in X.build(M) if r.get("kind") == "L"}
        except Exception:
            _XW[k] = {}
    return _XW[k]


def _side(M, it, inh):
    """3.35.0: the column a sentence lands in on the outline matrix: "M" for a sentence designated M (Evaluation),
    "L" for every other requirement (L, SOW, an RFI's interest, or not designated). Support takes its requirement's."""
    import setupdoc as SD, compliance as C
    lm = SD.lm_of(M, it, inh)
    if not lm and it.get("decision") == "Context":
        byid = {x["id"]: x for x in M.items}
        hosts = [byid[h] for h in C.cf_ids(it.get("context_for", "")) if h in byid]
        lm = next((SD.lm_of(M, h, inh) for h in hosts if SD.lm_of(M, h, inh)), "")
    return "M" if lm == "M" else "L"


def _sref(M, it, inh):
    """The RFP place of a sentence for the outline matrix: its RFP section number (L.4.2.1), else page and paragraph."""
    import setupdoc as SD
    return SD.ref_of(M, it, inh)[0] or it.get("section", "") or _where(it, M) or it.get("id", "")


def _stext(it):
    t = ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", "")
    return ("(Supporting context) " + t) if it.get("decision") == "Context" else t


def _refs_cell(M, its, inh):
    return "\n".join(dict.fromkeys(_sref(M, x, inh) for x in its))


def _content_cell(M, its, inh):
    """Each sentence's words; with more than one place, each starts with its place so the two columns read together."""
    if len({_sref(M, x, inh) for x in its}) <= 1:
        return "\n\n".join(_stext(x) for x in its)
    return "\n\n".join(f"{_sref(M, x, inh)}: {_stext(x)}" for x in its)


def _factors(M, its, inh):
    """The Section M factors the L/M crosswalk ties these sentences' instructions to."""
    import setupdoc as SD
    xw = _crosswalk(M)
    out = []
    for it in its:
        num = it.get("section", "") or SD.ref_of(M, it, inh)[0]
        while num:
            if num in xw:
                out += [f"{r} {t}".strip() for r, t in xw[num]]
                break
            num = num.rsplit(".", 1)[0] if "." in num else ""
    return "\n".join(dict.fromkeys(out))


def _item_value(M, lab, key, inh, Ls=(), Ms=()):
    """3.35.0: an outline item's own columns, and its Section L and M content."""
    import setupdoc as SD, compliance as C, pagebudget as PB
    if key == "item":
        o = next((o for o in M.outline if C.outline_label(o) == lab), None)
        return " ".join(x for x in ((o or {}).get("num", ""), (o or {}).get("title", "") or (lab if o is None else "")) if x) or lab
    if key == "assigned_to":
        p = SD.section_people(M, lab) if lab else {}
        return ", ".join(dict.fromkeys(n for n in [p.get("lead", "")] + [x.strip() for x in (p.get("with", "") or "").split(",")] if n))
    if key == "page_alloc":
        return PB.fmt(PB.pages(M, lab)) if lab else ""
    if key == "pct_complete":
        v = SD.progress_of(M, lab) if lab else None
        return "" if v is None else f"{v}%"
    if key == "l_refs":
        return _refs_cell(M, Ls, inh)
    if key == "l_content":
        return _content_cell(M, Ls, inh)
    if key == "m_refs":
        return _refs_cell(M, Ms, inh) if Ms else _factors(M, [x for x in Ls if x.get("decision") == "Keep"], inh)
    if key == "m_content":
        return _content_cell(M, Ms, inh)
    return ""


def _value(M, it, key, inh, people, ctx=None, vols=None):
    import setupdoc as SD, compliance as C
    if it.get("_kind") == "item":                                   # 3.35.0: a row of the outline matrix
        if key == "item" and it.get("_unplaced"):
            return UNPLACED
        if key in OUTLINE_KEYS:
            return _item_value(M, it["map"], key, inh, it.get("_L", ()), it.get("_M", ()))
        if key in ("volume", "deliverable", "page_limit", "format", "section", "section_no", "section_name", "lead", "order"):
            return _value(M, dict(it, _kind="empty"), key, inh, people, ctx, vols) if key != "lead" else \
                SD.section_people(M, it["map"]).get("lead", "")
        if key == "text":
            return _content_cell(M, list(it.get("_L", ())) + list(it.get("_M", ())), inh)
        return ""
    if key in OUTLINE_KEYS:                                          # 3.35.0: the same columns on a sentence's row
        lab = it.get("map", "")
        if it.get("_kind") == "empty" or key in ("item", "assigned_to", "page_alloc", "pct_complete"):
            if key == "assigned_to" and it.get("_kind") != "empty":
                return _value(M, it, "authors", inh, people, ctx, vols)
            return _item_value(M, lab, key, inh)
        side = _side(M, it, inh)
        one = [it] + list(it.get("_ctx") or [])
        if key in ("l_refs", "l_content"):
            return _item_value(M, lab, key, inh, Ls=one) if side == "L" else ""
        if side == "M":
            return _item_value(M, lab, key, inh, Ms=one)
        return _factors(M, [it], inh) if key == "m_refs" else ""
    if it.get("_kind") == "empty":
        vol = (vols or {}).get(it["map"], "")
        d = _deliv(ctx, vol)
        o = next((o for o in M.outline if C.outline_label(o) == it["map"]), None)
        return {"section": it["map"], "volume": vol, "text": "(nothing assigned yet)", "role": "Proposal section",
                "section_no": o.get("num", "") if o else "", "section_name": (o.get("title", "") if o else "") or it["map"],
                "deliverable": d["name"] if d else "", "page_limit": d.get("limit", "") if d else "",
                "format": d.get("format", "") if d else "", "order": it.get("_order", "")}.get(key, "")
    if key == "order":
        return it.get("_order", "")
    if key in ("reference", "doc", "lm", "doc_type"):              # 2.68.0
        if key == "doc":
            return SD.initial_of(M, it)
        if key == "doc_type":
            return (SD.docs_of(M).get(it.get("file", "")) or {}).get("type", "")
        lm = SD.lm_of(M, it, inh)
        if not lm and it.get("decision") == "Context":            # support takes the L and M of what it supports
            byid = {x["id"]: x for x in M.items}
            lm = "/".join(dict.fromkeys(SD.lm_of(M, byid[h], inh) for h in C.cf_ids(it.get("context_for", ""))
                                        if h in byid and SD.lm_of(M, byid[h], inh)))
        if key == "lm":
            return "L/M" if it.get("lm_both") and lm == "L" else lm      # 3.90.0: both, as the outline workbook said
        return SD.full_ref(M, dict(it, lm=lm) if lm and "/" not in lm else it, inh)
    if key == "ref":
        return SD.ref_of(M, it, inh)[0] or _where(it, M) or it["id"]
    if key in ("volume", "deliverable", "page_limit", "format"):
        vol = (vols or {}).get(it.get("map", ""), "")
        if key == "volume":
            return vol
        d = _deliv(ctx, vol)
        return (d.get({"deliverable": "name", "page_limit": "limit", "format": "format"}[key], "") if d else "")
    if key == "evaluated_by":                   # 3.16.0: the Section M factors the crosswalk ties its instruction to
        num = it.get("section", "") or SD.ref_of(M, it, inh)[0]
        xw = _crosswalk(M)
        while num:
            if num in xw:
                return "; ".join(f"{r} {t}".strip() for r, t in xw[num])
            num = num.rsplit(".", 1)[0] if "." in num else ""
        return ""
    if key == "far":
        return "; ".join(dict.fromkeys(" ".join(m.group(0).split()) for m in _FAR.finditer(it.get("text", ""))))
    if key in ("topic", "objective", "keypoints", "excerpt"):      # 3.29.0: what review feeds the matrix
        rec = (ctx or {}).get("record") or {}
        if key == "topic":
            names = {t.get("id"): t.get("name", "") for t in rec.get("topics", []) if isinstance(t, dict)}
            return "; ".join(names[x] for x in (rec.get("topic_tags", {}).get(it["id"]) or []) if x in names)
        xs = [x for x in rec.get("excerpts", []) if isinstance(x, dict)]
        mine = [x for x in xs if any(p.get("sid") == it["id"] for p in x.get("parts", []))]
        import excerpts as EX
        if key == "objective":
            sec = it.get("map", "")
            objs = [x for x in xs if x.get("bin") == "objective" and (x in mine or (sec and sec in (x.get("sections") or [])))]
            return "\n".join(f"\u201c{EX.text_of(x)}\u201d ({EX.where_of(x)})" for x in objs)
        if key == "keypoints":
            return "\n".join(EX.text_of(x) + (f" ({x['note']})" if x.get("note") else "") for x in mine if x.get("bin") == "keypoint")
        src = "; ".join(dict.fromkeys(EX.where_of(x) for x in mine if EX.where_of(x)))
        return src or " ".join(b for b in (it.get("file", ""), _where(it, M)) if b)
    if key.startswith(CUSTOM):
        return (it.get("cols") or {}).get(key[len(CUSTOM):], "")
    if key == "rfp_section":
        return " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
    if key == "rfp_ref":                        # 2.56.0: the RFP's section number and title as written (else where it is)
        num = it.get("section", "") or SD.ref_of(M, it, inh)[0]
        return " ".join(x for x in (num, it.get("section_title", "")) if x) or _where(it, M) or it["id"]
    if key in ("section_no", "section_name"):
        lab = it.get("map", "")
        o = next((o for o in M.outline if C.outline_label(o) == lab), None)
        if o is None:
            return lab if key == "section_name" else ""
        return o.get("num", "") if key == "section_no" else (o.get("title", "") or lab)
    if key == "authors":
        own = SD.split_names(it.get("owner", ""))
        if own:
            return ", ".join(own)
        p = SD.section_people(M, it.get("map", "")) if it.get("map") else {}
        names = [p.get("lead", "")] + [x.strip() for x in (p.get("with", "") or "").split(",")]
        return ", ".join(dict.fromkeys(n for n in names if n))
    if key == "text":
        base = ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", "")
        if it.get("_ctx"):                       # 2.58.0: its support in the same cell, each with where it is in the RFP
            base += "\n\nSupporting context:" + "".join(f"\n({ctx_ref(M, c, inh)}) " + _value(M, c, "text", inh, people, ctx, vols)
                                                          for c in it["_ctx"])
        return base
    if key == "role":                           # 2.52.0: a support row says which requirement it supports
        if it.get("decision") == "Context":
            host = it.get("_host") or (C.cf_ids(it.get("context_for", "")) or [""])[0]
            return f"Support for {host}" if host else ("Support for " + it["map"] if it.get("map") else "Support")
        return C.LABEL.get(it.get("decision", ""), "Not used")
    if key == "section":
        return it.get("map", "")
    if key == "lead":
        m = it.get("map", "")
        if m not in people:
            people[m] = SD.section_people(M, m).get("lead", "") if m else ""
        return people[m]
    if key == "owner":
        return SD.owner_of(M, it)
    if key == "page":
        return it.get("response_page", "")
    if key == "status":
        return it.get("status", "")
    if key == "notes":
        return it.get("notes", "")
    if key == "context_for":
        return it.get("context_for", "")
    if key == "source":
        return it.get("file", "")
    if key == "location":
        w = _where(it, M) if it.get("place") else ""
        if w:
            return w
        p = it.get("page")
        return f"p.{p}" if p else (it.get("loc", "").split("(", 1)[-1].rstrip(")") if "(" in it.get("loc", "") else "")
    if key == "strength":
        return it.get("strength", "")
    if key == "type":
        return it.get("type", "")
    if key == "id":
        return it.get("id", "")
    return ""


def ctx_ref(M, it, inh=None):
    """Where a support sentence is in the RFP, for its requirement's cell: its RFP section number (else the heading
    number or the heading name) and its page: "L.4.2, p.3"; "Technical Approach, p.3"; "p.3, para 2"."""
    import setupdoc as SD
    inh = inh if inh is not None else SD.inherited_sections(M)
    num = it.get("section", "") or SD.ref_of(M, it, inh)[0]
    sec = num or it.get("section_title", "")
    w = _where(it, M)
    pg = w.split(",")[0] if w else (f"p.{it['page']}" if it.get("page") else "")
    return ", ".join(x for x in (sec, pg if sec else w) if x) or it.get("id", "")


def _fold(out):
    """Support rows into their requirement's row (context in the requirement's cell, 2.58.0). A support sentence that
    supports several requirements is in each of their cells. Support for a section only keeps a row of its own."""
    res = []
    for it in out:
        if it.get("_kind") == "ctx" and it.get("_host") and res and res[-1].get("_kind") == "req":
            res[-1].setdefault("_ctx", []).append(it)
            continue
        res.append(it)
    return res


def rows(M, design, ctx=None):
    """The matrix rows (2.51.0): our structure's sections in outline order; in each, the compliance requirements in
    the order they appear in the RFP, each followed by the Context rows that support it (in document order); Context
    for the section without a requirement after them; a section with nothing assigned yet keeps one row so it is not
    lost. Every row gets an Order number (sort on it to get this layout back). Returns (items, [[value, ...]]); an
    item's "_kind" is "req", "ctx" (supports the row above) or "empty"."""
    import setupdoc as SD, compliance as C
    if design.get("layout") == "outline":
        return outline_rows(M, design, ctx)
    labels = [C.outline_label(o) for o in M.outline]
    pos0 = {it.get("id"): i for i, it in enumerate(M.items)}
    roles = design["roles"]
    # 2.56.0: a sentence in several sections is a row in each of them (one row per section)
    keep = SD.expand(M, [it for it in M.items if it.get("decision") == "Keep" and "Keep" in roles
                         and not it.get("left_out")])           # 4.3.0: left out on Place: on its own sheet
    ctxs = SD.expand(M, [it for it in M.items if it.get("decision") == "Context" and "Context" in roles])
    pos = {id(it): (pos0.get(it.get("id"), 0), 1 if it.get("_also") else 0) for it in keep + ctxs}
    keep_ids = {it["id"] for it in keep}
    under, loose = {}, []
    for it in ctxs:
        if it.get("_also") and it.get("context_for"):
            continue                                  # support for requirements follows its requirements, not copies
        hosts = [h for h in C.cf_ids(it.get("context_for", "")) if h in keep_ids]
        for host in hosts:                            # 2.58.0: under every requirement it supports, repeated
            under.setdefault(host, []).append(it)
        if not hosts:
            loose.append(it)
    by_sec = {}
    for it in keep + loose:
        by_sec.setdefault(it.get("map", ""), []).append(it)
    out = []
    if design.get("order", "rfp") == "rfp":
        # 2.54.0: the RFP's order: requirements as the customer wrote them (file by file, top to bottom), each with its
        # support under it; support for a section and nothing else sits where it is in the RFP; proposal sections with
        # nothing assigned yet come last
        for it in sorted(keep + loose, key=lambda x: pos[id(x)]):
            out.append(dict(it, _kind="req" if it.get("decision") == "Keep" else "ctx"))
            if it.get("decision") == "Keep":
                for c in sorted(under.get(it["id"], []), key=lambda x: pos[id(x)]):
                    out.append(dict(c, _kind="ctx", _host=it["id"], map=it.get("map", c.get("map", ""))))
        if design.get("empty_sections", True):
            used = {it.get("map", "") for it in keep + loose}
            par = {labels[i] for i, o in enumerate(M.outline) if i + 1 < len(M.outline) and M.outline[i + 1].get("level", 1) > o.get("level", 1)}
            out += [{"_kind": "empty", "map": lab, "id": "", "decision": ""} for lab in labels if lab not in used and lab not in par]
        if design.get("context", "cell") == "cell":
            out = _fold(out)
        for n, it in enumerate(out, 1):
            it["_order"] = n
        inh = SD.inherited_sections(M)
        vols = volume_map(M)
        people = {}
        return out, [[_value(M, it, c["key"], inh, people, ctx, vols) for c in design["columns"]] for it in out]
    order = labels + [s for s in sorted(by_sec, key=lambda s: min(pos[id(x)] for x in by_sec[s])) if s not in labels]
    parents = set()
    for i, o in enumerate(M.outline):
        nxt = M.outline[i + 1] if i + 1 < len(M.outline) else None
        if nxt is not None and nxt.get("level", 1) > o.get("level", 1):
            parents.add(labels[i])
    for sec in order:
        group = sorted(by_sec.get(sec, []), key=lambda x: (x.get("decision") != "Keep", pos[id(x)]))
        if not group:
            if design.get("empty_sections", True) and sec in labels and sec not in parents:
                out.append({"_kind": "empty", "map": sec, "id": "", "decision": ""})
            continue
        for it in group:                          # copies: the matrix's own rows are not touched
            out.append(dict(it, _kind="req" if it.get("decision") == "Keep" else "ctx"))
            if it.get("decision") == "Keep":
                for c in sorted(under.get(it["id"], []), key=lambda x: pos[id(x)]):
                    out.append(dict(c, _kind="ctx", _host=it["id"], map=it.get("map", c.get("map", ""))))
    if design.get("context", "cell") == "cell":
        out = _fold(out)
    for n, it in enumerate(out, 1):
        it["_order"] = n
    inh = SD.inherited_sections(M)
    vols = volume_map(M)
    people = {}
    return out, [[_value(M, it, c["key"], inh, people, ctx, vols) for c in design["columns"]] for it in out]


def outline_rows(M, design, ctx=None):
    """3.35.0 the outline matrix: one row per item of the response outline (section, header, subheader), in outline
    order. A row holds the item's own values (assigned to, initial page allocation, % complete) and the sentences in it,
    Section L (every requirement not designated M) beside Section M, each in the RFP's order. A sentence in several
    items is in each of their rows. Items with nothing in them keep their row unless the design leaves them out.
    Returns (items, [[value, ...]]); an item's "_kind" is "item"."""
    import setupdoc as SD, compliance as C
    inh = SD.inherited_sections(M)
    roles = design["roles"]
    pos = {it.get("id"): i for i, it in enumerate(M.items)}
    secmap = {}
    for it in M.items:
        if it.get("decision") in ("Keep", "Context") and it.get("decision") in roles and not it.get("left_out"):
            for lab in SD.item_sections(M, it):
                secmap.setdefault(lab, []).append(it)
    labels = [C.outline_label(o) for o in M.outline]
    parents = {labels[i] for i, o in enumerate(M.outline) if i + 1 < len(M.outline)
               and M.outline[i + 1].get("level", 1) > o.get("level", 1)}
    out = []
    for o, lab in zip(M.outline, labels):
        its = sorted(secmap.get(lab, []), key=lambda x: (x.get("decision") != "Keep", pos.get(x.get("id"), 0)))
        if not its and not design.get("empty_sections", True) and lab not in parents:
            continue
        Ls = [x for x in its if _side(M, x, inh) == "L"]
        Ms = [x for x in its if _side(M, x, inh) == "M" or x.get("lm_both")]     # 3.90.0: a workbook's L and M sentence
        out.append({"_kind": "item", "map": lab, "id": "", "decision": "", "_level": int(o.get("level", 1) or 1),
                    "_L": Ls, "_M": Ms, "_parent": lab in parents})
    loose = [it for it in M.items if it.get("decision") == "Keep" and "Keep" in roles and not SD.item_sections(M, it)
             and not it.get("left_out")]
    if loose:                                     # requirements in no item yet are never left out of the matrix
        loose.sort(key=lambda x: pos.get(x.get("id"), 0))
        out.append({"_kind": "item", "map": "", "id": "", "decision": "", "_level": 1, "_unplaced": True,
                    "_L": [x for x in loose if _side(M, x, inh) == "L"], "_M": [x for x in loose if _side(M, x, inh) == "M"]})
    for n, it in enumerate(out, 1):
        it["_order"] = n
    vols = volume_map(M)
    people = {}
    return out, [[_value(M, it, c["key"], inh, people, ctx, vols) for c in design["columns"]] for it in out]


UNPLACED = "Not in the outline yet"


def left_out_rows(M):
    """4.3.0: [(piece, reason)] left out of the matrix on Place."""
    return [(it, it["left_out"]) for it in M.items if it.get("left_out")]


def customer_rows(M):
    import setupdoc as SD
    inh = SD.inherited_sections(M)
    return [[SD.ref_of(M, it, inh)[0] or it.get("section", "") or it["id"], _value(M, it, "text", inh, {}), it.get("file", ""),
             _value(M, it, "location", inh, {})] for it in M.items if it.get("decision") == "Customer"]


def preview(M, design, n=None, ctx=None):
    """Headings, rows and the count; 2.51.0: every row unless n is given."""
    _items, r = rows(M, design, ctx)
    return [c["heading"] for c in design["columns"]], (r if n is None else r[:n]), len(r)


def export(M, path, design, effort_name="", when=None, ctx=None):
    """Write the designed compliance matrix workbook. Returns {"path", "rows", "customer"}."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    when = when or datetime.datetime.now()
    design = clean(design)
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"
    title = design["title"] or f"{effort_name or M.name}: Compliance Matrix"
    ws.append([title])
    ws["A1"].font = Font(bold=True, size=14, color="1E3A8A")
    ws.append([f"Built {when:%B %d, %Y %H:%M} from the decisions in Stationkeeper. "
               + ", ".join(lab for r, lab in ROLES if r in design["roles"]) + "."])
    ws["A2"].font = Font(italic=True, color="475569")
    ws.append([])
    items, data = rows(M, design, ctx)
    _table(ws, design, items, data)
    # 2.68.0: a tab for each volume, with the rows in that volume's sections (the first tab keeps every row)
    vols = volume_map(M)
    mode, _n, heads_ = __import__("setupdoc").volumes_of(M)
    tabs = []
    if mode == "several" and len(heads_) > 1:
        for v in heads_:
            pick = [k for k, it in enumerate(items) if vols.get(it.get("map", "")) == v]
            if not pick:
                continue
            name = _sheet_name(v, [ws.title] + [t.title for t in tabs])
            vs = wb.create_sheet(name)
            vs.append([f"{title}: {v}"])
            vs["A1"].font = Font(bold=True, size=14, color="1E3A8A")
            vs.append([f"The rows in {v}. Built {when:%B %d, %Y %H:%M}."])
            vs["A2"].font = Font(italic=True, color="475569")
            vs.append([])
            _table(vs, design, [items[k] for k in pick], [data[k] for k in pick])
            tabs.append(vs)
    cust = customer_rows(M) if design["customer_sheet"] else []
    if design["customer_sheet"]:
        cs = wb.create_sheet("Customer's")
        cs.append(["Pieces that read like requirements but are the customer's to act on. Identified, not answered."])
        cs["A1"].font = Font(italic=True, color="475569")
        cs.append(["RFP reference", "Sentence", "Source document", "Location in the document"])
        for cell in cs[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="7E22CE")
        for r in cust:
            cs.append(r)
            for cell in cs[cs.max_row]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for col, w in zip("ABCD", (16, 80, 28, 20)):
            cs.column_dimensions[col].width = w
    outs = [(it, why) for it, why in left_out_rows(M)]
    if outs:                                      # 4.3.0: left out of the matrix on Place, each with its reason
        ls = wb.create_sheet("Left out")
        ls.append(["Requirements left out of the matrix on Matrix & Outline > Place, each with its reason."])
        ls["A1"].font = Font(italic=True, color="475569")
        ls.append(["ID", "Requirement", "Reason", "Source document"])
        for cell in ls[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="64748B")
        for it, why in outs:
            ls.append([it.get("id", ""), it.get("text", ""), why, it.get("file", "")])
            for cell in ls[ls.max_row]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for col, w in zip("ABCD", (14, 80, 36, 28)):
            ls.column_dimensions[col].width = w
    ab = wb.create_sheet("About")
    c = M.counts()
    for r in (["Effort", effort_name or M.name], ["Built", f"{when:%Y-%m-%d %H:%M}"],
              ["Compliance requirements", c["Keep"]], ["Context", c["Context"]], ["Customer's", c.get("Customer", 0)],
              ["Not used", c[""] + c["Drop"]], ["Rows in this matrix", len(data)],
              ["Note", "Built by Stationkeeper from the compliance decisions; the working matrix stays in Stationkeeper. "
                       "This workbook holds customer content: keep it on this PC or SharePoint."]):
        ab.append(r)
    ab.column_dimensions["A"].width = 26
    ab.column_dimensions["B"].width = 90
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    wb.save(tmp)
    os.replace(tmp, path)
    return {"path": path, "rows": len(data), "customer": len(cust), "left_out": len(outs)}


def _sheet_name(v, taken):
    """An Excel tab name for a volume: 31 characters, none of []:*?/\\, not taken."""
    base = "".join(ch for ch in v if ch not in '[]:*?/\\').strip()[:31] or "Volume"
    name, k = base, 2
    while name in taken:
        name = f"{base[:27]} ({k})"
        k += 1
    return name


def _table(ws, design, items, data):
    """The heading row (row 4) and the rows, styled: a requirement and its support read as one block."""
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    heads = [c["heading"] for c in design["columns"]]
    ws.append(heads)
    thin = Side(style="thin", color="CBD5E1")
    for k, cell in enumerate(ws[4], 1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1E3A8A")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        ws.column_dimensions[cell.column_letter].width = width_of(design["columns"][k - 1]["key"])
    # 2.51.0: a requirement and the Context rows under it read as one block: Context rows lighter, indented, with no
    # line between them and the requirement; a section with nothing assigned yet is gray and italic
    ctx_fill, empty_fill = PatternFill("solid", fgColor="F1F5F9"), PatternFill("solid", fgColor="FAFAFA")
    none = Side(style=None)
    text_col = next((k for k, c in enumerate(design["columns"]) if c["key"] == "text"), None)
    import compliance as _C
    import cwords as _CW
    cw = _CW.load()                                  # 2.52.0: compliance words in the team's style, as on screen
    for i, (it, r) in enumerate(zip(items, data)):
        ws.append([_C.clean_chars(v) for v in r])
        if text_col is not None and it.get("_kind") in ("req", "ctx"):
            ws.cell(row=ws.max_row, column=text_col + 1).value = _CW.xlsx_value(_C.clean_chars(r[text_col]), cw)
        kind = it.get("_kind")
        nxt = items[i + 1].get("_kind") if i + 1 < len(items) else None
        attached_below = nxt == "ctx" and items[i + 1].get("_host") in (it.get("id"), it.get("_host"))
        if kind == "item":                                   # 3.35.0: the outline matrix: the item indented by level
            lvl = max(1, it.get("_level", 1))
            for k, cell in enumerate(ws[ws.max_row]):
                key = design["columns"][k]["key"]
                if key in ("l_content", "m_content") and r[k]:      # compliance words in the team's style
                    cell.value = _CW.xlsx_value(_C.clean_chars(r[k]), cw)
                cell.alignment = Alignment(vertical="top", wrap_text=True, indent=(lvl - 1) * 2 if key == "item" else 0)
                cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
                if lvl == 1:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill("solid", fgColor="EEF2FF")
                elif it.get("_parent"):
                    cell.font = Font(bold=True)
            continue
        for k, cell in enumerate(ws[ws.max_row]):
            cell.alignment = Alignment(vertical="top", wrap_text=True, indent=2 if (kind == "ctx" and k == text_col) else 0)
            cell.border = Border(top=none if (kind == "ctx" and it.get("_host")) else thin,
                                 bottom=none if attached_below else thin, left=thin, right=thin)
            if kind == "ctx":
                cell.fill = ctx_fill
                cell.font = Font(color="475569", size=10)
            elif kind == "empty":
                cell.fill = empty_fill
                cell.font = Font(color="94A3B8", italic=True)
    ws.freeze_panes = "A5"
    if data:
        ws.auto_filter.ref = f"A4:{ws.cell(row=4, column=len(heads)).column_letter}{ws.max_row}"
    ws.print_title_rows = "4:4"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0


def safe_name(name):
    """A file or folder name Windows accepts (2.50.0: an effort name with / or : broke the export)."""
    return "".join(ch if ch not in '<>:"/\\|?*' and ord(ch) >= 32 else " " for ch in name).strip().rstrip(".") or "export"


def long_path(path):
    """2.50.0: deep OneDrive or SharePoint folders pass Windows' 260-character limit; the long-path form has none."""
    p = os.path.abspath(path)
    if os.name == "nt" and len(p) > 200 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + p if not p.startswith("\\\\") else "\\\\?\\UNC\\" + p[2:]
    return path


def export_together(M, folder, design, effort_name="", when=None, ctx=None):
    """The designed matrix and the Response Setup, from the same decisions, in one dated folder. Returns the folder and
    the files written."""
    import setupdoc as SD
    when = when or datetime.datetime.now()
    name = f"{(effort_name or M.name)} compliance export {when:%Y-%m-%d %H%M}"
    name = safe_name(name)
    sub = long_path(os.path.join(folder, name))
    k = 2
    while os.path.exists(sub):
        sub = os.path.join(folder, f"{name} ({k})"); k += 1
    os.makedirs(sub)
    mx = export(M, os.path.join(sub, safe_name(f"{(effort_name or M.name).replace(' ', '_')}_Compliance_Matrix_{when:%Y-%m-%d}.xlsx")),
                design, effort_name, when, ctx)
    files = [mx["path"]]
    if M.outline:
        files += SD.export(M, sub, when)
    return {"folder": sub, "files": files, "rows": mx["rows"]}


def effort_ctx(ws):
    """What the matrix takes from the effort, without a screen (2.61.0, the Qt edition): each deliverable's name, page
    limit and format, from the effort record, the submission requirements and the named volumes."""
    out = {"deliverables": []}
    if ws is None:
        return out
    try:
        import effortrec as R, deliverables as DL, docversions as DV, subreq as SR
        r = R.Record(ws.root)
        lib = DV.Library(ws.p("documents")).load()
        rows = SR.Register(lib).rows() if lib.docs else []
        vols = [x for x in (ws.get("volumes", []) or []) if isinstance(x, dict) and x.get("name")]
        for d in DL.items(r):
            sp = {x["field"]: x["value"] for x in DL.spec(d, rows, vols)}
            fmt = "; ".join(f"{f}: {sp[f]}" for f in ("Font", "Margins", "Page size", "Line spacing", "File format") if sp.get(f))
            out["deliverables"].append({"name": d["name"], "limit": sp.get("Page limit") or d.get("limit", ""),
                                        "format": fmt or d.get("format", "")})
        out["record"] = {k: r.data.get(k) or ([] if k != "topic_tags" else {})        # 3.29.0: topics, objectives,
                         for k in ("topics", "topic_tags", "excerpts")}               # key points, excerpts
    except Exception:
        import diag
        diag.swallowed()
    return out
