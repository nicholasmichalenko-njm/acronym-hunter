"""Final package check (3.4.0): the submission PDFs checked before upload, the job production does by hand under the most
time pressure of the effort. For each PDF: opens without a password, page count against the volume's page limit, page
size (letter or A4, and pages that differ), fonts embedded, bookmarks, pages with no searchable text, file size against
the limit, and the file name against what it must contain. For the package: every required volume and form has a file.
Reads with PDFium; nothing is changed. Rules only."""
import os, re

SIZES = {"Letter": (612, 792), "A4": (595, 842), "Legal": (612, 1008), "Tabloid": (792, 1224)}
TOL = 4                                    # points


def page_size_name(w, h):
    a, b = sorted((round(w), round(h)))
    for name, (x, y) in SIZES.items():
        if abs(a - x) <= TOL and abs(b - y) <= TOL:
            return name
    return f"{a / 72:.2f} x {b / 72:.2f} in"


def read_pdf(path):
    """{"pages", "sizes" [(name, landscape)], "fonts" {name: embedded}, "bookmarks", "no_text" [page numbers],
    "encrypted", "error", "bytes"}."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    out = {"pages": 0, "sizes": [], "fonts": {}, "bookmarks": 0, "no_text": [], "encrypted": False, "error": "",
           "bytes": os.path.getsize(path) if os.path.isfile(path) else 0}
    try:
        pdf = pdfium.PdfDocument(path)
    except pdfium.PdfiumError as e:
        msg = str(e).lower()
        out["encrypted"] = "password" in msg
        out["error"] = "needs a password" if out["encrypted"] else "does not open as a PDF"
        return out
    try:
        out["pages"] = len(pdf)
        try:
            out["encrypted"] = raw.FPDF_GetSecurityHandlerRevision(pdf.raw) != -1
        except Exception:
            pass
        try:
            out["bookmarks"] = sum(1 for _ in pdf.get_toc())
        except Exception:
            out["bookmarks"] = 0
        import ctypes
        for i in range(len(pdf)):
            page = pdf[i]
            w, h = page.get_size()
            out["sizes"].append((page_size_name(w, h), w > h))
            try:
                tp = page.get_textpage()
                if not tp.get_text_range().strip():
                    out["no_text"].append(i + 1)
                tp.close()
            except Exception:
                pass
            try:
                n = raw.FPDFPage_CountObjects(page.raw)
                for k in range(n):
                    obj = raw.FPDFPage_GetObject(page.raw, k)
                    if raw.FPDFPageObj_GetType(obj) != raw.FPDF_PAGEOBJ_TEXT:
                        continue
                    font = raw.FPDFTextObj_GetFont(obj)
                    if not font:
                        continue
                    b = ctypes.create_string_buffer(256)
                    ln = raw.FPDFFont_GetBaseFontName(font, b, 256)
                    name = b.raw[:max(0, ln - 1)].decode("latin-1", "replace") if ln else "(unnamed)"
                    name = re.sub(r"^[A-Z]{6}\+", "", name)              # subset prefix
                    emb = bool(raw.FPDFFont_GetIsEmbedded(font))
                    out["fonts"][name] = out["fonts"].get(name, False) or emb
            except Exception:
                pass
            page.close()
    finally:
        pdf.close()
    return out


def _mb(n):
    return n / (1024 * 1024)


def check(paths, limits=(), size_mb=None, must_contain=(), required=(), allowed_sizes=("Letter",)):
    """Every PDF checked. limits: page-limit rows ({"subject", "value"}) matched to files by volume; size_mb: the
    largest a file may be; must_contain: words every file name must hold; required: names of the volumes and forms
    that must each have a file. Returns {"files": [{"file", "path", "pages", "limit", "info", "problems", "ok"}],
    "missing": [required names with no file], "problems": total}."""
    import subreq as SR
    files = []
    for p in sorted(paths, key=lambda x: os.path.basename(x).lower()):
        name = os.path.basename(p)
        info = read_pdf(p)
        probs = []
        if info["error"]:
            probs.append(f"{name} {info['error']}")
        elif info["encrypted"]:
            probs.append("is password-protected or restricted: portals often refuse these")
        limit = None
        for r in limits:
            if r.get("kind", "Page limit") == "Page limit" and SR.match_volume(r.get("subject", ""), name):
                limit = SR._limit_n(r.get("value", ""))
                if limit:
                    break
        if limit and info["pages"] > limit:
            probs.append(f"{info['pages']} pages, over the {limit}-page limit (check which pages the limit leaves out)")
        sizes = [s for s, _l in info["sizes"]]
        odd = sorted({s for s in sizes if s not in allowed_sizes})
        if odd:
            pages = [str(k + 1) for k, s in enumerate(sizes) if s not in allowed_sizes]
            probs.append(f"page size {', '.join(odd)} on page{'s' if len(pages) > 1 else ''} {', '.join(pages[:12])}"
                         + ("..." if len(pages) > 12 else "") + f" (expected {' or '.join(allowed_sizes)})")
        land = [str(k + 1) for k, (_s, l) in enumerate(info["sizes"]) if l]
        notes = []
        if land:
            notes.append(f"landscape: page{'s' if len(land) > 1 else ''} {', '.join(land[:12])}")
        bad_fonts = sorted(f for f, e in info["fonts"].items() if not e)
        if bad_fonts:
            probs.append("fonts not embedded: " + ", ".join(bad_fonts[:8]))
        if info["pages"] and len(info["no_text"]) == info["pages"]:
            probs.append("no searchable text on any page (a scan?)")
        elif info["no_text"]:
            notes.append(f"no text on page{'s' if len(info['no_text']) > 1 else ''} {', '.join(map(str, info['no_text'][:12]))} (pictures or blank)")
        if info["pages"] > 20 and not info["bookmarks"]:
            notes.append("no bookmarks")
        if size_mb and _mb(info["bytes"]) > size_mb:
            probs.append(f"{_mb(info['bytes']):.1f} MB, over the {size_mb:g} MB limit")
        for w in must_contain:
            if w and w.lower() not in name.lower():
                probs.append(f"file name does not contain “{w}”")
        files.append({"file": name, "path": p, "pages": info["pages"], "limit": limit, "mb": round(_mb(info["bytes"]), 2),
                      "fonts": len(info["fonts"]), "bookmarks": info["bookmarks"], "notes": notes, "problems": probs, "ok": not probs})
    missing = []
    for req in required:
        if not any(SR.match_volume(req, f["file"]) or _words_in(req, f["file"]) for f in files):
            missing.append(req)
    return {"files": files, "missing": missing, "problems": sum(len(f["problems"]) for f in files) + len(missing)}


def _words_in(req, filename):
    """True when the file name holds the requirement's distinctive words (SF 33 -> 'SF33', 'SF_33', 'sf 33')."""
    fn = re.sub(r"[^a-z0-9]", "", filename.lower())
    words = [w for w in re.findall(r"[A-Za-z]+|\d+", req or "") if len(w) > 1 or w.isdigit()]
    key = re.sub(r"[^a-z0-9]", "", (req or "").lower())
    if key and key in fn:
        return True
    strong = [w.lower() for w in words if w.lower() not in ("volume", "vol", "the", "and", "of", "form")]
    return bool(strong) and all(w in fn for w in strong)


def export(path, result, effort=""):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Final package"
    ws.append(["File", "Pages", "Limit", "MB", "Fonts", "Bookmarks", "Problems", "Notes"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for f in result["files"]:
        ws.append([f["file"], f["pages"], f["limit"] or "", f["mb"], f["fonts"], f["bookmarks"], "; ".join(f["problems"]) or "OK", "; ".join(f["notes"])])
        if f["problems"]:
            ws.cell(row=ws.max_row, column=7).font = Font(color="B91C1C", bold=True)
    for m in result["missing"]:
        ws.append([f"(missing) {m}", "", "", "", "", "", "no file for it in the package", ""])
        ws.cell(row=ws.max_row, column=7).font = Font(color="B91C1C", bold=True)
    for i, w in enumerate([40, 8, 8, 8, 8, 10, 60, 40], 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    if effort:
        wb.properties.title = f"{effort} final package check"
    wb.save(path)
    return path
