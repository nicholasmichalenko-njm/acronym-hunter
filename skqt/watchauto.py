"""The effort's own folder, watched (4.25.1; Nicholas 2026-11-12 16:49 and 17:08, answers 8 and 9). A file dropped into
the effort's folder is added to Documents by itself: one of our own documents, kept for reference, where it sits (it is
not copied anywhere), in any kind of file. A line says what came in. The customer's folder keeps its table (a customer
document needs its type and initial), and so do the folders a person chose to watch.

Left out of the effort's folder: our volumes, Response Setup, Exports, Redlines, Deleted (the Trash), the app's own
data, and the files beside the effort list. What was already in the folder the first time it is checked is left alone.
Rules only (No AI); nothing leaves the PC."""
import os

import diag


def where(win):
    """{"effort_root", "skip", "not_in"} for watch.check; {} with no effort open or when it cannot be worked out."""
    try:
        return _where(win)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return {}


def _where(win):
    if getattr(win, "ws", None) is None or not win.effort_path:
        return {}
    import effortfolders as EF
    import doctrash as T
    root = EF.root(win.effort_path)
    if not root or not os.path.isdir(root):
        return {}
    info = win.efforts.get(win.effort_name) or {}
    skip = [EF.folder(win.effort_path, k, make=False) for k in ("volumes", "setup", "exports", "redlines")]
    skip += [info.get("volumes_dir") or "", T.folder(win.ws), os.path.join(root, T.VISIBLE)]
    skip = [s for s in skip if s and os.path.normcase(os.path.abspath(s)) != os.path.normcase(os.path.abspath(root))]
    return {"effort_root": root, "skip": skip, "not_in": [root, os.path.dirname(os.path.abspath(win.effort_path))]}


class _Same(dict):
    """The same choice for every file (the page's add takes choices by file name)."""

    def get(self, _name, _default=None):
        return dict(self)


def came_in(win, found):
    """Add the files that came into the effort's folder, by themselves. Returns the paths it started on ([] when
    there are none, or the page is busy: the next check finds them again). A file tried once this session and not
    added is offered in the strip instead, so nothing is tried over and over."""
    auto = list((found or {}).get("auto") or [])
    if not auto or win.ws is None:
        return []
    tried = win.__dict__.setdefault("_wa_tried", set())
    fresh = [(p, c) for p, c in auto if os.path.normcase(p) not in tried]
    stale = [(p, c) for p, c in auto if os.path.normcase(p) in tried]
    if stale:
        found["new"] = list(found.get("new", [])) + stale
    found["auto"] = []
    if not fresh:
        return []
    page = win.library_page
    if page.lib is None or page.running():
        return []
    import watch as WA
    paths = [p for p, _c in fresh]
    tried.update(os.path.normcase(p) for p in paths)
    rel = WA.relative_folders(paths, win.ws.root, win.watch_customer_dir(), where(win).get("effort_root", ""))
    names = ", ".join(os.path.basename(p) for p in paths[:4]) + ("..." if len(paths) > 4 else "")
    win.last_came_in = (f"{len(paths)} file(s) came into the effort's folder and " + ("was" if len(paths) == 1 else "were")
                        + f" added to Documents for reference: {names}")
    win.status(win.last_came_in)
    diag.activity("qt_watch_came_in", n=len(paths))
    got = page.add(paths, folders=rel, category=WA.AUTO, choices=_Same(role="reference"), edited="version")
    return paths if got is not None else []
