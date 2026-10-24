# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Edition (set by build.ps1 -Edition):
#   us      Tesseract OCR (HP origin, Google-developed, Google-trained English model) plus docTR (Mindee, Apache 2.0) on
#           ONNX Runtime (Microsoft, MIT), models exported by this project. No RapidOCR or PaddleOCR.
#   legacy  RapidOCR + PaddleOCR PP-OCRv4 models on ONNX Runtime (v1.5.x engine).
US = os.environ.get('AH_EDITION', 'us') == 'us'

datas = []
binaries = []
hiddenimports = []
for _pkg in ['pypdfium2', 'pypdfium2_raw', 'customtkinter', 'rapidfuzz', 'openpyxl', 'onnxruntime'] + ([] if US else ['rapidocr_onnxruntime']):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# ONNX Runtime ships model-conversion scripts (onnxruntime\transformers: GPT-2, Llama, Whisper...). The app never uses
# them, and Core must hold no language-model tooling (tools\check_core.py), so their files are left out too.
_ort_tools = ('onnxruntime/transformers', 'onnxruntime/quantization', 'onnxruntime/tools')
datas = [d for d in datas if not d[1].replace('\\', '/').startswith(_ort_tools)]
hiddenimports = [h for h in hiddenimports if not h.startswith(('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools'))]
if US:
    # Tesseract engine + 3 training tools + their DLLs + Google's eng.traineddata, fetched by tools\fetch_tesseract.ps1
    if not os.path.isfile('vendor/tesseract/tesseract.exe'):
        raise SystemExit('vendor\\tesseract missing: run tools\\fetch_tesseract.ps1 first')
    datas += [('vendor/tesseract', 'tesseract')]
    hiddenimports += ['tess_train', 'sandbox']
    # docTR text finder + reader (2.1.0): two ONNX models exported by this project from Mindee's weights
    if os.environ.get('AH_CLASSIC') != '1':      # Classic build: Tesseract only, no docTR
        if not os.path.isfile('vendor/doctr/doctr_models.json'):
            raise SystemExit('vendor\\doctr missing: export the docTR models first (see vendor\\doctr\\SOURCE.txt)')
        datas += [('vendor/doctr', 'doctr')]
        hiddenimports += ['doctr_engine']
# US edition also leaves out standard-library and helper modules the app never uses that link Windows networking:
# ssl (TLS), asyncio (_overlapped), multiprocessing, psutil. Checked by tools\network_audit.py at build time.
_edition_excludes = (['rapidocr_onnxruntime', 'pyclipper', 'shapely', 'yaml',
                      'ssl', '_ssl', 'asyncio', 'multiprocessing', 'psutil'] if US else [])


# Drop hidden imports for submodules excluded below (avoids noisy "not found" errors in the log)
_skip = ('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools', 'pymupdf.layout')
hiddenimports = [h for h in hiddenimports if not h.startswith(_skip)]
hiddenimports += ['defusedxml', 'defusedxml.ElementTree']  # openpyxl uses it only if importable
hiddenimports += ['trainer_gui', 'preview_pane', 'PIL.ImageTk']   # the Trainer opens as a window inside the scanner (one program)
hiddenimports += ['equations', 'symbol_picker', 'help_guide', 'diag', 'feedback', 'effort', 'effort_ui', 'custdefs', 'volcheck', 'volcheck_ui', 'compliance', 'compliance_ui', 'docxw', 'complearn', 'workspace', 'workspace_ui']   # equation and symbol recognition (2.0.0), symbol picker (2.3.0)
hiddenimports += ['skia']   # Google Skia (BSD-3): draws SVG pictures for OCR
datas += [('assets/scanner.ico', 'assets'), ('assets/trainer.ico', 'assets')]   # window/taskbar icons at runtime
datas += [('assets/help', 'assets/help')]   # "?" guide screenshots
datas += [('assets/common_words.txt', 'assets')]   # SCOWL common words: sentence-end words are not abbreviations

def make_analysis(script):
  return Analysis(
    [script],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # pymupdf/__init__.py runs `try: import pymupdf.layout except ImportError`.
    # The layout add-on (pymupdf_layout / pymupdf4llm) is unused by this app and its
    # ONNX/YAML resources do not survive freezing -> FileNotFoundError at startup.
    # Excluding it turns that import into a clean ImportError that PyMuPDF swallows.
    excludes=['pymupdf', 'fitz', 'pymupdf.layout', 'pymupdf4llm', 'matplotlib', 'scipy', 'pandas',
              'IPython', 'jupyter', 'notebook', 'pytest',
              'onnxruntime.quantization', 'onnxruntime.transformers', 'onnxruntime.tools'] + _edition_excludes,
    noarchive=False,
    optimize=0,
  )

a = make_analysis('app_gui.py')
# Strip payload the app never uses: PyMuPDF layout models + C headers/libs, OpenCV video (FFmpeg) DLL.
def _keep(entry):
    dest = entry[0].replace('/', '\\').lower()
    return not (dest.startswith('pymupdf\\layout') or dest.startswith('pymupdf\\mupdf-devel')
                or 'opencv_videoio_ffmpeg' in dest
                or dest.startswith('onnxruntime\\datasets'))   # ONNX Runtime demo models: unused, and the leak check allows no stray .onnx
a.datas = [e for e in a.datas if _keep(e)]
a.binaries = [e for e in a.binaries if _keep(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AcronymHunter',
    icon='assets/scanner.ico',
    version='version_info.txt',  # Windows file properties (publisher, description, version)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-packed DLLs trip corporate EDR/AV
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AcronymHunter',
)
