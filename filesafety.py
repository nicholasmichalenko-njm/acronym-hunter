"""File safety (3.57.0, claude/stationkeeper-direction-decisions-2026-11-05.md): authoring lives in shared Word files on
SharePoint, so Stationkeeper reads a file and writes a new one; it never saves over what it read. Before reading, it says
what lowers trust in the result: the file sits in a OneDrive or SharePoint folder (it may change while you work, and a
save into it can make a conflict copy), Word has it open (its ~$ owner file), it holds other people's tracked changes,
or it is an old .doc or a macro file.

sync_folder(path) / word_owner(path) / others_changes(path, me) / warnings(path, me) / new_path(path, tag, when, folder)
/ guard(out_path, *inputs) raises WouldOverwrite. Rules only; nothing leaves the PC."""
import datetime, os, re, zipfile


class WouldOverwrite(Exception):
    """An output path that is one of the files read."""


def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p or "")))


def sync_folder(path):
    """'OneDrive' or 'SharePoint' when the file sits in a synced folder, else ''."""
    p = _norm(path)
    for var in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        root = os.environ.get(var)
        if root and (p + os.sep).startswith(_norm(root) + os.sep):
            return "OneDrive"
    parts = re.split(r"[\\/]", os.path.normpath(os.path.abspath(path or "")))
    if any(x.lower().startswith("sharepoint") or " - sharepoint" in x.lower() for x in parts):
        return "SharePoint"
    if any(x.lower() == "onedrive" or x.lower().startswith("onedrive - ") for x in parts):
        return "OneDrive"
    return ""


def word_owner(path):
    """(True, name or '') when Word's owner file (~$...) sits beside the file: someone has it open. (False, '') otherwise."""
    d, n = os.path.split(path or "")
    for cand in ("~$" + n, "~$" + n[2:]):
        f = os.path.join(d, cand)
        if len(cand) > 2 and os.path.isfile(f):
            who = ""
            try:
                with open(f, "rb") as fh:
                    b = fh.read(64)
                k = b[0] if b else 0
                who = b[1:1 + k].decode("latin-1", "replace").strip() if 0 < k < 60 else ""
            except OSError:
                pass
            return True, who
    return False, ""


def others_changes(path, me=""):
    """{author: tracked changes} by people other than me in a .docx ({} when none or not a Word file)."""
    if os.path.splitext(path or "")[1].lower() not in (".docx", ".docm"):
        return {}
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return {}
    out = {}
    for m in re.finditer(r'<w:(?:ins|del|moveFrom|moveTo)\b[^>]*\bw:author="([^"]*)"', xml):
        who = m.group(1) or "unknown"
        if me and who.casefold() == me.casefold():
            continue
        out[who] = out.get(who, 0) + 1
    return out


def warnings(path, me=""):
    """Plain sentences about what lowers trust in what is read from this file ([] when nothing does)."""
    out = []
    where = sync_folder(path)
    if where:
        out.append(f"This file is in a {where} folder: it can change while you work. Stationkeeper reads it and writes "
                   "a new file; it never saves over it.")
    open_, who = word_owner(path)
    if open_:
        out.append(f"Word has this file open{' (' + who + ')' if who else ''}: what is read is the last saved version.")
    ch = others_changes(path, me)
    if ch:
        n = sum(ch.values())
        out.append(f"It holds {n} tracked change{'s' if n != 1 else ''} by " + ", ".join(sorted(ch)) +
                   ": the result reads the text with them as if accepted.")
    ext = os.path.splitext(path or "")[1].lower()
    if ext == ".doc":
        out.append("This is an old .doc file: save it as .docx in Word for a full read.")
    elif ext == ".docm":
        out.append("This file carries macros (.docm): Stationkeeper reads it but never runs them.")
    return out


def new_path(path, tag, when=None, folder=None):
    """A new file beside the original (or in folder): '<name>_<tag>_<date>_<time><ext>', never an existing file."""
    when = when or datetime.datetime.now()
    stem, ext = os.path.splitext(os.path.basename(path))
    folder = folder or os.path.dirname(path)
    base = os.path.join(folder, f"{stem}_{tag}_{when:%Y-%m-%d_%H%M}")
    out, k = base + ext, 2
    while os.path.exists(out):
        out, k = f"{base} ({k}){ext}", k + 1
    return out


def guard(out_path, *inputs):
    """Raise WouldOverwrite when out_path is one of the files read."""
    o = _norm(out_path)
    for p in inputs:
        if p and _norm(p) == o:
            raise WouldOverwrite(out_path)
    return out_path
