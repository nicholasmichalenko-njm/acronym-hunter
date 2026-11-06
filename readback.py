"""Read-back (3.67.0, Template Studio decision 3): a template or volume made from the Studio, read back from its XML and set
against what the Studio holds. Each section's page numbering (none, i, I, 1, A-1), where it restarts, its chapter style,
orientation and paper, and whether its header or footer shows a page number; the sections matched to the volume's parts
in order; each part checked against its plan; the fields against the field recipes; Heading 7 on the same list as
Heading 1 when a part numbers from it. Word is used only to draw one page per part (draw_parts): a copy laid out by a
hidden Word, the PDF's first page of each part as a picture.

sections(path) -> [section]          assign(secs, parts) -> [(part, [section index])]
check(path, parts, recipes) -> {"rows": [{part, what, plan, file, status}], "sections", "matched", "summary"}
draw_parts(path, out_dir, parts, runner) -> {"ok", "pngs": {part id: png}, "pages", "starts"} or {"ok": False, "why"}
The file is only read; draw_parts lays out a temporary copy. Rules only; nothing leaves the PC."""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
W = "{%s}" % NS_W
FMT = {"lowerRoman": "i", "upperRoman": "I", "decimal": "1", None: "1"}
CHAP_SEP = {"hyphen": "-", "period": ".", "colon": ":", "emDash": "-", "enDash": "-"}
STATUS = ("matches", "differs", "missing")


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def _xml(z, name):
    try:
        return etree.fromstring(z.read(name), _parser())
    except (KeyError, etree.XMLSyntaxError):
        return None


def _rels(z, name="word/_rels/document.xml.rels"):
    root = _xml(z, name)
    return {r.get("Id"): r.get("Target") for r in (root if root is not None else [])}


def _plain_instrs(root):
    out = [f.get(W + "instr") or "" for f in root.iter(W + "fldSimple")]
    cur = None
    for el in root.iter(W + "fldChar", W + "instrText"):
        if el.tag == W + "fldChar":
            t = el.get(W + "fldCharType")
            if t == "begin":
                cur = ""
            elif t in ("separate", "end") and cur is not None:
                out.append(cur); cur = None
        elif cur is not None:
            cur += el.text or ""
    return [" ".join(i.split()) for i in out if i and i.strip()]


def _switch_fmt(instr):
    """The format a PAGE field's switch prints in (roman i, ROMAN I, Arabic 1), or '' when it has none."""
    m = re.search(r"\\\*\s*(roman|arabic)\b", instr, re.I)
    if not m:
        return ""
    return "1" if m.group(1).lower() == "arabic" else ("I" if m.group(1) == "ROMAN" else "i")


def _paper(w, h):
    a, b = sorted((int(w or 12240), int(h or 15840)))
    if abs(a - 12240) < 200 and abs(b - 15840) < 200:
        return "Letter"
    if abs(a - 15840) < 200 and abs(b - 24480) < 200:
        return "11x17"
    return f"{a / 1440:.1f}x{b / 1440:.1f} in"


def sections(path):
    """Each section of the body in order: {"index", "format", "restart", "start", "chapter", "sep", "orient", "paper",
    "page_number" (its header or footer shows PAGE), "first_text"}. A section without its own header or footer
    reference uses the one before it, as Word does."""
    with zipfile.ZipFile(path) as z:
        doc = _xml(z, "word/document.xml")
        if doc is None:
            return []
        rels = _rels(z)
        has_page = {}
        for rid, target in rels.items():
            if re.match(r"(header|footer)\d*\.xml$", os.path.basename(target or "")):
                part = _xml(z, "word/" + target.lstrip("/").replace("word/", ""))
                pages = [i for i in (_plain_instrs(part) if part is not None else []) if re.match(r"PAGE\b", i, re.I)]
                has_page[rid] = _switch_fmt(pages[0]) if pages else None      # None: no page number; "" : as the section says
        body = doc.find(W + "body")
        out, texts = [], []
        refs = {}                                  # (header|footer, type) -> rid, carried forward
        for el in body:
            sp = None
            if el.tag == W + "p":
                t = "".join(x.text or "" for x in el.iter(W + "t")).strip()
                if t and len(texts) < 1:
                    texts.append(t[:80])
                sp = el.find(f"{W}pPr/{W}sectPr")
            elif el.tag == W + "sectPr":
                sp = el
            if sp is None:
                continue
            for kind in ("header", "footer"):
                for r in sp.findall(f"{W}{kind}Reference"):
                    refs[(kind, r.get(W + "type") or "default")] = r.get("{%s}id" % NS_R)
            title = sp.find(W + "titlePg")
            first = title is not None and title.get(W + "val") not in ("0", "false")
            want = "first" if first else "default"
            shown = [refs.get((k, want)) or refs.get((k, "default")) for k in ("header", "footer")]
            pn = sp.find(W + "pgNumType")
            pg = sp.find(W + "pgSz")
            fmt = FMT.get(pn.get(W + "fmt") if pn is not None else None, "other")
            chap = pn.get(W + "chapStyle") if pn is not None else None
            out.append({"index": len(out), "format": ("A-1" if chap and fmt == "1" else fmt),
                        "restart": pn is not None and pn.get(W + "start") is not None,
                        "start": int(pn.get(W + "start")) if pn is not None and (pn.get(W + "start") or "").isdigit() else 1,
                        "chapter": f"Heading {chap}" if chap else "", "sep": CHAP_SEP.get(pn.get(W + "chapSep") if pn is not None else None, "-"),
                        "orient": "Landscape" if pg is not None and pg.get(W + "orient") == "landscape" else "Portrait",
                        "paper": _paper(pg.get(W + "w") if pg is not None else None, pg.get(W + "h") if pg is not None else None),
                        "page_number": any(has_page.get(r) is not None for r in shown if r), "first_text": texts[0] if texts else ""})
            sw = next((has_page[r] for r in shown if r and has_page.get(r)), "")
            if sw:                                 # a PAGE field's own format prints over the section's
                out[-1]["format"] = "A-1" if chap and sw == "1" else sw
            texts = []
        return out


