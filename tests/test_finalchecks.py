"""3.4.0 final checks, without screens: the PDF package (page size, fonts not embedded, pages without text, page
limits by volume, file size, file names, a file that does not open, required volumes and forms missing), cross-
references and numbering in a Word draft, and the comparison of two drafts with its Word redline."""
import os, shutil, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app_gui as A
import pkgcheck as PK, xrefcheck as X, draftcompare as DC, docxw
from openpyxl import load_workbook

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


S = os.path.join(A.BASE_DIR, "test_samples")
tmp = tempfile.mkdtemp()
pk = os.path.join(tmp, "Final"); os.makedirs(pk)
shutil.copy2(os.path.join(S, "rfp_hard", "Hard_RFP.pdf"), os.path.join(pk, "FA8810_Volume_I_Technical.pdf"))
shutil.copy2(os.path.join(S, "Kestrel_Program_Manual.pdf"), os.path.join(pk, "FA8810_Volume_II_Management.pdf"))
shutil.copy2(os.path.join(S, "Corrupt_File_Test.pdf"), os.path.join(pk, "Volume_III_Price.pdf"))
info = PK.read_pdf(os.path.join(pk, "FA8810_Volume_II_Management.pdf"))
check("a PDF read: pages, page size, fonts and whether embedded, pages with no text", info["pages"] == 8 and info["sizes"][0] == ("A4", False)
      and info["fonts"] == {"Helvetica": False} and info["no_text"] == [7, 8], info)
check("page sizes named", PK.page_size_name(612, 792) == "Letter" and PK.page_size_name(842, 595) == "A4" and PK.page_size_name(700, 700).endswith("in"))
limits = [{"kind": "Page limit", "subject": "Volume II", "value": "5 pages"}]
r = PK.check([os.path.join(pk, f) for f in os.listdir(pk)], limits, size_mb=0.001, must_contain=["FA8810"],
             required=["Volume I Technical", "Volume II Management", "SF 33"])
by = {f["file"]: f for f in r["files"]}
v2 = by["FA8810_Volume_II_Management.pdf"]
check("over the volume's page limit", v2["limit"] == 5 and any("over the 5-page limit" in p for p in v2["problems"]), v2["problems"])
check("A4 when the package must be Letter", any("page size A4" in p for p in v2["problems"]))
check("fonts not embedded", any("fonts not embedded: Helvetica" in p for p in v2["problems"]))
check("pages with no text are noted", any("no text on pages 7, 8" in n for n in v2["notes"]), v2["notes"])
check("over the file size limit", any("MB limit" in p for p in v2["problems"]))
check("a file name without the required words", any("does not contain “FA8810”" in p for p in by["Volume_III_Price.pdf"]["problems"]))
check("a file that does not open", any("does not open as a PDF" in p for p in by["Volume_III_Price.pdf"]["problems"]))
check("a clean Letter file with embedded fonts has no font or size problem", not any("fonts" in p or "page size" in p
                                                                                     for p in by["FA8810_Volume_I_Technical.pdf"]["problems"]))
check("a required form with no file is missing", r["missing"] == ["SF 33"], r["missing"])
x = PK.export(os.path.join(tmp, "pkg.xlsx"), r, "Kestrel")
check("the package workbook", load_workbook(x).active.max_row == 5)
# cross-references
d = docxw.Doc()
d.heading("1.1 Approach", 2)
d.para("Figure 1 shows the bus; Tables 1 and 2 list the masses. See Figure 4. Error! Reference source not found.")
d.para("Figure 1. The spacecraft bus")
d.table(["Item", "kg"], [["Radiator", "12"]], [3000, 2000]); d.para("Table 1. Mass budget")
d.table(["Item", "W"], [["Heater", "40"]], [3000, 2000])
d.heading("1.2 Risk", 2)
d.para("Figure 3. Risk burn-down"); d.para("Figure 2. Out of order")
p = os.path.join(tmp, "Vol.docx"); d.save(p)
res = X.check(p)
kinds = sorted(q["kind"] for q in res["problems"])
check("captions found in order of the document", res["captions"]["Figure"] == ["1", "3", "2"] and res["captions"]["Table"] == ["1"])
check("Word's broken references", "Broken reference" in kinds)
check("figures out of order", kinds.count("Figure out of order") == 2)
check("a mention with no caption (Table 2, Figure 4), and a list of tables read as two mentions", {q["text"].split(",")[0] for q in res["problems"]
      if q["kind"].endswith("not found")} == {"the text mentions Table 2", "the text mentions Figure 4"}, [q["text"] for q in res["problems"]])
check("captions never mentioned", sorted(q["text"].split(" is ")[0] for q in res["problems"] if q["kind"].endswith("never mentioned")) == ["Figure 2", "Figure 3"])
check("a table with no caption beside it", "Table with no caption" in kinds)
check("... in its section", next(q for q in res["problems"] if q["kind"] == "Figure out of order")["where"] == "1.2 Risk")
check("chapter numbering: 3-2 after 3-1, 4-1 after 3-2", X._follows(X._split("3-1"), X._split("3-2")) and X._follows(X._split("3-2"), X._split("4-1"))
      and not X._follows(X._split("3-1"), X._split("3-3")))
xx = X.export(os.path.join(tmp, "x.xlsx"), [("Vol", res)])
check("the cross-reference workbook", load_workbook(xx).active.max_row == len(res["problems"]) + 1)
# compare two drafts
d2 = docxw.Doc()
d2.heading("1.1 Approach", 2)
d2.para("Figure 1 shows the bus; Tables 1 and 2 list the masses in kilograms. A new paragraph about margin.")
d2.heading("1.2 Risk", 2); d2.para("Figure 3. Risk burn-down")
p2 = os.path.join(tmp, "Vol2.docx"); d2.save(p2)
c = DC.compare(p, p2)
check("comparing two drafts: changed, added and removed sentences", c["counts"]["changed"] >= 1 and c["counts"]["added"] >= 1 and c["counts"]["removed"] >= 1, c["counts"])
check("... counted by heading", "1.1 Approach" in DC.by_section(c["rows"]))
rl = DC.export(os.path.join(tmp, "red.docx"), c, "Volume I")
xml = zipfile.ZipFile(rl).read("word/document.xml").decode("utf-8")
check("... the Word redline: struck-through and added words", "w:strike" in xml and "kilograms" in xml and "Volume I" in xml)
n = sum(checks)
print(f"FINAL CHECKS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
