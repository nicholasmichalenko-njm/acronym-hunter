"""Exact preview through Word (3.32.0): the volume's template and setup made as Make templates makes them, in a dated
folder of their own, then laid out by Word on this PC: Word updates the fields (the TOC, the lists, page numbers and
cross-references), counts the pages, notes the page each heading starts on, and saves a PDF of it. The Structure
Builder shows those pages: Word's own layout and the true page count.

Nothing is recorded: no template version, no export, and the effort's files are not touched. The dated folder is kept
beside the setup documents (the last three are kept). Rules kept from prodword: macros forced off, no prompts, the
paths go to PowerShell in environment variables, only the Word this job started is ended. Offline: no network."""
import datetime, json, os, shutil, subprocess, sys

KEEP = 3

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
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    foreach ($t in $d.TablesOfFigures) { $t.Update() }
    $d.Repaginate()
    foreach ($t in $d.TablesOfContents) { $t.UpdatePageNumbers() }
    foreach ($t in $d.TablesOfFigures) { $t.UpdatePageNumbers() }
    $out.pages = $d.ComputeStatistics(2)
    $heads = @()
    $n = 0
    foreach ($p in $d.Paragraphs) {
      $n++; if ($n -gt 20000) { break }
      if ($p.OutlineLevel -lt 10) {
        $t = ($p.Range.Text -replace "[`r`n`a\x07]", '').Trim()
        if ($t) { $heads += @{ t = $t; p = $p.Range.Information(3) } } } }
    $out.heads = $heads
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


def lay_out(docx, pdf, runner=None, timeout=1800):
    """Word updates the fields of docx, counts its pages, notes each heading's page and saves the PDF.
    Returns {"ok", "pages", "heads": [(text, page)]} or {"ok": False, "why"}. runner (tests): runner(cmd, env, timeout)
    -> the script's output text."""
    if runner is None and not available():
        return {"ok": False, "why": "Word on this PC is needed for the exact preview."}
    pidfile = os.path.join(os.path.dirname(docx), f".sk_word_{os.getpid()}.pid")
    env = dict(os.environ, SK_DOC=os.path.abspath(docx), SK_PDF=os.path.abspath(pdf), SK_PIDFILE=pidfile)
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
    try:
        if runner is not None:
            text = runner(cmd, env, timeout)
        else:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            text = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "Word took too long; the Word this preview started was ended."}
    except OSError as e:
        return {"ok": False, "why": f"Windows PowerShell could not start ({type(e).__name__})."}
    finally:
        if runner is None:
            import prodword
            prodword._end_hidden(prodword._pids(pidfile))
        try:
            os.remove(pidfile)
        except OSError:
            pass
    try:
        res = json.loads(next(x for x in reversed((text or "").strip().splitlines()) if x.startswith("{")))
    except (StopIteration, ValueError):
        return {"ok": False, "why": "Word did not answer."}
    if not res.get("ok") or not os.path.isfile(pdf):
        code = str(res.get("why") or "")
        return {"ok": False, "why": "Word could not lay out the preview." + (f" (code {code})" if code else "")}
    heads = res.get("heads") or []
    heads = [heads] if isinstance(heads, dict) else heads
    return {"ok": True, "pages": int(res.get("pages") or 0),
            "heads": [(str(h.get("t", "")), int(h.get("p") or 0)) for h in heads if isinstance(h, dict)]}


def section_of_pages(heads, labels, pages):
    """[label or ''] for each page (1-based pages, list index 0 = page 1): the last section heading that starts on or
    before the page and is one of labels."""
    want = set(labels)
    starts = sorted((p, t) for t, p in heads if t in want and p > 0)
    out, cur, k = [], "", 0
    for page in range(1, pages + 1):
        while k < len(starts) and starts[k][0] <= page:
            cur = starts[k][1]
            k += 1
        out.append(cur)
    return out


def prune(folder, keep=KEEP):
    """Only the last few dated preview folders stay."""
    try:
        subs = sorted(d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d)))
    except OSError:
        return
    for d in subs[:-keep] if keep else subs:
        shutil.rmtree(os.path.join(folder, d), ignore_errors=True)


def run(M, volume, folder, config_dir, ws=None, effort_name="", info=None, context=None, runner=None, when=None,
        starts=None, progress=None):
    """The exact preview of one volume (every volume's setup is one file when there is one volume). Returns {"ok",
    "pages", "pdf", "docx", "heads", "when", "volume"} or {"ok": False, "why"}."""
    import setupdoc as SD
    import setuptemplate as ST
    say = progress or (lambda *a: None)
    when = when or datetime.datetime.now()
    sub = os.path.join(folder, when.strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(sub, exist_ok=True)
    names = [n for n, _e in SD.volume_groups(M)]
    vols = [volume] if volume and volume in names else None
    say(0.1, "Making the template and the setup")
    try:
        made = ST.make_all(M, sub, config_dir, ws, effort_name, info, when=when, context=context, word=None,
                           starts=starts, volumes=vols, record=False)
    except PermissionError:
        return {"ok": False, "why": "A file in the preview folder is open in Word: close it, then try again."}
    if not made:
        return {"ok": False, "why": "That volume has nothing to make yet."}
    docx = made[0]["setup"]
    pdf = os.path.splitext(docx)[0] + ".pdf"
    say(0.4, "Word is laying out the pages")
    res = lay_out(docx, pdf, runner=runner)
    prune(folder)
    if not res.get("ok"):
        return res
    res.update(pdf=pdf, docx=docx, when=when.strftime("%Y-%m-%d %H:%M"), volume=made[0]["volume"])
    return res
