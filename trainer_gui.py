"""Acronym Hunter Trainer: region rescans and OCR training-sample capture.

Opens as a window inside the scanner (TrainerWindow: Advanced > Trainer, or right-click a result > Check in picture)
and shares its engine, config\\ folder, network guard, and sandbox. TrainerApp runs it on its own (from source).
"""
import app_gui as eng          # sandbox + temp redirect + network guard + OCR engine + config (must be first)
import os, io, csv, re, json, zipfile, posixpath, hashlib, threading, datetime
import numpy as np
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

TRAIN_DIR = os.path.join(eng.BASE_DIR, "training_data")
IMG_DIR = os.path.join(TRAIN_DIR, "images")
LABELS_FILE = os.path.join(TRAIN_DIR, "labels.txt")     # PaddleOCR recognition format: images/x.png<TAB>text
META_FILE = os.path.join(TRAIN_DIR, "samples.csv")      # who/what/where for each sample
DET_DIR = os.path.join(TRAIN_DIR, "regions")
DET_LABELS_FILE = os.path.join(TRAIN_DIR, "det_labels.txt")   # PaddleOCR detection format: regions/x.png<TAB>[boxes]
SAVE_LOG = os.path.join(TRAIN_DIR, "save_log.jsonl")          # one line per save, so Undo removes the whole save
PACKAGE_DIR = os.path.join(TRAIN_DIR, "package")
CHOICES = ("Skip", "Save as text", "Not text")
OPEN_TYPES = [("Documents and images", "*.pdf *.pptx *.docx *.xlsx *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif *.svg *.svgz *.emf *.wmf *.emz *.wmz")]
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

# --------------------------------------------------------------------------------------
# Training data store (inside the app folder; never shipped in the zip or committed)
# --------------------------------------------------------------------------------------
def _clean_text(t):
    return re.sub(r"[\t\r\n]+", " ", t).strip()

def _png(pil_img):
    buf = io.BytesIO(); pil_img.save(buf, "PNG"); return buf.getvalue()

def _sample_id(data):
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + hashlib.sha1(data).hexdigest()[:8] + "_" + os.urandom(3).hex()

def _meta(rows):
    new = not os.path.exists(META_FILE)
    with open(META_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Date", "Image", "Text", "OCR read", "Confidence", "Source", "Box (x0,y0,x1,y1)"])
        w.writerows(rows)

def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def save_sample(pil_img, text, ocr_text, conf, source, box):
    """One text-line image for recognition training (images/ + labels.txt). Returns the image path."""
    os.makedirs(IMG_DIR, exist_ok=True)
    data = _png(pil_img)
    rel = f"images/{_sample_id(data)}.png"
    with open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "wb") as f:
        f.write(data)
    with open(LABELS_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{rel}\t{_clean_text(text)}\n")
    _meta([[_now(), rel, _clean_text(text), _clean_text(ocr_text), f"{conf:.2f}", source,
            ",".join(str(int(v)) for v in box)]])
    return rel

def save_region(pil_img, text_boxes, unsure_boxes, not_text, source, region):
    """The whole drawn box for detection training (regions/ + det_labels.txt).
    text_boxes: [(box, text)] real text. unsure_boxes: lines left on Skip (marked ### = ignore, not taught either way).
    Everything else in the image, including every 'Not text' line, is taught as background."""
    os.makedirs(DET_DIR, exist_ok=True)
    data = _png(pil_img)
    rel = f"regions/{_sample_id(data)}.png"
    with open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "wb") as f:
        f.write(data)
    pts = lambda b: [[int(b[0]), int(b[1])], [int(b[2]), int(b[1])], [int(b[2]), int(b[3])], [int(b[0]), int(b[3])]]
    label = [{"transcription": _clean_text(t), "points": pts(b)} for b, t in text_boxes]
    label += [{"transcription": "###", "points": pts(b)} for b in unsure_boxes]
    if not label:   # PaddleOCR skips images with no boxes; a 1-pixel ignore box keeps a pure "not text" example
        label = [{"transcription": "###", "points": pts((0, 0, 1, 1))}]
    with open(DET_LABELS_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{rel}\t{json.dumps(label, ensure_ascii=False)}\n")
    rx, ry = region[0], region[1]
    _meta([[_now(), rel, "(not text)", _clean_text(t), f"{c:.2f}", source,
            ",".join(str(int(v)) for v in (rx + b[0], ry + b[1], rx + b[2], ry + b[3]))] for b, t, c in not_text])
    return rel

def _log_save(entry):
    os.makedirs(TRAIN_DIR, exist_ok=True)
    with open(SAVE_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _drop_lines(path, images):
    if not os.path.exists(path):
        return
    keep = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip() and l.split("\t", 1)[0] not in images]
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(l + "\n" for l in keep))
    os.replace(path + ".tmp", path)

