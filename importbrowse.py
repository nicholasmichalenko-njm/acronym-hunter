"""The import browser's rules (3.44.0): what a template or Word document holds, by layer, each item New, Same as the
library, or Differs (and what differs), and each Word section of the file as a section you can keep.

LAYERS          the import's groups (templatelib.collect's cards) under Building blocks, Components and Sections
layer_of(card)  the layer a group belongs to
differs(lib, it) a short line of what differs from the library's newest version ("size 12 here, 11 in the library")
sections_of(path) each Word section: its page setup, page numbers, and its header and footer kept whole (with pictures)
section_card(path, lib) the Sections group for the browser
Rules only; the file is read once and never written."""
import base64, os, posixpath, re, zipfile

LAYERS = (("blocks", "Building blocks"), ("components", "Components"), ("sections", "Sections"))
BLOCKS = ("styles:", "variables", "pages", "heading_numbering", "list_numbering", "table_styles", "theme", "fonts")
BADGE = {"new": "New", "same": "Same as the library", "variant": "Differs"}
TWIP = 1440.0


def layer_of(card):
    k = card.key
    if k == "sections":
        return "sections"
    return "blocks" if any(k == b or (b.endswith(":") and k.startswith(b)) for b in BLOCKS) else "components"


def _flat(v, pre=""):
    out = {}
    if isinstance(v, dict):
        for k, x in v.items():
            if str(k).startswith("_") or k in ("xml", "header", "footer", "header_media", "footer_media", "b64"):
                continue
            out.update(_flat(x, f"{pre} {k}".strip()))
    elif isinstance(v, list):
        for n, x in enumerate(v, 1):
            out.update(_flat(x, f"{pre} {n}".strip()))
    else:
        out[pre or "value"] = v
    return out


