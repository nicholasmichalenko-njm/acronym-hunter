import base64
import collections
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
if __name__ == "__main__":   # the Trainer window does "import app_gui": reuse this module, never load a second copy
    sys.modules.setdefault("app_gui", sys.modules[__name__])

SANDBOX_DIR = os.path.join(BASE_DIR, "_local_sandbox")
SANDBOX_TEMP = os.path.join(SANDBOX_DIR, os.environ.get("SK_SANDBOX_TEMP", "temp"))   # 2.59.0: the Qt edition has its own
try:
    for d in (SANDBOX_DIR, SANDBOX_TEMP):
        os.makedirs(d, exist_ok=True)
except OSError as _e:
    _msg = (f"The app cannot write to its own folder:\n{BASE_DIR}\n\n"
            "Unzip the whole Stationkeeper folder to a location you can write to "
            "(for example Desktop or Documents), then run Stationkeeper.exe from there.\n\n"
            f"Details: {type(_e).__name__}")
    if os.name == "nt":                          # 3.14.0: a plain Windows message box, before Qt is loaded
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, _msg, "Stationkeeper cannot start", 0x10)
    else:
        sys.stderr.write(_msg + "\n")
    sys.exit(1)

# Redirect only temp-file locations into the app folder.
# USERPROFILE / APPDATA / LOCALAPPDATA are deliberately NOT redirected: Windows expands its
# Desktop, Documents and Downloads paths from them, so redirecting breaks the file picker
# ("location is not available"). None of the app's libraries write to those folders.
os.environ["TEMP"] = SANDBOX_TEMP
os.environ["TMP"] = SANDBOX_TEMP
os.environ["TMPDIR"] = SANDBOX_TEMP
os.environ["PYTHONPYCACHEPREFIX"] = os.path.join(SANDBOX_DIR, "pycache")

# 2.80.0: your data lives in "Stationkeeper Data" beside the program folder (datahome.py); updates never touch it
import datahome as _DH
DATA_DIR, DATA_WHY = _DH.resolve(BASE_DIR)
try:
    DATA_MOVED = _DH.ensure(DATA_DIR, BASE_DIR)
except OSError:
    DATA_DIR, DATA_WHY, DATA_MOVED = BASE_DIR, "program folder", []
if _DH.frozen():                  # 2.90.0: the program folder holds the program; read-me files in About Stationkeeper
    _DH.ensure_about(BASE_DIR)
    try:
        _DH.tidy_program_folder(BASE_DIR, DATA_DIR)
    except Exception:
        pass

def cleanup_sandbox():
    if os.path.exists(SANDBOX_TEMP):
        shutil.rmtree(SANDBOX_TEMP, ignore_errors=True)

cleanup_sandbox()                 # clear leftovers from a killed session
os.makedirs(SANDBOX_TEMP, exist_ok=True)   # recreate it: temp files must land here, never elsewhere on disk
atexit.register(cleanup_sandbox)

import traceback
import datetime
LOG_DIR = os.path.join(BASE_DIR, "logs")
import diag   # content-free diagnostics (logs\\events.jsonl): never file names, paths or document content

def log_error(context, with_traceback=True, area=None, **counts):
    """Record an error in logs\\events.jsonl. context must be a fixed message (tools\\check_diag.py enforces it):
    only the message, the error type, code locations and counts are kept."""
    exc = sys.exc_info() if with_traceback and sys.exc_info()[0] is not None else None
    if area is None:
        try:
            area = diag._clean_area(sys._getframe(1).f_code.co_name)
        except Exception:
            area = "app"
    diag.error(area, context, exc=exc, **counts)

def _excepthook(exc_type, exc, tb):
    diag.error("app", "Uncaught error", exc=(exc_type, exc, tb))

import secure                       # 2.97.0: SCIF-ready writes no logs at all, decided before anything is written
if secure.start(BASE_DIR, DATA_DIR):
    diag.off()
else:
    diag.setup(LOG_DIR, "?")
atexit.register(diag.shutdown)

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
import codecs
import unicodedata
import zipfile
import threading
import subprocess
import cv2
import pypdfium2 as pdfium        # Google PDFium (BSD-3 / Apache-2.0): PDF text, pictures, page images
import pypdfium2.raw as _pdfium_raw
import openpyxl
import numpy as np
from rapidfuzz import process, fuzz
import importlib.util
import equations as EQ             # equations and their symbols (equation-editor math, typed math, definitions)

DB_FILE = os.path.join(DATA_DIR, "acronym_database.csv")

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
            log_error("A CSV file is not UTF-8; read as Windows-1252", with_traceback=False, ext=".csv")
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
CONFIG_DIR = os.path.join(DATA_DIR, "config")
CHOICES_FILE = os.path.join(CONFIG_DIR, "choices.json")   # Apply Choice, kept for every later scan on this PC
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
    "tesseract_min_confidence": 0.30,  # Tesseract (US edition) line confidence floor; its scores run lower than RapidOCR's
    "doctr_enabled": 1,           # 1 = also read pictures with docTR (neural text finder + reader), add what Tesseract missed
    "doctr_min_confidence": 0.5,  # docTR word confidence floor (0-1)
    "doctr_extra_passes": 1,      # 1 = inverted pass for dark pictures and turned passes for vertical labels
    "doctr_override_confidence": 0.95,  # where Tesseract read text, a docTR word this sure that Tesseract lacks is added
    "line_removal_pass": 1,       # 1 = pictures with table or box lines are read a second time with the lines removed (2.22.0)
}
OCR_ENGINE_MAX_SIDE = 2000        # RapidOCR downsizes images whose longest side exceeds this

# ---- OCR engine choice ----
# "tesseract": Tesseract 5 (Apache 2.0; HP origin, developed by Google) with Google-trained models. US edition.
# "rapidocr":  RapidOCR + PaddleOCR PP-OCRv4 models (Apache 2.0; Baidu / RapidAI). Legacy edition.
# The build decides which engine ships; AH_OCR_ENGINE overrides for testing.
TESS_MIN_WORD_CONF = 30           # Tesseract word confidence (0-100) below which a word is dropped as noise
TESS_PSM = 11                     # page segmentation: 11 = sparse text (diagram labels anywhere on the image)
CUSTOM_TESS_MODEL = "acronym"     # config\models\acronym.traineddata = model fine-tuned on your Trainer samples

def _find_tesseract():
    for d in (os.environ.get("AH_TESSERACT_DIR", ""), os.path.join(getattr(sys, "_MEIPASS", ""), "tesseract"),
              os.path.join(BASE_DIR, "_internal", "tesseract"), os.path.join(BASE_DIR, "vendor", "tesseract")):
        if d and os.path.isfile(os.path.join(d, "tesseract.exe")):
            return d
    return None

TESS_DIR = _find_tesseract()

DOCTR_FILES = ("doctr_det.onnx", "doctr_reco.onnx", "doctr_models.json")

def doctr_folder_ok(d):
    """A docTR model folder is used only when every ONNX file matches the SHA-256 its doctr_models.json records."""
    import hashlib
    try:
        info = json.load(open(os.path.join(d, "doctr_models.json"), encoding="utf-8"))
        for key in ("doctr_det", "doctr_reco"):
            m = info["models"][key]
            path = os.path.join(d, m["onnx"])
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            if h.hexdigest().upper() != str(m["onnx_sha256"]).upper():
                return False
        return True
    except Exception:
        diag.swallowed()
        return False

def _find_doctr():
    """Folder with docTR's ONNX models. Trained models installed in config\\models\\doctr (Training Kit or a
    Knowledge Pack) win when their SHA-256 checks pass; otherwise the bundled models (Mindee, Apache 2.0)."""
    trained = os.path.join(CONFIG_DIR, "models", "doctr")
    if os.path.isfile(os.path.join(trained, "doctr_models.json")):
        if doctr_folder_ok(trained):
            return trained
        log_error("Trained docTR models failed their SHA-256 check; using the bundled models", with_traceback=False)
    for d in (os.environ.get("AH_DOCTR_DIR", ""), os.path.join(getattr(sys, "_MEIPASS", ""), "doctr"),
              os.path.join(BASE_DIR, "_internal", "doctr"), os.path.join(BASE_DIR, "vendor", "doctr")):
        if d and os.path.isfile(os.path.join(d, "doctr_models.json")):
            return d
    return None

DOCTR_DIR = _find_doctr()
EDITION_NAME = "US Classic (Tesseract only)" if not DOCTR_DIR else "US (Tesseract + docTR second reader)"

OCR_BACKEND = os.environ.get("AH_OCR_ENGINE") or ("tesseract" if TESS_DIR else "rapidocr")

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
        log_error("OCR settings file could not be read; using defaults")
    return cfg

OCR_CFG = load_ocr_settings()

