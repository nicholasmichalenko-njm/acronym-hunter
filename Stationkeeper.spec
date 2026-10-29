# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Edition (set by build.ps1 -Edition):
#   us      Tesseract OCR (HP origin, Google-developed, Google-trained English model) plus docTR (Mindee, Apache 2.0) on
#           ONNX Runtime (Microsoft, MIT), models exported by this project. No RapidOCR or PaddleOCR.
#   legacy  RapidOCR + PaddleOCR PP-OCRv4 models on ONNX Runtime (v1.5.x engine).
US = os.environ.get('AH_EDITION', 'us') == 'us'
# App (set by build.ps1 -App, 2.15.0):
#   user      Stationkeeper: scans and saves corrections. No Trainer, no Improve Reading, no Tesseract training tools.
#   training  Stationkeeper Training: imports corrections packs, trains and tests the reader, exports Knowledge Packs.
TRAINING = os.environ.get('AH_APP', 'user') == 'training'

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
    if TRAINING:
        datas += [('vendor/tesseract', 'tesseract')]
        hiddenimports += ['tess_train', 'sandbox']
    else:   # the user app ships the engine only: the training tools stay in Stationkeeper Training
        _tools = ('lstmtraining.exe', 'lstmeval.exe', 'combine_tessdata.exe', 'unicharset_extractor.exe', 'merge_unicharsets.exe',
                  'combine_lang_model.exe')
        for _root, _dirs, _files in os.walk('vendor/tesseract'):
            if 'langdata' in os.path.relpath(_root, 'vendor/tesseract').split(os.sep):
                continue                              # 2.55.0: the character-set table is for training only
            for _f in _files:
                if _f.lower() not in _tools and not _f.lower().startswith('libicu'):   # ICU: only the training tools load it
                    _rel = os.path.relpath(_root, 'vendor/tesseract')
                    datas += [(os.path.join(_root, _f), 'tesseract' if _rel == '.' else os.path.join('tesseract', _rel))]
        hiddenimports += ['sandbox']
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
hiddenimports += ['preview_pane', 'PIL.ImageTk', 'pictures', 'corrections']   # picture preview; corrections (2.15.0)
if TRAINING:
    hiddenimports += ['trainer_gui', 'training_app']   # the Trainer and Improve Reading: Stationkeeper Training only
hiddenimports += ['equations', 'symbol_picker', 'help_guide', 'diag', 'feedback', 'effort', 'effort_ui', 'custdefs', 'volcheck', 'volcheck_ui', 'compliance', 'compliance_ui', 'docxw', 'complearn', 'placelearn', 'cwords', 'exportall_ui', 'shell_ui', 'compliance_page', 'workspace', 'workspace_ui', 'ai_stack', 'ai_ui', 'setupdoc', 'setup_ui', 'context', 'effort_wizard', 'effort_home', 'master_db', 'keywords', 'keywords_ui', 'offerings']   # equation and symbol recognition (2.0.0), symbol picker (2.3.0)
hiddenimports += ['skia']   # Google Skia (BSD-3): draws SVG pictures for OCR
datas += [('assets/scanner.ico', 'assets'), ('assets/trainer.ico', 'assets'), ('assets/scanner_256.png', 'assets')]   # window/taskbar icons; the menu's Stationkeeper mark (2.88.0)
datas += [('assets/help', 'assets/help')]   # "?" guide screenshots
datas += [('assets/common_words.txt', 'assets')]   # SCOWL common words: sentence-end words are not abbreviations
datas += [('README.txt', 'docs'), ('OVERVIEW.md', 'docs'), ('SECURITY.md', 'docs')]   # 2.90.0: the read-me files live in the program; the app keeps About Stationkeeper filled from them

