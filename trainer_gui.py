"""Acronym Hunter Trainer: region rescans (C) and OCR training-sample capture (D).

Ships in the same folder as AcronymHunter.exe and shares its engine (_internal), its config\\
folder, its network guard, and its sandbox. Importing app_gui runs that setup before anything else.
"""
import app_gui as eng          # sandbox + temp redirect + network guard + OCR engine + config (must be first)
import os, io, csv, re, zipfile, posixpath, hashlib, threading, datetime
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
OPEN_TYPES = [("Documents and images", "*.pdf *.pptx *.docx *.xlsx *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif")]
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
    doc = eng.fitz.open(path)
    try:
        pix = doc[index].get_pixmap(dpi=int(eng.OCR_CFG["pdf_scan_dpi"]), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()

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

def list_sources(path):
    name, ext = os.path.basename(path), os.path.splitext(path)[1].lower()
    if ext in eng.IMAGE_EXTS:
        return [(f"{name} (Image)", lambda: _img_from_bytes(open(path, "rb").read()))]
    if ext == ".pdf":
        doc = eng.fitz.open(path); n = len(doc); doc.close()
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
                if posixpath.splitext(target)[1].lower() not in eng.IMAGE_EXTS or (where, target) in seen:
                    continue
                seen.add((where, target))
                shape = eng.shape_name(blip)
                shown = f"'{shape}' " if shape else ""
                out.append((f"{name} ({where}, image {shown}{posixpath.basename(target)})",
                            (lambda t=target: _img_from_bytes(_zip_read(path, t)))))
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

def save_sample(pil_img, text, ocr_text, conf, source, box):
    os.makedirs(IMG_DIR, exist_ok=True)
    buf = io.BytesIO(); pil_img.save(buf, "PNG"); data = buf.getvalue()
    sid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + hashlib.sha1(data).hexdigest()[:8]
    fname = f"{sid}.png"
    with open(os.path.join(IMG_DIR, fname), "wb") as f:
        f.write(data)
    with open(LABELS_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"images/{fname}\t{_clean_text(text)}\n")
    new = not os.path.exists(META_FILE)
    with open(META_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Date", "Image", "Text", "OCR read", "Confidence", "Source", "Box (x0,y0,x1,y1)"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), f"images/{fname}", _clean_text(text),
                    _clean_text(ocr_text), f"{conf:.2f}", source, ",".join(str(int(v)) for v in box)])
    return fname

