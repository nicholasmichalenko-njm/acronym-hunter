"""Measured pages for Quick Parts (3.32.0): Word counts how many pages each library Quick Part fills, on this PC, so the
page plan, the page budget and a prepaginated setup use its true length.

How: a new document is made in a hidden Word from the Quick Part's kept source file (so it has that template's page
setup, styles and Quick Parts), its body is emptied, the Quick Part is inserted, and Word counts the pages. The
document is closed without saving; nothing is written anywhere but a work copy in the library's own folder, taken away
at the end. A .docx source is copied as a template first (only its content type changes), since Word keeps Quick Parts
in templates.

Rules kept from prodword and office_pdf: macros forced off, no prompts, the paths and names go to PowerShell in
environment variables (never inside the command text), only the Word this job started is ended, and Word windows the
person has open are never touched. Measuring is offline: no network is used or needed."""
import json, os, shutil, subprocess, sys, zipfile

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$app = New-Object -ComObject Word.Application
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
if ($env:SK_PIDFILE -and $mine) { Set-Content -Path $env:SK_PIDFILE -Value ($mine -join ',') }
$res = @()
try {
  $app.Visible = $false; $app.DisplayAlerts = 0
  try { $app.AutomationSecurity = 3 } catch {}
  foreach ($line in ($env:SK_LIST -split "`n")) { if (-not $line) { continue }
    $src, $name, $cat = $line -split "`t"
    $r = @{ pages = 0; why = '' }
    try {
      $d = $app.Documents.Add($src, $false, 0, $false)
      try {
        $t = $d.AttachedTemplate
        $bb = $null
        for ($i = 1; $i -le $t.BuildingBlockEntries.Count; $i++) {
          $e = $t.BuildingBlockEntries.Item($i)
          if ($e.Name -eq $name -and (-not $cat -or $e.Category.Name -eq $cat)) { $bb = $e; break } }
        if ($bb -eq $null) { $r.why = 'missing' } else {
          [void]$d.Content.Delete()
          [void]$bb.Insert($d.Range(0, 0), $true)
          $d.Repaginate()
          $r.pages = $d.ComputeStatistics(2) }
      } finally { $d.Close(0); try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($d) } catch {}; $d = $null }
    } catch { $r.why = "$($_.Exception.HResult)" }
    $res += $r }
} finally {
  try { $app.NormalTemplate.Saved = $true } catch {}
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  for ($i = 0; $i -lt 40; $i++) { try { $app.Quit(); break } catch { Start-Sleep -Milliseconds 500 } }
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
  $app = $null; [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
ConvertTo-Json -Compress -InputObject @($res)
"""

_AS_TEMPLATE = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml", ".dotx"),
    "application/vnd.ms-word.document.macroEnabled.main+xml":
        ("application/vnd.ms-word.template.macroEnabledTemplate.main+xml", ".dotm"),
}


def available():
    return sys.platform.startswith("win")


def as_template(src, folder):
    """A .dotx (or .dotm) work copy of a .docx: only the main part's content type changes. A template is used as it is."""
    if os.path.splitext(src)[1].lower() in (".dotx", ".dotm"):
        return src
    zin = zipfile.ZipFile(src)
    ct = zin.read("[Content_Types].xml").decode("utf-8")
    ext = ".dotx"
    for a, (b, e) in _AS_TEMPLATE.items():
        if a in ct:
            ct, ext = ct.replace(a, b), e
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, os.path.splitext(os.path.basename(src))[0] + ext)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, ct.encode("utf-8") if n == "[Content_Types].xml" else zin.read(n))
    zin.close()
    return out


def jobs(lib, ids):
    """[(item id, source path, entry name, category)] for the Quick Parts among ids whose kept source is on this PC."""
    out = []
    for iid in ids:
        it = lib.get(iid)
        if it is None or it["kind"] != "quickpart":
            continue
        v = lib.values(it) or {}
        src = lib.source_path(v.get("source") or "") if v.get("source") else ""
        if src and os.path.isfile(src) and v.get("entry"):
            out.append((iid, src, v["entry"], v.get("category") or ""))
    return out


def measure(lib, ids, runner=None, timeout=900, keep=True):
    """Word measures each Quick Part among ids and the library keeps its pages (measured). Returns {item id: pages, or
    the reason in words}. runner (tests): runner(cmd, env, timeout) -> the script's output text. keep False (3.49.0, a
    background job): the pages are only returned; the window keeps them (qpjobs), so a job never saves the library."""
    todo = jobs(lib, ids)
    out = {iid: "Its source file is not in the library." for iid in ids
           if (lib.get(iid) or {}).get("kind") == "quickpart" and iid not in {j[0] for j in todo}}
    if not todo:
        return out
    if runner is None and not available():
        return dict(out, **{j[0]: "Word on this PC is needed to measure pages." for j in todo})
    work = os.path.join(lib.root, "_measuring")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    srcs = {}
    lines = []
    try:
        for iid, src, name, cat in todo:
            if src not in srcs:
                srcs[src] = as_template(src, os.path.join(work, str(len(srcs))))
            lines.append(f"{os.path.abspath(srcs[src])}\t{name}\t{cat}")
        pidfile = os.path.join(work, f".sk_word_{os.getpid()}.pid")
        env = dict(os.environ, SK_LIST="\n".join(lines), SK_PIDFILE=pidfile)
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]
        try:
            if runner is not None:
                text = runner(cmd, env, timeout)
            else:
                r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                text = r.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            text = ""
        except OSError as e:
            return dict(out, **{j[0]: f"Windows PowerShell could not start ({type(e).__name__})." for j in todo})
        finally:
            if runner is None:
                import prodword
                prodword._end_hidden(prodword._pids(pidfile))
        try:
            res = json.loads(next(x for x in reversed((text or "").strip().splitlines()) if x.startswith(("[", "{"))))
            res = [res] if isinstance(res, dict) else list(res)
        except (StopIteration, ValueError):
            res = []
        for k, (iid, _src, _name, _cat) in enumerate(todo):
            r = res[k] if k < len(res) and isinstance(res[k], dict) else {}
            n = int(r.get("pages") or 0)
            if n > 0:
                if keep:
                    lib.set_pages(iid, n, "measured")
                out[iid] = n
            else:
                out[iid] = ("Word did not find the Quick Part in its source file." if r.get("why") == "missing"
                            else "Word could not measure it." + (f" (code {r['why']})" if r.get("why") else "") if r else "Word did not answer.")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out
