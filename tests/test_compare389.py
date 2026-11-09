"""3.89.0 Compare on the page, the rules: editorial changes (punctuation, spacing, capitals, a heading's number; never a
number inside a sentence); the new and changed words by position; the suggested choice with its reason (update the placed
sentence, remove it, add a new requirement to the section its heading maps to, a submission rule, No action for
editorial); decision 6 (what each change touches, recorded per pair, the flags on placed sentences until the change is
decided, an added sentence flagging what was placed from its heading); each change found on the new version's page, a
removed one marked where it stood; the page strip. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import changereview as CR, comparemap as CM, docversions as DV
from pdfmake import make_pdf

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


class M:
    def __init__(self):
        self.setup, self.pending = None, False
        self.outline = [{"num": "1", "title": "Technical Approach", "level": 1}, {"num": "2", "title": "Management", "level": 1},
                        {"num": "2.1", "title": "Risk Management", "level": 2}]
        self.items = []

    def add(self, iid, text, num, title, decision="Keep", map_=""):
        self.items.append({"id": iid, "text": text, "section": num, "section_title": title, "file": "Kestrel_RFP.pdf",
                           "decision": decision, "type": "Requirement", "map": map_})
        return self.items[-1]


def r_(kind, old, new):
    return {"kind": kind, "old": old, "new": new, "section": "", "diff": [], "oi": None, "nj": None}


ed = CM.editorial
check("punctuation and capitals only: editorial", ed(r_("changed", "The Offeror shall submit a plan.", "The offeror shall submit a plan;")))
check("a heading renumbered: editorial", ed(r_("changed", "L.3.5 Staffing Approach", "L.3.6 Staffing Approach")))
check("a number inside a sentence is never editorial", not ed(r_("changed", "Volume I shall not exceed 50 pages.", "Volume I shall not exceed 40 pages.")))
check("a word changed is not editorial", not ed(r_("changed", "the five highest risks", "the ten highest risks")))
check("changed words by position", CM.changed_words(r_("changed", "the five highest risks", "the ten highest risks")) == [1]
      and CM.changed_words(r_("added", "", "Each risk has an owner")) == [0, 1, 2, 3, 4])

old = [("L.3", "Volumes", "Volume I Technical shall not exceed 50 pages."), ("L.4", "Risk", "The Offeror shall identify the five highest risks."),
       ("L.4", "Risk", "Risk reviews happen weekly at the operations center."), ("L.4", "Risk", "Each risk has an owner."),
       ("L.5", "Transition", "Transition takes ninety days.")]
new = [("L.3", "Volumes", "Volume I Technical shall not exceed 40 pages."), ("L.4", "Risk", "The Offeror shall identify the ten highest risks."),
       ("L.4", "Risk", "Each risk has an owner"), ("L.4", "Risk", "The Offeror shall describe a mitigation plan for each high risk."),
       ("L.5", "Transition", "Transition takes ninety days.")]
sn = lambda L: [{"s": s, "t": t, "x": x} for s, t, x in L]                       # noqa: E731
rows = CR.keyed(DV.compare(sn(old), sn(new)))
kinds = [r["kind"] for r in rows]
check("the comparison under test", kinds == ["changed", "changed", "removed", "changed", "added", "same"], kinds)
m = M()
pl = m.add("R-1", old[0][2], "L.3", "Volumes", map_="1 Technical Approach")
rk = m.add("R-2", old[1][2], "L.4", "Risk", map_="2.1 Risk Management")
wk = m.add("R-3", old[2][2], "L.4", "Risk", map_="2.1 Risk Management")
import docintake as DI
links = DI.link(m, rows)
sug = [CM.suggest(r, links[k], m, (), sn(new)) for k, r in enumerate(rows)]
check("a changed sentence that is placed: Update our wording, with the reason", sug[1]["kind"] == "updates" and sug[1]["target"] == "R-2"
      and sug[1]["why"] == "R-2 in 2.1 Risk Management has the old wording", sug[1])
check("a removed sentence that is placed: Remove it", sug[2]["kind"] == "removes" and sug[2]["target"] == "R-3", sug[2])
check("editorial: No action", sug[3]["kind"] == "none")
check("an added requirement with no map yet: Add, pick the section", sug[4]["kind"] == "new" and sug[4]["target"] == ""
      and "under L.4" in sug[4]["why"], sug[4])
import homesuggest as HS
HS.map_heading(m, "L.4", "2.1 Risk Management")
s4 = CM.suggest(rows[4], links[4], m, (), sn(new))
check("... and once L.4 maps to a section: Add to it, with the reason", s4["kind"] == "new" and s4["target"] == "2.1 Risk Management"
      and s4["why"] == "A new requirement under L.4; L.4 is answered by 2.1 Risk Management", s4)
check("a submission rule with nothing placed: Updates a submission rule", CM.suggest(rows[0], [], m, ("rule",), sn(new))["kind"] == "rule")
check("an unchanged sentence suggests nothing", CM.suggest(rows[5], [], m, (), sn(new)) is None)
# decision 6
t = CM.touches(rows, links, m, sn(new))
check("what each change touches: the placed sentences, changed and removed", t[rows[1]["key"]]["items"] == ["R-2"]
      and t[rows[2]["key"]]["how"] == "removed" and t[rows[0]["key"]]["items"] == ["R-1"])
check("an added sentence touches what was placed from its heading", set(t[rows[4]["key"]]["items"]) == {"R-2", "R-3"}
      and t[rows[4]["key"]]["heading"] == "L.4")
check("an editorial change touches nothing", rows[3]["key"] not in t)
tmp = tempfile.mkdtemp()
rv = CR.Review(tmp).load()
va, vb = {"id": "v1", "label": "Original"}, {"id": "v2", "label": "Amendment 1"}
rv.opened({"id": "d1", "name": "Kestrel RFP"}, va, vb, rows, save=False)
rv.set_touch(CR.pair_key(va, vb), t)
rv = CR.Review(tmp).load()
fl = CM.flags(m, rv)
check("flags on placed sentences, saved with the pair", fl["R-2"][0]["text"] == "Changed in Amendment 1" and fl["R-3"][0]["text"] == "Removed in Amendment 1"
      and any(x["text"] == "Amendment 1 added text under L.4" for x in fl["R-2"]), fl)
rv.decide(CR.pair_key(va, vb), rows[1]["key"], "updates", "R-2")
fl = CM.flags(m, rv)
check("a decided change takes its flag off; the others stay", not any(x["key"] == rows[1]["key"] for x in fl.get("R-2", []))
      and "R-3" in fl)
wk["map"] = ""
check("a sentence no longer placed carries no flag", "R-3" not in CM.flags(m, rv))
check("the flags keep the place: nothing moves", rk["map"] == "2.1 Risk Management" and pl["map"] == "1 Technical Approach")
# on the page
pdf = os.path.join(tmp, "Kestrel_RFP_Amd1.pdf")
make_pdf(pdf, [["L.3 Volumes", new[0][2], "L.4 Risk", new[1][2], new[2][2]], [new[3][2], "L.5 Transition", new[4][2]]])
placed = CM.place(pdf, rows)
check("each change found on the new version's page", placed[rows[0]["key"]]["page"] == 1 and placed[rows[4]["key"]]["page"] == 2
      and placed[rows[0]["key"]]["rects"], {k: v["page"] for k, v in placed.items()})
check("the changed word is marked by itself", len(placed[rows[0]["key"]]["changed"]) == 1 and len(placed[rows[4]["key"]]["changed"]) >= 10)
rm = placed[rows[2]["key"]]
check("a removed sentence is marked where it stood, just before the next one", rm.get("removed") and rm["page"] == 1
      and rm["rects"][0][3] <= placed[rows[3]["key"]]["rects"][0][1], rm)
check("an unchanged sentence is not marked", rows[5]["key"] not in placed)
st = CM.page_status(placed, rows, lambda k: k == rows[4]["key"])
check("the strip: a page with a change to decide, and a page whose changes are all decided", st == {1: "todo", 2: "done"}, st)

print(f"COMPARE 389 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
