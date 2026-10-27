"""Background work that never touches the window (2.47.0). Rules only (No AI).

Python's cycle collector can run in whichever thread happens to allocate memory. If it ran in a background thread it
could free window objects there (a font, an image), and Tk must only ever be called from the window's own thread: that
can freeze or crash the app. So while background work runs, the cycle collector is paused (ordinary freeing goes on as
usual); the window's thread collects first and turns it back on when the work is done (settle, called every tick)."""
import gc, threading

_live = []


def start(fn, name="stationkeeper-work"):
    """Run fn() in a background thread. Call from the window's thread. Returns the thread."""
    gc.collect()
    gc.disable()
    t = threading.Thread(target=fn, name=name, daemon=False)
    _live.append(t)
    t.start()
    return t


def settle():
    """From the window's thread: forget finished work; when none is left, turn the cycle collector back on."""
    _live[:] = [t for t in _live if t.is_alive()]
    if not _live and not gc.isenabled():
        gc.enable()


def wait(t, timeout=None):
    """Wait for one piece of work (from the window's thread), then settle."""
    if t is not None:
        t.join(timeout)
    settle()