APP_SETTINGS_FILE = os.path.join(CONFIG_DIR, "app_settings.json")
APP_DEFAULTS = {
    "advanced_features_default": False,   # Advanced tools (Fix OCR, OCR Fixes, Region Trainer) start hidden
    "allow_advanced_toggle": True,        # False = hide the Advanced switch; the default above is locked in
    "allow_training": True,               # False = no Trainer, no "Check in picture", no "Improve Reading" (nothing saved)
    "ocr_sandbox": True,                  # run Tesseract inside a Windows AppContainer with no network permission
    "ocr_sandbox_required": False,        # True = refuse to read pictures if the sandbox cannot start
    "usage_logging": True,                # False = do not record which controls are clicked (logs\\activity.jsonl)
    "allow_model_features": True,         # False = no docTR second reader and no math reader add-on (Tesseract only)
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
        log_error("App settings file could not be read; using defaults")
    return cfg

APP_CFG = load_app_settings()

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
        log_error("OCR fixes file could not be read")
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
        log_error("OCR ignore list could not be read")
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

def ocr_cutoff():
    """Confidence a reading needs to be kept by the scanner (engine-specific)."""
    return float(OCR_CFG["tesseract_min_confidence" if OCR_BACKEND == "tesseract" else "min_confidence"])

OCR_SANDBOX_STATUS = "not used yet"

def run_tesseract_tool(cmd, input_bytes=b"", timeout=180, read_dirs=(), write_dirs=()):
    """Run a Tesseract program (cmd[0] in TESS_DIR). Returns (exit code, stdout, stderr).
    Normally inside a Windows AppContainer with no network permission (sandbox.py). If the sandbox cannot start
    (for example the app folder is on a network share), it runs as a plain child process unless
    ocr_sandbox_required is true. The Tesseract build itself contains no network code either way."""
    global OCR_SANDBOX_STATUS
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    if APP_CFG["ocr_sandbox"] and os.name == "nt":
        try:
            import sandbox
            sandbox.grant(TESS_DIR)
            for d in read_dirs:
                sandbox.grant(d)
            for d in write_dirs:
                sandbox.grant(d, write=True)
            result = sandbox.run(list(cmd), input_bytes, timeout=timeout, env=env)
            OCR_SANDBOX_STATUS = "on: Windows AppContainer with no network permission"
            return result
        except TimeoutError:
            raise
        except Exception as e:
            log_error("OCR sandbox could not start")
            OCR_SANDBOX_STATUS = f"could not start ({type(e).__name__}: {e})"
            if APP_CFG["ocr_sandbox_required"]:
                raise RuntimeError("The OCR sandbox could not start and config\\app_settings.json requires it "
                                   "(ocr_sandbox_required). Text in pictures was not read.")
    elif not APP_CFG["ocr_sandbox"]:
        OCR_SANDBOX_STATUS = "off (config\\app_settings.json: ocr_sandbox = false)"
    r = subprocess.run(list(cmd), input=input_bytes, capture_output=True, timeout=timeout, env=env,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, r.stdout, r.stderr

_TESS_LEAD_ONE = re.compile(r"^[1l|](?=[A-Z]{2})")

class TesseractEngine:
    """Tesseract 5 run as a child process (tesseract.exe from the app's own folder; images go in through stdin,
    results come back through stdout, nothing is written to disk). Called like RapidOCR so the scanner and the
    Trainer work with either engine:
        engine(img)                -> ([[box, text, confidence 0-1], ...], None)   one entry per text line
        engine(img, use_det=False) -> ([[text, confidence 0-1]], None)             the whole image read as one line
    Tesseract has no network code path in this use: the app passes only "stdin", never a file name or URL."""

    def __init__(self, exe_dir):
        global OCR_MODEL_INFO
        self.exe = os.path.join(exe_dir, "tesseract.exe")
        custom = os.path.join(MODELS_DIR, CUSTOM_TESS_MODEL + ".traineddata")
        if os.path.isfile(custom):
            self.tessdata, self.lang = MODELS_DIR, CUSTOM_TESS_MODEL
            OCR_MODEL_INFO = "Tesseract 5 with your trained model (acronym.traineddata)"
        else:
            self.tessdata, self.lang = os.path.join(exe_dir, "tessdata"), "eng"
            OCR_MODEL_INFO = "Tesseract 5 with Google's English model (tessdata_best)"

    def _run(self, img, psm):
        img = cv2.copyMakeBorder(img, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255 if img.ndim == 2 else (255, 255, 255))
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            return []
        cmd = [self.exe, "stdin", "stdout", "--tessdata-dir", self.tessdata, "-l", self.lang, "--psm", str(psm),
               "--dpi", "300", "-c", "tessedit_create_tsv=1", "-c", "tessedit_create_txt=0"]
        code, out, err = run_tesseract_tool(cmd, buf.tobytes(), timeout=180,
                                            read_dirs=[self.tessdata] if self.tessdata != os.path.join(TESS_DIR, "tessdata") else [])
        if code != 0:
            raise RuntimeError("Tesseract failed: " + err.decode("utf-8", "replace").strip()[-300:])
        lines = {}
        for row in out.decode("utf-8", "replace").splitlines()[1:]:
            c = row.split("\t")
            if len(c) < 12 or c[0] != "5":
                continue
            text, conf = c[11].strip(), float(c[10])
            if not text or conf < TESS_MIN_WORD_CONF:
                continue
            text = _TESS_LEAD_ONE.sub("I", text)   # "1CD-204" -> "ICD-204": a diagram line touching a capital I
            x, y, w, h = (int(v) - (12 if i < 2 else 0) for i, v in enumerate(c[6:10]))
            lines.setdefault((c[2], c[3], c[4]), []).append((x, y, x + w, y + h, text, conf))
        import eqlayout as EL           # 2.55.0: equations by position rules (sub- and superscripts, fractions)
        flat = []
        for words in lines.values():
            words.sort(key=lambda t: t[0])
            x0, y0 = min(t[0] for t in words), min(t[1] for t in words)
            x1, y1 = max(t[2] for t in words), max(t[3] for t in words)
            conf = sum(t[5] for t in words) / len(words) / 100.0
            flat.append((x0, y0, x1, y1, EL.join_words(words), conf))
        if len(flat) > 1:
            try:
                gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                flat = EL.fractions(flat, gray[12:-12, 12:-12])   # word boxes are in unpadded coordinates
            except Exception:
                diag.swallowed()
        return [([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], t, c) for x0, y0, x1, y1, t, c in flat]

    def __call__(self, img, use_det=True, text_score=None, **_ignored):
        if not use_det:
            lines = self._run(img, 7)
            if not lines:
                return [], None
            return [[" ".join(t[1] for t in lines), sum(t[2] for t in lines) / len(lines)]], None
        floor = float(OCR_CFG["tesseract_min_confidence"]) if text_score is None else float(text_score)
        return [list(t) for t in self._run(img, TESS_PSM) if t[2] >= floor], None

def _build_ocr():
    """Tesseract (US edition) or RapidOCR (legacy edition), per OCR_BACKEND."""
    global OCR_MODEL_INFO
    if OCR_BACKEND == "tesseract":
        if not TESS_DIR:
            raise RuntimeError("Tesseract engine files are missing from this copy of the app.")
        return TesseractEngine(TESS_DIR)
    from rapidocr_onnxruntime import RapidOCR
    try:
        import onnxruntime as _ort   # ONNX Runtime telemetry (Windows TraceLogging) off
        _ort.disable_telemetry_events()
    except Exception:
        diag.swallowed()
        pass
    try:
        return _build_ocr_configured()
    except Exception:
        log_error("Custom OCR configuration failed; falling back to bundled models and default settings")
        OCR_MODEL_INFO = "bundled PP-OCRv4 (custom settings/models failed; see the logs folder)"
        return RapidOCR()

def _build_ocr_configured():
    global OCR_MODEL_INFO
    import yaml
    import rapidocr_onnxruntime as _ro
    from rapidocr_onnxruntime import RapidOCR
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
        log_error("Custom OCR model failed to load; using bundled models")
        engine = RapidOCR()
        OCR_MODEL_INFO = "bundled PP-OCRv4 (custom model failed to load; see the logs folder)"
    return engine

# 2.55.0: no AI and ML switch. Picture reading (ML) always runs; there is no generative AI in the app.
def ai_ml_on():
    return True

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
        diag.swallowed()
        header = []
    layout = [(db_field(h), h) for h in header if h]
    have = {f for f, _ in layout if f}
    layout += [(f, f) for f in DB_FIELDS if f not in have]   # add any missing core column at the end
    return layout

KNOWN_ACTION = "Omit"                 # database Action: the omit list (company names, locations...) (2.13.0)
KNOWN_BLANK = "(on the omit list)"
KNOWN_STATUS = "Found in omit list"
OMIT_REASON_COL = "Omit reason"
OMIT_REASONS = ["Company or organization", "Location", "Program or product", "Person or role", "Other"]

def load_database():
    include_db = {}
    exclude_db = {}
    exclude_upper = set()

    if not os.path.exists(DB_FILE):
        return include_db, exclude_db, exclude_upper

    import alt_forms
    alts_of = {}                                       # 2.26.0: primary -> its alternate forms
    for raw_row in read_csv_rows(DB_FILE):
        row = db_row(raw_row)
        cell, cell_alts = alt_forms.split_term(row.get("Term", ""))
        term = fold(cell)
        row_alts = cell_alts + alt_forms.parse_alts(raw_row.get(alt_forms.ALT_COL, ""))
        cat = row.get("Category") or "Acronym"
        defn = row.get("Definition", "")
        action = (row.get("Action") or "Include").capitalize()

        if not term:
            continue

        if action == "Exclude" or cat.lower() in {"exclude", "ignore", "noise"}:
            exclude_db[term] = {"category": cat, "definition": defn or "Excluded by user rule"}
            exclude_upper.add(term.upper())
        elif action.lower().startswith(("known", "omit")):   # 2.13.0: the omit list: recognized, kept, left off the lists
            if term not in include_db:
                include_db[term] = {"category": cat, "definitions": []}
            include_db[term]["known"] = True
            include_db[term]["omit_reason"] = (raw_row.get(OMIT_REASON_COL) or "").strip() or include_db[term].get("omit_reason", "")
            d = defn or KNOWN_BLANK
            if d not in include_db[term]["definitions"]:
                include_db[term]["definitions"].append(d)
        else:
            if not defn:
                continue
            if term not in include_db:
                include_db[term] = {"category": cat, "definitions": []}
            if defn not in include_db[term]["definitions"]:
                include_db[term]["definitions"].append(defn)
            for a in row_alts:
                alts_of.setdefault(term, {}).setdefault(fold(a), defn)

    for term, alts in alts_of.items():                 # alternate forms are looked for, and point to their primary
        for a, defn in alts.items():
            if a and a != term and a not in include_db and a not in exclude_db:
                include_db[a] = {"category": include_db[term]["category"], "definitions": [defn], "alt_of": term}
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
    if OCR_CFG["denoise_strength"] > 0 and OCR_BACKEND != "tesseract":   # Tesseract binarizes on its own; denoise only cost time
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
        if float(conf) < float(OCR_CFG["tesseract_min_confidence" if OCR_BACKEND == "tesseract" else "min_confidence"]) or not str(text).strip():
            continue
        if fold(str(text)).strip() in _OCR_IGNORE:   # marked "Not text" in the Trainer
            continue
        xs = [pt[0] for pt in box]; ys = [pt[1] for pt in box]
        out.append((min(xs) + x_off, min(ys) + y_off, max(xs) + x_off, max(ys) + y_off, str(text), float(conf)))
    return out

def remove_lines(gray):
    """The picture with long straight lines (table rules, box edges, connectors) painted white, or None when it has
    few lines. Text touching a line reads better once the line is gone (2.22.0). Rules only (OpenCV), no model."""
    h, w = gray.shape[:2]
    if h < 40 or w < 40:
        return None
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, w // 25), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 25)))
    mask = cv2.bitwise_or(cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk), cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk))
    if cv2.countNonZero(mask) < 0.002 * h * w:
        return None
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    out = gray.copy()
    out[mask > 0] = 255
    return out

def _merge_lines(kept, extra):
    """Add lines from another pass that the kept lines do not already hold (same place, same or longer reading)."""
    kept = list(kept)
    for item in sorted(extra, key=lambda t: -len(t[4])):   # longest reading of a line wins
        cx, cy, txt = (item[0] + item[2]) / 2, (item[1] + item[3]) / 2, item[4]
        duplicate = any(k[0] - 10 <= cx <= k[2] + 10 and k[1] - 10 <= cy <= k[3] + 10
                        and (txt in k[4] or k[4] in txt) for k in kept)
        if not duplicate:
            kept.append(item)
    return kept

def _tile_starts(length, tile, step):
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile + 1, step))
    if starts[-1] != length - tile:
        starts.append(length - tile)
    return starts

_doctr_engine = None
_doctr_failed = [False]
_allow_models = []

def _models_allowed():
    """Admin lock (config\\app_settings.json "allow_model_features": false): no docTR, no math reader."""
    if not _allow_models:
        try:
            _allow_models.append(bool(load_app_settings().get("allow_model_features", True)))
        except Exception:
            diag.swallowed()
            _allow_models.append(True)
    return _allow_models[0]

def doctr_active():
    if not _models_allowed():
        return False
    return bool(DOCTR_DIR) and OCR_BACKEND == "tesseract" and bool(int(OCR_CFG.get("doctr_enabled", 1))) and not _doctr_failed[0]

def get_doctr():
    global _doctr_engine
    with _ocr_lock:
        if _doctr_engine is None:
            import doctr_engine
            _doctr_engine = doctr_engine.DocTREngine(DOCTR_DIR)
    return _doctr_engine

def doctr_info():
    if not DOCTR_DIR:
        return "not bundled"
    try:
        info = json.load(open(os.path.join(DOCTR_DIR, "doctr_models.json"), encoding="utf-8"))
        import onnxruntime as _ort
        m = info["models"]
        trained = (f"trained here by the Training Kit ({info.get('trained', '?')}), "
                   if info.get("trained_by") else "exported by this project from Mindee's weights, ")
        return (f"docTR (Mindee, Apache 2.0) {m['doctr_det']['arch']} + {m['doctr_reco']['arch']} on ONNX Runtime {_ort.__version__}, "
                + trained + ("on" if doctr_active() else "off"))
    except Exception as e:
        diag.swallowed()
        return f"unavailable ({type(e).__name__})"

