import os
import sys
import shutil
import atexit

# ==============================================================================
# 1. ZERO-FOOTPRINT FOLDER SANDBOX & OFFLINE NETWORK KILL-SWITCH
#    (Must execute BEFORE importing OCR, OpenCV, or Office libraries)
# ==============================================================================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

SANDBOX_DIR = os.path.join(BASE_DIR, "_local_sandbox")
SANDBOX_TEMP = os.path.join(SANDBOX_DIR, "temp")
try:
    for d in (SANDBOX_DIR, SANDBOX_TEMP):
        os.makedirs(d, exist_ok=True)
except OSError as _e:
    import tkinter as _tk
    from tkinter import messagebox as _mb
    _r = _tk.Tk(); _r.withdraw()
    _mb.showerror("Acronym Hunter cannot start",
                  f"The app cannot write to its own folder:\n{BASE_DIR}\n\n"
                  "Unzip the whole AcronymHunter folder to a location you can write to "
                  "(for example Desktop or Documents), then run AcronymHunter.exe from there.\n\n"
                  f"Details: {_e}")
    sys.exit(1)

# Redirect only temp-file locations into the app folder.
# USERPROFILE / APPDATA / LOCALAPPDATA are deliberately NOT redirected: Windows expands its
# Desktop, Documents and Downloads paths from them, so redirecting breaks the file picker
# ("location is not available"). None of the app's libraries write to those folders.
os.environ["TEMP"] = SANDBOX_TEMP
os.environ["TMP"] = SANDBOX_TEMP
os.environ["TMPDIR"] = SANDBOX_TEMP
os.environ["PYTHONPYCACHEPREFIX"] = os.path.join(SANDBOX_DIR, "pycache")

def cleanup_sandbox():
    if os.path.exists(SANDBOX_TEMP):
        shutil.rmtree(SANDBOX_TEMP, ignore_errors=True)

cleanup_sandbox()                 # clear leftovers from a killed session
os.makedirs(SANDBOX_TEMP, exist_ok=True)   # recreate it: temp files must land here, never elsewhere on disk
atexit.register(cleanup_sandbox)

import traceback
import datetime
LOG_DIR = os.path.join(BASE_DIR, "logs")

