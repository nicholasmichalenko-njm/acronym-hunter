"""The pages a volume will have (3.31.0), worked out from the structure and Production Standards, for the Structure
Builder's live preview: which part each page is in, its page number as the part numbers it, its header and footer, and
what is on it (an element's title and entries, a divider's title, a placeholder, the headings of the response and how
many requirements sit under each), portrait or landscape.

Pages come from the page budget: a section with pages set takes them; one without takes one page for its first-level
section and runs on for the rest. Every first-level section of the response and every appendix starts a new page. It is a
plan, not Word's layout: Exact preview in Word (exactpreview) gives Word's own pages. 3.32.0: a library Quick Part placed in
a section adds the pages it fills (measured by Word or typed), and an element made of one takes them. Rules only;
nothing leaves the PC."""
import math

PART_KEY = {"cover": "cover", "title": "cover", "front": "front", "body": "body", "appendix": "appendix", "back": "backer"}
SLOTS = ("left", "center", "right")


def _roman(n):
    out = ""
    for v, s in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"),
                 (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += s; n -= v
    return out


def number(numbers, n, chapter=1):
    """How page n of a part reads ('ii', '3', '2-1', 'A-1'); '' with no page numbers."""
    if not numbers or not numbers.get("fmt"):
        return ""
    f = numbers["fmt"]
    k = n + int(numbers.get("start_at") or 1) - 1
    s = {"decimal": str(k), "lowerRoman": _roman(k), "upperRoman": _roman(k).upper(),
         "lowerLetter": chr(96 + min(max(k, 1), 26)), "upperLetter": chr(64 + min(max(k, 1), 26))}.get(f, str(k))
    if numbers.get("chapter_level"):
        lvl = int(numbers["chapter_level"])
        ch = chr(64 + max(1, chapter)) if lvl >= 7 else str(chapter)
        sep = {"hyphen": "-", "period": ".", "colon": ":", "enDash": "–", "emDash": "—"}.get(numbers.get("separator") or "hyphen", "-")
        s = f"{ch}{sep}{s}"
    return s


def _part_of(std, key):
    parts = ((std or {}).get("pagination") or {}).get("parts") or []
    by = {p.get("key"): p for p in parts}
    for k in {"cover": ("cover",), "front": ("front",), "body": ("body", "all"), "appendix": ("appendix", "body", "all"),
              "backer": ("backer", "back")}.get(key, (key,)):
        if k in by:
            return by[k]
    return {}


def _fill(text, std, page=""):
    import re
    v = (std or {}).get("variables") or {}
    sample = {"volume_name": "Volume name", "solicitation": "Solicitation", "company": "Company", "chapter": "Chapter",
              "pages": "#", "classification": ""}

    def one(m):
        k = m.group(1)
        if k == "page":
            return page or ""
        if v.get(k):
            return str(v[k])
        for f in (std or {}).get("fill_ins") or []:
            if f.get("key") == k:
                return f.get("value") or f.get("name") or k
        return sample.get(k, k)
    return re.sub(r"\{(\w+)\}", one, text or "")


def _hf(std, key, page):
    lay = ((std or {}).get("hf_layouts") or {}).get(key) or {}
    out = {}
    for kind in ("header", "footer"):
        spec = lay.get(kind) or {}
        out[kind] = {s: _fill(spec.get(s, ""), std, page) for s in SLOTS}
        if kind == "header" and not any(out[kind].values()):
            p = _part_of(std, key)
            if p.get("header"):
                out[kind]["center"] = _fill(p["header"], std, page)
        if kind == "footer" and not any(out[kind].values()) and page:
            out[kind]["center"] = page
    mark = ""
    v = (std or {}).get("variables") or {}
    if (((lay.get("footer") or {}).get("marking")) or _part_of(std, key).get("footer_marking")) and v.get("marking"):
        mark = str(v["marking"])
    return out["header"], out["footer"], mark


def item_pages(ex, x):
    """3.32.0: the pages of a library item placed in a section (a Quick Part measured or typed); None when unknown."""
    if (x or {}).get("kind") != "quickpart":
        return None
    return ((ex or {}).get("lib_pages") or {}).get(x.get("id")) or qp_pages(ex, x.get("name"))


def qp_pages(ex, name):
    """The pages of a library Quick Part by its name; None when it has none."""
    return ((ex or {}).get("lib_pages_by_name") or {}).get(str(name or "").casefold()) if name else None


def plan(M, volume, std=None, extras=None):
    """[{"part", "key", "label", "kind", "orient", "num", "header", "footer", "marking", "title", "lines"}] for the volume's
    pages, in order. lines: [(text, how)] where how is "h1".."h9", "toc", "row", "text", "note", "lib"."""
    import compliance as C
    import outline_ops as O
    import pagebudget as PB
    import responseelements as RE
    import setupdoc as SD
    import structparts as SP
    ex = extras or {}
    data = ex.get("data") or RE.builtins()
    heads = O.volume_heads(M)
    labs = O.in_volume(M, volume) if volume else O.labels(M)
    entries = [o for o in M.outline if C.outline_label(o) in set(labs) and C.outline_label(o) not in heads]
    P = SD.placed_in(M)
    B = SD.by_id(M)
    pages = []
    counters, chapter = {}, {"body": 0, "appendix": 0}
    numbered = [(C.outline_label(o), O.heading_level(M, C.outline_label(o))) for o in entries
                if SP.part_of(o) in ("body", "appendix") and o.get("kind") not in ("element", "divider")]

    def new_page(o, kind, title="", orient="portrait", part=None):
        part = part or SP.part_of(o) if o is not None else (part or "cover")
        key = PART_KEY.get(part, "body")
        sp = _part_of(std, key)
        nums = sp.get("numbers")
        restart = (nums or {}).get("restart", "part")
        if key not in counters or ((restart == "each" or (nums or {}).get("chapter_level")) and kind == "chapter"):
            counters[key] = 0 if restart != "never" or not pages else max(counters.values() or [0])
        counters[key] += 1
        ch = chapter.get(part, 1)
        num = "" if (nums or {}).get("chapter_level") and ch == 0 else number(nums, counters[key], max(1, ch))
        hd, ft, mark = _hf(std, key, num)
        pg = {"part": part, "key": key, "label": C.outline_label(o) if o is not None else "", "kind": kind, "orient": orient,
              "num": num, "header": hd, "footer": ft, "marking": mark, "title": title, "lines": []}
        pages.append(pg)
        return pg

    has_cover = any((o.get("element") and (RE.get(data, o["element"]) or {}).get("source") == "cover") for o in entries)
    if not has_cover:
        new_page(None, "cover", "Cover (the template's)", part="cover")
    land = []                                            # (level, orient) of open Word sections
    cur = None
    for o in entries:
        lab = C.outline_label(o)
        part = SP.part_of(o)
        lvl = o.get("level", 1)
        while land and land[-1][0] >= lvl:
            land.pop()
        if o.get("brk"):
            land.append((lvl, o["brk"].get("orient", "portrait")))
        orient = land[-1][1] if land else "portrait"
        hl = O.heading_level(M, lab)
        k = o.get("kind") or ""
        budget = PB.pages(M, lab)
        if k == "element":
            e = RE.get(data, o.get("element") or "") or {}
            src = e.get("source", "placeholder")
            qp = qp_pages(ex, e.get("lib")) if src == "quickpart" else None
            if qp and (not budget or (PB.source(M, lab) == "team" and budget == float(e.get("pages") or 0))):
                budget = qp                              # 3.32.0: a Quick Part's measured (or typed) pages
            n = int(math.ceil(budget or e.get("pages") or 1))
            if src == "divider":
                new_page(o, "divider", lab, orient)
                cur = None
                continue
            if src in ("cover", "backer"):
                pg = new_page(o, "cover", e.get("name", lab))
                cur = None
                continue
            pg = new_page(o, "element", lab, orient)
            if src == "toc":
                pg["lines"] += [(f"{l}", "toc") for l, h in numbered if h <= 3]
            elif src == "list_appendix":
                pg["lines"] += [(l, "toc") for l, h in numbered if l.lower().startswith("appendix ")]
            elif src in ("list_figure", "list_table"):
                pg["lines"] += [(("Figure" if src == "list_figure" else "Table") + " #", "toc")]
            elif src == "acronyms":
                pg["lines"] += [(f"{t}  {d}", "row") for t, d in (ex.get("acronyms") or [])[:30]] or [("(the acronyms in the effort's list)", "note")]
            elif src == "matrix":
                pg["lines"] += [(f"{i}  {s}", "row") for i, _r, s in SD.matrix_rows(M, entries, P)[:30]]
            elif src == "quickpart":
                pg["lines"].append((f"Quick Part: {e.get('lib') or lab}" + (f" ({qp} page{'s' if qp != 1 else ''}, measured)"
                                                                            if qp else ""), "lib"))
            elif src == "units":
                pg["lines"].append(("Unit, meaning, system", "row"))
            else:
                pg["lines"].append((f"Placeholder: {n} page{'s' if n != 1 else ''}", "note"))
            for _ in range(n - 1):
                new_page(o, "more", lab, orient)
            cur = None
            continue
        if k == "divider":
            new_page(o, "divider", lab, orient)
            cur = None
            continue
        if k == "placeholder":
            n = int(math.ceil(budget or 1))
            pg = new_page(o, "placeholder", lab, orient)
            pg["lines"] += [(lab, f"h{min(max(hl, 1), 9)}"), (f"Placeholder: {n} page{'s' if n != 1 else ''}", "note")]
            for _ in range(n - 1):
                new_page(o, "more", lab, orient)
            cur = None
            continue
        starts = cur is None or hl <= 1 or (o.get("brk") is not None) or (cur["orient"] != orient) or cur["part"] != part
        lp = sum(item_pages(ex, x) or 0 for x in o.get("lib") or [])     # 3.32.0: pages the placed Quick Parts fill
        if starts:
            if hl <= 1 and part in chapter:
                chapter[part] += 1
            if budget and (hl <= 1 or o.get("brk")):
                n, budgeted = int(math.ceil(budget)), True
            else:
                n, budgeted = max(1, int(math.ceil(lp))), False
            cur = new_page(o, "chapter" if hl <= 1 else "section", lab, orient)
            cur["_left"] = n
            cur["_budgeted"] = budgeted
            extra = n - 1
        else:
            extra = max(0, int(math.ceil(lp)) - 1) if lp and not cur.get("_budgeted") else 0   # a 1-page Quick Part fits on the page
        cur["lines"].append((lab, f"h{min(max(hl, 1), 9)}"))
        for x in o.get("lib") or []:
            xp = item_pages(ex, x)
            cur["lines"].append((f"{x.get('name', '')} ({x.get('kind', '')}" + (f", {xp} page{'s' if xp != 1 else ''}" if xp else "") + ")", "lib"))
        nreq = sum(1 for i in P.get(lab, []) if (B.get(i) or {}).get("decision") == "Keep")
        if nreq:
            cur["lines"].append((f"{nreq} requirement{'s' if nreq != 1 else ''}", "text"))
        budgeted = cur.get("_budgeted")
        for _ in range(extra):
            new_page(o, "more", lab, orient)
        if extra:
            cur = pages[-1]
            cur["_budgeted"] = budgeted
            cur["lines"].append((f"(continued: {lab})", "note"))
    return pages


def summary(pages):
    """Pages in each part, and the volume's page count, for the preview's line under it."""
    by = {}
    for p in pages:
        by[p["part"]] = by.get(p["part"], 0) + 1
    return by, len(pages)