def _decode_rgb(image_bytes):
    arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    if arr is None:
        return None
    if arr.ndim == 2:
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    elif arr.shape[2] == 4:                       # transparent picture: flatten onto white
        a = arr[:, :, 3:4].astype(np.float32) / 255.0
        arr = (arr[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    if arr.dtype != np.uint8:
        arr = cv2.convertScaleAbs(arr, alpha=255.0 / max(1, int(arr.max())))
    return cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)

def _norm_tok(t):
    return re.sub(r"[^0-9a-z&]", "", t.lower())

def _doctr_extra(image_bytes, tess_lines, clean_shape):
    """Words docTR reads that Tesseract did not, as extra lines.
    - In a region Tesseract read, a docTR word is added only if Tesseract has no word there that matches it
      (capitals and punctuation ignored, or a close spelling). Tesseract stays the reader of record there.
    - In a region Tesseract found nothing, all of docTR's words are added: that is the text Tesseract missed."""
    if not doctr_active():
        return ""
    try:
        rgb = _decode_rgb(image_bytes)
        if rgb is None or min(rgb.shape[:2]) < 8:
            return ""
        check_cancel()
        lines = get_doctr().read(rgb, extra_passes=bool(int(OCR_CFG.get("doctr_extra_passes", 1))))
    except ScanCancelled:
        raise
    except Exception as e:
        diag.swallowed()
        _doctr_failed[0] = True
        log_error("docTR could not read a picture; it is switched off for this session")
        note_skip("docTR", f"docTR failed, so pictures were read by Tesseract only: {type(e).__name__}: {e}. Details are in the logs folder.")
        return ""
    from rapidfuzz import fuzz
    sx = clean_shape[1] / max(1, rgb.shape[1]); sy = clean_shape[0] / max(1, rgb.shape[0])
    floor = float(OCR_CFG.get("doctr_min_confidence", 0.5))
    out, seen = [], set()
    for ln in lines:
        box, text, conf = ln[0], ln[1], ln[2]
        words = ln[3] if len(ln) > 3 else [(t, conf) for t in text.split()]
        if fold(text).strip() in _OCR_IGNORE:
            continue
        xs = [p[0] * sx for p in box]; ys = [p[1] * sy for p in box]
        bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
        area = max(1.0, (bx1 - bx0) * (by1 - by0))
        near = [t for t in tess_lines
                if max(0, min(bx1, t[2]) - max(bx0, t[0])) * max(0, min(by1, t[3]) - max(by0, t[1])) > 0.3 * area]
        tess_toks = [x for x in (_norm_tok(x) for t in near for x in t[4].split()) if x]
        new = []
        for tok, wconf in words:
            n = _norm_tok(tok)
            if not n or wconf < floor:
                continue
            if tess_toks:
                # Tesseract read this region: keep its reading unless docTR is sure and has more than Tesseract
                # and its word contains Tesseract's (TWTA where Tesseract read WTA). A docTR word inside a Tesseract
                # word ("TES" in NOTES) or merely different ("SOV" for SOW) never counts.
                if (wconf < float(OCR_CFG.get("doctr_override_confidence", 0.95)) or any(n in x for x in tess_toks)
                        or not any(len(x) >= 2 and x in n for x in tess_toks)):
                    continue
            new.append(tok)
        ln_txt = " ".join(new)
        if ln_txt and ln_txt not in seen:
            seen.add(ln_txt); out.append(ln_txt)
    return "\n".join(out)

def _ocr_raw(image_bytes):
    clean_img = enhance_image_for_ocr(image_bytes)
    if clean_img is None:
        return ""
    lines = _ocr_lines(clean_img)          # whole-image pass (large text, layout)
    h, w = clean_img.shape[:2]
    tile, over = int(OCR_CFG["tile_size_px"]), int(OCR_CFG["tile_overlap_px"])
    if OCR_BACKEND == "rapidocr" and OCR_CFG["tile_large_images"] and max(h, w) > OCR_ENGINE_MAX_SIDE and 0 <= over < tile:
        # The engine shrank this image; re-read it in full-resolution tiles so small text survives.
        tiled = []
        for y in _tile_starts(h, tile, tile - over):
            for x in _tile_starts(w, tile, tile - over):
                tiled += _ocr_lines(clean_img[y:y + tile, x:x + tile], x, y)
        lines = _merge_lines(lines, tiled)
    lines.sort(key=lambda t: (round(t[1] / 20), t[0]))
    text = "\n".join(t[4] for t in lines)
    extra = _doctr_extra(image_bytes, lines, clean_img.shape)
    bare_text = ""
    if OCR_CFG.get("line_removal_pass", 1) and max(h, w) <= 4000:
        bare = remove_lines(clean_img)
        if bare is not None:     # kept apart from the first pass so docTR still adds what Tesseract missed there
            got = [t for t in _merge_lines(lines, _ocr_lines(bare))[len(lines):]]
            bare_text = "\n".join(t[4] for t in sorted(got, key=lambda t: (round(t[1] / 20), t[0])))
    return text + ("\n" + extra if extra else "") + ("\n" + bare_text if bare_text else "")

_OCR_CALLS = [0]   # pictures sent to OCR while scanning the current file (a file with 0 does not depend on the reader)

_typed_only = threading.local()   # set by typed_chunks(): read typed text only, skip every picture

def typed_chunks(filepath):
    """Typed text of a file without reading any picture (fast; for the preview pane). [(location label, text)]"""
    _typed_only.on = True
    try:
        return extract_chunks_from_file(filepath, lambda _m: None, 1, 1)
    finally:
        _typed_only.on = False

def rfp_chunks(filepath, say=None):
    """2.47.0: customer documents for the compliance review and Submission: typed text, plus scanned PDF pages read
    whole by OCR (AI and ML, when on for the effort), so no page is left out. Pictures inside typed pages are not read.
    say(text): 2.82.0, the reader's progress lines ("PDF page 3/40"), for a progress bar."""
    _typed_only.on = True
    _typed_only.pages = True
    try:
        return extract_chunks_from_file(filepath, say or (lambda _m: None), 1, 1)
    finally:
        _typed_only.on = False
        _typed_only.pages = False

def read_image_bytes(image_bytes, page=False):
    if getattr(_typed_only, "on", False) and not (page and getattr(_typed_only, "pages", False)):
        return ""
    _OCR_CALLS[0] += 1                 # the file has pictures: its saved results depend on the picture reader
    key = hashlib.sha1(image_bytes).hexdigest()
    if key not in _OCR_CACHE:
        try:
            _OCR_CACHE[key] = _ocr_raw(image_bytes)
        except Exception as e:
            log_error("OCR failed on one image")
            note_skip("OCR engine", f"OCR failed, so text inside images was not read: {type(e).__name__}: {e}. Details are in the logs folder.")
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
        text = _TC.a_text(para)                 # 2.55.0: a line break inside a paragraph is a space
        if text.strip():
            lines.append(text)
    return lines

def chart_lines(root):
    lines = drawingml_lines(root)  # titles, axis titles
    for cache in root.iter(_q("c", "strCache")):  # category labels, series names
        lines += [v.text for v in cache.iter(_q("c", "v")) if v.text and v.text.strip()]
    return lines

_CAPTION_RE = re.compile(r"^\s*(Figure|Fig\.|Table|Exhibit|Chart|Diagram)\s+[A-Z]?[\d.\-]+\s*[.:\u2013\u2014-]", re.I)

import textcheck as _TC   # 2.55.0: Word text as it reads (tabs and line breaks are spaces)

def word_paragraph_kinds(root):
    """(text, is_heading, kind) per Word paragraph. kind (2.23.0): "text" for running text, "table" inside a table,
    "figure" inside a text box or drawing, "caption" for a caption (Caption style, or "Figure 3." / "Table 2:" at the
    start). First use is judged in running text only."""
    W_P, W_T = _q("w", "p"), _q("w", "t")
    W_TBL, W_TXBX = _q("w", "tbl"), _q("w", "txbxContent")
    for para in root.iter(W_P):
        if _in_fallback(para):
            continue
        text = _TC.w_text(para, owner=para)     # 2.55.0: tabs and line breaks are spaces
        style = para.find("%s/%s" % (_q("w", "pPr"), _q("w", "pStyle")))
        sval = (style.get(_q("w", "val")) or "").lower() if style is not None else ""
        kind = "text"
        for anc in para.iterancestors():
            if anc.tag == W_TXBX or anc.tag.endswith("}txbx") or anc.tag.endswith("}drawing"):
                kind = "figure"; break
            if anc.tag == W_TBL:
                kind = "table"; break
        if kind == "text" and (sval.startswith(("caption", "tableoffigures")) or _CAPTION_RE.match(text)):
            kind = "caption"
        yield text, sval.startswith(("heading", "title")) and kind == "text", kind

def word_paragraphs(root):
    """(text, is_heading) per Word paragraph; text-box paragraphs counted once, deleted text ignored."""
    for text, is_heading, _kind in word_paragraph_kinds(root):
        yield text, is_heading

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

def _pil_png(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()

def render_svg(data):
    """Draw SVG bytes as PNG with Google Skia (BSD-3), from the bytes in memory. No resource loader is given, so
    images the SVG links to are never fetched; text is drawn with installed Windows fonts."""
    import skia
    dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(data))
    if dom is None:
        raise ValueError("SVG could not be parsed")
    size = dom.containerSize()
    w, h = size.width() or 800.0, size.height() or 600.0
    zoom = max(1.0, min(4.0, 2400.0 / max(w, h, 1)))
    surface = skia.Surface(max(1, int(w * zoom)), max(1, int(h * zoom)))
    with surface as canvas:
        canvas.clear(skia.ColorWHITE)
        canvas.scale(zoom, zoom)
        dom.setContainerSize(skia.Size(w, h))
        dom.render(canvas)
    return surface.makeImageSnapshot().encodeToData().bytes()

def render_pdf_page(path, index, dpi):
    """One PDF page as a PIL image (PDFium)."""
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[index]
        try:
            return page.render(scale=dpi / 72.0).to_pil().convert("RGB")
        finally:
            page.close()
    finally:
        doc.close()

def pdf_page_count(path):
    doc = pdfium.PdfDocument(path)
    try:
        return len(doc)
    finally:
        doc.close()

def render_vector(data, ext):
    """Draw a vector graphic as PNG bytes for OCR: SVG via Google Skia, EMF/WMF via Windows GDI (Pillow)."""
    data = _maybe_gunzip(data)
    if ext in (".svg", ".svgz"):
        return render_svg(data)
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
    if getattr(_typed_only, "on", False):
        return
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
                    diag.swallowed()
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
def _outer_maths(root):
    """Equation-editor equations (m:oMath) that are not inside another one and not in a Fallback copy."""
    M = EQ._m("oMath")
    for om in root.iter(M):
        if _in_fallback(om) or any(a.tag == M for a in om.iterancestors()):
            continue
        yield om

def _eq_chunk_text(om):
    linear = " ".join(EQ.omml_text(om).split())
    return linear, linear + "\t" + "|".join(EQ.omml_symbols(om))

def _is_equation(linear):
    return any(r in linear for r in EQ.RELATIONS) or bool(re.search(r"[∑∫∏√]|\)/\(", linear))

def omml_chunks(root, label, chunks):
    """Equation-editor equations in one part (a slide, a header): exact, read from the math markup."""
    for om in _outer_maths(root):
        linear, text = _eq_chunk_text(om)
        if linear and _is_equation(linear):
            chunks.append((label + EQ.EQ_LABEL, text))

def docx_math(body, filename, chunks):
    """Word equations with their paragraph location, and nomenclature tables whose symbol cells are equations."""
    W_P, W_T, W_TC, W_TR = _q("w", "p"), _q("w", "t"), _q("w", "tc"), _q("w", "tr")
    idx, heading, defs = 0, "", []
    for para in body.iter(W_P):
        if _in_fallback(para):
            continue
        idx += 1
        style = para.find("%s/%s" % (_q("w", "pPr"), _q("w", "pStyle")))
        if style is not None and (style.get(_q("w", "val")) or "").lower().startswith(("heading", "title")):
            heading = _TC.w_text(para).strip() or heading
        for om in _outer_maths(para):
            if next(om.iterancestors(W_P), None) is not para:
                continue
            linear, text = _eq_chunk_text(om)
            if linear and _is_equation(linear):
                where = f"section '{heading[:60]}', " if heading else ""
                chunks.append((f"{filename} ({where}para {idx})" + EQ.EQ_LABEL, text))
    for tr in body.iter(W_TR):   # symbol in one cell (as an equation or text), meaning in another
        cells = []
        for tc in tr.iter(W_TC):
            math = " ".join(" ".join(EQ.omml_text(om).split()) for om in _outer_maths(tc)).strip()
            words = " ".join(_TC.w_text(tc).split())
            cells.append((math, words))
        if len(cells) >= 2:
            sym_cell = next((m for m, w in cells if m and not w and not _is_equation(m)), None)
            meaning = next((w for m, w in cells if w and not m and len(w.split()) >= 1 and w[:1].isalpha()), None)
            if sym_cell and meaning:
                defs.append((EQ.normalize_symbol(sym_cell), meaning))
    if defs:
        chunks.append((filename + EQ.DEF_LABEL, "\n".join(f"{a}\t{b}" for a, b in dict.fromkeys(defs))))

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
                omml_chunks(root, f"{filename} ({tag})", chunks)
            except Exception as e:
                log_error("PowerPoint slide could not be fully read", ext=".pptx")
                note_skip(f"{filename} (Slide {n})", f"Slide could not be fully read: {type(e).__name__}: {e}")
        # Logos and graphics placed on layouts/masters appear on many slides; scan each once.
        for lpath in sorted(names):
            m = re.match(r"ppt/slide(Layout|Master)s/slide(?:Layout|Master)(\d+)\.xml$", lpath)
            if m:
                try:
                    part_images(z, lpath, _xml(z, lpath), f"{filename} (Slide {m.group(1).lower()} {m.group(2)}", chunks, seen)
                except Exception:
                    log_error("PowerPoint layout picture could not be read", ext=".pptx")

def extract_docx(filepath, filename, status_callback, prefix, chunks):
    with zipfile.ZipFile(filepath) as z:
        names = set(z.namelist())
        status_callback(f"{prefix} - Reading Word body...")
        body = _xml(z, "word/document.xml")
        block, start, heading, idx, cur = [], 1, "", 0, "text"
        tags = {"text": "", "table": "table, ", "figure": "text box, ", "caption": "caption, "}

        def flush(end):
            if block:
                where = f"section '{heading[:60]}', " if heading else ""
                chunks.append((f"{filename} ({where}{tags[cur]}para {start}-{end})", "\n".join(block)))

        for text, is_heading, kind in word_paragraph_kinds(body):
            idx += 1
            if text.strip() and (kind != cur or is_heading):   # tables, text boxes and captions get their own passages
                flush(idx - 1)
                block, start, cur = [], idx, kind
                if is_heading:
                    heading = text.strip()
            if text.strip():
                block.append(text)
            if len(block) >= 25:
                flush(idx)
                block, start = [], idx + 1
        flush(idx)
        seen = set()
        part_images(z, "word/document.xml", body, f"{filename} (Body", chunks, seen)
        docx_math(body, filename, chunks)

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
                log_error("Word part could not be read", ext=".docx")
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
                    log_error("Excel part could not be read", ext=".xlsx")
                    note_skip(f"{filename} ({sname})", f"{kind} could not be read: {type(e).__name__}: {e}")

def _pdf_page_text(page):
    tp = page.get_textpage()
    try:
        # 2.50.0: PDFium marks a hyphen at a line break as U+FFFE (shown as a box, and refused by Excel): keep a hyphen
        return tp.get_text_range().replace("\r\n", "\n").replace("\r", "\n").replace("\ufffe", "-").replace("\uffff", "")
    finally:
        tp.close()

def extract_pdf(filepath, filename, status_callback, prefix, chunks):
    """PDF text and pictures with Google PDFium (pypdfium2). The file is only read."""
    doc = pdfium.PdfDocument(filepath)
    try:
        total_pages = len(doc)
        seen_images = set()
        for i in range(total_pages):
            check_cancel()
            pnum = i + 1
            if pnum == 1 or pnum % 5 == 0 or pnum == total_pages:
                status_callback(f"{prefix} - PDF page {pnum}/{total_pages}...")
            try:
                page = doc[i]
                try:
                    digital_text = _pdf_page_text(page)
                    parts = [digital_text]
                    if len(digital_text.strip()) < OCR_CFG["scanned_page_max_chars"]:  # scanned page: OCR it whole
                        pil = page.render(scale=int(OCR_CFG["pdf_scan_dpi"]) / 72.0).to_pil().convert("RGB")
                        parts.append(read_image_bytes(_pil_png(pil), page=True))
                    else:  # digital page: OCR each embedded figure once per document
                        for obj in page.get_objects(filter=[_pdfium_raw.FPDF_PAGEOBJ_IMAGE], max_depth=5):
                            try:
                                pil = obj.get_bitmap(render=False).to_pil()
                                key = hashlib.sha1(pil.tobytes()).hexdigest()
                                if key in seen_images:
                                    continue
                                seen_images.add(key)
                                if pil.mode not in ("RGB", "L"):
                                    pil = pil.convert("RGB")
                                parts.append(read_image_bytes(_pil_png(pil)))
                            except ScanCancelled:
                                raise
                            except Exception:
                                diag.swallowed()
                                pass
                    chunks.append((f"{filename} (p.{pnum})", "\n".join(parts)))
                finally:
                    page.close()
            except ScanCancelled:
                raise
            except Exception as e:
                log_error("PDF page could not be read", ext=".pdf")
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
    key = f"[Error] {os.path.basename(filepath)}"
    findings[key] = {
        "category": "File Error", "count": 1, "locations": [filepath],
        "definitions": [], "in_db": True, "excluded": False, "file_error": True,
        "selected_definition": (exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}")[:300], "status": "Could not read file"
    }

def record_skip(findings, label, reason):
    key = f"[Not scanned] {label}"
    if key not in findings:
        findings[key] = {
            "category": "Not Scanned", "count": 1, "locations": [label],
            "definitions": [], "in_db": True, "excluded": False, "file_error": True,
            "selected_definition": reason, "status": "Not scanned"
        }

# ==============================================================================
# 5c. CLIENT ACRONYM LISTS (from RFPs): optional; when loaded, their definitions take precedence
# ==============================================================================
CLIENT_DB = {}   # fold(term) -> {"term": as written, "definitions": [...], "sources": [list names]}
CLIENT_LIST_EXTS = {".csv", ".tsv", ".txt", ".xlsx", ".docx", ".pdf"}
CLIENT_TAG, DB_TAG = "[Client] ", "[Database] "
_TERM_HDR = re.compile(r"^(acronyms?|abbreviations?|abbrev\.?|terms?|items?|symbols?|acronym\s*/\s*abbreviation)$", re.I)
_DEF_HDR = re.compile(r"^(definitions?|meanings?|descriptions?|expansions?|full\s+(form|name|term)|spelled\s+out|stands\s+for)$", re.I)
_LINE_SEPS = ("\t", " – ", " — ", " - ", " = ", ": ")

def set_client_lists(lists):
    """Rebuild CLIENT_DB from [{"name": ..., "rows": [[term, definition], ...]}]. Empty list = no client lists."""
    CLIENT_DB.clear()
    for lst in lists or []:
        for term, defn in lst.get("rows", []):
            key = fold(term).strip()
            if not key or not defn:
                continue
            e = CLIENT_DB.setdefault(key, {"term": key, "definitions": [], "sources": []})
            if defn.casefold() not in {x.casefold() for x in e["definitions"]}:
                e["definitions"].append(defn)
            if lst.get("name") not in e["sources"]:
                e["sources"].append(lst.get("name"))
    return CLIENT_DB

def _clean_pair(term, defn):
    t = re.sub(r"\s+", " ", fold(str(term or ""))).strip().strip(":–—-").strip()
    d = re.sub(r"\s+", " ", fold(str(defn or ""))).strip().strip(":–—-").strip()
    if not (1 <= len(t) <= 25) or not re.search(r"[^\W\d_]", t) or len(d) < 2 or t.casefold() == d.casefold():
        return None
    if _TERM_HDR.match(t) or _DEF_HDR.match(d) or len(t.split()) > 4:
        return None
    return t, d

def _pairs_from_table(rows):
    """Rows of cell strings -> (term, definition). Finds header columns by name, else uses the first two filled columns."""
    rows = [[(c or "").strip() if isinstance(c, str) else ("" if c is None else str(c)) for c in r] for r in rows]
    ti = di = None
    for r in rows[:3]:
        for i, c in enumerate(r):
            if ti is None and _TERM_HDR.match(c): ti = i
            elif di is None and _DEF_HDR.match(c): di = i
        if ti is not None and di is not None:
            break
    out = []
    for r in rows:
        if ti is not None and di is not None and max(ti, di) < len(r):
            pair = _clean_pair(r[ti], r[di])
        else:
            filled = [c for c in r if c]
            pair = _clean_pair(filled[0], " ".join(filled[1:])) if len(filled) >= 2 else None
        if pair:
            out.append(pair)
    return out

def _pair_from_line(line, strict=False):
    line = line.strip()
    for sep in _LINE_SEPS:
        if sep in line:
            t, d = line.split(sep, 1)
            break
    else:
        m = re.match(r"^(\S{1,25})\s{2,}(.+)$", line) or (None if strict else re.match(r"^([A-Z][A-Za-z0-9&/.\-]{1,15})\s+(.{3,})$", line))
        if not m:
            return None
        t, d = m.group(1), m.group(2)
    if strict and not re.search(r"[A-Z]", t):
        return None
    return _clean_pair(t, d)

def _pdf_table_rows(page):
    """Rows of cells from a PDF page. PDFium reports each run of text with its box; runs on the same line that sit
    far apart are separate cells. Recovers two-column tables (TERM | definition) without a table library."""
    tp = page.get_textpage()
    try:
        segs = []
        for k in range(tp.count_rects()):
            left, bottom, right, top = tp.get_rect(k)
            h = top - bottom
            txt = tp.get_text_bounded(left + 0.5, bottom + h * 0.25, right - 0.5, top - h * 0.25).replace("\ufffe", "-").strip()
            if txt:
                segs.append((left, bottom, right, top, " ".join(txt.split())))
    finally:
        tp.close()
    lines = []
    for seg in sorted(segs, key=lambda x: (-(x[1] + x[3]) / 2, x[0])):
        mid = (seg[1] + seg[3]) / 2
        for line in lines:
            if line[0][1] <= mid <= line[0][3]:
                line.append(seg); break
        else:
            lines.append([seg])
    rows = []
    for line in lines:
        line.sort(key=lambda x: x[0])
        height = max(1.0, max(x[3] - x[1] for x in line))
        cells, cur, prev_right = [], "", None
        for left, _b, right, _t, txt in line:
            if prev_right is not None and left - prev_right > 1.2 * height:
                cells.append(cur); cur = txt
            else:
                cur = (cur + " " + txt).strip()
            prev_right = right
        cells.append(cur)
        rows.append(cells)
    return rows

CLIENT_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")

def parse_client_text(text):
    """(term, definition) pairs from pasted or typed text (2.28.0): rows pasted from Excel or Word (tabs), lines like
    'ACR - definition', 'ACR: definition', 'ACR  definition', and 'Spelled Out Words (ACR)' in running text."""
    lines = [l for l in (text or "").splitlines() if l.strip()]
    pairs = []
    if lines and sum("\t" in l for l in lines) >= len(lines) / 2:
        pairs = _pairs_from_table([l.split("\t") for l in lines])
    else:
        for l in lines:
            p = _pair_from_line(l, strict=True)            # "ACR - definition", "ACR: definition", "ACR  definition"
            if p is None:
                m = re.match(r"^\s*([A-Za-z0-9&/.\-]{2,16})\s+(.{3,})$", l)
                t = m.group(1) if m else ""
                if m and (sum(c.isupper() for c in t) >= 2 or any(c.isdigit() for c in t)) and not t.isdigit():
                    p = _clean_pair(t, m.group(2))         # "ACR definition": only when it looks like an acronym
            if p:
                pairs.append(p)
    try:
        import custdefs
        have = {t.casefold() for t, _d in pairs}
        for term, hits in custdefs.extract([("Pasted", text or "")]).items():
            if term.casefold() not in have and hits:
                pairs.append([term, hits[0]["definition"]]); have.add(term.casefold())
    except Exception:
        diag.swallowed()
    seen, out = set(), []
    for t, d in pairs:
        k = (t.casefold(), d.casefold())
        if k not in seen:
            seen.add(k); out.append([t, d])
    return out

def client_list_pictures(path):
    """Text of a scanned PDF list or a picture of a list, read with the picture reader (2.28.0). '' when AI and ML are
    off for this effort or the file has no pictures to read."""
    ext = os.path.splitext(path)[1].lower()
    texts = []
    if ext in CLIENT_IMAGE_EXTS:
        with open(path, "rb") as f:
            texts.append(read_image_bytes(f.read()))
    elif ext == ".pdf":
        doc = pdfium.PdfDocument(path)
        try:
            for i in range(min(len(doc), 30)):
                page = doc[i]
                try:
                    pil = page.render(scale=int(OCR_CFG.get("pdf_scan_dpi", 300)) / 72.0).to_pil().convert("RGB")
                finally:
                    page.close()
                b = io.BytesIO(); pil.save(b, "PNG")
                texts.append(read_image_bytes(b.getvalue()))
        finally:
            doc.close()
    return "\n".join(t for t in texts if t)

def parse_client_list(path, pictures=True):
    """(term, definition) pairs from a client acronym list: CSV/TSV/TXT, Excel, Word (tables or 'TERM - definition'
    lines), or PDF (tables, else lines). Files are only read; parsing uses the same hardened readers as scanning.
    2.28.0: a scanned PDF with no typed text, or a picture of a list, is read with the picture reader (pictures=True)."""
    ext = os.path.splitext(path)[1].lower()
    pairs = []
    if ext in CLIENT_IMAGE_EXTS:
        return parse_client_text(client_list_pictures(path)) if pictures else []
    if ext in (".csv", ".tsv"):
        text, delim = _decode_csv(path)
        pairs = _pairs_from_table(list(csv.reader(io.StringIO(text, newline=""), delimiter="\t" if ext == ".tsv" else delim)))
    elif ext == ".txt":
        text, _ = _decode_csv(path)
        lines = [l for l in text.splitlines() if l.strip()]
        if sum("\t" in l for l in lines) > len(lines) / 2:
            pairs = _pairs_from_table([l.split("\t") for l in lines])
        else:
            pairs = [p for p in (_pair_from_line(l) for l in lines) if p]
    elif ext == ".xlsx":
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        try:
            for ws in wb.worksheets:
                pairs += _pairs_from_table([list(r) for r in ws.iter_rows(values_only=True)])
        finally:
            wb.close()
    elif ext == ".docx":
        W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(path) as z:
            root = _xml(z, "word/document.xml")
        text_of = lambda el: _TC.w_text(el)
        for tbl in root.iter(W + "tbl"):
            pairs += _pairs_from_table([[text_of(tc) for tc in tr.iter(W + "tc")] for tr in tbl.iter(W + "tr")])
        body = root.find(W + "body")
        for para in (body if body is not None else []):
            if para.tag == W + "p":
                p = _pair_from_line(text_of(para), strict=True)
                if p:
                    pairs.append(p)
    elif ext == ".pdf":
        doc = pdfium.PdfDocument(path)
        try:
            rows, lines = [], []
            for i in range(len(doc)):
                page = doc[i]
                try:
                    rows += _pdf_table_rows(page)
                    lines += _pdf_page_text(page).splitlines()
                finally:
                    page.close()
            pairs = _pairs_from_table([r for r in rows if len(r) >= 2])
            if not pairs:
                pairs = [p for p in (_pair_from_line(l, strict=True) for l in lines) if p]
        finally:
            doc.close()
        if not pairs and pictures and not "".join(lines).strip():   # a scanned list: no typed text at all
            pairs = parse_client_text(client_list_pictures(path))
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    seen, out = set(), []
    for t, d in pairs:
        k = (t.casefold(), d.casefold())
        if k not in seen:
            seen.add(k); out.append([t, d])
    return out

def apply_client_overlay(findings, m):
    """Client definitions take precedence. Each matching row shows the client meaning(s) first, labeled, with any
    different database meanings after them, so the user can still pick."""
    if not CLIENT_DB:
        return findings
    db_include = m.get("db_include", {})
    for term, d in findings.items():
        c = CLIENT_DB.get(fold(term).strip())
        if not c or d.get("file_error"):
            continue
        cdefs = c["definitions"]
        cset = {x.casefold() for x in cdefs}
        dbdefs = [x for x in db_include.get(term, {}).get("definitions", []) if x.casefold() not in cset]
        d.update({"client": True, "client_definitions": cdefs, "db_definitions": dbdefs, "client_sources": c["sources"],
                  "excluded": False, "in_db": True,
                  "definitions": [CLIENT_TAG + x for x in cdefs] + [DB_TAG + x for x in dbdefs]})
        if d["category"].endswith("(Candidate)"):
            d["category"] = d["category"].replace(" (Candidate)", "")
        if len(cdefs) == 1:
            d["selected_definition"] = cdefs[0]
            d["status"] = "Client list (database differs)" if dbdefs else "Client list"
        else:
            d["selected_definition"] = f"MULTIPLE ({len(cdefs)} client meanings) - Choose: " + " OR ".join(cdefs)
            d["status"] = f"CHOOSE (client list: {len(cdefs)} meanings)"
    return findings

def build_matcher():
    """Load the database, client lists, corrections, ignore list, and patterns once per scan."""
    refresh_ocr_ignore()
    include_db, exclude_db, exclude_upper = load_database()
    db_include = {k: dict(v, definitions=list(v["definitions"])) for k, v in include_db.items()}
    for key, c in CLIENT_DB.items():   # client terms are always looked for, and win over database Exclude rules
        exclude_db.pop(key, None); exclude_upper.discard(key.upper())
        if key not in include_db:
            include_db[key] = {"category": "Acronym", "definitions": list(c["definitions"])}
    all_terms = set(include_db.keys()) | set(exclude_db.keys())
    direct_pattern = None
    if all_terms:
        sorted_terms = sorted(all_terms, key=len, reverse=True)
        # (?<![^\W\d_]) = not preceded by a letter; digits may touch a unit (25°C, 10µm, 150psi)
        direct_pattern = re.compile(r'(?<![^\W\d_])(' + '|'.join([re.escape(t) for t in sorted_terms]) + r")(?:'?s)?(?!\w)")
    return {
        "include_db": include_db, "exclude_db": exclude_db, "exclude_upper": exclude_upper, "db_include": db_include,
        "ocr_fixes": load_ocr_fixes(), "direct_pattern": direct_pattern,
        "fuzzy_targets": {t: t for t in include_db.keys() if len(t) >= 3 and t.isupper()},
        "acronym_re": re.compile(r'\b([A-Z][A-Z0-9/&]{1,7}s?)\b'),
        # Codes and designators kept whole: PCU-28V, MIL-STD-1553B, RS-422, PN 4521-003A, ST-200X, J1-P3, SN77X2
        "designator_re": re.compile(r'(?<![\w/-])((?:[A-Z0-9]+-)+[A-Z0-9]+|[A-Z]{1,4}[0-9][A-Z0-9]{2,8})(?![\w/-])'),
        # Mixed-case acronyms: DoD, DoE, IoT, MoU, PhD, DoDAF
        "mixed_re": re.compile(r'\b([A-Z][a-z]?[A-Z][A-Za-z]{0,2}[A-Z]|[A-Z][a-z][A-Z])\b'),
        "unit_re": re.compile(r'(?<!\w)\d+(?:\.\d+)?\s*([a-zA-Z\u00b0\u03bc\u03a9\u00c5]{1,5}(?:/[a-zA-Z0-9\^]{1,4})?)(?!\w)'),
        "common_words": common_words(),
        "symbol_defs": {},
        "abbrev_re": re.compile(r'(?<!\w)([a-zA-Z]{1,4}/[a-zA-Z]{1,4}|[a-zA-Z]{2,6}\.)(?!\w)'),
    }

_HITS = None   # terms recorded in the chunk being matched (for first use)

# Real abbreviations written with a period that are also (or look like) ordinary words: always reported.
PERIOD_ABBREVIATIONS = set("""
approx appx assy avg ave cal cap ch chap co col config corp ctrl dept dia doc docs dr dwg ea eng engr eq eqn est etc
fig figs ft ga gal govt hr hrs ht inc incl intl jr lb lbs ltd max mfg mgmt mgr min misc mo mr mrs ms mt natl no nos
oz para pg pgs pkg pp pt pts qty qual ref refs reqt rev rm rqmt sec sect spec specs sq sr st std sta tech tel temp
tot vol vols vs wk wt yr yrs
""".split())
_COMMON_WORDS = None

def common_words():
    """Common 2-6 letter English words (SCOWL, assets\\common_words.txt). Loaded once."""
    global _COMMON_WORDS
    if _COMMON_WORDS is None:
        words = set()
        try:
            with open(asset_path("common_words.txt"), encoding="utf-8") as f:
                words = {w.strip() for w in f if w.strip() and not w.startswith("#")}
        except (OSError, TypeError):
            log_error("Common words list missing; sentence-end words may be reported as abbreviations")
        _COMMON_WORDS = frozenset(words)
    return _COMMON_WORDS

def _file_of(label):
    """File name at the start of a location label ("Volume (Final).docx (Slide 3)" -> "Volume (Final).docx")."""
    exts = "|".join(re.escape(e) for e in sorted(SUPPORTED_EXTS, key=len, reverse=True))
    mt = re.match(rf"(.+?(?:{exts}))(?= \(| \[|$)", label, re.I)
    return mt.group(1) if mt else label

_SEC_RE = re.compile(r"\(section '([^']*)'")
_SEC_KEY = re.compile(r"\s*(?:(?:section|part|volume|chapter)\s+)?(\d+|[A-Z](?=\.|\s*[-:)]|\s*$))", re.I)

def section_of(label):
    """The major section a location belongs to, for the per-section first-use rule (2.22.0).
    Word headings set sections: numbered headings group by their first number or letter ("2.", "2.1 Approach", "2.3" are
    all section 2; "C.3 Work" and "Section C" are section C), other headings are their own section. Text before the first
    heading is "(start)". None for parts outside the body text (pictures, headers, footnotes); "" for files with no
    headings (PDF pages, slides, sheets)."""
    mt = _SEC_RE.search(label)
    if mt:
        h = mt.group(1).strip()
        k = _SEC_KEY.match(h)
        return k.group(1).upper() if k else h
    if re.search(r"\((?:(?:table|caption|text box), )?para \d", label):
        return "(start)"
    if re.search(r"\((?:Body|Header|Footer|Footnotes|Endnotes|Comments)", label):
        return None
    return ""

def loc_kind(label):
    """Where a location sits (2.23.0): "text" (running text, footnotes), "table", "figure" (pictures, diagrams, charts,
    SmartArt, text boxes), "caption", "header" (headers and footers) or "notes" (comments, speaker notes). First use is
    judged in running text only; the others are reported apart."""
    if _OCR_LOC.search(label) or EQ.PIC_LABEL in label or re.search(
            r"\((?:Vector text|Image)\)|, SVG |, text box, | chart\)| SmartArt\)|\(Body", label):
        return "figure"
    if re.search(r"\((?:Header|Footer)\b", label):
        return "header"
    if re.search(r"\(Comments\b| notes\)|\(Slide \d+(?:, hidden)? notes", label):
        return "notes"
    if ", table, " in label or "(table, " in label:
        return "table"
    if ", caption, " in label or "(caption, " in label:
        return "caption"
    return "text"

def _note(fu, key, label, paren, defs, term, text, mt):
    if key not in fu:
        fu[key] = {"loc": label, "defined": paren}
        if paren:                                       # the words written before "(ACR)" (2.7.0 volume check)
            fu[key]["lf"] = _long_form_before(term, text, mt.start() - 1)
            if len(defs) > 1:
                fu[key]["redefs"] = [label]
        if paren is False and defs:
            fu[key]["later"] = label
    else:
        if fu[key]["defined"] is False and not fu[key].get("later") and defs:
            fu[key]["later"] = label
        elif fu[key]["defined"] and defs and label not in fu[key].get("redefs", []) and len(fu[key].get("redefs", [])) < 5:
            fu[key].setdefault("redefs", []).append(label)

def note_first_use(findings, hits, label, text):
    """Per file, where each term first appears in reading order, and whether that first use is written the way
    proposals define an acronym: "Spelled Out Words (ACR)". Records a later "(ACR)" when the first use is bare.
    From 2.22.0 the same is kept per section of each file (first_use_sec) for the per-section rule."""
    f = _file_of(label)
    sec = section_of(label)
    kind = loc_kind(label)
    for term in dict.fromkeys(hits):
        d = findings.get(term)
        if d is None:
            continue
        if kind in ("text", "table", "figure", "caption"):   # uses per file, for QA/QC "never used again" (2.25.0)
            u = d.setdefault("uses", {})
            u[f] = u.get(f, 0) + hits.count(term)
        if kind != "text":                              # figures, tables and captions: where, not first use (2.23.0)
            ff = d.setdefault("first_fig", {})
            if f not in ff:
                ff[f] = {"loc": label, "kind": kind}
            continue
        pat = re.escape(term) + r"s?"
        mt = re.search(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])", text)
        paren = None if mt is None else text[max(0, mt.start() - 1):mt.start()] == "("
        defs = list(re.finditer(r"\(\s*" + pat + r"\s*\)", text))
        _note(d.setdefault("first_use", {}), f, label, paren, defs, term, text, mt)
        if sec is not None:
            _note(d.setdefault("first_use_sec", {}).setdefault(f, {}), sec, label, paren, defs, term, text, mt)

