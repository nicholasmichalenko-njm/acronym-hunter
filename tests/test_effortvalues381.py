"""3.81.0 the count before Every setting... goes: for every effort this PC knows, the sections of the old full editor
that hold an effort's own value Effort Formatting does not list, and in how many efforts; values Effort Formatting shows
are not counted; the text shows counts only (never a setting's name or value). Fictional content (Heron, Osprey)."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import effort as E, workspace as W
import effortvalues as EV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
reg = os.path.join(tmp, "efforts.json")
R = E.Registry(reg)
for name, over, vol in (("Heron", {"variables": {"body_font": "Garamond"}, "terms": {"Jordan Example": "an employee name"},
                                   "toc": {"levels": 2}}, {}),
                        ("Osprey", {"toc": {"levels": 3}}, {"p1": {"captions": {"Table": "above"}, "graphics": {"min_dpi": 300}}})):
    d = os.path.join(tmp, name); os.makedirs(d)
    lst = os.path.join(d, f"{name}_Effort_List.xlsx")
    dd = W.data_dir_for(lst); os.makedirs(dd)
    json.dump({"prod_std": {"over": over, "over_vol": vol}}, open(os.path.join(dd, "settings.json"), "w"))
    R.put(name, path=lst)
R.put("Gone", path=os.path.join(tmp, "Gone", "Gone_Effort_List.xlsx"))
rep = EV.report(reg)
by = {r["key"]: r for r in rep["sections"]}
check("every effort known, the ones on this PC read", rep["efforts"] == 3 and rep["read"] == 2, rep)
check("a section two efforts use comes first", rep["sections"][0]["key"] == "toc" and by["toc"]["efforts"] == 2, rep["sections"])
check("values Effort Formatting lists are not counted", "variables" not in by and "captions" not in by, list(by))
check("sections set for one volume count too", by.get("graphics", {}).get("efforts") == 1 and by.get("terms", {}).get("efforts") == 1)
txt = EV.write_text(rep)
check("the text shows counts only: no setting's name or value", "Jordan" not in txt and "levels" not in txt
      and "Table of contents: 2 effort(s)" in txt, txt)
check("an effort no longer on this PC is not made again", not os.path.exists(os.path.join(tmp, "Gone")))
n = sum(checks)
print(f"EFFORT VALUES 381 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
