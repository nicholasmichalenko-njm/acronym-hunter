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
$app = New-Object -ComObject Word.Application
$was = $app.Documents.Count
$app.Visible = $false; $app.DisplayAlerts = 0
try { $app.AutomationSecurity = 3 } catch {}
$d = $app.Documents.Open($env:SK_SRC, $false, $true, $false)
try { $d.ExportAsFixedFormat($env:SK_OUT, 17) } finally { $d.Close(0) }
if ($was -eq 0) { $app.Quit() }
""",
    "excel": r"""
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject Excel.Application
$was = $app.Workbooks.Count
$app.Visible = $false; $app.DisplayAlerts = $false
try { $app.AutomationSecurity = 3 } catch {}
$wb = $app.Workbooks.Open($env:SK_SRC, 0, $true)
try { $wb.ExportAsFixedFormat(0, $env:SK_OUT) } finally { $wb.Close($false) }
if ($was -eq 0) { $app.Quit() }
""",
    "powerpoint": r"""
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject PowerPoint.Application
$was = $app.Presentations.Count
try { $app.AutomationSecurity = 3 } catch {}
$p = $app.Presentations.Open($env:SK_SRC, -1, 0, 0)
try { $p.SaveAs($env:SK_OUT, 32) } finally { $p.Close() }
if ($was -eq 0) { $app.Quit() }
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


def make(path, folder, timeout=180, runner=None):
    """The PDF copy of a Word, Excel or PowerPoint file (made now if needed). Returns its path. Raises RuntimeError with
    a plain reason when Office is not on this PC or could not save it. runner(cmd, env, timeout) -> (code, out, err)
    replaces the real call in tests."""
    k = kind(path)
    if not k:
        raise RuntimeError("not a Word, Excel or PowerPoint file")
    os.makedirs(folder, exist_ok=True)
    out = copy_path(path, folder)
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    tmp = out + ".part.pdf"
    try:
        os.remove(tmp)
    except OSError:
        pass
    env = dict(os.environ, SK_SRC=os.path.abspath(path), SK_OUT=os.path.abspath(tmp))
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT[k]]
    if runner is None:
        if not available():
            raise RuntimeError("Microsoft Office is needed to show Word, Excel and PowerPoint files as they look")
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            code, err = r.returncode, r.stderr
        except subprocess.TimeoutExpired:
            raise RuntimeError("Office took too long to save the PDF copy")
        except OSError as e:
            raise RuntimeError(f"Windows PowerShell could not start ({type(e).__name__})")
    else:
        code, _o, err = runner(cmd, env, timeout)
    if code != 0 or not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
        msg = (err or b"").decode("utf-8", "replace") if isinstance(err, (bytes, bytearray)) else str(err or "")
        low = msg.lower()
        if "80040154" in low or "class not registered" in low or "comobject" in low and "retriev" in low:
            raise RuntimeError(f"Microsoft {k.capitalize()} is not installed on this PC")
        raise RuntimeError(f"{k.capitalize()} could not save a PDF copy" + (f": {msg.strip().splitlines()[-1][:160]}" if msg.strip() else ""))
    os.replace(tmp, out)
    return out
