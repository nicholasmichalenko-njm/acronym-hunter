"""Unfiled work (2.91.0): a workspace that is always there, so any tool can be used before an effort exists.

Unfiled is an ordinary effort kept in Stationkeeper Data\\Efforts\\Unfiled (the registry marks it unfiled): the Library,
Read RFP, Customer terms, Submission check and every other page work in it as in any effort. Its work is filed one of
two ways:
- Make it an effort: Unfiled becomes a named effort with its own folder (by an effort package, so every path follows),
  and Unfiled starts empty again. A copy of the old Unfiled folder is kept in the new effort's backups.
- Add to an effort: chosen documents join another effort's Library (with their category, folder, tags, role, initial,
  type and every version), customer documents copied into that effort's Customer Documents folder, others into its
  library folder; and Unfiled's acronyms join that effort's effort list without replacing any it has.
Nothing is filed by itself; the window reminds while Unfiled holds work. Standard library plus the effort modules.
"""
import os, shutil

NAME = "Unfiled"


def list_path(data_dir):
    import datahome
    return os.path.join(datahome.efforts_dir(data_dir), NAME, f"{NAME}_Effort_List.xlsx")


def is_unfiled(registry, name):
    return bool(name) and bool((registry.get(name) or {}).get("unfiled"))


def ensure(registry, data_dir):
    """Unfiled's list (made when missing) registered as unfiled. Returns its name."""
    import effort as E
    import effortfolders as EF
    info = registry.get(NAME) or {}
    path = info.get("path") if info.get("unfiled") and info.get("path") else list_path(data_dir)
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        L = E.EffortList(path, NAME)
        L.pending = True
        L.save()
    EF.create_all(path)
    if not info.get("unfiled") or info.get("path") != path:
        registry.put(NAME, path=path, unfiled=True, customer_dir=EF.folder(path, "customer"), volumes_dir=EF.folder(path, "volumes"))
    return NAME


def counts(registry):
    """{documents, matrix, terms, context, notes}: what Unfiled holds (zeros when it is empty or missing)."""
    out = {"documents": 0, "matrix": 0, "terms": 0, "context": 0, "notes": 0}
    info = registry.get(NAME) or {}
    path = info.get("path", "")
    if not info.get("unfiled") or not os.path.isfile(path):
        return out
    import workspace as W
    data = W.data_dir_for(path)
    try:
        import docversions as DV
        out["documents"] = len(DV.Library(os.path.join(data, "documents")).load().all)
    except Exception:
        pass
    st = W.read_json(os.path.join(data, "settings.json"), None) or {}
    out["matrix"] = int(bool(st.get("compliance_path")) and os.path.isfile(st.get("compliance_path", "")))
    try:
        import effort as E
        out["terms"] = len(E.EffortList(path, NAME).load().rows)
    except Exception:
        pass
    ctx = W.read_json(os.path.join(data, "context", "attach.json"), None) or {}
    out["context"] = len(ctx.get("att", []) if isinstance(ctx, dict) else [])
    rec = W.read_json(os.path.join(data, "record.json"), None) or {}
    out["notes"] = len(rec.get("notes", [])) + len(rec.get("tasks", []))
    return out


def empty(c):
    return not any(c.values())


def summary_text(c):
    parts = []
    for k, one, many in (("documents", "document", "documents"), ("matrix", "compliance matrix", "compliance matrices"),
                         ("terms", "term", "terms"), ("context", "piece of context", "pieces of context"),
                         ("notes", "note or task", "notes and tasks")):
        if c.get(k):
            parts.append(f"{c[k]} {one if c[k] == 1 else many}")
    return ", ".join(parts) if parts else "nothing yet"


def documents(registry):
    """[(doc id, name, category, versions)] in Unfiled's Library."""
    info = registry.get(NAME) or {}
    if not info.get("path"):
        return []
    import docversions as DV
    import workspace as W
    lib = DV.Library(os.path.join(W.data_dir_for(info["path"]), "documents")).load()
    return [(d["id"], d["name"], d.get("category", "customer"), len(d["versions"])) for d in lib.all]


