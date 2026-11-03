"""3.32.1 bullets as Word stores them and as people see them: Symbol's round bullet and Wingdings' square, arrowhead
and check shown as real characters; two bullets compared by what they show; a bullet written as Word writes it (the
character in Symbol or Wingdings) so it shows on every PC; list numbering learned as the bullet people see and written
back in Word's form, with a second run changing nothing; Symbol-font typed bullets found as typed bullets; the Table
looks of an import taken over the standard's, not in their place (the 3.32.1 import fix)."""
import copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
from prodengine.pe import bullets as B, listnum as LN, lists as LS
from prodengine.engine.pkg import Package
import prodrules as PRL, templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


check("Symbol's round bullet shows as a bullet", B.shown("", "Symbol") == "•" and B.shown("·", "Symbol") == "•")
check("Wingdings' square, arrowhead and check show as themselves", B.shown("", "Wingdings") == "▪" and B.shown("§", "Wingdings") == "▪"
      and B.shown("", "Wingdings") == "➢" and B.shown("", "Wingdings") == "✓")
check("a symbol character with no font named still shows a bullet", B.shown("") == "•" and B.shown("") == "▪")
check("an ordinary character is left alone", B.shown("o", "Courier New") == "o" and B.shown("–") == "–")
check("compared by what shows", B.same("", "Symbol", "•", "") and not B.same("", "Wingdings", "•", ""))
check("written as Word writes it", B.word_form("•") == ("", "Symbol") and B.word_form("▪") == ("", "Wingdings")
      and B.word_form("", "Symbol") == ("", "Symbol") and B.word_form("") == ("", "Wingdings"))
check("a font the person chose is kept", B.word_form("•", "Arial") == ("•", "Arial") and B.word_form("o", "Courier New") == ("o", "Courier New"))
check("for a person: the character, no symbol font", B.for_display("", "Symbol") == ("•", "") and B.for_display("–", "Arial") == ("–", "Arial"))
# ---------------------------------------------------------------- list numbering in a file
std = PRL.engine_ready(PRL.for_effort(tempfile.mkdtemp()))
std["list_numbering"] = {"on": True, "lists": [{"name": "Bullets", "levels": [
    {"style": "List Bullet", "fmt": "bullet", "text": "•", "font": "", "left": 0.25, "hanging": 0.25},
    {"style": "List Bullet 2", "fmt": "bullet", "text": "▪", "font": "", "left": 0.5, "hanging": 0.25},
    {"style": "List Bullet 3", "fmt": "bullet", "text": "–", "font": "", "left": 0.75, "hanging": 0.25}]}]}
src = os.path.join(HERE, "pefix", "data", "small.docx")
pkg = Package(src)
r = LN.op_list_numbering(pkg, std)
lv = LN.read_levels(pkg, ["List Bullet", "List Bullet 2", "List Bullet 3"], strict=True)
check("written: the round bullet in Symbol, the square in Wingdings, the dash as it is", lv["List Bullet"]["text"] == ""
      and lv["List Bullet"]["font"] == "Symbol" and lv["List Bullet 2"]["text"] == "" and lv["List Bullet 2"]["font"] == "Wingdings"
      and lv["List Bullet 3"]["text"] == "–", lv)
check("Word's check expects the character Word reports", [c["expect"] for c in r["checks"]][:2] == ["", ""])
check("the file shows the standard's bullets: nothing differs", LN.differences(pkg, std) == [], LN.differences(pkg, std))
check("a second run changes nothing", LN.op_list_numbering(pkg, std).get("lists") == 0)
lt = LN.learn(pkg, dict(std, lists={"bullet_styles": ["List Bullet", "List Bullet 2", "List Bullet 3"], "number_styles": []}))
check("learned as the bullets people see", [(x["text"], x["font"]) for x in lt["lists"][0]["levels"]] == [("•", ""), ("▪", ""), ("–", "")], lt)
std2 = copy.deepcopy(std); std2["list_numbering"]["lists"][0]["levels"][0]["text"] = "➢"
d = LN.differences(pkg, std2)
check("a different bullet is reported as the characters people see", d and "'•'" in d[0][1] and "'➢'" in d[0][1], d)
check("a Symbol-font typed bullet is a typed bullet", LS._bullet_prefix("\tText")[1] == "")
# ---------------------------------------------------------------- the import fix: Table looks over the standard's
work = copy.deepcopy(PRL.COMPANY)
TL.use_values(tempfile.mkdtemp(), "table_look", "Table looks", {"row_types": {"header": {"fill": "1F3864", "edges": "box"},
                                                                         "body": {"fill": "", "edges": "grid"}}}, work)
check("a row look taken from a file goes over the standard's: its tag style, font and size stay",
      work["row_types"]["header"]["fill"] == "1F3864" and work["row_types"]["header"].get("tag_style") == PRL.COMPANY["row_types"]["header"]["tag_style"]
      and "size" in work["row_types"]["body"], work["row_types"]["header"])
bad = copy.deepcopy(PRL.COMPANY); bad["row_types"]["header"] = {"fill": "FFFFFF"}
fixed = PRL.repair_rows(bad)
check("a standard an earlier import left without row settings is repaired", fixed == ["header"] and "tag_style" in bad["row_types"]["header"]
      and bad["row_types"]["header"]["fill"] == "FFFFFF")
n = sum(checks)
print(f"BULLETS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
