"""Compare in Word (3.60.0): two Word files compared by Word itself (Review > Compare), the result saved as a new file
with every change a tracked change, the later file's formatting kept. Word on this PC only, in a hidden Word started
for this job, the same way the field update runs (prodword): the two files open read-only, macros off, no prompts, the
paths in environment variables, only the Word this job started ended if it takes too long. Neither file is changed;
the result is a new file and never one of the two.

compare(old_path, new_path, out_path, author) -> {"ok", "revisions", "seconds"} or {"ok": False, "why"}."""
import json, os, subprocess, time

import filesafety as FS
import prodword as PW

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$out = @{ ok = $false }
$a = $null; $b = $null; $r = $null
try {
  $app.Visible = $false; $app.DisplayAlerts = 0
  try { $app.AutomationSecurity = 3 } catch {}
  $a = $app.Documents.Open($env:SK_OLD, $false, $true, $false)
  $b = $app.Documents.Open($env:SK_NEW, $false, $true, $false)
  # destination new document (2), word-level granularity (1), compare formatting, case, white space, tables, headers,
  # footnotes, text boxes and fields; the changes shown by the author given
  $r = $app.CompareDocuments($a, $b, 2, 1, $true, $true, $true, $true, $true, $true, $true, $true, $true, $true, $env:SK_AUTHOR, $true)
  $out.revisions = $r.Revisions.Count
  $r.SaveAs2([ref]$env:SK_OUT, [ref]16)
  $out.ok = $true
} catch {
  $out.why = "$($_.Exception.HResult)"
} finally {
  foreach ($d in @($r, $b, $a)) { if ($d -ne $null) { try { $d.Close(0) } catch {}; try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($d) } catch {} } }
  try { $app.NormalTemplate.Saved = $true } catch {}
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
$out | ConvertTo-Json -Compress
"""


def available():
    return PW.available()


def compare(old_path, new_path, out_path, author="Compare", timeout=900, runner=None):
    if not (old_path.lower().endswith(".docx") and new_path.lower().endswith(".docx")):
        return {"ok": False, "why": "Word compares two Word files (.docx)."}
    if not available() and runner is None:
        return {"ok": False, "why": "Word on Windows is needed to compare in Word."}
    FS.guard(out_path, old_path, new_path)
    if os.path.exists(out_path):
        return {"ok": False, "why": "That file is already there: choose a new name."}
    t0 = time.perf_counter()
    pidfile = os.path.join(os.path.dirname(os.path.abspath(out_path)), f".sk_word_{os.getpid()}.pid")
    env = dict(os.environ, SK_OLD=os.path.abspath(old_path), SK_NEW=os.path.abspath(new_path), SK_OUT=os.path.abspath(out_path),
               SK_AUTHOR=author or "Compare", SK_PIDFILE=pidfile)
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
    try:
        if runner is not None:
            out = runner(cmd, env, timeout)
        else:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        PW._end(pidfile)
        return {"ok": False, "why": "Word took too long; the Word this job started was ended."}
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
        code = str(res.get("why", ""))
        return {"ok": False, "why": "Word could not compare the two files" + (f" (code {code})." if code else ".")}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    return res
