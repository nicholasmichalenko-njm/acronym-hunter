"""Equations and their symbols.

Three sources, all read without OCR except the last:
  1. Word / PowerPoint equation-editor math (OMML, the <m:oMath> markup): read exactly, structure included.
  2. Typed math in text and PDFs (F = m·a, Δv = I_sp·g₀·ln(m₀/m_f)): found by its operators, Greek letters,
     subscripts and superscripts.
  3. Definitions in the document: "where ṁ is the mass flow rate", nomenclature lists ("σ_y – yield stress"),
     and nomenclature tables (symbol in one cell, meaning in the next).
Pure functions only: app_gui wires them into scanning and matching.
"""
import re
import unicodedata

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
def _m(tag):
    return "{%s}%s" % (M_NS, tag)

EQ_LABEL = " [equation]"          # chunk label suffix: text is one equation, kept as-is in project files
DEF_LABEL = " [symbol definitions]"   # chunk label suffix: lines "symbol<TAB>meaning"
PIC_LABEL = " [equation picture]"     # chunk label suffix: a picture that looks like it holds math

FUNCTIONS = set("sin cos tan sec csc cot sinh cosh tanh arcsin arccos arctan atan asin acos ln log exp lim max min "
                "det arg mod sgn sign erf deg rad abs".split())
GREEK = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψωϑϕϵϱς"
_SUBS = str.maketrans("₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₔₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ", "0123456789aeoxəhklmnpstijruv")
_SUPS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱ⁺⁻", "0123456789ni+-")
MATH_OPS = set("+−-×·÷/^√∑∏∫∮∂∇±∓∞≈≤≥≠≡∝≅∘⋅′″")
RELATIONS = "=≈≤≥≡∝≅≠"
STOP = set("is are was were be the an at of and or for to in on by as with from where when that this which we it its "
           "then so if than per into over under each all".split())   # words that end an equation, never part of it

# ---------------------------------------------------------------------------
# 1. OMML (equation editor) -> linear text + symbols
# ---------------------------------------------------------------------------
def _chr(el, prop, tag, default):
    p = el.find(_m(prop))
    c = p.find(_m(tag)) if p is not None else None
    return c.get(_m("val"), default) if c is not None else default

def _kid(el, tag):
    return el.find(_m(tag))

def omml_text(el):
    """Linear text of an OMML element: I_sp, (num)/(den), √(x), ∫_a^b f, ṁ (accent kept as a combining mark)."""
    if el is None:
        return ""
    tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
    T = omml_text
    if tag == "r":
        return "".join(t.text or "" for t in el.iter(_m("t")))
    if tag == "t":
        return el.text or ""
    if tag == "sSub":
        return T(_kid(el, "e")) + "_" + _grp(T(_kid(el, "sub")))
    if tag == "sSup":
        return T(_kid(el, "e")) + "^" + _grp(T(_kid(el, "sup")))
    if tag == "sSubSup":
        return T(_kid(el, "e")) + "_" + _grp(T(_kid(el, "sub"))) + "^" + _grp(T(_kid(el, "sup")))
    if tag == "sPre":
        return "{}_" + _grp(T(_kid(el, "sub"))) + "^" + _grp(T(_kid(el, "sup"))) + T(_kid(el, "e"))
    if tag == "f":
        return "(" + T(_kid(el, "num")) + ")/(" + T(_kid(el, "den")) + ")"
    if tag == "rad":
        deg = T(_kid(el, "deg"))
        return ("∜" if deg == "4" else "∛" if deg == "3" else "√") + "(" + T(_kid(el, "e")) + ")"
    if tag == "d":
        beg, end, sep = _chr(el, "dPr", "begChr", "("), _chr(el, "dPr", "endChr", ")"), _chr(el, "dPr", "sepChr", "|")
        return beg + (", " if sep == "|" else sep).join(T(e) for e in el.findall(_m("e"))) + end
    if tag == "nary":
        op = _chr(el, "naryPr", "chr", "∫")
        sub, sup = T(_kid(el, "sub")), T(_kid(el, "sup"))
        return op + ("_" + _grp(sub) if sub else "") + ("^" + _grp(sup) if sup else "") + " " + T(_kid(el, "e"))
    if tag == "acc":
        mark = _chr(el, "accPr", "chr", "̂")
        mark = {"˙": "̇", "¨": "̈", "^": "̂", "~": "̃", "¯": "̄", "→": "⃗", "⃗": "⃗"}.get(mark, mark)
        base = T(_kid(el, "e"))
        return unicodedata.normalize("NFC", base + mark) if len(base) == 1 else base + mark
    if tag == "bar":
        return T(_kid(el, "e")) + "̅"
    if tag == "func":
        return T(_kid(el, "fName")) + "(" + T(_kid(el, "e")) + ")"
    if tag in ("limLow", "limUpp"):
        return T(_kid(el, "e")) + ("_" if tag == "limLow" else "^") + _grp(T(_kid(el, "lim")))
    if tag == "m":
        return "[" + "; ".join(", ".join(T(e) for e in mr.findall(_m("e"))) for mr in el.findall(_m("mr"))) + "]"
    if tag == "eqArr":
        return "; ".join(T(e) for e in el.findall(_m("e")))
    if tag.endswith("Pr") or tag in ("ctrlPr",):
        return ""
    return "".join(T(c) for c in el)

