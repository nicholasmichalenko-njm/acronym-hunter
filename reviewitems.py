"""Review's decisions and captures, the team's way (3.29.0). Each decision (L, M, SOW, Interest, Support, Customer's,
Ignore) and each capture (Contact, Submission, Formatting, Acronym, Question, Key date, Objective, Key point, Graphic need,
Evaluation factor, Page limit, Deliverable, Effort detail, Hot button, Other submission detail, Written formatting rule,
and the team's and the effort's own) has a name, a key, a color and whether it shows; a capture sits on the bar or in
More. An effort type can hide decisions (an RFI hides L, M and SOW and shows Interest). What a built-in does stays
wired (a contact goes to Customer information); its name, key, color and showing are yours.

Kept in <config>/review_items.json, only what differs from the built-in values. Rules only; nothing leaves the PC."""
import copy, json, os

FILE = "review_items.json"
# code, name, short, key, color: what each decision is called on its button, in the legend and on the page
DECISIONS = (("L", "L (Instructions)", "L", "L", "#16A34A"),
             ("M", "M (Evaluation)", "M", "E", "#EA580C"),
             ("C", "SOW (Work)", "SOW", "R", "#0D9488"),
             ("I", "Customer interest (RFI)", "Interest", "I", "#4338CA"),
             ("ctx", "Support", "Support", "C", "#2563EB"),
             ("cust", "Customer's", "Customer's", "G", "#7E22CE"),
             ("ignore", "Ignore", "Ignore", "X", "#64748B"))
# key, name, shortcut, color, place (bar or more), what it does (shown in Settings)
CAPTURES = (("contact", "Contact", "", "#DB2777", "bar", "A point of contact, into Customer information"),
            ("submit", "Submission", "", "#DB2777", "bar", "A submission instruction, into Submission Rules"),
            ("format", "Formatting", "", "#DB2777", "bar", "A measured formatting rule, into Submission Rules and Production Standards"),
            ("acronym", "Acronym", "", "#DB2777", "bar", "An acronym and what it stands for, into the effort list"),
            ("question", "Question", "", "#DB2777", "bar", "A question for the customer, into Customer Q&A"),
            ("keydate", "Key date", "", "#DB2777", "bar", "A date onto the effort calendar"),
            ("objective", "Objective", "O", "#B45309", "bar", "A customer objective, mapped to the sections that answer it"),
            ("keypoint", "Key point", "K", "#0E7490", "bar", "Your train of thought: a theme, a discriminator, a risk"),
            ("graphic", "Graphic need", "P", "#DB2777", "bar", "A concept that needs a graphic, into Graphic needs"),
            ("factor", "Evaluation factor", "", "#DB2777", "more", "An evaluation factor, into Evaluation and hot buttons"),
            ("pagelimit", "Page limit", "", "#DB2777", "more", "A page limit, into the page budget"),
            ("deliverable", "Deliverable", "", "#DB2777", "more", "A deliverable, onto the deliverables board"),
            ("detail", "Effort detail", "", "#DB2777", "more", "Contract type, NAICS, set-aside..., into the Effort Record"),
            ("hot", "Hot button", "", "#DB2777", "more", "A hot button, into Evaluation and hot buttons"),
            ("other", "Other submission detail", "", "#BE185D", "more", "Submission detail that fits no rule, listed in Submission Rules"),
            ("written", "Written formatting rule", "", "#BE185D", "more", "A rule in words (a marking, a label), on Final Checks"))
# the effort types' own showing (the team can change these in Settings)
EFFORT_TYPE_HIDE = {"rfi": ["L", "M", "C"]}
EFFORT_TYPE_SHOW = {"rfi": ["I"]}
DEFAULT_HIDDEN = ["I"]                       # Interest shows only where an effort type shows it


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def load(config_dir):
    """{"decisions": {code: {...}}, "captures": {key: {...}}, "hide": {effort type: [codes]}, "show": {...}} with every
    built-in filled in from the team's changes."""
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            saved = {}
    except (OSError, ValueError):
        saved = {}
    out = {"decisions": {}, "captures": {}, "order": [], "hide": copy.deepcopy(EFFORT_TYPE_HIDE),
           "show": copy.deepcopy(EFFORT_TYPE_SHOW), "into_target": saved.get("into_target", True) is not False}
    sd = saved.get("decisions") or {}
    for code, name, short, key, color in DECISIONS:
        d = {"code": code, "name": name, "short": short, "key": key, "color": color, "shown": code not in DEFAULT_HIDDEN}
        d.update({k: v for k, v in (sd.get(code) or {}).items() if k in ("name", "short", "key", "color", "shown")})
        out["decisions"][code] = d
    sc = saved.get("captures") or {}
    for key, name, keyseq, color, place, does in CAPTURES:
        c = {"key": key, "name": name, "keyseq": keyseq, "color": color, "place": place, "shown": True, "does": does, "builtin": True}
        c.update({k: v for k, v in (sc.get(key) or {}).items() if k in ("name", "keyseq", "color", "place", "shown")})
        out["captures"][key] = c
    order = [k for k in (saved.get("order") or []) if k in out["captures"]]
    out["order"] = order + [k for k, *_r in CAPTURES if k not in order]
    for k in ("hide", "show"):
        if isinstance(saved.get(k), dict):
            out[k].update({et: [c for c in v if c in out["decisions"]] for et, v in saved[k].items() if isinstance(v, list)})
    return out


