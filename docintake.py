"""Customer documents in, outside any window (2.65.0): read a file sentence by sentence, suggest which document it is a
version of (the name and the text), and add it to the effort's library (copied into the customer documents folder).
Both programs use it; the classic window's Documents step calls the same functions. Also: which compliance matrix
sentences each changed sentence of a compare touches (Compare linked to the matrix). Rules only (No AI); nothing leaves
the PC.
"""
import datetime, os, re, shutil
import diag
import docversions as DV
import sensitivity as S

Spill = S.Spill                      # 2.97.0: a document marked above CUI: everything stops, nothing is copied


def read(path):
    """The text of a file, sentence by sentence (typed text, and scanned pages and pictures through the reader).
    2.96.0: an old .doc, .xls or .ppt file is read from its PDF copy (Microsoft Office makes it)."""
    try:
        import app_gui
        import ocrpdf
        src = path
        if ocrpdf.is_legacy(path):
            import tempfile
            import office_pdf as OP
            src = OP.make(path, tempfile.mkdtemp(prefix="sk_legacy_"))
        try:
            chunks = app_gui.rfp_chunks(src)
        finally:
            if src != path:                              # 2.97.0: the PDF copy of an old Office file is not kept
                shutil.rmtree(os.path.dirname(src), ignore_errors=True)
    except Exception:
        diag.swallowed()
        chunks = []
    return DV.snapshot(os.path.basename(path), chunks)


class Stopped(Exception):
    """2.83.0: the person pressed Stop while files were being read; nothing was added."""


FILE_TYPES = (".docx", ".pdf", ".pptx", ".xlsx", ".txt", ".doc", ".xls", ".ppt",            # 2.96.0: old Office files
              ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")                  # and pictures


def _not_documents():
    import watch
    return watch.NOT_DOCUMENTS


def walk(folder):
    """2.83.0: every document file in a dropped folder, with the folder path it sits in (relative to the folder, with the
    dropped folder's own name first): [(path, relative folder)]."""
    out = []
    root = os.path.abspath(folder)
    top = os.path.basename(root.rstrip("\\/"))
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if not d.startswith((".", "~", "_")))
        for f in sorted(fns):
            if f.startswith("~$") or f.lower().endswith(_not_documents()):      # 4.25.2: any kind of file is a document
                continue                                                         # to keep (a kind the reader does not open has no text)
            rel = os.path.relpath(dp, root)
            out.append((os.path.join(dp, f), top if rel == "." else top + "/" + rel.replace(os.sep, "/")))
    return out


def plan(lib, paths, reader=read, progress=None, stop=None, folders=None, category=None, edited="version"):
    """For each new file: its text and the suggested match. Files are taken in the order given, so a later file can be
    matched to an earlier one in the same batch. Returns [entry]: {path, sha, dup, sents, cands, best, choice
    ('new', 'version' or 'skip'), doc, name, label}.
    2.83.0: and its category, folder, tags and role (suggested from the folders it came from and its type).
    folders: {path: relative folder}; category: the category every file goes to (else guessed, customer when unsure);
    progress(fraction, text) per file; stop() True raises Stopped.
    2.97.0: a file marked above CUI raises Spill (sensitivity.guard) before anything is read on or copied; each entry
    keeps the level found ("sensitivity", -1 when none).
    4.17.0: a file read before from this very place, changed since: edited "replace" (Documents' Add files: the person
    edited it) offers it first as the same document with its file replaced; "version" (the watch: the customer's newer
    file saved over the old) as its next version. Both are in the add table's choices."""
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
        level = S.guard(p)                               # 2.97.0: marked above CUI: stop before reading or copying
        sents = reader(p)
        level = S.guard_lines(os.path.basename(p), [x["x"] for x in sents], level)
        tp = DV.text_print(sents)                       # 3.15.1: the same words as a document here: not added twice
        same = lib.find_text(tp)
        twin = None if same else next((e for e in out if tp and e.get("text_print") == tp), None)
        if same or twin:
            d0 = same[0] if same else {"id": "", "name": twin["name"]}
            out.append({"path": p, "sha": h, "dup": same or (d0, None), "dup_how": "same text", "text_print": tp,
                        "sents": sents, "choice": "skip", "cands": [], "best": None, "doc": d0["id"] or None,
                        "name": DV.display_name(p), "label": "", "category": d0.get("category", cat), "folder": rel,
                        "tags": DV.folder_tags(rel), "role": lib.role_of(d0) if same else DV.suggest_role(cat, ""),
                        "sensitivity": level})
            continue
        cands = [(d, sc, how) for d, sc, how in lib.suggest(os.path.basename(p), [s["x"] for s in sents])]
        came = lib.find_source(p)                       # 3.15.1: a file added before from this very place: a new version
        if came and not any(c[0]["id"] == came[0]["id"] for c in cands):
            cands.append((came[0], 1.0, "added before from this file"))
        elif came:
            cands = [(d, 1.0, how + "; added before from this file") if d["id"] == came[0]["id"] else (d, sc, how)
                     for d, sc, how in cands]
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
        same_file = None                                # 4.17.0: the very file a document was read from, edited where it
        if came:                                        # sits: the same document and version, its file replaced
            last = lib.latest(came[0])
            if last is not None and DV.same_path(lib.path_of(last), p):
                same_file = came[0]["id"]
        dtype = DV.guess_type(os.path.basename(p))                  # 2.68.0: the person confirms the type and initial
        taken = [e.get("initial", "") for e in out]
        out.append({"path": p, "sha": h, "sents": sents, "cands": cands, "best": best, "text_print": tp,
                    "choice": "replace" if same_file and edited == "replace" else "version" if (best and DV.Library.band(best[1]) == "strong") or same_file else "new",
                    "doc": same_file or (best[0]["id"] if best else None), "replace_of": came[0]["id"] if came else None, "name": DV.display_name(p), "label": "",
                    "type": dtype, "initial": lib.suggest_initial(dtype, taken) if cat == "customer" else "",
                    "category": cat, "folder": rel, "tags": DV.folder_tags(rel), "role": DV.suggest_role(cat, dtype),
                    "suggested_role": DV.suggest_role(cat, dtype), "sensitivity": level,
                    "under": (lib.base_for_orders() or {}).get("id", "") if dtype in DV.ORDER_TYPES else ""})
    if progress is not None:
        progress(1.0, "Read")
    return out


