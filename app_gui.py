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
for d in (SANDBOX_DIR, SANDBOX_TEMP):
    os.makedirs(d, exist_ok=True)

os.environ["USERPROFILE"] = SANDBOX_DIR
os.environ["HOME"] = SANDBOX_DIR
os.environ["APPDATA"] = os.path.join(SANDBOX_DIR, "appdata")
os.environ["LOCALAPPDATA"] = os.path.join(SANDBOX_DIR, "localappdata")
os.environ["TEMP"] = SANDBOX_TEMP
os.environ["TMP"] = SANDBOX_TEMP
os.environ["TMPDIR"] = SANDBOX_TEMP
os.environ["PYTHONPYCACHEPREFIX"] = os.path.join(SANDBOX_DIR, "pycache")

def cleanup_sandbox():
    if os.path.exists(SANDBOX_TEMP):
        shutil.rmtree(SANDBOX_TEMP, ignore_errors=True)

cleanup_sandbox()                 # clear leftovers from a killed session
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
import tkinter.font as tkfont
import zipfile
import threading
import subprocess
import cv2
import pymupdf as fitz  # Modern PyMuPDF import (no deprecation warnings)
import docx             # python-docx
import openpyxl
import numpy as np
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from pptx import Presentation
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
    with open(DB_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(starter_rows)

# RapidOCR loads lazily on first image (uses pre-bundled offline ONNX weights)
_ocr_engine = None
_ocr_lock = threading.Lock()

def get_ocr():
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            _ocr_engine = RapidOCR()
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

    with open(DB_FILE, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            term = (row.get("Term") or "").strip()
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
    if width < 1200:
        img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(gray)
    return cv2.fastNlMeansDenoising(contrasted, None, h=10, templateWindowSize=7, searchWindowSize=21)

def read_image_bytes(image_bytes):
    clean_img = enhance_image_for_ocr(image_bytes)
    if clean_img is None:
        return ""
    result, _ = get_ocr()(clean_img)
    if not result:
        return ""
    extracted = [line[1] for line in result if float(line[2]) > 0.50]
    return " ".join(extracted)

def ocr_office_media(filepath, media_prefix, status_callback, prefix):
    media_chunks = []
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            m_files = [
                f for f in z.namelist()
                if f.startswith(media_prefix) and os.path.splitext(f)[1].lower() in IMAGE_EXTS
            ]
            for idx, mf in enumerate(m_files, start=1):
                status_callback(f"{prefix} - OCR embedded image {idx}/{len(m_files)}...")
                img_bytes = z.read(mf)
                txt = read_image_bytes(img_bytes)
                if txt.strip():
                    media_chunks.append((f"{os.path.basename(filepath)} (Image: {os.path.basename(mf)})", txt))
    except Exception:
        pass
    return media_chunks

# ==============================================================================
# 5. LAYER 1: ALL-FORMAT UNPACKER (OPTIMIZED FOR 1,000+ PAGE DOCUMENTS)
# ==============================================================================
def extract_chunks_from_file(filepath, status_callback, file_idx, total_files):
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    chunks = []
    prefix = f"[{file_idx}/{total_files}] {filename}"

    # A. Standalone Images
    if ext in IMAGE_EXTS:
        status_callback(f"{prefix} - Running OCR on image...")
        with open(filepath, 'rb') as f:
            chunks.append((f"{filename} (Image)", read_image_bytes(f.read())))

    # B. PDF Documents (Smart Hybrid Mode for 1,000+ Page Speed)
    elif ext == '.pdf':
        doc = fitz.open(filepath)
        total_pages = len(doc)
        seen_xrefs = set()

        for i, page in enumerate(doc):
            pnum = i + 1
            if pnum == 1 or pnum % 5 == 0 or pnum == total_pages:
                status_callback(f"{prefix} - Scanning PDF Page {pnum}/{total_pages}...")

            digital_text = page.get_text()
            parts = [digital_text]
            page_images = page.get_images(full=True)

            # Case 1: Scanned page with little/no digital text -> Render full page at 200 DPI
            if len(digital_text.strip()) < 40:
                pix = page.get_pixmap(dpi=200)
                parts.append(read_image_bytes(pix.tobytes("png")))
            # Case 2: Digital page containing embedded figures/diagrams -> OCR each unique image
            elif page_images:
                for img_info in page_images:
                    xref = img_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    try:
                        base_img = doc.extract_image(xref)
                        if base_img and "image" in base_img:
                            parts.append(read_image_bytes(base_img["image"]))
                    except Exception:
                        pass

            chunks.append((f"{filename} (p.{pnum})", "\n".join(parts)))
        doc.close()

    # C. PowerPoint Presentations
    elif ext == '.pptx':
        prs = Presentation(filepath)
        total_slides = len(prs.slides)
        for i, slide in enumerate(prs.slides):
            snum = i + 1
            status_callback(f"{prefix} - Scanning Slide {snum}/{total_slides}...")
            sparts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    sparts.append(shape.text_frame.text)
                if shape.has_table:
                    for row in shape.table.rows:
                        sparts.append(" ".join(c.text for c in row.cells))
                if shape.shape_type == 13:
                    sparts.append(read_image_bytes(shape.image.blob))
            chunks.append((f"{filename} (Slide {snum})", "\n".join(sparts)))

    # D. Word Documents (.docx)
    elif ext == '.docx':
        status_callback(f"{prefix} - Reading Word document...")
        doc = docx.Document(filepath)
        p_block = []
        for idx, p in enumerate(doc.paragraphs, start=1):
            if p.text.strip():
                p_block.append(p.text)
            if idx % 25 == 0 and p_block:
                chunks.append((f"{filename} (Paras {idx-24}-{idx})", "\n".join(p_block)))
                p_block = []
        if p_block:
            chunks.append((f"{filename} (Document Text)", "\n".join(p_block)))
        for t_idx, table in enumerate(doc.tables, start=1):
            t_text = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
            chunks.append((f"{filename} (Table {t_idx})", "\n".join(t_text)))
        chunks.extend(ocr_office_media(filepath, "word/media/", status_callback, prefix))

    # E. Excel Workbooks (.xlsx)
    elif ext == '.xlsx':
        status_callback(f"{prefix} - Reading Excel workbook...")
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        for sname in wb.sheetnames:
            sheet = wb[sname]
            scells = []
            for row in sheet.iter_rows(values_only=True):
                for val in row:
                    if val is not None and not isinstance(val, (int, float)):
                        val_str = str(val).strip()
                        if val_str:
                            scells.append(val_str)
            if scells:
                chunks.append((f"{filename} ({sname})", "\n".join(scells)))
        wb.close()
        chunks.extend(ocr_office_media(filepath, "xl/media/", status_callback, prefix))

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

def analyze_batch(filepaths, status_callback):
    include_db, exclude_db, exclude_upper = load_database()
    all_terms = set(include_db.keys()) | set(exclude_db.keys())

    direct_pattern = None
    if all_terms:
        sorted_terms = sorted(all_terms, key=len, reverse=True)
        direct_pattern = re.compile(r'(?<!\w)(' + '|'.join([re.escape(t) for t in sorted_terms]) + r")(?:'?s)?(?!\w)")

    fuzzy_targets = {t: t for t in include_db.keys() if len(t) >= 3 and t.isupper()}

    unknown_acronym_re = re.compile(r'\b([A-Z][A-Z0-9/&]{1,7}s?)\b')
    unknown_unit_re = re.compile(r'(?<!\w)\d+(?:\.\d+)?\s*([a-zA-Z\u00b0\u03bc]{1,5}(?:/[a-zA-Z0-9\^]{1,4})?)\b')
    unknown_abbrev_re = re.compile(r'(?<!\w)([a-zA-Z]{1,4}/[a-zA-Z]{1,4}|[a-zA-Z]{2,6}\.)(?!\w)')

    findings = {}
    total = len(filepaths)

    for idx, filepath in enumerate(filepaths, start=1):
        try:
            chunks = extract_chunks_from_file(filepath, status_callback, idx, total)
        except Exception as e:
            log_error(f"Could not read {filepath}")
            record_file_error(findings, filepath, e)
            continue
        for loc_label, text in chunks:
            if not text.strip():
                continue

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
                    if best and best[1] >= 80:
                        record_included(findings, best[0], f"{loc_label} [OCR fix: {cand}]", include_db)
                        continue
                record_candidate(findings, cand, "Acronym (Candidate)", loc_label)

            for match in unknown_unit_re.finditer(text):
                ucand = match.group(1)
                if (ucand in include_db or ucand in exclude_db or
                        ucand.upper() in exclude_upper or ucand.lower() in NON_UNIT_WORDS or ucand.isdigit()):
                    continue
                record_candidate(findings, ucand, "Unit (Candidate)", loc_label)

            for match in unknown_abbrev_re.finditer(text):
                acand = match.group(1)
                base = acand.rstrip('.')
                if (acand in include_db or acand in exclude_db or base in include_db or base in exclude_db or
                        acand.upper() in exclude_upper or base.upper() in exclude_upper):
                    continue
                if acand.endswith('.') and acand[:-1].lower() in {"end", "out", "see", "all", "one", "two", "now"}:
                    continue
                record_candidate(findings, acand, "Abbreviation (Candidate)", loc_label)

    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

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
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Term", "Category", "Definition", "Action"])
        w.writerows(rows)
    os.replace(tmp, DB_FILE)

def read_db_rows():
    rows = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append([(r.get("Term") or "").strip(), r.get("Category") or "Acronym",
                             r.get("Definition") or "", r.get("Action") or "Include"])
    return rows

DB_LOCKED_MSG = "acronym_database.csv is open in another program (usually Excel). Close it and try again."

def update_csv_exclusion(term, cat, reason):
    rows = []
    found = False
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                t = (r.get("Term") or "").strip()
                if t == term:
                    r["Action"] = "Exclude"
                    found = True
                rows.append([t, r.get("Category", "Acronym"), r.get("Definition", ""), r.get("Action", "Include")])
    if not found:
        rows.append([term, cat.replace(" (Candidate)", ""), reason, "Exclude"])
    write_db_rows(rows)

# ==============================================================================
# 7. DESKTOP GUI APPLICATION
# ==============================================================================
SETTINGS_FILE = os.path.join(SANDBOX_DIR, "settings.json")
ALL_TYPES = "All types"
STATUS_FILTERS = ["All statuses", "Needs choice", "New candidates", "Resolved", "File errors", "Excluded"]
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

        self.entry_def = ctk.CTkEntry(act, placeholder_text="Definition to Include in DB...", width=230, state="disabled")
        self.entry_def.pack(side="left", padx=5, pady=12)

        self.btn_save = ctk.CTkButton(act, text="Include in DB", command=self.save_candidate, state="disabled", fg_color="#0284C7", width=105)
        self.btn_save.pack(side="left", padx=5, pady=12)

        self.btn_exc = ctk.CTkButton(act, text="🚫 Exclude", command=self.exclude_term, state="disabled", fg_color="#DC2626", width=100)
        self.btn_exc.pack(side="right", padx=10, pady=12)

    def _on_tk_error(self, exc_type, exc, tb):
        _excepthook(exc_type, exc, tb)
        if isinstance(exc, PermissionError):
            messagebox.showerror("Database locked", DB_LOCKED_MSG)
        else:
            messagebox.showerror("Error", f"{exc_type.__name__}: {exc}\n\nDetails saved to logs\\error.log")

    def open_file(self, path):
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.call(["open", path])
        else: subprocess.call(["xdg-open", path])

    def select_files(self):
        fps = filedialog.askopenfilenames(title="Select Files", filetypes=[("Supported", "*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif")])
        if fps: self.start_batch(list(fps))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if not folder: return
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
            "File errors": st.startswith("⛔"),
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
            for w in (self.btn_exc, self.btn_apply, self.btn_save, self.entry_def, self.combo):
                w.configure(state="disabled")
            self.lbl_act.configure(text="File could not be read:")
            return

        self.btn_exc.configure(state="disabled" if data.get("excluded", False) else "normal")

        if data["in_db"] and not data.get("excluded", False) and len(data["definitions"]) > 1:
            opts = list(data["definitions"]) + ["Keep All Possibilities"]
            self.combo.configure(state="normal", values=opts); self.combo.set(opts[0])
            self.btn_apply.configure(state="normal")
            self.entry_def.configure(state="disabled"); self.btn_save.configure(state="disabled")
            self.lbl_act.configure(text=f"Disambiguate '{term}':")
        elif not data["in_db"]:
            self.combo.configure(state="disabled", values=["Not in DB"]); self.combo.set("Not in DB")
            self.btn_apply.configure(state="disabled")
            self.entry_def.configure(state="normal"); self.entry_def.delete(0, "end")
            self.btn_save.configure(state="normal")
            self.lbl_act.configure(text=f"New Candidate '{term}':")
        else:
            self.combo.configure(state="disabled", values=data["definitions"][:1])
            if data["definitions"]: self.combo.set(data["definitions"][0])
            self.btn_apply.configure(state="disabled")
            self.entry_def.configure(state="disabled"); self.btn_save.configure(state="disabled")
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

    def save_candidate(self):
        if not self.selected_term: return
        nd = self.entry_def.get().strip()
        if not nd:
            messagebox.showwarning("Error", "Type a definition first.")
            return
        data = self.results[self.selected_term]
        cat = data["category"].replace(" (Candidate)", "")
        with open(DB_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([self.selected_term, cat, nd, "Include"])
        data["in_db"] = True
        data["excluded"] = False
        data["category"] = cat
        data["definitions"] = [nd]
        data["selected_definition"] = nd
        data["status"] = "✅ Added to DB"
        self.tree.item(self.selected_term, values=(self.selected_term, data["category"], data["count"], data["status"], data["selected_definition"], "; ".join(data["locations"])), tags=("resolved",))
        self.entry_def.delete(0, "end")
        self.entry_def.configure(state="disabled")
        self.btn_save.configure(state="disabled")

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
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Report", "*.csv")], initialfile="Acronym_Report.csv")
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