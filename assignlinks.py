"""Assign: each kept requirement and evaluation criterion linked to the section of the outline that answers it
(4.66.0; Nicholas 2026-11-24 "Start there", to the Matrix page as three views by job: Assign, Check, Matrix).

This is the list and the four things done to it; the links themselves are the ones the app has always kept (a
piece's Outline column and its extra copies, through setupdoc.place, add_section and unplace), so the matrix, the
setup, Place on the customer's page and the crosswalk all read what is assigned here. Standard library only."""
import compliance as C
import setupdoc as SD

KINDS = ("Requirement", "Evaluation")
NAMES = {"Requirement": "Requirement", "Evaluation": "Evaluation criterion"}
# 4.68.0: where a piece stands in the draft, set by a person and never by the app. Kept in the piece's own Compliance
# status (the matrix's column of that name), so nothing new is saved: "" is Not started.
MARKS = (("", "Not started"), ("Drafted", "Drafted"), ("Addressed", "Addressed"))
DONE = "Addressed"


def mark_of(it):
    return (it.get("status") or "").strip()


def mark_name(it):
    return mark_of(it) or "Not started"


def set_mark(M, ids, mark):
    """Each piece's mark becomes mark ('' for Not started). Returns how many changed."""
    by = SD.by_id(M)
    mark = (mark or "").strip()
    n = 0
    for i in ids:
        it = by.get(i)
        if it is not None and mark_of(it) != mark:
            it["status"] = mark
            if hasattr(M, "log"):
                M.log(i, f"status: {mark or 'Not started'}")
            n += 1
    return n


def pieces(M):
    """Every kept requirement and evaluation criterion, once, in matrix order."""
    seen, out = set(), []
    for it in SD.all_items(M):
        if SD.kind_of(it) in KINDS and it["id"] not in seen:
            seen.add(it["id"]); out.append(it)
    return out


def ref_of(it):
    """Where the piece is in the customer's documents, short: 'L.4.1' or the file's name."""
    return it.get("section") or it.get("num") or it.get("file") or ""


def rows(M, show="unplaced", kind="", find=""):
    """The list. show: 'unplaced', 'all', or a section's label (what is assigned to it). kind: '' or one of KINDS.
    find: words in the text or the reference. Each row: {id, ref, text, kind, sections, suggested}."""
    out = []
    words = [w for w in (find or "").lower().split() if w]
    for it in pieces(M):
        k = SD.kind_of(it)
        if kind and k != kind:
            continue
        secs = SD.item_sections(M, it)
        if show == "unplaced" and secs:
            continue
        if show not in ("unplaced", "all") and show not in secs:
            continue
        text = it.get("text", "")
        if words and not all(w in (text + " " + ref_of(it)).lower() for w in words):
            continue
        sug = ""
        if not secs:
            try:
                sug = C.suggest_map(it, M.outline)[0] or ""
            except Exception:  # noqa: BLE001
                sug = ""
        out.append({"id": it["id"], "ref": ref_of(it), "text": text, "kind": k, "sections": secs, "suggested": sug, "mark": mark_name(it)})
    return out


def counts(M):
    """({section label: pieces assigned}, pieces not assigned, pieces in all)."""
    per, un, n = {}, 0, 0
    for it in pieces(M):
        n += 1
        secs = SD.item_sections(M, it)
        un += 0 if secs else 1
        for lab in secs:
            per[lab] = per.get(lab, 0) + 1
    return per, un, n


def assign(M, ids, label):
    """Each piece's section becomes label (a piece already there is left). Returns how many moved or were placed."""
    by = SD.by_id(M)
    n = 0
    for i in ids:
        it = by.get(i)
        if it is None or not label or it.get("map") == label:
            continue
        if label in SD.item_sections(M, it):                 # it was an extra copy here: make this its section
            SD.unplace(M, i, label)
        SD.place(M, i, label)
        n += 1
    return n


def also(M, ids, label):
    """Each piece is in label as well as where it is. Returns how many were added."""
    by = SD.by_id(M)
    n = 0
    for i in ids:
        it = by.get(i)
        if it is None or not label:
            continue
        if not SD.item_sections(M, it):
            SD.place(M, i, label); n += 1
        elif SD.add_section(M, it, label):
            n += 1
    return n


def take_out(M, ids, label=""):
    """Each piece leaves label, or every section it is in when no label is given. Returns how many links went."""
    by = SD.by_id(M)
    n = 0
    for i in ids:
        it = by.get(i)
        if it is None:
            continue
        for lab in ([label] if label else list(SD.item_sections(M, it))):
            if lab in SD.item_sections(M, it):
                SD.unplace(M, i, lab); n += 1
    return n


def take_suggestions(M, ids=None):
    """Every piece not assigned (or the ones named) goes to the section suggested for it, when there is one. Returns
    how many were placed."""
    want = set(ids) if ids is not None else None
    n = 0
    for r in rows(M, "unplaced"):
        if r["suggested"] and (want is None or r["id"] in want):
            SD.place(M, r["id"], r["suggested"]); n += 1
    return n


# ---------------------------------------------------------------- 4.67.0: Check, what is left to link
def gaps(M):
    """What Assign has left: {"requirements": rows not assigned, "criteria": rows not assigned, "empty": [labels of
    sections that hold nothing, in themselves or in any section under them]}. A volume's own heading, and the parts
    Word builds (a table of contents, a divider), are not sections to fill."""
    un = rows(M, "unplaced")
    per, _un, _n = counts(M)
    try:
        _mode, _name, heads = SD.volumes_of(M)
    except Exception:  # noqa: BLE001
        heads = []
    heads = set(heads or [])
    out, o = [], list(M.outline)
    for i, e in enumerate(o):
        lab = C.outline_label(e)
        if lab in heads or e.get("kind") in ("element", "divider", "reserve") or str(e.get("num", "")).lower().startswith("volume"):
            continue
        n = per.get(lab, 0)
        lv = e.get("level", 1)
        for f in o[i + 1:]:
            if f.get("level", 1) <= lv:
                break
            n += per.get(C.outline_label(f), 0)
        if not n:
            out.append(lab)
    return {"requirements": [r for r in un if r["kind"] == "Requirement"], "criteria": [r for r in un if r["kind"] == "Evaluation"],
            "empty": out, "open": [r for r in rows(M, "all") if r["sections"] and r["mark"] != DONE]}   # 4.68.0: assigned, not yet Addressed


def gap_count(M):
    g = gaps(M)
    return len(g["requirements"]) + len(g["criteria"]) + len(g["empty"]) + len(g["open"])
