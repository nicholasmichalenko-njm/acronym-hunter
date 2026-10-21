import os
import sys
import shutil
import atexit
import time

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
import getpass
import platform
import tkinter as tk
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
    text, delimiter = _decode_csv(path)
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter))

def read_csv_header(path):
    text, delimiter = _decode_csv(path)
    return next(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter), [])

def _decode_csv(path):
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
    return text, delimiter

# ---- Database columns: any order, common header names, extra columns kept ----
DB_FIELDS = ("Term", "Definition", "Category", "Action")   # order for new files
DB_ALIASES = {
    "term": "Term", "item": "Term", "acronym": "Term", "abbreviation": "Term", "acronym / abbreviation": "Term",
    "definition": "Definition", "meaning": "Definition", "description": "Definition", "expansion": "Definition",
    "category": "Category", "type": "Category",
    "action": "Action", "rule": "Action", "include/exclude": "Action",
}

def db_field(header):
    return DB_ALIASES.get((header or "").strip().lstrip("\ufeff").casefold())

def db_row(r):
    """A database row as {Term, Definition, Category, Action} whatever the column names or order."""
    out = {}
    for k, v in r.items():
        f = db_field(k)
        if f and f not in out:
            out[f] = (v or "").strip()
    return out

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
OCR_IGNORE_FILE = os.path.join(CONFIG_DIR, "ocr_ignore.csv")   # OCR readings that are not text (diagram lines, specks)
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

APP_SETTINGS_FILE = os.path.join(CONFIG_DIR, "app_settings.json")
APP_DEFAULTS = {
    "advanced_features_default": False,   # Advanced tools (Fix OCR, OCR Fixes, Region Trainer) start hidden
    "allow_advanced_toggle": True,        # False = hide the Advanced switch; the default above is locked in
}

def load_app_settings():
    cfg = dict(APP_DEFAULTS)
    try:
        with open(APP_SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
            for k, v in json.load(f).items():
                if k in APP_DEFAULTS and isinstance(v, bool):
                    cfg[k] = v
    except FileNotFoundError:
        pass
    except Exception:
        log_error("config/app_settings.json could not be read; using defaults")
    return cfg

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
# ---- OCR ignore list: exact readings that come from lines, arrows, or specks, never real text ----
_OCR_IGNORE = set()

def load_ocr_ignore():
    """Readings from config/ocr_ignore.csv. Applies only to text read by OCR, never to typed document text."""
    out = set()
    try:
        for row in read_csv_rows(OCR_IGNORE_FILE):
            r = fold((row.get("Reading") or "").strip())
            if r:
                out.add(r)
    except FileNotFoundError:
        pass
    except Exception:
        log_error("config/ocr_ignore.csv could not be read")
    return out

def read_ocr_ignore_rows():
    try:
        return [[(r.get("Reading") or "").strip(), (r.get("Note") or "").strip()] for r in read_csv_rows(OCR_IGNORE_FILE)
                if (r.get("Reading") or "").strip()]
    except FileNotFoundError:
        return []

def write_ocr_ignore_rows(rows):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = OCR_IGNORE_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        w = csv.writer(f)
        w.writerow(["Reading", "Note"])
        w.writerows(rows)
    os.replace(tmp, OCR_IGNORE_FILE)

def refresh_ocr_ignore():
    global _OCR_IGNORE
    _OCR_IGNORE = load_ocr_ignore()
    return _OCR_IGNORE

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp', '.gif'}
VECTOR_FILE_EXTS = {'.svg', '.svgz', '.emf', '.wmf', '.emz', '.wmz'}
SUPPORTED_EXTS = IMAGE_EXTS | VECTOR_FILE_EXTS | {'.pdf', '.pptx', '.docx', '.xlsx'}

# Create an EMPTY database (header only) if missing. Terms come from the user or a Knowledge Pack.
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        csv.writer(f).writerow(list(DB_FIELDS))

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
def db_layout():
    """[(field or None, header text)] in the file's own column order; DB_FIELDS order for a new file."""
    try:
        header = [h.strip().lstrip("\ufeff") for h in read_csv_header(DB_FILE)]
    except (FileNotFoundError, StopIteration):
        header = []
    layout = [(db_field(h), h) for h in header if h]
    have = {f for f, _ in layout if f}
    layout += [(f, f) for f in DB_FIELDS if f not in have]   # add any missing core column at the end
    return layout

def load_database():
    include_db = {}
    exclude_db = {}
    exclude_upper = set()

    if not os.path.exists(DB_FILE):
        return include_db, exclude_db, exclude_upper

    for raw_row in read_csv_rows(DB_FILE):
        row = db_row(raw_row)
        term = fold(row.get("Term", ""))
        cat = row.get("Category") or "Acronym"
        defn = row.get("Definition", "")
        action = (row.get("Action") or "Include").capitalize()

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

VECTOR_EXTS = {".emf", ".wmf", ".emz", ".wmz", ".svg", ".svgz"}
NS_ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"   # PowerPoint/Word SVG picture companion
VECTOR_TEXT_MIN_CHARS = 3   # vector graphic with less real text than this is drawn as a picture and OCR'd
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
        if fold(str(text)).strip() in _OCR_IGNORE:   # marked "Not text" in the Trainer
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

# ---------------------------------------------------------------------------
# Vector graphics: read real text first; draw and OCR only when there is none
# ---------------------------------------------------------------------------
import gzip
import struct

def _maybe_gunzip(data):
    if data[:2] == b"\x1f\x8b":   # .svgz / .emz / .wmz
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as g:
            return g.read(200 * 1024 * 1024)
    return data

def svg_text(data):
    """Text from <text>/<tspan>/<textPath>, plus HTML labels in <foreignObject> (draw.io) when no <text> fallback exists."""
    root = _ET.fromstring(_maybe_gunzip(data), parser=_SAFE_XML)
    lines = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        tag = _ET.QName(el).localname
        if tag == "text":
            t = " ".join(x.strip() for x in el.itertext() if x.strip())
            if t:
                lines.append(t)
        elif tag == "foreignObject":
            parent = el.getparent()
            has_fallback = parent is not None and any(isinstance(c.tag, str) and _ET.QName(c).localname == "text" for c in parent)
            if not has_fallback:
                t = " ".join(x.strip() for x in el.itertext() if x.strip())
                if t:
                    lines.append(t)
    return "\n".join(lines)

def _assemble_runs(runs):
    """Join text runs (x, y, text) into lines; single characters placed one by one are joined without spaces."""
    runs = sorted(runs, key=lambda r: (round(r[1] / 4), r[0]))
    lines, cur, cur_y, prev = [], [], None, ""
    for x, y, t in runs:
        if cur_y is None or abs(y - cur_y) > 4:
            if cur: lines.append("".join(cur))
            cur, cur_y, prev = [t], y, t
            continue
        cur.append(t if (len(t) == 1 and len(prev) == 1) else " " + t)
        prev = t
    if cur: lines.append("".join(cur))
    return "\n".join(l.strip() for l in lines if l.strip())

def emf_text(data):
    """Text from EMF records: EMR_EXTTEXTOUTW/A (real characters only) and EMF+ DrawString in EMR_COMMENT."""
    runs_gdi, runs_plus, pos, n = [], [], 0, len(data)
    while pos + 8 <= n:
        rtype, size = struct.unpack_from("<II", data, pos)
        if size < 8 or pos + size > n:
            break
        try:
            if rtype in (83, 84) and size >= 76:            # EMR_EXTTEXTOUTA / EMR_EXTTEXTOUTW
                x, y, nchars, off, opts = struct.unpack_from("<iiIII", data, pos + 36)
                if not (opts & 0x10) and nchars and off + nchars * (2 if rtype == 84 else 1) <= size:   # 0x10 = glyph indices
                    raw = data[pos + off: pos + off + nchars * (2 if rtype == 84 else 1)]
                    t = raw.decode("utf-16-le" if rtype == 84 else "cp1252", "ignore").strip("\x00")
                    if t.strip(): runs_gdi.append((x, y, t))
            elif rtype == 70 and size >= 16:                  # EMR_COMMENT, possibly EMF+
                dsize = struct.unpack_from("<I", data, pos + 8)[0]
                if data[pos + 12: pos + 16] == b"EMF+":
                    buf, p = data[pos + 16: pos + 12 + dsize], 0
                    while p + 12 <= len(buf):
                        t2, _flags, sz, _dsz = struct.unpack_from("<HHII", buf, p)
                        if sz < 12 or p + sz > len(buf): break
                        if t2 == 0x401C and sz >= 40:        # EmfPlusDrawString
                            length = struct.unpack_from("<I", buf, p + 20)[0]
                            lx, ly = struct.unpack_from("<ff", buf, p + 24)
                            t = buf[p + 40: p + 40 + length * 2].decode("utf-16-le", "ignore")
                            if t.strip(): runs_plus.append((lx, ly, t))
                        p += sz
            elif rtype == 14:                                 # EMR_EOF
                break
        except struct.error:
            pass
        pos += size
    return _assemble_runs(runs_plus or runs_gdi)              # EMF+ text is authoritative in dual-mode files

def wmf_text(data):
    """Text from WMF META_TEXTOUT / META_EXTTEXTOUT records (ANSI)."""
    pos = 22 if data[:4] == b"\xd7\xcd\xc6\x9a" else 0          # placeable header
    if pos + 18 > len(data): return ""
    pos += struct.unpack_from("<H", data, pos + 2)[0] * 2        # header size in 16-bit words
    runs = []
    while pos + 6 <= len(data):
        size_words, func = struct.unpack_from("<IH", data, pos)
        size = size_words * 2
        if size < 6 or pos + size > len(data): break
        try:
            if func == 0x0521:                                    # META_TEXTOUT
                ln = struct.unpack_from("<H", data, pos + 6)[0]
                t = data[pos + 8: pos + 8 + ln].decode("cp1252", "ignore")
                y, x = struct.unpack_from("<hh", data, pos + 8 + ln + (ln & 1))
                runs.append((x, y, t))
            elif func == 0x0A32:                                  # META_EXTTEXTOUT
                y, x, ln, opts = struct.unpack_from("<hhHH", data, pos + 6)
                start = pos + 14 + (8 if opts & 0x0006 else 0)
                runs.append((x, y, data[start: start + ln].decode("cp1252", "ignore")))
            elif func == 0x0000:
                break
        except struct.error:
            pass
        pos += size
    return _assemble_runs([r for r in runs if r[2].strip()])

def render_vector(data, ext):
    """Draw a vector graphic as PNG bytes for OCR: SVG via MuPDF, EMF/WMF via Windows GDI (Pillow)."""
    data = _maybe_gunzip(data)
    if ext in (".svg", ".svgz"):
        doc = fitz.open(stream=data, filetype="svg")
        try:
            page = doc[0]
            zoom = max(1.0, min(4.0, 2400.0 / max(page.rect.width, page.rect.height, 1)))
            return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).tobytes("png")
        finally:
            doc.close()
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    base_w, base_h = im.size
    dpi = max(150, min(600, int(72 * 2400 / max(base_w, base_h, 1))))   # aim for ~2400 px on the long side
    try:
        im.load(dpi=dpi)
    except TypeError:
        im.load()
    im = im.convert("RGB")
    if max(im.size) < 1600:   # GDI ignored the dpi request: scale up so small labels stay readable
        k = 2400 / max(im.size)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    out = io.BytesIO(); im.save(out, "PNG")
    return out.getvalue()

