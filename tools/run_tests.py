"""Run every test and stop the release on any failure (3.37.0).

Finds the tests by folder, so a new test runs without anyone adding it to a list and a renamed one cannot be skipped
without a word: every tests/test_*.py, then every tests/qt_*.py, each in its own process with a time limit.

A test fails when it exits non-zero (an uncaught error does that), prints a FAIL line, or runs past the time limit. A
Traceback alone is not a failure: test_diag raises one in a thread on purpose to prove the crash log keeps no data. A test named in
RETRY_ONCE (timing-sensitive) gets one second run on its own; the log says when it passed only on the second run.

    venv\\Scripts\\python.exe tools\\run_tests.py              every test (used by buildrel before anything is built)
    venv\\Scripts\\python.exe tools\\run_tests.py qt_kickoff   only the named tests

4.5.0: SK_TEST_WORKERS=N (N > 1) runs N tests at a time, each worker with its own data folder (SK_DATA_DIR) and temp
folder (SK_TEST_WORKER), so tests cannot share settings, efforts or temp files (each process empties its temp folder at
start). The tests in SERIAL (Word, timings, this runner) run after them, one at a time. 4.6.0: on Windows, a hidden Word
a test left behind (no window, not running before the tests) is ended after each of those and at the end. A test
that fails while others run gets one run on its own; the log names it ("PASSED ONLY WHEN RUN ALONE"), and a test that
fails twice fails the gate. The output keeps the tests' order.

Prints each test's output (as the build log always had), then one totals line:
    TESTS_DONE <n> passed, <m> failed
and exits 1 when anything failed, so the build stops there. No network; standard library only."""
import os, re, shutil, subprocess, sys, tempfile, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.environ.get("SK_TESTS_DIR") or os.path.join(ROOT, "tests")   # another folder only for this runner's own test
LIMIT_S = int(os.environ.get("SK_TEST_LIMIT_S", "900"))
RETRY_ONCE = {"qt_speed"}                 # timings vary with what else the PC is doing
SERIAL = {"qt_speed", "test_wordgate", "test_office_pdf", "test_prodoffice", "test_run_tests", "test_setuptemplate",
          "test_prodtemplate", "qt_prodfix", "test_prodfix"}     # Word, timings and the runner itself: one at a time
FAIL_LINE = re.compile(r"\bFAIL\b")       # "QT X FAIL (27/28)", "FAIL  a check"; not "FAILED" in a message being tested
SKIP_LINE = re.compile(r"^\s*SKIP\b")        # a test that leaves a check out says "SKIP: why" (not the app's own Skip choices)


def discover(only=None):
    names = sorted(f[:-3] for f in os.listdir(TESTS) if f.startswith("test_") and f.endswith(".py"))
    names += sorted(f[:-3] for f in os.listdir(TESTS) if f.startswith("qt_") and f.endswith(".py"))
    if only:
        missing = [n for n in only if n not in names]
        if missing:
            print("NO SUCH TEST: " + ", ".join(missing))
        names = [n for n in names if n in only]
    return names


def run_one(name, env=None):
    """(ok, why, output). why is "" when ok."""
    start = time.time()
    try:
        p = subprocess.run([sys.executable, os.path.join(TESTS, name + ".py")], cwd=ROOT, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=LIMIT_S, env=env)
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


_WORD_LEFT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$keep = @($env:SK_KEEP -split ',')
$n = 0
Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -eq 0 -and $keep -notcontains "$($_.Id)" } |
  ForEach-Object { Stop-Process -Id $_.Id -Force; $n++ }
$n
"""


def word_pids():
    """4.6.0: the Word processes running now (Windows only), so the ones the tests leave can be told apart."""
    if os.name != "nt":
        return None
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"], capture_output=True, timeout=60)
        return {ln.split('","')[1] for ln in p.stdout.decode("utf-8", "replace").splitlines() if ln.startswith('"WINWORD')}
    except (OSError, subprocess.SubprocessError, IndexError):
        return set()


def end_word_left(before):
    """End the windowless Word processes that started during the tests (a Word someone has open has a window and is
    never touched; Word that was running before the tests is left alone). Returns how many."""
    if before is None:
        return 0
    try:
        p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _WORD_LEFT], capture_output=True,
                           timeout=120, env=dict(os.environ, SK_KEEP=",".join(sorted(before))))
        return int((p.stdout.decode("utf-8", "replace").strip().splitlines() or ["0"])[-1] or 0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0


def workers():
    try:
        return max(1, int(os.environ.get("SK_TEST_WORKERS", "1")))
    except ValueError:
        return 1


def run_parallel(names, n):
    """Runs names n at a time and returns {name: (ok, why, out, started)}. Each worker keeps its own data folder."""
    base = tempfile.mkdtemp(prefix="sk_workers_")
    queue, lock, done = list(names), threading.Lock(), {}

    def work(i):
        env = dict(os.environ, SK_DATA_DIR=os.path.join(base, f"w{i}"), SK_TEST_WORKER=f"w{i}")   # own data and temp folders
        env.pop("SK_TEST_WORKERS", None)
        while True:
            with lock:
                if not queue:
                    return
                name = queue.pop(0)
            started = time.strftime('%H:%M:%S')
            ok, why, out = run_one(name, env)
            with lock:
                done[name] = (ok, why, out, started)
                print(f"TRAN {name} {'ok' if ok else 'failed'} ({len(done)}/{len(names)})", flush=True)

    ts = [threading.Thread(target=work, args=(i,), daemon=True) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    shutil.rmtree(base, ignore_errors=True)
    return done


def main(argv):
    names = discover(argv[1:] or None)
    if not names:
        print("TESTS_DONE 0 passed, 0 failed (no tests found)")
        return 1
    failed, retried, skipped, alone = [], [], [], []
    word_before = word_pids()
    n = workers()
    pre = {}
    if n > 1:
        par = [x for x in names if x not in SERIAL]
        print(f"WORKERS {n} ({len(par)} tests at {n} at a time, then {len(names) - len(par)} one at a time)", flush=True)
        pre = run_parallel(par, n)
        names = par + [x for x in names if x in SERIAL]
    for name in names:
        if name in pre:
            ok, why, out, started = pre[name]
            print(f"TSTART {name} {started}", flush=True)
            if not ok:
                print(out.rstrip())
                print(f"ALONE {name} (failed while others ran: {why})", flush=True)
                ok, why, out = run_one(name)
                if ok:
                    alone.append(name)
        else:
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
        if name in SERIAL and word_before is not None:
            n_left = end_word_left(word_before)
            if n_left:
                print(f"WORD_LEFT {name}: ended {n_left} hidden Word process(es) the test left", flush=True)
    n_left = end_word_left(word_before)
    if n_left:
        print(f"WORD_LEFT ended {n_left} hidden Word process(es) left by the tests", flush=True)
    print()
    if retried:
        print("PASSED ONLY ON A SECOND RUN: " + ", ".join(retried))
    if alone:
        print("PASSED ONLY WHEN RUN ALONE: " + ", ".join(alone))
    if skipped:
        print("LEFT A CHECK OUT (SKIP lines; run them on the PC with Word): " + ", ".join(skipped))
    for name, why in failed:
        print(f"FAILED: {name}: {why}")
    print(f"TESTS_DONE {len(names) - len(failed)} passed, {len(failed)} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
