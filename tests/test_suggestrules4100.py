"""4.10.0: the shred's phrase rules as one growing team list (morning answer 15): the Suggestion rules sheet of Company
Standards.xlsx, edited in Excel or made in the app; Retired rules stay listed and are not used; how often each rule was
kept and not right, from every effort on every PC that shares the team library (each PC writes only its own file).
Fictional content."""
import json, os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import openpyxl
import suggestrules as SR, teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


cfg = A.CONFIG_DIR
S = {"team_library": ""}
T.tick(cfg, S)                                                  # the first write
SR.add_rule(cfg, None, "proposals are limited to", "L", scope="team", why="A page limit is an instruction", who="Pat")
check("a team rule made in the app marks the workbook to write", T.state(cfg).get("dirty") is True)


class WS:                                                       # an effort's workspace: two suggestions kept, one not right
    def __init__(self, root, recs):
        self.root, self.d = root, {"suggestions": recs}

    def get(self, k):
        return self.d.get(k)


w1 = WS(os.path.join(tmp, "Kestrel"), {"a": {"cat": "L", "rule": "Proposals are  limited to", "state": "accepted"},
                                       "b": {"cat": "L", "rule": "proposals are limited to", "state": "accepted"},
                                       "c": {"cat": "L", "rule": "proposals are limited to", "state": "rejected"},
                                       "d": {"cat": "SOW", "rule": "", "state": "accepted"}})
check("an effort's tally: kept and not right per rule (only suggestions that came from a rule)",
      SR.tally(w1) == {"proposals are limited to": [2, 1]}, SR.tally(w1))
sums = T.sync_scores(cfg, w1, S)
other = os.path.join(T.folder(cfg, S), "Lists", "Suggestion scores", "LAPTOP7.json")
json.dump({"format": 1, "scores": {"proposals are limited to": [1, 0]}}, open(other, "w"))
sums = T.sync_scores(cfg, None, S)
check("the counts add every PC's file in the team library", sums.get("proposals are limited to") == [3, 1], sums)
T.tick(cfg, S)
book = T.book_path(cfg, S)
wb = openpyxl.load_workbook(book)
sh = wb["Suggestion rules"]
hdr = [c.value for c in sh[1]]
row = {h: c.value for h, c in zip(hdr, next(sh.iter_rows(min_row=2)))}
check("the Suggestion rules sheet: the phrase, what it suggests in words, why, status, who, and the counts",
      hdr == ["Phrase", "Suggests", "Why", "Status", "Added by", "Added", "Times kept", "Times not right"]
      and row["Phrase"] == "proposals are limited to" and row["Suggests"] == "L (Instructions)" and row["Status"] == "Approved"
      and row["Times kept"] == 3 and row["Times not right"] == 1, row)
sh.cell(2, hdr.index("Suggests") + 1).value = "M (Evaluation)"
sh.append(["will be evaluated on", "M (Evaluation)", "Evaluation wording", "Approved", "", "", None, None])
sh.append(["the government may", "Ignore", "Not ours", "Retired", "", "", None, None])
sh.append(["xx", "L", "", "Approved", "", "", None, None])                       # too short: left out
wb.save(book); time.sleep(0.02)
T.tick(cfg, S)
rules = {r["phrase"]: r for r in SR.team_rules(cfg)}
check("edited in Excel: the change, a new rule and a retired one reach the team's rules", rules["proposals are limited to"]["cat"] == "M"
      and rules["proposals are limited to"]["who"] == "Pat" and rules["will be evaluated on"]["cat"] == "M"
      and rules["the government may"].get("retired") and "xx" not in rules, rules)
used = [r["phrase"] for r in SR.all_rules(cfg, None)]
check("a Retired rule is kept on the list and not used", "the government may" not in used and "will be evaluated on" in used, used)
wb = openpyxl.load_workbook(book); sh = wb["Suggestion rules"]; hdr = [c.value for c in sh[1]]
sh.cell(2, hdr.index("Times kept") + 1).value = 99
wb.save(book); time.sleep(0.02)
r = T.tick(cfg, S)
check("the counts are the app's: typing over them changes no rule", ("Suggestion rules", "") not in (r.get("changed") or []), r.get("changed"))
print(f"SUGGESTRULES 4100 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
