"""4.12.0: a worker thread is never dropped while its run() may still be returning. Its last signal reaches the window
before run() returns; dropping the only reference then destroys a running QThread and Windows ends the app (the Acronym
Finder test crash of 4.10.0 and 4.11.0, caught in Full Text). Every place that lets a worker go uses progress.let_go
(or waits, or keeps it until finished). Static check over skqt, plus let_go itself on a real thread."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

NAMES = ("worker", "loader", "_exact_worker")


def run():
    bad = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "skqt"))):
        if not fn.endswith(".py"):
            continue
        src = open(os.path.join(ROOT, "skqt", fn), encoding="utf-8").read()
        if "QThread" not in src and "JobWorker" not in src and "Worker(" not in src:
            continue
        func = ""
        for i, line in enumerate(src.splitlines(), 1):
            m = re.match(r"\s*def (\w+)\(", line)
            if m:
                func = m.group(1)
            for n in NAMES:
                if re.search(rf"self\.{re.escape(n)} = None\b", line) and func not in ("__init__", "abandon"):
                    bad.append(f"{fn}:{i} ({func}): self.{n} = None")
    assert not bad, "a worker dropped without let_go:\n" + "\n".join(bad)
    from PySide6.QtCore import QCoreApplication, QThread
    import time
    app = QCoreApplication.instance() or QCoreApplication([])
    from skqt import progress as PR

    class Slow(QThread):
        def run(self):
            time.sleep(0.3)

    w = Slow(); w.start()
    assert PR.let_go(w) is None and w in PR._KEEP
    t = time.time()
    while w in PR._KEEP and time.time() - t < 10:
        app.processEvents(); time.sleep(0.02)
    assert w not in PR._KEEP and w.isFinished()
    idle = Slow()
    assert PR.let_go(idle) is None and idle not in PR._KEEP      # never started: nothing to keep
    assert PR.let_go(None) is None
    print("test_threads4120: all checks passed")


if __name__ == "__main__":
    run()
