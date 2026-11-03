"""3.23.0 fill-ins: a value typed once shows everywhere it is referenced. A styleref fill-in puts the value once on the
cover in its own style and every header STYLEREF to that style shows it; a docprop fill-in writes a document property
and headers show it through DOCPROPERTY; fields carry no MERGEFORMAT switch (each result takes the formatting where it
sits); a blank fill-in with no cover text stops headers from being built rather than typing a wrong value."""
import os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import fillins as FI, prodrules as PRL, prodtemplate as PT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


std = PRL.for_effort(tempfile.mkdtemp())
std["fill_ins"] = [{"name": "Contract type", "kind": "styleref", "value": "CPFF"},
                   {"name": "Proposal number", "kind": "docprop", "property": "Proposal Number", "value": "P-2026-114"},
                   {"name": "Customer", "kind": "docprop", "property": "Company", "value": "US Space Force"}]
std["variables"].update(volume_name="Volume I Technical", solicitation="FA8810-26-R-0042", company="Acme Space")
std["hf_layouts"]["body"]["header"] = {"left": "{contract_type}", "center": "{customer}", "right": "{proposal_number}", "rule_below": True}
check("the standard's fill-ins: a cover style and two document properties", FI.styles(std)["contract_type"] == "SK Contract type"
      and FI.props(std) == {"proposal_number": "Proposal Number", "customer": "Company"} and "contract_type" in FI.tokens(std))
tj = PT.make(std, os.path.join(tempfile.mkdtemp(), "out"))
z = zipfile.ZipFile(tj.copy)
doc = z.read("word/document.xml").decode()
hdrs = " ".join(z.read(n).decode() for n in z.namelist() if re.match(r"word/header\d+\.xml", n))
check("the value sits once on the cover, in its own style", doc.count(">CPFF<") == 1 and 'w:pStyle w:val="SKContracttype"' in doc,
      re.findall(r'pStyle w:val="SK[^"]*"', doc))
check("headers read it through STYLEREF", 'STYLEREF "SK Contract type"' in hdrs, re.findall(r"instrText[^>]*>([^<]+)", hdrs)[:8])
check("and the document properties through DOCPROPERTY", 'DOCPROPERTY "Proposal Number"' in hdrs and 'DOCPROPERTY "Company"' in hdrs)
cp = z.read("docProps/custom.xml").decode() if "docProps/custom.xml" in z.namelist() else ""
app = z.read("docProps/app.xml").decode()
check("the properties are written: a custom one, and Company in Word's own place", 'name="Proposal Number"' in cp and "P-2026-114" in cp
      and "<Company>US Space Force</Company>" in app, (cp[:300], app[:300]))
check("no field carries MERGEFORMAT: each result takes the formatting where it sits", "MERGEFORMAT" not in hdrs + doc)
check("the template passes its own check", tj.check.count() == 0 and not [s for s in tj.steps if s.get("refused")],
      ([f["what"][:80] for f in tj.check.findings], [s.get("refused") for s in tj.steps if s.get("refused")]))
check("a field's formatting switch can be taken off", FI.strip_mergeformat('STYLEREF "Cover Title" \\* MERGEFORMAT') == 'STYLEREF "Cover Title"')
std2 = PRL.for_effort(tempfile.mkdtemp())
std2["fill_ins"] = [{"name": "Program", "kind": "docprop"}]
std2["hf_layouts"]["body"]["header"] = {"left": "{program}"}
check("a docprop fill-in never blocks headers (Word shows the property)", "program" not in PRL.missing_values(std2, []))
print(f"FILL-INS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
