"""4.57.0 (the one-system rule; claude/stationkeeper-column-lists-for-both-tools.md): the app reads a standards workbook
under the plain column names, Word's own words and the plain cell forms, beside the names and forms it writes today.
The same standard written both ways reads to the same values. A workbook in a newer format is not read and never
written over. The app still writes today's names. Fictional values only."""
import copy, json, os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import banned as B
import bookshape as BS
import fieldrecipes as FR
import listsbook as LB
import prodrules as PRL
import standardsbook as SB
import teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def head(ws):
    return [c.value for c in ws[1]]


def rename(ws, old, new):
    h = head(ws)
    if old in h:
        ws.cell(1, h.index(old) + 1).value = new


def col(ws, name):
    h = head(ws)
    return h.index(name) + 1 if name in h else None


def drop(ws, name):
    c = col(ws, name)
    if c:
        ws.delete_cols(c)


def add(ws, name, values):
    c = ws.max_column + 1
    ws.cell(1, c).value = name
    for i, v in enumerate(values, 2):
        ws.cell(i, c).value = v


def names(ws):
    return [ws.cell(i, col(ws, "Name")).value for i in range(2, ws.max_row + 1)]


FMT = {v: k for k, v in BS._FMT.items()} | {"bullet": "Bullet"}
ALIGN = {"left": "Left", "center": "Centered", "right": "Right", "both": "Justified"}
PARTS = ("style_defs", "row_types", "table_types", "heading_numbering", "list_numbering", "page_setups", "captions", "fonts")


def plain(src, dst):
    """The workbook at src written again under the plain names, Word's words and the plain forms, with no Columns and
    no About sheet: what the macros or a person would make."""
    wb = openpyxl.load_workbook(src)
    for sheet, m in BS.NAMES.items():
        ws = wb[sheet]
        for new, old in m.items():
            if new != "Edge inside, vertical":
                rename(ws, old, new)
    for sheet, c, words in (("Heading numbering", "Number format", FMT), ("List numbering", "Number format", FMT),
                            ("Table looks", "Alignment", ALIGN), ("Table types", "Alignment", ALIGN), ("Styles", "Alignment", ALIGN),
                            ("Table looks", "Vertical alignment", {"top": "Top", "center": "Center", "bottom": "Bottom"}),
                            ("Page setups", "Orientation", {"portrait": "Portrait", "landscape": "Landscape"}),
                            ("Styles", "Line rule", {"exact": "Exactly", "atLeast": "At least"})):
        ws = wb[sheet]; k = col(ws, c)
        for i in range(2, ws.max_row + 1):
            if k and ws.cell(i, k).value in words:
                ws.cell(i, k).value = words[ws.cell(i, k).value]
    ws = wb["Table looks"]
    for c in range(1, ws.max_column + 1):
        if str(ws.cell(1, c).value).startswith("Edge "):
            for i in range(2, ws.max_row + 1):
                v = ws.cell(i, c).value
                if isinstance(v, str) and v.startswith("["):
                    w, hx = json.loads(v); ws.cell(i, c).value = f"{w:g}, {hx}"
    looks = {n: i for i, n in enumerate(names(ws), 2)}
    tt = wb["Table types"]
    roles_c, over_c = col(tt, "Roles"), col(tt, "Override")
    roles = [json.loads(tt.cell(i, roles_c).value or "[]") for i in range(2, tt.max_row + 1)]
    overs = [json.loads(tt.cell(i, over_c).value or "{}") if over_c else {} for i in range(2, tt.max_row + 1)]
    tnames = names(tt)
    for label, role in BS.HAS:
        add(tt, label, [role in r for r in roles])
    kcol = {k: col(ws, {v: n for n, v in BS.NAMES["Table looks"].items() if n != "Edge inside, vertical"}.get(SB._label(k), SB._label(k)))
            for k in BS.KEYS["Table looks"]}
    for label, role in BS.LOOKS:
        cells = []
        for tn, ov in zip(tnames, overs):
            if role not in ov:
                cells.append(None); continue
            new = f"{role}, {tn}"                           # the type's own look, as a named row of Table looks
            r = ws.max_row + 1
            for c in range(1, ws.max_column + 1):
                ws.cell(r, c).value = ws.cell(looks[role], c).value
            ws.cell(r, col(ws, "Name")).value = new; ws.cell(r, col(ws, "ID")).value = None
            for k, v in SB._flat(ov[role]).items():
                x = "none" if v is None else (v if not isinstance(v, list) else f"{v[0]:g}, {v[1]}")
                ws.cell(r, kcol[k]).value = x
            cells.append(new)
        add(tt, label, cells)
    drop(tt, "Roles"); drop(tt, "Override"); drop(tt, "Name (value)")
    ps = wb["Page setups"]
    rc = col(ps, "Rules")
    rules = [json.loads(ps.cell(i, rc).value or "{}") if rc else {} for i in range(2, ps.max_row + 1)]
    for label, key in BS.SWITCHES:
        add(ps, label, [r.get(key) for r in rules])
    drop(ps, "Rules"); drop(ps, "Name (value)")
    fa = wb["Fonts allowed"]
    rows = [{h: fa.cell(i, c).value for c, h in enumerate(head(fa), 1)} for i in range(2, fa.max_row + 1)]
    wb.remove(fa); fa = wb.create_sheet("Fonts allowed")
    fa.append(["Name", "Status", "Used for", "Min size (pt)", "Max size (pt)", "RFP reference"])
    use_word = {"header_footer": "Header and footer"}
    for r in rows:
        for font in json.loads(r.get("Fonts") or "[]"):
            fa.append([font, "Approved", use_word.get(r["Name"], r["Name"].capitalize()), r.get("Min size"), r.get("Max size"), r.get("RFP reference")])
    wb.remove(wb["Columns"])
    for nm in ("About", "Read me"):                    # 4.59.0: the app writes Read me, not About
        if nm in wb.sheetnames:
            wb.remove(wb[nm])
    wb.save(dst)