def _long_form_before(term, text, paren_at):
    """Schwartz-Hearst long form ending right before the parenthesis, or "" when the words do not fit the acronym."""
    import custdefs
    before = re.split(r"[.;:!?\n(]\s", text[max(0, paren_at - 200):paren_at])[-1]
    words = before.split()[-(min(len(term) + 5, len(term) * 2) + 2):]
    try:
        return (custdefs._best_long_form(term, words) or "") if words else ""
    except Exception:
        diag.swallowed()
        return ""

def first_use_lines(d, with_file=True):
    """Readable first-use lines for acronyms only (units and abbreviations are never defined this way)."""
    if not d.get("category", "").startswith("Acronym") or d.get("excluded") or d.get("known"):
        return []
    out = []
    for f, u in d.get("first_use", {}).items():
        loc = u["loc"] if with_file else (u["loc"][len(f):].strip() or u["loc"])
        if u["defined"] is True:
            state = "defined here"
        elif u["defined"] is None:
            state = "check (OCR-corrected)"
        elif u.get("later") == u["loc"]:
            state = "NOT defined at first use; spelled out later in the same passage"
        elif u.get("later"):
            state = f"NOT defined at first use; spelled out later at {u['later']}"
        else:
            state = "NOT defined in this file"
        out.append(f"{loc}: {state}")
    names = {"table": "a table", "figure": "a figure", "caption": "a caption", "header": "a header or footer",
             "notes": "a comment or notes"}
    for f, g in d.get("first_fig", {}).items():           # figures and tables are not first uses (2.23.0)
        loc = g["loc"] if with_file else (g["loc"][len(f):].strip() or g["loc"])
        where = names.get(g["kind"], g["kind"])
        out.append(f"{loc}: in {where}" + ("" if f in d.get("first_use", {}) else " only (no first use in text)"))
    return out

