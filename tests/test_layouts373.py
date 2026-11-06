"""3.73.0 without a screen: outline layouts set ahead of time. The starting layout is the column names given; an import
uses the layout that knows the most headings (case, spacing and a trailing colon ignored); a renamed or added column is
unknown until it is said once, then remembered; formatting rules by color, italic and bold give each look its setup
kind, the most specific rule winning; 3.71.0's saved columns and rules read as a layout; the newest saved layout wins a
tie. Fictional content (Kestrel)."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import outlinelayouts as OL, outlinexl as OX

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def make(path, headers):
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    wb = Workbook(); ws = wb.active
    ws.append(headers)
    ital = InlineFont(i=True, color="FF000000"); cust = InlineFont(color="FF6B21A8")
    row = ["1.1", "Ground Segment Architecture", "L.4.2.1", "The offeror shall describe its ground segment architecture.",
           None, "R. Diaz", "Lead with the dual-site design."] + [""] * (len(headers) - 7)
    ws.append(row)
    i = [OL.norm(h) for h in headers].index("supporting rfp content")
    ws.cell(row=2, column=i + 1).value = CellRichText([TextBlock(cust, "The Government requires a resilient ground segment. "),
                                                      TextBlock(ital, "See SOW C.3.4.")])
    wb.save(path)
    return path


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg")
GIVEN = ["Response Section Number", "Response Section Name", "RFPL Number", "Compliance Requirement", "Supporting RFP Content",
         "Authors", "Management Guidance"]
lays = OL.load(cfg)
check("the starting layout is the column names given, with black italic as supporting RFP text",
      list(lays) == [OL.STARTING] and lays[OL.STARTING]["names"]["requirement"] == ["Compliance Requirement"]
      and OL.rule_kind(lays[OL.STARTING], "support", "-Iauto") == "support", lays)
book = OX.read(make(os.path.join(tmp, "a.xlsx"), GIVEN))
p = OL.profile(cfg, book)
check("an import uses the layout: every column known, black italic rule applied, the purple look left for the person",
      p["name"] == OL.STARTING and not p["unknown"] and p["columns"]["Compliance Requirement"] == "requirement"
      and p["rules"]["Supporting RFP Content"] == {"-Iauto": "support"}, p)
check("case, spacing and a trailing colon are ignored", OL.role_of(lays[OL.STARTING], "  compliance   REQUIREMENT:") == "requirement")
renamed = GIVEN[:3] + ["L Requirement"] + GIVEN[4:] + ["Volume"]
book2 = OX.read(make(os.path.join(tmp, "b.xlsx"), renamed))
p2 = OL.profile(cfg, book2)
check("a renamed column and an added one are new to the layout (and take a guess meanwhile)",
      sorted(p2["unknown"]) == ["L Requirement", "Volume"] and p2["columns"]["L Requirement"] == "requirement", p2)
OL.remember(cfg, OL.STARTING, "L Requirement", "requirement")
OL.remember(cfg, OL.STARTING, "Volume", "ignore")
p3 = OL.profile(cfg, book2)
check("said once, remembered: the next import knows both", not p3["unknown"] and p3["columns"]["Volume"] == "ignore"
      and "L Requirement" in OL.load(cfg)[OL.STARTING]["names"]["requirement"], p3)
lay = OL.load(cfg)[OL.STARTING]
lay["rules"]["support"].append({"color": "6B21A8", "italic": None, "bold": None, "kind": "customer"})
lay["rules"]["support"].append({"color": "", "italic": True, "bold": True, "kind": "pm"})
OL.put(cfg, OL.STARTING, lay)
lay = OL.load(cfg)[OL.STARTING]
check("rules by color: the purple text is customer requirement text", OL.rule_kind(lay, "support", "--6B21A8") == "customer")
check("the most specific rule wins; between rules as specific, the one listed last (bold italic, added after italic black)", OL.rule_kind(lay, "support", "BIauto") == "pm"
      and OL.rule_kind(lay, "support", "-Iauto") == "support")
check("a look no rule fits is left for the person", OL.rule_kind(lay, "support", "--FF0000") is None)
check("a rule's look as a sample key", OL.look_key("000000", True, False) == "-Iauto" and OL.look_key("#6b21a8", False, True) == "B-6B21A8")
# ---- 3.71.0's saved columns and rules read as a layout
cfg2 = os.path.join(tmp, "cfg2")
OX.save_profile(cfg2, "Kestrel outline", {"columns": dict(OX.guess(GIVEN)), "rules": {"Supporting RFP Content": {"--6B21A8": "customer"}}})
l2 = OL.load(cfg2)
check("3.71.0's saved columns and rules read as a layout", "Kestrel outline" in l2 and OL.STARTING not in l2
      and OL.rule_kind(l2["Kestrel outline"], "support", "--6B21A8") == "customer")
# ---- ties: the newest saved wins
OL.put(cfg2, "Second", {"names": {k: [h] for h, k in OX.guess(GIVEN).items()}, "skip": [], "rules": {}})
check("two layouts that know the same headings: the newest saved is used", OL.best(cfg2, GIVEN)[0] == "Second")
OL.put(cfg2, "Kestrel outline", l2["Kestrel outline"])
check("... and saving the other makes it the newest", OL.best(cfg2, GIVEN)[0] == "Kestrel outline")
check("the file carries its format number", json.load(open(os.path.join(cfg2, OL.FILE), encoding="utf-8"))["format"] == 1)

print(f"LAYOUTS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
if __name__ == "__main__":                                   # qt_layouts373 imports the workbook maker
    sys.exit(0 if all(checks) else 1)