def read_vector(data, ext):
    """(text, method) for a vector graphic. method: 'vector text', 'OCR', or '' when nothing could be read."""
    ext = ext.lower()
    try:
        if ext in (".svg", ".svgz"):
            text = svg_text(data)
        else:
            raw = _maybe_gunzip(data)
            text = emf_text(raw) if raw[40:44] == b" EMF" else wmf_text(raw)
    except Exception:
        log_error("Vector text extraction failed")
        text = ""
    if len(text.strip()) >= VECTOR_TEXT_MIN_CHARS:
        return text, "vector text"
    try:
        return read_image_bytes(render_vector(data, ext)), "OCR"
    except Exception:
        log_error("Vector graphic could not be drawn for OCR")
        return "", ""

def part_images(z, partpath, root, label_base, chunks, seen, rels=None):
    """OCR every picture referenced by one part (slide, layout, Word body/header, Excel drawing)."""
    rels = rels if rels is not None else zip_rels(z, partpath)
    refs = []
    for blip in root.iter(_q("a", "blip")):
        if not _in_fallback(blip):
            svg = next(blip.iter("{%s}svgBlip" % NS_ASVG), None)   # SVG original stored beside the PNG
            svg_rid = svg.get(_q("r", "embed")) if svg is not None else None
            if svg_rid and svg_rid in rels and not rels[svg_rid][2]:
                try:
                    stext = svg_text(z.read(rels[svg_rid][1]))
                except Exception:
                    stext = ""
                if len(stext.strip()) >= VECTOR_TEXT_MIN_CHARS:
                    name = shape_name(blip); shown = f"'{name}' " if name else ""
                    target = rels[svg_rid][1]
                    if (label_base, target) not in seen:
                        seen.add((label_base, target))
                        chunks.append((f"{label_base}, SVG {shown}{posixpath.basename(target)})", stext))
                    continue   # exact SVG text beats OCR of the PNG copy
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
                text, method = read_vector(z.read(target), ext)
                if text.strip():
                    chunks.append((label if method == "OCR" else label[:-1] + ", vector text)", text))
                elif not method:
                    note_skip(label, "Vector graphic could not be read or drawn.")
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
    if ext in VECTOR_FILE_EXTS:
        status_callback(f"{prefix} - Reading vector graphic...")
        with open(filepath, "rb") as f:
            text, method = read_vector(f.read(), ext)
        if text.strip():
            chunks.append((f"{filename} ({'Vector text' if method == 'vector text' else 'Image'})", text))
        else:
            note_skip(f"{filename} (Vector)", "Vector graphic has no readable text and could not be drawn for OCR.")
    elif ext in IMAGE_EXTS:
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
    """exc may be an exception or a message string."""
    key = f"⛔ {os.path.basename(filepath)}"
    findings[key] = {
        "category": "File Error", "count": 1, "locations": [filepath],
        "definitions": [], "in_db": True, "excluded": False, "file_error": True,
        "selected_definition": (exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}")[:300], "status": "⛔ Could not read file"
    }

def record_skip(findings, label, reason):
    key = f"⛔ {label}"
    if key not in findings:
        findings[key] = {
            "category": "Not Scanned", "count": 1, "locations": [label],
            "definitions": [], "in_db": True, "excluded": False, "file_error": True,
            "selected_definition": reason, "status": "⛔ Not scanned"
        }

def build_matcher():
    """Load the database, corrections, ignore list, and patterns once per scan."""
    refresh_ocr_ignore()
    include_db, exclude_db, exclude_upper = load_database()
    all_terms = set(include_db.keys()) | set(exclude_db.keys())
    direct_pattern = None
    if all_terms:
        sorted_terms = sorted(all_terms, key=len, reverse=True)
        # (?<![^\W\d_]) = not preceded by a letter; digits may touch a unit (25°C, 10µm, 150psi)
        direct_pattern = re.compile(r'(?<![^\W\d_])(' + '|'.join([re.escape(t) for t in sorted_terms]) + r")(?:'?s)?(?!\w)")
    return {
        "include_db": include_db, "exclude_db": exclude_db, "exclude_upper": exclude_upper,
        "ocr_fixes": load_ocr_fixes(), "direct_pattern": direct_pattern,
        "fuzzy_targets": {t: t for t in include_db.keys() if len(t) >= 3 and t.isupper()},
        "acronym_re": re.compile(r'\b([A-Z][A-Z0-9/&]{1,7}s?)\b'),
        "unit_re": re.compile(r'(?<!\w)\d+(?:\.\d+)?\s*([a-zA-Z\u00b0\u03bc\u03a9\u00c5]{1,5}(?:/[a-zA-Z0-9\^]{1,4})?)(?!\w)'),
        "abbrev_re": re.compile(r'(?<!\w)([a-zA-Z]{1,4}/[a-zA-Z]{1,4}|[a-zA-Z]{2,6}\.)(?!\w)'),
    }

def match_chunks(findings, chunks, m):
    """Run the three gates over [(location label, text)] and record findings."""
    for loc_label, text in chunks:
        if not text.strip():
            continue
        text = fold(text)

        # Gate 1 & 2: Unified Database (Exclusions & Inclusions)
        if m['direct_pattern']:
            for match in m['direct_pattern'].finditer(text):
                term = match.group(1)
                if term in m['exclude_db'] and term not in m['include_db']:
                    record_excluded(findings, term, loc_label, m['exclude_db'])
                elif term in m['include_db']:
                    record_included(findings, term, loc_label, m['include_db'])

        # Gate 3: Heuristic Candidate Discovery (Items not in DB)
        for match in m['acronym_re'].finditer(text):
            raw = match.group(1)
            cand = raw[:-1] if raw.endswith('s') and len(raw) > 2 else raw
            if raw in m['ocr_fixes'] or cand in m['ocr_fixes']:
                wrong = raw if raw in m['ocr_fixes'] else cand
                apply_ocr_fix(findings, wrong, m['ocr_fixes'][wrong], "Acronym (Candidate)", loc_label, m['include_db'], m['exclude_db'])
                continue
            if cand in m['include_db'] or cand in m['exclude_db'] or cand.upper() in m['exclude_upper'] or cand.isdigit():
                continue
            if sum(1 for c in cand if c.isupper()) < 2:
                continue
            if any(ch in OCR_CONFUSIONS for ch in cand):
                fixed = cand.translate(OCR_MAP)
                if fixed in m['include_db']:
                    record_included(findings, fixed, f"{loc_label} [OCR fix: {cand}]", m['include_db'])
                    continue
            if any(ch.isdigit() for ch in cand) and m['fuzzy_targets']:
                best = process.extractOne(cand, m['fuzzy_targets'].keys(), scorer=fuzz.ratio)
                if best and best[1] >= OCR_CFG["fuzzy_min_score"]:
                    record_included(findings, best[0], f"{loc_label} [OCR fix: {cand}]", m['include_db'])
                    continue
            record_candidate(findings, cand, "Acronym (Candidate)", loc_label)

        for match in m['unit_re'].finditer(text):
            ucand = match.group(1)
            if ucand in m['ocr_fixes']:
                apply_ocr_fix(findings, ucand, m['ocr_fixes'][ucand], "Unit (Candidate)", loc_label, m['include_db'], m['exclude_db'])
                continue
            if (ucand in m['include_db'] or ucand in m['exclude_db'] or
                    ucand.upper() in m['exclude_upper'] or ucand.lower() in NON_UNIT_WORDS or ucand.isdigit()):
                continue
            record_candidate(findings, ucand, "Unit (Candidate)", loc_label)

        for match in m['abbrev_re'].finditer(text):
            acand = match.group(1)
            if acand in m['ocr_fixes']:
                apply_ocr_fix(findings, acand, m['ocr_fixes'][acand], "Abbreviation (Candidate)", loc_label, m['include_db'], m['exclude_db'])
                continue
            base = acand.rstrip('.')
            if (acand in m['include_db'] or acand in m['exclude_db'] or base in m['include_db'] or base in m['exclude_db'] or
                    acand.upper() in m['exclude_upper'] or base.upper() in m['exclude_upper']):
                continue
            if acand.endswith('.') and acand[:-1].lower() in {"end", "out", "see", "all", "one", "two", "now"}:
                continue
            record_candidate(findings, acand, "Abbreviation (Candidate)", loc_label)



