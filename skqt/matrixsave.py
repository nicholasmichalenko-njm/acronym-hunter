"""The matrix saved without stopping the window (4.30.4, the scale pass after Nicholas's 700-page document). Two seconds
after the last change the whole matrix workbook is written. With 4,200 pieces that took 12 seconds on the window's own
thread, so the window froze every time a person paused. Now the timer's save copies the matrix as it stands and writes
that copy on another thread; the status line says Saving the matrix, then nothing. The window keeps answering while
it is written, more slowly (both threads share Python's one lock), where before it did not answer at all. A change made while it is written
is a new wait and is saved by the next one. Closing, switching efforts and Save now still write at once, after waiting
for a write under way (settle), so the newest is always the last on disk. Rules only (No AI); nothing leaves the PC."""
import copy
import pickle

from PySide6.QtCore import QThread

import diag


SAVING = "Saving the matrix..."


class _Saver(QThread):
    def __init__(self, win, clone):
        super().__init__(win)
        self.clone, self.result = clone, "error"

    def run(self):
        try:
            self.clone.save()
            self.result = "ok"
        except PermissionError:
            self.result = "locked"
        except Exception:  # noqa: BLE001
            diag.swallowed()
            self.result = "error"


def _blob(M):
    """The matrix as it stands, without its saved mark: two of these are equal when nothing changed between them."""
    return pickle.dumps({k: v for k, v in vars(M).items() if k != "pending"}, pickle.HIGHEST_PROTOCOL)


def settle(win):
    """Wait for a write under way and finish what follows it (before a save on this thread, a close, another effort)."""
    t = getattr(win, "_matrix_saver", None)
    if t is not None and t.isRunning():
        t.wait()
    if t is not None and not getattr(t, "handled", True):
        _done(win, t)


def soon(win):
    """The timer's save. Returns the thread, or None when it saved here or had nothing to save."""
    win.save_timer.stop()
    r = win.review
    if r is None or not r.M.pending:
        win.title()
        return None
    t = getattr(win, "_matrix_saver", None)
    if t is not None and t.isRunning():
        win.save_timer.start()                           # one write at a time: this change waits for the next
        return None
    M = r.M
    if not win.safety.before_save(M):
        win.title()
        return None
    try:
        blob = _blob(M)
        clone = copy.copy(M)
        clone.__dict__ = dict(pickle.loads(blob), pending=True)
    except Exception:  # noqa: BLE001  something in it cannot be copied: saved here, as before
        diag.swallowed()
        return win.save_now()
    t = win._matrix_saver = _Saver(win, clone)
    t.handled, t.M, t.blob = False, M, blob              # the matrix stays "not saved yet" until this is on disk
    t.finished.connect(lambda: _done(win, t))
    win.status(SAVING)
    t.start()
    return t


def _done(win, t):
    if getattr(t, "handled", True):
        return
    t.handled = True
    M = t.M
    same = win.review is not None and win.review.M is M
    if t.result == "ok":
        try:
            M.pending = _blob(M) != t.blob               # saved, unless it changed while it was written
            if same and not M.pending:
                win.safety.saved(M.path)                 # clears the recovery copy; a dated copy now and then
            elif same:
                win.safety.loaded(M.path)                # changed since: the newer recovery copy stays for the next save
            try:
                __import__("matrixhistory").keep(M.path)
            except Exception:
                diag.swallowed()
            if same:
                win.fill_search()
                if win.statusBar().currentMessage() == SAVING:
                    win.statusBar().clearMessage()
        except Exception:
            diag.swallowed()
    else:
        M.pending = True
        if same:
            win.status("The matrix is open in Excel: close it there, and it is saved again in two seconds."
                       if t.result == "locked" else "The matrix could not be saved.")
            if t.result == "locked":
                win.save_timer.start()
    if same:
        if M.pending and t.result == "ok":
            win.save_timer.start()
        win.title()
