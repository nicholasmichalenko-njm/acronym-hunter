"""3.58.0 Final Check engine, standard library only (plus the app's PDF reader). The pages each tick-out finds (the
cover, the TOC, the acronym list, resumes, dividers); every page counts until ticked out; the page limit; the TOC's page
numbers against the PDF; the FAR 52.215-1(e) legend on the cover and the page marking on every page; leftovers, PDF
properties, another effort's name; the report in Excel. Fictional content."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import finalcheck as FC
sys.path.insert(0, HERE)
from pdfmake import make_pdf, MARK, filler, body, PAGES as pages   # noqa: E402

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
pdf = make_pdf(os.path.join(tmp, "Volume I Technical.pdf"), pages, title="Volume I draft")
P = FC.read_pdf(pdf)
check("the PDF's text page by page, and its properties", len(P["texts"]) == 7 and "Orbit Operations" in P["texts"][3]
      and P["meta"].get("Title") == "Volume I draft", P["meta"])
c = FC.classify(P["texts"])
check("the cover is page 1", c["cover"] == [1])
check("the table of contents", c["toc"] == [2], c)
check("the acronym list", c["acronyms"] == [6], c)
check("dividers and blank pages", c["dividers"] == [7], c)
n, out = FC.count_pages(P["texts"], [])
check("every page counts until one is ticked out", n == 7 and out == {})
n, out = FC.count_pages(P["texts"], ["cover", "toc", "acronyms"])
check("ticked out: cover, TOC, acronym list", n == 4 and set(out) == {"cover", "toc", "acronyms"}, (n, out))
mm = FC.toc_mismatches(P["texts"])
check("a TOC line whose heading is on another printed page", ("1.2 Ground Contacts", 9, 3) in mm and len(mm) == 1, mm)

# a Word file to go with it
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
docx = os.path.join(tmp, "Volume I Technical.docx")
with zipfile.ZipFile(docx, "w") as z:
    z.writestr("word/document.xml", f'<w:document {WNS}><w:body><w:p><w:r><w:t>1 Technical Approach</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>Unlike the Osprey bid, staffing is TBD.</w:t></w:r></w:p></w:body></w:document>')
rows = [{"kind": "Page limit", "subject": "Volume I", "value": "5 pages"}]
r = FC.run({"name": "Volume I Technical", "docx": docx, "pdf": pdf, "exclude": ["cover", "toc", "acronyms"]},
           {"rows": rows, "other_names": ["Osprey"], "allowed_sizes": ("Letter",)})
L = {(x["section"], x["check"]): x for x in r["lines"]}
check("eight sections in order", [s for s in FC.SECTIONS if any(x["section"] == s for x in r["lines"])] == list(FC.SECTIONS),
      sorted({x["section"] for x in r["lines"]}))
pl = L[("Page limits", "Pages against the limit")]
check("page limits: 4 counted of 7, under the 5-page limit", pl["status"] == FC.PASS and "4 of 7" in pl["detail"], pl)
r2 = FC.run({"name": "Volume I Technical", "docx": docx, "pdf": pdf, "exclude": []}, {"rows": rows})
pl2 = [x for x in r2["lines"] if x["check"] == "Pages against the limit"][0]
check("... every page counted: 7 is over 5", pl2["status"] == FC.FAIL and "2 over" in pl2["detail"], pl2)
check("the legend on the cover", L[("Markings", "Proprietary legend on the cover")]["status"] == FC.PASS)
check("the page marking on every page after the cover (blank pages aside)", L[("Markings", "Page marking on every page")]["status"] == FC.PASS,
      L[("Markings", "Page marking on every page")])
pages2 = [p[:] for p in pages]; pages2[0] = ["Kestrel Constellation Support", "Volume I Technical"]; pages2[3] = body(2)[:-2] + ["2"]
pdf2 = make_pdf(os.path.join(tmp, "Volume I no marks.pdf"), pages2)
r3 = FC.run({"name": "Volume I Technical", "pdf": pdf2, "exclude": []}, {})
L3 = {x["check"]: x for x in r3["lines"]}
check("no legend: fail", L3["Proprietary legend on the cover"]["status"] == FC.FAIL)
check("a page without the marking: fail, with its page", L3["Page marking on every page"]["status"] == FC.FAIL
      and "page 4" in L3["Page marking on every page"]["detail"], L3["Page marking on every page"])
r4 = FC.run({"name": "Volume I Technical", "pdf": pdf2}, {"marking": "Kestrel Works proprietary"})
check("the effort's own marking text is the one checked", "page 2" in [x for x in r4["lines"] if x["check"] == "Page marking on every page"][0]["detail"])
check("the TOC mismatch is a structure fail", L[("Structure", "Table of contents page numbers")]["status"] == FC.FAIL)
check("leftovers in the Word file", L[("Leftovers", "Setup text, hidden text, comments, tracked changes, placeholders")]["status"] == FC.FAIL)
check("another effort's name", L[("Leftovers", "Another effort's name")]["status"] == FC.FAIL and "Osprey" in L[("Leftovers", "Another effort's name")]["detail"])
check("PDF properties need a person", L[("Leftovers", "PDF properties")]["status"] == FC.HUMAN and "A. Writer" in L[("Leftovers", "PDF properties")]["detail"])
check("no standard, no matrix, no acronym list: each needs a person, never a pass",
      all(L[k]["status"] == FC.HUMAN for k in [("Format rules", "Against the standards"), ("Compliance", "Requirements placed in a section"),
                                                ("Acronyms", "First use and the list")]))
check("files: the PDF as the portal takes it (fonts not embedded here)", L[("Files", "The PDF as the portal takes it")]["status"] == FC.FAIL)
check("counts", r["counts"][FC.PASS] + r["counts"][FC.FAIL] + r["counts"][FC.HUMAN] == len(r["lines"]))
rn = FC.run({"name": "Volume II", "docx": docx, "pdf": ""}, {})
check("no PDF set: the PDF's checks ask for it", any(x["status"] == FC.HUMAN and "Set this volume's PDF" in x["detail"] for x in rn["lines"]))
xl = FC.export(os.path.join(tmp, "fc.xlsx"), [r, rn], "Kestrel")
import openpyxl
wb = openpyxl.load_workbook(xl)
check("the report in Excel: a summary and a sheet per volume", wb.sheetnames[:1] == ["Summary"] and len(wb.sheetnames) == 3
      and wb["Summary"]["A3"].value == "Volume I Technical")
wb.close()
n = sum(checks)
print(f"FINAL CHECK {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
