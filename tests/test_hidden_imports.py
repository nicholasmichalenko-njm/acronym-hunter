"""4.1.0: every module the code reaches only through __import__("...") is in Stationkeeper.spec's hidden imports, so the
built program has it (4.1.0's first PC build stopped at the self test: skqt.qadrawer was left out of the bundle)."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


STD = {"os", "re", "io", "sys", "json", "time", "datetime", "app_gui"}
files = [os.path.join(ROOT, f) for f in os.listdir(ROOT) if f.endswith(".py")]
files += [os.path.join(ROOT, "skqt", f) for f in os.listdir(os.path.join(ROOT, "skqt")) if f.endswith(".py")]
text = {f: open(f, encoding="utf-8").read() for f in files}
dyn = set()
for t in text.values():
    dyn |= set(re.findall(r'__import__\("([A-Za-z_][\w.]*)"', t))
spec = open(os.path.join(ROOT, "Stationkeeper.spec"), encoding="utf-8").read()


def static(m):
    last = m.rsplit(".", 1)[-1]
    pat = re.compile(rf"(from \. import [\w, ]*\b{last}\b|from \.{last} import|import {re.escape(m)}\b|from {re.escape(m)} import|"
                     rf"^\s*import [\w, ]*\b{last}\b|^\s*from {last} import)", re.M)
    return any(pat.search(t) for t in text.values())


missing = sorted(m for m in dyn - STD if f"'{m}'" not in spec and not static(m))
check("every module reached only through __import__ is a hidden import of the build", not missing, missing)
print(f"HIDDEN IMPORTS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
