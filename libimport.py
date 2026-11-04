"""Import from a Word file, all or nothing (3.49.0).

1. stage()   reads the file into a holding area (the library's _collecting folder); the libraries do not change.
2. Each staged item lands in a library and category (libcats), says New, Same as (which item) or Differs (what
   differs), and carries a tick (take it) and what to do with it in the library: Add, Add as a new version, Keep both
   (renamed), Replace, or Skip.
3. restate() works the states out again from what the library holds right now (another window may have kept items).
4. commit()  keeps every ticked item in one transaction: if anything fails, nothing is kept, and the error goes to the
   caller with the step it was in. New items are Draft and carry the effort types chosen.
5. The report says what was added, versioned, replaced and skipped; undo() takes the import back.
6. apply_here() puts the ticked items into a copy of a standard being edited; the caller keeps the copy only when
   every item went in.

Quick Parts' pages are never measured here: that is a button (qpjobs). The file is read once and never written;
macros never run."""
import copy, datetime, json, os, uuid

import diag
import importbrowse as IB
import libcats as LC
import templatelib as TL

ACTIONS = (("add", "Add"), ("version", "Add as a new version"), ("both", "Keep both (renamed)"), ("replace", "Replace"),
           ("skip", "Do not keep in the library"))
ACTION = dict(ACTIONS)
ALLOWED = {"new": ("add", "skip"), "variant": ("version", "both", "replace", "skip"), "same": ("skip", "both")}
DEFAULT = {"new": "add", "variant": "version", "same": "skip"}


class ImportFailed(Exception):
    """Nothing was kept. step: what was being done ('keeping Heading 1'); cause: the error underneath."""
    def __init__(self, step, cause):
        super().__init__(step)
        self.step, self.cause = step, cause


def _place(lib, it):
    """Where a staged item will land, from its kind and values (no library item yet)."""
    if it["kind"] == "quickpart":
        return "quickparts", str(it["values"].get("category") or "") or LC.NO_CATEGORY
    if it["kind"] == "style":
        t = (it["values"] or {}).get("type")
        return "formatting", {"character": "char_styles", "table": "table_styles"}.get(t, "para_styles")
    return LC._KIND.get(it["kind"], (None, None))


def stage(path, std, lib, installed_fonts=None, only=None):
    """([staged item], error). Each staged item: kind, name, values, summary, library, category, state, match (id),
    match_name, differs (a line), take (ticked), action."""
    diag.activity("import_read")
    cards, err = IB.collect(path, std, lib, installed_fonts)
    items = []
    for c in cards:
        for it in c.items:
            if only is not None and it["kind"] not in only:
                continue
            it = dict(it)
            it["group"] = c.title
            it["library"], it["category"] = _place(lib, it)
            items.append(it)
    restate(lib, items, first=True)
    return items, err


def restate(lib, items, first=False):
    """Works each item's state out from what the library holds now. A tick and action chosen stay unless the state
    changed and the action no longer fits."""
    lib.fresh()
    for it in items:
        st, hit = lib.match(it["kind"], it["name"], it["values"])
        changed = st != it.get("state") or first
        it["state"], it["match"] = st, hit["id"] if hit else ""
        it["match_name"] = lib.shown_name(hit) if hit else ""
        it["differs"] = IB.differs(lib, it)[1] if st == "variant" else ""
        if changed or it.get("action") not in ALLOWED[st]:
            it["action"] = DEFAULT[st]
            it["take"] = st != "same" if first or "take" not in it else it["take"]
    return items


def _prepare(lib, it, path, kept):
    """The values to keep: a page design's file and a Quick Part's source copied into the library (in the transaction)."""
    values = copy.deepcopy(it["values"])
    if it["kind"] in ("cover", "backer", "title") and values.get("_tmp"):
        values["file"] = lib.keep_file(values.pop("_tmp"), values["file"])
    if it["kind"] == "quickpart":
        if "source" not in kept:
            kept["source"] = lib.keep_file(path, os.path.basename(path))
        values["source"] = kept["source"]
    return values


def _unique(lib, kind, name, stem):
    base = f"{name} ({stem})"
    shown, n = base, 2
    while any(i["kind"] == kind and i["name"].casefold() == shown.casefold() for i in lib.items):
        shown, n = f"{base} {n}", n + 1
    return shown