def scan_file(filepath, status_callback, idx, total):
    """Read one file. Returns (chunks, skipped [(label, reason)], error message or None)."""
    _SKIPPED.clear()
    try:
        chunks = extract_chunks_from_file(filepath, status_callback, idx, total)
        err = None
    except Exception as e:
        log_error(f"Could not read {filepath}")
        chunks, err = [], f"{type(e).__name__}: {e}"
    return chunks, list(_SKIPPED), err

def analyze_batch(filepaths, status_callback):
    m = build_matcher()
    findings = {}
    total = len(filepaths)
    _OCR_CACHE.clear()
    for idx, filepath in enumerate(filepaths, start=1):
        chunks, skips, err = scan_file(filepath, status_callback, idx, total)
        if err:
            record_file_error(findings, filepath, err)
        for label, reason in skips:
            record_skip(findings, label, reason)
        match_chunks(findings, chunks, m)
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

# ==============================================================================
# PROJECTS: remember a folder's findings, rescan only what changed, track changes
# ==============================================================================
APP_VERSION = "1.4.2"            # keep in step with version_info.txt
PROJECT_EXT = ".ahproj"
PROJECT_FORMAT = "AcronymHunterProject"
LOCK_STALE_HOURS = 12
SKIP_DIRS = {"_internal", "_local_sandbox", "training_data", "logs", "config", "__pycache__", ".git"}
CHANGE_LABELS = {"new": "New", "changed": "Changed", "unchanged": "Unchanged", "gone": "No longer found"}

_NUM_TOKEN = re.compile(r"[\d.,]+")
_EDGE_PUNCT = "()[]{}\"'\u201c\u201d\u2018\u2019,;:!?"

def _termlike(token):
    """True for tokens that can ever match: 2+ capitals, a digit, a symbol, or an abbreviation-style word ending in '.'
    Hyphenated words count if any part does (S-band. -> band.)."""
    core = token.strip(_EDGE_PUNCT)
    if not core:
        return False
    if "-" in core.strip("-"):
        return any(_termlike(part) for part in core.split("-") if part)
    if sum(c.isupper() for c in core) >= 2 or any(c.isdigit() for c in core):
        return True
    if any(not c.isalpha() and c not in ".-'" for c in core):
        return True
    return core.endswith(".") and core[:-1].isalpha() and 1 <= len(core) - 1 <= 6

def weak_terms(m):
    """Database / correction words that _termlike() would drop (e.g. lowercase units like 'psi'). They are kept
    explicitly, and changing them invalidates saved results so nothing is missed."""
    words = set()
    for term in list(m["include_db"]) + list(m["exclude_db"]) + list(m["ocr_fixes"]):
        words.update(w for w in term.split() if not _termlike(w))
    return words

def engine_signature(weak=()):
    """Saved results are reused only while extraction, OCR settings, OCR models, and weak terms are unchanged."""
    models = sorted((n, os.path.getsize(os.path.join(MODELS_DIR, n)), int(os.path.getmtime(os.path.join(MODELS_DIR, n))))
                    for n in os.listdir(MODELS_DIR)) if os.path.isdir(MODELS_DIR) else []
    return hashlib.sha1(json.dumps([APP_VERSION.rsplit(".", 1)[0], OCR_CFG, models, sorted(weak), sorted(_OCR_IGNORE)],
                                   sort_keys=True).encode()).hexdigest()[:12]

def _numberish(token):
    t = token.strip(_EDGE_PUNCT)
    return bool(t) and t[-1].isdigit() and any(c.isdigit() for c in t)

def reduce_text(text, weak=()):
    """Terms-only text for the project file: keeps term-like tokens, the word after a number (units), and the
    database's own lowercase words. Each run of dropped words becomes '~' so neighbors never become adjacent
    (matching results stay identical to a full-text scan). Sentences cannot be reconstructed."""
    out, prev_num = [], False
    for line in text.splitlines():
        kept, gap = [], False
        for t in line.split():
            if _termlike(t) or prev_num or t.strip(_EDGE_PUNCT) in weak:
                if gap:
                    kept.append("~")
                kept.append(t); gap = False
            else:
                gap = True
            prev_num = _numberish(t)
        if gap and kept:
            kept.append("~")
        out.append(" ".join(kept) if kept else "~")
    return "\n".join(out)

class Project:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.root = os.path.dirname(self.path)
        self.name = os.path.splitext(os.path.basename(self.path))[0]
        self.lock_path = self.path + ".lock"
        self.read_only = False
        self.locked_by = None
        self.data = None

    @staticmethod
    def new_data():
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return {"format": PROJECT_FORMAT, "version": 1, "app_version": APP_VERSION, "created": now,
                "last_scan": None, "last_stats": {}, "files": {}, "history": {}, "decisions": {}, "manual": {}}

    def load(self):
        with open(self.path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if data.get("format") != PROJECT_FORMAT:
            raise ValueError("This is not an Acronym Hunter project file.")
        base = self.new_data(); base.update(data); self.data = base

    def save(self):
        if self.read_only or self.data is None:
            return
        self.data["app_version"] = APP_VERSION
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        for attempt in range(6):   # OneDrive/SharePoint sync can hold the file for a moment while uploading
            try:
                os.replace(tmp, self.path); return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.5)

    # ---- single-editor lock ----
    @staticmethod
    def _me():
        return {"user": getpass.getuser(), "computer": platform.node()}

    def acquire_lock(self, force=False):
        """True if we hold the lock; False if someone else holds a fresh lock (self.locked_by says who)."""
        if os.path.exists(self.lock_path) and not force:
            try:
                info = json.load(open(self.lock_path, encoding="utf-8"))
                age_h = (datetime.datetime.now() - datetime.datetime.fromisoformat(info["time"])).total_seconds() / 3600
                me = self._me()
                if (info.get("user"), info.get("computer")) != (me["user"], me["computer"]) and age_h < LOCK_STALE_HOURS:
                    self.locked_by = info
                    return False
            except Exception:
                pass
        with open(self.lock_path, "w", encoding="utf-8") as f:
            json.dump(dict(self._me(), time=datetime.datetime.now().isoformat(timespec="seconds")), f)
        return True

    def release_lock(self):
        try:
            if not self.read_only and os.path.exists(self.lock_path):
                info = json.load(open(self.lock_path, encoding="utf-8"))
                if (info.get("user"), info.get("computer")) == (self._me()["user"], self._me()["computer"]):
                    os.remove(self.lock_path)
        except Exception:
            pass

    # ---- files ----
    def list_files(self):
        out = []
        for dirpath, dirnames, files in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in files:
                if f.startswith("~$") or os.path.splitext(f)[1].lower() not in SUPPORTED_EXTS:
                    continue
                out.append(os.path.relpath(os.path.join(dirpath, f), self.root).replace(os.sep, "/"))
        return sorted(out)

def project_findings(project, status_callback, full=False, rescan=True):
    """Scan the project folder, reusing saved results for unchanged files. rescan=False rebuilds from saved results only."""
    m = build_matcher()
    findings, stats = {}, {"files": 0, "scanned": 0, "reused": 0, "removed": 0}
    _OCR_CACHE.clear()
    weak = weak_terms(m)
    cache, sig = project.data["files"], engine_signature(weak)
    files = project.list_files() if rescan else sorted(cache)
    stats["files"] = len(files)
    stats["removed"] = len(set(cache) - set(files)) if rescan else 0
    new_cache = {}
    for idx, rel in enumerate(files, start=1):
        absf = os.path.join(project.root, rel.replace("/", os.sep))
        entry = cache.get(rel)
        st = os.stat(absf) if rescan and os.path.exists(absf) else None
        fresh = (entry and entry.get("engine") == sig and
                 (not rescan or (st and entry["size"] == st.st_size and abs(entry["mtime"] - st.st_mtime) < 1.0)))
        if (not full and fresh) or not rescan:
            if entry is None:
                continue
            stats["reused"] += 1
            if rescan:
                status_callback(f"[{idx}/{len(files)}] {rel} - unchanged, using saved results")
        else:
            chunks, skips, err = scan_file(absf, status_callback, idx, len(files))
            entry = {"size": st.st_size, "mtime": st.st_mtime, "engine": sig,
                     "scanned": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                     "chunks": [[label, reduce_text(fold(text), weak)] for label, text in chunks if text.strip()],
                     "skips": skips, "error": err}
            stats["scanned"] += 1
        new_cache[rel] = entry
        if entry.get("error"):
            record_file_error(findings, rel, entry["error"])
        for label, reason in entry.get("skips", []):
            record_skip(findings, label, reason)
        match_chunks(findings, entry["chunks"], m)
    if rescan:
        project.data["files"] = new_cache
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True)), stats

