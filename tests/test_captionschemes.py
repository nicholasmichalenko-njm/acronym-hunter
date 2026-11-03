"""3.22.1 caption schemes: each caption rule numbers its way: sequence only (Table 1) or chapter then sequence
(Table 2-1), and its own number as 1, I, i, A or a; the template writes the SEQ field with that switch and passes its
own check; Fix a Copy rewrites a caption field whose format differs."""
import os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodrules as PRL, prodtemplate as PT
from prodengine.pe import fixes2 as X2

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


check("the switch for each format", [X2.seq_format({"number_format": f}) for f in ("ROMAN", "alphabetic", "", "bogus")] == ["ROMAN", "alphabetic", "ARABIC", "ARABIC"])
check("sequence only: no chapter number", X2.caption_instrs({"identifier": "Table", "chapter_level": 0, "number_format": "ROMAN"})
      == (None, "SEQ Table \\* ROMAN"))
check("chapter then sequence", X2.caption_instrs({"identifier": "Figure", "chapter_level": 1, "number_format": "ALPHABETIC"})
      == ("STYLEREF 1 \\s", "SEQ Figure \\* ALPHABETIC \\s 1"))
std = PRL.for_effort(tempfile.mkdtemp())
for c in std["captions"]:
    if c["label"] == "Table" and c["part"] == "body":
        c["chapter_level"] = 0; c["number_format"] = "ROMAN"
tj = PT.make(std, os.path.join(tempfile.mkdtemp(), "out"))
doc = zipfile.ZipFile(tj.copy).read("word/document.xml").decode()
check("the template writes the caption with that scheme", "SEQ Table \\* ROMAN" in doc and "STYLEREF 1 \\s" in doc, re.findall(r"SEQ [^<]+", doc)[:4])
check("the template passes its own check", tj.check.count() == 0 and not [s for s in tj.steps if s.get("refused")],
      ([f["what"][:80] for f in tj.check.findings], [s.get("refused") for s in tj.steps if s.get("refused")]))
std2 = PRL.for_effort(tempfile.mkdtemp())
for c in std2["captions"]:
    if c["label"] == "Table" and c["part"] == "body":
        c["chapter_level"] = 0; c["number_format"] = "ALPHABETIC"
import prodfix as PF
job = PF.run(tj.copy, os.path.join(tempfile.mkdtemp(), "fixed"), std2, {"on": ["caption_fields"], "word_update": False}, open_list=[])
d2 = zipfile.ZipFile(job.copy).read("word/document.xml").decode()
check("Fix a Copy rewrites a caption field whose number format differs", "SEQ Table \\* ALPHABETIC" in d2 and "SEQ Table \\* ROMAN" not in d2,
      re.findall(r"SEQ [^<]+", d2)[:4])
print(f"CAPTION SCHEMES {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
