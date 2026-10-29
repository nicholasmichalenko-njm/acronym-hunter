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
n = sum(checks)
print(f"OFFICE PDF PASS ({n}/{len(checks)})" if n == len(checks) else f"OFFICE PDF FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
