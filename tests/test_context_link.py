"""2.33.0 Context linked to its requirement: default link, remap on merge, problems, setup order, outputs, reload."""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C, setupdoc as SD


def row(i, sec, text, dec, typ="Instruction"):
    return {"id": f"{sec}-{i:02d}", "text": text, "lead": "", "file": "L.docx", "page": "", "section": sec, "section_title": "",
            "actor": "", "type": typ, "strength": "", "suggest": "", "modal": "", "xrefs": "", "compound": False,
            "decision": dec, "map": "", "owner": "", "status": "", "response_page": "", "notes": "", "links": "",
            "learned": "", "new": "", "context": "", "loc": "", "key": C.text_key(text), "context_for": ""}


def run():
    items = [row(1, "L.4", "The Offeror shall describe the thermal design.", "Keep"),
             row(2, "L.4", "Thermal margins matter because the orbit has long eclipses.", "Context", "Context"),
             row(3, "L.4", "The Offeror shall provide the power budget.", "Keep"),
             row(4, "L.5", "Background on the mission.", "Context", "Context"),
             row(5, "L.5", "The Offeror shall provide a schedule.", "Keep"),
             row(6, "L.6", "Unrelated note with no requirement nearby.", "Context", "Context")]
    n = C.link_contexts(items)
    by = {it["id"]: it for it in items}
    assert by["L.4-02"]["context_for"] == "L.4-01", by["L.4-02"]["context_for"]      # the nearest Keep before it
    assert by["L.5-04"]["context_for"] == "L.5-05"                                    # none before in L.5: the one after
    assert by["L.6-06"]["context_for"] == "" and n == 2
    probs = dict((it["id"], why) for it, why in C.context_problems(items))
    assert probs == {"L.6-06": "not assigned to a requirement or a section"}, probs
    # merging the requirement keeps the link on the merged row
    C.merge_items(items, ["L.4-01", "L.4-03"])
    assert by["L.4-02"]["context_for"] == "L.4-01"
    items.append(row(7, "L.4", "The Offeror shall list risks.", "Keep"))
    by["L.4-02"]["context_for"] = "L.4-07"
    C.merge_items(items, ["L.4-01", "L.4-07"])
    assert by["L.4-02"]["context_for"] == "L.4-01", by["L.4-02"]["context_for"]
    # placed apart: a problem
    by["L.4-01"]["map"], by["L.4-02"]["map"] = "1.1 Thermal", "1.2 Power"
    assert any(it["id"] == "L.4-02" and "placed in 1.2 Power" in why for it, why in C.context_problems(items))
    by["L.4-02"]["map"] = "1.1 Thermal"
    # a decision that is no longer Context loses its link
    by["L.6-06"]["decision"] = "Drop"; by["L.6-06"]["context_for"] = "L.5-05"
    C.link_contexts(items)
    assert by["L.6-06"]["context_for"] == ""
    # the setup prints Context right under its requirement, even when the matrix order puts it elsewhere
    d = tempfile.mkdtemp()
    M = C.Matrix(os.path.join(d, "M.xlsx"), "T")
    items2 = [row(1, "L.4", "Context that the RFP puts first.", "Context", "Context"),
              row(2, "L.4", "The Offeror shall describe A.", "Keep"),
              row(3, "L.4", "The Offeror shall describe B.", "Keep")]
    items2[0]["context_for"] = "L.4-03"
    for it in items2:
        it["map"] = "1.1 Thermal"
    M.items = items2
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal")
    order = SD.placed_in(M)["1.1 Thermal"]
    assert order == ["L.4-02", "L.4-03", "L.4-01"], order
    # the matrix keeps the link; the coverage report names it
    M.save()
    N = C.Matrix(M.path).load()
    assert next(x for x in N.items if x["id"] == "L.4-01")["context_for"] == "L.4-03"
    cp = os.path.join(d, "cov.docx"); C.write_coverage_docx(N, cp)
    assert "Context for L.4-03" in zipfile.ZipFile(cp).read("word/document.xml").decode()
    # an amendment re-read keeps the link for unchanged sentences
    new = [dict(x, context_for="", decision="") for x in items2]
    merged = C.merge_reread(N.items, new)
    assert next(x for x in merged if x["id"] == "L.4-01")["context_for"] == "L.4-03"
    print("context link ok")


if __name__ == "__main__":
    run()
