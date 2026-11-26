"""Deliverables that act (4.81.0; step D2 of claude/stationkeeper-deliverables-that-act-and-the-documents-door-direction-2026-11-25.md;
UX decisions 175, 176, 187). Each deliverable says what has to happen to it next, worked out from its kind and its file and
never set by hand: one action, named for the next thing to do (Redline it, Make a Word file, Open the form, Attach a
file..., Open in Outline), or none when there is nothing to do ("File is here").

Its file lives once, in Documents, and the deliverable points at it: the customer's file (the form to fill in, the document
to redline) as doc_id, as the 4.25.3 tiles already do; ours (the file we submit) as our_doc. A file added from the Shred
bar's "Add a file now..." goes through Documents' own Add and is attached once it is in (file_wanted). The state is worked
out too: Nothing yet; In work (it has our file, a Word copy was made, or the team moved it on); Ready is not reached until
the Submission Check reads this list. Rules only (No AI); nothing leaves the PC. Standard library only."""
import difflib, os, re

import deliverables as DL

NAME = {"write": "Document We Write", "form": "Form We Fill In", "file": "File We Submit", "redline": "Redline We Return"}
STATES = ("Nothing yet", "In work", "Ready")
PDFISH = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")
LABEL = {"redline": "Redline it", "word": "Make a Word file", "form": "Open the form", "attach": "Attach a file...",
         "outline": "Open in Outline"}
TIP = {"redline": "Opens the Word file to mark up",
       "word": "A Word file of the customer's PDF, made in the effort's Redlines folder (Redlining > Prepare)",
       "form": "Opens the form where it is in Documents. No copy is made",
       "attach": "Pick its file from Documents",
       "outline": "The Outline, where this volume is planned"}
MARK = {"redline": "redline", "form": "fill"}             # the mark the customer's document gets in Documents (docmarks.RETURNS)


def kind_key(d):
    """The pass's kind ("write", "form", "file", "redline"), from the Shred mark, else read from the list's own kind."""
    k = d.get("shred_kind")
    if k in NAME:
        return k
    kind = d.get("kind") or ""
    if kind == "Customer file":
        return "form" if d.get("returns") == "fill" else "redline"
    return {"Form": "form", "Volume": "write", "Attachment": "file"}.get(kind, "")


def kind_name(d):
    return NAME.get(kind_key(d)) or d.get("kind") or "Deliverable"


def _latest_path(lib, doc_id):
    doc = lib.doc(doc_id) if lib is not None and doc_id else None
    if not doc or not doc.get("versions"):
        return None, ""
    try:
        return doc, lib.path_of(doc["versions"][-1])
    except Exception:  # noqa: BLE001
        return doc, ""


def copy_of(path, folder):
    """The Word copy Redlining's Prepare made of a PDF or a picture, or ""."""
    if not path or not folder:
        return ""
    try:
        import redlineprep as RP
        return RP.state(folder, path).get("copy") or ""
    except Exception:  # noqa: BLE001
        return ""


def due_of(rec, d):
    """The deliverable's own due date, else the proposal's (one value with Customer information, 4.78.0)."""
    own = (d.get("due") or "").strip()
    if own:
        return own[:10]
    return ((rec.data.get("due") if rec is not None else "") or "")[:10]


def next_of(d, lib=None, folder="", volume="", due=""):
    """What the row shows and does: {kind, key, file, file_line, ref, due, state, action, label, tip, path, doc_id}."""
    k = kind_key(d)
    cust, cpath = _latest_path(lib, d.get("doc_id"))
    ours, opath = _latest_path(lib, d.get("our_doc"))
    if ours is None and d.get("file"):
        opath = d["file"]
    out = {"kind": kind_name(d), "key": k, "file": "", "file_line": "No file yet", "ref": d.get("cust_ref", ""), "due": due,
           "state": "Nothing yet", "action": "", "label": "", "tip": "", "path": "", "doc_id": d.get("doc_id", "")}
    names = []
    if cust is not None:
        names.append(cust.get("name", ""))
    if ours is not None:
        names.append(("ours: " if names else "") + ours.get("name", ""))
    elif opath:
        names.append(("ours: " if names else "") + os.path.basename(opath))
    if names:
        out["file"] = "; ".join(n for n in names if n)
        out["file_line"] = "Its file: " + out["file"]
    copy = ""
    if k == "write":
        out["action"] = "outline"
    elif k == "file":
        if ours is not None or opath:
            out["file_line"] = (out["file_line"] + ". File is here") if names else "File is here"
        else:
            out["action"] = "attach"
    elif k in ("form", "redline"):
        if cust is None:
            out["action"] = "attach"
        elif os.path.splitext(cpath or "")[1].lower() in PDFISH:
            copy = copy_of(cpath, folder)
            out["action"], out["path"] = (k, copy) if copy else ("word", cpath)
        else:
            out["action"], out["path"] = k, cpath
    elif not names:
        out["action"] = "attach"
    if out["action"]:
        out["label"], out["tip"] = LABEL[out["action"]], TIP[out["action"]]
        if out["action"] == "outline" and volume:
            out["tip"] = f"The Outline, where {volume} is planned"
    if ours is not None or opath or copy or (d.get("status") or "Not started") != "Not started":
        out["state"] = "In work"
    return out


