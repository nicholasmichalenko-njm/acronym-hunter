"""2.50.0 Training Studio logic: the stable test set, word accuracy, the OCR fixes test, the compliance tests from
gathered matrices, the scorecard (an area that got worse is left out; the trainer can leave one out), and the pack:
only the areas kept go in, the scorecard travels with it, the install card lines come from it."""
import os, sys, tempfile, json, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A
import studio as ST, compliance as C
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


# the test set
samples = [{"rel": f"img/{i}.png", "text": "TT&C link", "read": "TT8C link", "rejected": i == 3} for i in range(200)]
train, test = ST.split(samples)
check("about one line in ten is set aside, the same every time", 8 <= len(test) <= 35 and ST.split(samples)[1] == test
      and not any(s["rejected"] for s in train + test) and len(train) + len(test) == 199, len(test))
# word accuracy and fixes
check("word accuracy", ST.word_accuracy([("TT8C link", "TT&C link")]) == 50.0 and ST.word_accuracy([("a b", "a b")]) == 100.0)
check("fixes applied word by word", ST.apply_fixes("the TT8C link", {"tt8c": "TT&C"}) == "the TT&C link")
fx = ST.test_fixes(samples, {"tt8c": "TT&C"})
check("the fixes test: with the fixes reads better", fx["now"] == 50.0 and fx["after"] == 100.0 and fx["n"] == 199, fx)
bad = ST.test_fixes(samples, {"link": "lnk"})
check("a fix that breaks words reads worse", bad["after"] < bad["now"], bad)
# compliance from two matrices
def matrix(name, n):
    text = "L.4 Technical Volume\n" + " ".join(
        [f"The Offeror shall describe item {i} of the thermal design." for i in range(n)] +
        [f"Background paragraph {i} explains the history of the program office." for i in range(n)])
    M = C.Matrix(os.path.join(tmp, name), "K")
    M.items = C.extract([("Section L.docx", [("Page 1", text)])])
    M.outline = C.parse_outline("Volume I\n1.1 Thermal\n1.2 History")
    for it in M.items:
        if "shall" in it["text"]:
            it["decision"], it["map"] = "Keep", "1.1 Thermal"
        elif "Background" in it["text"]:
            it["decision"] = "Drop"
    M.save()
    return M.path
paths = [matrix("Kestrel_Matrix.xlsx", 34), matrix("Osprey_Matrix.xlsx", 32)]
res = ST.gather_matrices(paths, A.COMPLIANCE_LEARNED_FILE, A.CONFIG_DIR)
check("gather: decisions learned from each matrix", [n for _f, n in res] == [68, 64] and ST.load_state(A.CONFIG_DIR)["matrices"] == paths, res)
comp = ST.test_compliance(ST._matrices(paths))
check("compliance tests: Keep or not against the rules, sections in the top 3", comp[0]["n"] == 132 and comp[0]["after"] is not None
      and any(r["test"].startswith("Section suggestions") for r in comp), comp)
# a reader report, the scorecard
open(A.OCR_FIXES_FILE, "w", encoding="utf-8").write("Misread,Correct,Note\nTT8C,TT&C,\n")
os.makedirs(A.MODELS_DIR); open(os.path.join(A.MODELS_DIR, A.CUSTOM_TESS_MODEL + ".traineddata"), "wb").write(b"model")
report = {"words_correct_before_pct": 90.0, "words_correct_after_pct": 88.5, "check_lines": 20, "better": False}
have = [n for n, _p in A._knowledge_sources()]
rows = ST.scorecard(samples, A.load_ocr_fixes(), A.load_ocr_ignore(), report, ST._matrices(paths), have)
by = {r["area"]: r for r in rows}
check("the reader that got worse is left out automatically", not by["reading"]["include"] and by["reading"]["why"] == "Left out: got worse")
check("the fixes that help go in", by["fixes"]["include"] and by["fixes"]["change"] == 50.0, by["fixes"])
check("the acronyms database goes in, not tested", by["acronyms"]["include"] and by["acronyms"]["after"] is None)
check("an area with nothing to ship is not in", not by["banned"]["include"] and by["banned"]["why"] == "Nothing to ship")
rows2 = ST.scorecard(samples, A.load_ocr_fixes(), A.load_ocr_ignore(), report, ST._matrices(paths), have, left_out=["acronyms"])
check("the trainer can leave an area out", not {r["area"]: r for r in rows2}["acronyms"]["include"])
inc = ST.included_files(rows)
check("the files that go in follow the areas", "ocr_corrections.csv" in inc and "acronym_database.csv" in inc
      and not any(f.startswith("models/") for f in inc), inc)
pack = os.path.join(tmp, ST.default_name(__import__("datetime").date(2026, 11, 3)))
info = A.make_knowledge_pack(pack, "test", include=inc, scorecard=rows)
check("the pack is a .skknow with only the areas kept", pack.endswith("Stationkeeper Knowledge 2026-11-03.skknow")
      and "models/" + A.CUSTOM_TESS_MODEL + ".traineddata" not in info["files"] and "ocr_corrections.csv" in info["files"])
info2, data = A.read_knowledge_pack(pack)
lines = ST.card_lines(info2)
check("the scorecard travels with the pack, and the card says what was tested", info2["scorecard"][0]["area"] == "reading"
      and any(l.startswith("OCR fixes and ignore list: Words right on corrected lines, 50.0% to 100.0%") for l in lines)
      and not any(l.startswith("Reading") for l in lines), lines)
rep = A.install_knowledge_pack(pack)
check("it installs like any Knowledge Pack", "Installed Knowledge Pack" in rep and "Models: none in this pack" in rep, rep[:200])
n = sum(checks)
print(f"STUDIO PASS ({n}/{len(checks)})" if n == len(checks) else f"STUDIO FAIL ({n}/{len(checks)})")
