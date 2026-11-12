"""4.23.3: shapes of term the scan passed over, on a made-up page (Nicholas 2026-11-12 13:51: "it's missed things").
One letter and digits given in brackets (C2); initials with periods (U.S.); a small letter before capitals (eMASS).
And two finds that were wrong: the word after a designator read as a unit (F-35 feed), a unit with the sentence's
period as a second term (dB.). What the scan found before stays found. Fictional content (the Kestrel program)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
from docx import Document
import app_gui as A

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


LINES = ["The Department of Defense (DoD) funds the Kestrel Ground Station (KGS).",
         "Command and control (C2) links carry the F-35 feed. The J6 office and section L2 are named without brackets.",
         "Research and development (R&D) follows TCP/IP and U.S. Government rules. The office is in Washington, D.C.",
         "The RFPs list three SOWs. Power is 28 VDC at 10 kHz and 3 dB.",
         "The Program Management Office (PMO) leads; PMO-2 supports. The MoU is signed.",
         "The eMASS record is updated. Test and evaluation (T&E) is led by DT&E staff.",
         "The unit PCU-28V draws 4 A. See CDRL A001."]
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "Kestrel_shapes.docx")
d = Document()
for ln in LINES:
    d.add_paragraph(ln)
d.save(p)
r = A.analyze_batch([p], lambda *a, **k: None)
got = set(r)
check("one letter and digits given in brackets is found: C2", "C2" in got and r["C2"]["category"].startswith("Acronym"), sorted(got))
check("... not the same shape without brackets (J6, L2: too many section labels look like it)", "J6" not in got and "L2" not in got)
check("initials with periods are found: U.S., D.C.", {"U.S.", "D.C."} <= got, sorted(got))
check("a small letter before capitals is found: eMASS", "eMASS" in got)
check("the word after a designator is not a unit: F-35 feed", "feed" not in got and "F-35" in got, sorted(got))
check("a unit with the sentence's period is one term: dB, not dB.", "dB" in got and "dB." not in got)
before = {"DoD", "KGS", "R&D", "TCP/IP", "RFP", "SOW", "VDC", "kHz", "PMO", "PMO-2", "MoU", "T&E", "DT&E", "PCU-28V", "CDRL"}
check("what the scan found before is still found", before <= got, sorted(before - got))
check("a number inside a designator is still not a unit of its own (PCU-28V)", "V" not in got)
check("a real unit after a number is still found (4 A, 28 VDC)", "A" in got or "VDC" in got, sorted(got))
m = A.build_matcher()
check("an ordinary sentence start is not initials (A. B. needs no space between)", not m["dotted_re"].search("Plan A. Before the review"))
check("a word in capitals after a small word is not a small-letter term (toDO is, do NOT is not)", m["lowlead_re"].search("the eCFR text")
      and not m["lowlead_re"].search("do NOT use") and not m["lowlead_re"].search("pre-CDR review"))
k = sum(checks)
print(f"ACR SHAPES 4233 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
