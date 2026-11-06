"""A Word template the team brings (3.72.0, claude/stationkeeper-template-setup-decisions-2026-11-06.md): read, never
written. read(path) says what it holds: its sections in order (cover, title page, front matter, body, appendix, back
matter) with each one's page numbering and whether it has a header and footer, the heading styles and the numbering
each one uses, its Quick Parts by gallery, its theme fonts, and its paragraph style names. A .dotx, .dotm or .docx is
read as XML only; macros never run.

number_headings(body, sroot, nroot) settles each heading's number (also for the setup on the app's own templates): when
Word's own heading numbering would print the number typed at the start of the heading, the typed one goes; when the
first heading starts the list at another number, the list starts there; when Word would print another number, the typed
one stays and Word's is turned off for that heading, so the response's numbering always matches the outline. Returns
one note per heading whose typed number stayed. Rules only; nothing leaves the PC."""
import copy, os, re, zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"w": W, "r": R, "a": A}
KIND_NAMES = {"cover": "Cover page", "title": "Title page", "front": "Front matter", "body": "Body", "appendix": "Appendix",
              "back": "Back matter"}
EXTS = (".dotx", ".dotm", ".docx")
TYPED = re.compile(r"^\s*((?:[A-Z]\.)?\d+(?:\.\d+)*)\.?(?:\s+|$)")


def _w(t):
    return f"{{{W}}}{t}"


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def xml_of(z, name):
    try:
        return etree.fromstring(z.read(name), _parser())
    except KeyError:
        return None


def text_of(el):
    return "".join(t.text or "" for t in el.iter(_w("t")))


# ------------------------------------------------------------------ styles and heading numbering
def style_names(sroot):
    """{style id: lower-case name}."""
    out = {}
    for s in sroot.findall("w:style", NS) if sroot is not None else []:
        nm = s.find("w:name", NS)
        out[s.get(_w("styleId"))] = (nm.get(_w("val")) if nm is not None else "").casefold()
    return out


def heading_ids(sroot):
    """{level: style id} for the built-in Heading 1 to 9 the file defines (found by name, whatever its id)."""
    out = {}
    for sid, nm in style_names(sroot).items():
        m = re.fullmatch(r"heading ([1-9])", nm)
        if m:
            out[int(m.group(1))] = sid
    return out


def _style_num(sroot, sid, seen=None):
    """(numId, ilvl) a paragraph style numbers with, following basedOn; None when it does not."""
    seen = seen or set()
    if sid in seen or sroot is None:
        return None
    seen.add(sid)
    s = next((x for x in sroot.findall("w:style", NS) if x.get(_w("styleId")) == sid), None)
    if s is None:
        return None
    np_ = s.find("w:pPr/w:numPr", NS)
    if np_ is not None:
        ni, il = np_.find("w:numId", NS), np_.find("w:ilvl", NS)
        if ni is not None:
            return (ni.get(_w("val")), int(il.get(_w("val"))) if il is not None else 0)
    b = s.find("w:basedOn", NS)
    return _style_num(sroot, b.get(_w("val")), seen) if b is not None else None


def _levels(nroot, num_id):
    """{ilvl: {"start", "fmt", "text"}} for a numbering instance, its overrides applied; {} when unknown."""
    if nroot is None or num_id in (None, "0"):
        return {}
    num = next((n for n in nroot.findall("w:num", NS) if n.get(_w("numId")) == str(num_id)), None)
    if num is None:
        return {}
    an = num.find("w:abstractNumId", NS)
    absn = next((a for a in nroot.findall("w:abstractNum", NS) if an is not None and a.get(_w("abstractNumId")) == an.get(_w("val"))), None)
    out = {}
    for lvl in absn.findall("w:lvl", NS) if absn is not None else []:
        g = lambda tag: (lvl.find(tag, NS).get(_w("val")) if lvl.find(tag, NS) is not None else None)
        out[int(lvl.get(_w("ilvl")))] = {"start": int(g("w:start") or 1), "fmt": g("w:numFmt") or "decimal", "text": g("w:lvlText") or ""}
    for ov in num.findall("w:lvlOverride", NS):
        so = ov.find("w:startOverride", NS)
        k = int(ov.get(_w("ilvl")))
        if so is not None and k in out:
            out[k]["start"] = int(so.get(_w("val")))
    return out


