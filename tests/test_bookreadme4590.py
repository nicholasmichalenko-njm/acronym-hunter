"""4.59.0 (release C of claude/stationkeeper-app-plan-the-workbook-in-the-shared-shape-2026-11-19.md): a standards
workbook says what it is on its Read me tab (UX decisions 134, 135, 149; the shared shapes page, section 1); the About
tab goes; one that says it is the other kind is not read and not written over; an effort's workbook is named Effort
Standards (a program's Program Standards, decision 133) and one under the earlier name is renamed once.
Fictional names only (Kestrel, Heron, Osprey)."""
import os, shutil, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import bookmerge as BM
import bookreadme as BR
import formats as F
import prodrules as PRL
import standardsbook as SB
import teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def cells(ws):
    return [[c.value for c in r] for r in ws.iter_rows()]


tmp = tempfile.mkdtemp()
std = PRL.load(tempfile.mkdtemp())["company"]

# ---- the Global Standards: a Read me tab first, no About
g = os.path.join(tmp, "Global Standards.xlsx")
SB.write(g, std, [], kind=BR.GLOBAL)
wb = openpyxl.load_workbook(g)
rm = wb["Read me"]
check("the Read me tab is the first tab", wb.sheetnames[0] == "Read me", wb.sheetnames[:3])
check("there is no About tab", "About" not in wb.sheetnames)
check("A1 and B1: This workbook is, Global Standards; A2: It belongs to", (rm["A1"].value, rm["B1"].value, rm["A2"].value)
      == ("This workbook is", "Global Standards", "It belongs to"))
check("B1 has the drop-down of the three kinds", any('"Global Standards,Effort Standards,Program Standards"' == d.formula1
                                                  and "B1" in str(d.sqref) for d in rm.data_validations.dataValidation))
check("the text both tools write, word for word, from row 4", [rm.cell(4 + i, 1).value for i in range(7)] == list(BR.TEXT))
bottom = {r[0]: r[1] for r in cells(rm) if r and r[0] in ("Made by", "Format")}
check("Made by and Format at the bottom", bottom.get("Format") == SB.FORMAT == 4 and str(bottom.get("Made by") or "").startswith("Stationkeeper"), bottom)
check("the format is 4, as formats.py says, and is read from the Read me tab", SB.disk_format(g) == 4 == F.number("Company Standards workbook"))
book = SB.read(g)
check("read: it says Global Standards, and it reads with no problem", book["kind"] == "Global Standards" and not book["problems"], book["problems"])
res = SB.apply(PRL.load(tempfile.mkdtemp())["company"], [], book)
check("... and the values read back", not res["problems"] and set(res["company"]["style_defs"]) == set(std["style_defs"]))

# ---- written again: the Read me tab kept as it is; a person's own line stays
rm["B2"] = "the proposals team"; rm["A15"] = "Our own note"; wb.save(g)
SB.write(g, std, [], kind=BR.GLOBAL)
rm = openpyxl.load_workbook(g)["Read me"]
got = cells(rm)
check("written again: the Read me tab is kept, a person's own words with it", rm["B2"].value == "the proposals team"
      and any(r[0] == "Our own note" for r in got))
check("... with one Made by line and one Format line", sum(1 for r in got if r[0] == "Made by") == 1
      and sum(1 for r in got if r[0] == "Format") == 1)

# ---- a Read me tab made by the macros is kept; either form of the line is read
m = os.path.join(tmp, "Heron Effort Standards.xlsx")
x = openpyxl.Workbook(); ws = x.active; ws.title = "Read me"
ws["A1"], ws["B1"], ws["A2"], ws["B2"] = "This workbook is", "Effort Standards", "It belongs to", "Heron"
ws["A12"], ws["B12"] = "Made by", "Stationkeeper Macros 1.27.0"
x.create_sheet("Styles").append(["ID", "Name", "Status", "Font"]); x.save(m)
check("read: the macros' Effort Standards workbook and its owner", (SB.read(m)["kind"], SB.read(m)["owner"]) == ("Effort Standards", "Heron"))
SB.write(m, {"style_defs": {"Body Text": {"font": "Garamond"}}}, None, volumes=[], kind=BR.EFFORT, owner="Heron")
y = openpyxl.load_workbook(m)
check("written by the app: the macros' Read me tab stays first and says the same", y.sheetnames[0] == "Read me"
      and y["Read me"]["B1"].value == "Effort Standards" and y["Read me"]["B2"].value == "Heron")
check("... Made by now names the app, on the same line", y["Read me"]["A12"].value == "Made by"
      and str(y["Read me"]["B12"].value).startswith("Stationkeeper") and "Macros" not in str(y["Read me"]["B12"].value))
one = os.path.join(tmp, "one cell.xlsx")
z = openpyxl.Workbook(); z.active.title = "Read me"; z.active["A1"] = "this workbook is: program standards"; z.save(one)
check("the words and the value in one cell, any letter case", SB.read(one)["kind"] == "Program Standards")
nol = os.path.join(tmp, "no line.xlsx")
z = openpyxl.Workbook(); z.active.title = "Styles"; z.active.append(["ID", "Name"]); z.save(nol)
check("no Read me line: no kind, and never refused for that alone", SB.read(nol)["kind"] == ""
      and BR.refused(SB.read(nol), "Global Standards") is None and BR.refused(SB.read(nol), "effort") is None)

