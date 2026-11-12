"""Compliance words (2.31.0): the words that make a sentence a requirement, shown in a style the user picks.

shall, must, will, should, may, is required to, not exceed, and the imperative verbs (describe, provide, submit...)
are bold by default on screen and in every compliance output: the Excel matrix, the setup documents, the coverage
report and the Word outline. The user can add italic, underline, a color and a highlight, and edit the word list.
Saved on this PC in config\\compliance_words.json. Rules only, no AI.
"""
import json, os, re

VERBS = ("describe", "provide", "submit", "identify", "demonstrate", "discuss", "explain", "include", "address",
         "propose", "deliver", "furnish", "specify", "list", "present", "show", "ensure", "maintain", "comply",
         "state", "indicate", "define", "detail", "outline", "summarize", "prepare", "document", "certify", "exceed")
# verbs count only where they give an order: at the start of a sentence or list item, or right after shall / must...
# ("Describe the approach", "shall provide"), so "the document" or "state of the art" stay plain
DEFAULT_WORDS = ["shall not", "must not", "will not", "may not", "shall", "must", "will", "should", "may",
                 "is required to", "are required to", "is required", "are required", "required", "not to exceed",
                 "not exceed", "no more than", "limited to", "is expected to", "are expected to",
                 "describe", "provide", "submit", "identify", "demonstrate", "discuss", "explain", "include", "address",
                 "propose", "deliver", "furnish", "specify", "list", "present", "show", "ensure", "maintain", "comply",
                 "state", "indicate", "define", "detail", "outline", "summarize", "prepare", "document", "certify", "exceed"]
DEFAULT_STYLE = {"bold": True, "italic": False, "underline": False, "color": "", "highlight": ""}
COLORS = {"None": "", "Red": "C00000", "Dark red": "8B0000", "Blue": "0070C0", "Dark blue": "1F3864",
          "Green": "00803C", "Purple": "7030A0", "Orange": "C55A11"}
HIGHLIGHTS = {"None": "", "Yellow": "FFFF00", "Light green": "C6EFCE", "Light blue": "DDEBF7", "Pink": "FFC7CE",
              "Gray": "D9D9D9"}
_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
_cache = {}


def _config_dir():
    import sys
    app = sys.modules.get("app_gui")
    return getattr(app, "CONFIG_DIR", None) if app else None


def path(config_dir=None):
    d = config_dir or _config_dir()
    return os.path.join(d, "compliance_words.json") if d else None


def _clean(d):
    st = dict(DEFAULT_STYLE)
    src = (d or {}).get("style") or {}
    for k in ("bold", "italic", "underline"):
        if k in src:
            st[k] = bool(src[k])
    for k in ("color", "highlight"):
        v = str(src.get(k) or "").strip().lstrip("#")
        st[k] = v.upper() if _HEX.match(v) else ""
    words = [" ".join(str(w).split()).lower() for w in ((d or {}).get("words") or DEFAULT_WORDS)]
    words = [w for w in dict.fromkeys(words) if w and len(w) <= 60]
    return {"style": st, "words": words or list(DEFAULT_WORDS)}


def load(config_dir=None):
    """{"style": {...}, "words": [...]}: the defaults until the user saves a style."""
    p = path(config_dir)
    try:
        with open(p, encoding="utf-8") as f:
            return _clean(json.load(f))
    except (OSError, ValueError, TypeError):
        return _clean({})


def save(cfg, config_dir=None):
    p = path(config_dir)
    if not p:
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_clean(cfg), f, indent=1)
    os.replace(tmp, p)
    _team_dirty(p)


def pattern(words):
    key = tuple(words)
    if key not in _cache:
        alts = sorted(words, key=len, reverse=True)
        _cache.clear()
        _cache[key] = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in alts) + r")(?![\w-])",
                                 re.I) if alts else None
    return _cache[key]


_LEAD = re.compile(r"^\s*(?:\(?[a-z0-9ivx]{1,4}[.)]\s*)?$", re.I)
_JOIN = re.compile(r"^\s*(?:,\s*)?(?:(?:and|or|and/or)\s+)?(?:not\s+)?(?:also\s+|clearly\s+|fully\s+)?$", re.I)


def _marks(it):
    """4.18.0: a piece's own compliance language: (words marked on it, words the list marks that it says are not)."""
    cl = (it or {}).get("cl") or {}
    norm = lambda xs: [" ".join(str(x).split()).lower() for x in xs or () if str(x).strip()]      # noqa: E731
    return norm(cl.get("add")), norm(cl.get("not"))


