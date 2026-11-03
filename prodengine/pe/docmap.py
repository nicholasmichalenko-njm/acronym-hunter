"""One read pass over a Word document that maps what QA/QC needs: headings and parts (body / appendix),
captions with their fields and expected numbers, TOCs and lists, bookmarks, and cross-references with their
targets. Read only. Text stays in memory for the screens; nothing here is logged.

build(pkg, std) -> DocMap   (pkg: engine.pkg.Package; std: pe.rules.resolve(...))
audit(dm, std)  -> [Finding] (grouped by area; every finding names its rule and whether a fix exists)
"""
import re
from dataclasses import dataclass, field

from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q
from prodengine.engine.fingerprint import visible_text

WP, WR = q("p"), q("r")
HEAD_RX = re.compile(r"^heading ([1-9])$", re.I)


@dataclass
class Para:
    i: int
    style: str
    level: int            # heading level 1..9, else 0
    text: str
    in_table: bool
    el: object = None


@dataclass
class Field:
    instr: str
    kind: str
    result: str
    para: int
    begin: object = None


@dataclass
class Caption:
    para: int
    label: str
    part: str             # body | appendix
    chapter: str          # expected chapter part: "2", "A" ("" when level 0)
    expected: str         # expected full number "2-3"
    shown: str            # number as it reads now (cached field results or typed)
    fields: list
    typed: bool
    sep: str
    after: str            # "period_tab", "period_space", "tab", "colon_space", "other"
    in_table_row: int     # -1 when not in a table, else the row index
    table: int            # 1-based table index or 0
    position: str         # "first_row" | "last_row" | "above" | "below" | "other"
    style: str


@dataclass
class Bookmark:
    name: str
    kind: str             # xref_target | toc_target | section_mark | scope | user | hidden_other
    start_para: int
    end_para: int
    wraps: str            # what it wraps: caption, heading, text, empty
    target_text: str = ""
    used_by: int = 0


@dataclass
class XRef:
    para: int
    kind: str             # REF, PAGEREF, NOTEREF, HYPERLINK
    target: str
    switches: list
    shown: str
    target_kind: str = ""
    target_now: str = ""
    status: str = ""      # ok | broken | stale | error_shown | no_charformat


@dataclass
class Toc:
    para: int
    instr: str
    kind: str             # main | list | other
    switches: dict
    entries: int
    entry_styles: set = field(default_factory=set)


@dataclass
class Finding:
    area: str             # captions | toc | bookmarks | xrefs | headings
    severity: str         # error | warning | info
    rule: str
    what: str
    where: int            # paragraph index
    fix: str = ""         # name of the fix that resolves it, or "" for report only
    group: str = ""


@dataclass
class DocMap:
    paras: list
    headings: list
    captions: list
    bookmarks: dict
    xrefs: list
    tocs: list
    first_appendix: int   # paragraph index of the first Heading 7, or -1
    stats: dict


# ---------------------------------------------------------------- helpers
def style_names(pkg):
    sp = pkg.word_part("/styles")
    out = {}
    if sp:
        for s in pkg.tree(sp).findall("w:style", NS):
            n = s.find("w:name", NS)
            if n is not None:
                out[s.get(q("styleId"))] = n.get(q("val"))
    return out


def para_style(p, names):
    ps = p.find("w:pPr/w:pStyle", NS)
    return names.get(ps.get(q("val")), ps.get(q("val"))) if ps is not None else "Normal"


