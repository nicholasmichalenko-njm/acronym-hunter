"""Pages, sections, headers and footers: a section map read from the file, the pagination scheme the effort
chose (pe.rules PAGINATION_PRESETS or a custom one), the audit between the two, and the fixes.

map_sections(pkg, std) -> SectionMap      read only
audit(sm, std)         -> [Finding]       area "pages"; every finding names its rule and its fix
fixes (guarded write path, closed file; the live mode makes the same changes through Word):
  op_chapter_breaks(pkg, std)   a Next Page section break before each chapter heading that needs its own section
  op_page_numbers(pkg, std)     pgNumType of every section from the scheme (format, restart, chapter part)
  op_page_setup(pkg, std)       paper, orientation and margins of each section to its PageSetup row
  op_hf_text(pkg, std, old, new) typed header or footer text (a volume name copied from another volume)
  op_page_field_clean(pkg)      PAGE fields lose format switches (the section owns the format)

Rules of the team kept here (brief 3.6): the section settings own the page number format, a PAGE field has no
switch; a placed landscape or tabloid page continues the numbers and keeps headers and footers linked;
"Different odd and even pages" is a document setting that no fix changes.
"""
import copy
import math
import re
from dataclasses import dataclass, field

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, local, ensure, remove, insert_ordered
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import rules as R

TW = 1440
HF_TYPES = ("default", "first", "even")


@dataclass
class HF:
    part: str              # word/footer3.xml or "" when the type is not set anywhere before
    own: bool              # this section has its own reference (not linked to previous)
    text: str
    fields: list           # instruction words: PAGE, STYLEREF, DOCPROPERTY ...
    page_switches: list    # PAGE fields with a format switch
    typed_page: str        # a typed "Page 5" style number, if any


@dataclass
class Section:
    i: int
    first_para: int        # body paragraph index of its first paragraph
    first_style: str
    first_text: str
    chars: int
    pages_est: int
    orient: str
    paper: str             # Letter | Tabloid | Legal | other
    margins: dict          # inches
    numbers: dict          # current pgNumType: fmt, start, chapStyle, chapSep
    title_pg: bool
    headers: dict          # type -> HF
    footers: dict
    part: str = ""
    chapter_start: bool = False
    expected: dict = field(default_factory=dict)
    shows: str = ""        # what the first page number reads as (estimate)
    el: object = None      # the sectPr
    owner: object = None   # the paragraph that holds the sectPr (None for the body's final sectPr)


@dataclass
class ChapterInside:
    section: int
    para: int
    style: str
    text: str
    break_possible: bool   # the element before the heading is a paragraph, so a break can go there


@dataclass
class SectionMap:
    sections: list
    inside: list           # chapter headings that do not start a section
    even_odd: bool
    scheme: dict
    stats: dict


# ---------------------------------------------------------------- reading
def _style_names(pkg):
    sp = pkg.word_part("/styles")
    out = {}
    if sp:
        for s in pkg.tree(sp).findall("w:style", NS):
            n = s.find("w:name", NS)
            if n is not None:
                out[s.get(q("styleId"))] = canon_style(n.get(q("val")))
    return out


BUILTIN = {"normal": "Normal", "caption": "Caption", "title": "Title", "toc heading": "TOC Heading",
           "table of figures": "Table of Figures", "list bullet": "List Bullet", "list number": "List Number",
           "list paragraph": "List Paragraph", "header": "Header", "footer": "Footer",
           "footnote text": "Footnote Text"}


def canon_style(name):
    """Word stores built-in names in lower case (heading 1, toc 2); the app shows them as the UI does."""
    l = (name or "").lower()
    if l in BUILTIN:
        return BUILTIN[l]
    m = re.match(r"^(heading|toc|list bullet|list number|list continue) (\d)$", l)
    if m:
        base = {"heading": "Heading", "toc": "TOC", "list bullet": "List Bullet", "list number": "List Number",
                "list continue": "List Continue"}[m.group(1)]
        return f"{base} {m.group(2)}"
    return name


def _vt(el):
    return " ".join(visible_text(el).replace("\u00b6", " ").split())


def _pstyle(p, names):
    ps = p.find("w:pPr/w:pStyle", NS)
    sid = ps.get(q("val")) if ps is not None else "Normal"
    return names.get(sid, sid)


