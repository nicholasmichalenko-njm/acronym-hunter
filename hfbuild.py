"""Headers and footers built as tables here (3.42.0), and Quick Parts made from them.

A header or footer layout may hold a one-row table of cells: std["hf_layouts"][part][kind]["table"] = {"cells": [cell],
"borders": "none" | "below" | "above" | "grid"}; a cell = {"width_in": inches (0: share the rest), "lines": [{"text":
words and fields such as {volume_name} {page} {a_number}, "align", "size", "bold"}], "logo": {"b64", "name", "ct", "w_in",
"h_in", "align"} or None}. Make templates and Fix a Copy write it (prodengine/pe/hf.py).

r7_footer(std)       Rule 7's footer: the A number on the left (a STYLEREF to its style), two standard lines in the
                     middle (the marking, then the team's line: blank until the team says what it is), the page number
                     on the right
logo(path, ...)      a picture file as a cell's logo
make_quick_part(...) a header or footer built here as a Quick Part: written into a small Word file of its own (its
                     glossary), kept with the standards' parts, and added to the standard's Quick Parts (in the gallery
                     and category chosen); every template made from the standard then carries it
Rules only; nothing leaves the PC."""
import base64, copy, os

R7_LINE2 = ""            # the team's second standard line (Rule 7): blank until the team gives the words


def cells_of(spec):
    return list(((spec or {}).get("table") or {}).get("cells") or [])


def r7_footer(std=None, line2=None, width_in=6.5):
    """Rule 7's footer as a cells table: left the A number, middle the marking and the team's standard line, right the page."""
    std = std or {}
    r7 = std.get("hf_r7") or {}
    second = r7.get("line2", R7_LINE2) if line2 is None else line2
    third = round(width_in / 3, 2)
    return {"marking": False, "table": {"borders": "none", "cells": [
        {"width_in": third, "lines": [{"text": "{a_number}", "align": "left", "size": None, "bold": False}], "logo": None},
        {"width_in": round(width_in - 2 * third, 2), "lines": [{"text": "{marking}", "align": "center", "size": None, "bold": True},
                                                            {"text": second, "align": "center", "size": 8, "bold": False}], "logo": None},
        {"width_in": third, "lines": [{"text": "{page}", "align": "right", "size": None, "bold": False}], "logo": None}]}}


def is_r7(spec):
    """True when a footer layout is Rule 7's three cells (the A number left, the page number right)."""
    cells = cells_of(spec)
    if len(cells) != 3:
        return False
    left = " ".join(l.get("text", "") for l in cells[0].get("lines") or [])
    right = " ".join(l.get("text", "") for l in cells[2].get("lines") or [])
    return "{a_number}" in left and "{page}" in right


def new_cell(width_in=0.0, text="", align="left"):
    return {"width_in": width_in, "lines": ([{"text": text, "align": align, "size": None, "bold": False}] if text else []), "logo": None}


def logo(path, w_in=1.2, h_in=None, align="left"):
    """A picture file (PNG, JPG, GIF, BMP or EMF) as a cell's logo; h_in from the picture's proportions when not given."""
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    ct = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "bmp": "image/bmp",
          "emf": "image/x-emf"}.get(ext, "image/png")
    with open(path, "rb") as f:
        data = f.read()
    if h_in is None:
        h_in = round(w_in / 2, 2)
        try:
            from PIL import Image
            with Image.open(path) as im:
                h_in = round(w_in * im.height / max(1, im.width), 2)
        except Exception:  # noqa: BLE001  EMF and odd files keep the 2:1 guess
            pass
    return {"b64": base64.b64encode(data).decode("ascii"), "name": os.path.basename(path), "ct": ct, "w_in": float(w_in),
            "h_in": float(h_in), "align": align if align in ("left", "center", "right") else "left"}


def build_part(std, part, kind, parts_dir=""):
    """The header or footer this layout makes, as Word writes it: {kind: xml, kind + "_media": [pictures]} (the shape
    kept designs use). Made on a scratch template; nothing is kept."""
    import tempfile
    import prodrules as PRL
    import prodtemplate as PT
    from prodengine.engine.pkg import Package
    from prodengine.pe import hf as H
    s = PRL.engine_ready(copy.deepcopy(std))
    s["name"] = "Scratch"
    job = PT.make(s, tempfile.mkdtemp(prefix="sk_hf_"), "", parts_dir=parts_dir or s.get("_parts_dir") or "")
    d = H.designs_of(Package(job.copy), PRL.engine_ready(copy.deepcopy(std))).get(part) or {}
    return {kind: d.get(kind, ""), kind + "_media": d.get(kind + "_media", [])}


def make_quick_part(std, part, kind, name, category="", gallery="", parts_dir="", built=None):
    """A header or footer built here as a Quick Part in the standard: written into a Word file of its own (kept in
    parts_dir), and added to std["quick_parts"]["entries"]. built (tests): build_part's result. Returns the entry, or
    None when the layout makes nothing."""
    import qpmake as QM
    name = " ".join((name or "").split())
    if not name:
        return None
    b = built if built is not None else build_part(std, part, kind, parts_dir)
    if not b.get(kind):
        return None
    gallery = gallery or {"header": "hdrs", "footer": "ftrs"}[kind]
    src = QM.make_source(parts_dir, [{"name": name, "category": category or "Stationkeeper", "gallery": gallery, "xml": b[kind],
                                      "media": b.get(kind + "_media") or []}], label=name)
    entry = {"name": name, "category": category or "Stationkeeper", "source": os.path.basename(src), "gallery": gallery, "made_here": True}
    qp = std.setdefault("quick_parts", {"one_gallery": True, "entries": []})
    qp["entries"] = [e for e in qp.get("entries") or [] if e.get("name") != name] + [entry]
    return entry
