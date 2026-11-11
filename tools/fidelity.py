"""How faithful Redline's copy is to its PDF (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, step 1).

For each fictional fixture PDF (test_samples/fidelity/<set>/Fnn_*.pdf) it makes the copy and scores:
- words: the copy against the PDF word for word (redlinecheck.faithful); 0 differences is a pass;
- tables: each table the fixture's Word file holds (fidelity_truth.json) found in the copy exactly: every row, every
  cell's text, and how many columns and rows each cell spans;
- pages: the copy's page sizes and orientations against the PDF's;
- the 4.12.0 way (tables from aligned text only), and Word's own conversion (word_reflow, made on the build PC), for the
  same tables: the baselines.
Pictures of the pages (the copy saved as PDF by Word, then compared) are scored on the build PC (tools/fidelity_pdfs.ps1).
Run: python tools/fidelity.py [set folder] [--show]. Rules only (No AI); nothing leaves the PC."""
import json, os, re, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FIX = os.path.join(ROOT, "test_samples", "fidelity")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_tables(path):
    """The copy's tables as the truth holds them: [[[{"text","cs","rs"}]]] (merged-down cells counted)."""
    from lxml import etree
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    out = []
    for tbl in root.iter(W + "tbl"):
        grid = []                                      # rows of (col, cs, kind, text)
        for tr in tbl.findall(W + "tr"):
            row, col = [], 0
            for tc in tr.findall(W + "tc"):
                pr = tc.find(W + "tcPr")
                cs = 1
                vm = None
                if pr is not None:
                    gs = pr.find(W + "gridSpan")
                    cs = int(gs.get(W + "val")) if gs is not None else 1
                    v = pr.find(W + "vMerge")
                    if v is not None:
                        vm = v.get(W + "val") or "continue"
                text = " ".join(" ".join("".join(t.text or "" for t in p.iter(W + "t")).split()) for p in tc.findall(W + "p"))
                row.append((col, cs, vm, " ".join(text.split())))
                col += cs
            grid.append(row)
        rows = []
        for ri, row in enumerate(grid):
            cells = []
            for col, cs, vm, text in row:
                if vm == "continue":
                    continue
                rs = 1
                if vm == "restart":
                    for below in grid[ri + 1:]:
                        if any(c == col and v == "continue" for c, _s, v, _t in below):
                            rs += 1
                        else:
                            break
                cells.append({"text": text, "cs": cs, "rs": rs})
            rows.append(cells)
        out.append(rows)
    return out


def docx_pages(path):
    """[(w, h) in points] of each section of the copy."""
    from lxml import etree
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    return [(round(int(s.get(W + "w")) / 20), round(int(s.get(W + "h")) / 20)) for s in root.iter(W + "pgSz")]


def _baseline(pdf, want):
    """How many of the fixture's tables the 4.12.0 way (aligned text only) gets exactly."""
    import pagesent as PS
    import redlinetables as RT
    doc = PS.read(pdf)
    doc["skip"] = PS.running(doc)
    got = [[[{"text": " ".join(c.split()), "cs": 1, "rs": 1} for c in r] for r in t["rows"]] for t in RT.find(doc, set(doc["skip"]))]
    return sum(1 for w in want if w in got)


def score(folder, show=False, keep=None):
    import pagesent as PS
    import redlinecheck as CK
    import redlinecopy as RC
    with open(os.path.join(FIX, "fidelity_truth.json"), encoding="utf-8") as f:
        truth = json.load(f)
    rows = []
    tmp = keep or tempfile.mkdtemp()
    os.makedirs(tmp, exist_ok=True)
    for stem in sorted(truth):
        pdf = os.path.join(folder, stem + ".pdf")
        if not os.path.isfile(pdf):
            continue
        want = [t["rows"] for t in truth[stem]]
        out = os.path.join(tmp, stem + " - copy.docx")
        RC.build(pdf, out)
        got = docx_tables(out)
        exact = sum(1 for w in want if w in got)
        diffs = CK.faithful(pdf, out)["differences"]
        doc = PS.read(pdf)
        sizes = sorted({(round(p["w"]), round(p["h"])) for p in doc["pages"]})
        pages_ok = set(docx_pages(out)) == set(sizes)
        wr = os.path.join(FIX, "word_reflow", stem + ".docx")          # Word's own conversion, made on the build PC
        word = sum(1 for w in want if w in docx_tables(wr)) if os.path.isfile(wr) else None
        rows.append({"fixture": stem, "tables": len(want), "exact": exact, "baseline": _baseline(pdf, want),
                     "word_diffs": len(diffs), "pages_ok": pages_ok, "word": word})
        if show and (exact < len(want) or diffs):
            for w in want:
                if w not in got:
                    print(f"  {stem} want {json.dumps(w)[:300]}")
            for g in got:
                print(f"  {stem} got  {json.dumps(g)[:300]}")
            for d in diffs[:3]:
                print(f"  {stem} {d['kind']}: {d['was']!r} -> {d['now']!r} (page {d['page']})")
    return rows


def report(rows):
    wd = lambda v: "-" if v is None else str(v)                     # noqa: E731
    lines = [f"{'Fixture':24s} {'Tables':>6s} {'Exact':>6s} {'4.12.0':>6s} {'Word':>5s} {'Word diffs':>10s} {'Pages':>6s}"]
    for r in rows:
        lines.append(f"{r['fixture']:24s} {r['tables']:6d} {r['exact']:6d} {r['baseline']:6d} {wd(r.get('word')):>5s} "
                     f"{r['word_diffs']:10d} {'same' if r['pages_ok'] else 'DIFF':>6s}")
    t = sum(r["tables"] for r in rows)
    ws = [r["word"] for r in rows if r.get("word") is not None]
    lines.append(f"{'Total':24s} {t:6d} {sum(r['exact'] for r in rows):6d} {sum(r['baseline'] for r in rows):6d} "
                 f"{(str(sum(ws)) if ws else '-'):>5s} {sum(r['word_diffs'] for r in rows):10d} {sum(r['pages_ok'] for r in rows):3d}/{len(rows)}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder = args[0] if args else os.path.join(FIX, "pdf_word_tagged")
    k = sys.argv.index("--keep") if "--keep" in sys.argv else -1
    keep = sys.argv[k + 1] if 0 <= k < len(sys.argv) - 1 else None       # the copies kept (to save as PDF and compare)
    args = [a for a in args if a != keep]
    folder = args[0] if args else os.path.join(FIX, "pdf_word_tagged")
    print(report(score(folder, show="--show" in sys.argv, keep=keep)))
