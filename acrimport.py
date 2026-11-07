"""Import a list into the effort's acronym list (3.76.0): any Excel or CSV layout, merged.

read(path) -> {"headings", "rows", "guess", "ours"}: the first sheet's (or the CSV's) heading row and its rows; the term,
definition, found-in and notes columns guessed from the headings; ours is True for Stationkeeper's own exports (an
Acronym List, a scan report, another copy's list), which read with no questions.
to_rows(book, columns) -> [{column of the effort list: value}] for the columns confirmed.
merge(effort_list, rows, name) -> the merge's report (effortmerge.merge_rows): new terms in the list, the same meaning
fills empty fields, two meanings keep ours and add theirs to Other definitions, listed for review. Only the effort list
changes, never the scan results.
Rules only (No AI); nothing leaves the PC."""
import csv, os

FIELDS = ("Term", "Definition", "Found in", "Notes")
HINTS = {"Term": ("term", "acronym", "abbreviation", "acronym / abbreviation", "abbrev", "acr", "item", "symbol", "unit"),
         "Definition": ("definition", "meaning", "expansion", "spelled out", "description", "stands for", "full name",
                        "long form", "full form"),
         "Found in": ("found in", "where found", "location", "locations", "source", "document", "documents", "used in",
                      "where"),
         "Notes": ("notes", "note", "comments", "comment", "remarks")}
OURS = {"Term", "Definition", "Status", "Found in"}           # an Acronym List or another copy's list
SCAN = {"Term", "Type", "Count", "Found in"}                   # a scan report


def _cell(v):
    return "" if v is None else " ".join(str(v).split())


def _table(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt"):
        for enc in ("utf-8-sig", "cp1252"):
            try:
                with open(path, newline="", encoding=enc) as f:
                    return [[_cell(c) for c in r] for r in csv.reader(f)]
            except UnicodeDecodeError:
                continue
        return []
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Effort List"] if "Effort List" in wb.sheetnames else wb.worksheets[0]
        return [[_cell(c) for c in r] for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def guess(headings):
    """{field: column index} from the headings: an exact hint first, then a heading that starts with one."""
    low = [h.casefold().strip(" :*") for h in headings]
    out = {}
    for field in FIELDS:
        for i, h in enumerate(low):
            if i not in out.values() and h in HINTS[field]:
                out[field] = i
                break
    for field in FIELDS:
        if field in out:
            continue
        for i, h in enumerate(low):
            if i not in out.values() and any(h.startswith(x) for x in HINTS[field]):
                out[field] = i
                break
    return out


def read(path):
    t = [r for r in _table(path) if any(r)]
    if not t:
        return {"headings": [], "rows": [], "guess": {}, "ours": False, "name": os.path.basename(path)}
    k = 0                                            # the heading row: the first with a term-like heading, in the top ten
    for i, r in enumerate(t[:10]):
        if "Term" in guess(r):
            k = i
            break
    heads, rows = t[k], t[k + 1:]
    hs = set(heads)
    return {"headings": heads, "rows": rows, "guess": guess(heads), "ours": OURS <= hs or SCAN <= hs,
            "name": os.path.basename(path), "all": "Status" in hs and OURS <= hs}


def to_rows(book, columns=None):
    """[{field: value}] from the rows, with columns {field: index} (default: the guess). Our own list keeps every column."""
    heads = book["headings"]
    if book.get("all") and columns is None:
        import effort as E
        idx = {h: i for i, h in enumerate(heads) if h in E.COLUMNS}
        return [{h: (r[i] if i < len(r) else "") for h, i in idx.items()} for r in book["rows"] if r and r[idx["Term"]]]
    cols = columns if columns is not None else book["guess"]
    if "Term" not in cols:
        return []
    out = []
    for r in book["rows"]:
        row = {f: (r[i] if i < len(r) else "") for f, i in cols.items() if i is not None and i >= 0}
        if row.get("Term"):
            out.append(row)
    return out


def merge(L, rows, name):
    import effortmerge as M
    n = M.merge_rows(L, rows, name)
    if n["added"] or n["filled"] or n["review"]:
        L.pending = True
        L.save()
    return n


def not_found(L, results):
    """Imported terms no scan of this effort has found: they show 'not found in this effort's documents yet'."""
    return [t for t in L.order if t not in (results or {}) and not (L.rows[t].get("Found in") or "").strip()]