def apply_project_history(project, findings, update=True):
    """Mark each finding New / Changed / Unchanged against the last scan; add 'No longer found' rows."""
    hist = project.data["history"]
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for term, d in findings.items():
        if d.get("file_error"):
            continue
        locs = sorted(d["locations"])[:200]
        h = hist.get(term)
        if update:
            if h is None or h.get("state") == "gone":
                state = "new"
            elif h.get("count") != d["count"] or h.get("locations") != locs:
                state = "changed"
            else:
                state = "unchanged"
            first = h["first_seen"] if h else today
            hist[term] = {"first_seen": first, "last_seen": today, "count": d["count"], "locations": locs,
                          "category": d["category"], "definition": d["selected_definition"], "state": state}
            h = hist[term]
        if h:
            d["change"] = CHANGE_LABELS.get(h.get("state"), "")
            d["first_seen"], d["last_seen"] = h.get("first_seen", ""), h.get("last_seen", "")
    for term, h in hist.items():
        if term in findings:
            continue
        if update:
            h["state"] = "gone"
        if h.get("state") == "gone":
            findings[term] = {"category": h.get("category", ""), "count": 0, "locations": h.get("locations", []),
                              "definitions": [], "in_db": True, "excluded": False, "gone": True,
                              "selected_definition": h.get("definition", ""), "status": "✖ No longer found",
                              "change": CHANGE_LABELS["gone"], "first_seen": h.get("first_seen", ""),
                              "last_seen": h.get("last_seen", "")}
    if update:
        project.data["last_scan"] = today

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
    """Atomic rewrite: write a temp file beside the DB, then swap it in (no half-written DB).
    rows: [term, category, definition, action(, {extra column: value})]. Keeps the file's own column order,
    header names, and extra columns, so a reordered or extended database stays the way the user set it up."""
    layout = db_layout()
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding=CSV_WRITE_ENCODING) as f:
        w = csv.writer(f)
        w.writerow([h for _, h in layout])
        for r in rows:
            vals = {"Term": r[0], "Category": r[1], "Definition": r[2], "Action": r[3]}
            extra = r[4] if len(r) > 4 else {}
            w.writerow([vals[f] if f else extra.get(h, "") for f, h in layout])
    os.replace(tmp, DB_FILE)

def read_db_rows():
    rows = []
    if os.path.exists(DB_FILE):
        for r in read_csv_rows(DB_FILE):
            d = db_row(r)
            extra = {k: v for k, v in r.items() if k and not db_field(k)}
            rows.append([d.get("Term", ""), d.get("Category") or "Acronym",
                         d.get("Definition", ""), d.get("Action") or "Include", extra])
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
    update_csv_exclusions([(term, cat, reason)])

def update_csv_exclusions(items):
    """Mark several terms Exclude in one database write. items: [(term, category, reason)]."""
    rows = read_db_rows()
    for term, cat, reason in items:
        found = False
        for r in rows:
            if fold(r[0]) == fold(term):
                r[3] = "Exclude"
                found = True
        if not found:
            rows.append([term, cat.replace(" (Candidate)", ""), reason, "Exclude"])
    write_db_rows(rows)

# ==============================================================================
# 6b. KNOWLEDGE PACKS: trained models + database + OCR fixes + ignore list, shared via approved SharePoint
# ==============================================================================
KNOWLEDGE_FORMAT = "AcronymHunterKnowledge"
KNOWLEDGE_INFO_FILE = os.path.join(CONFIG_DIR, "knowledge_installed.json")
KNOWLEDGE_BACKUP_DIR = os.path.join(CONFIG_DIR, "knowledge_backups")
PACK_MODEL_FILES = ("rec.onnx", "det.onnx", "cls.onnx", "rec_keys.txt")
PACK_DATA_FILES = {"acronym_database.csv": "DB", "ocr_corrections.csv": "FIXES", "ocr_ignore.csv": "IGNORE"}
PACK_MAX_MEMBER_BYTES = 400 * 1024 * 1024
PACK_ROOT = "knowledge/"

def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def _knowledge_sources():
    """(name inside the pack, path on disk) for every knowledge file that exists in this copy."""
    out = []
    for name, path in (("acronym_database.csv", DB_FILE), ("ocr_corrections.csv", OCR_FIXES_FILE),
                       ("ocr_ignore.csv", OCR_IGNORE_FILE)):
        if os.path.isfile(path):
            out.append((name, path))
    for m in PACK_MODEL_FILES:
        path = os.path.join(MODELS_DIR, m)
        if os.path.isfile(path):
            out.append(("models/" + m, path))
    return out

def make_knowledge_pack(out_path, notes=""):
    """Write a Knowledge Pack zip of this copy's database, OCR fixes, ignore list, and models. Returns its info."""
    files = _knowledge_sources()
    now = datetime.datetime.now()
    info = {"format": KNOWLEDGE_FORMAT, "version": now.strftime("%Y.%m.%d-%H%M"), "created": now.strftime("%Y-%m-%d %H:%M"),
            "created_by": getpass.getuser(), "computer": platform.node(), "app_version": APP_VERSION,
            "notes": notes.strip(), "handling": "Contains knowledge learned from internal documents. Approved SharePoint only. Never GitHub or email.",
            "files": {}}
    for name, path in files:
        info["files"][name] = {"sha256": _sha256_file(path), "bytes": os.path.getsize(path)}
    try:
        info["counts"] = {"database_rows": len(read_db_rows()), "ocr_fixes": len(read_ocr_fix_rows()),
                          "ignored_readings": len(read_ocr_ignore_rows())}
    except Exception:
        info["counts"] = {}
    info["models"] = [n.split("/", 1)[1] for n, _ in files if n.startswith("models/")]
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(PACK_ROOT + "pack_info.json", json.dumps(info, indent=1, ensure_ascii=False))
        for name, path in files:
            z.write(path, PACK_ROOT + name)
    os.replace(tmp, out_path)
    return info

def read_knowledge_pack(path):
    """Validate a pack and return (info, {name: bytes}). Refuses unknown members, oversize members, and any
    file whose SHA-256 does not match pack_info.json (a damaged or altered pack)."""
    allowed = {PACK_ROOT + "pack_info.json"} | {PACK_ROOT + n for n in PACK_DATA_FILES} | \
              {PACK_ROOT + "models/" + m for m in PACK_MODEL_FILES}
    with zipfile.ZipFile(path) as z:
        entries = [e for e in z.infolist() if not e.is_dir()]
        for e in entries:
            if e.filename not in allowed:
                raise ValueError(f"Unexpected file in pack: {e.filename}. Not a valid Knowledge Pack.")
            if e.file_size > PACK_MAX_MEMBER_BYTES:
                raise ValueError(f"{e.filename} is too large.")
        if PACK_ROOT + "pack_info.json" not in {e.filename for e in entries}:
            raise ValueError("pack_info.json is missing. Not a Knowledge Pack.")
        info = json.loads(z.read(PACK_ROOT + "pack_info.json").decode("utf-8"))
        if info.get("format") != KNOWLEDGE_FORMAT:
            raise ValueError("Not an Acronym Hunter Knowledge Pack.")
        data = {}
        for name, meta in info.get("files", {}).items():
            member = PACK_ROOT + name
            if member not in allowed:
                raise ValueError(f"Pack lists an unexpected file: {name}")
            blob = z.read(member)
            if _sha256_bytes(blob) != meta.get("sha256"):
                raise ValueError(f"{name} does not match its fingerprint. The pack is damaged or was altered.")
            data[name] = blob
        if len(data) != len(entries) - 1:
            raise ValueError("The pack holds files that pack_info.json does not list.")
    return info, data

def _backup_targets():
    return [DB_FILE, OCR_FIXES_FILE, OCR_IGNORE_FILE, KNOWLEDGE_INFO_FILE] + [os.path.join(MODELS_DIR, m) for m in PACK_MODEL_FILES]

def backup_knowledge(reason):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(KNOWLEDGE_BACKUP_DIR, stamp)
    os.makedirs(dest, exist_ok=True)
    manifest = {"reason": reason, "time": stamp, "files": {}}
    for i, path in enumerate(_backup_targets()):
        rel = os.path.relpath(path, BASE_DIR)
        if os.path.isfile(path):
            shutil.copy2(path, os.path.join(dest, f"{i}.bak"))
            manifest["files"][rel] = f"{i}.bak"
        else:
            manifest["files"][rel] = None
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    return dest

def list_knowledge_backups():
    if not os.path.isdir(KNOWLEDGE_BACKUP_DIR):
        return []
    return sorted(d for d in os.listdir(KNOWLEDGE_BACKUP_DIR) if os.path.isfile(os.path.join(KNOWLEDGE_BACKUP_DIR, d, "manifest.json")))

def restore_last_knowledge_backup():
    """Put back exactly what the last Install or Load replaced. Returns the reason recorded, or None."""
    backups = list_knowledge_backups()
    if not backups:
        return None
    src = os.path.join(KNOWLEDGE_BACKUP_DIR, backups[-1])
    manifest = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    for rel, bak in manifest["files"].items():
        path = os.path.join(BASE_DIR, rel)
        if bak is None:
            if os.path.isfile(path):
                os.remove(path)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            shutil.copy2(os.path.join(src, bak), path)
    shutil.rmtree(src, ignore_errors=True)
    reset_ocr_engine()
    return manifest.get("reason", "last update")

