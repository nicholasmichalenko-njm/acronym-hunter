"""3.21.0 excerpts and bins: an excerpt keeps the customer's words verbatim with document, page, paragraph, numbering
and heading, part by part (rows not next to each other too); it sits in a built-in bin or one the effort made; a value
only when one exists; written formatting rules are checked by phrase when they quote the words, else on Final Checks;
objectives map to sections; a bin taken out leaves its excerpts under Other; a shared bin travels with the team; all of
it is kept in the effort record."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import effortrec as RR, excerpts as EX, teampack as TP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
rec = RR.Record(tmp)
a = {"id": "L.5.2-03", "file": "Section_L.pdf", "page": 14, "section": "L.5.2", "section_title": "Submission Instructions",
     "text": "Proposals shall be submitted electronically to the Contracting Officer no later than 2:00 PM MT on 15 December 2026."}
b = {"id": "L.5.4-01", "file": "Section_L.pdf", "page": 15, "section": "L.5.4", "section_title": "Copies", "text": "Provide one copy."}

# ---------------------------------------------------------------- an excerpt keeps words and place
xid = EX.add(rec, "submit", [EX.part_of(a, para="3", version="Amendment 0001"), EX.part_of(b)], value="2026-12-15 14:00 MT", ref="Due | Proposal")
x = EX.get(RR.Record(tmp), xid)
check("an excerpt keeps the words verbatim, part by part", x is not None and EX.text_of(x).startswith("Proposals shall")
      and EX.text_of(x).endswith("Provide one copy.") and " ... " in EX.text_of(x))
check("and exactly where each part sits", "Section_L.pdf (Amendment 0001) p.14 para 3, L.5.2 Submission Instructions" in EX.where_of(x)
      and "p.15, L.5.4 Copies" in EX.where_of(x), EX.where_of(x))
check("a value only when one exists, and the rule it was filed with", x["value"] == "2026-12-15 14:00 MT" and EX.for_rule(rec, "Due | Proposal"))
check("no words, no excerpt", EX.add(rec, "submit", [EX.part_of(dict(a, text="  "))]) is None)
check("the sentence knows its excerpts and bins", [e["id"] for e in EX.of_sentence(rec, "L.5.4-01")] == [xid]
      and EX.bins_of(rec)["L.5.2-03"] == ["submit"])

# ---------------------------------------------------------------- formatting: measured or written
m = EX.add(rec, "format", [EX.part_of(dict(a, text="Use 12-point Times New Roman."))], value="Font: 12 pt Times New Roman")
w1 = EX.add(rec, "format", [EX.part_of(dict(a, text='Mark each page header and footer "CUI//SP-PROPIN".'))])
w2 = EX.add(rec, "format", [EX.part_of(dict(a, text="Pages shall be numbered consecutively within each volume."))])
check("a formatting excerpt with a value is measured", EX.get(rec, m)["sub"] == "measured")
check("a written rule that quotes the marking is a phrase check", EX.get(rec, w1)["sub"] == "written" and EX.get(rec, w1)["check"] == "phrase"
      and EX.phrase_of(EX.text_of(EX.get(rec, w1))) == "CUI//SP-PROPIN")
check("any other written rule is a Final Checks item", EX.get(rec, w2)["check"] == "final")

# ---------------------------------------------------------------- objectives, key points, edits
o = EX.add(rec, "objective", [EX.part_of(dict(a, text="The Government seeks to reduce launch cost by 30 percent."))])
check("an objective not mapped yet is counted", [e["id"] for e in EX.objectives_unmapped(rec)] == [o])
EX.update(rec, o, sections=["1.1 Technical Approach", "2.1 Cost Approach"])
check("mapped to the sections that answer it", EX.get(RR.Record(tmp), o)["sections"] == ["1.1 Technical Approach", "2.1 Cost Approach"]
      and not EX.objectives_unmapped(rec))
k = EX.add(rec, "keypoint", [EX.part_of(a)], note="Our autonomous ops cut this by half")
EX.update(rec, k, value="", note="Our autonomous ops cut it by 40 percent", part=0, text="Proposals shall be submitted electronically.")
kk = EX.get(RR.Record(tmp), k)
check("a key point keeps a note; the words and note can be fixed later", kk["note"].endswith("40 percent")
      and EX.text_of(kk) == "Proposals shall be submitted electronically." and kk["edited"])
check("counts by bin", EX.counts(rec) == {"submit": 1, "format": 3, "objective": 1, "keypoint": 1}, EX.counts(rec))

# ---------------------------------------------------------------- custom bins
bid = EX.add_bin(rec, "Transition risk", feeds=["setup", "truth", "nope"])
check("a bin of the effort's own: a color, where it feeds, a key", bid and EX.custom_bins(rec)[0]["feeds"] == ["setup", "truth"]
      and EX.custom_bins(rec)[0]["color"] in EX.COLORS and next(b for b in EX.bins(rec) if b["id"] == bid)["key"] == "Alt+1")
check("a name already taken is refused", EX.add_bin(rec, "transition risk") is None and EX.add_bin(rec, "Key points") is None)
c = EX.add(rec, bid, [EX.part_of(b)], note="From kickoff")
cfg = os.path.join(tmp, "cfg")
check("Share with team puts it in the team's bins", EX.share_bin(rec, bid, cfg) and [t["name"] for t in EX.team_bins(cfg)] == ["Transition risk"])
rec2 = RR.Record(tempfile.mkdtemp())
check("another effort on this PC sees the team's bin", any(x["name"] == "Transition risk" and x.get("team") for x in EX.bins(rec2, cfg)))
check("the team's bins travel in a team pack", "bins" in TP.available(cfg))
pack = os.path.join(tmp, "T" + TP.EXT)
TP.make(cfg, pack, ["bins"], name="T")
cfg2 = os.path.join(tmp, "cfg2")
info, data = TP.read(pack)
TP.install(cfg2, info, data)
check("... and install on another PC", [t["name"] for t in EX.team_bins(cfg2)] == ["Transition risk"])
check("taking a bin out leaves its excerpts under Other", EX.remove_bin(rec, bid) == 1 and EX.get(rec, c)["bin"] == "other")
check("an excerpt taken out", EX.remove(rec, c) and EX.get(rec, c) is None)

print(f"EXCERPTS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
