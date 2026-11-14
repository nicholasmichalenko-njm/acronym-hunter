"""Deciding thousands of finds without a wait (4.30.3; Nicholas 2026-11-13 16:23: with nearly 2,500 candidates every
"not a term" froze the window). Each decision used to do three whole-effort jobs before the window answered: read and
write the whole session file, build every row of the list again, and work out where each term was found again. Now:

- the session file and the effort list workbook are written a moment after the last decision (SAVE_AFTER), once (on
  another thread when THREADED; from 4.30.4 on the window's own, see THREADED); "Saving your decisions" then "Decisions saved" shows
  beside the tabs. Leaving the page, switching tabs and closing write at once and wait for it. There is no step to
  take. What a crash can lose is the last second and a half of decisions;
- while On the page is showing, the list behind it is not built; it is built when The list is opened;
- when the list is showing, only the rows that changed are drawn again, and a row that left is taken out;
- where a term was found is worked out once and kept until its places change.

Nothing about what is decided, kept or shown changes. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication

SAVE_AFTER = 1500        # milliseconds after the last decision
TYPE_AFTER = 250         # milliseconds after the last key in the search box before the list is filled (0: at once)
FEW = 25                 # rows taken out one by one; more than this and the list is built afresh
# 4.30.4: False until the access violation of 2026-11-13 is understood. The program ended a moment after quick decisions on
# 4.30.3, the first release that wrote on another thread, and the crash record had lost the thread that crashed. Written
# on the window's own thread, the write is a short pause a moment after the last decision, never during one.
THREADED = False
DONE_ON = None
AT_ONCE = False          # tests that read the files straight after a decision turn this on: every save writes there and then


class _Leave(QObject):
    """Leaving or closing the page writes what is waiting."""
    def __init__(self, page):
        super().__init__(page)
        self.page = page

    def eventFilter(self, _o, e):
        if e.type() in (QEvent.Hide, QEvent.Close):
            flush(self.page)
        return False


def watch(page):
    """The page's session saves a moment after the last decision. Safe to call on every fill."""
    s = page.session
    if s is None or getattr(s, "later", None) is not None:
        return s
    if getattr(page, "_save_timer", None) is None:
        page._save_timer = QTimer(page); page._save_timer.setSingleShot(True); page._save_timer.setInterval(SAVE_AFTER)
        page._save_timer.timeout.connect(lambda: _write(page))
        page._leave = _Leave(page); page.installEventFilter(page._leave)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(lambda: flush(page))
    t = page._save_timer

    def later():
        if AT_ONCE or QThread.currentThread() is not page.thread() or not page.isVisible():
            return s.flush()                            # a scan on its own thread, or another page using this session: at once
        w = getattr(page, "_waiting", None)
        if w is not None and w is not s:
            w.flush()                                   # another effort's session was waiting: it is written first
        page._waiting = s                               # the session itself: it is written even if the effort changes
        t.start()
    s.later = later
    return s


class _Saver(QThread):
    """Writes one snapshot of what was waiting. 4.30.4: what follows the write (the line beside the tabs, the marks) runs
    on the window's thread. In 4.30.3 it was connected as a bare function, which Qt runs on the thread that finished:
    the writing thread then touched the window's widgets, and the program could end with an access violation a moment
    after a decision (Nicholas 2026-11-13 20:05)."""
    def __init__(self, page, session, snap):
        super().__init__(page)
        self.page, self.session, self.snap, self.result, self.error = page, session, snap, (False, None), False
        self.finished.connect(self.after, Qt.QueuedConnection)      # this object lives on the window's thread: it runs there

    @Slot()
    def after(self):
        _done(self.page, self.session, self.snap, self.result, self.error)

    def run(self):
        try:
            self.result = type(self.session).write_snapshot(self.snap)
        except Exception:  # noqa: BLE001  the decisions stay in memory and are written at the next save
            import diag
            diag.swallowed()
            self.error = True


def say(page, text):
    """Beside the tabs, where a scan says its progress (left alone while a scan runs)."""
    if page.worker is None and getattr(page, "progress", None) is not None:
        page.progress.setText(text)


def _write(page):
    """The timer: write what is waiting on another thread. A write still running is waited for by trying again."""
    old = getattr(page, "_saver", None)
    if old is not None and old.isRunning():
        page._save_timer.start()
        return None
    s = getattr(page, "_waiting", None)
    page._waiting = None
    snap = s.snapshot() if s is not None else None
    if snap is None:
        return None
    if not THREADED or getattr(page, "save_inline", False):  # on the window's thread: a short pause, said beside the tabs
        say(page, "Saving your decisions...")
        QCoreApplication.processEvents()                     # the line shows before the pause
        try:
            res, err = type(s).write_snapshot(snap), False
        except Exception:  # noqa: BLE001  kept in memory; written at the next save
            import diag
            diag.swallowed()
            res, err = (False, None), True
        _done(page, s, snap, res, err)
        return res
    say(page, "Saving your decisions...")
    t = page._saver = _Saver(page, s, snap)
    t.start()
    return t


