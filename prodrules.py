"""Production standards (3.6.0): one model for checking and fixing, in three layers that the person controls value by
value: the team standard, a document type (proposal volume, cost volume, customer deliverable...), and this effort
(the RFP's rules). A layer keeps only what it changes; everything else comes from the layer below. Blank means
"not set": a rule nobody sets is not checked and not written.

The model is the format engine's (prodengine.pe.rules) plus what production needs on top of it:
  styles             allowed styles, hide unused built-ins, remove unused custom styles, merge styles from a template,
                     write the format variables into the styles they drive
  heading_numbering  the nine heading levels: format, number text, number and text positions, restarts
  checks             Format Check options (TOC switches never used, page number fields, caption fields, table caption
                     placement, landscape sections)
Saved in the config folder (production_standards.json); the effort's layer lives in the effort's settings.
"""
import copy, json, os, re

from prodengine.pe import rules as PR
from prodengine.engine.ops import word_ops as WO

FILE = "production_standards.json"
SCOPES = ("body", "heading", "table", "caption", "header_footer", "footnote", "graphic")
SCOPE_NAMES = {"body": "Body text", "heading": "Headings", "table": "Text in tables", "caption": "Captions",
               "header_footer": "Headers and footers", "footnote": "Footnotes", "graphic": "Text in graphics"}
VAR_FOR_SCOPE = {"body": ("body_font", "body_size"), "table": ("table_font", "table_size"),
                 "caption": ("caption_font", "caption_size")}
# header and footer tokens that name one volume or one effort (filled from the effort and the file, never stored)
HF_TOKENS = {"volume_name": "Volume name", "solicitation": "Solicitation", "company": "Company",
             "classification": "Classification", "project": "Project"}
PAGE_SIZES = {"Letter": (8.5, 11), "A4": (8.27, 11.69), "Legal": (8.5, 14), "Tabloid": (11, 17)}


def _company_default():
    c = copy.deepcopy(PR.COMPANY)
    c["fonts"] = {k: {"min_size": None, "max_size": None, "fonts": None, "rfp_ref": ""} for k in SCOPES}
    c["styles"] = {"allowed": [], "hide_unused_builtin": False, "remove_unused_custom": False, "template": "",
                   "apply_variables": True}
    c["style_defs"] = {}               # 3.7.0: the style library, {style: {prop: value}}; blank = not checked
    c["table_styles"] = {}             # 3.10.0: Word table styles, {name: {"xml", "based_on"}}
    c["page_parts"] = {}               # 3.10.0: {"cover": file, "backer": file} in production_parts
    c["quick_parts"] = {"one_gallery": True, "entries": []}
    c["fill_ins"] = []
    c["hf_designs"] = {}               # 3.24.0: {part: header and footer kept whole} from the template library                 # 3.23.0: tokens typed once: a cover style (STYLEREF) or a document property    # 3.22.0: the Quick Parts a template carries, from files in production_parts
    c["list_numbering"] = {"on": False, "lists": [   # 3.9.0: what each list style shows, level by level (inches)
        {"name": "Bullets", "levels": [
            {"style": "List Bullet", "fmt": "bullet", "text": "\u2022", "font": "", "left": 0.25, "hanging": 0.25},
            {"style": "List Bullet 2", "fmt": "bullet", "text": "\u2013", "font": "", "left": 0.5, "hanging": 0.25},
            {"style": "List Bullet 3", "fmt": "bullet", "text": "\u25aa", "font": "", "left": 0.75, "hanging": 0.25}]},
        {"name": "Numbers", "levels": [
            {"style": "List Number", "fmt": "decimal", "text": "%1.", "font": "", "left": 0.25, "hanging": 0.25},
            {"style": "List Number 2", "fmt": "lowerLetter", "text": "%2.", "font": "", "left": 0.5, "hanging": 0.25},
            {"style": "List Number 3", "fmt": "lowerRoman", "text": "%3.", "font": "", "left": 0.75, "hanging": 0.25}]}]}
    c["excel"] = {"font": "", "size": None, "header": {"bold": True, "fill": "", "color": ""}, "freeze_header": True,   # 3.11.0
                  "print": {"orientation": "", "fit_width": True, "repeat_header": True, "footer_page": True, "marking": False}}
    c["powerpoint"] = {"fonts": "", "min_size": 12, "title_min_size": None, "slide_size": "", "marking": False, "titles": True}
    import prodgraphics as _PG                        # 3.17.0: graphics standards
    c["graphics"] = dict(_PG.DEFAULT)
    c["heading_numbering"] = {"on": False, "levels": [
        {"style": s, "fmt": f, "text": t, "number_at": a, "text_at": b, "restart": r} for (s, f, t, a, b, r) in WO.HEADING_LEVELS]}
    c["checks"] = {"toc_forbid": ["\\o", "\\u"], "page_numbers": True, "caption_fields": True,
                   "table_caption_position": "first row", "landscape_ok": True}
    c["pagination"] = presets()["team"]
    c["hf_layouts"]["backer"] = {"header": {}, "footer": {}}
    # values that belong to one volume or one effort are never part of a standard: they come from the effort and the
    # file each time (context below), so no sample value can ever be typed into a real copy
    c["variables"].update({k: "" for k in HF_TOKENS})
    t = c["terms"]
    t["banned"] = []                    # the team's Banned Phrases list is added for each run
    t["replace"] = [r for r in t["replace"] if r.get("why") == "Common misspelling"]
    t["lists"] = {k: [] for k in t["lists"]}   # dictionaries, author list and the effort's acronyms are added for each run
    c["name"] = "Team standard"
    return c


