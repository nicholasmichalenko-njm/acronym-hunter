"""Leaving a requirement out of the matrix (4.3.0; claude/stationkeeper-releases-4.3-to-4.5-decisions-2026-11-10.md,
decisions 2 and 3). On Matrix & Outline > Place, a Requirement, Instruction or Deliverable can be left out of the
matrix with a reason (and an optional note), kept on the piece (the matrix workbook's Left out column) and in its log.
The Matrix tab and its export show placed pieces only; left-out pieces and their reasons go on their own sheet.
Rules only (No AI); nothing leaves the PC."""

REASONS = ("Covered elsewhere", "Duplicate", "Not ours to answer", "Information only", "Other")
FIELD = "left_out"


def text(reason, note=""):
    note = " ".join((note or "").split())
    return f"{reason}: {note}" if note else reason


def leave_out(M, rows, reason, note="", log=None):
    """Leave the pieces out of the matrix with this reason. Returns how many changed."""
    if reason not in REASONS:
        raise ValueError(reason)
    if reason == "Other" and not (note or "").strip():
        raise ValueError("Other needs a note")
    t = text(reason, note)
    n = 0
    for it in rows:
        if it.get(FIELD) != t:
            it[FIELD] = t
            it["map"] = ""
            n += 1
            if log is not None:
                log(it.get("id", ""), f"left out of the matrix: {t}")
    if n and hasattr(M, "pending"):
        M.pending = True
    return n


def put_back(M, rows, log=None):
    n = 0
    for it in rows:
        if it.get(FIELD):
            it[FIELD] = ""
            n += 1
            if log is not None:
                log(it.get("id", ""), "back in the matrix")
    if n and hasattr(M, "pending"):
        M.pending = True
    return n


def is_out(it):
    return bool(it.get(FIELD))


def left_out(M):
    """[(piece, reason)] in order."""
    return [(it, it[FIELD]) for it in M.items if it.get(FIELD)]
