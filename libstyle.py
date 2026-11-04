"""Every value of a library item, to see and edit one by one (3.49.0).

A style: each property with where it comes from. Styles read from Word hold every value as Word shows it (through the
styles they are based on), so a value equal to its base style's is "from <base>", a value of its own is "set here", and
Reset puts the base's value back. The base is the library's style of that name (the newest version, from the same file
when there is one); the chain is every base up to the last.

Anything else: its values as a tree of what and value; plain values (words, numbers, yes or no) edit in place, Word
XML and pictures are kept whole and shown by size. Rules only; no Qt."""
import copy, json

# (key, label, kind): kind text, num, bool, align, line_rule, stylename, type
PROPS = (("type", "Type", "type"), ("based_on", "Based on", "stylename"), ("next", "Next style", "stylename"),
         ("font", "Font", "text"), ("size", "Size (pt)", "num"), ("bold", "Bold", "bool"), ("italic", "Italic", "bool"),
         ("underline", "Underline", "bool"), ("caps", "All caps", "bool"), ("small_caps", "Small caps", "bool"),
         ("color", "Color (hex)", "text"), ("hidden", "Hidden text", "bool"), ("jc", "Alignment", "align"),
         ("before", "Space before (pt)", "num"), ("after", "Space after (pt)", "num"),
         ("line", "Line spacing (lines, or pt if exact)", "num"), ("line_rule", "Line rule", "line_rule"),
         ("left", "Left indent (pt)", "num"), ("right", "Right indent (pt)", "num"), ("first", "First line (pt)", "num"),
         ("hanging", "Hanging (pt)", "num"), ("keep_next", "Keep with next", "bool"), ("keep_lines", "Keep lines together", "bool"),
         ("page_break_before", "Page break before", "bool"), ("widow", "Widow control", "bool"),
         ("tabs", "Tab stops", "text"), ("border_top", "Border above", "text"), ("border_bottom", "Border below", "text"),
         ("border_left", "Border left", "text"), ("border_right", "Border right", "text"), ("shading", "Shading (hex, or none)", "text"))
CHOICES = {"type": [("paragraph", "Paragraph"), ("character", "Character"), ("table", "Table")],
           "align": [("", "Not set"), ("left", "Left"), ("center", "Center"), ("right", "Right"), ("both", "Justified")],
           "line_rule": [("", "Multiple"), ("exact", "Exactly"), ("atLeast", "At least")],
           "bool": [(None, "Not set"), (True, "On"), (False, "Off")]}
OWN = ("type", "based_on", "next")                      # a style's own, never taken from its base
BLOBS = ("xml", "header", "footer", "b64", "header_media", "footer_media")


def base_item(lib, item, name):
    """The library's style named name: from the same file when there is one, else the newest version."""
    cands = [i for i in lib.items if i["kind"] == "style" and lib.base_of(i).casefold() == (name or "").casefold()]
    if not cands:
        return None
    same = [i for i in cands if i.get("source") and i.get("source") == item.get("source")]
    return max(same or cands, key=lambda i: int(i.get("version") or 1))


def chain(lib, item, values=None):
    """[(name, item or None, values)] from the item's base to the last base (a loop stops)."""
    out, seen = [], {lib.base_of(item).casefold()}
    v = values if values is not None else (lib.values(item) or {})
    while v.get("based_on") and str(v["based_on"]).casefold() not in seen:
        nm = str(v["based_on"])
        seen.add(nm.casefold())
        b = base_item(lib, item, nm)
        v = (lib.values(b) or {}) if b else {}
        out.append((nm, b, v))
        if b is None:
            break
    return out


def origins(lib, item, values):
    """{key: (where, base value)}: where is 'here', 'from <name>' or '' (not set)."""
    ch = chain(lib, item, values)
    base_name, base = (ch[0][0], ch[0][2]) if ch else ("", {})
    out = {}
    for k, _l, _kind in PROPS:
        have = values.get(k)
        if k in OWN or not ch:
            out[k] = ("here" if have not in (None, "") else "", None)
        elif have in (None, ""):
            out[k] = ("", base.get(k))
        elif k in base and _same(have, base.get(k)):
            out[k] = (f"from {base_name}", base.get(k))
        else:
            out[k] = ("here", base.get(k))
    return out


def _same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-6 if not isinstance(a, bool) and not isinstance(b, bool) else a == b
    except (TypeError, ValueError):
        return a == b


def reset(lib, item, values, key):
    """The values with key put back to its base style's (taken off when the base does not set it)."""
    v = copy.deepcopy(values)
    ch = chain(lib, item, v)
    base = ch[0][2] if ch else {}
    if key in base and key not in OWN:
        v[key] = copy.deepcopy(base[key])
    else:
        v.pop(key, None)
    return v


def parse(kind, text):
    """A typed value from what was entered: numbers for num, the stored value for choices; '' is not set (None)."""
    if kind == "num":
        t = str(text).strip()
        if not t:
            return None
        f = float(t)
        return int(f) if f.is_integer() else round(f, 2)
    if kind == "text" or kind == "stylename":
        t = " ".join(str(text).split())
        return t or None
    return text if text not in ("",) else None


def set_value(values, key, value):
    v = copy.deepcopy(values)
    if value is None:
        v.pop(key, None)
    else:
        v[key] = value
    return v


# ------------------------------------------------------------------ any item: a tree of values
def rows(values, path=()):
    """[(path, what, value shown, editable)] every value, nested ones under their parent (path is a tuple of keys and
    list positions)."""
    out = []
    if isinstance(values, dict):
        items = [(k, x) for k, x in values.items() if not str(k).startswith("_")]
    elif isinstance(values, list):
        items = list(enumerate(values))
    else:
        return out
    for k, x in items:
        p = path + (k,)
        what = f"{k + 1}" if isinstance(k, int) else str(k).replace("_", " ")
        if k in BLOBS or (isinstance(x, str) and len(x) > 300):
            size = len(json.dumps(x)) if not isinstance(x, str) else len(x)
            out.append((p, what, f"kept whole ({size:,} characters)", False))
        elif isinstance(x, (dict, list)):
            out.append((p, what, f"{len(x)} value(s)" if x else "none", False))
            out += rows(x, p)
        else:
            out.append((p, what, "" if x is None else ("yes" if x is True else "no" if x is False else str(x)), True))
    return out


def get_path(values, path):
    v = values
    for k in path:
        v = v[k]
    return v


def set_path(values, path, text):
    """The values with the plain value at path set from text, keeping its type (number, yes or no, words). Raises
    ValueError when text does not fit the type."""
    v = copy.deepcopy(values)
    old = get_path(v, path)
    t = str(text).strip()
    if isinstance(old, bool):
        if t.casefold() not in ("yes", "no", "true", "false", "on", "off"):
            raise ValueError("yes or no")
        new = t.casefold() in ("yes", "true", "on")
    elif isinstance(old, int):
        new = int(float(t)) if t else 0
    elif isinstance(old, float):
        new = float(t) if t else 0.0
    elif old is None:
        new = json.loads(t) if t[:1] in "0123456789-" and t.replace(".", "", 1).lstrip("-").isdigit() else (t or None)
    else:
        new = t
    parent = get_path(v, path[:-1]) if len(path) > 1 else v
    parent[path[-1]] = new
    return v
