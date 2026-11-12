"""4.16.0: the PDF's comments in Redline's Word copy (claude/stationkeeper-pdf-comments-plan-4.16.html). Fictional PDFs
commented the way Acrobat writes comments (tools/make_comment_fixtures.py), each comment with its right answer in
comments_truth.json: a highlight or underline is a Word comment on exactly its words; a cross-out is a tracked deletion
of exactly its letters; an insert is a tracked insertion at its letter; Replace text is a deletion and an insertion;
replies are Word replies; Completed marks the comment done; a note, callout, shape or stamp is placed by position on
the right words; a mark on the running header goes to the page's first words. Check still finds the copy word for word;
rejecting every change gives the PDF's words; Make it without the PDF's comments leaves them out."""
import json, os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
import pdfcomments as PC, redlinecheck as CK, redlinecopy as RC, redlinemarks as RM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def n(s):
    return "".join(ch for ch in (s or "").casefold() if ch.isalnum())


def sp(s):
    return " ".join((s or "").split())


FIX = os.path.join(ROOT, "test_samples", "comments")
truth = json.load(open(os.path.join(FIX, "comments_truth.json"), encoding="utf-8"))
tmp = tempfile.mkdtemp()

check("an Acrobat date keeps the reviewer's clock, as Word writes dates", PC.pdf_date("D:20261103091500-07'00'") == "2026-11-03T09:15:00Z"
      and PC.pdf_date("junk") == "")
score = {"right": 0, "all": 0}
for name, spec in truth.items():
    pdf = os.path.join(FIX, name)
    out = os.path.join(tmp, name.replace(".pdf", ".docx"))
    res = RC.build(pdf, out)
    rb = RM.read_back(out)
    tops = [c for c in rb["comments"] if not c["parent"]]
    found = {}

    def comment_for(t):
        for c in tops:
            if c["author"] == t["author"] and sp(c["text"]) == sp(t["note"]):
                return c
        return None

    def para_of(c):
        """The accepted text of the paragraph the comment's words sit in."""
        return rb["accepted"][c["para"]] if 0 <= c["para"] < len(rb["accepted"]) else ""

    for t in spec["comments"]:
        ok, info = False, ""
        if t["want"] == "comment":
            c = comment_for(t)
            found[t["id"]] = c
            if c is None:
                info = "no Word comment by that reviewer with that note"
            else:
                ok = True
                if t.get("words") and t.get("how") != "position":
                    ok = n(c["range"]) == n(t["words"]); info = f"on {c['range']!r}"
                elif t.get("words"):
                    ok = n(t["words"]) in n(c["range"]) or n(c["range"]) in n(t["words"]); info = f"on {c['range']!r}"
                if ok and t.get("near"):
                    ok = n(t["near"]) in n(para_of(c)); info = f"in {para_of(c)[:60]!r}"
                if ok and t.get("context"):
                    ok = n(t["context"]) in n(para_of(c)); info = f"in {para_of(c)[:60]!r}"
        elif t["want"] == "reply":
            par = found.get(t["to"])
            ok = par is not None and any(c["parent"] == par["id"] and c["author"] == t["author"] and sp(c["text"]) == sp(t["note"])
                                         for c in rb["comments"])
        elif t["want"] == "done":
            par = found.get(t["to"])
            ok = par is not None and par["done"]
        elif t["want"] == "delete":
            ok = any(a == t["author"] and sp(x).strip() == t["words"] for a, x in rb["deleted"])
            info = rb["deleted"]
            if ok and t.get("accepted"):
                ok = any(sp(t["accepted"]) in sp(p) for p in rb["accepted"]); info = "accepted text"
            if ok and t.get("note"):
                ok = comment_for(t) is not None; info = "its note"
        elif t["want"] in ("insert", "replace"):
            ok = any(sp(t["accepted"]) in sp(p) for p in rb["accepted"])
            info = [p for p in rb["accepted"] if n(t["insert"]) in n(p)][:1]
            if ok and t["want"] == "replace":
                ok = any(a == t["author"] and x.strip() == t["words"] for a, x in rb["deleted"])
        score["all"] += 1; score["right"] += bool(ok)
        check(f"{name}: {t['id']} ({t['want']})", ok, info)
    recs = res.get("comments") or []
    import zipfile
    xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    kids = [c for c in rb["comments"] if c["parent"]]
    check(f"{name}: a reply is marked as Word marks one (after its comment's reference)", all(
        xml.index(f'commentReference w:id="{c["parent"]}"') < xml.index(f'commentRangeEnd w:id="{c["id"]}"') for c in kids))
    check(f"{name}: every comment is listed with how it was placed", recs and all(r["how"] and r["became"] for r in recs), recs[:2])
    check(f"{name}: what was placed by position is said so", res.get("by_position", 0) >= sum(1 for t in spec["comments"] if t.get("how") == "position"),
          res.get("by_position"))
    f = CK.faithful(pdf, out)
    check(f"{name}: Check finds the copy word for word (the comments' changes undone)", not f["differences"], f["differences"][:3])
    check(f"{name}: Check lists the comments", len(f["comments"]) == len(recs))
    plain = os.path.join(tmp, "plain-" + name.replace(".pdf", ".docx"))
    r2 = RC.build(pdf, plain, comments=False)
    check(f"{name}: Make it without the PDF's comments leaves them out", not r2.get("comments") and not RM.read_back(plain)["comments"])
check("every fixture comment lands right", score["right"] == score["all"], score)
base = os.path.join(FIX, "C01_prose.pdf")
r3 = RC.build(base, os.path.join(tmp, "base.docx"))
check("a PDF with no comments is copied as before", "comments" not in r3)
print(f"comments placed right: {score['right']} of {score['all']}")
k = sum(checks)
print(f"COMMENTS 4160 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