BACKER = {"key": "backer", "name": "Back cover", "starts": {"last_section": True, "styles": ["Back Cover", "Backer"]},
          "numbers": None, "header": "", "footer_marking": False, "linked": False}


def presets():
    """The engine's page schemes, each with a back cover part. A back cover is recognised only as the last section
    starting with one of its styles, so a volume without one never loses page numbers on its last pages."""
    out = copy.deepcopy(PR.PAGINATION_PRESETS)
    for p in out.values():
        if not any(x["key"] == "backer" for x in p["parts"]):
            p["parts"].append(copy.deepcopy(BACKER))
    return out


COMPANY = _company_default()


# ------------------------------------------------------------------ layers
def diff(edited, base):
    """What edited changes against base: a layer holding only those values. Lists are compared whole."""
    if isinstance(edited, dict) and isinstance(base, dict):
        out = {}
        for k, v in edited.items():
            if k not in base:
                out[k] = copy.deepcopy(v)
            elif v != base[k]:
                d = diff(v, base[k])
                if d != {} or not isinstance(v, dict):
                    out[k] = d
        return out
    return copy.deepcopy(edited)


def merge(base, over):
    return PR.deep_merge(base, over or {})


STARTER_EFFORT_TYPES = [("rfp", "RFP response"), ("rfp_limited", "Page-limited RFP response"), ("rfi", "RFI response"),
                        ("white_paper", "White paper"), ("program", "Program deliverables")]     # 3.18.2: RFI response
NEW_STARTERS = ("rfi",)                          # 3.18.2: starters an older file gains once
PROFILE_KEYS = ("id", "name", "match")            # a profile's own fields; everything else is its layer
EFFORT_TYPE_KEYS = ("id", "name", "profiles", "default_profile", "profile_over", "matrix_view")   # 3.35.0: its starting matrix view


