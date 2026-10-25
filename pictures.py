"""Pictures inside files, and reading a region of one (2.15.0: shared by Acronym Hunter and Acronym Hunter Training).

Every page or embedded picture in a file as (label, loader -> PIL RGB image), the scanner location that points at
one, and region OCR that shows every reading, including ones below the scanner's confidence cutoff.
"""
import app_gui as eng          # engine: sandbox, network guard, OCR, readers (must be first)
import os, io, re, zipfile, posixpath
import numpy as np
import cv2
from PIL import Image

PAD = 16                                                # white border added around a region before reading

# --------------------------------------------------------------------------------------
# Sources: every page or embedded picture in a file, as (label, loader -> PIL RGB image)
# --------------------------------------------------------------------------------------
def _img_from_bytes(data):
    return Image.open(io.BytesIO(data)).convert("RGB")

def _zip_read(path, member):
    with zipfile.ZipFile(path) as z:
        return z.read(member)

def _render_pdf_page(path, index):
    return eng.render_pdf_page(path, index, int(eng.OCR_CFG["pdf_scan_dpi"]))

def _office_parts(z, path):
    """[(part path, location label)] for parts that can hold pictures, in reading order."""
    names = set(z.namelist())
    low = path.lower()
    if low.endswith(".pptx"):
        pres, prels = eng._xml(z, "ppt/presentation.xml"), eng.zip_rels(z, "ppt/presentation.xml")
        ids = [s.get(eng._q("r", "id")) for s in pres.iter(eng._q("p", "sldId"))]
        return [(prels[r][1], f"Slide {n}") for n, r in enumerate(ids, 1) if r in prels]
    if low.endswith(".docx"):
        parts = [("word/document.xml", "Body")]
        for p in sorted(names):
            m = re.match(r"word/(header|footer)(\d*)\.xml$", p)
            if m:
                parts.append((p, f"{m.group(1).title()} {m.group(2)}".strip()))
        return parts
    if low.endswith(".xlsx"):
        wbx, wrels = eng._xml(z, "xl/workbook.xml"), eng.zip_rels(z, "xl/workbook.xml")
        parts = []
        for s in wbx.iter(eng._q("ss", "sheet")):
            rid = s.get(eng._q("r", "id"))
            if rid in wrels:
                for kind, target, ext in eng.zip_rels(z, wrels[rid][1]).values():
                    if kind == "drawing" and not ext:
                        parts.append((target, s.get("name")))
        return parts
    return []

def match_source(labels, location):
    """Index of the Trainer source (page or picture) that a scanner location points at, or None.
    "Deck.pptx (Slide 4, image 'Picture 2' image1.png)" matches that picture; "Deck.pptx (Slide 4)" (typed text) matches
    nothing; "Manual.pdf (p.1)" matches page 1, never page 12."""
    loc = location.split(" [OCR fix", 1)[0].rstrip(")").replace("(Vector text", "(Vector graphic")
    for i, label in enumerate(labels):
        core = label.rstrip(")")
        if loc == core or (loc.startswith(core) and loc[len(core)] in ", "):
            return i
    return None

def list_sources(path):
    name, ext = os.path.basename(path), os.path.splitext(path)[1].lower()
    if ext in eng.IMAGE_EXTS:
        return [(f"{name} (Image)", lambda: _img_from_bytes(open(path, "rb").read()))]
    if ext in eng.VECTOR_FILE_EXTS:   # drawn at high resolution so small labels can be boxed
        return [(f"{name} (Vector graphic)", lambda: _img_from_bytes(eng.render_vector(open(path, "rb").read(), ext)))]
    if ext == ".pdf":
        n = eng.pdf_page_count(path)
        return [(f"{name} (p.{i + 1})", (lambda i=i: _render_pdf_page(path, i))) for i in range(n)]
    out, seen = [], set()
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for part, where in _office_parts(z, path):
            if part not in names:
                continue
            root, rels = eng._xml(z, part), eng.zip_rels(z, part)
            for blip in root.iter(eng._q("a", "blip")):
                rid = blip.get(eng._q("r", "embed"))
                if not rid or rid not in rels or rels[rid][2]:
                    continue
                target = rels[rid][1]
                text_ext = posixpath.splitext(target)[1].lower()
                is_vec = text_ext in eng.VECTOR_EXTS
                if (text_ext not in eng.IMAGE_EXTS and not is_vec) or (where, target) in seen:
                    continue
                seen.add((where, target))
                shape = eng.shape_name(blip)
                shown = f"'{shape}' " if shape else ""
                load = (lambda t=target, e=text_ext: _img_from_bytes(eng.render_vector(_zip_read(path, t), e))) if is_vec \
                    else (lambda t=target: _img_from_bytes(_zip_read(path, t)))
                out.append((f"{name} ({where}, {'vector' if is_vec else 'image'} {shown}{posixpath.basename(target)})", load))
    return out

# --------------------------------------------------------------------------------------
# Region OCR: shows EVERY reading, including ones below the scanner's confidence cutoff
# --------------------------------------------------------------------------------------
def _prepare(pil_crop):
    bgr = cv2.cvtColor(np.array(pil_crop), cv2.COLOR_RGB2BGR)
    bgr = cv2.copyMakeBorder(bgr, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    ok, buf = cv2.imencode(".png", bgr)
    clean = eng.enhance_image_for_ocr(buf.tobytes())
    return clean, (clean.shape[1] / bgr.shape[1] if clean is not None else 1.0)

def read_region_lines(pil_crop):
    """[((x0, y0, x1, y1) in crop pixels, text, confidence)] for every detected text line."""
    clean, scale = _prepare(pil_crop)
    if clean is None:
        return []
    res, _ = eng.get_ocr()(clean, text_score=0.0, box_thresh=float(eng.OCR_CFG["detect_box_thresh"]),
                           unclip_ratio=float(eng.OCR_CFG["detect_unclip_ratio"]))
    lines = []
    for box, text, conf in (res or []):
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        x0, y0 = max(0, min(xs) / scale - PAD), max(0, min(ys) / scale - PAD)
        x1 = min(pil_crop.width, max(xs) / scale - PAD); y1 = min(pil_crop.height, max(ys) / scale - PAD)
        if x1 > x0 and y1 > y0:
            lines.append(((x0, y0, x1, y1), str(text), float(conf)))
    lines.sort(key=lambda l: (round(l[0][1] / 15), l[0][0]))
    return lines

def tighten(pil_crop):
    """Trim empty margins so the text fills the box (the recognizer scales every line to 48 px tall)."""
    g = np.array(pil_crop.convert("L"))
    _t, ink = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ys, xs = np.nonzero(ink)
    if len(xs) == 0 or ink.mean() > 127:       # blank, or light text on a dark background: leave as is
        return pil_crop
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    m = max(2, int(0.2 * (y1 - y0 + 1)))
    return pil_crop.crop((max(0, x0 - m), max(0, y0 - m), min(pil_crop.width, x1 + m + 1), min(pil_crop.height, y1 + m + 1)))

def read_region_as_one_line(pil_crop):
    """Skip text detection and read the whole region as one line (recovers words the detector missed)."""
    tight = tighten(pil_crop)
    bgr = cv2.cvtColor(np.array(tight), cv2.COLOR_RGB2BGR)
    if bgr.shape[0] < 32:                      # enlarge small text so strokes survive the 48 px resize
        f = 48.0 / bgr.shape[0]
        bgr = cv2.resize(bgr, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    res, _ = eng.get_ocr()(bgr, use_det=False, use_cls=False)
    if not res:
        return "", 0.0
    return str(res[0][0]), float(res[0][1])
