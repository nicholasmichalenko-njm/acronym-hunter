"""Tricky tables shaped like a proposal volume's, with the role of every row set by hand (the answer key).
Built with python-docx plus raw XML for SEQ fields, fills, merges and repeat headers. No real content.

make(path) -> {"tables": [{"name", "type", "labels": [role per row], "ask_ok": set of row indexes where a
question is the right outcome}]}
"""
import copy
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def _repeat(row):
    trpr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); trpr.append(h)


def _seq_caption(par, label, title, ident=None):
    """Label, then { STYLEREF 1 \\s }-{ SEQ ident \\* ARABIC \\s 1 }, period, tab, title (the team's caption)."""
    ident = ident or label
    par.add_run(label + " ")
    for instr, res in ((r" STYLEREF 1 \s ", "2"), (None, "-"), (f" SEQ {ident} \\* ARABIC \\s 1 ", "1")):
        if instr is None:
            par.add_run(res); continue
        for kind in ("begin", None, "separate", "result", "end"):
            r = par.add_run()
            if kind in ("begin", "separate", "end"):
                fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
            elif kind is None:
                it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r._r.append(it)
            else:
                r.text = res
    par.add_run(".\t" + title)


def _merge_row(table, r):
    row = table.rows[r]
    a, b = row.cells[0], row.cells[len(row.cells) - 1]
    return a.merge(b)


def _noise(cell, font="Calibri", size=11, bold=None):
    """Direct formatting the fix must clear (it is what real tables carry)."""
    for p in cell.paragraphs:
        for r in p.runs:
            r.font.name = font; r.font.size = Pt(size)
            if bold is not None:
                r.font.bold = bold