def load(config_dir):
    """3.8.0: {"company": the team standard, "types": [document profiles {"id", "name", "match": [words], ...layer}],
    "default": profile id, "effort_types": [{"id", "name", "profiles": [ids], "default_profile": id,
    "profile_over": {profile id: layer}, ...shared layer}], "default_effort_type": id}.
    A 3.5 file becomes profiles with the same values; a 3.6 or 3.7 file keeps its profiles and gains the starter
    effort types (RFP response, page-limited RFP response, white paper, program deliverables), each holding every
    profile and changing nothing until edited."""
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    if d and d.get("version") not in (2, 3):
        d = migrate_35(d)
    company = merge(COMPANY, d.get("company") or {})
    types = [t for t in d.get("types", []) if isinstance(t, dict) and t.get("id")]
    if not types:
        types = [{"id": "proposal", "name": "Proposal volume"}]
    ids = [t["id"] for t in types]
    default = d.get("default") if d.get("default") in ids else ids[0]
    ets = [e for e in d.get("effort_types", []) if isinstance(e, dict) and e.get("id")] if d.get("version") == 3 else []
    if d.get("version") != 3 and not ets:
        ets = [{"id": i, "name": n, "profiles": list(ids), "default_profile": default} for i, n in STARTER_EFFORT_TYPES]
    for e in ets:
        e["profiles"] = [p for p in (e.get("profiles") or []) if p in ids] or [default]
        if e.get("default_profile") not in e["profiles"]:
            e["default_profile"] = e["profiles"][0]
        e["profile_over"] = {k: v for k, v in (e.get("profile_over") or {}).items() if k in ids}
    removed = [str(x) for x in d.get("removed_effort_types", []) if x]
    if d.get("version") == 3 and int(d.get("starters", 1) or 1) < 2:    # 3.18.2: RFI response joins an older file once
        have = {e["id"] for e in ets}
        for k, (i, n) in enumerate(STARTER_EFFORT_TYPES):
            if i in NEW_STARTERS and i not in have and i not in removed and not any(e["name"].casefold() == n.casefold() for e in ets):
                ets.insert(min(k, len(ets)), {"id": i, "name": n, "profiles": list(ids), "default_profile": default,
                                              "profile_over": {}})
    eids = [e["id"] for e in ets]
    return {"version": 3, "company": company, "types": types, "default": default, "effort_types": ets,
            "default_effort_type": d.get("default_effort_type") if d.get("default_effort_type") in eids else "",
            "removed_effort_types": removed}


