"""4.56.2 (the one-system rule; claude/stationkeeper-app-sync-check-against-macros-1.23.0-2026-11-18.md, F1 and F2): the
app no longer loses what others put in a standards workbook.
- A sheet the app does not know (a Read me, a list the Stationkeeper Macros keep, a sheet of the person's own) is still
  there, in its place, after the app writes. Before, the app wrote a new workbook each time.
- A workbook that changed while the app's own changes were waiting is read first and merged row by row: a row changed
  in Excel stays, a row changed in the app stays, a row changed in both keeps the workbook's values and is named; a
  workbook that cannot be read is not written over.
The same for an effort's workbook. Fictional values only."""
import os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import banned as B
import bookmerge as BM
import prodrules as PRL
import teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def styles(book):
    wb = openpyxl.load_workbook(book); ws = wb["Styles"]; h = [c.value for c in ws[1]]
    return {r[h.index("Name")].value: {k: r[i].value for i, k in enumerate(h)} for r in ws.iter_rows(min_row=2)}


def excel(book, edit):
    """A change made in Excel (or by a macro): open, edit, save, with a later file time."""
    wb = openpyxl.load_workbook(book); edit(wb); wb.save(book)
    t = time.time() + excel.n; excel.n += 2; os.utime(book, (t, t))


excel.n = 2


def cell(wb, sheet, name, col, value):
    ws = wb[sheet]; h = [c.value for c in ws[1]]
    row = next(i for i, r in enumerate(ws.iter_rows(min_row=2), 2) if r[h.index("Name")].value == name)
    ws.cell(row, h.index(col) + 1).value = value


def app_change(name, **props):
    d = PRL.load(cfg); d["company"]["style_defs"].setdefault(name, {"type": "paragraph"}).update(props); PRL.save(cfg, d)


def app_styles():
    return PRL.load(cfg)["company"]["style_defs"]


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
S = {"team_library": ""}
data = PRL.load(cfg)
data["company"]["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11, "after": 6},
                                 "Heading 1": {"type": "paragraph", "size": 14, "bold": True},
                                 "Caption": {"type": "paragraph", "size": 9},
                                 "Table Text": {"type": "paragraph", "size": 10}}
PRL.save(cfg, data)
T.tick(cfg, S)
book = T.book_path(cfg, S)
check("the first write keeps a copy to compare with later", os.path.isfile(BM.base_path(cfg, book)))

# ---- F1: sheets the app does not know stay, in their place
def add_sheets(wb):
    rm = wb.create_sheet("Read me", 0)
    rm["A1"], rm["B1"], rm["A2"], rm["B2"] = "This workbook is", "Global Standards", "It belongs to", "Kestrel team"
    sm = wb.create_sheet("Style map"); sm.append(["From", "To"]); sm.append(["Body", "Body Text"])
    own = wb.create_sheet("My notes", 3); own.append(["Anything"]); own.append(["kept"])


excel(book, add_sheets)
T.tick(cfg, S)                                               # the app reads the change (nothing of its own to write)
app_change("Body Text", size=12)
r = T.tick(cfg, S)
wb = openpyxl.load_workbook(book)
check("after the app writes, a Read me sheet is still the first sheet, with its two lines", wb.sheetnames[0] == "Read me"
      and (wb["Read me"]["A1"].value, wb["Read me"]["B1"].value, wb["Read me"]["B2"].value) == ("This workbook is", "Global Standards", "Kestrel team"),
      wb.sheetnames)
check("... a list the macros keep is still there with its rows", "Style map" in wb.sheetnames
      and [c.value for c in wb["Style map"][2]] == ["Body", "Body Text"], wb.sheetnames)
check("... a sheet of the person's own keeps its place and its cells", wb.sheetnames.index("My notes") == 3 and wb["My notes"]["A2"].value == "kept",
      wb.sheetnames)
check("... and the app's own change is written", styles(book)["Body Text"]["Size (pt)"] == 12 and not T.state(cfg).get("dirty"), r["said"])
check("... each of the app's sheets is there once", all(wb.sheetnames.count(n) == 1 for n in ("Styles", "Settings", "Phrases", "About", "Columns")),
      wb.sheetnames)

# ---- F2: the workbook changed while the app's change was waiting; different rows
app_change("Heading 1", size=16)
excel(book, lambda wb: cell(wb, "Styles", "Caption", "Size (pt)", 8))
r = T.tick(cfg, S)
st = styles(book)
check("a row changed in Excel while the app's change waited is still as Excel left it", st["Caption"]["Size (pt)"] == 8, st["Caption"])
check("... the app's change to another row is written too", st["Heading 1"]["Size (pt)"] == 16, st["Heading 1"])
check("... the app's own standards took the workbook's row", app_styles()["Caption"]["size"] == 8 and app_styles()["Heading 1"]["size"] == 16)
check("... and the app says it read the workbook first", any("were read from it before yours were written" in x for x in r["said"]), r["said"])
check("... the sheets nobody knows are still there", {"Read me", "Style map", "My notes"} <= set(openpyxl.load_workbook(book).sheetnames))