def _kind_fmt(sec):
    return "none" if not sec["page_number"] else sec["format"]


def assign(secs, parts):
    """The sections matched to the parts in order: the first section starts the first part; a section starts the next
    part when its numbering restarts or changes format (a landscape or foldout section that carries on the count
    stays in the part it is in). Returns [(part, [indexes])]; a part with no section gets []."""
    out = [(p, []) for p in parts]
    if not parts:
        return out
    i, prev = 0, None
    for s in secs:
        f = _kind_fmt(s)
        if prev is not None and (s["restart"] or f != prev) and i + 1 < len(parts):
            i += 1
        out[i][1].append(s["index"])
        prev = f
    return out


def _row(part, what, plan, have):
    return {"part": part, "what": what, "plan": plan, "file": have, "status": "matches" if str(plan) == str(have) else "differs"}


def check(path, parts, recipes=None):
    """The read-back: each part's first section against its plan, then the fields and the Heading 7 numbering link."""
    secs = sections(path)
    matched = assign(secs, parts)
    rows = []
    for p, idx in matched:
        if not idx:
            rows.append({"part": p["name"], "what": "Its sections", "plan": "at least one", "file": "none found", "status": "missing"})
            continue
        s = secs[idx[0]]
        rows.append(_row(p["name"], "Page numbers", p["format"], _kind_fmt(s)))
        if p["format"] != "none":
            rows.append(_row(p["name"], "Numbering restarts", "Yes" if p["restart"] else "No", "Yes" if s["restart"] else "No"))
        if p["format"] == "A-1":
            rows.append(_row(p["name"], "Chapter style", p.get("chapter") or "Heading 7", s["chapter"] or "none"))
        rows.append(_row(p["name"], "Orientation", p["orient"], s["orient"]))
        rows.append(_row(p["name"], "Paper", p["paper"], s["paper"]))
        if len(idx) > 1:
            others = sorted({(secs[k]["orient"], secs[k]["paper"]) for k in idx[1:]} - {(s["orient"], s["paper"])})
            if others:
                rows.append({"part": p["name"], "what": "Other sections in it", "plan": "", "status": "matches",
                             "file": "; ".join(f"{o.lower()} {pp}" for o, pp in others)})
    if recipes is not None:
        import fieldrecipes as FR
        found = FR.check(FR.read_fields(path), recipes)
        n = FR.summary(found)
        bad = [r for r in found if r["status"] == "differs"]
        rows.append({"part": "Whole file", "what": "Fields against the field recipes", "plan": "each matches its recipe",
                     "file": f"{n['matches']} match, {n['differs']} differ, {n['no recipe']} have none"
                     + (": " + "; ".join(f"{r['code']} (recipe: {r['expected']})" for r in bad[:3]) if bad else ""),
                     "status": "differs" if bad else "matches"})
        miss = FR.missing_bookmarks(path, recipes)
        if miss:
            rows.append({"part": "Whole file", "what": "Bookmarks the recipes need", "plan": ", ".join(miss), "file": "missing", "status": "missing"})
    if any(p["format"] == "A-1" for p in parts):
        link = heading_link(path)
        rows.append({"part": "Whole file", "what": "Heading 7 numbers on the same list as Heading 1", "plan": "Yes",
                     "file": link, "status": "matches" if link == "Yes" else "differs"})
    n = {k: sum(1 for r in rows if r["status"] == k) for k in STATUS}
    return {"rows": rows, "sections": secs, "matched": [(p["id"], idx) for p, idx in matched],
            "summary": f"{len(secs)} section(s) in {sum(1 for _p, i in matched if i)} of {len(parts)} part(s): "
                       f"{n['matches']} match, {n['differs']} differ, {n['missing']} missing"}


