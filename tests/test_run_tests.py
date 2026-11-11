"""3.37.0 the release gate: tools/run_tests.py finds tests by folder and fails on a non-zero exit, a crash, a FAIL line or
a test that runs too long; a passing set exits 0; a timing test gets one second run; helpers that are not tests are left
alone; a Traceback a test raises on purpose in a thread is not a failure. Runs the gate on small made-up tests in a
scratch folder (never on this suite, so it cannot call itself)."""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "tools", "run_tests.py")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok))
    print(("ok   " if ok else "FAIL ") + name + (f"  ({info})" if info and not ok else ""))


def gate(files, *names, limit="20"):
    d = tempfile.mkdtemp()
    for fn, body in files.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write(body)
    env = dict(os.environ, SK_TESTS_DIR=d, SK_TEST_LIMIT_S=limit)
    p = subprocess.run([sys.executable, RUNNER, *names], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


GOOD = "print('GOOD PASS (3/3)')\n"
code, out = gate({"test_a.py": GOOD, "qt_b.py": GOOD, "_helper.py": "raise SystemExit(1)\n", "win_x.py": "raise SystemExit(1)\n"})
check("a passing set exits 0", code == 0, out[-300:])
check("both families run, test_ before qt_", out.find("TSTART test_a") < out.find("TSTART qt_b") and "TSTART qt_b" in out, out[-300:])
check("helpers that are not tests are left alone", "_helper" not in out and "win_x" not in out, out[-300:])
check("the totals line counts them", "TESTS_DONE 2 passed, 0 failed" in out, out[-300:])

code, out = gate({"test_a.py": GOOD, "test_exit.py": "import sys; print('x'); sys.exit(3)\n"})
check("a non-zero exit fails the gate", code == 1 and "FAILED: test_exit: exit 3" in out, out[-300:])

code, out = gate({"test_crash.py": "print('start')\nraise ValueError('boom')\n"})
check("a crash fails the gate", code == 1 and "FAILED: test_crash: exit 1" in out, out[-300:])

thread = ("import threading\nt = threading.Thread(target=lambda: (_ for _ in ()).throw(ValueError('on purpose')))\n"
          "t.start(); t.join(); print('diag ok')\n")
code, out = gate({"test_thread.py": thread})
check("a Traceback from a thread that the test raises on purpose is not a failure", code == 0 and "Traceback" in out, out[-300:])

code, out = gate({"qt_quiet.py": "print('ok   one'); print('FAIL two'); print('QT QUIET FAIL (1/2)')\n"})
check("a line saying a check failed fails the gate even when the exit is 0", code == 1 and "FAIL line" in out, out[-300:])

code, out = gate({"test_word.py": "print('LEAK CHECK FAILED is the message under test'); print('word ok')\n"})
check("FAILED inside a message under test is not a failure", code == 0, out[-300:])

code, out = gate({"test_slow.py": "import time; time.sleep(30)\n"}, limit="2")
check("a test that runs too long fails the gate", code == 1 and "ran past 2 s" in out, out[-300:])

flaky = ("import os, sys\nf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ran')\n"
         "if not os.path.exists(f):\n    open(f, 'w').close(); print('QT SPEED FAIL (0/1)'); sys.exit(1)\nprint('QT SPEED PASS (1/1)')\n")
code, out = gate({"qt_speed.py": flaky})
check("the timing test gets one second run and the log says so", code == 0 and "PASSED ONLY ON A SECOND RUN: qt_speed" in out,
      out[-400:])

# 4.5.0: several at a time, each with its own data folder; the output keeps the order; a contention failure runs alone
shared = ("import os, sys\nd = os.environ.get('SK_DATA_DIR', '')\nprint('dir ' + os.path.basename(d))\n"
          "sys.exit(0 if d else 4)\n")
alone_body = ("import os, sys\nif os.environ.get('SK_DATA_DIR'):\n    print('busy'); sys.exit(2)\nprint('alone ok')\n")
os.environ["SK_TEST_WORKERS"] = "3"
code, out = gate({"test_p1.py": shared, "test_p2.py": shared, "test_p3.py": shared, "qt_p4.py": shared,
                  "test_alone.py": alone_body, "test_run_tests.py": "print('serial')\n"})
del os.environ["SK_TEST_WORKERS"]
check("workers: a passing set exits 0 and says how many at a time", code == 0 and "WORKERS 3" in out, out[-500:])
check("workers: each test has a data folder of its worker's", out.count("dir w") == 4, out[-500:])
check("workers: the output keeps the tests' order", out.find("TSTART test_alone") < out.find("TSTART test_p1") < out.find("TSTART qt_p4")
      < out.find("TSTART test_run_tests"), out[-500:])
check("workers: a test that fails among others passes alone and the log names it",
      "PASSED ONLY WHEN RUN ALONE: test_alone" in out and "TESTS_DONE 6 passed, 0 failed" in out, out[-500:])
code, out = gate({"test_p1.py": shared, "test_bad.py": "import sys; sys.exit(5)\n"})
check("without workers nothing changes (no data folder of its own)", code == 1 and "WORKERS" not in out and "FAILED: test_p1: exit 4" in out, out[-500:])

code, out = gate({"test_a.py": GOOD, "test_c.py": GOOD}, "test_c")
check("named tests run alone", "TSTART test_c" in out and "TSTART test_a" not in out, out[-300:])

code, out = gate({"test_word.py": "print('SKIP: Word is not on this PC'); print('the same file is skipped'); print('ok')\n",
                  "test_feature.py": "print('PASS the same file twice is skipped')\n"})
check("a test that leaves a check out (no Word) is listed", code == 0 and "LEFT A CHECK OUT" in out and "test_word" in out
      and "test_feature" not in out.split("LEFT A CHECK OUT")[1],
      out[-300:])

n = sum(checks)
print(f"RUN TESTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
