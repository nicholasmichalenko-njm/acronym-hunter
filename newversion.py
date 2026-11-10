"""A new version of a document already in the shred (4.2.0; claude/stationkeeper-fix-text-decisions-2026-11-10.md,
decisions 3, 9 and 10). It is extracted at once, and its pieces never appear twice:
- a sentence that stays the same keeps its piece and every decision on it; the piece moves onto the new version's page
  (Shred shows the latest version's pages);
- a new sentence arrives as a new piece, not sorted yet, marked "New in <document> <version>";
- a changed or removed sentence leaves its piece where it was until Documents > Changes decides it (No impact, Re-shred,
  Ask, or Update our wording).
The pairing is docversions.compare, the same rules Changes uses. Rules only (No AI); nothing leaves the PC."""
import os

import docversions as DV


def _norm(t):
    return " ".join((t or "").split())


def merge(M, old_file, new_file, items, heads, src, label=""):
    """Bring the new version's extracted items into the matrix M. Returns {"kept", "added", "waiting"}."""
    import compliance as C
    olds = [it for it in M.items if it.get("file") == old_file and it.get("header") != "Yes"]
    news = [it for it in items if it.get("file") == new_file and it.get("header") != "Yes"]
    rows = DV.compare([{"x": _norm(it.get("text"))} for it in olds], [{"x": _norm(it.get("text"))} for it in news])
    kept = added = waiting = 0
    add = []
    import setupdoc as SD
    St = SD.setup_of(M)                                   # what the text check leaves alone (compliance_read.complete)
    sup = St.setdefault("superseded", [])
    if old_file not in sup:
        sup.append(old_file)
    wait = St.setdefault("for_changes", {}).setdefault(new_file, [])
    for r in rows:
        if r["kind"] == "same":
            o, n = olds[r["oi"]], news[r["nj"]]
            for k in ("file", "key", "page", "loc", "section", "section_title"):
                if k in n:
                    o[k] = n[k]
            kept += 1
        elif r["kind"] == "added":
            n = dict(news[r["nj"]], id="")
            n["new"] = f"New in {label or new_file}"
            add.append(n)
            added += 1
        else:
            waiting += 1                                  # changed or removed: Changes decides
            if r.get("new"):
                wait.append(_norm(r["new"]).lower())
    for it in items:                                      # the new version's own headings and set-aside lines
        if it.get("file") == new_file and it.get("header") == "Yes":
            add.append(dict(it, id=""))
    M.items += add
    C.assign_ids(M.items)
    C.link_items(M.items)
    M.headings += heads
    M.sources += src
    M.log("matrix", f"new version {label or new_file}: {kept} kept, {added} new, {waiting} for Changes")
    M.pending = True
    return {"kept": kept, "added": added, "waiting": waiting, "rows": add}


def extract(host, doc_id):
    """Extract the latest version of a document whose earlier version is in the matrix, in the background. Returns the
    worker or None."""
    rp = host.read_page
    if rp.running() or host.review is None:
        return None
    lib = DV.Library(host.ws.p("documents")).load()
    d = lib.doc(doc_id)
    if d is None or len(d.get("versions") or []) < 2:
        return None
    have = set(host.review.files())
    old = next((v for v in reversed(d["versions"][:-1]) if v.get("file") in have), None)
    vn = d["versions"][-1]
    path = lib.path_of(vn)
    if old is None or not path or not os.path.isfile(path):
        return None
    label = f"{d['name']} {vn.get('label', '')}".strip()
    rp.refresh()
    rp._merge = lambda items, heads, src: merge(host.review.M, old["file"], vn.get("file") or os.path.basename(path),
                                                items, heads, src, label)["rows"]
    w = rp.read(paths=[path], identities="suggested", start="auto")
    if w is None:
        rp._merge = None
        return None
    host.status(f"Extracting {label}: the same sentences keep their pieces; changes wait in Documents > Changes.")
    return w
