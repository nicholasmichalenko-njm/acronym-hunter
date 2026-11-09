"""Section designs (3.87.0, claude/stationkeeper-section-designs-2026-11-08.md): a library of sections built in Word and
kept whole: the CUI cover, the cover, the title page, the Table of Contents, Acronyms and Abbreviations, Units and Symbols,
and the back cover. Word is the authoring tool; the app keeps each design's file, reads it, fills it and places it.

    A design is one Word file. Each piece of text that changes per effort sits in its own paragraph, in its own style
    (a fill-in style); each STYLEREF source has its own style. What fills it is set once per design: one row per
    styled paragraph (a fill-in key, or "as written").
    A table keeps its header row; its sample row repeats once per entry (an Acronyms table: term, meaning).
    Fields are kept exactly as written; the filled file asks Word to update its fields when it opens.

shelves: SHELVES, SHELF_NAME. Library (in the config folder, section_designs/index.json, format 1):
    designs(config_dir, shelf=None) / add(config_dir, shelf, path, name="") / replace(config_dir, did, path) /
    remove(config_dir, did) / get(config_dir, did) / set_map(config_dir, did, mapping)
read(path) -> {"paragraphs", "tables", "fields", "sources", "sections"}   (the file is only read)
other_pages(path) -> [{"style", "where", "in_textbox"}]: text other pages read (STYLEREF sources) and where
check(path) -> [problem]: only a STYLEREF source missing or sitting in a text box
split(path, out_dir) -> [file per Word section]
adopt(config_dir, lib) -> n: 3.90.0 (decision 13): covers, title pages and back covers live here. Each one the template
    library kept (Layout's old shelves) is brought onto its shelf once, the newest version of each family, marked with
    the library item it came from; Effort Profiles pick from these shelves too (templateprofile.pick_design)
fill(path, mapping, values, out, rows=None) -> out: mapped paragraphs take their values, the sample row repeats
Libraries stand apart from Setup; Setup only picks a design per section. Rules only; nothing leaves the PC."""
import copy, datetime, hashlib, json, os, re, shutil, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS_W
SHELVES = ("cui", "cover", "title", "toc", "acronyms", "units", "back")
SHELF_NAME = {"cui": "CUI cover", "cover": "Cover", "title": "Title page", "toc": "Table of Contents",
              "acronyms": "Acronyms and Abbreviations", "units": "Units and Symbols", "back": "Back cover"}
OPTIONAL = {"cui", "title", "units", "back"}          # these can be None in Setup
FOLDER = "section_designs"
FORMAT = 1
AS_WRITTEN = ""
_STYLEREF = re.compile(r'STYLEREF\s+(?:"([^"]+)"|(\S+))', re.I)


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


# ------------------------------------------------------------------ the library
def _root(config_dir):
    return os.path.join(config_dir, FOLDER)


