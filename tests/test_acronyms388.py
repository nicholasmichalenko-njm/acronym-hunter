"""3.88.0 Acronyms v2 rules: definitions in the stated order with their source and reason; the terms one click can add
(one customer definition, nothing that disagrees); meanings that need a choice with their places; table and figure
numbers suggested as Not a term; plurals joined to their term; in our drafts, first use per volume (right, used before
it is spelled out, spelled out again, each with its change) and the volume's own Acronyms table against what its text
uses. Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import acrsuggest as AS, acrdrafts as AD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


results = {
    "GSE": {"customer_definitions": ["Ground Support Equipment"], "custdef_all": [{"definition": "Ground Support Equipment", "where": "RFP p. 41 (L.3.6)"}],
            "in_db": True, "definitions": ["Ground Support Equipment", "General Systems Engineering"]},
    "PM": {"customer_definitions": ["Program Manager", "Project Manager"],
           "custdef_all": [{"definition": "Program Manager", "where": "RFP p. 41"}, {"definition": "Project Manager", "where": "J-1 p. 12"}]},
    "IMS": {"customer_definitions": ["Integrated Master Schedule"], "custdef_all": [{"definition": "Integrated Master Schedule", "where": "RFP p. 9"}],
            "client_definitions": ["Integrated Management System"]},
    "BOE": {"customer_definitions": ["Basis of Estimate"], "custdef_all": [{"definition": "Basis of Estimate", "where": "RFP p. 12"}], "effort": "In the list"},
    "FTE": {"customer_definitions": ["Full-Time Equivalent"], "custdef_all": [{"definition": "Full-Time Equivalent", "where": "RFP p. 14"}]},
    "FTEs": {},
    "KPP": {},
    "L-3": {},
}
s = AS.suggestions(results["GSE"])
check("definitions in the stated order, each with source and why", [(x["source"], x["definition"]) for x in s] ==
      [("Customer", "Ground Support Equipment"), ("This PC", "General Systems Engineering")]
      and s[0]["why"] == "Spelled out by the customer, RFP p. 41 (L.3.6)", s)
check("the effort's list comes first", AS.suggestions({"list_definition": "Ground Segment Equipment", **results["GSE"]})[0]["source"] == "List")
check("one click adds only the terms with one customer definition and nothing that disagrees",
      AS.one_customer(results) == ["FTE", "GSE"], AS.one_customer(results))
check("two customer meanings need a choice, each with its page", AS.meanings(results["PM"]) ==
      [{"definition": "Program Manager", "where": "RFP p. 41"}, {"definition": "Project Manager", "where": "J-1 p. 12"}])
check("one meaning is no choice", AS.meanings(results["GSE"]) == [])
check("a table number is suggested as Not a term", AS.not_a_term_hint("L-3") == "Looks like a table or figure number"
      and AS.not_a_term_hint("J-1") and AS.not_a_term_hint("F-2.1") and not AS.not_a_term_hint("GSE"))
check("a plural joins its term", AS.plural_base("FTEs", results) == "FTE" and AS.plural_base("GSE", results) == "")

# in our drafts
tmp = tempfile.mkdtemp()
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def p(t, style=""):
    st = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ""
    return f"<w:p>{st}<w:r><w:t xml:space=\"preserve\">{t}</w:t></w:r></w:p>"


def row(a, b):
    return f"<w:tr><w:tc>{p(a)}</w:tc><w:tc>{p(b)}</w:tc></w:tr>"


body = (p("1 Overview GSE", "TOC1")
        + p("The Kestrel team maintains all Ground Support Equipment (GSE) at the site.")
        + p("Each GSE item is inspected monthly. The IMS shows the inspections.")
        + p("The Integrated Master Schedule (IMS) is updated weekly.")
        + p("Ground Support Equipment (GSE) spares are kept on site.")
        + "<w:tbl>" + row("Acronym", "Meaning") + row("GSE", "Ground Support Equipment") + row("TT&amp;C", "Tracking, Telemetry and Command")
        + row("IMS", "Integrated Master Schedule") + "</w:tbl>")
draft = os.path.join(tmp, "Kestrel Volume II Draft.docx")
with zipfile.ZipFile(draft, "w") as z:
    z.writestr("word/document.xml", f"<w:document {WNS}><w:body>{body}<w:sectPr/></w:body></w:document>")
fu = AD.first_use(draft, {"GSE": "Ground Support Equipment", "IMS": "Integrated Master Schedule", "KPP": "Key Performance Parameter"})
by = {(e["term"], e["status"]) for e in fu}
check("spelled out at first use is right; the table of contents line does not count", ("GSE", "right") in by)
check("used before it is spelled out: the change spells it out there", any(e["term"] == "IMS" and e["status"] == "before"
      and e["where"] == "paragraph 2" and e["change"] == "Spell it out here: Integrated Master Schedule (IMS)" for e in fu), fu)
check("spelled out again later: keep the acronym, drop the words", any(e["term"] == "GSE" and e["status"] == "again"
      and e["where"] == "paragraph 4" for e in fu) and any(e["term"] == "IMS" and e["status"] == "again" for e in fu))
check("a term the draft never uses is not listed", not any(e["term"] == "KPP" for e in fu))
tc = AD.table_check(draft, ["GSE", "IMS", "BOE"])
check("the volume's own Acronyms table is found", tc["table"] == {"GSE": "Ground Support Equipment", "TT&C": "Tracking, Telemetry and Command",
                                                               "IMS": "Integrated Master Schedule"}, tc["table"])
check("listed but not used", tc["listed_not_used"] == ["TT&C"], tc)
draft2 = os.path.join(tmp, "Kestrel Volume III Draft.docx")
with zipfile.ZipFile(draft2, "w") as z:
    z.writestr("word/document.xml", f"<w:document {WNS}><w:body>{p('The Basis of Estimate (BOE) and the GSE list.')}"
               + "<w:tbl>" + row("Acronym", "Meaning") + row("GSE", "Ground Support Equipment") + row("TT&amp;C", "Tracking") + "</w:tbl><w:sectPr/></w:body></w:document>")
check("used but not listed", AD.table_check(draft2, ["GSE", "IMS", "BOE"])["used_not_listed"] == ["BOE"])
check("each volume restarts first use", any(e["term"] == "GSE" and e["status"] == "before" for e in AD.first_use(draft2, {"GSE": "Ground Support Equipment"})))

print(f"ACRONYMS 388 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
