"""The section panel's records (3.83.0, claude/stationkeeper-redesign-decisions-2026-11-08.md): what Review and Setup
show under a section, in one place.

    Management guidance            the section's direction to authors, saved as it is typed (the setup's "mgmt")
    References and notes for authors   files from the Effort Library, files added, or a note; each becomes a Word
                                   comment on the section's heading in the setup (3.86.0) and Strip setup takes it out
    Notes and context              what the effort already holds about the section: notes pointed at it, meeting
                                   topics aimed at it, captures placed in it. Copy one into the guidance, send it to
                                   the authors as a reference, or keep it as context.

guidance(M, label) / set_guidance(M, label, text)
refs(M, label) / add_ref(M, label, path="", note="", where="", origin="") / update_ref / remove_ref / comment_text(ref)
context(rec, label) -> [{"key","kind","source","text","at","used"}] / mark_used(rec, key, how)
copy_into_guidance(M, rec, label, key) / send_to_authors(M, rec, label, key)
unassigned(rec) / point_at(rec, nid, label) / note_on(rec, label, text)
relabel(rec, mapping): notes pointed at a section follow it when the structure renames or moves it.
References are kept in the matrix's setup ("authorrefs", additive); marks in the effort record. Rules only; nothing
leaves the PC."""
import datetime, os

import setupdoc as SD

KIND_NAME = {"note": "Note", "topic": "Meeting topic", "capture": "Capture"}
ORIGIN_NAME = {"library": "From the Effort Library", "file": "Added file", "note": "Note", "context": "From the notes"}


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _pending(M):
    if hasattr(M, "pending"):
        M.pending = True


# ------------------------------------------------------------------ guidance
def guidance(M, label):
    return SD.setup_of(M)["mgmt"].get(label, "")


def set_guidance(M, label, text):
    """Saved as typed: an empty box takes the section's guidance out. Returns True when it changed."""
    S = SD.setup_of(M)
    text = (text or "").rstrip()
    if S["mgmt"].get(label, "") == text:
        return False
    if text:
        S["mgmt"][label] = text
    else:
        S["mgmt"].pop(label, None)
    _pending(M)
    return True


# ------------------------------------------------------------------ references for authors
def _store(M):
    S = SD.setup_of(M)
    if not isinstance(S.get("authorrefs"), dict):
        S["authorrefs"] = {}
    return S["authorrefs"]


def refs(M, label):
    return list(_store(M).get(label, []))


def _rid(M):
    used = {r.get("id") for lst in _store(M).values() for r in lst}
    n = len(used) + 1
    while f"R{n:03d}" in used:
        n += 1
    return f"R{n:03d}"


def add_ref(M, label, path="", note="", where="", origin=""):
    """A file (with where to look in it) or a note alone. Returns the reference's id, or None for nothing."""
    path, note, where = (path or "").strip(), (note or "").strip(), (where or "").strip()
    if not path and not note:
        return None
    lst = _store(M).setdefault(label, [])
    if path and any(r.get("path") == path for r in lst):
        return next(r["id"] for r in lst if r.get("path") == path)
    r = {"id": _rid(M), "path": path, "name": os.path.basename(path.replace("\\", "/")) if path else "",
         "where": where, "note": note, "origin": origin if origin in ORIGIN_NAME else ("file" if path else "note"),
         "at": _now()}
    lst.append(r)
    _pending(M)
    return r["id"]


def update_ref(M, label, rid, **f):
    for r in _store(M).get(label, []):
        if r.get("id") == rid:
            changed = False
            for k in ("where", "note"):
                if k in f and (f[k] or "").strip() != r.get(k, ""):
                    r[k] = (f[k] or "").strip()
                    changed = True
            if changed:
                _pending(M)
            return changed
    return False


def remove_ref(M, label, rid):
    lst = _store(M).get(label, [])
    keep = [r for r in lst if r.get("id") != rid]
    if len(keep) == len(lst):
        return False
    if keep:
        _store(M)[label] = keep
    else:
        _store(M).pop(label, None)
    _pending(M)
    return True


