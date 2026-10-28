"""2.56.1 a header or footer that repeats on every page is one line of the review, not text missing from it: the text
check and the whole-document page do not add it again, and copies added by 2.55.0 and 2.56.0 are taken out once."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A, compliance as C, textcheck as T, docview as DV, setupdoc as SD, compliance_ui as CU

PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")     # a header on each of its 3 pages
items = C.extract([("Section_L_print.pdf", A.rfp_chunks(PDF))])
heads = [it for it in items if "FA8811-26-R-0099" in it["text"]]
assert len(heads) == 1, "the reader keeps the repeated header once"
r = T.check(PDF, items)
assert not [l for l in r["lines"] if l[2] == "missing" and "FA8811" in l[1]], [l for l in r["lines"] if l[2] == "missing"]
lines = DV.doc_lines(PDF)
res = DV.align(lines, items)
assert not [m for m in DV.missing_runs(lines, res) if "FA8811" in m[0]], DV.missing_runs(lines, res)
assert not any("FA8811" in l for _w, l in lines), "2.57.0: headers and footers are not text of the page view at all"
# copies added before 2.56.1 are taken out once (undecided ones only)
M = C.Matrix(os.path.join(os.path.dirname(PDF), "_none.xlsx"), "K")
M.items = [dict(x) for x in items]
dup = dict(heads[0], id="X-01", new="Added by the text check", decision="")
dup2 = dict(heads[0], id="X-02", new="Added by the text check", decision="Keep")
M.items += [dup, dup2]
fake = types.SimpleNamespace(matrix=M, status=types.SimpleNamespace(configure=lambda **k: None))
n = CU.ComplianceMixin._c_drop_repeats(fake)
assert n == 1 and dup not in M.items and dup2 in M.items, n
assert CU.ComplianceMixin._c_drop_repeats(fake) == 0, "once"
# a PDF's running header read on every page by an older version: the copies are taken out too
M2 = C.Matrix(os.path.join(os.path.dirname(PDF), "_none2.xlsx"), "K")
M2.items = [dict(x) for x in items] + [dict(heads[0], id="Y-01"), dict(heads[0], id="Y-02")]
fake2 = types.SimpleNamespace(matrix=M2, status=types.SimpleNamespace(configure=lambda **k: None))
assert CU.ComplianceMixin._c_drop_repeats(fake2) == 2
print("repeats ok")
