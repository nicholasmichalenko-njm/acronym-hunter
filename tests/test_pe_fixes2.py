"""Round 4 fixes on the planted volume of test_pe_docmap: typed caption to fields (C1), list scope by identifier
(T5), cross-reference relink (X1). Gate: each passes the guard with exactly its declared field changes, the visible
text of the caption is unchanged, its finding is gone, and a second run changes nothing."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import rules as R, docmap as D, fixes2 as X2
from tests.pefix import fixtures_doc as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_fx2_"), "volume.docx")
F.make(path)
before = collections.Counter(f.rule for f in D.audit(D.build(Package(path), std), std))
pk0 = Package(path)
text0 = visible_text(pk0.tree(pk0.main))
fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
steps = [("typed caption to fields", X2.op_caption_typed, X2.CAPTION_TYPED_ALLOWED, {"std": std}),
         ("lists by identifier", X2.op_toc_list_identifiers, X2.LIST_ALLOWED, {"std": std}),
         ("relink the broken reference", X2.op_xref_relink, X2.RELINK_ALLOWED, {"std": std, "mapping": {"_Ref999999999": "_Ref100000003"}})]
for name, fn, al, args in steps:
    try:
        r = safewrite.apply(fixed, fn, allowed=al, op_args=args)
        check(f"'{name}' passes the guard", r.changed, r.report)
        print("   ", {k: v for k, v in r.report.items() if k != "checks"})
    except Exception as e:
        check(f"'{name}' passes the guard", False, str(e)[:400])
pk = Package(fixed)
check("visible text of the whole body unchanged", visible_text(pk.tree(pk.main)) == text0)
dm = D.build(pk, std)
after = collections.Counter(f.rule for f in D.audit(dm, std))
print("  before:", dict(before), "\n  after: ", dict(after))
check("C1 gone (the caption is now fields)", "C1" not in after)
check("T5 gone (no bookmark scope)", "T5" not in after)
check("X1 gone and the unused target is now used (B3 gone)", "X1" not in after and "B3" not in after)
check("the converted caption reads the same and is a field caption", any(c.label == "Table" and c.shown == "1-3" and not c.typed for c in dm.captions),
      [(c.shown, c.typed) for c in dm.captions])
check("schema order valid", check_order(pk.tree(pk.main)) == [])
again = [safewrite.apply(fixed, fn, allowed=al, op_args=args).changed for _n, fn, al, args in steps[:2]]
check("second run changes nothing", not any(again), again)
try:
    safewrite.apply(fixed, X2.op_xref_relink, allowed=X2.RELINK_ALLOWED, op_args={"std": std, "mapping": {"_Ref100000001": "_RefNOPE"}})
    check("relink to a target that does not exist is refused", False)
except Exception as e:
    check("relink to a target that does not exist is refused", "not a bookmark" in str(e), str(e)[:200])
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE FIXES2 {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
sys.exit(0 if all(ok) else 1)
