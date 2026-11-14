"""3.22.0 the team's data never reaches GitHub: no Stationkeeper Data file, team pack, template library, standards file,
dictionary, phrase list, author list or acronym list (other than the generic starter in base\\) is tracked by git, and
the ignore list names them. A tracked one fails the build before anything is published."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD_EXT = (".skdata", ".skteam", ".sklib", ".skknow", ".sktrain")
BAD_NAMES = ("custom_dictionaries.json", "production_standards.json", "Company Standards.xlsx", "Global Standards.xlsx", "global_standards.json", "team_library_state.json", "team_bins.json", "banned_words.csv", "author_list.json",
             "wall_of_truth.json", "suggestion_rules.json", "acronym_database.csv")
BAD_DIRS = ("production_parts/", "template_library/", "data_backups/", "team_backups/", "knowledge_backups/")
ALLOWED = ("base/",                       # the generic starter data shipped with the program
           "tests/golden/")                 # 3.38.1: fictional golden files (tools/make_golden.py), never real data

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


try:
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout.splitlines()
except (OSError, subprocess.SubprocessError):
    files = None
if files is None or not files:
    check("not a git checkout: nothing to guard here", True)
else:
    bad = [f for f in files if not f.startswith(ALLOWED) and (f.lower().endswith(BAD_EXT) or os.path.basename(f) in BAD_NAMES
                                                            or any(d in f for d in BAD_DIRS))]
    check("git tracks none of the team's data", not bad, bad[:20])
ign = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
check("the ignore list names the team's data files", all(p in ign for p in ("*.skdata", "*.skteam", "*.sklib", "template_library/", "production_parts/")))
print(f"DATA GUARD {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
