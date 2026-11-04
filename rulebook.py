"""The Rules page (3.38.0): every production rule as one plain sentence, in one list.

Two families: rules for our documents (what Audit, Fix a Copy and Make templates follow and check) and rules for reading
the customer's documents (Review's suggestion rules, kept in suggestrules.py). Each rule of ours says how it is kept:
"app" (checked straight from the file), "word" (checked with Word on this PC: anything about the laid-out page) or
"people" (a checklist item for people). A rule's values live where they live (Production Standards, Effort Formatting,
Banned phrases, the acronym list); a rule points there ("where") and never holds a second copy. The check codes a rule
answers ("codes") tie Audit and Fix a Copy findings to it, so they report by rule.

The built-in rules are the team's (R1 to R13 in the project's production rules list). The team can turn one off for every
effort, and add its own rules (kept by people). An effort departs from a rule only on Effort Formatting (its own list of
rules it turns off). Kept on this PC beside the global standards (rules.json); a team pack carries it. Rules only."""
import copy, json, os, uuid

FILE = "rules.json"
KEPT = (("app", "Checked by the app"), ("word", "Checked with Word on this PC"), ("people", "Checklist for people"))
KEPT_NAME = dict(KEPT)
GROUPS = ("Pages and markings", "Formatting", "Acronyms", "Writing", "Approach")
# id, group, sentence, kept by, where its values live (page key, section), check codes it answers
BUILTIN = (
    ("1", "Pages and markings", "A style reference (STYLEREF) never reads text in a text box: text a header, footer or field "
     "reads sits in the page or in a table cell.", "app", ("prodstd", "part_cover"), ("RU1",)),
    ("2", "Pages and markings", "On the cover or title page, the A number sits right under the proprietary statement, commercial "
     "data rights and Warning content, right-justified.", "app", ("prodstd", "styledefs"), ("RU2",)),
    ("3", "Pages and markings", "The page marking (Unclassified, a classification, CUI or the response's own) sits at the top "
     "center and bottom center of every page.", "app", ("prodstd", "hf"), ("RU3", "P10")),
    ("4", "Formatting", "Style names follow the effort's response type: a style named with RFP is named RFI in an RFI "
     "response, BAA in a BAA response, and so on.", "app", ("effortfmt", ""), ("RU4",)),
    ("5", "Formatting", "A response with no title page carries no title page styles in its template.", "app",
     ("prodstd", "styledefs"), ("RU5",)),
    ("6", "Formatting", "Every heading level puts its number at 0 inches, then a tab to the text: no level is indented "
     "differently from another.", "app", ("prodstd", "headnum"), ("RU6", "S5")),
    ("7", "Pages and markings", "The footer is a one-row, three-column table: the A number on the left (a STYLEREF to its "
     "style on the cover or title page), two standard lines in the middle, the page number on the right.", "app",
     ("prodstd", "hf"), ("RU7",)),
    ("8", "Formatting", "Caption rows and notes rows in tables sit at 0.0 inches left and right.", "app",
     ("prodstd", "rows"), ("RU8",)),
    ("9", "Formatting", "Only approved styles are in use.", "app", ("prodstd", "styles"), ("S1",)),
    ("10", "Acronyms", "Each acronym is spelled out at its first use in running text, and not spelled out again later.",
     "app", ("acrlist", ""), ("A1", "A2")),
    ("11", "Acronyms", "Every acronym a document uses is on the effort's acronym list.", "app", ("acrlist", ""), ("A3",)),
    ("12", "Writing", "No banned phrases; replacements follow Words to avoid and fix.", "app", ("prodstd", "terms"),
     ("W1", "W2")),
    ("13", "Formatting", "Our style names start with AA, then a name that says where the style is used and what it is for.",
     "people", ("prodstd", "styledefs"), ()),
)
WHERE_NAME = {"prodstd": "Production Standards", "effortfmt": "Effort Formatting", "acrlist": "the Acronym List"}


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def load(config_dir):
    """{"off": [rule ids turned off for every effort], "own": [{"id", "group", "text", "kept"}]}."""
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    own = [r for r in d.get("own", []) if isinstance(r, dict) and r.get("id") and r.get("text")]
    return {"off": [str(x) for x in d.get("off", [])], "own": own}