def make(path):
    doc = Document()
    doc.add_heading("2 Technical Approach", level=1)
    key = {"tables": []}

    # ---- T1 labor hours: sections, subtotals in 3 spellings, total, empty row, note and source
    doc.add_paragraph("Table 2-1 lists the labor hours.")
    data = [("cap", None), ("hdr", ["WBS", "Task", "Engineer III", "Analyst II", "Total hours"]),
            ("hdr2", ["", "", "(hours)", "(hours)", ""]), ("sub", "1.0 Program Management"),
            ("body", ["1.1", "Program planning", "320", "160", "480"]), ("body", ["1.2", "Risk management", "120", "240", "360"]),
            ("subtot", ["", "Subtotal, Program Management", "440", "400", "840"]), ("sub", "2.0 Systems Engineering"),
            ("body", ["2.1", "Requirements analysis", "880", "240", "1,120"]), ("body", ["2.2", "Interface control", "640", "160", "800"]),
            ("subdash", ["", "Subtotal - Systems Engineering", "1,520", "400", "1,920"]), ("empty", None),
            ("sub", "3.0 Operations"), ("body", ["3.1", "Mission operations", "1,200", "600", "1,800"]),
            ("sectot", ["", "3.0 total", "1,200", "600", "1,800"]), ("tot", ["", "Total hours", "3,160", "1,400", "4,560"]),
            ("note", "Note: Hours are for the base period only."), ("note", "Source: Basis of estimate, rev 3.")]
    t = doc.add_table(rows=len(data), cols=5)
    labels, ask_ok = [], set()
    for i, (kind, val) in enumerate(data):
        row = t.rows[i]
        if kind == "cap":
            c = _merge_row(t, i); _seq_caption(c.paragraphs[0], "Table", "Labor hours by task and labor category"); labels.append("caption")
        elif kind in ("hdr", "hdr2"):
            for j, v in enumerate(val):
                row.cells[j].text = v; _shade(row.cells[j], "D9E2F3"); _noise(row.cells[j], bold=True)
            _repeat(row); labels.append("header" if kind == "hdr" else "header2")
        elif kind == "sub":
            c = _merge_row(t, i); c.text = val; _shade(c, "D9D9D9"); labels.append("subhead")
        elif kind == "empty":
            labels.append("keep"); ask_ok.add(i)
        elif kind == "note":
            c = _merge_row(t, i); c.text = val; labels.append("note")
        else:
            for j, v in enumerate(val):
                row.cells[j].text = v; _noise(row.cells[j])
            labels.append({"body": "body", "subtot": "subtotal", "subdash": "subtotal", "sectot": "subtotal", "tot": "total"}[kind])
            if kind == "sectot":
                ask_ok.add(i)
    key["tables"].append({"name": "Labor hours (sections, subtotals, notes)", "type": "std", "labels": labels, "ask_ok": ask_ok})

    # ---- T2 compliance matrix: 150 rows over several pages, gray subheads by fill, no notes
    doc.add_paragraph("Table 2-2 is the compliance matrix.")
    n = 150
    t = doc.add_table(rows=n, cols=4)
    labels = []
    c = _merge_row(t, 0); _seq_caption(c.paragraphs[0], "Table", "Requirements compliance matrix"); labels.append("caption")
    for j, v in enumerate(["RFP reference", "Requirement", "Proposal section", "Page"]):
        t.rows[1].cells[j].text = v
    _repeat(t.rows[1]); labels.append("header")
    for i in range(2, n):
        if (i - 2) % 25 == 0:
            for j in range(4):
                t.rows[i].cells[j].text = (f"Section C.{(i - 2) // 25 + 1}" if j == 0 else ""); _shade(t.rows[i].cells[j], "BFBFBF")
            labels.append("subhead")
        else:
            for j, v in enumerate([f"C.{(i - 2) // 25 + 1}.{i}", "The contractor shall provide the service described.", f"3.{i % 9}", str(10 + i // 3)]):
                t.rows[i].cells[j].text = v
            _noise(t.rows[i].cells[1], font="Arial", size=10)
            labels.append("body")
    key["tables"].append({"name": "Compliance matrix (150 rows, several pages)", "type": "cm", "labels": labels, "ask_ok": set()})

    # ---- T3 key personnel: caption not merged (text in cell 1, others empty), bold-only subhead row
    doc.add_paragraph("Table 2-3 names the key personnel.")
    t = doc.add_table(rows=7, cols=3)
    labels, ask_ok = [], set()
    _seq_caption(t.rows[0].cells[0].paragraphs[0], "Table", "Key personnel"); labels.append("caption")
    for j, v in enumerate(["Name", "Role", "Clearance"]):
        t.rows[1].cells[j].text = v
    labels.append("header")
    t.rows[2].cells[0].text = "Program office"; _noise(t.rows[2].cells[0], bold=True); labels.append("subhead"); ask_ok.add(2)
    for i, (a, b, cl) in enumerate([("Jordan Reyes", "Program Manager", "TS"), ("Avery Chen", "Chief Engineer", "TS"),
                                    ("Sam Patel", "Deputy PM", "S")], start=3):
        for j, v in enumerate((a, b, cl)):
            t.rows[i].cells[j].text = v
        labels.append("body")
    c = _merge_row(t, 6); c.text = "Notes: Clearances are current as of submission."; labels.append("note")
    key["tables"].append({"name": "Key personnel (caption not merged, bold subhead)", "type": "kp", "labels": labels, "ask_ok": ask_ok})

    # ---- T4 figure table: picture row, caption in the bottom row
    doc.add_paragraph("Figure 2-1 shows the concept.")
    t = doc.add_table(rows=2, cols=1)
    import io, struct, zlib
    def png(w=120, h=60):
        raw = b"".join(b"\x00" + bytes([200, 210, 225]) * w for _ in range(h))
        def chunk(tag, data): return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    t.rows[0].cells[0].paragraphs[0].add_run().add_picture(io.BytesIO(png()), width=Inches(4))
    _seq_caption(t.rows[1].cells[0].paragraphs[0], "Figure", "Operations concept")
    key["tables"].append({"name": "Figure table (caption in the bottom row)", "type": "fig", "labels": ["body", "caption"], "ask_ok": set()})

    # ---- T5 no caption row: starts with a header; a Grand total row; a one-cell row with no fill
    doc.add_paragraph("A table without a caption row.")
    t = doc.add_table(rows=6, cols=3)
    labels, ask_ok = [], set()
    for j, v in enumerate(["Item", "Quantity", "Cost"]):
        t.rows[0].cells[j].text = v
    labels.append("header"); ask_ok.add(0)          # no caption: the header is asked, not known by position
    c = _merge_row(t, 1); c.text = "Hardware"; labels.append("subhead"); ask_ok.add(1)
    for i, (a, b, cc) in enumerate([("Antenna", "2", "40,000"), ("Receiver", "4", "22,000")], start=2):
        for j, v in enumerate((a, b, cc)):
            t.rows[i].cells[j].text = v
        labels.append("body")
    for j, v in enumerate(["Grand total", "6", "62,000"]):
        t.rows[4].cells[j].text = v
    labels.append("total")
    c = _merge_row(t, 5); c.text = "Prices are in fiscal year 2027 dollars."; labels.append("note"); ask_ok.add(5)
    key["tables"].append({"name": "No caption row (header unknown by position)", "type": "std", "labels": labels, "ask_ok": ask_ok})

    doc.save(path)
    return key