def comment_text(r):
    """The Word comment's words: the file, where to look, the note."""
    lines = []
    if r.get("name"):
        lines.append(f"Reference: {r['name']}" + (f" ({r['where']})" if r.get("where") else ""))
    if r.get("note"):
        lines.append(r["note"])
    return "\n".join(lines)


def describe(r):
    """One line for the list."""
    if r.get("name"):
        return r["name"] + (f"  ·  {r['where']}" if r.get("where") else "") + (f"  ·  {r['note']}" if r.get("note") else "")
    return r.get("note", "")


# ------------------------------------------------------------------ notes and context
def _used(rec):
    return rec.data.setdefault("section_ctx_used", {})


def context(rec, label):
    """What the effort already holds about the section, newest first."""
    import excerpts as EX
    import meetings as MT
    used = _used(rec)
    out = []
    for n in rec.notes(on="section", on_id=label):
        out.append({"key": "note:" + n["id"], "kind": "note", "source": n.get("who", ""), "text": n["text"], "at": n["at"]})
    for m, t in MT.topics(rec, target=label):
        out.append({"key": f"topic:{m.get('id', '')}:{t.get('id', '')}", "kind": "topic",
                    "source": m.get("title") or m.get("name") or "Meeting", "text": t.get("text") or t.get("title", ""),
                    "at": m.get("date") or m.get("at", "")})
    for x in EX.in_section(rec, label):
        out.append({"key": "capture:" + str(x.get("id", "")), "kind": "capture", "source": EX.SOURCE_NAME.get(EX.source_of(x), ""),
                    "text": EX.text_of(x) or x.get("value", ""), "at": x.get("at", "")})
    for c in out:
        c["used"] = used.get(c["key"], "")
    return sorted(out, key=lambda c: c["at"] or "", reverse=True)


def mark_used(rec, key, how):
    """how: 'guidance', 'authors', 'context' (kept as context), or '' to clear."""
    u = _used(rec)
    if how:
        u[key] = how
    else:
        u.pop(key, None)
    rec.save()


def _item(rec, label, key):
    return next((c for c in context(rec, label) if c["key"] == key), None)


def copy_into_guidance(M, rec, label, key):
    """Adds the item's words to the end of the guidance. Returns the new guidance, or None."""
    c = _item(rec, label, key)
    if c is None or not c["text"].strip():
        return None
    cur = guidance(M, label)
    if c["text"].strip() in cur:
        new = cur
    else:
        new = (cur.rstrip() + "\n\n" if cur.strip() else "") + c["text"].strip()
    set_guidance(M, label, new)
    mark_used(rec, key, "guidance")
    return new


def send_to_authors(M, rec, label, key):
    """The item becomes a note for the authors (a Word comment). Returns the reference's id, or None."""
    c = _item(rec, label, key)
    if c is None:
        return None
    rid = add_ref(M, label, note=c["text"], origin="context")
    if rid:
        mark_used(rec, key, "authors")
    return rid


# ------------------------------------------------------------------ the unassigned tray
def unassigned(rec):
    import quicknote as QN
    return list(QN.inbox(rec))


def note_on(rec, label, text, who=None):
    return rec.add_note(text, on="section", on_id=label, label=label, who=who)


def point_at(rec, nid, label, who=None):
    """A note waiting in the tray goes to a section."""
    import quicknote as QN
    return QN.send_from_inbox(rec, nid, "section:" + label, who=who)


def relabel(rec, mapping):
    """Notes pointed at a section follow it; a section taken out leaves its notes on the effort."""
    n = 0
    for x in rec.data.get("notes", []):
        if x.get("on") == "section" and x.get("on_id") in mapping:
            new = mapping[x["on_id"]]
            if new:
                x["on_id"] = x["label"] = new
            else:
                x["on"], x["on_id"] = "effort", ""
            n += 1
    if n:
        rec.save()
    return n
