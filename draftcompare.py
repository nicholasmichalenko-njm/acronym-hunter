"""Compare our own drafts (3.4.0): two versions of a volume (the red team copy and today's, say), sentence by sentence
under their headings, with the same engine Changes uses for the customer's documents: what changed (words struck
through and added), what was added and what was removed. The answer to "what changed since red team?". Writes a Word
redline; changes neither file. Rules only."""
import datetime, getpass, hashlib, os

import docversions as DV


def snapshot(path):
    """[{"x": sentence, "s": heading it sits under, "t": ""}] from a .docx, in reading order."""
    import setupdoc as SD
    import walloftruth as WT
    out, head = [], ""
    for text, style, level in SD.docx_paragraphs(path):
        t = " ".join((text or "").split())
        if not t:
            continue
        if level is not None or (style or "").lower().startswith("heading"):
            head = t
            continue
        for s in WT.sentences(t):
            out.append({"x": s, "s": head, "t": ""})
    return out


def _version(path, label):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    st = os.stat(path)
    return {"label": label, "file": os.path.basename(path), "added": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "who": "saved", "sha256": h.hexdigest()}


def compare(old_path, new_path):
    """{"rows" (DV.compare rows), "counts" {changed, added, removed, same}, "old", "new"}."""
    rows = DV.compare(snapshot(old_path), snapshot(new_path))
    return {"rows": rows, "counts": DV.summary(rows), "old": _version(old_path, "Earlier"), "new": _version(new_path, "Later")}


def by_section(rows):
    """{heading: {"changed", "added", "removed"}} for the headings where anything changed."""
    out = {}
    for r in rows:
        if r["kind"] == "same":
            continue
        d = out.setdefault(r["section"] or "(before the first heading)", {"changed": 0, "added": 0, "removed": 0})
        d[r["kind"]] += 1
    return out


def export(path, result, name="", only_changes=True):
    old, new = dict(result["old"]), dict(result["new"])
    old["who"] = new["who"] = getpass.getuser()
    return DV.export_redline(path, name or new["file"], old, new, result["rows"], only_changes)
