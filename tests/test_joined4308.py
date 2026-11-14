"""4.30.8 (Nicholas 2026-11-13 20:55, 20:58): the reader offered the front piece of a joined term, ending in its slash,
as a find of its own beside the whole term: two decisions for one term, one of them never a term. A term joined by a
slash or an ampersand is taken whole; its pieces are not offered; no find ends in a join mark. Then (21:33) one rule for
every join mark: the joined term or its pieces, never both, with one remembered answer. Made-up terms."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
import acrjoined as J
import app_gui as A

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


t = "The ABCD/EFGH pair."
check("a find cut at its slash becomes the whole joined term", J.whole(t, 4, "ABCD/") == ("ABCD/EFGH", 13))
t = "A WXZ/QPR/JKL chain."
check("a chain of three is one term", J.whole(t, 2, "WXZ/QPR/") == ("WXZ/QPR/JKL", 13))
check("a slash with nothing joined after it is dropped from the find", J.whole("Use the KLM/ port.", 8, "KLM/") == ("KLM", 12))
check("a find with no join mark is as it was", J.whole("The QRX unit.", 4, "QRX") == ("QRX", 7))
check("a joined term that already fits is as it was", J.whole("The TT&C/GNC board.", 4, "TT&C/GNC") == ("TT&C/GNC", 12))
check("a plural keeps its s", J.whole("Two ABCD/EFGHs here.", 4, "ABCD/") == ("ABCD/EFGHs", 14))
long = "The " + "/".join(["LONGNAME"] * 5) + " line."
check("a chain too long to be a term is left alone", J.whole(long, 4, "LONGNAME")[0] == "LONGNAME")

from docx import Document
d = Document()
for line in ["The QRX/ZVB team reports weekly.", "Use the QRX/ZVB interface and the KLM/ port.", "A WXZ/QPR/JKL chain here and WXZ/QPR again.",
             "The TT&C/GNC board met.", "QRX alone too. DCV/JKLM/ ends. The ABCD/EFGH pair and the R/W unit, I/O ports, N/A."]:
    d.add_paragraph(line)
p = os.path.join(tempfile.mkdtemp(), "Osprey.docx"); d.save(p)
A.CANCEL.clear()
res = A.analyze_batch([p], lambda m: None)
got = sorted(res)
check("a scan offers no find that ends or begins with a slash or an ampersand", not [x for x in got if x[:1] in "/&" or x[-1:] in "/&"], got)
check("each joined term is found once, whole", all(x in got for x in ("ABCD/EFGH", "WXZ/QPR/JKL", "QRX/ZVB", "TT&C/GNC", "DCV/JKLM")), got)
check("the pieces inside a joined term are not offered beside it", not any(x in got for x in ("EFGH", "JKL", "ZVB", "C/GNC", "GNC", "JKLM")), got)
check("a piece that also stands alone in the text is still found", "QRX" in got and "KLM" in got and "WXZ/QPR" in got, got)
check("short joined terms are found as before", all(x in got for x in ("R/W", "I/O", "N/A")), got)


# ---- one rule for every join (Option A, 21:33): the joined term or its pieces, never both
def scan(lines, answers=None, known=(), hyphen=False):
    d = Document()
    for line in lines:
        d.add_paragraph(line)
    p = os.path.join(tempfile.mkdtemp(), "Heron.docx"); d.save(p)
    J.ANSWERS, J.KNOWN, J.HYPHEN_WHOLE = dict(answers or {}), set(known), hyphen
    A.CANCEL.clear()
    try:
        return A.analyze_batch([p], lambda m: None)
    finally:
        J.ANSWERS, J.KNOWN, J.HYPHEN_WHOLE = {}, set(), False


for mark in "/&-._":
    j = f"QRXT{mark}ZVBN"
    r = scan([f"The {j} unit ships."])
    check(f"joined by {mark!r} and not known apart: one find, whole", j in r and "QRXT" not in r and "ZVBN" not in r, sorted(r))
    r = scan([f"The {j} unit ships.", "The QRXT team met. The ZVBN team met."])
    check(f"joined by {mark!r}, each piece standing alone elsewhere: the pieces, not the joined term",
          j not in r and "QRXT" in r and "ZVBN" in r and j in (r["QRXT"].get("in_joined") or {}), sorted(r))
    r = scan([f"The {j} unit ships.", "The QRXT team met."])
    check(f"joined by {mark!r}, one piece alone elsewhere: the joined term, and the piece where it stands alone",
          j in r and "QRXT" in r and "ZVBN" not in r and len(r["QRXT"]["locations"]) == 1, sorted(r))
r = scan(["The QRXT/ZVBN unit ships.", "The QRXT team met. The ZVBN team met."], answers={"QRXT/ZVBN": "whole"})
check("answered one term: whole even when each piece stands alone", "QRXT/ZVBN" in r and r["QRXT"]["count"] == 1, sorted(r))
r = scan(["The QRXT/ZVBN unit ships."], answers={"QRXT/ZVBN": "pieces"})
check("answered separate terms: the pieces, with nothing else known", "QRXT/ZVBN" not in r and "QRXT" in r and "ZVBN" in r, sorted(r))
r = scan(["The QRXT/ZVBN unit ships."], known={"QRXT", "ZVBN"})
check("each piece in the effort's list: the pieces", "QRXT/ZVBN" not in r and "QRXT" in r and "ZVBN" in r, sorted(r))
r = scan(["The QRXT-ZVBN unit ships.", "The QRXT team met. The ZVBN team met."], hyphen=True)
check("the effort's hyphen rule still makes a hyphen-joined term whole", "QRXT-ZVBN" in r and r["QRXT"]["count"] == 1, sorted(r))
r = scan(["The QRXT-ZVBN-12 unit ships.", "The QRXT team met. The ZVBN team met."])
check("a number among the pieces: a designator, read as it always was (the whole, and its letters too)",
      "QRXT-ZVBN-12" in r and r["QRXT"]["count"] == 2 and not r["QRXT-ZVBN-12"].get("joined"), sorted(r))
r = scan(["MLI blankets per QRXT-STD-7000 here."])
check("the letters in front of a numbered standard are still found (the accuracy floor)", "QRXT" in r and "QRXT-STD-7000" in r, sorted(r))
r = scan(["The QRX-12 unit and the F-35 one."])
check("letters and a number joined are read as before", "QRX-12" in r and "QRX" in r, sorted(r))
r = scan(["Send it by AND/OR gate, a QRX-based design, the I/O and R&D lines."])
check("ordinary words and single letters joined are read as before", "QRX" in r and "I/O" in r and "R&D" in r, sorted(r))
r = scan(["The QRXTZVBNK system and the QRXTZVBNKLPD one. Nine QRXTZVBNKs came."])
check("a run of nine capitals or more is found", "QRXTZVBNK" in r and "QRXTZVBNKLPD" in r and r["QRXTZVBNK"]["count"] == 2, sorted(r))
r = scan(["The CONTRACTOR shall comply. This is MANDATORY for each SUBSYSTEMX.", "Each contractor has a subsystemx plan."])
check("a long ordinary word in capitals is not offered", not any(x in r for x in ("CONTRACTOR", "MANDATORY", "SUBSYSTEMX")), sorted(r))
r = scan(["Volume III and Phase IIB follow Section IV and Part XII. The IV line and the XI group."])
check("Roman numerals are not offered; IV and XI away from a label still are",
      not any(x in r for x in ("III", "IIB", "XII")) and "IV" in r and "XI" in r and r["IV"]["count"] == 1, {k: v["count"] for k, v in r.items()})
r = scan(["A 3QRX part and 12ZVB part, at 5 MHZ and 10GB."])
check("a term that starts with a digit is one term, not a unit", "3QRX" in r and "12ZVB" in r and "QRX" not in r
      and r["3QRX"]["category"].startswith("Acronym") and "10GB" not in r and "5MHZ" not in r, {k: v["category"] for k, v in r.items()})
n = sum(checks)
print(f"JOINED 4308 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
