"""A PDF copy of a Word, Excel or PowerPoint customer document, made by Microsoft Office on this PC (2.56.0), so Assign
can show the document exactly as it looks. Office does the conversion (it is the program that lays the file out);
Stationkeeper only asks it to save a PDF.

- Runs Office through Windows PowerShell's COM support, hidden, offline: no network is used or needed.
- The file opens read-only; macros are forced off (AutomationSecurity = 3); no prompts are shown.
- Office windows the person already has open are left alone: the copy is closed and Office is quit only when it was
  not already open (PowerPoint shares one instance).
- The paths go to PowerShell in environment variables, never inside the command text.
- The copy is kept in the effort's folder (page copies) beside the matrix, named with a fingerprint of the original,
  so a changed file gets a new copy and an unchanged one is not converted twice.
"""
import hashlib, os, subprocess, sys

KINDS = {".docx": "word", ".docm": "word", ".doc": "word", ".rtf": "word",
         ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel",
         ".pptx": "powerpoint", ".pptm": "powerpoint", ".ppt": "powerpoint"}

_SCRIPT = {
    "word": r"""
$ErrorActionPreference = 'Stop'
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$was = $null
try {
$was = $app.Documents.Count
$app.Visible = $false; $app.DisplayAlerts = 0
try { $app.AutomationSecurity = 3 } catch {}
foreach ($pair in ($env:SK_LIST -split "`n")) { if (-not $pair) { continue }
  if ($env:SK_STOPFILE -and (Test-Path -LiteralPath $env:SK_STOPFILE)) { break }
  $src, $out = $pair -split "`t"
  try { $d = $app.Documents.Open($src, $false, $true, $false, 'sk-no-password', 'sk-no-password')
        try { $d.ExportAsFixedFormat($out, 17) } finally { $d.Close(0) } } catch { Write-Error "$($_.Exception.Message)" -ErrorAction Continue } }
} finally {
  if ($was -eq 0 -or $was -eq $null) { try { $app.Quit() } catch {} }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers() }
""",
    "excel": r"""
$ErrorActionPreference = 'Stop'
$before = @(Get-Process EXCEL -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Excel.Application
$mine = @(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$was = $null
try {
$was = $app.Workbooks.Count
$app.Visible = $false; $app.DisplayAlerts = $false
try { $app.AutomationSecurity = 3 } catch {}
foreach ($pair in ($env:SK_LIST -split "`n")) { if (-not $pair) { continue }
  if ($env:SK_STOPFILE -and (Test-Path -LiteralPath $env:SK_STOPFILE)) { break }
  $src, $out = $pair -split "`t"
  try { $wb = $app.Workbooks.Open($src, 0, $true, [Type]::Missing, 'sk-no-password', 'sk-no-password')
        try { $wb.ExportAsFixedFormat(0, $out) } finally { $wb.Close($false) } } catch { Write-Error "$($_.Exception.Message)" -ErrorAction Continue } }
} finally {
  if ($was -eq 0 -or $was -eq $null) { try { $app.Quit() } catch {} }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers() }
""",
    "powerpoint": r"""
$ErrorActionPreference = 'Stop'
$before = @(Get-Process POWERPNT -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject PowerPoint.Application
$mine = @(Get-Process POWERPNT -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$was = $null
try {
$was = $app.Presentations.Count
try { $app.AutomationSecurity = 3 } catch {}
foreach ($pair in ($env:SK_LIST -split "`n")) { if (-not $pair) { continue }
  if ($env:SK_STOPFILE -and (Test-Path -LiteralPath $env:SK_STOPFILE)) { break }
  $src, $out = $pair -split "`t"
  try { $p = $app.Presentations.Open($src, -1, 0, 0)
        try { $p.SaveAs($out, 32) } finally { $p.Close() } } catch { Write-Error "$($_.Exception.Message)" -ErrorAction Continue } }
} finally {
  if ($was -eq 0 -or $was -eq $null) { try { $app.Quit() } catch {} }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers() }
""",
}


def kind(path):
    return KINDS.get(os.path.splitext(path or "")[1].lower(), "")


def fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def copy_path(path, folder):
    """Where the PDF copy of path lives (it may not exist yet)."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(folder, f"{stem}.{fingerprint(path)}.pdf")


def available():
    return sys.platform.startswith("win")


def make_many(paths, folder, timeout=600, runner=None, stop=None):
    """PDF copies of several files, one Office session per program (Office starting is the slow part). Returns
    {path: copy path or RuntimeError}. 3.14.3: stop() True (Stationkeeper is closing) asks the script to stop: it
    finishes the document it is on, keeps the copies it finished, and quits the Office it started. A script that does
    not stop in time is ended with its Office, and none of its copies is kept (they are made again next time)."""
    out, todo = {}, {}
    for p in paths:
        k = kind(p)
        if not k:
            out[p] = RuntimeError("not a Word, Excel or PowerPoint file")
            continue
        os.makedirs(folder, exist_ok=True)
        c = copy_path(p, folder)
        if os.path.isfile(c) and os.path.getsize(c) > 0:
            out[p] = c
        else:
            todo.setdefault(k, []).append((p, c))
    for k, pairs in todo.items():
        if stop is not None and stop():
            for p, _c in pairs:
                out[p] = RuntimeError("stopped before the PDF copy was made")
            continue
        listing = "\n".join(f"{os.path.abspath(p)}\t{os.path.abspath(c)}.part.pdf" for p, c in pairs)
        pidfile = os.path.join(folder, f".office_{k}_{os.getpid()}.pid")
        stopfile = os.path.join(folder, f".office_{k}_{os.getpid()}.stop")   # 3.14.3: asks the script to stop
        env = dict(os.environ, SK_LIST=listing, SK_PIDFILE=pidfile, SK_STOPFILE=stopfile)
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT[k]]
        err = b""
        cut = False                             # 3.14.3: ended early (too long, or closing): keep no part copies
        try:
            if runner is not None:
                _code, _o, err = runner(cmd, env, timeout)
            elif not available():
                err = b"Microsoft Office is needed"
            else:
                err = _run(cmd, env, timeout, stop)
                if err is _STOPPED:                     # it stopped between documents: what it finished is whole
                    err = b"stopped before the PDF copy was made"
                elif err is _KILLED:                    # it ignored the stop: end the Office it started, by its IDs
                    _end_started(pidfile, k)
                    err, cut = b"stopped before the PDF copy was made", True
        except subprocess.TimeoutExpired:
            err, cut = b"Office took too long to save the PDF copies", True
            _end_started(pidfile, k)            # 2.71.0: the hidden Office it started does not stay behind
        except OSError as e:
            err = f"Windows PowerShell could not start ({type(e).__name__})".encode()
        for f in (pidfile, stopfile):
            try:
                os.remove(f)
            except OSError:
                pass
        msg = (err or b"").decode("utf-8", "replace") if isinstance(err, (bytes, bytearray)) else str(err or "")
        for p, c in pairs:
            part = c + ".part.pdf"
            if cut and os.path.isfile(part):
                try:
                    os.remove(part)
                except OSError:
                    pass
            if not cut and os.path.isfile(part) and os.path.getsize(part) > 0:
                os.replace(part, c)
                out[p] = c
            elif msg == "stopped before the PDF copy was made":
                out[p] = RuntimeError(msg)
            else:
                low = msg.lower()
                why = (f"Microsoft {k.capitalize()} is not installed on this PC" if "80040154" in low or "class not registered" in low
                       else f"{k.capitalize()} could not save a PDF copy" + (f": {msg.strip().splitlines()[-1][:160]}" if msg.strip() else ""))
                out[p] = RuntimeError(why)
    return out


_STOPPED = object()       # the script stopped itself and quit the Office it started
_KILLED = object()        # it did not stop in time and was ended


def _run(cmd, env, timeout, stop=None, popen=None, grace=90):
    """3.14.3: the copy script, checked every half second. stop() True writes the stop file: the script finishes the
    step it is on, skips the rest and quits only the Office it started (Office may still be starting; killing the
    script then would leave it behind). Only a script that has not ended after grace seconds is ended; its Office is
    then ended by its process IDs. Returns _STOPPED, _KILLED, or the script's error output; past the timeout,
    TimeoutExpired."""
    import time
    p = (popen or subprocess.Popen)(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    t0 = time.monotonic()
    asked = None
    while True:
        try:
            _o, e = p.communicate(timeout=0.5)
            return _STOPPED if asked is not None else e
        except subprocess.TimeoutExpired:
            pass
        now = time.monotonic()
        if asked is None and stop is not None and stop():
            asked = now
            try:
                with open(env["SK_STOPFILE"], "w", encoding="utf-8") as f:
                    f.write("stop")
            except (OSError, KeyError):
                pass
        if asked is not None and now - asked > grace:
            p.kill(); p.communicate()
            return _KILLED
        if asked is None and now - t0 > timeout:
            p.kill(); p.communicate()
            raise subprocess.TimeoutExpired(cmd, timeout)


_IMAGE = {"word": "WINWORD.EXE", "excel": "EXCEL.EXE", "powerpoint": "POWERPNT.EXE"}


def _end_started(pidfile, k, runner=None):
    """2.71.0: when a copy takes too long, end the Office program this copy started (its process IDs were written by
    the script the moment it started). Office windows the person opened are never touched: only the IDs that appeared
    when this copy started, and only if they are still that Office program. Returns the IDs ended."""
    try:
        with open(pidfile, encoding="utf-8") as f:
            ids = [int(x) for x in f.read().replace("\n", ",").split(",") if x.strip().isdigit()]
    except (OSError, ValueError):
        return []
    done = []
    for pid in ids:
        cmd = ["taskkill", "/PID", str(pid), "/FI", f"IMAGENAME eq {_IMAGE[k]}", "/F"]
        try:
            if runner is not None:
                runner(cmd)
            else:
                subprocess.run(cmd, capture_output=True, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            done.append(pid)
        except (OSError, subprocess.SubprocessError):
            pass
    return done


def make(path, folder, timeout=180, runner=None):
    """The PDF copy of one file (made now if needed). Returns its path; raises RuntimeError with a plain reason."""
    r = make_many([path], folder, timeout, runner).get(path)
    if isinstance(r, Exception) or r is None:
        raise r or RuntimeError("no PDF copy")
    return r
