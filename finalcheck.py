"""Final Check (3.58.0, claude/stationkeeper-final-check-decisions-2026-11-05.md): one ready-to-send report per volume,
on its Word file and its PDF together. Eight sections, each line Pass, Fail or Needs a person, with where and what to
do: Compliance, Page limits, Format rules, Structure, Acronyms, Leftovers, Markings, Files. Every page counts against a
page limit until it is ticked out (the cover, the TOC, the acronym list, resumes, dividers). The markings checked are the
proprietary legend on the cover and the page marking on every page (FAR 52.215-1(e)). Reads only; nothing is changed.
Rules only; nothing leaves the PC.

run(volume, ctx) -> {"volume", "docx", "pdf", "lines": [{"section", "check", "status", "detail"}], "counts"}
volume: {"name", "docx", "pdf", "exclude": [kinds]}; ctx (each optional): std, matrix, rows (submission rules),
amendments (n), qa_report (Submission Check's report on the volumes), other_names, effort_name, size_mb, must_contain,
allowed_sizes, marking."""
import os, re
import formcheck as FM          # 3.68.0: customer forms

PASS, FAIL, HUMAN = "Pass", "Fail", "Needs a person"
SECTIONS = ("Compliance", "Page limits", "Format rules", "Structure", "Acronyms", "Leftovers", "Markings", "Files")
EXCLUDE = (("cover", "The cover"), ("toc", "The table of contents"), ("acronyms", "The acronym list"),
           ("resumes", "Resumes"), ("dividers", "Dividers and blank pages"), ("appendices", "Appendices"))   # 3.66.0: appendices
LEGEND = "shall not be disclosed outside the Government"            # FAR 52.215-1(e) title page legend
PAGE_MARK = "Use or disclosure of data contained on this sheet"     # FAR 52.215-1(e) page marking
_MARKLINE = re.compile(r"(?i)use or disclosure of data|subject to the restriction|proprietary information|^\s*(page\s+)?\d+\s*$")
_TOC_LINE = re.compile(r"^(?P<t>[A-Z0-9][^\n]{2,120}?)\s*(?:\.{2,}|\s{2,}|\t)\s*\.*\s*(?P<n>\d{1,4})\s*$", re.M)


def _flat(s):
    return re.sub(r"\s+", " ", (s or "").replace("­", "").replace("-\n", "")).strip().lower()


# ------------------------------------------------------------------ the PDF
def read_pdf(path):
    """{"texts": [text per page], "meta": {Title, Author, ...}, "error"}."""
    out = {"texts": [], "meta": {}, "error": "", "sizes": []}
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(path)
    except Exception as e:  # noqa: BLE001
        out["error"] = "needs a password" if "password" in str(e).lower() else "does not open as a PDF"
        return out
    try:
        try:
            out["meta"] = {k: v for k, v in (pdf.get_metadata_dict() or {}).items() if v}
        except Exception:  # noqa: BLE001
            pass
        for i in range(len(pdf)):
            page = pdf[i]
            try:
                out["sizes"].append(tuple(page.get_size()))              # 3.66.0: points; an 11x17 sheet counts as more
            except Exception:  # noqa: BLE001
                out["sizes"].append((612.0, 792.0))
            try:
                tp = page.get_textpage()
                out["texts"].append(tp.get_text_range() or "")
                tp.close()
            except Exception:  # noqa: BLE001
                out["texts"].append("")
            page.close()
    finally:
        pdf.close()
    return out


