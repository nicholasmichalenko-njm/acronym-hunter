"""Update fields in Word (3.6.0): after the engine's fixes, Word itself renumbers what only Word can lay out: page
numbers, caption numbers (SEQ and STYLEREF), cross-references, the table of contents and the lists of tables and
figures. It runs on the Stationkeeper copy only, in a hidden Word started for this job.

Rules from the feasibility lab, all kept here:
- Refused unless the file is a Stationkeeper copy in the output folder (prodcopy.check_write).
- Fields that read other files (LINK, INCLUDETEXT, INCLUDEPICTURE) are locked first, so an unreachable source can
  never replace their content with an error; their results stay exactly as they were.
- Word's 'update links at open' setting is turned off for this Word only while it opens the copy and set back
  before Word quits (a normal quit saves whatever value is set, so it is always restored first).
- Macros are forced off; no prompts are shown; the copy opens without repair (a damaged file stops the job).
- Only the Word this job started is ended if it takes too long; Word windows the person has open are not touched.
- The paths go to PowerShell in environment variables, never inside the command text.
Returns {"ok", "pages", "fields", "errors", "tocs", "lists", "locked", "seconds"} or {"ok": False, "why"}."""
import json, os, subprocess, sys, time

import prodcopy as PCY

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$links = $null
$out = @{ ok = $false }
try {
  $app.Visible = $false; $app.DisplayAlerts = 0
  try { $app.AutomationSecurity = 3 } catch {}
  try { $links = $app.Options.UpdateLinksAtOpen; $app.Options.UpdateLinksAtOpen = $false } catch {}
  $d = $app.Documents.Open($env:SK_COPY, $false, $false, $false, 'sk-no-password', 'sk-no-password', $false, '', '', 0, 0, $false, $false, 0, $true)
  try {
    $locked = 0
    foreach ($story in $d.StoryRanges) {
      $r = $story
      while ($r -ne $null) {
        foreach ($f in $r.Fields) { if (@(56, 67, 68) -contains $f.Type) { $f.Locked = $true; $locked++ } }
        $r = $r.NextStoryRange
      }
    }
    foreach ($s in $d.Sections) { foreach ($h in $s.Headers) { foreach ($f in $h.Range.Fields) { if (@(56, 67, 68) -contains $f.Type) { $f.Locked = $true; $locked++ } } }
                                  foreach ($h in $s.Footers) { foreach ($f in $h.Range.Fields) { if (@(56, 67, 68) -contains $f.Type) { $f.Locked = $true; $locked++ } } } }
    # pass 1: every field in every story, then the TOC and the lists of tables and figures in full
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) { [void]$r.Fields.Update(); $r = $r.NextStoryRange } }
    foreach ($s in $d.Sections) { foreach ($h in $s.Headers) { [void]$h.Range.Fields.Update() }; foreach ($h in $s.Footers) { [void]$h.Range.Fields.Update() } }
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    foreach ($t in $d.TablesOfFigures) { $t.Update() }
    $d.Repaginate()
    # pass 2: only what depends on where pages fall now that the TOC and lists have their final length
    foreach ($t in $d.TablesOfContents) { $t.UpdatePageNumbers() }
    foreach ($t in $d.TablesOfFigures) { $t.UpdatePageNumbers() }
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) {
      foreach ($f in $r.Fields) { if ($f.Type -eq 37) { [void]$f.Update() } }; $r = $r.NextStoryRange } }
    $errors = 0; $fields = 0
    foreach ($story in $d.StoryRanges) { $r = $story; while ($r -ne $null) {
      foreach ($f in $r.Fields) { $fields++; try { if ($f.Result.Text -like '*Error!*') { $errors++ } } catch {} }
      $r = $r.NextStoryRange } }
    $out.pages = $d.ComputeStatistics(2)
    $out.fields = $fields; $out.errors = $errors; $out.locked = $locked
    $out.tocs = $d.TablesOfContents.Count; $out.lists = $d.TablesOfFigures.Count
    $d.Save()
    $out.ok = $true
  } finally { $d.Close(0); try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($d) } catch {}; $d = $null }
} catch {
  $out.why = "$($_.Exception.HResult)"
} finally {
  try { if ($links -ne $null) { $app.Options.UpdateLinksAtOpen = $links } } catch {}
  try { $app.NormalTemplate.Saved = $true } catch {}       # nothing for Word to ask about on the way out
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(0); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
$out | ConvertTo-Json -Compress
"""


def available():
    return sys.platform.startswith("win")


def _pids(pidfile):
    try:
        return [int(x) for x in open(pidfile).read().strip().split(",") if x.strip().isdigit()]
    except OSError:
        return []


_END_HIDDEN = r"""
$ErrorActionPreference = 'SilentlyContinue'
$left = 0
foreach ($id in ($env:SK_PIDS -split ',')) { if (-not $id) { continue }
  for ($i = 0; $i -lt 40; $i++) { if (-not (Get-Process -Id $id -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 500 }
  $p = Get-Process -Id $id -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -eq 'WINWORD' -and $p.MainWindowHandle -eq 0) { Stop-Process -Id $id -Force; $left++ } }
$left
"""


def _end_hidden(pids, timeout=60):
    """The Word this job started must be gone when the job ends. Wait up to 20 seconds for it to quit, then end it,
    but only that exact process, only if it is still Word, and only while it has no window (a Word a person is using
    is never touched)."""
    if not pids or not available():
        return 0
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _END_HIDDEN],
                           env=dict(os.environ, SK_PIDS=",".join(str(p) for p in pids)), capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return int((r.stdout.decode("utf-8", "replace").strip().splitlines() or ["0"])[-1] or 0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0


def _end(pidfile):
    _end_hidden(_pids(pidfile))


def update_fields(copy_path, timeout=1800, runner=None):
    PCY.check_write(copy_path)
    if not available() and runner is None:
        return {"ok": False, "why": "Word on Windows is needed to update fields."}
    if PCY.owner_files(copy_path):
        return {"ok": False, "why": "Someone opened the copy in Word. Close it first."}
    t0 = time.perf_counter()
    pidfile = os.path.join(os.path.dirname(copy_path), f".sk_word_{os.getpid()}.pid")
    env = dict(os.environ, SK_COPY=os.path.abspath(copy_path), SK_PIDFILE=pidfile)
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
    try:
        if runner is not None:
            out = runner(cmd, env, timeout)
        else:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        _end(pidfile)
        return {"ok": False, "why": "Word took too long; the Word this job started was ended. The copy keeps the engine's fixes."}
    except OSError as e:
        return {"ok": False, "why": f"Windows PowerShell could not start ({type(e).__name__})."}
    finally:
        pids = _pids(pidfile)
        try:
            os.remove(pidfile)
        except OSError:
            pass
    ended = _end_hidden(pids) if runner is None else 0
    try:
        res = json.loads(next(x for x in reversed(out.strip().splitlines()) if x.startswith("{")))
    except (StopIteration, ValueError):
        return {"ok": False, "why": "Word did not answer."}
    if not res.get("ok"):
        code = str(res.get("why", ""))
        why = {"-2146822880": "Word could not open the copy (damaged).", "-2146824090": "Word could not open the copy."}.get(code, "Word could not update the fields.")
        return {"ok": False, "why": why + (f" (code {code})" if code else "")}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    res["word_ended"] = ended            # 1 when Word had to be ended after it did not quit by itself
    return res
