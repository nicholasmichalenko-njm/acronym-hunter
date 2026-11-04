"""The three libraries (3.49.0): every template library item lands in one library and one category, the way Word
template experts work: fundamentals (Formatting Standards), components (Quick Parts), assembly pieces (Layout).

LIBRARIES        (key, title) of the three libraries
CATEGORIES       {library: [(key, title, kinds)]}; a style goes by its Word type (paragraph, character, table)
place(lib, item) (library, category key), or (None, None) for an item no library shows (a matrix view)
effort_types(item), fits(item, eid), status(item)
items_in(lib, library, category=None, eid=None, status=None, words="")
counts(lib, library, eid=None, status=None)
set_effort_types(lib, ids, ets), set_status(lib, ids, status)

An item's effort types are tags (a list of effort type ids; "*" is every effort type); a profile built for one effort
type picks from the items tagged for it. Status: Draft (just imported), Approved (ready to build with), Retired (kept,
not offered). Items kept before 3.49.0 read as Approved: they were in use. Rules only; no Qt."""
import templatelib as TL

ALL = "*"
LIBRARIES = (("formatting", "Formatting Standards"), ("quickparts", "Quick Parts"), ("layout", "Layout"))
LIBRARY = dict(LIBRARIES)
CATEGORIES = {
    "formatting": [("theme", "Theme and colors", ("theme",)),
                   ("fonts", "Font sets", ("variables", "font")),
                   ("page_setup", "Page setups", ("page_setup",)),
                   ("pagination", "Pagination schemes", ("pagination",)),
                   ("heading_numbering", "Heading numbering", ("heading_numbering",)),
                   ("lists", "Lists", ("list_numbering",)),
                   ("para_styles", "Paragraph styles", ("style",)),
                   ("char_styles", "Character styles", ()),
                   ("table_styles", "Table styles", ("table_style",))],
    "quickparts": [],                                   # by each Quick Part's own category (01 Front matter, ...)
    "layout": [("covers", "Covers", ("cover", "cover_design")),
               ("titles", "Title pages", ("title",)),
               ("backers", "Back covers", ("backer",)),
               ("hf", "Headers and footers", ("hf", "hf_design")),
               ("sections", "Sections and section designs", ("section", "part")),
               ("table_looks", "Table looks", ("table_look",)),
               ("captions", "Captions", ("captions",)),
               ("toc", "Table of contents and lists", ("toc",))]}
_KIND = {k: (lib, cat) for lib, cats in CATEGORIES.items() for cat, _t, kinds in cats for k in kinds}
NO_CATEGORY = "No category"


def category_title(library, cat):
    if library == "quickparts":
        return cat or NO_CATEGORY
    return next((t for k, t, _ks in CATEGORIES.get(library, []) if k == cat), cat)


def _values(lib, item, cache={}):  # noqa: B006  a small cache by id and content: an item's values change only with its hash
    key = (lib.root, item["id"], item.get("hash"))
    if key not in cache:
        cache[key] = lib.values(item) or {}
    return cache[key]


def place(lib, item):
    """(library, category) for an item."""
    k = item.get("kind")
    if k == "quickpart":
        return "quickparts", str(_values(lib, item).get("category") or "") or NO_CATEGORY
    if k == "style":
        t = _values(lib, item).get("type")
        return "formatting", {"character": "char_styles", "table": "table_styles"}.get(t, "para_styles")
    return _KIND.get(k, (None, None))


def effort_types(item):
    v = (item.get("tags") or {}).get("effort_types")
    return [str(x) for x in v] if isinstance(v, list) else []


def fits(item, eid):
    """True when an item is offered for an effort type (tagged for it or for every effort type)."""
    ets = effort_types(item)
    return ALL in ets or eid in ets


def status(item):
    s = item.get("status")
    return s if s in dict(TL.STATUSES) else "approved"


def effort_type_words(item, names):
    """'Every effort type', 'RFP response, RFI response' or 'Not tagged' (names: {id: name})."""
    ets = effort_types(item)
    if ALL in ets:
        return "Every effort type"
    return ", ".join(names.get(e, e) for e in ets) or "Not tagged"


def items_in(lib, library, category=None, eid=None, status_=None, words=""):
    """The items of a library (and category), newest first within a family, filtered by effort type ("" untagged
    only), status and words in the name, summary or source."""
    out = []
    w = (words or "").casefold().strip()
    for i in lib.items:
        lb, cat = place(lib, i)
        if lb != library or (category is not None and cat != category):
            continue
        if eid == "":
            if effort_types(i):
                continue
        elif eid is not None and not fits(i, eid):
            continue
        if status_ is not None and status(i) != status_:
            continue
        if w and w not in " ".join(str(i.get(x) or "") for x in ("name", "summary", "source", "label")).casefold():
            continue
        out.append(i)
    return sorted(out, key=lambda i: (lib.base_of(i).casefold(), -int(i.get("version") or 1)))


def counts(lib, library, eid=None, status_=None):
    """{category: number of items} for a library (filters as items_in)."""
    out = {}
    for i in items_in(lib, library, None, eid, status_):
        out[place(lib, i)[1]] = out.get(place(lib, i)[1], 0) + 1
    return out


def categories(lib, library):
    """[(key, title)] a library lists: its fixed categories, or the Quick Parts' own categories in order."""
    if library != "quickparts":
        return [(k, t) for k, t, _ks in CATEGORIES[library]]
    cats = sorted({place(lib, i)[1] for i in lib.items if i.get("kind") == "quickpart"}, key=lambda c: (c == NO_CATEGORY, c.casefold()))
    return [(c, c) for c in cats]


def set_effort_types(lib, ids, ets):
    """Tags items with effort types (a list of ids, or [ALL]). All or nothing. Returns how many changed."""
    ets = [ALL] if ALL in (ets or []) else sorted(dict.fromkeys(str(e) for e in (ets or []) if e))
    n = 0
    with lib.transaction():
        for iid in ids:
            i = lib.get(iid)
            if i is not None and effort_types(i) != ets:
                i.setdefault("tags", {})["effort_types"] = list(ets)
                n += 1
    return n


def set_status(lib, ids, st):
    if st not in dict(TL.STATUSES):
        return 0
    n = 0
    with lib.transaction():
        for iid in ids:
            i = lib.get(iid)
            if i is not None and status(i) != st:
                i["status"] = st
                n += 1
    return n
