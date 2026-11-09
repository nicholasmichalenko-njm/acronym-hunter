"""Setup from a workbook, on the page (3.91.0; claude/stationkeeper-setup-from-workbook-3.91.md). The team's filled
outline workbook goes straight into a Word setup with its styles: each column says what it is (its tag) and where it
goes; any text says which character style it takes (a character style never moves text); the rows keep the workbook's
order, and inside a row the tags go in their numbered order (one section can have its own). The page Word gets is
previewed before anything is written.

page(book, profile, saved) -> the settings for this workbook ("page" in its outline layout):
  {"tags": {heading: tag}, "order": [tag], "styles": {tag: paragraph style}, "chars": {"heading|look": character style,
   "" for none, "-" to leave the text out}, "own": {"heading|look": tag it follows}, "sections": {number: [tag]},
   "source": {"place": "inline" | "line", "limit": 40, "char": character style}, "looks": {style: look}, "template": path}
paragraphs(book, profile, page) -> [{"tag", "style", "runs": [(text, character style)], "row", "col", "section", "level"}]
write(paras, page, out_path, template=None) -> out_path       the setup on the template (or a plain document)

Guidance right after the heading (decision, 12:50) is the order's second place: "heading", "guidance", ...; anywhere else
it goes with its row. The source is written exactly as typed (12:50). Styles the template has are used as they are; a
missing one is made from its look. The workbook is only read. Rules only; nothing leaves the PC."""
import copy, io, os, re, tempfile, zipfile
from xml.sax.saxutils import escape

from lxml import etree

import outlinexl as OX

TAGS = (("heading", "Heading"), ("guidance", "Guidance"), ("source", "Source"), ("rfp", "RFP text"),
        ("support", "Supporting text"), ("authors", "Authors"), ("skip", "Leave out"))
TAG = dict(TAGS)
ROLE_TAG = {"section_number": "heading", "section_name": "heading", "reference": "source", "reference_l": "source",
            "reference_m": "source", "requirement": "rfp", "requirement_l": "rfp", "requirement_m": "rfp", "support": "support",
            "guidance": "guidance", "authors": "skip", "lm": "skip", "ignore": "skip"}
ORDER = ("heading", "guidance", "source", "rfp", "support", "authors")
STYLES = {"guidance": "SK PM Direction", "source": "SK Source", "rfp": "SK RFP Requirement", "support": "SK RFP Support",
          "authors": "SK Setup Note"}
SOURCE_CHAR = "SK Source Char"
# the character style a kind of text takes inside its cell when the layout's rules name the kind
KIND_CHAR = {"rfp": "SK Compliance Char", "rfp_l": "SK Compliance Char", "rfp_m": "SK Compliance Char",
             "support": "SK RFP Support Char", "customer": "SK Customer Char", "pm": "SK PM Direction Char", "skip": "-"}
# a style's look when the template does not have it and nobody set one (hex colors; size in points)
LOOKS = {"SK PM Direction": {"color": "00B050", "hidden": True}, "SK Source": {"color": "B45309", "bold": True, "size": 9, "hidden": True},
         "SK RFP Requirement": {"color": "7030A0", "hidden": True}, "SK RFP Support": {"color": "2E74B5", "italic": True, "hidden": True},
         "SK Setup Note": {"color": "1E3A8A", "hidden": True}, SOURCE_CHAR: {"color": "B45309", "bold": True, "size": 9, "hidden": True},
         "SK Compliance Char": {"color": "C00000", "bold": True, "hidden": True}, "SK RFP Support Char": {"color": "2E74B5", "italic": True, "hidden": True},
         "SK Customer Char": {"color": "6B21A8", "hidden": True}, "SK PM Direction Char": {"color": "00B050", "hidden": True}}
LOOK_KEYS = ("font", "size", "color", "bold", "italic", "underline", "hidden")
_NUM = re.compile(r"^\s*((?:\d+|[A-Z])(?:\.\d+)*)\.?\s+(.+)$")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def _w(t):
    return f"{{{W}}}{t}"


def key(header, look):
    return f"{header}|{look}"


