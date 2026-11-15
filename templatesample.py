"""The sample pages a template gives (4.43.0; ST41 of 2026-11-15): what a document made from the template looks like,
as a short strip of pages, so a pick is seen without exporting. The pages: each starting page the template picks, a
front matter page with a Table of Contents, a body page with headings, a list, a table and a figure with their
captions, a landscape page and an appendix page. Each page says its size, margins, header and footer distances, what
the header and footer hold, and the page number its part gives it.

This is the app's own drawing of the standard's values: close, not Word's layout. The screen labels it Approximate.
The filler words are the same for every template. Only read; nothing is saved and nothing leaves the PC."""
import prodrules as PRL

SAMPLE = {"volume_name": "Volume I: Technical", "solicitation": "Solicitation number", "company": "Company",
          "classification": "", "project": "Project", "marking": "Restriction marking", "team_line": "", "a_number": "",
          "date": "Month Day, Year", "title": "Proposal title", "customer": "Customer"}
_SEP = {"hyphen": "-", "period": ".", "colon": ":", "emDash": "-", "enDash": "-"}
_ROMAN = {"lowerRoman": "i", "upperRoman": "I", "lowerLetter": "a", "upperLetter": "A"}


def _num(v, variables, default):
    if isinstance(v, str) and v.startswith("="):
        v = variables.get(v[1:])
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _fill(text):
    out = str(text or "")
    for k, v in SAMPLE.items():
        out = out.replace("{" + k + "}", v)
    return out.strip()


def page_number(numbers):
    """The number a part's first page shows: 'i', '1', '1-1', 'A-1'; '' for a part with no numbers."""
    if not numbers:
        return ""
    fmt = numbers.get("fmt") or "decimal"
    one = _ROMAN.get(fmt, "1")
    lvl = numbers.get("chapter_level")
    if not lvl:
        return one
    sep = _SEP.get(numbers.get("separator") or "hyphen", "-")
    return ("A" if int(lvl) >= 7 else "1") + sep + one


def _setup(std, key):
    v = std.get("variables") or {}
    ps = (std.get("page_setups") or {}).get(key) or {}
    w, h = PRL.PAGE_SIZES.get(v.get("paper") or "Letter", PRL.PAGE_SIZES["Letter"])
    if key != "portrait":
        w, h = _num(ps.get("w"), v, h), _num(ps.get("h"), v, w)
    m = [_num(ps.get(k, "=margin_" + k), v, 1.0) for k in ("top", "bottom", "left", "right")]
    if key == "portrait":
        m = [_num(v.get("margin_" + k), v, 1.0) for k in ("top", "bottom", "left", "right")]
    return {"w": w, "h": h, "m": m, "hd": _num(ps.get("header"), v, 0.5), "ft": _num(ps.get("footer"), v, 0.5)}


def _part(std, key):
    return next((p for p in (std.get("pagination") or {}).get("parts") or [] if p.get("key") == key), {})


def _headings(std, n=3):
    hn = std.get("heading_numbering") or {}
    levels = [l for l in hn.get("levels") or [] if l.get("style")][:n]
    out = []
    for i in range(n):
        text = ""
        if hn.get("on") and i < len(levels):
            text = str(levels[i].get("text") or "")
            for d in range(1, 10):
                text = text.replace(f"%{d}", "1")
        out.append((i + 1, text))
    return out


def _caption(std, label):
    c = next((c for c in std.get("captions") or [] if c.get("label") == label and c.get("part") in ("body", None, "")), None) \
        or next((c for c in std.get("captions") or [] if c.get("label") == label), None)
    if c is None:
        return None
    lvl = c.get("chapter_level")
    num = ("1" + str(c.get("separator") or "-") + "1") if lvl else "1"
    return {"text": f"{label} {num}.", "above": (c.get("position") or "below") == "above"}


def _bullets(std):
    ln = std.get("list_numbering") or {}
    out = []
    for lst in (ln.get("lists") or [])[:2]:
        for i, lv in enumerate((lst.get("levels") or [])[:2]):
            mark = str(lv.get("text") or "")
            for d in range(1, 10):
                mark = mark.replace(f"%{d}", "1" if lv.get("fmt") == "decimal" else "a")
            out.append((i, mark))
    return out or [(0, "•"), (1, "–"), (0, "1."), (1, "a.")]


def pages(std, config_dir=None, starts=()):
    """[{"key", "label", "w", "h", "m" (top, bottom, left, right), "hd", "ft", "header" (left, center, right), "footer", "number", "blocks"}].
    A block is a tuple: ("title", text), ("toc",), ("h", level, number), ("text", lines), ("list", [(level, mark)]),
    ("table", caption or None), ("figure", caption or None), ("built", name). starts: the names of the starting pages."""
    port, land = _setup(std, "portrait"), _setup(std, "landscape")
    out = []

    def page(key, label, setup, part, blocks):
        p = _part(std, part)
        hf = ((std.get("hf_layouts") or {}).get(part) or {}).get("header") or {}
        head = (_fill(hf.get("left")), _fill(hf.get("center")), _fill(hf.get("right")))
        if not any(head):
            head = (_fill(p.get("header")), "", "")
        out.append(dict(setup, key=key, label=label, header=head, footer=SAMPLE["marking"] if p.get("footer_marking") else "",
                        number=page_number(p.get("numbers")), blocks=blocks))

    for i, name in enumerate(starts):
        page(f"start{i}", name, port, "cover", [("built", name)])
    page("front", "Front matter", port, "front", [("title", "Table of Contents"), ("toc",)])
    hs = _headings(std)
    tab, fig = _caption(std, "Table"), _caption(std, "Figure")
    page("body", "Body", port, "body", [("h", 1, hs[0][1]), ("text", 3), ("h", 2, hs[1][1]), ("text", 2), ("list", _bullets(std)),
                                         ("table", tab), ("h", 3, hs[2][1]), ("figure", fig)])
    page("landscape", "Landscape page", land, "body", [("h", 2, hs[1][1]), ("table", tab)])
    page("appendix", "Appendix", port, "appendix", [("title", "Appendix A"), ("text", 4), ("figure", fig)])
    return out
