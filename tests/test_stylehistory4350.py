"""4.35.0 (ST15, ST16, ST24 of 2026-11-14): one style, one history. A saved change is a new Latest that every set
using the style gets; restoring an earlier version makes a new version on top and loses nothing; the wide restore does
the same for every style and is undone the same way. Fictional styles."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import stylehistory as SH, stylelib as SL, styleown as SO, templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


lib = TL.Library(os.path.join(tmp, "cfg"))
h2, _ = lib.add("style", "Osprey Heading 2", {"type": "paragraph", "size": 13.0, "bold": True})
body, _ = lib.add("style", "Osprey Body", {"type": "paragraph", "size": 11.0})
tech = SL.new_set(lib, "Technical volume"); cost = SL.new_set(lib, "Cost volume")
SL.add_to_set(lib, tech["id"], [h2["id"], body["id"]]); SL.add_to_set(lib, cost["id"], [h2["id"]])
at = {}


def stamp(it, when):                                             # the minute a version was saved (the clock is the PC's)
    it["at"] = when; lib.save(); at[it["version"]] = when
    return it


stamp(h2, "2026-11-10T09:00"); stamp(body, "2026-11-10T09:00")
uses = lambda sid, fam: [lib.get(i)["version"] for i in lib.kit(sid)["items"] if lib.get(i)["family"] == fam]

v2, st, moved = SO.save(lib, h2["id"], {"size": 14.0}, sid=tech["id"])
stamp(v2, "2026-11-11T10:00")
check("a change saved from inside one set is a new Latest", st == "version" and v2["version"] == 2 and lib.latest(h2["id"])["id"] == v2["id"])
check("... and every set that uses the style gets it (ST24)", sorted(moved) == ["Cost volume", "Technical volume"]
      and uses(tech["id"], h2["family"]) == [2] and uses(cost["id"], h2["family"]) == [2], moved)
check("no set is left behind", SH.behind(lib) == [])
v3, st, _m = SO.save(lib, v2["id"], {"size": 15.0, "italic": True}); stamp(v3, "2026-11-12T11:00")
same, st2, _m = SO.save(lib, v3["id"], {"size": 15.0, "italic": True})
check("saving with nothing changed makes no version", st2 == "same" and same["id"] == v3["id"] and len(lib.family(h2["id"])) == 3)

rows = SH.history(lib, h2["id"])
check("the history is newest first, Latest marked once", [r["version"] for r in rows] == [3, 2, 1] and [r["latest"] for r in rows] == [True, False, False])
check("each version says what changed from the one before, in words", rows[0]["changes"] == [("Size", "14 pt", "15 pt"), ("Italic", "off", "on")]
      and rows[1]["changes"] == [("Size", "13 pt", "14 pt")] and rows[2]["note"] == "The first version", rows)
check("... with when, and which sets use it", rows[1]["at"] == "2026-11-11 10:00" and sorted(rows[0]["sets"]) == ["Cost volume", "Technical volume"] and rows[1]["sets"] == [])

new, sets = SH.restore(lib, h2["id"])
check("restoring version 1 makes version 4 on top with version 1's values", new["version"] == 4 and lib.values(new)["size"] == 13.0 and not lib.values(new).get("italic")
      and new["note"] == "Restored from version 1" and lib.latest(h2["id"])["id"] == new["id"])
check("nothing is overwritten or lost: versions 1, 2 and 3 are as they were", [lib.values(x)["size"] for x in reversed(lib.family(h2["id"]))] == [13.0, 14.0, 15.0, 13.0])
check("every set uses the restored Latest", sorted(sets) == ["Cost volume", "Technical volume"] and uses(tech["id"], h2["family"]) == [4])
check("restoring the Latest does nothing", SH.restore(lib, new["id"]) == (None, []))
back, _s = SH.restore(lib, v3["id"])
check("a restore is undone by restoring the one before it: version 5 with version 3's values", back["version"] == 5 and lib.values(back)["size"] == 15.0
      and SH.history(lib, h2["id"])[0]["note"] == "Restored from version 3")
again, st3, _m = SO.save(lib, back["id"], {"size": 14.0, "italic": False})
check("typing an earlier version's values by hand is still a new Latest, never a step back", st3 == "version" and again["version"] == 6
      and lib.latest(h2["id"])["id"] == again["id"] and uses(cost["id"], h2["family"]) == [6], (st3, again.get("version")))

# the wide restore
b2, _st, _m = SO.save(lib, body["id"], {"size": 12.0}); stamp(b2, "2026-11-13T12:00")
late, _ = lib.add("style", "Osprey Callout", {"type": "paragraph", "size": 9.0}); stamp(late, "2026-11-13T15:00")
for x in lib.family(h2["id"])[:3]:
    stamp(x, "2026-11-13T13:00")
check("the times styles changed are listed newest first", SH.moments(lib)[0] == "2026-11-13 15:00" and "2026-11-10 09:00" in SH.moments(lib))
pairs = SH.as_of(lib, "2026-11-12 23:59")
check("as of a time: each style that changed since, with the version of that time", [(lib.base_of(a), a["version"], b["version"]) for a, b in pairs]
      == [("Osprey Body", 2, 1), ("Osprey Heading 2", 6, 3)], [(lib.base_of(a), a["version"], b["version"]) for a, b in pairs])
n_before = len(lib.items)
token = SH.restore_as_of(lib, "2026-11-12 23:59")
check("the wide restore makes one new Latest for each of them", len(token) == 2 and len(lib.items) == n_before + 2
      and lib.values(lib.latest(body["id"]))["size"] == 11.0 and lib.values(lib.latest(h2["id"]))["size"] == 15.0)
check("a style made after that time stays as it is", lib.latest(late["id"])["id"] == late["id"])
check("doing it again changes nothing", SH.as_of(lib, "2026-11-12 23:59") == [] or all(a.get("hash") == b.get("hash") for a, b in SH.as_of(lib, "2026-11-12 23:59")))
check("undo: what was Latest before the restore is Latest again, as new versions", SH.undo(lib, token) == 2
      and lib.values(lib.latest(body["id"]))["size"] == 12.0 and lib.values(lib.latest(h2["id"]))["size"] == 14.0 and len(lib.items) == n_before + 4)

# a set from before 4.35.0 still on an earlier version
old = SL.new_set(lib, "Old set"); lib.kit(old["id"])["items"].append(h2["id"]); lib.save()
bh = SH.behind(lib)
check("a set still on an earlier version is named with what it holds and the Latest", [(k["name"], a["version"], b["version"]) for k, a, b in bh] == [("Old set", 1, lib.latest(h2["id"])["version"])], bh)
check("Use the latest moves it", SH.use_latest(lib, old["id"]) == 1 and SH.behind(lib) == [])
lib2 = TL.Library(os.path.join(tmp, "cfg"))
check("the history is kept on disk", [r["version"] for r in SH.history(lib2, h2["id"])][:1] == [lib.latest(h2["id"])["version"]] and len(SH.history(lib2, h2["id"])) == len(lib.family(h2["id"])))

n = sum(checks)
print(f"STYLE HISTORY 4350 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
