"""Format Check (3.5.0): a Word draft read against the production standards, without changing it. Opens the .docx
read-only as a zip (never through Word, never for writing) and reports: fonts and sizes as Word shows them, by scope
(body, tables, captions, headings, headers and footers, footnotes) and where each comes from (a style, or formatting
typed over it); margins, page size and orientation by section; captions (typed numbers instead of fields, numbering
scheme, the separator after the number, where a table's caption sits); the table of contents (forbidden switches,
hand-typed lines); typed bullets and numbers instead of Word lists; and page numbers in each section's footer. Rules
only; the file is only read."""
import os, re, zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
w = lambda tag: f"{{{W}}}{tag}"          # noqa: E731
_CAP = re.compile(r"^\s*(Figure|Table|Exhibit)\s+([A-Z]?\d+(?:[.\-‐-–]\d+)?)(.?)(\s?)", re.I)
_TYPED_LIST = re.compile(r"^\s*(?:[•·▪●–—◦➢*]\s|[o-]\t|"
                         r"(?:\d{1,2}|[a-z]|[ivx]{1,4})[.)]\s|\((?:\d{1,2}|[a-z]|[ivx]{1,4})\)\s)", re.I)


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


class Doc:
    """A .docx opened read-only: its parts, styles, theme fonts and relationships."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:                       # read once, then work from memory: the file is never held
            data = f.read()
        import io
        self.z = zipfile.ZipFile(io.BytesIO(data))
        names = set(self.z.namelist())
        if "word/document.xml" not in names:
            raise ValueError("not a Word document (no word/document.xml)")
        self.names = names
        self.doc = self.xml("word/document.xml")
        self.styles = self.xml("word/styles.xml") if "word/styles.xml" in names else None
        self.rels = self._rels("word/_rels/document.xml.rels")
        self.theme = {"major": "", "minor": ""}
        th = next((n for n in names if n.startswith("word/theme/") and n.endswith(".xml")), None)
        if th:
            t = self.xml(th)
            for kind in ("major", "minor"):
                el = t.find(f".//{{{A}}}{kind}Font/{{{A}}}latin")
                if el is not None:
                    self.theme[kind] = el.get("typeface", "")
        self.style = {}
        self.default_para = ""
        self.defaults = {"font": "", "size": 0.0}
        self._read_styles()

    def xml(self, name):
        return etree.fromstring(self.z.read(name), parser=_parser())

    def _rels(self, name):
        if name not in self.names:
            return {}
        x = self.xml(name)
        return {r.get("Id"): "word/" + r.get("Target").lstrip("/").replace("word/", "") for r in x.iter(f"{{{PR}}}Relationship")}

    # ------------------------------------------------------------ fonts as Word resolves them
    def _rfont(self, rpr):
        if rpr is None:
            return None
        rf = rpr.find(w("rFonts"))
        if rf is None:
            return None
        if rf.get(w("ascii")):
            return rf.get(w("ascii"))
        th = rf.get(w("asciiTheme")) or ""
        if th:
            return self.theme["major" if th.startswith("major") else "minor"] or None
        return rf.get(w("hAnsi")) or None

    def _rsize(self, rpr):
        if rpr is None:
            return None
        sz = rpr.find(w("sz"))
        return int(sz.get(w("val"))) / 2 if sz is not None and (sz.get(w("val")) or "").isdigit() else None

    def _read_styles(self):
        if self.styles is None:
            return
        dd = self.styles.find(f"{w('docDefaults')}/{w('rPrDefault')}/{w('rPr')}")
        self.defaults = {"font": self._rfont(dd) or self.theme["minor"] or "", "size": self._rsize(dd) or 10.0}
        for st in self.styles.iter(w("style")):
            sid = st.get(w("styleId"))
            if st.get(w("type")) == "paragraph" and st.get(w("default")) in ("1", "true", "on"):
                self.default_para = sid
            name = st.find(w("name"))
            based = st.find(w("basedOn"))
            rpr = st.find(w("rPr"))
            ppr = st.find(w("pPr"))
            ol = ppr.find(w("outlineLvl")) if ppr is not None else None
            num = ppr.find(w("numPr")) if ppr is not None else None
            tbl_rpr = st.find(w("rPr")) if st.get(w("type")) == "table" else None
            self.style[sid] = {"type": st.get(w("type")), "name": (name.get(w("val")) if name is not None else sid) or sid,
                               "based": based.get(w("val")) if based is not None else None,
                               "font": self._rfont(rpr), "size": self._rsize(rpr),
                               "outline": int(ol.get(w("val"))) if ol is not None and (ol.get(w("val")) or "").isdigit() else None,
                               "numbered": num is not None, "tbl_font": self._rfont(tbl_rpr), "tbl_size": self._rsize(tbl_rpr)}

    def chain(self, sid):
        seen, out = set(), []
        while sid and sid in self.style and sid not in seen:
            seen.add(sid); out.append(sid); sid = self.style[sid]["based"]
        return out

    def style_value(self, sid, key):
        """(value, style it comes from) along the basedOn chain."""
        for s in self.chain(sid):
            v = self.style[s].get(key)
            if v not in (None, ""):
                return v, s
        return None, None

    def style_name(self, sid):
        return self.style.get(sid, {}).get("name", sid or "Normal")

    def is_heading(self, sid):
        if not sid:
            return False
        nm = self.style_name(sid).lower()
        return nm.startswith("heading") or nm == "title" or self.style_value(sid, "outline")[0] is not None

    def numbered(self, sid):
        return bool(sid) and any(self.style[s]["numbered"] for s in self.chain(sid))


def _text(p):
    out = []
    for el in p.iter():
        if el.tag == w("t"):
            out.append(el.text or "")
        elif el.tag == w("tab"):
            out.append("\t")
    return "".join(out)


def _pstyle(p):
    ps = p.find(f"{w('pPr')}/{w('pStyle')}")
    return ps.get(w("val")) if ps is not None else ""


def _in_table(el):
    return any(a.tag == w("tc") for a in el.iterancestors())


def _skip_run(r):
    rpr = r.find(w("rPr"))
    if rpr is not None and (rpr.find(w("vanish")) is not None):
        return True
    if any(a.tag in (w("del"), w("moveFrom")) for a in r.iterancestors()):
        return True
    t = "".join(x.text or "" for x in r.iter(w("t")))
    return not t.strip()


def _table_style(el):
    for a in el.iterancestors(w("tbl")):
        ts = a.find(f"{w('tblPr')}/{w('tblStyle')}")
        return ts.get(w("val")) if ts is not None else ""
    return ""


def _scope(doc, p, part):
    if part == "header":
        return "header"
    if part == "footnote":
        return "footnote"
    sid = _pstyle(p)
    nm = doc.style_name(sid).lower() if sid else ""
    if nm.startswith("caption") or _CAP.match(_text(p) or ""):
        return "caption"
    if doc.is_heading(sid):
        return "heading"
    if _in_table(p):
        return "table"
    return "body"


def run_font(doc, p, r):
    """(font, size, source) for one run as Word shows it: defaults, table style, paragraph style chain, character
    style, then formatting typed on the run. source: 'typed' or the style name or 'defaults'."""
    font, size, fsrc, ssrc = doc.defaults["font"], doc.defaults["size"], "defaults", "defaults"
    ts = _table_style(p) if _in_table(p) else ""
    if ts:
        f, s_ = doc.style_value(ts, "tbl_font")
        z, s2 = doc.style_value(ts, "tbl_size")
        if f:
            font, fsrc = f, doc.style_name(s_)
        if z:
            size, ssrc = z, doc.style_name(s2)
    sid = _pstyle(p) or doc.default_para
    f, s_ = doc.style_value(sid, "font")
    z, s2 = doc.style_value(sid, "size")
    # Word: in a table, a paragraph left in the default style (Normal) takes the table style's formatting; any other
    # paragraph style wins over the table style
    normal_only = ts and sid == doc.default_para
    if f and not (normal_only and fsrc != "defaults"):
        font, fsrc = f, doc.style_name(s_)
    if z and not (normal_only and ssrc != "defaults"):
        size, ssrc = z, doc.style_name(s2)
    rpr = r.find(w("rPr"))
    if rpr is not None:
        rs = rpr.find(w("rStyle"))
        if rs is not None:
            f, s_ = doc.style_value(rs.get(w("val")), "font")
            z, s2 = doc.style_value(rs.get(w("val")), "size")
            if f:
                font, fsrc = f, doc.style_name(s_)
            if z:
                size, ssrc = z, doc.style_name(s2)
        f, z = doc._rfont(rpr), doc._rsize(rpr)
        if f:
            font, fsrc = f, "typed"
        if z:
            size, ssrc = z, "typed"
    return font or "", float(size or 0), fsrc, ssrc


def _parts(doc):
    """[(part kind, xml, name)]: the body, then headers and footers, then footnotes."""
    out = [("body", doc.doc, "word/document.xml")]
    for n in sorted(doc.names):
        if re.match(r"word/(header|footer)\d*\.xml$", n):
            out.append(("header", doc.xml(n), n))
    if "word/footnotes.xml" in doc.names:
        out.append(("footnote", doc.xml("word/footnotes.xml"), "word/footnotes.xml"))
    return out


def _where(doc, p):
    """The nearest heading above the paragraph (or the table it sits in), for 'where' in a finding."""
    head = ""
    top = p
    for a in p.iterancestors():
        if a.tag == w("body"):
            break
        top = a
    for prev in top.itersiblings(preceding=True):
        if prev.tag == w("p") and doc.is_heading(_pstyle(prev)):
            head = _text(prev).strip()
            break
    return head[:80]


# ------------------------------------------------------------------ the checks
def check_fonts(doc, std):
    """Grouped findings: one per (scope, font, size, source) that breaks the scope's rule, with how many runs and an
    example."""
    rules = std.get("fonts", {})
    groups = {}
    for part, x, _n in _parts(doc):
        for p in x.iter(w("p")):
            scope = _scope(doc, p, part)
            rule = rules.get(scope) or {}
            want_font = (rule.get("font") or "").strip()
            lo, hi = float(rule.get("min") or 0), float(rule.get("max") or 0)
            if not (want_font or lo or hi):
                continue
            for r in p.iter(w("r")):
                if _skip_run(r) or r.find(w("instrText")) is not None or r.find(w("sym")) is not None:
                    continue
                font, size, fsrc, ssrc = run_font(doc, p, r)
                bad = []
                if want_font and font and font.lower() != want_font.lower():
                    bad.append(("font", f"font {font} (should be {want_font})", fsrc))
                if lo and size and size < lo:
                    bad.append(("size", f"{size:g} pt (smallest allowed {lo:g})", ssrc))
                if hi and size and size > hi:
                    bad.append(("size", f"{size:g} pt (largest allowed {hi:g})", ssrc))
                for kind, text, src in bad:
                    key = (scope, kind, text, src)
                    g = groups.setdefault(key, {"scope": scope, "problem": text, "source": src, "count": 0,
                                                "where": _where(doc, p) if part == "body" else part.capitalize(),
                                                "example": _text(p).replace("\t", " ")[:90]})
                    g["count"] += 1
    out = []
    for g in sorted(groups.values(), key=lambda g: -g["count"]):
        how = ("typed over the style" if g["source"] == "typed" else f"from the style {g['source']}")
        out.append({"area": "Fonts", "where": g["where"], "problem": f"{g['scope'].capitalize()}: {g['problem']}",
                    "detail": f"{g['count']} run(s), {how}. Example: “{g['example']}”", "count": g["count"]})
    return out


def check_pages(doc, std):
    out = []
    want = std.get("page", "Letter")
    mw, mh = __import__("prodstd").PAGES.get(want, (12240, 15840))
    min_m = float(std.get("margins_in") or 0)
    sects = list(doc.doc.iter(w("sectPr")))
    for k, s in enumerate(sects, 1):
        sz, mar = s.find(w("pgSz")), s.find(w("pgMar"))
        if sz is not None:
            wd, ht = int(sz.get(w("w"), "0") or 0), int(sz.get(w("h"), "0") or 0)
            land = wd > ht
            a, b = sorted((wd, ht))
            if abs(a - mw) > 40 or abs(b - mh) > 40:
                out.append({"area": "Pages", "where": f"Section {k}", "problem": f"page size {a / 1440:.2f} x {b / 1440:.2f} in (should be {want})", "detail": "", "count": 1})
            if land and not std.get("landscape_ok", True):
                out.append({"area": "Pages", "where": f"Section {k}", "problem": "landscape section", "detail": "", "count": 1})
        if mar is not None and min_m:
            small = []
            for side in ("top", "bottom", "left", "right"):
                v = mar.get(w(side))
                if v and v.lstrip("-").isdigit() and abs(int(v)) / 1440 < min_m - 0.005:
                    small.append(f"{side} {abs(int(v)) / 1440:.2f} in")
            if small:
                out.append({"area": "Pages", "where": f"Section {k}", "problem": f"margins under {min_m:g} in: " + ", ".join(small), "detail": "", "count": 1})
    return out


def _fields_in(p):
    """Field instructions in a paragraph (simple fields and complex ones)."""
    out = [fs.get(w("instr"), "") for fs in p.iter(w("fldSimple"))]
    out += ["".join(x.text or "" for x in p.iter(w("instrText")))] if p.find(f".//{w('instrText')}") is not None else []
    return out


def check_captions(doc, std):
    out = []
    want_fields = std.get("caption_fields", True)
    scheme = std.get("caption_numbers", "chapter")
    sep = std.get("caption_sep", "tab")
    for p in doc.doc.iter(w("p")):
        sid = _pstyle(p)
        nm = doc.style_name(sid).lower() if sid else ""
        text = _text(p)
        m = _CAP.match(text or "")
        if not m or not (nm.startswith("caption") or m.group(3) in (".", ":", "–", "-")):
            continue
        label = f"{m.group(1).capitalize()} {m.group(2)}"
        where = _where(doc, p)
        instr = " ".join(_fields_in(p)).upper()
        if want_fields and "SEQ" not in instr:
            out.append({"area": "Captions", "where": where, "problem": f"{label}: number typed, not a caption field",
                        "detail": "Word will not renumber it or list it in the list of tables or figures.", "count": 1})
        num = m.group(2)
        if scheme == "chapter" and not re.search(r"[.\-‐-–]", num):
            out.append({"area": "Captions", "where": where, "problem": f"{label}: plain number; the standard numbers by section (2-1, A-1)", "detail": "", "count": 1})
        elif scheme == "plain" and re.search(r"[.\-‐-–]", num):
            out.append({"area": "Captions", "where": where, "problem": f"{label}: section number; the standard numbers 1, 2, 3", "detail": "", "count": 1})
        after = text[m.end(2):m.end(2) + 2]
        if sep == "tab" and "\t" not in after:
            out.append({"area": "Captions", "where": where, "problem": f"{label}: a space after the number; the standard uses a tab", "detail": "", "count": 1})
        elif sep == "space" and "\t" in after:
            out.append({"area": "Captions", "where": where, "problem": f"{label}: a tab after the number; the standard uses a space", "detail": "", "count": 1})
    # tables: where the caption sits
    pos = std.get("caption_position", "either")
    for k, t in enumerate(doc.doc.iter(w("tbl")), 1):
        if any(a.tag == w("tbl") for a in t.iterancestors()):
            continue
        rows = t.findall(w("tr"))
        first = _text(rows[0]) if rows else ""
        in_row = bool(_CAP.match(first))
        prev = t.getprevious()
        nxt = t.getnext()
        above = prev is not None and prev.tag == w("p") and bool(_CAP.match(_text(prev)))
        below = nxt is not None and nxt.tag == w("p") and bool(_CAP.match(_text(nxt)))
        ok = {"first row": in_row, "above": above, "below": below, "either": in_row or above or below}.get(pos, True)
        if not ok:
            got = "first row" if in_row else "above it" if above else "below it" if below else "nowhere"
            nth = {1: "1st", 2: "2nd", 3: "3rd"}.get(k, f"{k}th")
            out.append({"area": "Captions", "where": _where(doc, t), "problem": f"The {nth} table: caption {got}; the standard puts it {pos if pos != 'either' else 'next to it'}",
                        "detail": f"“{first[:70]}”", "count": 1})
    return out


def check_toc(doc, std):
    out = []
    forbid = [x.lower() for x in std.get("toc_forbid", [])]
    tocs = []
    for p in doc.doc.iter(w("p")):
        for ins in _fields_in(p):
            if ins.strip().upper().startswith("TOC"):
                tocs.append(ins.strip())
    for ins in tocs:
        bad = [s for s in forbid if re.search(re.escape(s) + r"(\s|$)", ins.lower())]
        if bad:
            out.append({"area": "Table of contents", "where": "", "problem": f"TOC field uses {', '.join(bad)}", "detail": ins[:120], "count": 1})
    in_field = False
    typed = 0
    depth = 0
    for p in doc.doc.iter(w("p")):
        for fc in p.iter(w("fldChar")):
            t = fc.get(w("fldCharType"))
            depth += 1 if t == "begin" else -1 if t == "end" else 0
        sid = _pstyle(p)
        nm = doc.style_name(sid).lower() if sid else ""
        in_field = depth > 0 or p.find(f".//{w('instrText')}") is not None or p.find(f".//{w('fldSimple')}") is not None
        if re.match(r"toc ?\d", nm) and not in_field and _text(p).strip():
            typed += 1
    if typed:
        out.append({"area": "Table of contents", "where": "", "problem": f"{typed} table-of-contents line(s) typed by hand, outside a TOC field",
                    "detail": "They will not update when pages move.", "count": typed})
    return out


def check_lists(doc, std):
    groups = {}
    for p in doc.doc.iter(w("p")):
        if p.find(f"{w('pPr')}/{w('numPr')}") is not None or doc.numbered(_pstyle(p)):
            continue
        text = _text(p)
        if not text or not _TYPED_LIST.match(text) or _CAP.match(text) or doc.is_heading(_pstyle(p)):
            continue
        where = _where(doc, p)
        key = (where, _in_table(p))
        g = groups.setdefault(key, {"count": 0, "example": text.strip()[:70]})
        g["count"] += 1
    return [{"area": "Lists", "where": wh, "problem": f"{g['count']} typed bullet(s) or number(s){' in a table' if tb else ''}",
             "detail": f"Typed, not a Word list. Example: “{g['example']}”", "count": g["count"]} for (wh, tb), g in groups.items()]


def check_page_numbers(doc, std):
    if not std.get("page_numbers", True):
        return []
    out = []
    sects = list(doc.doc.iter(w("sectPr")))
    last_footer = None
    for k, s in enumerate(sects, 1):
        ref = next((f for f in s.findall(w("footerReference")) if f.get(w("type"), "default") == "default"), None)
        part = doc.rels.get(ref.get(f"{{{R}}}id")) if ref is not None else last_footer
        if ref is not None:
            last_footer = part
        if not part or part not in doc.names:
            out.append({"area": "Page numbers", "where": f"Section {k}", "problem": "no footer, so no page number", "detail": "", "count": 1})
            continue
        x = doc.xml(part)
        instr = " ".join(fs.get(w("instr"), "") for fs in x.iter(w("fldSimple"))) + " " + " ".join(t.text or "" for t in x.iter(w("instrText")))
        if not re.search(r"\bPAGE\b", instr.upper()):
            txt = "".join(t.text or "" for t in x.iter(w("t")))
            typed = re.search(r"\b\d+\b", txt)
            out.append({"area": "Page numbers", "where": f"Section {k}",
                        "problem": "page number typed, not a PAGE field" if typed else "footer has no page number",
                        "detail": f"“{txt.strip()[:60]}”" if txt.strip() else "", "count": 1})
    return out


AREAS = (("Fonts", check_fonts), ("Pages", check_pages), ("Captions", check_captions), ("Table of contents", check_toc),
         ("Lists", check_lists), ("Page numbers", check_page_numbers))


def check(path, std, areas=None):
    """{"file", "findings": [{area, where, problem, detail, count}], "counts": {area: n}, "error"} for one draft."""
    out = {"file": os.path.basename(path), "path": path, "findings": [], "counts": {}, "error": ""}
    try:
        doc = Doc(path)
    except (zipfile.BadZipFile, etree.XMLSyntaxError, KeyError, ValueError, OSError) as e:
        out["error"] = "does not open as a Word document" if not isinstance(e, OSError) else "could not be read"
        return out
    for name, fn in AREAS:
        if areas and name not in areas:
            continue
        try:
            got = fn(doc, std)
        except Exception:
            got = [{"area": name, "where": "", "problem": "this check could not read part of the file", "detail": "", "count": 1}]
        out["findings"] += got
        out["counts"][name] = sum(1 for _ in got)
    return out


def export(path, results, effort=""):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Format Check"
    ws.append(["Draft", "Area", "Where", "Finding", "Detail"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for r in results:
        if r["error"]:
            ws.append([r["file"], "File", "", r["error"], ""])
        for f in r["findings"]:
            ws.append([r["file"], f["area"], f["where"], f["problem"], f["detail"]])
    for i, wd in enumerate([30, 18, 30, 50, 80], 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = wd
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    if effort:
        wb.properties.title = f"{effort} format check"
    wb.save(path)
    return path
