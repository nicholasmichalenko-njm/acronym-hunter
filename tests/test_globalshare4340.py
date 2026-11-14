"""4.34.0 (ST18, ST19 of 2026-11-14): a save in the Global Standards reaches everyone at once, each file is kept once
in the folder, a version written the earlier way is still read, and each PC leaves its own receipt. Fictional PCs."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A", "Stationkeeper Data")
import formats as F, globalfile as GX, globalfolder as GF, globalstd as GS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(cfg, rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


A, B = (os.path.join(tmp, x, "Stationkeeper Data", "config") for x in "AB")
FOLDER = os.path.join(tmp, "Shared", "Global Standards"); os.makedirs(FOLDER)
os.makedirs(A); os.makedirs(B)
put(A, "rules.json", json.dumps({"rules": {"RU1": {"on": True}}}))
put(A, "doc_types.json", json.dumps({"types": [{"name": "RFP"}]}))

man = GF.share(A, FOLDER, by="Ada")
check("the first save is shared as version 1, with no button pressed", man and man["version"] == 1 and man["format"] == F.number("global standards version") == 2, man)
check("with nothing changed, nothing more is shared", GF.share(A, FOLDER) is None and GF.versions(FOLDER) == [1])
store = lambda: sorted(os.listdir(os.path.join(FOLDER, GF.STORE)))
n1 = len(store())
check("the version's folder holds only its list; the files are in the store, each under its fingerprint",
      os.listdir(os.path.join(FOLDER, "v0001")) == ["manifest.json"] and set(man["files"].values()) == set(store()), store())
put(A, "rules.json", json.dumps({"rules": {"RU1": {"on": False}}}))
man2 = GF.share(A, FOLDER, by="Ada")
check("a change is shared as the next version", man2 and man2["version"] == 2 and GS.state(A)["version"] == 2)
check("one changed file adds one file to the folder, not a copy of everything", len(store()) == n1 + 1, (n1, len(store())))
check("both versions read whole", GF.read(FOLDER, 1) and GF.read(FOLDER, 2)
      and json.load(open(GF._member_path(FOLDER, 1, "config/rules.json")))["rules"]["RU1"]["on"] is True)

got = GF.take(B, FOLDER)
check("another PC takes the latest", got["version"] == 2 and json.load(open(os.path.join(B, "rules.json")))["rules"]["RU1"]["on"] is False)
check("a PC that only reads shares nothing of its own", GF.share(B, FOLDER) is None)

# two people who can update: the second is told, nothing is overwritten (ST13)
put(B, "rules.json", json.dumps({"rules": {"RU1": {"on": "B's"}}}))
put(A, "doc_types.json", json.dumps({"types": [{"name": "RFP"}, {"name": "SOW"}]}))
GF.share(A, FOLDER, by="Ada")
check("a PC with its own change while the folder holds a newer version does not share over it",
      GF.share(B, FOLDER, by="Ben") is None and GF.versions(FOLDER) == [1, 2, 3] and GF.ready(B, FOLDER)["version"] == 3)

# a version written the earlier way (4.31.0 to 4.33.1) is still read
OLD = os.path.join(tmp, "Old", "Global Standards"); v = os.path.join(OLD, "v0001", "config"); os.makedirs(v)
shutil.copyfile(os.path.join(A, "rules.json"), os.path.join(v, "rules.json"))
json.dump({"format": 1, "version": 1, "by": "Ada", "when": "2026-11-14 04:00", "note": "",
           "files": {"config/rules.json": GS._sha_file(os.path.join(v, "rules.json"))}, "parts": {}}, open(os.path.join(OLD, "v0001", "manifest.json"), "w"))
check("a version of format 1 reads, with its files in its own folder", GF.read(OLD, 1) is not None and GF.current(OLD)["version"] == 1
      and GF._member_path(OLD, 1, "config/rules.json") == os.path.join(v, "rules.json"))
C = os.path.join(tmp, "C", "config"); os.makedirs(C)
check("and is taken", GF.take(C, OLD)["version"] == 1 and os.path.isfile(os.path.join(C, "rules.json")))
put(C, "rules.json", json.dumps({"rules": {"RU1": {"on": "next"}}}))
m = GF.share(C, OLD, by="Cy")
check("the next version beside it is written the new way, and both read", m["version"] == 2 and m["format"] == 2 and GF.read(OLD, 1) and GF.read(OLD, 2))
f = GX.write(FOLDER, 3)
D = os.path.join(tmp, "D", "config"); os.makedirs(D)
check("a file to share is made from the new layout and installs", os.path.isfile(f) and GX.install(D, f)["version"] == 3
      and len(json.load(open(os.path.join(D, "doc_types.json")))["types"]) == 2)

# receipts (ST19)
p = GF.receipt(A, FOLDER, name="Ada", pc="PC-0417")
check("a PC writes its own receipt: one file for one person on one PC", os.path.basename(p) == "Ada (PC-0417).json"
      and os.path.dirname(p) == os.path.join(FOLDER, "Receipts") and json.load(open(p))["version"] == 3, p)
GF.receipt(B, FOLDER, name="Ben", pc="PC-0522")
rows = GF.receipts(FOLDER, people=["Ada", "Ben", "Cy"])
check("the list says who is on which version, newest first, and who has not been seen",
      [(r["name"], r["version"]) for r in rows] == [("Ada", 3), ("Ben", 2), ("Cy", None)], rows)
os.remove(p)
check("a deleted receipt: that person shows as not seen", [(r["name"], r["version"]) for r in GF.receipts(FOLDER, people=["Ada"])] == [("Ben", 2), ("Ada", None)])
check("... until their app opens again and rewrites it", os.path.isfile(GF.receipt(A, FOLDER, name="Ada", pc="PC-0417")) and GF.receipts(FOLDER)[0]["name"] == "Ada")
shutil.rmtree(os.path.join(FOLDER, "Receipts"))
check("the whole Receipts folder deleted: each app makes it and its own file again", os.path.isfile(GF.receipt(B, FOLDER, name="Ben", pc="PC-0522")))
GF.take(B, FOLDER)
GF.receipt(B, FOLDER, name="Ben", pc="PC-0522")
check("taking a version rewrites the receipt with the new number", GF.receipts(FOLDER)[0]["version"] == 3 and len(os.listdir(os.path.join(FOLDER, "Receipts"))) == 1)
check("a name that is not a file name is made safe", os.path.basename(GF.receipt(A, FOLDER, name="A/da:*?", pc="P\\C")) == "Ada (PC).json")
check("with no name given the sign-in name is used", os.path.basename(GF.receipt(A, FOLDER)).endswith(".json") and len(GF.receipts(FOLDER)) == 3)
row = [r for r in GF.receipts(FOLDER) if r["name"] == "Ben"][0]
check("a line is removed by its file, and only inside Receipts", GF.forget_receipt(FOLDER, row["file"]) and not GF.forget_receipt(FOLDER, "../current.json")
      and "Ben" not in [r["name"] for r in GF.receipts(FOLDER)])
check("a folder that cannot be written gives no receipt and no error", GF.receipt(A, os.path.join(A, "rules.json", "x"), name="Ada") == "")

n = sum(checks)
print(f"GLOBAL SHARE 4340 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
