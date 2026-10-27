"""2.40.0 text check: every piece of typed text in a customer document reaches the review. The raw read (straight from
the file's parts) and the program's reader agree word for word on Word (text box, table, header, footer, footnote),
PDF, PowerPoint and Excel samples; an all-caps instruction line and a short table cell are sentences to assign, not
section titles; headers and footers do not rename the section; a line that never reached the review is found."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import app_gui as A, compliance as C, textcheck as T, hardfile


def run():
    d = tempfile.mkdtemp()
    hard = hardfile.make(d)
    S = os.path.join(A.BASE_DIR, "test_samples")
    files = [hard, os.path.join(S, "rfp", "Kestrel_RFP_Sections_C_L_M.docx"), os.path.join(S, "rfp", "Kestrel_RFP_Section_L_Part2.pdf"),
             os.path.join(S, "Kestrel_Large_Briefing.pptx"), os.path.join(S, "Kestrel_Program_Manual.pdf"),
             os.path.join(S, "Kestrel_Compliance_Matrix.xlsx"), os.path.join(S, "Kestrel_Technical_Volume.docx")]
    for f in files:
        ch = A.typed_chunks(f)
        heads = []
        items = C.extract([(os.path.basename(f), ch)], heads)
        r = T.check(f, items, heads, ch)
        assert r["words"] and r["missing"] == 0 and r["pct"] == 100.0, (os.path.basename(f), r["missing"], [x for x in r["lines"] if x[2] == "missing"][:5])
        assert r["reader_missing"] == 0, (os.path.basename(f), r["reader_missing"])
        assert T.summary_text(r).startswith(f"{os.path.basename(f)}: all {r['words']} words are in the review")
    # the hard file: every part read, the all-caps instruction and the table cell are sentences
    raw = " | ".join(t for _w, t in T.raw_text(hard))
    for part in ("Text box: the Offeror shall keep", "CLIN 0001", "CUI: Kestrel", "Attachment 4, Revision B", "Footnote: test at 1E-6 torr."):
        assert part in raw, part
    assert raw.count("Text box: the Offeror") == 1                    # the old-Word copy of a text box is not counted twice
    ch = A.typed_chunks(hard)
    heads = []
    items = C.extract([("Hard_RFP.docx", ch)], heads)
    texts = [it["text"] for it in items]
    assert "NOTE TO OFFERORS: SUBMIT QUESTIONS EARLY" in texts and "CLIN 0001" in " ".join(texts), texts
    foot = next(it for it in items if it["text"].startswith("Footnote"))
    assert foot["section_title"] != "Attachment 4, Revision B" and "CUI" not in foot["section_title"], foot["section_title"]
    # a line that did not reach the review is found, with where it is
    short = [it for it in items if not it["text"].startswith("Thermal analysis report")]
    r = T.check(hard, short, heads)
    miss = [x for x in r["lines"] if x[2] == "missing"]
    assert r["missing"] >= 6 and miss and miss[0][1].startswith("Thermal analysis report") and miss[0][0] == "document", miss
    assert "not in the review yet" in T.summary_text(r)
    # 2.47.0: a line added to the review goes where it is in the document, not at the end
    import pdfmini
    pdf = pdfmini.write(os.path.join(tempfile.mkdtemp(), "o.pdf"), [["Alpha shall be first.", "Bravo shall be second.",
                                                                     "Charlie shall be third."], ["Delta shall be fourth."]])
    rows = [{"id": "A", "file": "o.pdf", "text": "Alpha shall be first."}, {"id": "X", "file": "other.pdf", "text": "Elsewhere."},
            {"id": "C", "file": "o.pdf", "text": "Charlie shall be third."}, {"id": "D", "file": "o.pdf", "text": "Delta shall be fourth."}]
    pos, new = T.positions(pdf, [r for r in rows if r["file"] == "o.pdf"], ["Bravo shall be second", "Echo is nowhere"])
    assert pos["A"] < new[0] < pos["C"] < pos["D"] and new[1] is None, (pos, new)
    assert T.insert_at(rows, "o.pdf", pos, new[0]) == 2, "before Charlie, after Alpha (the other file's row stays)"
    assert T.insert_at(rows, "o.pdf", pos, None) == 4, "not found: after the file's last row"
    assert T.insert_at(rows, "new.pdf", pos, 3) == 4, "a file with no rows yet: at the end"
    print("textcheck ok")


if __name__ == "__main__":
    run()
