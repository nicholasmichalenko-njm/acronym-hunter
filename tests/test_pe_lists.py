"""Lists cleanup on a planted document. Gate: every planted finding reported and nothing else; the fix passes the
guarded write path; the words are unchanged except the typed prefixes; questions hold their lists until answered;
answers clear them; a second run changes nothing."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import rules as R, lists as L
from tests.pefix import fixtures_lists as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_lists_"), "lists.docx")
expected = F.make(path)
lm = L.scan(Package(path), std)
fs = L.audit(lm, std)
for f in fs:
    print(f"  {f.rule:4} {f.severity:7} {f.what}  -> {f.fix or 'report only'}")
got = collections.Counter(f.rule for f in fs)
for rule, n in expected.items():
    check(f"{rule} reported {n} time(s)", got.get(rule, 0) == n, got.get(rule, 0))
check("nothing reported that was not planted", not {r for r in got if r not in expected})
check("typed levels: bullet o is level 2, a) is level 2",
      [i.level for i in lm.items if i.marker in ("o", "a")] == [2, 2], [(i.marker, i.level) for i in lm.items])
ask = [b for b in lm.blocks if b.restart == "ask"]
check("one question: list C continues list B", [b.items[0].text for b in ask] == ["Holds reviews"], [(b.id, b.why) for b in ask])
check("typed 4. starts at 4 as typed", any(b.items[0].text.startswith("4.") and b.start == 4 and b.restart == "typed" for b in lm.blocks))

words_before = [" ".join(visible_text(p).replace("¶", " ").split()) for p in Package(path).tree(Package(path).main).iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")]
fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
try:
    r = safewrite.apply(fixed, L.op_lists, allowed=L.LISTS_ALLOWED, op_args={"std": std})
    check("fix (no answers) passes the guard", r.changed, r.report)
    print("  ", r.report)
except Exception as e:
    check("fix (no answers) passes the guard", False, str(e)[:400])
pk = Package(fixed)
check("schema order valid", check_order(pk.tree(pk.main)) == [] and check_order(pk.tree(pk.word_part("/numbering"))) == [])
after = [" ".join(visible_text(p).replace("¶", " ").split()) for p in pk.tree(pk.main).iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")]
import re
strip = re.compile(r"^(• |o |\[sym:F0B7\] |\d\. |a\) |2\.1 )")
held_typed = set()
diffs = [(a, b) for a, b in zip(words_before, after) if a != b and strip.sub("", a) != b]
check("only typed prefixes left the text", not diffs, diffs[:4])
check("the list waiting for an answer is unchanged", "Holds reviews" in after)
lm2 = L.scan(pk, std)
left = collections.Counter(f.rule for f in L.audit(lm2, std))
print("  left:", dict(left))
check("after the fix: only the question and report-only findings", set(left) <= {"L5?", "L7", "L8"}, set(left))
asks = [b for b in lm2.blocks if b.restart == "ask"]
print("  questions now:", [(b.id, b.why, b.shows_from) for b in asks])
# answer: restart list C; the typed 4. then lands on 4 by itself
ans = {b.id: "restart" for b in asks if b.items[0].text == "Holds reviews"}
r = safewrite.apply(fixed, L.op_lists, allowed=L.LISTS_ALLOWED, op_args={"std": std, "answers": ans})
check("fix with the answer passes the guard", r.changed, r.report)
lm3 = L.scan(Package(fixed), std)
left3 = collections.Counter(f.rule for f in L.audit(lm3, std))
print("  left after the answer:", dict(left3), [(b.id, b.restart, b.shows_from, b.items[0].text) for b in lm3.blocks if b.numbered])
check("after the answer only report-only findings remain", set(left3) <= {"L7", "L8"}, set(left3))
check("the continued list shows 4 as the writer typed", any(b.items[0].text == "Close out" and b.shows_from == 4 for b in lm3.blocks))
check("every list after the first has its own explicit start", all(b.restart in ("first", "done") for b in lm3.blocks if b.numbered),
      [(b.id, b.restart) for b in lm3.blocks if b.numbered])
again = safewrite.apply(fixed, L.op_lists, allowed=L.LISTS_ALLOWED, op_args={"std": std, "answers": ans})
check("second run changes nothing", not again.changed, again.report)
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE LISTS {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path, fixed)
sys.exit(0 if all(ok) else 1)
