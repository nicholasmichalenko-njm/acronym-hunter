"""4.58.0 (release B of claude/stationkeeper-app-plan-the-workbook-in-the-shared-shape-2026-11-19.md): the app WRITES a
standards workbook under the plain column names, in Word's words and the plain cell forms, every column always, with
drop-downs; a table type's own look is a named row of Table looks ("Shaded header", Nicholas 2026-11-22 12:01); Fonts
allowed is one row per font, its rows kept as they were where the app did not change them; a workbook in an older
format is copied once before it is written over. What it writes reads back to the same standard. Fictional values only."""
import copy, filecmp, json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import bookshape as BS
import bookwrite as BW
import formats as F
import prodrules as PRL
import standardsbook as SB
import prodengine.pe.rules as R

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def head(ws):
    return [c.value for c in ws[1]]


def rows(ws):
    h = head(ws)
    return [dict(zip(h, (c.value for c in r))) for r in ws.iter_rows(min_row=2)]


def by_name(ws):
    return {r["Name"]: r for r in rows(ws)}


def standard():
    c = PRL.load(tempfile.mkdtemp())["company"]
    c["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11, "jc": "both", "line": 13, "line_rule": "exact"},
                       "Heron Body": {"type": "paragraph", "size": 10, "line": 1.15},
                       "Heading 1": {"type": "paragraph", "size": 14, "bold": True, "jc": "center"}}
    tt = c["table_types"]
    tt["kp"]["name"] = "Shaded"                                  # a type whose own name differs from its row's Name
    tt["osprey"] = copy.deepcopy(tt["kp"]); tt["osprey"]["name"] = "Osprey grid"   # the same change as Shaded's
    tt["merlin"] = {"name": "merlin", "width_pct": 90, "align": "left"}             # no list of kinds: every kind
    for k, p in c["page_setups"].items():
        p["name"] = k
    c["page_setups"]["portrait"]["rules"] = {"restart": True, "linked": False}
    c["fonts"]["body"].update(fonts=["Arial", "Garamond"], min_size=10, max_size=12)
    c["fonts"]["table"].update(fonts=["Arial"], min_size=8, max_size=10)
    c["heading_numbering"]["levels"][0]["fmt"] = "upperRoman"
    return c


PARTS = ("style_defs", "row_types", "table_types", "heading_numbering", "list_numbering", "page_setups", "captions", "fonts")


def blank_of(std):
    b = copy.deepcopy(std)
    for part in PARTS:
        b[part] = {} if isinstance(std[part], dict) and part not in ("heading_numbering", "list_numbering") else \
            ({"on": std[part].get("on"), "levels" if part == "heading_numbering" else "lists": []} if isinstance(std[part], dict) else [])
    return b


def effect(c):
    out = {}
    for k, t in c["table_types"].items():
        out[k] = {x: v for x, v in t.items() if x not in ("roles", "override")}
        out[k]["roles"] = sorted(t["roles"]) if t.get("roles") is not None else None
        out[k]["looks"] = {role: R.row_look(c, role, k) for role in R.ROLES if role in c["row_types"]}
    return out


def norm(v):
    """A blank (None or "") is the same as a value never set; 0 and 0.0 are one number."""
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items() if x is not None and x != "" and norm(x) != {}}
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def read_into(path, base):
    book = SB.read(path)
    return SB.apply(copy.deepcopy(base), [], book), book


tmp = tempfile.mkdtemp()
std = standard()
p = os.path.join(tmp, "Global Standards.xlsx")
SB.write(p, std, [])
wb = openpyxl.load_workbook(p)

# ---- the names, every column, the words and the forms
check("each tab its own names, with their units", "Number format" in head(wb["Heading numbering"])
      and "Left indent (in)" in head(wb["List numbering"]) and "Left margin (in)" in head(wb["Page setups"])
      and "Row style" in head(wb["Table looks"]) and "Edge above" in head(wb["Table looks"]))
olds = {"Fmt", "Text", "Tag style", "Align", "Valign", "Fill", "W", "H", "Orient", "Roles", "Override", "Rules", "Rfp ref", "Edges: top"}
check("no column the app wrote before 4.58.0 under its older name", not any(olds & set(head(ws)) for ws in wb.worksheets
                                                                           if ws.title in BW.FULL), [(ws.title, olds & set(head(ws))) for ws in wb.worksheets if olds & set(head(ws))])
for sheet, full in BW.FULL.items():
    h = head(wb[sheet])
    got = [c for c in h if c in full]
    check(f"{sheet}: every agreed column, in the agreed order", got == list(full), [c for c in full if c not in h][:5])
