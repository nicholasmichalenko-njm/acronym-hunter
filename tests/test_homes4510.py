"""4.51.0 homes.py alone, in a temp folder: a name from a file's name; a free name that no effort, program or Unfiled has;
the answers to "Where does it go?" in order (the open home first, the efforts, the programs, a new effort, a new
program; no archived home and no Unfiled; no program for a use only an effort has); a new name checked; Unfiled holds
work only when it exists and holds something, and asking never makes it; the once-only start offer's memory.
Fictional (Kestrel, Heron, Osprey)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import effort as E, homes as HM, programs as PG, unfiled as UF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


data = os.path.join(tmp, "Stationkeeper Data")
reg = E.Registry(os.path.join(data, "config", "efforts.json"))


def effort(name, **kw):
    p = os.path.join(data, "Efforts", name, f"{name}_Effort_List.xlsx")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    reg.put(name, path=p, **kw)


# suggest_name
check("suggest_name: the stem, underscores and hyphens as spaces", HM.suggest_name([os.path.join("x", "Kestrel_RFP-Sections__C.docx")]) == "Kestrel RFP Sections C")
check("... runs of spaces collapsed and trimmed", HM.suggest_name(["/x/  Heron   bid  .pdf"]) == "Heron bid")
check("... at most 60 characters", len(HM.suggest_name(["/x/" + "Osprey " * 20 + ".docx"])) <= 60
      and HM.suggest_name(["/x/" + "Osprey " * 20 + ".docx"]).startswith("Osprey Osprey"))
check("... the first file only", HM.suggest_name(["/a/Heron.docx", "/a/Osprey.docx"]) == "Heron")
check("... nothing for no paths", HM.suggest_name([]) == "" and HM.suggest_name(None) == "")

# homes
effort("Kestrel"); effort("heron")
PG.create(reg, data, "Osprey")
effort("Old bid", archived=True)
effort("Albatross")
check("free_name: a name no one has stays", HM.free_name(reg, "Plover") == "Plover")
check("... a taken name, any case, gets 2", HM.free_name(reg, "kestrel") == "kestrel 2")
effort("Kestrel 2")
check("... then 3", HM.free_name(reg, "Kestrel") == "Kestrel 3")
check("... a program's name counts", HM.free_name(reg, "OSPREY") == "OSPREY 2")
check("... Unfiled's name counts even when there is no Unfiled", HM.free_name(reg, "unfiled") == "unfiled 2")

c = HM.choices(reg, "", [])
keys = [x["key"] for x in c]
check("choices with nothing open: efforts A to Z, programs, then the two new ones",
      keys == [("home", "Albatross"), ("home", "heron"), ("home", "Kestrel"), ("home", "Kestrel 2"), ("home", "Osprey"),
               ("new_effort", None), ("new_program", None)], keys)
check("... labels", [x["label"] for x in c][-3:] == ["Osprey (program)", "A new effort", "A new program"]
      and c[0]["label"] == "Albatross" and c[0]["kind"] == "effort" and c[4]["kind"] == "program")
c = HM.choices(reg, "Kestrel", ["/x/a.docx"])
check("the open effort is first, '(open now)', and not listed again", c[0] == {"key": ("home", "Kestrel"), "label": "Kestrel (open now)", "kind": "effort"}
      and [x["key"] for x in c].count(("home", "Kestrel")) == 1)
c = HM.choices(reg, "Osprey", [])
check("an open program is first too", c[0] == {"key": ("home", "Osprey"), "label": "Osprey (open now)", "kind": "program"}
      and [x["key"] for x in c].count(("home", "Osprey")) == 1)
check("no archived home is listed", all(x["key"][1] != "Old bid" for x in HM.choices(reg, "", [])))
c = HM.choices(reg, "Kestrel", [], programs=False)
check("programs=False: no program and no new program", [x["key"] for x in c] == [("home", "Kestrel"), ("home", "Albatross"), ("home", "heron"),
                                                                               ("home", "Kestrel 2"), ("new_effort", None)], [x["key"] for x in c])
check("... an open program is not offered then", ("home", "Osprey") not in [x["key"] for x in HM.choices(reg, "Osprey", [], programs=False)])

# check_new
check("check_new: a free name", HM.check_new(reg, "Plover") == "")
check("... no name: Give the effort a name.", HM.check_new(reg, "  ") == "Give the effort a name.")
check("... no name for a program says program", HM.check_new(reg, "", "program") == "Give the program a name.")
check("... a taken name, any case", "already has that name" in HM.check_new(reg, "KESTREL"))
check("... Unfiled's name", "Unfiled" in HM.check_new(reg, "unfiled"))
check("... a name with nothing a folder can hold", "letter or digit" in HM.check_new(reg, "???"))

# Unfiled
check("holds_work: no Unfiled, no work", not HM.holds_work(reg))
check("... and asking never makes Unfiled", reg.get(UF.NAME) is None and not os.path.isdir(os.path.join(data, "Efforts", UF.NAME)))
check("no offer due with no Unfiled; the state is empty; setting it makes nothing",
      not HM.start_offer_due(reg) and HM.offer_state(reg) == "" and HM.set_offer_state(reg, "later") is False and reg.get(UF.NAME) is None)
UF.ensure(reg, data)
check("an empty Unfiled holds no work and is offered nothing", not HM.holds_work(reg) and not HM.start_offer_due(reg))
check("Unfiled is never a choice", all(x["key"][1] != UF.NAME for x in HM.choices(reg, UF.NAME, [])))
L = E.EffortList(UF.list_path(data), UF.NAME).load()
L.add_or_update("KBS", Definition="Kestrel Bus System")
L.pending = True; L.save()
check("Unfiled with a term holds work; the offer is due", HM.holds_work(reg) and HM.start_offer_due(reg))
check("shown_name: Unfiled reads Unfiled, from before; others as they are", HM.shown_name(reg, UF.NAME) == "Unfiled, from before" == HM.SHOWN
      and HM.shown_name(reg, "Kestrel") == "Kestrel" and HM.shown_name(reg, "") == "")
check("Not now is kept on Unfiled's entry and the offer is not due again", HM.set_offer_state(reg, HM.LATER) and HM.offer_state(reg) == "later"
      and not HM.start_offer_due(reg) and (reg.get(UF.NAME) or {}).get("named_offer") == "later")
check("named is kept too", HM.set_offer_state(reg, HM.NAMED) and HM.offer_state(reg) == "named")
check("... read back from the file", HM.offer_state(E.Registry(reg.path)) == "named")
check("the registry name stays Unfiled", UF.NAME == "Unfiled" and UF.is_unfiled(reg, "Unfiled"))

n = sum(checks)
print(f"HOMES 4510 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
