"""4.30.1 (Nicholas 2026-11-13 14:41): the app's own working folders carry Windows' Hidden mark; the folders people work
in do not. Hidden is set on each PC when the effort opens; the backups stay one click away. Fictional paths."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import hidefolders as HF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
base = os.path.join(tmp, "Stationkeeper"); eff = os.path.join(tmp, "Efforts", "Osprey")
data = os.path.join(eff, "Osprey_Effort_List - app data")
for d in (os.path.join(base, "_internal"), os.path.join(base, "_local_sandbox"), os.path.join(base, "assets"), data,
          os.path.join(eff, "01_proposal"), os.path.join(tmp, "Stationkeeper Data")):
    os.makedirs(d)
marked = []
setter = lambda p, a: (marked.append((os.path.relpath(p, tmp).replace(os.sep, "/"), a)) or True)   # noqa: E731
got = HF.program(base, setter)
check("the program's own working folders are hidden: _internal and _local_sandbox", [os.path.basename(p) for p in got] == ["_internal", "_local_sandbox"]
      and all(a == HF.HIDDEN for _p, a in marked), marked)
check("... and nothing else of the program: not its folder, not what else is in it", {p for p, _a in marked} == {"Stationkeeper/_internal", "Stationkeeper/_local_sandbox"})
marked.clear()
check("an effort's app data folder is hidden", HF.effort(data, setter) and marked == [("Efforts/Osprey/Osprey_Effort_List - app data", HF.HIDDEN)], marked)
check("... the folders people work in and Stationkeeper Data are never passed to it", not any("01_proposal" in p or p == "Stationkeeper Data" for p, _a in marked))
check("a folder that is not there is left alone", HF.hide(os.path.join(tmp, "nowhere"), setter) is False and HF.hide("", setter) is False)
check("off Windows nothing is marked and nothing fails", os.name == "nt" or (HF.hide(data) is False and HF.is_hidden(data) is False))
b = HF.backups_folder(data)
check("the backups folder is reached by its path, hidden or not, and made if missing", os.path.isdir(b) and b == os.path.join(data, "backups"))
src = open(os.path.join(os.path.dirname(HERE), "skqt_main.py"), encoding="utf-8").read()
saf = open(os.path.join(os.path.dirname(HERE), "skqt", "safety.py"), encoding="utf-8").read()
rec = open(os.path.join(os.path.dirname(HERE), "skqt", "recordpage.py"), encoding="utf-8").read()
check("the program hides its folders at start, an effort's when it opens, and Effort Record has Open the backups folder",
      "_HF.program(A.BASE_DIR)" in src and "HF.effort(h.ws.root)" in saf and '"Open the backups folder"' in rec)
n = sum(checks)
print(f"HIDE FOLDERS 4301 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