def fields_in(p):
    """Top-level complex and simple fields of a paragraph, in order, with their shown results."""
    out, depth, cur = [], 0, None
    for el in p.iter(WR, q("fldSimple")):
        if el.tag == q("fldSimple"):
            out.append(Field(" ".join((el.get(q("instr")) or "").split()), "", visible_text(el).replace("\u00b6", ""), 0, el))
            continue
        fc = el.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
                if depth == 1:
                    cur = {"instr": "", "result": "", "sep": False, "begin": el}
            elif t == "separate" and depth == 1:
                cur["sep"] = True
            elif t == "end":
                depth -= 1
                if depth == 0 and cur:
                    out.append(Field(" ".join(cur["instr"].split()), "", cur["result"], 0, cur["begin"]))
                    cur = None
            continue
        if cur is not None and depth == 1:
            it = el.find("w:instrText", NS)
            if it is not None and not cur["sep"]:
                cur["instr"] += it.text or ""
            elif cur["sep"]:
                cur["result"] += "".join(t.text or "" for t in el.findall("w:t", NS)) + \
                    ("\t" if el.find("w:tab", NS) is not None else "")
    for f in out:
        f.kind = (f.instr.split()[0].upper() if f.instr else "")
    return out


def doc_fields(body, para_of):
    """Top-level fields of the body in document order; a field may span paragraphs (a TOC always does).
    Each: Field with para = paragraph of its begin, plus end_para and the paragraphs its result covers."""
    out, depth, cur = [], 0, None
    for el in body.iter(WR, q("fldSimple")):
        pi = para_of.get(id(next(el.iterancestors(WP), None)), 0)
        if el.tag == q("fldSimple"):
            if depth == 0:
                f = Field(" ".join((el.get(q("instr")) or "").split()), "", visible_text(el).replace("\u00b6", ""), pi, el)
                f.end_para = pi
                out.append(f)
            continue
        fc = el.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
                if depth == 1:
                    cur = {"instr": "", "result": "", "sep": False, "begin": el, "para": pi}
            elif t == "separate" and depth == 1:
                cur["sep"] = True
            elif t == "end":
                depth -= 1
                if depth == 0 and cur:
                    f = Field(" ".join(cur["instr"].split()), "", cur["result"], cur["para"], cur["begin"])
                    f.end_para = pi
                    out.append(f)
                    cur = None
            continue
        if cur is not None and depth == 1:
            it = el.find("w:instrText", NS)
            if it is not None and not cur["sep"]:
                cur["instr"] += it.text or ""
            elif cur["sep"]:
                cur["result"] += "".join(t.text or "" for t in el.findall("w:t", NS))
    for f in out:
        f.kind = (f.instr.split()[0].upper() if f.instr else "")
    return out


def to_alpha(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def classify_after(text_after_number):
    t = text_after_number
    if t.startswith(".\t"):
        return "period_tab"
    if t.startswith(". "):
        return "period_space"
    if t.startswith("\t"):
        return "tab"
    if t.startswith(": "):
        return "colon_space"
    return "other"


# ---------------------------------------------------------------- build
def _seq_text(n, fmt):
    """A caption's own number as Word shows it for the SEQ switch."""
    if fmt in ("ROMAN", "roman"):
        vals = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
                (5, "V"), (4, "IV"), (1, "I"))
        out, k = "", n
        for v, r in vals:
            while k >= v:
                out += r; k -= v
        return out if fmt == "ROMAN" else out.lower()
    if fmt in ("ALPHABETIC", "alphabetic"):
        out, k = "", n
        while k > 0:
            k, rem = divmod(k - 1, 26)
            out = chr(65 + rem) + out
        return out if fmt == "ALPHABETIC" else out.lower()
    return str(n)


