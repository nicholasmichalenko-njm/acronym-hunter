"""A document's status panel on Documents (4.0.0; canvas "Six Steps", board 1; claude/stationkeeper-six-steps-plan-4.0.md):
click a document and the panel says what has been done to it (its text checked, the shred, the changes from its last
version, whether it feeds the matrix, its text taken as context) and offers one button, its next thing: Check the text,
Review changes, Shred it (4.1.0: extracts it at once), Continue the shred. The right-click menu keeps five things about the file itself (Open,
Set type, Add a newer version, Leave out, Show in folder); the rest of what can be said about a document is under More.
Rules only (No AI); nothing leaves the PC."""
import os

import diag

OK, WARN, NONE = "ok", "warn", "none"


def _verify(page, d):
    """(verified, pages, to look at) for a customer document's latest version, or None when there is no page copy yet."""
    if d.get("category", "customer") != "customer" or not d.get("versions"):
        return None
    try:
        import verifystate as VS
        h = page.host
        path = page.lib.path_of(d["versions"][-1])
        pdf = h.verify_page.pdf_of(path, make=False) if path else None
        if not pdf:
            return None
        c = VS.counts(pdf, VS.Store(h.ws.root), os.path.basename(path))
        return c["verified"], c["pages"], c["look"]
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _changes(page, d):
    """None for a document with one version; else (opened, changes still to decide)."""
    if len(d.get("versions") or []) < 2:
        return None
    try:
        import changereview as CHR
        rv = CHR.Review(page.host.ws.root).load()
        pairs = [p for p in rv.pairs.values() if p.get("name") == d["name"]]
        if not pairs:
            return (False, 0)
        left = 0
        for p in pairs:
            done, n = rv.progress_of(p)
            left += max(0, n - done)
        return (True, left)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return (False, 0)


def _pieces(page, d):
    """(pieces, not sorted) of this document in the shred, or None when it is not extracted (4.1.0)."""
    try:
        R = page.host.review
        f = (d.get("versions") or [{}])[-1].get("file", "")
        items = [it for it in (R.M.items if R is not None else []) if it.get("file") == f and it.get("header") != "Yes"]
        if not items:
            return None
        import shredtypes as ST
        return len(items), sum(1 for it in items if not ST.type_of(it))
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _acros(page, d):
    """(terms found on its pages, to decide), or None before a scan found any there (4.1.0)."""
    try:
        s = page.host.acronym_page.session
        if s is None or not s.results:
            return None
        import acrpages as AG
        f = (d.get("versions") or [{}])[-1].get("file", "")
        terms = {}
        for p in AG.pages(s.results):
            if p["name"] == f:
                terms.update(p["terms"])
        return (len(terms), sum(1 for v in terms.values() if v == "decide")) if terms else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _queued(page, d):
    try:
        import reshred as RS
        return sum(1 for x in RS.Queue(page.host.ws.root).load().open_items() if x.get("doc") == d.get("name"))
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return 0


def status(page, d, st=None):
    """[(what, detail, state)] for one document, state ok, warn or none; and its next thing (label, key) or None."""
    out = []
    lib = page.lib
    v = _verify(page, d)
    if d.get("category", "customer") == "customer":
        if v is None:
            out.append(("Text check", "Not checked yet (its page copy is made when it opens in Text check)", NONE))
        else:
            ver, pages, look = v
            out.append(("Text check", f"{ver} of {pages} pages checked" + (f"; {look} to look at" if look else ""),
                        WARN if look else OK if ver == pages else NONE))
    text, _tone, key = page.review_state(d, st)
    shred = {"unread": ("Not extracted yet", NONE), "needs": (text.replace("Needs reviewing", "In progress"), WARN),
             "reviewed": ("Done", OK), "not_needed": ("Left out", NONE)}[key]
    out.append(("Shred", shred[0], shred[1]))
    pc = _pieces(page, d)                                      # 4.1.0: its pieces and its acros and abs
    if pc is not None:
        out.append(("Pieces", f"{pc[0]} piece(s)" + (f", {pc[1]} not sorted" if pc[1] else ", all sorted"), WARN if pc[1] else OK))
    ac = _acros(page, d)
    if ac is not None:
        out.append(("Acros & Abs", f"{ac[0]} found" + (f", {ac[1]} to decide" if ac[1] else ", all decided"), WARN if ac[1] else OK))
    ch = _changes(page, d)
    if ch is not None:
        opened, left = ch
        out.append(("Changes from its last version", ("Not reviewed yet" if not opened else f"{left} to review" if left else "Reviewed"),
                    WARN if (not opened or left) else OK))
    role = lib.role_of(d)
    out.append(("Feeds the matrix", "Yes (Place decides what goes in)" if role == "matrix" else "No", OK if role == "matrix" else NONE))
    try:
        import ctxdocs as CX
        nt = len(CX.Store(page.host.ws.root).load().of_doc(d["id"]))
    except Exception:  # noqa: BLE001
        nt = 0
    if nt:
        out.append(("Used as context", f"{nt} sentence(s) taken from it in the shred", OK))
    n = len(d.get("versions") or [])
    out.append(("Versions", f"{n} version(s); the latest governs" if n > 1 else "1 version", NONE))
    nxt = None
    if key == "not_needed":                                  # left out: nothing to do until it is put back
        return out, None
    if v is not None and v[2]:
        nxt = (f"Check the text ({v[2]} page(s) to look at)", "verify")
    elif ch is not None and (not ch[0] or ch[1]):
        nxt = ("Review changes" + (f" ({ch[1]} left)" if ch[0] and ch[1] else ""), "compare")
    elif key == "unread":
        nxt = ("Shred it", "read")
    elif _queued(page, d):
        nxt = (f"Re-shred {_queued(page, d)} passage(s)", "reshred")
    elif key == "needs":
        nxt = ("Continue the shred", "assign")
    elif key == "reviewed":
        nxt = ("Open in Shred", "assign")
    return out, nxt