def save(config_dir, data):
    os.makedirs(config_dir, exist_ok=True)
    p = _path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"off": data.get("off", []), "own": data.get("own", [])}, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def rules(config_dir):
    """Every rule of ours: [{"id", "label", "group", "text", "kept", "where", "codes", "on", "own"}], built-in first."""
    d = load(config_dir)
    out = []
    for rid, group, text, kept, where, codes in BUILTIN:
        out.append({"id": rid, "label": f"Rule {rid}", "group": group, "text": text, "kept": kept, "where": where,
                    "codes": codes, "on": rid not in d["off"], "own": False})
    for r in d["own"]:
        out.append({"id": r["id"], "label": f"Rule {r['id']}", "group": r.get("group") or "Approach", "text": r["text"],
                    "kept": r.get("kept") if r.get("kept") in KEPT_NAME else "people", "where": ("", ""), "codes": (),
                    "on": r["id"] not in d["off"], "own": True})
    return out


def get(config_dir, rid):
    return next((r for r in rules(config_dir) if r["id"] == str(rid)), None)


def set_on(config_dir, rid, on):
    d = load(config_dir)
    off = [x for x in d["off"] if x != str(rid)]
    if not on:
        off.append(str(rid))
    d["off"] = off
    save(config_dir, d)
    return on


def add(config_dir, text, group="Approach", kept="people"):
    """A rule of the team's own (a checklist item unless the app can check it). Returns its id."""
    text = " ".join((text or "").split())
    if not text:
        return None
    d = load(config_dir)
    n = 1 + max([int(r["id"]) for r in d["own"] if str(r["id"]).isdigit()] + [len(BUILTIN)])
    d["own"].append({"id": str(n), "group": group if group in GROUPS else "Approach", "text": text[:600],
                     "kept": kept if kept in KEPT_NAME else "people"})
    save(config_dir, d)
    return str(n)


def edit(config_dir, rid, text=None, group=None, kept=None):
    d = load(config_dir)
    r = next((x for x in d["own"] if x["id"] == str(rid)), None)
    if r is None:
        return False
    if text is not None and " ".join(text.split()):
        r["text"] = " ".join(text.split())[:600]
    if group in GROUPS:
        r["group"] = group
    if kept in KEPT_NAME:
        r["kept"] = kept
    save(config_dir, d)
    return True


def remove(config_dir, rid):
    d = load(config_dir)
    n = len(d["own"])
    d["own"] = [x for x in d["own"] if x["id"] != str(rid)]
    d["off"] = [x for x in d["off"] if x != str(rid)]
    save(config_dir, d)
    return len(d["own"]) < n


# ------------------------------------------------------------------ an effort's own exceptions
def effort_off(ws):
    return [str(x) for x in ((ws.get("prod_std", {}) or {}).get("rules_off") or [])] if ws is not None else []


def set_effort_on(ws, rid, on):
    """An effort departs from a rule (on=False) or follows it again. Kept in the effort's formatting."""
    eff = dict(ws.get("prod_std", {}) or {})
    off = [x for x in (eff.get("rules_off") or []) if x != str(rid)]
    if not on:
        off.append(str(rid))
    if off:
        eff["rules_off"] = off
    else:
        eff.pop("rules_off", None)
    ws.set("prod_std", eff)
    return on


def in_force(config_dir, ws=None):
    """The rules in force: on for every effort and not turned off by this effort."""
    off = set(effort_off(ws))
    return [r for r in rules(config_dir) if r["on"] and r["id"] not in off]


# ------------------------------------------------------------------ findings by rule
def rule_of_code(code, config_dir=None, ws=None):
    """The rule a check code answers ("Rule 6"), or "" for a check no rule names. With config_dir, only rules in force."""
    pool = in_force(config_dir, ws) if config_dir else rules_builtin()
    for r in pool:
        if code in r["codes"]:
            return r["label"]
    return ""


def rules_builtin():
    return [{"id": rid, "label": f"Rule {rid}", "codes": codes} for rid, _g, _t, _k, _w, codes in BUILTIN]


def order_key(label):
    """Sort key for a rule label: Rule 1, Rule 2 ... Rule 10, then findings no rule names."""
    try:
        return (0, int(str(label).split()[-1]))
    except (ValueError, IndexError):
        return (1, 0)


def response_types():
    return ("RFP", "RFI", "BAA", "RFQ", "CSO", "Sources Sought", "White paper")


def summary(config_dir, ws=None):
    """{"n", "app", "word", "people", "off"} for the top of the Rules page."""
    rs = rules(config_dir)
    force = {r["id"] for r in in_force(config_dir, ws)}
    return {"n": len(rs), "app": sum(1 for r in rs if r["kept"] == "app"), "word": sum(1 for r in rs if r["kept"] == "word"),
            "people": sum(1 for r in rs if r["kept"] == "people"), "off": sum(1 for r in rs if r["id"] not in force)}