# ---- the wrong kind is refused, on both sides
check("an Effort Standards workbook is not taken as the Global Standards", "not read as the Global Standards" in
      (BR.refused(SB.read(m), "Global Standards") or ""))
check("a Global Standards workbook is not taken as an effort's", "not read as this effort's workbook" in (BR.refused(SB.read(g), "effort") or ""))
check("an effort's line takes a Program Standards workbook (decision 118)", BR.refused(SB.read(one), "effort") is None)

cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
lib = T.folder(cfg, {})
os.makedirs(lib, exist_ok=True)
shutil.copyfile(m, os.path.join(lib, T.BOOK))            # the team's folder now holds an Effort Standards workbook
before = open(os.path.join(lib, T.BOOK), "rb").read()
r = T.read_book(cfg, {}, force=True)
check("the app does not read it as the Global Standards, and says why", not r["read"]
      and any("not read as the Global Standards" in x for x in r["problems"]), r)
T.mark_dirty(cfg) if hasattr(T, "mark_dirty") else None
w = T.write_book(cfg, {})
check("... and does not write over it", w == "unread" and open(os.path.join(lib, T.BOOK), "rb").read() == before, w)
check("... and the line at the bottom says so", any("not read as the Global Standards" in x for x in T.take_said()))

# ---- an effort's workbook: its new name, the rename once, a program's
ed = os.path.join(tmp, "Efforts", "Kestrel"); os.makedirs(ed)
lst = os.path.join(ed, "Kestrel_Effort_List.xlsx")
old = os.path.join(ed, "Kestrel Effort Formatting.xlsx")
SB.write(old, {"style_defs": {"Body Text": {"font": "Garamond"}}}, None, volumes=[])
BM.keep_base(cfg, old)
check("the earlier name is there before", os.path.isfile(old) and os.path.isfile(BM.base_path(cfg, old)))
p = T.effort_book_path(lst, "Kestrel", cfg)
check("an effort's workbook is named Effort Standards", os.path.basename(p) == "Kestrel Effort Standards.xlsx", p)
check("... the one under the earlier name was renamed, not copied: one workbook in the folder", os.path.isfile(p)
      and not os.path.isfile(old) and sorted(f for f in os.listdir(ed) if f.endswith(".xlsx")) == ["Kestrel Effort Standards.xlsx"])
check("... and the copy the next merge compares with moved with it", os.path.isfile(BM.base_path(cfg, p))
      and not os.path.isfile(BM.base_path(cfg, old)))
pd = os.path.join(tmp, "Programs", "Osprey"); os.makedirs(pd)
plist = os.path.join(pd, "Osprey" + __import__("programs").LIST_TAIL)
check("a program's workbook is named Program Standards", os.path.basename(T.effort_book_path(plist, "Osprey")) == "Osprey Program Standards.xlsx"
      and T.effort_kind(plist) == "Program Standards" and T.effort_kind(lst) == "Effort Standards")
held = os.path.join(ed, "Heron Effort Formatting.xlsx"); shutil.copyfile(old if os.path.isfile(old) else p, held)
_real = os.replace
os.replace = lambda a, b: (_ for _ in ()).throw(PermissionError("open in Excel"))
try:
    q = T.effort_book_path(os.path.join(ed, "Heron_Effort_List.xlsx"), "Heron", cfg)
finally:
    os.replace = _real
check("while Excel has it open it is used under its earlier name, and renamed the next time", q == held
      and os.path.basename(T.effort_book_path(os.path.join(ed, "Heron_Effort_List.xlsx"), "Heron", cfg)) == "Heron Effort Standards.xlsx")

# ---- an older workbook (format 3, About, no Read me) is read, and written the new way
o = os.path.join(tmp, "older.xlsx")
SB.write(o, std, [], kind=BR.GLOBAL)
x = openpyxl.load_workbook(o); x.remove(x["Read me"]); a = x.create_sheet("About"); a.append(["What", "Value"]); a.append(["Format", 3]); x.save(o)
check("an older workbook with About and no Read me reads with no problem", not SB.read(o)["problems"] and SB.disk_format(o) == 3)
SB.write(o, std, [], kind=BR.GLOBAL)
x = openpyxl.load_workbook(o)
check("... written by 4.59.0: About gone, Read me first, format 4", "About" not in x.sheetnames and x.sheetnames[0] == "Read me" and SB.disk_format(o) == 4)
kept = os.path.join(tmp, "kc")
SB.write(o, std, [], keep_dir=kept, kind=BR.GLOBAL)
check("a format 3 or 4 workbook is not copied again into the folder kept from before 4.58", not os.path.isdir(os.path.join(kept, SB.BEFORE)))

print(f"BOOKREADME 4590 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