def save(config_dir, data):
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    body = {"version": 3, "company": diff(data["company"], COMPANY), "types": data["types"], "default": data.get("default", ""),
            "effort_types": data.get("effort_types", []), "default_effort_type": data.get("default_effort_type", ""),
            "removed_effort_types": data.get("removed_effort_types", []), "starters": 2}
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(body, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def type_of(data, tid):
    return next((t for t in data["types"] if t["id"] == tid), data["types"][0])


def layer_of(t):
    return {k: v for k, v in t.items() if k not in PROFILE_KEYS}


def effort_type_of(data, eid):
    """The effort type, or None (no effort types, or an unknown id)."""
    return next((e for e in data.get("effort_types", []) if e["id"] == eid), None)


# ------------------------------------------------------------------ 3.18.2: effort types you add, rename and take out
def add_effort_type(data, name):
    """A new effort type holding every profile. Returns it, or None (no name, or the name is taken)."""
    name = " ".join((name or "").split())
    ets = data.setdefault("effort_types", [])
    if not name or any(e["name"].casefold() == name.casefold() for e in ets):
        return None
    e = {"id": slug(name, {x["id"] for x in ets}), "name": name, "profiles": [t["id"] for t in data["types"]],
         "default_profile": data.get("default") or data["types"][0]["id"], "profile_over": {}}
    ets.append(e)
    data["removed_effort_types"] = [x for x in data.get("removed_effort_types", []) if x != e["id"]]
    return e


def rename_effort_type(data, eid, name):
    """A new name; its id (what efforts point at) stays. Returns True when renamed."""
    name = " ".join((name or "").split())
    e = effort_type_of(data, eid)
    if e is None or not name or any(x["name"].casefold() == name.casefold() and x["id"] != eid for x in data.get("effort_types", [])):
        return False
    e["name"] = name
    return True


def remove_effort_type(data, eid):
    """Take an effort type out (a starter one stays out). Efforts that used it keep their own values. Returns True."""
    ets = data.get("effort_types", [])
    if effort_type_of(data, eid) is None:
        return False
    data["effort_types"] = [e for e in ets if e["id"] != eid]
    data.setdefault("removed_effort_types", [])
    if eid not in data["removed_effort_types"]:
        data["removed_effort_types"].append(eid)
    if data.get("default_effort_type") == eid:
        data["default_effort_type"] = ""
    return True


def move_effort_type(data, eid, step):
    ets = data.get("effort_types", [])
    i = next((k for k, e in enumerate(ets) if e["id"] == eid), -1)
    j = i + step
    if i < 0 or not (0 <= j < len(ets)):
        return False
    ets[i], ets[j] = ets[j], ets[i]
    return True


def effort_layer_of(e):
    return {k: v for k, v in (e or {}).items() if k not in EFFORT_TYPE_KEYS}


def resolved_type(data, tid, eid=None):
    """The standard for one profile: the team standard, the profile's changes, then (3.8.0) the effort type's shared
    values and its changes for this profile. An effort type's values win over the profile's: they are the rules of
    that kind of effort (a page-limited RFP's fonts and margins hold for every volume in it)."""
    t = type_of(data, tid)
    std = merge(data["company"], layer_of(t))
    e = effort_type_of(data, eid) if eid else None
    if e is not None:
        std = merge(std, effort_layer_of(e))
        std = merge(std, (e.get("profile_over") or {}).get(t["id"]) or {})
    std["name"] = t["name"]
    return std


def profile_for(data, eid, deliverable_name="", fallback=True):
    """3.8.0: the profile a deliverable takes in an effort type: the first of the effort type's profiles whose match
    words are in the deliverable's name, else the effort type's default profile."""
    e = effort_type_of(data, eid)
    ids = e["profiles"] if e else [t["id"] for t in data["types"]]
    low = (deliverable_name or "").lower()
    for pid in ids:
        words = [w.strip().lower() for w in (type_of(data, pid).get("match") or []) if w.strip()]
        if any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words):
            return pid
    if not fallback:
        return None
    return (e or {}).get("default_profile") or data["default"]


def for_effort(config_dir, ws=None, data=None, type_id=None):
    """The standard in force for the open effort: team -> its profile -> its effort type -> the effort's own values.
    type_id (3.7.0): a deliverable's own profile instead of the effort's."""
    data = data or load(config_dir)
    eff = (ws.get("prod_std", {}) if ws is not None else {}) or {}
    ids = [t["id"] for t in data["types"]]
    eid = eff.get("effort_type") if effort_type_of(data, eff.get("effort_type")) else None
    et = effort_type_of(data, eid)
    eff_default = eff.get("type") if eff.get("type") in ids else ((et or {}).get("default_profile") or data["default"])
    tid = type_id if type_id in ids else eff_default
    std = merge(resolved_type(data, tid, eid), eff.get("over") or {})
    vol = (eff.get("over_vol") or {}).get(tid) or {}                  # 3.36.0: this effort's changes for one volume
    std = merge(std, vol)
    std["name"] = type_of(data, tid)["name"]
    std["effort_type"] = (et or {}).get("name", "")
    std["effort_over"] = bool(eff.get("over") or vol)
    std["_parts_dir"] = os.path.join(config_dir, "production_parts")     # 3.10.0: where covers and back covers are kept
    return engine_ready(std)


def repair_rows(std):
    """3.32.1: every table row look carries the settings the engine reads (its tag style, font, size, spacing...). A
    look taken whole from a file holds only what the file showed; the rest comes from the same role's team default
    (else the body row's). Returns the roles repaired."""
    base = COMPANY.get("row_types") or {}
    fixed = []
    for role, look in list((std.get("row_types") or {}).items()):
        if not isinstance(look, dict):
            continue
        ref = base.get(role) or base.get("body") or {}
        miss = {k: copy.deepcopy(v) for k, v in ref.items() if k not in look}
        if miss:
            look.update(miss)
            fixed.append(role)
    return fixed