# ---------------------------------------------------------------- the settings
def page(book, profile, saved=None):
    """This workbook's settings: what was saved with its layout, with every column and look it has filled in."""
    saved = copy.deepcopy(saved or {})
    cols = profile.get("columns") or {}
    rules = profile.get("rules") or {}
    out = {"tags": {}, "order": list(saved.get("order") or ORDER), "styles": dict(STYLES, **(saved.get("styles") or {})),
           "chars": dict(saved.get("chars") or {}), "own": dict(saved.get("own") or {}),
           "sections": {k: list(v) for k, v in (saved.get("sections") or {}).items()},
           "source": dict({"place": "inline", "limit": 40, "char": SOURCE_CHAR}, **(saved.get("source") or {})),
           "looks": {k: dict(v) for k, v in (saved.get("looks") or {}).items()}, "template": saved.get("template") or ""}
    for t in ORDER:                                         # a tag new since the order was saved goes at its usual place
        if t not in out["order"]:
            out["order"].append(t)
    for h in [h for h in book["headers"] if h]:
        out["tags"][h] = (saved.get("tags") or {}).get(h) or ROLE_TAG.get(cols.get(h) or "ignore", "skip")
        if out["tags"][h] not in ("rfp", "support", "guidance"):
            continue
        lks = OX.looks(book, h)
        free = [x["look"] for x in lks if not (rules.get(h) or {}).get(x["look"])]
        main = (free or [x["look"] for x in lks] or [None])[0]   # the column's own text (most used, no rule): no character style
        for x in lks:
            k = key(h, x["look"])
            if k in out["chars"] or k in out["own"]:
                continue
            kind = (rules.get(h) or {}).get(x["look"])
            if not kind and x["look"][1:2] == "I" and out["tags"][h] == "rfp":
                kind = "support"                            # italic inside RFP text reads as supporting text until said otherwise
            out["chars"][k] = "" if x["look"] == main or not kind else KIND_CHAR.get(kind, "")
    return out


def tag_order(pg, section=""):
    """The order inside a row for a section: its own when it has one, else every section's."""
    return list((pg.get("sections") or {}).get(section) or pg["order"])


def move(pg, tag, to, section=None):
    """A tag moved to place `to` (0 is first) in the order of every section, or of one section (12:32)."""
    order = tag_order(pg, section or "") if section else list(pg["order"])
    if tag in order:
        order.remove(tag)
    order.insert(max(0, min(int(to), len(order))), tag)
    if section:
        pg.setdefault("sections", {})[section] = order
    else:
        pg["order"] = order
    return order


def back_to_every(pg, section):
    return (pg.get("sections") or {}).pop(section, None) is not None


def look_of(pg, style, template_looks=None):
    """A style's look: what was set on this page, else the template's, else the default."""
    lk = dict((template_looks or {}).get(style) or LOOKS.get(style) or {"hidden": True})
    lk.update((pg.get("looks") or {}).get(style) or {})
    return lk


def styles_in_use(pg, paras):
    """[(style, "paragraph" | "character")] in the order they first appear on the page."""
    out, seen = [], set()
    for p in paras:
        if p["style"] not in seen:
            seen.add(p["style"]); out.append((p["style"], "paragraph"))
        for _t, ch in p["runs"]:
            if ch and ch not in seen:
                seen.add(ch); out.append((ch, "character"))
    return out


# ---------------------------------------------------------------- the page
def _text(runs):
    return " ".join("".join(t for t, _lk in runs).split())


def _sections(book, profile, pg):
    """The workbook's rows under their sections, in the workbook's order."""
    cols = profile.get("columns") or {}
    heads = [(i, h) for i, h in enumerate(book["headers"]) if h and pg["tags"].get(h) == "heading"]
    num_i = [i for i, h in heads if cols.get(h) == "section_number"]
    name_i = [i for i, h in heads if cols.get(h) != "section_number"]
    out, cur = [], None
    for r in book["rows"]:
        cells = r["cells"]
        num = " ".join(_text(cells[i]) for i in num_i if i < len(cells)).strip()
        name = " ".join(_text(cells[i]) for i in name_i if i < len(cells)).strip()
        if name and not num:
            m = _NUM.match(name)
            if m:
                num, name = m.group(1), m.group(2)
        if (num or name) and (cur is None or num != cur["num"] or (name and name != cur["title"])):
            again = next((s for s in out if s["num"] == num and s["title"] == (name or num)), None)
            cur = again or {"num": num, "title": name or num, "level": OX._level(num) if num else 1, "rows": [], "row": r["row"]}
            if again is None:
                out.append(cur)
        if cur is None:
            cur = {"num": "", "title": "", "level": 1, "rows": [], "row": r["row"]}
            out.append(cur)
        cur["rows"].append(r)
    return out