def _grp(s):
    s = s.strip()
    return s if len(s) <= 1 else "{" + s + "}"

def omml_symbols(el):
    """Variable symbols in an OMML equation, with subscripts and accents attached: I_sp, m_0, ṁ, Δv, σ_y."""
    out = []
    def walk(e):
        tag = e.tag.split("}")[-1] if isinstance(e.tag, str) else ""
        if tag in ("sSub", "sSubSup"):
            base, sub = omml_text(_kid(e, "e")).strip(), omml_text(_kid(e, "sub")).strip()
            if _simple(base) and re.fullmatch(r"[\w,.′̀-ͯ]{1,8}", sub or ""):
                out.append(normalize_symbol(base + "_" + sub))
                if tag == "sSubSup":
                    walk_kids(_kid(e, "sup"))
                return
        if tag == "acc" or tag == "bar":
            t = omml_text(e).strip()
            if _simple(unicodedata.normalize("NFD", t).rstrip("̀́̂̃̄̅̇̈⃗")):
                out.append(normalize_symbol(t)); return
        if tag == "func":
            walk_kids(_kid(e, "e")); return
        if tag == "r":
            out.extend(symbols_in_text(omml_text(e), from_math=True)); return
        walk_kids(e)
    def walk_kids(e):
        if e is not None:
            for c in e:
                walk(c)
    walk(el)
    return _dedupe(out)

def _simple(base):
    return bool(base) and bool(re.fullmatch(rf"[A-Za-z{GREEK}][A-Za-z{GREEK}]{{0,3}}", base))

# ---------------------------------------------------------------------------
# 2. Symbols and equations in plain text
# ---------------------------------------------------------------------------
_SYM = re.compile(rf"(?<![A-Za-z{GREEK}_])([{GREEK}][A-Za-z]{{0,2}}|[A-Za-z]{{1,4}})([\u0300-\u036f\u20d7]*)"
                  rf"((?:_\{{[^}}]{{1,12}}\}}|_[A-Za-z0-9]{{1,6}}|[₀-₉ₐ-ₜᵢⱼᵣᵤᵥ]+|[0-9]{{1,2}}(?![0-9.]))?)(?![A-Za-z{GREEK}\u0300-\u036f])")