def classify(texts):
    """{kind: [page numbers]} the pages each tick-out kind finds: the cover (page 1), the TOC, the acronym list,
    resumes, dividers and blank pages (under 15 words)."""
    out = {k: [] for k, _t in EXCLUDE}
    if texts:
        out["cover"] = [1]
    mode = ""
    for i, t in enumerate(texts, 1):
        head = _flat("\n".join(t.strip().splitlines()[:4]))
        bodytext = "\n".join(x for x in t.splitlines() if not _MARKLINE.search(x))   # a page marking alone is still blank
        words = len(re.findall(r"[A-Za-z]{2,}", bodytext))
        if i == 1:
            continue
        if re.search(r"\b(table of )?contents\b", head) and len(_TOC_LINE.findall(t)) >= 3:
            mode = "toc"
        elif mode == "toc" and len(_TOC_LINE.findall(t)) >= 5:
            pass
        elif re.search(r"\b(acronyms|abbreviations|acronym list)\b", head):
            mode = "acronyms"
        elif re.match(r"appendix\s+[a-z0-9]\b", head) or mode == "appendices":      # 3.66.0: from the first appendix on
            mode = "appendices"
        elif re.search(r"\b(resumes?|résumés?|key personnel resumes)\b", head):
            mode = "resumes"
        elif mode == "resumes" and not re.search(r"^\s*\d+(\.\d+)*\s+[A-Z]", t.strip().splitlines()[0] if t.strip() else ""):
            pass
        else:
            mode = ""
        if mode:
            out[mode].append(i)
        elif words < 15:
            out["dividers"].append(i)
    return out


def count_pages(texts, exclude, sizes=None, foldout=1, drop=None):
    """(pages counted, {kind: [pages left out]}). 3.66.0: a sheet larger than letter (an 11x17 foldout) counts as foldout
    pages when the volume's plan says so. 3.68.0: drop, the pages of customer forms that do not count."""
    found = classify(texts)
    out = {k: found[k] for k in exclude if found.get(k)}
    if drop:
        out["forms"] = sorted(drop)
    gone = {p for v in out.values() for p in v}
    n = 0
    for i in range(1, len(texts) + 1):
        if i in gone:
            continue
        w, h = (sizes[i - 1] if sizes and i - 1 < len(sizes) else (612.0, 792.0))
        n += foldout if max(w, h) > 1008 else 1                      # longer than 14 inches: a foldout
    return n, out


def plan_rules(ctx, name):
    """The parts and numbering plan of the volume this file is (by its name), else None."""
    import subreq as SR
    plans = (ctx or {}).get("part_plans") or {}
    key = next((k for k in plans if k == name or SR.match_volume(k, name)), None)
    if key is None:
        return None
    import partplan as PP

    class _R:
        data = {"part_plans": plans}
    return dict(PP.final_check_rules(_R, key) or {}, volume=key)


def limit_for(rows, name):
    import subreq as SR
    for r in rows or ():
        if r.get("kind", "Page limit") == "Page limit" and SR.match_volume(r.get("subject", ""), name):
            n = SR._limit_n(r.get("value", ""))
            if n:
                return n, r.get("subject", "")
    return None, ""


def toc_mismatches(texts):
    """[(title, TOC page, page it is on)] TOC lines whose heading sits on a page with another printed number."""
    printed = []
    for t in texts:
        lines = [x.strip() for x in t.strip().splitlines() if x.strip()]
        nums = [x for x in (lines[-2:] if lines else []) if re.fullmatch(r"(?:Page\s+)?\d{1,4}(?:\s+of\s+\d+)?", x, re.I)]
        printed.append(int(re.search(r"\d+", nums[-1]).group(0)) if nums else None)
    toc = classify(texts)["toc"]
    out = []
    for p in toc:
        for m in _TOC_LINE.finditer(texts[p - 1]):
            title, n = m.group("t").strip(" ."), int(m.group("n"))
            key = _flat(title)[:60]
            if len(key) < 6:
                continue
            for i, t in enumerate(texts, 1):
                if i in toc or i == 1:
                    continue
                if key in _flat(t) and printed[i - 1] is not None:
                    if printed[i - 1] != n:
                        out.append((title, n, printed[i - 1]))
                    break
    return out


# ------------------------------------------------------------------ the report
def _line(section, check, status, detail=""):
    return {"section": section, "check": check, "status": status, "detail": detail}


def _pages(nums, k=12):
    nums = list(nums)
    return ", ".join(map(str, nums[:k])) + (" ..." if len(nums) > k else "")


