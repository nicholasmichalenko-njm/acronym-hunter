"""The response structure without a screen (2.60.0, both editions): where a structure can start from, and setting
it on the matrix so every assignment stays valid. Rules only (No AI); nothing leaves the PC."""
import zipfile
import compliance as C
import setupdoc as SD


def from_headings(M, letter="L"):
    """The RFP's numbered headings in Section letter ("" or "All": every numbered heading) as outline entries."""
    return C.outline_from_headings(M.headings, "" if letter in ("", "All") else letter)


def from_rfp_outline(M):
    """The RFP's own outline (headers marked or found, in order, with levels); each RFP section is mapped to the
    proposal section made from it, unless the person mapped it already."""
    import rfpoutline as RO
    out = RO.as_outline(M)
    for o in out:
        if o["num"] and not RO.mapped(M, o["num"]):
            RO.map_section(M, o["num"], C.outline_label(o))
    return out


def from_word(path):
    """Heading 1-6 paragraphs of a Word document as outline entries."""
    with zipfile.ZipFile(path) as z:
        return C.outline_from_docx_xml(z.read("word/document.xml"))


def apply(M, text):
    """Set the structure from its text (one section per line). Sentences in sections no longer there lose that
    section (a sentence that lost its first section keeps its next one). Returns (sections, mappings cleared)."""
    ol = C.parse_outline(text)
    M.outline = ol
    labels = {C.outline_label(o) for o in ol}
    lost = 0
    for it in M.items:
        if it.get("map") and it["map"] not in labels:
            it["map"] = ""
            lost += 1
    S = SD.setup_of(M)
    for lab in [l for l in S["copies"] if l not in labels]:
        S["copies"].pop(lab, None)
    for it in M.items:
        if not it.get("map"):
            rest = SD.item_sections(M, it)
            if rest:
                it["map"] = rest[0]
                S["copies"][rest[0]] = [i for i in S["copies"].get(rest[0], []) if i != it["id"]]
    M.log("outline", f"outline set: {len(ol)} sections" + (f"; {lost} mappings cleared" if lost else ""))
    M.pending = True
    return len(ol), lost


def section_counts(M):
    """{section label: (compliance requirements, context)} counting every section a sentence is in."""
    out = {}
    for it in M.items:
        d = it.get("decision")
        if d not in ("Keep", "Context"):
            continue
        for lab in SD.item_sections(M, it) or ([it["map"]] if it.get("map") else []):
            k, c = out.get(lab, (0, 0))
            out[lab] = (k + (d == "Keep"), c + (d == "Context"))
    return out
