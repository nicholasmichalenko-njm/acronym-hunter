"""The Word check of a finished template (3.23.0): when Word is on this PC, a hidden Word makes a new document from the
template (the template itself is never opened for writing), updates every field, and puts in each of the template's
Quick Parts one after another, confirming each one: its fields update without an error, every style it uses is one of
the template's, and the document still opens and paginates. Word is then closed without saving anything.

Same rules as Update fields in Word: macros forced off, no prompts, links not updated, only the Word this job started is
ended if it takes too long, Word windows the person has open are never touched, paths go to PowerShell in environment
variables. Returns {"ok", "entries": [{"name", "category", "ok", "fields", "errors", "styles_missing"}], "fields",
"field_errors", "pages", "seconds"} or {"ok": False, "why"}."""
import json, os, subprocess, sys, time

import prodword as PW

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$links = $null
$out = @{ ok = $false; entries = @() }
try {
  $app.Visible = $false; $app.DisplayAlerts = 0
  try { $app.AutomationSecurity = 3 } catch {}
  try { $links = $app.Options.UpdateLinksAtOpen; $app.Options.UpdateLinksAtOpen = $false } catch {}
  $d = $app.Documents.Add($env:SK_TPL, $false, 0, $false)
  try {
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) { [void]$r.Fields.Update(); $r = $r.NextStoryRange } }
    foreach ($s in $d.Sections) { foreach ($h in $s.Headers) { [void]$h.Range.Fields.Update() }; foreach ($h in $s.Footers) { [void]$h.Range.Fields.Update() } }
    $errs = @()
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) {
      foreach ($f in $r.Fields) { if ($f.Result.Text -like '*Error!*') { $errs += $f.Code.Text.Trim() } }; $r = $r.NextStoryRange } }
    $out.field_errors = $errs
    $out.fields = $d.Fields.Count
    $names = @{}; foreach ($st in $d.Styles) { $names[$st.NameLocal] = 1 }
    $t = $d.AttachedTemplate
    $n = $t.BuildingBlockEntries.Count
    for ($i = 1; $i -le $n; $i++) {
      $bb = $t.BuildingBlockEntries.Item($i)
      $e = @{ name = $bb.Name; category = $bb.Category.Name; ok = $false; fields = 0; errors = @(); styles_missing = @() }
      try {
        $end = $d.Content; $end.Collapse(0); $end.InsertParagraphAfter(); $end = $d.Content; $end.Collapse(0)
        $start = $end.Start
        $got = $bb.Insert($end, $true)
        $rng = $d.Range($start, $d.Content.End)
        [void]$rng.Fields.Update()
        $e.fields = $rng.Fields.Count
        foreach ($f in $rng.Fields) { if ($f.Result.Text -like '*Error!*') { $e.errors += $f.Code.Text.Trim() } }
        foreach ($p in $rng.Paragraphs) { $sn = $p.Style.NameLocal; if (-not $names.ContainsKey($sn)) { $e.styles_missing += $sn } }
        $e.ok = ($e.errors.Count -eq 0 -and $e.styles_missing.Count -eq 0)
      } catch { $e.errors += "insert failed $($_.Exception.HResult)" }
      $out.entries += $e
    }
    $d.Repaginate()
    $out.pages = $d.ComputeStatistics(2)
    $out.ok = $true
  } finally { $d.Close(0); try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($d) } catch {}; $d = $null }
} catch {
  $out.why = "$($_.Exception.HResult)"
} finally {
  try { if ($links -ne $null) { $app.Options.UpdateLinksAtOpen = $links } } catch {}
  try { $app.NormalTemplate.Saved = $true } catch {}
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(0); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
$out | ConvertTo-Json -Compress -Depth 5
"""


def available():
    return sys.platform.startswith("win")


def gate(template_path, timeout=900, runner=None):
    """Word's own check of a finished template (see the module text). runner (tests): replaces PowerShell."""
    if not available() and runner is None:
        return {"ok": False, "why": "Word on Windows is needed for the Word check."}
    t0 = time.perf_counter()
    pidfile = os.path.join(os.path.dirname(os.path.abspath(template_path)), f".sk_gate_{os.getpid()}.pid")
    env = dict(os.environ, SK_TPL=os.path.abspath(template_path), SK_PIDFILE=pidfile)
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
    try:
        if runner is not None:
            out = runner(cmd, env, timeout)
        else:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        PW._end(pidfile)
        return {"ok": False, "why": "Word took too long; the Word this check started was ended."}
    except OSError as e:
        return {"ok": False, "why": f"Windows PowerShell could not start ({type(e).__name__})."}
    finally:
        pids = PW._pids(pidfile)
        try:
            os.remove(pidfile)
        except OSError:
            pass
    if runner is None:
        PW._end_hidden(pids)
    try:
        res = json.loads(next(x for x in reversed(out.strip().splitlines()) if x.startswith("{")))
    except (StopIteration, ValueError):
        return {"ok": False, "why": "Word did not answer."}
    if not res.get("ok"):
        return {"ok": False, "why": f"Word could not check the template (code {res.get('why', '')})."}
    ents = res.get("entries") or []
    if isinstance(ents, dict):                       # ConvertTo-Json gives one entry as an object, not a list
        ents = [ents]
    for e in ents:
        for k in ("errors", "styles_missing"):
            v = e.get(k) or []
            e[k] = [x for x in ([v] if isinstance(v, str) else v) if x]
    res["entries"] = ents
    fe = res.get("field_errors") or []
    res["field_errors"] = [x for x in ([fe] if isinstance(fe, str) else fe) if x]
    res["seconds"] = round(time.perf_counter() - t0, 1)
    return res


def text(res):
    """The Word check in words, for the validation report."""
    if not res:
        return ""
    if not res.get("ok"):
        return "Word check: " + res.get("why", "not run")
    bad = [e for e in res["entries"] if not e.get("ok")]
    lines = [f"Word check: {len(res['entries'])} Quick Part(s) put in, {len(bad)} with a problem; {res.get('fields', 0)} field(s) "
             f"updated, {len(res['field_errors'])} with an error; {res.get('pages', 0)} page(s)."]
    for f in res["field_errors"]:
        lines.append(f"  field error: {f}")
    for e in bad:
        why = "; ".join([f"field error {x}" for x in e["errors"]] + [f"style {x} not in the template" for x in e["styles_missing"]])
        lines.append(f"  {e.get('category', '')} / {e.get('name', '')}: {why}")
    return "\n".join(lines)


_OPEN = r"""
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
  $d = $app.Documents.Open($env:SK_TPL, $false, $true, $false, 'sk-no-password', 'sk-no-password', $false, '', '', 0, 0, $false, $false, 0, $true)
  try {
    $d.Repaginate(); $out.pages = $d.ComputeStatistics(2); $out.paragraphs = $d.Paragraphs.Count; $out.sections = $d.Sections.Count
    $hid = 0; foreach ($p in $d.Paragraphs) { if ($p.Range.Font.Hidden -eq -1) { $hid++ } }; $out.hidden_paragraphs = $hid
    $out.ok = $true
  } finally { $d.Close(0) }
} catch { $out.why = "$($_.Exception.HResult)" }
finally {
  try { $app.NormalTemplate.Saved = $true } catch {}
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(0); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
}
$out | ConvertTo-Json -Compress
"""


def open_check(path, timeout=300):
    """3.24.0: Word opens a document read-only and paginates it (a setup written on a template): {"ok", "pages",
    "paragraphs", "sections", "hidden_paragraphs"} or {"ok": False, "why"}."""
    if not available():
        return {"ok": False, "why": "Word on Windows is needed."}
    pidfile = os.path.join(os.path.dirname(os.path.abspath(path)), f".sk_open_{os.getpid()}.pid")
    env = dict(os.environ, SK_TPL=os.path.abspath(path), SK_PIDFILE=pidfile)
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _OPEN], env=env, capture_output=True,
                           timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        PW._end(pidfile)
        return {"ok": False, "why": "Word took too long."}
    finally:
        pids = PW._pids(pidfile)
        try:
            os.remove(pidfile)
        except OSError:
            pass
    PW._end_hidden(pids)
    try:
        return json.loads(next(x for x in reversed(out.strip().splitlines()) if x.startswith("{")))
    except (StopIteration, ValueError):
        return {"ok": False, "why": "Word did not answer."}