def line(nx):
    """One line for the row: the state, its file, the customer's reference, the due date."""
    bits = [nx["state"], nx["file_line"]]
    if nx.get("ref"):
        bits.append(nx["ref"])
    if nx.get("due"):
        bits.append("Due " + nx["due"])
    return "  ·  ".join(bits)


def _norm(s):
    s = os.path.splitext(s or "")[0] if re.search(r"\.[a-z0-9]{2,4}$", s or "", re.I) else (s or "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def suggest(lib, d):
    """The document in Documents whose name matches the deliverable's (the customer's words), or "". The match is the
    outline marking's: alike at 0.6, or one name's words all inside the other's, two words or more."""
    if lib is None:
        return ""
    want = _norm(d.get("name"))
    words = set(want.split()) - {"the", "a", "an", "of", "and", "for", "to"}
    best = (0.0, "")
    for doc in lib.all:
        names = [doc.get("name", "")] + [os.path.basename(v.get("path", "") or "") for v in (doc.get("versions") or [])[-1:]]
        for n in names:
            c = _norm(n)
            if not c or not want:
                continue
            r = difflib.SequenceMatcher(None, want, c).ratio()
            cw = set(c.split()) - {"the", "a", "an", "of", "and", "for", "to"}
            if min(len(words), len(cw)) >= 2 and (words <= cw or cw <= words):
                r = max(r, 0.8)
            if r > best[0]:
                best = (r, doc["id"])
    return best[1] if best[0] >= 0.6 else ""


def slot_of(d):
    """Where an attached file goes: the customer's (doc_id) for a form or a redline, else ours (our_doc)."""
    return "doc_id" if kind_key(d) in MARK else "our_doc"


def attach(rec, lib, did, doc_id, who=None):
    """Point the deliverable at a document in Documents. A form or a redline takes it as the customer's file and the
    document is marked Filled-in or Redlined Deliverable (the 4.25.3 link, both ways); anything else as ours. Returns
    the slot, or ""."""
    d = DL.get(rec, did)
    doc = lib.doc(doc_id) if lib is not None and doc_id else None
    if d is None or doc is None:
        return ""
    slot = slot_of(d)
    d[slot] = doc_id
    if slot == "doc_id":
        k = kind_key(d)
        d["returns"] = MARK[k]
        d["form_version"] = (doc.get("versions") or [{}])[-1].get("id", "")
        have = lib.returns_of(doc)
        if MARK[k] not in have:
            lib.set_returns(doc_id, have + [MARK[k]])
    d.pop("file_wanted", None)
    rec.log("deliverable", f"{d['name']}: its file is {doc.get('name', '')}", ref={"deliverable": did}, who=who)
    rec.save()
    return slot


def want(rec, did, path, who=None):
    """Add a file now: the file goes through Documents' own Add; the deliverable waits for it by its file name."""
    d = DL.get(rec, did)
    if d is None or not path:
        return False
    d["file_wanted"] = os.path.basename(path)
    rec.log("deliverable", f"{d['name']}: waiting for {d['file_wanted']} to be in Documents", ref={"deliverable": did}, who=who)
    rec.save()
    return True


def take_wanted(rec, lib):
    """Attach every file a deliverable is waiting for that is now in Documents. Returns how many."""
    if lib is None:
        return 0
    n = 0
    for d in DL.items(rec):
        w = (d.get("file_wanted") or "").lower()
        if not w:
            continue
        for doc in lib.all:
            v = (doc.get("versions") or [{}])[-1]
            if os.path.basename(v.get("path", "") or "").lower() == w or os.path.basename(lib.path_of(v) or "").lower() == w:
                n += bool(attach(rec, lib, d["id"], doc["id"]))
                break
    return n


def has_file(d):
    return bool(d.get("doc_id") or d.get("our_doc") or d.get("file"))
