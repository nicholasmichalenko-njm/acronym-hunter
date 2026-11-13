"""What the scan says while it reads (4.30.3; Nicholas 2026-11-13 16:18 and 16:20: a 700-page file sat at 0% for minutes).
The reader's progress lines pass through here so that every picture it reads is said too: "PDF page 37/700, picture 2/5",
"Reading Word body, picture 12/41". A long page or a file full of pictures then moves the bar while it is read, and a
Word, PowerPoint or Excel file has a position at all. Reading is unchanged: the same pages, pictures and readers in the
same order; only what is reported is new. One scan per thread. Standard library only; nothing leaves the PC."""
import re
import threading
import zipfile

_T = threading.local()
_HAS_PART = re.compile(r"(?:page|slide)\s+\d+\s*/\s*\d+", re.I)
_MEDIA = re.compile(r"/media/[^/]+\.(png|jpe?g|gif|bmp|tiff?|emf|wmf|svg)$", re.I)


def media_count(path):
    """How many pictures an Office file holds (its media folder). 0 when it cannot be told."""
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist() if _MEDIA.search(n))
    except Exception:  # noqa: BLE001  the reader reports a file it cannot open
        return 0


def wrap(cb, path="", ext=""):
    """The callback the reader uses for this file: it forwards every line and remembers the last, so pictures can be
    said against it."""
    _T.cb, _T.base, _T.k = cb, "", 0
    _T.n = media_count(path) if ext in (".docx", ".pptx", ".xlsx") else 0
    _T.per_page = False

    def say(msg):
        _T.base = str(msg).rstrip(". ")
        if _T.per_page:
            _T.k, _T.n = 0, 0
        cb(msg)
    return say


def pictures(n):
    """A PDF page has this many pictures (counted afresh on each page)."""
    _T.per_page, _T.k, _T.n = True, 0, int(n)


def picture():
    """One more picture is about to be read: say which."""
    cb = getattr(_T, "cb", None)
    if cb is None:
        return
    _T.k += 1
    n = _T.n if (_T.per_page or not _HAS_PART.search(_T.base)) else 0
    if n and _T.k > n:
        n = _T.k                                  # a picture used twice: never "13 of 12"
    if _T.base:
        cb(f"{_T.base}, picture {_T.k}" + (f"/{n}" if n else "") + "...")


def done():
    _T.cb = None
