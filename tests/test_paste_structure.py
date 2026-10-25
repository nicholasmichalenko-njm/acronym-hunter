"""2.28.0: customer lists pasted or typed (and pictures of lists), and the response structure suggested from the
customer documents for Start an effort."""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"


def run():
    import app_gui as A, compliance as C, structure as S
    P = lambda t: {a: b for a, b in A.parse_client_text(t)}
    excel = "Acronym\tDefinition\nTRL\tTechnology Readiness Level\nCDR\tCritical Design Review\n"
    assert P(excel) == {"TRL": "Technology Readiness Level", "CDR": "Critical Design Review"}, P(excel)
    typed = "KTS - Kestrel Thermal System\nRWA: Reaction Wheel Assembly\nPCU  Power Control Unit\nEGSE Electrical Ground Support Equipment"
    got = P(typed)
    assert got == {"KTS": "Kestrel Thermal System", "RWA": "Reaction Wheel Assembly", "PCU": "Power Control Unit",
                   "EGSE": "Electrical Ground Support Equipment"}, got
    sentence = "The Ground Support Equipment (GSE) arrives first. The team meets weekly."
    assert P(sentence) == {"GSE": "Ground Support Equipment"}, P(sentence)
    assert A.parse_client_text("") == [] and A.parse_client_text("just some words here") == []
    # a picture of a list goes through the picture reader; with AI and ML off nothing is read
    d = tempfile.mkdtemp()
    from PIL import Image
    png = os.path.join(d, "list.png"); Image.new("RGB", (200, 60), "white").save(png)
    A.set_ai_ml(False)
    try:
        assert A.parse_client_list(png) == [] and A.client_list_pictures(png) == ""
    finally:
        A.set_ai_ml(True)
    assert A.parse_client_list(png, pictures=False) == []

    # the response structure from the sample RFP
    rfp = os.path.join(ROOT, "test_samples", "rfp")
    fc = [(f, A.typed_chunks(os.path.join(rfp, f))) for f in sorted(os.listdir(rfp))]
    heads = []
    C.extract(fc, heads)
    res = S.suggest(fc, heads)
    lines = res["text"].splitlines()
    assert lines[0] == "Volume I Technical" and "    1.1 Technical Approach [L.4.1]" in lines and "    1.2 Management Approach [L.4.2]" in lines, lines
    assert "Volume II Management" in lines and "Volume III Cost" in lines and res["volumes"] == 3, lines
    assert any("Past Performance [L.3]" in l for l in lines), "a Section L heading with no volume is listed last to place"
    assert res["total_pages"] == "50" and any("50 pages" in n for n in res["notes"]), res["notes"]
    assert not any("General Instructions" in l for l in lines), "instruction-only headings are not sections"
    vols = S.find_volumes([("x", "Volume I - Technical Proposal (not to exceed 25 pages). Volume II: Cost Volume, 10 pages.")])
    assert vols[1]["title"] == "Technical" and vols[1]["pages"] == "25" and vols[2]["title"] == "Cost" and vols[2]["pages"] == "10", vols
    none = S.suggest([("memo.docx", [("memo.docx (para 1-1)", "Nothing about the proposal here.")])], [])
    assert none["text"] == "" and "Type the structure" in none["notes"][-1]
    outline = C.parse_outline(res["text"])
    lab, score = C.suggest_map({"section": "L.4.1", "text": "Describe the thermal approach.", "lead": ""}, outline)
    assert lab.startswith("1.1 Technical Approach") and score >= 2.5, (lab, score)
    print("paste and structure ok")


if __name__ == "__main__":
    run()
