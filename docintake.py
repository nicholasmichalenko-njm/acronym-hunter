"""Customer documents in, outside any window (2.65.0): read a file sentence by sentence, suggest which document it is a
version of (the name and the text), and add it to the effort's library (copied into the customer documents folder).
Both programs use it; the classic window's Documents step calls the same functions. Also: which compliance matrix
sentences each changed sentence of a compare touches (Compare linked to the matrix). Rules only (No AI); nothing leaves
the PC.
"""
import datetime, os, re, shutil
import diag
import docversions as DV


def read(path):
    """The text of a file, sentence by sentence (typed text, and scanned pages through the reader)."""
    try:
        import app_gui
        chunks = app_gui.rfp_chunks(path)
    except Exception:
        diag.swallowed()
        chunks = []
    return DV.snapshot(os.path.basename(path), chunks)


def plan(lib, paths, reader=read):
    """For each new file: its text and the suggested match. Files are taken in the order given, so a later file can be
    matched to an earlier one in the same batch. Returns [entry]: {path, sha, dup, sents, cands, best, choice
    ('new', 'version' or 'skip'), doc, name, label}."""
    out = []
    for p in paths:
        try:
            h = DV.sha256(p)
        except OSError:
            continue
        got = lib.find_sha(h)
        if got:
            out.append({"path": p, "sha": h, "dup": got, "sents": [], "choice": "skip", "cands": [], "best": None, "doc": None,
                        "name": DV.display_name(p), "label": ""})
            continue
        sents = reader(p)
        cands = [(d, sc, how) for d, sc, how in lib.suggest(os.path.basename(p), [s["x"] for s in sents])]
        for k, e in enumerate(out):              # earlier files in this batch that will become new documents
            if e.get("dup") or e["choice"] != "new":
                continue
            ns = DV.name_similarity(os.path.basename(p), os.path.basename(e["path"]))
            ts = DV.text_similarity([s["x"] for s in sents], [s["x"] for s in e["sents"]])
            sc = round(max(ts, 0.5 * ns + 0.5 * ts), 3)
            cands.append(({"id": f"batch:{k}", "name": e["name"], "versions": []}, sc,
                          f"{int(round(ts * 100))}% of the text is the same" + ("; the name matches" if ns >= 0.9 else "")))
        cands.sort(key=lambda x: -x[1])
        best = cands[0] if cands and DV.Library.band(cands[0][1]) else None
        out.append({"path": p, "sha": h, "sents": sents, "cands": cands, "best": best,
                    "choice": "version" if best and DV.Library.band(best[1]) == "strong" else "new",
                    "doc": best[0]["id"] if best else None, "name": DV.display_name(p), "label": ""})
    return out


def apply(lib, entries, customer_dir="", log=None):
    """Add the planned files: copy each into the customer documents folder, then record it. log(kind, text, ref): the
    effort's timeline. Returns [(doc, version)]."""
    made, batch_doc = [], {}
    for k, e in enumerate(entries):
        if e.get("dup") or e["choice"] == "skip":
            continue
        src = dest = e["path"]
        cd = customer_dir
        if cd and os.path.isdir(cd) and os.path.normcase(os.path.dirname(os.path.abspath(src))) != os.path.normcase(os.path.abspath(cd)):
            dest = os.path.join(cd, os.path.basename(src))
            if os.path.exists(dest) and DV.sha256(dest) != e["sha"]:
                base, ext = os.path.splitext(dest)
                dest = f"{base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}{ext}"
            try:
                if not os.path.exists(dest):
                    shutil.copy2(src, dest)
            except OSError:
                diag.swallowed(); dest = src
        doc_id = e.get("doc") if e["choice"] == "version" else None
        if doc_id and str(doc_id).startswith("batch:"):
            doc_id = batch_doc.get(int(doc_id.split(":")[1]))
        d, v = lib.add(dest, e["sents"], doc_id=doc_id, doc_name=e.get("name", ""), label=e.get("label", ""), sha=e["sha"])
        batch_doc[k] = d["id"]
        made.append((d, v))
    if made:
        diag.activity("submission_added", n=len(made))
        for d, v in made:                                # the paper trail
            i = d["versions"].index(v)
            what = ""
            if i:
                try:
                    what = "; " + DV.summary_text(DV.summary(DV.compare(lib.text(d["versions"][i - 1]), lib.text(v))))
                except Exception:
                    diag.swallowed()
            if log is not None:
                log("customer", f"{d['name']}: {v['label']} added ({v['file']}){what}" if i else
                    f"{d['name']} added ({v['file']}, {v.get('sentences', 0)} sentences)", {"version": v["id"]})
    return made


# ------------------------------------------------------------------ Compare linked to the matrix (2.65.0)
def _words(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def link(M, rows, owner_of=None, files=()):
    """For each compare row, the matrix sentences it touches: [[{id, decision, map, owner, how}]], aligned with rows. The
    same sentence (as the matrix keeps it); else, for a changed sentence, the matrix sentence with most of the same
    words (at least 60 percent), preferring the files compared."""
    import compliance as C
    import impact as IM
    if M is None or not M.items:
        return [[] for _ in rows]
    idx = IM._item_index(M.items)
    owner_of = owner_of or (lambda it: it.get("owner", ""))
    pool = [it for it in M.items if not files or it.get("file") in files] or M.items
    wpool = [(it, _words(it.get("text", ""))) for it in pool]

    def entry(it, how):
        return {"id": it["id"], "decision": it.get("decision", ""), "map": it.get("map", ""), "owner": owner_of(it), "how": how}
    out = []
    for r in rows:
        if r["kind"] == "same":
            out.append([])
            continue
        hits = []
        for txt in (r.get("old"), r.get("new")):
            it = idx.get(C.text_key(txt)) if txt else None
            if it is not None and it["id"] not in [h["id"] for h in hits]:
                hits.append(entry(it, "the same sentence"))
        if not hits and r["kind"] == "changed":
            w = _words(r.get("old")) | _words(r.get("new"))
            best, score = None, 0.0
            for it, iw in wpool:
                if not iw or not w:
                    continue
                sc = len(w & iw) / min(len(w), len(iw))
                if sc > score:
                    best, score = it, sc
            if best is not None and score >= 0.6:
                hits.append(entry(best, f"{int(round(score * 100))}% of the words"))
        out.append(hits)
    return out
