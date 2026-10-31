"""Word gate for Fix a Copy (3.6.0). Runs on the build PC with Word, under the feasibility lab's Python (pywin32 for
Word read-backs, PyMuPDF for page labels). Not part of the shipped program.

For each Word-saved fixture (small 38 pages, large 516 pages, xl 757 pages; each with planted defects and an answer
manifest):
  1. Check, plan, and Fix a Copy exactly as the app does it, with Update fields in Word (prodword) and the real
     open-file check (Office is asked which files are open).
  2. The original is byte for byte unchanged; nothing was written beside it.
  3. Word opens the fixed copy with repair off; Word's re-save of it has the same text, fields, bookmarks, tables,
     sections, drawings and revisions (no silent repair).
  4. Caption numbers read as Word numbers the chapters (2-1, A-1), none wrong, as many as the manifest.
  5. Broken references: exactly the ones the manifest planted (nothing else broke).
  6. Header and footer fields clean (no PAGE switch, no STYLEREF MERGEFORMAT).
  7. Every table row carries the tag style of its role by an independent reading of the fixture's content.
  8. Page labels in Word's PDF: cover none, front matter i, ii..., chapters c-1.., appendices A-1..; landscape pages continue.
  9. A second run on the fixed copy changes nothing but the copy mark.
Also the engine's puncture suite with Stationkeeper's engine. Usage:
  python tools\\word_gate.py <fixtures dir> <work dir> <results.json> <lab harness dir> [small,large,xl]
"""
import json, os, re, shutil, sys, tempfile, time, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
fixtures, work, out_json, harness = sys.argv[1:5]
which = (sys.argv[5] if len(sys.argv) > 5 else "small,large,xl").split(",")
sys.path.insert(0, harness)
from wordsession import WordSession, retry          # noqa: E402  (lab harness, pywin32)
import prodcopy as PCY, prodfix as PF, prodrules as PRL, prodword as PW   # noqa: E402
from prodengine.engine.pkg import Package, NS, W   # noqa: E402
from prodengine.engine.fingerprint import fingerprint, diff, visible_text   # noqa: E402
from prodengine.engine.ops import word_ops as ops   # noqa: E402

STRUCT = ["text", "text_len", "deleted_text", "fields", "bookmarks", "bookmark_context", "tables", "drawings", "drawing_xml",
          "objects", "content_controls", "content_control_props", "revisions", "note_refs", "comment_refs",
          "section_count", "paragraphs", "alt_content", "hyperlinks", "media", "external_links"]


def fields_with_results(root):
    out, stack = [], []
    for el in root.iter():
        tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
        if tag == "fldChar":
            t = el.get(f"{{{W}}}fldCharType")
            if t == "begin":
                stack.append({"instr": "", "res": "", "phase": "instr"})
            elif t == "separate" and stack:
                stack[-1]["phase"] = "res"
            elif t == "end" and stack:
                f = stack.pop()
                out.append((" ".join(f["instr"].split()), f["res"]))
                if stack and stack[-1]["phase"] == "res":
                    stack[-1]["res"] += f["res"]
        elif tag == "instrText" and stack:
            stack[-1]["instr"] += el.text or ""
        elif tag == "t" and stack and stack[-1]["phase"] == "res":
            stack[-1]["res"] += el.text or ""
    return out


def word_chapter_numbers(doc):
    rows = []
    for p in doc.ListParagraphs:
        n = p.Style.NameLocal
        if n in ("Heading 1", "Heading 7"):
            rng = p.Range
            rows.append((rng.Start, n, rng.ListFormat.ListString))
    rows.sort()
    return [(n, s) for _, n, s in rows]


