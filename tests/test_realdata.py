"""3.23.0 testing with the team's real data, at build time only: when the build PC has a Stationkeeper Data file in the
folder named by SK_REAL_DATA (outside the code, never committed), it is imported into a scratch folder, a template is
made from the team standard with every Quick Part it lists, and the template is checked; the summary prints for the
build log (counts only, no names or text). Without the folder the test says so and passes."""
import glob, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


folder = os.environ.get("SK_REAL_DATA", "")
files = sorted(glob.glob(os.path.join(folder, "*.skdata")), key=os.path.getmtime) if folder and os.path.isdir(folder) else []
if not files:
    check("no real data on this PC: nothing to test (put a Stationkeeper Data file in the SK_REAL_DATA folder)", True)
else:
    import app_gui as A
    import teamdata as TD, prodrules as PRL, prodtemplate as PT, prodparts as PP, templatecheck as TC
    cfg = os.path.join(tmp, "data", "config"); os.makedirs(cfg, exist_ok=True)
    A.DB_FILE = os.path.join(tmp, "data", "acronym_database.csv")
    man, data = TD.read(files[-1])
    said = TD.install(cfg, man, data)
    check("the real data file imports", said, man.get("parts"))
    std = PRL.engine_ready(PRL.resolved_type(PRL.load(cfg), PRL.load(cfg)["default"]))
    std["_parts_dir"] = PP.parts_dir(cfg)
    std["name"] = "Real data check"
    tj = PT.make(std, os.path.join(tmp, "out"))
    rep = tj.validation
    qp = next((s for s in tj.steps if s.get("key") == "quick_parts"), {}).get("report") or {}
    print(f"REAL DATA: {len(man.get('parts', {}))} part(s); template check {tj.check.count()} finding(s); validation "
          f"{len(rep.problems()) if rep else '-'} problem(s), {len(rep.warnings()) if rep else '-'} warning(s); Quick Parts "
          f"{len(qp.get('copied', []))} in, {len(qp.get('skipped', []))} left out, {len(qp.get('missing', []))} missing")
    check("a template is made from the team's real standard", os.path.isfile(tj.copy) and not [s for s in tj.steps if s.get("refused")],
          [s.get("refused") for s in tj.steps if s.get("refused")])
shutil.rmtree(tmp, ignore_errors=True)
print(f"REAL DATA {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