def _cell_paras(pg, header, col, runs):
    """A cell as paragraphs [(runs, own tag or None)]: a new line starts a paragraph; text of a look made its own
    paragraph comes out on its own; text left out goes."""
    out, cur = [], []
    for t, lk in runs:
        k = key(header, lk)
        ch = (pg.get("chars") or {}).get(k, "")
        if ch == "-":
            continue
        own = (pg.get("own") or {}).get(k)
        for n, part in enumerate(t.split("\n")):
            if n and cur:
                out.append((cur, None)); cur = []
            if not part:
                continue
            if own:
                if cur:
                    out.append((cur, None)); cur = []
                out.append(([(part, "")], own))
                continue
            if cur and cur[-1][1] == ch:
                cur[-1] = (cur[-1][0] + part, ch)
            else:
                cur.append((part, ch))
    if cur:
        out.append((cur, None))
    tidy = []
    for rs, own in out:                                     # spaces as Word shows them: one between words, none at the ends
        rs = [(re.sub(r"[ \t]+", " ", t), c) for t, c in rs]
        rs[0] = (rs[0][0].lstrip(), rs[0][1]); rs[-1] = (rs[-1][0].rstrip(), rs[-1][1])
        rs = [(t, c) for t, c in rs if t]
        if rs:
            tidy.append((rs, own))
    return tidy


def paragraphs(book, profile, pg):
    hdr = book["headers"]
    out = []

    def add(tag, style, runs, row, col, sec, own=False):
        out.append({"tag": tag, "style": style, "runs": runs, "row": row, "col": col, "section": sec["num"],
                    "level": sec["level"], "own": own})
    for sec in _sections(book, profile, pg):
        order = tag_order(pg, sec["num"])
        if sec["title"] or sec["num"]:
            lvl = max(1, min(sec["level"], 9))
            add("heading", f"Heading {lvl}", [((sec["num"] + " " if sec["num"] else "") + sec["title"], "")], sec["row"], -1, sec)
        early = len(order) > 1 and order[0] == "heading" and order[1] == "guidance"
        body = [t for t in order if t != "heading" and not (early and t == "guidance")]
        if early:                                            # 12:50: once, right after the section's heading
            for r in sec["rows"]:
                for i, h in enumerate(hdr):
                    if pg["tags"].get(h) == "guidance" and i < len(r["cells"]):
                        for rs, _own in _cell_paras(pg, h, i, r["cells"][i]):
                            add("guidance", pg["styles"]["guidance"], rs, r["row"], i, sec)
        for r in sec["rows"]:
            cells, waiting, after = r["cells"], None, {}
            for tag in body:
                for i, h in enumerate(hdr):
                    if pg["tags"].get(h) != tag or i >= len(cells) or not cells[i]:
                        continue
                    if tag == "source":                      # exactly as typed (12:50)
                        src = "".join(t for t, _lk in cells[i]).strip()
                        if not src:
                            continue
                        if pg["source"].get("place") == "inline" and len(src) < int(pg["source"].get("limit") or 40):
                            waiting = (src, i)
                        else:
                            add("source", pg["styles"]["source"], [(src, "")], r["row"], i, sec)
                        continue
                    for rs, own in _cell_paras(pg, h, i, cells[i]):
                        if own:
                            after.setdefault(own, []).append((rs, i))
                            continue
                        if waiting:                          # a short source starts the next text, in its own character style
                            rs = [(waiting[0] + " ", pg["source"].get("char") or SOURCE_CHAR)] + rs
                            waiting = None
                        add(tag, pg["styles"].get(tag) or STYLES.get(tag, "Normal"), rs, r["row"], i, sec)
                for rs, i in after.pop(tag, []):              # text made its own paragraph follows the tag it was put after
                    add(tag, pg["styles"].get(tag) or STYLES.get(tag, "Normal"), rs, r["row"], i, sec, own=True)
            if waiting:                                      # nothing after it in the row: its own line
                add("source", pg["styles"]["source"], [(waiting[0], "")], r["row"], waiting[1], sec)
            for tag, lst in after.items():
                for rs, i in lst:
                    add(tag, pg["styles"].get(tag) or STYLES.get(tag, "Normal"), rs, r["row"], i, sec, own=True)
    return out


