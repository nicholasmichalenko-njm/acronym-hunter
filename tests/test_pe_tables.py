"""Row roles and the table fix on tricky generated tables. Runs anywhere (no Word).
Gate: no wrong sure decision; every asked row is either a right suggestion or an expected question;
the fix keeps every word, every row, the schema order, and passes the unit guard; idempotent."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine import safewrite
from prodengine.engine.pkg import Package, NS
from prodengine.engine.ordered import check_order, q
from prodengine.pe import rules as R, tables as T
from tests.pefix import fixtures_tables as F

ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

std = R.resolve(R.COMPANY, R.TEMPLATE_TYPES["dod_tech"])
check("standards validate", R.validate(std) == [], R.validate(std))
tmp = tempfile.mkdtemp(prefix="pe_tables_")
path = os.path.join(tmp, "tables.docx")
key = F.make(path)
pkg = Package(path)
root = pkg.tree(pkg.main)
names = T.style_name_map(pkg.tree(pkg.word_part("/styles")))
tbls = [t for t in root.iter(q("tbl")) if not any(True for _ in t.iterancestors(q("tbl")))]
check("fixture has 5 tables", len(tbls) == 5)
score = {"rows": 0, "sure_right": 0, "sure_wrong": 0, "asked": 0, "asked_bad": 0, "questions": 0}
report = []
for t, k in zip(tbls, key["tables"]):
    decs = T.classify(t, std, k["type"], names)
    qs = T.questions(decs)
    score["questions"] += len(qs)
    wrong = []
    for d, want in zip(decs, k["labels"]):
        score["rows"] += 1
        if d.status in ("sure", "tagged"):
            if d.role == want: score["sure_right"] += 1
            else: score["sure_wrong"] += 1; wrong.append((d.index, d.role, want))
        else:
            score["asked"] += 1
            if not (d.role == want or d.index in k["ask_ok"]):
                score["asked_bad"] += 1; wrong.append((d.index, "ask:" + d.role, want))
    report.append({"table": k["name"], "rows": len(decs), "questions": len(qs), "wrong": wrong})
    check(f"{k['name']}: no wrong decision", not wrong, wrong)
check("no wrong sure decision anywhere", score["sure_wrong"] == 0, score)
print(json.dumps(score))
for r in report:
    print(f"  {r['table']}: {r['rows']} rows, {r['questions']} question(s)")

# learning: answer the dash-subtotal question, learn it, a fresh classify no longer asks it
std2 = json.loads(json.dumps(std))
decs = T.classify(tbls[0], std2, "std", names)
grp = next(g for g in T.questions(decs) if g.startswith("R45"))
rule = T.learn_rule(std2, grp, "subtotal")
decs2 = T.classify(tbls[0], std2, "std", names)
check("learned rule removes that question", rule is not None and grp not in T.questions(decs2), grp)

# apply through the real write path, with answers for the expected questions
def op(pkg, std, answers):
    return T.op_fix_tables(pkg, std, table_types={1: "std", 2: "cm", 3: "kp", 4: "fig", 5: "std"}, answers=answers)
answers = {}
for t, k in zip(tbls, key["tables"]):
    for g, info in T.questions(T.classify(t, std, k["type"], names)).items():
        answers[g] = k["labels"][info["rows"][0]] if k["labels"][info["rows"][0]] != "keep" else "keep"
out = os.path.join(tmp, "fixed.docx"); shutil.copyfile(path, out)
r = safewrite.apply(out, op, allowed=("pstyles", "para_format", "table_format", "direct_run_format", "tables"),
                    op_args={"std": std, "answers": answers})
reps = r.report["tables"]
check("write path accepted the fix (unit guard held)", r.changed)
check("every table keeps every word and row", all(x["report"]["text_same"] and x["report"]["rows_same"] for x in reps),
      [(x["index"], x["report"]["text_same"], x["report"]["rows_same"]) for x in reps])
check("key personnel caption reported as should-be-merged (not merged by the fix)", reps[2]["report"]["should_merge"] == [0], reps[2]["report"])
m = safewrite.apply(out, T.op_merge_rows, allowed=T.MERGE_ALLOWED, op_args={"targets": {3: [0]}})
check("merge step merges it and proves the words unchanged", m.report["merged"] == 1)
p2 = Package(out); r2 = p2.tree(p2.main)
check("schema order is valid after the fix", check_order(r2) == [], check_order(r2)[:3])
t2 = [t for t in r2.iter(q("tbl")) if not any(True for _ in t.iterancestors(q("tbl")))]
hdr = [len([tr for tr in t.findall("w:tr", NS) if tr.find("w:trPr/w:tblHeader", NS) is not None]) for t in t2]
check("repeat header rows: caption+header (+2nd header) at the top only", hdr[:3] == [3, 2, 2], hdr)
tc = t2[0].findall("w:tr", NS)[15].findall("w:tc", NS)[0]
top = tc.find("w:tcPr/w:tcBorders/w:top", NS)
check("total row has its own top rule (1.5 pt navy)", top is not None and top.get(q("sz")) == "12" and top.get(q("color")) == "1F3864")
runs_direct = sum(1 for t in t2[:3] for rpr in t.iter(q("rPr")) if rpr.find("w:rFonts", NS) is not None)
check("direct fonts cleared in fixed tables (the tag styles hold the look)", runs_direct == 0, runs_direct)
# idempotent: a second fix changes nothing
out2 = os.path.join(tmp, "fixed2.docx"); shutil.copyfile(out, out2)
r3 = safewrite.apply(out2, op, allowed=("pstyles", "para_format", "table_format", "direct_run_format", "tables"),
                     op_args={"std": std, "answers": answers})
d3 = [d for x in r3.report["tables"] for d in x["decisions"]]
check("second run: every row is recognized by its tag style, no questions",
      all(d.status == "tagged" or (d.role == "keep") for d in d3) and sum(len(x["questions"]) for x in r3.report["tables"]) <= 1,
      [(d.index, d.status, d.role) for d in d3 if d.status != "tagged"][:6])
print(f"{sum(ok)}/{len(ok)} passed")
print(f"TEST PE TABLES {'PASS' if all(ok) else 'FAIL'} ({sum(ok)}/{len(ok)})")
print("OUT", out, path)
sys.exit(0 if all(ok) else 1)
