# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rapidocr_onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rapidfuzz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


# Drop hidden imports for submodules excluded below (avoids noisy "not found" errors in the log)
_skip = ('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools', 'pymupdf.layout')
hiddenimports = [h for h in hiddenimports if not h.startswith(_skip)]

a = Analysis(
    ['app_gui.py'],
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
              'onnxruntime.quantization', 'onnxruntime.transformers', 'onnxruntime.tools'],
    noarchive=False,
    optimize=0,
)
# Strip payload the app never uses: PyMuPDF layout models + C headers/libs, OpenCV video (FFmpeg) DLL.
def _keep(entry):
    dest = entry[0].replace('/', '\\').lower()
    return not (dest.startswith('pymupdf\\layout') or dest.startswith('pymupdf\\mupdf-devel')
                or 'opencv_videoio_ffmpeg' in dest)
a.datas = [e for e in a.datas if _keep(e)]
a.binaries = [e for e in a.binaries if _keep(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AcronymHunter',
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
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # UPX-packed DLLs trip corporate EDR/AV and can corrupt onnxruntime
    upx_exclude=[],
    name='AcronymHunter',
)