def dump_old(src, dst):
    """4.58.0: the app writes the plain names now. A workbook under the names 4.57.0 wrote is made from a reading of
    src (bookshape turns a reading into those names), with a Columns sheet and an About sheet stating Format 2."""
    book = SB.read(src)
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for sheet, hdr in book["headers"].items():
        if sheet in ("About", "Columns"):
            continue
        ws = wb.create_sheet(sheet); ws.append(list(hdr))
        aside = {str(x).casefold() for x in (book.get("aside") or {}).get(sheet) or ()}
        for r in book["sheets"].get(sheet) or []:
            if str(r.get("Name") or "").casefold() not in aside:     # a look a type names: 4.57.0 had none
                ws.append([r.get(h) for h in hdr])
    ab = wb.create_sheet("About"); ab.append(["What", "Value"]); ab.append(["Format", 2])
    wb.create_sheet("Columns").append(["Sheet", "Column", "Key", "Group", "What it holds"])
    wb.save(dst)


def standard():
    c = PRL.load(tempfile.mkdtemp())["company"]
    c["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11, "jc": "both", "line": 13, "line_rule": "exact"},
                       "Heading 1": {"type": "paragraph", "size": 14, "bold": True, "jc": "center"}}
    for k, t in c["table_types"].items():
        t["name"] = k
    first = next(iter(c["table_types"]))
    c["table_types"][first]["override"] = {"header": {"fill": "D9E2F3", "edges": {"bottom": [1.5, "112233"]}}}
    c["table_types"][first]["roles"] = ["caption", "header", "body", "total", "note"]
    for k, p in c["page_setups"].items():
        p["name"] = k
    next(iter(c["page_setups"].values()))["rules"] = {"restart": True, "linked": False}
    for k, f in c["fonts"].items():
        f.update(fonts=["Arial", "Garamond"] if k == "body" else ["Arial"], min_size=9 if k == "table" else None, max_size=12 if k == "table" else None)
    c["heading_numbering"]["levels"][0]["fmt"] = "upperRoman"
    return c


