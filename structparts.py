"""Parts of the response structure (3.19.0): each volume is a cover, a title page, front matter, the response itself,
appendices and a back cover, in that order. A section of the structure belongs to one part (the response unless it says
otherwise). Cover, title page, front matter and back cover items carry no section number; appendices are lettered
(Appendix A, then A.1 under it); the response is numbered as it always was.

Each part follows its own rules from Production Standards: the page scheme's part of the same name gives its page
numbering, its header, whether the marking is in its footer, and the heading style that starts it. This module reads
those rules for a volume (its profile in the effort type) and says them in words for the structure, the Page budget and
the Response Setup documents. Which parts count toward the volume's page limit is kept with the structure (setup
"part_counts"); only the response counts unless the person says otherwise. Rules only; nothing leaves the PC."""

PARTS = (("cover", "Cover"), ("title", "Title page"), ("front", "Front matter"), ("body", "Response"),
         ("appendix", "Appendices"), ("back", "Back cover"))
PART_NAME = dict(PARTS)
ORDER = {k: n for n, (k, _name) in enumerate(PARTS)}
ITEM_NAME = {"cover": "Cover", "title": "Title page", "front": "Front matter item", "body": "Response section",
             "appendix": "Appendix", "back": "Back cover"}
FRONT_PRESETS = ("Cover letter", "Table of contents", "List of figures", "List of tables", "Acronyms and abbreviations",
                 "Compliance matrix", "Executive summary")
COUNTS_DEFAULT = {"body": True}
NUMBERED = ("body", "appendix")
# the page scheme's part each structure part follows, and where to look when the scheme has no such part
SCHEME_KEYS = {"cover": ("cover",), "title": ("title", "cover"), "front": ("front",), "body": ("body", "all"),
               "appendix": ("appendix", "body", "all"), "back": ("backer", "back")}
_TAGS = {"cover": "cover", "title": "title", "title page": "title", "front": "front", "front matter": "front",
         "response": "body", "body": "body", "appendix": "appendix", "appendices": "appendix", "back": "back",
         "back cover": "back"}
TAG = {"cover": "Cover", "title": "Title page", "front": "Front matter", "appendix": "Appendix", "back": "Back cover"}
FMT = {"decimal": "1, 2, 3", "lowerRoman": "i, ii, iii", "upperRoman": "I, II, III", "lowerLetter": "a, b, c",
       "upperLetter": "A, B, C"}
SEP = {"hyphen": "-", "period": ".", "colon": ":", "enDash": "–", "emDash": "—"}


def part_of(o):
    p = (o or {}).get("part") or "body"
    return p if p in PART_NAME else "body"


def tag_part(text):
    """'[Front matter] Table of contents' -> ('front', 'Table of contents'); untagged -> ('', text)."""
    import re
    m = re.match(r"^\[([A-Za-z ]+)\]\s*(.*)$", text or "")
    if m and m.group(1).strip().lower() in _TAGS:
        return _TAGS[m.group(1).strip().lower()], m.group(2).strip()
    return "", text


def has_parts(M):
    """True when any section is in a part other than the response (the structure then shows its parts)."""
    return any(part_of(o) != "body" for o in getattr(M, "outline", []) or [])


# ------------------------------------------------------------------ page limits
def counts(M, part):
    """Does this part count toward the volume's page limit?"""
    import setupdoc as SD
    v = (SD.setup_of(M).get("part_counts") or {}).get(part)
    return bool(COUNTS_DEFAULT.get(part, False)) if v is None else bool(v)


def set_counts(M, part, on):
    import setupdoc as SD
    S = SD.setup_of(M)
    pc = S.get("part_counts")
    if not isinstance(pc, dict):
        pc = S["part_counts"] = {}
    pc[part] = bool(on)
    if hasattr(M, "pending"):
        M.pending = True


def label_part(M):
    """{section label: its part}, children taking their part from the item that starts their block."""
    import compliance as C
    return {C.outline_label(o): part_of(o) for o in M.outline}


def counted(M, label):
    return counts(M, label_part(M).get(label, "body"))


# ------------------------------------------------------------------ rules from Production Standards
def scheme_part(std, part):
    """The page scheme part this structure part follows (or None)."""
    parts = (std or {}).get("pagination", {}).get("parts", []) if isinstance((std or {}).get("pagination"), dict) else []
    by = {p.get("key"): p for p in parts}
    for k in SCHEME_KEYS.get(part, ()):
        if k in by:
            return by[k]
    return None


def numbers_text(n, part=""):
    if not n:
        return "no page numbers"
    fmt = FMT.get(n.get("fmt"), n.get("fmt") or "1, 2, 3")
    if n.get("chapter_level") and n.get("fmt") == "decimal":
        s = SEP.get(n.get("separator") or "hyphen", "-")
        return f"A{s}1, A{s}2 by appendix" if part == "appendix" else f"1{s}1, 1{s}2 by chapter"
    if n.get("restart") == "never":
        return fmt + ", continuing from the part before"
    return fmt + (", starting again here" if n.get("restart") == "part" else "")


def rules(std, part):
    """{"found", "numbers", "header", "marking", "starts"} in words for a part, from the standard's page scheme."""
    p = scheme_part(std, part)
    if p is None:
        return {"found": False, "numbers": "", "header": "", "marking": "", "starts": "", "scheme": ""}
    st = p.get("starts") or {}
    starts = (f"the {st['style']} style" if st.get("style") else f"the {', '.join(st['styles'])} style" if st.get("styles")
              else "the first section" if st.get("first_section") else "the last section" if st.get("last_section") else "")
    head = p.get("header") or ""
    head = "none" if not head else head.replace("{volume_name}", "the volume name").replace("{", "").replace("}", "")
    via = "" if p.get("key") in SCHEME_KEYS.get(part, ())[:1] else p.get("name", "")
    return {"found": True, "numbers": numbers_text(p.get("numbers"), part), "header": head,
            "marking": "the marking in the footer" if p.get("footer_marking") else "no marking in the footer",
            "starts": starts, "scheme": via}


def summary(std, part, counts_on=None):
    """One line for the structure and the setup documents."""
    r = rules(std, part)
    if not r["found"]:
        txt = "not in the page scheme of Production Standards"
    else:
        txt = (r["numbers"] if r["numbers"] == "no page numbers" else f"page numbers {r['numbers']}") \
            + f"; header: {r['header']}; {r['marking']}" + (f"; starts with {r['starts']}" if r["starts"] else "")
        if r["scheme"]:
            txt += f" (follows the scheme's {r['scheme']})"
    if counts_on is not None:
        txt += "; counts toward the page limit" if counts_on else "; not counted toward the page limit"
    return txt


def standard_for(config_dir, ws, volume_label=""):
    """The production standard in force for a volume of the open effort (its profile in the effort type)."""
    try:
        import prodrules as PRL
        data = PRL.load(config_dir)
        eff = (ws.get("prod_std", {}) if ws is not None else {}) or {}
        tid = PRL.profile_for(data, eff.get("effort_type"), volume_label) if volume_label else None
        return PRL.for_effort(config_dir, ws, data, type_id=tid)
    except Exception:
        import diag
        diag.swallowed()
        return {}


def summaries(config_dir, ws, M, volume_label=""):
    """{part: one line} for a volume."""
    std = standard_for(config_dir, ws, volume_label)
    return {k: summary(std, k, counts(M, k)) for k, _n in PARTS}
