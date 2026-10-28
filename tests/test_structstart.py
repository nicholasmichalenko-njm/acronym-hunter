"""2.69.0 how a response structure starts, for an RFP that does not use Sections L and M: what it prescribes (volumes
named in its headings and text, a list after "shall be organized as follows:"), its headings from one document or all,
blank; L and M suggested from section titles and wording (shown, not put in the matrix until set); copying an RFP
section with its subsections into the structure maps it and places its requirements; numbering made in Assign survives
saving and reopening, and a new section never takes a number already used."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import compliance as C, setupdoc as SD, structstart as SS, outline_ops as O, rfpoutline as RO
from test_assign import row


def rfp():
    M = C.Matrix(os.path.join(tempfile.mkdtemp(), "Osprey_Matrix.xlsx"), "Osprey")
    M.headings = [{"num": n, "title": t, "file": "Osprey_RFP.docx"} for n, t in (
        ("5", "PROPOSAL PREPARATION INSTRUCTIONS"), ("5.1", "General"), ("5.2", "Volume 1 – Technical Proposal"),
        ("5.2.1", "Technical Approach"), ("5.2.2", "Staffing Plan"), ("5.2.2.1", "Key Personnel"),
        ("5.3", "Volume 2 - Price Proposal"), ("6", "EVALUATION CRITERIA"), ("6.1", "Technical Factor"))]
    M.headings.append({"num": "3.1", "title": "Spacecraft Bus", "file": "Osprey_SOW.docx"})

    def r(i, sec, title, text, typ="Instruction", lead="", f="Osprey_RFP.docx"):
        x = row(i, sec, text)
        x.update(section_title=title, type=typ, lead=lead, file=f)
        return x
    M.items = [
        r(1, "5.1", "General", "Volume 3, Past Performance, is due five days before the proposal.", "Information"),
        r(2, "5.2", "Volume 1 – Technical Proposal", "(a) Executive Summary", lead="Volume 1 shall be organized as follows:"),
        r(3, "5.2", "Volume 1 – Technical Proposal", "(b) Transition Plan; no more than five pages", lead="Volume 1 shall be organized as follows:"),
        r(4, "5.2.2", "Staffing Plan", "The Offeror shall describe its staffing plan."),
        r(5, "5.2.2.1", "Key Personnel", "The Offeror shall provide resumes for key personnel."),
        r(6, "6.1", "Technical Factor", "The Government will evaluate the staffing plan.", "Evaluation"),
        r(7, "", "", "The offeror shall submit the proposal electronically."),
        r(8, "3.1", "Spacecraft Bus", "The contractor shall deliver the bus.", "SOW", f="Osprey_SOW.docx"),
    ]
    SD.set_doc(M, "Osprey_RFP.docx", "R", "RFP")
    SD.set_doc(M, "Osprey_SOW.docx", "S", "SOW")
    return M


def run():
    M = rfp()
    by = {it["id"]: it for it in M.items}
    ol, why = SS.prescribed(M)
    labs = [C.outline_label(o) for o in ol]
    assert labs[:6] == ["Volume I Technical Proposal", "1 Executive Summary", "2 Transition Plan", "3 Technical Approach",
                        "4 Staffing Plan", "4.1 Key Personnel"], labs
    assert "Volume II Price Proposal" in labs and "Volume III Past Performance" in labs, labs
    assert all(o["level"] >= 1 for o in ol) and any("organized as follows" in w for w in why), why
    assert not any(l.startswith("Volume") and "Evaluation" in l for l in labs), "evaluation criteria are not a volume"
    # headings: all, one document, one letter
    allh = SS.from_headings(M, "All")
    assert [o["num"] for o in allh][:2] == ["5", "5.1"] and allh[0]["level"] == 1 and allh[0]["title"] == "Proposal Preparation Instructions"
    sow = SS.from_headings(M, "All", ["Osprey_SOW.docx"])
    assert [C.outline_label(o) for o in sow] == ["3.1 Spacecraft Bus"] and sow[0]["level"] == 1
    assert SS.from_headings(M, "L") == [], "no Section L in this RFP: nothing assumed"
    # L and M from titles and wording; the matrix takes them only once set
    assert SD.lm_why(M, by["5.2.2-04"]) == ("L", "the wording tells the offeror what to submit"), SD.lm_why(M, by["5.2.2-04"])
    assert SD.lm_why(M, by["6.1-06"])[1] == "the RFP section is titled Technical Factor", SD.lm_why(M, by["6.1-06"])
    assert SD.lm_suggest(M, by["6.1-06"]) == "M" and SD.lm_suggest(M, by["5.2.2-04"]) == "L"
    assert SD.lm_suggest(M, by["-07"]) == "L", SD.lm_why(M, by["-07"])
    assert SD.lm_suggest(M, by["3.1-08"]) == "", "SOW work: no suggestion"
    assert SD.lm_of(M, by["6.1-06"]) == "", "a suggestion from titles or wording is not in the matrix until set"
    SD.set_lm(M, [by["6.1-06"]], "M")
    assert SD.lm_of(M, by["6.1-06"]) == "M" and SD.full_ref(M, by["6.1-06"]) == "R-M-6.1"
    assert SD.full_ref(M, by["5.2.2-04"]) == "R-5.2.2", "no L or M set: the reference has none"
    # start: prescribed, then blank
    SS.apply(M, ol)
    assert SD.volumes_of(M)[0] == "several" and len(SD.volumes_of(M)[2]) == 3
    SS.apply(M, [])
    assert M.outline == []
    # copy an RFP section with its subsections; its requirements with no section go into it
    C.assign_requirement(M.items, [by["5.2.2-04"], by["5.2.2.1-05"]], "")
    v1 = O.add_volume(M, "Technical")
    made = SS.copy_section(M, by["5.2.2-04"], parent=v1, with_subsections=True)
    assert made[0] == "1 Staffing Plan" and made[1:] == ["1.1 Key Personnel"], made
    assert by["5.2.2-04"]["map"] == "1 Staffing Plan" and by["5.2.2.1-05"]["map"] == "1.1 Key Personnel"
    assert RO.mapped(M, "5.2.2") == "1 Staffing Plan" and M.outline[O.index_of(M, made[0])]["from"] == "5.2.2"
    new = O.rename(M, made[0], "Our Team")
    assert RO.mapped(M, "5.2.2") == new and by["5.2.2-04"]["map"] == new, "the RFP mapping follows a rename"
    # numbering made in Assign survives saving; a new section never reuses a number
    O.add(M, "Management", parent=v1)
    M.save()
    M2 = C.Matrix(M.path).load()
    assert [o.get("auto") for o in M2.outline] == [None, True, True, True], [o.get("auto") for o in M2.outline]
    assert M2.outline[1].get("from") == "5.2.2"
    lab = O.add(M2, "Transition", parent=O.labels(M2)[0])
    assert lab == "3 Transition", O.labels(M2)
    typed = C.Matrix(os.path.join(tempfile.mkdtemp(), "T.xlsx"), "T")
    typed.items = []
    typed.outline = C.parse_outline("1 Intro\n2 Approach")                # typed numbers, not made here
    assert O.add(typed, "Risk") == "3 Risk", O.labels(typed)
    print("structure start ok")


if __name__ == "__main__":
    run()
