"""One PDF reader at a time (4.5.0). PDFium is not thread-safe: the background extraction (Shred, 4.2.0) and the page on
screen (Shred's page, Fix text, Changes) reading PDFs at the same moment could crash the app. install() wraps every
PDFium function in pypdfium2.raw with one lock, so each call runs alone. pypdfium2's own helpers look the functions up
on that module at each call, so the documents, pages, text and pictures all go through it. Calls are short, so the
screen stays responsive while a long extraction runs. Nothing leaves the PC."""
import threading

LOCK = threading.RLock()
_done = False


def _wrap(fn):
    def locked(*a, **k):
        with LOCK:
            return fn(*a, **k)
    locked.__name__ = getattr(fn, "__name__", "pdfium")
    locked.__wrapped__ = fn
    for attr in ("argtypes", "restype"):
        if hasattr(fn, attr):
            try:
                setattr(locked, attr, getattr(fn, attr))
            except (AttributeError, TypeError):
                pass
    return locked


def install():
    """Wrap pypdfium2.raw's FPDF functions once. Returns how many were wrapped (0 the second time)."""
    global _done
    if _done:
        return 0
    import pypdfium2.raw as raw
    n = 0
    for name in dir(raw):
        if not name.startswith(("FPDF", "FORM_", "FPDFText", "FPDFPage", "FPDFBitmap")):
            continue
        fn = getattr(raw, name)
        if callable(fn) and not isinstance(fn, type) and not hasattr(fn, "__wrapped__"):
            setattr(raw, name, _wrap(fn))
            n += 1
    _done = True
    return n
