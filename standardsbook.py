"""The Company Standards workbook (4.7.0; claude/stationkeeper-team-library-files-decisions-2026-11-10.md): the values of
the Company Standards (Default) in one Excel workbook that people edit in Excel or in the app. The workbook is the
truth; production_standards.json and field_recipes.json are the app's cache of it, rebuilt from it.

One row per item, wide (decision 1):
- the organizing columns first: ID (hidden; the app fills it, so a rename keeps identity), Name, Category, Status
  (Draft, Approved, Retired: only Approved rows reach the standard, templates and the macros), Changed (who, when, in
  the app or in Excel), then where they apply: Used on, Set, Menu group, Show in menu, Notes, Tags, Owner;
- then the property columns, only those some row uses, in Excel groups that collapse (Font, Paragraph, Spacing,
  Indents, Borders and shading, Numbering, Other), the key columns frozen on the left;
- "Other Word settings" last: every property without a column of its own, as text, so nothing is lost.
Columns a person adds are kept both ways and never reach Word. The Columns sheet says what each column holds.

Sheets: Styles, Table looks, Table types, Heading numbering, List numbering, Page setups, Captions, Fonts allowed,
Settings (the base fonts, sizes and margins) and Fields (the field recipes). An effort's workbook has the same sheets
and holds only that effort's changes: a blank cell means the Company Standards (Default) value.

Rules only (No AI); nothing leaves the PC."""
import copy, datetime, getpass, json, os, re, uuid

import diag

ORG = ("ID", "Name", "Category", "Status", "Changed", "Used on", "Set", "Menu group", "Show in menu", "Notes", "Tags", "Owner")
OTHER = "Other Word settings"
VOLUME = "Volume"                            # 4.10.0: an effort's workbook only; blank means every volume
STATUSES = ("Approved", "Draft", "Retired")
GROUPS = ("Font", "Paragraph", "Spacing", "Indents", "Borders and shading", "Numbering", "Other")
_GROUP_OF = {"font": "Font", "size": "Font", "bold": "Font", "italic": "Font", "underline": "Font", "caps": "Font",
             "small_caps": "Font", "color": "Font", "hidden": "Font", "type": "Paragraph", "based_on": "Paragraph",
             "next": "Paragraph", "jc": "Paragraph", "align": "Paragraph", "keep_next": "Paragraph", "keep_lines": "Paragraph",
             "page_break_before": "Paragraph", "widow": "Paragraph", "valign": "Paragraph", "repeat": "Paragraph",
             "before": "Spacing", "after": "Spacing", "line": "Spacing", "line_rule": "Spacing", "left": "Indents",
             "right": "Indents", "first": "Indents", "hanging": "Indents", "tabs": "Indents", "number_at": "Numbering",
             "text_at": "Numbering", "fmt": "Numbering", "text": "Numbering", "restart": "Numbering", "level": "Numbering",
             "fill": "Borders and shading", "shading": "Borders and shading"}
_FIXED = ("used_on",)                     # a style's Used on is an organizing column, not a property
# (sheet, path in the standard, shape, the field that names a row)
SHEETS = (("Styles", ("style_defs",), "map", None), ("Table looks", ("row_types",), "map", None),
          ("Table types", ("table_types",), "map", None), ("Heading numbering", ("heading_numbering", "levels"), "list", "style"),
          ("List numbering", ("list_numbering", "lists"), "lists", None), ("Page setups", ("page_setups",), "map", None),
          ("Captions", ("captions",), "list", None), ("Fonts allowed", ("fonts",), "map", None))
SETTINGS = "Settings"
FIELDS = "Fields"
COLUMNS = "Columns"
ABOUT = "About"
FORMAT = 2                                   # formats.py "Company Standards workbook" (2: 4.10.0, Volume, Theme, Suggestion rules)
FIELD_COLS = (("Field code(s)", "codes"), ("Text between", "between"), ("What it does", "note"), ("Where it goes", "where"),
              ("Use case", "use_case"), ("Bookmark it needs", "bookmark"), ("What the bookmark spans", "spans"),
              ("Style it reads", "style"), ("Depends on", "depends"), ("Sample result", "sample"))