def ctx_text(d):
    """'Statement of Work (spelled out in the document; nearby: tasks)', 'differs by place: ...' or ''."""
    c = d.get("context") or {}
    if c.get("mixed"):
        means = list(dict.fromkeys(v[0] for v in c.get("by_loc", {}).values()))
        return "differs by place: " + " / ".join(means)
    if not c.get("definition"):
        return ""
    return c["definition"] + (f" ({'; '.join(c.get('cues', [])[:2])})" if c.get("cues") else "")

def first_use_flag(d):
    """True if any file's first use of an acronym is not written as "Words (ACR)"."""
    return any(u["defined"] is False for u in d.get("first_use", {}).values()) and bool(first_use_lines(d))

def record_symbol(findings, sym, loc, m):
    if sym in m['include_db']:
        record_included(findings, sym, loc, m['include_db'])
    elif sym in m['exclude_db']:
        record_excluded(findings, sym, loc, m['exclude_db']); return
    else:
        if sym not in findings:
            findings[sym] = {"category": "Symbol", "count": 0, "locations": [], "definitions": [], "in_db": False,
                             "excluded": False, "selected_definition": "[Not defined in the document or database]",
                             "status": "SYMBOL NOT DEFINED"}
        findings[sym]["count"] += 1
        if loc not in findings[sym]["locations"]:
            findings[sym]["locations"].append(loc)
    findings[sym]["symbol"] = True

def record_equation(findings, loc, text, m):
    linear, _sep, syms = text.partition("\t")
    linear = " ".join(linear.split())
    syms = [x for x in syms.split("|") if x] if _sep else EQ.symbols_in_text(linear, common=m['common_words'])
    key = linear if len(linear) <= 160 else linear[:157] + "..."
    if key not in findings:
        findings[key] = {"category": "Equation", "count": 0, "locations": [], "definitions": [], "in_db": False,
                         "excluded": False, "selected_definition": "", "status": "EQUATION", "equation": True,
                         "symbols": []}
    d = findings[key]
    d["count"] += 1
    if loc not in d["locations"]:
        d["locations"].append(loc)
    d["symbols"] = list(dict.fromkeys(d["symbols"] + syms))
    for sym in syms:
        record_symbol(findings, sym, loc, m)

def finalize_symbols(findings, m):
    """Give each symbol the meaning stated in the documents (where ṁ is ..., nomenclature lists and tables).
    Also sets aside capital-letter heading words (mark_heading_words, 2.20.0)."""
    mark_heading_words(findings, m)
    stated = {}
    for _file, defs in m['symbol_defs'].items():
        for sym, desc in defs:
            lst = stated.setdefault(sym, [])
            if desc.casefold() not in {x.casefold() for x in lst}:
                lst.append(desc)
    for sym, d in findings.items():
        if not d.get("symbol") or d.get("in_db") or d.get("excluded"):
            continue
        descs = stated.get(sym, [])
        if len(descs) == 1:
            d.update({"definitions": descs, "selected_definition": descs[0], "status": "Defined in document"})
        elif len(descs) > 1:
            d.update({"definitions": descs, "status": f"CHOOSE (defined {len(descs)} ways)",
                      "selected_definition": f"MULTIPLE ({len(descs)} meanings) - Choose: " + " OR ".join(descs)})

def summarize_equations(findings):
    """Each equation row lists its symbols and which ones are still undefined."""
    for key, d in findings.items():
        if not d.get("equation"):
            continue
        undefined = [x for x in d["symbols"] if x in findings and status_kind(findings[x]["status"]) == "candidate"]
        d["selected_definition"] = "Symbols: " + ", ".join(d["symbols"]) + (f"  |  not defined: {', '.join(undefined)}" if undefined else "")
        d["status"] = f"EQUATION: {len(undefined)} symbol(s) not defined" if undefined else "EQUATION (all symbols defined)"