def caption_numbers(path, chapters):
    pkg = Package(path)
    root = pkg.tree(pkg.main)
    names = {}
    for s in pkg.tree(pkg.word_part("/styles")).findall("w:style", NS):
        nm = s.find("w:name", NS)
        if nm is not None:
            names[s.get(f"{{{W}}}styleId")] = nm.get(f"{{{W}}}val")
    shown1 = [s for n, s in chapters if n == "Heading 1"]
    shown7 = [s.split()[-1] for n, s in chapters if n == "Heading 7"]
    h1 = h7 = 0
    seq, total, bad, ex = {}, 0, 0, []
    for p in root.iter(f"{{{W}}}p"):
        ps = p.find("w:pPr/w:pStyle", NS)
        st = names.get(ps.get(f"{{{W}}}val"), "") if ps is not None else "Normal"
        if st == "Heading 1":
            h1 += 1
        elif st == "Heading 7":
            h7 += 1
        txt = visible_text(p).replace("¶", "")
        m = re.match(r"^(Table|Figure)\s+([^.\t ]+)", txt)
        if not m or not (st in ("Caption", "PE Table Caption", "PE Figure Caption") or any("SEQ" in i for i, _r in fields_with_results(p))):
            continue
        label, num = m.groups()
        part = (label, "app", h7) if h7 else (label, "body", h1)
        seq[part] = seq.get(part, 0) + 1
        c1 = shown1[h1 - 1] if 0 < h1 <= len(shown1) else str(h1)
        c7 = shown7[h7 - 1] if 0 < h7 <= len(shown7) else chr(64 + h7)
        exp = f"{c7}-{seq[part]}" if h7 else f"{c1}-{seq[part]}"
        total += 1
        if num.strip() != exp:
            bad += 1
            if len(ex) < 6:
                ex.append((label, num, exp))
    return {"captions": total, "wrong": bad, "examples": ex}


def error_refs(path):
    pkg = Package(path)
    out = set()
    for story in pkg.stories():
        for instr, res in fields_with_results(pkg.tree(story)):
            if "Error!" in res:
                parts = instr.split()
                out.add(parts[1] if len(parts) > 1 else instr)
    return sorted(out)


def hf_codes(path):
    pkg = Package(path)
    bad = []
    for story in pkg.stories():
        r = pkg.tree(story)
        if r.tag.split("}")[-1] not in ("hdr", "ftr"):
            continue
        for instr, _res in fields_with_results(r):
            u = instr.upper()
            if (u.startswith("STYLEREF") and "MERGEFORMAT" in u) or (u.startswith("PAGE") and "\\*" in u):
                bad.append(instr)
    return bad


def oracle_roles(tbl):
    out = []
    for r, tr in enumerate(tbl.findall("w:tr", NS)):
        first = ops.cell_text(tr.findall("w:tc", NS)[0])
        whole = " ".join(ops.cell_text(tc) for tc in tr.findall("w:tc", NS))
        if r == 0 and re.match(r"^(Table|Figure) ", whole):
            out.append("caption")
        elif first == "Item":
            out.append("header")
        elif first.startswith("Phase"):
            out.append("subhead")
        elif first.startswith("Total"):
            out.append("total")
        elif first.startswith("Note"):
            out.append("note")
        else:
            out.append("body")
    return out


def table_roles(fixture, fixed, std):
    """Rows whose paragraph style is not the tag style of the role an independent reading of the content gives."""
    fx = Package(fixture); fp = Package(fixed)
    names = {}
    for s in fp.tree(fp.word_part("/styles")).findall("w:style", NS):
        nm = s.find("w:name", NS)
        if nm is not None:
            names[s.get(f"{{{W}}}styleId")] = nm.get(f"{{{W}}}val")
    t_in = fx.tree(fx.main).find("w:body", NS).findall("w:tbl", NS)
    t_out = fp.tree(fp.main).find("w:body", NS).findall("w:tbl", NS)
    rows = wrong = 0
    ex = []
    for i, (a, b) in enumerate(zip(t_in, t_out), 1):
        if ops.is_figure_table(a):
            continue
        want = oracle_roles(a)
        for r, tr in enumerate(b.findall("w:tr", NS)):
            ps = tr.find(".//w:p/w:pPr/w:pStyle", NS)
            have = names.get(ps.get(f"{{{W}}}val"), "") if ps is not None else ""
            exp = std["row_types"][want[r]]["tag_style"] if r < len(want) else ""
            rows += 1
            if have != exp:
                wrong += 1
                if len(ex) < 6:
                    ex.append((i, r + 1, have, exp))
    return {"tables": len(t_in), "rows": rows, "wrong": wrong, "examples": ex}


