"""4.24.0: four more shapes of term for the scan (Nicholas 2026-11-12, answer 15: all four): a digit before one capital
(5G, 3D); a known unit with no number before it (mA, pH); a hyphenated name (Wi-Fi); a small letter before one capital
(xApp, iPad). Each keeps to the shape that is rarely anything else: a label (section 3B), a number and a unit written
together (4A), a word with a prefix (Re-Do) and a slip of the keys (tHe) are left alone. What the scan found before
stays found. A term with no definition is exported with an empty definition (answer 16). Fictional content."""
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


LINES = ["The Kestrel Ground Station (KGS) uses a 5G link and 3D models of the site.",
         "See section 3B and option 2A. The heater draws 4A at 28 VDC.",
         "Current is given in mA and acidity in pH. The gain is 12 dBm and the margin is quoted in dB.",
         "The Wi-Fi network is closed. We will Re-Do the survey. Co-Op students help.",
         "An xApp runs on the controller and each crew has an iPad. Then tHe review starts.",
         "The plan has a 2Q review after a 7X upgrade and the 4K display.",
         "The Program Management Office (PMO) leads; the MoU is signed; eMASS is updated; U.S. rules apply (C2)."]
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "Kestrel_shapes2.docx")
d = Document()
for ln in LINES:
    d.add_paragraph(ln)
d.save(p)
r = A.analyze_batch([p], lambda *a, **k: None)
got = set(r)
check("a digit before one capital is found: 5G, 3D, 4K", {"5G", "3D", "4K"} <= got, sorted(got))
check("... and its letter is not a unit of its own (G, D, K)", not ({"G", "D", "K"} & got), sorted(got))
check("... one that describes a thing is found (a 7X upgrade, a 2Q review)", {"7X", "2Q"} <= got, sorted(got))
check("a label is left alone: section 3B, option 2A", "3B" not in got and "2A" not in got, sorted(got))
check("a number and a unit written together stays a unit: 4A", "4A" not in got and "A" in got, sorted(got))
check("a known unit with no number before it is found: mA, pH, dB", {"mA", "pH", "dB"} <= got
      and all(r[u]["category"].startswith("Unit") for u in ("mA", "pH")), sorted(got))
check("a unit after a number is found once, as before: dBm", "dBm" in got)
check("a hyphenated name is found: Wi-Fi", "Wi-Fi" in got and r["Wi-Fi"]["category"].startswith("Acronym"), sorted(got))
check("... a word with a prefix is not: Re-Do, Co-Op", "Re-Do" not in got and "Co-Op" not in got)
check("a small letter before one capital is found: xApp, iPad", {"xApp", "iPad"} <= got, sorted(got))
check("... a slip of the keys is not: tHe", "tHe" not in got)
before = {"KGS", "VDC", "PMO", "MoU", "eMASS", "U.S.", "C2"}
check("what the scan found before is still found", before <= got, sorted(before - got))
m = A.build_matcher()
check("a decimal, a date and a part number are not digit terms (1.5G, 2026-11-3A, PN 4521-3A)",
      not any(A.digit_term(t, x) for t in ("a 1.5G load", "on 2026-11-3A here", "PN 4521-3A unit")
              for x in m["digitlead_re"].finditer(t)))
n = sum(checks)
print(f"TEST ACRSHAPES 4240 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
