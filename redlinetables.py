"""Tables in the redline copy (4.11.0; morning answer 17: getting tables right is crucial for redlining).

A PDF keeps no tables, only text placed on the page. A table shows as rows of text whose pieces line up in columns. This
finds them from where each piece of each line sits (pagesent's segments):
- the page's lines are grouped into rows by their height on the page (cells of one row are often separate lines);
- a run of rows, each in two or more pieces, whose pieces start at the same places is a table (two rows at least);
- a row with nothing in the first column carries on the row above (a cell's text that wrapped onto a second line);
- two columns where every first cell is a list marker or a number ((a), 1., 3.1.2) are a list or numbered headings,
  not a table.
The columns' widths come from where they start on the page. Rules only (No AI); nothing leaves the PC."""
import re

TOL = 8.0                                     # points a column's pieces may start apart and still line up
MARKER = re.compile(r"^(\(?[A-Za-z0-9]{1,4}[.)]|[•▪●–\-o*]|[A-Z]?\.?\d+(\.\d+)*\.?|\(?[ivxIVX]{1,5}\))$")


def _rows(page, keep):
    """The page's lines (those in keep) grouped by height on the page: [{"lines": [li], "segs": [(l, r, text, li)],
    "top", "bottom"}], top to bottom."""
    out = []
    for li in sorted(keep, key=lambda i: (page["lines"][i]["box"][1], page["lines"][i]["box"][0])):
        ln = page["lines"][li]
        top, bot = ln["box"][1], ln["box"][3]
        segs = [(a, b, txt, li) for a, b, txt in (ln.get("segs") or [(ln["box"][0], ln["box"][2], " ".join(ln["text"].split()))])]
        if out:
            r = out[-1]
            ov = min(bot, r["bottom"]) - max(top, r["top"])
            if ov > 0.5 * min(bot - top, r["bottom"] - r["top"]):
                r["lines"].append(li); r["segs"] = sorted(r["segs"] + segs); r["bottom"] = max(r["bottom"], bot)
                continue
        out.append({"lines": [li], "segs": sorted(segs), "top": top, "bottom": bot})
    return out


def _columns(rows):
    """Column starts from rows of two or more pieces: places where pieces of two rows or more start."""
    xs = sorted(s[0] for r in rows if len(r["segs"]) >= 2 for s in r["segs"])
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= TOL:
            groups[-1].append(x)
        else:
            groups.append([x])
    multi = sum(1 for r in rows if len(r["segs"]) >= 2)
    need = 2 if multi >= 2 else 99
    return [min(g) for g in groups if len(g) >= need]


def _col(x, cols):
    k = 0
    for i, c in enumerate(cols):
        if x + TOL >= c:
            k = i
    return k


def _table(rows, page_w):
    """A table from a run of rows, or None."""
    cols = _columns(rows)
    if len(cols) < 2:
        return None
    aligned = [r for r in rows if len(r["segs"]) >= 2 and all(any(abs(s[0] - c) <= TOL for c in cols) for s in r["segs"])]
    if len(aligned) < 2 or len(aligned) < 0.6 * sum(1 for r in rows if len(r["segs"]) >= 2):
        return None
    cells = []
    for r in rows:
        put = {}
        for s in r["segs"]:
            k = _col(s[0], cols)
            put[k] = (put[k] + " " + s[2]) if k in put else s[2]
        if 0 in put or not cells:                      # a new row; else the text wrapped from the row above
            cells.append([put.get(k, "") for k in range(len(cols))])
        else:
            for k, v in put.items():
                cells[-1][k] = (cells[-1][k] + " " + v).strip()
    if len(cols) == 2 and all(MARKER.match(c[0] or "x") or not c[0] for c in cells):
        return None                                    # a list, or numbered headings with a gap after the number
    right = max(s[1] for r in rows for s in r["segs"])
    widths = [max(1.0, (cols[k + 1] if k + 1 < len(cols) else max(right, cols[k] + 36)) - cols[k]) for k in range(len(cols))]
    return {"rows": cells, "widths": widths, "lines": sorted(li for r in rows for li in r["lines"])}


def find(doc, skip):
    """The tables of a read PDF (pagesent.read): [{"page": index, "rows": [[cell]], "widths": [points], "lines":
    [(page, line)]}] in reading order. skip: {(page, line)} left out (running headers, footers, lines set aside)."""
    out = []
    for pi, page in enumerate(doc.get("pages") or []):
        keep = [li for li in range(len(page["lines"])) if (pi, li) not in skip]
        rows = _rows(page, keep)
        i = 0
        while i < len(rows):
            if len(rows[i]["segs"]) < 2:
                i += 1
                continue
            j = i + 1
            col0 = rows[i]["segs"][0][0]
            while j < len(rows):
                r = rows[j]
                gap = r["top"] - rows[j - 1]["bottom"]
                height = max(4.0, rows[j - 1]["bottom"] - rows[j - 1]["top"])
                if gap > 2.5 * height:
                    break
                if len(r["segs"]) >= 2 or (r["segs"] and r["segs"][0][0] > col0 + TOL):
                    j += 1
                    continue
                break
            t = _table(rows[i:j], page.get("w") or 612) if j - i >= 2 else None
            if t:
                t["page"] = pi
                t["lines"] = [(pi, li) for li in t["lines"]]
                out.append(t)
                i = j
            else:
                i += 1
    return out


def text_of(table):
    """The table's words, row by row and cell by cell (how Word reads the copy's table)."""
    return " ".join(c for row in table["rows"] for c in row if c)
