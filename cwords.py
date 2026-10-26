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


def segments(text, cfg=None):
    """[(piece, is_compliance_word)] covering the whole text in order."""
    cfg = cfg or load()
    pat = pattern(cfg["words"])
    text = str(text or "")
    if not pat:
        return [(text, False)] if text else []
    hits, last = [], None
    for m in pat.finditer(text):
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


def styled(cfg):
    st = cfg["style"]
    return st["bold"] or st["italic"] or st["underline"] or bool(st["color"]) or bool(st["highlight"])


def docx_parts(text, base=None, cfg=None):
    """Runs for docxw.Doc.rich: the base format everywhere, the user's style added on compliance words."""
    cfg = cfg or load()
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
    return [(t, word if w else base) for t, w in segments(text, cfg)] or [("", base)]


def xlsx_value(text, cfg=None):
    """A rich-text cell value for openpyxl (Excel has no highlight per run, so highlight is left out there)."""
    cfg = cfg or load()
    text = str(text or "")
    segs = segments(text, cfg)
    if not styled(cfg) or not any(w for _t, w in segs):
        return text
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    st = cfg["style"]
    font = InlineFont(b=st["bold"] or None, i=st["italic"] or None, u="single" if st["underline"] else None,
                      color=("FF" + st["color"]) if st["color"] else None)
    return CellRichText(*[TextBlock(font, t) if w else t for t, w in segs])


def tk_font_options(cfg, family, size):
    """(font tuple, foreground, background) for a tk.Text tag."""
    st = cfg["style"]
    mods = (["bold"] if st["bold"] else []) + (["italic"] if st["italic"] else []) + (["underline"] if st["underline"] else [])
    return (family, size, " ".join(mods) or "normal"), ("#" + st["color"]) if st["color"] else None, \
        ("#" + st["highlight"]) if st["highlight"] else None
