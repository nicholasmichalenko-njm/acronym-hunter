"""4.7.1: the team's lists as files (listsbook; claude/stationkeeper-team-library-files-decisions-2026-11-10.md, phase 2).
The small lists are sheets of Company Standards.xlsx (Phrases, Authors, Compliance words, Piece types, Document types),
written when the app changes them and read into each list's own file when people change them in Excel. The master
acronym list is Lists\\Acronyms.csv and each custom dictionary Lists\\Dictionaries\\<name>.dic, both ways. Fictional."""
import os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import openpyxl
import authorlist as AL, banned as B, customdict as CD, cwords as CW, doctypes as DT, shredtypes as ST, teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


cfg = A.CONFIG_DIR
S = {"team_library": ""}
B.save(B.starter())
lst = AL.AuthorList(os.path.join(cfg, AL.FILE)).load(); lst.people = [{"name": "Pat Writer", "efforts": AL.ALL, "added": "2026-11-01", "source": "typed"}]; lst.save()
check("saving a list marks the workbook to write", T.state(cfg).get("dirty") is True)
T.tick(cfg, S)
book = T.book_path(cfg, S)
wb = openpyxl.load_workbook(book)
check("the lists are sheets of the workbook", all(s in wb.sheetnames for s in ("Phrases", "Authors", "Compliance words", "Piece types",
                                                                                "Document types")), wb.sheetnames)
ph = wb["Phrases"]
check("Phrases: the phrase, its level, what to use instead, why", [c.value for c in ph[1]][:4] == ["Phrase", "Level", "Use instead", "Why"]
      and ph.max_row - 1 == len(B.load()))
ph.append(["leverage", "Avoid", "use", "Jargon"])
au = wb["Authors"]; au.append(["Sam Editor", "Kestrel", "", ""])
cw = wb["Compliance words"]; cw.append(["is required to"])
pt = wb["Piece types"]
for r in pt.iter_rows(min_row=2):
    if r[0].value == "instruction":
        r[1].value = "Proposal instruction"
dt = wb["Document types"]; dt.append(["Model contract", "MC", False, False, "model contract"])
wb.save(book); time.sleep(0.02)
r = T.tick(cfg, S)
check("a phrase added in Excel reaches the phrase list", any(x["Phrase"] == "leverage" and x["Level"] == "Avoid" for x in B.load()))
people = {p["name"]: p for p in AL.AuthorList(os.path.join(cfg, AL.FILE)).load().people}
check("an author added in Excel, for one effort", people.get("Sam Editor", {}).get("efforts") == ["Kestrel"] and "Pat Writer" in people, people)
check("a compliance word", "is required to" in CW.load(cfg)["words"])
check("a piece type renamed", ST.load(cfg)["instruction"]["name"] == "Proposal instruction")
check("a document type with its initial", any(t["name"] == "Model contract" and t["initial"] == "MC" for t in DT.load(cfg)["types"]))
check("... reading them marks nothing to write back", not T.state(cfg).get("dirty"))
# the large lists
data_dir = os.path.dirname(cfg)
with open(os.path.join(data_dir, "acronym_database.csv"), "w", encoding="utf-8") as f:
    f.write("Acronym,Definition\nIMS,Integrated Master Schedule\n")
st = CD.Store(cfg); st.dicts.append({"id": "d1", "name": "Program words", "words": ["Kestrel", "Osprey"], "created": "", "changed": "", "exports": []}); st.save()
T.tick(cfg, S)
lists = os.path.join(T.folder(cfg, S), "Lists")
check("the master acronym list is Lists\\Acronyms.csv", open(os.path.join(lists, "Acronyms.csv"), encoding="utf-8").read().startswith("Acronym,Definition"))
dic = os.path.join(lists, "Dictionaries", "Program words.dic")
check("each dictionary is a Word .dic file", os.path.isfile(dic) and CD.read_dic(dic) == ["Kestrel", "Osprey"], CD.read_dic(dic) if os.path.isfile(dic) else None)
time.sleep(0.02)
with open(os.path.join(lists, "Acronyms.csv"), "a", encoding="utf-8") as f:
    f.write("GCS,Ground Control Segment\n")
CD.write_dic(dic, ["Kestrel", "Osprey", "Heron"])
r = T.tick(cfg, S)
check("an acronym added to Acronyms.csv reaches the app's list", "GCS" in open(os.path.join(data_dir, "acronym_database.csv"), encoding="utf-8").read())
check("a word added to the .dic reaches the dictionary", "Heron" in CD.Store(cfg).by_name("Program words")["words"])
check("... and the status says so", any("lists" in x for x in r["said"]), r["said"])
print(f"LISTS 471 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
