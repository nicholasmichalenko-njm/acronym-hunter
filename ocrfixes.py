"""Fixes for misread text in pictures (3.51.0, brought back into the main app): "KSF > KSE", applied every time a picture
is read on this PC, for every effort (app_gui reads config/ocr_corrections.csv at each scan). Not training: training
(the Training app's Trainer) makes the reader better; a fix corrects one reading the same way every time.

rows() / add(wrong, right) / update(i, wrong, right, note) / remove(indexes) / undo()
Every change keeps the list as it was first, so Undo puts back the last change. Rules only; nothing leaves the PC."""
import os

import app_gui as A


def _undo_path():
    return A.OCR_FIXES_FILE + ".undo.csv"


def rows():
    """[[misread, correct, note]]."""
    return A.read_ocr_fix_rows()


def _write(new):
    old = rows()
    os.makedirs(A.CONFIG_DIR, exist_ok=True)
    import csv
    with open(_undo_path(), "w", newline="", encoding=A.CSV_WRITE_ENCODING) as f:
        w = csv.writer(f); w.writerow(["Misread", "Correct", "Note"]); w.writerows(old)
    A.write_ocr_fix_rows(new)


def add(wrong, right, note=""):
    """Adds (or replaces) the fix for a misread. Returns the rows."""
    wrong, right = " ".join(str(wrong).split()), " ".join(str(right).split())
    if not wrong or not right or wrong == right:
        return rows()
    new = [r for r in rows() if r[0] != wrong] + [[wrong, right, note]]
    _write(new)
    return new


def update(i, wrong, right, note=""):
    new = rows()
    if 0 <= i < len(new):
        new[i] = [" ".join(str(wrong).split()), " ".join(str(right).split()), note]
        _write(new)
    return new


def remove(indexes):
    keep = [r for k, r in enumerate(rows()) if k not in set(indexes)]
    _write(keep)
    return keep


def undo():
    """Puts back the list as it was before the last change. Returns True when there was one."""
    p = _undo_path()
    if not os.path.isfile(p):
        return False
    old = []
    for r in A.read_csv_rows(p):
        old.append([(r.get("Misread") or "").strip(), (r.get("Correct") or "").strip(), (r.get("Note") or "").strip()])
    A.write_ocr_fix_rows(old)
    os.remove(p)
    return True
