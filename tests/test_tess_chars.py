"""2.55.0 Improve Reading learns Greek letters, math and unit signs: the characters Google's English reader lacks are
found, a new character set is built with the engine's own tools (no network), and training uses it with the old
model; without the tools or the data table, training keeps Google's set."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tess_train as T

tmp = tempfile.mkdtemp()
u = os.path.join(tmp, "eng.lstm-unicharset")
open(u, "w", encoding="utf-8").write("5\nNULL 0 Common 0\na 3 x\nb 3 x\n= 10 x\n° 10 x\n")
known = T.read_unicharset(u)
assert {"a", "b", "=", "°"} <= known
new = T.new_characters(known, ["a = b ΔV"], extra="Ωab")
assert new == sorted({"Δ", "V", "Ω"}), new
assert "Δ" in T.MATH_CHARS and "₀" in T.MATH_CHARS and "µ" in T.MATH_CHARS
tess = os.path.join(tmp, "tess"); work = os.path.join(tmp, "work"); os.makedirs(tess); os.makedirs(work)
open(os.path.join(work, "eng.lstm-unicharset"), "w").write("x")
calls = []


def run(cmd, timeout=600):
    calls.append(os.path.basename(cmd[0]))
    if calls[-1] == "unicharset_extractor.exe":
        open(cmd[2], "w").write("u")
    elif calls[-1] == "merge_unicharsets.exe":
        open(cmd[3], "w").write("m")
    elif calls[-1] == "combine_lang_model.exe":
        d = os.path.join(cmd[cmd.index("--output_dir") + 1], "eng"); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "eng.traineddata"), "w").write("t")
    return 0, ""


assert T.extend_traineddata(run, tess, work, "base", ["Δ"], ["ΔV"]) is None and not calls     # no tools: Google's set
for t in T.ADD_TOOLS:
    open(os.path.join(tess, t), "w").write("")
assert T.extend_traineddata(run, tess, work, "base", ["Δ"], ["ΔV"]) is None                   # no data table
os.makedirs(os.path.join(tess, "langdata")); open(os.path.join(tess, "langdata", "radical-stroke.txt"), "w").write("1 1 1 1 1\n")
td = T.extend_traineddata(run, tess, work, "base", ["Δ"], ["ΔV"])
assert td and td.endswith(os.path.join("lang", "eng", "eng.traineddata")) and calls == list(T.ADD_TOOLS), (td, calls)
assert "Δ" in open(os.path.join(work, "chars.txt"), encoding="utf-8").read()
r = {"words_correct_before_pct": 80, "words_correct_after_pct": 90, "check_lines": 5, "chars_correct_before_pct": 90,
     "chars_correct_after_pct": 95, "samples": 400, "added_characters": "ΔΩ"}
assert "New characters the reader learned: ΔΩ" in T.describe(r)
print("tess chars ok")

import studio as S
rep = {"words_correct_before_pct": 80, "words_correct_after_pct": 85, "check_lines": 30, "better": True,
       "symbols_correct_before_pct": 40, "symbols_correct_after_pct": 88, "symbol_lines": 6}
rows = S.scorecard([], {}, [], rep, [], ["models/acronym.traineddata"])
sym = [r for r in rows if r["title"] == "Symbols and equations"]
assert sym and sym[0]["now"] == 40 and sym[0]["after"] == 88 and sym[0]["include"], sym
rep["symbols_correct_after_pct"] = 30
rows = S.scorecard([], {}, [], rep, [], ["models/acronym.traineddata"])
assert not any(r["include"] for r in rows if r["area"] == "reading"), "worse on symbols leaves the reader out"
print("studio symbols ok")
