"""4.30.4 (Nicholas 2026-11-13 20:05): a hard crash recorded only three idle worker threads, because the first twelve
frames of the dump were kept and the dump lists the newest threads first. The record now leads with the thread that
crashed. File name, line and function only. Made-up paths."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import diag

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


worker = '''Thread 0x0000{n} (most recent call first):
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\concurrent\\\\futures\\\\thread.py", line 81 in _worker
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\threading.py", line 982 in run
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\threading.py", line 1045 in _bootstrap_inner
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\threading.py", line 1002 in _bootstrap
'''
raw = "Windows fatal exception: access violation\n\n" + "\n".join(worker.format(n=n) for n in ("1a2b", "3c4d", "5e6f")) + '''
Current thread 0x00000a10 (most recent call first):
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\skqt\\\\acronympage.py", line 345 in show_detail
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\skqt\\\\acrfast.py", line 140 in sync_rows
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\skqt\\\\acronympage.py", line 262 in fill
  File "C:\\\\Osprey\\\\app\\\\_internal\\\\skqt_main.py", line 160 in main
'''
w = diag.crash_where(raw)
check("the thread that crashed leads the record, in full", w[:5] == ["crashed in this thread:", "acronympage.py:345:show_detail", "acrfast.py:140:sync_rows",
                                                                  "acronympage.py:262:fill", "skqt_main.py:160:main"], w[:6])
check("each other thread follows with two frames", w.count("another thread:") == 3 and w[5:8] == ["another thread:", "thread.py:81:_worker", "threading.py:982:run"], w[5:9])
check("only file name, line and function are kept: no folder", not any("Osprey" in x or "\\" in x or "/" in x for x in w))
native = "Windows fatal exception: access violation\n\n" + worker.format(n="1a2b") + "\nCurrent thread 0x00000a10 (most recent call first):\n  <no Python frame>\n"
check("a crash outside Python code says so, and is not mistaken for a worker thread",
      diag.crash_where(native)[:2] == ["crashed in this thread:", "no Python code (inside a program library)"], diag.crash_where(native))
old = 'Fatal Python error: Segmentation fault\n  File "/x/y/app_gui.py", line 12 in scan\n'
check("a dump with no thread headings keeps its frames as before", diag.crash_where(old) == ["app_gui.py:12:scan"])
n = sum(checks)
print(f"CRASH WHERE 4304 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
