"""The effort's Trash (4.17.0; claude/stationkeeper-documents-replace-delete-plan-4.17.md). Nothing Documents deletes or
replaces is lost: the files, the document's record and its shred pieces move into <effort data>\\trash\\<entry>, each
entry with entry.json (what it was, when, who, what was in it). Restore puts an entry back; Empty the Trash removes
entries for good, and only when asked. Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, json, os, shutil, uuid


def folder(ws):
    """<effort data>\\trash; ws is the effort's workspace or its data folder."""
    return ws.p("trash") if hasattr(ws, "p") else os.path.join(ws, "trash")


def put(ws, kind, name, payload, files=()):
    """Move files (paths) into a new entry with payload. Returns the entry id. A file that is gone is noted, not moved."""
    eid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f-") + uuid.uuid4().hex[:4]     # newest sorts last
    d = os.path.join(folder(ws), eid)
    os.makedirs(os.path.join(d, "files"), exist_ok=True)
    kept = []
    for k, p in enumerate(dict.fromkeys(f for f in files if f)):
        rec = {"orig": os.path.abspath(p), "kept": ""}
        if os.path.isfile(p):
            dst = os.path.join(d, "files", f"{k:02d}-{os.path.basename(p)}")
            shutil.move(p, dst)
            rec["kept"] = os.path.relpath(dst, d)
        kept.append(rec)
    entry = {"id": eid, "kind": kind, "name": name, "when": datetime.datetime.now().isoformat(timespec="seconds"),
             "who": getpass.getuser(), "files": kept, "payload": payload}
    with open(os.path.join(d, "entry.json"), "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=1, ensure_ascii=False)
    return eid


def entries(ws):
    """Every entry, newest first."""
    out = []
    base = folder(ws)
    if not os.path.isdir(base):
        return out
    for n in sorted(os.listdir(base), reverse=True):
        try:
            with open(os.path.join(base, n, "entry.json"), encoding="utf-8") as f:
                out.append(json.load(f))
        except (OSError, ValueError):
            continue
    return out


def entry(ws, eid):
    return next((e for e in entries(ws) if e["id"] == eid), None)


def take_back(ws, eid):
    """Move an entry's files back where they were (a file there now keeps its place: the old one comes back beside it,
    named with "restored"), remove the entry and return it with "back": {orig: where it went}."""
    e = entry(ws, eid)
    if e is None:
        return None
    d = os.path.join(folder(ws), eid)
    back = {}
    for rec in e["files"]:
        if not rec.get("kept"):
            continue
        src = os.path.join(d, rec["kept"])
        dst = rec["orig"]
        if os.path.exists(dst):
            stem, ext = os.path.splitext(dst)
            dst = f"{stem} (restored {datetime.datetime.now().strftime('%Y-%m-%d %H%M')}){ext}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        back[rec["orig"]] = dst
    shutil.rmtree(d, ignore_errors=True)
    e["back"] = back
    return e


def empty(ws, eid=None):
    """Remove one entry (or every entry) for good. Returns how many."""
    n = 0
    for e in entries(ws):
        if eid is None or e["id"] == eid:
            shutil.rmtree(os.path.join(folder(ws), e["id"]), ignore_errors=True)
            n += 1
    return n


def size(ws):
    total = 0
    for root, _dirs, files in os.walk(folder(ws)):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total
