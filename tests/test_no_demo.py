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


def shipped_sources():
    """The program's own tracked files (git ls-files): fast, and never another folder's venv or build output."""
    import subprocess
    try:
        names = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=60, check=True).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):          # not a git checkout: walk, skipping other environments
        names = []
        for d, dirs, files in os.walk(ROOT):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith((".", "venv", "dist", "kit_"))]
            names += [os.path.relpath(os.path.join(d, f), ROOT) for f in files]
    for n in names:
        n = n.replace("\\", "/")
        if n.split("/")[0] in SKIP_DIRS:
            continue
        if n.endswith(".py") or n in ("README.txt", "OVERVIEW.md", "SECURITY.md"):
            yield os.path.join(ROOT, n)


hits = []
for p in shipped_sources():
    if not os.path.isfile(p):
        continue
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