def _roman(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
                 (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s; n -= v
    return out


def fmt_num(n, fmt):
    """A counter as Word prints it in that number format; None for bullets and none."""
    if fmt in ("decimal", "decimalZero"):
        return f"{n:02d}" if fmt == "decimalZero" and n < 10 else str(n)
    if fmt in ("upperRoman", "lowerRoman"):
        r = _roman(max(1, n))
        return r if fmt == "upperRoman" else r.lower()
    if fmt in ("upperLetter", "lowerLetter"):
        s = chr(ord("A") + (max(1, n) - 1) % 26) * (1 + (max(1, n) - 1) // 26)
        return s if fmt == "upperLetter" else s.lower()
    return None


def label(levels, counters, ilvl):
    """What Word prints for a paragraph at ilvl with these counters; None when that level prints no number."""
    lv = levels.get(ilvl)
    if not lv or fmt_num(1, lv["fmt"]) is None:
        return None
    out = lv["text"]
    for k in range(ilvl + 1):
        lk = levels.get(k) or {"fmt": "decimal", "start": 1}
        out = out.replace(f"%{k + 1}", fmt_num(counters.get(k, lk["start"]), lk["fmt"]) or "")
    return out.strip()


def heading_numbering(sroot, nroot):
    """[{"level", "style", "numbered", "sample"}] for Heading 1 to 9 as the file defines them."""
    out = []
    hid = heading_ids(sroot)
    counters = {}
    for lev in range(1, 10):
        sid = hid.get(lev)
        if not sid:
            continue
        num = _style_num(sroot, sid)
        levels = _levels(nroot, num[0]) if num else {}
        sample = None
        if num:
            counters = {k: (levels.get(k) or {"start": 1})["start"] for k in range(num[1] + 1)}
            sample = label(levels, counters, num[1])
        out.append({"level": lev, "style": sid, "numbered": bool(sample), "sample": sample or ""})
    return out


def _norm(s):
    return (s or "").strip().rstrip(".").strip()


def _strip_prefix(p, n):
    """The first n characters of a paragraph's text taken off (and the spaces after them), runs kept."""
    left = n
    for t in p.iter(_w("t")):
        if left <= 0:
            if t.text and t.text != t.text.lstrip():
                t.text = t.text.lstrip()
            if t.text:
                return
            continue
        s = t.text or ""
        cut = min(len(s), left)
        left -= cut
        t.text = s[cut:].lstrip() if left <= 0 else ""
        if t.text:
            return


def _set_num(p, num_id, ilvl):
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(_w("pPr")); p.insert(0, ppr)
    old = ppr.find("w:numPr", NS)
    if old is not None:
        ppr.remove(old)
    np_ = etree.Element(_w("numPr"))
    etree.SubElement(np_, _w("ilvl")).set(_w("val"), str(ilvl))
    etree.SubElement(np_, _w("numId")).set(_w("val"), str(num_id))
    ps = ppr.find("w:pStyle", NS)
    (ps.addnext(np_) if ps is not None else ppr.insert(0, np_))


def _new_num(nroot, num_id, starts):
    """A new numbering instance on the same list as num_id, with these start values; returns its id."""
    old = next(n for n in nroot.findall("w:num", NS) if n.get(_w("numId")) == str(num_id))
    nid = str(max(int(n.get(_w("numId"))) for n in nroot.findall("w:num", NS)) + 1)
    new = etree.SubElement(nroot, _w("num")); new.set(_w("numId"), nid)
    new.append(copy.deepcopy(old.find("w:abstractNumId", NS)))
    for k, v in starts.items():
        ov = etree.SubElement(new, _w("lvlOverride")); ov.set(_w("ilvl"), str(k))
        etree.SubElement(ov, _w("startOverride")).set(_w("val"), str(v))
    return nid


def number_headings(body, sroot, nroot, only=None):
    """See the module text. only: the paragraphs to settle (the setup's own); others are counted but left as they are."""
    if nroot is None:
        return []
    hid = {sid: lev for lev, sid in heading_ids(sroot).items()}
    paras = []
    for p in body.iter(_w("p")):
        ps = p.find("w:pPr/w:pStyle", NS)
        sid = ps.get(_w("val")) if ps is not None else None
        direct = p.find("w:pPr/w:numPr", NS)
        if direct is not None:
            ni = direct.find("w:numId", NS); il = direct.find("w:ilvl", NS)
            num = (ni.get(_w("val")) if ni is not None else None, int(il.get(_w("val"))) if il is not None else 0)
        else:
            num = _style_num(sroot, sid) if sid else None
        if num and num[0] not in (None, "0"):
            paras.append((p, num, sid in hid and (only is None or p in only)))
    fi = next((i for i, (_p, _n, ours) in enumerate(paras) if ours), None)
    if fi is not None:                                      # the list starts where the outline starts
        p, (nid, il), _o = paras[fi]
        levels = _levels(nroot, nid)
        m = TYPED.match(text_of(p))
        earlier = any(n2[0] == nid for _q, n2, _x in paras[:fi])      # the template's own paragraphs on the list come first
        if m and il == 0 and m.group(1).isdigit() and levels.get(0) and levels[0]["fmt"] == "decimal" \
                and int(m.group(1)) != levels[0]["start"] and not earlier:
            new = _new_num(nroot, nid, {0: int(m.group(1))})
            for i, (q, (n2, l2), ours) in enumerate(paras):
                if n2 == nid:
                    _set_num(q, new, l2)
                    paras[i] = (q, (new, l2), ours)
    counters, started, notes = {}, {}, []
    for p, (nid, il), ours in paras:
        levels = _levels(nroot, nid)
        c = counters.setdefault(nid, {})
        st = started.setdefault(nid, set())
        before = (dict(c), set(st))
        c[il] = c[il] + 1 if il in st else (levels.get(il) or {"start": 1})["start"]
        st.add(il)
        for k in [k for k in st if k > il]:
            st.discard(k); c.pop(k, None)
        for k in range(il):
            c.setdefault(k, (levels.get(k) or {"start": 1})["start"])
        if not ours:
            continue
        txt = text_of(p)
        m = TYPED.match(txt)
        if not m:
            continue
        shown = label(levels, c, il)
        if shown is not None and _norm(shown) == _norm(m.group(1)):
            _strip_prefix(p, len(m.group(0).rstrip()))
        else:
            c.clear(); c.update(before[0]); st.clear(); st.update(before[1])
            _set_num(p, "0", 0)
            notes.append(f"{txt.strip()[:60]}: its typed number stays (Word's numbering would print {shown or 'no number'})")
    return notes


# ------------------------------------------------------------------ sections
def split_sections(body):
    """[[elements of section 1], ...]: each section ends with the paragraph holding its section break, the last with the
    body's own section properties."""
    out, cur = [], []
    for el in body:
        cur.append(el)
        if (el.tag == _w("p") and el.find("w:pPr/w:sectPr", NS) is not None) or el.tag == _w("sectPr"):
            out.append(cur); cur = []
    if cur:
        if out:
            out[-1].extend(cur)
        else:
            out.append(cur)
    return out


def sect_of(els):
    last = els[-1]
    return last if last.tag == _w("sectPr") else last.find("w:pPr/w:sectPr", NS)


def _has_toc(els):
    for el in els:
        for it in el.iter(_w("instrText")):
            if re.match(r"\s*TOC\b", it.text or ""):
                return True
        for fs in el.iter(_w("fldSimple")):
            if re.match(r"\s*TOC\b", fs.get(_w("instr")) or ""):
                return True
        for g in el.iter(_w("docPartGallery")):
            if "Table of Contents" in (g.get(_w("val")) or ""):
                return True
    return False


def kinds(secs, names):
    """Each section's kind: the first with a Heading 1 is the body; after it, one headed as an appendix (an Appendix style,
    Heading 7 or deeper, or a heading that starts with Appendix) is the appendix, one with a Heading 1 more body, the rest
    back matter; before it, a table of contents makes front matter, the first is the cover, the next the title page."""
    def heads(els):
        out = []
        for el in els:
            if el.tag != _w("p"):
                continue
            ps = el.find("w:pPr/w:pStyle", NS)
            nm = names.get(ps.get(_w("val")), "") if ps is not None else ""
            if nm.startswith("heading") or nm.startswith("appendix"):
                out.append((nm, text_of(el).strip()))
        return out
    hs = [heads(s) for s in secs]
    body = next((i for i, h in enumerate(hs) if any(nm == "heading 1" for nm, _t in h)), None)
    out = []
    for i, s in enumerate(secs):
        if body is None:
            out.append("front" if _has_toc(s) else ("cover" if i == 0 and len(secs) > 1 else "body"))
        elif i < body:
            out.append("front" if _has_toc(s) else ("cover" if i == 0 else ("title" if "title" not in out else "front")))
        elif i == body:
            out.append("body")
        elif any(nm.startswith("appendix") or re.match(r"heading [7-9]", nm) or t.lower().startswith("appendix") for nm, t in hs[i]):
            out.append("appendix")
        elif any(nm == "heading 1" for nm, _t in hs[i]):
            out.append("body")
        else:
            out.append("back")
    if out and "body" not in out:                           # no headings anywhere: the last section takes the setup
        out[-1] = "body"
    return out


def _story_refs(sp):
    return {f"{etree.QName(r).localname[:6]}:{r.get(_w('type')) or 'default'}": r.get(f"{{{R}}}id")
            for r in sp if etree.QName(r).localname in ("headerReference", "footerReference")} if sp is not None else {}


# ------------------------------------------------------------------ reading a file
def read(path):
    """What the template holds (see the module text). Raises ValueError for a file that is not a Word file it can read."""
    if os.path.splitext(path)[1].lower() not in EXTS:
        raise ValueError("Pick a Word template or document (.dotx, .dotm or .docx).")
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        raise ValueError("That file does not open as a Word file.") from e
    with z:
        doc, sroot, nroot = xml_of(z, "word/document.xml"), xml_of(z, "word/styles.xml"), xml_of(z, "word/numbering.xml")
        if doc is None or sroot is None:
            raise ValueError("That file has no Word document inside.")
        import readback as RB
        rb = RB.sections(path)
        names = style_names(sroot)
        secs = split_sections(doc.find("w:body", NS))
        ks = kinds(secs, names)
        out_secs, refs = [], {}
        for i, (els, k) in enumerate(zip(secs, ks)):
            refs.update(_story_refs(sect_of(els)))
            first = next((t for t in (text_of(e).strip() for e in els) if t), "")
            r = rb[i] if i < len(rb) else {}
            out_secs.append({"index": i, "kind": k, "name": KIND_NAMES[k], "first_text": first[:80], "format": r.get("format", ""),
                             "restart": bool(r.get("restart")), "page_number": bool(r.get("page_number")),
                             "header": any(x.startswith("header") for x in refs), "footer": any(x.startswith("footer") for x in refs),
                             "paragraphs": sum(1 for e in els if e.tag == _w("p"))})
        theme = {"name": "", "major": "", "minor": ""}
        th = xml_of(z, "word/theme/theme1.xml")
        if th is not None:
            theme["name"] = th.get("name") or ""
            for k, tag in (("major", "majorFont"), ("minor", "minorFont")):
                lat = th.find(f".//a:{tag}/a:latin", NS)
                theme[k] = lat.get("typeface") if lat is not None else ""
        has_vba = any(n.lower().endswith("vbaproject.bin") for n in z.namelist())
    qps = []
    try:
        import prodquickparts as PQ
        qps = [dict(q, gallery_name=PQ.gallery_name(q.get("gallery"))) for q in PQ.read(path)]
    except Exception:  # noqa: BLE001  a file whose glossary the engine refuses still reads; its Quick Parts are left out
        import diag
        diag.swallowed()
    paras = sorted({nm for s, nm in names.items() if nm and s} - {""})
    return {"file": os.path.basename(path), "sections": out_secs, "headings": heading_numbering(sroot, nroot), "quick_parts": qps,
            "theme": theme, "styles": paras, "macros": has_vba}


def default_picks(info):
    """Blank in the template's look: no cover, title or front matter pages, no Quick Parts, the body's header and footer on."""
    return {"keep": [], "quick_parts": [], "no_hf": []}


def setup_styles_status(info, opts):
    """[(kind, style name, "in the template" | "added")] for the setup styles the effort uses."""
    have = set(info.get("styles") or [])
    return [(k, (o or {}).get("style", ""), "in the template" if (o or {}).get("style", "").casefold() in have else "added")
            for k, o in (opts or {}).items() if (o or {}).get("include", True) and not str(k).startswith("cap:")]
