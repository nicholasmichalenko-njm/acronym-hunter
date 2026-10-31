"""Terms on a planted document. Gate: every planted hit, nothing else; field results skipped; the fix keeps run
formatting and changes only the matched words; banned phrases change only with a yes; dictionaries are written as
Word reads them."""
import collections, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package
from prodengine.engine import safewrite
from prodengine.engine.ordered import check_order
from prodengine.pe import rules as R, terms as T
from tests.pefix import fixtures_terms as F
from docx import Document

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY)
path = os.path.join(tempfile.mkdtemp(prefix="pe_terms_"), "terms.docx")
expected = F.make(path)
hits = T.scan(Package(path), std)
for h in hits:
    print(f"  {h.rule} {h.story:22} p{h.para} {h.found!r} -> {h.suggest!r}")
got = collections.Counter(h.rule for h in hits)
for rule, n in expected.items():
    check(f"{rule}: {n} hit(s)", got.get(rule, 0) == n, got.get(rule, 0))
check("nothing else", not {r for r in got if r not in expected})
check("the TOC field result is not searched", not any(h.found == "recieve" and h.para == 0 for h in hits))
check("a phrase split across runs is found", any(h.found == "in order to" for h in hits))
check("capital kept in the suggestion", any(h.found == "Seperate" and h.suggest == "Separate" for h in hits))
fs = T.audit(hits)
for f in fs:
    print(f"  {f.rule} {f.what} -> {f.fix or 'report only'}")

fixed = path.replace(".docx", "_fixed.docx"); shutil.copyfile(path, fixed)
r = safewrite.apply(fixed, T.op_terms, allowed=T.TERMS_ALLOWED, op_args={"std": std})
check("Fix all (misspellings and marks) passes the guard", r.changed, r.report)
d = Document(fixed)
texts = [p.text for p in d.paragraphs]
check("misspellings fixed in body and header", "Separate the data from the model." in texts and
      d.sections[0].header.paragraphs[0].text.startswith("Separate volume"), texts)
check("bold run kept on the replaced word", any(r_.text == "receive" and r_.bold for p in d.paragraphs for r_ in p.runs))
check("TM on first use only", texts.count("Kestrel Mission Suite™ runs the ground segment.") == 1 and
      "Kestrel Mission Suite also plans passes." in texts, texts)
check("R added where it was missing", "OrbitLink® carries the data; OrbitLink® routes it." in texts)
check("banned phrases untouched without a yes", "We will utilize a world-class approach." in texts)
check("the name near miss untouched without a yes", any(t.startswith("Jordon Reyes") for t in texts))
check("the TOC field result untouched", any("How we recieve data" in t for t in texts), texts[:2])
hits2 = T.scan(Package(fixed), std)
yes = [h.id for h in hits2 if h.rule in ("W1", "W4") and h.suggest]
r2 = safewrite.apply(fixed, T.op_terms, allowed=T.TERMS_ALLOWED, op_args={"std": std, "accept": (), "hit_ids": yes})
check("the reviewed yes answers pass the guard", r2.changed, r2.report)
texts = [p.text for p in Document(fixed).paragraphs]
check("suggestions applied: use, to, the name", "We will use a world-class approach." in texts and
      "The team works to deliver on time." in texts and any(t.startswith("Jordan Reyes") for t in texts), texts)
left = collections.Counter(h.rule for h in T.scan(Package(fixed), std))
check("only the banned word with no suggestion remains", dict(left) == {"W1": 1}, dict(left))
again = safewrite.apply(fixed, T.op_terms, allowed=T.TERMS_ALLOWED, op_args={"std": std})
check("second Fix all changes nothing", not again.changed)
pk = Package(fixed)
check("schema order valid", all(check_order(pk.tree(s)) == [] for s in pk.stories()))
# dictionaries
out = tempfile.mkdtemp(prefix="pe_dic_")
rep = T.export_dictionaries(std, out)
print("  ", rep)
raw = open(os.path.join(out, "PE_Names.dic"), "rb").read()
check(".dic is UTF-16 LE with a byte order mark", raw[:2] == b"\xff\xfe")
words = raw[2:].decode("utf-16-le").split("\r\n")
check("names are split into words", "Reyes" in words and "Jordan" in words and "Jordan Reyes" not in words)
lex = open(os.path.join(out, "ExcludeDictionaryEN0409.lex"), "rb").read()[2:].decode("utf-16-le").split("\r\n")
check("the exclusion file holds single banned words only", "utilize" in lex and "seamless" in lex and "in order to" not in lex and "world-class" not in lex)
check("phrases are listed as kept in the app check", "in order to" in rep["phrases_kept_in_app"])
# superscript marks: the TM goes in its own superscript run; the words around it keep their run
import copy as _c
std_sup = _c.deepcopy(std)
for r_ in std_sup["terms"]["replace"]:
    if r_["find"] in ("Kestrel Mission Suite", "OrbitLink"):
        r_["superscript"] = True
sup = path.replace(".docx", "_sup.docx"); shutil.copyfile(path, sup)
r3 = safewrite.apply(sup, T.op_terms, allowed=T.TERMS_ALLOWED, op_args={"std": std_sup})
check("superscript marks pass the guard", r3.changed, r3.report)
d = Document(sup)
sups = [(r_.text, r_.font.superscript) for p_ in d.paragraphs for r_ in p_.runs if r_.text in ("\u2122", "\u00ae")]
print("   mark runs:", sups)
check("each added mark is its own superscript run", sups.count(("\u2122", True)) == 1 and ("\u00ae", True) in sups, sups)
check("text reads the same as the plain fix", "Kestrel Mission Suite\u2122 runs the ground segment." in [p_.text for p_ in d.paragraphs])
check("second run with superscript marks changes nothing", not safewrite.apply(sup, T.op_terms, allowed=T.TERMS_ALLOWED, op_args={"std": std_sup}).changed)
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE TERMS {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("FILES", path, fixed)
sys.exit(0 if all(ok) else 1)