# ---- the same row changed in both places
app_change("Table Text", size=11)
excel(book, lambda wb: cell(wb, "Styles", "Table Text", "Size (pt)", 9))
r = T.tick(cfg, S)
check("a row changed in both places keeps the workbook's values", styles(book)["Table Text"]["Size (pt)"] == 9 and app_styles()["Table Text"]["size"] == 9,
      styles(book)["Table Text"])
check("... and the app names the row", any("Changed in both places" in x and "Styles: Table Text" in x for x in r["said"]), r["said"])

# ---- a row added in Excel (as a macro's Capture does, Draft), a phrase added, while the app's change waited
def add_rows(wb):
    ws = wb["Styles"]; h = [c.value for c in ws[1]]
    new = [None] * len(h); new[h.index("Name")] = "AA Callout"; new[h.index("Status")] = "Draft"; new[h.index("Size (pt)")] = 10
    ws.append(new)
    ph = wb["Phrases"]; hh = [c.value for c in ph[1]]
    row = [None] * len(hh); row[hh.index("Phrase")] = "world class"; ph.append(row)


app_change("Body Text", after=8)
excel(book, add_rows)
T.tick(cfg, S)
st = styles(book)
check("a Draft row added while the app's change waited is kept as Draft", st.get("AA Callout", {}).get("Status") == "Draft"
      and st["AA Callout"]["Size (pt)"] == 10, list(st))
check("... a phrase added to the Phrases sheet is kept, in the workbook and in the app", any(r.get("Phrase") == "world class" for r in B.load())
      and "world class" in [r[0].value for r in openpyxl.load_workbook(book)["Phrases"].iter_rows(min_row=2)])
check("... with the app's own change", st["Body Text"]["Space after (pt)"] == 8, st["Body Text"])

# ---- rows taken out
def drop(wb, name):
    ws = wb["Styles"]; h = [c.value for c in ws[1]]
    for i in range(ws.max_row, 1, -1):
        if ws.cell(i, h.index("Name") + 1).value == name:
            ws.delete_rows(i)


app_change("Heading 1", size=18)
excel(book, lambda wb: drop(wb, "Caption"))
T.tick(cfg, S)
check("a row taken out in Excel that the app did not touch is gone (as a read always did)", "Caption" not in styles(book) and "Caption" not in app_styles())
app_change("Table Text", size=12)
excel(book, lambda wb: drop(wb, "Table Text"))
r = T.tick(cfg, S)
check("a row taken out in Excel that the app had changed is kept and named", styles(book).get("Table Text", {}).get("Size (pt)") == 12
      and any("Styles: Table Text" in x for x in r["said"]), r["said"])

# ---- no copy to compare with: nothing is removed
os.remove(BM.base_path(cfg, book))
app_change("Body Text", size=13)
excel(book, lambda wb: (drop(wb, "Heading 1"), cell(wb, "Styles", "Table Text", "Size (pt)", 10)))
r = T.tick(cfg, S)
st = styles(book)
check("with nothing to compare with, no row is removed and a row that differs keeps the workbook's values", "Heading 1" in st
      and st["Table Text"]["Size (pt)"] == 10 and any("Changed in both places" in x for x in r["said"]), (list(st), r["said"]))

# ---- a workbook that cannot be read is not written over
app_change("Body Text", size=14)
with open(book, "wb") as f:
    f.write(b"not a workbook")
t = time.time() + 60; os.utime(book, (t, t))
r = T.tick(cfg, S)
check("a changed workbook that cannot be read is not written over, and the app says so", open(book, "rb").read() == b"not a workbook"
      and T.state(cfg).get("dirty") and any("could not be read" in x and "not written over it" in x for x in r["said"]), r["said"])

# ---- an effort's workbook
class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


import effortformat as EFM
w = WS()
EFM.set_layer(w, {"style_defs": {"Body Text": {"font": "Garamond"}, "Heading 1": {"size": 15}}})
epath = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx"); os.makedirs(os.path.dirname(epath))
T.effort_tick(w, epath, "Kestrel")
ebook = T.effort_book_path(epath, "Kestrel")


def e_edit(wb):
    wb.create_sheet("Page limits").append(["Heading", "Max pages"]); wb["Page limits"].append(["Technical", 30])
    cell(wb, "Styles", "Heading 1", "Size (pt)", 17)


excel(ebook, e_edit)
lay = EFM.layer(w); lay["style_defs"]["Body Text"]["font"] = "Georgia"; EFM.set_layer(w, lay); T.mark_effort_dirty(w)
got = T.effort_tick(w, epath, "Kestrel")
ewb = openpyxl.load_workbook(ebook); es = styles(ebook)
check("an effort's workbook: a sheet the app does not know is kept", got == "written" and "Page limits" in ewb.sheetnames
      and [c.value for c in ewb["Page limits"][2]] == ["Technical", 30], (got, ewb.sheetnames))
check("... a row changed in Excel and a row changed in the app are both kept", es["Heading 1"]["Size (pt)"] == 17 and es["Body Text"]["Font"] == "Georgia"
      and EFM.layer(w)["style_defs"]["Heading 1"]["size"] == 17, es)
check("... and the app has a line to say", any("were read from it before yours were written" in x for x in T.take_said()))

print(f"BOOKKEEP 4562 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
