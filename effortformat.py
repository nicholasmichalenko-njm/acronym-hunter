"""Effort Formatting (3.36.0): one effort's formatting on top of the Global Standards, kept apart from them.

The Global Standards (Production Standards: the Global Standards, volume profiles, effort types, the template library)
hold for every effort. An effort keeps its own changes in its workspace: for every volume in it ("over") or for one
volume ("over_vol"[profile id]). The values efforts change most are named here (FIELDS); every other value is reached
through the full editor on the effort's layer. The RFP's own format rules (Submission Rules, kind Format) are offered
beside each value. Make it global writes an effort's change into a global layer (the Global Standards, a volume profile
or the effort type), records it in the global change history (with what it was, so it can be put back), and takes it
off the effort. Nothing here changes the Global Standards except Make it global. Rules only; nothing leaves the PC."""
import copy, datetime, getpass, json, os

import prodrules as PRL

SPACING = (("single", "Single"), ("1.15", "1.15"), ("1.5", "1.5 lines"), ("double", "Double"))
POSITION = (("above", "Above"), ("below", "Below"))
HEADINGS = ("Heading 1", "Heading 2", "Heading 3")
# (key, group, label, path in the standard, kind)
FIELDS = (
    ("body_font", "Body text", "Font", ("variables", "body_font"), "font"),
    ("body_size", "Body text", "Size (pt)", ("variables", "body_size"), "size"),
    ("line_spacing", "Body text", "Line spacing", ("variables", "line_spacing"), "spacing"),
    ("space_after_body", "Body text", "Space after (pt)", ("variables", "space_after_body"), "size"),
    ("table_font", "Tables", "Font", ("variables", "table_font"), "font"),
    ("table_size", "Tables", "Size (pt)", ("variables", "table_size"), "size"),
    ("caption_font", "Captions", "Font", ("variables", "caption_font"), "font"),
    ("caption_size", "Captions", "Size (pt)", ("variables", "caption_size"), "size"),
    ("caption_table", "Captions", "Table captions", ("captions", "Table"), "position"),
    ("caption_figure", "Captions", "Figure captions", ("captions", "Figure"), "position"),
    ("heading_font", "Headings", "Font (Heading 1 to 3)", ("style_defs", "Heading 1", "font"), "font"),
    ("heading1_size", "Headings", "Heading 1 size (pt)", ("variables", "heading1_size"), "size"),
    ("heading_numbers", "Headings", "Heading numbers", ("heading_numbering", "on"), "onoff"),
    ("paper", "Paper and margins", "Paper", ("variables", "paper"), "paper"),
    ("margin_top", "Paper and margins", "Top (in)", ("variables", "margin_top"), "inches"),
    ("margin_bottom", "Paper and margins", "Bottom (in)", ("variables", "margin_bottom"), "inches"),
    ("margin_left", "Paper and margins", "Left (in)", ("variables", "margin_left"), "inches"),
    ("margin_right", "Paper and margins", "Right (in)", ("variables", "margin_right"), "inches"),
    ("hf_left", "Header and footer", "Header, left", ("hf_layouts", "body", "header", "left"), "text"),
    ("hf_center", "Header and footer", "Header, center", ("hf_layouts", "body", "header", "center"), "text"),
    ("hf_right", "Header and footer", "Header, right", ("hf_layouts", "body", "header", "right"), "text"),
    ("team_line", "Header and footer", "Footer, the team's line (Rule 7)", ("variables", "team_line"), "text"),   # 3.48.0
    ("marking", "Header and footer", "Restriction marking", ("variables", "marking"), "text"),
)
FIELD = {f[0]: f for f in FIELDS}
# what Submission Rules' Format rows set (prodrules.from_rfp) for each field
RFP_SUBJECT = {"body_font": "Font", "body_size": "Font", "table_font": "Font in tables and figures",
               "table_size": "Font in tables and figures", "caption_size": "Font in tables and figures",
               "margin_top": "Margins", "margin_bottom": "Margins", "margin_left": "Margins", "margin_right": "Margins",
               "paper": "Page size", "line_spacing": "Line spacing"}
HISTORY = "production_standards_history.jsonl"


