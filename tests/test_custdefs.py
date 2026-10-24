"""Customer-definition extraction on realistic RFP-style text."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import custdefs as C

RFP = [("RFP.pdf (p.3)", """L.4.2 The Offeror shall describe its Integration and Test (I&T) approach, including the Thermal Vacuum (TVAC) campaign.
The Government will evaluate realism against the Integrated Master Schedule (IMS). Deliver per the Contract Data Requirements List (CDRL) A003.
The Space Vehicle (SV) shall survive a Total Ionizing Dose (TID) of 30 krad. See Figure 2 (Rev C) and Section 3.2 (p. 14).
The ground segment uses the Common Ground Architecture (CGA). The Power Control Unit (PCU) provides 28 V.
Telemetry, Tracking and Command (TT&C) uses S-band. Low Earth Orbit (LEO) operations last five years (5).
Systems Engineering and Integration (SE&I) is led by the prime. MEOP (Maximum Expected Operating Pressure) applies to all tanks."""),
       ("SOW.docx (section 'Acronyms', para 40-48)", """ACRONYMS AND ABBREVIATIONS
CDR\tCritical Design Review
PDR - Preliminary Design Review
SOW: Statement of Work
ICD     Interface Control Document
EGSE    Electrical Ground Support Equipment
FFP     Firm-Fixed-Price"""),
       ("Attachment J-2.xlsx (Glossary)", """SOW\tScope of Work
TBD\tTo Be Determined""")]

def run():
    d = C.extract(RFP)
    want = {"I&T": "Integration and Test", "TVAC": "Thermal Vacuum", "IMS": "Integrated Master Schedule",
            "CDRL": "Contract Data Requirements List", "SV": "Space Vehicle", "TID": "Total Ionizing Dose",
            "CGA": "Common Ground Architecture", "PCU": "Power Control Unit", "TT&C": "Telemetry, Tracking and Command",
            "LEO": "Low Earth Orbit", "SE&I": "Systems Engineering and Integration", "MEOP": "Maximum Expected Operating Pressure",
            "CDR": "Critical Design Review", "PDR": "Preliminary Design Review", "ICD": "Interface Control Document",
            "EGSE": "Electrical Ground Support Equipment", "FFP": "Firm-Fixed-Price", "TBD": "To Be Determined"}
    bad = []
    for k, v in want.items():
        got = [x["definition"] for x in d.get(k, [])]
        if v not in got:
            bad.append(f"{k}: want {v!r}, got {got}")
    for junk in ("Rev", "C", "p", "5", "2", "14"):
        if junk in d:
            bad.append(f"junk term {junk!r}: {d[junk]}")
    sow = [x["definition"] for x in d.get("SOW", [])]
    if sow != ["Statement of Work", "Scope of Work"]:
        bad.append(f"SOW conflict: {sow}")
    print(f"found {len(d)} terms; {len(want) - len([b for b in bad if not b.startswith('junk')])}/{len(want)} expected definitions")
    for b in bad:
        print("  MISS", b)
    assert not bad
    results = {"SOW": {}, "PCU": {}, "XYZ": {}}
    assert C.merge_into(results, d) == 2 and results["SOW"]["customer_definitions"] == sow and "customer_definitions" not in results["XYZ"]
    print("custdefs ok")

if __name__ == "__main__":
    run()
