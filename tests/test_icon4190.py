"""4.19.0: the taskbar icon. Built, the program's folder holds the exe and _internal holds the assets, so an icon looked
for beside the exe was never found and Windows showed a blank one. The window icon comes from app_gui.asset_path, which
looks in _internal (sys._MEIPASS) first; nothing else builds an assets path from BASE_DIR. The icons have their sizes."""
import os, re, struct, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_TEST"] = "1"
import app_gui as A

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


tmp = tempfile.mkdtemp()                                   # the built layout: the exe's folder has no assets
old_base, had = A.BASE_DIR, hasattr(sys, "_MEIPASS")
A.BASE_DIR = tmp
sys._MEIPASS = ROOT                                        # _internal, where the build puts assets
try:
    got = A.asset_path("scanner.ico")
    check("built: the icon is found in _internal, not beside the exe", got == os.path.join(ROOT, "assets", "scanner.ico"), got)
    check("... and the Trainer's", A.asset_path("trainer.ico") == os.path.join(ROOT, "assets", "trainer.ico"))
finally:
    A.BASE_DIR = old_base
    if not had:
        del sys._MEIPASS
check("from source: found beside the code", A.asset_path("scanner.ico") == os.path.join(ROOT, "assets", "scanner.ico"))
bad = []
for d, _s, fs in os.walk(ROOT):
    if any(p in d for p in (".git", "tests", "tools", "_local_sandbox", "build", "dist")):
        continue
    for f in fs:
        if f.endswith(".py"):
            t = open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
            if re.search(r"BASE_DIR,\s*[\"']assets[\"']", t) and f != "app_gui.py":
                bad.append(f)
check("no window builds an assets path from BASE_DIR (it misses _internal when built)", not bad, bad)
src = open(os.path.join(ROOT, "skqt_main.py"), encoding="utf-8").read()
check("the built program's self-test fails without a window icon", "windowIcon().isNull()" in src)
with open(os.path.join(ROOT, "assets", "scanner.ico"), "rb") as fh:
    head = fh.read(6 + 16 * 16)
n = struct.unpack("<H", head[4:6])[0]
sizes = sorted({(head[6 + 16 * i] or 256) for i in range(n)})
check("the icon holds the taskbar's sizes (16, 24, 32, 48, 256)", all(s in sizes for s in (16, 24, 32, 48, 256)), sizes)
k = sum(checks)
print(f"ICON 4190 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if k == len(checks) else 1)
