"""2.90.0 a tidy program folder: the read-me files move into the program (_internal\\docs) and an update pack from an
earlier copy carries them there, taking the old ones off the top of the folder and leaving config and the database
alone; the app fills About Stationkeeper from them; the old program-folder data copies move into the data folder (never
deleted, never when the data lives in the program folder); the data folder's READ ME says what each item is; a new
effort's folders and where saves start."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import edsign
import updatepack as U
import datahome as DH
import effortfolders as EF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


KEY = bytes(range(32))
U.PUBLIC_KEYS = [edsign.public_key(KEY).hex()]
tmp = tempfile.mkdtemp()


def build(folder, version, files):
    shutil.rmtree(folder, ignore_errors=True)
    for rel, text in files.items():
        p = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
    return U.write_manifest(folder, "Stationkeeper", version)


OLD = {"Stationkeeper.exe": "exe 2.89", "_internal/base_library.zip": "lib", "README.txt": "readme 2.89", "OVERVIEW.md": "o",
       "SECURITY.md": "s", "CHECKSUM.txt": "c 2.89"}
NEW = {"Stationkeeper.exe": "exe 2.90", "_internal/base_library.zip": "lib", "_internal/docs/README.txt": "readme 2.90",
       "_internal/docs/OVERVIEW.md": "o", "_internal/docs/SECURITY.md": "s", "_internal/docs/CHECKSUM.txt": "c 2.90"}
M89 = build(os.path.join(tmp, "b89"), "2.89.0", OLD)
M90 = build(os.path.join(tmp, "b90"), "2.90.0", NEW)
check("the read-me files inside the program are program files", all(U.is_program_path(r, "Stationkeeper") for r in NEW))
pack = os.path.join(tmp, "up.skupdate")
U.make_pack(os.path.join(tmp, "b90"), pack, KEY, [M89])
APP = os.path.join(tmp, "Stationkeeper")
shutil.copytree(os.path.join(tmp, "b89"), APP)
os.makedirs(os.path.join(APP, "config")); open(os.path.join(APP, "config", "app_settings.json"), "w").write('{"mine": true}')
open(os.path.join(APP, "acronym_database.csv"), "w").write("Term\nMINE\n")
plan = U.check(pack, APP, "Stationkeeper")
U.stage(plan, pack, APP)
U.apply(plan, APP)
top = sorted(os.listdir(APP))
check("the update takes the read-me files off the top of the program folder", not any(n in top for n in U.DOCS), top)
check("and puts them in the program", open(os.path.join(APP, "_internal", "docs", "README.txt")).read() == "readme 2.90")
check("config and the database are never touched", open(os.path.join(APP, "acronym_database.csv")).read() == "Term\nMINE\n"
      and open(os.path.join(APP, "config", "app_settings.json")).read() == '{"mine": true}')
docs = os.path.join(APP, "_internal", "docs")
got = DH.ensure_about(APP, docs)
about = os.path.join(APP, DH.ABOUT)
check("the app fills About Stationkeeper from them", sorted(got) == sorted(os.listdir(docs)) and open(os.path.join(about, "README.txt")).read() == "readme 2.90")
check("and copies nothing that is already the same", DH.ensure_about(APP, docs) == [])
open(os.path.join(docs, "README.txt"), "w").write("readme 2.91")
check("a newer read-me replaces the old copy", DH.ensure_about(APP, docs) == ["README.txt"] and open(os.path.join(about, "README.txt")).read() == "readme 2.91")
check("no read-me files in the program (running from source): nothing happens", DH.ensure_about(APP, os.path.join(tmp, "none")) == [])
# the data folder beside it
DATA = os.path.join(tmp, DH.NAME)
DH.ensure(DATA, APP)
check("the data folder has its own copies (from 2.80.0)", os.path.isfile(os.path.join(DATA, "acronym_database.csv")) and os.path.isdir(os.path.join(DATA, "config")))
readme = open(os.path.join(DATA, "READ ME.txt"), encoding="utf-8").read()
check("the data folder's READ ME says what each item is", all(w in readme for w in ("Efforts\\", "acronym_database.csv", "config\\", "training_data")))
moved = DH.tidy_program_folder(APP, DATA)
left = os.path.join(DATA, DH.LEFTOVERS)
check("the old program-folder copies move into the data folder", sorted(moved) == ["acronym_database.csv", "config"]
      and not os.path.exists(os.path.join(APP, "config")) and open(os.path.join(left, "acronym_database.csv")).read() == "Term\nMINE\n"
      and os.path.isfile(os.path.join(left, "READ ME.txt")))
check("the program folder now holds the program, its read-me folder and nothing else", sorted(os.listdir(APP)) ==
      sorted(["Stationkeeper.exe", "_internal", DH.ABOUT, U.UPDATE_DIR]), sorted(os.listdir(APP)))
check("the data folder's own copies stay where they are", open(os.path.join(DATA, "config", "app_settings.json")).read() == '{"mine": true}')
SAME = os.path.join(tmp, "progfolder"); os.makedirs(os.path.join(SAME, "config"))
open(os.path.join(SAME, "acronym_database.csv"), "w").write("Term\n")
check("data in the program folder (Program Files): nothing moves", DH.tidy_program_folder(SAME, SAME) == []
      and os.path.isfile(os.path.join(SAME, "acronym_database.csv")))
# an effort's folders
L = os.path.join(DATA, "Efforts", "Kestrel", "Kestrel_Effort_List.xlsx")
made = EF.create_all(L)
check("a new effort gets Customer Documents, Volumes, Response Setup and Exports", sorted(os.path.basename(p) for p in made)
      == sorted(EF.SUBS.values()) and all(os.path.isdir(p) for p in made))
check("saves start in the effort's Exports folder", EF.out(L, "Kestrel_Calendar.xlsx") == os.path.join(DATA, "Efforts", "Kestrel", "Exports", "Kestrel_Calendar.xlsx"))
check("Response Setup starts in its own folder", EF.out(L, kind="setup") == os.path.join(DATA, "Efforts", "Kestrel", "Response Setup"))
check("no effort: no folder", EF.out("", "x.xlsx") == "x.xlsx" and EF.folder("", "exports") == "")
ad = os.path.join(DATA, "Efforts", "Kestrel", "Kestrel_Effort_List - app data"); os.makedirs(ad)
note = EF.note_app_data(ad)
check("the effort's app data folder says not to edit it", "Do not edit" in open(note, encoding="utf-8").read())
n = sum(checks)
print(f"TIDY FOLDERS PASS ({n}/{len(checks)})" if n == len(checks) else f"TIDY FOLDERS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