SETTING_ROWS = (("heading_numbering.on", "Heading numbering on"), ("list_numbering.on", "List numbering on"))


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _label(key):
    try:
        import libstyle as LS
        lab = dict((k, n) for k, n, _t in LS.PROPS)
    except Exception:  # noqa: BLE001
        lab = {}
    out = lab.get(key) or key.replace("_", " ").replace(".", ": ").strip().capitalize()
    return out + " (value)" if out in ORG or out == OTHER else out


def group_of(key):
    k = key.split(".")[0]
    if k.startswith("border") or k in ("edges", "fill", "shading"):
        return "Borders and shading"
    return _GROUP_OF.get(k, "Other")


# ------------------------------------------------------------------ cells
def to_cell(v):
    """A value as a cell: numbers, words and yes/no as they are; lists and tables as text Excel shows and keeps."""
    if v is None:
        return None
    if isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def from_cell(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str):
        t = v.strip()
        if t[:1] in "[{":
            try:
                return json.loads(t)
            except ValueError:
                return v
        if t.upper() in ("TRUE", "FALSE"):
            return t.upper() == "TRUE"
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _flat(d, prefix=""):
    """{prop: value} with nested tables as "edges.top" keys (one level; deeper stays a cell of its own)."""
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict) and k not in ("override", "rules") and all(not isinstance(x, dict) for x in v.values()):
            for k2, v2 in v.items():
                out[f"{prefix}{k}.{k2}"] = v2
        else:
            out[prefix + k] = v
    return out


def _unflat(flat):
    out = {}
    for k, v in flat.items():
        if "." in k:
            a, b = k.split(".", 1)
            out.setdefault(a, {})
            if isinstance(out[a], dict):
                out[a][b] = v
        else:
            out[k] = v
    return out


def _dig(d, path):
    for p in path:
        d = (d or {}).get(p) if isinstance(d, dict) else None
    return d


def _put(d, path, v):
    for p in path[:-1]:
        d = d.setdefault(p, {})
    d[path[-1]] = v


# ------------------------------------------------------------------ the standard as rows
def rows_of(company, sheet):
    """[(name, {prop: value})] for one sheet, from the standard (the company layer, or an effort's layer)."""
    spec = next(s for s in SHEETS if s[0] == sheet)
    _n, path, shape, name_key = spec
    data = _dig(company, path)
    out = []
    if shape == "map":
        for name, props in (data or {}).items():
            out.append((str(name), _flat(props if isinstance(props, dict) else {"value": props})))
    elif shape == "list":
        for k, props in enumerate(data or []):
            if not isinstance(props, dict):
                continue
            nm = props.get(name_key) if name_key else " ".join(str(props.get(x) or "") for x in ("label", "part")).strip()
            out.append((str(nm or f"Row {k + 1}"), _flat(props)))
    elif shape == "lists":
        for lst in data or []:
            for lv, props in enumerate(lst.get("levels") or [], 1):
                out.append((f"{lst.get('name', 'List')} {lv}", dict(_flat(props), **{"list": lst.get("name", ""), "level": lv})))
    return out


def _clean(props):
    """A row's values without the empty ones (a blank cell and a value never set are the same)."""
    return {k: v for k, v in (props or {}).items() if v is not None and v != ""}


def put_rows(company, sheet, rows):
    """Write a sheet's [(name, {prop: value})] back into the standard (a new copy); rows keep the workbook's order."""
    spec = next(s for s in SHEETS if s[0] == sheet)
    _n, path, shape, _name_key = spec
    c = copy.deepcopy(company)
    if shape == "map":
        _put(c, path, {name: _unflat(props) for name, props in rows})
    elif shape == "list":
        _put(c, path, [_unflat(props) for _name, props in rows])
    elif shape == "lists":
        lists = []
        for _name, props in rows:
            p = dict(props)
            ln = p.pop("list", "") or "List"
            p.pop("level", None)
            if not lists or lists[-1]["name"] != ln:
                lists.append({"name": ln, "levels": []})
            lists[-1]["levels"].append(_unflat(p))
        _put(c, path, lists)
    return c


# ------------------------------------------------------------------ writing
def _meta(company, sheet):
    return ((company.get("book_meta") or {}).get(sheet) or {})


