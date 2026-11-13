"""4.30.0, step 1 of the Standards board (2026-11-13): Global Standards is one set with a version number. The parts and
their files, a fingerprint per part, the version this PC is on, and what changed on the PC since. Fictional data."""
import datetime, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import formats as F, globalstd as GS, teamdata as TD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
base = set(GS.parts(cfg))                               # the master acronym list the program starts with, when there is one
B = len(base)
check("a new PC: nothing of its own yet, draft 1, not published", base <= {"acronyms"} and GS.state(cfg)["version"] == 0
      and GS.line(cfg) == f"Global Standards: draft 1, not published. {B} part{'' if B == 1 else 's'} on this PC.", GS.line(cfg))
put("rules.json", '{"format": 1, "rules": []}')
put("banned_words.csv", "word\nsynergy\n")
put("production_standards.json", '{"version": 3}')
put(os.path.join("production_parts", "cover.docx"), "cover")
put("templates_named.json", "{}")
ps = GS.parts(cfg)
check("the parts name what the PC holds, the team data file's and the ones it does not carry (rules, named templates)",
      set(ps) - base == {"rules", "banned", "standards", "named"} and ps["rules"][0] == "Rules"
      and set(ps["standards"][1]) == {"config/production_standards.json", "config/production_parts/cover.docx"}, {k: list(v[1]) for k, v in ps.items()})
check("every part of the team data file but the Preview tools choice is a part of Global Standards",
      set(TD.all_parts()) - set(GS.names()) == {"access"} and set(GS.MORE) <= set(GS.names()))
fp = GS.fingerprint(cfg)
check("one fingerprint per part; the same files give the same value", set(fp) == set(ps) and fp == GS.fingerprint(cfg)
      and all(len(v) == 64 for v in fp.values()))
s = GS.status(cfg)
check("nothing taken yet: the draft is 1 and every part counts as changed", s["version"] == 0 and s["draft"] == 1 and len(s["changed"]) == 4 + B
      and GS.line(cfg) == f"Global Standards: draft 1, not published. {4 + B} parts on this PC.", s)
st = GS.take(cfg, 1, GS.PUBLISHED, by="A. Publisher", note="First version", when=datetime.datetime(2026, 11, 13, 9, 0))
saved = json.load(open(os.path.join(cfg, GS.FILE), encoding="utf-8"))
check("take a version: kept with its number, where it came from, who, when, the note and each part's fingerprint",
      saved["version"] == 1 and saved["source"] == "published" and saved["by"] == "A. Publisher" and saved["taken"] == "2026-11-13 09:00"
      and saved["parts"] == fp and saved["format"] == F.number("global standards"), saved)
check("... the PC matches it: no draft, nothing changed", GS.status(cfg)["draft"] == 0 and GS.status(cfg)["changed"] == []
      and GS.line(cfg) == f"Global Standards version 1, published from this PC, taken 2026-11-13 09:00. {4 + B} parts on this PC, all as that version has them.", GS.line(cfg))
put("banned_words.csv", "word\nsynergy\nleverage\n")
put("piece_types.json", "{}")
os.remove(os.path.join(cfg, "templates_named.json"))
s = GS.status(cfg)
check("a part changed, one added, one gone: each is named, and the draft is the next number", s["draft"] == 2
      and s["changed"] == ["Banned and avoided phrases", "Named templates", "Piece types"], s)
check("... the line says so", GS.line(cfg) == "Global Standards version 1, published from this PC, taken 2026-11-13 09:00. "
      "Changed on this PC since (draft 2): Banned and avoided phrases, Named templates, Piece types.", GS.line(cfg))
put("rules.json", '{"format": 1, "rules": []}')
check("a file saved again with the same contents is not a change", "Rules" not in GS.status(cfg)["changed"])
with open(os.path.join(cfg, GS.FILE), "w", encoding="utf-8") as f:
    f.write("not json")
check("a state file that cannot be read: draft 1 again, nothing lost", GS.state(cfg)["version"] == 0 and GS.status(cfg)["draft"] == 1)
check("a work folder inside a part (a name starting with _) is not part of it", not any("/_" in m for _n, ms in GS.parts(cfg).values() for m in ms))
n = sum(checks)
print(f"GLOBAL STANDARDS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
