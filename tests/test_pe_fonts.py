"""Font compliance on a planted document. Gate: every planted group reported with its source (hand or style),
nothing else; Fix all removes only the hand formatting that breaks a rule; the style fix clears the rest; no text
changes; a second run changes nothing."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.pe import rules as R, fonts as Fo
from tests.pefix import fixtures_fonts as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY, effort={"fonts": F.RULES})
path = os.path.join(tempfile.mkdtemp(prefix="pe_fonts_"), "fonts.docx")
expected = F.make(path)
runs = Fo.scan(Package(path), std)
fs = Fo.audit(runs, std)
for f in fs:
    print(f"  {f.rule:4} {f.what}  -> {f.fix}")
got = collections.Counter(f.rule for f in fs)
for rule, n in expected.items():
    check(f"{rule}: {n} group(s)", got.get(rule, 0) == n, got.get(rule, 0))
check("nothing else", not {r for r in got if r not in expected}, dict(got))
check("scopes found: body, table, caption, header", {r.scope for r in runs} >= {"body", "table", "caption", "header_footer"})
check("Wingdings and hidden text skipped", not any(r.font == "Wingdings" or r.size == 6 for r in runs))
check("hand formatting over a good style is Fix all", all(f.fix == "op_fonts" for f in fs if f.rule in ("F1",)))
check("a hand 8 pt over an 8.5 pt style needs the style fix", any(f.rule == "F2" and f.fix == "op_font_styles" and "Table" in f.what for f in fs))
fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
r = safewrite.apply(fixed, Fo.op_fonts, allowed=Fo.FONTS_ALLOWED, op_args={"std": std})
check("Fix all passes the guard (formatting only)", r.changed, r.report)
left = collections.Counter(f.rule for f in Fo.audit(Fo.scan(Package(fixed), std), std))
print("  left after Fix all:", dict(left))
check("hand formatting groups that could be fixed are gone", "F1" not in left and left.get("F2", 0) == 1, dict(left))
r = safewrite.apply(fixed, Fo.op_font_styles, allowed=Fo.FONTS_ALLOWED, op_args={"std": std})
check("the style fix passes the guard", r.changed, r.report)
r = safewrite.apply(fixed, Fo.op_fonts, allowed=Fo.FONTS_ALLOWED, op_args={"std": std})
left = collections.Counter(f.rule for f in Fo.audit(Fo.scan(Package(fixed), std), std))
print("  left after the style fix and Fix all:", dict(left))
check("all clean", not left, dict(left))
again = [safewrite.apply(fixed, fn, allowed=(), op_args={"std": std}).changed for fn in (Fo.op_fonts, Fo.op_font_styles)]
check("second run changes nothing", not any(again), again)
pk = Package(fixed)
check("schema order valid", all(check_order(pk.tree(s)) == [] for s in pk.stories()) and check_order(pk.tree(pk.word_part("/styles"))) == [])
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE FONTS {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path, fixed)
sys.exit(0 if all(ok) else 1)
