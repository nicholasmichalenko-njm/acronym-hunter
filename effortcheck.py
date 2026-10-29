"""Effort health (2.80.0): what is checked when an effort opens, with a fix for each problem it can fix.

Errors: the effort list or the compliance matrix is missing or cannot be read (fix: put back its newest dated copy).
Warnings: a damaged settings or record file (fix: put back a backup package), the customer documents folder moved
(fix: find it), the live effort sits in a folder OneDrive uploads (fix: move it to this PC), a path longer than Windows
handles well, little free disk space, a sync conflict copy beside the effort's files (OneDrive keeps both copies when two
PCs save; compare it with Restore). Pure Python, no network.
"""
import json, os, re, shutil

LONG_PATH = 240
LOW_DISK = 500 * 1024 * 1024


def _issue(kind, severity, text, fix=""):
    return {"kind": kind, "severity": severity, "text": text, "fix": fix}


def _readable_xlsx(path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        wb.close()
        return True
    except Exception:
        return False


def check(ws, list_path, matrix_path="", customer_dir="", volumes_dir=""):
    """[{kind, severity ('error'|'warn'), text, fix}] for the open effort."""
    out = []
    copies = {k: [b for b in ws.backups(k)] for k in ("effort", "matrix")}
    if not os.path.isfile(list_path):
        out.append(_issue("list_missing", "error", "The effort list is missing from its folder.", "restore_list" if copies["effort"] else ""))
    elif not _readable_xlsx(list_path):
        out.append(_issue("list_damaged", "error", "The effort list cannot be read (the file is damaged).", "restore_list" if copies["effort"] else ""))
    if matrix_path:
        if not os.path.isfile(matrix_path):
            out.append(_issue("matrix_missing", "error", "The compliance matrix is missing from its folder.",
                              "restore_matrix" if copies["matrix"] else ""))
        elif not _readable_xlsx(matrix_path):
            out.append(_issue("matrix_damaged", "error", "The compliance matrix cannot be read (the file is damaged).",
                              "restore_matrix" if copies["matrix"] else ""))
    for d, _dirs, files in os.walk(ws.root):
        if os.path.basename(d) in ("backups", "recovery"):
            continue
        for f in files:
            if f.endswith(".json") and f != "lock.json":
                p = os.path.join(d, f)
                try:
                    with open(p, encoding="utf-8") as fh:
                        json.load(fh)
                except (OSError, ValueError):
                    out.append(_issue("json_damaged", "warn", f"A saved file of the effort cannot be read: {f}. Put back a backup "
                                      "package (Effort record > Restore...).", "restore_package"))
    if customer_dir and not os.path.isdir(customer_dir):
        out.append(_issue("customer_moved", "warn", "The customer documents folder is not where it was. Show Stationkeeper where it "
                          "is now.", "find_customer"))
    if volumes_dir and not os.path.isdir(volumes_dir):
        out.append(_issue("volumes_moved", "warn", "The volumes folder is not where it was. Show Stationkeeper where it is now.", "find_volumes"))
    try:
        import workmode as WM
        if WM.is_synced(os.path.dirname(os.path.abspath(list_path))):
            out.append(_issue("live_synced", "warn", "This effort's working files sit in a folder OneDrive uploads. Two PCs saving "
                              "at once can leave conflict copies. Keep the live effort on this PC and share it through packages "
                              "and backups in the team folder.", "move_local"))
    except Exception:
        pass
    longest = max([len(os.path.abspath(p)) for p in (list_path, matrix_path) if p] +
                  [len(os.path.join(d, f)) for d, _x, fs in os.walk(ws.root) for f in fs] or [0])
    if longest > LONG_PATH:
        out.append(_issue("long_path", "warn", f"Some of the effort's file paths are {longest} characters long; Windows and Office "
                          "can fail past 260. Use a shorter folder (for example move the effort to this PC).", "move_local"))
    try:
        if shutil.disk_usage(os.path.dirname(os.path.abspath(list_path))).free < LOW_DISK:
            out.append(_issue("low_disk", "warn", "Less than 500 MB of disk space is free; saves and backups can fail. Free some space."))
    except OSError:
        pass
    for p in (list_path, matrix_path):
        if not p:
            continue
        d, stem = os.path.dirname(os.path.abspath(p)), os.path.splitext(os.path.basename(p))[0]
        if os.path.isdir(d):
            pat = re.compile(rf"^{re.escape(stem)}-[A-Za-z0-9_.-]+\.xlsx$", re.I)
            for f in sorted(os.listdir(d)):
                if pat.match(f):
                    out.append(_issue("conflict_copy", "warn", f"A sync conflict copy is beside the effort's files: {f}. OneDrive keeps "
                                      "both copies when two PCs save. Compare it before deleting it.", ""))
    return out


def summary(issues):
    e = sum(1 for i in issues if i["severity"] == "error")
    w = len(issues) - e
    if not issues:
        return "Effort health: everything checks out."
    return "Effort health: " + ", ".join(x for x in ((f"{e} problem(s) to fix" if e else ""), (f"{w} warning(s)" if w else "")) if x) + "."


def restore_copy(ws, kind, target):
    """Put back the newest dated copy that can be read; the damaged file is kept beside it. Returns the copy used."""
    for path, _k, _stem, when in ws.backups(kind):
        if _readable_xlsx(path):
            if os.path.exists(target):
                import datetime
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                base, ext = os.path.splitext(target)
                shutil.move(target, f"{base} (damaged {stamp}){ext}")
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            shutil.copy2(path, target)
            return path
    return None
