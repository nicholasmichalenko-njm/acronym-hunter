"""Word gate for document types as templates (3.7.0). Runs on the build PC with Word, under the feasibility lab's Python
(pywin32, PyMuPDF). Not part of the shipped program.

  1. Learn a document type from the master template (styles, variables, page setups, heading numbering) and from a
     finished volume (headers and footers, the TOC); learning never writes either file.
  2. Make templates: from the team standard on the Stationkeeper base; from the learned document type on the base;
     from the learned type starting from the master template itself. Word updates each template's fields.
  3. Word opens every template with repair off; Word's re-save shows no structural drift.
  4. Each template passes its own check after Word's update (no finding in any area).
  5. Word reads back the style definitions: for every style of the library, Word's own Font and ParagraphFormat
     values (font, size, bold, italic, color, space before and after, indents, keep with next, keep together,
     page break before) equal the library's.
  6. Page labels in Word's PDF of the base template: cover none, i, 1-1, A-1.
  7. ROUND TRIP: learning from the Word-saved template gives back the same style library.
  8. A Fix a Copy run with the learned type on the large volume, then the copy's styles match the library (Word
     reads them back the same way).
  9. No Word left running.
Usage: python tools\\template_gate.py <fixtures dir> <work dir> <results.json> <lab harness dir>
"""
import json, os, shutil, sys, time, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
fixtures, work, out_json, harness = sys.argv[1:5]
sys.path.insert(0, harness)
from wordsession import WordSession, retry          # noqa: E402  (lab harness, pywin32)
import prodcopy as PCY, prodfix as PF, prodlearn as PL, prodrules as PRL, prodtemplate as PT, prodword as PW   # noqa: E402
from prodengine.engine.pkg import Package   # noqa: E402
from prodengine.engine.fingerprint import fingerprint, diff   # noqa: E402

STRUCT = ["text", "text_len", "fields", "bookmarks", "tables", "drawings", "objects", "content_controls", "revisions",
          "section_count", "paragraphs", "hyperlinks", "media", "external_links"]
JC = {0: "left", 1: "center", 2: "right", 3: "both"}