def run(volume, ctx=None):
    ctx = ctx or {}
    name = volume.get("name") or os.path.splitext(os.path.basename(volume.get("docx") or volume.get("pdf") or ""))[0]
    docx, pdf = volume.get("docx") or "", volume.get("pdf") or ""
    has_docx, has_pdf = bool(docx) and os.path.isfile(docx), bool(pdf) and os.path.isfile(pdf)
    lines = []
    P = read_pdf(pdf) if has_pdf else {"texts": [], "meta": {}, "error": "not set"}
    texts = P["texts"]
    no_pdf = _line("", "", HUMAN, "Set this volume's PDF beside its Word file to check this.")
    form_pages = set()

    # 1 compliance
    M = ctx.get("matrix")
    if M is None:
        lines.append(_line("Compliance", "Requirements placed in a section", HUMAN, "No compliance matrix in this effort."))
    else:
        import setupdoc as SD
        unp = SD.export_check(M)["unplaced"]
        lines.append(_line("Compliance", "Requirements placed in a section", FAIL if unp else PASS,
                           (f"{len(unp)} requirement(s) not placed: " + ", ".join(unp[:10]) + (" ..." if len(unp) > 10 else ""))
                           if unp else "Every requirement and context is placed."))
    if ctx.get("amendments"):
        lines.append(_line("Compliance", "Amendments acknowledged", HUMAN,
                           f"The Library holds {ctx['amendments']} amendment(s): confirm each is acknowledged where the RFP asks."))

    # 2 page limits
    limit, subject = limit_for(ctx.get("rows"), name)
    if not has_pdf:
        lines.append(dict(no_pdf, section="Page limits", check="Pages against the limit"))
    else:
        rules = plan_rules(ctx, name)
        exclude = volume.get("exclude") or ((rules or {}).get("exclude") or [])
        flines, fpages = FM.check(texts, (rules or {}).get("forms"), _line, PASS, FAIL, HUMAN)
        n, out = count_pages(texts, exclude, P.get("sizes"), (rules or {}).get("foldout", 1) if rules else 1, fpages["drop"])
        left = "; ".join(f"{dict(EXCLUDE + (('forms', 'Customer forms'),))[k].lower()} (page {_pages(v)})" for k, v in out.items())
        detail = f"{n} of {len(texts)} pages counted" + (f", leaving out {left}" if left else ", every page counted")
        if rules and not volume.get("exclude"):
            detail += f" (by the parts and numbering of {rules['volume']})"
        if not limit:
            lines.append(_line("Page limits", "Pages against the limit", HUMAN, detail + ". No page limit found for this volume."))
        else:
            lines.append(_line("Page limits", "Pages against the limit", FAIL if n > limit else PASS,
                               detail + f"; the limit is {limit} ({subject})" + (f": {n - limit} over." if n > limit else ".")))
        ticked = set(volume.get("exclude") or [])
        missing = [dict(EXCLUDE)[k] for k in ticked if not classify(texts).get(k)]
        if missing:
            lines.append(_line("Page limits", "Pages ticked out found", HUMAN, "Ticked out but not found in the PDF: "
                               + ", ".join(missing) + ". Check the count by hand."))
        lines += flines
        form_pages = set(fpages["form_pages"])

    # 3 format rules
    std = ctx.get("std")
    if not has_docx:
        lines.append(_line("Format rules", "Against the standards", HUMAN, "No Word file for this volume."))
    elif std is None:
        lines.append(_line("Format rules", "Against the standards", HUMAN, "No standard for this volume (Team > Effort Profiles)."))
    else:
        try:
            import prodfix as PF
            chk = PF.check(docx, std)
            errs = [f for f in chk.findings if f.get("severity") == "error"]
            areas = {}
            for f in errs:
                areas[f["area"]] = areas.get(f["area"], 0) + 1
            lines.append(_line("Format rules", "Against the standards", FAIL if errs else PASS,
                               ("; ".join(f"{n} in {a}" for a, n in sorted(areas.items(), key=lambda x: -x[1])) + ". Audit lists each one.")
                               if errs else f"No errors against {std.get('name', 'the standard')}"
                               + (f" ({len(chk.findings)} warning(s) or note(s) in Audit)." if chk.findings else ".")))
        except Exception as e:  # noqa: BLE001
            lines.append(_line("Format rules", "Against the standards", HUMAN, f"The Word file could not be checked ({type(e).__name__})."))
    if has_pdf:
        import pkgcheck as PK
        info = PK.read_pdf(pdf)
        allowed = tuple(ctx.get("allowed_sizes") or ("Letter",))
        odd = [str(k + 1) for k, (s, _l) in enumerate(info["sizes"]) if s not in allowed]
        lines.append(_line("Format rules", "Page size", FAIL if odd else PASS,
                           f"Not {' or '.join(allowed)} on page {_pages(odd)}." if odd else f"Every page is {' or '.join(allowed)}."))

    # 4 structure
    if has_docx:
        try:
            import xrefcheck as X
            pr = X.check(docx)["problems"]
            lines.append(_line("Structure", "Numbering and cross-references", FAIL if pr else PASS,
                               "; ".join(f"{p['kind']}: {p['text']}" for p in pr[:6]) + (" ..." if len(pr) > 6 else "") if pr
                               else "Figures and tables in order, every reference resolves."))
        except Exception as e:  # noqa: BLE001
            lines.append(_line("Structure", "Numbering and cross-references", HUMAN, f"Not read ({type(e).__name__})."))
        if ctx.get("recipes"):                                           # 3.66.0: the team's field recipes
            import fieldrecipes as FR
            rows = FR.check(FR.read_fields(docx), ctx["recipes"])
            bad = [r for r in rows if r["status"] == "differs"]
            miss = FR.missing_bookmarks(docx, ctx["recipes"])
            lines.append(_line("Structure", "Fields match the field recipes", FAIL if bad or miss else PASS,
                               "; ".join([f"{r['part']}: {r['code']} (the recipe {r['recipe']} says {r['expected']})" for r in bad[:5]]
                                         + [f"the bookmark {b} is missing" for b in miss])
                               + (" ..." if len(bad) > 5 else "") if bad or miss else
                               f"{FR.summary(rows)['matches']} field(s) match a recipe."))
    if has_pdf:
        mm = toc_mismatches(texts)
        lines.append(_line("Structure", "Table of contents page numbers", FAIL if mm else (PASS if classify(texts)["toc"] else HUMAN),
                           "; ".join(f"{t} says {a}, on page {b}" for t, a, b in mm[:6]) if mm else
                           ("The page numbers match the PDF." if classify(texts)["toc"] else "No table of contents found in the PDF.")))

    # 5 acronyms
    qr = ctx.get("qa_report")
    if not has_docx:
        lines.append(_line("Acronyms", "First use and the list", HUMAN, "No Word file for this volume."))
    elif not qr:
        lines.append(_line("Acronyms", "First use and the list", HUMAN, "No effort acronym list to check against (Acros & Abs > Scan)."))
    else:
        import volcheck as V
        mine = {os.path.basename(docx), os.path.splitext(os.path.basename(docx))[0], name}
        rows = [x for k in ("first_use", "acronym_list", "banned") for x in (qr.get(k) or []) if x.get("volume") in mine]
        bad = [x for x in rows if x.get("level") == V.BAD]
        warn = [x for x in rows if x.get("level") == V.WARN]
        lines.append(_line("Acronyms", "First use, the volume's list, banned words", FAIL if bad else PASS,
                           (f"{len(bad)} to fix" + (f", {len(warn)} to check" if warn else "") + ": "
                            + "; ".join(f"{x.get('term') or x.get('found', '')} ({x.get('state') or x.get('phrase', '')})" for x in bad[:6])
                            + (" ..." if len(bad) > 6 else "") + ". Submission Check lists each.") if bad else
                           ("Defined at first use; the list matches use" + (f"; {len(warn)} to check in Submission Check." if warn else "."))))
        s_ = qr.get("summary") or {}
        if s_.get("missing") or s_.get("not_approved"):
            lines.append(_line("Acronyms", "Terms in the effort list and approved", HUMAN,
                               f"Across the volumes checked: {s_.get('missing', 0)} not in the effort list, {s_.get('not_approved', 0)} with no definition yet."))

    # 6 leftovers
    if has_docx:
        import leftovers as LO
        r = LO.check(docx)
        lines.append(_line("Leftovers", "Setup text, hidden text, comments, tracked changes, placeholders",
                           FAIL if any(r["counts"].values()) else PASS, LO.summary(r)))
        names = [n for n in (ctx.get("other_names") or []) if n and len(n) > 3]
        if names:
            import techedit as T
            body = " ".join(p["text"] for p in T.read(docx)[0])
            hit = sorted({n for n in names if re.search(r"\b" + re.escape(n) + r"\b", body, re.I)})
            lines.append(_line("Leftovers", "Another effort's name", FAIL if hit else PASS,
                               "Found: " + ", ".join(hit) if hit else "No other effort's name in the text."))
    if has_pdf:
        meta = {k: v for k, v in P["meta"].items() if k in ("Title", "Author", "Subject", "Keywords", "Creator")}
        lines.append(_line("Leftovers", "PDF properties", HUMAN if meta else PASS,
                           ("Check these are meant to go out: " + "; ".join(f"{k}: {v}" for k, v in meta.items())) if meta
                           else "No title, author, subject or keywords set."))

    # 7 markings
    if not has_pdf:
        lines.append(dict(no_pdf, section="Markings", check="Proprietary legend on the cover"))
    else:
        flat = [_flat(t) for t in texts]
        legend = _flat(LEGEND)
        on_cover = any(legend in flat[i] for i in range(min(2, len(flat))))
        lines.append(_line("Markings", "Proprietary legend on the cover", PASS if on_cover else FAIL,
                           "Found on the cover." if on_cover else "The FAR 52.215-1(e) legend (" + LEGEND + "...) is not on the "
                           "cover or the page after it."))
        mark = _flat(ctx.get("marking") or PAGE_MARK)
        mark = " ".join(mark.split()[:8])
        miss = [i for i, f in enumerate(flat, 1) if i > 1 and mark not in f and i not in classify(texts)["dividers"]
                and i not in form_pages]                     # 3.68.0: a customer form carries its own marking
        lines.append(_line("Markings", "Page marking on every page", FAIL if miss else PASS,
                           f"Missing on page {_pages(miss)}." if miss else "On every page after the cover."))

    # 8 files
    if not has_pdf:
        lines.append(dict(no_pdf, section="Files", check="The PDF as the portal takes it"))
    else:
        import pkgcheck as PK
        r = PK.check([pdf], [], ctx.get("size_mb"), ctx.get("must_contain") or (), (), tuple(ctx.get("allowed_sizes") or ("Letter",)))
        f = r["files"][0]
        probs = [p for p in f["problems"] if "page size" not in p]
        lines.append(_line("Files", "The PDF as the portal takes it", FAIL if probs else PASS,
                           "; ".join(probs) if probs else f"{f['pages']} pages, {f['mb']:.1f} MB, fonts embedded, searchable text"
                           + (f"; {'; '.join(f['notes'])}" if f["notes"] else "") + "."))
    counts = {s: sum(1 for x in lines if x["status"] == s) for s in (PASS, FAIL, HUMAN)}
    return {"volume": name, "docx": docx, "pdf": pdf, "lines": lines, "counts": counts}


