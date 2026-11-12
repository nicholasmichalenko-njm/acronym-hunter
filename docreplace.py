"""Replace a document's file, keeping it the same document and the same version (4.17.0;
claude/stationkeeper-documents-replace-delete-plan-4.17.md). Asked 2026-11-11 17:42: "it's not clear how I can rescan the
same doc and have the shred process identify it as the same and not a new version".

- changed_on_disk(lib): the documents whose file was edited where it sits (its bytes are not the ones read).
- replace(ws, lib, doc_id, new_path=None): the new file takes the old one's place and name (new_path None: the file
  edited in place is read again). The old file and its kept text go to the Trash first. The version keeps its label;
  its fingerprint, text and sentence count are the new file's, and it remembers it was replaced.
- merge(M, file, items, heads, src): the file's fresh extract into the shred. A sentence that stayed keeps its piece and
  every decision on it (moved to its new page and place); a changed sentence keeps its piece and decisions with the new
  words (marked "Changed when the file was replaced"); a new sentence is a new piece; a piece whose sentence is gone
  goes to the Trash with the old file. The file's headings and set-aside lines are read afresh.
Rules only (No AI); nothing leaves the PC."""
import copy, datetime, getpass, os, shutil

import docversions as DV
import doctrash as T

MARK = "Changed when the file was replaced"


def changed_on_disk(lib):
    """[(doc, version)]: the latest version's file is there but is no longer the file that was read."""
    out = []
    for d in lib.docs:
        v = lib.latest(d)
        p = lib.path_of(v) if v else ""
        if not p or not os.path.isfile(p) or not v.get("sha256"):
            continue
        try:
            if DV.sha256_cached(p) != v["sha256"]:
                out.append((d, v))
        except OSError:
            continue
    return out


def replace(ws, lib, doc_id, new_path=None, reader=None, M=None):
    """Read the new (or edited) file as the same version. Returns {"doc", "version", "trash", "file"} or None."""
    import docintake as DI
    d = lib.doc(doc_id)
    v = lib.latest(d) if d else None
    cur = lib.path_of(v) if v else ""
    if v is None or not cur:
        return None
    old = copy.deepcopy(v)
    text_json = os.path.join(lib.folder, v["id"] + ".json")
    keep = []
    if new_path and os.path.normcase(os.path.abspath(new_path)) != os.path.normcase(os.path.abspath(cur)):
        if os.path.isfile(cur):
            keep.append(cur)                              # the file being replaced, as it was
    tmp_text = text_json + ".was"
    if os.path.isfile(text_json):
        shutil.copy2(text_json, tmp_text)
        keep.append(tmp_text)
    snap = [copy.deepcopy(it) for it in (M.items if M is not None else []) if it.get("file") == v.get("file")]
    eid = T.put(ws, "replaced", f"{d['name']}: {v.get('label', '')} before it was replaced",
                {"doc_id": d["id"], "version": old, "items": snap, "file": v.get("file", "")}, files=keep)
    if new_path and keep and keep[0] == cur:
        shutil.copy2(new_path, cur)
    sents = (reader or DI.read)(cur)
    v.update({"sha256": DV.sha256(cur), "sentences": len(sents), "reviewed": ""})
    tp = DV.text_print(sents)
    if tp:
        v["text_sha"] = tp
    v.pop("change", None)
    v.setdefault("replaced", []).append({"when": datetime.datetime.now().isoformat(timespec="minutes"),
                                         "who": getpass.getuser(), "was": old.get("sha256", ""), "trash": eid,
                                         "from": os.path.basename(new_path) if new_path else "edited in place"})
    lib._write_text(v["id"], sents)
    i = d["versions"].index(v)
    if i + 1 < len(d["versions"]):
        d["versions"][i + 1].pop("change", None)
    v["reread"] = True                                    # the shred reads it again (skqt.docmanage.reread, on the timer)
    lib.save()
    return {"doc": d, "version": v, "trash": eid, "file": v.get("file", "")}


def _norm(t):
    return " ".join((t or "").split())


