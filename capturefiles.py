"""Capture files (3.41.0): read a capture file (call notes, a capture plan, a competitor brief, the team's intel) into
numbered paragraphs, so the words worth keeping become captures with their source: the file, its page (PDF) and the
heading they sit under. Word (.docx), PDF (its own text) and plain text are read; nothing is changed and nothing leaves
the PC. Rules only (No AI)."""
import os, re

EXTS = (".docx", ".pdf", ".txt", ".md")


def _docx(path):
    import docx
    out, heading = [], ""
    for k, p in enumerate(docx.Document(path).paragraphs, 1):
        t = " ".join((p.text or "").split())
        if not t:
            continue
        sname = (p.style.name if p.style is not None else "") or ""
        if sname.lower().startswith("heading") or sname.lower() == "title":
            heading = t
        out.append({"page": "", "para": str(k), "heading": heading, "text": t})
    return out


def _pdf(path):
    import pypdfium2 as pdfium
    out, doc = [], pdfium.PdfDocument(path)
    try:
        for i in range(len(doc)):
            tp = doc[i].get_textpage()
            try:
                text = tp.get_text_range() or ""
            finally:
                tp.close()
            k = 0
            for block in re.split(r"\n\s*\n|\r\n\s*\r\n", text):
                t = " ".join(block.split())
                if t:
                    k += 1
                    out.append({"page": str(i + 1), "para": str(k), "heading": "", "text": t})
    finally:
        doc.close()
    return out


def _txt(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    out = []
    for k, block in enumerate([b for b in re.split(r"\n\s*\n", text) if b.strip()], 1):
        out.append({"page": "", "para": str(k), "heading": "", "text": " ".join(block.split())})
    return out


def read(path):
    """[{"page", "para", "heading", "text"}] for each paragraph with words; [] for a file it cannot read."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".docx":
            return _docx(path)
        if ext == ".pdf":
            return _pdf(path)
        if ext in (".txt", ".md"):
            return _txt(path)
    except Exception:  # noqa: BLE001  a damaged file reads as nothing
        return []
    return []


def capture(rec, bin_id, path, paras, sections=(), one_each=True, note="", who=None):
    """The chosen paragraphs as captures in a bin, each part with the file, page, paragraph and heading. one_each: one
    capture per paragraph (else one capture holding them all). Returns the new capture ids."""
    import excerpts as EX
    name = os.path.basename(path)
    parts = [EX.part_from_file(name, p["text"], page=p.get("page", ""), para=p.get("para", ""), heading=p.get("heading", "")) for p in paras]
    groups = [[x] for x in parts] if one_each else [parts]
    ids = []
    for g in groups:
        xid = EX.add(rec, bin_id, g, note=note, sections=sections, who=who, source="intel")
        if xid:
            ids.append(xid)
    return ids
