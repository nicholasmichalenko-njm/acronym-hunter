"""4.7.0: the team library as files (claude/stationkeeper-team-library-files-decisions-2026-11-10.md). The Company Standards
workbook is written from the standards the first time (nothing deleted), read back after a change in Excel (a value,
a new row as Draft, a column of your own kept both ways, a renamed row keeping its ID), written after a change in the
app (marked, then written once), waits while Excel holds it, reports a copy from another PC and a file it cannot read;
a property column taken out asks once; the Word files mirror both ways; an effort's workbook holds only its changes.
Fictional values only."""
import json, os, shutil, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import fieldrecipes as FR
import prodrules as PRL
import standardsbook as SB
import teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
S = {"team_library": ""}
data = PRL.load(cfg)
data["company"]["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11, "after": 6},
                                 "Heading 1": {"type": "paragraph", "size": 14, "bold": True, "used_on": "Body"}}
PRL.save(cfg, data)
check("a change in the app marks the workbook to write", T.state(cfg).get("dirty") is True)
said = T.tick(cfg, S)["said"]
book = T.book_path(cfg, S)
check("the first tick writes Company Standards.xlsx in Stationkeeper Data\\Team library", os.path.isfile(book)
      and book.endswith(os.path.join("Team library", "Company Standards.xlsx")) and not T.state(cfg).get("dirty"), (book, said))
wb = openpyxl.load_workbook(book)
check("its sheets", wb.sheetnames == ["Styles", "Table looks", "Table types", "Heading numbering", "List numbering", "Page setups",
                                      "Captions", "Fonts allowed", "Settings", "Fields", "About", "Columns"], wb.sheetnames)
ws = wb["Styles"]
hdr = [c.value for c in ws[1]]
check("organizing columns first, then only the properties some row uses, Other Word settings last",
      hdr[:12] == list(SB.ORG) and "Size (pt)" in hdr and "Small caps" not in hdr and hdr[-1] == SB.OTHER, hdr)
check("ID hidden, the key columns frozen, the property columns grouped", ws.column_dimensions["A"].hidden and ws.freeze_panes == "C2"
      and any(d.outlineLevel for d in ws.column_dimensions.values()))
check("Used on is a column of its own", [r[hdr.index("Used on")].value for r in ws.iter_rows(min_row=2)] == ["", "Body"]
      or [r[hdr.index("Used on")].value for r in ws.iter_rows(min_row=2)] == [None, "Body"])
check("Fields holds the recipes", wb["Fields"].max_row - 1 == len(FR.load(cfg)))
check("nothing changed by a tick with nothing new", T.tick(cfg, S).get("read") is False)
# edit in Excel
rows = list(ws.iter_rows(min_row=2))
body = next(r for r in rows if r[1].value == "Body Text")
h1 = next(r for r in rows if r[1].value == "Heading 1")
body[hdr.index("Size (pt)")].value = 12
h1[1].value = "Heading One"                                  # renamed: its ID keeps it
ws.cell(1, len(hdr) + 1).value = "Reviewer"; ws.cell(body[0].row, len(hdr) + 1).value = "Pat"
new = [None] * len(hdr); new[1] = "AA Callout"; new[3] = "Draft"; new[hdr.index("Size (pt)")] = 10
ws.append(new)
wb.save(book)
time.sleep(0.05)
r = T.tick(cfg, S)
std = PRL.load(cfg)["company"]["style_defs"]
check("a value changed in Excel reaches the standard", std.get("Body Text", {}).get("size") == 12, std)
check("a renamed row keeps its values under the new name", "Heading One" in std and "Heading 1" not in std and std["Heading One"]["bold"] is True, list(std))
check("a Draft row waits outside the standard (only Approved goes into templates and the macros)", "AA Callout" not in std)
check("Changed says who and that it was Excel", "(Excel)" in (PRL.load(cfg)["company"]["book_meta"]["Styles"]["Body Text"]["changed"]))
check("the read says what changed", any("change" in x for x in r["said"]), r)
# the app changes something: written, your column kept
d2 = PRL.load(cfg); d2["company"]["style_defs"]["Body Text"]["after"] = 8; PRL.save(cfg, d2)
T.tick(cfg, S)
wb = openpyxl.load_workbook(book); ws = wb["Styles"]; hdr = [c.value for c in ws[1]]
rows = {r[1].value: r for r in ws.iter_rows(min_row=2)}
check("a change in the app is written to the workbook", rows["Body Text"][hdr.index("Space after (pt)")].value == 8)
check("... your own column and its value kept", "Reviewer" in hdr and rows["Body Text"][hdr.index("Reviewer")].value == "Pat", hdr)
check("... the Draft row kept in the workbook", "AA Callout" in rows and rows["AA Callout"][3].value == "Draft")
check("... and Changed says the app", "(app)" in str(rows["Body Text"][hdr.index("Changed")].value))
# Excel holds it: the app waits
real = SB.write
SB.write = lambda *a, **k: (_ for _ in ()).throw(PermissionError("locked"))
d3 = PRL.load(cfg); d3["company"]["style_defs"]["Body Text"]["after"] = 9; PRL.save(cfg, d3)
said = T.tick(cfg, S)["said"]
check("Excel holds the workbook: the app waits and says so", T.state(cfg).get("dirty") and any("open in Excel" in x for x in said), said)
SB.write = real
T.tick(cfg, S)
check("... and writes when it is free", not T.state(cfg).get("dirty"))
# a column taken out asks once
wb = openpyxl.load_workbook(book); ws = wb["Styles"]; hdr = [c.value for c in ws[1]]
ws.delete_cols(hdr.index("Bold") + 1); wb.save(book)
r = T.tick(cfg, S)
check("a property column taken out asks once (the values kept until you answer)", ("Styles", "bold") in [tuple(x) for x in r.get("question", [])]
      and PRL.load(cfg)["company"]["style_defs"]["Heading One"].get("bold") is True, r.get("question"))