def build(pkg, std):
    names = style_names(pkg)
    root = pkg.tree(pkg.main)
    body = root.find("w:body", NS)
    paras, headings = [], []
    para_of = {}
    tables = []
    for el in body.iter(WP, q("tbl")):
        if el.tag == q("tbl"):
            if not any(True for _ in el.iterancestors(q("tbl"))):
                tables.append(el)
            continue
        st = para_style(el, names)
        m = HEAD_RX.match(st)
        in_tbl = any(True for _ in el.iterancestors(q("tbl")))
        p = Para(len(paras), st, int(m.group(1)) if m else 0, visible_text(el).replace("\u00b6", "").strip(), in_tbl, el)
        para_of[id(el)] = p.i
        paras.append(p)
        if p.level:
            headings.append(p)
    first_app = next((h.i for h in headings if h.level == 7), -1)
    # chapter numbers, the way STYLEREF 1 \s and STYLEREF 7 \n \t read them (numbering starts at 1 / A)
    chap_at, h1, h7 = {}, 0, 0
    cur = ""
    for p in paras:
        if p.level == 1 and (first_app < 0 or p.i < first_app):
            h1 += 1; cur = str(h1)
        elif p.level == 7:
            h7 += 1; cur = to_alpha(h7)
        chap_at[p.i] = cur
    # table index and row of every paragraph in a table
    where_tbl = {}
    for ti, tbl in enumerate(tables, 1):
        trs = tbl.findall("w:tr", NS)
        for ri, tr in enumerate(trs):
            for pe in tr.iter(WP):
                where_tbl[id(pe)] = (ti, ri, len(trs))
    # captions
    labels = {c["label"] for c in std["captions"]}
    rx = re.compile(r"^(" + "|".join(sorted(labels)) + r")\s+(.*)$")
    seq_count = {}
    captions = []
    for p in paras:
        m = rx.match(p.text)
        if not m:
            continue
        fl = fields_in(p.el)
        has_seq = any(f.kind == "SEQ" for f in fl)
        if not has_seq and p.style.lower() not in ("caption",) and not p.style.lower().startswith(("pe table caption", "pe figure caption")):
            continue                                   # a sentence that starts with "Table" is not a caption
        label = m.group(1)
        part = "appendix" if first_app >= 0 and p.i > first_app else "body"
        rule = next((c for c in std["captions"] if c["label"] == label and c["part"] == part), None)
        if rule is None:
            continue
        key = (label, part, chap_at.get(p.i, ""))
        seq_count[key] = seq_count.get(key, 0) + 1
        chapter = chap_at.get(p.i, "") if rule["chapter_level"] else ""
        seqn = _seq_text(seq_count[key], rule.get("number_format"))          # 3.22.1: 1, I, i, A or a
        expected = (f"{chapter}{rule['separator']}{seqn}" if chapter else seqn)
        num_m = re.match(r"^([0-9A-Za-z]+(?:[\-.:\u2013][0-9A-Za-z]+)?)(.*)$", m.group(2), re.S)
        shown = num_m.group(1) if num_m else ""
        rest = num_m.group(2) if num_m else m.group(2)
        sep = next((c for c in "-.:\u2013" if c in shown), "")
        ti, ri, nrows = where_tbl.get(id(p.el), (0, -1, 0))
        if ti:
            position = "first_row" if ri == 0 else ("last_row" if ri == nrows - 1 else "other")
        else:
            position = "other"
        raw_after = "".join(t.text or "" for t in p.el.iter(q("t")))
        # after-number from the raw runs (a tab is a w:tab, not text)
        after = _after_number(p.el, shown)
        captions.append(Caption(p.i, label, part, chapter, expected, shown, [f.instr for f in fl], not has_seq, sep,
                                after, ri, ti, position, p.style))
    # bookmarks and what they wrap
    bms = {}
    starts = {}
    for el in body.iter(q("bookmarkStart"), q("bookmarkEnd"), WP):
        if el.tag == WP:
            cur_para = para_of.get(id(el), 0)
            continue
        if el.tag == q("bookmarkStart"):
            starts[el.get(q("id"))] = (el.get(q("name")), _para_index(el, para_of))
        else:
            sid = el.get(q("id"))
            if sid in starts:
                name, sp = starts.pop(sid)
                ep = _para_index(el, para_of)
                bms[name] = Bookmark(name, _bm_kind(name), sp, ep, "", "")
    for b in bms.values():
        span = [p for p in paras if b.start_para <= p.i <= b.end_para]
        cap = next((c for c in captions if c.para == b.start_para), None)
        if cap and b.start_para == b.end_para:
            b.wraps, b.target_text = "caption", f"{cap.label} {cap.shown}"
        elif span and span[0].level and b.start_para == b.end_para:
            b.wraps, b.target_text = "heading", span[0].text[:80]
        elif b.start_para != b.end_para:
            b.wraps, b.target_text = "range", f"{len(span)} paragraphs"
        else:
            b.wraps, b.target_text = "text", (span[0].text[:60] if span else "")
    # TOC fields and cross-references
    tocs, xrefs = [], []
    toc_entry_paras = sum(1 for p in paras if p.style.lower().startswith("toc ") and p.style.lower() != "toc heading"
                          or p.style.lower() == "table of figures")
    for f in doc_fields(body, para_of):
        parts = f.instr.split()
        if f.kind == "TOC":
            sw = _toc_switches(f.instr)
            kind = "list" if ("c" in sw or "f" in sw) and "t" not in sw and "o" not in sw else "main"
            t = Toc(f.para, f.instr, kind, sw, 0)
            inside = [p for p in paras if f.para <= p.i <= f.end_para]
            t.entries = sum(1 for p in inside if p.text)
            t.entry_styles = {p.style for p in inside}
            t.end_para = f.end_para
            tocs.append(t)
        elif f.kind in ("REF", "PAGEREF", "NOTEREF") and len(parts) > 1:
            xrefs.append(XRef(f.para, f.kind, parts[1], parts[2:], f.result.strip()))
        elif f.kind == "HYPERLINK" and "\\l" in parts:
            xrefs.append(XRef(f.para, "HYPERLINK", parts[parts.index("\\l") + 1].strip('"'), parts, f.result.strip()))
    for x in xrefs:
        b = bms.get(x.target)
        if b is None:
            x.status = "broken"
            continue
        b.used_by += 1
        x.target_kind, x.target_now = b.wraps, b.target_text
        cap = next((c for c in captions if c.para == b.start_para), None)
        if x.shown.startswith("Error!"):
            x.status = "error_shown"
        elif cap and x.kind == "REF" and x.shown and cap.expected not in x.shown and cap.shown not in x.shown:
            x.status = "stale"
        elif cap and x.kind == "REF" and x.shown and cap.shown != cap.expected and cap.expected not in x.shown:
            x.status = "stale"
        else:
            x.status = "ok"
    for t in tocs:
        if "b" in t.switches and t.switches["b"] in bms:
            bms[t.switches["b"]].used_by += 1
            bms[t.switches["b"]].kind = "scope"
    stats = {"paragraphs": len(paras), "headings": len(headings), "captions": len(captions), "tables": len(tables),
             "bookmarks": len(bms), "xrefs": len(xrefs), "tocs": len(tocs), "toc_entry_paragraphs": toc_entry_paras}
    return DocMap(paras, headings, captions, bms, xrefs, tocs, first_app, stats)