# ------------------------------------------------------------------ the effort's layers
def eff_of(ws):
    return dict((ws.get("prod_std", {}) or {}) if ws is not None else {})


def layer(ws, tid=None):
    """The effort's own changes: for every volume (tid None) or for one volume."""
    e = eff_of(ws)
    return copy.deepcopy(e.get("over") or {}) if not tid else copy.deepcopy((e.get("over_vol") or {}).get(tid) or {})


def set_layer(ws, lay, tid=None):
    e = eff_of(ws)
    lay = _prune(lay)
    if not tid:
        if lay:
            e["over"] = lay
        else:
            e.pop("over", None)
    else:
        ov = dict(e.get("over_vol") or {})
        if lay:
            ov[tid] = lay
        else:
            ov.pop(tid, None)
        if ov:
            e["over_vol"] = ov
        else:
            e.pop("over_vol", None)
    ws.set("prod_std", e)
    try:                                               # 4.7.0: the effort's workbook follows
        import teamlib
        teamlib.mark_effort_dirty(ws)
    except Exception:  # noqa: BLE001
        pass


def _prune(d):
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        v = _prune(v)
        if v in ({}, None):
            continue
        out[k] = v
    return out


def ids(config_dir, ws, data=None):
    """(data, effort type id or None, the effort's default volume id, [the effort's volume ids])."""
    data = data or PRL.load(config_dir)
    e = eff_of(ws)
    tids = [t["id"] for t in data["types"]]
    eid = e.get("effort_type") if PRL.effort_type_of(data, e.get("effort_type")) else None
    et = PRL.effort_type_of(data, eid)
    vols = et["profiles"] if et else tids
    default = e.get("type") if e.get("type") in tids else ((et or {}).get("default_profile") or data["default"])
    return data, eid, default, vols


def team_std(config_dir, ws, tid=None, data=None):
    """What the Global Standards give this effort before its own changes: for one volume, the effort's every-volume
    changes count as inherited too."""
    data, eid, default, _v = ids(config_dir, ws, data)
    std = PRL.resolved_type(data, tid or default, eid)
    if tid:
        std = PRL.merge(std, layer(ws))
    return std


def effort_std(config_dir, ws, tid=None, data=None):
    return PRL.merge(team_std(config_dir, ws, tid, data), layer(ws, tid))