T.answer_removed(cfg, "drop", S)
check("... Take it off every row: gone from the standard and the workbook", "bold" not in PRL.load(cfg)["company"]["style_defs"]["Heading One"]
      and "Bold" not in [c.value for c in openpyxl.load_workbook(book)["Styles"][1]])
# a file that cannot be read, and a copy from another PC
shutil.copy2(book, book.replace(".xlsx", "-LAPTOP7.xlsx"))
open(book, "wb").write(b"not a workbook")
r = T.tick(cfg, S)
check("a workbook that cannot be read is reported; the last good reading stays", r.get("problems")
      and PRL.load(cfg)["company"]["style_defs"]["Body Text"]["size"] == 12, r)
check("a copy from another PC is reported, never read", "Company Standards-LAPTOP7.xlsx" in (r.get("conflicts") or []), r.get("conflicts"))
# the Word files, both ways
parts = os.path.join(cfg, "production_parts"); os.makedirs(parts)
open(os.path.join(parts, "Cover.docx"), "wb").write(b"cover v1")
T.sync_content(cfg, S)
team_cover = os.path.join(T.folder(cfg, S), "Content", "Standards parts", "Cover.docx")
check("a Word file the app keeps appears in the team library", open(team_cover, "rb").read() == b"cover v1")
time.sleep(0.02); open(team_cover, "wb").write(b"cover v2, edited in Word")
got = T.sync_content(cfg, S)
check("... edited in Word there, the app's copy follows", open(os.path.join(parts, "Cover.docx"), "rb").read() == b"cover v2, edited in Word"
      and got["in"] == ["Cover.docx"], got)
open(os.path.join(parts, "Cover.docx"), "wb").write(b"cover v3 from the app")
T.sync_content(cfg, S)
check("... changed in the app, the team's file follows", open(team_cover, "rb").read() == b"cover v3 from the app")
os.remove(team_cover); T.sync_content(cfg, S)
check("... nothing is deleted: a file gone from one side comes back from the other", os.path.isfile(team_cover))
# Settings can point it elsewhere (a synced SharePoint library)
elsewhere = os.path.join(tmp, "SharePoint", "Proposal Team Library")
check("Settings can point the team library at another folder", T.book_path(cfg, {"team_library": elsewhere}).startswith(elsewhere))


# an effort's workbook: only its changes
class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


import effortformat as EFM
w = WS()
EFM.set_layer(w, {"variables": {"body_size": 12}, "style_defs": {"Body Text": {"font": "Garamond"}}})
epath = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx"); os.makedirs(os.path.dirname(epath))
check("the effort's workbook is written beside its list", T.effort_tick(w, epath, "Kestrel") == "written"
      and os.path.isfile(T.effort_book_path(epath, "Kestrel")))
ewb = openpyxl.load_workbook(T.effort_book_path(epath, "Kestrel"))
eh = [c.value for c in ewb["Styles"][1]]
check("... holding only the effort's changes", [r[1].value for r in ewb["Styles"].iter_rows(min_row=2)] == ["Body Text"]
      and "Size (pt)" not in eh and [r[0].value for r in ewb["Settings"].iter_rows(min_row=2)] == ["body_size"], eh)
ews = ewb["Styles"]; ews.cell(2, eh.index("Font") + 1).value = "Georgia"
ewb["Settings"].cell(2, 2).value = None                      # blank: back to the Company Standards (Default)
ewb.save(T.effort_book_path(epath, "Kestrel")); time.sleep(0.02)
T.effort_tick(w, epath, "Kestrel")
lay = EFM.layer(w)
check("... edited in Excel: the effort's layer follows; a blank cell means the Company Standards (Default)",
      lay.get("style_defs", {}).get("Body Text", {}).get("font") == "Georgia" and "body_size" not in (lay.get("variables") or {}), lay)
print(f"TEAMLIB 470 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
