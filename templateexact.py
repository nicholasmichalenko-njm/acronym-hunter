"""A template's exact pages, drawn by Word on request and kept (4.44.0; ST57 of 2026-11-15). The template's exported
file already holds a sample of every part: the cover's lines, the table of contents and the lists, a body with
headings, bullets, a table and a figure with their captions, and an appendix. That file, opened as a document, is what
a person gets from the template. Word on this PC opens it, updates its fields and saves a PDF (exactpreview.lay_out:
macros off, no prompts, a time limit, only the Word it started is ended); each page of the PDF becomes a picture.

The pictures are kept by what the template is made from (namedtemplates.fingerprint), the version made and SPECIMEN,
so one set of picks is drawn once. On the PC this was measured on, Word's PDF step alone took one to two minutes
(claude/stationkeeper-open-error-word-pdf-export-slow-2026-11-15.md), so nothing here runs unless a person asks.
Only reads the template; nothing leaves the PC."""
import io, os, re, shutil, tempfile, zipfile

SPECIMEN = 1                     # raise when what is drawn changes, so kept pictures are drawn again
SUB = "template_pages"
LIMIT = 300                      # seconds Word may take before the job is ended
WIDTH = 760                      # pixels across a portrait page
SLOW = "Word is drawing the pages. On this PC that can take a minute or more. The sample pages stay until it is done."


def folder(config_dir, t):
    """Where this template's exact pages are kept, for what it is made from now."""
    import namedtemplates as NT
    made = (t or {}).get("made") or {}
    return os.path.join(config_dir, SUB, f"{NT.fingerprint(config_dir, t)}_{int(made.get('version') or 0)}_{SPECIMEN}")


def ready(config_dir, t):
    """Whether the template's file is there and made from what the template holds now."""
    made = (t or {}).get("made") or {}
    import namedtemplates as NT
    return bool(made) and os.path.isfile(made.get("path") or "") and made.get("fp") == NT.fingerprint(config_dir, t)


def cached(config_dir, t):
    """[picture paths, in page order] kept for this template as it is now; [] when none."""
    if not t or not ready(config_dir, t):
        return []
    d = folder(config_dir, t)
    try:
        names = sorted(n for n in os.listdir(d) if re.match(r"^page\d{3}\.png$", n))
    except OSError:
        return []
    return [os.path.join(d, n) for n in names]


def document(path):
    """The template's file as a document (bytes): the same parts, said to be a document, without the Quick Parts."""
    import libpreview as LP
    with zipfile.ZipFile(path) as zin:
        parts = {n: zin.read(n) for n in zin.namelist()}
    ct = parts["[Content_Types].xml"].decode("utf-8").replace(*LP._DOC_CT)
    parts["[Content_Types].xml"] = ct.encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            if not n.startswith("word/glossary/"):
                z.writestr(n, b)
    return LP._drop_glossary_rel(buf.getvalue())


def pictures(pdf, out_dir, width=WIDTH):
    """Each page of the PDF as page001.png, page002.png... in out_dir. Returns the paths; [] when it cannot be read."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001  an unreadable PDF gives no pictures
        return []
    out = []
    try:
        os.makedirs(out_dir, exist_ok=True)
        for i in range(len(doc)):
            page = doc[i]
            w, h = page.get_size()
            scale = max(0.5, width / max(1.0, min(w, h)))
            p = os.path.join(out_dir, f"page{i + 1:03d}.png")
            page.render(scale=scale).to_pil().save(p + ".tmp", "PNG")
            os.replace(p + ".tmp", p)
            page.close()
            out.append(p)
    except Exception:  # noqa: BLE001
        out = []
    finally:
        doc.close()
    return out


def prune(config_dir, keep=12):
    """Keeps the newest sets of pictures; the rest go."""
    root = os.path.join(config_dir, SUB)
    try:
        ds = sorted((os.path.join(root, n) for n in os.listdir(root)), key=os.path.getmtime, reverse=True)
    except OSError:
        return 0
    for d in ds[keep:]:
        shutil.rmtree(d, ignore_errors=True)
    return max(0, len(ds) - keep)


def draw(config_dir, t, runner=None, timeout=LIMIT):
    """Word draws the template's pages. Returns {"ok": True, "pages": [paths], "cached": bool} or {"ok": False, "why"}.
    runner (tests): passed to exactpreview.lay_out."""
    import exactpreview as XP
    if not t or not ready(config_dir, t):
        return {"ok": False, "why": "Export the template first: Word draws the file the export writes."}
    have = cached(config_dir, t)
    if have:
        return {"ok": True, "pages": have, "cached": True}
    if runner is None and not XP.available():
        return {"ok": False, "why": "Word on this PC draws the exact pages; these are the app's sample pages."}
    work = tempfile.mkdtemp(prefix="sk_tplpages_")
    try:
        docx, pdf = os.path.join(work, "template.docx"), os.path.join(work, "template.pdf")
        try:
            with open(docx, "wb") as f:
                f.write(document(t["made"]["path"]))
        except (OSError, KeyError, zipfile.BadZipFile):
            return {"ok": False, "why": "The template's file could not be read. Export it again."}
        r = XP.lay_out(docx, pdf, runner=runner, timeout=timeout)
        if not r.get("ok"):
            return {"ok": False, "why": r.get("why") or "Word could not draw the pages."}
        tmp_out = os.path.join(work, "pages")
        got = pictures(pdf, tmp_out)
        if not got:
            return {"ok": False, "why": "Word's pages could not be turned into pictures."}
        dst = folder(config_dir, t)
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(tmp_out, dst)
        prune(config_dir)
        return {"ok": True, "pages": cached(config_dir, t), "cached": False, "count": r.get("pages")}
    finally:
        shutil.rmtree(work, ignore_errors=True)
