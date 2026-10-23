"""Export Mindee's official docTR weights to ONNX ourselves (provenance: we convert, nobody else).
Run with venv_gpu (PyTorch + docTR from source). Writes export\\doctr_det.onnx, export\\doctr_reco.onnx,
export\\EXPORT_INFO.json (versions, weight URLs and SHA-256 of every file)."""
import hashlib, json, os, sys
import torch
import doctr
from doctr.models import db_mobilenet_v3_large, crnn_vgg16_bn
from doctr.models.utils import export_model_to_onnx

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "export"); os.makedirs(OUT, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest().upper()
info = {"doctr": doctr.__version__, "torch": torch.__version__, "models": {}}
for name, ctor, shape in (("doctr_det", db_mobilenet_v3_large, (1, 3, 1024, 1024)),
                          ("doctr_reco", crnn_vgg16_bn, (1, 3, 32, 128))):
    m = ctor(pretrained=True, exportable=True).eval()
    url = m.cfg.get("url", "")
    path = export_model_to_onnx(m, os.path.join(OUT, name), torch.rand(*shape))
    cache = os.path.join(os.path.expanduser("~"), ".cache", "doctr", "models", os.path.basename(url))
    info["models"][name] = {"arch": ctor.__name__, "weights_url": url,
                            "weights_sha256": sha(cache) if os.path.exists(cache) else "",
                            "onnx": os.path.basename(path), "onnx_sha256": sha(path),
                            "mean": list(m.cfg["mean"]), "std": list(m.cfg["std"]), "input_shape": list(m.cfg["input_shape"]),
                            "vocab": m.cfg.get("vocab", "")}
    print(name, path, os.path.getsize(path) // 1024, "KB")
json.dump(info, open(os.path.join(OUT, "EXPORT_INFO.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "vocab"} for k, v in info["models"].items()}, indent=1))
