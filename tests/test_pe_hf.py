"""Header and footer builder on the planted sections volume. Gate: after the chapter breaks, the page numbers, the
margins and the header and footer build, the pages audit is clean; fields declared exactly; old parts removed;
the body text is unchanged; a second build is stable (same content, no new findings)."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import rules as R, sections as S, hf as H
from tests.pefix import fixtures_sections as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_hf_"), "volume.docx")
F.make(path)
pk0 = Package(path); body0 = visible_text(pk0.tree(pk0.main))
for name, fn, al in [("chapter breaks", S.op_chapter_breaks, S.CHAPTER_ALLOWED), ("page numbers", S.op_page_numbers, S.NUMBERS_ALLOWED),
                     ("margins", S.op_page_setup, S.SETUP_ALLOWED), ("headers and footers", H.op_hf_build, H.HF_ALLOWED)]:
    try:
        r = safewrite.apply(path, fn, allowed=al, op_args={"std": std})
        check(f"'{name}' passes the guard", r.changed, r.report)
        if fn is H.op_hf_build:
            print("   made", r.report["made"], "removed", r.report["removed"]); made_first = list(r.report["made"])
    except Exception as e:
        check(f"'{name}' passes the guard", False, str(e)[:500])
pk = Package(path)
check("body text unchanged", visible_text(pk.tree(pk.main)) == body0)
sm = S.map_sections(pk, std)
for s in sm.sections:
    print(f"   {s.i} {s.part:8} reads {s.shows:5} header{'(own)' if s.headers['default'].own else '(linked)'}: {s.headers['default'].text!r} "
          f"footer fields {s.footers['default'].fields}")
left = S.audit(sm, std)
for f in left:
    print("   left:", f.rule, f.what)
check("pages audit clean after the build", not left, [f.rule for f in left])
check("cover has an empty header and footer of its own", sm.sections[0].headers["default"].own and sm.sections[0].headers["default"].text == "")
check("the landscape page is linked", all(not s.footers["default"].own for s in sm.sections if s.orient == "landscape"))
check("every numbered page has a PAGE field", all("PAGE" in s.footers["default"].fields for s in sm.sections if s.part != "cover"))
check("schema order valid in every story", all(check_order(pk.tree(x)) == [] for x in pk.stories()))
r2 = safewrite.apply(path, H.op_hf_build, allowed=H.HF_ALLOWED, op_args={"std": std})
sm2 = S.map_sections(Package(path), std)
check("a second build gives the same headers and footers", [(s.headers["default"].text, s.footers["default"].text) for s in sm2.sections] ==
      [(s.headers["default"].text, s.footers["default"].text) for s in sm.sections])
check("a second build leaves no orphan parts", len([n for n in Package(path).raw if n.startswith(("word/header", "word/footer"))]) == len(made_first),
      sorted(n for n in Package(path).raw if n.startswith(("word/header", "word/footer"))))
check("3.6.0: a second build changes nothing at all", r2.changed is False and r2.report.get("unchanged") is True)
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE HF {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path)
sys.exit(0 if all(ok) else 1)
