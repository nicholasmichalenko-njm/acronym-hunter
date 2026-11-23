"""4.59.0: a standards workbook says what it is, on its Read me tab (UX decisions 134, 135 and 149; the shared shapes
page, section 1; release C of the plan for the workbook in the shared shape).

- The Read me tab is the first tab of a workbook the app makes: A1 "This workbook is", B1 the kind (Global Standards,
  Effort Standards or Program Standards, with a drop-down); A2 "It belongs to", B2 the effort's or program's name;
  then the text the Stationkeeper Macros write, word for word (SKW_Workbooks.WriteReadMe, 1.25.0 on); then, at the
  bottom, "Made by" and "Format". The About tab goes.
- A Read me tab already in the workbook (made by the macros, or typed by a person) is kept as it is; only its
  "Made by" and "Format" lines are brought up to date. People may move the tab: it is not moved back.
- Reading: the two lines are read in either form (the words and the value side by side, or "This workbook is: Effort
  Standards" in one cell), in any letter case. A workbook that says it is the other kind is refused: one that says
  Effort Standards or Program Standards is not read as the Global Standards, one that says Global Standards is not read
  as an effort's or a program's. A workbook with no line is read as before (never refused for that alone).
Rules only (No AI); nothing leaves the PC."""

TAB = "Read me"
KIND_LINE = "This workbook is"
OWNER_LINE = "It belongs to"
GLOBAL, EFFORT, PROGRAM = "Global Standards", "Effort Standards", "Program Standards"
KINDS = (GLOBAL, EFFORT, PROGRAM)
# The text both tools write, word for word (the macros' WriteReadMe; the layout page).
TEXT = (
    "Stationkeeper and the Stationkeeper Macros both read and write this workbook. You can edit it in Excel.",
    "Free to change: the file's name; any row; the order of tabs and columns; colours and widths. You can add tabs and "
    "columns of your own; they are kept and never reach Word.",
    "Please do not change: the name of this tab; the name of any other tab; the first row of any tab (the column names).",
    "A blank cell means \"not set\". In an effort's workbook it means \"use the Global Standards value\".",
    "Only rows marked Approved are used in documents and templates. Draft rows are waiting for a Stationkeeper Admin.",
    "If something stops working: run \"Check this workbook\" from the Stationkeeper Macros menu or from Stationkeeper. "
    "It says what is wrong in plain words.",
    "Close the workbook when you are done. While it is open in Excel, neither tool can save to it; they keep your change "
    "and save it when the file is free.",
)
MADE_BY, FORMAT_LINE = "Made by", "Format"


def _norm(v):
    return " ".join(str(v or "").replace(":", " ").split()).casefold()


def _kind_word(v):
    n = _norm(v)
    return next((k for k in KINDS if k.casefold() == n), "")


def _lines(book):
    """The Read me tab of a reading (standardsbook.read) as rows of cell values; [] when there is none."""
    for sheet, head in (book.get("headers") or {}).items():
        if str(sheet).strip().casefold() == TAB.casefold():
            rows = [list(head)]
            for r in (book.get("sheets") or {}).get(sheet) or []:
                rows.append([r.get(h) for h in head])
            return rows
    return []


def _value(rows, words):
    w = words.casefold()
    for row in rows:
        for i, cell in enumerate(row):
            n = _norm(cell)
            if n == w:
                nxt = next((c for c in row[i + 1:] if str(c or "").strip()), "")
                return str(nxt or "").strip()
            if n.startswith(w + " "):
                return str(cell).split(":", 1)[-1].strip() if ":" in str(cell) else str(cell)[len(words):].strip()
    return None


def kind_of(book):
    """(kind, owner) a reading says on its Read me tab: kind is one of KINDS or "" (no line, or a word not one of the
    three); owner is the name beside "It belongs to" or ""."""
    rows = _lines(book)
    return _kind_word(_value(rows, KIND_LINE)), (_value(rows, OWNER_LINE) or "")


def has_tab(book):
    return bool(_lines(book))


def refused(book, expect):
    """The plain-words reason a reading is not taken as expect (GLOBAL, or "effort" for an effort's or a program's),
    or None. Only a line that says the other kind refuses."""
    kind, _owner = kind_of(book)
    if expect == GLOBAL and kind in (EFFORT, PROGRAM):
        return (f"This workbook says it is {'an' if kind == EFFORT else 'a'} {kind} workbook (the line \"{KIND_LINE}\" "
                f"on its Read me tab). It is not read as the Global Standards, and nothing is written over it.")
    if expect == "effort" and kind == GLOBAL:
        return (f"This workbook says it is the Global Standards (the line \"{KIND_LINE}\" on its Read me tab). It is not "
                "read as this effort's workbook, and nothing is written over it.")
    return None


def write(wb, kind, owner, fmt, made_by):
    """The Read me tab in an openpyxl workbook: made as the first tab when there is none, kept as it is when there is
    one (only its Made by and Format lines are set). The About tab is taken out."""
    from openpyxl.styles import Font
    from openpyxl.worksheet.datavalidation import DataValidation
    if "About" in wb.sheetnames:
        wb.remove(wb["About"])
    name = next((s for s in wb.sheetnames if s.strip().casefold() == TAB.casefold()), None)
    if name is None:
        ws = wb.create_sheet(TAB, 0)
        ws["A1"], ws["B1"] = KIND_LINE, kind
        ws["A2"], ws["B2"] = OWNER_LINE, owner or ""
        ws["B2"].number_format = "@"
        ws["A1"].font = ws["A2"].font = Font(bold=True)
        dv = DataValidation(type="list", formula1='"' + ",".join(KINDS) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add("B1")
        for i, line in enumerate(TEXT):
            ws.cell(4 + i, 1).value = line
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 40
    else:
        ws = wb[name]
    found = {}
    for row in ws.iter_rows():
        n = _norm(row[0].value) if row else ""
        if n in (MADE_BY.casefold(), FORMAT_LINE.casefold()):
            found[n] = row[0].row
    nxt = ws.max_row + (2 if not found else 1)
    for words, value in ((MADE_BY, made_by), (FORMAT_LINE, fmt)):
        r = found.get(words.casefold())
        if r is None:
            r, nxt = nxt, nxt + 1
        ws.cell(r, 1).value, ws.cell(r, 2).value = words, value
    return ws
