"""Shred > Requirements (3.55.0, decisions 1 to 3 in claude/stationkeeper-shred-compare-decisions-2026-11-04.md): one
file in, every requirement out, with no matrix to set up. The same reader as Review (compliance.extract), each row
labelled by kind from where it sits and its words: Requirement (Section C and other statements of need), Instruction
(L) (Section L and format rules), Evaluation (M), SOW task (a statement of work). Export a draft compliance matrix
(Excel); File to an effort reads the file into that effort's Review. Rules only; nothing leaves the PC.

shred(path) -> {"file", "rows": [{id, kind, section, title, page, words, text, loc, suggest}], "counts": {kind: n}}
export(result, path) -> rows written."""
import os, re

KINDS = ("Requirement", "Instruction (L)", "Evaluation (M)", "SOW task")
COLUMNS = ("ID", "Kind", "Section", "Section title", "Page", "Words", "Requirement", "Where", "Suggested")


def kind_of(it, file_kind=""):
    t = it.get("type") or ""
    sec = (it.get("section") or "").upper()
    if t in ("Instruction", "Format") or sec.startswith("L"):
        return KINDS[1]
    if t == "Evaluation" or sec.startswith("M"):
        return KINDS[2]
    if t == "SOW" and (file_kind == "SOW" or re.match(r"^\d", sec)):
        return KINDS[3]
    return KINDS[0]


def shred(path):
    import app_gui as A
    import compliance as C
    name = os.path.basename(path)
    items = C.extract([(name, A.typed_chunks(path))], every=False)
    fk = C.file_kind(name)
    rows = []
    for it in items:
        if it.get("suggest") not in ("Keep", "Review") or it.get("type") in ("Heading", "Context"):
            continue
        rows.append({"id": it.get("id", ""), "kind": kind_of(it, fk), "section": it.get("section", ""),
                     "title": it.get("section_title", ""), "page": it.get("page") or "", "words": it.get("modal", ""),
                     "text": " ".join(it.get("text", "").split()), "loc": it.get("loc", ""), "suggest": it.get("suggest", "")})
    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS}
    return {"file": path, "rows": rows, "counts": counts}


def export(result, path):
    """The draft compliance matrix: one row per requirement, the columns a matrix starts from."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Requirements"
    ws.append(list(COLUMNS))
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3A5F")
    for r in result["rows"]:
        ws.append([r["id"], r["kind"], r["section"], r["title"], r["page"], r["words"], r["text"], r["loc"], r["suggest"]])
    for col, w in zip("ABCDEFGHI", (12, 16, 10, 28, 7, 12, 80, 40, 10)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{max(2, ws.max_row)}"
    about = wb.create_sheet("About")
    for line in (["File", os.path.basename(result["file"])], ["Requirements", len(result["rows"])],
                 *[[k, n] for k, n in result["counts"].items()],
                 ["Note", "A draft from Stationkeeper's quick shred. File it to an effort to decide each one in Review."]):
        about.append(line)
    wb.save(path)
    return len(result["rows"])
