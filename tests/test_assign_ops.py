"""2.59.0 Assign decisions without a screen (assign_ops, used by the Qt edition) and reading without a screen
(compliance_read, used by both editions)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import compliance as C, setupdoc as SD, compliance_read as CR, assign_ops as AO

B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples")
PDF = os.path.join(B, "rfp_walk", "Section_L_print.pdf")


def run():
    items, heads, src, empty = CR.read_files([PDF], lambda p: [])
    assert len(items) == 44 and not empty and src[0][0] == "Section_L_print.pdf" and len(src[0][1]) == 64, (len(items), empty)
    assert all(it.get("place") for it in items), "every PDF sentence has its place"
    assert not any("FA8811-26-R-0099" in it["text"] for it in items), "no header in the review"
    M = CR.new_matrix(os.path.join(B, "_none_Compliance_Matrix.xlsx"), items, heads, src)
    assert M.outline and M.name == "_none"
    M.outline = C.parse_outline("1 Technical\n1.1 Approach\n2 Management")
    R = AO.Review(M)
    by = lambda w: next(it for it in M.items if it["text"].startswith(w))
    a, b, c = by("The Offeror shall describe its technical approach"), by("Each volume shall be written"), by("Information provided")
    assert R.req([a], "1.1 Approach") == 1 and a["decision"] == "Keep" and a["map"] == "1.1 Approach" and R.last_req == a["id"]
    assert R.req([a], "2 Management") == 1 and SD.item_sections(M, a) == ["1.1 Approach", "2 Management"], "a second section"
    assert R.remove_section(a, "2 Management") and SD.item_sections(M, a) == ["1.1 Approach"]
    assert R.req([b], "Nope") == 0, "only sections of the structure"
    R.req([b], "2 Management")
    R.last_req = a["id"]
    R.ctx([c])
    assert c["decision"] == "Context" and C.cf_ids(c["context_for"]) == [a["id"]], c.get("context_for")
    R.link(c, b["id"])
    assert C.cf_ids(c["context_for"]) == [a["id"], b["id"]] and R.related(c) == ([a["id"], b["id"]], "hosts")
    assert R.related(a) == ([c["id"]], "supports")
    R.unlink(c, b["id"])
    assert C.cf_ids(c["context_for"]) == [a["id"]]
    assert R.set_authors([a, c], "A. Lee; K. Park") == 2 and a["owner"] == c["owner"] == "A. Lee, K. Park"
    assert R.set_notes(a, " Use the figure. ") and a["notes"] == "Use the figure." and not R.set_notes(a, "Use the figure.")
    assert R.counts() == {"1.1 Approach": 1, "2 Management": 1}
    g = by("Offerors are cautioned")
    R.customer([g]); assert g["decision"] == "Customer"
    R.clear([g]); assert g["decision"] in ("", "Drop") and not g.get("map")
    x1, x2 = by("Pages shall be"), by("Each page shall be numbered")
    first = R.combine([x1, x2])
    assert first is x1 and "Each page shall be numbered" in x1["text"] and x2 not in M.items and ";" in x1["place"], x1.get("place")
    n0 = len(M.items)
    parts = R.split(x1, x1["text"].index("Each page"))
    assert len(parts) == 2 and len(M.items) == n0 + 1 and parts[0]["id"].endswith("a") and parts[1]["text"].startswith("Each page")
    assert R.undo_last() and len(M.items) == n0, "undo the split"
    for _ in range(20):
        R.undo_last()
    assert not any(it.get("decision") for it in M.items), "undo all the way back"
    # nothing missed
    assert CR.complete(M) == 0 and "all" in CR.text_check_line(CR.text_check(M))
    print("ASSIGN OPS PASS")


if __name__ == "__main__":
    run()