def _remove_images(images):
    for rel in images:
        try:
            os.remove(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)))
        except OSError:
            pass
    _drop_lines(LABELS_FILE, images)
    _drop_lines(DET_LABELS_FILE, images)
    if os.path.exists(META_FILE):
        rows = [r for r in csv.reader(open(META_FILE, encoding="utf-8", newline="")) if not (len(r) > 1 and r[1] in images)]
        with open(META_FILE + ".tmp", "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
        os.replace(META_FILE + ".tmp", META_FILE)

def remove_last_save():
    """Undo the most recent save: its line samples, region sample, and ignore-list entries. Returns a description."""
    entries = []
    if os.path.exists(SAVE_LOG):
        entries = [l for l in open(SAVE_LOG, encoding="utf-8").read().splitlines() if l.strip()]
    if entries:
        last = json.loads(entries.pop())
        with open(SAVE_LOG + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(l + "\n" for l in entries))
        os.replace(SAVE_LOG + ".tmp", SAVE_LOG)
        _remove_images(set(last.get("images", [])))
        ignored = set(last.get("ignored", []))
        if ignored:
            eng.write_ocr_ignore_rows([r for r in eng.read_ocr_ignore_rows() if r[0] not in ignored])
        return last.get("summary", "last save")
    # samples saved before v1.3.1 have no log: remove the last line sample
    if not os.path.exists(LABELS_FILE):
        return None
    lines = [l for l in open(LABELS_FILE, encoding="utf-8").read().splitlines() if l.strip()]
    if not lines:
        return None
    img_rel, text = (lines[-1].split("\t", 1) + [""])[:2]
    _remove_images({img_rel})
    return f"sample '{text}'"

def _count(path):
    return sum(1 for l in open(path, encoding="utf-8") if l.strip()) if os.path.exists(path) else 0

def training_stats():
    """(text-line samples, region samples, not-text examples, bytes on disk)"""
    not_text = 0
    if os.path.exists(META_FILE):
        not_text = sum(1 for r in csv.reader(open(META_FILE, encoding="utf-8", newline="")) if len(r) > 2 and r[2] == "(not text)")
    size = 0
    for root, _d, files in os.walk(TRAIN_DIR):
        size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    return _count(LABELS_FILE), _count(DET_LABELS_FILE), not_text, size

def _model_characters():
    """Characters the current recognition model can output (from its ONNX metadata)."""
    if eng.OCR_BACKEND == "tesseract":   # Google's English model writes Latin letters, digits, and common symbols
        import string
        return set(string.printable) | set("±°µΩ×÷–—’‘“”•§©®™¼½¾²³")
    import onnxruntime as ort
    import rapidocr_onnxruntime as _ro
    custom = os.path.join(eng.MODELS_DIR, "rec.onnx")
    keys = os.path.join(eng.MODELS_DIR, "rec_keys.txt")
    if os.path.isfile(keys):
        return set(open(keys, encoding="utf-8").read().splitlines()) | {" "}
    path = custom if os.path.isfile(custom) else os.path.join(os.path.dirname(_ro.__file__), "models", "ch_PP-OCRv4_rec_infer.onnx")
    meta = ort.InferenceSession(path, providers=["CPUExecutionProvider"]).get_modelmeta().custom_metadata_map
    return set(meta.get("character", "").splitlines()) | {" "}

def build_training_package():
    """Split the samples into train/val lists that PaddleOCR reads directly from training_data\\.
    No images are copied, so the package adds only a few KB. Returns a report string."""
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    def split(src, prefix):
        lines = [l for l in open(src, encoding="utf-8").read().splitlines() if l.strip()] if os.path.exists(src) else []
        train, val = [], []
        for l in lines:   # stable split: the same sample always lands in the same set
            (val if int(hashlib.sha1(l.split("\t", 1)[0].encode()).hexdigest(), 16) % 10 == 0 else train).append(l)
        if lines and not val:
            val.append(train.pop())
        for name, rows in ((f"{prefix}_train.txt", train), (f"{prefix}_val.txt", val)):
            with open(os.path.join(PACKAGE_DIR, name), "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(r + "\n" for r in rows))
        return lines, len(train), len(val)
    rec, rec_t, rec_v = split(LABELS_FILE, "rec")
    det, det_t, det_v = split(DET_LABELS_FILE, "det")
    missing = set()
    try:
        chars = _model_characters()
        for l in rec:
            missing |= {c for c in l.split("\t", 1)[-1] if c not in chars}
    except Exception:
        eng.log_error("Could not read the recognition model's character list")
    report = [f"Training package written to {PACKAGE_DIR}",
              f"Text-line samples (recognition): {len(rec)}  ->  {rec_t} train / {rec_v} check",
              f"Region samples (detection):      {len(det)}  ->  {det_t} train / {det_v} check"]
    report.append("Recognition: ready to fine-tune." if len(rec) >= 300 else
                  f"Recognition: {len(rec)} of about 300 samples minimum (1,000+ recommended). Keep collecting.")
    report.append("Detection: ready to fine-tune." if len(det) >= 100 else
                  f"Detection: {len(det)} of about 100 region samples minimum (300+ recommended). Keep collecting.")
    if missing:
        report.append("Characters the current model cannot output (fix the label or they will be skipped): "
                      + " ".join(sorted(missing)))
    open(os.path.join(PACKAGE_DIR, "package_report.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
    return "\n".join(report)

def fixes_from_correction(ocr_text, corrected):
    """Word pairs that differ between what OCR read and the corrected text (same word count only)."""
    strip = lambda w: re.sub(r"^[^\w&/]+|[^\w&/.]+$", "", w)
    a, b = ocr_text.split(), corrected.split()
    if len(a) != len(b):
        return []
    return [(strip(x), strip(y)) for x, y in zip(a, b) if strip(x) and strip(y) and strip(x) != strip(y)]

HELP_TEXT_TESSERACT = """HOW YOUR SAMPLES MAKE THE SCANNER BETTER (US edition, Tesseract engine)

Right away (no training needed):
  1. "Not text" on a green line -> ignore list -> gone from the next scan.
  2. Correct a misread word, then "Add OCR Fixes from Corrections" -> fixed on the next scan.

Training the reader on this PC (CPU only, no GPU, no internet, no extra download):
  3. Keep saving lines with "Save as text". 20 is the minimum; 300+ gives a dependable gain.
     Save the styles the scanner gets wrong: small labels, unusual fonts, text on shading.
  4. Click "Improve Reading" (here, or on the banner in the scanner). It fine-tunes Google's
     English model on your lines with Tesseract's own training tool, on this PC's processor,
     and checks the result on lines it did not train on. A few hundred lines take minutes.
  5. It installs the new reader only if it scored better, then offers to rescan.
     The scanner uses config\\models\\acronym.traineddata from then on.
  6. Score it on real files. Worse? Scanner > Knowledge > Undo Last Knowledge Change.
  7. Better? Scanner > Knowledge > Export Knowledge Pack > approved SharePoint folder.
     Colleagues click Knowledge > Install Knowledge Pack.

What "Not text" regions do here: Tesseract finds text with fixed rules, so region samples do not
train it. They still feed the ignore list (step 1) and stay saved for any future engine.

Undo Last Save removes everything from the last save, including ignore-list entries it added.
training_data\\ holds crops of your documents: handle it at the documents' classification.
The trained model is learned from those crops: same handling, approved SharePoint only.
"""

HELP_TEXT = """WHAT EACH CHOICE DOES

Save as text
  You confirm the line is real text and its spelling is right (fix it in the box first).
  Saved: a picture of that one line + its correct text (training_data\\images, labels.txt).
  Teaches the READER (recognition model) to spell this style correctly.

Not text
  You confirm the "reading" is not text: a diagram line, arrow, border, speck, or hatching
  that OCR turned into letters or Asian characters.
  Saved: the whole box you drew, with the not-text spot marked as background
  (training_data\\regions, det_labels.txt). Teaches the FINDER (detection model) to stop
  drawing a text box there.
  Works right away too: if the line was GREEN (the scanner keeps it), that exact reading is
  added to config\\ocr_ignore.csv, so the scanner drops it from pictures on the next scan.
  It never affects typed text in documents. Review or edit the list with "Ignore List".

Skip
  Not used for training. In the region sample it is marked "unsure", so it teaches nothing either way.

GREEN vs RED
  Green = confidence at or above the cutoff (config\\ocr_settings.json: min_confidence, or
          tesseract_min_confidence in the US edition).
          The scanner keeps it, so a wrong green reading can become a false result.
  Red   = below the cutoff. The scanner already throws it away. Marking a red line
          "Not text" is still a useful training example; it just does not need the ignore list.

HOW YOUR SAMPLES MAKE THE SCANNER BETTER

Right away (no training needed):
  1. Not text on green lines -> ignore list -> gone from the next scan.
  2. Correct a misread word, then "Add OCR Fixes from Corrections" -> fixed on the next scan.

Over time (training a new model with the offline Training Kit):
  3. Keep saving. Aim for 300+ text lines (1,000+ is better) and 100+ regions.
  4. "Prepare Training Package" shows how many you have and flags any character
     the model cannot output.
  5. Copy this training_data\\ folder into the Training Kit's samples\\<your name>\\.
  6. Double-click Train.cmd in the kit. It trains offline (often overnight) and writes
     output\\models\\ (rec.onnx = reader, det.onnx = finder).
  7. Scanner > Knowledge > Load Trained Models > pick output\\models. Score it.
     Worse? Knowledge > Undo Last Knowledge Change.
  8. Better? Knowledge > Export Knowledge Pack > approved SharePoint folder.
     Colleagues click Knowledge > Install Knowledge Pack.

Undo Last Save removes everything from the last save, including ignore-list entries it added.
training_data\\ holds crops of your documents: handle it at the documents' classification.
"""

# --------------------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------------------
class _TrainerUI:
    """The Trainer's contents. TrainerWindow shows them inside the scanner; TrainerApp on their own."""
    scanner = None

    def _build_ui(self, start_file=None, focus=None):
        self.title(f"Acronym Hunter {eng.APP_VERSION}: Trainer (check pictures and teach the reader)")
        self.focus_target = focus      # (scanner location, term) from "Check in picture"
        self.focus_term = focus[1] if focus else None
        self.geometry("1300x800"); self.minsize(1000, 560)
        self.sources, self.img, self.tk_img, self.zoom = [], None, None, 1.0
        self.source_label, self.region, self.region_img, self.line_rows = "", None, None, []
        self.drag_start, self.rect_id = None, None

        top = ctk.CTkFrame(self); top.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkButton(top, text="Open File", width=120, command=self.open_file).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(top, text="Fit", width=60, command=self.fit).pack(side="left", padx=(16, 4))
        ctk.CTkButton(top, text="-", width=40, command=lambda: self.set_zoom(self.zoom / 1.25)).pack(side="left", padx=2)
        ctk.CTkButton(top, text="+", width=40, command=lambda: self.set_zoom(self.zoom * 1.25)).pack(side="left", padx=2)
        self.lbl_zoom = ctk.CTkLabel(top, text="", width=60); self.lbl_zoom.pack(side="left", padx=6)
        ctk.CTkButton(top, text="Select Whole Image", width=150, fg_color="#64748B",
                      command=self.select_all).pack(side="left", padx=8)
        self.lbl_help = ctk.CTkLabel(top, text="Open a file, pick a page or picture, then drag a box around missed text.",
                                     text_color="gray")
        self.lbl_help.pack(side="left", padx=12)

        body = ctk.CTkFrame(self); body.pack(fill="both", expand=True, padx=12, pady=4)
        body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, width=300); left.grid(row=0, column=0, sticky="nsw", padx=(0, 6))
        ctk.CTkLabel(left, text="Pages and pictures", font=("Arial", 13, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.listbox = tk.Listbox(left, width=42, activestyle="none", exportselection=False, font=("Segoe UI", 10))
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_source)

        mid = ctk.CTkFrame(body); mid.grid(row=0, column=1, sticky="nsew")
        mid.grid_rowconfigure(0, weight=1); mid.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(mid, bg="#3A3F47", highlightthickness=0, cursor="crosshair")
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        hsb = ttk.Scrollbar(mid, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns"); hsb.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Control-MouseWheel>", lambda e: self.set_zoom(self.zoom * (1.25 if e.delta > 0 else 0.8)))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        right = ctk.CTkFrame(body, width=440); right.grid(row=0, column=2, sticky="nse", padx=(6, 0))
        right.grid_propagate(False); right.grid_rowconfigure(2, weight=1); right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="What OCR read in the box", font=("Arial", 13, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(right, justify="left", wraplength=410, text=(
            "GREEN line: the scanner keeps this reading; it can show up in your results.\n"
            "RED line: low confidence; the scanner already ignores it.\n"
            "Numbers match the boxes on the picture. For each line pick:\n"
            "  Skip: leave it out of training.\n"
            "  Save as text: it is real text. Fix the spelling first; typing picks this.\n"
            "  Not text: lines, arrows, or specks read as letters (even Asian characters).\n"
            "Then click Save Choices.")).grid(row=1, column=0, sticky="w", padx=10)
        self.lines_frame = ctk.CTkScrollableFrame(right); self.lines_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)

        one = ctk.CTkFrame(right); one.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(one, text="Whole box as ONE line (use when OCR found nothing or split it):", justify="left").pack(anchor="w", padx=6, pady=(6, 2))
        self.lbl_one = ctk.CTkLabel(one, text="Read as one line: -", text_color="gray"); self.lbl_one.pack(anchor="w", padx=6)
        self.entry_one = ctk.CTkEntry(one, placeholder_text="Correct text for the whole box"); self.entry_one.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(one, text="Save Whole Box as One Sample", command=self.save_whole).pack(fill="x", padx=6, pady=(0, 8))

        acts = ctk.CTkFrame(right); acts.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 8))
        ctk.CTkButton(acts, text="Save Choices", command=self.save_choices).pack(fill="x", padx=6, pady=(8, 4))
        ctk.CTkButton(acts, text="Add OCR Fixes from Corrections", fg_color="#7C3AED", command=self.add_fixes).pack(fill="x", padx=6, pady=(0, 8))

        bottom = ctk.CTkFrame(self); bottom.pack(side="bottom", fill="x", padx=12, pady=(4, 12), before=body)  # never pushed off-screen
        self.lbl_stats = ctk.CTkLabel(bottom, text=""); self.lbl_stats.pack(side="left", padx=10, pady=8)
        ctk.CTkButton(bottom, text="Close", width=80, command=self.destroy).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(bottom, text="Undo Last Save", width=140, fg_color="#DC2626", command=self.undo_sample).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(bottom, text="Open Training Folder", width=160, fg_color="#475569", command=self.open_folder).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(bottom, text="Ignore List", width=110, fg_color="#475569", command=self.open_ignore_list).pack(side="right", padx=6, pady=8)
        if eng.OCR_BACKEND == "tesseract":
            self.btn_train = ctk.CTkButton(bottom, text="Improve Reading...", width=150, fg_color="#0F766E",
                                           command=(self.scanner.open_improve if self.scanner is not None else self.train_reader))
            self.btn_train.pack(side="right", padx=6, pady=8)
        else:
            ctk.CTkButton(bottom, text="Prepare Training Package", width=190, fg_color="#0F766E", command=self.prepare_package).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(bottom, text="How training works", width=150, fg_color="#1E3A8A", command=self.show_help).pack(side="right", padx=6, pady=8)
        self.lbl_status = ctk.CTkLabel(bottom, text="", text_color="gray"); self.lbl_status.pack(side="left", padx=20)
        self.refresh_stats()
        if start_file and os.path.exists(start_file):
            self.after(300, lambda: self.load_file(start_file))

    def focus_on(self, path, location, term):
        """Open the picture a scanner result came from, read it, and outline the line holding the term."""
        self.focus_target, self.focus_term = (location, term), term
        self.load_file(path)

    def _apply_focus(self):
        location, term = self.focus_target
        self.focus_target = None
        i = match_source([lbl for lbl, _ in self.sources], location)
        if i is None:
            self.lbl_status.configure(text=f"'{term}' was read from typed text there, not a picture: nothing to check."); return
        self.listbox.selection_clear(0, "end"); self.listbox.selection_set(i); self.listbox.see(i); self.on_source()
        self.after(250, self.select_all)

class TrainerApp(_TrainerUI, ctk.CTk):
    def __init__(self, start_file=None):
        ctk.CTk.__init__(self)
        eng.ACTIVE_ICON = "trainer.ico"
        eng.apply_window_icon(self)
        self.report_callback_exception = lambda et, e, tb: (eng._excepthook(et, e, tb),
            messagebox.showerror("Error", f"{et.__name__}: {e}\n\nDetails saved to logs\\error.log"))
        self._build_ui(start_file)

class TrainerWindow(_TrainerUI, ctk.CTkToplevel):
    def __init__(self, scanner, start_file=None, focus=None):
        ctk.CTkToplevel.__init__(self, scanner)
        self.scanner = scanner
        self._build_ui(start_file, focus)
        self.after(150, self.lift)

    # ---------- files and pages ----------
    def open_file(self):
        path = filedialog.askopenfilename(parent=self, title="Open a document or image", filetypes=OPEN_TYPES)
        if path:
            self.focus_target = self.focus_term = None
            self.load_file(path)

    def load_file(self, path):
        try:
            self.sources = list_sources(path)
        except Exception as e:
            eng.log_error(f"Trainer could not open {path}")
            messagebox.showerror("Cannot open", f"{type(e).__name__}: {e}"); return
        self.listbox.delete(0, "end")
        for label, _loader in self.sources:
            inner = label.split(" (", 1)[-1].rstrip(")")
            self.listbox.insert("end", os.path.basename(path) if inner == "Image" else inner)
        if not self.sources:
            self.lbl_status.configure(text="No pages or embedded pictures found in that file."); return
        if self.focus_target:
            self._apply_focus(); return
        self.listbox.selection_set(0); self.on_source()

    def on_source(self, _e=None):
        sel = self.listbox.curselection()
        if not sel: return
        label, loader = self.sources[sel[0]]
        try:
            self.img = loader()
        except Exception as e:
            eng.log_error(f"Trainer could not load {label}")
            messagebox.showerror("Cannot show", f"This picture could not be opened (for example EMF/SVG).\n\n{type(e).__name__}: {e}"); return
        self.source_label = label
        self.region = None; self.clear_lines(); self.fit()
        self.lbl_status.configure(text=f"{label}  |  {self.img.width} x {self.img.height} px")

    # ---------- viewing ----------
    def fit(self):
        if self.img is None: return
        cw, ch = max(200, self.canvas.winfo_width()), max(200, self.canvas.winfo_height())
        self.set_zoom(min(cw / self.img.width, ch / self.img.height, 1.0))

    def set_zoom(self, z):
        if self.img is None: return
        max_z = (40_000_000 / (self.img.width * self.img.height)) ** 0.5   # keep the on-screen copy reasonable
        self.zoom = max(0.05, min(z, 3.0, max_z))
        w, h = max(1, int(self.img.width * self.zoom)), max(1, int(self.img.height * self.zoom))
        self.tk_img = ImageTk.PhotoImage(self.img.resize((w, h), Image.LANCZOS if self.zoom < 1 else Image.NEAREST))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, w, h))
        self.lbl_zoom.configure(text=f"{self.zoom * 100:.0f}%")
        if self.region:
            self.draw_region(); self.draw_line_boxes()

    def draw_region(self):
        x0, y0, x1, y1 = (v * self.zoom for v in self.region)
        self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="#22D3EE", width=2, dash=(4, 2))

    def draw_line_boxes(self):
        self.canvas.delete("linebox")
        if not self.region: return
        rx, ry = self.region[0], self.region[1]
        for row in self.line_rows:
            (x0, y0, x1, y1), conf = row["box"], row["conf"]
            choice = row["choice"].get() if "choice" in row else "Skip"
            color = "#9CA3AF" if choice == "Not text" else ("#22C55E" if conf >= eng.ocr_cutoff() else "#EF4444")
            dash = (3, 3) if choice == "Not text" else None
            X0, Y0 = (rx + x0) * self.zoom, (ry + y0) * self.zoom
            self.canvas.create_rectangle(X0, Y0, (rx + x1) * self.zoom, (ry + y1) * self.zoom,
                                         outline=color, width=2, dash=dash, tags="linebox")
            self.canvas.create_text(X0 + 2, Y0 - 2, text=str(row["n"]), anchor="sw", fill=color,
                                    font=("Segoe UI", 10, "bold"), tags="linebox")
            if self.focus_term and eng.fold(self.focus_term) in eng.fold(row["text"]):
                self.canvas.create_rectangle(X0 - 5, Y0 - 5, (rx + x1) * self.zoom + 5, (ry + y1) * self.zoom + 5,
                                             outline="#FACC15", width=3, tags="linebox")

    # ---------- selecting a region ----------
    def on_press(self, e):
        if self.img is None: return
        self.drag_start = (self.canvas.canvasx(e.x), self.canvas.canvasy(e.y))
        if self.rect_id: self.canvas.delete(self.rect_id)
        self.canvas.delete("linebox")
        self.rect_id = self.canvas.create_rectangle(*self.drag_start, *self.drag_start, outline="#22D3EE", width=2, dash=(4, 2))

    def on_drag(self, e):
        if self.drag_start:
            self.canvas.coords(self.rect_id, *self.drag_start, self.canvas.canvasx(e.x), self.canvas.canvasy(e.y))

    def on_release(self, e):
        if not self.drag_start: return
        x0, y0 = self.drag_start; x1, y1 = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y); self.drag_start = None
        box = [min(x0, x1) / self.zoom, min(y0, y1) / self.zoom, max(x0, x1) / self.zoom, max(y0, y1) / self.zoom]
        box = [max(0, box[0]), max(0, box[1]), min(self.img.width, box[2]), min(self.img.height, box[3])]
        if box[2] - box[0] < 6 or box[3] - box[1] < 6:
            return
        self.run_region(tuple(box))

    def select_all(self):
        if self.img is not None:
            if self.rect_id: self.canvas.delete(self.rect_id)
            self.region = (0, 0, self.img.width, self.img.height); self.draw_region(); self.run_region(self.region)

    def run_region(self, box):
        self.region = box
        self.region_img = self.img.crop(tuple(int(v) for v in box))
        self.clear_lines()
        self.lbl_status.configure(text="Reading the box...")
        crop = self.region_img
        def work():
            try:
                lines = read_region_lines(crop); one = read_region_as_one_line(crop)
                self.after(0, lambda: self.show_lines(lines, one))
            except Exception as err:
                eng.log_error("Trainer region OCR failed")
                msg = f"{type(err).__name__}: {err}"
                self.after(0, lambda: self.lbl_status.configure(text=f"OCR failed: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    # ---------- results panel ----------
    def clear_lines(self):
        for w in self.lines_frame.winfo_children():
            w.destroy()
        self.line_rows = []
        self.lbl_one.configure(text="Read as one line: -"); self.entry_one.delete(0, "end")
        self.canvas.delete("linebox")

    def show_lines(self, lines, one):
        cutoff = eng.ocr_cutoff()
        ignored = eng.load_ocr_ignore()
        for n, (box, text, conf) in enumerate(lines, start=1):
            kept = conf >= cutoff
            on_list = eng.fold(text).strip() in ignored
            fr = ctk.CTkFrame(self.lines_frame); fr.pack(fill="x", padx=2, pady=3)
            col = ctk.CTkFrame(fr, fg_color="transparent"); col.pack(fill="x", expand=True, padx=4, pady=2)
            note = "already on the ignore list" if on_list else ("scanner keeps this" if kept else "scanner ignores this")
            ctk.CTkLabel(col, text=f"{n}.  OCR read: {text}   ({conf:.2f}, {note})", anchor="w",
                         text_color=("#6B7280" if on_list else "#15803D" if kept else "#DC2626")).pack(fill="x")
            ent = ctk.CTkEntry(col); ent.insert(0, text); ent.pack(fill="x", pady=(0, 2))
            choice = tk.StringVar(value="Skip")
            seg = ctk.CTkSegmentedButton(col, values=list(CHOICES), variable=choice,
                                         command=lambda _v: self.draw_line_boxes())
            seg.pack(fill="x", pady=(0, 2))
            ent.bind("<KeyRelease>", lambda _e, c=choice: (c.set("Save as text"), self.draw_line_boxes()))
            self.line_rows.append({"n": n, "box": box, "text": text, "conf": conf, "choice": choice, "entry": ent})
        if not lines:
            ctk.CTkLabel(self.lines_frame, text="No text lines detected in the box.\nUse 'Whole box as ONE line' below.",
                         text_color="gray", justify="left").pack(anchor="w", padx=6, pady=6)
        text1, conf1 = one
        self.lbl_one.configure(text=f"Read as one line: {text1 or '(nothing)'}   ({conf1:.2f})")
        self.entry_one.delete(0, "end"); self.entry_one.insert(0, text1)
        self.draw_line_boxes()
        msg = f"{len(lines)} line(s) found. Pick Skip, Save as text, or Not text for each, then Save Choices."
        if self.focus_term:
            hits = [str(r["n"]) for r in self.line_rows if eng.fold(self.focus_term) in eng.fold(r["text"])]
            msg = (f"'{self.focus_term}' is line {', '.join(hits)} (yellow outline). " if hits else
                   f"'{self.focus_term}' was not read in this picture now. Drag a box around it to check. ") + msg
        self.lbl_status.configure(text=msg)

    # ---------- saving ----------
    def save_choices(self):
        if self.region_img is None or not self.line_rows:
            messagebox.showinfo("Nothing to save", "Draw a box around text first."); return
        text_rows = [r for r in self.line_rows if r["choice"].get() == "Save as text" and r["entry"].get().strip()]
        junk = [r for r in self.line_rows if r["choice"].get() == "Not text"]
        if not text_rows and not junk:
            messagebox.showinfo("Nothing chosen", "Pick 'Save as text' or 'Not text' for at least one line."); return
        rx, ry = self.region[0], self.region[1]
        images = []
        for r in text_rows:   # recognition samples: one tight line each
            x0, y0, x1, y1 = r["box"]; m = 3
            crop = self.region_img.crop((int(max(0, x0 - m)), int(max(0, y0 - m)),
                                         int(min(self.region_img.width, x1 + m)), int(min(self.region_img.height, y1 + m))))
            images.append(save_sample(crop, r["entry"].get(), r["text"], r["conf"], self.source_label,
                                      (rx + x0, ry + y0, rx + x1, ry + y1)))
        unsure = [r["box"] for r in self.line_rows if r["choice"].get() == "Skip"]
        images.append(save_region(self.region_img, [(r["box"], r["entry"].get()) for r in text_rows], unsure,
                                  [(r["box"], r["text"], r["conf"]) for r in junk], self.source_label, self.region))
        # Not text + the scanner keeps it today -> ignore that exact reading in pictures from now on
        cutoff = eng.ocr_cutoff()
        rows = eng.read_ocr_ignore_rows(); have = {eng.fold(x[0]).strip() for x in rows}
        added = []
        for r in junk:
            key = eng.fold(r["text"]).strip()
            if r["conf"] >= cutoff and key and key not in have:
                rows.append([r["text"].strip(), f"Not text, Trainer {_now()}, {self.source_label}"]); have.add(key)
                added.append(r["text"].strip())
        if added:
            eng.write_ocr_ignore_rows(rows)
        summary = f"{len(text_rows)} text line(s), {len(junk)} not-text line(s)"
        _log_save({"time": _now(), "images": images, "ignored": added, "summary": summary})
        for r in self.line_rows:
            r["choice"].set("Skip")
        self.draw_line_boxes()
        msg = f"Saved {summary}."
        if added:
            msg += " Scanner now ignores: " + ", ".join(added)
        self.refresh_stats(msg)

    def save_whole(self):
        text = self.entry_one.get().strip()
        if self.region_img is None or not text:
            messagebox.showinfo("Missing", "Draw a box and type the correct text first."); return
        read = self.lbl_one.cget("text").replace("Read as one line: ", "").rsplit("   (", 1)
        rel = save_sample(tighten(self.region_img), text, read[0], float(read[1].rstrip(")")) if len(read) > 1 else 0.0,
                          self.source_label, self.region)
        _log_save({"time": _now(), "images": [rel], "ignored": [], "summary": f"whole box '{text}'"})
        self.refresh_stats("Saved the whole box as one sample.")

    def add_fixes(self):
        pairs = []
        for r in self.line_rows:
            pairs += fixes_from_correction(r["text"], r["entry"].get())
        one_read = self.lbl_one.cget("text").replace("Read as one line: ", "").rsplit("   (", 1)[0]
        if one_read and one_read != "(nothing)":
            pairs += fixes_from_correction(one_read, self.entry_one.get())
        pairs = list(dict.fromkeys(pairs))
        if not pairs:
            messagebox.showinfo("No fixes", "No single-word corrections found. Change a word in a line, then try again."); return
        rows = eng.read_ocr_fix_rows()
        existing = {r[0] for r in rows}
        added = [(a, b) for a, b in pairs if a not in existing]
        rows += [[a, b, "Added in Trainer"] for a, b in added]
        eng.write_ocr_fix_rows(rows)
        self.refresh_stats("Added OCR fixes: " + ", ".join(f"{a} > {b}" for a, b in added) if added else "Those fixes already exist.")

    def undo_sample(self):
        what = remove_last_save()
        self.refresh_stats(f"Removed: {what}" if what else "Nothing to undo.")

    def open_ignore_list(self):
        if not os.path.exists(eng.OCR_IGNORE_FILE):
            eng.write_ocr_ignore_rows([])
        os.startfile(eng.OCR_IGNORE_FILE)

    def prepare_package(self):
        try:
            report = build_training_package()
        except Exception as e:
            eng.log_error("Prepare Training Package failed")
            messagebox.showerror("Package failed", f"{type(e).__name__}: {e}"); return
        messagebox.showinfo("Training package", report + "\n\nNext: follow TRAINING_GUIDE.md section 8 (or click 'How training works').")
        self.refresh_stats("Training package prepared.")

    def train_reader(self):
        """Fine-tune Tesseract on the saved text lines, in a background thread, then offer to install the model."""
        import tess_train
        n = len(tess_train.read_samples(TRAIN_DIR))
        if n < tess_train.MIN_SAMPLES:
            messagebox.showinfo("Not enough samples", f"{n} text-line samples saved. Training needs at least "
                                f"{tess_train.MIN_SAMPLES} (300+ for a dependable gain). Keep using 'Save as text'."); return
        if not messagebox.askyesno("Train the reader", f"Train on {n} saved text lines? This runs on this PC's processor "
                                   "(no GPU, no internet) and usually takes a few minutes. You can keep the Trainer open."):
            return
        out_dir = os.path.join(TRAIN_DIR, "model")
        self.btn_train.configure(state="disabled", text="Training...")
        def work():
            try:
                r = tess_train.train(eng.TESS_DIR, TRAIN_DIR, out_dir,
                                     progress=lambda m: self.after(0, lambda: self.refresh_stats(m)),
                                     runner=lambda cmd, timeout=600: eng.run_tesseract_tool(cmd, b"", timeout, write_dirs=[out_dir]))
                self.after(0, lambda: self._train_done(r, out_dir))
            except Exception as e:
                eng.log_error("Train Reader failed")
                msg = f"{e}"
                self.after(0, lambda: (messagebox.showerror("Training failed", msg),
                                       self.btn_train.configure(state="normal", text="Improve Reading")))
        threading.Thread(target=work, daemon=True).start()

    def _train_done(self, r, out_dir):
        import tess_train
        self.btn_train.configure(state="normal", text="Improve Reading")
        text = tess_train.describe(r)
        self.refresh_stats("Training finished. " + text.splitlines()[0])
        b, a = r["char_error_before_pct"], r["char_error_after_pct"]
        worse = a is not None and b is not None and a > b
        if worse:
            messagebox.showwarning("Training finished", text + f"\n\nNot installed. The model is in {out_dir}."); return
        if messagebox.askyesno("Training finished", text + "\n\nInstall it in the scanner now?\n"
                               "(Scanner > Knowledge > Undo Last Knowledge Change puts the previous model back.)"):
            eng.load_trained_models(out_dir)
            messagebox.showinfo("Installed", "The scanner now reads pictures with your trained model "
                                "(config\\models\\acronym.traineddata). Rescan to see the effect.")

    def show_help(self):
        if getattr(self, "help_win", None) is not None and self.help_win.winfo_exists():
            self.help_win.focus(); return
        win = ctk.CTkToplevel(self); self.help_win = win
        win.title("How training works"); win.geometry("720x620"); win.transient(self); win.after(100, win.lift)
        box = ctk.CTkTextbox(win, wrap="word", font=("Segoe UI", 13)); box.pack(fill="both", expand=True, padx=12, pady=12)
        help_text = HELP_TEXT.split("HOW YOUR SAMPLES MAKE THE SCANNER BETTER")[0] + HELP_TEXT_TESSERACT \
            if eng.OCR_BACKEND == "tesseract" else HELP_TEXT
        box.insert("1.0", help_text); box.configure(state="disabled")

    def open_folder(self):
        os.makedirs(TRAIN_DIR, exist_ok=True)
        os.startfile(TRAIN_DIR)

    def refresh_stats(self, msg=None):
        n, regions, junk, size = training_stats()
        self.lbl_stats.configure(text=f"Text lines: {n}  |  Regions: {regions}  |  Not-text examples: {junk}  |  {size / 1024 / 1024:.1f} MB")
        if msg:
            self.lbl_status.configure(text=msg)

if __name__ == "__main__":
    import sys
    try:
        TrainerApp(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
    except Exception:
        eng.log_error("Trainer failed to start")
        raise