def _body_blocks(pkg):
    """[(sectPr, owner paragraph or None, [block elements])] for the main body."""
    body = pkg.tree(pkg.main).find("w:body", NS)
    out, cur = [], []
    for el in body:
        n = local(el)
        if n == "p":
            cur.append(el)
            sp = el.find("w:pPr/w:sectPr", NS)
            if sp is not None:
                out.append((sp, el, cur)); cur = []
        elif n in ("tbl", "sdt"):
            cur.append(el)
        elif n == "sectPr":
            out.append((el, None, cur)); cur = []
    return out


def _instr_words(root):
    words, page_sw = [], []
    instr, depth = "", 0
    for r in root.iter(q("r"), q("fldSimple")):
        if local(r) == "fldSimple":
            ins = " ".join((r.get(q("instr")) or "").split())
            words.append(ins.split(" ")[0].upper() if ins else "")
            if words[-1] == "PAGE" and "\\*" in ins:
                page_sw.append(ins)
            continue
        fc = r.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
                if depth == 1:
                    instr = ""
            elif t == "end":
                depth -= 1
                if depth == 0:
                    ins = " ".join(instr.split())
                    words.append(ins.split(" ")[0].upper() if ins else "")
                    if words[-1] == "PAGE" and "\\*" in ins:
                        page_sw.append(ins)
            continue
        it = r.find("w:instrText", NS)
        if it is not None and depth == 1:
            instr += it.text or ""
    return words, page_sw


TYPED_PAGE = re.compile(r"\bPage\s+(\d+|[ivxlc]+|[A-Z]-\d+|\d+-\d+)\b")


def _text_outside_fields(root):
    """Visible text that is not a field result (to spot a typed page number)."""
    out, depth, in_result = [], 0, False
    for el in root.iter(q("r"), q("p")):
        if local(el) == "p":
            out.append("\n"); continue
        fc = el.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
            elif t == "separate":
                in_result = True
            elif t == "end":
                depth -= 1
                in_result = depth > 0 and in_result
            continue
        if depth == 0:
            for t in el.findall("w:t", NS):
                out.append(t.text or "")
            if el.find("w:tab", NS) is not None:
                out.append("\t")
    return "".join(out)


def _hf_info(pkg, part, own):
    if not part:
        return HF("", own, "", [], [], "")
    root = pkg.tree(part)
    words, sw = _instr_words(root)
    typed = TYPED_PAGE.search(_text_outside_fields(root))
    return HF(part, own, _vt(root), words, sw, typed.group(0) if typed else "")


def _paper(w, h):
    a, b = sorted((w, h))
    for name, (x, y) in {"Letter": (8.5, 11), "Legal": (8.5, 14), "Tabloid": (11, 17), "A4": (8.27, 11.69)}.items():
        if abs(a - x) < 0.05 and abs(b - y) < 0.05:
            return name
    return f"{a:g} x {b:g} in"


