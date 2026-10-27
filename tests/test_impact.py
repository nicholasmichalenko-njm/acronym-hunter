"""2.42.0 impact review: what one new customer version touched. A changed due date and a new attachment (submission
requirements); the new attachment suggested as a deliverable, a deliverable's page limit and a newer form version;
matrix sentences changed and removed with their section and owner, new sentences not assigned; a renamed heading with
our section named like it; new acronyms against the effort list and the master database; a new customer phrase (joined
from overlapping pieces); who it touches; the headline; the Word report; pending and reviewed versions."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import impact as IM, docversions as DV, subreq as SR, compliance as C, effortrec as ER, deliverables as D
from test_docversions import amend


def run():
    import app_gui as A
    d = tempfile.mkdtemp()
    orig = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
    src = amend(orig, os.path.join(d, "Kestrel_RFP.docx"), [("Proposals shall not exceed 50 pages", "Volume I shall not exceed 50 pages")])
    amd = amend(src, os.path.join(d, "Kestrel_RFP_Amd1.docx"), [
        ("December 15, 2026", "December 22, 2026"),
        ("exceed 50 pages", "exceed 40 pages"),
        ("L.4.2 Management Approach", "L.4.2 Management and Schedule Approach"),
        ("an Integrated Master Schedule (IMS) as Attachment J-2.",
         "an Integrated Master Schedule (IMS) as Attachment J-2. The Offeror shall provide a Small Business Participation Plan (SBPP) "
         "as Attachment J-7. The SBPP shall describe verification by analysis and test. Verification by analysis and test applies "
         "to every TRL claim."),
        ("The Contractor should use flight-proven components where practical.", "")])
    lib = DV.Library(os.path.join(d, "documents"))
    doc, v1 = lib.add(src, DV.snapshot("a.docx", A.typed_chunks(src)), doc_name="RFP", who="t", when="2026-10-02T09:00")
    assert IM.pending(lib) == [] and IM.build(lib, v1["id"]) is None, "an Original has nothing to compare with"
    # the matrix, read from the Original, with two sentences placed and owned
    M = C.Matrix(os.path.join(d, "m.xlsx"))
    M.items = C.extract([("Kestrel_RFP.docx", A.typed_chunks(src))], [])
    M.outline = [{"num": "1.1", "title": "Management Approach", "level": 1}]
    for it in M.items:
        if "Integrated" in it["text"] or "flight-proven" in it["text"] or "due no later" in it["text"]:
            it.update(decision="Keep", map="1.1 Management Approach", owner="J. Smith" if "flight" in it["text"] else "R. Diaz")
    # the effort's deliverables before the amendment: a volume with our file, a form
    rec = ER.Record(d)
    vol = os.path.join(d, "Vol_1.docx")
    with zipfile.ZipFile(vol, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("docProps/app.xml", "<Properties><Pages>45</Pages></Properties>")
    proposal = D.add(rec, "Volume I Technical", kind="Volume", owner="B. Chen", file=vol)
    f1 = os.path.join(d, "Form.docx")
    fd, fv1 = lib.add(f1 if os.path.exists(f1) else vol, [{"s": "", "t": "", "x": "CLIN 0001 price", "l": ""}], doc_name="Pricing form",
                      who="t", when="2026-10-03T09:00")
    cost = D.add(rec, "Cost volume", kind="Volume", doc_id=fd["id"], form_version=fv1["id"], owner="A. Lee")
    # the amendment arrives, and a new form version
    _d, v2 = lib.add(amd, DV.snapshot("b.docx", A.typed_chunks(amd)), doc_id=doc["id"], who="R. Diaz", when="2026-10-14T09:00")
    _f, fv2 = lib.add(vol, [{"s": "", "t": "", "x": "CLIN 0001 price and travel", "l": ""}], doc_id=fd["id"], who="t", when="2026-10-15T09:00")
    assert [v["label"] for _x, v in IM.pending(lib)] == ["Amendment 1", "Amendment 1"] and IM.pending(lib)[0][1] is fv2
    reg = SR.Register(lib)
    rows = [r for r in reg.rows() if not r.get("hidden")]
    r = IM.build(lib, v2["id"], rows, rec, M, in_list=lambda t: t == "IMS", in_master=lambda t: t == "TRL", common=A.common_words())
    assert r["doc"] == "RFP" and r["version"] == "Amendment 1" and r["prev"] == "Original" and r["who"] == "R. Diaz"
    assert r["text"]["changed"] == 2 and r["text"]["removed"] == 1 and r["text"]["added"] == 3, r["text"]
    # submission requirements
    req = {x["key"]: x for x in r["requirements"]}
    due = req["Due | Proposal"]
    assert due["change"] == "changed" and due["was"].startswith("December 15, 2026") and due["now"].startswith("December 22, 2026")
    assert req["Deliverable | Attachment J-7"]["change"] == "new" and "Small Business Participation Plan" in req["Deliverable | Attachment J-7"]["now"]
    assert req["Page limit | Volume I"]["was"] == "50 pages" and req["Page limit | Volume I"]["now"] == "40 pages", req.keys()
    # deliverables: the new attachment suggested; the volume's limit changed and our file is over; the form's new version
    assert [s["subject"] for s in r["suggested"]] == ["Attachment J-7"]
    assert all(x["id"] != cost for x in r["deliverables"]), "the form is another document's version"
    rf = IM.build(lib, fv2["id"], rows, rec, M)
    assert [x["name"] for x in rf["deliverables"]] == ["Cost volume"] and "New form version Amendment 1" in rf["deliverables"][0]["why"][0]
    pr = next((x for x in r["deliverables"] if x["id"] == proposal), None)
    assert pr is not None and pr["why"][0].startswith("Page limit was 50 pages, now 40 pages") and "45 pages" in pr["why"][0] and pr["over"], r["deliverables"]
    # compliance: changed and removed, with section and owner; new sentences not assigned
    c = r["compliance"]
    assert c["in_matrix"] and [x["id"] for x in c["changed"]][:1] and any(x["owner"] == "R. Diaz" and x["map"] == "1.1 Management Approach"
                                                                          for x in c["changed"]), c["changed"]
    assert [(x["owner"], x["map"]) for x in c["removed"]] == [("J. Smith", "1.1 Management Approach")]
    assert len(c["added"]) == 3 and all(not a["id"] and not a["decision"] for a in c["added"])
    # structure, acronyms, keywords
    assert r["structure"] == [{"num": "L.4.2", "change": "renamed", "was": "Management Approach", "now": "Management and Schedule Approach",
                               "ours": "1.1 Management Approach"}], r["structure"]
    acr = {x["term"]: x for x in r["acronyms"]["new"]}
    assert set(acr) == {"SBPP", "TRL"} and acr["SBPP"]["count"] == 2 and acr["TRL"]["in_master"] and not acr["SBPP"]["in_list"]
    assert r["keywords"] == [{"phrase": "verification by analysis and test", "count": 2}], r["keywords"]
    assert IM.keywords([], ["Verification by analysis and test. Verification by analysis and test."], [{"kind": "added", "new": "Verification by analysis and test."}],
                       have=["verification by analysis and test"]) == []
    # who it touches, counts, headline
    assert set(r["people"]) == {"R. Diaz", "J. Smith", "B. Chen"}, r["people"]
    assert r["counts"]["compliance"] == len(c["changed"]) + 1 + 3 and r["counts"]["deliverables"] == 2
    h = IM.headline(r)
    assert h.startswith("Amendment 1 of RFP: 2 changed, 3 added, 1 removed. It touches 3 submission requirement(s), 2 deliverable(s)"), h
    # the Word report
    p = IM.export_word(os.path.join(d, "impact.docx"), r, "Kestrel")
    x = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
    for want in ("IMPACT REVIEW", "Amendment 1 of RFP", "Submission requirements", "Attachment J-7", "1.1 Management Approach",
                 "Management and Schedule Approach", "SBPP", "verification by analysis and test", "Who it touches", "R. Diaz"):
        assert want in x, want
    from xml.dom import minidom
    minidom.parseString(x.encode("utf-8"))
    # reviewed: no longer pending
    lib.mark_reviewed(v2["id"], who="pm")
    assert [v["id"] for _x, v in IM.pending(lib)] == [fv2["id"]] and len(IM.reviewable(lib)) == 2
    assert IM.build(lib, v2["id"], rows)["reviewed"].endswith("pm")
    # terms: headings in capitals and common words are skipped
    t = IM.terms(["SECTION L - INSTRUCTIONS TO OFFERORS", "The PDR and CDR follow the IMS. Volume II covers it."])
    assert set(t) == {"PDR", "CDR", "IMS"}, t
    print("impact ok")


if __name__ == "__main__":
    run()