def go_next(page, d, key):
    """The panel's button: open the page its next thing is done on, with this document."""
    h = page.host
    if key == "verify":                                  # 4.2.0: Fix text, in Shred, on this document
        ok = page.read_in_assign(d["id"])
        __import__("skqt.fixtext", fromlist=["x"]).toggle(h.assign_page, True)
        return bool(ok)
    if key == "compare":
        h.go("compare")
        try:
            h.compare_page.open_pair(d["id"])
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return True
    if key == "read":
        if page.lib.role_of(d) == "not_needed":
            return False
        from . import shredpick as SP                # 4.1.0: extracted at once, in the background, then opened in Shred
        h.go("assign")
        return bool(SP.extract(h.assign_page, d["id"]))
    if key == "assign":
        return page.read_in_assign(d["id"])
    if key == "reshred":                                 # 4.1.0: the passages Changes queued
        h.go("assign")
        return __import__("skqt.reshredbar", fromlist=["x"]).open_next(h.assign_page) is not None
    return False


# ------------------------------------------------------------------ the right-click menu: five things about the file
def row_menu(page, at=None, run=True):
    """Open, Set type, Add a newer version, Leave out (or Put back), Show in folder. Returns the menu."""
    from PySide6.QtWidgets import QMenu
    ids = page.selected_ids()
    m = QMenu(page)
    if not ids or page.lib is None:
        return m
    d = page.lib.doc(ids[0])
    m.addAction("Open", lambda: open_file(page, d))
    tm = m.addMenu("Set type")
    for k, n in page.lib.categories():
        a = tm.addAction(n, lambda k=k: page.set_category(k)); a.setCheckable(True); a.setChecked(d.get("category") == k)
    tm.addSeparator()
    tm.addAction("Initial and type...", lambda: page.identity())
    m.addAction("Add a newer version...", lambda: newer_version(page, d))
    out = page.lib.role_of(d) == "not_needed"
    m.addAction("Put it back" if out else "Leave out", lambda: page.set_role("context" if out else "not_needed",
                                                                            why="put back" if out else "left out"))
    m.addAction("Show in folder", lambda: show_in_folder(page, d))
    page._menu = m
    if run and at is not None:
        m.exec(at)
    return m


def path_of(page, d):
    try:
        return page.lib.path_of(d["versions"][-1]) if d and d.get("versions") else ""
    except Exception:  # noqa: BLE001
        return ""


def open_file(page, d):
    p = path_of(page, d)
    if not p or not os.path.isfile(p):
        page.host.status("The original file is not here.")
        return ""
    if not os.environ.get("AH_TEST"):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(p))
    return p


def show_in_folder(page, d):
    p = path_of(page, d)
    folder = os.path.dirname(p) if p else ""
    if not folder or not os.path.isdir(folder):
        page.host.status("Its folder is not here.")
        return ""
    if not os.environ.get("AH_TEST"):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
    return folder


def newer_version(page, d, path=None):
    """Pick the new file; it comes in through the same table as any file, offered as this document's next version."""
    if path is None:
        from PySide6.QtWidgets import QFileDialog
        path, _f = QFileDialog.getOpenFileName(page, f"A newer version of {d['name']}", "")
        if not path:
            return None
    return page.add([path], category=d.get("category", "customer"))
