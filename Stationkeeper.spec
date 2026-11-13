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
for _pkg in ['pypdfium2', 'pypdfium2_raw', 'rapidfuzz', 'openpyxl', 'onnxruntime', 'pptx'] + ([] if US else ['rapidocr_onnxruntime']):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# ONNX Runtime ships model-conversion scripts (onnxruntime\transformers: GPT-2, Llama, Whisper...). The app never uses
# them, and Core must hold no language-model tooling (tools\check_core.py), so their files are left out too.
_ort_tools = ('onnxruntime/transformers', 'onnxruntime/quantization', 'onnxruntime/tools')
datas = [d for d in datas if not d[1].replace('\\', '/').startswith(_ort_tools)]
hiddenimports = [h for h in hiddenimports if not h.startswith(('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools'))]
# 3.47.0: imgcore, this project's own compiled picture steps (native\imgcore.c), built by build.ps1 into vendor\imgcore.
# It replaces OpenCV in US editions; the legacy edition keeps OpenCV for RapidOCR.
if not os.path.isfile('vendor/imgcore/imgcore.dll'):
    raise SystemExit('vendor\\imgcore\\imgcore.dll missing: build.ps1 compiles native\\imgcore.c first')
binaries += [('vendor/imgcore/imgcore.dll', '.')]
datas += [('effortdata/effort-data.schema.json', 'effortdata')]   # 4.9.0: the effort data's JSON Schema, app data (not a document)
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
_edition_excludes = (['rapidocr_onnxruntime', 'pyclipper', 'shapely', 'yaml', 'six', 'tqdm', 'colorama', 'cv2',
                      'ssl', '_ssl', 'asyncio', 'multiprocessing', 'psutil'] if US else [])


# Drop hidden imports for submodules excluded below (avoids noisy "not found" errors in the log)
_skip = ('onnxruntime.transformers', 'onnxruntime.quantization', 'onnxruntime.tools', 'pymupdf.layout')
hiddenimports = [h for h in hiddenimports if not h.startswith(_skip)]
hiddenimports += ['defusedxml', 'defusedxml.ElementTree']  # openpyxl uses it only if importable
hiddenimports += ['pictures', 'corrections']   # pictures; corrections (2.15.0)
# 3.14.0: the classic tkinter window is gone; the engine modules it shared are named here so the Qt build finds them.
hiddenimports += ['equations', 'diag', 'effort', 'custdefs', 'volcheck', 'compliance', 'docxw', 'complearn', 'placelearn', 'cwords',
                  'workspace', 'setupdoc', 'master_db', 'keywords', 'offerings', 'acrrules', 'qacheck', 'trainpack']
if TRAINING:
    hiddenimports += ['trainerkit']   # the Trainer's rules and Improve Reading: Stationkeeper Training only
hiddenimports += ['skia']   # Google Skia (BSD-3): draws SVG pictures for OCR
hiddenimports += ['skqt.qadrawer', 'skqt.reshredbar', 'skqt.effortvaluesview', 'skqt.shredpick', 'skqt.rulesdates', 'reshred',
                  'shredtypes', 'skqt.fixtext', 'matrixhistory', 'newversion', 'skqt.placemode', 'skqt.outlinepage', 'skqt.typechips', 'skqt.placepane', 'skqt.shredfocus', 'effortdata', 'skqt.watchauto', 'skqt.docgroups', 'skqt.graphicspage', 'skqt.makechecked', 'skqt.shredband', 'skqt.shredselbar', 'skqt.shredprogress', 'ocrjoin', 'skqt.overviewpage', 'skqt.effortpages', 'skqt.undoline', 'skqt.namedtplpage', 'skqt.globalview', 'skqt.styleedit']   # 4.1.0, 4.2.0: reached only through __import__ (tests/test_hidden_imports.py)
datas += [('assets/scanner.ico', 'assets'), ('assets/trainer.ico', 'assets'), ('assets/scanner_256.png', 'assets')]   # window/taskbar icons; the menu's Stationkeeper mark (2.88.0)
if os.path.isdir('assets/brand'):              # 3.0.3: the company logos built into the program (logo_01.png...)
    datas += [('assets/brand', 'assets/brand')]
datas += [('assets/common_words.txt', 'assets')]   # SCOWL common words: sentence-end words are not abbreviations
datas += [('assets/spelling_words.txt', 'assets')]   # 3.54.0: SCOWL words for Technical Edit's spelling check
datas += [('README.txt', 'docs'), ('OVERVIEW.md', 'docs'), ('SECURITY.md', 'docs')]   # 2.90.0: the read-me files live in the program; the app keeps About Stationkeeper filled from them

