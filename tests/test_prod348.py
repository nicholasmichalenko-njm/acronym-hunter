"""3.48.0 production: Rule 7's team line comes from the standard (and a Rule 7 footer saved before 3.48.0 takes it),
Quick Parts from a file follow the template's fonts and sizes unless marked Keep its own fonts (symbol fonts and
parts built here keep theirs), and the field menu lists the page, Rule 7 and fill-in fields. Fictional content."""
import os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import hfbuild as HB, prodrules as PRL, prodtemplate as PT, qpmake as QM
from prodengine.pe import rules as PR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def std_():
    s = PRL.for_effort(tempfile.mkdtemp())
    s["style_roles"]["a_number"] = "Heading 2"
    s["variables"]["marking"] = "Kestrel restriction marking."
    return s


def footers(path):
    z = zipfile.ZipFile(path)
    return " ".join(z.read(n).decode("utf-8") for n in z.namelist() if re.match(r"word/footer\d+\.xml$", n))


def glossary(path):
    return zipfile.ZipFile(path).read("word/glossary/document.xml").decode("utf-8")


# ---- Rule 7's team line
check("the default Rule 7 footer carries the {team_line} token", PR.COMPANY["hf_layouts"]["body"]["footer"]["table"]["cells"][1]
      ["lines"][1]["text"] == "{team_line}" and "team_line" in PR.COMPANY["variables"])
s = std_()
s["variables"]["team_line"] = "Kestrel Systems proprietary"
f = footers(PT.make(s, tempfile.mkdtemp(), "").copy)
check("the team's line from the standard is written in every Rule 7 footer", "Kestrel Systems proprietary" in f and "{team_line}" not in f)
s = std_()
f = footers(PT.make(s, tempfile.mkdtemp(), "").copy)
check("no team's line yet: the line stays blank (no token on the page)", "{team_line}" not in f and "Kestrel restriction marking." in f)
s = std_()
for part in ("front", "body", "appendix"):                # a Rule 7 footer saved by 3.42.0 to 3.47.0: its second line blank text
    s["hf_layouts"][part]["footer"]["table"]["cells"][1]["lines"][1]["text"] = ""
s["variables"]["team_line"] = "Kestrel line for old footers"
f = footers(PT.make(s, tempfile.mkdtemp(), "").copy)
check("a Rule 7 footer saved before 3.48.0 takes the team's line too", "Kestrel line for old footers" in f)
s = std_()
s["hf_r7"] = {"line2": "Kestrel line kept by 3.42.0"}
f = footers(PT.make(s, tempfile.mkdtemp(), "").copy)
check("the 3.42.0 builder's team line still reads", "Kestrel line kept by 3.42.0" in f)

import effortformat as EFM
check("Effort Formatting's footer box is the team's line", EFM.FIELD["team_line"][3] == ("variables", "team_line")
      and "ft_center" not in EFM.FIELD)

# ---- Quick Parts follow the template's fonts
parts = tempfile.mkdtemp()
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
body = (f'<w:p xmlns:w="{W}"><w:pPr><w:rPr><w:rFonts w:ascii="Comic Sans MS" w:hAnsi="Comic Sans MS"/><w:sz w:val="40"/></w:rPr></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:ascii="Comic Sans MS" w:hAnsi="Comic Sans MS"/><w:b/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr>'
        '<w:t>Kestrel callout</w:t></w:r>'
        '<w:r><w:rPr><w:rFonts w:ascii="Wingdings" w:hAnsi="Wingdings"/><w:sz w:val="40"/></w:rPr><w:t>&#xF0FC;</w:t></w:r></w:p>')
src = QM.make_source(parts, [{"name": "Kestrel Callout", "category": "05 Callouts", "gallery": "docParts", "xml": body},
                             {"name": "Kestrel Callout Kept", "category": "05 Callouts", "gallery": "docParts", "xml": body}])
s = std_()
s["quick_parts"] = {"one_gallery": True, "entries": [
    {"name": "Kestrel Callout", "category": "05 Callouts", "source": os.path.basename(src)},
    {"name": "Kestrel Callout Kept", "category": "05 Callouts", "source": os.path.basename(src), "as_built": True}]}
job = PT.make(s, tempfile.mkdtemp(), "", parts_dir=parts)
g = glossary(job.copy)
one = g[g.index('w:val="Kestrel Callout"'):g.index('w:val="Kestrel Callout Kept"')]
kept = g[g.index('w:val="Kestrel Callout Kept"'):]
check("a Quick Part from a file loses its typed font and sizes (the template's styles decide)",
      "Comic Sans MS" not in one and 'w:sz w:val="40"' not in one.split("Wingdings")[0] and "<w:b/>" in one, one[:600])
check("a symbol-font run keeps its font (the character means something only in it)", "Wingdings" in one)
check("Keep its own fonts leaves a Quick Part exactly as built", "Comic Sans MS" in kept and 'w:sz w:val="40"' in kept)
rec = next((r for r in job.steps if r.get("key") == "quick_parts"), {})
check("Make templates reports the typed settings it took off, and the step was allowed",
      not rec.get("refused") and (rec.get("report") or {}).get("fonts_followed", 0) >= 4, rec)

# ---- the field menu
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QLineEdit
app = QApplication.instance() or QApplication([])
from skqt.fieldpicker import FieldButton, choices
s = std_()
s["fill_ins"] = [{"key": "contract_type", "name": "Contract type"}]
ch = dict(choices(s))
check("the field menu lists the page, Rule 7, volume and fill-in fields in words",
      ch.get("page") == "Page number" and ch.get("a_number") == "A number (Rule 7)" and ch.get("team_line")
      and ch.get("volume_name") and ch.get("contract_type") == "Contract type")
e1, e2 = QLineEdit(), QLineEdit()
e1.setText("Volume "); e1.setCursorPosition(7)
fb = FieldButton(lambda: s, [e1, e2])
fb.pick("volume_name")
check("a field goes where the cursor is in the box last used", e1.text() == "Volume {volume_name}" and e2.text() == "")
fb.last = e2
fb.pick("page")
check("the box last used gets the next field", e2.text() == "{page}")
fb.fill()
check("the menu shows the fields by name", any(a.text() == "Page number" for a in fb.menu_.actions())
      and not any("{" in a.text() for a in fb.menu_.actions()))
got = []
FieldButton(lambda: s, on_pick=got.append).pick("marking")
check("a field can go to a function instead (the builder's chosen line)", got == ["marking"])

n = sum(checks)
print(f"PROD 3.48 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