def check(lib, entries):
    """2.68.0: what is wrong with a plan before it is added: every new document needs an initial and a type, and no two
    documents share an initial. [] when it can be added."""
    out, seen = [], {x.casefold() for x in lib.initials()}       # 4.24.0: Amd1 and AMD1 are the same initial
    for e in entries:
        if e.get("dup") or e["choice"] != "new":
            continue
        if e.get("category", "customer") != "customer":     # 2.83.0: only customer documents need an initial and type
            continue
        ini = DV.clean_initial(e.get("initial", ""))
        name = os.path.basename(e["path"])
        if not ini:
            out.append(f"{name}: give it an initial.")
        elif ini.casefold() in seen:
            out.append(f"{name}: the initial {ini} is already used.")
        if e.get("type") not in DV.DOC_TYPES:
            out.append(f"{name}: pick its type.")
        seen.add(ini.casefold())
    return out


def in_effort(lib, path):
    """4.25.1: the file sits in the effort's own folder (and not in the app's data): it is not copied anywhere."""
    er = getattr(lib, "effort_root", "") or ""
    if not er:
        return False
    p = os.path.normcase(os.path.abspath(path))
    data = os.path.normcase(os.path.abspath(lib.data_dir))
    return p.startswith(os.path.normcase(os.path.abspath(er)) + os.sep) and not p.startswith(data + os.sep)


def library_dir(lib, category, folder=""):
    """2.83.0: where a document that is not a customer document is copied: <effort data>\\library\\<category>\\<folder>;
    3.78.0: <effort>\\Library\\<top folder>\\<folder> once the library knows its effort (effortlib.attach)."""
    import effortlib as EL                              # 3.78.0: the Effort Library's real folders, when it knows them
    p = EL.folder_path(lib, category, folder)
    if p:
        return p
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
        if e["choice"] == "replace" and e.get("doc"):     # 4.17.0: the same version, its file replaced; the shred reads it again
            import docreplace as RP
            res = RP.replace(lib.data_dir, lib, e["doc"], new_path=src, reader=lambda _p, s=e["sents"]: s)
            if res is not None:
                made.append((res["doc"], res["version"]))
                if log is not None:
                    log("customer", f"{res['doc']['name']}: {res['version'].get('label', '')} replaced ({os.path.basename(src)}); "
                        "the old file is in the Trash", {"version": res["version"]["id"]})
            continue
        cat = e.get("category", "customer")
        if e["choice"] == "version" and e.get("doc") and not str(e["doc"]).startswith("batch:"):
            cat = (lib.doc(e["doc"]) or {}).get("category", cat)           # a new version goes where its document is
        if cat != "customer" and getattr(lib, "library_root", ""):     # 3.78.0: the folder as it is on disk
            import effortlib as EL
            tags0 = DV.folder_tags(e.get("folder", ""))
            e = dict(e, folder=EL.clean_folder(lib, cat, e.get("folder", "")), tags=list(dict.fromkeys(list(e.get("tags", [])) + tags0)))
        cd = customer_dir if cat == "customer" else library_dir(lib, cat, e.get("folder", ""))
        if cat != "customer" and not in_effort(lib, src):
            os.makedirs(cd, exist_ok=True)
        inside = cd and os.path.normcase(os.path.abspath(src)).startswith(os.path.normcase(os.path.abspath(cd)) + os.sep)
        inside = inside or in_effort(lib, src)             # 4.25.1: a file already in the effort's folder stays where it sits
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
                       save=False, role_confirmed=DV.use_key(e.get("role")) != DV.use_key(e.get("suggested_role", e.get("role"))), source=src)
        if e.get("under") and not d.get("under") and e["choice"] == "new":   # an order, under its contract or RFP
            lib.set_under(d["id"], e["under"], save=False)
        if e.get("sensitivity", -1) > d.get("sensitivity", -1):     # 2.97.0: the highest level found in its versions
            d["sensitivity"] = e["sensitivity"]
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
                    f"{d['name']} added ({v['file']}, {v.get('sentences', 0)} pieces)", {"version": v["id"]})
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
                hits.append(entry(it, "the same piece"))
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