def _columns(rows, known=()):
    """The property columns some row uses, by group then first use."""
    seen = []
    for _n, props in rows:
        for k, v in props.items():
            if k not in seen and k not in _FIXED and v is not None:
                seen.append(k)
    for k in known:
        if k not in seen:
            seen.append(k)
    return sorted(seen, key=lambda k: (GROUPS.index(group_of(k)), seen.index(k)))


def book_rows(company, recipes=None):
    """{sheet: [row dict by column]} and {sheet: [property keys]}: what the workbook holds for this standard."""
    sheets, cols = {}, {}
    for sheet, _p, _s, _k in SHEETS:
        meta = _meta(company, sheet)
        rows = rows_of(company, sheet)
        held = [(n, p) for n, p in (meta.get("_held") or {}).items()]            # Draft and Retired rows wait here
        allrows = rows + [(n, p) for n, p in held if n not in dict(rows)]
        keys = _columns(allrows)
        cols[sheet] = keys
        out = []
        for name, props in allrows:
            m = meta.get(name) or {}
            r = {"ID": m.get("id") or uuid.uuid4().hex[:10], "Name": name, "Category": m.get("category", ""),
                 "Status": m.get("status") or ("Approved" if name not in dict(held) else "Draft"),
                 "Changed": m.get("changed", ""), "Used on": props.get("used_on") or m.get("used_on", ""),
                 "Set": m.get("set", ""), "Menu group": m.get("menu_group", ""), "Show in menu": m.get("show_in_menu", ""),
                 "Notes": m.get("notes", ""), "Tags": m.get("tags", ""), "Owner": m.get("owner", "")}
            for k in keys:
                r[k] = props.get(k)
            r[OTHER] = m.get("other", "")
            r.update(m.get("own") or {})
            out.append(r)
        sheets[sheet] = out
    sheets[SETTINGS] = [{"Name": k, "Value": v} for k, v in sorted((company.get("variables") or {}).items())] + \
        [{"Name": lab, "Value": _dig(company, key.split("."))} for key, lab in SETTING_ROWS
         if _dig(company, key.split(".")) is not None]                 # an effort's book: only what it sets
    fr = []
    for r in recipes or []:
        x = r.get("extra") or {}
        row = {"ID": r.get("id", ""), "Name": r.get("name", ""), "Category": x.get("category", r.get("where", "")),
               "Status": x.get("status", "Approved"), "Changed": x.get("changed", ""), "Menu group": x.get("menu_group", ""),
               "Show in menu": x.get("show_in_menu", ""), "Notes": x.get("notes", ""), "Tags": x.get("tags", ""),
               "Owner": x.get("owner", ""), OTHER: x.get("other", "")}
        for lab, key in FIELD_COLS:
            v = r.get(key)
            row[lab] = " | ".join(v) if isinstance(v, list) else (v or "")
        if not row.get("Sample result") and r.get("codes"):              # worked out on the sample page (fieldpreview)
            try:
                import fieldpreview as FP
                txt, known = FP.recipe(r["codes"], r.get("between", ""), label=FP.label_of(r["codes"]))
                row["Sample result"] = txt if known else ""
            except Exception:  # noqa: BLE001
                diag.swallowed()
        row.update(x.get("own") or {})
        fr.append(row)
    sheets[FIELDS] = fr
    return sheets, cols


def _with_volumes(sheets, cols, volumes):
    """4.10.0: an effort's workbook: the every-volume rows (Volume blank), then each volume's own rows."""
    for sheet, _p, _s, _k in SHEETS:
        for r in sheets[sheet]:
            r[VOLUME] = ""
    for r in sheets[SETTINGS]:
        r[VOLUME] = ""
    for label, lay in volumes:
        s2, c2 = book_rows(lay)
        for sheet, _p, _s, _k in SHEETS:
            for r in s2[sheet]:
                r[VOLUME] = label
                sheets[sheet].append(r)
            seen = cols[sheet] + [k for k in c2[sheet] if k not in cols[sheet]]
            cols[sheet] = sorted(seen, key=lambda k: (GROUPS.index(group_of(k)), seen.index(k)))
        for r in s2[SETTINGS]:
            r[VOLUME] = label
            sheets[SETTINGS].append(r)
    return sheets, cols


