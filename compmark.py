"""Shred in passes, the Compliance pass (4.72.0; UX decisions 164, 167, 168, 170, 179; the brief
claude/stationkeeper-ux-build-brief-addition-shred-in-passes-2026-11-19.md). Three kinds, by who the sentence is about:
Work Requirement (SOW), Response Instruction (L), Evaluation Criterion (M). They are the piece types the shred already
keeps (requirement, instruction, evaluation), so a mark is a row of the matrix at once and nothing new is saved for it.
This module keeps what is the pass's own: Not needed and For the setup for a piece (the matrix's setup, "comp_marks"),
the documents a person said hold nothing of this kind ("comp_none"), each document's state, the section the app
suggests, and the pieces still to look at. Rules only (No AI); nothing leaves the PC. Standard library only."""
import compliance as C
import outline_ops as OO
import setupdoc as SD
import shredtypes as ST

KINDS = (("requirement", "Work Requirement (SOW)"), ("instruction", "Response Instruction (L)"),
         ("evaluation", "Evaluation Criterion (M)"))
KEYS = tuple(k for k, _n in KINDS)
NAME = dict(KINDS)
NOT_NEEDED, FOR_SETUP = "x", "s"


def marks(M):
    return SD.setup_of(M).setdefault("comp_marks", {})


def kinds_of(it):
    """The pass's kinds a piece has, in the bar's order."""
    got = ST.types_of(it)
    return [k for k in KEYS if k in got]


def state(M, it):
    """"x" (Not needed), "s" (For the setup) or "" for a piece in this pass."""
    return "" if kinds_of(it) else marks(M).get(it.get("id"), "")


def sections_of(M, it):
    return SD.item_sections(M, it)


def suggested_section(M, it):
    """The section of our outline the app suggests for a piece, or "" (no outline, or nothing alike)."""
    if not M.outline:
        return ""
    try:
        return C.suggest_map(it, M.outline)[0] or ""
    except Exception:  # noqa: BLE001
        return ""


def not_needed(M, it, on=True):
    """Looked at; nothing for this pass. It leaves the pass's next and can be reopened (on=False)."""
    iid = it.get("id")
    if on:
        marks(M)[iid] = NOT_NEEDED
    elif marks(M).get(iid) == NOT_NEEDED:
        marks(M).pop(iid)
    M.pending = True
    return bool(on)


def for_setup(M, it, label):
    """For the setup: the piece goes into a section as text for the author. A piece nobody decided on becomes the
    customer's own (identified, not answered); a decided piece keeps its decision and is put there too."""
    if OO.index_of(M, label) < 0:
        return False
    if not it.get("decision"):
        C.assign_customer(M.items, [it])
        SD.clear_sections(M, it)
    if label not in SD.item_sections(M, it):
        SD.place(M, it.get("id"), label, copy=bool(it.get("map")))
    if not kinds_of(it):
        marks(M)[it.get("id")] = FOR_SETUP
    M.log(it.get("id", ""), f"Compliance: for the setup, under {label}")
    M.pending = True
    return True


def open_rows(M, file):
    """The pieces of a document this pass has not dealt with: no kind, no decision, not set aside here; headings out."""
    got = marks(M)
    return [it for it in M.items if it.get("file") == file and it.get("type") != "Heading" and not kinds_of(it)
            and not it.get("decision") and it.get("id") not in got and not ST._keys(it.get(ST.FIELD))]


def count(M):
    return sum(1 for it in M.items if kinds_of(it))


def docs(M):
    """[{"file", "finds", "none", "state"}] for every customer document: Not looked at; Has finds (count); Nothing of
    this kind here (said by a person)."""
    files, finds = [], {}
    for it in M.items:
        f = it.get("file", "")
        if f and f not in files:
            files.append(f)
        if kinds_of(it):
            finds[f] = finds.get(f, 0) + 1
    none = set(SD.setup_of(M).get("comp_none") or [])
    out = []
    for f in files:
        n = finds.get(f, 0)
        out.append({"file": f, "finds": n, "none": f in none and not n,
                    "state": f"Has finds ({n})" if n else ("Nothing of this kind here" if f in none else "Not looked at")})
    return out


def set_none(M, file, on=True):
    S = SD.setup_of(M)
    cur = [f for f in (S.get("comp_none") or []) if f != file]
    if on:
        cur.append(file)
    S["comp_none"] = cur
    M.pending = True
    return bool(on)
