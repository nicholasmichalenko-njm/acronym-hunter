"""2.36.0 Assign: a compliance requirement goes into a section; Context supports requirements (its section follows
the first) or a section itself; clearing removes links to it; section context prints first in the setup documents;
the coverage report says compliance requirement, context or not used; context problems for section context."""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C, setupdoc as SD


def row(i, sec, text):
    return {"id": f"{sec}-{i:02d}", "text": text, "lead": "", "file": "L.docx", "page": "", "section": sec, "section_title": "",
            "actor": "", "type": "Instruction", "strength": "", "suggest": "", "modal": "", "xrefs": "", "compound": False,
            "decision": "", "map": "", "owner": "", "status": "", "response_page": "", "notes": "", "links": "",
            "learned": "", "new": "", "context": "", "loc": "", "key": C.text_key(text), "context_for": "", "draft": "", "draft_cf": ""}


def run():
    a = row(1, "L.4", "The Offeror shall describe the thermal design.")
    b = row(2, "L.4", "Thermal margins matter because the orbit has long eclipses.")
    c = row(3, "L.5", "The Offeror shall provide the schedule.")
    d = row(4, "L.5", "The schedule covers the full period of performance.")
    e = row(5, "L.5", "Page 4 of 12")
    items = [a, b, c, d, e]
    C.assign_requirement(items, [a], "1.1 Thermal")
    C.assign_requirement(items, [c], "1.2 Schedule")
    assert a["decision"] == "Keep" and a["map"] == "1.1 Thermal"
    C.assign_context(items, [b], ["L.4-01", "L.5-03", "L.5-05"])          # L.5-05 is not a requirement: ignored
    assert b["context_for"] == "L.4-01; L.5-03" and b["map"] == "1.1 Thermal", b
    C.assign_context(items, [d], section="1.2 Schedule")
    assert d["context_for"] == "" and d["map"] == "1.2 Schedule" and C.context_label(d) == "Context for section 1.2 Schedule"
    # a requirement moves: its Context (first link) follows
    C.assign_requirement(items, [a], "1.2 Schedule")
    assert b["map"] == "1.2 Schedule", b["map"]
    C.assign_requirement(items, [a], "1.1 Thermal")
    # problems: section context is fine; unattached context is not
    assert C.context_problems(items) == []
    C.assign_context(items, [e], [])
    assert e["map"] == "" and [w for _i, w in C.context_problems(items)] == ["not assigned to a requirement or a section"]
    C.clear_assignment(items, [e])
    # clearing a requirement removes the links to it
    C.clear_assignment(items, [c])
    assert c["decision"] == "" and b["context_for"] == "L.4-01"
    C.assign_requirement(items, [c], "1.2 Schedule")
    # setup documents: section context first, requirement context under its requirement
    M = C.Matrix(os.path.join(tempfile.mkdtemp(), "m.xlsx"), "K"); M.items = items
    M.outline = C.parse_outline("Volume I\n1.1 Thermal\n1.2 Schedule")
    P = SD.placed_in(M)
    assert P["1.1 Thermal"] == ["L.4-01", "L.4-02"], P
    assert P["1.2 Schedule"] == ["L.5-04", "L.5-03"], P
    # coverage report wording
    out = os.path.join(tempfile.mkdtemp(), "cov.docx"); C.write_coverage_docx(M, out)
    with zipfile.ZipFile(out) as z:
        x = z.read("word/document.xml").decode("utf-8")
    assert "Every sentence was read: 2 compliance requirement(s), 2 context, 1 not used." in x
    assert "Compliance requirement" in x and "Context for section 1.2 Schedule" in x and "Not used" in x
    # link_contexts leaves a section's context alone
    C.link_contexts(items)
    assert d["context_for"] == ""
    print("assign ok")


if __name__ == "__main__":
    run()
