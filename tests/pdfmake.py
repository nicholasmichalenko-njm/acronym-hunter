"""A plain PDF for the Final Check tests (3.58.0): one page per list of lines, Helvetica. Fictional content."""


def make_pdf(path, pages, title=""):
    """A plain PDF, one page per list of lines (Helvetica), for the tests."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for lines in pages:
        esc = [l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for l in lines]
        body = "BT /F1 11 Tf 72 740 Td 14 TL " + " ".join(f"({l}) Tj T*" for l in esc) + " ET"
        objs.append(f"<< /Length {len(body)} >>\nstream\n{body}\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {len(objs)} 0 R /Resources << /Font << /F1 3 0 R >> >> >>")
        kids.append(len(objs))
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    if title:
        objs.append(f"<< /Title ({title}) /Author (A. Writer) >>")
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R{f' /Info {len(objs)} 0 R' if title else ''} >>\nstartxref\n{x}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)
    return path


MARK = "Use or disclosure of data contained on this sheet is subject to the restriction on the title page."
filler = "The Kestrel team keeps the network on station with daily orbit planning and ground contact reviews."
body = lambda n, extra=(): [f"{n} Technical Approach Detail", filler, filler, filler] + list(extra) + [MARK, str(n)]
pages = [["Kestrel Constellation Support", "Volume I Technical", "This proposal includes data that shall not be disclosed outside the",
          "Government and shall not be duplicated, used, or disclosed for any purpose other than to evaluate this proposal."],
         ["Table of Contents", "1 Technical Approach ........ 1", "1.1 Orbit Operations ........ 2", "1.2 Ground Contacts ........ 9",
          "Acronyms ........ 5", MARK],
         body(1, ["1 Technical Approach"]), body(2, ["1.1 Orbit Operations"]), body(3, ["1.2 Ground Contacts"]),
         ["Acronyms and Abbreviations", "GS Ground Station used for every contact window in the plan", "TT&C Telemetry tracking "
          "and command for each pass of the constellation", "SOC Space Operations Center staffed every day of the year", MARK],
         ["", MARK]]
PAGES = pages
