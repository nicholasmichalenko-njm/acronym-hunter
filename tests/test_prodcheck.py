"""3.5.0 production standards and Format Check, without screens: the standards (built-in, team types, an effort's
values from the RFP's formatting rules), fonts as Word resolves them (defaults, theme, table style against Normal,
paragraph and character styles, typed formatting), margins and page size by section, captions (typed numbers,
numbering scheme, separator, table caption placement), the table of contents, typed lists, page numbers; and the gate:
the original file's bytes and date never change."""
import hashlib, os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodstd as PS, prodcheck as PC, prod_fixture as FX
from openpyxl import load_workbook

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def fingerprint(p):
    st = os.stat(p)
    return hashlib.sha256(open(p, "rb").read()).hexdigest(), st.st_mtime_ns, st.st_size


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg")
data = PS.load(cfg)
check("the built-in proposal volume standard", data["types"][0]["name"] == "Proposal volume" and data["default"] == "Proposal volume")
t2 = PS.merge(data["types"][0], {"name": "Cost volume", "fonts": {"table": {"min": 8}}})
data["types"].append(t2); data["default"] = "Cost volume"; PS.save(cfg, data)
d2 = PS.load(cfg)
check("team document types saved; a merge keeps what it does not set", [t["name"] for t in d2["types"]] == ["Proposal volume", "Cost volume"]
      and d2["default"] == "Cost volume" and PS.get(d2, "Cost volume")["fonts"]["table"] == {"font": "Arial", "min": 8, "max": 10})
rows = [{"kind": "Format", "subject": "Font", "value": "12-point Times New Roman"},
        {"kind": "Format", "subject": "Font in tables and figures", "value": "8-point, no smaller"},
        {"kind": "Format", "subject": "Margins", "value": "1-inch margins"}, {"kind": "Format", "subject": "Page size", "value": "8.5 x 11"}]
over, said = PS.from_rfp(rows)
check("the RFP's formatting rules become the effort's values", over["fonts"]["body"] == {"min": 12.0, "max": 12.0, "font": "Times New Roman"}
      and over["fonts"]["table"]["min"] == 8.0 and over["fonts"]["table"]["max"] == 0 and over["margins_in"] == 1.0 and over["page"] == "Letter"
      and len(said) == 4, over)


class WS:
    def __init__(self, d): self.d = d
    def get(self, k, default=None): return self.d.get(k, default)


eff = PS.for_effort(cfg, WS({"prod_std": {"type": "Proposal volume", "over": {"fonts": {"table": {"min": 8, "max": 0}}}}}))
check("an effort's standard: its type with its own values on top", eff["name"] == "Proposal volume" and eff["fonts"]["table"]["min"] == 8
      and eff["fonts"]["body"]["font"] == "Times New Roman")
# the draft
src = FX.build(os.path.join(tmp, "Volume I.docx"))
before = fingerprint(src)
time.sleep(0.05)
r = PC.check(src, PS.DEFAULT)
after = fingerprint(src)
check("THE GATE: the original's bytes, date and size are unchanged after a check", before == after)
F = r["findings"]
by = lambda area: [f for f in F if f["area"] == area]   # noqa: E731
doc = PC.Doc(src)
check("fonts as Word resolves them: theme defaults, Normal, headings", doc.defaults == {"font": "Calibri", "size": 11.0}
      and doc.style_value("Heading2", "font") == ("Arial", "Heading1") and doc.style_value("Heading2", "size") == (14.0, "Heading2"))
check("a table left in Normal takes the table style's font (Word's rule): no table finding", not any(f["problem"].startswith("Table:") for f in by("Fonts")),
      [f["problem"] for f in by("Fonts")])
fonts = {f["problem"]: f["detail"] for f in by("Fonts")}
check("a font typed over the style is found, and says so", any("font Calibri" in k and "typed over the style" in v for k, v in fonts.items()), fonts)
check("a size typed below the smallest allowed", any("9 pt (smallest allowed 12)" in k for k in fonts))
check("headings are not held to the body rule", not any("Arial" in k and k.startswith("Body") for k in fonts))
pages = [f["problem"] for f in by("Pages")]
check("page size and margins by section", any("should be Letter" in p for p in pages) and any("right 0.50 in" in p for p in pages)
      and all(f["where"] == "Section 2" for f in by("Pages")), pages)
caps = [f["problem"] for f in by("Captions")]
check("a typed caption number (not a field) is found; one made of fields is not", any(p.startswith("Table 1-1: number typed") for p in caps)
      and not any(p.startswith("Table 1-2") for p in caps), caps)
check("numbering scheme and separator", any("Figure 3: plain number" in p for p in caps) and any("Figure 3: a space after the number" in p for p in caps))
check("a table whose caption is not in its first row", any(p.startswith("The 2nd table: caption above it") for p in caps))
toc = [f["problem"] for f in by("Table of contents")]
check("TOC: forbidden switches and hand-typed lines", any("uses \\o, \\u" in p for p in toc) and any("1 table-of-contents line" in p for p in toc), toc)
check("typed bullets and numbers, a real list left alone", by("Lists")[0]["problem"].startswith("2 typed") and len(by("Lists")) == 1)
check("a typed page number in a footer", [f["problem"] for f in by("Page numbers")] == ["page number typed, not a PAGE field"])
check("each finding says where it is", by("Lists")[0]["where"] == "1.1 Approach")
s2 = PS.merge(PS.DEFAULT, {"caption_numbers": "plain", "caption_sep": "space", "caption_position": "above", "toc_forbid": [], "page_numbers": False,
                           "margins_in": 0.5, "page": "", "fonts": {"body": {"font": "", "min": 0, "max": 0}}})
s2["page"] = "A4"
r2 = PC.check(src, s2, areas=["Captions", "Table of contents", "Page numbers", "Pages", "Fonts"])
check("a different standard gives different findings", not any("space after" in f["problem"] for f in r2["findings"])
      and not r2["counts"]["Page numbers"] and not any("uses \\o" in f["problem"] for f in r2["findings"])
      and any("a tab after the number; the standard uses a space" in f["problem"] for f in r2["findings"]), [f["problem"] for f in r2["findings"]])
bad = os.path.join(tmp, "bad.docx"); open(bad, "wb").write(b"not a zip")
check("a file that is not a Word document says so", PC.check(bad, PS.DEFAULT)["error"] == "does not open as a Word document")
x = PC.export(os.path.join(tmp, "fc.xlsx"), [r], "Kestrel")
check("the workbook", load_workbook(x).active.max_row == len(F) + 1)
check("THE GATE, again after every check above", fingerprint(src) == before)
n = sum(checks)
print(f"PROD CHECK {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
