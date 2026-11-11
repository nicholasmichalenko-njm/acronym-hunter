"""4.9.0: effort data for Stationkeeper Macros (claude/stationkeeper-effort-data-contract-v1.md). The first publish
writes the manifest last, rules.json with the same revision, the template and the dictionary (UTF-16 LE with a BOM);
byte counts and fingerprints are exact; rules.json follows the shipped schema; nothing changed publishes nothing; a
change bumps the revision and writes only the part that changed (the rest keep their part revision); a phrase or an
acronym reaches rules.json; a template input change rebuilds the template; a reader never meets a half-written part
(.tmp then rename); the revision never goes down; the effort keeps a stable id. Fictional values only."""
import hashlib, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import banned as B, customdict as CD, effort as E, effortdata as ED, prodrules as PRL, workspace as W
import _minischema as MS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


cfg = A.CONFIG_DIR
ED_DIR = os.path.join(tmp, "Kestrel"); os.makedirs(ED_DIR)
LIST = os.path.join(ED_DIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True
L.rows["IMS"] = {"Term": "IMS", "Definition": "Integrated Master Schedule", "Status": E.IN}; L.order.append("IMS")
L.rows["FAR"] = {"Term": "FAR", "Definition": "", "Status": E.NOT}; L.order.append("FAR")
L.save()
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
B.save(B.starter())
st = CD.Store(cfg); st.dicts.append({"id": "d1", "name": "Program words", "words": ["Kestrel"], "created": "", "changed": "", "exports": []}); st.save()
res = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0", info={"solicitation": "EX-26-R-0001"})
base = ED.folder(LIST)
man = json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8"))
rules = json.load(open(os.path.join(base, "rules", "rules.json"), encoding="utf-8"))
check("the first publish writes the snapshot in <effort folder>\\Stationkeeper Data", res and res["revision"] == 1
      and os.path.basename(base) == "Stationkeeper Data" and os.path.dirname(base) == ED_DIR)
check("the manifest: contract, effort with its stable id, revision, writer, fixed warning times", man["contract"] == ED.CONTRACT
      and man["effort"]["id"] == ws.get("effort_id") and len(man["effort"]["id"]) == 32 and man["effort"]["solicitation"] == "EX-26-R-0001"
      and man["revision"] == 1 and man["writer"]["app_version"] == "4.9.0" and man["freshness"] == {"warn_after_hours": 24, "stale_after_hours": 72})
check("rules.json carries the manifest's revision", rules["manifest_revision"] == man["revision"] == 1)
keys = {p["key"]: p for p in man["parts"]}
check("parts: rules, template and dictionary", set(keys) == {"rules", "template", "dictionary"}, list(keys))
exact = all(os.path.getsize(os.path.join(base, *p["path"].split("/"))) == p["bytes"]
            and hashlib.sha256(open(os.path.join(base, *p["path"].split("/")), "rb").read()).hexdigest() == p["sha256"] for p in man["parts"])
check("every part's byte count and fingerprint are exact", exact)
dic = open(os.path.join(base, "dictionaries", "effort.dic"), "rb").read()
check("the dictionary: UTF-16 LE with a BOM, the team's words and the effort's acronyms", dic.startswith(b"\xff\xfe")
      and set(CD.read_dic(os.path.join(base, "dictionaries", "effort.dic"))) == {"Kestrel", "IMS"})
import zipfile
with zipfile.ZipFile(os.path.join(base, "templates", "effort.dotx")) as zt:      # closed: Windows cannot replace an open file
    check("the template is a .dotx with no macros", "word/document.xml" in zt.namelist() and not any("vbaProject" in n for n in zt.namelist())
          and "template.main+xml" in zt.read("[Content_Types].xml").decode())
schema = json.load(open(ED.schema_path(), encoding="utf-8"))
check("rules.json follows the schema shipped with the app (and a copy sits beside it)", not MS.errors(rules, schema)
      and os.path.isfile(os.path.join(base, "rules", ED.SCHEMA_FILE)), MS.errors(rules, schema)[:3])
check("the acronyms in the list, the ones that are not terms as ignore; placeholders apart from banned phrases",
      rules["acronyms"] == [{"acronym": "IMS", "definition": "Integrated Master Schedule"}] and rules["ignore"] == [{"text": "FAR"}]
      and any(p["text"] == "TBD" for p in rules["placeholders"]) and not any(b["phrase"] == "TBD" for b in rules["banned_phrases"]))
check("JSON booleans and numbers, not words", isinstance(rules["settings"]["CaptionInFirstRow"], bool)
      and isinstance(rules["settings"]["TableWidthPercent"], int))
check("README says not to edit", "Do not edit" in open(os.path.join(base, "README.txt"), encoding="utf-8").read())
check("nothing changed: nothing is published", ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0") is None)
tpl_rev = keys["template"]["part_revision"]
B.save(B.load() + [{"Phrase": "game-changer", "Level": "Avoid", "Use instead": "say what changes", "Why": "Jargon"}])
r2 = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0")
man2 = json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8")); k2 = {p["key"]: p for p in man2["parts"]}
rules2 = json.load(open(os.path.join(base, "rules", "rules.json"), encoding="utf-8"))
check("a phrase added: the revision goes up, only rules.json is written, the template keeps its part revision",
      r2["revision"] == 2 and r2["written"] == ["rules"] and k2["template"]["part_revision"] == tpl_rev and k2["rules"]["part_revision"] == 2
      and any(b["phrase"] == "game-changer" and b["replacement"] == "say what changes" for b in rules2["banned_phrases"]) and rules2["manifest_revision"] == 2, r2)
d = PRL.load(cfg); d["company"]["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11}}; PRL.save(cfg, d)
r3 = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0")
check("a style changed: the template is rebuilt", r3 and "template" in r3["written"], r3)
leftover = [f for dp, _d, fs in os.walk(base) for f in fs if f.endswith((".tmp", ".building")) or f.startswith("~$")]
check("no half-written or temporary files are left", not leftover, leftover)
ws.set("effort_data", {"revision": 1, "parts": {}})          # the app's own count lost: the manifest on disk still wins
r4 = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0", force=True)
check("the revision never goes down", r4["revision"] == 4, r4)
real = ED._replace
seen, order = [], []
def slow_replace(tmp_, target, tries=5):                      # a reader looks while each part is renamed into place
    seen.append(sorted(f for f in os.listdir(os.path.dirname(target)) if not f.endswith((".tmp", ".building"))))
    order.append(os.path.basename(target))
    return real(tmp_, target, tries)
ED._replace = slow_replace
B.save(B.load() + [{"Phrase": "paradigm shift", "Level": "Avoid", "Use instead": "", "Why": "Jargon"}])
ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0")
ED._replace = real
mt = json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8"))
check("the manifest is written last, after every part", order and order[-1] == "manifest.json" and "rules.json" in order, order)
check("a reader during a publish meets only whole files: each part is written under .tmp and renamed",
      all(not f.endswith(".tmp") for s in seen for f in s))
def held(tmp_, target, tries=5):                             # Word has effort.dotx open as a document's template
    if target.endswith("effort.dotx"):
        raise PermissionError(13, "in use", target)
    return real(tmp_, target, tries)
ED._replace = held
d = PRL.load(cfg); d["company"]["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 12}}; PRL.save(cfg, d)
B.save(B.load() + [{"Phrase": "best of breed", "Level": "Avoid", "Use instead": "", "Why": "Jargon"}])
r6 = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0")
ED._replace = real
r7 = json.load(open(os.path.join(base, "rules", "rules.json"), encoding="utf-8"))
m7 = json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8")); t7 = next(p_ for p_ in m7["parts"] if p_["key"] == "template")
check("the template held open by Word: the rules still go out, the template waits and the manifest keeps the old one",
      r6 and r6["pending"] == ["template"] and "rules" in r6["written"] and any(b["phrase"] == "best of breed" for b in r7["banned_phrases"])
      and t7["sha256"] == hashlib.sha256(open(os.path.join(base, "templates", "effort.dotx"), "rb").read()).hexdigest()
      and not os.path.exists(os.path.join(base, "templates", "effort.dotx.tmp")), r6)
r8 = ED.publish(cfg, ws, LIST, "Kestrel", "4.9.0")
check("... and the next try writes the template", r8 and "template" in r8["written"] and not r8["pending"], r8)
print(f"EFFORTDATA 490 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