def _fmt_page(n, fmt):
    if fmt in ("lowerRoman", "upperRoman"):
        vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
                (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
        s, k = "", n
        for v, r in vals:
            while k >= v:
                s += r; k -= v
        return s.upper() if fmt == "upperRoman" else s
    if fmt in ("lowerLetter", "upperLetter"):
        s = chr(ord("a") + (n - 1) % 26) * ((n - 1) // 26 + 1)
        return s.upper() if fmt == "upperLetter" else s
    return str(n)


def map_sections(pkg, std):
    names = _style_names(pkg)
    rels = pkg.rels_of(pkg.main)
    settings = pkg.word_part("/settings")
    even_odd = settings is not None and pkg.tree(settings).find("w:evenAndOddHeaders", NS) is not None
    scheme = std["pagination"]
    heading_levels = {f"Heading {k}": k for k in range(1, 10)}
    secs, inside = [], []
    last_hf = {("header", t): "" for t in HF_TYPES} | {("footer", t): "" for t in HF_TYPES}
    pidx = 0
    blocks = _body_blocks(pkg)
    para_of = {}
    for bi, (sp, owner, els) in enumerate(blocks):
        first = None
        chars = 0
        page_breaks = 0
        for el in els:
            if local(el) == "p":
                para_of[el] = pidx; pidx += 1
                t = visible_text(el)
                chars += len(t)
                page_breaks += sum(1 for b in el.iter(q("br")) if b.get(q("type")) == "page")
                if first is None and (t.strip() or _pstyle(el, names) != "Normal"):
                    first = el
            else:
                rows = sum(1 for _ in el.iter(q("tr")))
                chars += rows * 120
                for p in el.iter(q("p")):
                    para_of[p] = pidx; pidx += 1
                if first is None:
                    first = el
        pgsz, pgmar = sp.find("w:pgSz", NS), sp.find("w:pgMar", NS)
        w = int(pgsz.get(q("w"), 12240)) / TW if pgsz is not None else 8.5
        h = int(pgsz.get(q("h"), 15840)) / TW if pgsz is not None else 11
        orient = (pgsz.get(q("orient")) if pgsz is not None else None) or ("landscape" if w > h else "portrait")
        mg = {k: (int(pgmar.get(q(k), 1440)) / TW if pgmar is not None else 1.0)
              for k in ("top", "bottom", "left", "right", "header", "footer")}
        pn = sp.find("w:pgNumType", NS)
        numbers = {k: pn.get(q(k)) for k in ("fmt", "start", "chapStyle", "chapSep") if pn is not None and pn.get(q(k))}
        heads, foots = {}, {}
        for kind, store in (("header", heads), ("footer", foots)):
            refs = {r.get(q("type")): r.get(f"{{{NS['r']}}}id") for r in sp.findall(f"w:{kind}Reference", NS)}
            for t in HF_TYPES:
                if t in refs and refs[t] in rels:
                    last_hf[(kind, t)] = rels[refs[t]][1]
                store[t] = _hf_info(pkg, last_hf[(kind, t)], t in refs)
        fs = (_pstyle(first, names) if first is not None and local(first) == "p" else ("table" if first is not None else ""))
        ft = _vt(first)[:80] if first is not None else ""
        lines = max(1, math.ceil(chars / 3300)) + page_breaks
        s = Section(bi, para_of.get(els[0], pidx) if els else pidx, fs, ft, chars, lines, orient, _paper(w, h), mg,
                    numbers, sp.find("w:titlePg", NS) is not None and sp.find("w:titlePg", NS).get(q("val"), "1") not in ("0", "false"),
                    heads, foots, el=sp, owner=owner)
        secs.append(s)
        # chapter headings that sit inside the section (not first)
        for el in els:
            if local(el) != "p" or el is first:
                continue
            st = _pstyle(el, names)
            if st in heading_levels:
                prev = el.getprevious()
                inside.append(ChapterInside(bi, para_of[el], st, _vt(el)[:80],
                                            prev is not None and local(prev) == "p"))
    sm = SectionMap(secs, inside, even_odd, scheme, {"sections": len(secs)})
    _assign_parts(sm, std)
    _expect(sm, std)
    _shows(sm)
    return sm


def _starts(part, s, index, total=None):
    st = part.get("starts", {})
    if st.get("first_section"):
        return index == 0
    if st.get("last_section"):                       # 3.6.0: a back cover; only with one of its styles
        styles = st.get("styles") or ([st["style"]] if st.get("style") else [])
        return total is not None and index == total - 1 and index > 0 and s.first_style in styles
    if st.get("style"):
        return s.first_style == st["style"]
    return False


def _assign_parts(sm, std):
    parts = sm.scheme["parts"]
    cur = None
    started = set()
    for s in sm.sections:
        for k, p in enumerate(parts):
            if p["key"] in started:
                continue
            if _starts(p, s, s.i, len(sm.sections)) and (cur is None or k > cur):
                cur = k
                started.add(p["key"])
                s.chapter_start = True      # first section of a part starts it
                break
        s.part = parts[cur]["key"] if cur is not None else parts[0]["key"]
        p = parts[cur] if cur is not None else parts[0]
        if p.get("chapter_style") and s.first_style == p["chapter_style"]:
            s.chapter_start = True
    # the chapter headings inside a section matter only where the part restarts at each chapter
    keep = []
    for c in sm.inside:
        p = _part(sm, sm.sections[c.section].part)
        if p.get("chapter_style") == c.style and (p.get("numbers") or {}).get("restart") == "each":
            keep.append(c)
    sm.inside = keep


def _part(sm, key):
    return next(p for p in sm.scheme["parts"] if p["key"] == key)


def _is_placed_page(s, std):
    return s.orient == "landscape"


def _expect(sm, std):
    """What each section's pgNumType must be, from its part."""
    first_of_part = {}
    for s in sm.sections:
        first_of_part.setdefault(s.part, s.i)
    for s in sm.sections:
        p = _part(sm, s.part)
        n = p.get("numbers")
        e = {}
        if n:
            if n["fmt"] != "decimal":
                e["fmt"] = n["fmt"]
            restart = (n["restart"] == "part" and s.i == first_of_part[s.part]) or \
                      (n["restart"] == "each" and s.chapter_start and not _is_placed_page(s, std))
            if restart:
                e["start"] = str(n.get("start_at", 1))
            if n.get("chapter_level"):
                e["chapStyle"] = str(n["chapter_level"])
                if n.get("separator", "hyphen") != "hyphen":
                    e["chapSep"] = n["separator"]
        s.expected = e


def _shows(sm):
    """The number the first page of each section reads as, with estimated page counts."""
    page, chap_counter = 1, {}
    chapter_label = {}
    num_h1, num_h7 = 0, 0
    for s in sm.sections:
        if s.first_style == "Heading 1":
            num_h1 += 1
        if s.first_style == "Heading 7":
            num_h7 += 1
        n = s.numbers
        if "start" in n:
            page = int(n["start"])
        fmt = n.get("fmt", "decimal")
        p = _part(sm, s.part)
        if p.get("numbers") is None:
            s.shows = "none"
        else:
            num = _fmt_page(page, fmt)
            cs = n.get("chapStyle")
            if cs:
                ch = str(num_h1) if cs == "1" else (chr(64 + num_h7) if cs == "7" and num_h7 else "?")
                num = f"{ch}{R.SEPARATORS.get(n.get('chapSep', 'hyphen'), '-')}{num}"
            s.shows = num
        page += s.pages_est


def _norm_numbers(n):
    """Defaults Word assumes when an attribute is missing: decimal, hyphen."""
    return {k: v for k, v in n.items() if not ((k == "fmt" and v == "decimal") or (k == "chapSep" and v == "hyphen"))}


# ---------------------------------------------------------------- audit
def _fill(text, std):
    return re.sub(r"\{(\w+)\}", lambda m: str(std["variables"].get(m.group(1), m.group(0))), text or "")


def audit(sm, std):
    from prodengine.pe.docmap import Finding
    out = []
    setups = std["page_setups"]
    vol = std["variables"].get("volume_name", "")
    marking = std["variables"].get("marking", "")
    for c in sm.inside:
        out.append(Finding("pages", "error", "P3",
                           f"{c.style} \"{c.text}\" is inside section {c.section + 1}, so its pages do not restart and do not "
                           f"show its own chapter number", c.para, "op_chapter_breaks" if c.break_possible else "", "chapter_breaks"))
    for s in sm.sections:
        p = _part(sm, s.part)
        where = s.first_para
        tag = f"Section {s.i + 1} ({p['name']})"
        cur = _norm_numbers(s.numbers)
        if s.part and p.get("numbers") is not None:
            want = s.expected
            if {k: cur.get(k) for k in ("fmt", "chapStyle", "chapSep")} != {k: want.get(k) for k in ("fmt", "chapStyle", "chapSep")}:
                out.append(Finding("pages", "error", "P1", f"{tag}: page numbers are {_describe(cur)}; the scheme says {_describe(want)}",
                                   where, "op_page_numbers", "numbers"))
            if ("start" in cur) != ("start" in want) or cur.get("start", "1") != want.get("start", "1"):
                if "start" in want:
                    what = f"{tag}: pages continue from the section before; the scheme restarts at {want['start']} here"
                else:
                    what = f"{tag}: pages restart at {cur['start']}; the scheme continues them here"
                    if _is_placed_page(s, std):
                        what = f"{tag}: a placed landscape page restarts its numbers; it must continue"
                out.append(Finding("pages", "error", "P2", what, where, "op_page_numbers", "numbers"))
        # page setup
        key = "landscape" if s.orient == "landscape" and s.paper == "Letter" else ("tabloid" if s.paper == "Tabloid" else "portrait")
        ps = setups.get(key)
        if ps:
            want = {k: float(R.value(std, ps[k])) for k in ("top", "bottom", "left", "right", "header", "footer")}
            off = [k for k in want if abs(want[k] - s.margins[k]) > 0.01]
            if off:
                out.append(Finding("pages", "warning", "P9",
                                   f"{tag}: margins {', '.join(f'{k} {s.margins[k]:g}' for k in off)} in; {ps['name']} has "
                                   f"{', '.join(f'{k} {want[k]:g}' for k in off)}", where, "op_page_setup", "setup"))
        if s.orient == "landscape" and s.i > 0 and (s.headers["default"].own or s.footers["default"].own):
            out.append(Finding("pages", "warning", "P8", f"{tag}: a placed landscape page has its own header or footer; "
                                                         f"the rule keeps them linked to the page before", where, "word:link", "placed"))
        # headers and footers
        fd = s.footers["default"]
        hd = s.headers["default"]
        if p.get("numbers") is None:
            if "PAGE" in fd.fields:
                out.append(Finding("pages", "error", "P7", f"{tag}: shows a page number; the scheme has none here", where,
                                   "word:unlink", "hf"))
        else:
            if "PAGE" not in fd.fields and "PAGE" not in hd.fields:
                out.append(Finding("pages", "error", "P6", f"{tag}: no PAGE field in the header or footer" +
                                   (f" (typed \"{fd.typed_page}\")" if fd.typed_page else ""), where, "", "hf"))
        if fd.page_switches:
            out.append(Finding("pages", "warning", "P5", f"{tag}: the PAGE field carries a format switch "
                                                         f"({fd.page_switches[0]}); the section owns the format", where,
                               "op_page_field_clean", "hf"))
        want_head = _fill(p.get("header", ""), std)
        if want_head and hd.part and want_head not in hd.text and "STYLEREF" not in hd.fields and "DOCPROPERTY" not in hd.fields:
            out.append(Finding("pages", "error", "P4", f"{tag}: the header reads \"{hd.text[:60]}\"; this volume is \"{want_head}\"",
                               where, "op_hf_text", "hf"))
        if p.get("footer_marking") and marking and marking[:40] not in fd.text and marking[:40] not in hd.text:
            out.append(Finding("pages", "error", "P10", f"{tag}: the restriction marking is missing from the footer",
                               where, "word:marking", "hf"))
    # dedupe P10/P4/P7 for sections that share the same header or footer part
    seen, ded = set(), []
    for f in out:
        key = (f.rule, f.what.split(": ", 1)[-1])
        if f.rule in ("P4", "P10", "P5") and key in seen:
            continue
        seen.add(key)
        ded.append(f)
    return ded


def _describe(n):
    if not n or not any(k in n for k in ("fmt", "chapStyle")):
        base = "1, 2, 3"
    else:
        f = n.get("fmt", "decimal")
        base = {"decimal": "1, 2, 3", "lowerRoman": "i, ii, iii", "upperRoman": "I, II, III",
                "lowerLetter": "a, b, c", "upperLetter": "A, B, C"}[f]
    if n.get("chapStyle"):
        ch = "chapter from Heading " + n["chapStyle"]
        base = ("A-1, A-2" if n["chapStyle"] == "7" else "2-1, 2-2") + f" ({ch})"
    return base


# ---------------------------------------------------------------- fixes
CHAPTER_ALLOWED = ("section_count",)
NUMBERS_ALLOWED = ()
SETUP_ALLOWED = ()
HF_TEXT_ALLOWED = ("word/header*.xml|text", "word/header*.xml|text_len", "word/footer*.xml|text", "word/footer*.xml|text_len")
PAGE_FIELD_ALLOWED = ("fields",)


def op_chapter_breaks(pkg, std):
    """A Next Page break before each chapter heading that sits inside a section, where the part restarts at
    each chapter. The new break carries the section's settings so the pages before it look exactly as now;
    the headers and footers move to it, and the section that now starts at the heading is linked to it."""
    pkg.touch(pkg.main)
    sm = map_sections(pkg, std)
    names = _style_names(pkg)
    blocks = _body_blocks(pkg)
    added = 0
    for c in sm.inside:
        if not c.break_possible:
            continue
        sp, owner, els = blocks[c.section]
        heading = next(el for el in els if local(el) == "p" and _vt(el)[:80] == c.text
                       and _pstyle(el, names) == c.style)
        prev = heading.getprevious()
        if prev.find("w:pPr/w:sectPr", NS) is not None:
            continue
        pkg.mark(prev)
        if owner is not None:
            pkg.mark(owner)
        else:
            pkg.mark(sp)
        new = copy.deepcopy(sp)
        for r in sp.findall("w:headerReference", NS) + sp.findall("w:footerReference", NS):
            sp.remove(r)                          # the later section inherits the same parts from the new one
        for r in new.findall("w:titlePg", NS):
            pass
        t = sp.find("w:type", NS)
        if t is not None:
            sp.remove(t)                          # starts on a new page (the default)
        ppr = ensure(prev, "pPr")
        insert_ordered(ppr, new)
        added += 1
        blocks = _body_blocks(pkg)
    return {"breaks_added": added, "after": "Then set page numbers", "checks": []}


def op_page_numbers(pkg, std):
    pkg.touch(pkg.main)
    sm = map_sections(pkg, std)
    changed = 0
    for s in sm.sections:
        cur = _norm_numbers(s.numbers)
        p = _part(sm, s.part)
        if p.get("numbers") is None:
            want = cur                             # no page numbers: leave the settings as they are
        else:
            want = s.expected
        if cur == want:
            continue
        pkg.mark(s.owner if s.owner is not None else s.el)
        remove(s.el, "pgNumType")
        if want:
            el = etree.Element(q("pgNumType"))
            for k in ("fmt", "start", "chapStyle", "chapSep"):
                if k in want:
                    el.set(q(k), want[k])
            insert_ordered(s.el, el)
        changed += 1
    return {"sections_changed": changed, "checks": []}


def op_page_setup(pkg, std):
    pkg.touch(pkg.main)
    sm = map_sections(pkg, std)
    changed = 0
    for s in sm.sections:
        key = "landscape" if s.orient == "landscape" and s.paper == "Letter" else ("tabloid" if s.paper == "Tabloid" else "portrait")
        ps = std["page_setups"].get(key)
        if not ps:
            continue
        want = {k: float(R.value(std, ps[k])) for k in ("top", "bottom", "left", "right", "header", "footer")}
        if all(abs(want[k] - s.margins[k]) <= 0.01 for k in want):
            continue
        pkg.mark(s.owner if s.owner is not None else s.el)
        pm = ensure(s.el, "pgMar")
        for k, v in want.items():
            pm.set(q(k), str(int(round(v * TW))))
        for k in ("gutter",):
            if pm.get(q(k)) is None:
                pm.set(q(k), "0")
        changed += 1
    return {"sections_changed": changed, "checks": []}


def op_hf_text(pkg, std, old, new):
    """Replace typed text old with new in every header and footer part. Only that text changes; the op proves
    it paragraph by paragraph. Fields are not touched (a STYLEREF or DOCPROPERTY updates in Word)."""
    done = []
    for part in pkg.stories():
        root = pkg.tree(part)
        if local(root) not in ("hdr", "ftr"):
            continue
        for p in root.iter(q("p")):
            before = visible_text(p)
            if old not in before:
                continue
            ts = [t for t in p.iter(q("t")) if next(t.iterancestors(q("instrText")), None) is None]
            joined = "".join(t.text or "" for t in ts)
            k = joined.find(old)
            if k < 0:
                continue                           # the text is split by a field or a tab: report only
            pkg.touch(part)
            pkg.mark(p)
            pos = 0
            remaining = None
            for t in ts:
                tx = t.text or ""
                a, b = pos, pos + len(tx)
                pos = b
                if b <= k or a >= k + len(old):
                    continue
                s0, s1 = max(k, a) - a, min(k + len(old), b) - a
                if remaining is None:
                    t.text = tx[:s0] + new + tx[s1:]
                    remaining = True
                else:
                    t.text = tx[:s0] + tx[s1:]
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            after = visible_text(p)
            if after != before.replace(old, new, 1):
                raise ValueError("header or footer text changed beyond the declared words")
            done.append(part)
    return {"parts": sorted(set(done)), "checks": []}


def op_page_field_clean(pkg):
    from prodengine.engine.ops.word_ops import op_hf_clean
    return op_hf_clean(pkg)


def scheme_summary(scheme, std):
    """Plain words for each part, for the screens."""
    out = []
    for p in scheme["parts"]:
        n = p.get("numbers")
        if not n:
            nums = "no page number"
        else:
            d = _describe({"fmt": n["fmt"], **({"chapStyle": str(n["chapter_level"])} if n.get("chapter_level") else {})})
            r = {"part": "restart at the part", "each": f"restart at each {p.get('chapter_style', 'chapter')}",
                 "never": "continue"}[n["restart"]]
            nums = f"{d}, {r}"
        out.append({"key": p["key"], "name": p["name"], "numbers": nums, "header": _fill(p.get("header", ""), std),
                    "marking": bool(p.get("footer_marking"))})
    return out
