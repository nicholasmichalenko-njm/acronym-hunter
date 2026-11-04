"""Checks for the team's production rules (3.38.0), read straight from a Word file (never written). Each returns
findings as (code, what) for Audit and Fix a Copy, which report them under their rule (rulebook.py):

RU1 a style a header or footer reads (STYLEREF) used inside a text box (Rule 1)
RU2 the A number on the cover or title page not right-justified, or not right under the restriction and Warning block (Rule 2)
RU3 the page marking missing from the top center or bottom center of a page part (Rule 3)
RU4 a style named with another response type (Rule 4)
RU5 a title page style in a response with no title page (Rule 5)
RU6 heading levels indented differently, or a heading number not at 0 inches (Rule 6)
RU7 a footer that is not a one-row, three-column table with the A number on the left and the page number on the right (Rule 7)
RU8 a caption or notes row indented from the left or right (Rule 8)

The A number's style and the restriction block's style come from Production Standards (std["style_roles"]); where a
style is used (std["style_defs"][name]["used_on"]) is set there too: a style's name decides nothing. Rules only."""
import re

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
TOKENS = ("RFP", "RFI", "BAA", "RFQ", "CSO")
TW = 1440.0


def q(t):
    return f"{{{W}}}{t}"


def _text(el):
    return "".join(t.text or "" for t in el.iter(q("t")))


def _styles(pkg):
    """({styleId: name}, {name: styleId}, styles root)."""
    try:
        sp = pkg.word_part("/styles")
        root = pkg.tree(sp) if sp else None
    except Exception:  # noqa: BLE001
        root = None
    ids = {}
    if root is not None:
        for s in root.findall("w:style", NS):
            n = s.find("w:name", NS)
            if n is not None:
                ids[s.get(q("styleId"))] = n.get(q("val"))
    return ids, {v: k for k, v in ids.items()}, root


def _pstyle(p, ids):
    ps = p.find("w:pPr/w:pStyle", NS)
    return ids.get(ps.get(q("val")), ps.get(q("val"))) if ps is not None else ""


def _in_textbox(p):
    return any(a.tag == q("txbxContent") for a in p.iterancestors())


def _jc(p, sroot, style_id):
    jc = p.find("w:pPr/w:jc", NS)
    if jc is not None:
        return jc.get(q("val"))
    seen = set()
    while sroot is not None and style_id and style_id not in seen:
        seen.add(style_id)
        s = next((x for x in sroot.findall("w:style", NS) if x.get(q("styleId")) == style_id), None)
        if s is None:
            break
        j = s.find("w:pPr/w:jc", NS)
        if j is not None:
            return j.get(q("val"))
        b = s.find("w:basedOn", NS)
        style_id = b.get(q("val")) if b is not None else None
    return "left"


def _instr(part_root):
    """Every field instruction in a part (complex and simple fields)."""
    out = [(t.text or "") for t in part_root.iter(q("instrText"))]
    out += [f.get(q("instr")) or "" for f in part_root.iter(q("fldSimple"))]
    joined = " ".join(out)
    return [x.strip() for x in re.split(r"(?=\b(?:STYLEREF|PAGE|NUMPAGES|SECTIONPAGES|DOCPROPERTY|REF)\b)", joined) if x.strip()]


def styleref_names(instrs):
    out = []
    for s in instrs:
        m = re.match(r'STYLEREF\s+"?([^"\\]+?)"?\s*(\\|$)', s.strip(), re.I)
        if m:
            out.append(m.group(1).strip())
    return out


def _sections(pkg):
    """[(sectPr, [body paragraphs and tables before it])] in document order."""
    root = pkg.tree(pkg.main)
    body = root.find("w:body", NS)
    out, cur = [], []
    for el in body:
        if el.tag == q("sectPr"):
            out.append((el, cur)); cur = []
            continue
        cur.append(el)
        sp = el.find("w:pPr/w:sectPr", NS) if el.tag == q("p") else None
        if sp is not None:
            out.append((sp, cur)); cur = []
    if cur:
        out.append((None, cur))
    return out


def _hf_parts(pkg, sect, kind="header", which="default"):
    """The part names a section's header (or footer) references, of one type (default, first, even)."""
    out = []
    if sect is None:
        return out
    rels = pkg.rels_of(pkg.main)
    for ref in sect.findall(f"w:{kind}Reference", NS):
        if which and ref.get(q("type")) != which:
            continue
        rid = ref.get(f"{{{R_NS}}}id")
        r = rels.get(rid)
        if r:
            out.append(r[1])                                    # resolved by the package (word/header1.xml)
    return out


def _part(pkg, name):
    try:
        return pkg.tree(name) if pkg.has(name) else None
    except Exception:  # noqa: BLE001
        return None