def read_into(path, base):
    book = SB.read(path)
    res = SB.apply(copy.deepcopy(base), [], book)
    return res, book


tmp = tempfile.mkdtemp()
std = standard()
old_p, new_p = os.path.join(tmp, "old.xlsx"), os.path.join(tmp, "new.xlsx")
app_p = os.path.join(tmp, "app.xlsx")
SB.write(app_p, std, FR.load(tmp))
dump_old(app_p, old_p)
plain(old_p, new_p)
nh = {ws.title: head(ws) for ws in openpyxl.load_workbook(new_p).worksheets}
check("the second workbook really is under the plain names, with no Columns or About sheet", "Number format" in nh["Heading numbering"]
      and "Fmt" not in nh["Heading numbering"] and "Top margin (in)" in nh["Page setups"] and "Has header row" in nh["Table types"]
      and "Roles" not in nh["Table types"] and "Used for" in nh["Fonts allowed"] and "Columns" not in nh and "About" not in nh, nh.keys())
blank = copy.deepcopy(std)
for part in PARTS:
    blank[part] = {} if isinstance(std[part], dict) and part not in ("heading_numbering", "list_numbering") else \
        ({"on": std[part].get("on"), "levels" if part == "heading_numbering" else "lists": []} if isinstance(std[part], dict) else [])
ro, bo = read_into(old_p, blank)
rn, bn = read_into(new_p, blank)
check("neither reading reports a problem", not ro["problems"] and not rn["problems"], (ro["problems"], rn["problems"]))
import prodengine.pe.rules as R


def effect(c):
    """Table types as they come out: the kinds of row as a set, and each kind's full look in that type."""
    out = {}
    for k, t in c["table_types"].items():
        out[k] = {x: v for x, v in t.items() if x not in ("roles", "override")}
        out[k]["roles"] = sorted(t.get("roles") or [])
        out[k]["looks"] = {role: R.row_look(c, role, k) for role in c["row_types"]}
    return out


for part in PARTS:
    a, b = ro["company"].get(part), rn["company"].get(part)
    if part == "fonts":                                     # the plain shape has no row for a use with no font
        a = {k: v for k, v in a.items() if v.get("fonts")}
    if part == "table_types":
        a, b = effect(ro["company"]), effect(rn["company"])
    check(f"the plain names read to the same {part.replace('_', ' ')}", a == b,
          [k for k in (a if isinstance(a, dict) else {}) if (b or {}).get(k) != a[k]][:6] if isinstance(a, dict) else "differs")
c = rn["company"]
first = next(iter(std["table_types"]))
check("a type's own header look came through as its change to the header", c["table_types"][first]["override"] == std["table_types"][first]["override"]
      and R.row_look(c, "header", first)["fill"] == "D9E2F3", sorted(c["table_types"][first].get("override") or {}))
check("... the look a type names is kept on its sheet and is not made a kind of row", f"header, {first}" not in c["row_types"]
      and f"header, {first}" in (c["book_meta"]["Table looks"].get("_held") or {}), sorted(c["row_types"]))
check("the app's own plain workbook reads to the same table types as the old names", effect(read_into(app_p, blank)[0]["company"]) == effect(ro["company"]))
check("a reading under today's names is left as it is", bo["headers"]["Heading numbering"] == head(openpyxl.load_workbook(old_p)["Heading numbering"]))

# ---- both names on one sheet: the value under the older name wins; a blank older cell takes the plain one
both = os.path.join(tmp, "both.xlsx")
wb = openpyxl.load_workbook(old_p); ws = wb["Heading numbering"]
add(ws, "Number format", ["A, B, C"] * (ws.max_row - 1))
ws.cell(3, col(ws, "Fmt")).value = None
wb.save(both)
lv = read_into(both, blank)[0]["company"]["heading_numbering"]["levels"]
check("with both columns filled the older one wins; where it is blank the plain one is used", lv[0]["fmt"] == "upperRoman" and lv[1]["fmt"] == "upperLetter",
      (lv[0].get("fmt"), lv[1].get("fmt")))