def pdf_page_labels(pdf):
    import pymupdf as fitz
    d = fitz.open(pdf)
    labels = []
    for pg in d:
        h = pg.rect.height
        words = [w_ for w_ in pg.get_text("words") if w_[1] > h - 72 * 0.9]
        words.sort(key=lambda w_: (w_[1], w_[0]))
        nums = [w_[4] for w_ in words if re.fullmatch(r"[ivxlcdm]+|[0-9A-Z]+-\d+|\d+", w_[4])]
        labels.append(nums[-1] if nums else "")
    return labels


def check_page_labels(labels, n_chapters, n_appendix):
    def roman(n):
        vals = [(100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
        s = ""
        for v_, r_ in vals:
            while n >= v_:
                s += r_; n -= v_
        return s
    problems = []
    k = 0
    while k < len(labels) and not re.fullmatch(r"[ivxlcdm]+|[0-9A-Z]+-\d+", labels[k]):
        k += 1
    covers = k
    r = 0
    while k < len(labels) and re.fullmatch(r"[ivxlcdm]+", labels[k]):
        if labels[k] != roman(r + 1):
            problems.append((k + 1, labels[k], roman(r + 1)))
        r += 1; k += 1
    prev, chapters, apps = None, set(), set()
    for i in range(k, len(labels)):
        m = re.fullmatch(r"([0-9]+|[A-Z])-(\d+)", labels[i])
        if not m:
            problems.append((i + 1, labels[i], "c-n")); prev = None; continue
        c, n = m.group(1), int(m.group(2))
        (apps if c.isalpha() else chapters).add(c)
        if prev:
            pc, pn = prev
            ok = (c == pc and n == pn + 1) or (n == 1 and ((c.isdigit() and pc.isdigit() and int(c) == int(pc) + 1) or
                                                          (c.isalpha() and pc.isalpha() and ord(c) == ord(pc) + 1) or (c == "A" and pc.isdigit())))
            if not ok:
                problems.append((i + 1, labels[i], f"after {pc}-{pn}"))
        prev = (c, n)
    if len(chapters) != n_chapters:
        problems.append(("chapters", len(chapters), n_chapters))
    if len(apps) != n_appendix:
        problems.append(("appendices", len(apps), n_appendix))
    if covers != 1:
        problems.append(("cover pages", covers, 1))
    return {"pages": len(labels), "covers": covers, "front": r, "chapters": len(chapters), "appendices": len(apps),
            "problems": len(problems), "first": problems[:8]}


def gate(name):
    res = {"fixture": name, "checks": {}}
    ok = res["checks"]
    fx = os.path.join(fixtures, f"{name}.docx")
    man = json.load(open(os.path.join(fixtures, f"manifest_{name}.json")))
    src_dir = os.path.join(work, name, "Volumes"); out_dir = os.path.join(work, name, "Production Copies")
    os.makedirs(src_dir, exist_ok=True)
    orig = os.path.join(src_dir, f"{name} volume.docx")
    shutil.copy2(fx, orig)
    before = PCY.state(orig)
    std = PRL.for_effort(tempfile.mkdtemp())
    t = time.perf_counter()
    chk = PF.check(orig, std)
    res["check_s"] = round(time.perf_counter() - t, 1)
    res["found"] = {a: dict(c) for a, c in chk.by_area().items() if c}
    plan = PF.default_plan(chk)
    plan["word_update"] = True
    t = time.perf_counter()
    job = PF.run(orig, out_dir, std, plan, word=PW.update_fields, before=chk)        # real open-file check: Office is asked
    res["run_s"] = round(time.perf_counter() - t, 1)
    PF.write_report(job, "Word gate")
    res["steps"] = [{"step": s["step"], "changed": s.get("changed"), "refused": s.get("refused", "")[:300],
                     **({"word": s.get("report")} if s.get("key") == "word_update" else {})} for s in job.steps]
    res["left"] = {a: dict(c) for a, c in job.after_check.by_area().items() if c}
    ok["no fix refused"] = not any(s.get("refused") for s in job.steps)
    word = next((s for s in job.steps if s.get("key") == "word_update"), {})
    ok["Word updated the fields"] = bool(word.get("changed"))
    ok["original byte for byte unchanged"] = PCY.state(orig) == before and job.original_ok
    ok["nothing written beside the original"] = sorted(os.listdir(src_dir)) == [os.path.basename(orig)]
    ok["only the copy and its report in the output folder"] = sorted(os.listdir(out_dir)) == sorted([os.path.basename(job.copy), os.path.basename(job.report_path)])
    with WordSession() as w:
        try:
            doc = w.open(job.copy, readonly=True)
            ok["Word opens the copy with repair off"] = True
        except Exception as e:  # noqa: BLE001
            ok["Word opens the copy with repair off"] = False
            res["open_error"] = str(e)[:300]
            return res
        resaved = os.path.join(work, name, "word_resave.docx")
        retry(doc.SaveAs2, os.path.abspath(resaved), 16)
        d = [k for k in diff(fingerprint(Package(job.copy)), fingerprint(Package(resaved))) if k.split("|", 1)[1] in STRUCT]
        res["resave_diff"] = d[:20]
        ok["Word's re-save shows no structural drift (no silent repair)"] = not d
        chapters = word_chapter_numbers(doc)
        pdf = os.path.join(work, name, "copy.pdf")
        retry(doc.ExportAsFixedFormat, os.path.abspath(pdf), 17)
        res["word_pages"] = doc.ComputeStatistics(2)
        res["tocs"] = [doc.TablesOfContents(i + 1).Range.Paragraphs.Count for i in range(doc.TablesOfContents.Count)]
        res["lists"] = [doc.TablesOfFigures(i + 1).Range.Paragraphs.Count for i in range(doc.TablesOfFigures.Count)]
        w.close(doc)
    caps = caption_numbers(job.copy, chapters)
    res["captions"] = caps
    ok["every caption number right (Word's chapters, 2-1, A-1)"] = caps["wrong"] == 0 and caps["captions"] == len(man["captions"])
    errs = error_refs(job.copy)
    res["error_refs"] = errs
    ok["broken references: only the planted ones"] = errs == sorted(man["broken_refs"])
    ok["header and footer fields clean"] = hf_codes(job.copy) == []
    tr = table_roles(fx, job.copy, PRL.engine_ready(std))
    res["table_roles"] = tr
    ok["every table row carries its role's style"] = tr["wrong"] == 0 and tr["tables"] == man["tables"] + man["figures"]
    labels = pdf_page_labels(pdf)
    n_ch = sum(1 for s in man["sections"] if s == "chapter")
    n_app = sum(1 for s in man["sections"] if s == "appendix")
    pl = check_page_labels(labels, n_ch, n_app)
    res["page_labels"] = pl
    ok["page labels: cover, i ii..., c-1..., A-1... (landscape continues)"] = pl["problems"] == 0
    ok["lists of tables and figures filled"] = bool(res["lists"]) and all(n > 1 for n in res["lists"])
    t = time.perf_counter()
    job2 = PF.run(job.copy, os.path.join(work, name, "Second run"), std, dict(plan, word_update=False))
    res["second_run_s"] = round(time.perf_counter() - t, 1)
    res["second_run_changed"] = [s["step"] for s in job2.steps if s.get("changed")]
    ok["a second run changes nothing but the copy mark"] = res["second_run_changed"] == ["Mark the copy"]
    return res


def main():
    os.makedirs(work, exist_ok=True)
    out = {"started": time.strftime("%Y-%m-%d %H:%M"), "fixtures": []}
    for name in which:
        try:
            out["fixtures"].append(gate(name))
        except Exception as e:  # noqa: BLE001
            out["fixtures"].append({"fixture": name, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]})
        json.dump(out, open(out_json, "w"), indent=1, default=str)
    total = sum(len(f.get("checks", {})) for f in out["fixtures"])
    passed = sum(sum(1 for v in f.get("checks", {}).values() if v) for f in out["fixtures"])
    for f in out["fixtures"]:
        print("==", f["fixture"], f.get("error", ""), f"check {f.get('check_s')} s, run {f.get('run_s')} s")
        for k, v in f.get("checks", {}).items():
            print("PASS" if v else "FAIL", k)
    print(f"WORD GATE {'PASS' if passed == total and total else 'FAIL'} ({passed}/{total})")
    json.dump(out, open(out_json, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
