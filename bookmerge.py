"""4.56.2: a standards workbook that changed while the app's own changes were waiting (the one-system rule: the app and
the Stationkeeper Macros write the same workbook, and so do people in Excel).

Before 4.56.2 the app wrote its waiting changes over the workbook without reading it, so a row changed in Excel or by a
macro in between was lost with no word. Now the app reads first and merges row by row, three ways:
- base: the workbook as the app last read or wrote it (a copy kept in the config folder, base_path);
- mine: the workbook the app would write now;
- theirs: the workbook as it is.
A row only they changed is taken from the workbook; a row only the app changed is kept; a row changed in both places
keeps the workbook's values and is reported by name; a row is removed only when one side removed it and the other left
it as it was. With no base (the first time, or a base that cannot be read) nothing is removed and a row that differs
keeps the workbook's values and is reported.

Rows are matched by each sheet's key column (Name on most; Phrase, Word or Key on some lists), with Volume beside it in
an effort's workbook. Rules only (No AI); nothing leaves the PC."""
import hashlib, json, os, shutil

import diag

IGNORE = ("ID", "Changed")                       # the app fills these; they never make a row "changed"
KEYS = {"Phrases": "Phrase", "Suggestion rules": "Phrase", "Compliance words": "Word", "Piece types": "Key"}
APP_ONLY = ("About", "Columns")                  # the app's own sheets: never merged row by row
VOLUME = "Volume"
BASES = "book_base"


def base_path(config_dir, book):
    """Where the copy of a workbook as last read or written is kept: the config folder, one file per workbook."""
    tag = hashlib.sha256(os.path.normcase(os.path.abspath(book)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(config_dir, BASES, tag + ".xlsx")


def keep_base(config_dir, book):
    """After a read or a write: the workbook as it is now is the base for the next merge."""
    try:
        b = base_path(config_dir, book)
        os.makedirs(os.path.dirname(b), exist_ok=True)
        shutil.copyfile(book, b + ".tmp")
        os.replace(b + ".tmp", b)
        return True
    except OSError:
        diag.swallowed()
        return False


def _norm(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).strip()
    return t.upper() if t.upper() in ("TRUE", "FALSE") else t


def _sig(row, ignore):
    return json.dumps(sorted((k, _norm(v)) for k, v in row.items() if k and k not in ignore and _norm(v) != ""))


def _keyed(rows, cols):
    """{key: row} in the sheet's order; a key used twice gets its count, so no row is dropped."""
    out, seen = {}, {}
    for r in rows or []:
        k = tuple(_norm(r.get(c)) for c in cols)
        n = seen.get(k, 0)
        seen[k] = n + 1
        out[k + ((n,) if n else ())] = r
    return out


def _label(sheet, key):
    return f"{sheet}: " + ", ".join(str(x) for x in key if x not in ("", None))


def merge(base, mine, theirs, readonly=None):
    """The merged reading (the shape standardsbook.read gives) and a report {"taken": n, "both": [text]}.
    base may be None. readonly: {sheet: columns only the app fills}, left out when rows are compared."""
    out = {"sheets": {}, "headers": {}, "problems": []}
    rep = {"taken": 0, "both": []}
    for sheet, m_rows in mine["sheets"].items():
        m_head = list(mine["headers"].get(sheet) or [])
        if sheet in APP_ONLY or sheet not in theirs["sheets"]:
            out["sheets"][sheet], out["headers"][sheet] = list(m_rows), m_head
            continue
        t_head = list(theirs["headers"].get(sheet) or [])
        head = m_head + [h for h in t_head if h and h not in m_head]
        key = KEYS.get(sheet, "Name")
        if key not in head:                          # a sheet with no key column cannot be matched: the app's stands
            out["sheets"][sheet], out["headers"][sheet] = list(m_rows), m_head
            continue
        cols = [key] + ([VOLUME] if VOLUME in head else [])
        ign = tuple(IGNORE) + tuple((readonly or {}).get(sheet) or ())
        has_base = base is not None and sheet in (base.get("sheets") or {})
        B = _keyed(base["sheets"][sheet], cols) if has_base else {}
        M, T = _keyed(m_rows, cols), _keyed(theirs["sheets"][sheet], cols)
        rows = []
        for k, t in T.items():
            if not any(k[:len(cols)]):
                continue                             # a row with no name: the app never reads one
            m, b = M.get(k), B.get(k)
            if m is not None:
                if _sig(m, ign) == _sig(t, ign):
                    rows.append(m)
                elif b is not None and _sig(b, ign) == _sig(m, ign):
                    rows.append(t)
                    rep["taken"] += 1
                elif b is not None and _sig(b, ign) == _sig(t, ign):
                    rows.append(m)
                else:
                    rows.append(t)
                    rep["both"].append(_label(sheet, k))
            elif b is not None:                      # the app took the row out
                if _sig(b, ign) != _sig(t, ign):
                    rows.append(t)
                    rep["both"].append(_label(sheet, k))
            else:
                rows.append(t)
                rep["taken"] += 1
        for k, m in M.items():
            if k in T:
                continue
            b = B.get(k)
            if b is None:
                rows.append(m)                       # the app added it (or there is no base: nothing is removed)
            elif _sig(b, ign) != _sig(m, ign):
                rows.append(m)                       # taken out of the workbook, changed in the app: kept, and said
                rep["both"].append(_label(sheet, k))
            else:
                rep["taken"] += 1                    # taken out of the workbook, untouched here: it goes
        out["sheets"][sheet], out["headers"][sheet] = rows, head
    if "Columns" in out["sheets"]:                   # the columns the workbook names and the app's reading does not
        have = {(r.get("Sheet"), r.get("Column")) for r in out["sheets"]["Columns"]}
        out["sheets"]["Columns"] = list(out["sheets"]["Columns"]) + [
            r for r in theirs["sheets"].get("Columns", []) if (r.get("Sheet"), r.get("Column")) not in have]
    return out, rep


def said(what, rep):
    """The lines for the person: what was read first, and the rows changed in both places."""
    out = []
    if rep.get("taken"):
        out.append(f"{what} changed while your changes were waiting: {rep['taken']} row(s) were read from it "
                   "before yours were written.")
    both = rep.get("both") or []
    if both:
        more = f" and {len(both) - 4} more" if len(both) > 4 else ""
        out.append(f"Changed in both places, the workbook's kept ({what}): " + "; ".join(both[:4]) + more + ".")
    return out
