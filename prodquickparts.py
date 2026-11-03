"""Quick Parts in a standard (3.22.0): the building blocks a template made from the standard carries.

Picked from any template or Word document (.dotx, .dotm, .docx), which is read once and never written; macros never run,
only the XML is read. A copy of the source file is kept with this PC's standards (<config>\\production_parts, the same
folder as covers and back covers, never the program folder), so the standard can put the entries into every template it
makes. Make a template copies them in with their pictures and styles and, when the standard says so, puts every one in
the Quick Parts gallery under its category (Word lists them by category, then name)."""
import hashlib, os, re, shutil

import prodparts as PP
from prodengine.engine.pkg import Package, NS
from prodengine.engine.ops import glossary as G

QUICK_GALLERY = "docParts"            # Word's Quick Parts gallery
QP_ALLOWED = ("word/glossary/*", "package|parts")     # the guarded write lets this op change the glossary and add its parts only


def gallery_name(g):
    return G.GALLERIES.get(g or "", g or "no gallery")


def read(path):
    """[{name, category, gallery, description, text, pictures}] of a file's Quick Parts; [] when it has none."""
    pkg = Package(path)
    return [{k: e[k] for k in ("name", "category", "gallery", "description", "text", "pictures")} for e in G.entries(pkg)]


def keep_source(config_dir, path):
    """A copy of the source file in the standards' parts folder (once per distinct file). Returns its file name."""
    with open(path, "rb") as f:
        data = f.read()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(path))[0])[:40] or "quickparts"
    ext = os.path.splitext(path)[1].lower() if os.path.splitext(path)[1].lower() in (".dotx", ".dotm", ".docx") else ".dotx"
    name = f"qp_{stem}_{hashlib.sha256(data).hexdigest()[:8]}{ext}"
    folder = PP.parts_dir(config_dir)
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, name)
    if not os.path.isfile(dst):
        shutil.copyfile(path, dst)
    return name


def op_quick_parts(pkg, entries, parts_dir, one_gallery=True):
    """Copy the standard's Quick Parts into the template from their kept sources; in one gallery when asked, each under
    its category. A missing source or a name already in the template is reported, never guessed."""
    by_src, missing = {}, []
    for e in entries or []:
        src = os.path.join(parts_dir or "", e.get("source") or "")
        if not e.get("name") or not os.path.isfile(src):
            missing.append(e.get("name") or "(no name)")
            continue
        by_src.setdefault(src, []).append(e)
    copied, skipped = [], []
    for src, es in by_src.items():
        try:
            r = G.op_provision(pkg, src, [e["name"] for e in es])
        except G.Refused as ex:
            skipped += [(e["name"], str(ex)) for e in es]
            continue
        copied += [n for n in r.get("copied", [])]
        skipped += list(r.get("skipped", []))
    want = {e["name"]: e for e in entries or [] if e.get("name") in copied}
    if want and G.gloss_part(pkg):
        pkg.touch(G.gloss_part(pkg))
        for dp in pkg.tree(G.gloss_part(pkg)).iter(f"{{{NS['w']}}}docPart"):
            pr = dp.find("w:docPartPr", NS)
            nm = pr.find("w:name", NS)
            name = nm.get(f"{{{NS['w']}}}val") if nm is not None else None
            if name not in want:
                continue
            pkg.mark(dp)
            if want[name].get("category"):
                G._set(pr, ["category", "name"], want[name]["category"])
            if one_gallery:
                G._set(pr, ["category", "gallery"], QUICK_GALLERY)
        G.check_unique(pkg)
    return {"copied": copied, "skipped": skipped, "missing": missing}