def match_chunks(findings, chunks, m):
    """Run the three gates over [(location label, text)] and record findings."""
    global _HITS
    for loc_label, text in chunks:
        if not text.strip():
            continue
        text = fold(text)
        if loc_label.endswith(EQ.EQ_LABEL):
            record_equation(findings, loc_label[:-len(EQ.EQ_LABEL)], text, m); continue
        if loc_label.endswith(EQ.DEF_LABEL):
            name = loc_label[:-len(EQ.DEF_LABEL)]
            m['symbol_defs'].setdefault(name, [])
            m['symbol_defs'][name] += [tuple(l.split("\t", 1)) for l in text.splitlines() if "\t" in l]
            continue
        if loc_label.endswith(EQ.PIC_LABEL):
            loc = loc_label[:-len(EQ.PIC_LABEL)]
            key = f"[equation picture] {_file_of(loc)}"
            if key not in findings:
                findings[key] = {"category": "Equation (picture)", "count": 0, "locations": [], "definitions": [],
                                 "in_db": False, "excluded": False, "status": "CHECK EQUATION PICTURE",
                                 "selected_definition": "Math inside a picture. OCR reads letters, not math layout: check it "
                                                        "in the preview. Read as: " + text[:120]}
            findings[key]["count"] += 1
            if loc not in findings[key]["locations"]:
                findings[key]["locations"].append(loc)
            continue
        _HITS = hits = []

        # Gate 1 & 2: Unified Database (Exclusions & Inclusions)
        if m['direct_pattern']:
            for match in m['direct_pattern'].finditer(text):
                term = match.group(1)
                if term in m['exclude_db'] and term not in m['include_db']:
                    record_excluded(findings, term, loc_label, m['exclude_db'])
                elif term in m['include_db']:
                    record_included(findings, term, loc_label, m['include_db'])

        # Gate 3a: codes and designators, reported whole. Their pieces are not reported as units or abbreviations.
        code_spans = []
        for match in m['designator_re'].finditer(text):
            tok = match.group(1)
            letters = sum(c.isalpha() for c in tok)
            if len(tok) < 4 or letters == 0 or (not any(c.isdigit() for c in tok) and "-" not in tok):
                continue
            if "-" in tok and not any(c.isdigit() for c in tok) and min(len(p) for p in tok.split("-")) < 2:
                continue   # "A-B" style fragments
            code_spans.append(match.span(1))
            if tok in m['include_db']:
                record_included(findings, tok, loc_label, m['include_db'])
            elif tok in m['exclude_db'] or tok.upper() in m['exclude_upper']:
                if tok in m['exclude_db']:
                    record_excluded(findings, tok, loc_label, m['exclude_db'])
            else:
                record_candidate(findings, tok, "Designator (Candidate)", loc_label)
        in_code = lambda span: any(a <= span[0] and span[1] <= b for a, b in code_spans)

        for match in m['mixed_re'].finditer(text):
            tok = match.group(1)
            if tok in m['include_db'] or tok in m['exclude_db'] or tok.upper() in m['exclude_upper'] or tok.isupper() or tok.lower() in m['common_words']:
                continue
            record_candidate(findings, tok, "Acronym (Candidate)", loc_label)

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
            record_candidate(findings, cand, "Acronym (Candidate)", loc_label,
                             caps_run=cand.isalpha() and in_caps_run(text, match.start(1), match.end(1)))

        for match in m['unit_re'].finditer(text):
            ucand = match.group(1)
            if in_code(match.span()):
                continue   # "28V" inside PCU-28V is part of a code, not a measurement
            if ucand in m['ocr_fixes']:
                apply_ocr_fix(findings, ucand, m['ocr_fixes'][ucand], "Unit (Candidate)", loc_label, m['include_db'], m['exclude_db'])
                continue
            if (ucand in m['include_db'] or ucand in m['exclude_db'] or
                    ucand.upper() in m['exclude_upper'] or ucand.lower() in NON_UNIT_WORDS or ucand.isdigit()):
                continue
            if (len(ucand) >= 3 and ucand[0].isupper() and ucand[1:].islower() and ucand.lower() in m['common_words']):
                continue   # "1 Add ...", "3 Open ...": a capitalized ordinary word after a number, not a unit (2.21.0)
            record_candidate(findings, ucand, "Unit (Candidate)", loc_label,
                             caps_run=ucand.isalpha() and ucand.isupper() and in_caps_run(text, match.start(1), match.end(1)))

        for match in m['abbrev_re'].finditer(text):
            acand = match.group(1)
            if in_code(match.span(1)):
                continue
            if acand in m['ocr_fixes']:
                apply_ocr_fix(findings, acand, m['ocr_fixes'][acand], "Abbreviation (Candidate)", loc_label, m['include_db'], m['exclude_db'])
                continue
            base = acand.rstrip('.')
            if (acand in m['include_db'] or acand in m['exclude_db'] or base in m['include_db'] or base in m['exclude_db'] or
                    acand.upper() in m['exclude_upper'] or base.upper() in m['exclude_upper']):
                continue
            if acand.endswith('.') and '/' not in acand:
                if len(base) >= 2 and base.isupper():
                    continue   # "CCB." is an acronym ending a sentence: the acronym rule already reports CCB
                if base.lower() in m['common_words'] and base.lower() not in PERIOD_ABBREVIATIONS:
                    continue   # "award." is an ordinary word ending a sentence, not an abbreviation
            record_candidate(findings, acand, "Abbreviation (Candidate)", loc_label)
        _HITS = None
        note_first_use(findings, hits, loc_label, text)


CANCEL = threading.Event()   # set by the Cancel Scan button

class ScanCancelled(BaseException):
    """Raised to stop a scan. BaseException, so per-page error handlers (except Exception) do not swallow it."""

def check_cancel():
    if CANCEL.is_set():
        raise ScanCancelled()

def scan_file(filepath, status_callback, idx, total):
    """Read one file. Returns (chunks, skipped [(label, reason)], error message or None)."""
    _SKIPPED.clear()
    try:
        chunks = extract_chunks_from_file(filepath, status_callback, idx, total)
        chunks += EQ.text_math_chunks(chunks, common_words())
        err = None
    except Exception as e:
        log_error("File could not be read", ext=os.path.splitext(filepath)[1].lower())
        chunks, err = [], f"{type(e).__name__}: {e}"
    return chunks, list(_SKIPPED), err

# ---------------------------------------------------------------------------
# Full text mode: every word the scanner reads, typed and OCR, in reading order
# ---------------------------------------------------------------------------
_OCR_LOC = re.compile(r"\(Image\)|, image ")

def _para_span(loc):
    mt = re.search(r"para (\d+)(?:-(\d+))?\)", loc)
    return (int(mt.group(1)), int(mt.group(2) or mt.group(1))) if mt else None

def _reading_order(chunks):
    """Word equations sit in their paragraph's place: after the text block that holds or precedes that paragraph."""
    eqs = [c for c in chunks if c[0].endswith(EQ.EQ_LABEL) and _para_span(c[0])]
    rest = [c for c in chunks if c not in eqs]
    if not eqs:
        return chunks
    out, placed = [], set()
    for c in rest:
        out.append(c)
        span = _para_span(c[0])
        if span and not c[0].endswith(EQ.EQ_LABEL):
            for i, e in enumerate(eqs):
                if i not in placed and _para_span(e[0])[0] <= span[1]:
                    out.append(e); placed.add(i)
    out += [e for i, e in enumerate(eqs) if i not in placed]
    return out

def full_text_of(filepath, status_callback=lambda m: None, idx=1, total=1):
    """All text in one file, as the scanner reads it: typed text exactly, picture text through the sandboxed OCR
    reader, equations in linear form and in reading order, then every symbol definition found. Returns (text, error)."""
    chunks, skips, err = scan_file(filepath, status_callback, idx, total)
    name = os.path.basename(filepath)
    out = [f"===== {name} ====="]
    if err:
        out.append(f"[Could not read this file: {err}]")
    defs = {}
    for loc, text in _reading_order(chunks):
        if loc.endswith(EQ.DEF_LABEL):
            for line in text.splitlines():
                sym, _t, meaning = line.partition("\t")
                if sym and meaning:
                    defs.setdefault(sym.strip(), meaning.strip())
            continue
        if loc.endswith(EQ.PIC_LABEL):
            continue   # the picture's text is already shown where it was read
        where = loc[len(name):].strip() if loc.startswith(name) else loc
        if loc.endswith(EQ.EQ_LABEL):
            linear, _t, syms = text.partition("\t")
            out.append(f"--- {where[:-len(EQ.EQ_LABEL)].strip() or 'Equation'} [equation] ---")
            out.append(linear.strip() + (f"\n    symbols: {', '.join(x for x in syms.split('|') if x)}" if syms else ""))
            continue
        body = text.strip()
        if not body:
            continue
        tag = "  [read by OCR: check spelling]" if _OCR_LOC.search(loc) else ""
        out.append(f"--- {where or 'Text'}{tag} ---")
        out.append(body)
    if defs:
        out.append("--- Symbol definitions found in this file ---")
        out += [f"{k} = {v}" for k, v in defs.items()]
    for lbl, why in skips:
        out.append(f"[Not read: {lbl}: {why}]")
    return "\n".join(out) + "\n", err

def analyze_batch(filepaths, status_callback, capture=None):
    """Scan files once. capture (dict): filled with each file's terms-only cache entry, so the results can be saved
    as a project later without reading the files again."""
    m = build_matcher()
    findings = {}
    total = len(filepaths)
    _OCR_CACHE.clear()
    if capture is not None:
        weak = weak_terms(m); sigs = (engine_signature(weak), text_signature(weak), ocr_signature())
    for idx, filepath in enumerate(filepaths, start=1):
        check_cancel()
        _OCR_CALLS[0] = 0
        chunks, skips, err = scan_file(filepath, status_callback, idx, total)
        if capture is not None:
            try:
                capture[os.path.abspath(filepath)] = cache_entry(os.stat(filepath), weak, chunks, skips, err, _OCR_CALLS[0], sigs)
            except OSError:
                pass
        if err:
            record_file_error(findings, filepath, err)
        for label, reason in skips:
            record_skip(findings, label, reason)
        match_chunks(findings, chunks, m)
    finalize_symbols(findings, m)
    apply_client_overlay(findings, m)
    summarize_equations(findings)
    mark_alt_forms(findings, m)
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

ALT_STATUS = "Alt form of"

def mark_alt_forms(findings, m):
    """A found alternate form keeps its own row, labelled with its primary and the primary's definition (2.26.0)."""
    for term, d in findings.items():
        alt_of = (m["include_db"].get(fold(term)) or {}).get("alt_of")
        if alt_of and not d.get("excluded"):
            d["alt_of"] = alt_of
            d["status"] = f"{ALT_STATUS} {alt_of}"
            defs = (m["include_db"].get(alt_of) or {}).get("definitions") or []
            if len(defs) == 1:
                d["selected_definition"] = defs[0]

def refresh_batch(filepaths, status_callback, cache):
    """Match files again against the current database (2.14.0), reusing the text already read in this session when the
    file and everything its saved text depends on are unchanged; other files are read again. Updates cache."""
    m = build_matcher()
    findings = {}
    _OCR_CACHE.clear()
    weak = weak_terms(m); sigs = (engine_signature(weak), text_signature(weak), ocr_signature())
    total = len(filepaths)
    for idx, filepath in enumerate(filepaths, start=1):
        check_cancel()
        key = os.path.abspath(filepath)
        entry = cache.get(key)
        try:
            st = os.stat(filepath)
        except OSError:
            st = None
        fresh = entry and st and entry_current(entry, sigs) and entry["size"] == st.st_size and abs(entry["mtime"] - st.st_mtime) < 1.0
        if fresh:
            status_callback(f"[{idx}/{total}] {os.path.basename(filepath)} - unchanged, matching again")
        else:
            _OCR_CALLS[0] = 0
            chunks, skips, err = scan_file(filepath, status_callback, idx, total)
            if st is None:
                record_file_error(findings, filepath, err or "File not found")
                continue
            entry = cache_entry(st, weak, chunks, skips, err, _OCR_CALLS[0], sigs)
            cache[key] = entry
        if entry.get("error"):
            record_file_error(findings, filepath, entry["error"])
        for label, reason in entry.get("skips", []):
            record_skip(findings, label, reason)
        match_chunks(findings, entry["chunks"], m)
    finalize_symbols(findings, m)
    apply_client_overlay(findings, m)
    summarize_equations(findings)
    mark_alt_forms(findings, m)
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

# ==============================================================================
# PROJECTS: remember a folder's findings, rescan only what changed, track changes
# ==============================================================================
APP_VERSION = "3.41.0"            # keep in step with version_info.txt
diag.VERSION = APP_VERSION
PROJECT_EXT = ".ahproj"
PROJECT_FORMAT = "AcronymHunterProject"
LOCK_STALE_HOURS = 12
SKIP_DIRS = {"_internal", "_local_sandbox", "training_data", "logs", "config", "__pycache__", ".git", "Stationkeeper Data"}
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

def _sha12(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]

def text_signature(weak=()):
    """What typed-text results depend on: the app's extraction code (major.minor version) and the weak terms."""
    return _sha12([APP_VERSION.rsplit(".", 1)[0], sorted(weak)])

def ocr_signature():
    """What picture results depend on: the OCR engine, its settings, the installed reader, and the ignore list."""
    models = sorted((n, os.path.getsize(os.path.join(MODELS_DIR, n)), int(os.path.getmtime(os.path.join(MODELS_DIR, n))))
                    for n in os.listdir(MODELS_DIR)) if os.path.isdir(MODELS_DIR) else []
    dsig = ""
    if doctr_active():
        try:
            dsig = hashlib.sha1(open(os.path.join(DOCTR_DIR, "doctr_models.json"), "rb").read()).hexdigest()[:12]
        except Exception:
            diag.swallowed()
            dsig = "doctr"
    return _sha12([OCR_BACKEND, OCR_CFG, models, sorted(_OCR_IGNORE), dsig])

def engine_signature(weak=()):
    """Both signatures together (older project files store only this)."""
    return _sha12([text_signature(weak), ocr_signature()])

def cache_entry(st, weak, chunks, skips, err, ocr_used, sigs):
    sig, tsig, osig = sigs
    return {"size": st.st_size, "mtime": st.st_mtime, "engine": sig, "text_sig": tsig, "ocr_sig": osig,
            "ocr_used": bool(ocr_used), "scanned": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "chunks": [[label, text if label.endswith((EQ.EQ_LABEL, EQ.DEF_LABEL, EQ.PIC_LABEL)) else reduce_text(fold(text), weak)]
                       for label, text in chunks if text.strip()],
            "skips": skips, "error": err}