def engine_ready(std):
    """The engine's rules read fonts as {min_size, fonts}; blank strings and zeros mean not set."""
    repair_rows(std)
    for k, r in (std.get("fonts") or {}).items():
        for f in ("min_size", "max_size"):
            if r.get(f) in ("", 0, 0.0):
                r[f] = None
        if r.get("fonts") in ("", [], None):
            r["fonts"] = None
        elif isinstance(r.get("fonts"), str):
            r["fonts"] = [x.strip() for x in r["fonts"].split(",") if x.strip()] or None
    return std


def slug(name, taken):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "type"
    out, n = s, 2
    while out in taken:
        out, n = f"{s}_{n}", n + 1
    return out


# ------------------------------------------------------------------ 3.5 files
def migrate_35(d):
    """3.5.0 kept {"types": [{"name", "fonts": {scope: {font, min, max}}, "margins_in", "page", ...}], "default": name}."""
    types, taken = [], set()
    scope_map = {"body": "body", "table": "table", "caption": "caption", "heading": "heading", "header": "header_footer",
                 "footnote": "footnote"}
    default_id = ""
    for t in d.get("types", []):
        if not isinstance(t, dict) or not t.get("name"):
            continue
        tid = slug(t["name"], taken); taken.add(tid)
        layer = {"id": tid, "name": t["name"], "variables": {}, "fonts": {}, "checks": {}}
        for old, new in scope_map.items():
            r = (t.get("fonts") or {}).get(old) or {}
            fr = {}
            if r.get("font"):
                fr["fonts"] = [r["font"]]
            if r.get("min"):
                fr["min_size"] = float(r["min"])
            if r.get("max"):
                fr["max_size"] = float(r["max"])
            if fr:
                layer["fonts"][new] = fr
            if new in VAR_FOR_SCOPE:
                fv, sv = VAR_FOR_SCOPE[new]
                if r.get("font"):
                    layer["variables"][fv] = r["font"]
                if r.get("min"):
                    layer["variables"][sv] = float(r["min"])
        if t.get("margins_in"):
            for side in ("top", "bottom", "left", "right"):
                layer["variables"]["margin_" + side] = float(t["margins_in"])
        if t.get("page"):
            layer["variables"]["paper"] = t["page"]
        for k_old, k_new in (("toc_forbid", "toc_forbid"), ("page_numbers", "page_numbers"), ("caption_fields", "caption_fields"),
                             ("caption_position", "table_caption_position"), ("landscape_ok", "landscape_ok")):
            if k_old in t:
                layer["checks"][k_new] = t[k_old]
        if t.get("caption_numbers") == "plain" or t.get("caption_sep") == "space":
            caps = copy.deepcopy(COMPANY["captions"])
            for c in caps:
                if t.get("caption_numbers") == "plain":
                    c["chapter_level"] = None
                if t.get("caption_sep") == "space":
                    c["after_number"] = "period_space"
            layer["captions"] = caps
        types.append(layer)
        if t["name"] == d.get("default"):
            default_id = tid
    return {"version": 2, "company": {}, "types": types, "default": default_id or (types[0]["id"] if types else "")}