st = by_name(wb["Styles"])
check("Word's words: Justified, Exactly, Centered", st["Body Text"]["Alignment"] == "Justified" and st["Body Text"]["Line rule"] == "Exactly"
      and st["Heading 1"]["Alignment"] == "Centered", (st["Body Text"]["Alignment"], st["Body Text"]["Line rule"]))
check("a style that sets a spacing and no rule says Multiple", st["Heron Body"]["Line rule"] == "Multiple", st["Heron Body"]["Line rule"])
check("Number format in Word's words", rows(wb["Heading numbering"])[0]["Number format"] == "I, II, III", rows(wb["Heading numbering"])[0])
ps = by_name(wb["Page setups"])
check("Orientation in Word's words, and the two switches as columns", ps["portrait"]["Orientation"] == "Portrait"
      and ps["portrait"]["Page numbers restart"] is True and ps["portrait"]["Header and footer continue from the section before"] is False
      and ps["landscape"]["Header and footer continue from the section before"] is True, ps["portrait"])
check("Name (value) goes where it is the same as Name", "Name (value)" not in head(wb["Page setups"]))
tl = by_name(wb["Table looks"])
check("an edge as a width and a colour", tl["header"]["Edge above"] == "1, 1F3864", tl["header"]["Edge above"])

# ---- table types
tt = by_name(wb["Table types"])
check("the kinds of row as yes or no", tt["kp"]["Has header row"] is True and tt["kp"]["Has total row"] is False, tt["kp"])
check("a type with no list of kinds leaves every Has cell blank", all(tt["merlin"][c] is None for c in BW.HAS_COLS), tt["merlin"])
check("a type's own header is a look of its own, named after the type and the kind of row", tt["kp"]["Header look"] == "Shaded header"
      and "Shaded header" in tl and tl["Shaded header"]["Shading (hex, or none)"] == "D9E2F3", tt["kp"]["Header look"])
check("two types with the same change share one look", tt["osprey"]["Header look"] == "Shaded header"
      and "Osprey grid header" not in tl, tt["osprey"]["Header look"])
check("a kind the type does not change names no look", tt["kp"]["Body look"] is None)
check("Name (value) is kept where a type's own name differs from its Name", "Name (value)" in head(wb["Table types"])
      and tt["kp"]["Name (value)"] == "Shaded")
fig = by_name(wb["Table looks"]).get("Figure table caption") or {}
check("a line a type's look takes away is written none", fig.get("Edge below") == "none", fig.get("Edge below"))

# ---- the drop-downs
dv = {str(r) for d in wb["Styles"].data_validations.dataValidation for r in d.sqref.ranges}
col = lambda ws, n: openpyxl.utils.get_column_letter(head(ws).index(n) + 1)   # noqa: E731
check("drop-downs on Alignment, Line rule, Status and a switch", all(f"{col(wb['Styles'], n)}2:{col(wb['Styles'], n)}5000" in dv
                                                                    for n in ("Alignment", "Line rule", "Status", "Bold")), sorted(dv)[:6])
lists = {d.formula1 for d in wb["Table types"].data_validations.dataValidation}
check("Table types' Alignment has no Justified (the macros' list)", '"Left,Centered,Right"' in lists, lists)
check("the agreed columns fold", any(d.outlineLevel for d in wb["Styles"].column_dimensions.values()))
cs = [(r[0].value, r[1].value, r[2].value) for r in wb["Columns"].iter_rows(min_row=2)]
check("the Columns sheet lists the plain names", ("Heading numbering", "Number format", "fmt") in cs
      and ("List numbering", "Left indent (in)", "left") in cs and not any(s == "Fonts allowed" for s, _c, _k in cs), cs[:4])
check("the format is 3, as formats.py says", SB.disk_format(p) == 3 == F.number("Company Standards workbook"))

# ---- it reads back to the same standard
res, book = read_into(p, blank_of(std))
c = res["company"]
check("it reads with no problem", not res["problems"], res["problems"])
for part in PARTS:
    a, b = std.get(part), c.get(part)
    if part == "fonts":
        a = {k: v for k, v in a.items() if v.get("fonts")}
        b = {k: v for k, v in b.items()}
        a = {k: {x: y for x, y in v.items() if y is not None} for k, v in a.items()}
        b = {k: {x: y for x, y in v.items() if y is not None} for k, v in b.items()}
    if part == "table_types":
        a, b = effect(std), effect(c)
    a, b = norm(a), norm(b)
    check(f"the {part.replace('_', ' ')} read back the same", a == b,
          [k for k in (a if isinstance(a, dict) else {}) if (b or {}).get(k) != a[k]][:4] if isinstance(a, dict) else "differs")