def entry_current(entry, sigs):
    """Saved results for a file stay valid when nothing they depend on changed. A file with no pictures is not
    re-read after Improve Reading, a new Knowledge Pack reader, or an OCR setting change."""
    sig, tsig, osig = sigs
    if "text_sig" in entry:
        return entry["text_sig"] == tsig and (not entry.get("ocr_used", True) or entry.get("ocr_sig") == osig)
    return entry.get("engine") == sig

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
                "last_scan": None, "last_stats": {}, "files": {}, "history": {}, "decisions": {}, "manual": {},
                "client_lists": [], "mode": "folder", "members": []}

    def load(self):
        with open(self.path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if data.get("format") != PROJECT_FORMAT:
            raise ValueError("This is not a Stationkeeper project file.")
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
                diag.swallowed()
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
            diag.swallowed()
            pass

    # ---- files ----
    def member_path(self, rel):
        """Absolute path of a project file entry (relative to the project folder, or absolute)."""
        return rel if os.path.isabs(rel) else os.path.join(self.root, rel.replace("/", os.sep))

    def to_member(self, path):
        path = os.path.abspath(path)
        try:
            rel = os.path.relpath(path, self.root)
        except ValueError:          # another drive
            return path
        return path if rel.startswith("..") else rel.replace(os.sep, "/")

    def list_files(self):
        if self.data.get("mode") == "files":   # a saved set of files, not a whole folder
            return sorted(m for m in self.data.get("members", []) if os.path.isfile(self.member_path(m)))
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
    cache, sig = project.data["files"], (engine_signature(weak), text_signature(weak), ocr_signature())
    files = project.list_files() if rescan else sorted(cache)
    stats["files"] = len(files)
    stats["removed"] = len(set(cache) - set(files)) if rescan else 0
    new_cache = {}
    try:
        _project_loop(project, files, cache, sig, weak, m, findings, stats, new_cache, status_callback, full, rescan)
    except ScanCancelled:
        if rescan:   # keep what was read so far; the next rescan continues from there
            project.data["files"].update(new_cache)
        raise
    if rescan:
        project.data["files"] = new_cache
    finalize_symbols(findings, m)
    apply_client_overlay(findings, m)
    summarize_equations(findings)
    mark_alt_forms(findings, m)
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True)), stats

def _project_loop(project, files, cache, sig, weak, m, findings, stats, new_cache, status_callback, full, rescan):
    for idx, rel in enumerate(files, start=1):
        check_cancel()
        absf = project.member_path(rel)
        entry = cache.get(rel)
        st = os.stat(absf) if rescan and os.path.exists(absf) else None
        fresh = (entry and entry_current(entry, sig) and
                 (not rescan or (st and entry["size"] == st.st_size and abs(entry["mtime"] - st.st_mtime) < 1.0)))
        if (not full and fresh) or not rescan:
            if entry is None:
                continue
            stats["reused"] += 1
            if rescan:
                status_callback(f"[{idx}/{len(files)}] {rel} - unchanged, using saved results")
        else:
            _OCR_CALLS[0] = 0
            chunks, skips, err = scan_file(absf, status_callback, idx, len(files))
            entry = cache_entry(st, weak, chunks, skips, err, _OCR_CALLS[0], sig)
            stats["scanned"] += 1
        new_cache[rel] = entry
        if entry.get("error"):
            record_file_error(findings, rel, entry["error"])
        for label, reason in entry.get("skips", []):
            record_skip(findings, label, reason)
        match_chunks(findings, entry["chunks"], m)

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
                              "selected_definition": h.get("definition", ""), "status": "No longer found",
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
    if _HITS is not None:
        _HITS.append(term)
    info = include_db[term]
    defs = info["definitions"]
    multi = len(defs) > 1
    if term not in findings:
        findings[term] = {
            "category": info["category"], "count": 0, "locations": [],
            "definitions": defs, "in_db": True, "excluded": False,
            "selected_definition": (f"MULTIPLE ({len(defs)} options) - Choose: " + " OR ".join(defs)) if multi else defs[0],
            "status": "CHOOSE DEFINITION" if multi else "Resolved (In DB)"
        }
        if info.get("known"):           # recognized, kept, left off the acronym lists; never asked to define at first use
            findings[term].update(known=True, status=KNOWN_STATUS + (f": {info['omit_reason']}" if info.get("omit_reason") else ""),
                                  selected_definition=defs[0], omit_reason=info.get("omit_reason", ""))
    findings[term]["count"] += 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

def record_excluded(findings, term, loc, exclude_db):
    if _HITS is not None:
        _HITS.append(term)
    info = exclude_db[term]
    if term not in findings:
        findings[term] = {
            "category": info["category"], "count": 0, "locations": [],
            "definitions": [info["definition"]], "in_db": True, "excluded": True,
            "selected_definition": f"[EXCLUDED] {info['definition']}", "status": "Excluded by DB rule"
        }
    findings[term]["count"] += 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

_CAPS_WORD = re.compile(r"^[A-Z][A-Z&]+$")
_STRUCTURE_WORDS = {"appendix", "appendices", "attachment", "attachments", "exhibit", "exhibits", "annex", "section",
                    "sections", "chapter", "enclosure", "addendum", "amendment", "contents", "glossary", "introduction",
                    "summary", "overview", "background", "references", "foreword", "preface", "index"}
_ENGLISH_ENDINGS = ("tion", "tions", "sion", "sions", "ment", "ments", "ing", "ings", "ance", "ence", "ness", "ity", "ities",
                    "ive", "ives", "al", "als", "ure", "ures", "ers", "ies", "ical", "ally", "ated", "ates")
_NUMBERING = re.compile(r"[\d.]+|[A-Z]\.?[\d.]*")

def in_caps_run(text, start, end):
    """True when the token at text[start:end] sits among other all-capital words on its line (a heading or title
    such as "SECTION M - EVALUATION FACTORS FOR AWARD"), or is alone on its line apart from numbering."""
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    strip = ".,;:()[]'\"-/"
    before = [w.strip(strip) for w in text[ls:start].split()]
    before = [w for w in before if w and not _NUMBERING.fullmatch(w)]
    after = [w for w in (x.strip(strip) for x in text[end:le].split()) if w]
    if not before and not after:
        return True
    near = before[-1:] + after[:1]
    return any(_CAPS_WORD.match(w) and len(w) >= 2 for w in near)

def mark_heading_words(findings, m):
    """Known gap F6 (2.20.0): an ordinary English word in capitals that only ever appears inside an all-capital
    heading or title (AWARD, DESIGN, SCOPE OF WORK) is not an acronym. It is kept as excluded (Show Excluded lists it);
    a word that also appears on its own in running text (the SOW tasks) stays a candidate."""
    common = m.get('common_words') or set()
    for term, d in findings.items():
        low = term.lower()
        structure = low in _STRUCTURE_WORDS          # APPENDIX A, SECTION L, ATTACHMENT 3: labels, never acronyms (2.21.0)
        wordlike = structure or low in common or (len(low) >= 7 and low.endswith(_ENGLISH_ENDINGS))   # list: 2-6 letters
        if (d.get("status") == "NEW CANDIDATE" and d.get("category") == "Acronym (Candidate)" and not d.get("in_db")
                and term.isalpha() and len(term) >= 2 and wordlike
                and (structure or d.get("caps_run", 0) >= d.get("count", 0) > 0)):
            d["excluded"] = True
            d["status"] = "EXCLUDED: heading word in capitals"
            d["selected_definition"] = "An ordinary word that only appears in all-capital headings"

def record_candidate(findings, term, cat, loc, caps_run=False):
    if _HITS is not None:
        _HITS.append(term)
    if term not in findings:
        findings[term] = {
            "category": cat, "count": 0, "locations": [],
            "definitions": [], "in_db": False, "excluded": False,
            "selected_definition": "[Not in Database — Definition omitted]", "status": "NEW CANDIDATE"
        }
    findings[term]["count"] += 1
    if caps_run:
        findings[term]["caps_run"] = findings[term].get("caps_run", 0) + 1
    if loc not in findings[term]["locations"]:
        findings[term]["locations"].append(loc)

def write_db_rows(rows):
    """Atomic rewrite: write a temp file beside the DB, then swap it in (no half-written DB).
    rows: [term, category, definition, action(, {extra column: value})]. Keeps the file's own column order,
    header names, and extra columns, so a reordered or extended database stays the way the user set it up."""
    layout = db_layout()
    have = {h for _f, h in layout}
    for r in rows:                                   # a new extra column (Omit reason) is added at the end
        for h in (r[4] if len(r) > 4 and isinstance(r[4], dict) else {}):
            if h and h not in have and not db_field(h):
                layout.append((None, h)); have.add(h)
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

