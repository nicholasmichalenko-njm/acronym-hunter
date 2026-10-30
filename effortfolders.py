"""An effort's own folders (2.90.0): one folder per effort, laid out so a person can find everything without the app.

    <effort>\\
      Customer Documents\\     the RFP and its attachments, as the customer sent them
      Volumes\\                the Word volumes the team writes
      Response Setup\\         the documents writers start from
      Exports\\                acronym lists, status reports, the calendar, reviews, Export all
      <name>_Compliance_Matrix.xlsx
      <name>_Effort_List.xlsx
      <name>_Effort_List - app data\\   the app's working files for the effort (a note inside says not to edit them)

A new effort gets the four folders. An older effort keeps its files where they are; a folder appears the first time
something is saved into it. Every save still asks where to put the file: these are only where the dialog starts.
Standard library only.
"""
import os

SUBS = {"customer": "Customer Documents", "volumes": "Volumes", "setup": "Response Setup", "exports": "Exports"}
NOTE = "About this folder.txt"
NOTE_TEXT = ("Stationkeeper keeps this effort's working files here: the record, the document library and its versions,\r\n"
             "what was taken from documents, change decisions, backups of the matrix and the calendar.\r\n\r\n"
             "Do not edit, move or rename anything in this folder. Keep it beside the effort list: effort packages and\r\n"
             "backups carry it, and the effort opens from it. Your own files go in the folders beside it.\r\n")


_FIELDS = {}                       # 2.95.0: effort root -> its fields (name, client, solicitation...) for folder and file names


def root(effort_path):
    """The effort's folder. 2.95.0: when the team keeps the effort list in a folder of its tree (Settings > Folders and
    file names), the root is that many folders up (kept in the effort's settings as root_up)."""
    if not effort_path:
        return ""
    d = os.path.dirname(os.path.abspath(effort_path))
    up = _root_up(effort_path)
    for _ in range(up):
        d = os.path.dirname(d)
    return d


def _root_up(effort_path):
    import json
    import workspace as W
    try:
        with open(os.path.join(W.data_dir_for(effort_path), "settings.json"), encoding="utf-8") as f:
            return max(0, min(4, int((json.load(f) or {}).get("root_up", 0))))
    except (OSError, ValueError, TypeError):
        return 0


def remember(effort_path, fields):
    """2.95.0: the effort's fields for folder names with {Effort}, {Client}..."""
    if effort_path:
        _FIELDS[root(effort_path)] = {k: v for k, v in (fields or {}).items() if v}


def fields_of(effort_path):
    return dict(_FIELDS.get(root(effort_path), {}))


def _make(p, fallback):
    try:
        os.makedirs(p, exist_ok=True)
        return p
    except OSError:
        return fallback


def folder(effort_path, kind, make=True):
    """The effort's folder with that job (customer, volumes, setup, exports; 2.95.0: as the team's tree names it), created
    unless make is False; '' with no effort."""
    import folderplan as FP
    r = root(effort_path)
    if not r:
        return ""
    parts = FP.folder_path(FP.folder_of(role=kind), fields_of(effort_path)) or [SUBS[kind]]
    p = os.path.join(r, *parts)
    return _make(p, r) if make else p


def place(effort_path, key, fields=None, ext=None, make=True):
    """2.95.0: where a save dialog starts for an output: its folder in the team's tree, with its name by the team's
    pattern ("" for an output that is a folder). Fields add to the effort's own."""
    import folderplan as FP
    r = root(effort_path)
    f_all = dict(fields_of(effort_path), **{k: v for k, v in (fields or {}).items() if v})
    if not r:
        return FP.name_of(key, f_all, ext=ext) if key in FP.OUT else ""
    parts = FP.folder_path(FP.folder_of(key), f_all)
    d = os.path.join(r, *parts) if parts else r
    if make:
        d = _make(d, r)
    if key not in FP.OUT or not FP.OUT[key][3] and ext is None:
        return d
    return os.path.join(d, FP.next_version(d, key, f_all, ext=ext))


def out(effort_path, name="", kind="exports"):
    """Where a save dialog starts: the effort's Exports (or other) folder, with the suggested file name."""
    f = folder(effort_path, kind)
    return os.path.join(f, name) if f and name else (f or name)


def create_all(effort_path, fields=None):
    """Every folder of the team's tree (2.95.0), then the four jobs' folders. Existing folders are left as they are."""
    import folderplan as FP
    if fields:
        remember(effort_path, fields)
    r = root(effort_path)
    if not r:
        return []
    made = []
    for t in FP.current()["tree"]:
        parts = FP.folder_path(t["path"], fields_of(effort_path))
        if parts:
            made.append(_make(os.path.join(r, *parts), r))
    return list(dict.fromkeys(made + [folder(effort_path, k) for k in SUBS]))


def new_list_path(efforts_dir, name, fields=None):
    """2.95.0: where a new effort's list goes: Efforts/<name>/[the team's home folder]/<list name>. Returns (path, how
    many folders up the effort's root is)."""
    import folderplan as FP
    import re
    safe = re.sub(r"[^A-Za-z0-9 _.-]+", "", name).strip() or "Effort"
    f = dict(fields or {}, Effort=name)
    home = FP.folder_path(FP.current().get("home", ""), f)
    nm = FP.name_of("effort_list", f)
    return os.path.join(efforts_dir, safe.replace(" ", "_"), *home, nm), len(home)


def note_app_data(data_dir):
    """The note inside the effort's app data folder (written once)."""
    p = os.path.join(data_dir, NOTE)
    if data_dir and os.path.isdir(data_dir) and not os.path.exists(p):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(NOTE_TEXT)
        except OSError:
            pass
    return p