def _para_index(el, para_of):
    p = next(el.iterancestors(WP), None)
    if p is not None:
        return para_of.get(id(p), 0)
    nxt = el.getnext()
    while nxt is not None and nxt.tag != WP:
        nxt = nxt.getnext()
    if nxt is not None:
        return para_of.get(id(nxt), 0)
    prev = el.getprevious()
    while prev is not None and prev.tag != WP:
        prev = prev.getprevious()
    return para_of.get(id(prev), 0) if prev is not None else 0


def _bm_kind(name):
    if name.startswith("_Ref"):
        return "xref_target"
    if name.startswith("_Toc"):
        return "toc_target"
    if name.startswith("_PEPN"):
        return "section_mark"
    if name.startswith("_"):
        return "hidden_other"
    return "user"


def _toc_switches(instr):
    out = {}
    for m in re.finditer(r'\\([a-z])(?:\s+"([^"]*)"|\s+([^\s\\]+))?', instr):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else (m.group(3) or True)
    return out


def _after_number(p, shown):
    """What follows the caption number: period+tab, period+space, tab, colon+space. With fields, that is the
    text right after the end of the SEQ field; with a typed number, the text right after the number."""
    depth, instr, in_seq, seen_seq, buf = 0, "", False, False, ""
    for r in p.iter(WR):
        fc = r.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
                if depth == 1:
                    instr = ""
            elif t == "end":
                depth -= 1
                if depth == 0 and instr.strip().upper().startswith("SEQ"):
                    seen_seq, buf = True, ""
            continue
        it = r.find("w:instrText", NS)
        if it is not None:
            instr += it.text or ""
            continue
        if depth == 0 and seen_seq:
            for ch in r:
                if ch.tag == q("t"):
                    buf += ch.text or ""
                elif ch.tag == q("tab"):
                    buf += "\t"
    if not seen_seq:
        txt = "".join((t.text or "") if t.tag == q("t") else "\t" for t in p.iter(q("t"), q("tab")))
        k = txt.find(shown)
        buf = txt[k + len(shown):] if k >= 0 and shown else ""
    return classify_after(buf[:2])