def normalize_symbol(sym):
    """One spelling per symbol: m₀ -> m_0, I_{sp} -> I_sp, accents composed (m + dot -> ṁ)."""
    s = unicodedata.normalize("NFC", sym.strip())
    s = re.sub(r"[₀-₉ₐ-ₜᵢⱼᵣᵤᵥ]+", lambda mt: "_" + mt.group(0).translate(_SUBS), s)
    s = re.sub(r"_\{([^{}]*)\}", lambda mt: "_" + mt.group(1).replace(" ", ""), s)
    s = re.sub(r"^([^\W\d_]{1,4})([0-9]{1,2})$", r"\1_\2", s)   # OCR or typed m0 -> m_0
    return s.replace("__", "_")

def symbols_in_text(text, from_math=False, common=frozenset()):
    """Symbols in an equation's text. Plain words (common English, 4+ letters without a subscript) and function names
    are not symbols. In equation-editor runs every letter group counts."""
    out = []
    text = unicodedata.normalize("NFD", text)   # m with dot above -> m + combining dot, so accents attach to their letter
    for mt in _SYM.finditer(text):
        core, marks, sub = mt.group(1), mt.group(2), mt.group(3)
        if core.lower() in FUNCTIONS and not sub:
            continue
        lhs = bool(re.match(r"\s*[=≈≡]", text[mt.end():]))   # left of an equals sign: always a symbol (Re = ...)
        if not from_math and not lhs:
            if core.lower() in STOP and not sub and not marks:
                continue
            if re.search(r"\d\s*$", text[:mt.start()]) and core.isascii() and len(core) >= 2 and not sub:
                continue   # "276 MPa": a unit after a number, not a symbol
            if core.isalpha() and core.isascii() and len(core) >= 4 and not sub:
                continue
            if core.lower() in common and len(core) >= 2 and not sub and not marks:
                continue
        out.append(normalize_symbol(core + marks + sub))
    return _dedupe(out)

def _dedupe(items):
    return list(dict.fromkeys(i for i in items if i))

def _mathy(tok, common):
    t = tok.strip(",;:.")
    if not t or t.lower() in STOP:
        return False
    if any(c in MATH_OPS or c in GREEK or c in "()[]{}_^" or c.isdigit() or "₀" <= c <= "ₜ" or c in "⁰¹²³⁴⁵⁶⁷⁸⁹" for c in t):
        return True
    if t.isalpha():
        return len(t) <= 3 or t.lower() in FUNCTIONS or (len(t) <= 5 and t.lower() not in common)
    return len(t) <= 4

def _signal(expr):
    """True if text carries real math: an operator, Greek letter, sub/superscript, or root/sum/integral."""
    return bool(re.search(rf"[{GREEK}√∑∏∫∮∂∇±×·÷^_⋅′]|[₀-₉ₐ-ₜ⁰-⁹]|\w\s*[*/]\s*\w|\w\s+[+−-]\s+\w|\)\s*/\s*\(", expr))

def find_equations(line, common=frozenset()):
    """Equations in one line of text: a relation (= ≈ ≤ ≥ ≡ ∝ ≠) with math on both sides."""
    if not any(r in line for r in RELATIONS):
        return []
    toks = line.split()
    out, i = [], 0
    while i < len(toks):
        tok = toks[i]
        if any(r in tok for r in RELATIONS):
            j = i
            while j - 1 >= 0 and _mathy(toks[j - 1], common):
                j -= 1
            k = i
            while k + 1 < len(toks) and _mathy(toks[k + 1], common):
                k += 1
            left = " ".join(toks[j:i]) + (tok.split("=")[0] if tok not in RELATIONS and "=" in tok else "")
            right = " ".join(toks[i + 1:k + 1])
            expr = " ".join(toks[j:k + 1]).strip(" ,;.:")
            sides_ok = (left.strip() or not tok.startswith(tuple(RELATIONS))) and (right.strip() or not tok.endswith(tuple(RELATIONS)))
            if sides_ok and len(expr) >= 3 and _signal(expr):
                out.append(expr)
            i = k + 1
        else:
            i += 1
    return out