def segments(text, cfg=None, add=(), drop=()):
    """[(piece, is_compliance_word)] covering the whole text in order. 4.18.0: add, words marked on this piece (always
    compliance language there); drop, words the list marks that this piece says are not."""
    cfg = cfg or load()
    add = [" ".join(str(w).split()).lower() for w in add or () if str(w).strip()]
    drop = {" ".join(str(w).split()).lower() for w in drop or ()}
    pat = pattern(list(dict.fromkeys(list(cfg["words"]) + add)))
    text = str(text or "")
    if not pat:
        return [(text, False)] if text else []
    hits, last = [], None
    for m in pat.finditer(text):
        low = " ".join(m.group(0).split()).lower()
        if low in drop and low not in add:
            continue
        if low in add:
            hits.append(m); last = m
            continue
        if m.group(0).lower() in VERBS:
            before = text[last.end():m.start()] if last is not None else None
            sent_start = _LEAD.match(text[:m.start()]) or re.search(r"[.;:]\s+(?:\(?[a-z0-9ivx]{1,4}[.)]\s*)?$", text[:m.start()], re.I)
            if not (sent_start or (before is not None and _JOIN.match(before))):
                continue
        hits.append(m)
        last = m
    out, pos = [], 0
    for m in hits:
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def add_words(words, config_dir=None):
    """2.50.0: add words or phrases to the list (right-click > Add to compliance words). Returns the ones added."""
    cfg = load(config_dir)
    have = set(cfg["words"])
    new = [w for w in dict.fromkeys(" ".join(str(x).split()).lower().strip(" .,;:()\"'") for x in words) if w and len(w) <= 60 and w not in have]
    if new:
        cfg["words"] = cfg["words"] + new
        save(cfg, config_dir)
    return new


def added(cfg=None):
    """The words the team added to the built-in list."""
    cfg = cfg or load()
    return [w for w in cfg["words"] if w not in DEFAULT_WORDS]


def styled(cfg):
    st = cfg["style"]
    return st["bold"] or st["italic"] or st["underline"] or bool(st["color"]) or bool(st["highlight"])


def docx_parts(text, base=None, cfg=None, it=None):
    """Runs for docxw.Doc.rich: the base format everywhere, the user's style added on compliance words (4.18.0: and on the
    words marked on the piece it, not on the ones it says are not)."""
    cfg = cfg or load()
    add, drop = _marks(it)
    base = dict(base or {})
    st = cfg["style"]
    word = dict(base)
    if st["bold"]:
        word["bold"] = True
    if st["italic"]:
        word["italic"] = True
    if st["underline"]:
        word["underline"] = True
    if st["color"]:
        word["color"] = st["color"]
    if st["highlight"]:
        word["fill"] = st["highlight"]
    return [(t, word if w else base) for t, w in segments(text, cfg, add, drop)] or [("", base)]


def xlsx_value(text, cfg=None, it=None):
    """A rich-text cell value for openpyxl (Excel has no highlight per run, so highlight is left out there)."""
    cfg = cfg or load()
    text = str(text or "")
    segs = segments(text, cfg, *_marks(it))
    if not styled(cfg) or not any(w for _t, w in segs):
        return text
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    st = cfg["style"]
    font = InlineFont(b=st["bold"] or None, i=st["italic"] or None, u="single" if st["underline"] else None,
                      color=("FF" + st["color"]) if st["color"] else None)
    return CellRichText(*[TextBlock(font, t) if w else t for t, w in segs])


def html(text, cfg=None, it=None):
    """4.18.0: the text as HTML for a label, compliance words in the user's style (on screen in Shred's piece pane)."""
    import html as H
    cfg = cfg or load()
    st = cfg["style"]
    css = ";".join(x for x in ("font-weight:700" if st["bold"] else "", "font-style:italic" if st["italic"] else "",
                                "text-decoration:underline" if st["underline"] or not styled(cfg) else "",
                                f"color:#{st['color']}" if st["color"] else "",
                                f"background:#{st['highlight']}" if st["highlight"] else "") if x)
    return "".join(f'<span style="{css}">{H.escape(t)}</span>' if w else H.escape(t) for t, w in segments(text, cfg, *_marks(it)))


def mark(it, words, on=True):
    """4.18.0: words on the piece it are compliance language (on) or are not (False: the list's mark taken off here)."""
    w = " ".join(str(words).split()).strip(" .,;:()\"'")
    if not w or len(w) > 120:
        return False
    cl = it.setdefault("cl", {})
    a, n = [x for x in cl.get("add", []) if x.lower() != w.lower()], [x for x in cl.get("not", []) if x.lower() != w.lower()]
    (a if on else n).append(w)
    cl["add"], cl["not"] = a, n
    if not a and not n:
        it.pop("cl", None)
    return True


def clear(it):
    return bool(it.pop("cl", None))


def tk_font_options(cfg, family, size):
    """(font tuple, foreground, background) for a tk.Text tag."""
    st = cfg["style"]
    mods = (["bold"] if st["bold"] else []) + (["italic"] if st["italic"] else []) + (["underline"] if st["underline"] else [])
    return (family, size, " ".join(mods) or "normal"), ("#" + st["color"]) if st["color"] else None, \
        ("#" + st["highlight"]) if st["highlight"] else None


def _team_dirty(path):
    """4.7.1: the team library's workbook follows a list saved here."""
    try:
        import teamlib
        teamlib.mark_dirty_file(path)
    except Exception:  # noqa: BLE001
        pass