# ------------------------------------------------------------------ the RFP's own rules
def from_rfp(rows):
    """The effort's own values from Submission Rules (kind Format): body and table fonts and sizes, margins, page size.
    Returns ({layer}, [what was read, in words])."""
    over, said = {}, []
    for r in rows:
        subj, val = r.get("subject", ""), r.get("value", "") or ""
        if r.get("kind") != "Format" or not val:
            continue
        if subj in ("Font", "Font in tables and figures"):
            scope = "body" if subj == "Font" else "table"
            m = re.search(r"(\d+(?:\.\d+)?)\s*-?\s*(?:point|pt)", val, re.I)
            face = re.sub(r"(\d+(?:\.\d+)?)\s*-?\s*(?:point|pt)\b", "", val, flags=re.I)
            face = re.sub(r"\b(no smaller|minimum|at least|or larger|or greater|font|type|size)\b", "", face, flags=re.I).strip(" ,;-.")
            fr = over.setdefault("fonts", {}).setdefault(scope, {})
            fv, sv = VAR_FOR_SCOPE[scope]
            if m:
                size = float(m.group(1))
                fr["min_size"] = size
                over.setdefault("variables", {})[sv] = size
                if scope == "table":
                    over["fonts"].setdefault("caption", {})["min_size"] = size
            if face and re.search(r"[A-Za-z]{3,}", face):
                fr["fonts"] = [face]
                over.setdefault("variables", {})[fv] = face
            said.append(f"{subj}: {val}")
        elif subj == "Margins":
            m = re.search(r"(\d+(?:\.\d+)?)", val)
            if m:
                v = over.setdefault("variables", {})
                for side in ("top", "bottom", "left", "right"):
                    v["margin_" + side] = float(m.group(1))
                said.append(f"Margins: {val}")
        elif subj == "Page size":
            over.setdefault("variables", {})["paper"] = "A4" if "a4" in val.lower() else "Letter"
            said.append(f"Page size: {val}")
        elif subj == "Line spacing":
            low = val.lower()
            sp = ("double" if "double" in low or re.search(r"\b2(?:\.0)?\b", low) else
                  "1.5" if re.search(r"1\.5|one and a half|one-and-a-half", low) else
                  "1.15" if "1.15" in low else "single" if "single" in low or re.search(r"\b1(?:\.0)?\b", low) else "")
            if sp:
                over.setdefault("variables", {})["line_spacing"] = sp
                said.append(f"Line spacing: {val}")
    return over, said


# ------------------------------------------------------------------ the effort's and the file's own values
def volume_for(path, rec):
    """The deliverable a draft belongs to (by its file), or None."""
    if not path or rec is None:
        return None
    try:
        import deliverables as DL
        want = os.path.normcase(os.path.realpath(path))
        for d in DL.items(rec):
            f = d.get("file") or ""
            if f and os.path.normcase(os.path.realpath(f)) == want:
                return d
    except Exception:  # noqa: BLE001  no record, or an older one
        return None
    return None


def context(config_dir, effort_name="", info=None, effort_list=None, rec=None, path=""):
    """What a run takes from the effort and the team's lists, never from a stored standard:
      variables  solicitation (the effort's basics), company (Folder plan), volume_name (the deliverable the draft
                 belongs to; blank when the draft is not on the Deliverables board)
      banned     the team's Banned Phrases
      lists      team_terms (the custom dictionaries), employee_names (the author list for this effort), acronyms
                 (the effort's approved acronyms)
    Every source is optional; a source that cannot be read adds nothing."""
    out = {"variables": {}, "banned": [], "lists": {}, "deliverable": None}
    info = info or {}
    if str(info.get("solicitation") or "").strip():
        out["variables"]["solicitation"] = " ".join(str(info["solicitation"]).split())
    try:
        import folderplan as FPL
        comp = FPL.load(config_dir).get("company") or ""
        if comp:
            out["variables"]["company"] = comp
    except Exception:  # noqa: BLE001
        pass
    d = volume_for(path, rec)
    if d:
        out["deliverable"] = {k: d.get(k, "") for k in ("id", "name", "kind", "limit", "format", "doc_type")}
        out["variables"]["volume_name"] = d.get("name", "")
    try:
        import banned as BN
        for r in BN.load():
            if r.get("Phrase"):
                out["banned"].append({"find": r["Phrase"], "suggest": r.get("Use instead", ""),
                                      "why": r.get("Why") or r.get("Level") or "Banned phrase"})
    except Exception:  # noqa: BLE001
        pass
    try:
        import customdict as CD
        words = set()
        for dct in CD.Store(config_dir).dicts:
            words.update(dct.get("words", []))
        out["lists"]["team_terms"] = CD.sort_words(words)
        if effort_list is not None:
            out["lists"]["acronyms"] = CD.from_effort(effort_list)
    except Exception:  # noqa: BLE001
        pass
    try:
        import authorlist as AL
        al = AL.load(config_dir)
        out["lists"]["employee_names"] = al.for_effort(effort_name) if effort_name else al.names()
    except Exception:  # noqa: BLE001
        pass
    return out