# ---- through the team library: looks of the macros' own, Draft phrases, semicolons, and what the app writes
for left in (B.path(), os.path.join(os.path.dirname(B.path()), LB.WAITING)):       # nothing left by an earlier run
    if os.path.isfile(left):
        os.remove(left)
cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
S = {"team_library": ""}
d = PRL.load(cfg); d["company"] = standard(); PRL.save(cfg, d)
T.tick(cfg, S)
book = T.book_path(cfg, S)
n_looks = len(PRL.load(cfg)["company"]["row_types"])


def excel(edit):
    wb = openpyxl.load_workbook(book); edit(wb); wb.save(book)
    t = time.time() + excel.n; excel.n += 2; os.utime(book, (t, t))


excel.n = 2


def macro_rows(wb):
    ws = wb["Table looks"]
    for nm in ("number", "short"):
        r = ws.max_row + 1
        ws.cell(r, col(ws, "Name")).value = nm; ws.cell(r, col(ws, "Status")).value = "Approved"; ws.cell(r, col(ws, "Bold")).value = True
    add(ws, "Recognized by", [None] * (ws.max_row - 3) + ["digits", "1 to 3 words"])
    ph = wb["Phrases"]
    if "Status" not in head(ph):                     # 4.58.0: the app writes Status itself
        add(ph, "Status", [None] * (ph.max_row - 1))
    ph.append(["robust solution", "Avoid", "", "proposed by a writer", "Draft"])
    ph.append(["turnkey", "Banned", "", "no longer checked", "Retired"])
    ph.append(["best in class", "Banned", "", "", "Approved"])
    au = wb["Authors"]; au.append(["Pat Doe", "Kestrel; Osprey", "", ""])


excel(macro_rows)
T.tick(cfg, S)
c = PRL.load(cfg)["company"]
check("the macros' own looks are not made kinds of row in the app", len(c["row_types"]) == n_looks and "number" not in c["row_types"], sorted(c["row_types"]))
ph = [r["Phrase"] for r in B.load()]
check("a Draft or Retired phrase is not in the list the checks use; an Approved one is", "best in class" in ph and "robust solution" not in ph and "turnkey" not in ph, ph[-4:])
import authorlist as AL
pat = next((p for p in AL.AuthorList(os.path.join(cfg, AL.FILE)).load().people if p["name"] == "Pat Doe"), {})
check("efforts separated by semicolons are read as two efforts", pat.get("efforts") == ["Kestrel", "Osprey"], pat.get("efforts"))
d = PRL.load(cfg); d["company"]["style_defs"]["Body Text"]["size"] = 12; PRL.save(cfg, d)      # a change in the app
T.tick(cfg, S)
wb = openpyxl.load_workbook(book)
tl = wb["Table looks"]
check("after the app writes, the macros' looks and their own column are still on the sheet", {"number", "short"} <= set(names(tl))
      and "Recognized by" in head(tl) and tl.cell(names(tl).index("short") + 2, col(tl, "Recognized by")).value == "1 to 3 words", names(tl))
rows = {r[0].value: r[-1].value for r in wb["Phrases"].iter_rows(min_row=2)}
check("... the Draft and Retired phrases are still on the Phrases sheet with their Status", head(wb["Phrases"])[-1] == "Status"
      and rows.get("robust solution") == "Draft" and rows.get("turnkey") == "Retired" and rows.get("best in class") == "Approved", rows)
check("... and since 4.58.0 the app writes the plain column names", "Number format" in head(wb["Heading numbering"]) and "Fmt" not in head(wb["Heading numbering"]))

# ---- Fonts allowed, one row per font: read, and left on its sheet as the person has it
def fonts_plain(wb):
    wb.remove(wb["Fonts allowed"]); fa = wb.create_sheet("Fonts allowed")
    fa.append(["Name", "Status", "Used for", "Min size (pt)", "Max size (pt)"])
    for row in (("Georgia", "Approved", "Body", 10, 12), ("Verdana", "", "Tables", 8, 10), ("Tahoma", "Draft", "Body", None, None),
                ("Calibri", "Approved", "Any", None, None)):
        fa.append(list(row))