def heading_link(path):
    """Yes when Heading 1 and Heading 7 take their numbers from the same list; No; or Not numbered."""
    with zipfile.ZipFile(path) as z:
        st = _xml(z, "word/styles.xml")
    if st is None:
        return "Not numbered"
    by = {}
    for s in st.iter(W + "style"):
        nm = s.find(W + "name")
        name = (nm.get(W + "val") if nm is not None else "").casefold()
        num = s.find(f"{W}pPr/{W}numPr/{W}numId")
        by[name] = num.get(W + "val") if num is not None else None
    a, b = by.get("heading 1"), by.get("heading 7")
    if not a or not b:
        return "Not numbered"
    return "Yes" if a == b else "No"


# ---------------------------------------------------------------- Word draws one page per part
_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$out = @{ ok = $false }
try {
  $app.Visible = $false; $app.DisplayAlerts = 0
  try { $app.AutomationSecurity = 3 } catch {}
  $d = $app.Documents.Open($env:SK_DOC, $false, $false, $false, 'sk-no-password', 'sk-no-password', $false, '', '', 0, 0, $false, $false, 0, $true)
  try {
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) { [void]$r.Fields.Update(); $r = $r.NextStoryRange } }
    foreach ($s in $d.Sections) { foreach ($h in $s.Headers) { [void]$h.Range.Fields.Update() }; foreach ($h in $s.Footers) { [void]$h.Range.Fields.Update() } }
    $d.Repaginate()
    $starts = @()
    foreach ($s in $d.Sections) { $starts += $d.Range($s.Range.Start, $s.Range.Start).Information(3) }
    $out.starts = $starts
    $out.pages = $d.ComputeStatistics(2)
    $d.ExportAsFixedFormat($env:SK_PDF, 17)
    $out.ok = $true
  } finally { $d.Close(0); try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($d) } catch {}; $d = $null }
} catch {
  $out.why = "$($_.Exception.HResult)"
} finally {
  try { $app.NormalTemplate.Saved = $true } catch {}
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
$out | ConvertTo-Json -Compress -Depth 4
"""


def available():
    return sys.platform.startswith("win")


def page_png(pdf, index, png, width_px=420):
    """One page of a PDF as a PNG. Returns png or ''."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        try:
            page = doc[max(0, min(index, len(doc) - 1))]
            w, _h = page.get_size()
            page.render(scale=max(0.3, width_px / max(1.0, w))).to_pil().save(png, "PNG")
        finally:
            doc.close()
        return png
    except Exception:  # noqa: BLE001  an unreadable PDF gives no picture
        return ""


def draw_parts(path, out_dir, parts, runner=None, timeout=900):
    """A hidden Word lays out a temporary copy (fields updated), notes the page each section starts on and saves a PDF;
    the first page of each part becomes a picture in out_dir. The file itself is never opened by Word."""
    if runner is None and not available():
        return {"ok": False, "why": "Word on this PC draws the pages; the read-back above is read from the file."}
    work = tempfile.mkdtemp(prefix="sk_readback_")
    try:
        doc = os.path.join(work, "read back" + os.path.splitext(path)[1].replace(".dotx", ".docx").replace(".dotm", ".docx"))
        shutil.copy2(path, doc)
        if path.lower().endswith((".dotx", ".dotm")):
            _as_document(doc)
        pdf = os.path.join(work, "read back.pdf")
        pidfile = os.path.join(work, ".sk_word.pid")
        env = dict(os.environ, SK_DOC=doc, SK_PDF=pdf, SK_PIDFILE=pidfile)
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
        try:
            if runner is not None:
                text = runner(cmd, env, timeout)
            else:
                r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                text = r.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return {"ok": False, "why": "Word took too long; the Word this job started was ended."}
        except OSError as e:
            return {"ok": False, "why": f"Windows PowerShell could not start ({type(e).__name__})."}
        finally:
            if runner is None:
                import prodword
                prodword._end_hidden(prodword._pids(pidfile))
        try:
            res = json.loads(next(x for x in reversed((text or "").strip().splitlines()) if x.startswith("{")))
        except (StopIteration, ValueError):
            return {"ok": False, "why": "Word did not answer."}
        if not res.get("ok"):
            return {"ok": False, "why": "Word could not lay out the file" + (f" (code {res.get('why')})." if res.get("why") else ".")}
        starts = [int(x) for x in (res.get("starts") or [])]
        os.makedirs(out_dir, exist_ok=True)
        pngs = {}
        for p, idx in assign(sections(path), parts):
            if idx and idx[0] < len(starts):
                png = os.path.join(out_dir, f"part {p['id']}.png")
                if page_png(pdf, starts[idx[0]] - 1, png):
                    pngs[p["id"]] = png
        return {"ok": True, "pngs": pngs, "pages": res.get("pages"), "starts": starts}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _as_document(path):
    """A template copy's content type set to a document's, so Word opens it as a document (the copy only)."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == "[Content_Types].xml":
                data = data.replace(b"wordprocessingml.template.main+xml", b"wordprocessingml.document.main+xml")
            zout.writestr(it, data)
    os.replace(tmp, path)
