"""The outline workbook written back out in its own layout (3.73.0, claude/stationkeeper-versions-decisions-2026-11-06.md
decision 6). The last version's workbook, kept with the effort, is the pattern: its title rows, headings, column widths
and each column's cell style stay; its rows are written again from the effort as it is now (sections in order, each
requirement with its RFP reference, the customer and supporting text beside it in the looks the layout gives them, the
guidance, the authors). The file reads as the clean next version; one Changes sheet lists every change from the last
version, by row and section. The kept workbook is only read. Rules only; nothing leaves the PC."""
import copy, os

import outlinelayouts as OL
import outlineversions as OV
import outlinexl as OX


def _kept(M, effort_path):
    last = OV.current(M)
    if last is None:
        raise ValueError("No outline version yet: bring the outline workbook in first.")
    if not last.get("kept") or not effort_path:
        raise ValueError("The last version's workbook is not kept with this effort: bring it in again from the effort.")
    import effortfolders as EF
    p = os.path.join(EF.root(effort_path), *last["kept"].split("/"))
    if not os.path.isfile(p):
        raise ValueError("The last version's workbook is missing from the effort's Outline Versions folder.")
    return last, p


def rows_now(M):
    """The effort's outline as rows (the shape outlineversions keeps), in order."""
    import compliance as C
    import setupdoc as SD
    S = SD.setup_of(M)
    B, P = SD.by_id(M), SD.placed_in(M)
    out, secs = [], []
    for o in M.outline:
        lab = C.outline_label(o)
        auth = S["owners"].get(lab) or {}
        authors = [a for a in [auth.get("lead", "")] + [x.strip() for x in (auth.get("with") or "").split(",")] if a]
        secs.append({"num": o["num"], "title": o["title"], "level": o.get("level", 1), "authors": authors})
        base = {"section": lab, "num": o["num"], "title": o["title"], "ref": "", "req": "", "customer": [], "support": [], "guidance": "",
                "authors": authors}
        rows = []
        if S["mgmt"].get(lab):
            rows.append(dict(base, guidance=S["mgmt"][lab], customer=[], support=[]))
        cur = None
        for iid in P.get(lab) or []:
            it = B.get(iid)
            if it is None:
                continue
            kind = SD.kind_of(it)
            if it.get("decision") == "Keep" and kind == "Requirement":
                cur = dict(base, ref=S["refs"].get(iid, "") or it.get("section", ""), req=it.get("text", ""),
                           guidance=S["notes"].get(iid, ""), customer=[], support=[])
                rows.append(cur)
            elif kind in ("Customer", "Context"):
                if cur is None:
                    cur = dict(base, customer=[], support=[]); rows.append(cur)
                cur["customer" if kind == "Customer" else "support"].append(it.get("text", ""))
        if not rows:
            rows.append(dict(base, customer=[], support=[]))
        for k, r in enumerate(rows):
            r["first"] = k == 0
        out += rows
    return out, secs


def _look_for(prof, header, kind):
    for look, k in ((prof.get("rules") or {}).get(header) or {}).items():
        if k == kind:
            return look
    return None


def _font(look):
    from openpyxl.cell.text import InlineFont
    col = look[2:]
    return InlineFont(b=look[0] == "B" or None, i=look[1] == "I" or None, color=None if col == "auto" else "FF" + col)


def write_back(M, out, config_dir, effort_path):
    """See the module text. Returns {"path", "rows", "changes"}."""
    from openpyxl import load_workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    last, src = _kept(M, effort_path)
    book = OX.read(src, known=OL.known_names(config_dir))
    prof = OL.profile(config_dir, book)
    wb = load_workbook(src, rich_text=True)
    ws = wb.worksheets[0]                                       # the sheet the reader reads
    hr = book["header_row"]
    heads = book["headers"]
    role_col = {}
    for i, h in enumerate(heads):
        r = (prof["columns"] or {}).get(h)
        if r and r != "ignore" and r not in role_col:
            role_col[r] = i + 1
    pattern = {c: copy.copy(ws.cell(row=hr + 1, column=c)._style) for c in range(1, len(heads) + 1)}
    height = ws.row_dimensions[hr + 1].height
    if ws.max_row > hr:
        ws.delete_rows(hr + 1, ws.max_row - hr)
    rows, secs = rows_now(M)
    h_of = {r: heads[c - 1] for r, c in role_col.items()}
    for n, r in enumerate(rows, start=hr + 1):
        for c in range(1, len(heads) + 1):
            ws.cell(row=n, column=c)._style = copy.copy(pattern[c])
        if height:
            ws.row_dimensions[n].height = height

        def put(role, val, n=n):
            if role in role_col and val not in ("", None):
                ws.cell(row=n, column=role_col[role]).value = val
        put("section_number", r["num"]); put("section_name", r["title"])
        put("reference", r["ref"])
        if r["first"]:
            put("authors", "; ".join(r["authors"]))
        if "requirement" in role_col and r["req"]:
            lk = _look_for(prof, h_of["requirement"], "rfp")
            put("requirement", CellRichText([TextBlock(_font(lk), r["req"])]) if lk and lk != "--auto" else r["req"])
        parts = [("customer", t) for t in r["customer"]] + [("support", t) for t in r["support"]]
        if "support" in role_col and parts:
            blocks = []
            for kind, t in parts:
                lk = _look_for(prof, h_of["support"], kind) or ("-Iauto" if kind == "support" else "--auto")
                blocks.append(TextBlock(_font(lk), t + (" " if (kind, t) != parts[-1] else "")))
            put("support", CellRichText(blocks))
        put("guidance", r["guidance"])
    now = {"rows": [dict(r) for r in rows], "sections": secs, "headers": heads}
    changes = OV.compare(M, None, None, old=last, new_record=now)
    if "Changes" in wb.sheetnames:
        del wb["Changes"]
    cs = wb.create_sheet("Changes")
    cs.append(["Change", "Section", "Was", "Now"])
    for c in changes:
        cs.append([c["kind"] + (f" ({c['what']})" if c["kind"] == "Changed" else ""), c["section"], c["old"], c["new"]])
    if not changes:
        cs.append(["No changes since version " + str(last["v"]), "", "", ""])
    for col, wd in zip("ABCD", (24, 36, 60, 60)):
        cs.column_dimensions[col].width = wd
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + ".part.xlsx"
    wb.save(tmp)
    os.replace(tmp, out)
    return {"path": out, "rows": len(rows), "changes": len(changes)}
