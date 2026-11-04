"""3.38.0 the rulebook (rulebook.py): Rule 1 to 13 as one list, each with its group, how it is kept (app, Word, people),
where its values live and the check codes it answers; turning a rule off for every effort; the team's own rules (added,
edited, removed, numbered after the built-in ones); an effort's own exceptions kept in its formatting; the rules in force;
the summary; and each effort's standard carrying the rules off and its response type."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodrules as PRL, rulebook as RB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


class WS:
    """The part of an effort's workspace the rules use."""
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


cfg = tempfile.mkdtemp()
rs = RB.rules(cfg)
check("13 built-in rules, numbered 1 to 13, all on", [r["id"] for r in rs] == [str(i) for i in range(1, 14)] and all(r["on"] for r in rs))
check("every rule has a group, a sentence and how it is kept", all(r["group"] in RB.GROUPS and r["text"] and r["kept"] in RB.KEPT_NAME
                                                                     for r in rs))
check("each rule points to where its values live, never a copy", all(r["where"][0] in RB.WHERE_NAME for r in rs if r["kept"] == "app"))
check("Rule 13 (the AA naming convention) is kept by people and answers no check", RB.get(cfg, 13)["kept"] == "people"
      and not RB.get(cfg, 13)["codes"])
check("check codes lead to their rule", RB.rule_of_code("RU7") == "Rule 7" and RB.rule_of_code("A3") == "Rule 11"
      and RB.rule_of_code("W1") == "Rule 12" and RB.rule_of_code("X9") == "")
check("rules sort by number, then findings no rule names", sorted(["Rule 10", "", "Rule 2"], key=RB.order_key) == ["Rule 2", "Rule 10", ""])

RB.set_on(cfg, 7, False)
check("a rule turned off for every effort is kept off", not RB.get(cfg, 7)["on"] and RB.load(cfg)["off"] == ["7"])
check("a rule off is not in force, and its codes lead nowhere when in force is asked", "7" not in {r["id"] for r in RB.in_force(cfg)}
      and RB.rule_of_code("RU7", cfg) == "")
RB.set_on(cfg, 7, True)
check("and on again", RB.get(cfg, 7)["on"] and RB.load(cfg)["off"] == [])

rid = RB.add(cfg, "  Every figure has   a callout in the text. ", group="Writing")
check("the team's own rule is numbered after the built-in ones and kept by people", rid == "14" and RB.get(cfg, rid)["kept"] == "people"
      and RB.get(cfg, rid)["own"] and RB.get(cfg, rid)["text"] == "Every figure has a callout in the text.")
check("an empty rule is not added", RB.add(cfg, "   ") is None)
rid2 = RB.add(cfg, "Graphics are 300 dpi or better.", group="Nonsense", kept="word")
check("a second own rule takes the next number; an unknown group becomes Approach", rid2 == "15" and RB.get(cfg, rid2)["group"] == "Approach"
      and RB.get(cfg, rid2)["kept"] == "word")
check("an own rule can be edited", RB.edit(cfg, rid, text="Every figure is called out before it appears.", group="Formatting")
      and RB.get(cfg, rid)["text"].startswith("Every figure is called out") and RB.get(cfg, rid)["group"] == "Formatting")
check("a built-in rule cannot be edited", not RB.edit(cfg, 3, text="Something else"))
RB.set_on(cfg, rid2, False)
check("an own rule can be removed, and its off mark goes with it", RB.remove(cfg, rid2) and RB.get(cfg, rid2) is None
      and rid2 not in RB.load(cfg)["off"])
check("a built-in rule cannot be removed", not RB.remove(cfg, 4) and RB.get(cfg, 4) is not None)

ws = WS()
RB.set_effort_on(ws, 2, False)
check("an effort's exception is kept in its formatting", ws.get("prod_std")["rules_off"] == ["2"] and RB.effort_off(ws) == ["2"])
check("the effort's exception takes the rule out of force for that effort only", "2" not in {r["id"] for r in RB.in_force(cfg, ws)}
      and "2" in {r["id"] for r in RB.in_force(cfg)})
RB.set_on(cfg, 8, False)
sm = RB.summary(cfg, ws)
check("the summary counts rules, how they are kept and how many are off here", sm["n"] == 14 and sm["people"] == 2 and sm["off"] == 2
      and sm["app"] + sm["word"] + sm["people"] == 14, sm)

std = PRL.for_effort(cfg, ws)
check("each effort's standard carries the rules off (every effort and this one)", std["_rules_off"] == ["2", "8"], std.get("_rules_off"))
RB.set_effort_on(ws, 2, True)
check("following the rule again clears the effort's exception", "rules_off" not in ws.get("prod_std") and PRL.for_effort(cfg, ws)["_rules_off"] == ["8"])
eff = dict(ws.get("prod_std") or {}); eff["response_type"] = "RFI"; ws.set("prod_std", eff)
check("an effort's response type reaches its standard (Rule 4)", PRL.for_effort(cfg, ws)["response_type"] == "RFI")
check("response types offered", {"RFP", "RFI", "BAA"} <= set(RB.response_types()))
check("Rule 6 is applied to each effort's standard: every heading level's number at 0, one text position",
      len({(l["number_at"], l["text_at"]) for l in std["heading_numbering"]["levels"]}) == 1
      and std["heading_numbering"]["levels"][0]["number_at"] == 0)

with open(os.path.join(cfg, RB.FILE), "w", encoding="utf-8") as f:
    f.write("{not json")
check("a damaged rules file reads as every rule on, no own rules", all(r["on"] for r in RB.rules(cfg)) and len(RB.rules(cfg)) == 13)

n = sum(checks)
print(f"RULEBOOK {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