def save(config_dir, data):
    """Only what differs from the built-in values is written."""
    dec = {}
    for code, name, short, key, color in DECISIONS:
        d = (data.get("decisions") or {}).get(code) or {}
        diff = {k: d[k] for k, v in (("name", name), ("short", short), ("key", key), ("color", color),
                                     ("shown", code not in DEFAULT_HIDDEN)) if k in d and d[k] != v}
        if diff:
            dec[code] = diff
    cap = {}
    for key, name, keyseq, color, place, _does in CAPTURES:
        c = (data.get("captures") or {}).get(key) or {}
        diff = {k: c[k] for k, v in (("name", name), ("keyseq", keyseq), ("color", color), ("place", place), ("shown", True))
                if k in c and c[k] != v}
        if diff:
            cap[key] = diff
    out = {"format": 1, "decisions": dec, "captures": cap, "order": list(data.get("order") or []),
           "hide": data.get("hide") or {}, "show": data.get("show") or {}}
    if data.get("into_target") is False:                 # 3.29.1: captures go into the target section unless turned off
        out["into_target"] = False
    os.makedirs(config_dir, exist_ok=True)
    tmp = _path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    os.replace(tmp, _path(config_dir))
    return out


def reset(config_dir, what=None):
    """Back to the built-in values for one decision or capture (what), or for everything."""
    data = load(config_dir)
    if what is None:
        try:
            os.remove(_path(config_dir))
        except OSError:
            pass
        return load(config_dir)
    for code, name, short, key, color in DECISIONS:
        if code == what:
            data["decisions"][code] = {"code": code, "name": name, "short": short, "key": key, "color": color,
                                       "shown": code not in DEFAULT_HIDDEN}
    for key, name, keyseq, color, place, does in CAPTURES:
        if key == what:
            data["captures"][key].update(name=name, keyseq=keyseq, color=color, place=place, shown=True)
    save(config_dir, data)
    return load(config_dir)


def decisions_for(data, effort_type="", show_all=False):
    """The decisions Review shows for an effort of this type, in order."""
    hide = set((data.get("hide") or {}).get(effort_type or "", []))
    show = set((data.get("show") or {}).get(effort_type or "", []))
    out = []
    for code, *_r in DECISIONS:
        d = data["decisions"][code]
        on = (d["shown"] or code in show) and code not in hide
        if on or show_all:
            out.append(d)
    return out


def keys_in_use(data, custom=()):
    """{key: [what uses it]} for every key set on a decision, a capture or a custom capture, to show clashes."""
    use = {}
    for d in data["decisions"].values():
        if d.get("key"):
            use.setdefault(d["key"].upper(), []).append(d["name"])
    for c in data["captures"].values():
        if c.get("keyseq") and c.get("shown"):
            use.setdefault(c["keyseq"].upper(), []).append(c["name"])
    for c in custom:
        if c.get("key"):
            use.setdefault(str(c["key"]).upper(), []).append(c.get("name", ""))
    return use


RESERVED = {"J": "Combine", "S": "Split", "SHIFT+S": "Extract", "H": "Pan", "F": "For a requirement", "N": "Note", "Q": "Question",
            "T": "Task", "B": "Captures menu", "DELETE": "Take a decision off", "RETURN": "Accept", "ESCAPE": "Clear",
            "CTRL+A": "Select all", "CTRL+T": "Sort mode", "CTRL+Z": "Undo", **{str(n): "Topics in Sort mode" for n in range(1, 10)}}


def clashes(data, custom=()):
    """[(key, [names])]: a key used twice, or a key Review keeps for itself."""
    out = []
    for k, names in sorted(keys_in_use(data, custom).items()):
        if len(names) > 1:
            out.append((k, names))
        elif k in RESERVED:
            out.append((k, names + [f"Review's own {RESERVED[k]}"]))
    return out
