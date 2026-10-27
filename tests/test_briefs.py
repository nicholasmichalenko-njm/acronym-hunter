"""2.43.0 author briefs: from an impact review, one brief per person it touches. Changed and removed sentences go to
the section's owner, lead and contributors, quoted; a new sentence goes to the people of the sections its RFP section
feeds; a renamed heading goes to the people of our section named for it; a deliverable's change goes to its owner;
due date, page limit and format changes go to everyone, with an Everyone brief; the text and the Word file."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import impact as IM, briefs as B, docversions as DV, subreq as SR, compliance as C, effortrec as ER, deliverables as D, setupdoc as SD
from test_docversions import amend


def run():
    import app_gui as A
    d = tempfile.mkdtemp()
    orig = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
    src = amend(orig, os.path.join(d, "Kestrel_RFP.docx"), [("Proposals shall not exceed 50 pages", "Volume I shall not exceed 50 pages")])
    amd = amend(src, os.path.join(d, "Kestrel_RFP_Amd1.docx"), [
        ("December 15, 2026", "December 22, 2026"), ("exceed 50 pages", "exceed 40 pages"), ("the five highest", "the ten highest"),
        ("L.4.2 Management Approach", "L.4.2 Management and Schedule Approach"),
        ("an Integrated Master Schedule (IMS) as Attachment J-2.",
         "an Integrated Master Schedule (IMS) as Attachment J-2. The IMS shall show every gate review."),
        ("The Contractor should use flight-proven components where practical.", "")])
    lib = DV.Library(os.path.join(d, "documents"))
    doc, _v1 = lib.add(src, DV.snapshot("a.docx", A.typed_chunks(src)), doc_name="RFP", who="t", when="2026-10-02T09:00")
    M = C.Matrix(os.path.join(d, "m.xlsx"))
    M.items = C.extract([("Kestrel_RFP.docx", A.typed_chunks(src))], [])
    M.outline = C.parse_outline("1.1 Thermal Design\n1.2 Management Approach")
    for it in M.items:
        if "five highest" in it["text"]:
            C.assign_requirement(M.items, [it], "1.1 Thermal Design")
        if "Integrated Master Schedule" in it["text"] or "flight-proven" in it["text"]:
            C.assign_requirement(M.items, [it], "1.2 Management Approach")
    SD.set_people(M, "1.1 Thermal Design", lead="J. Smith", with_="K. Ito")
    SD.set_people(M, "1.2 Management Approach", lead="R. Diaz")
    rec = ER.Record(d)
    vol = os.path.join(d, "Vol_1.docx")
    with zipfile.ZipFile(vol, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("docProps/app.xml", "<Properties><Pages>45</Pages></Properties>")
    D.add(rec, "Volume I Technical", kind="Volume", owner="B. Chen", file=vol)
    _d, v2 = lib.add(amd, DV.snapshot("b.docx", A.typed_chunks(amd)), doc_id=doc["id"], who="R. Diaz", when="2026-10-14T09:00")
    rows = [x for x in SR.Register(lib).rows() if not x.get("hidden")]
    owner_of = lambda it: SD.owner_of(M, it)                                  # noqa: E731
    r = IM.build(lib, v2["id"], rows, rec, M, owner_of)
    bs = B.build(r, M, owner_of, lambda lab: SD.section_people(M, lab))
    assert list(bs) == ["J. Smith", "K. Ito", "R. Diaz", "B. Chen", B.EVERYONE], list(bs)
    js = bs["J. Smith"]
    assert list(js["sections"]) == ["1.1 Thermal Design"] and "the ten highest" in js["sections"]["1.1 Thermal Design"][0]
    assert js["sections"]["1.1 Thermal Design"][0].startswith("Changed (") and "was \"The offeror shall: (a) identify the five highest" in js["sections"]["1.1 Thermal Design"][0]
    assert bs["K. Ito"]["sections"] == js["sections"], "a contributor gets the section's changes too"
    rd = bs["R. Diaz"]["sections"]["1.2 Management Approach"]
    assert any(x.startswith("Removed (") and "flight-proven" in x for x in rd), rd
    assert any(x.startswith("New in RFP L.4.2, which this section answers") and "every gate review" in x for x in rd), rd
    assert any(x.startswith("RFP heading L.4.2 is now \"Management and Schedule Approach\"") for x in rd), rd
    assert bs["B. Chen"]["deliverables"] and bs["B. Chen"]["deliverables"][0].startswith("Volume I Technical: Page limit was 50 pages, now 40 pages")
    ev = bs[B.EVERYONE]["everyone"]
    assert any(x.startswith("Due, Proposal: was December 15, 2026") for x in ev) and any(x == "Page limit, Volume I: was 50 pages, now 40 pages" for x in ev), ev
    assert all(b["everyone"] == ev for b in bs.values())
    t = B.text(r, js, due="December 22, 2026, 2:00 p.m. Mountain Time (57 days)")
    assert t.startswith("Subject: RFP, Amendment 1: what changed for J. Smith\n\nJ. Smith,\nAmendment 1 of RFP arrived (") and \
        "YOUR SECTIONS\n1.1 Thermal Design\n- Changed (" in t and "FOR EVERYONE\n- Due, Proposal" in t and \
        "Proposal due December 22, 2026" in t, t
    te = B.text(r, bs[B.EVERYONE])
    assert te.startswith("Subject: RFP, Amendment 1: what changed for the team\n\nTeam,") and "YOUR SECTIONS" not in te
    assert B.counts(bs["R. Diaz"])["lines"] == 3
    p = B.export_word(os.path.join(d, "briefs.docx"), r, bs, due="December 22, 2026", effort_name="Kestrel")
    x = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
    assert x.count('w:type="page"') == len(bs) - 1 and "AUTHOR BRIEF" in x and "K. Ito" in x and "Your deliverables" in x
    from xml.dom import minidom
    minidom.parseString(x.encode("utf-8"))
    # no matrix, no people: only the deliverable owner and everyone
    bs2 = B.build(IM.build(lib, v2["id"], rows, rec, None))
    assert list(bs2) == ["B. Chen", B.EVERYONE], list(bs2)
    print("briefs ok")


if __name__ == "__main__":
    run()
