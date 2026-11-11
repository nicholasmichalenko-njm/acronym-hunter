"""4.10.0: the Theme sheet of Company Standards.xlsx (morning answer 12): twelve colors and two fonts as rows, written
from the standard's theme and read back into Word's theme XML; a standard with no theme starts from the Office base;
a value that is not a color is reported and kept as it was. Fictional content."""
import os, sys, tempfile
import xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import openpyxl
import standardsbook as SB
import templatelib as TL
import themebook as TB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "Company Standards.xlsx")
check("the base theme is Word's own shape and reads as the Office colors and fonts", ET.fromstring(TB.BASE.split("?>", 1)[1]) is not None
      and TL.read_theme(TB.BASE)["colors"]["accent1"] == "4472C4" and TL.read_theme(TB.BASE)["minor"] == "Calibri")
company = {"style_defs": {"Normal": {"font": "Calibri", "size": 11}}}
SB.write(p, company)
wb = openpyxl.load_workbook(p)
rows = [[c.value for c in r] for r in wb["Theme"].iter_rows()]
check("the workbook has a Theme sheet: twelve colors, then the headings and body fonts", rows[0] == ["Name", "Value", "Notes"]
      and [r[0] for r in rows[1:]] == [TL.THEME_NAMES[s] for s in TL.THEME_SLOTS] + ["Headings font", "Body font"], rows[:3])
check("... blank when the standard has no theme", all(r[1] in (None, "") for r in rows[1:]))
ws = wb["Theme"]
names = [r[0] for r in rows]
ws.cell(names.index("Accent 1") + 1, 2).value = "#1f3864"
ws.cell(names.index("Body font") + 1, 2).value = "Arial"
ws.cell(names.index("Accent 2") + 1, 2).value = "navy"
wb.save(p)
res = SB.apply(company, None, SB.read(p))
t = res["company"].get("theme") or {}
got = TL.read_theme(t.get("xml", ""))
check("filled in: the theme starts from the base with the values typed", got and got["colors"]["accent1"] == "1F3864" and got["minor"] == "Arial"
      and got["colors"]["accent3"] == "A5A5A5" and got["major"] == "Calibri Light", got and (got["colors"], got["minor"]))
check("... the changes are listed", ("Theme", "Accent 1") in res["changed"] and ("Theme", "Body font") in res["changed"], res["changed"])
check("... a value that is not a color is reported and kept as it was", any("navy" in x for x in res["problems"]) and got["colors"]["accent2"] == "ED7D31",
      res["problems"])
check("... the XML is still well formed", ET.fromstring(t["xml"].split("?>", 1)[1]) is not None)
# a standard with its own theme: Text dark 1 from a system color to a fixed one; the rest kept as Word wrote it
own = TB.BASE.replace('name="Office Theme"', 'name="Kestrel Theme"').replace("<a:objectDefaults/>", "<a:objectDefaults><!-- kept --></a:objectDefaults>")
company2 = {"theme": {"name": "Kestrel Theme", "xml": own}}
SB.write(p, company2)
wb = openpyxl.load_workbook(p); ws = wb["Theme"]; names = [r[0].value for r in ws.iter_rows()]
check("a standard's theme is shown", ws.cell(names.index("Text dark 1") + 1, 2).value == "000000"
      and ws.cell(names.index("Headings font") + 1, 2).value == "Calibri Light")
ws.cell(names.index("Text dark 1") + 1, 2).value = "222222"
wb.save(p)
res = SB.apply(company2, None, SB.read(p))
x = res["company"]["theme"]["xml"]
check("... a color typed over a system color becomes that color; the rest of the theme is kept", '<a:dk1><a:srgbClr val="222222"/></a:dk1>' in x
      and "<!-- kept -->" in x and 'name="Kestrel Theme"' in x, x[:200])
res = SB.apply(res["company"], None, SB.read(p))
check("read again with nothing new: no change", not [c for c in res["changed"] if c[0] == "Theme"], res["changed"])
check("an effort's workbook has no Theme sheet (its theme stays in the app)",
      "Theme" not in openpyxl.load_workbook(SB.write(os.path.join(tmp, "Kestrel Effort Formatting.xlsx"), {}, volumes=[])).sheetnames)
print(f"THEMEBOOK 4100 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
