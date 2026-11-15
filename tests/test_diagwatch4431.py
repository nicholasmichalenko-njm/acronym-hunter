"""4.43.1 (ST53 of 2026-11-15): what the diagnostics now see, with fixed words and no content. A Qt message is kept by
its kind and its fixed name, never its text; a window that stops answering leaves where each thread was, as file, line
and function; an error while Python cleans up is recorded; and the PDF lock covers closes made by Python's cleanup."""
import gc, json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import diag, diagwatch as DW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
logs = os.path.join(tmp, "logs")
diag.OFF = False
diag.setup(logs, "4.43.1")


def events():
    p = os.path.join(logs, "events.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.isfile(p) else []


SECRET = "Kestrel Volume I Technical.docx"
check("a known Qt message has a fixed name", DW.template_of("QObject::startTimer: Timers cannot be started from another thread") == "timer_started_from_another_thread"
      and DW.template_of("QObject: Cannot create children for a parent that is in a different thread.\n(Parent is QStatusBar(0x1f2))") == "child_for_parent_in_another_thread")
check("a message that is not on the list is other", DW.template_of(f"Could not open {SECRET}") == "other" and DW.template_of("") == "other")
check("every fixed name is short lower-case words", all(__import__("re").match(r"^[a-z][a-z_]{2,40}$", n) for n in DW.NAMES))
DW.qt_message(1, f"QPixmap::scaled: Pixmap is a null pixmap in {SECRET}")
ev = events()
check("a warning is recorded by kind and name", len(ev) == 1 and ev[0]["area"] == "qt" and ev[0]["msg"] == "Qt reported a problem"
      and ev[0]["type"] == "warning" and ev[0]["tpl"] == "pixmap" and ev[0]["n"] == 1, ev)
check("... and never by its text", SECRET not in json.dumps(ev) and "null pixmap" not in json.dumps(ev))
for _ in range(9):
    DW.qt_message(1, "QPixmap::scaled: again")
check("a repeat is counted, not written each time: the tenth is", [e["n"] for e in events() if e.get("tpl") == "pixmap"] == [1, 10])
DW.qt_message(0, "debug chatter"); DW.qt_message(4, "info chatter")
check("debug and info messages are not recorded", len(events()) == 2)
DW.qt_message(3, f"something fatal about {SECRET}")
check("a fatal message is always recorded, as other when unknown", events()[-1]["type"] == "fatal" and events()[-1]["tpl"] == "other" and SECRET not in json.dumps(events()))

# ---------------------------------------------------------------- Qt's handler, for real
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QCoreApplication, qWarning
app = QCoreApplication.instance() or QCoreApplication([])
before = len(events())
DW.install_qt()
qWarning(f"QObject::connect: No such signal in {SECRET}")
ev = events()
check("Qt's own warning reaches the record through the handler", len(ev) == before + 1 and ev[-1]["tpl"] == "connect_failed" and SECRET not in json.dumps(ev), ev[-1:])

# ---------------------------------------------------------------- errors while Python cleans up
DW.install_cleanup()


class Leaky:
    def __del__(self):
        raise ValueError(f"could not close {SECRET}")


Leaky(); gc.collect()
errs = [json.loads(l) for l in open(os.path.join(logs, "errors.jsonl"), encoding="utf-8")] if os.path.isfile(os.path.join(logs, "errors.jsonl")) else []
allrec = errs + events()
hit = [e for e in allrec if e.get("area") == "cleanup"]
check("an error in an object's cleanup is recorded", len(hit) == 1 and hit[0]["msg"] == "An error while Python was cleaning up", allrec[-2:])
check("... without its message", SECRET not in json.dumps(allrec))

# ---------------------------------------------------------------- a window that stops answering
raw = '''Timeout (0:00:05)!
Thread 0x00001a2c (most recent call first):
  File "C:\\\\Users\\\\someone\\\\app\\\\threading.py", line 331 in wait
  File "C:\\\\Users\\\\someone\\\\app\\\\jobs.py", line 40 in run

Thread 0x00000b10 (most recent call first):
  File "C:\\\\Users\\\\someone\\\\app\\\\skqt\\\\pagecanvas.py", line 212 in draw
  File "C:\\\\Users\\\\someone\\\\app\\\\skqt_main.py", line 120 in main
'''
where = DW.hang_where(raw)
check("where each thread was: the window's thread first, as file, line and function", where == ["the window's thread:", "pagecanvas.py:212:draw", "skqt_main.py:120:main",
                                                                                               "another thread:", "threading.py:331:wait", "jobs.py:40:run"], where)
check("... with no folder or user name", "someone" not in json.dumps(where) and "Users" not in json.dumps(where))
old = DW.HANG
DW.HANG = 0.4
check("the watchdog starts", DW.start() and os.path.isfile(os.path.join(logs, "hang_raw.txt")))
DW.beat(); time.sleep(0.15); DW.beat()
check("a window that keeps answering leaves nothing", os.path.getsize(os.path.join(logs, "hang_raw.txt")) == 0 and not [e for e in events() if e["area"] == "hang"])
time.sleep(0.9)                                   # the window's thread is away longer than HANG
check("... away too long: where the threads are is written while it is away", os.path.getsize(os.path.join(logs, "hang_raw.txt")) > 0)
DW.beat()
hang = [e for e in events() if e["area"] == "hang"]
check("the next beat records it once, with where it was", len(hang) == 1 and hang[0]["msg"] == "The window stopped answering" and hang[0]["type"] == "ended"
      and any(f.startswith("test_diagwatch4431.py:") for f in hang[0]["where"]), hang)
check("... and the file is empty again", os.path.getsize(os.path.join(logs, "hang_raw.txt")) == 0)
DW.beat(); DW.stop()
check("stopped: the empty file is gone", not os.path.exists(os.path.join(logs, "hang_raw.txt")))
DW.HANG = old

# ---------------------------------------------------------------- the PDF lock covers cleanup closes
import pdflock
pdflock.install()
import pypdfium2 as pdfium, pypdfium2.raw as raw_mod
calls = []
for name in ("FPDF_ClosePage", "FPDF_CloseDocument"):
    inner = getattr(raw_mod, name).__wrapped__

    def mk(fn, name):
        def w(*a, **k):
            calls.append((name, pdflock.LOCK._is_owned()))
            return fn(*a, **k)
        return w
    setattr(raw_mod, name, pdflock._wrap(mk(inner, name)))
doc = pdfium.PdfDocument(os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Program_Manual.pdf"))
page = doc[0]
del page; gc.collect()
check("a page closed by Python's cleanup is closed inside the lock", calls == [("FPDF_ClosePage", True)], calls)
del doc; gc.collect()
check("... and a document too", calls[-1] == ("FPDF_CloseDocument", True), calls)
import skqt.acrfast as AF, skqt.matrixsave as MS
check("background saving is on again (ST52)", AF.THREADED is True and MS.THREADED is True)
diag.shutdown()
print(f"DIAGWATCH 4431 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
