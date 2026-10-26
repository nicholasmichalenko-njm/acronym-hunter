"""Placement learning across proposals (2.30.0): synthetic proposals whose outlines are numbered and titled differently."""
import os, random, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C
import complearn as CL
import placelearn as P

TOPICS = {   # concept: (title variants, requirement sentence templates, volume)
    "thermal": (["Thermal Design", "Thermal Control Subsystem", "Thermal Management", "Thermal Analysis and Design"],
                ["The Offeror shall describe the thermal control design and margins for the {x}.",
                 "Provide thermal analysis results showing temperature limits are met for the {x}.",
                 "The contractor shall maintain heater power and radiator sizing margins for the {x}."], "technical"),
    "power": (["Electrical Power", "Power Subsystem", "Electrical Power System", "Power Generation and Storage"],
              ["Describe the solar array and battery sizing for the {x}.",
               "The Offeror shall show end-of-life power margin for the {x}.",
               "Provide the power budget and battery depth of discharge for the {x}."], "technical"),
    "schedule": (["Integrated Master Schedule", "Schedule", "Program Schedule", "Master Schedule and Milestones"],
                 ["Provide an integrated master schedule with critical path for the {x}.",
                  "The Offeror shall identify key milestones and schedule margin for the {x}.",
                  "Describe how schedule status will be reported monthly for the {x}."], "management"),
    "risk": (["Risk Management", "Risk Mitigation", "Risks and Mitigation", "Program Risk"],
             ["Identify the top technical risks and mitigation plans for the {x}.",
              "The Offeror shall describe the risk management process including likelihood and consequence ratings.",
              "Provide a risk register with burn-down plans for the {x}."], "management"),
    "staffing": (["Key Personnel", "Staffing Plan", "Personnel and Staffing", "Team Organization and Key Personnel"],
                 ["Provide resumes for the program manager and chief engineer.",
                  "The Offeror shall describe the staffing plan and labor categories for the {x}.",
                  "Describe how key personnel will be retained and replaced."], "management"),
    "pastperf": (["Past Performance", "Relevant Experience", "Corporate Experience", "Past Performance References"],
                 ["Provide three references for contracts of similar size and scope.",
                  "The Offeror shall describe relevant experience delivering spacecraft within the last five years.",
                  "Include contract numbers and points of contact for each reference."], "past_performance"),
    "verification": (["Verification and Test", "Test and Verification", "Verification and Validation", "Integration and Test"],
                     ["Describe the environmental test campaign including thermal vacuum and vibration for the {x}.",
                      "The Offeror shall provide the verification matrix mapping requirements to test, analysis, inspection.",
                      "Provide the integration and test flow for the {x}."], "technical"),
}
VOLS = {"technical": ["Technical", "Technical Volume", "Technical Proposal"],
        "management": ["Management", "Management Volume", "Program Management"],
        "past_performance": ["Past Performance", "Past Performance Volume", "Experience"]}
THINGS = ["spacecraft", "bus", "payload", "vehicle", "satellite", "system"]


def proposal(seed):
    r = random.Random(seed)
    lines, sec_of, vi = [], {}, 0
    for vol in ("technical", "management", "past_performance"):
        vi += 1
        lines.append(f"Volume {['I','II','III'][vi-1]} - {r.choice(VOLS[vol])}")
        concepts = [c for c, v in TOPICS.items() if v[2] == vol]
        r.shuffle(concepts)
        for k, c in enumerate(concepts, 1):
            title = r.choice(TOPICS[c][0])
            lines.append(f"{vi}.{k} {title}")
            sec_of[c] = f"{vi}.{k} {title}"
    outline = C.parse_outline("\n".join(lines))
    items, n = [], 0
    for c, (_t, sents, _v) in TOPICS.items():
        for s in sents:
            for _rep in range(2):
                n += 1
                items.append({"id": f"R{n}", "text": s.format(x=r.choice(THINGS)), "lead": "", "file": f"f{seed}",
                              "decision": r.choice(["Keep", "Keep", "Context"]), "map": sec_of[c], "type": "Instruction",
                              "section": f"L.{r.randint(1, 9)}"})
    return outline, items          # reading order: sentences about one topic sit together, as in an RFP


def run():
    d = tempfile.mkdtemp()
    L = CL.Learner(os.path.join(d, "compliance_learned.json"))
    hist = []
    for i in range(1, 8):
        outline, items = proposal(i)
        sid = f"m{i}"
        pl = L.placer()
        chk = pl.check(sid, items, outline) if pl.matrices() else None
        pl.learn(sid, items, outline)
        if chk:
            hist.append(round(chk["top3"] / chk["total"], 2))
    print("top-3 hit rate on each new proposal (learned from the earlier ones):", hist)
    assert hist and hist[-1] >= 0.8 and hist[0] <= hist[-1] + 0.05, hist
    # rank a fresh sentence against a fresh outline with titles worded differently
    outline, _items = proposal(99)
    pl = L.placer()
    it = {"id": "x", "text": "The Offeror shall describe radiator sizing and heater margins.", "type": "Instruction", "section": "L.4"}
    top = pl.rank(it, outline)
    print("thermal sentence ->", top)
    assert top and "Thermal" in top[0][0], top
    # synonym list joins title words that share no letters
    syn = P.parse_synonyms("solution, approach, methodology\nschedule, ims")
    assert P.tokens("Technical Solution", syn) == P.tokens("Technical Methodology", syn), syn
    merged, n = P.merge_synonym_text("risk, mitigation\n", "safety, assurance\nrisk, mitigation\n")
    assert n == 1 and "safety, assurance" in merged, (n, merged)
    assert P.Placer.band(top) in ("strong", "possible"), top
    # saved counts hold numbers only, and survive save, reload and a Knowledge Pack merge
    L.save()
    raw = open(L.path, encoding="utf-8").read()
    assert "thermal" not in raw.lower() and "radiator" not in raw.lower()
    L2 = CL.Learner(L.path)
    assert L2.placer().placed() == L.placer().placed() > 0
    L3 = CL.Learner(os.path.join(d, "other.json"))
    added = L3.merge_pack(raw.encode())
    assert L3.placer().placed() == L.placer().placed(), (added, L3.placer().placed())
    assert len(L3.placer().history()) == len(hist)
    # nothing suggested before there is enough to go on
    L4 = CL.Learner(os.path.join(d, "empty.json"))
    assert L4.placer().rank(it, outline) == []
    print("placement learning ok")


if __name__ == "__main__":
    run()
