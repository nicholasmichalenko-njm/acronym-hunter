"""3.22.0 Our data: one Stationkeeper Data file carries the team's foundational data (acronyms, dictionaries, phrases,
standards with their covers and Quick Parts sources, team lists, bins) and nothing about one effort (no Wall of Truth); it is labeled as team data and refuses a git
folder; import shows what each part adds, merges add-only (this PC's own entries win), keeps a copy of what it touches,
and Undo puts it back; a part from a newer version is reported and kept, never dropped; a damaged file is refused."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A")
import app_gui as A
import authorlist as AL, banned as BN, customdict as CD, excerpts as EX, prodrules as PRL, teamdata as TD, teampack as TP
import walloftruth as WT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfgA = os.path.join(tmp, "A", "config"); cfgB = os.path.join(tmp, "B", "config")
os.makedirs(cfgA, exist_ok=True); os.makedirs(cfgB, exist_ok=True)
dbA, dbB = os.path.join(tmp, "A", "acronym_database.csv"), os.path.join(tmp, "B", "acronym_database.csv")

# ---------------------------------------------------------------- PC A builds the team's data
A.DB_FILE = dbA
A.write_db_rows([["CDRL", "Acronym", "Contract Data Requirements List", "Include"], ["TBD", "Acronym", "To Be Determined", "Exclude"]])
open(os.path.join(cfgA, "ocr_corrections.csv"), "w").write("Misread,Correct,Note\nC0RL,CDRL,\n")     # as Windows installs seed it
st = CD.Store(cfgA); st.add("Space terms", ["apogee", "perigee"]); st.save()
open(os.path.join(cfgA, "banned_words.csv"), "w").write("Phrase,Level,Use instead,Why\nworld-class,bad,,Unsupported\n")
data = PRL.load(cfgA); data["types"].append({"id": "rfi", "name": "RFI response", "match": ["rfi"]})
data["company"]["fonts"]["body"]["min_size"] = 11
PRL.save(cfgA, data)
os.makedirs(os.path.join(cfgA, "production_parts"), exist_ok=True)
open(os.path.join(cfgA, "production_parts", "cover-abc123.docx"), "wb").write(b"PK cover bytes")
WT.team_save(cfgA, [{"label": "Mass budget", "value": "412 kg"}])
TP.save_topics(cfgA, ["Thermal", "Schedule"])
EX.save_team_bins(cfgA, [{"name": "Transition risk", "color": "#B45309"}])
al = AL.load(cfgA); al.add("Dana Ruiz")
have = TD.available(cfgA)
check("this PC lists what it can carry, and the Wall of Truth is not part of it", {"acronyms", "dictionaries", "banned", "standards", "topics", "bins", "authors"} <= set(have)
      and "wall" not in have, have)

repo = os.path.join(tmp, "repo"); os.makedirs(os.path.join(repo, ".git"))
try:
    TD.export(cfgA, os.path.join(repo, "x" + TD.EXT)); refused = False
except ValueError:
    refused = True
check("the data file is never written into a folder git tracks", refused and not os.path.exists(os.path.join(repo, "x" + TD.EXT)))
out = os.path.join(tmp, "share", TD.file_name())
man = TD.export(cfgA, out)
z = zipfile.ZipFile(out)
check("one file, labeled as the team's data inside and out", out.endswith(".skdata") and "team data" in os.path.basename(out)
      and TD.README in z.namelist() and "Never put it on GitHub" in z.read(TD.README).decode() and "Never put it on GitHub" in man["label"])
check("it carries the acronyms, dictionaries, phrases, standards with their pages, team lists and bins",
      {"data/acronym_database.csv", "config/custom_dictionaries.json", "config/banned_words.csv", "config/production_standards.json",
       "config/production_parts/cover-abc123.docx", "config/team_topics.json", "config/team_bins.json",
       "config/author_list.json"} <= set(man["files"]), sorted(man["files"]))
check("nothing about one effort goes in: no Wall of Truth", "config/wall_of_truth.json" not in man["files"])

# ---------------------------------------------------------------- PC B has some data of its own
A.DB_FILE = dbB
A.write_db_rows([["CDRL", "Acronym", "Contract Data Requirements List", "Include"], ["ICD", "Acronym", "Interface Control Document", "Include"],
                 ["TBD", "Acronym", "To Be Decided", "Include"]])
stB = CD.Store(cfgB); stB.add("Space terms", ["apogee", "delta-v"]); stB.save()
TP.save_topics(cfgB, ["Key personnel"])
m2, d2 = TD.read(out)
pv = {p["key"]: p for p in TD.preview(cfgB, m2, d2)}
check("import shows what each part does before anything is written", pv["dictionaries"]["state"] == "merge" and pv["topics"]["state"] == "merge"
      and pv["standards"]["state"] == "new" and not os.path.isfile(os.path.join(cfgB, "production_standards.json")), {k: v["state"] for k, v in pv.items()})
rep = dict(TD.install(cfgB, m2, d2))
rows = {r[0]: r for r in A.read_db_rows()}
check("acronyms merge add-only: new terms come in, this PC's own definitions stay", "ICD" in rows and rows["TBD"][2] == "To Be Decided", rows.keys())
w = CD.Store(cfgB).by_name("Space terms")
check("dictionaries merge: words added to the one this PC has", set(w["words"]) == {"apogee", "perigee", "delta-v"}, w)
dB = PRL.load(cfgB)
check("standards come in: profiles, the team standard, and their cover files", any(t["id"] == "rfi" for t in dB["types"])
      and dB["company"]["fonts"]["body"]["min_size"] == 11 and os.path.isfile(os.path.join(cfgB, "production_parts", "cover-abc123.docx")), rep.get("standards"))
check("team lists, bins, phrases and authors come in", set(TP.topics(cfgB)) == {"Key personnel", "Thermal", "Schedule"}
      and [b["name"] for b in EX.team_bins(cfgB)] == ["Transition risk"] and not WT.team_load(cfgB)
      and "world-class" in open(os.path.join(cfgB, "banned_words.csv")).read() and "Dana Ruiz" in AL.load(cfgB).names(), rep)
check("OCR fixes come into this PC's own list", "C0RL" in open(os.path.join(cfgB, "ocr_corrections.csv")).read())
check("importing again changes nothing", all(p["state"] == "same" for p in TD.preview(cfgB, m2, d2) if p["key"] not in ("acronyms", "dictionaries", "topics", "authors", "banned"))
      and dict(TD.install(cfgB, m2, d2)).get("standards", "").startswith("0 profile(s)"))
check("Undo puts back what the last import touched", TD.undo(cfgB) > 0)
TD.undo(cfgB)
check("... back to this PC's own data", not os.path.isfile(os.path.join(cfgB, "production_standards.json")) and TP.topics(cfgB) == ["Key personnel"]
      and "ICD" in {r[0] for r in A.read_db_rows()} and "CDRL" in {r[0] for r in A.read_db_rows()}
      and "perigee" not in CD.Store(cfgB).by_name("Space terms")["words"], TP.topics(cfgB))

# ---------------------------------------------------------------- newer and damaged files
z2 = os.path.join(tmp, "newer" + TD.EXT)
with zipfile.ZipFile(out) as zi, zipfile.ZipFile(z2, "w") as zo:
    mm = json.loads(zi.read(TD.MANIFEST)); mm["format"] = "sk-data-7"
    mm["parts"]["bids"] = {"name": "Bid library", "v": 1, "files": []}
    for n in zi.namelist():
        zo.writestr(n, json.dumps(mm) if n == TD.MANIFEST else zi.read(n))
m3, d3 = TD.read(z2)
p3 = {p["key"]: p for p in TD.preview(cfgB, m3, d3)}
check("a file from a newer version still imports what this version knows, and names the rest", p3["bids"]["state"] == "unknown"
      and p3["topics"]["known"] and "bids" not in dict(TD.install(cfgB, m3, d3, parts=["topics", "bids"])))
bad = os.path.join(tmp, "bad" + TD.EXT)
with zipfile.ZipFile(out) as zi, zipfile.ZipFile(bad, "w") as zo:
    for n in zi.namelist():
        zo.writestr(n, b"changed" if n == "config/team_topics.json" else zi.read(n))
try:
    TD.read(bad); ok = False
except ValueError:
    ok = True
check("a damaged or changed file is refused", ok)

print(f"TEAM DATA {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
