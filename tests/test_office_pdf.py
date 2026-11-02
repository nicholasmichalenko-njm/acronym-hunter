"""2.71.0 Office PDF copies never leave a hidden Office behind: the copy script records the process IDs of the Office
program it starts (only the ones that appeared when it started, never a window the person opened); when a copy takes
too long, those are ended (and only if they are still that Office program); a password-protected Word or Excel file
fails at once instead of waiting on a hidden prompt."""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import office_pdf as OP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "Section_L.docx")
open(src, "wb").write(b"PK fake docx")
folder = os.path.join(tmp, "copies")
check("the Word script records the IDs of the Word it starts", "SK_PIDFILE" in OP._SCRIPT["word"]
      and "$before -notcontains" in OP._SCRIPT["word"] and "SK_PIDFILE" in OP._SCRIPT["excel"] and "SK_PIDFILE" in OP._SCRIPT["powerpoint"])
check("a protected Word or Excel file fails at once (a wrong password, not a hidden prompt)",
      "'sk-no-password'" in OP._SCRIPT["word"] and "'sk-no-password'" in OP._SCRIPT["excel"])
seen = {}


def slow(cmd, env, timeout):
    seen["pidfile"] = env["SK_PIDFILE"]
    with open(env["SK_PIDFILE"], "w", encoding="utf-8") as f:
        f.write("4242,4343")
    raise subprocess.TimeoutExpired(cmd, timeout)


ended = []
real = OP._end_started
OP._end_started = lambda pidfile, k, runner=None: ended.append(real(pidfile, k, runner=lambda c: seen.setdefault("cmds", []).append(c)))
res = OP.make_many([src], folder, timeout=1, runner=slow)
OP._end_started = real
check("a copy that takes too long says so", isinstance(res[src], RuntimeError) and "too long" in str(res[src]), res[src])
check("and ends the Word it started, by its IDs, only if it is still Word", ended == [[4242, 4343]]
      and seen["cmds"][0] == ["taskkill", "/PID", "4242", "/FI", "IMAGENAME eq WINWORD.EXE", "/F"], seen.get("cmds"))
check("the ID file is cleaned up", not os.path.exists(seen["pidfile"]))
check("no ID file: nothing is ended", OP._end_started(os.path.join(tmp, "none.pid"), "word", runner=lambda c: 1 / 0) == [])
check("2.93.0: every script quits the Office it started, even when a file fails, and never ends another copy's Office",
      all("} finally {" in sc and "if ($was -eq 0 -or $was -eq $null)" in sc and "ReleaseComObject($app)" in sc and "[GC]::Collect()" in sc
          and "Stop-Process" not in sc for sc in OP._SCRIPT.values()))
# 3.14.3: Stationkeeper closing stops a copy at once
class FakeProc:
    def __init__(self, *a, **k):
        self.killed = False
    def communicate(self, timeout=None):
        if self.killed:
            return b"", b""
        raise subprocess.TimeoutExpired("powershell", timeout)
    def kill(self):
        self.killed = True
procs = []
asked = {"n": 0}
def stop_after_one():
    asked["n"] += 1
    return asked["n"] > 1
r = OP._run(["powershell"], {}, 600, stop=stop_after_one, popen=lambda *a, **k: procs.append(FakeProc()) or procs[-1])
check("the copy script is checked while it runs: stop ends it at once", r is OP._STOPPED and procs[0].killed, r)
try:
    OP._run(["powershell"], {}, 0.6, popen=lambda *a, **k: FakeProc())
    late = False
except subprocess.TimeoutExpired:
    late = True
check("past the time limit it is ended and says so", late)
src2 = os.path.join(tmp, "Section_M.docx"); open(src2, "wb").write(b"PK fake docx")
folder2 = os.path.join(tmp, "copies2")
real_av, real_run, real_end = OP.available, OP._run, OP._end_started
ended2 = []
def half_made(cmd, env, timeout, stop):
    for line in env["SK_LIST"].splitlines():                    # Word got part way through
        open(line.split("\t")[1], "wb").write(b"%PDF-1.7 half")
    with open(env["SK_PIDFILE"], "w", encoding="utf-8") as f:
        f.write("5151")
    return OP._STOPPED
OP.available, OP._run = (lambda: True), half_made
OP._end_started = lambda pidfile, k, runner=None: ended2.append(k)
res2 = OP.make_many([src2], folder2, stop=lambda: False)
OP.available, OP._run, OP._end_started = real_av, real_run, real_end
check("stopped: no copy, no half-made part kept, the Word it started is ended", isinstance(res2[src2], RuntimeError)
      and "stopped" in str(res2[src2]) and not any(f.endswith(".pdf") for f in os.listdir(folder2))
      and ended2 == ["word"], (res2, os.listdir(folder2), ended2))
res3 = OP.make_many([src2], folder2, stop=lambda: True, runner=lambda *a: 1 / 0)
check("asked to stop before it starts: Office is never started", "stopped" in str(res3[src2]), res3)
n = sum(checks)
print(f"OFFICE PDF PASS ({n}/{len(checks)})" if n == len(checks) else f"OFFICE PDF FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
