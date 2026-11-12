"""Delete a document, or one version of it, into the effort's Trash; and put it back (4.17.0;
claude/stationkeeper-documents-replace-delete-plan-4.17.md). Asked 2026-11-11 17:42: "I need a way to delete or reupload
a specific doc ... move it to a trash can maintained by the app so nothing is truly lost".

what_goes(lib, M, doc_id, vid): what a delete takes, for the question asked first: versions, files, shred pieces (and how
many of them hold a decision). delete(ws, lib, M, doc_id, vid): the files, the versions' kept text, the record and the
pieces of the shred move to the Trash (doctrash). A file another version still uses stays, and so do its pieces.
restore(ws, lib, M, eid): everything back where it was. Rules only (No AI); nothing leaves the PC."""
import copy, os

import doctrash as T


def _decided(it):
    return bool(it.get("decision") or it.get("owner") or it.get("kind_set") or it.get("placed"))


def _scope(lib, doc_id, vid=None):
    d = lib.doc(doc_id)
    if d is None:
        return None, [], False
    vs = [v for v in d["versions"] if vid is None or v["id"] == vid]
    whole = vid is None or len(d["versions"]) <= len(vs)
    return d, vs, whole


def _files_going(lib, d, vs):
    """(file names whose pieces go, paths that move): only what no version left behind still uses."""
    stay = [v for v in d["versions"] if v not in vs]
    stay_names = {v.get("file", "") for v in stay}
    stay_paths = {os.path.normcase(lib.path_of(v) or "") for v in stay}
    names = [v.get("file", "") for v in vs if v.get("file") and v.get("file") not in stay_names]
    paths = []
    for v in vs:
        p = lib.path_of(v)
        if p and os.path.normcase(p) not in stay_paths and p not in paths:
            paths.append(p)
    return list(dict.fromkeys(names)), paths


def what_goes(lib, M, doc_id, vid=None):
    """{"name", "versions", "files", "pieces", "decided", "whole"} for the question asked first."""
    d, vs, whole = _scope(lib, doc_id, vid)
    if d is None:
        return None
    names, paths = _files_going(lib, d, vs)
    pieces = [it for it in (M.items if M is not None else []) if it.get("file") in names and it.get("header") != "Yes"]
    return {"name": d["name"], "versions": [v.get("label", "") for v in vs], "files": [os.path.basename(p) for p in paths],
            "pieces": len(pieces), "decided": sum(1 for it in pieces if _decided(it)), "whole": whole}


def question(info, vid=None):
    """The words of the question asked before a delete."""
    what = f"the document {info['name']}" if info["whole"] else f"{', '.join(info['versions'])} of {info['name']}"
    bits = []
    if info["whole"] and len(info["versions"]) > 1:
        bits.append(f"its {len(info['versions'])} versions")
    if info["files"]:
        bits.append("the file" + ("s " if len(info["files"]) > 1 else " ") + ", ".join(info["files"]))
    if info["pieces"]:
        bits.append(f"{info['pieces']} piece(s) of the shred" + (f", {info['decided']} with a decision" if info["decided"] else ""))
    goes = ("; ".join(bits) + " go with it.") if bits else ""
    return (f"Delete {what}? {goes} They move to the effort's Trash (Documents > More > Trash...), where Restore puts them "
            "back. Nothing is lost until the Trash is emptied.").replace("  ", " ")


def delete(ws, lib, M, doc_id, vid=None):
    """Move the document (or one version) and its pieces to the Trash. Returns the Trash entry id, or None."""
    d, vs, whole = _scope(lib, doc_id, vid)
    if d is None or not vs:
        return None
    names, paths = _files_going(lib, d, vs)
    texts = [os.path.join(lib.folder, v["id"] + ".json") for v in vs]
    payload = {"doc_id": d["id"], "whole": whole, "doc": copy.deepcopy(d) if whole else None,
               "doc_at": lib.all.index(d), "versions": [(d["versions"].index(v), copy.deepcopy(v)) for v in vs],
               "items": [], "sources": [], "headings": [], "texts": [os.path.basename(t) for t in texts]}
    if M is not None and names:
        payload["items"] = [(k, copy.deepcopy(it)) for k, it in enumerate(M.items) if it.get("file") in names]
        payload["sources"] = [list(r) for r in M.sources if r and r[0] in names]
        payload["headings"] = [dict(h) for h in getattr(M, "headings", []) if h.get("file") in names]
        M.items = [it for it in M.items if it.get("file") not in names]
        M.sources = [r for r in M.sources if not (r and r[0] in names)]
        M.headings = [h for h in getattr(M, "headings", []) if h.get("file") not in names]
        M.log("matrix", f"{d['name']}: {len(payload['items'])} piece(s) moved to the Trash with the document")
        M.pending = True
    if whole:
        lib.all.remove(d)
    else:
        for v in vs:
            d["versions"].remove(v)
    lib.save()
    name = d["name"] if whole else f"{d['name']}: {', '.join(v.get('label', '') for v in vs)}"
    return T.put(ws, "document" if whole else "version", name, payload, files=paths + texts)


def restore(ws, lib, M, eid):
    """Put a deleted document or version back: its record, its files and text where they were, its pieces in the shred.
    Returns the entry, or None."""
    e = T.entry(ws, eid)
    if e is None or e["kind"] not in ("document", "version"):
        return None
    e = T.take_back(ws, eid)
    p = e["payload"]
    back = e.get("back") or {}
    for t in p.get("texts", []):                           # the kept text goes back beside the index
        for orig, now in back.items():
            if os.path.basename(orig) == t and os.path.normcase(os.path.dirname(orig)) == os.path.normcase(lib.folder):
                if now != orig and not os.path.exists(orig):
                    os.replace(now, orig)

    def fix_path(v):
        orig = v.get("path", "")
        if orig in back and back[orig] != orig:
            v["path"] = back[orig]
        return v
    if p["whole"]:
        d = p["doc"]
        d["versions"] = [fix_path(v) for v in d["versions"]]
        if lib.doc(d["id"]) is None:
            lib.all.insert(min(p.get("doc_at", len(lib.all)), len(lib.all)), d)
    else:
        d = lib.doc(p["doc_id"])
        if d is None:
            return None
        for i, v in sorted(p["versions"]):
            if not any(x["id"] == v["id"] for x in d["versions"]):
                d["versions"].insert(min(i, len(d["versions"])), fix_path(v))
    lib.save()
    if M is not None and p.get("items"):
        taken = {it.get("id") for it in M.items}
        for k, it in sorted(p["items"], key=lambda x: x[0]):
            if it.get("id") in taken:
                it["id"] = ""                             # its number was given to a new piece meanwhile
            M.items.insert(min(k, len(M.items)), it)
        M.sources += [r for r in p.get("sources", []) if r not in M.sources]
        M.headings += [h for h in p.get("headings", []) if h not in M.headings]
        import compliance as C
        C.assign_ids(M.items)
        M.log("matrix", f"{e['name']}: {len(p['items'])} piece(s) put back from the Trash")
        M.pending = True
    return e