check("the looks a type names are kept on Table looks and are not kinds of row", "Shaded header" not in c["row_types"]
      and "Shaded header" in (c["book_meta"]["Table looks"].get("_held") or {}))
check("a type with no list of kinds is still every kind", c["table_types"]["merlin"].get("roles") is None, c["table_types"]["merlin"])
# written again from what was read: the same workbook, nothing piles up
p2 = os.path.join(tmp, "again.xlsx")
SB.write(p2, c, [])
wb2 = openpyxl.load_workbook(p2)
check("written again: the same names on Table looks, no second Shaded header", sorted(by_name(wb2["Table looks"])) == sorted(tl),
      sorted(set(by_name(wb2["Table looks"])) ^ set(tl)))
strip = lambda d: {k: v for k, v in d.items() if k not in ("ID", "Changed")}                    # noqa: E731
check("written again: the same table types row for row", [strip(r) for r in rows(wb2["Table types"])] == [strip(r) for r in rows(wb["Table types"])])

# ---- Fonts allowed: one row per font; the person's own sizes and notes kept where the app changed nothing
fa = rows(wb["Fonts allowed"])
check("Fonts allowed is one row per font with its use", [(r["Name"], r["Used for"]) for r in fa][:3] ==
      [("Arial", "body"), ("Garamond", "body"), ("Arial", "table")] and fa[0]["Min size (pt)"] == 10, [(r["Name"], r["Used for"]) for r in fa])
wbp = openpyxl.load_workbook(p); ws = wbp["Fonts allowed"]; h = head(ws)
ws.cell(3, h.index("Max size (pt)") + 1).value = 11                    # Garamond for body: its own limit
ws.cell(3, h.index("Notes") + 1).value = "Heron's own body font"
ws.append([None if x != "Name" else "Tahoma" for x in h]); ws.cell(ws.max_row, h.index("Status") + 1).value = "Draft"
ws.cell(ws.max_row, h.index("Used for") + 1).value = "body"
wbp.save(p)
res, book = read_into(p, c)
c = res["company"]
SB.write(p, c, [])
fa = {(r["Name"], r["Used for"]): r for r in rows(openpyxl.load_workbook(p)["Fonts allowed"])}
check("a use the app did not change keeps the person's rows: own sizes, notes and a Draft font", fa[("Garamond", "body")]["Max size (pt)"] == 11
      and fa[("Garamond", "body")]["Notes"] == "Heron's own body font" and fa[("Tahoma", "body")]["Status"] == "Draft", fa.get(("Garamond", "body")))
c["fonts"]["table"]["fonts"] = ["Arial", "Verdana"]                    # a change in the app, to one use only
SB.write(p, c, [])
fa = {(r["Name"], r["Used for"]): r for r in rows(openpyxl.load_workbook(p)["Fonts allowed"])}
check("a use the app changed is written font by font; the others are as they were", ("Verdana", "table") in fa
      and fa[("Garamond", "body")]["Notes"] == "Heron's own body font" and fa[("Garamond", "body")]["Max size (pt)"] == 11, sorted(fa))

# ---- the lists
import listsbook as LB
lw = os.path.join(tmp, "lists.xlsx")
SB.write(lw, std, [], lists={"Authors": (("Name", "Efforts", "Added", "Source"), [{"Name": "Pat Doe", "Efforts": "Kestrel, Osprey"}]),
                              "Phrases": (("Phrase", "Level", "Use instead", "Why"), [{"Phrase": "world-class", "Level": "Banned"}])})
lb = openpyxl.load_workbook(lw)
check("several efforts separated by semicolons", rows(lb["Authors"])[0]["Efforts"] == "Kestrel; Osprey", rows(lb["Authors"])[0])
check("Phrases always has Status, blank written as Approved", head(lb["Phrases"])[-1] == "Status" and rows(lb["Phrases"])[0]["Status"] == "Approved")

# ---- a workbook in an older format: copied once, then written in the plain shape
gold = os.path.join(ROOT, "tests", "golden", "4.48", "Global Standards.xlsx")
old = os.path.join(tmp, "team", "Global Standards.xlsx"); os.makedirs(os.path.dirname(old)); shutil.copyfile(gold, old)
cfg = os.path.join(tmp, "config")
before = SB.read(old)
got = SB.apply(blank_of(std), [], before)
check("the 4.48 workbook (format 2) reads with no problem", SB.disk_format(old) == 2 and not got["problems"], got["problems"])
SB.write(old, got["company"], [], keep_dir=cfg)
kept = os.path.join(cfg, SB.BEFORE)
copies = os.listdir(kept) if os.path.isdir(kept) else []
check("before the first write a copy of it as it was is kept in the config folder", len(copies) == 1
      and filecmp.cmp(os.path.join(kept, copies[0]), gold, shallow=False), copies)