def add_to(registry, target, doc_ids, terms=True, who=None):
    """Add Unfiled's chosen documents (every version) and its acronyms to the effort named target. Returns
    {"documents", "versions", "terms"} added. Unfiled keeps its copies until it is cleared."""
    import docintake as DI
    import docversions as DV
    import effort as E
    import effortfolders as EF
    import effortrec as R
    import workspace as W
    src_info, dst_info = registry.get(NAME) or {}, registry.get(target) or {}
    sdata, ddata = W.data_dir_for(src_info["path"]), W.data_dir_for(dst_info["path"])
    src = DV.Library(os.path.join(sdata, "documents")).load()
    dst = DV.Library(os.path.join(ddata, "documents")).load()
    cust_dir = dst_info.get("customer_dir") or EF.folder(dst_info["path"], "customer")
    n = {"documents": 0, "versions": 0, "terms": 0}
    for d in [d for d in src.all if d["id"] in set(doc_ids)]:
        made = None
        for v in d["versions"]:
            p = src.path_of(v)
            if not p or not os.path.isfile(p):
                continue
            cat = d.get("category", "customer")
            folder = cust_dir if cat == "customer" else DI.library_dir(dst, cat, d.get("folder", ""))
            os.makedirs(folder, exist_ok=True)
            target_path = os.path.join(folder, v.get("file") or os.path.basename(p))
            if os.path.exists(target_path) and DV.sha256(target_path) != v.get("sha256"):
                stem, ext = os.path.splitext(target_path)
                target_path = f"{stem} ({v.get('label', 'v')}){ext}"
            if not os.path.exists(target_path):
                shutil.copy2(p, target_path)
            have = next((x for x in dst.all for y in x["versions"] if y.get("sha256") == v.get("sha256")), None)
            if have is not None:
                made = made or have
                continue
            doc, _ver = dst.add(target_path, src.text(v), doc_id=made["id"] if made else None, doc_name=d["name"], label=v.get("label", ""),
                                sha=v.get("sha256"), who=who, initial=d.get("initial", ""), dtype=d.get("type", ""), category=cat,
                                folder=d.get("folder", ""), tags=d.get("tags", []), role=d.get("role"), save=False,
                                role_confirmed=not (d.get("role_by") or {}).get("suggested"))
            if made is None:
                n["documents"] += 1
            made = doc
            n["versions"] += 1
    dst.save()
    if terms:
        S = E.EffortList(src_info["path"], NAME).load()
        T = E.EffortList(dst_info["path"], target).load()
        for t in S.order:
            if t not in T.rows:
                row = S.rows[t]
                T.add_or_update(t, change_note="added from Unfiled work", **{k: v for k, v in row.items() if k != "Term"})
                n["terms"] += 1
        if n["terms"]:
            T.pending = True
            T.save()
    if any(n.values()):
        R.Record(ddata).log("document", f"From Unfiled work: {n['documents']} document(s), {n['versions']} version(s), "
                                        f"{n['terms']} term(s)", who=who, save=True)
    return n


def clear(registry, data_dir, keep_zip=""):
    """Empty Unfiled: its folder is zipped to keep_zip first when given (never deleted without that copy), then made
    again empty. Returns True."""
    info = registry.get(NAME) or {}
    path = info.get("path") or list_path(data_dir)
    folder = os.path.dirname(path)
    if os.path.isdir(folder):
        if keep_zip:
            import effortpkg as P
            os.makedirs(os.path.dirname(keep_zip), exist_ok=True)
            P.backup_folder(folder, keep_zip)
            if not os.path.isfile(keep_zip):
                return False
        shutil.rmtree(folder)
    registry.forget(NAME)
    ensure(registry, data_dir)
    return True
