"""3.79.0 the drift report without a screen: a dated copy with tracked changes beside a fictional draft (the Kestrel
technical volume); the author takes one change into the draft, rewrites another passage and leaves a third; the report
says Taken up, The passage changed and Still to take, counts the paragraphs changed since the copy, and advises making
the copy again once the draft has moved on. Fictional content."""
import datetime, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import wordlab as WL
import drift as DR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
draft = os.path.join(tmp, "Kestrel Volume II.docx")
shutil.copy2(os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx"), draft)
paras = WL.docx_paragraphs(draft)


def change(i, hit, fix):
    s = paras[i].index(hit)
    return {"para": i, "start": s, "end": s + len(hit), "hit": hit, "fix": fix, "on": True, "rule": "plain words", "why": ""}


chs = [change(4, "propellant", "fuel"), change(5, "flight software", "onboard code"), change(6, "w/o", "without")]
when = datetime.datetime(2026, 11, 6, 21, 30)
res = WL.to_copy(draft, chs, when=when)
check("the copy is made beside the draft with its date", os.path.basename(res["path"]) == "Kestrel Volume II - banned phrases 2026-11-06 2130.docx"
      and res["changes"] == 3, res)
check("the copy is found beside its draft", DR.copies_of(draft) == [res["path"]] and DR.when_of(res["path"]) == when
      and DR.kind_of(res["path"]) == "banned phrases")
got = DR.copy_changes(res["path"])
check("the copy's tracked changes are read: the old words and the new", [(c["old"], c["new"]) for c in got]
      == [("propellant", "fuel"), ("flight software", "onboard code"), ("w/o", "without")], got)
check("the draft as it was is read from the copy", [x for x in DR.original_paragraphs(res["path"]) if x] == [x for x in paras if x])
r0 = DR.report(draft, res["path"])
check("before the author does anything: every change is still to take", r0["open"] == 3 and r0["taken"] == 0 and r0["paras_changed"] == 0, r0)


def edit_draft(fn):
    with zipfile.ZipFile(draft) as z:
        items = {n: z.read(n) for n in z.namelist()}
    items["word/document.xml"] = fn(items["word/document.xml"].decode("utf-8")).encode("utf-8")
    with zipfile.ZipFile(draft, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in items.items():
            z.writestr(n, b)


edit_draft(lambda x: x.replace("propellant", "fuel", 1).replace("All flight software follows", "Every line of code meets", 1))
r1 = DR.report(draft, res["path"])
st = [c["state"] for c in r1["changes"]]
check("the author took one, rewrote one passage, left one", st == [DR.TAKEN, DR.MOVED, DR.OPEN], st)
check("the paragraphs changed since the copy are counted", r1["paras_changed"] == 2 and r1["paras"] >= 20, (r1["paras_changed"], r1["paras"]))
check("a copy that still fits says so", r1["advice"] == "The copy still fits the draft.", r1["advice"])
edit_draft(lambda x: x.replace(" the ", " a ").replace(" and ", " plus "))
r2 = DR.report(draft, res["path"])
check("a draft that moved on: make the copy again", r2["share"] >= DR.REMAKE_AT and r2["advice"].startswith("Make the copy again"), (r2["share"], r2["advice"]))
out = DR.write_xlsx(DR.reports(draft), os.path.join(tmp, "drift.xlsx"))
import openpyxl
wb = openpyxl.load_workbook(out)
check("the report in Excel: copies and changes", wb.sheetnames == ["Copies", "Changes"] and wb["Changes"].max_row == 4
      and wb["Copies"]["H2"].value.startswith("Make the copy again"))
check("the draft itself was only read", os.path.isfile(draft) and len(DR.copies_of(draft)) == 1)
n = sum(checks)
print(f"DRIFT 379 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