check("... and the workbook is now format 3, under the plain names", SB.disk_format(old) == 3 and "Number format" in head(openpyxl.load_workbook(old)["Heading numbering"]))
after = SB.apply(blank_of(std), [], SB.read(old))
for part in PARTS:
    a, b = got["company"].get(part), after["company"].get(part)
    if part == "table_types":
        a, b = effect(got["company"]), effect(after["company"])
    a, b = norm(a), norm(b)
    check(f"the 4.48 workbook's {part.replace('_', ' ')} are the same after the conversion", a == b, part)
SB.write(old, after["company"], [], keep_dir=cfg)
check("the copy is made once: a second write leaves it as it was", os.listdir(kept) == copies
      and filecmp.cmp(os.path.join(kept, copies[0]), gold, shallow=False))

# ---- a newer format than this one is still refused
nw = os.path.join(tmp, "newer.xlsx"); shutil.copyfile(p, nw)
x = openpyxl.load_workbook(nw)
for r in x["About"].iter_rows():
    if r[0].value == "Format":
        r[1].value = SB.FORMAT + 1
x.save(nw)
check("a workbook of format 4 is not read", BS.FORMAT_NEWER in SB.read(nw)["problems"])

# ---- an effort's workbook: only its changes, a volume, and a type's own look with no base look in the file
lay = {"style_defs": {"Body Text": {"font": "Garamond"}}, "table_types": {"kp": {"override": {"header": {"fill": "112233"}}}},
       "fonts": {"body": {"fonts": ["Georgia"]}}}
vol = {"style_defs": {"Body Text": {"size": 12}}}
ep = os.path.join(tmp, "Kestrel Effort Formatting.xlsx")
SB.write(ep, lay, None, volumes=[("Volume I", vol)])
ew = openpyxl.load_workbook(ep)
et = by_name(ew["Table types"])
check("in an effort's workbook a type's own look is named and holds only the change", et["kp"]["Header look"] == "Kp header"
      and by_name(ew["Table looks"])["Kp header"]["Shading (hex, or none)"] == "112233"
      and by_name(ew["Table looks"])["Kp header"]["Font"] is None, et["kp"])
check("Volume follows Name", head(ew["Styles"])[:3] == ["ID", "Name", "Volume"])
check("an effort's style with no rule says no rule (blank: the Global Standards')", all(r["Line rule"] is None for r in rows(ew["Styles"])))
parts = SB.split_volumes(SB.read(ep), ["Volume I"])
e0 = SB.apply({}, None, parts[""])["company"]
e1 = SB.apply({}, None, parts["Volume I"])["company"]
check("it reads back: the type's own header, the font, and the volume's own size", e0["table_types"]["kp"].get("override") == {"header": {"fill": "112233"}}
      and e0["fonts"]["body"]["fonts"] == ["Georgia"] and e1["style_defs"]["Body Text"].get("size") == 12,
      (e0["table_types"].get("kp"), e0.get("fonts"), e1.get("style_defs")))

# ---- Other Word settings: Word's words or the older ones read to the same value (asked by the macros thread, 2026-11-22)
ow = os.path.join(tmp, "other.xlsx"); SB.write(ow, {"style_defs": {"Heron Note": {"size": 9}, "Heron Quote": {"size": 9}}}, [])
x = openpyxl.load_workbook(ow); ws = x["Styles"]; h = head(ws)
for i in range(2, ws.max_row + 1):
    nm = ws.cell(i, h.index("Name") + 1).value
    ws.cell(i, h.index("Other Word settings") + 1).value = json.dumps({"jc": "Justified", "line_rule": "Exactly"} if nm == "Heron Note"
                                                                      else {"jc": "both", "line_rule": "exact"})
x["Styles"].delete_cols(h.index("Line rule") + 1); x["Styles"].delete_cols(h.index("Alignment") + 1)   # a workbook without them
x.save(ow)
sd = SB.apply({}, [], SB.read(ow))["company"]["style_defs"]
check("Other Word settings: Justified and both, Exactly and exact, read the same", sd["Heron Note"].get("jc") == sd["Heron Quote"].get("jc") == "both"
      and sd["Heron Note"].get("line_rule") == sd["Heron Quote"].get("line_rule") == "exact", sd)

print(f"BOOKWRITE 4580 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
