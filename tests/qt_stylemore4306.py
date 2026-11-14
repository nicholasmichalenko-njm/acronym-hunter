"""4.30.6 (Nicholas 2026-11-13 18:52): the style's own form sets line spacing, indents and tabs for every paragraph
style, and says which list level a numbered style is. Only what is changed is written, so what a style takes from its
base stays taken from it, and everything else Word wrote is kept. Fictional styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
import stylelib as SL
from skqt import stylespage as SP, styleedit as SE

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


class Host:
    def __init__(self, d):
        self.config_dir, self.said = d, []
    def status(self, t): self.said.append(t)
    def toast(self, t): self.said.append(t)
    def go(self, *_a): pass


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
BODY = (f'<w:style {W} w:type="paragraph" w:styleId="OspreyBody"><w:name w:val="Osprey Body"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="auto"/></w:pBdr><w:spacing w:before="120" w:after="120"/></w:pPr>'
        '<w:rPr><w:sz w:val="22"/></w:rPr></w:style>')
HEAD = (f'<w:style {W} w:type="paragraph" w:styleId="OspreyHeading2"><w:name w:val="Osprey Heading 2"/>'
        '<w:pPr><w:keepNext/><w:numPr><w:ilvl w:val="1"/><w:numId w:val="3"/></w:numPr></w:pPr><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>')
TOC = (f'<w:style {W} w:type="paragraph" w:styleId="OspreyTOC1"><w:name w:val="Osprey TOC 1"/>'
       '<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs></w:pPr><w:rPr><w:sz w:val="22"/></w:rPr></w:style>')
d = tempfile.mkdtemp()
host = Host(d); page = SP.StylesPage(host); lib = page.lib
rows = [{"name": "Osprey Body", "type": "paragraph", "values": {"type": "paragraph", "size": 11.0, "before": 6.0, "after": 6.0, "line": 1.0, "left": 0.0}, "xml": BODY, "keep": True},
        {"name": "Osprey Heading 2", "type": "paragraph", "values": {"type": "paragraph", "size": 13.0, "bold": True, "keep_next": True}, "xml": HEAD, "keep": True},
        {"name": "Osprey TOC 1", "type": "paragraph", "values": {"type": "paragraph", "size": 11.0, "tabs": [[467.5, "right", "dot"]]}, "xml": TOC, "keep": True},
        {"name": "Osprey Mark", "type": "character", "values": {"type": "character", "bold": True}, "xml": "", "keep": True}]
SL.bring_in(lib, rows, os.path.join(d, "Osprey.docx"))
by = lambda n: next(i for i in lib.items if i["kind"] == "style" and lib.base_of(i) == n)    # noqa: E731
body, head, toc, mark = by("Osprey Body"), by("Osprey Heading 2"), by("Osprey TOC 1"), by("Osprey Mark")

# ---- tabs in words
check("tabs read in words and back", SL.parse_tabs("6.5 right dots; 0.5") == ([[36.0, "left", "none"], [468.0, "right", "dot"]], [])
      and SL.tabs_text([[468.0, "right", "dot"], [36.0, "left", "none"]]) == "0.5 left; 6.5 right dots")
check("a part that is not a tab is named, not guessed", SL.parse_tabs("3.25 centre; 2 center")[1] == ["3.25 centre"] and SL.parse_tabs("2 center")[0] == [[144.0, "center", "none"]])

# ---- the form
dlg = SE.StyleEdit(page, body, lib.values(body))
m = dlg.more
check("a paragraph style's form has Line spacing, Indents, Tabs and Numbering", m is not None and m.sp.currentData() == "1.0" and m.tabs.text() == ""
      and m.num.text() == "Not part of a list.")
check("opened and left alone, the form changes none of them", m.values() == {} and not any(k in dlg.values() for k in SL.MORE))
dlg = SE.StyleEdit(page, head, lib.values(head))
check("a numbered heading says which level of its list it is", dlg.more.num.text().startswith("Part of a list, level 2."), dlg.more.num.text())
dlg = SE.StyleEdit(page, toc, lib.values(toc))
check("a table of contents style shows its tab in words", dlg.more.tabs.text() == "6.49 right dots" or dlg.more.tabs.text().startswith("6.4"), dlg.more.tabs.text())
check("a character style's form has none of these", SE.StyleEdit(page, mark, lib.values(mark)).more is None)

# ---- line spacing and a hanging indent on Osprey Body
dlg = SE.StyleEdit(page, body, lib.values(body)); m = dlg.more
m.sp.setCurrentIndex(m.sp.findData("1.15")); m.ind["left"].setValue(0.5); m.special.setCurrentIndex(m.special.findData("hanging")); m.by.setValue(0.25)
got = dlg.values()
check("the form gives what was changed, in points", got.get("line") == 1.15 and got.get("left") == 36.0 and got.get("hanging") == 18.0 and got.get("first") == 0.0
      and "right" not in got and "tabs" not in got, {k: got.get(k) for k in SL.MORE})
new = SE.review(page, body["id"], got)
v = lib.values(new); x = v["_xml"]
check("saved: the values are kept", new["id"] != body["id"] and v["line"] == 1.15 and v["left"] == 36.0 and v["hanging"] == 18.0 and "first" not in v)
check("... and written into Word's own definition", 'w:line="276"' in x and 'w:lineRule="auto"' in x and 'w:left="720"' in x and 'w:hanging="360"' in x, x)
check("... the right indent, never touched, is not written", "w:right=" not in x and "w:firstLine" not in x)
check("... what Word wrote besides is kept: its border, its base, its space before", "<w:pBdr>" in x and 'w:basedOn w:val="Normal"' in x and 'w:before="120"' in x)
check("the row's words say it", "indent left 0.5 in, hanging 0.25 in" in SL.describe(v)["paragraph"] and "line 1.15" in SL.describe(v)["paragraph"], SL.describe(v)["paragraph"])

# ---- exactly 14 points, a first-line indent in place of the hanging one, and tabs
dlg = SE.StyleEdit(page, new, v); m = dlg.more
check("the form opens on what was saved", m.sp.currentData() == "1.15" and m.special.currentData() == "hanging" and abs(m.by.value() - 0.25) < 1e-6 and abs(m.ind["left"].value() - 0.5) < 1e-6)
m.sp.setCurrentIndex(m.sp.findData("exact")); m.sp_by.setValue(14); m.special.setCurrentIndex(m.special.findData("first")); m.by.setValue(0.3)
m.tabs.setText("3.25 center; 6.5 right dots"); m.sync()
n2 = SE.review(page, new["id"], dlg.values())
v2 = lib.values(n2); x2 = v2["_xml"]
check("exactly 14 points", v2["line"] == 14.0 and v2["line_rule"] == "exact" and 'w:line="280"' in x2 and 'w:lineRule="exact"' in x2, x2)
check("a first-line indent takes the place of the hanging one", v2.get("first") == 21.6 and "hanging" not in v2 and 'w:firstLine="432"' in x2 and "w:hanging" not in x2)
check("two tabs, in order, the second with dots", v2["tabs"] == [[234.0, "center", "none"], [468.0, "right", "dot"]]
      and x2.index('w:pos="4680"') < x2.index('w:pos="9360"') and 'w:leader="dot"' in x2 and "exactly" in SL.describe(v2)["paragraph"] and "2 tab(s)" in SL.describe(v2)["paragraph"])
from lxml import etree
ppr = etree.fromstring(x2.encode()).find("{%s}pPr" % SL.W)
order = [c.tag.split("}")[1] for c in ppr]
check("the paragraph settings are in Word's own order", order.index("pBdr") < order.index("tabs") < order.index("spacing") < order.index("ind"), order)

# ---- the tab taken off the table of contents style; the numbered heading keeps its list
dlg = SE.StyleEdit(page, toc, lib.values(toc)); dlg.more.tabs.setText(""); dlg.more.sync()
t2 = SE.review(page, toc["id"], dlg.values())
check("clearing the tabs takes them out", "tabs" not in lib.values(t2) and "<w:tabs>" not in lib.values(t2)["_xml"])
dlg = SE.StyleEdit(page, head, lib.values(head)); dlg.more.ind["left"].setValue(0.4)
h2 = SE.review(page, head["id"], dlg.values())
check("an indent set on a numbered heading keeps its list and level", "<w:numPr>" in lib.values(h2)["_xml"] and 'w:ilvl w:val="1"' in lib.values(h2)["_xml"]
      and 'w:left="576"' in lib.values(h2)["_xml"] and SL.numbering_of(lib.values(h2)) == (True, 2))
# a style made in the app
it, _st = SL.new_style(lib, "Osprey Note", "paragraph", {"font": "Arial", "size": 10})
n3 = SE.review(page, it["id"], {"line": 1.5, "line_rule": "auto", "left": 18.0})
check("a style made here takes them too", 'w:line="360"' in lib.values(n3)["_xml"] and 'w:left="360"' in lib.values(n3)["_xml"])
c2 = SE.review(page, mark["id"], {"line": 2.0, "left": 36.0, "bold": False})
check("a character style never takes paragraph settings", c2 is not None and not any(k in lib.values(c2) for k in SL.MORE))
n = sum(checks)
print(f"QT STYLEMORE 4306 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