def reset_ocr_engine():
    """Load models again on the next image (after a model change)."""
    global _ocr_engine, OCR_MODEL_INFO
    with _ocr_lock:
        _ocr_engine = None
        OCR_MODEL_INFO = "not loaded yet"
    _OCR_CACHE.clear()

def _csv_bytes_rows(blob):
    os.makedirs(SANDBOX_TEMP, exist_ok=True)
    tmp = os.path.join(SANDBOX_TEMP, f"pack_{os.getpid()}_{time.time_ns()}.csv")
    with open(tmp, "wb") as f:
        f.write(blob)
    try:
        return read_csv_rows(tmp)
    finally:
        os.remove(tmp)

def merge_pack_database(blob):
    """Add-only: new terms and new definitions are added. The user's own rows, edits, and Exclude choices win."""
    rows = read_db_rows()
    have_pairs = {(fold(r[0]), r[2].strip().casefold()) for r in rows}
    have_terms = {fold(r[0]) for r in rows}
    excluded = {fold(r[0]) for r in rows if r[3].strip().capitalize() == "Exclude"}
    added = 0
    for raw in _csv_bytes_rows(blob):
        d = db_row(raw)
        term, defn = d.get("Term", ""), d.get("Definition", "")
        cat, action = d.get("Category") or "Acronym", (d.get("Action") or "Include").capitalize()
        key = fold(term)
        if not key:
            continue
        if action == "Exclude":
            if key in have_terms:
                continue
        elif key in excluded or (key, defn.casefold()) in have_pairs or not defn:
            continue
        rows.append([term, cat, defn, action]); have_terms.add(key); have_pairs.add((key, defn.casefold())); added += 1
    if added:
        write_db_rows(rows)
    return added

def merge_pack_fixes(blob):
    rows = read_ocr_fix_rows(); have = {fold(r[0]) for r in rows}; added = 0
    for r in _csv_bytes_rows(blob):
        wrong, right = (r.get("Misread") or "").strip(), (r.get("Correct") or "").strip()
        if wrong and right and fold(wrong) not in have:
            rows.append([wrong, right, (r.get("Note") or "").strip()]); have.add(fold(wrong)); added += 1
    if added:
        write_ocr_fix_rows(rows)
    return added

def merge_pack_ignore(blob):
    rows = read_ocr_ignore_rows(); have = {fold(r[0]).strip() for r in rows}; added = 0
    for r in _csv_bytes_rows(blob):
        reading = (r.get("Reading") or "").strip()
        if reading and fold(reading).strip() not in have:
            rows.append([reading, (r.get("Note") or "").strip()]); have.add(fold(reading).strip()); added += 1
    if added:
        write_ocr_ignore_rows(rows)
    return added

def _check_onnx(path):
    import onnxruntime as ort
    ort.InferenceSession(path, providers=["CPUExecutionProvider"])

def install_knowledge_pack(path):
    """Verify, back up, then install a pack. Models replace the current models; data files merge add-only."""
    info, data = read_knowledge_pack(path)
    models = {n.split("/", 1)[1]: b for n, b in data.items() if n.startswith("models/")}
    backup_knowledge(f"before installing Knowledge Pack {info.get('version', '?')}")
    report = [f"Installed Knowledge Pack {info.get('version', '?')} (made {info.get('created', '?')} by {info.get('created_by', '?')})"]
    if models:
        os.makedirs(MODELS_DIR, exist_ok=True)
        for m in PACK_MODEL_FILES:
            target = os.path.join(MODELS_DIR, m)
            if os.path.isfile(target):
                os.remove(target)
        for m, blob in models.items():
            with open(os.path.join(MODELS_DIR, m), "wb") as f:
                f.write(blob)
        report.append("Models: " + ", ".join(sorted(models)))
    else:
        report.append("Models: none in this pack (current models kept)")
    if "acronym_database.csv" in data:
        report.append(f"Database: {merge_pack_database(data['acronym_database.csv'])} new rows added (your own rows unchanged)")
    if "ocr_corrections.csv" in data:
        report.append(f"OCR fixes: {merge_pack_fixes(data['ocr_corrections.csv'])} added")
    if "ocr_ignore.csv" in data:
        report.append(f"Ignored readings: {merge_pack_ignore(data['ocr_ignore.csv'])} added")
    with open(KNOWLEDGE_INFO_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": info.get("version"), "created": info.get("created"), "created_by": info.get("created_by"),
                   "notes": info.get("notes", ""), "models": sorted(models), "pack_sha256": _sha256_file(path),
                   "installed": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, f, indent=1)
    reset_ocr_engine()
    return "\n".join(report)

def load_trained_models(folder):
    """Copy rec.onnx / det.onnx / cls.onnx / rec_keys.txt from a folder (Training Kit output) into config\\models."""
    found = [m for m in PACK_MODEL_FILES if os.path.isfile(os.path.join(folder, m))]
    if not any(m.endswith(".onnx") for m in found):
        raise ValueError("No rec.onnx, det.onnx, or cls.onnx in that folder.")
    if "rec.onnx" in found and "rec_keys.txt" not in found:
        raise ValueError("rec.onnx needs its rec_keys.txt beside it.")
    for m in found:
        if m.endswith(".onnx"):
            _check_onnx(os.path.join(folder, m))
    backup_knowledge(f"before loading models from {folder}")
    os.makedirs(MODELS_DIR, exist_ok=True)
    for m in found:
        shutil.copy2(os.path.join(folder, m), os.path.join(MODELS_DIR, m))
    reset_ocr_engine()
    return found

def knowledge_status():
    try:
        k = json.load(open(KNOWLEDGE_INFO_FILE, encoding="utf-8"))
        return f"Knowledge Pack {k.get('version')} (installed {k.get('installed')})"
    except Exception:
        models = [m for m in PACK_MODEL_FILES if os.path.isfile(os.path.join(MODELS_DIR, m))]
        return "No Knowledge Pack installed" + (f"; local models: {', '.join(models)}" if models else "; built-in models")

# ---- App icons (assets\scanner.ico, assets\trainer.ico; bundled into _internal\assets by the build) ----
ACTIVE_ICON = "scanner.ico"   # the Trainer sets "trainer.ico"

def asset_path(name):
    for base in (getattr(sys, "_MEIPASS", ""), BASE_DIR):
        p = os.path.join(base, "assets", name)
        if base and os.path.isfile(p):
            return p
    return None

def apply_window_icon(win, name=None):
    path = asset_path(name or ACTIVE_ICON)
    if not path:
        return
    def _set():
        try:
            win.iconbitmap(path)
        except Exception:
            pass
    _set()
    win.after(300, _set)   # CustomTkinter swaps in its own icon about 200 ms after a window opens

_ctk_toplevel_init = ctk.CTkToplevel.__init__
def _toplevel_init(self, *a, **k):
    _ctk_toplevel_init(self, *a, **k)
    apply_window_icon(self)
ctk.CTkToplevel.__init__ = _toplevel_init   # every pop-up window gets the app icon too

# ==============================================================================
# 7. DESKTOP GUI APPLICATION
# ==============================================================================
SETTINGS_FILE = os.path.join(SANDBOX_DIR, "settings.json")
ALL_TYPES = "All types"
STATUS_FILTERS = ["All statuses", "Needs choice", "New candidates", "Resolved", "Added manually",
                  "New since last scan", "Changed since last scan", "No longer found", "Errors / not scanned", "Excluded"]