def apply_context(std, ctx, volume_name=None):
    """The standard for one file: blank volume values filled from the context (a value a layer sets wins; the volume
    name typed on Fix a Copy wins over both), the team's banned phrases and lists added to the standard's own."""
    std = copy.deepcopy(std)
    v = std.setdefault("variables", {})
    for k, val in (ctx or {}).get("variables", {}).items():
        if val and not str(v.get(k) or "").strip():
            v[k] = val
    if volume_name is not None:
        v["volume_name"] = " ".join(str(volume_name).split())
    t = std.setdefault("terms", copy.deepcopy(COMPANY["terms"]))
    have = {str(b.get("find", "")).casefold() for b in t.get("banned", [])}
    for b in (ctx or {}).get("banned", []):
        if b["find"].casefold() not in have:
            t.setdefault("banned", []).append(b); have.add(b["find"].casefold())
    lists = t.setdefault("lists", {})
    for k, words in (ctx or {}).get("lists", {}).items():
        lists[k] = sorted(set(lists.get(k) or []) | set(words or []), key=str.casefold)
    return std


def _fill_keys(std):
    try:
        import fillins as FI
        return {f["key"] for f in FI.custom(std)}
    except ImportError:
        return set()


def hf_tokens(std):
    """The volume tokens the header and footer layouts and the page scheme use: {token: where}."""
    out = {}
    for part, lay in (std.get("hf_layouts") or {}).items():
        for side in ("header", "footer"):
            for slot, text in (lay.get(side) or {}).items():
                for k in re.findall(r"\{(\w+)\}", text if isinstance(text, str) else ""):
                    if k in HF_TOKENS or k in _fill_keys(std):
                        out.setdefault(k, f"{part} {side}")
    for p in (std.get("pagination") or {}).get("parts", []):
        for k in re.findall(r"\{(\w+)\}", p.get("header") or ""):
            if k in HF_TOKENS:
                out.setdefault(k, f"{p.get('name', p.get('key'))} header")
    return out


def missing_values(std, sources=()):
    """Tokens the layouts use whose value is blank and that the document cannot supply itself (a cover paragraph in
    the token's style, which headers then read through STYLEREF): [token]. Headers and footers are built only when
    this is empty, so a blank or wrong value is never typed into a copy."""
    import fillins as FI
    st, pr = FI.styles(std), FI.props(std)
    return [k for k in hf_tokens(std) if not str(FI.value(std, k) or "").strip() and st.get(k) not in set(sources) and k not in pr]


def page_limit(text):
    """3.7.0: the number of pages in a deliverable's limit ("25 pages", "25-page limit", "30"), or None."""
    m = re.search(r"(\d+)\s*-?\s*(?:pages?|pp\b|page limit)", text or "", re.I) or re.fullmatch(r"\s*(\d+)\s*", text or "")
    return int(m.group(1)) if m else None


def limit_note(limit_text, pages):
    """What Word's page count says against the deliverable's limit, in words, or ""."""
    n = page_limit(limit_text)
    if not n or not pages:
        return ""
    if pages > n:
        return (f"Word counts {pages} pages; the limit is {n} ({limit_text}). Check what the RFP counts (covers, the TOC "
                "and appendices are often excluded).")
    return f"Word counts {pages} pages; the limit is {n} ({limit_text})."


