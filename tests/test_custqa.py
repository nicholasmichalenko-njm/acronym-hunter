"""2.98.0 customer Q&A, key dates and what changed, without windows: questions are numbered in order, keep their
status history, move, and are removed with the numbers following; the Word export is a landscape document with a cover
block, the quote and the marking; the Excel export is the government layout; the customer's own Excel and Word templates
are filled under their header rows (found by their column names), leaving the rest as it was; key dates are found with
their kind, time and zone; a new version's summary counts what changed and finds the requirements it touches; the marks
say what each changed sentence was; and the old sentence is found on the old version's page."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import app_gui as A
import custqa as Q, captures as CP, whatchanged as WC, effortrec as R, docversions as DV, docintake as DI, compliance as C
import docxw, pdfmini, openpyxl

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
rec = R.Record(os.path.join(tmp, "data"))
a = Q.add(rec, "Will the Government accept a 25-page Volume II?", "Volume II shall not exceed 20 pages.", doc="Section_L.pdf",
          section="L.4.2", page="12", para="3", category="Format and submission")
b = Q.add(rec, "Is CDRL A003 due monthly or quarterly?", "The contractor shall deliver CDRL A003.", doc="SOW.docx", section="C.3")
c = Q.add(rec, "Should the IMS be in Microsoft Project?", "The Offeror shall provide an IMS.", doc="Section_L.pdf", section="L.5")
check("questions are numbered in order and start as Draft", [q["n"] for q in Q.items(rec)] == [1, 2, 3]
      and all(q["status"] == "Draft" for q in Q.items(rec)))
check("nothing to ask: not added", Q.add(rec, "", "") == "")
Q.update(rec, a, status="Approved", who="nmich")
q = Q.get(R.Record(os.path.join(tmp, "data")), a)
check("a status change is kept with who and when", q["status"] == "Approved" and q["history"][-1]["was"] == "Draft"
      and q["history"][-1]["who"] == "nmich")
Q.move(rec, c, -1)
check("moving one: the numbers follow", [x["id"] for x in Q.items(rec)] == [a, c, b] and [x["n"] for x in Q.items(rec)] == [1, 2, 3])
Q.update(rec, b, answer="Monthly, per CDRL A003 block 10.", answer_doc="Amendment 2")
check("an answer marks it Answered, with where it came", Q.get(rec, b)["status"] == "Answered" and Q.get(rec, b)["answer_doc"] == "Amendment 2")
check("the summary", Q.summary(rec) == "3 question(s): 1 draft, 1 approved, 1 answered", Q.summary(rec))
check("where it is, in words", Q.where(Q.get(rec, a)) == "Section L.4.2, p.12, para 3", Q.where(Q.get(rec, a)))
# Word
wd = os.path.join(tmp, "q.docx")
Q.export_docx(wd, Q.chosen(rec, ["Draft", "Approved"]), effort="Osprey", solicitation="FA8810-26-R-0001", offeror="Sierra Space",
              contact="M. Chen", marking="CUI")
z = zipfile.ZipFile(wd)
x = z.read("word/document.xml").decode()
check("Word: landscape, the cover block, the quote, our question", 'w:orient="landscape"' in x and "FA8810-26-R-0001" in x
      and "Sierra Space" in x and "Volume II shall not exceed 20 pages." in x and "Should the IMS be in Microsoft Project?" in x)
check("... only the statuses chosen", "CDRL A003 due monthly" not in x)
check("... and the marking in the header and footer", "CUI" in z.read("word/header1.xml").decode() and "CUI" in z.read("word/footer1.xml").decode())
# Excel
xl = os.path.join(tmp, "q.xlsx")
Q.export_xlsx(xl, Q.items(rec), effort="Osprey", solicitation="FA8810-26-R-0001", marking="CUI", answers=True)
ws = openpyxl.load_workbook(xl).active
hr = next(r for r in range(1, 10) if ws.cell(r, 1).value == "No.")
head = [ws.cell(hr, k).value for k in range(1, 9)]
check("Excel: the government layout", head == ["No.", "Document", "Section", "Page", "Paragraph", "RFP Text", "Question", "Government Response"], head)
check("... one row per question, with the answers when asked", ws.cell(hr + 3, 7).value == "Is CDRL A003 due monthly or quarterly?"
      and ws.cell(hr + 3, 8).value.startswith("Monthly") and ws.cell(1, 1).value == "CUI")
# the customer's Excel template
t = os.path.join(tmp, "Industry_Questions.xlsx")
wb = openpyxl.Workbook(); w = wb.active; w.title = "Questions"
w["A1"] = "FA8810-26-R-0001 Industry Questions"; w["A2"] = "Do not change the columns."
for k, h in enumerate(["Item No.", "RFP Section/Paragraph", "Page No.", "Offeror Question / Comment", "Government Response"], start=1):
    w.cell(4, k, h)
w["A40"] = "Instructions: submit by e-mail."
wb.save(t)
found = Q.template_columns(t)
check("the template's header row is found by its column names", found and found[0] == ("Questions", 4)
      and found[1] == {1: "n", 2: "section", 3: "page", 4: "question", 5: "answer"}, found)
out = os.path.join(tmp, "filled.xlsx")
n, fields = Q.fill_template(t, out, Q.items(rec))
w2 = openpyxl.load_workbook(out)["Questions"]
check("filled under the header, in its columns, the rest as it was", n == 3 and w2["A5"].value == 1 and w2["B5"].value == "L.4.2"
      and w2["D5"].value.startswith("Will the Government") and w2["E5"].value in (None, "") and w2["A1"].value.startswith("FA8810")
      and w2["A40"].value.startswith("Instructions"))
# the customer's Word template
tw = os.path.join(tmp, "QA_Form.docx")
d = docxw.Doc(); d.para("Questions and Answers Form"); d.table(["Number", "Reference", "Question", "Answer"], [["", "", "", ""]], [800, 2000, 4000, 3000])
d.para("Return this form by the questions due date."); d.save(tw)
ow = os.path.join(tmp, "QA_Form_filled.docx")
Q.fill_template(tw, ow, Q.items(rec))
rows = Q._docx_tables(ow)[0]
check("the Word template: a row per question in its table, the blank row used", len(rows) == 4 and rows[1][:3] == ["1", "Section L.4.2, p.12, para 3", "Will the Government accept a 25-page Volume II?"], rows[1])
check("... and the rest of the form kept", "Return this form" in zipfile.ZipFile(ow).read("word/document.xml").decode())
nq = os.path.join(tmp, "no_questions.docx")
d = docxw.Doc(); d.table(["Name", "Value"], [["a", "b"]], [3000, 3000]); d.save(nq)
try:
    Q.fill_template(nq, os.path.join(tmp, "x.docx"), Q.items(rec)); bad = False
except ValueError:
    bad = True
check("a file with no Question column is refused", bad and not os.path.exists(os.path.join(tmp, "x.docx")))
Q.remove(rec, c)
check("removing one: the numbers follow", [x["n"] for x in Q.items(rec)] == [1, 2])
# key dates
g = CP.key_date_guess("Questions shall be submitted no later than 2:00 p.m. Eastern Time on November 20, 2026.")
check("a key date: questions due, with its time and zone", g == {"date": "2026-11-20", "start": "14:00", "zone": "ET", "kind": "Questions due",
                                                               "title": "Questions due"}, g)
g = CP.key_date_guess("A site visit will be held on December 2, 2026 at 9:00 a.m. MT.")
check("a site visit", g["kind"] == "Meeting" and g["title"] == "Site visit" and g["zone"] == "MT")
g = CP.key_date_guess("Anticipated award is March 1, 2027.")
check("an award, no time written", g["title"] == "Award" and g["start"] == "")
check("no date: nothing", CP.key_date_guess("The Offeror shall describe its approach.") is None)
# what changed
lib = DV.Library(os.path.join(tmp, "data", "documents")).load()
base = ["L.4 Volume II", "Volume II shall not exceed 20 pages.", "The Offeror shall describe its approach to testing.",
        "Text shall be 12-point Times New Roman.", "The Offeror shall describe its risk process."]
amd = ["L.4 Volume II", "Volume II shall not exceed 25 pages.", "The Offeror shall describe its approach to testing.",
       "Text shall be 12-point Times New Roman.", "The Offeror shall describe its risk process and mitigation plans.",
       "The Offeror shall provide a quality plan."]
p1 = os.path.join(tmp, "RFP.pdf"); pdfmini.write(p1, [base], size=9)
p2 = os.path.join(tmp, "RFP_Amendment_1.pdf"); pdfmini.write(p2, [amd], size=9)
pl = DI.plan(lib, [p1]); pl[0]["initial"] = "R"; DI.apply(lib, pl, "")
pl = DI.plan(lib, [p2]); pl[0]["choice"] = "version"; pl[0]["doc"] = lib.docs[0]["id"]; made = DI.apply(lib, pl, "")
dd, vb = made[0]
M = C.Matrix(os.path.join(tmp, "m.xlsx"), "Osprey")
M.items = C.extract([("RFP.pdf", [("Page 1", "\n".join(base))])])
risk = next(it for it in M.items if "risk process" in it["text"])
C.assign_requirement(M.items, [risk], "1.1 Technical"); risk["owner"] = "J. Garcia"
s = WC.summary(lib, lib.doc(dd["id"]), vb, M=M)
check("what changed: counts", s and s["changed"] == 2 and s["added"] == 1 and s["removed"] == 0, s and (s["changed"], s["added"], s["removed"]))
check("... the submission rule it touches (the page limit)", any("25 pages" in r for r in s["rules"]), s["rules"])
check("... the requirement it touches", [h["id"] for h in s["requirements"]] == [risk["id"]], s["requirements"])
check("... and the title says which version", s["title"].startswith("What changed in Amendment 1"), s["title"])
check("the first version: no summary", WC.summary(lib, lib.doc(dd["id"]), lib.doc(dd["id"])["versions"][0]) is None)
m = WC.marks(lib, "RFP_Amendment_1.pdf")
ch = WC.mark_of(m, "Volume II shall not exceed 25 pages.")
check("the marks: a changed sentence says what it was", ch and ch["kind"] == "changed" and ch["old"] == "Volume II shall not exceed 20 pages."
      and ("+", "25") in ch["diff"], ch)
check("... a new sentence is new", WC.mark_of(m, "The Offeror shall provide a quality plan.")["kind"] == "added")
check("... an unchanged one is not marked", WC.mark_of(m, "The Offeror shall describe its approach to testing.") is None)
check("the first version has no marks", WC.marks(lib, "RFP.pdf") is None)
f = WC.find_on_pages(p1, "Volume II shall not exceed 20 pages.")
check("the old sentence is found on the old page", f is not None and f[0] == 0 and f[1], f)
n = sum(checks)
print(f"TEST CUSTQA {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