def write(path, company, recipes=None, own_cols=None, lists=None, volumes=None):
    """Write the workbook (to a .tmp, then in place). own_cols: {sheet: [column names people added]}, kept. volumes
    (an effort's workbook): [(volume name, its own layer)], written as rows with a Volume column. Raises
    PermissionError when Excel has it open; the caller waits and says so."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    sheets, cols = book_rows(company, recipes)
    org = ORG
    if volumes is not None:
        sheets, cols = _with_volumes(sheets, cols, volumes)
        org = ORG[:2] + (VOLUME,) + ORG[2:]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    head = Font(bold=True)
    fill = PatternFill("solid", fgColor="DCE6F1")
    colsheet = [("Sheet", "Column", "Key", "Group", "What it holds")]
    for sheet, _p, _s, _k in SHEETS:
        ws = wb.create_sheet(sheet)
        own = list((own_cols or {}).get(sheet) or [])
        keys = cols[sheet]
        header = list(org) + [_label(k) for k in keys] + [OTHER] + own
        ws.append(header)
        for r in sheets[sheet]:
            ws.append([to_cell(r.get(h)) for h in org] + [to_cell(r.get(k)) for k in keys] + [to_cell(r.get(OTHER))]
                      + [to_cell(r.get(h)) for h in own])
        _dress(ws, header, head, fill, get_column_letter)
        start = len(org) + 1                                     # the property columns, grouped
        for g in GROUPS:
            idx = [start + i for i, k in enumerate(keys) if group_of(k) == g]
            if idx:
                ws.column_dimensions.group(get_column_letter(idx[0]), get_column_letter(idx[-1]), outline_level=1)
        for i, k in enumerate(keys):
            colsheet.append((sheet, _label(k), k, group_of(k), ""))
        for h in own:
            colsheet.append((sheet, h, "", "Yours", "A column you added: kept, never sent to Word"))
    ws = wb.create_sheet(SETTINGS)
    sh = ["Name", VOLUME, "Value", "Notes"] if volumes is not None else ["Name", "Value", "Notes"]
    ws.append(sh)
    for r in sheets[SETTINGS]:
        ws.append([r["Name"]] + ([r.get(VOLUME, "")] if volumes is not None else []) + [to_cell(r["Value"]), ""])
    _dress(ws, sh, head, fill, get_column_letter, freeze="B2")
    ws = wb.create_sheet(FIELDS)
    own = list((own_cols or {}).get(FIELDS) or [])
    header = ["ID", "Name", "Category", "Status", "Changed"] + [lab for lab, _k in FIELD_COLS] + \
        ["Menu group", "Show in menu", "Notes", "Tags", OTHER] + own
    ws.append(header)
    for r in sheets[FIELDS]:
        ws.append([to_cell(r.get(h)) for h in header])
    _dress(ws, header, head, fill, get_column_letter)
    if volumes is None:                                         # 4.10.0: the theme's colors and fonts (the team's book)
        import themebook as TB
        ws = wb.create_sheet(TB.SHEET)
        ws.append(list(TB.COLS))
        for r in TB.rows(company):
            ws.append([r[c] for c in TB.COLS])
        _dress(ws, list(TB.COLS), head, fill, get_column_letter, freeze="B2")
        ws.column_dimensions["C"].width = 48
    for sheet, (cols, rows) in (lists or {}).items():          # 4.7.1: the team's small lists (listsbook)
        ws = wb.create_sheet(sheet)
        own = [h for h in (own_cols or {}).get(sheet) or [] if h not in cols]
        ws.append(list(cols) + own)
        for r in rows:
            ws.append([to_cell(r.get(c)) for c in cols] + [to_cell((r.get("_own") or {}).get(h)) for h in own])
        _dress(ws, list(cols) + own, head, fill, get_column_letter, freeze="B2")
    ws = wb.create_sheet(ABOUT)
    for row in (("What", "Value"), ("Format", FORMAT), ("Made by", "Stationkeeper"),
                ("How to use it", "Edit values here or in the app; the app reads what changed and writes what it changes. "
                 "A blank cell in an effort's workbook means the Company Standards (Default) value; a blank Volume means "
                 "every volume, a volume's name means that volume only. Only Approved rows "
                 "reach templates and the macros. Columns you add are kept and never reach Word.")):
        ws.append(list(row))
    ws = wb.create_sheet(COLUMNS)
    for row in colsheet:
        ws.append(list(row))
    for c in ws[1]:
        c.font = head
    tmp = path + ".tmp.xlsx"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    wb.save(tmp)
    try:
        os.replace(tmp, path)
    except PermissionError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return path


def _dress(ws, header, head, fill, letter, freeze="C2"):
    for c in ws[1]:
        c.font = head
        c.fill = fill
    for i, h in enumerate(header, 1):
        ws.column_dimensions[letter(i)].width = max(10, min(40, len(str(h)) + 4))
    if header and header[0] == "ID":
        ws.column_dimensions["A"].hidden = True
    ws.freeze_panes = freeze
    for row in ws.iter_rows(min_row=2):                         # "=caption_font" stays words, never a formula
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                c.data_type = "s"


# ------------------------------------------------------------------ reading
def read(path):
    """{"sheets": {sheet: [row dict]}, "headers": {sheet: [header]}, "problems": [text]}. A sheet that cannot be read
    is reported; nothing is half-read (the caller keeps its last good reading)."""
    import openpyxl
    out = {"sheets": {}, "headers": {}, "problems": []}
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    except Exception as e:  # noqa: BLE001
        out["problems"].append(f"The workbook could not be opened ({type(e).__name__}).")
        return out
    try:
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(h).strip() if h is not None else "" for h in rows[0]]
            out["headers"][ws.title] = header
            got = []
            for vals in rows[1:]:
                if vals is None or all(v is None or (isinstance(v, str) and not v.strip()) for v in vals):
                    continue
                got.append({h: v for h, v in zip(header, vals) if h})
            out["sheets"][ws.title] = got
    finally:
        wb.close()
    return out


def split_volumes(book, labels=()):
    """4.10.0: an effort's workbook read as one reading per volume: {"": the every-volume rows, name: that volume's rows}.
    labels: volume names to include even with no rows (a volume whose rows were all taken out)."""
    found = {""} | {str(x) for x in labels}
    for sheet, rows in book["sheets"].items():
        if VOLUME in (book["headers"].get(sheet) or []):
            found |= {" ".join(str(r.get(VOLUME) or "").split()) for r in rows}
    out = {}
    for lab in found:
        b = {"sheets": {}, "headers": book["headers"], "problems": list(book.get("problems") or [])}
        for sheet, rows in book["sheets"].items():
            if VOLUME in (book["headers"].get(sheet) or []):
                b["sheets"][sheet] = [r for r in rows if " ".join(str(r.get(VOLUME) or "").split()) == lab]
            else:
                b["sheets"][sheet] = rows
        out[lab] = b
    return out


def _key_map(book, sheet):
    """Header -> property key for a sheet, from the Columns sheet (the app's own labels as a fallback)."""
    m = {}
    for r in book["sheets"].get(COLUMNS, []):
        if r.get("Sheet") == sheet and r.get("Column") and r.get("Key"):
            m[str(r["Column"]).strip()] = str(r["Key"]).strip()
    return m


def apply(company, recipes, book, user=None, removed_answer=None):
    """The standard and recipes the workbook says, from a reading. Returns {"company", "recipes", "own_cols",
    "changed": [(sheet, name)], "removed_cols": [(sheet, key)], "problems"}. A property column that disappeared since
    the last write is listed in removed_cols; removed_answer "drop" takes it off every row, "keep" (the default until
    the person answers) keeps the values as they were."""
    c = copy.deepcopy(company)
    meta_all = copy.deepcopy(c.get("book_meta") or {})
    who = user or getpass.getuser()
    res = {"changed": [], "removed_cols": [], "problems": list(book.get("problems") or []), "own_cols": {}}
    if res["problems"]:
        res.update(company=company, recipes=recipes)
        return res
    for sheet, _p, _s, _k in SHEETS:
        if sheet not in book["sheets"]:
            continue
        header = book["headers"].get(sheet) or []
        kmap = _key_map(book, sheet)
        prop_cols = [h for h in header if h in kmap]
        own = [h for h in header if h and h not in ORG and h not in (OTHER, VOLUME) and h not in kmap]
        res["own_cols"][sheet] = own
        before = dict(rows_of(c, sheet))
        old_meta = meta_all.get(sheet) or {}
        last_cols = set((old_meta.get("_cols") or []))
        here = {kmap[h] for h in prop_cols}
        gone = [k for k in last_cols if k not in here]
        for k in gone:
            res["removed_cols"].append((sheet, k))
        new_rows, held, meta = [], {}, {"_cols": sorted(set(kmap.values()))}
        id_name = {m.get("id"): n for n, m in old_meta.items() if isinstance(m, dict) and m.get("id")}
        for r in book["sheets"][sheet]:
            name = str(r.get("Name") or "").strip()
            if not name:
                continue
            props = {}
            rid = str(r.get("ID") or "").strip()
            was = id_name.get(rid)
            base = dict(before.get(was or name) or {})
            for h in prop_cols:
                props[kmap[h]] = from_cell(r.get(h))
            for k in gone:                                          # a column people took out
                if removed_answer == "drop":
                    continue
                if k in base:
                    props[k] = base[k]
            other = r.get(OTHER)
            if other:
                try:
                    extra = json.loads(other) if str(other).strip()[:1] == "{" else {}
                    for k, v in extra.items():
                        props.setdefault(k, v)
                except ValueError:
                    res["problems"].append(f"{sheet}, {name}: Other Word settings is not readable; kept as it was.")
            props = _clean(props)
            if sheet == "Styles" and r.get("Used on"):
                props["used_on"] = str(r["Used on"])
            status = str(r.get("Status") or "Approved").strip().capitalize()
            status = status if status in STATUSES else "Approved"
            old_props = _clean(before.get(was or name))
            m = {"id": rid or uuid.uuid4().hex[:10], "category": r.get("Category") or "", "status": status,
                 "changed": r.get("Changed") or "", "set": r.get("Set") or "", "menu_group": r.get("Menu group") or "",
                 "show_in_menu": r.get("Show in menu") or "", "notes": r.get("Notes") or "", "tags": r.get("Tags") or "",
                 "owner": r.get("Owner") or "", "other": other or "", "own": {h: r.get(h) for h in own if r.get(h) is not None}}
            if props != old_props or was not in (None, name):
                m["changed"] = f"{who} {_now()} (Excel)"
                res["changed"].append((sheet, name))
            meta[name] = m
            if status == "Approved":
                new_rows.append((name, props))
            else:
                held[name] = props
        meta["_held"] = held
        meta_all[sheet] = meta
        if new_rows or _dig(c, _p) not in (None, [], {}):          # an empty sheet never empties what was not there
            c = put_rows(c, sheet, new_rows)
    st = book["sheets"].get(SETTINGS)
    if st:
        labs = {lab: key for key, lab in SETTING_ROWS}
        var = dict(c.get("variables") or {})
        for r in st:
            n = str(r.get("Name") or "").strip()
            if not n:
                continue
            v = from_cell(r.get("Value"))
            if n in labs:
                if v is not None:
                    _put(c, labs[n].split("."), bool(v))
            elif v is None:
                if var.pop(n, None) not in (None, ""):          # blank: not set here (the default below holds)
                    res["changed"].append((SETTINGS, n))
            elif var.get(n) != v:
                var[n] = v
                res["changed"].append((SETTINGS, n))
        c["variables"] = var
    c["book_meta"] = meta_all
    th = book["sheets"].get("Theme")
    if th is not None:                                          # 4.10.0: the theme's colors and fonts
        import themebook as TB
        t, probs, names = TB.apply(c, th)
        res["problems"] += probs
        if t is not None:
            c["theme"] = t
            res["changed"] += [(TB.SHEET, n) for n in names]
    new_recipes = recipes
    fr = book["sheets"].get(FIELDS)
    if fr is not None:
        header = book["headers"].get(FIELDS) or []
        known = {"ID", "Name", "Category", "Status", "Changed", "Menu group", "Show in menu", "Notes", "Tags", OTHER} | \
            {lab for lab, _k in FIELD_COLS}
        own = [h for h in header if h and h not in known]
        res["own_cols"][FIELDS] = own
        old = {r.get("id"): r for r in recipes or []}
        new_recipes = []
        for r in fr:
            name = str(r.get("Name") or "").strip()
            if not name:
                continue
            x = {"category": r.get("Category") or "", "status": str(r.get("Status") or "Approved"),
                 "changed": r.get("Changed") or "", "menu_group": r.get("Menu group") or "",
                 "show_in_menu": r.get("Show in menu") or "", "notes": r.get("Notes") or "", "tags": r.get("Tags") or "",
                 "other": r.get(OTHER) or "", "own": {h: r.get(h) for h in own if r.get(h) is not None}}
            rec = {"id": str(r.get("ID") or "") or uuid.uuid4().hex[:10], "name": name, "extra": x}
            for lab, key in FIELD_COLS:
                v = r.get(lab)
                rec[key] = [s.strip() for s in str(v).split("|") if s.strip()] if key == "codes" else (str(v) if v is not None else "")
            o = old.get(rec["id"])
            if o is None or any((o.get(k) or ("" if k != "codes" else [])) != rec[k] for _l, k in FIELD_COLS if k != "sample") \
                    or o.get("name") != name:                    # Sample result is worked out when blank: not a change
                x["changed"] = f"{who} {_now()} (Excel)"
                res["changed"].append((FIELDS, name))
            new_recipes.append(rec)
    res.update(company=c, recipes=new_recipes)
    return res


def stamp_app_changes(old_company, new_company, user=None):
    """Mark the rows the app changed (Changed: who, when, in the app) in new_company's book_meta. Returns the names."""
    who = user or getpass.getuser()
    meta_all = new_company.setdefault("book_meta", {})
    out = []
    for sheet, _p, _s, _k in SHEETS:
        a, b = dict(rows_of(old_company, sheet)), dict(rows_of(new_company, sheet))
        meta = meta_all.setdefault(sheet, {})
        for name, props in b.items():
            if _clean(a.get(name)) != _clean(props):
                meta.setdefault(name, {})["changed"] = f"{who} {_now()} (app)"
                out.append((sheet, name))
    return out


def row_hashes(company):
    """{"sheet/name": fingerprint} of every row's values, to tell which rows the app changed since the last write."""
    import hashlib
    out = {}
    for sheet, _p, _s, _k in SHEETS:
        for name, props in rows_of(company, sheet):
            out[f"{sheet}/{name}"] = hashlib.sha256(json.dumps(_clean(props), sort_keys=True, default=str).encode()).hexdigest()[:12]
    return out


def stamp_since(company, last_hashes, user=None):
    """Changed (who, when, in the app) on every row whose values differ from last_hashes. Returns the row keys."""
    who = user or getpass.getuser()
    meta_all = company.setdefault("book_meta", {})
    out = []
    for key, h in row_hashes(company).items():
        if last_hashes and last_hashes.get(key) != h:
            sheet, name = key.split("/", 1)
            meta_all.setdefault(sheet, {}).setdefault(name, {})["changed"] = f"{who} {_now()} (app)"
            out.append(key)
    return out


def remember_cols(company):
    """After a write: the property columns each sheet now has, so a column people take out is noticed."""
    meta_all = company.setdefault("book_meta", {})
    _sheets, cols = book_rows(company)
    for sheet, keys in cols.items():
        meta_all.setdefault(sheet, {})["_cols"] = sorted(keys)
    return company


def conflict_copies(path):
    """OneDrive's and SharePoint's copies of the workbook ("Company Standards-PCNAME.xlsx"): reported, never read."""
    d, base = os.path.dirname(path), os.path.splitext(os.path.basename(path))[0]
    try:
        return sorted(f for f in os.listdir(d) if f.lower().endswith(".xlsx") and f != os.path.basename(path)
                      and re.match(re.escape(base) + r"[-\s(]", f, re.I) and not f.startswith("~$"))
    except OSError:
        diag.swallowed()
        return []
