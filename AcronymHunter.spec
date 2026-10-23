# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Edition (set by build.ps1 -Edition):
#   us      Tesseract OCR (HP origin, Google-developed, Google-trained English model). No RapidOCR, PaddleOCR, or ONNX Runtime.
#   legacy  RapidOCR + PaddleOCR PP-OCRv4 models on ONNX Runtime (v1.5.x engine).
US = os.environ.get('AH_EDITION', 'us') == 'us'

datas = []
binaries = []
hiddenimports = []
for _pkg in ['pymupdf', 'customtkinter', 'rapidfuzz', 'openpyxl'] + ([] if US else ['rapidocr_onnxruntime', 'onnxruntime']):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
if US:
    # Tesseract engine + 3 training tools + their DLLs + Google's eng.traineddata, fetched by tools\fetch_tesseract.ps1
    if not os.path.isfile('vendor/tesseract/tesseract.exe'):
        raise SystemExit('vendor\\tesseract missing: run tools\\fetch_tesseract.ps1 first')
    datas += [('vendor/tesseract', 'tesseract')]
    hiddenimports += ['tess_train']
_edition_excludes = (['rapidocr_onnxruntime', 'onnxruntime', 'pyclipper', 'shapely', 'yaml'] if US else [])


# Drop hidden imports for submodules excluded below (avoids noisy "not found" errors in the log)
_skip = ('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools', 'pymupdf.layout')
hiddenimports = [h for h in hiddenimports if not h.startswith(_skip)]
hiddenimports += ['defusedxml', 'defusedxml.ElementTree']  # openpyxl uses it only if importable
datas += [('assets/scanner.ico', 'assets'), ('assets/trainer.ico', 'assets')]   # window/taskbar icons at runtime

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
    excludes=['pymupdf.layout', 'pymupdf4llm', 'matplotlib', 'scipy', 'pandas',
              'IPython', 'jupyter', 'notebook', 'pytest',
              'onnxruntime.quantization', 'onnxruntime.transformers', 'onnxruntime.tools'] + _edition_excludes,
    noarchive=False,
    optimize=0,
  )

a = make_analysis('app_gui.py')
b = make_analysis('trainer_gui.py')   # companion Trainer: region rescans + training samples
# Strip payload the app never uses: PyMuPDF layout models + C headers/libs, OpenCV video (FFmpeg) DLL.
def _keep(entry):
    dest = entry[0].replace('/', '\\').lower()
    return not (dest.startswith('pymupdf\\layout') or dest.startswith('pymupdf\\mupdf-devel')
                or 'opencv_videoio_ffmpeg' in dest
                or dest.startswith('onnxruntime\\datasets'))   # ONNX Runtime demo models: unused, and the leak check allows no stray .onnx
for an in (a, b):
    an.datas = [e for e in an.datas if _keep(e)]
    an.binaries = [e for e in an.binaries if _keep(e)]

pyz = PYZ(a.pure)
pyz_b = PYZ(b.pure)

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
    upx=False,  # UPX-packed DLLs trip corporate EDR/AV and can corrupt onnxruntime
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
exe_b = EXE(
    pyz_b,
    b.scripts,
    [],
    exclude_binaries=True,
    name='AcronymHunterTrainer',
    icon='assets/trainer.ico',
    version='version_info_trainer.txt',  # Windows file properties (publisher, description, version)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-packed DLLs trip corporate EDR/AV and can corrupt onnxruntime
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
    exe_b,          # both programs share one _internal folder: the Trainer adds only a few MB
    b.binaries,
    b.datas,
    strip=False,
    upx=False,  # UPX-packed DLLs trip corporate EDR/AV and can corrupt onnxruntime
    upx_exclude=[],
    name='AcronymHunter',
)