def norm_def(s):
    """Definitions compare without case, spacing or punctuation: 'Statement of Work' = 'statement-of-work'."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def _action_kind(a):
    a = str(a or "").strip().lower()
    return "omit" if a.startswith(("known", "omit")) else "exclude" if a.startswith("exclude") else "include"

def db_add(term, cat, defn, action="Include", extra=None):
    """Add one database row. The same term may have several rows, one per different definition.
    Returns ('added' | 'updated' | 'duplicate', existing row or None): 'duplicate' = this term already has this
    definition with this action (nothing written); 'updated' = same definition, the action changed (no new row)."""
    rows = read_db_rows()
    ft, nd = fold(term), norm_def(defn)
    same = [r for r in rows if fold(r[0]) == ft and norm_def(r[2]) == nd]
    if same:
        r = same[0]
        if _action_kind(r[3]) == _action_kind(action):
            return "duplicate", r                     # nothing changes, not even its omit reason
        r[3] = action
        if extra:
            r[4].update(extra)
        write_db_rows(rows)
        return "updated", r
    rows.append([term, cat, defn, action, dict(extra or {})])
    write_db_rows(rows)
    return "added", None

def db_definitions(term):
    """[(definition, action)] the database holds for a term."""
    ft = fold(term)
    return [(r[2], r[3]) for r in read_db_rows() if fold(r[0]) == ft]

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
PACK_MODEL_FILES = ("rec.onnx", "det.onnx", "cls.onnx", "rec_keys.txt", CUSTOM_TESS_MODEL + ".traineddata") + \
    tuple("doctr/" + f for f in DOCTR_FILES)      # trained docTR models (Training Kit), checked by SHA-256 on load
PACK_DATA_FILES = {"acronym_database.csv": "DB", "ocr_corrections.csv": "FIXES", "ocr_ignore.csv": "IGNORE",
                   "compliance_learned.json": "LEARNED",   # compliance learning: hashed counts only, no RFP words (2.10.0)
                   "offerings.csv": "OFFERINGS",           # the offerings catalog (2.19.0)
                   "keyword_learning.json": "KWLEARN",     # keyword Keep/Reject learning: hashed counts only (2.19.0)
                   "banned_words.csv": "BANNED",           # the team's banned words and phrases for QA/QC (2.27.0)
                   "placement_synonyms.csv": "SYNONYMS"}   # section title words that mean the same (2.30.0)

def _team_files():
    """(name in the pack, path) for the offerings catalog and keyword learning (paths follow CONFIG_DIR)."""
    return [("offerings.csv", os.path.join(CONFIG_DIR, "offerings.csv")),
            ("keyword_learning.json", os.path.join(CONFIG_DIR, "keyword_learning.json")),
            ("banned_words.csv", os.path.join(CONFIG_DIR, "banned_words.csv")),
            ("placement_synonyms.csv", os.path.join(CONFIG_DIR, "placement_synonyms.csv"))]
COMPLIANCE_LEARNED_FILE = os.path.join(CONFIG_DIR, "compliance_learned.json")
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
    for name, path in ([("acronym_database.csv", DB_FILE), ("ocr_corrections.csv", OCR_FIXES_FILE),
                       ("ocr_ignore.csv", OCR_IGNORE_FILE), ("compliance_learned.json", COMPLIANCE_LEARNED_FILE)] + _team_files()):
        if os.path.isfile(path):
            out.append((name, path))
    for m in PACK_MODEL_FILES:
        path = os.path.join(MODELS_DIR, m)
        if os.path.isfile(path):
            out.append(("models/" + m, path))
    return out

def make_knowledge_pack(out_path, notes="", include=None, scorecard=None):
    """Write a Knowledge Pack zip of this copy's database, OCR fixes, ignore list, and models. Returns its info.
    2.50.0 (Training Studio): include = the pack names to ship (the areas kept), scorecard = the tests shown on the
    install card. The file may be named .skknow (opens the install card on double-click) or .zip."""
    files = _knowledge_sources()
    if include is not None:
        files = [(n, p) for n, p in files if n in include]
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
        diag.swallowed()
        info["counts"] = {}
    info["models"] = [n.split("/", 1)[1] for n, _ in files if n.startswith("models/")]
    if scorecard is not None:
        info["scorecard"] = [{k: r.get(k) for k in ("area", "title", "test", "now", "after", "change", "n", "include", "why", "files")}
                             for r in scorecard]
        shipped = {n for n, _p in files}
        if "acronym_database.csv" not in shipped:
            info["counts"].pop("database_rows", None)
        if "ocr_corrections.csv" not in shipped:
            info["counts"].pop("ocr_fixes", None)
        if "ocr_ignore.csv" not in shipped:
            info["counts"].pop("ignored_readings", None)
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
            raise ValueError("Not a Stationkeeper Knowledge Pack.")
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
    return [DB_FILE, OCR_FIXES_FILE, OCR_IGNORE_FILE, KNOWLEDGE_INFO_FILE, COMPLIANCE_LEARNED_FILE] + \
        [os.path.join(MODELS_DIR, m) for m in PACK_MODEL_FILES] + [p for _n, p in _team_files()]

def backup_knowledge(reason):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(KNOWLEDGE_BACKUP_DIR, stamp)
    os.makedirs(dest, exist_ok=True)
    manifest = {"reason": reason, "time": stamp, "files": {}}
    for i, path in enumerate(_backup_targets()):
        rel = os.path.relpath(path, DATA_DIR)
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
        path = os.path.join(DATA_DIR, rel)
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
    global _doctr_engine, DOCTR_DIR
    with _ocr_lock:
        _ocr_engine = None
        OCR_MODEL_INFO = "not loaded yet"
        _doctr_engine = None          # docTR reloads too: trained models may have been installed or removed
        DOCTR_DIR = _find_doctr()
        _doctr_failed[0] = False
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
            target = os.path.join(MODELS_DIR, m)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
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
    if "compliance_learned.json" in data:
        import complearn
        L = complearn.Learner(COMPLIANCE_LEARNED_FILE)
        n = L.merge_pack(data["compliance_learned.json"])
        L.save()
        report.append(f"Compliance learning: {n} decisions added from the team (your own decisions unchanged)")
        if getattr(L, "placed_added", 0):
            report.append(f"Placement learning: {L.placed_added} placed rows added from the team (your own unchanged)")
    if "offerings.csv" in data:                        # add-only: offerings already here are kept as they are
        import offerings
        os.makedirs(SANDBOX_TEMP, exist_ok=True)
        tmp = os.path.join(SANDBOX_TEMP, f"pack_offerings_{os.getpid()}.csv")
        with open(tmp, "wb") as f:
            f.write(data["offerings.csv"])
        try:
            a, _same = offerings.import_file(tmp)
        finally:
            os.remove(tmp)
        report.append(f"Offerings catalog: {a} offerings added (your own unchanged)")
    if "keyword_learning.json" in data:                # hashed counts: the larger count per phrase wins (no double counting)
        import keywords
        mine, theirs = keywords.learning(), json.loads(data["keyword_learning.json"].decode("utf-8"))
        n = 0
        for side in ("keep", "reject"):
            for h, c in (theirs.get(side) or {}).items():
                if isinstance(c, int) and c > mine[side].get(h, 0):
                    mine[side][h] = c; n += 1
        keywords._write("keyword_learning.json", mine)
        report.append(f"Keyword learning: {n} team decisions added")
    if "banned_words.csv" in data:                     # add-only: phrases already here keep their own wording
        import banned
        os.makedirs(SANDBOX_TEMP, exist_ok=True)
        tmp = os.path.join(SANDBOX_TEMP, f"pack_banned_{os.getpid()}.csv")
        with open(tmp, "wb") as f:
            f.write(data["banned_words.csv"])
        try:
            a, _same = banned.import_file(tmp, keep_starter=False)
        finally:
            os.remove(tmp)
        report.append(f"Banned words: {a} phrases added (your own unchanged)")
    if "placement_synonyms.csv" in data:               # add-only: groups already here keep their own wording
        import placelearn
        sp = placelearn.synonyms_path(CONFIG_DIR)
        text, a = placelearn.merge_synonym_text(placelearn.load_synonyms(sp),
                                                data["placement_synonyms.csv"].decode("utf-8-sig", errors="replace"))
        placelearn.save_synonyms(sp, text)
        report.append(f"Section word synonyms: {a} groups added (your own unchanged)")
    with open(KNOWLEDGE_INFO_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": info.get("version"), "created": info.get("created"), "created_by": info.get("created_by"),
                   "notes": info.get("notes", ""), "models": sorted(models), "pack_sha256": _sha256_file(path),
                   "installed": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, f, indent=1)
    reset_ocr_engine()
    return "\n".join(report)

def load_trained_models(folder):
    """Copy trained models from a Training Kit output folder into config\\models.
    docTR kit output (doctr_models.json + two ONNX files) goes to config\\models\\doctr after its SHA-256 check."""
    if os.path.isfile(os.path.join(folder, "doctr_models.json")):
        if not all(os.path.isfile(os.path.join(folder, f)) for f in DOCTR_FILES):
            raise ValueError("A docTR model folder needs doctr_det.onnx, doctr_reco.onnx and doctr_models.json.")
        if not doctr_folder_ok(folder):
            raise ValueError("These docTR models do not match the SHA-256 in their doctr_models.json. Not installed.")
        for f in DOCTR_FILES[:2]:
            _check_onnx(os.path.join(folder, f))
        backup_knowledge(f"before loading docTR models from {folder}")
        dest = os.path.join(MODELS_DIR, "doctr")
        os.makedirs(dest, exist_ok=True)
        for f in DOCTR_FILES:
            shutil.copy2(os.path.join(folder, f), os.path.join(dest, f))
        reset_ocr_engine()
        return ["doctr/" + f for f in DOCTR_FILES]
    found = [m for m in PACK_MODEL_FILES if os.path.isfile(os.path.join(folder, m))]
    if not any(m.endswith((".onnx", ".traineddata")) for m in found):
        raise ValueError("No acronym.traineddata, rec.onnx, det.onnx, or cls.onnx in that folder.")
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
        diag.swallowed()
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


# ==============================================================================
# 7. DESKTOP GUI APPLICATION
# ==============================================================================
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json") if DATA_DIR != BASE_DIR else os.path.join(SANDBOX_DIR, "settings.json")
ALL_TYPES = "All types"
STATUS_FILTERS = ["All statuses", "Needs choice", "New candidates", "Resolved", "Client list", "Client and database differ",
                  "Alt forms", "Equations and symbols", "Undefined symbols",
                  "Added manually", "Customer documents", "Customer and database differ", "In effort list", "Not in effort list", "Effort: needs author", "Effort: approved",
                  "New since last scan", "Changed since last scan", "No longer found", "Errors / not scanned",
                  "Context suggests a meaning", "New in this scan (not in the effort list)", "Found in omit list",
                  "Known in: customer docs", "Known in: customer list", "Known in: master database only", "Known in: no source",
                  "Database update", "Excluded"]
MANUAL_MARK = ""   # statuses are plain words (2.7.0: no emoji in the interface or in exports)
# Status kinds by leading words. Older projects saved statuses with an emoji in front; status_text() drops it.
_KIND_WORDS = (("error", ("COULD NOT READ FILE", "NOT SCANNED")),
               ("choice", ("CHOOSE", "MULTIPLE", "CUSTOMER DOCS DIFFER")),
               ("client_differs", ("CLIENT LIST (DATABASE DIFFERS)",)),
               ("candidate", ("NEW CANDIDATE", "SYMBOL NOT DEFINED", "CHECK EQUATION PICTURE")),
               ("manual", ("ADDED MANUALLY",)),
               ("known", ("FOUND IN OMIT LIST", "KNOWN NAME")),
               ("resolved", ("RESOLVED", "DEFINED IN DOCUMENT", "USER SELECTED", "ADDED TO DB", "CLIENT LIST",
                             "CUSTOMER DOCUMENT", "EFFORT LIST:", "ALT FORM OF", "FORM OF")),   # 3.34.1: FORM OF (FY27)
               ("gone", ("NO LONGER FOUND",)),
               ("excluded", ("EXCLUDED", "NOT A TERM IN THIS EFFORT")))
RESOLVED_WORDS = ("Resolved", "Defined in document", "User Selected", "Added to DB", "Client list")   # the Resolved filter
STATUS_RANK = {"error": 0, "choice": 1, "client_differs": 2, "candidate": 3, "manual": 4, "resolved": 5, "known": 6, "gone": 7,
               "excluded": 8}

def status_text(st):
    """The status without any leading symbol (statuses saved by older versions began with an emoji)."""
    st = str(st or "")
    i = 0
    while i < len(st) and not (st[i].isascii() and (st[i].isalnum() or st[i] == "[")):
        i += 1
    return st[i:]

def status_kind(st):
    up = status_text(st).upper()
    for kind, words in _KIND_WORDS:
        if up.startswith(words):
            return kind
    return "other"
LOC_MAX_LINES = 3   # Locations wrap to at most this many lines in the table; double-click a row for all of them
MANUAL_CATEGORIES = ["Acronym", "Abbreviation", "Unit", "Other"]
FOUND_FILTERS = ("All documents", "Customer documents", "Ours", "Both")     # 2.38.0: where a term was found
COLUMNS = (  # id, heading, base width, anchor
    ("term", "Term / Unit", 120, "w"),
    ("category", "Type", 170, "w"),
    ("count", "Count", 70, "center"),
    ("foundin", "Found in", 110, "w"),      # 2.38.0: customer documents, our documents, or both
    ("change", "Change", 130, "w"),
    ("status", "Status", 210, "w"),
    ("definition", "Definition", 300, "w"),
    ("knownin", "Known in", 190, "w"),
    ("locations", "Source Locations", 420, "w"),
)
FONT_MIN, FONT_MAX, FONT_DEFAULT = 9, 28, 13

def base_type(category):
    return category.replace(" (Candidate)", "")

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        diag.swallowed()
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        diag.swallowed()
        pass

TRAIN_DIR = os.path.join(DATA_DIR, "training_data")   # the Trainer's saved samples (never shipped, never committed)

TRAINING_APP = False   # True only inside Stationkeeper Training (training_app.py sets it) (2.15.0)

def trainer_available():
    """The Trainer, Improve Reading and Load Trained Models: only in Stationkeeper Training (2.15.0)."""
    return TRAINING_APP and bool(APP_CFG["allow_training"]) and importlib.util.find_spec("trainerkit") is not None

def corrections_on():
    """Report misreading and Not text save corrections for the training team, unless allow_training is false.
    2.97.0: never in SCIF-ready, nor for an effort above CUI or of unknown sensitivity."""
    import secure
    return bool(APP_CFG["allow_training"]) and (secure.training_ok() if not TRAINING_APP else not secure.ACTIVE)

def write_acronym_report(path, terms, results, known_cell):
    """The acronym report (CSV, opens in Excel): one row per term shown (2.67.0: shared with the Qt edition)."""
    strip = lambda x: x[len(CLIENT_TAG):] if x.startswith(CLIENT_TAG) else x[len(DB_TAG):] if x.startswith(DB_TAG) else x
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Term", "Type", "Count", "Change", "Status", "Selected definition", "Possible definitions",
                    "Client list definition", "Database definition", "Author decision",
                    "Locations",
                    "First found by a scan (date)", "Last found by a scan (date)", "Known in", "Context suggests"])
        for term in terms:
            d = results[term]
            defs = d.get("definitions", [])
            client = d.get("client_definitions", [])
            dbdefs = d.get("db_definitions", []) if d.get("client") else ([] if d.get("excluded") else
                                                                          [x for x in defs if not d.get("manual")])
            w.writerow([term, d["category"], d["count"], d.get("change", ""), d["status"], d["selected_definition"],
                        "\n".join(defs) if len(defs) > 1 or d.get("client") else "",
                        "\n".join(client), "\n".join(strip(x) for x in dbdefs), "",
                        "\n".join(d["locations"]), d.get("first_seen", ""), d.get("last_seen", ""),
                        known_cell(term, d), ctx_text(d)])
    return len(terms)


def admin_report(name):
    """3.0.1: where a command-line result goes (--selftest with files, --install-knowledge, the update commands): logs\\
    normally. SCIF-ready keeps no logs at all, so there it goes to the program's _local_sandbox folder, beside
    qt_selftest.txt, and never creates a logs folder."""
    d = SANDBOX_DIR if secure.ACTIVE else LOG_DIR
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def run_selftest(paths):
    """--selftest <files>: read the files and report. 3.0.1: in SCIF-ready the report is content-free (how many files and
    terms, the security checks, OK or the error's type): no file names, no progress lines, no terms or definitions."""
    scif = bool(secure.ACTIVE)
    out = admin_report("selftest.txt")
    with open(out, "w", encoding="utf-8") as f:
        try:
            res = analyze_batch(paths, (lambda m: None) if scif else (lambda m: f.write(m + "\n")))
            import openpyxl.xml as _oxml
            security = (f"Security: network guard={socket.socket.connect is _guarded_connect}, "
                        f"office XML entities disabled={_SAFE_XML is not None}, openpyxl defusedxml={_oxml.DEFUSEDXML}\n")
            if scif:
                f.write(f"SCIF-ready self test: {len(paths)} file(s) read, {len(res)} term(s) found. Nothing about the files "
                        "or what they hold is kept.\n" + security)
                if OCR_BACKEND == "tesseract":
                    f.write(f"OCR sandbox: {OCR_SANDBOX_STATUS}\n")
                f.write("SELFTEST OK\n")
                return
            f.write(f"\nOCR models: {OCR_MODEL_INFO}\nText finder: {doctr_info()}\nKnowledge: {knowledge_status()}\nOCR settings: {json.dumps(OCR_CFG)}\n")
            f.write(security)
            if trainer_available():
                import trainerkit, tess_train    # the Trainer's rules and Improve Reading load inside this program
                f.write(f"Training features: on (Trainer window and Improve Reading loaded; "
                        f"{len(tess_train.read_samples(TRAIN_DIR))} saved lines)\n")
            else:
                f.write("Training features: in Stationkeeper Training; this program saves corrections only"
                        + ("" if APP_CFG["allow_training"] else " (off: allow_training = false)") + "\n")
            if OCR_BACKEND == "tesseract":
                f.write(f"OCR sandbox: {OCR_SANDBOX_STATUS}\n")
                if APP_CFG["ocr_sandbox"] and os.name == "nt":
                    import sandbox
                    f.write(f"Sandbox network probe (Windows curl.exe run in the same sandbox): {sandbox.network_probe()}\n")
            f.write(f"\nRESULTS: {len(res)} terms\n")
            for term, d in res.items():
                f.write(f"{term}\t{d['category']}\t{d['count']}\t{d['status']}\t{d['selected_definition']}\n")
            f.write("SELFTEST OK\n")
        except Exception as e:
            f.write(f"{type(e).__name__}\n" if scif else traceback.format_exc())     # SCIF: the type only, never a message
            f.write("SELFTEST FAILED\n")

if __name__ == "__main__":                      # 3.14.0: the command-line tools only; the window is Stationkeeper (Qt)
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        run_selftest(sys.argv[2:])
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--install-knowledge":   # used by build.ps1 -KnowledgePack
        with open(admin_report("knowledge_install.txt"), "w", encoding="utf-8") as f:
            try:
                f.write(install_knowledge_pack(sys.argv[2]) + "\nINSTALL OK\n")
            except Exception:
                f.write(traceback.format_exc() + "INSTALL FAILED\n")
        sys.exit(0)