def export(path, reports, effort="", when=None):
    """The report in Excel: a Summary sheet (one row per volume) and one sheet per volume."""
    import datetime
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    when = when or datetime.datetime.now()
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Summary"
    ws.append(["Final Check", effort, f"{when:%Y-%m-%d %H:%M}"])
    ws.append(["Volume", "Word file", "PDF", PASS, FAIL, HUMAN])
    for r in reports:
        ws.append([r["volume"], os.path.basename(r["docx"]), os.path.basename(r["pdf"]), r["counts"][PASS], r["counts"][FAIL], r["counts"][HUMAN]])
    fills = {PASS: "DCFCE7", FAIL: "FEE2E2", HUMAN: "FEF3C7"}
    used = set()
    for r in reports:
        t = re.sub(r"[\[\]:*?/\\]", "", r["volume"])[:28] or "Volume"
        while t in used:
            t = t[:26] + str(len(used))
        used.add(t)
        sh = wb.create_sheet(t)
        sh.append(["Section", "Check", "Result", "Detail"])
        for x in r["lines"]:
            sh.append([x["section"], x["check"], x["status"], x["detail"]])
            sh.cell(sh.max_row, 3).fill = PatternFill("solid", fgColor=fills[x["status"]])
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
        for col, wdt in zip("ABCD", (16, 34, 16, 90)):
            sh.column_dimensions[col].width = wdt
        for row in sh.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in ws[2]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for col in "ABC":
        ws.column_dimensions[col].width = 36
    wb.save(path)
    return path
