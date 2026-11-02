"""3.14.2: nothing that ships holds sample or demo content: no fictional effort names, products or numbers in the
program's code or the read-me files it carries, no sample effort, and no Guide pictures. Tests and build tools keep
their own fictional fixtures; they never ship."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"tests", "tools", "prototypes", "training_kit_src", "training_kit_doctr_src", "venv", "build", "dist", ".git",
             "_local_sandbox", "test_samples", "__pycache__", "vendor", "logs"}
BANNED = re.compile(r"kestrel|orbitlink|osprey|thermaloop|sample effort|try_sample|FA8810|Sierra Space|Jordan Reyes", re.I)

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


hits = []
for d, dirs, files in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
    for f in files:
        if f.endswith(".py") or (d == ROOT and f in ("README.txt", "OVERVIEW.md", "SECURITY.md")):
            p = os.path.join(d, f)
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if BANNED.search(line):
                    hits.append(f"{os.path.relpath(p, ROOT)}:{i}: {line.strip()[:90]}")
check("no fictional names or sample content in anything that ships", not hits, "\n  ".join([""] + hits[:20]))
check("no sample effort module or documents", not os.path.exists(os.path.join(ROOT, "skqt", "sample.py"))
      and not os.path.exists(os.path.join(ROOT, "assets", "sample")))
check("no Guide pictures", not os.path.exists(os.path.join(ROOT, "assets", "help")))
spec = open(os.path.join(ROOT, "Stationkeeper.spec"), encoding="utf-8").read()
check("the build carries neither", "assets/sample" not in spec and "assets/help" not in spec and "skqt.sample" not in spec)
n = sum(checks)
print(f"NO DEMO {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