# ---------------------------------------------------------------- the template's styles
def template_looks(path):
    """{style name: look} for the template's paragraph and character styles (what the preview draws them with)."""
    out = {}
    try:
        with zipfile.ZipFile(path) as z:
            sroot = etree.fromstring(z.read("word/styles.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
        return out
    for s in sroot.findall("w:style", NS):
        nm = s.find("w:name", NS)
        if nm is None or s.get(_w("type")) not in ("paragraph", "character"):
            continue
        rpr = s.find("w:rPr", NS)
        lk = {"type": s.get(_w("type"))}
        if rpr is not None:
            c = rpr.find("w:color", NS)
            if c is not None and c.get(_w("val")) not in (None, "auto"):
                lk["color"] = c.get(_w("val")).upper()
            for tagn, k in (("b", "bold"), ("i", "italic"), ("vanish", "hidden")):
                el = rpr.find(f"w:{tagn}", NS)
                if el is not None:
                    lk[k] = el.get(_w("val")) not in ("0", "false")
            u = rpr.find("w:u", NS)
            if u is not None and u.get(_w("val")) not in ("none", None):
                lk["underline"] = True
            sz = rpr.find("w:sz", NS)
            if sz is not None and (sz.get(_w("val")) or "").isdigit():
                lk["size"] = int(sz.get(_w("val"))) / 2
            f = rpr.find("w:rFonts", NS)
            if f is not None and f.get(_w("ascii")):
                lk["font"] = f.get(_w("ascii"))
        out[nm.get(_w("val"))] = lk
    return out


def _rpr_xml(lk):
    font = escape(lk["font"]) if lk.get("font") else ""
    return ((f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>' if font else "") + ("<w:b/>" if lk.get("bold") else "")
            + ("<w:i/>" if lk.get("italic") else "") + ("<w:vanish/>" if lk.get("hidden") else "")
            + (f'<w:color w:val="{escape(str(lk["color"]).lstrip("#"))}"/>' if lk.get("color") else "")
            + (f'<w:sz w:val="{int(round(float(lk["size"]) * 2))}"/>' if lk.get("size") else "")
            + ('<w:u w:val="single"/>' if lk.get("underline") else ""))


def _set_look(s, lk):
    """A style the template has, with the look set on this page put over its own."""
    rpr = s.find("w:rPr", NS)
    if rpr is None:
        rpr = etree.SubElement(s, _w("rPr"))
    for k, tagn in (("bold", "b"), ("italic", "i"), ("hidden", "vanish"), ("underline", "u"), ("color", "color"), ("size", "sz"), ("font", "rFonts")):
        if k not in lk:
            continue
        old = rpr.find(f"w:{tagn}", NS)
        if old is not None:
            rpr.remove(old)
        if lk[k] in (None, False, "", 0):
            continue
        el = etree.SubElement(rpr, _w(tagn))
        if k == "underline":
            el.set(_w("val"), "single")
        elif k == "color":
            el.set(_w("val"), str(lk[k]).lstrip("#").upper())
        elif k == "size":
            el.set(_w("val"), str(int(round(float(lk[k]) * 2))))
        elif k == "font":
            for a in ("ascii", "hAnsi", "cs"):
                el.set(_w(a), str(lk[k]))


def ensure_styles(sroot, pg, wanted):
    """{style name: style id} for every style the page uses: the template's own by name (with any look set on this page
    put over it), a missing one made from its look. Headings are the template's Heading 1 to 9."""
    by_name = {}
    for s in sroot.findall("w:style", NS):
        nm = s.find("w:name", NS)
        if nm is not None:
            by_name[(nm.get(_w("val")) or "").casefold()] = s
    ids = {s.get(_w("styleId")) for s in sroot.findall("w:style", NS)}
    out = {}
    for name, kind in wanted:
        s = by_name.get(name.casefold())
        if s is not None:
            if name in (pg.get("looks") or {}):
                _set_look(s, pg["looks"][name])
            out[name] = s.get(_w("styleId"))
            continue
        base = re.sub(r"[^A-Za-z0-9]", "", name) or "SKStyle"
        sid, n = base, 2
        while sid in ids:
            sid = f"{base}{n}"; n += 1
        lk = look_of(pg, name)
        typ = "character" if kind == "character" else "paragraph"
        based = "" if typ == "character" else '<w:basedOn w:val="Normal"/>'
        el = etree.fromstring(f'<w:style xmlns:w="{W}" w:type="{typ}" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{escape(name)}"/>'
                              f'{based}<w:qFormat/><w:rPr>{_rpr_xml(lk)}</w:rPr></w:style>')
        sroot.append(el); ids.add(sid); by_name[name.casefold()] = el
        out[name] = sid
    return out


def _run(text, rid=None):
    r = f'<w:rPr><w:rStyle w:val="{escape(rid)}"/></w:rPr>' if rid else ""
    return f'<w:r>{r}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def body_xml(paras, ids, heading_ids):
    out = []
    for p in paras:
        sid = heading_ids.get(p["level"]) if p["tag"] == "heading" else ids.get(p["style"])
        ppr = f'<w:pPr><w:pStyle w:val="{escape(sid)}"/></w:pPr>' if sid else ""
        out.append("<w:p>" + ppr + "".join(_run(t, ids.get(ch) if ch else None) for t, ch in p["runs"]) + "</w:p>")
    return "".join(out)


def _blank_template():
    import docxw
    d = docxw.Doc()
    fd, path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    d.save(path)
    return path


def write(paras, pg, out_path, template=None):
    """The setup: a new document made from the template (or a plain one) with the page in it. Returns out_path."""
    import setuptemplate as ST
    import templatefile as TF
    tmp = None
    if not template or not os.path.isfile(template):
        template = tmp = _blank_template()
    try:
        zin = zipfile.ZipFile(template)
        droot = etree.fromstring(zin.read("word/document.xml"))
        sroot = etree.fromstring(zin.read("word/styles.xml"))
        ids = ensure_styles(sroot, pg, [w for w in styles_in_use(pg, paras) if not w[0].startswith("Heading ")])
        hids = TF.heading_ids(sroot)
        names = ST._style_names(sroot)
        before = set(droot.iter(_w("p")))
        ST.place_body(droot, names, body_xml(paras, ids, hids), "")
        ours = [p for p in droot.iter(_w("p")) if p not in before]
        nroot = TF.xml_of(zin, "word/numbering.xml")
        TF.number_headings(droot.find("w:body", NS), sroot, nroot, only=set(ours))
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for i in zin.infolist():
                b = zin.read(i.filename)
                if i.filename == "word/document.xml":
                    b = etree.tostring(droot, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif i.filename == "word/styles.xml":
                    b = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif i.filename == "word/numbering.xml" and nroot is not None:
                    b = etree.tostring(nroot, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif i.filename == "[Content_Types].xml":
                    b = b.replace(ST.TEMPLATE_CT.encode(), ST.DOCUMENT_CT.encode())
                z.writestr(i, b)
        zin.close()
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    part = out_path + ".part"
    with open(part, "wb") as f:
        f.write(out.getvalue())
    os.replace(part, out_path)
    return out_path


# ---------------------------------------------------------------- kept with the outline layout
def saved(config_dir, layout_name):
    import outlinelayouts as OL
    return copy.deepcopy((OL.load(config_dir).get(layout_name) or {}).get("page") or {})


def save(config_dir, layout_name, pg):
    """The page's settings kept with the outline layout (its "page"); the next workbook with these columns opens as
    this one was left."""
    import outlinelayouts as OL
    lays = OL.load(config_dir)
    lay = lays.get(layout_name) or OL.new_layout()
    lay["page"] = {k: copy.deepcopy(pg[k]) for k in ("tags", "order", "styles", "chars", "own", "sections", "source", "looks", "template") if k in pg}
    OL.put(config_dir, layout_name, lay)
    return lay["page"]
