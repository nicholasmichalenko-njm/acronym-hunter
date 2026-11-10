"""3.98.0 Change a part (partvariant): a Quick Part's kind on Parts (a table, a callout, a header or footer); the styles
it names and typed formatting that stops them deciding; Let the styles decide; Make a variant (cell padding, widths, row
height, table style, a paragraph style swapped), each a new version that leaves the first as it was; Open in Word on its
own and Bring back as a new version. Fictional files (the Kestrel set)."""
import os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import partlib as PT
import partvariant as PV
import templatelib as TL
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
src = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
gl = os.path.join(tmp, "Kestrel Master.dotx"); with_glossary(src, gl, table_hdr=True)
lib = TL.Library(cfg)
plan = PT.look(gl, lib, work=os.path.join(tmp, "w"))
_d, items = PT.keep(cfg, lib, plan)
by = {i["name"]: i for i in items}
th = by["Table header"]
path, name = PV.source_of(lib, th)
got = PV.load(path, name)
check("a kept Quick Part reads from its own kept file", got is not None and name == "Table header")
check("its kind: a header with a table is a header or footer; the caption a Quick Part",
      PV.kind_of(lib.values(th), got[4]) == "hf" and PV.kind_of(lib.values(by["Table caption"])) == "quick")
check("a part in the Tables gallery is a table", PV.kind_of({"gallery": "tbls"}) == "tables" and PV.kind_of({"category": "Callouts"}) == "callouts")
t = PV.table_of(path, name)
check("its table as it is: width and columns in inches", t and t["width"] == 6.5 and t["columns"] == [4.0, 2.5], t)
cap = by["Volume cover"]
cp, cn = PV.source_of(lib, cap)
check("the styles a part names", ("heading 1", "paragraph") in PV.styles_used(cp, cn), PV.styles_used(cp, cn))
# typed formatting
def typed_copy():
    def one(dp, _i):
        r = next(r for r in dp.iter(PV.q("r")) if r.find("w:t", PV.NS) is not None)
        r.insert(0, PV.etree.fromstring(f'<w:rPr xmlns:w="{PV.W}"><w:sz w:val="16"/></w:rPr>'))
    p = PV.changed_copy(path, name, one, work=os.path.join(tmp, "t1"))
    return p
tc = typed_copy()
check("typed formatting is found", PV.typed(tc, name) == 1 and PV.typed(path, name) == 0)
v2, st = PV.keep_version(lib, th, tc, "typed")
new, st2 = PV.let_styles_decide(lib, v2)
np_, nn = PV.source_of(lib, new)
check("Let the styles decide: a new version without it; the version before stays", st2 == "version" and PV.typed(np_, nn) == 0
      and PV.typed(PV.source_of(lib, lib.get(v2["id"]))[0], name) == 1 and new["family"] == th["family"])
# a variant
var, st3 = PV.make_variant(lib, th, {"padding": {"top": 0.02, "bottom": 0.02, "left": 0.04, "right": 0.04}, "width": 6.0,
                                     "columns": [3.5, 2.5], "row_height": 0.2, "swap": {"heading 1": "QP Callout"}}, label="compact")
vp, vn = PV.source_of(lib, var)
t2 = PV.table_of(vp, vn)
check("Make a variant: padding, width, columns and row height", t2["padding"] == {"top": 0.02, "bottom": 0.02, "left": 0.04, "right": 0.04}
      and t2["width"] == 6.0 and t2["columns"] == [3.5, 2.5] and t2["row_height"] == 0.2, t2)
check("... a new version with its name; the first as it was", st3 == "version" and var["label"] == "compact"
      and PV.table_of(path, name)["width"] == 6.5 and var["family"] == th["family"])
rows = PT.rows(cfg, "hf", lib)
check("Parts lists it under Headers and footers with its versions as tabs (with the CUI header)", len(rows) == 2
      and [len(r["versions"]) for r in rows if r["family"] == "q:" + th["family"]] == [4], rows)
check("Quick Parts no longer lists it", all(r["family"] != "q:" + th["family"] for r in PT.rows(cfg, "quick", lib)))
sw, _s = PV.make_variant(lib, cap, {"swap": {"heading 1": "QP Callout"}}, label="callout")
check("a paragraph style swapped for another", ("QP Callout", "paragraph") in PV.styles_used(*PV.source_of(lib, sw))
      and ("heading 1", "paragraph") not in PV.styles_used(*PV.source_of(lib, sw)), PV.styles_used(*PV.source_of(lib, sw)))
# Open in Word, Bring back
out = PV.export(lib, th, os.path.join(tmp, "open"))
with zipfile.ZipFile(out) as z:
    doc = z.read("word/document.xml").decode()
check("Open in Word: the part on its own in a small Word file", out.endswith("Table header.docx") and "w:tbl" in doc and "RFP 123" in doc)
doc2 = doc.replace("RFP 123", "RFP 456")
with zipfile.ZipFile(out) as z:
    allf = {n: z.read(n) for n in z.namelist()}
allf["word/document.xml"] = doc2.encode()
saved = os.path.join(tmp, "saved.docx")
with zipfile.ZipFile(saved, "w") as z:
    for n, b in allf.items():
        z.writestr(n, b)
back, st4 = PV.bring_back(lib, th, saved, label="from Word")
bp, bn = PV.source_of(lib, back)
check("Bring back as a new version: what Word saved", st4 == "version" and "RFP 456" in "".join(
      t.text or "" for t in PV.body(PV.load(bp, bn)[4]).iter(PV.q("t"))) and back["family"] == th["family"])
shutil.rmtree(tmp, ignore_errors=True)
print(f"VARIANT 398 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
