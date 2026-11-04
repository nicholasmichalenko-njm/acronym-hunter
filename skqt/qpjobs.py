"""Measuring Quick Parts' pages in Word, safely (3.49.0): only when a person presses the button, one measuring at a
time, in the background. Every job is kept in RUNNING until it finishes, so nothing can drop a job while Word still
works (before 3.49.0 a second import replaced the first job while it ran, and the app closed). The job only reads; the
pages are kept by the window's thread, in one save, into the library as it is then (never a copy read minutes before)."""
import diag
import templatelib as TL

RUNNING = []          # every job until it finishes; never replaced


def busy():
    return any(w.isRunning() for w in RUNNING)


def why_not():
    import qpmeasure as QM
    if busy():
        return "Word is measuring already. Wait for it to finish, then measure again."
    if not QM.available():
        return "Word on this PC is needed to measure pages."
    return ""


def keep(config_dir, res):
    """The pages Word measured, kept in one save. Returns how many."""
    lib = TL.Library(config_dir)
    n = 0
    with lib.transaction():
        for iid, pages in (res or {}).items():
            if isinstance(pages, int) and pages > 0 and lib.get(iid) is not None:
                lib.set_pages(iid, pages, "measured")
                n += 1
    return n


def measure_now(config_dir, ids, runner, after=None):
    """Tests: Word's answers given; measured and kept here and now."""
    import qpmeasure as QM
    res = QM.measure(TL.Library(config_dir), ids, runner=runner, keep=False)
    keep(config_dir, res)
    if after:
        after(res)
    return res


def start(config_dir, ids, after=None, fn=None):
    """Starts measuring ids in the background. after(result) runs on the window's thread once the pages are kept.
    fn (tests): the job instead of Word. Returns the job, or None (nothing to measure, Word not here, or busy)."""
    import qpmeasure as QM
    if not ids or busy() or (fn is None and not QM.available()):
        return None
    from .progress import JobWorker
    job = fn or (lambda _p, _s: QM.measure(TL.Library(config_dir), list(ids), keep=False))
    w = JobWorker(job)

    def finished(res):
        try:
            if isinstance(res, dict):
                keep(config_dir, res)
            if after:
                after(res if isinstance(res, dict) else {})
        except Exception:  # noqa: BLE001  the pages could not be kept; the library is as it was
            diag.swallowed()

    w.done.connect(finished)
    def gone():
        w.wait(2000)                                    # the thread has ended before the last reference goes
        if w in RUNNING:
            RUNNING.remove(w)

    w.finished.connect(gone)
    RUNNING.append(w)
    diag.activity("quickparts_measure_started", n=len(ids))
    w.start()
    return w
