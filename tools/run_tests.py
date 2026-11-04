"""Run every test and stop the release on any failure (3.37.0).

Finds the tests by folder, so a new test runs without anyone adding it to a list and a renamed one cannot be skipped
without a word: every tests/test_*.py, then every tests/qt_*.py, each in its own process with a time limit.

A test fails when it exits non-zero (an uncaught error does that), prints a FAIL line, or runs past the time limit. A
Traceback alone is not a failure: test_diag raises one in a thread on purpose to prove the crash log keeps no data. A test named in
RETRY_ONCE (timing-sensitive) gets one second run on its own; the log says when it passed only on the second run.

    venv\\Scripts\\python.exe tools\\run_tests.py              every test (used by buildrel before anything is built)
    venv\\Scripts\\python.exe tools\\run_tests.py qt_kickoff   only the named tests

Prints each test's output (as the build log always had), then one totals line:
    TESTS_DONE <n> passed, <m> failed
and exits 1 when anything failed, so the build stops there. No network; standard library only."""
import os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.environ.get("SK_TESTS_DIR") or os.path.join(ROOT, "tests")   # another folder only for this runner's own test
LIMIT_S = int(os.environ.get("SK_TEST_LIMIT_S", "900"))
RETRY_ONCE = {"qt_speed"}                 # timings vary with what else the PC is doing
FAIL_LINE = re.compile(r"\bFAIL\b")       # "QT X FAIL (27/28)", "FAIL  a check"; not "FAILED" in a message being tested
SKIP_LINE = re.compile(r"\bskip(ped|s)?\b", re.I)


def discover(only=None):
    names = sorted(f[:-3] for f in os.listdir(TESTS) if f.startswith("test_") and f.endswith(".py"))
    names += sorted(f[:-3] for f in os.listdir(TESTS) if f.startswith("qt_") and f.endswith(".py"))
    if only:
        missing = [n for n in only if n not in names]
        if missing:
            print("NO SUCH TEST: " + ", ".join(missing))
        names = [n for n in names if n in only]
    return names


def run_one(name):
    """(ok, why, output). why is "" when ok."""
    start = time.time()
    try:
        p = subprocess.run([sys.executable, os.path.join(TESTS, name + ".py")], cwd=ROOT, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=LIMIT_S)
        out = p.stdout.decode("utf-8", "replace")
        code = p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace")
        return False, f"ran past {LIMIT_S} s", out
    secs = time.time() - start
    if code != 0:
        return False, f"exit {code}", out
    bad = [ln for ln in out.splitlines() if FAIL_LINE.search(ln)]
    if bad:
        return False, "FAIL line: " + bad[0].strip()[:160], out
    return True, f"{secs:.0f} s", out


def main(argv):
    names = discover(argv[1:] or None)
    if not names:
        print("TESTS_DONE 0 passed, 0 failed (no tests found)")
        return 1
    failed, retried, skipped = [], [], []
    for name in names:
        print(f"TSTART {name} {time.strftime('%H:%M:%S')}", flush=True)
        ok, why, out = run_one(name)
        if not ok and name in RETRY_ONCE:
            print(out.rstrip())
            print(f"RETRY {name} (failed first: {why})", flush=True)
            ok, why, out = run_one(name)
            if ok:
                retried.append(name)
        print(out.rstrip(), flush=True)
        if any(SKIP_LINE.search(ln) for ln in out.splitlines()):
            skipped.append(name)
        if not ok:
            failed.append((name, why))
            print(f"TEST_FAILED {name}: {why}", flush=True)
    print()
    if retried:
        print("PASSED ONLY ON A SECOND RUN: " + ", ".join(retried))
    if skipped:
        print("SAID THEY SKIPPED SOMETHING (check on the PC with Word): " + ", ".join(skipped))
    for name, why in failed:
        print(f"FAILED: {name}: {why}")
    print(f"TESTS_DONE {len(names) - len(failed)} passed, {len(failed)} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