excel(fonts_plain)
T.tick(cfg, S)
f = PRL.load(cfg)["company"]["fonts"]
check("Fonts allowed with one row per font is read by use; a Draft font is not allowed", f["body"]["fonts"] == ["Georgia", "Calibri"]
      and f["table"]["fonts"] == ["Verdana", "Calibri"] and "Tahoma" not in f["body"]["fonts"], {k: v.get("fonts") for k, v in f.items()})
d = PRL.load(cfg); d["company"]["style_defs"]["Body Text"]["size"] = 11; PRL.save(cfg, d)
T.tick(cfg, S)
fa = openpyxl.load_workbook(book)["Fonts allowed"]
check("... and the rows are written back as the person has them when the app did not change the fonts", "Used for" in head(fa)
      and names(fa) == ["Georgia", "Verdana", "Tahoma", "Calibri"], (head(fa), names(fa)))

# ---- the same when the workbook changed while a change of the app's waited (the two are merged, 4.56.2)
d = PRL.load(cfg); d["company"]["style_defs"]["Heading 1"]["size"] = 15; PRL.save(cfg, d)
excel(lambda wb: wb["Table looks"].cell(names(wb["Table looks"]).index("short") + 2, col(wb["Table looks"], "Recognized by")).__setattr__("value", "1 to 4 words"))
r = T.tick(cfg, S)
wb = openpyxl.load_workbook(book); tl = wb["Table looks"]; fa = wb["Fonts allowed"]
c = PRL.load(cfg)["company"]
check("after a merge the macros' looks are still only on their sheet, and Fonts allowed is still as the person has it",
      "short" not in c["row_types"] and len(c["row_types"]) == n_looks and names(fa) == ["Georgia", "Verdana", "Tahoma", "Calibri"]
      and tl.cell(names(tl).index("short") + 2, col(tl, "Recognized by")).value == "1 to 4 words"
      and c["style_defs"]["Heading 1"]["size"] == 15 and not T.state(cfg).get("dirty"), (sorted(c["row_types"]), head(fa), r["said"]))

# ---- a workbook in a newer format: not read, never written over
def newer(wb):
    ab = wb["Read me"] if "Read me" in wb.sheetnames else wb["About"]   # 4.59.0: the format is on Read me
    for r in ab.iter_rows():
        if r[0].value == "Format":
            r[1].value = SB.FORMAT + 1
    cellc = col(wb["Styles"], "Size (pt)"); wb["Styles"].cell(2, cellc).value = 30


excel(newer)
before = open(book, "rb").read()
r = T.tick(cfg, S)
check("a workbook in a newer format is not read, and the app says so", PRL.load(cfg)["company"]["style_defs"]["Body Text"]["size"] == 11
      and any(BS.FORMAT_NEWER in x for x in r["said"]), r["said"])
d = PRL.load(cfg); d["company"]["style_defs"]["Body Text"]["size"] = 13; PRL.save(cfg, d)
r = T.tick(cfg, S)
check("... and it is not written over while a change of the app's waits", open(book, "rb").read() == before and T.state(cfg).get("dirty")
      and any(BS.FORMAT_NEWER in x for x in r["said"]), r["said"])
check("the waiting file of phrases is the only new file the app keeps", os.path.isfile(os.path.join(os.path.dirname(B.path()), LB.WAITING)))

for left in (B.path(), os.path.join(os.path.dirname(B.path()), LB.WAITING)):       # 4.58.0: none left for a later test
    if os.path.isfile(left) and left.startswith(tmp):                               # (test_lists471 counts the phrases)
        os.remove(left)
w = os.path.join(os.path.dirname(B.path()), LB.WAITING)
if os.path.isfile(w):
    os.remove(w)
print(f"BOOKSHAPE 4570 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
