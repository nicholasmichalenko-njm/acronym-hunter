"""4.40.0 (ST28 of 2026-11-14): a Quick Part's versions work as a style's do. A change joins the line of the one it
was changed from and every part set on that line gets it; the history lists the versions with their sets; a restore puts
an earlier one on top as a new version; another version of the name is for the sets named, with its own history; the
Parts page lists the Latest of each line; a set left on an earlier version is told and moved. Fictional files."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import parthistory as PH, partlib as PT, stylelib as SL, templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
lib = TL.Library(cfg)


def vals(n):
    return {"entry": "Callout Box", "category": "Boxes", "gallery": "docParts", "source_sha": f"sha{n}", "description": ""}


v1, _ = lib.add("quickpart", "Callout Box", vals(1), source="a.dotx")
rfp = SL.new_set(lib, "RFP parts", kind="part")
pd = SL.new_set(lib, "Program parts", kind="part")
pl = SL.new_set(lib, "Page-limited parts", kind="part")
PT.add_to_set(cfg, lib, rfp["id"], ["q:" + v1["id"]]); PT.add_to_set(cfg, lib, pd["id"], ["q:" + v1["id"]])
v2, st = lib.add("quickpart", "Callout Box", vals(2), source="a.dotx")
moved = PH.changed(lib, v1, v2, st)
check("a change reaches every set that used the Quick Part", sorted(moved) == ["Program parts", "RFP parts"] and rfp["items"] == ["q:" + v2["id"]]
      and pd["items"] == ["q:" + v2["id"]] and pl["items"] == [], (moved, rfp["items"]))
check("the same values met again change nothing", PH.changed(lib, v1, v2, "same") == [] and PH.changed(lib, v2, v2, "variant") == [])
h = PH.history(lib, v2["id"])
check("the history: newest first, numbered, with the sets on each", [(r["version"], r["latest"], r["sets"]) for r in h]
      == [(2, True, ["RFP parts", "Program parts"]), (1, False, [])] and h[1]["note"] == "The first version", h)
new, sets = PH.restore(lib, v1["id"])
check("a restore puts the earlier version on top as a new one; nothing is removed", new is not None and PH.number(lib, new) == 3
      and (lib.values(new) or {}).get("source_sha") == "sha1" and lib.get(v1["id"]) and lib.get(v2["id"]) and new["note"] == "Restored from version 1", new)
check("... and the sets get it", sorted(sets) == ["Program parts", "RFP parts"] and rfp["items"] == ["q:" + new["id"]])
check("restoring the Latest does nothing", PH.restore(lib, new["id"]) == (None, []))
other, names = PH.create_version(lib, new["id"], [pl["id"], pd["id"]])
check("another version of the name, for the sets named", other is not None and names == ["Program parts", "Page-limited parts"]
      and PH.line_of(other) and lib.base_of(other) == "Callout Box" and other["note"] == "Another version, for Program parts, Page-limited parts", (names, other))
check("a set holds one Quick Part of a name: each named set gave up the one it had", pd["items"] == ["q:" + other["id"]] and pl["items"] == ["q:" + other["id"]]
      and rfp["items"] == ["q:" + new["id"]], (pd["items"], pl["items"]))
check("each has its own history", [r["version"] for r in PH.history(lib, other["id"])] == [1] and [r["version"] for r in PH.history(lib, new["id"])] == [3, 2, 1])
ln = PH.lines(lib, new["id"])
check("the lines of the name, each with its sets", [(t["id"], s) for t, s in ln] == [(new["id"], ["RFP parts"]), (other["id"], ["Program parts", "Page-limited parts"])], ln)
o2, st = lib.add("quickpart", "Callout Box", vals(9), source="a.dotx")
moved = PH.changed(lib, other, o2, st)
check("a change to one reaches the sets on that version and only those", sorted(moved) == ["Page-limited parts", "Program parts"]
      and PH.line_of(o2) == PH.line_of(other) and rfp["items"] == ["q:" + new["id"]] and pl["items"] == ["q:" + o2["id"]], (moved, rfp["items"]))
check("the Parts page lists the Latest of each line", [i["id"] for i in PH.tops(lib, v1["family"])] == [new["id"], o2["id"]]
      and PT.rows(cfg, "quick", lib)[0]["versions"] == ["q:" + new["id"], "q:" + o2["id"]], PT.rows(cfg, "quick", lib))
# a set left on an earlier version (made before 4.40.0)
old = SL.new_set(lib, "Legacy parts", kind="part"); old["items"].append("q:" + v1["id"]); lib.save()
b = PH.behind(lib)
check("a set on an earlier version is found, with the Latest of its line", [(k["name"], it["id"], t["id"]) for k, it, t in b] == [("Legacy parts", v1["id"], new["id"])], b)
check("Use the latest moves it", PH.use_latest(lib) == 1 and old["items"] == ["q:" + new["id"]] and PH.behind(lib) == [])
lib2 = TL.Library(cfg)
check("it is all kept", PH.line_of(lib2.get(o2["id"])) == PH.line_of(other) and [i["id"] for i in PH.tops(lib2, v1["family"])] == [new["id"], o2["id"]])
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