def check(pkg, std, marking="", response_type=""):
    """[(code, what)] for the rules this file breaks."""
    out = []
    ids, by_name, sroot = _styles(pkg)
    roles = (std or {}).get("style_roles") or {}
    a_style, r_style = roles.get("a_number") or "", roles.get("restriction") or ""
    root = pkg.tree(pkg.main)
    sections = _sections(pkg)
    hf_names = sorted({n for s, _els in sections for k in ("header", "footer") for n in _hf_parts(pkg, s, k, None)})
    hf_roots = {n: _part(pkg, n) for n in hf_names}
    # RU1: styles a header or footer reads, used in a text box
    read = set()
    for r_ in hf_roots.values():
        if r_ is not None:
            read.update(styleref_names(_instr(r_)))
    seen = set()
    for p in root.iter(q("p")):
        if _in_textbox(p):
            nm = _pstyle(p, ids)
            if nm and nm in read and nm not in seen:
                seen.add(nm)
                out.append(("RU1", f"{nm} is read by a header or footer (STYLEREF) but sits in a text box, where Word never "
                                   f"finds it: move it into the page or a table cell"))
    # RU2: the A number on the cover or title page
    if a_style:
        first = [el for _s, els in sections[:2] for el in els]
        paras = [p for el in first for p in (el.iter(q("p")) if el.tag != q("p") else [el])]
        hits = [i for i, p in enumerate(paras) if _pstyle(p, ids) == a_style]
        if not hits:
            out.append(("RU2", f"No paragraph in the A number's style ({a_style}) on the cover or title page"))
        for i in hits[:1]:
            p = paras[i]
            if _jc(p, sroot, by_name.get(a_style)) not in ("right", "end"):
                out.append(("RU2", f"The A number ({a_style}) is not right-justified"))
            prev = next((paras[j] for j in range(i - 1, -1, -1) if _text(paras[j]).strip()), None)
            ok = False
            if prev is not None:
                ptxt = _text(prev).strip()
                if r_style:
                    ok = _pstyle(prev, ids) == r_style
                if not ok and not r_style:
                    mk = " ".join(((std or {}).get("variables") or {}).get("marking", "").split())[:40].casefold()
                    low = ptxt.casefold()
                    ok = low.startswith("warning") or (mk and mk in low) or "data rights" in low or "proprietary" in low
            if not ok:
                out.append(("RU2", "The A number is not right under the proprietary statement, data rights and Warning block"))
    # RU3: the marking at the top and bottom center of every page part
    mk = " ".join((marking or "").split())
    if mk:
        for k, (sect, _els) in enumerate(sections):
            for kind, where in (("header", "top"), ("footer", "bottom")):
                parts = _hf_parts(pkg, sect, kind, "default")
                found = False
                for n in parts:
                    r_ = hf_roots.get(n)
                    if r_ is None:
                        r_ = _part(pkg, n)
                    if r_ is None:
                        continue
                    for p in r_.iter(q("p")):
                        if mk.casefold() in _text(p).casefold():
                            in_mid = _middle_cell(p)
                            if in_mid or _jc(p, sroot, (p.find("w:pPr/w:pStyle", NS).get(q("val")) if p.find("w:pPr/w:pStyle", NS) is not None else None)) == "center":
                                found = True
                if not found:
                    out.append(("RU3", f"Section {k + 1}: the marking ({mk}) is not at the {where} center"))
    # RU4: styles named with another response type
    rt = (response_type or "").upper()
    if rt in TOKENS:
        for name in sorted(set(ids.values())):
            other = [t for t in TOKENS if t != rt and re.search(rf"\b{t}\b", name)]
            if other:
                out.append(("RU4", f"{name} is named with {other[0]}; in an {rt} response it is named with {rt}"))
    # RU5: title page styles in a response with no title page
    sd = (std or {}).get("style_defs") or {}
    if not ((std or {}).get("page_parts") or {}).get("title"):
        fam = [n for n, d in sd.items() if (d or {}).get("used_on") == "Title page"]
        for n in fam:
            if n in by_name:
                out.append(("RU5", f"{n} is a title page style; this response has no title page"))
    # RU6: heading levels indented differently
    out += [("RU6", w) for w in _heading_indents(pkg, ids, sroot)]
    # RU7: the footer table
    for k, (sect, _els) in enumerate(sections):
        for n in _hf_parts(pkg, sect, "footer", "default"):
            r_ = hf_roots.get(n)
            if r_ is None:
                r_ = _part(pkg, n)
            if r_ is None:
                continue
            if not _text(r_).strip() and not _instr(r_):      # 3.42.0: an empty footer (a cover's) has nothing to check
                continue
            tbl = next(iter(r_.findall("w:tbl", NS)), None)
            if tbl is None:
                out.append(("RU7", f"Section {k + 1}: the footer is not a one-row, three-column table"))
                continue
            rows = tbl.findall("w:tr", NS)
            cells = rows[0].findall("w:tc", NS) if rows else []
            if len(rows) != 1 or len(cells) != 3:
                out.append(("RU7", f"Section {k + 1}: the footer table has {len(rows)} row(s) and {len(cells)} column(s), not 1 and 3"))
                continue
            left = " ".join(_instr(cells[0])); right = " ".join(_instr(cells[2]))
            if a_style and a_style not in styleref_names(_instr(cells[0])):
                out.append(("RU7", f"Section {k + 1}: the footer's left cell does not read the A number (STYLEREF {a_style})"))
            if not re.search(r"\bPAGE\b", right.upper()):
                out.append(("RU7", f"Section {k + 1}: the footer's right cell has no page number"))
    # RU8: caption and notes rows indented
    out += [("RU8", w) for w in _row_indents(root, ids, sroot, std)]
    return out


