"""4.22.0: Prepare for redline. Every PDF and picture in Documents can be prepared, one row each, with one button.

Three routes, all from the same reading of the PDF:
- a PDF (or a picture) becomes a Word copy that flows (redlinecopy): its pictures, headers and footers, fonts, tables;
- a PDF with a reviewer's comments becomes that copy with each comment where it was made: a tracked change for a
  cross-out, an insert or a replacement, a Word comment for a highlight or a note (pdfcomments, redlinemarks);
- a PDF's comments go into a Word file you already have (into_word): a dated copy of your file, never the file itself.
A picture or a scanned PDF is read from its page copy with words (ocrpdf), made when it is missing.
Rules only (No AI); nothing leaves the PC."""
import datetime, json, os, shutil

import redlinecopy as RC


def kind(path):
    import ocrpdf
    low = (path or "").lower()
    return "pdf" if low.endswith(".pdf") else ("picture" if ocrpdf.is_image(low) else "")


def sources(lib, marked=True):
    """[(doc id, name, path, kind)] of every document whose latest version is a PDF or a picture on this PC. 4.25.3
    (answer 25: "I only run redlines on things we mark as a Redlined Deliverable"): only those marked Redlined
    Deliverable, unless marked is False."""
    out = []
    for d in lib.all:
        if not d.get("versions"):
            continue
        if marked and "redline" not in (d.get("returns") or []):
            continue
        p = lib.path_of(d["versions"][-1])
        if p and kind(p) and os.path.isfile(p):
            out.append((d["id"], d["name"], p, kind(p)))
    return out


def page_form(path, copies_folder="", make=True):
    """The PDF a file is read from: the PDF itself, or the page copy with words of a picture or a scanned PDF (made
    when missing and make is True). "" when there is none yet."""
    import ocrpdf
    if not ocrpdf.needs_copy(path):
        return path
    if not copies_folder:
        return path if kind(path) == "pdf" else ""
    c = ocrpdf.copy_path(path, copies_folder)
    if os.path.isfile(c) and os.path.getsize(c) > 0:
        return c
    return ocrpdf.make(path, copies_folder) if make else ""


def copies_of(folder, path):
    """The prepared Word files made from one source (newest first): [(copy path, its sidecar)]."""
    name = os.path.basename(path)
    out = []
    for c in RC.copies(folder) if folder else []:
        side = RC.sidecar(c) or {}
        if side.get("source") == name:
            out.append((c, side))
    out.sort(key=lambda x: x[1].get("made", ""), reverse=True)
    return out


def state(folder, path):
    """{"copy", "when", "comments", "changes", "listed", "into"} of the newest prepared file of a source; "copy" is ""
    when it has not been prepared."""
    got = copies_of(folder, path)
    if not got:
        return {"copy": "", "when": "", "comments": 0, "changes": 0, "listed": 0, "into": ""}
    c, side = got[0]
    recs = side.get("comments") or []
    return {"copy": c, "when": (side.get("made") or "")[:16].replace("T", " "), "comments": len(recs),
            "changes": sum(1 for r in recs if r.get("became") in ("deletion", "insertion", "replacement")),
            "listed": sum(1 for r in recs if r.get("became") == "listed only"), "into": side.get("into", "")}


def said(st):
    """A row's state in words."""
    if not st["copy"]:
        return "Not prepared"
    out = f"Prepared {st['when']}"
    if st["into"]:
        out += f", into {st['into']}"
    if st["comments"]:
        out += f", {st['comments']} comment(s) placed" if not st["listed"] else \
            f", {st['comments'] - st['listed']} of {st['comments']} comment(s) placed"
    return out


def _resource(path, pdf):
    """The sidecar names the document the person knows, not the page copy it was read from."""
    if os.path.abspath(pdf) == os.path.abspath(path):
        return {}
    return {"source": os.path.basename(path), "read_from": os.path.basename(pdf)}


def _side_update(copy, **more):
    side = RC.sidecar(copy) or {}
    side.update(more)
    with open(copy + RC.SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    return side


def prepare(path, folder, copies_folder="", layout=None, comments=True):
    """Routes 1 and 2: the Word copy of a PDF or a picture, in folder, with the PDF's comments placed. Returns
    redlinecopy.build's result. Raises ValueError when the file has no words to read."""
    import ocrpdf
    if not copies_folder and ocrpdf.needs_copy(path):       # a file outside any effort: its page copy is not kept
        import tempfile
        copies_folder = tempfile.mkdtemp(prefix="sk_redline_")
    pdf = page_form(path, copies_folder)
    if not pdf:
        raise ValueError("This picture has not been read yet.")
    out = os.path.join(folder, RC.copy_name(path))
    res = RC.build(pdf, out, name=os.path.basename(path), layout=layout, comments=comments)
    more = _resource(path, pdf)
    if more:
        _side_update(out, **more)
    return res


def into_name(docx, when=None):
    stem = os.path.splitext(os.path.basename(docx))[0]
    return f"{stem} - redline copy - {(when or datetime.date.today()).isoformat()}.docx"


def into_word(path, docx, folder, copies_folder=""):
    """Route 3: the PDF's comments into a dated copy of a Word file you already have (the same text as the PDF).
    Returns {"path", "comments": [what each became], "changes", "word_comments", "listed", "nearby", "words": (in the
    PDF, found in the Word file)}; "comments" is empty when the PDF has none (nothing is written then)."""
    import pdfcomments as PC
    import pagesent as PS
    import redlinecheck as CK
    import redlinemarks as RM
    pdf = page_form(path, copies_folder)
    if not pdf:
        raise ValueError("This picture has not been read yet.")
    found = PC.read(pdf)
    if not found:
        return {"path": "", "comments": [], "changes": 0, "word_comments": 0, "listed": 0, "nearby": 0, "words": (0, 0)}
    name = os.path.basename(path)
    src = CK.pdf_words(pdf, name)[0]
    d = PS.doc_of(pdf)
    extra, force = PS.decided(pdf, name)
    doc = {"pages": d["pages"], "_out": ((set(d.get("skip") or ()) - set(force)) | set(extra))}
    pinned, stream = PC.pin(pdf, found, src, doc)
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, into_name(docx))
    if os.path.abspath(out) == os.path.abspath(docx):
        raise ValueError("The Word file is already a prepared copy of today: pick the file it was made from.")
    clean = [p for p in CK.docx_paragraphs(docx, reject=True) if p["text"].strip()]
    shutil.copyfile(docx, out)
    recs = RM.apply(out, pinned, stream, src)
    have = {w for p in clean for w in p["text"].split()}
    words = [w for w in stream.words]
    side = {"format": RC.FORMAT, "layout": "existing", "source": name, "source_sha256": RC._sha(pdf),
            "made": datetime.datetime.now().isoformat(timespec="seconds"), "paragraphs": clean, "set_aside": [],
            "comments": recs, "into": os.path.basename(docx)}
    if os.path.abspath(pdf) != os.path.abspath(path):
        side["read_from"] = os.path.basename(pdf)
    with open(out + RC.SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    became = [r["became"] for r in recs]
    return {"path": out, "comments": recs,
            "changes": sum(1 for b in became if b in ("deletion", "insertion", "replacement")),
            "word_comments": sum(1 for b in became if b == "comment"),
            "listed": sum(1 for b in became if b == "listed only"),
            "nearby": sum(1 for r in recs if r["how"] in ("position", "left out", "nearby words")),
            "words": (len(words), sum(1 for w in words if w in have))}
