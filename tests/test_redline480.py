"""4.8.0: Redline's three jobs (claude/stationkeeper-redline-plan-4.6.md, steps 1 to 3). The clean Word copy of the
fictional Section L: every word of the body in order, headings as Heading N by the depth of their number with the number
kept as text, no Word list numbering, the running headers and page numbers gone, a line set aside in Fix text left out
(and listed as set aside on purpose); the word-for-word check finds a word dropped from a copy with its heading; the
returned redline's check reports only the edit made with Track Changes off; the exceptions table reads an insertion, a
deletion, a replacement and a comment with the customer's numbers, and exports to Excel and Word."""
import os, re, sys, tempfile, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import openpyxl
import pagesent as PS
import redlinecheck as CK
import redlinecopy as RC
import redlineexcept as EX

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def rewrite(src, dst, fn, extra=None):
    with zipfile.ZipFile(src) as z:
        data = {n: z.read(n) for n in z.namelist()}
    data["word/document.xml"] = fn(data["word/document.xml"].decode("utf-8")).encode("utf-8")
    for k, v in (extra or {}).items():
        data[k] = v.encode("utf-8")
    with zipfile.ZipFile(dst, "w") as z:
        for n, b in data.items():
            z.writestr(n, b)
    return dst


PDF = os.path.join(ROOT, "test_samples", "rfp_walk", "Section_L_print.pdf")
d = tempfile.mkdtemp()
copy = os.path.join(d, RC.copy_name(PDF))
res = RC.build(PDF, copy)
check("the copy is named <document> - redline copy - <date>.docx", re.search(r"Section_L_print - redline copy - \d{4}-\d\d-\d\d\.docx$", copy))
xml = zipfile.ZipFile(copy).read("word/document.xml").decode("utf-8")
paras = CK.docx_paragraphs(copy)
heads = [(p["level"], p["text"]) for p in paras if p["kind"] == "heading"]
check("headings by the depth of their number, the number kept as text", (2, "L.1 General Instructions") in heads
      and any(lv == 1 and t.startswith("SECTION L") for lv, t in heads), heads[:5])
check("no Word list numbering anywhere", "w:numPr" not in xml)
doc = PS.doc_of(PDF)
run = {doc["pages"][pi]["lines"][li]["text"].strip() for pi, li in doc["skip"]}
body = " ".join(p["text"] for p in paras)
check("the running headers and page numbers are gone", run and not any(t and t in body for t in run if len(t) > 6), sorted(run)[:3])
f = CK.faithful(PDF, copy)
check("every word of the body is in the copy, in order", not f["differences"] and f["words"][0] == f["words"][1] > 300, f["words"])
check("a sidecar keeps the source's SHA-256 and the copy's paragraphs", (RC.sidecar(copy) or {}).get("source_sha256")
      and len(RC.sidecar(copy)["paragraphs"]) == res["paragraphs"])
# a line set aside in Fix text
first = next((pi, li) for pi, li in [(0, k) for k in range(len(doc["pages"][0]["lines"]))] if (pi, li) not in doc["skip"]
             and "cautioned" in doc["pages"][pi]["lines"][li]["text"])
PS.OVERRIDES.append(lambda path, name: ({first}, {}))
try:
    copy2 = os.path.join(d, "set aside.docx")
    RC.build(PDF, copy2)
    f2 = CK.faithful(PDF, copy2)
finally:
    PS.OVERRIDES.pop()
gone = doc["pages"][first[0]]["lines"][first[1]]["text"].strip()
check("a line set aside in Fix text stays out of the copy and is listed as set aside on purpose, not dropped",
      " ".join(p["text"] for p in CK.docx_paragraphs(copy2)).count(gone) == " ".join(p["text"] for p in CK.docx_paragraphs(copy)).count(gone) - 1
      and any(gone == t for _p, t in f2["set_aside"])
      and not f2["differences"], (f2["differences"][:2], f2["set_aside"]))