def _middle_cell(p):
    tc = next((a for a in p.iterancestors() if a.tag == q("tc")), None)
    if tc is None:
        return False
    tr = tc.getparent()
    cells = tr.findall("w:tc", NS)
    return len(cells) == 3 and cells.index(tc) == 1


def _ind(el):
    ind = el.find("w:pPr/w:ind", NS) if el.tag != q("pPr") else el.find("w:ind", NS)
    if ind is None:
        return None
    def v(*names):
        for n in names:
            x = ind.get(q(n))
            if x is not None:
                try:
                    return int(x)
                except ValueError:
                    return 0
        return 0
    return v("left", "start"), v("right", "end"), v("hanging"), v("firstLine")


def _heading_indents(pkg, ids, sroot):
    """Heading 1's multilevel list: every level's number at 0 inches and the same text position."""
    if sroot is None:
        return []
    h1 = next((s for s in sroot.findall("w:style", NS) if (s.find("w:name", NS) is not None
                                                            and s.find("w:name", NS).get(q("val")).lower() == "heading 1")), None)
    num = h1.find("w:pPr/w:numPr/w:numId", NS) if h1 is not None else None
    if num is None:
        return []
    try:
        np_ = pkg.word_part("/numbering")
        nroot = pkg.tree(np_) if np_ else None
    except Exception:  # noqa: BLE001
        nroot = None
    if nroot is None:
        return []
    nid = num.get(q("val"))
    n_el = next((n for n in nroot.findall("w:num", NS) if n.get(q("numId")) == nid), None)
    if n_el is None:
        return []
    aid = n_el.find("w:abstractNumId", NS).get(q("val"))
    ab = next((a for a in nroot.findall("w:abstractNum", NS) if a.get(q("abstractNumId")) == aid), None)
    if ab is None:
        return []
    out, base = [], None
    for lvl in ab.findall("w:lvl", NS)[:9]:
        il = int(lvl.get(q("ilvl")) or 0)
        ind = lvl.find("w:pPr/w:ind", NS)
        left = int(ind.get(q("left")) or ind.get(q("start")) or 0) if ind is not None else 0
        hang = int(ind.get(q("hanging")) or 0) if ind is not None else 0
        first = int(ind.get(q("firstLine")) or 0) if ind is not None else 0
        number_at = left - hang + first
        if abs(number_at) > 10:
            out.append(f"Heading level {il + 1}: its number sits at {number_at / TW:.2g} inch, not 0")
        if base is None:
            base = (left, hang)
        elif (left, hang) != base:
            out.append(f"Heading level {il + 1} is indented differently from level 1 (text at {left / TW:.2g} inch, "
                       f"level 1 at {base[0] / TW:.2g})")
    return out


def _row_indents(root, ids, sroot, std):
    import prodrules as PRL
    try:
        from prodengine.pe import rules as R
        names = {R.row_look(std, role, "std")["tag_style"] for role in ("caption", "note") if role in (std.get("row_types") or {})}
    except Exception:  # noqa: BLE001
        names = set()
    if not names:
        return []
    out, flagged = [], set()
    for t_i, tbl in enumerate(root.iter(q("tbl")), 1):
        for p in tbl.iter(q("p")):
            nm = _pstyle(p, ids)
            if nm in names:
                ind = _ind(p)
                if ind and (ind[0] or ind[1]) and (t_i, nm) not in flagged:
                    flagged.add((t_i, nm))
                    out.append(f"Table {t_i}: a {nm} row is indented ({ind[0] / TW:.2g} inch left, {ind[1] / TW:.2g} right), not 0.0")
    if sroot is not None:
        for nm in names:
            s = next((x for x in sroot.findall("w:style", NS) if x.find("w:name", NS) is not None
                      and x.find("w:name", NS).get(q("val")) == nm), None)
            ind = s.find("w:pPr/w:ind", NS) if s is not None else None
            if ind is not None:
                left = int(ind.get(q("left")) or ind.get(q("start")) or 0); right = int(ind.get(q("right")) or ind.get(q("end")) or 0)
                if left or right:
                    out.append(f"The {nm} style is indented ({left / TW:.2g} inch left, {right / TW:.2g} right), not 0.0")
    return out