# ------------------------------------------------------------------ one field
def _dig(d, path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _put(d, path, v):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    d[path[-1]] = v


def _pop(d, path):
    stack = []
    for k in path[:-1]:
        if not isinstance(d, dict) or k not in d:
            return
        stack.append((d, k))
        d = d[k]
    if isinstance(d, dict):
        d.pop(path[-1], None)


def _caption_pos(caps, label):
    for c in caps or []:
        if c.get("label") == label and c.get("part", "body") == "body":
            return c.get("position")
    return None


def value(std, key):
    """A field's value in a standard."""
    f = FIELD[key]
    if f[4] == "position":
        return _caption_pos(std.get("captions"), f[3][1])
    return _dig(std, f[3])


def get(config_dir, ws, key, tid=None):
    """{"team": inherited value, "effort": this effort's value or None, "shown": what is in force}."""
    team = value(team_std(config_dir, ws, tid), key)
    mine = _layer_value(ws, key, tid)
    return {"team": team, "effort": mine, "shown": team if mine is None else mine}


def _layer_value(ws, key, tid=None):
    f = FIELD[key]
    lay = layer(ws, tid)
    if f[4] == "position":
        return _caption_pos(lay.get("captions"), f[3][1]) if lay.get("captions") else None
    return _dig(lay, f[3])


def set_value(config_dir, ws, key, v, tid=None):
    """This effort's value for a field (None or '' takes it off: the global value holds again)."""
    f = FIELD[key]
    lay = layer(ws, tid)
    if v in (None, ""):
        if f[4] == "position":
            team = team_std(config_dir, ws, tid).get("captions")
            caps = lay.get("captions")
            if caps:
                tp = _caption_pos(team, f[3][1])
                for c in caps:
                    if c.get("label") == f[3][1] and c.get("part", "body") == "body":
                        c["position"] = tp
                if caps == team:
                    lay.pop("captions", None)
        elif key == "heading_font":
            for h in HEADINGS:
                _pop(lay, ("style_defs", h, "font"))
        else:
            _pop(lay, f[3])
    else:
        if f[4] == "position":
            caps = copy.deepcopy(lay.get("captions") or team_std(config_dir, ws, tid).get("captions") or [])
            for c in caps:
                if c.get("label") == f[3][1] and c.get("part", "body") == "body":
                    c["position"] = v
            lay["captions"] = caps
        elif key == "heading_font":
            for h in HEADINGS:
                _put(lay, ("style_defs", h, "font"), v)
        else:
            _put(lay, f[3], v)
    set_layer(ws, lay, tid)
    return get(config_dir, ws, key, tid)


def changed(config_dir, ws, tid=None):
    """[(what, global value, this effort's value)] for everything this effort sets at this scope, named fields first,
    then every other value the full editor set."""
    lay = layer(ws, tid)
    if not lay:
        return []
    team = team_std(config_dir, ws, tid)
    out, seen = [], set()
    for key, group, label, path, kind in FIELDS:
        mine = _layer_value(ws, key, tid)
        if mine is not None:
            out.append((f"{group}: {label}", value(team, key), mine))
            seen.add(path if kind != "position" else ("captions",))
            if key == "heading_font":
                seen.update(("style_defs", h, "font") for h in HEADINGS)

    def walk(d, path):
        if isinstance(d, dict) and d:
            for k, v in d.items():
                walk(v, path + (k,))
            return
        if path in seen or path[:1] in seen:
            return
        out.append((" > ".join(str(x).replace("_", " ") for x in path), _dig(team, path), d))
    walk(lay, ())
    return out


def reset_all(ws, tid=None):
    set_layer(ws, {}, tid)


# ------------------------------------------------------------------ the RFP's rules
def rfp(rows):
    """{field key: (value, what the RFP says)} from Submission Rules' Format rows."""
    over, said = PRL.from_rfp(rows or [])
    words = {}
    for s in said:
        subj = s.split(":", 1)[0]
        words[subj] = s
    out = {}
    v = over.get("variables") or {}
    for key, subj in RFP_SUBJECT.items():
        if key in v and subj in words:
            out[key] = (v[key], words[subj])
    mn = ((over.get("fonts") or {}).get("caption") or {}).get("min_size")
    if mn and RFP_SUBJECT["caption_size"] in words:                 # captions follow the tables and figures rule
        out["caption_size"] = (mn, words[RFP_SUBJECT["caption_size"]])
    return out


def breaks(shown, key, rfp_map):
    """True when a value in force breaks the RFP's rule for it (a size below the RFP's, another font, other margins)."""
    r = rfp_map.get(key)
    if not r or shown in (None, ""):
        return False
    want = r[0]
    kind = FIELD[key][4]
    try:
        if kind == "size":
            return float(shown) < float(want)
        if kind == "inches":
            return abs(float(shown) - float(want)) > 0.01
    except (TypeError, ValueError):
        return False
    if kind == "font":
        return str(shown).strip().casefold() != str(want).strip().casefold()
    return str(shown) != str(want)


# ------------------------------------------------------------------ back to the team
def targets(config_dir, ws, tid=None):
    """[(target key, words)] a change can be kept in: every effort, every volume of this kind, every effort of this
    effort type."""
    data, eid, default, _v = ids(config_dir, ws)
    t = PRL.type_of(data, tid or default)
    out = [("team", "The Global Standards: every effort"), ("type:" + t["id"], f"The {t['name']} profile: that kind of volume in every effort")]
    et = PRL.effort_type_of(data, eid)
    if et:
        out.append(("etype:" + et["id"], f"The {et['name']} effort type: every effort of that type"))
    return out


def _target_layer(data, target):
    if target == "team":
        return data["company"]
    kind, tid = target.split(":", 1)
    if kind == "type":
        return PRL.type_of(data, tid)
    e = PRL.effort_type_of(data, tid)
    if e is None:
        raise KeyError(target)
    return e


def keep_for_team(config_dir, ws, key, target, tid=None, who=None):
    """Write this effort's value for a field into a team layer, record it in the global change history, and take it
    off the effort (the global value now gives it). Returns the history entry, or None when the effort sets nothing."""
    mine = _layer_value(ws, key, tid)
    if mine is None:
        return None
    data = PRL.load(config_dir)
    lay = _target_layer(data, target)
    f = FIELD[key]
    if f[4] == "position":
        base = copy.deepcopy(lay.get("captions") or data["company"].get("captions") or [])
        was = _caption_pos(base, f[3][1])
        for c in base:
            if c.get("label") == f[3][1] and c.get("part", "body") == "body":
                c["position"] = mine
        prev = copy.deepcopy(lay.get("captions"))
        lay["captions"] = base
        undo = {"path": ["captions"], "value": prev}
    elif key == "heading_font":
        was = _dig(lay, ("style_defs", "Heading 1", "font"))
        prev = {h: _dig(lay, ("style_defs", h, "font")) for h in HEADINGS}
        for h in HEADINGS:
            _put(lay, ("style_defs", h, "font"), mine)
        undo = {"heading_fonts": prev}
    else:
        was = _dig(lay, f[3])
        _put(lay, f[3], mine)
        undo = {"path": list(f[3]), "value": was}
    PRL.save(config_dir, data)
    set_value(config_dir, ws, key, None, tid)
    entry = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "by": who or getpass.getuser(), "target": target,
             "field": key, "what": f"{f[1]}: {f[2]}", "was": was, "now": mine, "undo": undo}
    with open(os.path.join(config_dir, HISTORY), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def history(config_dir):
    try:
        with open(os.path.join(config_dir, HISTORY), encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]
    except (OSError, ValueError):
        return []


def undo_last(config_dir):
    """Put the team layer back as it was before the last Make it global. Returns the entry put back, or None."""
    hist = history(config_dir)
    live = [h for h in hist if not h.get("undone")]
    if not live:
        return None
    h = live[-1]
    data = PRL.load(config_dir)
    try:
        lay = _target_layer(data, h["target"])
    except KeyError:
        return None
    u = h.get("undo") or {}
    if "heading_fonts" in u:
        for name, font in u["heading_fonts"].items():
            if font is None:
                _pop(lay, ("style_defs", name, "font"))
            else:
                _put(lay, ("style_defs", name, "font"), font)
    elif u.get("path"):
        if u.get("value") is None:
            _pop(lay, tuple(u["path"]))
        else:
            _put(lay, tuple(u["path"]), u["value"])
    PRL.save(config_dir, data)
    h["undone"] = True
    with open(os.path.join(config_dir, HISTORY), "w", encoding="utf-8") as fh:
        for x in hist:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    return h


# ------------------------------------------------------------------ library parts this effort uses
def parts(config_dir, ws, tid=None):
    """[(slot, what it is, where it comes from in words)] for the template profile slots: the team's pinned version,
    this effort's own choice of version, or this effort's own values."""
    import templatelib as TL, templateprofile as TP
    lib = TL.Library(config_dir)
    std = effort_std(config_dir, ws, tid)
    lay = layer(ws, tid)
    mine_pins = (lay.get("library_pins") or {})
    out = []
    for slot, part, what, kind in TP.slots(std):
        st = TP.state(std, lib, slot)
        if slot in mine_pins and st["item"] is not None:
            src = f"This effort: {lib.shown_name(st['item'])}"
        elif st["item"] is not None:
            src = f"Global Standards: {lib.shown_name(st['item'])}"
        elif _slot_in_layer(lay, slot, kind):
            src = "This effort's own"
        else:
            src = "The Global Standards's own values"
        out.append((slot, f"{part}: {what}", src))
    return out


def _slot_in_layer(lay, slot, kind):
    if kind in ("cover", "backer", "title"):
        return bool((lay.get("page_parts") or {}).get(slot))
    if kind == "hf_design":
        return bool((lay.get("hf_designs") or {}).get(slot.split(":", 1)[1]))
    if kind == "table_look":
        return bool(lay.get("row_types") or lay.get("table_types"))
    if kind == "list_numbering":
        return bool(lay.get("list_numbering"))
    return bool(lay.get(kind))
