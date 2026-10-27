"""2.35.0 draft and commit; Context for several requirements: drafts do not count until committed, back to the
committed state clears a draft, commit reports counts, links survive save and reload, split and merge remap every
link, Prove problems per link, and a shared Context prints under each requirement in the setup documents."""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C, setupdoc as SD


def row(i, sec, text, dec="", typ="Instruction"):
    return {"id": f"{sec}-{i:02d}", "text": text, "lead": "", "file": "L.docx", "page": "", "section": sec, "section_title": "",
            "actor": "", "type": typ, "strength": "", "suggest": "", "modal": "", "xrefs": "", "compound": False,
            "decision": dec, "map": "", "owner": "", "status": "", "response_page": "", "notes": "", "links": "",
            "learned": "", "new": "", "context": "", "loc": "", "key": C.text_key(text), "context_for": "", "draft": "", "draft_cf": ""}


def run():
    a = row(1, "L.4", "The Offeror shall describe the thermal design.", "Keep")
    b = row(2, "L.4", "Thermal margins matter because the orbit has long eclipses.")
    c = row(3, "L.5", "The Offeror shall provide the power budget.", "Keep")
    d = row(4, "L.5", "Page 4 of 12")
    items = [a, b, c, d]
    # a draft does not count
    assert C.set_draft(b, "Context", ["L.4-01"]) and b["decision"] == "" and C.eff(b) == "Context" and C.eff_cf(b) == "L.4-01"
    C.set_draft(b, "Context", ["L.4-01", "L.5-03", "L.4-01"])
    assert C.eff_cf(b) == "L.4-01; L.5-03" and C.cf_ids(C.eff_cf(b)) == ["L.4-01", "L.5-03"]
    C.set_draft(d, "Drop")
    M = C.Matrix(os.path.join(tempfile.mkdtemp(), "m.xlsx"), "Kestrel"); M.items = items
    cnt = M.counts()
    assert cnt["drafts"] == 2 and cnt["Context"] == 0 and cnt[""] == 2 and cnt["open"] == 0, cnt
    # back to the committed state clears the draft
    C.set_draft(a, "Drop"); assert a["draft"] == "Drop"
    C.set_draft(a, "Keep"); assert a["draft"] == "" and C.eff(a) == "Keep"
    C.set_draft(a, ""); assert a["draft"] == C.UNDECIDED and C.eff(a) == ""
    C.set_draft(a, "Keep")
    # drafts survive save and reload (crash safety before commit)
    M.save(); N = C.Matrix(M.path).load()
    nb = next(x for x in N.items if x["id"] == "L.4-02")
    assert nb["draft"] == "Context" and nb["draft_cf"] == "L.4-01; L.5-03" and nb["decision"] == "", nb
    # commit part, then the rest
    r = C.commit([b])
    assert r == {"n": 1, "Keep": 0, "Context": 1, "Drop": 0, "Undecided": 0, "links": 2}, r
    assert b["decision"] == "Context" and b["context_for"] == "L.4-01; L.5-03" and not b["draft"]
    assert C.commit_text(r, 1) == "Committed 1 decision: 1 Context with 2 links. 1 draft left."
    r = C.commit(items)
    assert r["n"] == 1 and d["decision"] == "Drop" and C.commit_text(r, 0).endswith("No drafts left.")
    assert C.commit_text(C.commit(items), 0) == "Nothing to commit here: no drafts."
    # an older matrix (no Draft columns) loads with every decision committed
    assert all(x.get("draft", "") == "" for x in N.items if x["id"] in ("L.5-03",))
    # links follow a split or merge, in the committed and the drafted link
    C.set_draft(b, "Context", ["L.4-01", "L.5-03", "L.9-99"])
    C.remap_context_for(items, "L.5-03", "L.5-03a")
    assert b["context_for"] == "L.4-01; L.5-03a" and b["draft_cf"] == "L.4-01; L.5-03a; L.9-99"
    C.remap_context_for(items, "L.5-03a", "L.5-03")
    b["draft"] = b["draft_cf"] = ""
    # Prove: each link is checked; a shared Context placed with one of its requirements is fine
    a["map"], c["map"], b["map"] = "1.1 Thermal", "1.2 Power", "1.1 Thermal"
    assert C.context_problems(items) == []
    c["decision"] = "Drop"
    assert [w for _i, w in C.context_problems(items)] == ["its requirement L.5-03 is no longer Keep"]
    c["decision"] = "Keep"
    b["map"] = "1.3 Other"
    assert "placed in 1.3 Other, its requirements in 1.1 Thermal, 1.2 Power" in C.context_problems(items)[0][1]
    b["map"] = "1.1 Thermal"
    # setup documents: the shared Context prints under each requirement, naming the other
    M.items = items
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal\n1.2 Power")
    P = SD.placed_in(M)
    assert P["1.1 Thermal"] == ["L.4-01", "L.4-02"] and P["1.2 Power"] == ["L.5-03", "L.4-02"], P
    out = tempfile.mkdtemp()
    SD.export(M, out)
    xml = ""
    for f in os.listdir(out):
        if f.endswith(".docx"):
            with zipfile.ZipFile(os.path.join(out, f)) as z:
                xml += z.read("word/document.xml").decode("utf-8")
    assert xml.count("long eclipses") == 2 and "Also support for L.5-03" in xml and "Also support for L.4-01" in xml
    # the coverage report names every requirement
    cp = os.path.join(out, "cov.docx"); C.write_coverage_docx(M, cp)
    with zipfile.ZipFile(cp) as z:
        assert "Support for L.4-01; L.5-03" in z.read("word/document.xml").decode("utf-8")
    print("draft commit ok")


if __name__ == "__main__":
    run()
