"""The Parts library (3.95.0; claude/stationkeeper-libraries-and-sets.md, canvas "Libraries and Sets" boards 4, 7 and 8):
covers, marking (CUI) pages, title pages, front matter (contents, acronyms, units), back covers and Quick Parts, each
kind a tab. A page part is a whole Word file (the section designs store, sectiondesigns); a Quick Part is a gallery
entry kept in the template library. Every part has versions (a version is never changed: bring the Word file back as a
new version, Name this version), shown as tabs on its row; part sets group parts by use (a set names exact versions,
one of each part). Bring in from a document reads a file once: its pages (one per Word section, each said to be a
cover, a CUI page, a title page...) and its Quick Parts gallery; you tick what you keep. Rules only (No AI); nothing
leaves the PC."""
import os
import re
import tempfile

import sectiondesigns as SDZ

KINDS = (("covers", "Covers", ("cover",)), ("marking", "Marking pages", ("cui",)), ("titles", "Title pages", ("title",)),
         ("front", "Front matter", ("toc", "acronyms", "units")), ("back", "Back covers", ("back",)), ("quick", "Quick Parts", ()))
KIND = {k: (t, s) for k, t, s in KINDS}
PAGE_WORDS = {"cover": "Cover", "cui": "Marking page (CUI)", "title": "Title page", "toc": "Table of contents",
              "acronyms": "Acronyms and abbreviations", "units": "Units and symbols", "back": "Back cover"}
PAGE_SHELVES = ("cover", "cui", "title", "toc", "acronyms", "units", "back")


# ------------------------------------------------------------------ versions of a page part
def _all(config_dir):
    return SDZ.designs(config_dir)


def family(x):
    return x.get("family") or x["id"]


def version(x):
    return int(x.get("version") or 1)


def versions_of(config_dir, did):
    """Every version of a page part, oldest first."""
    x = SDZ.get(config_dir, did)
    if x is None:
        return []
    return sorted((y for y in _all(config_dir) if family(y) == family(x)), key=version)


def shown_name(config_dir, x):
    """'Blue cover v2: CUI' where a part has more than one version (Setup's picker and the rows)."""
    many = len(versions_of(config_dir, x["id"])) > 1
    return x["name"] + (f" v{version(x)}" if many else "") + (f": {x['label']}" if x.get("label") else "")


def new_version(config_dir, did, path, label=""):
    """The Word file brought back as a new version of the part (the version it came from stays; Setups that picked it
    keep it). What fills it carries over for the paragraphs that are still there. Returns the new version."""
    x = SDZ.get(config_dir, did)
    if x is None:
        return None
    y = SDZ.add(config_dir, x["shelf"], path, name=x["name"])
    info = SDZ.read(path)
    keep = {str(p["i"]) for p in info["paragraphs"]}
    m = {k: v for k, v in (x.get("map") or {}).items() if k in keep}
    m.update({k: v for k, v in SDZ.default_map(info).items() if k not in m})
    d = SDZ._index(config_dir)
    z = next(e for e in d["designs"] if e["id"] == y["id"])
    fam = family(x)
    for e in d["designs"]:                                   # the family's first version names the family too
        if e["id"] == fam:
            e.setdefault("family", fam); e.setdefault("version", 1)
    z.update({"family": fam, "version": 1 + max(version(e) for e in d["designs"] if family(e) == fam and e["id"] != z["id"]),
              "map": m, "label": " ".join(str(label or "").split())[:60], "came_from": did})
    SDZ._save(config_dir, d)
    return z


def set_label(config_dir, did, label):
    d = SDZ._index(config_dir)
    z = next((e for e in d["designs"] if e["id"] == did), None)
    if z is None:
        return False
    z["label"] = " ".join(str(label or "").split())[:60]
    SDZ._save(config_dir, d)
    return True


def rows(config_dir, kind, lib=None, shown=None, words=""):
    """One row per part (its versions are tabs): [{"family", "versions" (oldest first), "shown" (an id)}]. Page parts
    by their shelves; Quick Parts from the template library (ids "q:<item id>")."""
    shown = shown or {}
    q = (words or "").strip().casefold()
    out = []
    if kind == "quick":
        if lib is None:
            return []
        fams = {}
        for it in lib.items:
            if it["kind"] == "quickpart" and (not q or q in it["name"].casefold()):
                fams.setdefault(it.get("family") or it["id"], []).append(it)
        for fam, its in sorted(fams.items(), key=lambda kv: lib.base_of(kv[1][0]).casefold()):
            vs = sorted(its, key=lambda i: int(i.get("version") or 1))
            ids = ["q:" + i["id"] for i in vs]
            out.append({"family": "q:" + fam, "versions": ids, "shown": shown.get("q:" + fam) if shown.get("q:" + fam) in ids else ids[-1]})
        return out
    shelves = KIND.get(kind, ("", ()))[1]
    fams = {}
    for x in _all(config_dir):
        if x["shelf"] in shelves and (not q or q in x["name"].casefold()):
            fams.setdefault(family(x), []).append(x)
    for fam, xs in sorted(fams.items(), key=lambda kv: (shelves.index(kv[1][0]["shelf"]), kv[1][0]["name"].casefold())):
        vs = sorted(xs, key=version)
        ids = ["d:" + x["id"] for x in vs]
        out.append({"family": "d:" + fam, "versions": ids, "shown": shown.get("d:" + fam) if shown.get("d:" + fam) in ids else ids[-1]})
    return out


