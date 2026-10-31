"""Pages, sections, headers and footers on a planted volume. Gate: every planted finding is reported, nothing else;
each engine fix passes the guarded write path; what remains is only Word work (link, marking) or report-only."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.pe import rules as R, sections as S
from tests.pefix import fixtures_sections as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_sec_"), "volume.docx")
expected = F.make(path)
sm = S.map_sections(Package(path), std)
check("six sections found", len(sm.sections) == 6, len(sm.sections))
check("parts: cover, front, body x3, appendix", [s.part for s in sm.sections] == ["cover", "front", "body", "body", "body", "appendix"],
      [s.part for s in sm.sections])
fs = S.audit(sm, std)
for f in fs:
    print(f"  {f.rule} {f.severity:7} {f.what}  -> {f.fix or 'report only'}")
got = collections.Counter(f.rule for f in fs)
for rule, n in expected.items():
    check(f"{rule} reported {n} time(s)", got.get(rule, 0) == n, got.get(rule, 0))
check("nothing reported that was not planted", not {r for r in got if r not in expected}, {r: n for r, n in got.items() if r not in expected})

fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
steps = [("chapter breaks", S.op_chapter_breaks, S.CHAPTER_ALLOWED, {"std": std}),
         ("page numbers", S.op_page_numbers, S.NUMBERS_ALLOWED, {"std": std}),
         ("page setup", S.op_page_setup, S.SETUP_ALLOWED, {"std": std}),
         ("header text", S.op_hf_text, S.HF_TEXT_ALLOWED, {"std": std, "old": "Volume II Management", "new": "Volume I Technical"}),
         ("PAGE field switches", S.op_page_field_clean, S.PAGE_FIELD_ALLOWED, {})]
for name, fn, allowed, args in steps:
    try:
        r = safewrite.apply(fixed, fn, allowed=allowed, op_args=args)
        check(f"fix '{name}' passes the guard and changes the file", r.changed, r.report)
    except Exception as e:
        check(f"fix '{name}' passes the guard and changes the file", False, str(e)[:400])
pk = Package(fixed)
check("schema order valid after all fixes", check_order(pk.tree(pk.main)) == [])
sm2 = S.map_sections(pk, std)
check("seven sections after the chapter break", len(sm2.sections) == 7, len(sm2.sections))
print("  shows:", [(s.part, s.first_style, s.shows) for s in sm2.sections])
check("chapter 2 now starts its own section and restarts", any(s.first_text == "Technical Approach" and s.numbers.get("start") == "1"
                                                              for s in sm2.sections))
check("headers kept on the pages before the new break",
      [s.headers["default"].text for s in sm2.sections][2:4] == ["Volume I Technical", "Volume I Technical"],
      [s.headers["default"].text for s in sm2.sections])
left = collections.Counter(f.rule for f in S.audit(sm2, std))
print("  left after fixes:", dict(left))
check("only Word work or report-only findings remain", set(left) <= {"P6", "P8", "P10"}, set(left))
again = [safewrite.apply(fixed, fn, allowed=allowed, op_args=args).changed for _n, fn, allowed, args in steps]
check("second run of every fix changes nothing", not any(again), again)
# the other presets map the same file without errors and give their own expectations
for key in ("caps_roman_continuous", "straight"):
    st2 = R.resolve(R.COMPANY, effort={"pagination": R.PAGINATION_PRESETS[key]})
    m = S.map_sections(Package(path), st2)
    print(f"  preset {key}:", [(s.part, s.expected) for s in m.sections])
    check(f"preset {key} maps and audits", isinstance(S.audit(m, st2), list))
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE SECTIONS {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path, fixed)
sys.exit(0 if all(ok) else 1)
