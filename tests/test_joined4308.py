"""4.30.8 (Nicholas 2026-11-13 20:55, 20:58): the reader offered the front piece of a joined term, ending in its slash,
as a find of its own beside the whole term: two decisions for one term, one of them never a term. A term joined by a
slash or an ampersand is taken whole; its pieces are not offered; no find ends in a join mark. Made-up terms."""
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
n = sum(checks)
print(f"JOINED 4308 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
