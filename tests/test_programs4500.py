"""4.50.0 Programs (programs.py) on their own, in a temp folder: a name that cannot be used says why; a program is made
with its list, its Program Documents folder and its registry entry, and no proposal folder tree; programs, efforts and
Unfiled are told apart; the efforts on Home leave programs out; an effort of the type Program deliverables is offered the
move until it is kept as an effort; making it a program and an effort again changes only the registry's marks and its
record, and moves no file; a program's summary counts its program documents. Fictional (Kestrel, Heron, Osprey)."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import effort as E, effortrec as RR, effortsummary as ES, programs as PG, unfiled as UF, workspace as W, docversions as DV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "Stationkeeper Data")
reg = E.Registry(os.path.join(data, "config", "efforts.json"))


def effort(name, etype=""):
    path = os.path.join(data, "Efforts", name, f"{name}_Effort_List.xlsx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    L = E.EffortList(path, name); L.pending = True; L.save()
    os.makedirs(W.data_dir_for(path), exist_ok=True)
    if etype:
        json.dump({"prod_std": {"effort_type": etype, "type": "proposal"}}, open(os.path.join(W.data_dir_for(path), "settings.json"), "w"))
    RR.Record(W.data_dir_for(path)).save()
    reg.put(name, path=path)
    return path


effort("Heron")
UF.ensure(reg, data)
check("an empty name says so", PG.check_name(reg, "  ") == "Give the program a name.")
check("Unfiled's name, any case, says so", "Unfiled" in PG.check_name(reg, "unfiled"))
check("a home's name, any case, says so", "already has that name" in PG.check_name(reg, "HERON"))
check("a name with nothing a folder can hold says so", "letter or digit" in PG.check_name(reg, '<>:?*'))
check("a good name passes", PG.check_name(reg, "Kestrel Fleet") == "")
try:
    PG.create(reg, data, "heron")
    bad = False
except ValueError as ex:
    bad = "already has that name" in str(ex)
check("create refuses a name that cannot be used, with the reason", bad)

name = PG.create(reg, data, "Kestrel Fleet")
info = reg.get(name)
root = os.path.join(data, "Programs", "Kestrel_Fleet")
check("create makes the list in Stationkeeper Data\\Programs", info["path"] == os.path.join(root, "Kestrel_Fleet_Program_List.xlsx")
      and os.path.isfile(info["path"]) and PG.programs_dir(data) == os.path.join(data, "Programs"), info)
check("and a Program Documents folder, registered as its documents folders", os.path.isdir(os.path.join(root, PG.DOCS))
      and info["customer_dir"] == info["volumes_dir"] == os.path.join(root, PG.DOCS) and info.get("program") is True)
check("and no proposal folder tree", sorted(os.listdir(root)) == ["Kestrel_Fleet_Program_List.xlsx", PG.DOCS], os.listdir(root))
check("the list reads back as an effort list", E.EffortList(info["path"], name).load() is not None)
check("names, effort_names and is_program tell them apart", PG.names(reg) == ["Kestrel Fleet"] and PG.effort_names(reg) == ["Heron"]
      and PG.is_program(reg, name) and not PG.is_program(reg, "Heron") and not PG.is_program(reg, UF.NAME))
check("the efforts on Home leave programs out", [r["name"] for r in ES.all_efforts(reg)] == ["Heron"])
check("a program with no documents yet", PG.summary(reg, name) == {"name": name, "documents": 0, "missing": False, "was_effort": False})
check("the words for the count", (PG.count_text(0), PG.count_text(1), PG.count_text(3))
      == ("No program documents yet", "1 program document", "3 program documents"))

# the offer
op = effort("Osprey", "program")
effort("Gannet", "rfp")
check("the effort type is read from the home's settings", PG.effort_type_of(reg, "Osprey") == "program"
      and PG.effort_type_of(reg, "Heron") == "" and PG.effort_type_of(reg, "Nobody") == "")
check("an effort of the type Program deliverables is offered the move", PG.candidates(reg) == ["Osprey"] == PG.all_candidates(reg))
PG.keep_as_effort(reg, "Osprey")
check("kept as an effort: no longer offered, still in the card's list", PG.candidates(reg) == [] and PG.all_candidates(reg) == ["Osprey"]
      and reg.get("Osprey")["program_offer"] == "kept")
odata = W.data_dir_for(op)
lib = DV.Library(os.path.join(odata, "documents")).load()
doc = os.path.join(os.path.dirname(op), "Plan.txt"); open(doc, "w").write("Kestrel plan")
lib.add(doc, [{"x": "Kestrel plan"}]); lib.save()


def listing():
    out = []
    for d, _s, fs in os.walk(os.path.dirname(op)):
        out += [os.path.relpath(os.path.join(d, f), os.path.dirname(op)) for f in fs]
    return sorted(out)


before = listing()
rec_before = len(RR.Record(odata).data["timeline"])
check("make_program refuses Unfiled and an unknown name", not PG.make_program(reg, UF.NAME) and not PG.make_program(reg, "Nobody"))
check("make_program", PG.make_program(reg, "Osprey"))
o = reg.get("Osprey")
check("only the registry's marks change", o.get("program") is True and o.get("was_effort") is True and o["path"] == op)
check("no file moved and the effort type is left as it is", listing() == before and PG.effort_type_of(reg, "Osprey") == "program", (before, listing()))
tl = RR.Record(odata).data["timeline"]
check("one line in its record says it became a program", len(tl) == rec_before + 1 and "program" in tl[-1]["text"], tl[-1:])
check("it is a program now, with its document", PG.names(reg) == ["Kestrel Fleet", "Osprey"] and "Osprey" not in PG.effort_names(reg)
      and "Osprey" not in PG.all_candidates(reg) and PG.summary(reg, "Osprey")["documents"] == 1 and PG.summary(reg, "Osprey")["was_effort"])
check("and not on Home's efforts", "Osprey" not in [r["name"] for r in ES.all_efforts(reg)])
check("make_effort", PG.make_effort(reg, "Osprey") and reg.get("Osprey").get("program") is False)
check("an effort again: listed, nothing moved, one more line", "Osprey" in PG.effort_names(reg) and listing() == before
      and len(RR.Record(odata).data["timeline"]) == rec_before + 2 and "Osprey" in [r["name"] for r in ES.all_efforts(reg)])
check("make_effort refuses Unfiled", not PG.make_effort(reg, UF.NAME))
print(f"PROGRAMS 4.50.0 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
