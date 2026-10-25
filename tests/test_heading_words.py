"""2.20.0 known gap F6: ordinary words in all-capital headings are not acronyms. A common word that only appears in
capital headings is set aside (excluded, listed with Show Excluded); the same word written alone in running text, and
real acronyms in headings, stay candidates."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, docxw
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "Heads.docx")
d = docxw.Doc()
d.heading("3. THERMAL DESIGN", 1)
d.para("The radiator panels are sized for end of life.")
d.heading("M.1 BASIS FOR AWARD", 1)
d.para("The Government will award a contract.")
d.heading("4. PCU INTERFACES", 1)
d.para("The PCU feeds the bus. The REVIEW board meets monthly.")
d.heading("5. DESIGN REVIEW", 1)
d.para("Schedules follow.")
d.save(p)
r = A.analyze_batch([p], lambda m: None)
st = lambda t: r.get(t, {}).get("status", "(not found)")
assert st("THERMAL").startswith("EXCLUDED: heading"), st("THERMAL")
assert st("BASIS").startswith("EXCLUDED: heading") and st("AWARD").startswith("EXCLUDED: heading"), (st("BASIS"), st("AWARD"))
assert st("PCU") == "NEW CANDIDATE", st("PCU")                       # a real acronym, also in a heading
assert st("REVIEW") == "NEW CANDIDATE", st("REVIEW")                 # alone in running text once: stays for review
assert r["THERMAL"]["excluded"] and not r["PCU"]["excluded"]
assert A.in_caps_run("SECTION M - EVALUATION FACTORS FOR AWARD", 34, 37)
assert not A.in_caps_run("The SOW tasks follow.", 4, 7)
print("heading words ok")
