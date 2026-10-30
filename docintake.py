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


class Stopped(Exception):
    """2.83.0: the person pressed Stop while files were being read; nothing was added."""


FILE_TYPES = (".docx", ".pdf", ".pptx", ".xlsx", ".txt")


def walk(folder):
    """2.83.0: every document file in a dropped folder, with the folder path it sits in (relative to the folder, with the
    dropped folder's own name first): [(path, relative folder)]."""
    out = []
    root = os.path.abspath(folder)
    top = os.path.basename(root.rstrip("\\/"))
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if not d.startswith((".", "~", "_")))
        for f in sorted(fns):
            if f.startswith("~$") or not f.lower().endswith(FILE_TYPES):
                continue
            rel = os.path.relpath(dp, root)
            out.append((os.path.join(dp, f), top if rel == "." else top + "/" + rel.replace(os.sep, "/")))
    return out


def plan(lib, paths, reader=read, progress=None, stop=None, folders=None, category=None):
    """For each new file: its text and the suggested match. Files are taken in the order given, so a later file can be
    matched to an earlier one in the same batch. Returns [entry]: {path, sha, dup, sents, cands, best, choice
    ('new', 'version' or 'skip'), doc, name, label}.
    2.83.0: and its category, folder, tags and role (suggested from the folders it came from and its type).
    folders: {path: relative folder}; category: the category every file goes to (else guessed, customer when unsure);
    progress(fraction, text) per file; stop() True raises Stopped."""
    out = []
    folders = folders or {}
    n = max(1, len(paths))
    for k, p in enumerate(paths):
        if stop is not None and stop():
            raise Stopped()
        if progress is not None:
            progress(k / n, f"File {k + 1} of {len(paths)}: {os.path.basename(p)}")
        try:
            h = DV.sha256(p)
        except OSError:
            continue
        rel = folders.get(p, "")
        cat = category or DV.guess_category(rel + "/" + os.path.basename(p), "customer")
        got = lib.find_sha(h)
        if got:
            out.append({"path": p, "sha": h, "dup": got, "sents": [], "choice": "skip", "cands": [], "best": None, "doc": None,
                        "name": DV.display_name(p), "label": "", "category": got[0].get("category", "customer"),
                        "folder": rel, "tags": DV.folder_tags(rel), "role": lib.role_of(got[0])})
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
        dtype = DV.guess_type(os.path.basename(p))                  # 2.68.0: the person confirms the type and initial
        taken = [e.get("initial", "") for e in out]
        out.append({"path": p, "sha": h, "sents": sents, "cands": cands, "best": best,
                    "choice": "version" if best and DV.Library.band(best[1]) == "strong" else "new",
                    "doc": best[0]["id"] if best else None, "name": DV.display_name(p), "label": "",
                    "type": dtype, "initial": lib.suggest_initial(dtype, taken) if cat == "customer" else "",
                    "category": cat, "folder": rel, "tags": DV.folder_tags(rel), "role": DV.suggest_role(cat, dtype),
                    "suggested_role": DV.suggest_role(cat, dtype)})
    if progress is not None:
        progress(1.0, "Read")
    return out


def check(lib, entries):
    """2.68.0: what is wrong with a plan before it is added: every new document needs an initial and a type, and no two
    documents share an initial. [] when it can be added."""
    out, seen = [], set(lib.initials())
    for e in entries:
        if e.get("dup") or e["choice"] != "new":
            continue
        if e.get("category", "customer") != "customer":     # 2.83.0: only customer documents need an initial and type
            continue
        ini = DV.clean_initial(e.get("initial", ""))
        name = os.path.basename(e["path"])
        if not ini:
            out.append(f"{name}: give it an initial.")
        elif ini in seen:
            out.append(f"{name}: the initial {ini} is already used.")
        if e.get("type") not in DV.DOC_TYPES:
            out.append(f"{name}: pick its type.")
        seen.add(ini)
    return out


def library_dir(lib, category, folder=""):
    """2.83.0: where a document that is not a customer document is copied: <effort data>\\library\\<category>\\<folder>."""
    parts = [re.sub(r'[<>:"|?*]', "_", x).strip() or "_" for x in (folder or "").replace("\\", "/").split("/") if x.strip() and x not in (".", "..")]
    return os.path.join(lib.data_dir, "library", category, *parts)


def apply(lib, entries, customer_dir="", log=None, progress=None):
    """Add the planned files: copy each into the customer documents folder (2.83.0: other categories into the effort's
    library folder), then record it. log(kind, text, ref): the effort's timeline. Returns [(doc, version)]."""
    made, batch_doc = [], {}
    todo = [e for e in entries if not (e.get("dup") or e["choice"] == "skip")]
    for k, e in enumerate(entries):
        if e.get("dup") or e["choice"] == "skip":
            continue
        if progress is not None:
            progress(len(made) / max(1, len(todo)), f"Adding {len(made) + 1} of {len(todo)}: {os.path.basename(e['path'])}")
        src = dest = e["path"]
        cat = e.get("category", "customer")
        if e["choice"] == "version" and e.get("doc") and not str(e["doc"]).startswith("batch:"):
            cat = (lib.doc(e["doc"]) or {}).get("category", cat)           # a new version goes where its document is
        cd = customer_dir if cat == "customer" else library_dir(lib, cat, e.get("folder", ""))
        if cat != "customer":
            os.makedirs(cd, exist_ok=True)
        inside = cd and os.path.normcase(os.path.abspath(src)).startswith(os.path.normcase(os.path.abspath(cd)) + os.sep)
        if cd and os.path.isdir(cd) and not inside:        # 2.94.0: a file already in the folder (or a subfolder) stays put
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
        d, v = lib.add(dest, e["sents"], doc_id=doc_id, doc_name=e.get("name", ""), label=e.get("label", ""), sha=e["sha"],
                       initial=e.get("initial", ""), dtype=e.get("type", ""), category=cat, folder=e.get("folder", ""),
                       tags=[t for t in e.get("tags", []) if t not in DV.folder_tags(e.get("folder", ""))], role=e.get("role"),
                       save=False, role_confirmed=e.get("role") != e.get("suggested_role", e.get("role")))
        batch_doc[k] = d["id"]
        made.append((d, v))
    if made:
        lib.save()                                       # 2.83.0: once for the batch, not once per file
        diag.activity("submission_added", n=len(made))
        other = {}
        for d, v in made:                                # the paper trail
            if d.get("category", "customer") != "customer":            # 2.83.0: the library in one line per batch
                other[d["category"]] = other.get(d["category"], 0) + 1
                continue
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
        if other and log is not None:
            log("library", "Library: " + ", ".join(f"{n} to {lib.category_name(c)}" for c, n in other.items()) + " added")
    if progress is not None:
        progress(1.0, "Added")
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