def differs(lib, it, most=3):
    """What differs between an imported item and the library's newest version of the same name: [(what, here, library)]
    and a short line of it. Same or new: ([], "")."""
    if it.get("state") != "variant":
        return [], ""
    st, hit = lib.match(it["kind"], it["name"], it["values"])
    if st != "variant" or not hit:
        return [], ""
    a, b = _flat(it["values"]), _flat(lib.values(hit) or {})
    rows = [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    shown = lambda x: "none" if x in (None, "", False) else ("yes" if x is True else str(x))
    line = "; ".join(f"{k}: {shown(x)} here, {shown(y)} in the library" for k, x, y in rows[:most])
    if len(rows) > most:
        line += f"; and {len(rows) - most} more"
    return rows, line


def sections_of(path):
    """[{"n", "page": page setup (inches), "numbers": {"fmt", "start"}, "header", "footer", "header_media", "footer_media",
    "starts": the first words of the section}] for each Word section of the file, in order."""
    from lxml import etree
    from prodengine.engine.pkg import Package, NS
    W = NS["w"]
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    raw = open(path, "rb").read()
    pkg = Package.from_bytes(raw, os.path.basename(path))
    root = pkg.tree(pkg.main)
    body = root.find(f"{{{W}}}body")
    if body is None:
        return []
    rels = pkg.rels_of(pkg.main)
    out, first_words, prev_hf = [], "", {}
    sects = []
    for el in body:
        sp = el.find(f"{{{W}}}pPr/{{{W}}}sectPr") if el.tag == f"{{{W}}}p" else (el if el.tag == f"{{{W}}}sectPr" else None)
        if not first_words:
            first_words = " ".join("".join(t.text or "" for t in el.iter(f"{{{W}}}t")).split())[:80]
        if sp is not None:
            sects.append((sp, first_words))
            first_words = ""
    for n, (sp, words) in enumerate(sects, 1):
        def tw(el, a, default=None):
            v = el.get(f"{{{W}}}{a}") if el is not None else None
            try:
                return round(int(v) / TWIP, 2) if v is not None else default
            except ValueError:
                return default
        sz, mar = sp.find(f"{{{W}}}pgSz"), sp.find(f"{{{W}}}pgMar")
        w_, h_ = tw(sz, "w", 8.5), tw(sz, "h", 11)
        orient = (sz.get(f"{{{W}}}orient") if sz is not None else None) or ("landscape" if (w_ or 0) > (h_ or 0) else "portrait")
        page = {"name": f"Section {n}: {'Landscape' if orient == 'landscape' else 'Portrait'} {w_:g} x {h_:g} in", "w": w_, "h": h_,
                "orient": orient, "top": tw(mar, "top", 1), "bottom": tw(mar, "bottom", 1), "left": tw(mar, "left", 1),
                "right": tw(mar, "right", 1), "header": tw(mar, "header", 0.5), "footer": tw(mar, "footer", 0.5)}
        pn = sp.find(f"{{{W}}}pgNumType")
        numbers = {"fmt": (pn.get(f"{{{W}}}fmt") if pn is not None else None) or "",
                   "start": int(pn.get(f"{{{W}}}start")) if pn is not None and (pn.get(f"{{{W}}}start") or "").isdigit() else None}
        hf = dict(prev_hf)                                # a section with no header of its own carries the one before it
        for kind in ("header", "footer"):
            ref = next((r for r in sp.findall(f"{{{W}}}{kind}Reference") if r.get(f"{{{W}}}type") in (None, "default")), None)
            if ref is None or ref.get(f"{{{R}}}id") not in rels:
                continue
            tgt = rels[ref.get(f"{{{R}}}id")][1]
            hf[kind] = etree.tostring(pkg.tree(tgt), encoding="unicode")
            media = []
            for rid, (typ, t, mode) in pkg.rels_of(tgt).items():
                if mode != "External" and typ.endswith("/image") and t in pkg.raw:
                    media.append({"rid": rid, "name": posixpath.basename(t), "type": typ, "ct": pkg.content_type("/" + t),
                                  "b64": base64.b64encode(pkg.raw[t]).decode("ascii")})
            hf[kind + "_media"] = media
        prev_hf = hf
        out.append(dict({"n": n, "page": page, "numbers": numbers, "starts": words}, **hf))
    return out


def hf_text(xml):
    """The words a header or footer shows, fields as [PAGE] and the like."""
    if not xml:
        return ""
    words = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<w:instrText[^>]*>\s*(\w+)[^<]*</w:instrText>", r" [\1] ", xml)).split())
    return words[:90]


def section_card(path, lib):
    """The Sections group: each Word section as an item you can keep (kind "section")."""
    import templatelib as TL
    try:
        secs = sections_of(path)
    except Exception:  # noqa: BLE001  a file whose sections cannot be read just has no Sections group
        import diag
        diag.swallowed()
        return None
    if not secs:
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    items = []
    for s in secs:
        values = {k: s[k] for k in ("page", "numbers", "header", "footer", "header_media", "footer_media") if k in s}
        name = f"{stem} section {s['n']}"
        st, hit = lib.match("section", name, values)
        p = s["page"]
        summ = (f"{p['orient']} {p['w']:g} x {p['h']:g} in, margins {p['top']:g}/{p['bottom']:g}/{p['left']:g}/{p['right']:g}"
                + (f", pages {s['numbers']['fmt']}" if s["numbers"].get("fmt") else "")
                + (f"; header: {hf_text(s.get('header'))}" if hf_text(s.get("header")) else "")
                + (f"; footer: {hf_text(s.get('footer'))}" if hf_text(s.get("footer")) else "")
                + (f"; starts: {s['starts']}" if s.get("starts") else ""))
        items.append({"kind": "section", "name": name, "values": values, "summary": summ, "state": st,
                      "match": hit["name"] if hit else "", "keep": st != "same"})
    return TL.Card("sections", f"Word sections ({len(items)})", items,
                   "Each Word section of the file: its page setup, page numbers, and its header and footer kept whole. Use "
                   "here adds its page setup; Use in this standard from the library puts its header and footer on a part too.")


def collect(path, std, lib, installed_fonts=None):
    """templatelib.collect, with the Sections group (3.44.0). Returns ([Card], error)."""
    import templatelib as TL
    cards, err = TL.collect(path, std, lib, installed_fonts)
    if not err and not path.lower().endswith(".thmx"):
        sc = section_card(path, lib)
        if sc is not None:
            cards.append(sc)
    return cards, err
