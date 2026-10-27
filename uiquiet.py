"""Smooth moving and resizing (2.47.0). Rules only (No AI).

Dragging a window edge sends a stream of size events. Work done on each one (rewrapping text, redrawing a page or a
picture) piles up and the window stutters or appears to freeze. debounced() does that work once, a moment after the
size stops changing; busy() tells the app's regular tick to wait while the window is being moved or resized."""
import time

_until = [0.0]
SETTLE_S = 0.6


def debounced(widget, fn, ms=120):
    """An event handler that calls fn(last event) once, ms after the events stop."""
    state = {"job": None, "e": None}

    def fire():
        state["job"] = None
        try:
            if widget.winfo_exists():
                fn(state["e"])
        except Exception:
            pass

    def handler(e):
        state["e"] = e
        if state["job"] is not None:
            try:
                widget.after_cancel(state["job"])
            except Exception:
                pass
        try:
            state["job"] = widget.after(ms, fire)
        except Exception:
            pass
    return handler


def watch(root):
    """Note when the main window moves or changes size (cheap: one time stamp)."""
    last = {"geo": None}

    def on(e):
        if e.widget is root:
            geo = (e.x, e.y, e.width, e.height)
            if geo != last["geo"]:
                last["geo"] = geo
                _until[0] = time.time() + SETTLE_S
    root.bind("<Configure>", on, add="+")


def busy():
    """Whether the main window is being moved or resized right now."""
    return time.time() < _until[0]
