"""Volume check and first use (2.7.0): check final volumes against the effort's list.

Pure functions (no GUI, no files read except where a caller passes paths to write). Inputs are the scan results the
app already has, the Effort List rows, and the volumes in submission order.

Report parts:
  first_use     acronyms only. Per volume (rule "volume") or across the submission (rule "submission"): where the
                acronym first appears, whether it is written "Spelled Out Words (ACR)", whether the spelled-out words
                match the effort list, later re-definitions.
  missing       terms the volumes use that the effort list does not have.
  not_approved  terms in the list whose status is Proposed or Needs author.
  differs       the volume spells a term out differently from the effort list.
  unused        list entries (not Rejected) that no volume uses: keep them out of the volumes' acronym lists.
  lists         per volume: every acronym, abbreviation and unit it uses, with the list's definition.
Nothing leaves the PC: the report is written only where the user saves it.
"""
import re

LIST_TYPES = ("Acronym", "Abbreviation", "Unit")
OK, WARN, BAD, INFO = "ok", "warn", "bad", "info"


def natural_key(name):
    """Vol 2 before Vol 10."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def norm_def(s):
    """Definition comparison: case, hyphens, slashes, punctuation, plural endings and a leading 'the' do not count."""
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[-/–—_]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in s.split()]
    if words and words[0] == "the":
        words = words[1:]
    return " ".join(words)


def same_def(a, b):
    return bool(a) and bool(b) and norm_def(a) == norm_def(b)


def kind(category):
    for k in LIST_TYPES:
        if (category or "").startswith(k):
            return k
    return ""


def _uses(d, vol, file_of):
    return [loc for loc in d.get("locations", []) if file_of(loc) == vol]


def build(results, rows, volumes, rule="volume", vol_defs=None, file_of=None, in_picture=None):
    """results: the app's scan results {term: data}. rows: EffortList.rows {term: {column: value}}.
    volumes: file names (as in location labels) in submission order. vol_defs: {volume: custdefs.extract() result}.
    Returns a dict with the report parts (lists of dicts) and a summary."""
    vol_defs = vol_defs or {}
    file_of = file_of or (lambda loc: loc)
    in_picture = in_picture or (lambda loc: False)
    used = {v: {} for v in volumes}            # volume -> {term: [locations]}
    for term, d in results.items():
        if d.get("manual") or d.get("file_error") or d.get("gone") or not kind(d.get("category", "")):
            continue
        row = rows.get(term)
        if d.get("excluded") and not (row and row.get("Status") == "Rejected"):
            continue                           # excluded in the database: not a term anywhere
        for v in volumes:
            locs = _uses(d, v, file_of)
            if locs:
                used[v][term] = locs

    def list_def(term):
        r = rows.get(term)
        return (r or {}).get("Definition", "")

    def status(term):
        r = rows.get(term)
        return r["Status"] if r else "Not in effort list"

    rejected = {t for t, r in rows.items() if r.get("Status") == "Rejected"}

    # ---------------- first use (acronyms only)
    first_use = []
    defined_in = {}                            # term -> first volume where it was defined (submission rule)
    seen_in = {}                               # term -> first volume where it appeared (submission rule)
    for v in volumes:
        for term in sorted(used[v], key=str.lower):
            d = results[term]
            if kind(d.get("category", "")) != "Acronym" or term in rejected:
                continue
            u = d.get("first_use", {}).get(v)
            if not u:
                continue
            want = list_def(term)
            lf = u.get("lf", "")
            redefs = ["later in the same passage" if r == u["loc"] else r for r in u.get("redefs", [])]
            row = {"volume": v, "term": term, "loc": u["loc"], "written": lf, "list_definition": want,
                   "status": status(term), "also_defined": "; ".join(redefs[:5]), "level": OK, "state": ""}
            pic = " (first use is in a picture)" if in_picture(u["loc"]) else ""
            earlier = seen_in.get(term) if rule == "submission" else None
            if earlier:
                if u["defined"] is True:
                    row["level"], row["state"] = INFO, f"Defined again; first defined in {defined_in.get(term) or earlier}"
                    if not defined_in.get(term):
                        row["level"], row["state"] = WARN, f"Defined here, but first used undefined in {earlier}"
                        defined_in[term] = v
                elif defined_in.get(term):
                    row["level"], row["state"] = OK, f"Defined earlier in {defined_in[term]}"
                else:
                    row["level"], row["state"] = BAD, f"Not defined before this; first used in {earlier}"
                    if u.get("later"):
                        defined_in[term] = v
                first_use.append(row)
                continue
            if rule == "submission":
                seen_in[term] = v
            if u["defined"] is True:
                if rule == "submission":
                    defined_in[term] = v
                if want and lf and not same_def(lf, want):
                    row["level"], row["state"] = WARN, "Defined, but the words differ from the effort list"
                elif not lf:
                    row["level"], row["state"] = WARN, "Written as (ACR), but the spelled-out words were not found right before it"
                else:
                    row["state"] = "Defined at first use"
            elif u["defined"] is None:
                row["level"], row["state"] = WARN, "Check: read with an OCR correction"
            elif u.get("later"):
                row["level"] = BAD
                row["state"] = ("Not defined at first use; spelled out later in the same passage" if u["later"] == u["loc"]
                                else f"Not defined at first use; spelled out later at {u['later']}")
                if rule == "submission":
                    defined_in[term] = v
            else:
                row["level"], row["state"] = BAD, "Never defined in this volume" if rule == "volume" else "Not defined at first use"
            if redefs and row["level"] == OK:
                row["level"] = INFO
                row["state"] += "; defined again later"
            row["state"] += pic
            first_use.append(row)

    # ---------------- missing / not approved / differs
    missing, not_approved, differs = [], [], []
    all_terms = {}
    for v in volumes:
        for term, locs in used[v].items():
            all_terms.setdefault(term, []).append((v, locs))
    for term in sorted(all_terms, key=str.lower):
        d = results[term]
        vols = [v for v, _ in all_terms[term]]
        first_loc = all_terms[term][0][1][0]
        base = {"term": term, "type": kind(d.get("category", "")), "volumes": ", ".join(vols), "loc": first_loc,
                "count": sum(len(l) for _, l in all_terms[term])}
        r = rows.get(term)
        if r is None:
            sd = d.get("selected_definition", "")
            sd = "" if sd.startswith(("[", "⚠", "MULTIPLE", "Rescan")) else sd
            missing.append(dict(base, suggestion=sd))
            continue
        if r["Status"] == "Rejected":
            continue
        if r["Status"] in ("Proposed", "Needs author"):
            not_approved.append(dict(base, status=r["Status"], definition=r.get("Definition", "")))
        want = r.get("Definition", "")
        for v in vols:
            for h in (vol_defs.get(v) or {}).get(term, []):
                if want and not same_def(h["definition"], want):
                    differs.append(dict(base, volume=v, written=h["definition"], list_definition=want,
                                        loc=h.get("where", first_loc), sentence=h.get("sentence", "")))

    # ---------------- unused list entries
    unused = []
    for term in sorted(rows, key=str.lower):
        r = rows[term]
        if r.get("Status") == "Rejected" or term in all_terms:
            continue
        unused.append({"term": term, "type": r.get("Type", ""), "status": r.get("Status", ""), "definition": r.get("Definition", "")})

    # ---------------- per-volume acronym lists
    lists = {}
    for v in volumes:
        out = []
        for term in sorted(used[v], key=lambda t: (t.lower(), t)):
            if term in rejected:
                continue
            d = results[term]
            r = rows.get(term)
            if r:
                definition, st = r.get("Definition", ""), r["Status"]
            else:
                sd = d.get("selected_definition", "")
                definition, st = ("" if sd.startswith(("[", "⚠", "MULTIPLE", "Rescan")) else sd), "Not in effort list"
            out.append({"term": term, "definition": definition, "status": st, "type": kind(d.get("category", ""))})
        lists[v] = out

    summary = {"volumes": len(volumes), "rule": rule,
               "terms_used": len(all_terms),
               "first_use_problems": sum(1 for r in first_use if r["level"] in (BAD, WARN)),
               "missing": len(missing), "not_approved": len(not_approved), "differs": len(differs), "unused": len(unused)}
    return {"summary": summary, "first_use": first_use, "missing": missing, "not_approved": not_approved,
            "differs": differs, "unused": unused, "lists": lists, "volumes": list(volumes), "used": used}


def effort_updates(report):
    """{term: {"Used in volumes": ..., "First use": ...}} for terms already in the list."""
    vols = {}
    for v in report["volumes"]:
        for term in report["used"][v]:
            vols.setdefault(term, []).append(v)
    fu = {}
    for r in report["first_use"]:
        fu.setdefault(r["term"], []).append(f"{r['volume']}: {r['state']}")
    return {t: {"Used in volumes": "; ".join(v), "First use": "; ".join(fu.get(t, []))[:400]} for t, v in vols.items()}


# ------------------------------------------------------------------ writers
def write_excel(report, path, effort_name=""):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    fills = {BAD: "FDE2E2", WARN: "FEF3E2", INFO: "E0F2FE", OK: None}
    wb = Workbook()
    ws = wb.active; ws.title = "Summary"
    s = report["summary"]
    for r in (["Effort", effort_name], ["Volumes", ", ".join(report["volumes"])],
              ["First use rule", "Restarts in each volume" if s["rule"] == "volume" else "Runs across the whole submission"],
              ["Terms used", s["terms_used"]], ["First-use problems", s["first_use_problems"]],
              ["Not in effort list", s["missing"]], ["Not approved yet", s["not_approved"]],
              ["Definition differs", s["differs"]], ["In the list, not used", s["unused"]]):
        ws.append(r)
    ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 90

    def sheet(title, cols, rows, keys, widths, level_key=None):
        sh = wb.create_sheet(title[:31])
        sh.append(cols)
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
        for row in rows:
            sh.append([row.get(k, "") for k in keys])
            f = fills.get(row.get(level_key)) if level_key else None
            if f:
                for c in sh[sh.max_row]:
                    c.fill = PatternFill("solid", fgColor=f)
        for i, w in enumerate(widths, 1):
            sh.column_dimensions[sh.cell(row=1, column=i).column_letter].width = w
        for row in sh.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        sh.freeze_panes = "B2"
        if sh.max_row > 1:
            sh.auto_filter.ref = f"A1:{sh.cell(row=1, column=len(cols)).column_letter}{sh.max_row}"

    sheet("First use", ["Volume", "Acronym", "Result", "First use at", "Written as", "Effort list definition", "Also defined at", "List status"],
          report["first_use"], ["volume", "term", "state", "loc", "written", "list_definition", "also_defined", "status"],
          [22, 12, 46, 40, 34, 34, 30, 14], level_key="level")
    sheet("Not in effort list", ["Term", "Type", "Volumes", "Count", "Suggested definition", "First found at"],
          report["missing"], ["term", "type", "volumes", "count", "suggestion", "loc"], [14, 13, 30, 8, 40, 40])
    sheet("Not approved", ["Term", "Type", "Status", "Definition", "Volumes", "First found at"],
          report["not_approved"], ["term", "type", "status", "definition", "volumes", "loc"], [14, 13, 14, 40, 30, 40])
    sheet("Definition differs", ["Term", "Volume", "Volume says", "Effort list says", "Where", "Sentence"],
          report["differs"], ["term", "volume", "written", "list_definition", "loc", "sentence"], [14, 22, 36, 36, 36, 60])
    sheet("Unused in volumes", ["Term", "Type", "Status", "Definition"],
          report["unused"], ["term", "type", "status", "definition"], [14, 13, 14, 50])
    for i, v in enumerate(report["volumes"], 1):
        sheet(f"List {i} " + re.sub(r"[\[\]:*?/\\]", "", v)[:22], ["Term", "Definition", "Status", "Type"],
              report["lists"][v], ["term", "definition", "status", "type"], [14, 60, 18, 13])
    wb.save(path)


def _x(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def write_docx(entries, path, title="Acronyms and Abbreviations"):
    """A Word document with a two-column table (Term, Definition), built from the Office XML directly
    (no add-in, no macros). entries: [(term, definition)]."""
    import zipfile
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

    def cell(text, width, bold=False, shade=None):
        rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
        sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ""
        return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{sh}</w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr><w:r>{rpr}<w:t xml:space="preserve">{_x(text)}</w:t></w:r></w:p></w:tc>')

    rows = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>' + cell("Term", 2000, True, "D9E2F3") + cell("Definition", 7360, True, "D9E2F3") + "</w:tr>"]
    rows += ["<w:tr><w:trPr><w:cantSplit/></w:trPr>" + cell(t, 2000) + cell(d, 7360) + "</w:tr>" for t, d in entries]
    border = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    body = (f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>{_x(title)}</w:t></w:r></w:p>'
            f'<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>{border}</w:tblBorders>'
            f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid><w:gridCol w:w="2000"/><w:gridCol w:w="7360"/></w:tblGrid>'
            + "".join(rows) + '</w:tbl><w:p/><w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{body}</w:body></w:document>'
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
              '<w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
              '<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>'
              '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)