def commit(lib, path, items, effort_types=(LC.ALL,), tags=None, who=None):
    """Keeps every ticked item whose action is not Skip, all at once. Returns the report: {"id", "added": [ids],
    "versions": [ids], "replaced": [ids], "renamed": [(name, new name)], "skipped": n, "same": n, "quickparts": [ids]}.
    Raises ImportFailed (nothing kept) when anything fails."""
    rid = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    rep = {"id": rid, "file": os.path.basename(path), "at": TL._now(), "added": [], "versions": [], "replaced": [],
           "renamed": [], "skipped": 0, "same": 0, "quickparts": []}
    undo_rec = {"id": rid, "file": rep["file"], "at": rep["at"], "new": [], "old_values": {}}
    stem = os.path.splitext(os.path.basename(path))[0]
    t = dict(copy.deepcopy(tags or {}), effort_types=[LC.ALL] if LC.ALL in effort_types else sorted(set(effort_types)))
    kept = {}
    step = "starting"
    lib.fresh()
    diag.activity("import_commit", items=sum(1 for i in items if i.get("take")))
    try:
        with lib.transaction():
            for it in items:
                if not it.get("take"):
                    continue
                if it.get("action") == "skip":
                    rep["skipped"] += 1
                    continue
                step = f"keeping {it['name']}"
                values = _prepare(lib, it, path, kept)
                st, hit = lib.match(it["kind"], it["name"], values)       # what the library holds right now
                act = it["action"]
                if st == "same" and act != "both":
                    rep["same"] += 1
                    continue
                if act in ("version", "replace") and hit is None:
                    act = "add"
                if act == "add" and st == "variant":
                    act = "version"
                if act == "replace":
                    undo_rec["old_values"][hit["id"]] = lib.values(hit)
                    lib.update(hit["id"], values)
                    rep["replaced"].append(hit["id"])
                    item = hit
                elif act == "version":
                    item, _s = lib.save_version(hit["id"], values, who=who)
                    rep["versions"].append(item["id"])
                elif act == "both":
                    nm = _unique(lib, it["kind"], it["name"], stem)
                    item, _s = lib._new(it["kind"], nm, values, t, path, it.get("summary", ""), who)
                    rep["renamed"].append((it["name"], nm))
                    rep["added"].append(item["id"])
                else:
                    item, _s = lib._new(it["kind"], it["name"], values, t, path, it.get("summary", ""), who)
                    rep["added"].append(item["id"])
                if act != "replace":
                    item["status"] = "draft"
                    item.setdefault("tags", {}).update(copy.deepcopy(t))
                    item["source"] = os.path.basename(path)
                    undo_rec["new"].append(item["id"])
                if it["kind"] == "quickpart" and not item.get("pages"):
                    rep["quickparts"].append(item["id"])
            step = "writing the import's record"
            d = os.path.join(lib.root, "imports")
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, rid + ".json")
            lib._wrote(p)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(undo_rec, f, indent=1, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001  nothing was kept; the caller says so with the step
        diag.error("library_import", "An import could not be kept; nothing was kept", exc=(type(e), e, e.__traceback__))
        raise ImportFailed(step, e) from e
    diag.activity("import_done", added=len(rep["added"]) + len(rep["versions"]), items=len(rep["replaced"]))
    return rep


def undo(lib, rid):
    """Takes an import back: the items it added go, the items it replaced get their values back. Returns how many items
    it changed, or -1 when the import's record is not there."""
    p = os.path.join(lib.root, "imports", f"{rid}.json")
    try:
        with open(p, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return -1
    lib.fresh()
    n = 0
    with lib.transaction():
        for iid in rec.get("new", []):
            if lib.remove(iid):
                n += 1
        for iid, old in (rec.get("old_values") or {}).items():
            if old is not None and lib.update(iid, old):
                n += 1
    for iid in rec.get("new", []):                       # the removed items' value files, once the index no longer names them
        try:
            os.remove(os.path.join(lib.root, "items", iid + ".json"))
        except OSError:
            pass
    os.remove(p)
    return n


def imports(lib):
    """[(id, file, at)] of the imports that can be taken back, newest first."""
    d = os.path.join(lib.root, "imports")
    out = []
    for fn in sorted(os.listdir(d), reverse=True) if os.path.isdir(d) else []:
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                r = json.load(f)
            out.append((r["id"], r.get("file", ""), r.get("at", "")))
        except (OSError, ValueError, KeyError):
            continue
    return out


def apply_here(config_dir, items, work, path):
    """The ticked items put into a copy of a standard being edited. Returns (the copy, [what changed]); raises
    ImportFailed (the standard being edited is left as it was) when an item cannot go in."""
    w = copy.deepcopy(work)
    said = []
    for it in items:
        if not it.get("take") or it["kind"] == "font":
            continue
        try:
            s = TL.use_values(config_dir, it["kind"], it["name"], it["values"], w, src=path)
        except Exception as e:  # noqa: BLE001
            diag.error("library_import", "An item could not go into the standard being edited", exc=(type(e), e, e.__traceback__))
            raise ImportFailed(f"putting {it['name']} into what you are editing", e) from e
        if s:
            said.append(s)
    return w, said


def report_words(rep):
    """One line of what an import kept."""
    bits = [f"{len(rep['added'])} added" if rep["added"] else "", f"{len(rep['versions'])} new version(s)" if rep["versions"] else "",
            f"{len(rep['replaced'])} replaced" if rep["replaced"] else "", f"{len(rep['renamed'])} kept both, renamed" if rep["renamed"] else "",
            f"{rep['skipped']} not kept" if rep["skipped"] else "", f"{rep['same']} already in the library" if rep["same"] else ""]
    return "; ".join(b for b in bits if b) or "Nothing was kept."