def _done(page, s, snap, result, error):
    global DONE_ON
    DONE_ON = QThread.currentThread() is QCoreApplication.instance().thread()                       # tests: True on the window's thread, never the writing one
    did_s, did_l = result
    if error or (snap["session"] is not None and not did_s):
        s.unsaved = True                                    # not written: it waits for the next save
    if snap["list"] is not None:
        if did_l and not getattr(s, "list_unsaved", False) and s.effort is not None:
            s.effort.pending = False
        elif not did_l:
            s.list_unsaved = True
    import datetime
    if snap["list"] is not None and did_l is False and not error:
        say(page, "The effort list is open in Excel: your decisions are kept here and are written when it is closed.")
    elif error:
        say(page, "Your decisions are kept here; writing them will be tried again.")
    else:
        say(page, f"Decisions saved {datetime.datetime.now().strftime('%H:%M:%S')}")
    if (s.unsaved if hasattr(s, "unsaved") else False) or getattr(s, "list_unsaved", False):
        if not (snap["list"] is not None and did_l is False):   # Excel holding the list is not tried every second
            page._waiting = s
            page._save_timer.start()


def flush(page):
    """Write now whatever is waiting (leaving, closing, switching tabs, before a scan). Returns True when it wrote."""
    t = getattr(page, "_save_timer", None)
    if t is not None:
        t.stop()
    old = getattr(page, "_saver", None)
    if old is not None and old.isRunning():
        old.wait()                                          # a write under way finishes first, so the newest is last
    s = getattr(page, "_waiting", None) or page.session
    page._waiting = None
    return bool(s is not None and s.flush())


def light(page):
    """True when the list need not be built now: a decision was made on On the page (from_page, set by its decided()),
    which is what is showing, so only the counts and the page are drawn and the list is built when it is opened. Every
    other fill (a search, a filter, a scan) builds the list as before."""
    watch(page)
    s = page.session
    if (not getattr(page, "from_page", False) or getattr(page, "tool", False) or s is None or not s.results or page.worker is not None
            or not getattr(page, "tab_set", False) or page.tabs.currentIndex() != 0 or not page.onpage.isVisible()):
        page.list_stale = False
        return False
    page.list_stale = True
    from . import acrlayout as AL
    AL.fill_counts(page)                                # the counts, the tabs and the page shown (acrtabs.after_fill)
    return True


def typed(page):
    """The search box changed: the list is filled once, a moment after the last key, not once per key (with thousands
    of terms each fill is a visible wait)."""
    if TYPE_AFTER <= 0:
        return page.fill()
    t = getattr(page, "_type_timer", None)
    if t is None:
        t = page._type_timer = QTimer(page); t.setSingleShot(True); t.timeout.connect(page.fill)
    t.start(TYPE_AFTER)


def sync_rows(page):
    """The table's rows for page.terms. When the terms are the ones shown before, less some, those rows are taken out
    and the rest keep what is drawn; otherwise every row is drawn again."""
    s = page.session
    page._kinds = repr(sorted((s.doc_kinds() or {}).items())) if s else ""
    old, new = getattr(page, "_row_terms", None), list(page.terms)
    sigs = getattr(page, "_row_sigs", None)
    keep = set(new)
    few = old is not None and len(old) - len(new) <= FEW
    # 4.30.4 (Nicholas 2026-11-13 20:05: typing in the search froze the window, then small windows flashed): each row
    # taken out moved the selection, and each move drew the term's card again. No signal is sent while rows change, and
    # when many go (a search, a filter) the list is built afresh, which is faster than taking them out one by one.
    was = page.table.blockSignals(True)
    try:
        if few and sigs is not None and page.table.rowCount() == len(old) and [t for t in old if t in keep] == new:
            for i in range(len(old) - 1, -1, -1):
                if old[i] not in keep:
                    page.table.removeRow(i); del sigs[i]
        else:
            page.table.setRowCount(len(new))
            page._row_sigs = [None] * len(new)
    finally:
        page.table.blockSignals(was)
    page._row_terms = new
    return len(new)


def same(page, i, sig):
    """True when row i already shows exactly this (its items are left as they are)."""
    sigs = page._row_sigs
    if sigs[i] == sig and page.table.item(i, 0) is not None:
        return True
    sigs[i] = sig
    return False


def found_in(page, s, term, d):
    """Customer, Internal or Both for a term, kept until its places or the documents' kinds change."""
    cache = page.__dict__.setdefault("_found", {})
    locs = d.get("locations") or []
    key = (len(locs), locs[-1] if locs else "", getattr(page, "_kinds", ""))
    hit = cache.get(term)
    if hit is None or hit[0] != key:
        hit = cache[term] = (key, s.found_in(d))
    return hit[1]