# ---------------------------------------------------------------- audit
def audit(dm, std):
    out = []
    capr = {(c["label"], c["part"]): c for c in std["captions"]}
    toc = std["toc"]
    # captions
    seen_ident = set()
    for c in dm.captions:
        r = capr[(c.label, c.part)]
        seen_ident.add(r["identifier"])
        if c.typed:
            out.append(Finding("captions", "error", "C1", f"{c.label} {c.shown}: typed number, not a field", c.para,
                               "caption_fields", "typed"))
        else:
            seqs = [f for f in c.fields if f.upper().startswith("SEQ")]
            ident = seqs[0].split()[1] if seqs and len(seqs[0].split()) > 1 else ""
            if ident != r["identifier"]:
                out.append(Finding("captions", "error", "C2",
                                   f"{c.label} {c.shown}: numbered in the {ident or 'no'} list, the {c.part} rule uses {r['identifier']}",
                                   c.para, "caption_fields", "identifier"))
            want_sr = "STYLEREF 7" if r["chapter_level"] == 7 else f"STYLEREF {r['chapter_level']}"
            if r["chapter_level"] and not any(f.upper().startswith(want_sr) for f in c.fields):
                out.append(Finding("captions", "error", "C3", f"{c.label} {c.shown}: chapter part is not {want_sr}",
                                   c.para, "caption_fields", "chapter"))
        if c.shown != c.expected:
            out.append(Finding("captions", "warning", "C4",
                               f"{c.label} {c.shown or '(no number)'} reads as {c.expected} after an update", c.para,
                               "update_fields", "order"))
        if c.sep and c.sep != r["separator"]:
            out.append(Finding("captions", "error", "C5", f"{c.label} {c.shown}: separator {c.sep!r}, rule {r['separator']!r}",
                               c.para, "caption_fields", "separator"))
        if c.after != r["after_number"]:
            out.append(Finding("captions", "warning", "C6", f"{c.label} {c.shown}: after the number {c.after.replace('_', ' ')}, "
                               f"rule {r['after_number'].replace('_', ' ')}", c.para, "caption_after", "after"))
        if c.table:
            want = "last_row" if r["position"] == "below" else "first_row"
            if c.position != want:
                out.append(Finding("captions", "warning", "C7", f"{c.label} {c.shown}: caption in the {c.position.replace('_', ' ')}"
                                   f" of its table, rule {want.replace('_', ' ')}", c.para, "", "position"))
    # TOCs
    mains = [t for t in dm.tocs if t.kind == "main"]
    if not mains:
        out.append(Finding("toc", "warning", "T1", "No main table of contents field", 0, "toc_insert", "missing"))
    want_levels = ",".join(f"{s},{n}" for s, n in toc["levels"])
    for t in mains:
        if "o" in t.switches or "u" in t.switches:
            used_sw = " and ".join(x for x, k in (("outline levels (o)", "o"), ("paragraph outline levels (u)", "u"))
                                   if k in t.switches)
            out.append(Finding("toc", "error", "T2", "Main TOC uses " + used_sw + "; the rule pulls the heading styles by name",
                               t.para, "toc_field", "switches"))
        if t.switches.get("t") != want_levels:
            out.append(Finding("toc", "error", "T3", "Main TOC levels differ from the rule (Heading 7 and 8 as appendix levels)",
                               t.para, "toc_field", "levels"))
        for s in toc["switches"]:
            if s.strip("\\") not in t.switches:
                out.append(Finding("toc", "warning", "T4", f"Main TOC has no {s} switch", t.para, "toc_field", "switch"))
    lists = [t for t in dm.tocs if t.kind == "list"]
    for t in lists:
        if "b" in t.switches:
            out.append(Finding("toc", "info", "T5", f"List scoped by the bookmark {t.switches['b']}; caption identifiers can scope it with no bookmark",
                               t.para, "toc_list_identifiers", "scope"))
        ident = t.switches.get("c")
        if isinstance(ident, str) and ident not in seen_ident:
            out.append(Finding("toc", "error", "T6", f"List collects {ident!r} but no caption uses that list", t.para,
                               "toc_list_identifiers", "ident"))
    used = {s for t in dm.tocs for s in t.entry_styles}
    hand = [p for p in dm.paras if (p.style.lower().startswith("toc ") and p.style.lower() != "toc heading")
            and not any(t.para <= p.i <= getattr(t, "end_para", t.para) for t in dm.tocs)]
    if hand:
        out.append(Finding("toc", "error", "T7", f"{len(hand)} TOC-styled paragraphs are not inside a TOC field (typed by hand)",
                           hand[0].i, "", "hand"))
    # bookmarks
    for b in dm.bookmarks.values():
        if b.kind == "scope" or (b.kind == "user" and b.wraps == "range"):
            # a response scope should start at the first Heading 1 and stop before the first Heading 7
            h1 = next((h.i for h in dm.headings if h.level == 1), None)
            if b.name.lower().startswith(("response", "body", "volume")) and h1 is not None:
                end_ok = dm.first_appendix < 0 or b.end_para < dm.first_appendix
                if b.start_para > h1 or not end_ok:
                    out.append(Finding("bookmarks", "error", "B1", f"Scope bookmark {b.name} does not cover the response "
                                       "(first Heading 1 to before the first Heading 7)", b.start_para, "scope_reset", "scope"))
            if b.name.lower().startswith("append") and dm.first_appendix >= 0 and b.start_para != dm.first_appendix:
                out.append(Finding("bookmarks", "error", "B2", f"Scope bookmark {b.name} does not start at the first Heading 7",
                                   b.start_para, "scope_reset", "scope"))
        if b.kind == "xref_target" and b.used_by == 0:
            out.append(Finding("bookmarks", "info", "B3", f"Hidden cross-reference target {b.name} is not used", b.start_para,
                               "", "unused"))
    # cross-references
    for x in dm.xrefs:
        if x.status == "broken":
            out.append(Finding("xrefs", "error", "X1", f"{x.kind} to {x.target}: the target is gone", x.para, "xref_relink", "broken"))
        elif x.status == "error_shown":
            out.append(Finding("xrefs", "error", "X2", f"{x.kind} to {x.target} shows an error", x.para, "update_fields", "error"))
        elif x.status == "stale":
            out.append(Finding("xrefs", "warning", "X3", f"{x.kind} shows {x.shown!r}; the target now reads {x.target_now!r}",
                               x.para, "update_fields", "stale"))
        if x.kind in ("REF", "PAGEREF") and "\\*" in x.switches and "MERGEFORMAT" in " ".join(x.switches):
            out.append(Finding("xrefs", "warning", "X4", f"{x.kind} to {x.target} keeps MERGEFORMAT; the rule is CHARFORMAT",
                               x.para, "xref_switches", "merge"))
    # headings
    if dm.first_appendix >= 0:
        late = [h for h in dm.headings if h.i > dm.first_appendix and 1 <= h.level <= 6]
        if late:
            out.append(Finding("headings", "error", "H1", f"{len(late)} Heading 1 to 6 after the first Heading 7 (appendix)",
                               late[0].i, "", "after_appendix"))
    return out
