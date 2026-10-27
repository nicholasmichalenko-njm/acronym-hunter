"""2.50.0 fixes from the feedback report: PDFium's line-break hyphen (U+FFFE, shown as a box and refused by Excel)
becomes a hyphen; a matrix with it loads clean and exports; an effort name with / or : still exports together."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C, matrixdesign as MD
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


check("the line-break hyphen becomes a hyphen", C.clean_chars("state-of￾the-art") == "state-of-the-art")
check("control characters go", C.clean_chars("a\x0bb\x00c") == "abc" and C.clean_chars(5) == 5)
tmp = tempfile.mkdtemp()
M = C.Matrix(os.path.join(tmp, "K_Matrix.xlsx"), "K")
M.items = C.extract([("Section L.docx", [("Page 1", "L.4 Technical\nThe Offeror shall describe the long￾term plan.")])])
M.items[0]["text"] = "The Offeror shall describe the long￾term plan."
M.items[0]["decision"] = "Keep"
M.outline = C.parse_outline("Volume I\n1.1 Plan")
M.save()
M2 = C.Matrix(M.path).load()
check("a matrix saves and loads with the hyphen", any("long-term" in it["text"] for it in M2.items), [it["text"] for it in M2.items])
M2.items[0]["text"] = "The Offeror shall describe the long￾term plan."
res = MD.export_together(M2, tmp, MD.default(), "FA8810/26: Kestrel")
check("an effort name with / and : exports together", os.path.isfile(res["files"][0]) and "/" not in os.path.basename(res["folder"])
      and ":" not in os.path.basename(res["files"][0]), res["files"])
check("safe names", MD.safe_name('a<b>:c"d/e\\f|g?h*') == "a b  c d e f g h" and MD.safe_name("...") == "export")
n = sum(checks)
print(f"HYPHEN EXPORT PASS ({n}/{len(checks)})" if n == len(checks) else f"HYPHEN EXPORT FAIL ({n}/{len(checks)})")