MANUAL_MARK = "✍"
STATUS_ORDER = (("⛔", 0), ("⚠️", 1), ("🔍", 2), (MANUAL_MARK, 3), ("✅", 4), ("✖", 5), ("🚫", 6))
MANUAL_CATEGORIES = ["Acronym", "Abbreviation", "Unit", "Other"]
COLUMNS = (  # id, heading, base width, anchor
    ("term", "Term / Unit", 120, "w"),
    ("category", "Type", 170, "w"),
    ("count", "Count", 70, "center"),
    ("change", "Change", 130, "w"),
    ("status", "Status", 210, "w"),
    ("definition", "Definition", 360, "w"),
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

def trainer_available():
    if getattr(sys, "frozen", False):
        return os.path.exists(os.path.join(BASE_DIR, "AcronymHunterTrainer.exe"))
    return os.path.exists(os.path.join(BASE_DIR, "trainer_gui.py"))

class AcronymAppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Acronym Hunter {APP_VERSION}: acronyms, abbreviations and units (100% local)")
        apply_window_icon(self)
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
        self.app_cfg = load_app_settings()
        self.manual_items = {}   # term -> finding dict; kept across rescans until removed
        self.project = None      # open Project, or None for one-off scans
        self.project_stats = {}
        self.advanced_on = bool(self.settings.get("advanced", self.app_cfg["advanced_features_default"])) \
            if self.app_cfg["allow_advanced_toggle"] else self.app_cfg["advanced_features_default"]
        self.font_size = int(self.settings.get("font_size", FONT_DEFAULT))
        self.font_size = max(FONT_MIN, min(FONT_MAX, self.font_size))

        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=15, pady=(15, 8))

        self.btn_project = ctk.CTkButton(top, text="Project ▾", command=self.show_project_menu, fg_color="#1E3A8A", width=110, height=36)
        self.btn_project.pack(side="left", padx=5, pady=10)
        self.project_menu = tk.Menu(self, tearoff=0)

        self.btn_files = ctk.CTkButton(top, text="Select Files", command=self.select_files, width=150, height=36)
        self.btn_files.pack(side="left", padx=5, pady=10)

        self.btn_folder = ctk.CTkButton(top, text="Scan Folder", command=self.select_folder, width=130, height=36)
        self.btn_folder.pack(side="left", padx=5, pady=10)

        self.btn_export = ctk.CTkButton(top, text="Export CSV", command=self.export_csv, state="disabled", fg_color="green", width=130, height=36)
        self.btn_export.pack(side="left", padx=5, pady=10)

        self.btn_add = ctk.CTkButton(top, text="+ Add Item", command=self.open_add_item, fg_color="#B45309", width=120, height=36)
        self.btn_add.pack(side="left", padx=5, pady=10)

        self.btn_db = ctk.CTkButton(top, text="Edit Database CSV", command=lambda: self.open_file(DB_FILE), fg_color="#475569", width=160, height=36)
        self.btn_db.pack(side="right", padx=5, pady=10)
        self.btn_know = ctk.CTkButton(top, text="Knowledge", command=self.open_knowledge, fg_color="#0F766E", width=110, height=36)
        self.btn_know.pack(side="right", padx=5, pady=10)

        # Advanced tools: shown only when the Advanced switch is on
        self.btn_fixes = ctk.CTkButton(top, text="OCR Fixes", command=self.open_fix_manager, fg_color="#7C3AED", width=120, height=36)
        self.btn_trainer = None
        if trainer_available():   # only in the "WithTrainer" package (or when run from source)
            self.btn_trainer = ctk.CTkButton(top, text="Region Trainer", command=self.open_trainer, fg_color="#0F766E", width=130, height=36)
        self.adv_var = ctk.BooleanVar(value=self.advanced_on)
        self.sw_adv = ctk.CTkSwitch(top, text="Advanced", variable=self.adv_var, command=self.toggle_advanced, width=110)
        if self.app_cfg["allow_advanced_toggle"]:
            self.sw_adv.pack(side="right", padx=(12, 5), pady=10)

        self.lbl_project = ctk.CTkLabel(self, text="", font=("Arial", 13, "bold"), text_color="#1E3A8A")
        self.status = ctk.CTkLabel(self, text="Ready. 100% Local Sandbox Active (_local_sandbox).", font=("Arial", 13))
        self.status.pack(pady=(0, 4))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        atexit.register(self._release_project_lock)

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

        self.show_exc_var = ctk.BooleanVar(value=False)
        self.chk_exc = ctk.CTkCheckBox(fbar, text="Show Excluded", variable=self.show_exc_var, command=self.populate_table)
        self.chk_exc.pack(side="left", padx=(12, 4), pady=8)

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

        self.tree = ttk.Treeview(t_frame, columns=[c[0] for c in COLUMNS], show="headings", selectmode="extended")  # Ctrl/Shift+click: several rows
        for cid, label, width, anchor in COLUMNS:
            self.tree.column(cid, width=width, minwidth=50, anchor=anchor, stretch=(cid == "locations"))
        self.update_headings()

        self.tree.tag_configure("ambiguous", background="#FEF3C7", foreground="#92400E")
        self.tree.tag_configure("candidate", background="#E0F2FE", foreground="#075985")
        self.tree.tag_configure("resolved", background="#FFFFFF", foreground="#1E293B")
        self.tree.tag_configure("excluded", background="#F1F5F9", foreground="#94A3B8")
        self.tree.tag_configure("fileerror", background="#FEE2E2", foreground="#991B1B")
        self.tree.tag_configure("manual", background="#FEF9C3", foreground="#713F12")
        self.tree.tag_configure("gone", background="#E5E7EB", foreground="#6B7280")

        vsb = ttk.Scrollbar(t_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(t_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Control-a>", lambda _e: (self.tree.selection_set(self.tree.get_children()), "break")[1])

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

        self.lbl_act = ctk.CTkLabel(act, text="Select a row above (Ctrl+click or Shift+click for several):", font=("Arial", 12, "bold"))
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

        self.btn_exc = ctk.CTkButton(act, text="🚫 Exclude", command=self.exclude_term, state="disabled", fg_color="#DC2626", width=110)
        self.btn_exc.pack(side="right", padx=10, pady=12)

        self.apply_advanced_visibility()

    # ---------- advanced tools ----------
    def toggle_advanced(self):
        self.advanced_on = bool(self.adv_var.get())
        self.settings["advanced"] = self.advanced_on
        save_settings(self.settings)
        self.apply_advanced_visibility()

    def apply_advanced_visibility(self):
        """Show or hide Fix OCR, OCR Fixes, and Region Trainer."""
        for w in (self.btn_fixes, self.btn_trainer, self.btn_ocr):
            if w is not None:
                w.pack_forget()
        if self.advanced_on:
            self.btn_fixes.pack(side="right", padx=5, pady=10, after=self.btn_db)
            if self.btn_trainer is not None:
                self.btn_trainer.pack(side="right", padx=5, pady=10, after=self.btn_fixes)
            self.btn_ocr.pack(side="left", padx=5, pady=12, after=self.btn_save)

    # ---------- knowledge packs ----------
    def open_knowledge(self):
        if getattr(self, "know_win", None) is not None and self.know_win.winfo_exists():
            self.know_win.focus(); return
        win = ctk.CTkToplevel(self); self.know_win = win
        win.title("Knowledge"); win.geometry("600x500"); win.resizable(False, False)
        win.transient(self); win.after(100, win.lift)
        ctk.CTkLabel(win, text="Knowledge = trained OCR models + database + OCR fixes + ignore list",
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        lbl = ctk.CTkLabel(win, text="", justify="left", wraplength=560); lbl.pack(anchor="w", padx=16, pady=(0, 8))
        msg = ctk.CTkLabel(win, text="", justify="left", wraplength=560, text_color="#0F766E")
        def refresh(text=None):
            lbl.configure(text=knowledge_status() + f"\nBackups available for Undo: {len(list_knowledge_backups())}")
            if text is not None: msg.configure(text=text)
        def after_change(text):
            refresh(text)
            if self.project is not None and not self.project.read_only:
                if messagebox.askyesno("Rescan project?", "Knowledge changed. Rescan the open project now to apply it?", parent=win):
                    self.rescan_project()
        def install():
            path = filedialog.askopenfilename(parent=win, title="Install Knowledge Pack (from the approved SharePoint folder)",
                                              filetypes=[("Knowledge Pack", "*.zip")])
            if not path: return
            try:
                after_change(install_knowledge_pack(path))
            except PermissionError:
                messagebox.showerror("File in use", DB_LOCKED_MSG, parent=win)
            except Exception as e:
                log_error("Knowledge Pack install failed")
                messagebox.showerror("Not installed", f"{e}\n\nNothing was changed.", parent=win)
        def undo():
            what = restore_last_knowledge_backup()
            refresh(f"Restored the state from {what}." if what else "Nothing to undo.")
        ctk.CTkButton(win, text="Install Knowledge Pack...", command=install).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(win, text="Undo Last Knowledge Change", fg_color="#475569", command=undo).pack(fill="x", padx=16, pady=4)
        if self.advanced_on:
            ctk.CTkLabel(win, text="Trainer tools (Advanced)", font=("Arial", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
            def load_models():
                folder = filedialog.askdirectory(parent=win, title="Folder with rec.onnx / det.onnx (Training Kit output\\models)")
                if not folder: return
                try:
                    found = load_trained_models(folder)
                    after_change("Loaded " + ", ".join(found) + ". Score with tools\\evaluate.py; Undo puts the old models back.")
                except Exception as e:
                    log_error("Load trained models failed")
                    messagebox.showerror("Not loaded", f"{e}\n\nNothing was changed.", parent=win)
            def export():
                notes = notes_box.get().strip()
                name = f"AcronymHunter_Knowledge_{datetime.datetime.now():%Y.%m.%d-%H%M}.zip"
                path = filedialog.asksaveasfilename(parent=win, title="Save Knowledge Pack to the APPROVED SHAREPOINT folder",
                                                    initialfile=name, defaultextension=".zip", filetypes=[("Knowledge Pack", "*.zip")])
                if not path: return
                info = make_knowledge_pack(path, notes)
                refresh(f"Saved {os.path.basename(path)} (version {info['version']}, models: {', '.join(info['models']) or 'none'}).")
            ctk.CTkButton(win, text="Load Trained Models...", fg_color="#7C3AED", command=load_models).pack(fill="x", padx=16, pady=4)
            notes_box = ctk.CTkEntry(win, placeholder_text="Notes for this pack (what changed, score)")
            notes_box.pack(fill="x", padx=16, pady=(8, 2))
            ctk.CTkButton(win, text="Export Knowledge Pack...", fg_color="#B45309", command=export).pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(win, text="Knowledge Packs contain what was learned from internal documents. Save them ONLY to the "
                         "approved SharePoint folder. Never GitHub, email, or personal storage.",
                         text_color="#B45309", wraplength=560, justify="left").pack(anchor="w", padx=16, pady=(4, 0))
        msg.pack(anchor="w", padx=16, pady=(10, 0))
        refresh()

    # ---------- manual items ----------
    def open_add_item(self):
        if getattr(self, "add_win", None) is not None and self.add_win.winfo_exists():
            self.add_win.focus(); return
        win = ctk.CTkToplevel(self); self.add_win = win
        win.title("Add an item to the results"); win.geometry("560x430"); win.resizable(False, False)
        win.transient(self); win.after(100, win.lift)
        pad = {"padx": 16, "pady": (8, 0), "anchor": "w"}
        ctk.CTkLabel(win, text="Term (required)").pack(**pad)
        e_term = ctk.CTkEntry(win, width=520); e_term.pack(padx=16, pady=2)
        ctk.CTkLabel(win, text="Type").pack(**pad)
        c_cat = ctk.CTkComboBox(win, values=MANUAL_CATEGORIES, width=520); c_cat.set("Acronym"); c_cat.pack(padx=16, pady=2)
        ctk.CTkLabel(win, text="Definition").pack(**pad)
        e_def = ctk.CTkEntry(win, width=520); e_def.pack(padx=16, pady=2)
        ctk.CTkLabel(win, text="Where found (optional, e.g. 'Volume II, p.14')").pack(**pad)
        e_loc = ctk.CTkEntry(win, width=520); e_loc.pack(padx=16, pady=2)
        save_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="Also save to the database so future scans find it (needs a definition)",
                        variable=save_var).pack(padx=16, pady=(12, 0), anchor="w")
        msg = ctk.CTkLabel(win, text="", text_color="#DC2626"); msg.pack(padx=16, pady=(6, 0), anchor="w")

        def add():
            term, cat = fold(e_term.get().strip()), (c_cat.get().strip() or "Acronym")
            defn, loc = e_def.get().strip(), e_loc.get().strip()
            if not term:
                msg.configure(text="Enter a term."); return
            if term in self.results and not self.results[term].get("manual"):
                msg.configure(text=f"'{term}' is already in the results. Select it there to change its definition."); return
            if save_var.get() and not defn:
                msg.configure(text="A definition is needed to save it to the database."); return
            saved = False
            if save_var.get():
                rows = read_db_rows(); rows.append([term, cat, defn, "Include"]); write_db_rows(rows); saved = True
            item = {"category": cat, "count": 1, "locations": [loc or "Added manually"],
                    "definitions": [defn] if defn else [], "in_db": True, "excluded": False, "manual": True,
                    "selected_definition": defn or "[No definition given]",
                    "status": f"{MANUAL_MARK} Added manually" + (" (saved to DB)" if saved else "")}
            self.manual_items[term] = item
            self.results[term] = item
            self.save_project()
            self.selected_term = term
            self.refresh_type_options(); self.populate_table()
            self.btn_export.configure(state="normal")
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent"); btns.pack(fill="x", padx=16, pady=14)
        ctk.CTkButton(btns, text="Add to Results", command=add).pack(side="left")
        ctk.CTkButton(btns, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        e_term.focus_set()
        win.bind("<Return>", lambda _e: add())
        win._add_api = {"term": e_term, "cat": c_cat, "defn": e_def, "loc": e_loc, "save": save_var, "add": add, "msg": msg}

    def remove_manual_item(self):
        term = self.selected_term
        if not term or not self.results.get(term, {}).get("manual"): return
        self.manual_items.pop(term, None); self.results.pop(term, None)
        self.save_project()
        self.selected_term = None
        self.btn_exc.configure(text="🚫 Exclude", command=self.exclude_term, state="disabled")
        self.lbl_act.configure(text="Select a row above (Ctrl+click or Shift+click for several):")
        self.populate_table()

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
        fps = filedialog.askopenfilenames(title="Select Files", initialdir=self.start_dir(), filetypes=[("Supported", "*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif *.svg *.svgz *.emf *.wmf *.emz *.wmz")])
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
        self.run_job(lambda cb: analyze_batch(fps, cb))

    def run_job(self, job):
        """Run job(status_callback) -> results on a worker thread, then show them."""
        for b in (self.btn_files, self.btn_folder, self.btn_export, self.btn_project):
            b.configure(state="disabled")
        self.prog.configure(mode="indeterminate")
        self.prog.start()
        for i in self.tree.get_children(): self.tree.delete(i)
        threading.Thread(target=self.worker, args=(job,), daemon=True).start()

    def worker(self, job):
        try:
            results = job(lambda m: self.after(0, lambda: self.status.configure(text=m)))
            self.after(0, lambda: self.scan_done(results))
        except Exception as e:
            log_error("Scan failed")
            msg = f"{type(e).__name__}: {e}\n\nDetails saved to logs\\error.log"
            self.after(0, lambda: messagebox.showerror("Scan failed", msg))
            self.after(0, self.reset_ui)

    # ---------- projects ----------
    def show_project_menu(self):
        m, has, rw = self.project_menu, self.project is not None, self.project is not None and not self.project.read_only
        m.delete(0, "end")
        m.add_command(label="New Project...", command=self.new_project)
        m.add_command(label="Open Project...", command=self.open_project)
        m.add_separator()
        m.add_command(label="Rescan Project (changed files only)", command=self.rescan_project, state="normal" if rw else "disabled")
        m.add_command(label="Full Rescan (read every file again)", command=lambda: self.rescan_project(full=True), state="normal" if rw else "disabled")
        m.add_command(label='Clear "No longer found" items', command=self.clear_gone, state="normal" if rw else "disabled")
        m.add_separator()
        m.add_command(label="Close Project", command=self.close_project, state="normal" if has else "disabled")
        b = self.btn_project
        m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def new_project(self):
        folder = filedialog.askdirectory(title="Choose the folder that holds the project's documents", initialdir=self.start_dir())
        if not folder: return
        self.remember_dir(folder)
        name = os.path.basename(os.path.normpath(folder)) or "Project"
        path = os.path.join(folder, name + PROJECT_EXT)
        if os.path.exists(path):
            if messagebox.askyesno("Project exists", f"This folder already has a project:\n{path}\n\nOpen it?"):
                self.open_project(path)
            return
        if not self.close_project(): return
        proj = Project(path); proj.data = Project.new_data()
        try:
            proj.acquire_lock(); proj.save()
        except OSError as e:
            messagebox.showerror("Cannot create project", f"Could not write to this folder:\n{e}"); return
        self.project = proj
        self.manual_items = proj.data["manual"]
        messagebox.showinfo("Project created", f"Project file:\n{path}\n\nIt stores the terms found, your choices and the scan history. "
                            "It never stores sentences or document text. The first scan reads every file; later scans read only new or changed files.")
        self.rescan_project()

    def open_project(self, path=None):
        path = path or filedialog.askopenfilename(title="Open Project", initialdir=self.start_dir(),
                                                  filetypes=[("Acronym Hunter project", "*" + PROJECT_EXT)])
        if not path: return
        if not self.close_project(): return
        proj = Project(path)
        try:
            proj.load()
        except Exception as e:
            messagebox.showerror("Cannot open project", f"{type(e).__name__}: {e}"); return
        if not proj.acquire_lock():
            who = proj.locked_by or {}
            ans = messagebox.askyesnocancel("Project in use",
                f"{who.get('user', '?')} on {who.get('computer', '?')} has had this project open since {who.get('time', '?')}.\n\n"
                "Yes: open read-only (view and export only).\nNo: take over editing (only if they have finished).\nCancel: do not open.")
            if ans is None: return
            if ans: proj.read_only = True
            else: proj.acquire_lock(force=True)
        self.project = proj
        self.remember_dir(proj.root)
        self.manual_items = proj.data["manual"]
        self.project_stats = proj.data.get("last_stats", {})
        def job(cb):
            cb(f"Opening project '{proj.name}' from saved results...")
            res, _ = project_findings(proj, cb, rescan=False)
            apply_project_history(proj, res, update=False)
            return res
        self.run_job(job)

    def rescan_project(self, full=False):
        proj = self.project
        if proj is None or proj.read_only: return
        def job(cb):
            res, stats = project_findings(proj, cb, full=full)
            apply_project_history(proj, res, update=True)
            proj.data["last_stats"] = stats
            self.project_stats = stats
            return res
        self.run_job(job)

    def clear_gone(self):
        proj = self.project
        if proj is None or proj.read_only: return
        gone = [t for t, h in proj.data["history"].items() if h.get("state") == "gone"]
        if not gone:
            messagebox.showinfo("Nothing to clear", 'No "No longer found" items.'); return
        if not messagebox.askyesno("Clear items", f'Remove {len(gone)} "No longer found" item(s) from this project?'): return
        for t in gone:
            proj.data["history"].pop(t, None)
            if self.results.get(t, {}).get("gone"): self.results.pop(t, None)
        self.save_project(); self.populate_table()

    def close_project(self):
        """Close the open project (saving it). Returns False if the user cancels."""
        if self.project is None: return True
        if str(self.btn_project.cget("state")) == "disabled":
            messagebox.showwarning("Busy", "Wait for the scan to finish first."); return False
        self.save_project()
        self._release_project_lock()
        self.project, self.project_stats, self.manual_items, self.results = None, {}, {}, {}
        self.selected_term = None
        self.populate_table(); self.lbl_showing.configure(text="")
        self.status.configure(text="Project closed. Ready.")
        self.update_project_ui()
        return True

    def save_project(self):
        proj = self.project
        if proj is None or proj.read_only: return
        try:
            proj.save(); proj.acquire_lock(force=True)   # refresh lock time
        except OSError as e:
            messagebox.showerror("Project not saved", f"Could not save the project file:\n{e}")

    def _release_project_lock(self):
        if self.project is not None: self.project.release_lock()

    def on_close(self):
        if self.project is not None and str(self.btn_project.cget("state")) != "disabled":
            self.save_project()
        self._release_project_lock()
        self.destroy()

    def update_project_ui(self):
        proj = self.project
        if proj is None:
            self.lbl_project.pack_forget()
            self.btn_folder.configure(text="Scan Folder", command=self.select_folder)
            self.btn_files.configure(state="normal")
            self.btn_project.configure(text="Project ▾")
            return
        st = self.project_stats or {}
        bits = [f"Project: {proj.name}", proj.root]
        if proj.data.get("last_scan"): bits.append(f"last scan {proj.data['last_scan']}")
        if st: bits.append(f"{st.get('files', 0)} files ({st.get('scanned', 0)} read, {st.get('reused', 0)} unchanged, {st.get('removed', 0)} removed)")
        if proj.read_only:
            who = proj.locked_by or {}
            bits.append(f"READ-ONLY (in use by {who.get('user', '?')})")
        self.lbl_project.configure(text="  |  ".join(bits))
        self.lbl_project.pack(pady=(0, 2), before=self.status)
        self.btn_project.configure(text=f"{proj.name[:14]} ▾")
        self.btn_folder.configure(text="Rescan Project", command=self.rescan_project,
                                  state="disabled" if proj.read_only else "normal")
        self.btn_files.configure(state="disabled")

    def apply_saved_decisions(self):
        if self.project is None: return
        for term, choice in self.project.data["decisions"].items():
            d = self.results.get(term)
            if d and d.get("in_db") and not d.get("excluded") and not d.get("gone") and \
                    (choice == "Keep All Possibilities" or choice in d.get("definitions", [])):
                self._set_choice(d, choice)

    @staticmethod
    def _set_choice(data, choice):
        if choice == "Keep All Possibilities":
            data["selected_definition"] = "MULTIPLE: " + " | ".join(data["definitions"])
            data["status"] = "⚠️ MULTIPLE (Kept All)"
            return "ambiguous"
        data["selected_definition"] = choice
        data["status"] = "✅ User Selected"
        return "resolved"

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
        if c == "change":
            order = {"New": 0, "Changed": 1, "No longer found": 2, "Unchanged": 3}
            return (order.get(data.get("change", ""), 4), term.casefold())
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
            "Added manually": data.get("manual", False),
            "New since last scan": data.get("change") == "New",
            "Changed since last scan": data.get("change") == "Changed",
            "No longer found": data.get("gone", False),
            "Errors / not scanned": st.startswith("⛔"),
            "Excluded": data.get("excluded", False),
        }.get(wanted, True)

    @staticmethod
    def row_values(term, data):
        return (term, data["category"], data["count"], data.get("change", ""), data["status"],
                data["selected_definition"], "; ".join(data["locations"]))

    @staticmethod
    def row_tag(data):
        if data.get("excluded", False): return "excluded"
        if data.get("manual"): return "manual"
        if data.get("gone"): return "gone"
        st = data["status"]
        if st.startswith("⛔"): return "fileerror"
        if st.startswith("⚠️"): return "ambiguous"
        if st.startswith("🔍"): return "candidate"
        return "resolved"

    def scan_done(self, results):
        self.results = results
        for term, item in self.manual_items.items():   # manual items survive rescans
            if term not in self.results:
                self.results[term] = item
        self.apply_saved_decisions()
        self.save_project()
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
            self.tree.insert("", "end", iid=term, tags=(self.row_tag(data),), values=self.row_values(term, data))

        self.lbl_showing.configure(text=f"Showing {len(rows)} of {len(self.results)}" if self.results else "")
        if self.results:
            self.status.configure(text=f"Active Findings: {v_count} ({a_count} need choice, {c_count} new candidates) | Suppressed Exclusions: {e_count}")
        if v_count > 0: self.btn_export.configure(state="normal")
        if self.selected_term and self.tree.exists(self.selected_term):
            self.tree.selection_set(self.selected_term)
            self.tree.see(self.selected_term)

    def excludable(self, term):
        d = self.results.get(term)
        return bool(d) and not (d.get("excluded") or d.get("manual") or d.get("gone") or d.get("file_error"))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        if len(sel) > 1:   # several rows: only Exclude applies to a group
            n = sum(1 for t in sel if self.excludable(t))
            self.selected_term = sel[0]
            for w in (self.btn_apply, self.btn_save, self.btn_ocr, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.btn_exc.configure(text=f"🚫 Exclude {n}", command=self.exclude_term, state="normal" if n else "disabled")
            self.lbl_act.configure(text=f"{len(sel)} rows selected ({n} can be excluded):")
            return
        term = sel[0]
        self.selected_term = term
        data = self.results.get(term)
        if not data: return

        if data.get("file_error"):
            self.btn_exc.configure(text="🚫 Exclude", command=self.exclude_term)
            for w in (self.btn_exc, self.btn_apply, self.btn_save, self.btn_ocr, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.lbl_act.configure(text="File could not be read:")
            return

        if data.get("gone"):
            for w in (self.btn_exc, self.btn_apply, self.btn_save, self.btn_ocr, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.lbl_act.configure(text=f"'{term}' no longer found (last seen {data.get('last_seen', '?')}):")
            return

        if data.get("manual"):
            for w in (self.btn_apply, self.btn_save, self.btn_ocr, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.btn_exc.configure(text="Remove Item", command=self.remove_manual_item, state="normal")
            self.lbl_act.configure(text=f"Added manually '{term}':")
            return
        self.btn_exc.configure(text="🚫 Exclude", command=self.exclude_term)
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
        tag = self._set_choice(data, choice)
        if self.project is not None:
            self.project.data["decisions"][self.selected_term] = choice
            self.save_project()
        self.tree.item(self.selected_term, values=self.row_values(self.selected_term, data), tags=(tag,))

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
        self.tree.item(wrong, values=self.row_values(wrong, data), tags=("resolved",))
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
        self.tree.item(self.selected_term, values=self.row_values(self.selected_term, data), tags=("resolved",))
        self.entry_def.delete(0, "end")
        self.entry_def.configure(state="disabled")
        self.btn_save.configure(state="disabled"); self.btn_ocr.configure(state="disabled")

    def exclude_term(self):
        terms = [t for t in self.tree.selection() if self.excludable(t)]
        if not terms and self.selected_term and self.excludable(self.selected_term):
            terms = [self.selected_term]
        if not terms: return
        if len(terms) > 1:
            shown = ", ".join(terms[:12]) + (f" and {len(terms) - 12} more" if len(terms) > 12 else "")
            if not messagebox.askyesno("Exclude terms", f"Exclude {len(terms)} terms?\n\n{shown}\n\n"
                                       "They are saved to the database as Exclude rules, so future scans skip them. "
                                       "Show Excluded (or Status > Excluded) lists them again."):
                return
        items = []
        for term in terms:
            data = self.results[term]
            items.append((term, data["category"], data["definitions"][0] if data["definitions"] else "Excluded via GUI"))
        update_csv_exclusions(items)   # one database write for the whole group
        for term, _cat, reason in items:
            data = self.results[term]
            data["excluded"] = True
            data["in_db"] = True
            data["status"] = "🚫 Excluded by Rule"
            data["selected_definition"] = f"[EXCLUDED] {reason}"
        self.btn_exc.configure(text="🚫 Exclude", state="disabled")
        self.lbl_act.configure(text=f"Excluded {len(items)} term(s). Select a row above (Ctrl+click or Shift+click for several):")
        self.selected_term = None
        self.populate_table()

    def reset_ui(self):
        self.prog.stop()
        self.prog.configure(mode="determinate")
        self.prog.set(1)
        self.btn_files.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.btn_project.configure(state="normal")
        self.update_project_ui()

    def export_csv(self):
        path = filedialog.asksaveasfilename(initialdir=self.start_dir(), defaultextension=".csv", filetypes=[("CSV Report", "*.csv")], initialfile="Acronym_Report.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Term", "Category", "Count", "Change", "Status", "Definition", "Locations", "First seen", "Last seen"])
                for term, data in self.results.items():
                    if data.get("excluded", False): continue
                    w.writerow([term, data["category"], data["count"], data.get("change", ""), data["status"],
                                data["selected_definition"], "; ".join(data["locations"]),
                                data.get("first_seen", ""), data.get("last_seen", "")])
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")

def run_selftest(paths):
    os.makedirs(LOG_DIR, exist_ok=True)
    out = os.path.join(LOG_DIR, "selftest.txt")
    with open(out, "w", encoding="utf-8") as f:
        try:
            res = analyze_batch(paths, lambda m: f.write(m + "\n"))
            f.write(f"\nOCR models: {OCR_MODEL_INFO}\nKnowledge: {knowledge_status()}\nOCR settings: {json.dumps(OCR_CFG)}\n")
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
    if len(sys.argv) > 2 and sys.argv[1] == "--install-knowledge":   # used by build.ps1 -KnowledgePack
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "knowledge_install.txt"), "w", encoding="utf-8") as f:
            try:
                f.write(install_knowledge_pack(sys.argv[2]) + "\nINSTALL OK\n")
            except Exception:
                f.write(traceback.format_exc() + "INSTALL FAILED\n")
        sys.exit(0)
    try:
        app = AcronymAppGUI()
        app.mainloop()
    except Exception:
        log_error("Application failed to start")
        raise