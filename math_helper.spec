# -*- mode: python ; coding: utf-8 -*-
# Math reader add-on: AcronymHunterMath.exe (PyTorch CPU + transformers + IBM Granite-Docling-258M).
# Built by build_math_addon.ps1 in its own venv (venv_math). The model files are copied next to the exe by the
# build script, not bundled here.
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []
for _pkg in ['transformers', 'tokenizers', 'safetensors']:
    d, b, h = collect_all(_pkg)
    datas += d; binaries += b; hiddenimports += h
_keep = ('transformers.models.idefics3', 'transformers.models.llama', 'transformers.models.gpt2', 'transformers.models.auto',
         'transformers.models.siglip', 'transformers.models.idefics2')
hiddenimports = [h for h in hiddenimports
                 if not h.startswith(('transformers.models.', 'transformers.commands', 'transformers.pipelines')) or h.startswith(_keep)]

a = Analysis(['math_helper.py'], pathex=[], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['tkinter', 'matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter', 'notebook', 'pytest',
                       'torchvision', 'torchaudio', 'tensorflow', 'jax', 'flax', 'onnx', 'onnxruntime', 'cv2',
                       'sklearn', 'datasets', 'accelerate', 'bitsandbytes', 'triton'],
             noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AcronymHunterMath', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=True, icon='assets/scanner.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='math_addon')