def log_error(context, with_traceback=True):
    """Append an error to logs/error.log inside the app folder (windowed exe has no console)."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {context}\n")
            if with_traceback:
                f.write(traceback.format_exc())
    except Exception:
        pass

def _excepthook(exc_type, exc, tb):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Uncaught exception\n")
            f.write("".join(traceback.format_exception(exc_type, exc, tb)))
    except Exception:
        pass
sys.excepthook = _excepthook

import socket
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect
_real_getaddrinfo = socket.getaddrinfo

def _guarded_connect(self, address, *args, **kwargs):
    if isinstance(address, tuple) and address and address[0] not in _LOOPBACK:
        raise OSError("Offline Lockdown Active: outbound network connections are disabled.")
    return _real_connect(self, address, *args, **kwargs)

def _guarded_getaddrinfo(host, *args, **kwargs):
    if host not in (None, "", *_LOOPBACK):
        raise OSError("Offline Lockdown Active: DNS lookups are disabled.")
    return _real_getaddrinfo(host, *args, **kwargs)

socket.socket.connect = _guarded_connect
socket.getaddrinfo = _guarded_getaddrinfo

import urllib.request
def _blocked_network(*args, **kwargs):
    raise RuntimeError("Offline Lockdown Active: Outbound network connections are disabled.")
urllib.request.urlopen = _blocked_network
urllib.request.urlretrieve = _blocked_network

# ==============================================================================
# 2. IMPORTS & BUNDLED ONNX OCR INITIALIZATION
# ==============================================================================
import re
import csv
import json
import io
import codecs
import unicodedata
import tkinter.font as tkfont
import zipfile
import threading
import subprocess
import cv2
import pymupdf as fitz  # Modern PyMuPDF import (no deprecation warnings)
import openpyxl
import numpy as np
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from rapidfuzz import process, fuzz
from rapidocr_onnxruntime import RapidOCR

# ONNX Runtime ships Windows TraceLogging telemetry (routed to the OS diagnostics service).
# Turn it off so the OCR engine emits no usage events at all.
try:
    import onnxruntime as _ort
    _ort.disable_telemetry_events()
except Exception:
    pass

DB_FILE = os.path.join(BASE_DIR, "acronym_database.csv")

# ---- Text encoding: read any common CSV encoding, always write UTF-8 with BOM (Excel-friendly) ----
CSV_WRITE_ENCODING = "utf-8-sig"   # holds every Unicode character; the BOM tells Excel it is UTF-8

def read_csv_rows(path):
    """DictReader rows from a CSV saved as UTF-8 (with or without BOM), UTF-16 (Excel "Unicode Text",
    tab-delimited), or legacy Windows-1252 ("CSV (Comma delimited)" from older Excel)."""
    raw = open(path, "rb").read()
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        text = raw.decode("utf-16")
    elif raw.startswith(codecs.BOM_UTF8):
        text = raw[len(codecs.BOM_UTF8):].decode("utf-8")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")
            log_error(f"{os.path.basename(path)} is not UTF-8; read as Windows-1252. "
                      "Symbols may be wrong: re-save it in Excel as 'CSV UTF-8 (Comma delimited)'.", with_traceback=False)
    header = text.split("\n", 1)[0]
    delimiter = "\t" if header.count("\t") > header.count(",") else ","
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter))

# Look-alike characters that PDFs and Office mix freely; folded so a database term matches either form.
_FOLD = str.maketrans({
    "\u00b5": "\u03bc",   # micro sign -> Greek mu
    "\u2126": "\u03a9",   # ohm sign -> Greek capital omega
    "\u212b": "\u00c5",   # angstrom sign -> A with ring
    "\u212a": "K",        # kelvin sign -> K
    "\u2212": "-", "\u2010": "-", "\u2011": "-", "\u2013": "-",   # minus, hyphens, en dash -> hyphen
    "\u00a0": " ", "\u202f": " ",                                  # non-breaking spaces -> space
    "\ufb01": "fi", "\ufb02": "fl",                                # typographic ligatures
})

def fold(text):
    """Unicode-normalize (NFC) and fold look-alike characters, applied to database terms and document text."""
    return unicodedata.normalize("NFC", text).translate(_FOLD)

# ---- User-tunable accuracy files (config\ folder beside the exe) ----
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OCR_FIXES_FILE = os.path.join(CONFIG_DIR, "ocr_corrections.csv")
OCR_SETTINGS_FILE = os.path.join(CONFIG_DIR, "ocr_settings.json")
MODELS_DIR = os.path.join(CONFIG_DIR, "models")
OCR_DEFAULTS = {
    "min_confidence": 0.5,        # drop OCR lines the engine is less sure of (0-1)
    "pdf_scan_dpi": 300,          # render resolution for scanned PDF pages (300 beat 200 in tools\\evaluate.py)
    "scanned_page_max_chars": 40, # PDF page with fewer digital characters is treated as scanned
    "upscale_below_px": 1200,     # enlarge images narrower than this before OCR
    "upscale_factor": 2.0,
    "contrast_clip": 2.0,         # CLAHE contrast boost; 0 disables
    "denoise_strength": 10,       # 0 disables denoising (faster, better for clean screenshots)
    "detect_side_len": 736,       # text-detection resolution; raise for tiny text
    "detect_box_thresh": 0.5,     # lower finds fainter text boxes (more noise)
    "detect_unclip_ratio": 1.6,   # how far each detected text box is expanded
    "fuzzy_min_score": 80,        # RapidFuzz score (0-100) to accept an OCR near-miss of a DB term
    "tile_large_images": 1,       # 1 = read large images in overlapping tiles so small text is not shrunk away
    "tile_size_px": 1800,         # tile edge; keep under 2000 (the OCR engine shrinks anything larger)
    "tile_overlap_px": 300,       # overlap so words on a tile edge are read whole in the next tile
}
OCR_ENGINE_MAX_SIDE = 2000        # RapidOCR downsizes images whose longest side exceeds this

def load_ocr_settings():
    cfg = dict(OCR_DEFAULTS)
    try:
        with open(OCR_SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
            user = json.load(f)
        for k, v in user.items():
            if k in OCR_DEFAULTS and isinstance(v, (int, float)) and not isinstance(v, bool):
                cfg[k] = v
    except FileNotFoundError:
        pass
    except Exception:
        log_error("config/ocr_settings.json could not be read; using defaults")
    return cfg

OCR_CFG = load_ocr_settings()

def load_ocr_fixes():
    """Misread -> Correct pairs from config/ocr_corrections.csv. Re-read on every scan."""
    fixes = {}
    try:
        for row in read_csv_rows(OCR_FIXES_FILE):
            wrong, right = fold((row.get("Misread") or "").strip()), fold((row.get("Correct") or "").strip())
            if wrong and right and wrong != right:
                fixes[wrong] = right
    except FileNotFoundError:
        pass
    except Exception:
        log_error("config/ocr_corrections.csv could not be read")
    return fixes
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp', '.gif'}
SUPPORTED_EXTS = IMAGE_EXTS | {'.pdf', '.pptx', '.docx', '.xlsx'}

# Create starter unified database if missing
if not os.path.exists(DB_FILE):
    starter_rows = [
        ["Term", "Category", "Definition", "Action"],
        ["SOW", "Acronym", "Statement of Work", "Include"],
        ["RFP", "Acronym", "Request for Proposal", "Include"],
        ["CDR", "Acronym", "Critical Design Review", "Include"],
        ["CDR", "Acronym", "Call Detail Record", "Include"],
        ["LEO", "Acronym", "Low Earth Orbit", "Include"],
        ["LEO", "Acronym", "Law Enforcement Officer", "Include"],
        ["psi", "Unit", "Pounds per square inch", "Include"],
        ["kWh", "Unit", "Kilowatt-hour", "Include"],
        ["approx.", "Abbreviation", "Approximately", "Include"],
        ["w/o", "Abbreviation", "Without", "Include"],
        ["USA", "Acronym", "United States of America", "Exclude"],
        ["CEO", "Acronym", "Chief Executive Officer", "Exclude"],
        ["PDF", "Acronym", "Portable Document Format", "Exclude"],
        ["AM", "Abbreviation", "Ante Meridiem", "Exclude"],
        ["PM", "Abbreviation", "Post Meridiem", "Exclude"],
        ["TBD", "Acronym", "To Be Determined", "Exclude"],
        ["N/A", "Abbreviation", "Not Applicable", "Exclude"],
        ["THE", "Noise", "Common English Stopword", "Exclude"],
        ["AND", "Noise", "Common English Stopword", "Exclude"],
        ["FOR", "Noise", "Common English Stopword", "Exclude"],
        ["WITH", "Noise", "Common English Stopword", "Exclude"],
        ["NOTE", "Noise", "Document Formatting Word", "Exclude"],
        ["PAGE", "Noise", "Document Formatting Word", "Exclude"],
        ["TOTAL", "Noise", "Document Formatting Word", "Exclude"],
        ["TABLE", "Noise", "Document Formatting Word", "Exclude"],
        ["FIGURE", "Noise", "Document Formatting Word", "Exclude"],
        ["SECTION", "Noise", "Document Formatting Word", "Exclude"],
        ["II", "Noise", "Roman Numeral", "Exclude"],
        ["III", "Noise", "Roman Numeral", "Exclude"],
        ["IV", "Noise", "Roman Numeral", "Exclude"],
    ]
    with open(DB_FILE, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        csv.writer(f).writerows(starter_rows)

# RapidOCR loads lazily on first image (uses pre-bundled offline ONNX weights)
_ocr_engine = None
_ocr_lock = threading.Lock()

OCR_MODEL_INFO = "not loaded yet"

def _build_ocr():
    """Bundled PP-OCRv4 models, overridden by any det.onnx / rec.onnx / cls.onnx / rec_keys.txt in config\\models."""
    global OCR_MODEL_INFO
    try:
        return _build_ocr_configured()
    except Exception:
        log_error("Custom OCR configuration failed; falling back to bundled models and default settings")
        OCR_MODEL_INFO = "bundled PP-OCRv4 (custom settings/models failed; see logs\\error.log)"
        return RapidOCR()

def _build_ocr_configured():
    global OCR_MODEL_INFO
    import yaml
    import rapidocr_onnxruntime as _ro
    with open(os.path.join(os.path.dirname(_ro.__file__), "config.yaml"), "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["Global"]["text_score"] = float(OCR_CFG["min_confidence"])
    cfg["Det"]["limit_side_len"] = int(OCR_CFG["detect_side_len"])
    cfg["Det"]["box_thresh"] = float(OCR_CFG["detect_box_thresh"])
    cfg["Det"]["unclip_ratio"] = float(OCR_CFG["detect_unclip_ratio"])
    custom = []
    for part, section in (("det", "Det"), ("cls", "Cls"), ("rec", "Rec")):
        path = os.path.join(MODELS_DIR, f"{part}.onnx")
        if os.path.isfile(path):
            cfg[section]["model_path"] = os.path.abspath(path)
            custom.append(f"{part}.onnx")
    keys = os.path.join(MODELS_DIR, "rec_keys.txt")
    if os.path.isfile(keys):
        cfg["Rec"]["rec_keys_path"] = os.path.abspath(keys)
        custom.append("rec_keys.txt")
    os.makedirs(SANDBOX_TEMP, exist_ok=True)
    cfg_path = os.path.join(SANDBOX_TEMP, "rapidocr_config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    try:
        engine = RapidOCR(config_path=cfg_path)
        OCR_MODEL_INFO = ("custom " + ", ".join(custom)) if custom else "bundled PP-OCRv4"
    except Exception:
        log_error("OCR model from config\\models failed to load; falling back to bundled models")
        engine = RapidOCR()
        OCR_MODEL_INFO = "bundled PP-OCRv4 (custom model failed to load; see logs\\error.log)"
    return engine

def get_ocr():
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            _ocr_engine = _build_ocr()
    return _ocr_engine

# ==============================================================================
# 3. UNIFIED DATABASE LOADER (INCLUDES & EXCLUDES)
# ==============================================================================
def load_database():
    include_db = {}
    exclude_db = {}
    exclude_upper = set()

    if not os.path.exists(DB_FILE):
        return include_db, exclude_db, exclude_upper

    for row in read_csv_rows(DB_FILE):
        term = fold((row.get("Term") or "").strip())
        cat = (row.get("Category") or "Acronym").strip()
        defn = (row.get("Definition") or "").strip()
        action = (row.get("Action") or "Include").strip().capitalize()

        if not term:
            continue

        if action == "Exclude" or cat.lower() in {"exclude", "ignore", "noise"}:
            exclude_db[term] = {"category": cat, "definition": defn or "Excluded by user rule"}
            exclude_upper.add(term.upper())
        else:
            if not defn:
                continue
            if term not in include_db:
                include_db[term] = {"category": cat, "definitions": []}
            if defn not in include_db[term]["definitions"]:
                include_db[term]["definitions"].append(defn)

    return include_db, exclude_db, exclude_upper

# ==============================================================================
# 4. LAYER 2 & 3: OPENCV IMAGE PRE-PROCESSING & ONNX OCR READER
# ==============================================================================
def enhance_image_for_ocr(image_bytes):
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    height, width = img.shape[:2]
    # Ignore tiny 1x1 or icon-sized decorative graphics under 25px
    if width < 25 or height < 15:
        return None
    if width < OCR_CFG["upscale_below_px"] and OCR_CFG["upscale_factor"] > 1:
        f = float(OCR_CFG["upscale_factor"])
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if OCR_CFG["contrast_clip"] > 0:
        gray = cv2.createCLAHE(clipLimit=float(OCR_CFG["contrast_clip"]), tileGridSize=(8, 8)).apply(gray)
    if OCR_CFG["denoise_strength"] > 0:
        gray = cv2.fastNlMeansDenoising(gray, None, h=float(OCR_CFG["denoise_strength"]),
                                        templateWindowSize=7, searchWindowSize=21)
    return gray

# ---------------------------------------------------------------------------
# Shared helpers: OCR cache, skipped-content notes, Office XML parsing
# ---------------------------------------------------------------------------
import hashlib
import posixpath
from lxml import etree as _ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "v": "urn:schemas-microsoft-com:vml",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
}
def _q(prefix, tag):
    return "{%s}%s" % (NS[prefix], tag)

VECTOR_EXTS = {".emf", ".wmf", ".emz", ".wmz", ".svg"}
_OCR_CACHE = {}   # sha1(image bytes) -> text; a logo repeated on 50 slides is OCR'd once
_SKIPPED = []     # (location label, reason) for content that could not be scanned

def note_skip(label, reason):
    if (label, reason) not in _SKIPPED:
        _SKIPPED.append((label, reason))

def _ocr_lines(img, x_off=0, y_off=0):
    """[(x0, y0, x1, y1, text)] for lines at or above min_confidence, in full-image coordinates."""
    result, _ = get_ocr()(img)
    out = []
    for box, text, conf in (result or []):
        if float(conf) < float(OCR_CFG["min_confidence"]) or not str(text).strip():
            continue
        xs = [pt[0] for pt in box]; ys = [pt[1] for pt in box]
        out.append((min(xs) + x_off, min(ys) + y_off, max(xs) + x_off, max(ys) + y_off, str(text)))
    return out

def _tile_starts(length, tile, step):
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile + 1, step))
    if starts[-1] != length - tile:
        starts.append(length - tile)
    return starts

def _ocr_raw(image_bytes):
    clean_img = enhance_image_for_ocr(image_bytes)
    if clean_img is None:
        return ""
    lines = _ocr_lines(clean_img)          # whole-image pass (large text, layout)
    h, w = clean_img.shape[:2]
    tile, over = int(OCR_CFG["tile_size_px"]), int(OCR_CFG["tile_overlap_px"])
    if OCR_CFG["tile_large_images"] and max(h, w) > OCR_ENGINE_MAX_SIDE and 0 <= over < tile:
        # The engine shrank this image; re-read it in full-resolution tiles so small text survives.
        tiled = []
        for y in _tile_starts(h, tile, tile - over):
            for x in _tile_starts(w, tile, tile - over):
                tiled += _ocr_lines(clean_img[y:y + tile, x:x + tile], x, y)
        kept = list(lines)
        for item in sorted(tiled, key=lambda t: -len(t[4])):   # longest reading of a line wins
            cx, cy, txt = (item[0] + item[2]) / 2, (item[1] + item[3]) / 2, item[4]
            duplicate = any(k[0] - 10 <= cx <= k[2] + 10 and k[1] - 10 <= cy <= k[3] + 10
                            and (txt in k[4] or k[4] in txt) for k in kept)
            if not duplicate:
                kept.append(item)
        lines = kept
    lines.sort(key=lambda t: (round(t[1] / 20), t[0]))
    return "\n".join(t[4] for t in lines)

def read_image_bytes(image_bytes):
    key = hashlib.sha1(image_bytes).hexdigest()
    if key not in _OCR_CACHE:
        try:
            _OCR_CACHE[key] = _ocr_raw(image_bytes)
        except Exception as e:
            log_error("OCR failed on one image")
            note_skip("OCR engine", f"OCR failed, so text inside images was not read: {type(e).__name__}: {e}. See logs\\error.log.")
            _OCR_CACHE[key] = ""
    return _OCR_CACHE[key]

# Hardened XML parsing for untrusted Office files: no entity expansion (XXE / "billion laughs"),
# no DTD loading, no network access, no unbounded trees.
_SAFE_XML = _ET.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
MAX_EMBEDDED_IMAGE_BYTES = 100 * 1024 * 1024   # skip absurdly large embedded images (decompression-bomb guard)

def _xml(z, path):
    return _ET.fromstring(z.read(path), parser=_SAFE_XML)

def _in_fallback(el):
    return any(anc.tag == _q("mc", "Fallback") for anc in el.iterancestors())

def zip_rels(z, partpath):
    """rId -> (relationship kind, resolved target path, is_external) for one package part."""
    folder, fname = posixpath.split(partpath)
    relpath = posixpath.join(folder, "_rels", fname + ".rels")
    out = {}
    try:
        root = _xml(z, relpath)
    except KeyError:
        return out
    for rel in root.iter(_q("pr", "Relationship")):
        target, external = rel.get("Target", ""), rel.get("TargetMode") == "External"
        if not external:
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
        out[rel.get("Id")] = (rel.get("Type", "").rsplit("/", 1)[-1], target, external)
    return out

def drawingml_lines(root):
    """Text of every DrawingML paragraph: PowerPoint shapes, tables, groups, SmartArt, charts, Excel shapes."""
    lines = []
    for para in root.iter(_q("a", "p")):
        if _in_fallback(para):
            continue
        text = "".join(t.text or "" for t in para.iter(_q("a", "t")))
        if text.strip():
            lines.append(text)
    return lines

def chart_lines(root):
    lines = drawingml_lines(root)  # titles, axis titles
    for cache in root.iter(_q("c", "strCache")):  # category labels, series names
        lines += [v.text for v in cache.iter(_q("c", "v")) if v.text and v.text.strip()]
    return lines

def word_paragraphs(root):
    """(text, is_heading) per Word paragraph; text-box paragraphs counted once, deleted text ignored."""
    W_P, W_T = _q("w", "p"), _q("w", "t")
    for para in root.iter(W_P):
        if _in_fallback(para):
            continue
        text = "".join(t.text or "" for t in para.iter(W_T) if next(t.iterancestors(W_P), None) is para)
        style = para.find("%s/%s" % (_q("w", "pPr"), _q("w", "pStyle")))
        sval = (style.get(_q("w", "val")) or "") if style is not None else ""
        yield text, sval.lower().startswith(("heading", "title"))

def shape_name(el):
    """Name the user sees in the Selection Pane / Alt Text for the shape holding this picture."""
    for anc in el.iterancestors():
        qn = _ET.QName(anc)
        if qn.localname in ("inline", "anchor") and qn.namespace == NS["wp"]:
            doc_pr = anc.find(_q("wp", "docPr"))
            if doc_pr is not None:
                return doc_pr.get("name") or ""
        if qn.localname == "bg":
            return "Slide background"
        if qn.namespace in (NS["p"], NS["xdr"]) and qn.localname in ("pic", "sp", "graphicFrame", "cxnSp", "grpSp"):
            c_nv = anc.find(".//{*}cNvPr")
            if c_nv is not None:
                return c_nv.get("name") or ""
    return ""

def part_images(z, partpath, root, label_base, chunks, seen, rels=None):
    """OCR every picture referenced by one part (slide, layout, Word body/header, Excel drawing)."""
    rels = rels if rels is not None else zip_rels(z, partpath)
    refs = []
    for blip in root.iter(_q("a", "blip")):
        if not _in_fallback(blip):
            refs.append((blip.get(_q("r", "embed")), blip.get(_q("r", "link")), shape_name(blip)))
    for img in root.iter(_q("v", "imagedata")):  # legacy VML pictures
        if not _in_fallback(img):
            refs.append((img.get(_q("r", "id")), None, img.getparent().get("alt") or ""))
    for rid_embed, rid_link, name in refs:
        shown = f"'{name}' " if name else ""
        if rid_embed and rid_embed in rels and not rels[rid_embed][2]:
            target = rels[rid_embed][1]
            if (label_base, target) in seen:
                continue
            seen.add((label_base, target))
            label = f"{label_base}, image {shown}{posixpath.basename(target)})"
            ext = posixpath.splitext(target)[1].lower()
            if ext in VECTOR_EXTS:
                note_skip(label, "Vector graphic (EMF/WMF/SVG). Text drawn inside it was not scanned.")
                continue
            if ext not in IMAGE_EXTS:
                continue
            try:
                if z.getinfo(target).file_size > MAX_EMBEDDED_IMAGE_BYTES:
                    note_skip(label, "Embedded image is over 100 MB uncompressed; skipped as a safety limit.")
                    continue
                txt = read_image_bytes(z.read(target))
            except KeyError:
                note_skip(label, "Picture is referenced but missing from the file.")
                continue
            if txt.strip():
                chunks.append((label, txt))
        elif rid_link:
            link = rels.get(rid_link, ("", "unknown location", True))[1]
            note_skip(f"{label_base}, image {shown})".replace(" )", ")"),
                      f"Linked picture, not stored in the file (links to {link}). Insert it as an embedded picture to scan it.")

# ---------------------------------------------------------------------------
# Format readers
# ---------------------------------------------------------------------------
def extract_pptx(filepath, filename, status_callback, prefix, chunks):
    with zipfile.ZipFile(filepath) as z:
        names = set(z.namelist())
        pres = _xml(z, "ppt/presentation.xml")
        prels = zip_rels(z, "ppt/presentation.xml")
        slides = [prels[s.get(_q("r", "id"))][1] for s in pres.iter(_q("p", "sldId")) if s.get(_q("r", "id")) in prels]
        seen = set()
        for n, spath in enumerate(slides, start=1):
            status_callback(f"{prefix} - Slide {n}/{len(slides)}...")
            tag = f"Slide {n}"
            try:
                root = _xml(z, spath)
                if root.get("show") == "0":
                    tag += ", hidden"
                lines = drawingml_lines(root)
                if lines:
                    chunks.append((f"{filename} ({tag})", "\n".join(lines)))
                rels = zip_rels(z, spath)
                for kind, target, external in rels.values():
                    if external or target not in names:
                        continue
                    if kind == "notesSlide":
                        sub, extra = "notes", drawingml_lines(_xml(z, target))
                    elif kind == "diagramData":
                        sub, extra = "SmartArt", drawingml_lines(_xml(z, target))
                    elif kind == "chart":
                        sub, extra = "chart", chart_lines(_xml(z, target))
                    else:
                        continue
                    if extra:
                        chunks.append((f"{filename} ({tag} {sub})", "\n".join(extra)))
                part_images(z, spath, root, f"{filename} ({tag}", chunks, seen, rels)
            except Exception as e:
                log_error(f"{filename}: slide {n} could not be fully read")
                note_skip(f"{filename} (Slide {n})", f"Slide could not be fully read: {type(e).__name__}: {e}")
        # Logos and graphics placed on layouts/masters appear on many slides; scan each once.
        for lpath in sorted(names):
            m = re.match(r"ppt/slide(Layout|Master)s/slide(?:Layout|Master)(\d+)\.xml$", lpath)
            if m:
                try:
                    part_images(z, lpath, _xml(z, lpath), f"{filename} (Slide {m.group(1).lower()} {m.group(2)}", chunks, seen)
                except Exception:
                    log_error(f"{filename}: {lpath} could not be read")

def extract_docx(filepath, filename, status_callback, prefix, chunks):
    with zipfile.ZipFile(filepath) as z:
        names = set(z.namelist())
        status_callback(f"{prefix} - Reading Word body...")
        body = _xml(z, "word/document.xml")
        block, start, heading, idx = [], 1, "", 0

        def flush(end):
            if block:
                where = f"section '{heading[:60]}', " if heading else ""
                chunks.append((f"{filename} ({where}para {start}-{end})", "\n".join(block)))

        for text, is_heading in word_paragraphs(body):
            idx += 1
            if is_heading and text.strip():
                flush(idx - 1)
                block, start, heading = [], idx, text.strip()
            if text.strip():
                block.append(text)
            if len(block) >= 25:
                flush(idx)
                block, start = [], idx + 1
        flush(idx)
        seen = set()
        part_images(z, "word/document.xml", body, f"{filename} (Body", chunks, seen)

        status_callback(f"{prefix} - Reading headers, footers, notes, comments...")
        extras = [(p, ("Header " if "header" in p else "Footer ") + re.sub(r"\D", "", p.rsplit("/", 1)[-1]))
                  for p in sorted(names) if re.match(r"word/(header|footer)\d*\.xml$", p)]
        extras += [(p, lbl) for p, lbl in (("word/footnotes.xml", "Footnotes"), ("word/endnotes.xml", "Endnotes"),
                                           ("word/comments.xml", "Comments")) if p in names]
        for path, label in extras:
            try:
                root = _xml(z, path)
                lines = [t for t, _h in word_paragraphs(root) if t.strip()]
                if lines:
                    chunks.append((f"{filename} ({label.strip()})", "\n".join(lines)))
                part_images(z, path, root, f"{filename} ({label.strip()}", chunks, seen)
            except Exception as e:
                log_error(f"{filename}: {path} could not be read")
                note_skip(f"{filename} ({label})", f"Could not be read: {type(e).__name__}: {e}")

def extract_xlsx(filepath, filename, status_callback, prefix, chunks):
    status_callback(f"{prefix} - Reading Excel cells...")
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    try:
        for sname in wb.sheetnames:
            cells = []
            for row in wb[sname].iter_rows(values_only=True):
                for val in row:
                    if val is not None and not isinstance(val, (int, float)):
                        s = str(val).strip()
                        if s:
                            cells.append(s)
            if cells:
                chunks.append((f"{filename} ({sname})", "\n".join(cells)))
    finally:
        wb.close()

    status_callback(f"{prefix} - Reading shapes, charts, images, comments...")
    with zipfile.ZipFile(filepath) as z:
        names = set(z.namelist())
        wbx, wrels = _xml(z, "xl/workbook.xml"), zip_rels(z, "xl/workbook.xml")
        sheets = [(wrels[s.get(_q("r", "id"))][1], s.get("name")) for s in wbx.iter(_q("ss", "sheet")) if s.get(_q("r", "id")) in wrels]
        seen = set()
        for spath, sname in sheets:
            for kind, target, external in zip_rels(z, spath).values():
                if external or target not in names:
                    continue
                try:
                    if kind == "drawing":
                        droot = _xml(z, target)
                        lines = drawingml_lines(droot)
                        if lines:
                            chunks.append((f"{filename} ({sname} shapes)", "\n".join(lines)))
                        drels = zip_rels(z, target)
                        for dkind, dtarget, dext in drels.values():
                            if dkind == "chart" and not dext and dtarget in names:
                                clines = chart_lines(_xml(z, dtarget))
                                if clines:
                                    chunks.append((f"{filename} ({sname} chart)", "\n".join(clines)))
                        part_images(z, target, droot, f"{filename} ({sname}", chunks, seen, drels)
                    elif kind == "comments":
                        croot = _xml(z, target)
                        lines = ["".join(t.text or "" for t in c.iter(_q("ss", "t"))) for c in croot.iter(_q("ss", "comment"))]
                        lines = [l for l in lines if l.strip()]
                        if lines:
                            chunks.append((f"{filename} ({sname} comments)", "\n".join(lines)))
                except Exception as e:
                    log_error(f"{filename}: {target} could not be read")
                    note_skip(f"{filename} ({sname})", f"{kind} could not be read: {type(e).__name__}: {e}")

def extract_pdf(filepath, filename, status_callback, prefix, chunks):
    doc = fitz.open(filepath)
    try:
        total_pages = len(doc)
        seen_xrefs = set()
        for i in range(total_pages):
            pnum = i + 1
            if pnum == 1 or pnum % 5 == 0 or pnum == total_pages:
                status_callback(f"{prefix} - PDF page {pnum}/{total_pages}...")
            try:
                page = doc[i]
                digital_text = page.get_text()
                parts = [digital_text]
                if len(digital_text.strip()) < OCR_CFG["scanned_page_max_chars"]:  # scanned page: OCR it whole
                    parts.append(read_image_bytes(page.get_pixmap(dpi=int(OCR_CFG["pdf_scan_dpi"])).tobytes("png")))
                else:  # digital page: OCR each embedded figure once per document
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        if xref in seen_xrefs:
                            continue
                        seen_xrefs.add(xref)
                        try:
                            base_img = doc.extract_image(xref)
                            if base_img and base_img.get("image"):
                                parts.append(read_image_bytes(base_img["image"]))
                        except Exception:
                            pass
                chunks.append((f"{filename} (p.{pnum})", "\n".join(parts)))
            except Exception as e:
                log_error(f"{filename}: page {pnum} could not be read")
                note_skip(f"{filename} (p.{pnum})", f"Page could not be read: {type(e).__name__}: {e}")
    finally:
        doc.close()

# ==============================================================================
# 5. LAYER 1: ALL-FORMAT UNPACKER
# ==============================================================================
def extract_chunks_from_file(filepath, status_callback, file_idx, total_files):
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    chunks = []
    prefix = f"[{file_idx}/{total_files}] {filename}"
    if ext in IMAGE_EXTS:
        status_callback(f"{prefix} - Running OCR on image...")
        with open(filepath, 'rb') as f:
            chunks.append((f"{filename} (Image)", read_image_bytes(f.read())))
    elif ext == '.pdf':
        extract_pdf(filepath, filename, status_callback, prefix, chunks)
    elif ext == '.pptx':
        extract_pptx(filepath, filename, status_callback, prefix, chunks)
    elif ext == '.docx':
        extract_docx(filepath, filename, status_callback, prefix, chunks)
    elif ext == '.xlsx':
        extract_xlsx(filepath, filename, status_callback, prefix, chunks)
    return chunks

# ==============================================================================
# 6. LAYER 4 & 5: 3-GATE ENGINE (EXCLUSIONS, DB DISAMBIGUATION, & DISCOVERY)
# ==============================================================================
NON_UNIT_WORDS = {
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "days", "weeks", "months", "years", "hours", "minutes", "seconds", "items", "pages",
    "slides", "steps", "percent", "people", "users", "files", "lines", "rows", "times",
    "and", "or", "to", "of", "in", "on", "at", "for", "with", "by", "from", "is", "was"
}

OCR_CONFUSIONS = "0158|$"
OCR_MAP = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "|": "I", "$": "S"})

def record_file_error(findings, filepath, exc):
    key = f"⛔ {os.path.basename(filepath)}"
    findings[key] = {
        "category": "File Error", "count": 1, "locations": [filepath],
        "definitions": [], "in_db": True, "excluded": False, "file_error": True,
        "selected_definition": f"{type(exc).__name__}: {exc}"[:300], "status": "⛔ Could not read file"
    }

def record_skip(findings, label, reason):
    key = f"⛔ {label}"
    if key not in findings:
        findings[key] = {
            "category": "Not Scanned", "count": 1, "locations": [label],
            "definitions": [], "in_db": True, "excluded": False, "file_error": True,
            "selected_definition": reason, "status": "⛔ Not scanned"
        }

def analyze_batch(filepaths, status_callback):
    include_db, exclude_db, exclude_upper = load_database()
    ocr_fixes = load_ocr_fixes()
    all_terms = set(include_db.keys()) | set(exclude_db.keys())

    direct_pattern = None
    if all_terms:
        sorted_terms = sorted(all_terms, key=len, reverse=True)
        # (?<![^\W\d_]) = not preceded by a letter; digits may touch a unit (25°C, 10µm, 150psi)
        direct_pattern = re.compile(r'(?<![^\W\d_])(' + '|'.join([re.escape(t) for t in sorted_terms]) + r")(?:'?s)?(?!\w)")

    fuzzy_targets = {t: t for t in include_db.keys() if len(t) >= 3 and t.isupper()}

    unknown_acronym_re = re.compile(r'\b([A-Z][A-Z0-9/&]{1,7}s?)\b')
    unknown_unit_re = re.compile(r'(?<!\w)\d+(?:\.\d+)?\s*([a-zA-Z\u00b0\u03bc\u03a9\u00c5]{1,5}(?:/[a-zA-Z0-9\^]{1,4})?)(?!\w)')
    unknown_abbrev_re = re.compile(r'(?<!\w)([a-zA-Z]{1,4}/[a-zA-Z]{1,4}|[a-zA-Z]{2,6}\.)(?!\w)')

    findings = {}
    total = len(filepaths)
    _OCR_CACHE.clear()

    for idx, filepath in enumerate(filepaths, start=1):
        _SKIPPED.clear()
        try:
            chunks = extract_chunks_from_file(filepath, status_callback, idx, total)
        except Exception as e:
            log_error(f"Could not read {filepath}")
            record_file_error(findings, filepath, e)
            continue
        finally:
            for label, reason in list(_SKIPPED):
                record_skip(findings, label, reason)
        for loc_label, text in chunks:
            if not text.strip():
                continue
            text = fold(text)

            # Gate 1 & 2: Unified Database (Exclusions & Inclusions)
            if direct_pattern:
                for match in direct_pattern.finditer(text):
                    term = match.group(1)
                    if term in exclude_db and term not in include_db:
                        record_excluded(findings, term, loc_label, exclude_db)
                    elif term in include_db:
                        record_included(findings, term, loc_label, include_db)

            # Gate 3: Heuristic Candidate Discovery (Items not in DB)
            for match in unknown_acronym_re.finditer(text):
                raw = match.group(1)
                cand = raw[:-1] if raw.endswith('s') and len(raw) > 2 else raw
                if raw in ocr_fixes or cand in ocr_fixes:
                    wrong = raw if raw in ocr_fixes else cand
                    apply_ocr_fix(findings, wrong, ocr_fixes[wrong], "Acronym (Candidate)", loc_label, include_db, exclude_db)
                    continue
                if cand in include_db or cand in exclude_db or cand.upper() in exclude_upper or cand.isdigit():
                    continue
                if sum(1 for c in cand if c.isupper()) < 2:
                    continue
                if any(ch in OCR_CONFUSIONS for ch in cand):
                    fixed = cand.translate(OCR_MAP)
                    if fixed in include_db:
                        record_included(findings, fixed, f"{loc_label} [OCR fix: {cand}]", include_db)
                        continue
                if any(ch.isdigit() for ch in cand) and fuzzy_targets:
                    best = process.extractOne(cand, fuzzy_targets.keys(), scorer=fuzz.ratio)
                    if best and best[1] >= OCR_CFG["fuzzy_min_score"]:
                        record_included(findings, best[0], f"{loc_label} [OCR fix: {cand}]", include_db)
                        continue
                record_candidate(findings, cand, "Acronym (Candidate)", loc_label)

            for match in unknown_unit_re.finditer(text):
                ucand = match.group(1)
                if ucand in ocr_fixes:
                    apply_ocr_fix(findings, ucand, ocr_fixes[ucand], "Unit (Candidate)", loc_label, include_db, exclude_db)
                    continue
                if (ucand in include_db or ucand in exclude_db or
                        ucand.upper() in exclude_upper or ucand.lower() in NON_UNIT_WORDS or ucand.isdigit()):
                    continue
                record_candidate(findings, ucand, "Unit (Candidate)", loc_label)

            for match in unknown_abbrev_re.finditer(text):
                acand = match.group(1)
                if acand in ocr_fixes:
                    apply_ocr_fix(findings, acand, ocr_fixes[acand], "Abbreviation (Candidate)", loc_label, include_db, exclude_db)
                    continue
                base = acand.rstrip('.')
                if (acand in include_db or acand in exclude_db or base in include_db or base in exclude_db or
                        acand.upper() in exclude_upper or base.upper() in exclude_upper):
                    continue
                if acand.endswith('.') and acand[:-1].lower() in {"end", "out", "see", "all", "one", "two", "now"}:
                    continue
                record_candidate(findings, acand, "Abbreviation (Candidate)", loc_label)

    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

def apply_ocr_fix(findings, wrong, right, cat, loc, include_db, exclude_db):
    tagged = f"{loc} [OCR fix: {wrong}]"
    if right in include_db:
        record_included(findings, right, tagged, include_db)
    elif right in exclude_db:
        record_excluded(findings, right, tagged, exclude_db)
    else:
        record_candidate(findings, right, cat, tagged)

def record_included(findings, term, loc, include_db):
    info = include_db[term]
    defs = info["definitions"]
    multi = len(defs) > 1
    if term not in findings:
        findings[term] = {
            "category": info["category"], "count": 0, "locations": [],
            "definitions": defs, "in_db": True, "excluded": False,
            "selected_definition": (f"⚠️ MULTIPLE ({len(defs)} options) — Choose: " + " OR ".join(defs)) if multi else defs[0],
            "status": "⚠️ CHOOSE DEFINITION" if multi else "✅ Resolved (In DB)"
        }
    findings[term]["count"] += 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

def record_excluded(findings, term, loc, exclude_db):
    info = exclude_db[term]
    if term not in findings:
        findings[term] = {
            "category": info["category"], "count": 0, "locations": [],
            "definitions": [info["definition"]], "in_db": True, "excluded": True,
            "selected_definition": f"[EXCLUDED] {info['definition']}", "status": "🚫 Excluded by DB Rule"
        }
    findings[term]["count"] += 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

def record_candidate(findings, term, cat, loc):
    if term not in findings:
        findings[term] = {
            "category": cat, "count": 0, "locations": [],
            "definitions": [], "in_db": False, "excluded": False,
            "selected_definition": "[Not in Database — Definition omitted]", "status": "🔍 NEW CANDIDATE"
        }
    findings[term]["count"] += 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

def write_db_rows(rows):
    """Atomic rewrite: write a temp file beside the DB, then swap it in (no half-written DB)."""
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        w = csv.writer(f)
        w.writerow(["Term", "Category", "Definition", "Action"])
        w.writerows(rows)
    os.replace(tmp, DB_FILE)

def read_db_rows():
    rows = []
    if os.path.exists(DB_FILE):
        for r in read_csv_rows(DB_FILE):
            rows.append([(r.get("Term") or "").strip(), r.get("Category") or "Acronym",
                         r.get("Definition") or "", r.get("Action") or "Include"])
    return rows

DB_LOCKED_MSG = "A file the app needs is open in another program (usually Excel). Close it and try again."

def read_ocr_fix_rows():
    rows = []
    try:
        for r in read_csv_rows(OCR_FIXES_FILE):
            wrong, right = (r.get("Misread") or "").strip(), (r.get("Correct") or "").strip()
            if wrong or right:
                rows.append([wrong, right, (r.get("Note") or "").strip()])
    except FileNotFoundError:
        pass
    return rows

def write_ocr_fix_rows(rows):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = OCR_FIXES_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        w = csv.writer(f)
        w.writerow(["Misread", "Correct", "Note"])
        w.writerows(rows)
    os.replace(tmp, OCR_FIXES_FILE)

def update_csv_exclusion(term, cat, reason):
    rows = []
    found = False
    if os.path.exists(DB_FILE):
        for r in read_csv_rows(DB_FILE):
            t = (r.get("Term") or "").strip()
            if fold(t) == fold(term):
                r["Action"] = "Exclude"
                found = True
            rows.append([t, r.get("Category") or "Acronym", r.get("Definition") or "", r.get("Action") or "Include"])
    if not found:
        rows.append([term, cat.replace(" (Candidate)", ""), reason, "Exclude"])
    write_db_rows(rows)

# ==============================================================================
# 7. DESKTOP GUI APPLICATION
# ==============================================================================
SETTINGS_FILE = os.path.join(SANDBOX_DIR, "settings.json")
ALL_TYPES = "All types"
STATUS_FILTERS = ["All statuses", "Needs choice", "New candidates", "Resolved", "Errors / not scanned", "Excluded"]
STATUS_ORDER = (("⛔", 0), ("⚠️", 1), ("🔍", 2), ("✅", 3), ("🚫", 4))
COLUMNS = (  # id, heading, base width, anchor
    ("term", "Term / Unit", 120, "w"),
    ("category", "Type", 170, "w"),
    ("count", "Count", 70, "center"),
    ("status", "Status", 210, "w"),
    ("definition", "Definition (from database)", 360, "w"),
    ("locations", "Locations Found", 420, "w"),
)
FONT_MIN, FONT_MAX, FONT_DEFAULT = 9, 28, 13

def base_type(category):
    return category.replace(" (Candidate)", "")

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

class AcronymAppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local Acronym, Abbreviation & Unit Analyzer (100% Portable ONNX Edition)")
        self.geometry("1280x780")
        self.minsize(1000, 560)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.report_callback_exception = self._on_tk_error
        self.queued_files = []
        self.results = {}
        self.selected_term = None
        self.sort_col, self.sort_desc = "count", True
        self.settings = load_settings()
        self.font_size = int(self.settings.get("font_size", FONT_DEFAULT))
        self.font_size = max(FONT_MIN, min(FONT_MAX, self.font_size))

        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=15, pady=(15, 8))

        self.btn_files = ctk.CTkButton(top, text="Select Files", command=self.select_files, width=150, height=36)
        self.btn_files.pack(side="left", padx=5, pady=10)

        self.btn_folder = ctk.CTkButton(top, text="Scan Folder", command=self.select_folder, width=130, height=36)
        self.btn_folder.pack(side="left", padx=5, pady=10)

        self.btn_export = ctk.CTkButton(top, text="Export CSV", command=self.export_csv, state="disabled", fg_color="green", width=130, height=36)
        self.btn_export.pack(side="left", padx=5, pady=10)

        self.show_exc_var = ctk.BooleanVar(value=False)
        self.chk_exc = ctk.CTkCheckBox(top, text="Show Excluded", variable=self.show_exc_var, command=self.populate_table)
        self.chk_exc.pack(side="left", padx=12, pady=10)

        self.btn_db = ctk.CTkButton(top, text="Edit Database CSV", command=lambda: self.open_file(DB_FILE), fg_color="#475569", width=160, height=36)
        self.btn_db.pack(side="right", padx=5, pady=10)

        self.btn_fixes = ctk.CTkButton(top, text="OCR Fixes", command=self.open_fix_manager, fg_color="#7C3AED", width=120, height=36)
        self.btn_fixes.pack(side="right", padx=5, pady=10)

        self.btn_trainer = ctk.CTkButton(top, text="Region Trainer", command=self.open_trainer, fg_color="#0F766E", width=130, height=36)
        self.btn_trainer.pack(side="right", padx=5, pady=10)

        self.status = ctk.CTkLabel(self, text="Ready. 100% Local Sandbox Active (_local_sandbox).", font=("Arial", 13))
        self.status.pack(pady=(0, 4))

        self.prog = ctk.CTkProgressBar(self, width=1140)
        self.prog.pack(padx=15, pady=(0, 10))
        self.prog.set(0)

        # ---- Filter + view bar ----
        fbar = ctk.CTkFrame(self)
        fbar.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(fbar, text="Type:").pack(side="left", padx=(10, 4), pady=8)
        self.type_var = ctk.StringVar(value=ALL_TYPES)
        self.opt_type = ctk.CTkOptionMenu(fbar, variable=self.type_var, values=[ALL_TYPES], width=150,
                                          command=lambda _v: self.populate_table())
        self.opt_type.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(fbar, text="Status:").pack(side="left", padx=(12, 4), pady=8)
        self.status_var = ctk.StringVar(value=STATUS_FILTERS[0])
        self.opt_status = ctk.CTkOptionMenu(fbar, variable=self.status_var, values=STATUS_FILTERS, width=150,
                                            command=lambda _v: self.populate_table())
        self.opt_status.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(fbar, text="Search:").pack(side="left", padx=(12, 4), pady=8)
        self.search_var = ctk.StringVar()
        self.entry_search = ctk.CTkEntry(fbar, textvariable=self.search_var, width=170)
        self.entry_search.pack(side="left", padx=4, pady=8)
        self.search_var.trace_add("write", lambda *_a: self.populate_table())

        ctk.CTkButton(fbar, text="Clear", width=60, fg_color="#64748B",
                      command=self.clear_filters).pack(side="left", padx=(6, 4), pady=8)

        self.btn_bigger = ctk.CTkButton(fbar, text="A+", width=44, command=lambda: self.change_font_size(+1))
        self.btn_bigger.pack(side="right", padx=(4, 10), pady=8)
        self.lbl_size = ctk.CTkLabel(fbar, text="", width=48)
        self.lbl_size.pack(side="right", pady=8)
        self.btn_smaller = ctk.CTkButton(fbar, text="A-", width=44, command=lambda: self.change_font_size(-1))
        self.btn_smaller.pack(side="right", padx=4, pady=8)
        ctk.CTkLabel(fbar, text="Text size:").pack(side="right", padx=(12, 4), pady=8)

        self.lbl_showing = ctk.CTkLabel(fbar, text="", text_color="gray")
        self.lbl_showing.pack(side="right", padx=8, pady=8)

        # ---- Results table ----
        t_frame = ctk.CTkFrame(self)
        t_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        t_frame.grid_rowconfigure(0, weight=1)
        t_frame.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.tree_font = tkfont.Font(family="Segoe UI", size=self.font_size)
        self.head_font = tkfont.Font(family="Segoe UI", size=self.font_size, weight="bold")

        self.tree = ttk.Treeview(t_frame, columns=[c[0] for c in COLUMNS], show="headings", selectmode="browse")
        for cid, label, width, anchor in COLUMNS:
            self.tree.column(cid, width=width, minwidth=50, anchor=anchor, stretch=(cid == "locations"))
        self.update_headings()

        self.tree.tag_configure("ambiguous", background="#FEF3C7", foreground="#92400E")
        self.tree.tag_configure("candidate", background="#E0F2FE", foreground="#075985")
        self.tree.tag_configure("resolved", background="#FFFFFF", foreground="#1E293B")
        self.tree.tag_configure("excluded", background="#F1F5F9", foreground="#94A3B8")
        self.tree.tag_configure("fileerror", background="#FEE2E2", foreground="#991B1B")

        vsb = ttk.Scrollbar(t_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(t_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Text size shortcuts: Ctrl + / Ctrl - / Ctrl 0 / Ctrl + mouse wheel
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.bind_all(seq, lambda _e: self.change_font_size(+1))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.bind_all(seq, lambda _e: self.change_font_size(-1))
        self.bind_all("<Control-0>", lambda _e: self.change_font_size(0, reset=True))
        self.tree.bind("<Control-MouseWheel>", lambda e: self.change_font_size(+1 if e.delta > 0 else -1))
        self.apply_font_size()

        act = ctk.CTkFrame(self)
        act.pack(side="bottom", fill="x", padx=15, pady=(0, 15), before=t_frame)  # never pushed off-screen

        self.lbl_act = ctk.CTkLabel(act, text="Select a row above:", font=("Arial", 12, "bold"))
        self.lbl_act.pack(side="left", padx=10, pady=12)

        self.combo = ctk.CTkComboBox(act, values=["Select a row..."], width=270, state="disabled")
        self.combo.pack(side="left", padx=5, pady=12)

        self.btn_apply = ctk.CTkButton(act, text="Apply Choice", command=self.apply_choice, state="disabled", width=110)
        self.btn_apply.pack(side="left", padx=5, pady=12)

        self.entry_def = ctk.CTkEntry(act, placeholder_text="Definition, or correct term for Fix OCR", width=230, state="disabled")
        self.entry_def.pack(side="left", padx=5, pady=12)

        self.btn_save = ctk.CTkButton(act, text="Include in DB", command=self.save_candidate, state="disabled", fg_color="#0284C7", width=105)
        self.btn_save.pack(side="left", padx=5, pady=12)

        self.btn_ocr = ctk.CTkButton(act, text="Fix OCR", command=self.save_ocr_fix, state="disabled", fg_color="#7C3AED", width=90)
        self.btn_ocr.pack(side="left", padx=5, pady=12)

        self.btn_exc = ctk.CTkButton(act, text="🚫 Exclude", command=self.exclude_term, state="disabled", fg_color="#DC2626", width=100)
        self.btn_exc.pack(side="right", padx=10, pady=12)

    def _on_tk_error(self, exc_type, exc, tb):
        _excepthook(exc_type, exc, tb)
        if isinstance(exc, PermissionError):
            messagebox.showerror("Database locked", DB_LOCKED_MSG)
        else:
            messagebox.showerror("Error", f"{exc_type.__name__}: {exc}\n\nDetails saved to logs\\error.log")

    def open_trainer(self):
        """Launch the companion Trainer (region rescans and training samples) from the same folder."""
        if getattr(sys, "frozen", False):
            exe = os.path.join(BASE_DIR, "AcronymHunterTrainer.exe")
            if not os.path.exists(exe):
                messagebox.showwarning("Region Trainer", "AcronymHunterTrainer.exe is not in this folder."); return
            subprocess.Popen([exe], cwd=BASE_DIR)
        else:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "trainer_gui.py")], cwd=BASE_DIR)

    def open_file(self, path):
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.call(["open", path])
        else: subprocess.call(["xdg-open", path])

    def start_dir(self):
        last = self.settings.get("last_dir", "")
        if last and os.path.isdir(last):
            return last
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        return docs if os.path.isdir(docs) else os.path.expanduser("~")

    def remember_dir(self, path):
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if folder:
            self.settings["last_dir"] = folder
            save_settings(self.settings)

    def select_files(self):
        fps = filedialog.askopenfilenames(title="Select Files", initialdir=self.start_dir(), filetypes=[("Supported", "*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif")])
        if fps:
            self.remember_dir(fps[0])
            self.start_batch(list(fps))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder", initialdir=self.start_dir())
        if not folder: return
        self.remember_dir(folder)
        collected = []
        for root, _, files in os.walk(folder):
            for f in files:
                if not f.startswith("~$") and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                    collected.append(os.path.join(root, f))
        if not collected:
            messagebox.showwarning("Empty", "No supported files found.")
            return
        self.start_batch(collected)

    def start_batch(self, fps):
        self.queued_files = fps
        self.btn_files.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.btn_export.configure(state="disabled")
        self.prog.configure(mode="indeterminate")
        self.prog.start()
        for i in self.tree.get_children(): self.tree.delete(i)
        threading.Thread(target=self.worker, args=(fps,), daemon=True).start()

    def worker(self, fps):
        try:
            self.results = analyze_batch(fps, lambda m: self.after(0, lambda: self.status.configure(text=m)))
            self.after(0, self.scan_done)
        except Exception as e:
            log_error("Batch scan failed")
            msg = f"{type(e).__name__}: {e}\n\nDetails saved to logs\\error.log"
            self.after(0, lambda: messagebox.showerror("Scan failed", msg))
            self.after(0, self.reset_ui)

    # ---------- view: text size ----------
    def apply_font_size(self):
        size = self.font_size
        self.tree_font.configure(size=size)
        self.head_font.configure(size=size)
        row_h = self.tree_font.metrics("linespace") + max(8, size // 2)
        self.style.configure("Treeview", font=self.tree_font, rowheight=row_h)
        self.style.configure("Treeview.Heading", font=self.head_font, padding=(6, max(4, size // 3)))
        scale = size / 11.0
        for cid, _label, width, _anchor in COLUMNS:
            self.tree.column(cid, width=int(width * scale))
        self.lbl_size.configure(text=f"{size} pt")

    def change_font_size(self, step, reset=False):
        new = FONT_DEFAULT if reset else max(FONT_MIN, min(FONT_MAX, self.font_size + step))
        if new != self.font_size or reset:
            self.font_size = new
            self.apply_font_size()
            self.settings["font_size"] = new
            save_settings(self.settings)
        return "break"

    # ---------- view: sorting ----------
    def update_headings(self):
        for cid, label, _w, _a in COLUMNS:
            arrow = (" \u25BC" if self.sort_desc else " \u25B2") if cid == self.sort_col else ""
            self.tree.heading(cid, text=label + arrow, command=lambda c=cid: self.on_heading_click(c))

    def on_heading_click(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = col in ("count", "locations")  # numbers start high-to-low, text A-Z
        self.update_headings()
        self.populate_table()

    def sort_key(self, term, data):
        c = self.sort_col
        if c == "count":
            return (data["count"], term.casefold())
        if c == "locations":
            return (len(data["locations"]), term.casefold())
        if c == "category":
            return (data["category"].casefold(), term.casefold())
        if c == "status":
            rank = next((r for prefix, r in STATUS_ORDER if data["status"].startswith(prefix)), 9)
            return (rank, term.casefold())
        if c == "definition":
            return (data["selected_definition"].casefold(), term.casefold())
        return (term.casefold(),)

    # ---------- view: filtering ----------
    def clear_filters(self):
        self.type_var.set(ALL_TYPES)
        self.status_var.set(STATUS_FILTERS[0])
        self.search_var.set("")   # triggers populate_table
        self.populate_table()

    def refresh_type_options(self):
        types = sorted({base_type(d["category"]) for d in self.results.values()})
        values = [ALL_TYPES] + types
        self.opt_type.configure(values=values)
        if self.type_var.get() not in values:
            self.type_var.set(ALL_TYPES)

    @staticmethod
    def status_matches(data, wanted):
        st = data["status"]
        return {
            "Needs choice": st.startswith("⚠️"),
            "New candidates": st.startswith("🔍"),
            "Resolved": st.startswith("✅"),
            "Errors / not scanned": st.startswith("⛔"),
            "Excluded": data.get("excluded", False),
        }.get(wanted, True)

    @staticmethod
    def row_tag(data):
        if data.get("excluded", False): return "excluded"
        st = data["status"]
        if st.startswith("⛔"): return "fileerror"
        if st.startswith("⚠️"): return "ambiguous"
        if st.startswith("🔍"): return "candidate"
        return "resolved"

    def scan_done(self):
        self.reset_ui()
        self.refresh_type_options()
        self.populate_table()

    def populate_table(self):
        if not hasattr(self, "tree"):
            return
        for i in self.tree.get_children(): self.tree.delete(i)
        show_exc = self.show_exc_var.get()
        ftype, fstat = self.type_var.get(), self.status_var.get()
        query = self.search_var.get().strip().casefold()

        v_count = e_count = a_count = c_count = 0
        rows = []
        for term, data in self.results.items():
            excluded = data.get("excluded", False)
            if excluded:
                e_count += 1
            else:
                v_count += 1
                if data["status"].startswith("⚠️"): a_count += 1
                elif data["status"].startswith("🔍"): c_count += 1

            if excluded and not (show_exc or fstat == "Excluded"): continue
            if ftype != ALL_TYPES and base_type(data["category"]) != ftype: continue
            if fstat != STATUS_FILTERS[0] and not self.status_matches(data, fstat): continue
            if query and query not in term.casefold() and query not in data["selected_definition"].casefold(): continue
            rows.append((term, data))

        rows.sort(key=lambda r: self.sort_key(*r), reverse=self.sort_desc)
        for term, data in rows:
            self.tree.insert("", "end", iid=term, tags=(self.row_tag(data),),
                             values=(term, data["category"], data["count"], data["status"],
                                     data["selected_definition"], "; ".join(data["locations"])))

        self.lbl_showing.configure(text=f"Showing {len(rows)} of {len(self.results)}" if self.results else "")
        if self.results:
            self.status.configure(text=f"Active Findings: {v_count} ({a_count} need choice, {c_count} new candidates) | Suppressed Exclusions: {e_count}")
        if v_count > 0: self.btn_export.configure(state="normal")
        if self.selected_term and self.tree.exists(self.selected_term):
            self.tree.selection_set(self.selected_term)
            self.tree.see(self.selected_term)

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        term = sel[0]
        self.selected_term = term
        data = self.results.get(term)
        if not data: return

        if data.get("file_error"):
            for w in (self.btn_exc, self.btn_apply, self.btn_save, self.btn_ocr, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.lbl_act.configure(text="File could not be read:")
            return

        self.btn_exc.configure(state="disabled" if data.get("excluded", False) else "normal")

        if data["in_db"] and not data.get("excluded", False) and len(data["definitions"]) > 1:
            opts = list(data["definitions"]) + ["Keep All Possibilities"]
            self.combo.configure(state="normal", values=opts); self.combo.set(opts[0])
            self.btn_apply.configure(state="normal")
            self.entry_def.configure(state="disabled"); self.btn_save.configure(state="disabled"); self.btn_ocr.configure(state="disabled")
            self.lbl_act.configure(text=f"Disambiguate '{term}':")
        elif not data["in_db"]:
            self.combo.configure(state="disabled", values=["Not in DB"]); self.combo.set("Not in DB")
            self.btn_apply.configure(state="disabled")
            self.entry_def.configure(state="normal"); self.entry_def.delete(0, "end")
            self.btn_save.configure(state="normal"); self.btn_ocr.configure(state="normal")
            self.lbl_act.configure(text=f"New Candidate '{term}':")
        else:
            self.combo.configure(state="disabled", values=data["definitions"][:1])
            if data["definitions"]: self.combo.set(data["definitions"][0])
            self.btn_apply.configure(state="disabled")
            self.entry_def.configure(state="disabled"); self.btn_save.configure(state="disabled"); self.btn_ocr.configure(state="disabled")
            self.lbl_act.configure(text=f"Selected '{term}':")

    def apply_choice(self):
        if not self.selected_term: return
        choice = self.combo.get()
        data = self.results[self.selected_term]
        if choice == "Keep All Possibilities":
            data["selected_definition"] = "MULTIPLE: " + " | ".join(data["definitions"])
            data["status"] = "⚠️ MULTIPLE (Kept All)"
            tag = "ambiguous"
        else:
            data["selected_definition"] = choice
            data["status"] = "✅ User Selected"
            tag = "resolved"
        self.tree.item(self.selected_term, values=(self.selected_term, data["category"], data["count"], data["status"], data["selected_definition"], "; ".join(data["locations"])), tags=(tag,))

    def open_fix_manager(self):
        """View, add, edit, delete, and undo entries in config\\ocr_corrections.csv."""
        if getattr(self, "fix_win", None) is not None and self.fix_win.winfo_exists():
            self.fix_win.focus(); return
        win = ctk.CTkToplevel(self); self.fix_win = win
        win.title("OCR Fixes - config\\ocr_corrections.csv")
        win.geometry("760x520"); win.minsize(620, 400)
        win.transient(self); win.after(100, win.lift)

        ctk.CTkLabel(win, text="Each line turns an OCR misread into the correct term on the next scan.",
                     anchor="w").pack(fill="x", padx=14, pady=(12, 4))
        frame = ctk.CTkFrame(win); frame.pack(fill="both", expand=True, padx=14, pady=4)
        frame.grid_rowconfigure(0, weight=1); frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=("misread", "correct", "note"), show="headings", selectmode="browse")
        for cid, label, width in (("misread", "Misread", 160), ("correct", "Correct term", 160), ("note", "Note", 340)):
            tree.heading(cid, text=label); tree.column(cid, width=int(width * self.font_size / 11.0), anchor="w")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")

        form = ctk.CTkFrame(win); form.pack(fill="x", padx=14, pady=6)
        e_wrong = ctk.CTkEntry(form, placeholder_text="Misread (e.g. RFF)", width=150); e_wrong.pack(side="left", padx=4, pady=8)
        e_right = ctk.CTkEntry(form, placeholder_text="Correct (e.g. RFP)", width=150); e_right.pack(side="left", padx=4, pady=8)
        e_note = ctk.CTkEntry(form, placeholder_text="Note (optional)", width=220); e_note.pack(side="left", padx=4, pady=8)
        status = ctk.CTkLabel(win, text="", anchor="w", text_color="gray"); status.pack(fill="x", padx=14)

        def load():
            tree.delete(*tree.get_children())
            for i, row in enumerate(read_ocr_fix_rows()):
                tree.insert("", "end", iid=str(i), values=row)
        def rows_now():
            return [list(tree.item(i, "values")) for i in tree.get_children()]
        def save(rows, msg):
            write_ocr_fix_rows(rows); load(); status.configure(text=msg + "  Rescan to apply.")
        def on_pick(_e=None):
            sel = tree.selection()
            if not sel: return
            wrong, right, note = (list(tree.item(sel[0], "values")) + ["", "", ""])[:3]
            for ent, val in ((e_wrong, wrong), (e_right, right), (e_note, note)):
                ent.delete(0, "end"); ent.insert(0, val)
        def add_update():
            wrong, right, note = e_wrong.get().strip(), e_right.get().strip(), e_note.get().strip()
            if not wrong or not right or wrong == right:
                status.configure(text="Enter a misread and a different correct term."); return
            rows = rows_now()
            for r in rows:
                if r[0] == wrong:
                    r[1], r[2] = right, note or r[2]
                    save(rows, f"Updated: {wrong} > {right}."); return
            rows.append([wrong, right, note or "Added in OCR Fixes window"])
            save(rows, f"Added: {wrong} > {right}.")
        def delete():
            sel = tree.selection()
            if not sel:
                status.configure(text="Select a line to delete."); return
            rows = rows_now(); gone = rows.pop(int(tree.index(sel[0])))
            save(rows, f"Deleted: {gone[0]} > {gone[1]}.")
        def undo_last():
            rows = rows_now()
            if not rows:
                status.configure(text="Nothing to undo."); return
            gone = rows.pop()
            save(rows, f"Removed last entry: {gone[0]} > {gone[1]}.")

        btns = ctk.CTkFrame(win); btns.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkButton(btns, text="Add / Update", width=120, command=add_update).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(btns, text="Delete Selected", width=130, fg_color="#DC2626", command=delete).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(btns, text="Undo Last Entry", width=130, fg_color="#64748B", command=undo_last).pack(side="left", padx=4, pady=8)
        ctk.CTkButton(btns, text="Close", width=90, fg_color="#475569", command=win.destroy).pack(side="right", padx=4, pady=8)
        tree.bind("<<TreeviewSelect>>", on_pick)
        load()
        win._fix_api = {"tree": tree, "wrong": e_wrong, "right": e_right, "note": e_note, "status": status,
                        "add": add_update, "delete": delete, "undo": undo_last}   # used by automated tests

    def save_ocr_fix(self):
        """Record that the selected term is an OCR misread of the term typed in the box."""
        if not self.selected_term: return
        right = self.entry_def.get().strip()
        if not right:
            messagebox.showwarning("Fix OCR", "Type the correct term in the box first (for example RFP), then click Fix OCR.")
            return
        wrong = self.selected_term
        rows = [r for r in read_ocr_fix_rows() if r[0] != wrong]
        rows.append([wrong, right, "Added with Fix OCR"])
        write_ocr_fix_rows(rows)
        data = self.results[wrong]
        data["in_db"] = True
        data["status"] = f"🔧 OCR fix saved: {wrong} > {right}"
        data["selected_definition"] = "Rescan to apply. View, edit, or undo with the OCR Fixes button."
        self.tree.item(wrong, values=(wrong, data["category"], data["count"], data["status"], data["selected_definition"], "; ".join(data["locations"])), tags=("resolved",))
        self.entry_def.delete(0, "end")
        self.entry_def.configure(state="disabled")
        self.btn_save.configure(state="disabled"); self.btn_ocr.configure(state="disabled")

    def save_candidate(self):
        if not self.selected_term: return
        nd = self.entry_def.get().strip()
        if not nd:
            messagebox.showwarning("Error", "Type a definition first.")
            return
        data = self.results[self.selected_term]
        cat = data["category"].replace(" (Candidate)", "")
        rows = read_db_rows()
        rows.append([self.selected_term, cat, nd, "Include"])
        write_db_rows(rows)   # atomic rewrite in UTF-8; never mixes encodings by appending
        data["in_db"] = True
        data["excluded"] = False
        data["category"] = cat
        data["definitions"] = [nd]
        data["selected_definition"] = nd
        data["status"] = "✅ Added to DB"
        self.tree.item(self.selected_term, values=(self.selected_term, data["category"], data["count"], data["status"], data["selected_definition"], "; ".join(data["locations"])), tags=("resolved",))
        self.entry_def.delete(0, "end")
        self.entry_def.configure(state="disabled")
        self.btn_save.configure(state="disabled"); self.btn_ocr.configure(state="disabled")

    def exclude_term(self):
        if not self.selected_term: return
        term = self.selected_term
        data = self.results[term]
        reason = data["definitions"][0] if data["definitions"] else "Excluded via GUI"
        update_csv_exclusion(term, data["category"], reason)
        data["excluded"] = True
        data["in_db"] = True
        data["status"] = "🚫 Excluded by Rule"
        data["selected_definition"] = f"[EXCLUDED] {reason}"
        self.btn_exc.configure(state="disabled")
        self.populate_table()

    def reset_ui(self):
        self.prog.stop()
        self.prog.configure(mode="determinate")
        self.prog.set(1)
        self.btn_files.configure(state="normal")
        self.btn_folder.configure(state="normal")

    def export_csv(self):
        path = filedialog.asksaveasfilename(initialdir=self.start_dir(), defaultextension=".csv", filetypes=[("CSV Report", "*.csv")], initialfile="Acronym_Report.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Term", "Category", "Count", "Status", "Definition", "Locations"])
                for term, data in self.results.items():
                    if data.get("excluded", False): continue
                    w.writerow([term, data["category"], data["count"], data["status"], data["selected_definition"], "; ".join(data["locations"])])
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")

def run_selftest(paths):
    os.makedirs(LOG_DIR, exist_ok=True)
    out = os.path.join(LOG_DIR, "selftest.txt")
    with open(out, "w", encoding="utf-8") as f:
        try:
            res = analyze_batch(paths, lambda m: f.write(m + "\n"))
            f.write(f"\nOCR models: {OCR_MODEL_INFO}\nOCR settings: {json.dumps(OCR_CFG)}\n")
            import openpyxl.xml as _oxml
            f.write(f"Security: network guard={socket.socket.connect is _guarded_connect}, "
                    f"office XML entities disabled={_SAFE_XML is not None}, openpyxl defusedxml={_oxml.DEFUSEDXML}\n")
            f.write(f"\nRESULTS: {len(res)} terms\n")
            for term, d in res.items():
                f.write(f"{term}\t{d['category']}\t{d['count']}\t{d['status']}\t{d['selected_definition']}\n")
            f.write("SELFTEST OK\n")
        except Exception:
            f.write(traceback.format_exc())
            f.write("SELFTEST FAILED\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        run_selftest(sys.argv[2:])
        sys.exit(0)
    try:
        app = AcronymAppGUI()
        app.mainloop()
    except Exception:
        log_error("Application failed to start")
        raise