def make_analysis(script, qt=False):
  return Analysis(
    [script],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + (['skqt', 'skqt.mainwin', 'skqt.readpage', 'skqt.assign', 'skqt.theme', 'skqt.design', 'skqt.structure', 'skqt.prove', 'structure_ops', 'skqt.matrixpage', 'skqt.setuppage', 'skqt.crosswalkpage', 'crosswalk', 'effortstate', 'skqt.homepage', 'skqt.dashpage', 'reviewpkt', 'skqt.recordpage', 'skqt.reviewpage', 'acrsession', 'skqt.acronympage', 'skqt.effortlistpage', 'docintake', 'skqt.custdocs', 'skqt.qapage', 'skqt.keywordspage', 'skqt.exportallpage', 'skqt.settingspage', 'outline_ops', 'structstart', 'capture', 'skqt.trainingwin', 'skqt.trainerpage', 'skqt.pkgimport', 'skqt.updates', 'updatepack', 'edsign', 'skqt.people', 'authorlist', 'skqt.safety', 'skqt.modes', 'lineage', 'workmode', 'datahome', 'effortcheck', 'supportfile', 'skqt.helpcenter', 'skqt.progress', 'skqt.librarypage', 'ctxdocs', 'skqt.ctxassign', 'changereview', 'skqt.changeview', 'skqt.nowheel', 'skqt.listspage', 'skqt.adaptive', 'skqt.whereview', 'delivboard', 'skqt.delivboardview', 'branding', 'effortcal', 'skqt.brandview', 'skqt.calview', 'teampack', 'skqt.teamview', 'effortfolders', 'unfiled', 'effortsummary', 'postsub', 'skqt.effortshome', 'skqt.unfiledview', 'skqt.postsubpage', 'tzones', 'readablejob', 'tqexport', 'skqt.stagesedit', 'process', 'skqt.processview', 'skqt.rolesview', 'compliance_read',
                                    'assign_ops'] if qt else []),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # pymupdf/__init__.py runs `try: import pymupdf.layout except ImportError`.
    # The layout add-on (pymupdf_layout / pymupdf4llm) is unused by this app and its
    # ONNX/YAML resources do not survive freezing -> FileNotFoundError at startup.
    # Excluding it turns that import into a clean ImportError that PyMuPDF swallows.
    excludes=['pymupdf', 'fitz', 'pymupdf.layout', 'pymupdf4llm', 'matplotlib', 'scipy', 'pandas',
              'IPython', 'jupyter', 'notebook', 'pytest',
              'onnxruntime.quantization', 'onnxruntime.transformers', 'onnxruntime.tools',
              ] + (['PySide6.QtNetwork'] if qt else ['PySide6', 'shiboken6']) + _edition_excludes   # Qt only in Stationkeeper (Qt), 2.59.0
             + ([] if TRAINING else ['trainer_gui', 'tess_train', 'training_app']),
    noarchive=False,
    optimize=0,
  )

# 2.75.0: only the Qt window ships. Stationkeeper.exe (skqt_main.py) and StationkeeperTraining.exe (skqt_training.py);
# the classic tkinter programs are no longer built (AH_QT=0 builds the classic program alone, for a one-off comparison).
QT_APP = os.environ.get('AH_QT', '1') == '1'
# Strip payload the app never uses: PyMuPDF layout models + C headers/libs, OpenCV video (FFmpeg) DLL.
def _keep(entry):
    dest = entry[0].replace('/', '\\').lower()
    return not (dest.startswith('pymupdf\\layout') or dest.startswith('pymupdf\\mupdf-devel')
                or 'opencv_videoio_ffmpeg' in dest
                or dest.startswith('onnxruntime\\datasets'))   # ONNX Runtime demo models: unused, and the leak check allows no stray .onnx
# No Qt network parts: QtNetwork and the plugins that need it (TLS back ends, network information) are left out.
# The app imports none of them; tools\network_audit.py would fail the build on Qt6Network.dll.
def _keep_qt(entry):
    dest = entry[0].replace('/', '\\').lower()
    return _keep(entry) and not ('qt6network' in dest or 'qtnetwork' in dest or '\\plugins\\tls' in dest
                                 or '\\plugins\\networkinformation' in dest)

if QT_APP:
    a = make_analysis('skqt_training.py' if TRAINING else 'skqt_main.py', qt=True)
    a.datas = [e for e in a.datas if _keep_qt(e)]
    a.binaries = [e for e in a.binaries if _keep_qt(e)]
else:
    a = make_analysis('training_app.py' if TRAINING else 'app_gui.py')
    a.datas = [e for e in a.datas if _keep(e)]
    a.binaries = [e for e in a.binaries if _keep(e)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StationkeeperTraining' if TRAINING else 'Stationkeeper',
    icon='assets/trainer.ico' if TRAINING else 'assets/scanner.ico',
    version='version_info_trainer.txt' if TRAINING else 'version_info.txt',  # Windows file properties (publisher, description, version)
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
    name='StationkeeperTraining' if TRAINING else 'Stationkeeper',
)