# ---------------------------------------------------------------------------
# 3. Definitions: "where X is ...", nomenclature lines and tables
# ---------------------------------------------------------------------------
_SYM_PAT = rf"(?:[{GREEK}][A-Za-z]{{0,2}}|[A-Za-z]{{1,4}})[\u0300-\u036f\u20d7]*(?:_\{{[^}}]{{1,12}}\}}|_[A-Za-z0-9]{{1,6}}|[₀-₉ₐ-ₜ]+)?"
_WHERE = re.compile(rf"(?:\bwhere\b|\band\b|,|;)\s*({_SYM_PAT})\s+(?:is|=|denotes|represents|equals|are)\s+(?:the\s+|a\s+|an\s+)?"
                    rf"([A-Za-z][\w\- /()]{{2,60}}?)(?=[,;.]|\s+and\b|$)")
_LIST = re.compile(rf"^\s*({_SYM_PAT})\s*(?:=|:|–|—|-{{1,2}}|\t)\s*([A-Za-z][\w ,\-/()]{{2,80}})$")

def find_definitions(lines, common=frozenset()):
    """[(symbol, meaning)] stated in the text. A meaning must be words, not more math."""
    out = []
    lines = [unicodedata.normalize("NFD", l) for l in lines]
    for n, raw in enumerate(lines):
        line = raw.strip()
        for mt in _WHERE.finditer(line):
            if mt.group(1).lower() not in STOP:
                out.append((normalize_symbol(mt.group(1)), unicodedata.normalize("NFC", mt.group(2).strip(" .,;"))))
        mt = _LIST.match(line)
        if mt and not _signal(mt.group(2)) and len(mt.group(2).split()) >= 1 and mt.group(2)[0].isalpha():
            sym = mt.group(1)
            if not (sym.isupper() and len(sym) >= 2 and sym.isascii()):   # "PDR - Preliminary ..." is an acronym line
                out.append((normalize_symbol(sym), unicodedata.normalize("NFC", mt.group(2).strip(" .,;"))))
        # nomenclature table read as separate cells: a lone symbol, then its meaning on the next line
        if re.fullmatch(_SYM_PAT, line) and n + 1 < len(lines):
            nxt = lines[n + 1].strip()
            if len(nxt.split()) >= 2 and nxt[0].isalpha() and not _signal(nxt) and not re.fullmatch(_SYM_PAT, nxt):
                if not (line.isupper() and len(line) >= 2 and line.isascii()):
                    out.append((normalize_symbol(line), unicodedata.normalize("NFC", nxt.strip(" .,;"))))
    return out

def looks_like_math_picture(ocr_text):
    """OCR text of a picture that is probably an equation: a relation plus math signals, mostly short tokens."""
    t = ocr_text.strip()
    if not t or not any(r in t for r in RELATIONS):
        return False
    toks = t.split()
    short = sum(1 for x in toks if len(x) <= 4) / max(1, len(toks))
    return _signal(t) and short >= 0.5

def text_math_chunks(chunks, common=frozenset()):
    """Extra chunks for typed equations and definitions found in a file's ordinary chunks."""
    extra, defs = [], []
    for label, text in chunks:
        if label.endswith((EQ_LABEL, DEF_LABEL, PIC_LABEL)):
            continue
        lines = text.splitlines()
        for line in lines:
            for eq in find_equations(line, common):
                extra.append((label + EQ_LABEL, eq))
        defs += find_definitions(lines, common)
        is_picture = bool(re.search(r"\((Image|Vector graphic)\)|, (image|vector) ", label))
        if is_picture and looks_like_math_picture(text):
            extra.append((label + PIC_LABEL, " ".join(text.split())[:200]))
    if defs:
        name = chunks[0][0].split(" (")[0] if chunks else "file"
        extra.append((name + DEF_LABEL, "\n".join(f"{s}\t{d}" for s, d in dict.fromkeys(defs))))
    return extra