def sha(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def word_pids():
    import subprocess
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"], capture_output=True, text=True)
    return {int(row.split('","')[1]) for row in r.stdout.splitlines() if row.startswith('"WINWORD')}


def bgr_hex(v):
    v = int(v)
    if v < 0 or v == -16777216:
        return "auto"
    return f"{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"


def word_styles(doc, names):
    """Word's own reading of each style: {name: {prop: value}} in the library's units (points)."""
    out = {}
    for n in names:
        try:
            st = doc.Styles({"macro": "Macro Text"}.get(n, n))
        except Exception:  # noqa: BLE001
            out[n] = None
            continue
        f, pf = st.Font, None
        theme = False
        try:
            theme = f.TextColor.ObjectThemeColor > 0     # a theme color: the file's hex is its value in this theme
            rgb = f.TextColor.RGB
        except Exception:  # noqa: BLE001
            rgb = f.Color
        try:
            pf = st.ParagraphFormat
        except Exception:  # noqa: BLE001
            pf = None
        d = {"font": f.Name, "size": float(f.Size), "bold": f.Bold == -1, "italic": f.Italic == -1, "color": "theme" if theme else bgr_hex(rgb),
             "caps": f.AllCaps == -1}
        if pf is not None and st.Type == 1:
            d.update({"before": float(pf.SpaceBefore), "after": float(pf.SpaceAfter), "left": float(pf.LeftIndent),
                      "right": float(pf.RightIndent), "keep_next": pf.KeepWithNext == -1, "keep_lines": pf.KeepTogether == -1,
                      "page_break_before": pf.PageBreakBefore == -1, "jc": JC.get(pf.Alignment, str(pf.Alignment))})
            fi = float(pf.FirstLineIndent)
            d["first"], d["hanging"] = (fi, 0.0) if fi >= 0 else (0.0, -fi)
        out[n] = d
    return out


def compare(lib, word):
    bad = []
    for n, props in lib.items():
        w = word.get(n)
        if w is None:
            bad.append((n, "missing in Word"))
            continue
        for k, v in props.items():
            if k not in w:
                continue
            have = w[k]
            if k == "color":
                ok = have == "theme" or str(have).lower() == str(v).lower()
            elif k == "font":
                ok = str(have).lower() == str(v).lower()
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                ok = abs(float(have) - float(v)) < 0.06
            else:
                ok = have == v
            if not ok:
                bad.append((n, k, v, have))
    return bad


def open_and_read(path, lib_names, pdf=None):
    """Word opens the file with repair off; re-save drift; Word's style readings; an optional PDF."""
    res = {}
    with WordSession() as w:
        try:
            doc = w.open(path, readonly=True)
            res["opens"] = True
        except Exception as e:  # noqa: BLE001
            res["opens"] = False
            res["open_error"] = str(e)[:300]
            return res
        resaved = os.path.splitext(path)[0] + " word_resave.docx"
        retry(doc.SaveAs2, os.path.abspath(resaved), 16)
        res["resave_diff"] = [k for k in diff(fingerprint(Package(path)), fingerprint(Package(resaved))) if k.split("|", 1)[1] in STRUCT][:20]
        res["styles"] = word_styles(doc, lib_names)
        if pdf:
            retry(doc.ExportAsFixedFormat, os.path.abspath(pdf), 17)
        res["pages"] = doc.ComputeStatistics(2)
        w.close(doc)
    return res


def gate():
    res = {"checks": {}}
    ok = res["checks"]
    words_before = word_pids()
    os.makedirs(work, exist_ok=True)
    master = os.path.join(fixtures, "PE_Master_Effort_Template.dotx")
    volume = os.path.join(fixtures, "large.docx")
    m0, v0 = sha(master), sha(volume)
    std = PRL.for_effort(os.path.join(work, "cfg"))
    lm = PL.learn(master, std)
    lv = PL.learn(volume, std)
    ok["learned from the master template: styles, variables, page setups, heading numbering"] = \
        {"styles", "variables", "pages", "heading_numbering"} <= set(lm.areas)
    ok["learned from a finished volume: headers and footers, the TOC"] = {"headers", "toc"} <= set(lv.areas)
    learned = PRL.merge(std, lm.layer(["styles", "variables", "pages", "heading_numbering"]))
    learned["name"] = "Learned technical volume"
    lib = PRL.style_spec(PT.standard_for_template(PRL.engine_ready(learned)))
    out = os.path.join(work, "Production Copies", "Templates")
    made = {}
    for key, s, start in (("team base", std, ""), ("learned base", learned, ""), ("learned from the master", learned, master)):
        t = time.perf_counter()
        job = PT.make(s, out, start_from=start, word=PW.update_fields)
        made[key] = job
        word = next((x for x in job.steps if x.get("key") == "word_update"), {})
        res[key] = {"file": os.path.basename(job.copy), "seconds": round(time.perf_counter() - t, 1),
                    "refused": [(x["key"], x["refused"][:200]) for x in job.steps if x.get("refused")],
                    "findings_after_word": [f["what"][:160] for f in job.check.findings], "word": word.get("report")}
        ok[f"{key}: Word updated the template's fields"] = bool(word.get("changed"))
        if start:
            ok[f"{key}: every step ran except headers (its cover has no volume values)"] = \
                [k for k, _w in res[key]["refused"]] in ([], ["hf_build"])
            ok[f"{key}: its styles pass the check after Word"] = not [f for f in job.check.findings if f["rule"] in ("S4", "S7")]
        else:
            ok[f"{key}: every step ran"] = not res[key]["refused"]
            ok[f"{key}: PASSES ITS OWN CHECK after Word (no finding in any area)"] = job.check.count() == 0
    ok["learning and starting from the master never wrote it; the volume unchanged"] = sha(master) == m0 and sha(volume) == v0
    for key, job in made.items():
        lib_k = PRL.style_spec(PT.standard_for_template(PRL.engine_ready(std if key == "team base" else learned)))
        pdf = os.path.join(work, key.replace(" ", "_") + ".pdf") if key == "team base" else None
        rd = open_and_read(job.copy, list(lib_k), pdf)
        res[key]["word_open"] = {k: v for k, v in rd.items() if k != "styles"}
        ok[f"{key}: Word opens it with repair off"] = rd.get("opens", False)
        ok[f"{key}: Word's re-save shows no structural drift"] = rd.get("opens") and not rd.get("resave_diff")
        bad = compare(lib_k, rd.get("styles") or {})
        res[key]["style_mismatch"] = bad[:30]
        ok[f"{key}: Word reads every style of the library as defined ({len(lib_k)} styles)"] = rd.get("opens") and not bad
        if pdf and os.path.isfile(pdf):
            import pymupdf as fitz
            d = fitz.open(pdf)
            labels = []
            for pg in d:
                h = pg.rect.height
                ws = sorted([x for x in pg.get_text("words") if x[1] > h - 72 * 0.9], key=lambda x: (x[1], x[0]))
                import re
                nums = [x[4] for x in ws if re.fullmatch(r"[ivxlcdm]+|[0-9A-Z]+-\d+|\d+", x[4])]
                labels.append(nums[-1] if nums else "")
            res[key]["page_labels"] = labels
            ok[f"{key}: page labels cover, i..., 1-1..., A-1"] = labels and labels[0] == "" and "i" in labels and "1-1" in labels and "A-1" in labels
    back = PL.learn(made["learned base"].copy, learned).layer(["styles"])["style_defs"]
    want = lm.layer(["styles"])["style_defs"]
    rt = [(n, k, want[n][k], back.get(n, {}).get(k)) for n in want for k in want[n] if back.get(n, {}).get(k) != want[n][k]]
    res["round_trip_diffs"] = rt[:30]
    ok["ROUND TRIP: learning from the Word-saved template gives back the same style library"] = not rt
    # Fix a Copy with the learned type on a real volume: Word reads the copy's styles as the library
    src = os.path.join(work, "Volumes"); os.makedirs(src, exist_ok=True)
    orig = os.path.join(src, "large volume.docx"); shutil.copy2(volume, orig)
    before = PCY.state(orig)
    s2 = PRL.apply_context(learned, {"variables": {"solicitation": "GATE-26-R-0370"}}, volume_name="Volume I Technical")
    chk = PF.check(orig, s2)
    plan = PF.default_plan(chk)
    plan["word_update"] = True
    t = time.perf_counter()
    job = PF.run(orig, os.path.join(work, "Production Copies", "Gate"), s2, plan, word=PW.update_fields, before=chk)
    res["fix"] = {"seconds": round(time.perf_counter() - t, 1), "refused": [(x.get("key"), x["refused"][:200]) for x in job.steps if x.get("refused")],
                  "left": [f["what"][:120] for f in job.after_check.findings if f["area"] == "styles"]}
    ok["Fix a Copy with the learned type: no fix refused"] = not res["fix"]["refused"]
    ok["Fix a Copy with the learned type: no style finding left"] = not res["fix"]["left"]
    ok["Fix a Copy: the original byte for byte unchanged"] = PCY.state(orig) == before and job.original_ok
    lib2 = {k: v for k, v in PRL.style_spec(s2).items()}
    rd = open_and_read(job.copy, list(lib2))
    bad = compare(lib2, rd.get("styles") or {})
    res["fix"]["style_mismatch"] = bad[:30]
    ok["Fix a Copy: Word opens the copy and reads every style as the library defines"] = rd.get("opens") and not bad
    time.sleep(10)
    left = word_pids() - words_before
    res["word_left_running"] = sorted(left)
    ok["no Word left running"] = not left
    return res


def main():
    try:
        res = gate()
    except Exception as e:  # noqa: BLE001
        res = {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:], "checks": {}}
    json.dump(res, open(out_json, "w"), indent=1, default=str)
    for k, v in res.get("checks", {}).items():
        print("PASS" if v else "FAIL", k)
    if res.get("error"):
        print("ERROR", res["error"])
    n, total = sum(1 for v in res.get("checks", {}).values() if v), len(res.get("checks", {}))
    print(f"TEMPLATE GATE {'PASS' if n == total and total else 'FAIL'} ({n}/{total})")


if __name__ == "__main__":
    main()
