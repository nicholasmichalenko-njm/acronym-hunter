"""3.38.1 the file size ratchet: a file of the program's own code stays under 800 lines, and a file already over 800
(tools/size_baseline.json) grows at most 5% past its baseline. Edits land reliably in small files; a big file is split
when a feature touches it, never in one large refactor. Raise a baseline only with a reason written in the file."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"tests", "tools", "prototypes", "training_kit_src", "training_kit_doctr_src", "venv", "build", "dist", ".git",
             "_local_sandbox", "test_samples", "__pycache__", "vendor", "logs", "internal_builds", "kit_build", "training_kit"}
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = json.load(open(os.path.join(ROOT, "tools", "size_baseline.json"), encoding="utf-8"))
base, limit, growth = cfg["files"], int(cfg["limit_new"]), float(cfg["growth"])
sizes = {}
for d, ds, fs in os.walk(ROOT):
    ds[:] = [x for x in ds if x not in SKIP_DIRS and not x.startswith(".")]
    for f in fs:
        if f.endswith(".py"):
            p = os.path.join(d, f)
            sizes[os.path.relpath(p, ROOT).replace(os.sep, "/")] = sum(1 for _ in open(p, encoding="utf-8"))
check(f"the program's own code was measured ({len(sizes)} files)", len(sizes) > 150)
new_big = {p: n for p, n in sizes.items() if p not in base and n > limit}
check(f"a file not in the baseline stays under {limit} lines", not new_big, new_big)
grown = {p: (n, base[p]) for p, n in sizes.items() if p in base and n > int(base[p] * (1 + growth))}
check(f"a big file grows at most {growth:.0%} past its baseline (split it when a feature touches it)", not grown, grown)
gone = [p for p in base if p not in sizes]
check("every file in the baseline still exists (take out a file that was split or removed)", not gone, gone)
n = sum(checks)
print(f"FILE SIZES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
