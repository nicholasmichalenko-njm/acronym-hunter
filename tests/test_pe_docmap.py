"""Caption, TOC, bookmark and cross-reference audit on a planted document. Gate: every planted finding is
reported with its rule, and nothing else is reported."""
import collections, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.pe import rules as R, docmap as D
from tests.pefix import fixtures_doc as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_doc_"), "volume.docx")
expected = F.make(path)
dm = D.build(Package(path), std)
print(dm.stats)
fs = D.audit(dm, std)
got = collections.Counter(f.rule for f in fs)
for f in fs:
    print(f"  {f.rule} {f.severity:7} {f.area:9} p{f.where:<3} {f.what}  -> {f.fix or 'report only'}")
for rule, n in expected.items():
    check(f"{rule} reported {n} time(s)", got.get(rule, 0) == n, got.get(rule, 0))
extra = {r: n for r, n in got.items() if r not in expected}
check("nothing reported that was not planted", not extra, extra)
check("captions found: 6", len(dm.captions) == 6, len(dm.captions))
check("cross-references found: 3", len(dm.xrefs) == 3, len(dm.xrefs))
check("expected numbers follow chapters and appendix letters",
      [c.expected for c in dm.captions] == ["1-1", "1-2", "1-3", "1-4", "2-1", "A-1"], [c.expected for c in dm.captions])
# fixes through the guarded write path, then the audit again
import shutil
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.pe import fixes as X
fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
steps = [("toc field", X.op_toc_field, X.TOC_ALLOWED), ("toc styles", X.op_toc_styles, X.STYLES_ALLOWED),
         ("xref switches", X.op_xref_switches, X.XREF_ALLOWED), ("caption fields", X.op_caption_fields, X.CAPTION_ALLOWED),
         ("caption after number", X.op_caption_after, X.AFTER_ALLOWED), ("scope bookmarks", X.op_scope_reset, X.SCOPE_ALLOWED)]
for name, fn, allowed in steps:
    try:
        r = safewrite.apply(fixed, fn, allowed=allowed, op_args={"std": std})
        check(f"fix '{name}' passes the guard and changes the file", r.changed, r.report)
    except Exception as e:
        check(f"fix '{name}' passes the guard and changes the file", False, str(e)[:300])
pk = Package(fixed)
check("schema order valid after all fixes", check_order(pk.tree(pk.main)) == [] and check_order(pk.tree(pk.word_part("/styles"))) == [])
left = collections.Counter(f.rule for f in D.audit(D.build(pk, std), std))
print("left after fixes:", dict(left))
for rule in ("T2", "T3", "X4", "C2", "C6", "B1"):
    check(f"{rule} gone after its fix", rule not in left, left.get(rule))
check("only report-only or Word-update findings remain", set(left) <= {"C1", "C4", "C7", "T5", "T7", "B3", "X1", "X3"}, set(left))
# idempotent: running the fixes again changes nothing
again = [safewrite.apply(fixed, fn, allowed=allowed, op_args={"std": std}).changed for _n, fn, allowed in steps]
check("second run of every fix changes nothing", not any(again), again)
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE DOCMAP {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path, fixed)
sys.exit(0 if all(ok) else 1)
