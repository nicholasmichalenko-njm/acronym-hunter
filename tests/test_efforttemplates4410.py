"""4.41.0 (ST27 of 2026-11-14, step 5): an effort type names its templates. One template for each of its profiles, kept
on the effort type and never read as formatting; what an effort of the type starts with; the template for a volume by
its name; the volumes with no pick are offered and picked. Fictional names."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import efforttemplates as ET, effortprofiles as EP, namedtemplates as NT, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
data = PRL.load(cfg)
eid = "rfp_limited"
pid = PRL.effort_type_of(data, eid)["profiles"][0]
check("an effort type names no templates until it is given one", ET.of(data, eid) == {} and [r["template"] for r in ET.brings(cfg, eid)] == [""]
      and ET.words(ET.brings(cfg, eid)).startswith("This effort type names no templates yet."), ET.brings(cfg, eid))
check("no effort type: nothing", ET.brings(cfg, "") == [] and ET.words([]) == "" and ET.for_volume(cfg, "", "Volume I") is None)
t = NT.new(cfg, "Page-limited RFP, Technical")
check("a template is named for a profile", ET.put(cfg, eid, pid, t["id"]) and ET.of(PRL.load(cfg), eid) == {pid: t["id"]})
check("an unknown effort type, profile or template is refused", not ET.put(cfg, "nope", pid, t["id"]) and not ET.put(cfg, eid, "nope", t["id"])
      and not ET.put(cfg, eid, pid, "nope"))
data = PRL.load(cfg)
check("the names are not formatting: the effort type's layer does not hold them", "templates" not in PRL.effort_layer_of(PRL.effort_type_of(data, eid))
      and "templates" not in PRL.resolved_type(data, pid, eid))
rows = ET.brings(cfg, eid)
check("what an effort of this type starts with", rows[0]["template"] == "Page-limited RFP, Technical" and rows[0]["profile"] == PRL.type_of(data, pid)["name"]
      and rows[0]["made"] is False and rows[0]["holds"].startswith("Nothing picked yet"), rows)
check("... in one sentence, saying it is not made yet", ET.words(rows) == f"It starts with: {rows[0]['profile']}: Page-limited RFP, Technical (not made yet).", ET.words(rows))
check("another effort type is untouched", ET.of(data, "rfp") == {})
vol = EP.volumes(data, eid, pid)[0]
check("the template for a volume, by its name", ET.for_volume(cfg, eid, vol)["id"] == t["id"] and ET.for_volume(cfg, eid, "Some other volume")["id"] == t["id"]
      and ET.for_volume(cfg, "rfp", vol) is None)
check("a template that is not made is not offered", ET.offer(cfg, eid, [vol], {}) == [])
d = NT.load(cfg); made = os.path.join(tmp, "t.dotx"); open(made, "wb").write(b"x")
d[t["id"]]["made"] = {"path": made, "version": 1, "at": "2026-11-15T01:00:00", "fp": "x"}; NT.save(cfg, d)
off = ET.offer(cfg, eid, [vol, "Volume II"], {"Volume II": {"id": "other"}})
check("made: offered for the volumes with no pick, and only those", [(v, x["id"]) for v, x in off] == [(vol, t["id"])], off)
check("the sentence no longer says not made", ET.words(ET.brings(cfg, eid)).endswith("Page-limited RFP, Technical."))
check("taken off again", ET.put(cfg, eid, pid, "") and ET.of(PRL.load(cfg), eid) == {} and ET.for_volume(cfg, eid, vol) is None)
ET.put(cfg, eid, pid, t["id"]); NT.remove(cfg, t["id"])
check("a named template that was removed reads as none", ET.brings(cfg, eid)[0]["template"] == "" and ET.for_volume(cfg, eid, vol) is None)
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
