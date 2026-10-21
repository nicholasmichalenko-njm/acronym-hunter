"""After conversion: embed the reader's character list in rec.onnx, copy rec_keys.txt, and smoke-test the model.
  python onnx_finish.py <rec|det> <model.onnx> <dict.txt> <out dir>"""
import sys, os, shutil
import numpy as np, onnx, onnxruntime as ort
kind, path, dict_path, out = sys.argv[1:5]
if kind == "rec":
    keys = open(dict_path, encoding="utf-8").read().splitlines()
    m = onnx.load(path); meta = m.metadata_props.add(); meta.key, meta.value = "character", "\n".join(keys); onnx.save(m, path)
    shutil.copy2(dict_path, os.path.join(out, "rec_keys.txt"))
    shape = (1, 3, 48, 320)
else:
    shape = (1, 3, 640, 640)
sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
sess.run(None, {sess.get_inputs()[0].name: np.zeros(shape, dtype=np.float32)})
print(f"  {os.path.basename(path)}: {os.path.getsize(path) / 1e6:.1f} MB, loads and runs in ONNX Runtime")