def make_analysis(script, qt=True):
  return Analysis(
    [script],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + (['skqt', 'skqt.mainwin', 'skqt.readpage', 'skqt.assign', 'skqt.design', 'skqt.structure', 'skqt.prove', 'structure_ops', 'skqt.matrixpage', 'skqt.setuppage', 'skqt.crosswalkpage', 'crosswalk', 'effortstate', 'skqt.homepage', 'skqt.dashpage', 'reviewpkt', 'skqt.recordpage', 'skqt.reviewpage', 'acrsession', 'skqt.acronympage', 'skqt.effortlistpage', 'docintake', 'skqt.custdocs', 'skqt.qapage', 'skqt.keywordspage', 'skqt.exportallpage', 'skqt.settingspage', 'outline_ops', 'structstart', 'capture', 'skqt.trainingwin', 'skqt.trainerpage', 'skqt.pkgimport', 'skqt.updates', 'updatepack', 'edsign', 'skqt.people', 'authorlist', 'skqt.safety', 'skqt.modes', 'lineage', 'workmode', 'datahome', 'effortcheck', 'supportfile', 'skqt.helpcenter', 'skqt.progress', 'skqt.librarypage', 'ctxdocs', 'skqt.ctxassign', 'changereview', 'skqt.changeview', 'skqt.nowheel', 'skqt.listspage', 'skqt.adaptive', 'skqt.whereview', 'delivboard', 'skqt.delivboardview', 'branding', 'effortcal', 'skqt.brandview', 'skqt.calview', 'teampack', 'skqt.teamview', 'effortfolders', 'unfiled', 'effortsummary', 'postsub', 'skqt.effortshome', 'skqt.unfiledview', 'skqt.postsubpage', 'tzones', 'readablejob', 'tqexport', 'skqt.stagesedit', 'process', 'skqt.processview', 'skqt.rolesview', 'doctypes', 'skqt.doctypeui', 'skqt.doctypesview', 'watch', 'skqt.watchview', 'folderplan', 'skqt.folderplanview', 'ocrpdf', 'sheetview', 'captures', 'skqt.captureview', 'sensitivity', 'secure', 'buildvariant', 'skqt.sensgate', 'custqa', 'skqt.custqapage', 'whatchanged', 'skqt.whatview', 'custfocus', 'amendinst', 'skqt.guide', 'skqt.starteffort', 'graphics', 'customdict', 'skqt.dictview', 'effortsched', 'sincelast', 'pagebudget', 'mywork', 'skqt.schedview', 'skqt.budgetview', 'skqt.myworkpage', 'themes', 'storyboard', 'skqt.storyboardpage', 'walloftruth', 'skqt.wallpage', 'pkgcheck', 'xrefcheck', 'draftcompare', 'skqt.checkspage', 'prodrules', 'prodcopy', 'prodfix', 'prodword', 'prodlearn', 'prodtemplate', 'issuelog', 'skqt.issueview', 'prodparts', 'prodoffice', 'stagecolors', 'roleaccess', 'skqt.roleview', 'prodengine.pe.listnum', 'prodengine.pe.tablestyles', 'skqt.prodstdpage', 'skqt.prodfixpage', 'prodengine', 'prodengine.engine', 'prodengine.engine.pkg', 'prodengine.engine.guard', 'prodengine.engine.fingerprint', 'prodengine.engine.ordered', 'prodengine.engine.safewrite', 'prodengine.engine.ops', 'prodengine.engine.ops.word_ops', 'prodengine.engine.ops.merge', 'prodengine.pe', 'prodengine.pe.rules', 'prodengine.pe.tables', 'prodengine.pe.docmap', 'prodengine.pe.fixes', 'prodengine.pe.fixes2', 'prodengine.pe.sections', 'prodengine.pe.hf', 'prodengine.pe.lists', 'prodengine.pe.terms', 'prodengine.pe.fonts', 'compliance_read',
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
             + ['tkinter', '_tkinter', 'customtkinter', 'darkdetect', 'PIL.ImageTk', 'PIL._tkinter_finder']   # 3.14.0: no classic window
             + ['docx']   # 3.42.0: python-docx is for the tests only; the program reads Word with its own reader
             + ['_hashlib', 'PIL._avif', 'PIL.AvifImagePlugin', 'PIL._imagingft']   # 3.14.1: OpenSSL (Python's own SHA and BLAKE2 serve
                                                                                    # every hash), AVIF pictures, FreeType text drawing
             + ([] if TRAINING else ['tess_train', 'trainerkit']),
    noarchive=False,
    optimize=0,
  )

# Only the Qt window ships: Stationkeeper.exe (skqt_main.py) and StationkeeperTraining.exe (skqt_training.py). 3.14.0: the
# classic tkinter window is retired and no longer in the source.
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
    return _keep(entry) and _lean(dest) and not ('qt6network' in dest or 'qtnetwork' in dest or '\\plugins\\tls' in dest
                                 or '\\plugins\\networkinformation' in dest)

# 3.14.1: nothing ships that the program does not use.
# Tesseract runs as its own program from tesseract\ with its DLLs beside it; PyInstaller also copies those DLLs to the
# top of _internal (it follows tesseract.exe's dependencies), where nothing loads them.
_TESS_DLLS = {f.lower() for f in os.listdir('vendor/tesseract') if f.lower().endswith('.dll')} if os.path.isdir('vendor/tesseract') else set()
# Qt: the window draws with the Windows platform plugin and the Fusion style, in English, with no OpenGL and no SVG.
# Pictures it opens: PNG and BMP (built in), JPEG, GIF, and the window's ICO icon.
_QT_IMAGE_KEEP = {'qjpeg.dll', 'qgif.dll', 'qico.dll'}
def _lean(dest):
    if '\\' not in dest and dest in _TESS_DLLS | {'libcrypto-3.dll'}:
        return False
    if dest.startswith('pyside6\\'):
        rest = dest[len('pyside6\\'):]
        if rest in ('opengl32sw.dll', 'qt6svg.dll') or rest.startswith('translations\\'):
            return False
        if rest.startswith(('plugins\\generic\\', 'plugins\\styles\\', 'plugins\\iconengines\\')):
            return False
        if rest.startswith('plugins\\platforms\\') and rest != 'plugins\\platforms\\qwindows.dll':
            return False
        if rest.startswith('plugins\\imageformats\\') and rest.split('\\')[-1] not in _QT_IMAGE_KEEP:
            return False
    return True

a = make_analysis('skqt_training.py' if TRAINING else 'skqt_main.py', qt=True)
a.datas = [e for e in a.datas if _keep_qt(e)]
a.binaries = [e for e in a.binaries if _keep_qt(e)]

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