def merge(M, f, items, heads, src, ws=None, trash_name=""):
    """The fresh extract of file f into the shred M. Returns {"kept", "changed", "added", "gone", "rows"}."""
    import compliance as C
    olds = [it for it in M.items if it.get("file") == f and it.get("header") != "Yes"]
    news = [it for it in items if it.get("file") == f and it.get("header") != "Yes"]
    rows = DV.compare([{"x": _norm(it.get("text"))} for it in olds], [{"x": _norm(it.get("text"))} for it in news])
    kept = changed = 0
    add, gone = [], []
    where = ("file", "key", "page", "loc", "section", "section_title", "box", "boxes", "lead")
    for r in rows:
        if r["kind"] in ("same", "changed"):
            o, n = olds[r["oi"]], news[r["nj"]]
            for k in where:
                if k in n:
                    o[k] = n[k]
            if r["kind"] == "changed":
                o["text"] = n.get("text", o.get("text"))
                o["new"] = MARK
                M.log(o.get("id", ""), MARK.lower())
                changed += 1
            else:
                kept += 1
        elif r["kind"] == "added":
            add.append(dict(news[r["nj"]], id="", new=f"New when {f} was replaced"))
        else:
            gone.append(olds[r["oi"]])
    old_heads = [it for it in M.items if it.get("file") == f and it.get("header") == "Yes"]
    add += [dict(it, id="") for it in items if it.get("file") == f and it.get("header") == "Yes"]
    if gone and ws is not None:
        T.put(ws, "pieces", trash_name or f"{f}: pieces whose sentences are gone", {"file": f, "items": copy.deepcopy(gone)})
    drop = {id(x) for x in gone + old_heads}
    M.items = [it for it in M.items if id(it) not in drop] + add
    C.assign_ids(M.items)
    C.link_items(M.items)
    M.headings = [h for h in getattr(M, "headings", []) if h.get("file") != f] + list(heads or [])
    M.sources = [r for r in M.sources if not (r and r[0] == f)] + list(src or [])
    M.log("matrix", f"{f} replaced: {kept} kept, {changed} changed (decisions kept), {sum(1 for it in add if it.get('header') != 'Yes')} new, "
                    f"{len(gone)} to the Trash")
    M.pending = True
    return {"kept": kept, "changed": changed, "added": sum(1 for it in add if it.get("header") != "Yes"), "gone": len(gone),
            "rows": add}


def restore(ws, lib, M, eid):
    """Put the file back as it was before it was replaced: the old file, its text and its pieces. Returns the entry. A file
    edited where it sat has no old bytes to put back: its record, text and pieces come back, the file stays as it is."""
    e = T.entry(ws, eid)
    if e is None or e["kind"] != "replaced":
        return None
    p = e["payload"]
    d = lib.doc(p["doc_id"])
    v = next((x for x in (d or {}).get("versions", []) if x["id"] == p["version"]["id"]), None)
    if v is None:
        return None
    cur = lib.path_of(v)
    has_old = any(rec.get("kept") and not rec["orig"].endswith(".json.was") for rec in e["files"])
    if has_old and cur and os.path.isfile(cur):        # the replacing file goes to the Trash in its turn
        T.put(ws, "replaced", f"{d['name']}: {v.get('label', '')} as it was replaced",
              {"doc_id": d["id"], "version": copy.deepcopy(v), "file": v.get("file", ""),
               "items": [copy.deepcopy(it) for it in (M.items if M is not None else []) if it.get("file") == v.get("file")]},
              files=[cur])
    e = T.take_back(ws, eid)
    for orig, now in (e.get("back") or {}).items():
        if orig.endswith(".json.was"):
            os.replace(now, orig[:-4])
        elif now != orig and not os.path.exists(orig):
            os.replace(now, orig)
    v.clear(); v.update(p["version"])
    lib.save()
    if M is not None:
        M.items = [it for it in M.items if it.get("file") != p.get("file")] + p.get("items", [])
        import compliance as C
        C.assign_ids(M.items)
        M.pending = True
    return e
