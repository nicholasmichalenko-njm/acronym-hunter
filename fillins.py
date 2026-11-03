"""Fill-ins (3.23.0): type a value once and it shows everywhere it is referenced.

A fill-in is a token ({contract_type}) that headers, footers, the cover and Quick Parts use. It works one of two ways:
  styleref  (the default, as the team works today): the value sits once on the cover or title page in its own style;
            every STYLEREF field to that style (headers, footers, Quick Parts) shows it after a field update.
  docprop   a document property (a custom property, or Title, Subject or Company); DOCPROPERTY fields show it.
The built-in volume values (volume_name, solicitation, company, classification, project) are fill-ins too, kept in their
cover styles. Fields are written without the \\* MERGEFORMAT switch, so each result takes the formatting where it sits,
never the formatting it had before. Rules only; nothing leaves the PC."""
import re

KINDS = (("styleref", "Style on the cover (STYLEREF)"), ("docprop", "Document property (DOCPROPERTY)"))
BUILTIN_PROPS = {"Title": "core", "Subject": "core", "Company": "app", "Manager": "app"}


def _key(s):
    return re.sub(r"[^a-z0-9_]+", "_", str(s or "").strip().lower()).strip("_")[:40]


def custom(std):
    """The standard's own fill-ins, cleaned: [{"key", "name", "kind", "style", "property", "value"}]."""
    out = []
    for f in (std.get("fill_ins") or []):
        if not isinstance(f, dict):
            continue
        key = _key(f.get("key") or f.get("name"))
        if not key:
            continue
        kind = f.get("kind") if f.get("kind") in dict(KINDS) else "styleref"
        name = " ".join(str(f.get("name") or key.replace("_", " ").title()).split())[:60]
        style = " ".join(str(f.get("style") or ("SK " + name)).split())[:60] if kind == "styleref" else ""
        prop = " ".join(str(f.get("property") or name).split())[:60] if kind == "docprop" else ""
        out.append({"key": key, "name": name, "kind": kind, "style": style, "property": prop, "value": str(f.get("value") or "")[:300]})
    return out


def styles(std):
    """{token: cover style} for every styleref fill-in, the built-in volume values first."""
    from prodengine.pe.hf import SOURCE_STYLES
    out = dict(SOURCE_STYLES)
    for f in custom(std):
        if f["kind"] == "styleref":
            out[f["key"]] = f["style"]
    return out


def props(std):
    """{token: document property} for every docprop fill-in."""
    return {f["key"]: f["property"] for f in custom(std) if f["kind"] == "docprop"}


def value(std, key):
    """The value typed for a token: this layer's variables first, then the fill-in's own value."""
    v = (std.get("variables") or {}).get(key)
    if str(v or "").strip():
        return str(v)
    f = next((x for x in custom(std) if x["key"] == key), None)
    return f["value"] if f else ""


def tokens(std):
    """Every token a layout may use: the built-in ones and the standard's fill-ins: {token: name}."""
    import prodrules as PRL
    out = dict(PRL.HF_TOKENS)
    for f in custom(std):
        out[f["key"]] = f["name"]
    return out


def strip_mergeformat(instr):
    """A field instruction without \\* MERGEFORMAT or \\* CHARFORMAT, so the result takes the formatting where it sits."""
    return re.sub(r"\s*\\\*\s*(MERGEFORMAT|CHARFORMAT)\b", "", instr, flags=re.I).strip()
