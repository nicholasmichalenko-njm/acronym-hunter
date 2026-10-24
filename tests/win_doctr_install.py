"""Windows: install the trained docTR models from the training kit output, check SHA gate, Knowledge Pack round trip, Undo."""
import os, sys, json, shutil, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app_gui as A
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(A.BASE_DIR, "_local_sandbox", "kitdev", "output", "models")
print("bundled:", A.DOCTR_DIR)
found = A.load_trained_models(SRC)
print("installed:", found)
print("now using:", A.DOCTR_DIR, "|", A.doctr_info()[:140])
assert A.DOCTR_DIR.endswith(os.path.join("config", "models", "doctr"))
# Knowledge Pack carries them
pack = os.path.join(tempfile.mkdtemp(), "pack.zip")
info = A.make_knowledge_pack(pack, "test")
names = zipfile.ZipFile(pack).namelist()
print("pack has docTR:", [n for n in names if "doctr" in n])
# tamper: the SHA gate must refuse and fall back to the bundled models
p = os.path.join(A.MODELS_DIR, "doctr", "doctr_reco.onnx")
orig = open(p, "rb").read()
open(p, "ab").write(b"x")
A.reset_ocr_engine()
print("after tamper, using:", A.DOCTR_DIR)
assert not A.DOCTR_DIR.endswith(os.path.join("config", "models", "doctr"))
open(p, "wb").write(orig); A.reset_ocr_engine()
assert A.DOCTR_DIR.endswith(os.path.join("config", "models", "doctr"))
# undo restores the bundled models
print("undo:", A.restore_last_knowledge_backup())
print("after undo, using:", A.DOCTR_DIR)
assert not os.path.isdir(os.path.join(A.MODELS_DIR, "doctr")) or not os.listdir(os.path.join(A.MODELS_DIR, "doctr"))
print("PASS")