def count(config_dir, kind, lib=None):
    return len(rows(config_dir, kind, lib))


# ------------------------------------------------------------------ part sets (template library kits, kind "part")
def _fam_of(config_dir, lib, pid):
    if pid.startswith("d:"):
        x = SDZ.get(config_dir, pid[2:])
        return "d:" + family(x) if x else None
    it = lib.get(pid[2:]) if lib is not None else None
    return "q:" + (it.get("family") or it["id"]) if it else None


def add_to_set(config_dir, lib, sid, pids):
    """Parts into a part set, one version of each part (another version of the same part comes out). Returns the ids it
    replaced."""
    k = lib.kit(sid)
    if k is None:
        return []
    gone = []
    for pid in pids:
        fam = _fam_of(config_dir, lib, pid)
        if fam is None:
            continue
        for other in list(k["items"]):
            if other != pid and _fam_of(config_dir, lib, other) == fam:
                k["items"].remove(other); gone.append(other)
        if pid not in k["items"]:
            k["items"].append(pid)
    lib.save()
    return gone


def sets_of(lib, pid):
    import stylelib as SL
    return [k for k in SL.sets(lib, "part") if pid in k["items"]]


# ------------------------------------------------------------------ bringing parts in from a document
def guess(text, n):
    """What a page most likely is, from its words and its place in the file."""
    t = (text or "").casefold()
    if "controlled unclassified" in t or re.search(r"\bcui\b", t) and len(t) < 600:
        return "cui"
    if "table of contents" in t or t.strip().startswith("contents"):
        return "toc"
    if "acronym" in t or "abbreviation" in t:
        return "acronyms"
    if "units" in t and "symbol" in t:
        return "units"
    return "cover" if n == 1 else "title"


def _sha(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:10]


def _qp_values(e, h):
    """A Quick Part's values as the template library keeps them (the same as Make templates' reading of a file)."""
    return {"entry": e["name"], "category": e["category"] or "", "gallery": e["gallery"] or "", "source_sha": h,
            "description": e.get("description") or ""}


def look(path, lib=None, work=None):
    """What a file holds, only read: {"pages": [{"n", "file", "lines", "kind", "name", "keep"}], "gallery": [{entry...,
    "state", "keep"}]}. A file with several Word sections gives one page part per section."""
    import prodquickparts as QP
    work = work or tempfile.mkdtemp(prefix="sk_parts_")
    pages = []
    info = SDZ.read(path)
    files = SDZ.split(path, work) if info["sections"] > 1 else [path]
    stem = os.path.splitext(os.path.basename(path))[0]
    for n, f in enumerate(files, 1):
        try:
            inf = SDZ.read(f)
        except Exception:  # noqa: BLE001  a section Word can open but this reader cannot
            continue
        lines = [p["text"] for p in inf["paragraphs"] if p["text"].strip()]
        if not lines and not inf.get("tables"):
            continue
        k = guess(" ".join(lines[:12]), n)
        pages.append({"n": n, "file": f, "lines": lines[:12], "kind": k, "keep": True,
                      "name": f"{stem} {PAGE_WORDS[k].split(' (')[0].lower()}" if len(files) > 1 else stem})
    gallery = []
    try:
        entries = QP.read(path)
    except Exception:  # noqa: BLE001  no glossary
        entries = []
    h = _sha(path) if entries else ""
    for e in entries:
        st = "new"
        if lib is not None:
            st, _hit = lib.match("quickpart", e["name"], _qp_values(e, h))
        gallery.append(dict(e, state=st, keep=st != "same"))
    if len(files) == 1 and gallery:                 # a template with a gallery: its body is not a page to keep
        for x in pages:
            x["keep"] = False
    return {"pages": pages, "gallery": gallery, "path": path}


def keep(config_dir, lib, plan, tags=None):
    """The ticked pages onto their shelves, the ticked Quick Parts into the library. Returns (designs, quick part items)."""
    import templatelib as TL
    designs, items = [], []
    for p in plan["pages"]:
        if p.get("keep") and p.get("kind") in PAGE_SHELVES:
            designs.append(SDZ.add(config_dir, p["kind"], p["file"], name=p.get("name") or ""))
    picks = [e for e in plan["gallery"] if e.get("keep")]
    if picks:
        h = _sha(plan["path"])
        with lib.transaction():
            src = lib.keep_file(plan["path"], os.path.basename(plan["path"]))
            for e in picks:
                values = dict(_qp_values(e, h), source=src)
                it, _st = lib.add("quickpart", e["name"], values, tags=tags, source=plan["path"],
                                  summary=(e.get("text") or "")[:120], who=None)
                items.append(it)
        TL.cleanup(lib)
    return designs, items