def remove_last_sample():
    if not os.path.exists(LABELS_FILE):
        return None
    lines = [l for l in open(LABELS_FILE, encoding="utf-8").read().splitlines() if l.strip()]
    if not lines:
        return None
    last = lines.pop()
    tmp = LABELS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(l + "\n" for l in lines))
    os.replace(tmp, LABELS_FILE)
    img_rel, text = (last.split("\t", 1) + [""])[:2]
    try:
        os.remove(os.path.join(TRAIN_DIR, img_rel.replace("/", os.sep)))
    except OSError:
        pass
    if os.path.exists(META_FILE):
        rows = list(csv.reader(open(META_FILE, encoding="utf-8", newline="")))
        rows = [r for r in rows if not (len(r) > 1 and r[1] == img_rel)]
        with open(META_FILE + ".tmp", "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
        os.replace(META_FILE + ".tmp", META_FILE)
    return text

def training_stats():
    count = 0
    if os.path.exists(LABELS_FILE):
        count = sum(1 for l in open(LABELS_FILE, encoding="utf-8") if l.strip())
    size = 0
    for root, _d, files in os.walk(TRAIN_DIR):
        size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    return count, size

def fixes_from_correction(ocr_text, corrected):
    """Word pairs that differ between what OCR read and the corrected text (same word count only)."""
    strip = lambda w: re.sub(r"^[^\w&/]+|[^\w&/.]+$", "", w)
    a, b = ocr_text.split(), corrected.split()
    if len(a) != len(b):
        return []
    return [(strip(x), strip(y)) for x, y in zip(a, b) if strip(x) and strip(y) and strip(x) != strip(y)]

# --------------------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------------------
class TrainerApp(ctk.CTk):
    def __init__(self, start_file=None):
        super().__init__()
        self.title("Acronym Hunter Trainer - region rescan and training samples")
        self.geometry("1300x800"); self.minsize(1000, 560)
        ctk.set_appearance_mode("System")
        self.report_callback_exception = lambda et, e, tb: (eng._excepthook(et, e, tb),
            messagebox.showerror("Error", f"{et.__name__}: {e}\n\nDetails saved to logs\\error.log"))
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
        ctk.CTkLabel(right, text="Correct any line, tick it, and save it as a training sample.\nRed = below the scanner's confidence cutoff (dropped in scans).",
                     justify="left", text_color="gray").grid(row=1, column=0, sticky="w", padx=10)
        self.lines_frame = ctk.CTkScrollableFrame(right); self.lines_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)

        one = ctk.CTkFrame(right); one.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(one, text="Whole box as ONE line (use when OCR found nothing or split it):", justify="left").pack(anchor="w", padx=6, pady=(6, 2))
        self.lbl_one = ctk.CTkLabel(one, text="Read as one line: -", text_color="gray"); self.lbl_one.pack(anchor="w", padx=6)
        self.entry_one = ctk.CTkEntry(one, placeholder_text="Correct text for the whole box"); self.entry_one.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(one, text="Save Whole Box as One Sample", command=self.save_whole).pack(fill="x", padx=6, pady=(0, 8))

        acts = ctk.CTkFrame(right); acts.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 8))
        ctk.CTkButton(acts, text="Save Ticked Lines as Samples", command=self.save_ticked).pack(fill="x", padx=6, pady=(8, 4))
        ctk.CTkButton(acts, text="Add OCR Fixes from Corrections", fg_color="#7C3AED", command=self.add_fixes).pack(fill="x", padx=6, pady=(0, 8))

        bottom = ctk.CTkFrame(self); bottom.pack(side="bottom", fill="x", padx=12, pady=(4, 12), before=body)  # never pushed off-screen
        self.lbl_stats = ctk.CTkLabel(bottom, text=""); self.lbl_stats.pack(side="left", padx=10, pady=8)
        ctk.CTkButton(bottom, text="Remove Last Sample", width=150, fg_color="#DC2626", command=self.undo_sample).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(bottom, text="Open Training Folder", width=160, fg_color="#475569", command=self.open_folder).pack(side="right", padx=6, pady=8)
        self.lbl_status = ctk.CTkLabel(bottom, text="", text_color="gray"); self.lbl_status.pack(side="left", padx=20)
        self.refresh_stats()
        if start_file and os.path.exists(start_file):
            self.after(300, lambda: self.load_file(start_file))

    # ---------- files and pages ----------
    def open_file(self):
        path = filedialog.askopenfilename(title="Open a document or image", filetypes=OPEN_TYPES)
        if path:
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
            color = "#22C55E" if conf >= float(eng.OCR_CFG["min_confidence"]) else "#F97316"
            self.canvas.create_rectangle((rx + x0) * self.zoom, (ry + y0) * self.zoom, (rx + x1) * self.zoom,
                                         (ry + y1) * self.zoom, outline=color, width=2, tags="linebox")

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
        cutoff = float(eng.OCR_CFG["min_confidence"])
        for (box, text, conf) in lines:
            fr = ctk.CTkFrame(self.lines_frame); fr.pack(fill="x", padx=2, pady=3)
            var = tk.BooleanVar(value=False)
            ctk.CTkCheckBox(fr, text="", variable=var, width=24).pack(side="left", padx=(4, 0))
            col = ctk.CTkFrame(fr, fg_color="transparent"); col.pack(side="left", fill="x", expand=True, padx=4, pady=2)
            ctk.CTkLabel(col, text=f"OCR read: {text}   ({conf:.2f})", anchor="w",
                         text_color=("#15803D" if conf >= cutoff else "#DC2626")).pack(fill="x")
            ent = ctk.CTkEntry(col); ent.insert(0, text); ent.pack(fill="x", pady=(0, 2))
            ent.bind("<KeyRelease>", lambda _e, v=var: v.set(True))
            self.line_rows.append({"box": box, "text": text, "conf": conf, "var": var, "entry": ent})
        if not lines:
            ctk.CTkLabel(self.lines_frame, text="No text lines detected in the box.\nUse 'Whole box as ONE line' below.",
                         text_color="gray", justify="left").pack(anchor="w", padx=6, pady=6)
        text1, conf1 = one
        self.lbl_one.configure(text=f"Read as one line: {text1 or '(nothing)'}   ({conf1:.2f})")
        self.entry_one.delete(0, "end"); self.entry_one.insert(0, text1)
        self.draw_line_boxes()
        self.lbl_status.configure(text=f"{len(lines)} line(s) found. Correct, tick, and save.")

    # ---------- saving ----------
    def save_ticked(self):
        rows = [r for r in self.line_rows if r["var"].get() and r["entry"].get().strip()]
        if not rows:
            messagebox.showinfo("Nothing ticked", "Tick the lines to save (editing a line ticks it automatically)."); return
        rx, ry = self.region[0], self.region[1]
        for r in rows:
            x0, y0, x1, y1 = r["box"]
            m = 3
            crop = self.region_img.crop((int(max(0, x0 - m)), int(max(0, y0 - m)),
                                         int(min(self.region_img.width, x1 + m)), int(min(self.region_img.height, y1 + m))))
            save_sample(crop, r["entry"].get(), r["text"], r["conf"], self.source_label,
                        (rx + x0, ry + y0, rx + x1, ry + y1))
            r["var"].set(False)
        self.refresh_stats(f"Saved {len(rows)} sample(s).")

    def save_whole(self):
        text = self.entry_one.get().strip()
        if self.region_img is None or not text:
            messagebox.showinfo("Missing", "Draw a box and type the correct text first."); return
        read = self.lbl_one.cget("text").replace("Read as one line: ", "").rsplit("   (", 1)
        save_sample(tighten(self.region_img), text, read[0], float(read[1].rstrip(")")) if len(read) > 1 else 0.0,
                    self.source_label, self.region)
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
        text = remove_last_sample()
        self.refresh_stats(f"Removed last sample: {text}" if text is not None else "No samples to remove.")

    def open_folder(self):
        os.makedirs(TRAIN_DIR, exist_ok=True)
        os.startfile(TRAIN_DIR)

    def refresh_stats(self, msg=None):
        n, size = training_stats()
        self.lbl_stats.configure(text=f"Training samples: {n}   |   {size / 1024 / 1024:.1f} MB in training_data\\")
        if msg:
            self.lbl_status.configure(text=msg)

if __name__ == "__main__":
    import sys
    try:
        TrainerApp(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
    except Exception:
        eng.log_error("Trainer failed to start")
        raise