def _index(config_dir):
    p = os.path.join(_root(config_dir), "index.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("designs"), list) else {"format": FORMAT, "designs": []}
    except (OSError, ValueError):
        return {"format": FORMAT, "designs": []}


def _save(config_dir, d):
    os.makedirs(_root(config_dir), exist_ok=True)
    p = os.path.join(_root(config_dir), "index.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dict(d, format=FORMAT), f, indent=1)
    os.replace(p + ".tmp", p)


def designs(config_dir, shelf=None):
    return [x for x in _index(config_dir)["designs"] if shelf is None or x["shelf"] == shelf]


def get(config_dir, did):
    return next((x for x in designs(config_dir) if x["id"] == did), None)


def path_of(config_dir, x):
    return os.path.join(_root(config_dir), x["file"]) if x else ""


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def default_map(info):
    """Each styled paragraph's fill-in: its style's own key; Normal waits for a pick (as written)."""
    out = {}
    for p in info["paragraphs"]:
        st = p["style"]
        if st and st.lower() not in ("normal", "") and p["text"].strip():
            out[str(p["i"])] = re.sub(r"[^a-z0-9]+", "_", st.lower()).strip("_")
    return out


def add(config_dir, shelf, path, name=""):
    """A Word file onto a shelf (copied; the original is never changed). Returns the design."""
    if shelf not in SHELVES:
        raise ValueError(shelf)
    info = read(path)
    d = _index(config_dir)
    did = _sha(path)
    while any(x["id"] == did for x in d["designs"]):
        did = did[:-1] + "x"
    fname = f"{did}.docx"
    os.makedirs(_root(config_dir), exist_ok=True)
    shutil.copyfile(path, os.path.join(_root(config_dir), fname))
    x = {"id": did, "shelf": shelf, "name": " ".join((name or os.path.splitext(os.path.basename(path))[0]).split())[:80],
         "file": fname, "from": os.path.basename(path), "added": _now(), "map": default_map(info)}
    d["designs"].append(x)
    _save(config_dir, d)
    return x


def replace(config_dir, did, path):
    """Bring in the updated Word file: the design takes it; the map keeps the rows that still exist. Setups already made
    keep the copy they used."""
    d = _index(config_dir)
    x = next((y for y in d["designs"] if y["id"] == did), None)
    if x is None:
        return None
    shutil.copyfile(path, os.path.join(_root(config_dir), x["file"]))
    info = read(path)
    keep = {str(p["i"]) for p in info["paragraphs"]}
    x["map"] = {k: v for k, v in x["map"].items() if k in keep}
    x["map"].update({k: v for k, v in default_map(info).items() if k not in x["map"]})
    x["updated"] = _now()
    _save(config_dir, d)
    return x


def remove(config_dir, did):
    d = _index(config_dir)
    x = next((y for y in d["designs"] if y["id"] == did), None)
    if x is None:
        return False
    d["designs"].remove(x)
    try:
        os.remove(os.path.join(_root(config_dir), x["file"]))
    except OSError:
        pass
    _save(config_dir, d)
    return True


LIB_SHELF = {"cover": "cover", "title": "title", "backer": "back"}       # the template library's kinds -> shelves
SHELF_KIND = {v: k for k, v in LIB_SHELF.items()}


def adopt(config_dir, lib):
    """3.90.0: the template library's covers, title pages and back covers onto their shelves, once each (the newest
    version of each family). Returns how many came over."""
    have = {x.get("library") for x in designs(config_dir)} | {x.get("library_family") for x in designs(config_dir)}
    shas = {}
    for x in designs(config_dir):
        try:
            shas[_sha(path_of(config_dir, x))] = x
        except OSError:
            pass
    n = 0
    seen = set()
    for it in list(getattr(lib, "items", []) or []):
        shelf = LIB_SHELF.get(it.get("kind"))
        fam = it.get("family", it["id"])
        if not shelf or fam in seen:
            continue
        top = lib.latest(it["id"]) or it
        seen.add(fam)
        if top["id"] in have or fam in have:
            continue
        v = lib.values(top) or {}
        src = lib.source_path(v["file"]) if v.get("file") else ""
        if not src or not os.path.isfile(src):
            continue
        try:
            if _sha(src) in shas:
                x = shas[_sha(src)]
            else:
                x = add(config_dir, shelf, src, name=lib.shown_name(top))
        except Exception:  # noqa: BLE001  a file Word cannot open stays in the library only
            continue
        d = _index(config_dir)
        for y in d["designs"]:
            if y["id"] == x["id"]:
                y["library"], y["library_family"] = top["id"], fam
        _save(config_dir, d)
        n += 1
    return n


def set_map(config_dir, did, mapping):
    d = _index(config_dir)
    x = next((y for y in d["designs"] if y["id"] == did), None)
    if x is None:
        return None
    x["map"] = {str(k): (v or AS_WRITTEN) for k, v in mapping.items()}
    _save(config_dir, d)
    return x


# ------------------------------------------------------------------ reading a design
def _parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def _styles(data):
    out = {}
    if "word/styles.xml" in data:
        for s in etree.fromstring(data["word/styles.xml"], parser=_parser()).iter(W + "style"):
            nm = s.find(W + "name")
            out[s.get(W + "styleId")] = nm.get(W + "val") if nm is not None else s.get(W + "styleId")
    return out


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _pstyle(p, names):
    ps = p.find(f"{W}pPr/{W}pStyle")
    sid = ps.get(W + "val") if ps is not None else ""
    return names.get(sid, sid) or "Normal"


def _in_textbox(p):
    a = p.getparent()
    while a is not None:
        if a.tag == W + "txbxContent":
            return True
        a = a.getparent()
    return False


def _top_paragraphs(body):
    """Body paragraphs in order, text boxes included, table cells left to the tables."""
    out = []
    for p in body.iter(W + "p"):
        anc, in_tbl = p.getparent(), False
        while anc is not None and anc is not body:
            if anc.tag == W + "tc" and not _in_textbox(p):
                in_tbl = True
                break
            anc = anc.getparent()
        if not in_tbl:
            out.append(p)
    return out


def _instr(root):
    return [" ".join((t.text or "") for t in f.iter(W + "instrText")) for f in root.iter(W + "r")
            if f.find(W + "instrText") is not None] + [s.get(W + "instr") or "" for s in root.iter(W + "fldSimple")]


def read(path):
    data = _parts(path)
    names = _styles(data)
    root = etree.fromstring(data["word/document.xml"], parser=_parser())
    body = root.find(W + "body")
    paras = [{"i": i, "style": _pstyle(p, names), "text": _ptext(p), "in_textbox": _in_textbox(p)}
             for i, p in enumerate(_top_paragraphs(body))]
    tables = []
    for t in body.iter(W + "tbl"):
        rows = t.findall(W + "tr")
        cells = [[_ptext(c) for c in r.findall(W + "tc")] for r in rows]
        tables.append({"rows": len(rows), "header": cells[0] if cells else [], "sample": cells[1] if len(cells) > 1 else []})
    fields = [x.strip() for x in _instr(root) if x.strip()]
    for n, b in data.items():
        if re.match(r"word/(header|footer)\d*\.xml$", n):
            fields += [x.strip() for x in _instr(etree.fromstring(b, parser=_parser())) if x.strip()]
    sources = sorted({(m.group(1) or m.group(2)) for f in fields for m in [_STYLEREF.search(f)] if m})
    sections = len(body.findall(f".//{W}sectPr"))
    return {"paragraphs": paras, "tables": tables, "fields": fields, "sources": sources, "sections": max(1, sections)}


def other_pages(path):
    """Text other pages read: each STYLEREF source style and where its paragraph is (a text box is called out)."""
    info = read(path)
    out = []
    for st in info["sources"]:
        hits = [p for p in info["paragraphs"] if p["style"].casefold() == st.casefold()]
        out.append({"style": st, "where": (hits[0]["text"][:60] if hits else ""), "found": bool(hits),
                    "in_textbox": any(p["in_textbox"] for p in hits)})
    return out


def check(path):
    """Quiet unless a STYLEREF source is missing from the design or sits in a text box (Word cannot read it there)."""
    out = []
    for s in other_pages(path):
        if not s["found"]:
            out.append(f"Nothing in this design is in the style {s['style']}, which a header, footer or field reads.")
        elif s["in_textbox"]:
            out.append(f"The {s['style']} text sits in a text box: other pages cannot read it there. Put it in a paragraph.")
    return out


# ------------------------------------------------------------------ splitting a file with several Word sections
def split(path, out_dir, keep=None):
    """One file per Word section of the body (a section ends at a paragraph carrying its sectPr; the last at the body's).
    keep: the section numbers (from 1) to write; default all. Returns the files written."""
    data = _parts(path)
    root = etree.fromstring(data["word/document.xml"], parser=_parser())
    body = root.find(W + "body")
    final = body.find(W + "sectPr")
    groups, cur = [], []
    for el in list(body):
        if el is final:
            continue
        cur.append(el)
        if el.tag == W + "p" and el.find(f"{W}pPr/{W}sectPr") is not None:
            groups.append((cur, el.find(f"{W}pPr/{W}sectPr")))
            cur = []
    if cur or not groups:
        groups.append((cur, final))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    out = []
    for k, (els, sect) in enumerate(groups, 1):
        if keep is not None and k not in keep:
            continue
        r2 = copy.deepcopy(root)
        b2 = r2.find(W + "body")
        for el in list(b2):
            b2.remove(el)
        for el in els:
            e2 = copy.deepcopy(el)
            sp = e2.find(f"{W}pPr/{W}sectPr") if e2.tag == W + "p" else None
            if sp is not None:
                sp.getparent().remove(sp)
            b2.append(e2)
        if sect is not None:
            b2.append(copy.deepcopy(sect))
        d2 = dict(data)
        d2["word/document.xml"] = etree.tostring(r2, xml_declaration=True, encoding="UTF-8", standalone=True)
        dest = os.path.join(out_dir, f"{stem} (section {k}).docx")
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for n, b in d2.items():
                z.writestr(n, b)
        out.append(dest)
    return out


# ------------------------------------------------------------------ filling a design
def _set_text(p, text):
    runs = p.findall(W + "r")
    first = next((r for r in runs if r.find(W + "t") is not None), None)
    for r in runs:
        if r is not first and r.find(W + "t") is not None and r.find(W + "fldChar") is None and r.find(W + "instrText") is None:
            p.remove(r)
    if first is None:
        first = etree.SubElement(p, W + "r")
    for t in first.findall(W + "t"):
        first.remove(t)
    t = etree.SubElement(first, W + "t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def fill(path, mapping, values, out, rows=None):
    """A copy of the design with each mapped paragraph showing its value (a fill-in with no value keeps the design's
    words); rows: [[cell, ...]] for the first table whose sample row repeats once per entry. Fields stay as written and
    Word updates them when it opens the file. Returns out."""
    data = _parts(path)
    root = etree.fromstring(data["word/document.xml"], parser=_parser())
    body = root.find(W + "body")
    for i, p in enumerate(_top_paragraphs(body)):
        key = (mapping or {}).get(str(i)) or AS_WRITTEN
        if key and (values or {}).get(key):
            _set_text(p, str(values[key]))
    if rows is not None:
        t = next(iter(body.iter(W + "tbl")), None)
        if t is not None:
            trs = t.findall(W + "tr")
            if len(trs) >= 2:
                sample = trs[1]
                for extra in trs[2:]:
                    t.remove(extra)
                at = list(t).index(sample)
                t.remove(sample)
                for k, row in enumerate(rows):
                    tr = copy.deepcopy(sample)
                    for tc, val in zip(tr.findall(W + "tc"), row):
                        ps = tc.findall(W + "p")
                        if ps:
                            _set_text(ps[0], str(val))
                            for extra in ps[1:]:
                                tc.remove(extra)
                    t.insert(at + k, tr)
    data["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    if "word/settings.xml" in data:                         # Word updates the fields (STYLEREF, TOC, PAGE) on open
        sroot = etree.fromstring(data["word/settings.xml"], parser=_parser())
        if sroot.find(W + "updateFields") is None:
            uf = etree.SubElement(sroot, W + "updateFields"); uf.set(W + "val", "true")
        data["word/settings.xml"] = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out + ".part", "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in data.items():
            z.writestr(n, b)
    os.replace(out + ".part", out)
    return out


# ------------------------------------------------------------------ Setup's pick per section
def picks(M):
    import setupdoc as SD
    S = SD.setup_of(M)
    if not isinstance(S.get("designs"), dict):
        S["designs"] = {}
    return S["designs"]


def pick(M, shelf, did):
    """Setup picks a design for a section (did), or None (\"none\": the section is left out; optional sections only)."""
    if shelf not in SHELVES:
        return False
    if did == "none" and shelf not in OPTIONAL:
        return False
    picks(M)[shelf] = did or ""
    if hasattr(M, "pending"):
        M.pending = True
    return True


def picked(M, shelf):
    return picks(M).get(shelf, "")
