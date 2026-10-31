"""A volume-shaped test document for the caption, TOC, bookmark and cross-reference audits, with the expected
findings as the answer key. No real content.

Planted problems (rule key -> count):
  C1 typed caption number (1)        C2 appendix caption in the body list (1)     C4 caption numbers out of order (2)
  C6 period+space after the number (1)  C7 figure caption in the top row (1)
  T2 main TOC with \\o (1)  T3 levels differ (1)  T5 list scoped by a bookmark (1)  T7 hand-typed TOC lines (1)
  B1 response scope bookmark ends inside the appendix (1)  B3 unused _Ref target (1)
  X1 cross-reference to a deleted target (1)  X3 stale cross-reference (1)  X4 MERGEFORMAT on a REF (1)
"""
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

EXPECTED = {"C1": 1, "C2": 1, "C4": 2, "C6": 1, "C7": 1, "T2": 1, "T3": 1, "T5": 1, "T7": 1, "B1": 1, "B3": 1,
            "X1": 1, "X3": 1, "X4": 1}


class Builder:
    def __init__(self):
        self.doc = Document()
        for name in ("Caption", "TOC Heading", "TOC 1", "TOC 2", "Table of Figures", "Heading 7", "Heading 8"):
            try:
                self.doc.styles[name]
            except KeyError:
                from docx.enum.style import WD_STYLE_TYPE
                self.doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        self.bid = 100

    def p(self, text="", style=None):
        par = self.doc.add_paragraph(style=style)
        if text:
            par.add_run(text)
        return par

    def field(self, par, instr, result):
        for kind in ("begin", "instr", "separate", "result", "end"):
            r = par.add_run()
            if kind in ("begin", "separate", "end"):
                fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
            elif kind == "instr":
                it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._r.append(it)
            else:
                if "\t" in result:
                    a, b = result.split("\t", 1)
                    r.add_text(a); r._r.append(OxmlElement("w:tab")); r.add_text(b)
                else:
                    r.text = result

    def field_span(self, instr, entries, style):
        """A field whose begin is in the first entry paragraph and whose end is in the last (a Word TOC)."""
        pars = [self.p(None, style) for _ in entries]
        first, last = pars[0], pars[-1]
        for kind in ("begin", "instr", "separate"):
            r = first.add_run()
            if kind == "instr":
                it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._r.append(it)
            else:
                fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        for par, text in zip(pars, entries):
            a, b = text.split("\t", 1)
            r = par.add_run(a); r._r.append(OxmlElement("w:tab")); r.add_text(b)
        r = last.add_run(); fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), "end"); r._r.append(fc)
        return pars

    def bm_start(self, par, name, before=True):
        self.bid += 1
        s = OxmlElement("w:bookmarkStart"); s.set(qn("w:id"), str(self.bid)); s.set(qn("w:name"), name)
        if before:
            par._p.insert(1 if par._p.pPr is not None else 0, s)
        else:
            par._p.append(s)
        return str(self.bid)

    def bm_end(self, par, bid):
        e = OxmlElement("w:bookmarkEnd"); e.set(qn("w:id"), bid); par._p.append(e)

    def caption(self, par, label, chap, n, title, ident=None, chap_field="STYLEREF 1 \\s", after=".\t", typed=False,
                bookmark=None):
        par.style = self.doc.styles["Caption"]
        bid = self.bm_start(par, bookmark) if bookmark else None
        par.add_run(label + " ")
        if typed:
            par.add_run(f"{chap}-{n}")
        else:
            self.field(par, chap_field, chap)
            par.add_run("-")
            self.field(par, f"SEQ {ident or label} \\* ARABIC \\s {'7' if 'STYLEREF 7' in chap_field else '1'}", str(n))
        if bid:
            self.bm_end(par, bid)
        par.add_run(after + title)

    def table_with_caption(self, rows, cols, label, chap, n, title, caption_row="first", **kw):
        t = self.doc.add_table(rows=rows, cols=cols)
        r = 0 if caption_row == "first" else rows - 1
        c = t.rows[r].cells[0].merge(t.rows[r].cells[cols - 1]) if cols > 1 else t.rows[r].cells[0]
        self.caption(c.paragraphs[0], label, chap, n, title, **kw)
        for i in range(rows):
            if i != r:
                for j in range(cols):
                    t.rows[i].cells[j].text = f"r{i}c{j}"
        return t


def make(path):
    b = Builder()
    b.p("Example Program Technical Volume", "Title")
    b.p("Table of Contents", "TOC Heading")
    b.field_span('TOC \\o "1-3" \\h \\z \\u', ["1 Introduction\t1", "2 Approach\t3"], "TOC 1")   # T2 and T3
    b.p("List of Tables", "TOC Heading")
    b.field_span('TOC \\h \\z \\b Response \\c "Table"', ["Table 1-1 Tasks\t2", "Table 1-2 Schedule\t2"],
                 "Table of Figures")                                          # T5 (bookmark scope)
    b.p("Appendix A Glossary ........ A-1", "TOC 1")                          # T7 typed by hand (after the fields)
    b.p("", None)
    h1 = b.p("Introduction", "Heading 1")
    resp = b.bm_start(h1, "Response")                                         # scope bookmark (ends too late: B1)
    b.p("This volume describes the approach.")
    cap = b.p()
    b.caption(cap, "Table", "1", 1, "Tasks and owners", bookmark="_Ref100000001")
    b.table_with_caption(3, 3, "Table", "1", 2, "Schedule", bookmark="_Ref100000002")
    b.table_with_caption(3, 3, "Table", "1", 4, "Staffing", after=". ")       # C4 (shows 4, reads 3) and C6
    b.table_with_caption(3, 3, "Table", "1", 3, "Risks", typed=True)          # C1 typed (and C4: shows 3, reads 4)
    x = b.p("See ")
    b.field(x, "REF _Ref100000001 \\h \\* CHARFORMAT", "Table 1-1")           # ok
    x.add_run(" and ")
    b.field(x, "REF _Ref100000002 \\h \\* MERGEFORMAT", "Table 1-7")          # X3 stale, X4 MERGEFORMAT
    x.add_run(" and ")
    b.field(x, "REF _Ref999999999 \\h", "Table 1-9")                          # X1 broken
    x.add_run(".")
    b.p("Approach", "Heading 1")
    fig = b.table_with_caption(2, 1, "Figure", "2", 1, "Operations concept", caption_row="first")  # C7 caption on top
    b.p("The approach follows.")
    h7 = b.p("Glossary", "Heading 7")
    b.p("Terms follow.")
    endp = b.p("End of the response scope (wrongly inside the appendix).")
    b.bm_end(endp, resp)
    b.table_with_caption(3, 2, "Table", "A", 1, "Terms", chap_field="STYLEREF 7 \\n \\t", ident="Table")   # C2
    unused = b.p("Unused target paragraph")
    bid = b.bm_start(unused, "_Ref100000003")                                 # B3 unused hidden target
    b.bm_end(unused, bid)
    b.doc.save(path)
    return EXPECTED
