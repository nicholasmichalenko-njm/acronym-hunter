"""4.48.0, UX decision 67: the values the code carried (rules, effort folders, stages, phrases, topics, effort types,
the numbering scheme) are written once into the Production Datum when its keeper's save becomes a version, so the
first Datum holds them before any leaves the code. Nothing reads the file yet. Two fictional PCs and one folder."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A", "Stationkeeper Data")
import datumvalues as DV, formats as F, globalfolder as GF, globalstd as GS
import banned, effortrec, folderplan, process, prodrules, rulebook, topics

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(cfg, rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


A = os.path.join(tmp, "A", "Stationkeeper Data", "config"); os.makedirs(A)
B = os.path.join(tmp, "B", "Stationkeeper Data", "config"); os.makedirs(B)
Fd = os.path.join(tmp, "Shared", "Production Datum"); os.makedirs(Fd)

c = DV.collect()
check("every value the code carries is collected by name", set(c) >= {"effort_folders", "stages", "roles", "record_stages", "gate_goals",
      "rules", "banned_phrases", "topics", "effort_types", "effort_type_response", "marking", "pagination"}, sorted(c))
check("... exactly as the code has it: folders, stages, rules, phrases, topics, effort types",
      c["effort_folders"] == DV._plain(folderplan.DEFAULT_TREE) and c["stages"] == DV._plain(process.DEFAULT_STAGES)
      and c["record_stages"] == list(effortrec.DEFAULT_STAGES) and c["rules"] == DV._plain(rulebook.BUILTIN)
      and c["banned_phrases"] == DV._plain(banned.STARTER) and c["topics"] == list(topics.STARTER)
      and c["effort_types"] == DV._plain(prodrules.STARTER_EFFORT_TYPES))
check("... and it is plain data that reads back the same", json.loads(json.dumps(c)) == c)
check("no file yet: nothing is read, nothing is in the set", DV.read(A) == {} and "values" not in GS.parts(A))

put(A, "production_standards.json", json.dumps({"fonts": {"body": {"size": 11}}}))
man = GF.update(A, Fd, by="Ada", note="The first")
check("the keeper's save that becomes a version writes the file, once", os.path.isfile(os.path.join(A, DV.FILE)) and DV.read(A) == c)
check("... with its format number, as formats.py lists it", json.load(open(os.path.join(A, DV.FILE), encoding="utf-8"))["format"] == DV.FORMAT == F.number("datum values"))
check("... and the version carries it as a part of its own", "config/" + DV.FILE in man["files"] and man["parts"].get("values", {}).get("files") == ["config/" + DV.FILE]
      and GS.names()["values"] == "Values once built in", man["parts"])
check("... and the PC is on that version with nothing waiting", GS.state(A)["version"] == 1 and GS.changed(A) == [], GS.changed(A))

GF.take(B, Fd)
check("another PC that installs the Datum holds the values", DV.read(B) == c)

mine = json.load(open(os.path.join(A, DV.FILE), encoding="utf-8")); mine["values"]["topics"] = ["Kestrel topic"]
json.dump(mine, open(os.path.join(A, DV.FILE), "w", encoding="utf-8"))
check("a file that is there is never written over by the code", DV.keep(A) is False and DV.read(A)["topics"] == ["Kestrel topic"])
put(A, "banned_words.csv", "word\nsynergy\n")
GF.update(A, Fd, by="Ada", note="A change")
check("... not by a later version either", DV.read(A)["topics"] == ["Kestrel topic"])

fresh = os.path.join(tmp, "C", "config")
check("asked directly, a PC with no file gets one, and a second ask writes nothing", DV.keep(fresh) is True and DV.read(fresh) == c and DV.keep(fresh) is False)
check("the code still holds every value: this release moves nothing out", len(rulebook.BUILTIN) >= 8 and len(folderplan.DEFAULT_TREE) >= 11 and banned.STARTER)
k = sum(checks)
print(f"DATUM VALUES 4480 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