# ------------------------------------------------------------------ Format Check (3.5) reads a flat view
def to_check(std):
    """The 3.5 Format Check view of a standard: one font and a size range per kind of text, smallest margin, page."""
    v = std.get("variables", {})
    fonts = {}
    for scope_35, scope in (("body", "body"), ("table", "table"), ("caption", "caption"), ("heading", "heading"),
                            ("header", "header_footer"), ("footnote", "footnote")):
        r = (std.get("fonts") or {}).get(scope) or {}
        allowed = r.get("fonts") or []
        fv, sv = VAR_FOR_SCOPE.get(scope, (None, None))
        font = allowed[0] if allowed else (v.get(fv) if fv else "") or ""
        lo = r.get("min_size") or (v.get(sv) if sv else 0) or 0
        hi = r.get("max_size") or (lo if (sv and not r.get("min_size")) else 0) or 0
        fonts[scope_35] = {"font": font, "min": lo, "max": hi}
    margins = [v.get("margin_" + s) for s in ("top", "bottom", "left", "right") if v.get("margin_" + s) is not None]
    caps = std.get("captions") or []
    body = next((c for c in caps if c.get("part") == "body"), {})
    ch = std.get("checks") or {}
    return {"name": std.get("name", ""), "fonts": fonts, "margins_in": min(margins) if margins else 0, "page": v.get("paper", ""),
            "landscape_ok": ch.get("landscape_ok", True),
            "caption_numbers": "chapter" if body.get("chapter_level") else "plain",
            "caption_sep": "space" if str(body.get("after_number", "")).endswith("space") else "tab",
            "caption_fields": ch.get("caption_fields", True), "caption_position": ch.get("table_caption_position", "first row"),
            "toc_forbid": list(ch.get("toc_forbid") or []), "page_numbers": ch.get("page_numbers", True)}


# ------------------------------------------------------------------ the styles the variables drive
def variable_style_spec(std):
    """{style: {font, size, after, line}} from the format variables (pe.rules VARIABLE_TARGETS), for op_styles."""
    v = std.get("variables", {})
    spec = {}
    for var, styles in PR.VARIABLE_TARGETS.items():
        val = v.get(var)
        if val in (None, "") or styles == ["page setup"]:
            continue
        for s in styles:
            d = spec.setdefault(s, {})
            if var.endswith("_font"):
                d["font"] = val
            elif var.endswith("_size"):
                d["size"] = float(val)
            elif var == "space_after_body":
                d["after"] = float(val)
            elif var == "line_spacing":
                d["line"] = {"single": 1.0, "1.15": 1.15, "1.5": 1.5, "double": 2.0}.get(str(val), None)
                if d["line"] is None:
                    d.pop("line")
    return spec


def style_spec(std):
    """3.7.0: every style the standard defines, whole: the style library with the format variables on top (the
    variables win, so changing body size in one place changes every style it drives)."""
    spec = {}
    for name, d in (std.get("style_defs") or {}).items():
        props = {k: v for k, v in (d or {}).items() if v not in (None, "")}
        if props:
            spec[name] = props
    if (std.get("styles") or {}).get("apply_variables", True):
        for name, d in variable_style_spec(std).items():
            spec.setdefault(name, {}).update(d)
    return spec


def validate(std):
    out = list(PR.validate(std))
    for name, d in (std.get("style_defs") or {}).items():
        for k in ("size", "before", "after", "line", "left", "right", "first", "hanging"):
            v = (d or {}).get(k)
            if v not in (None, ""):
                try:
                    float(v)
                except (TypeError, ValueError):
                    out.append(f"style {name}: {k} is not a number")
        if (d or {}).get("type", "paragraph") not in ("paragraph", "character"):
            out.append(f"style {name}: unknown type")
    for k, r in (std.get("fonts") or {}).items():
        lo, hi = r.get("min_size"), r.get("max_size")
        if lo and hi and float(lo) > float(hi):
            out.append(f"{SCOPE_NAMES.get(k, k)}: the smallest size is larger than the largest")
    keys = [p["key"] for p in (std.get("pagination") or {}).get("parts", [])]
    if len(set(keys)) != len(keys):
        out.append("two page scheme parts share a key")
    for p in (std.get("pagination") or {}).get("parts", []):
        n = p.get("numbers")
        if n and n.get("fmt") not in PR.PAGE_FORMATS:
            out.append(f"page part {p.get('name')}: unknown number format {n.get('fmt')}")
    return out