# a word dropped from the copy
bad = rewrite(copy, os.path.join(d, "dropped.docx"), lambda x: x.replace("cautioned ", "", 1))
f3 = CK.faithful(PDF, bad)
check("a word dropped from a copy is found with its page and heading", f3["differences"] and f3["differences"][0]["kind"] == "Dropped"
      and f3["differences"][0]["was"] == "cautioned" and f3["differences"][0]["heading"] == "L.1 General Instructions", f3["differences"])
# the returned redline: one tracked edit, one untracked
A = 'w:author="Pat Writer" w:date="2026-11-10T09:00:00Z"'


def redline(x):
    x = x.replace("<w:t xml:space=\"preserve\">The Government intends", f"<w:t xml:space=\"preserve\">The Government intends", 1)
    x = x.replace("cautioned", "warned", 1)                                   # untracked: Track Changes was off
    x = re.sub(r'(<w:r><w:t xml:space="preserve">Pages shall be 8.5 by 11 inches)', lambda m: (
        f'<w:del w:id="91" {A}><w:r><w:delText xml:space="preserve">Pages shall be 8.5 by 11 inches</w:delText></w:r></w:del>'
        f'<w:ins w:id="92" {A}><w:r><w:t xml:space="preserve">Pages shall be A4</w:t></w:r></w:ins>'
        '<w:r><w:t xml:space="preserve">'), x, count=1)
    return x


def fix_rest(x):
    return x.replace('<w:r><w:t xml:space="preserve"> with one-inch margins', '<w:r><w:t xml:space="preserve"> with one-inch margins', 1)


rl = rewrite(copy, os.path.join(d, "returned.docx"), redline)
r = CK.returned(copy, rl)
check("the returned redline: only the edit made with Track Changes off is reported", len(r["differences"]) == 1
      and r["differences"][0]["was"] == "cautioned" and r["differences"][0]["now"] == "warned", r["differences"])
# the exceptions table
cm = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="http://schemas.openxmlformats.org/'
      'wordprocessingml/2006/main"><w:comment w:id="5" w:author="Pat Writer"><w:p><w:r><w:t>A4 is our standard.</w:t></w:r></w:p>'
      '</w:comment></w:comments>')


def exceptions(x):
    x = redline(x).replace("warned", "cautioned", 1)
    x = x.replace('<w:del w:id="91"', '<w:commentRangeStart w:id="5"/><w:del w:id="91"', 1)
    x = re.sub(r'(<w:r><w:t xml:space="preserve">Each page shall be numbered)', lambda m: (
        f'<w:del w:id="93" {A}><w:r><w:delText xml:space="preserve">Each page shall be numbered and shall include the '
        'solicitation number in the header.</w:delText></w:r></w:del><w:r><w:t xml:space="preserve">'), x, count=1)
    x = re.sub(r'(<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t xml:space="preserve">L.3 )', lambda m: (
        f'<w:p><w:ins w:id="94" {A}><w:r><w:t xml:space="preserve">Our addition before L.3.</w:t></w:r></w:ins></w:p>' + m.group(1)), x, count=1)
    return x


ex = rewrite(copy, os.path.join(d, "exceptions.docx"), exceptions, {"word/comments.xml": cm})
rows = EX.rows(ex)
kinds = [(r["Number"], r["Kind"]) for r in rows]
check("three rows: a replacement, a deletion and an insertion with the customer's numbers", ("L.2", "Replaced") in kinds
      and ("L.2", "Deleted") in kinds and ("L.2", "Inserted") in kinds and len(rows) == 3, kinds)
rep = next(r for r in rows if r["Kind"] == "Replaced")
check("... the original and our text, the author, the date and the comment", rep["Original text"].startswith("Pages shall be 8.5")
      and rep["Our text"] == "Pages shall be A4" and rep["Author"] == "Pat Writer" and rep["Date"] == "2026-11-10"
      and rep["Comment"] == "A4 is our standard.", rep)
xl = EX.to_excel(rows, os.path.join(d, "exceptions.xlsx"))
wd = EX.to_word(rows, os.path.join(d, "exceptions word.docx"))
check("the Excel and Word exports open", openpyxl.load_workbook(xl)["Exceptions"].max_row == len(rows) + 1
      and "Pages shall be A4" in zipfile.ZipFile(wd).read("word/document.xml").decode())
print(f"REDLINE 480 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
