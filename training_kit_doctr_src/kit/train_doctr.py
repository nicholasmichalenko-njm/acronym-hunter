"""Acronym Hunter Training Kit (docTR): teach docTR's finder and reader from your Trainer samples. Offline.

    python\\python.exe kit\\train_doctr.py --check          lockdown, PyTorch, docTR, starting weights
    python\\python.exe kit\\train_doctr.py --reader         train the reader (corrected text lines)
    python\\python.exe kit\\train_doctr.py --finder         train the finder (boxed regions)
    python\\python.exe kit\\train_doctr.py --reader --finder

Samples: copy each person's Acronym Hunter training_data\\ folder into samples\\<name>\\ (images\\ + labels.txt,
regions\\ + det_labels.txt). Results: output\\models\\ (doctr_det.onnx, doctr_reco.onnx, doctr_models.json,
REPORT.txt). A model is exported only if it scores better than the current one on samples it did not learn from.
In Acronym Hunter: Tools > Knowledge > Install trained docTR models, and pick output\\models.
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys, time
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KITDIR = os.path.join(KIT, "kit")
SAMPLES = os.path.join(KIT, "samples")
WORK = os.path.join(KIT, "work")
OUT = os.path.join(KIT, "output", "models")
WEIGHTS = os.path.join(KIT, "weights")              # Mindee's starting weights: weights\models\*.pt
BASE_MODELS = os.path.join(KIT, "base_models")      # the app's bundled docTR ONNX files + doctr_models.json
DOCTR_REF = os.path.join(KIT, "doctr_ref")          # docTR's reference training scripts (recognition\, detection\)
os.environ["DOCTR_CACHE_DIR"] = WEIGHTS
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
STARTING = {"db_mobilenet_v3_large-21748dd0.pt": "21748DD02C0E40475D9EA53E72817C4F08BA90ADEA5231D0DC2C1A65D7D6B4E1",
            "crnn_vgg16_bn-0417f351.pt": "0417F3511F5C75369BDCBE06539853B9C2D170AA3BACEB2ACC454C775DDAC087"}
# Characters added to the reader's alphabet when your labels use them (the stock alphabet has none of these)
EXTRA_SYMBOLS = ("αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨΩ" "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ" "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ"
                 "±×÷·≤≥≠≈≡∝∞∂∇∫∑∏√→←↔⇒°′″‰µΩÅℓ℃℉½¼¾⅓∠⊥∥∈∉⊂∪∩∀∃∆∅")

def log(*a):
    print(*a, flush=True)
    os.makedirs(os.path.join(KIT, "output"), exist_ok=True)
    with open(os.path.join(KIT, "output", "train_log.txt"), "a", encoding="utf-8") as f:
        f.write(" ".join(str(x) for x in a) + "\n")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest().upper()

def stable_val(name):
    return int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16) % 10 == 0     # 10% held out, same split every run

# ------------------------------------------------------------------ check
def check():
    ok = True
    os.environ["KIT_SELFTEST"] = "1"            # the lockdown log marks this refusal as the self-test
    try:
        import socket
        socket.create_connection(("example.com", 443), timeout=3)
        log("NETWORK: NOT BLOCKED (lockdown missing)"); ok = False
    except OSError as e:
        log("Network lockdown: on (" + str(e)[:70] + ")")
    os.environ.pop("KIT_SELFTEST", None)
    import torch, doctr
    gpu = "none (training runs on the processor)"
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        gpu = f"{p.name}, {p.total_memory / 1024 ** 3:.1f} GB"
        cap = os.environ.get("AH_GPU_MEM_GB")
        if cap:
            gpu += f" (capped at {cap} GB for this run)"
    log(f"PyTorch {torch.__version__}, docTR {doctr.__version__}, graphics card: {gpu}")
    try:
        import huggingface_hub
        shim = getattr(huggingface_hub, "__version__", "") == "0+offline-shim"
        log("Hugging Face Hub: " + ("offline stand-in (no network code)" if shim else "REAL PACKAGE PRESENT (not expected in the kit)"))
    except ImportError:
        log("Hugging Face Hub: not installed")
    for f, want in STARTING.items():
        p = os.path.join(WEIGHTS, "models", f)
        good = os.path.isfile(p) and sha(p) == want
        log(f"Starting weights {f}: {'OK' if good else 'MISSING OR CHANGED'}"); ok &= good
    for f in ("doctr_det.onnx", "doctr_reco.onnx", "doctr_models.json"):
        good = os.path.isfile(os.path.join(BASE_MODELS, f)); ok &= good
        log(f"Base model {f}: {'OK' if good else 'MISSING'}")
    n_lines = sum(len(_read_tsv(p)) for p in glob.glob(os.path.join(SAMPLES, "*", "labels.txt")))
    n_reg = sum(len(_read_tsv(p)) for p in glob.glob(os.path.join(SAMPLES, "*", "det_labels.txt")))
    log(f"Samples found: {n_lines} text lines, {n_reg} regions (in samples\\*\\)")
    return ok

def _read_tsv(path):
    out = []
    for line in open(path, encoding="utf-8").read().splitlines():
        if "\t" in line:
            a, b = line.split("\t", 1)
            out.append((a, b))
    return out

# ------------------------------------------------------------------ datasets
def _finder():
    """docTR's finder on PyTorch (for splitting line samples into words)."""
    from doctr.models import detection_predictor
    return detection_predictor("db_mobilenet_v3_large", pretrained=True, assume_straight_pages=True)

def _split_words(det, img, text):
    """Word crops for a line sample: docTR finds the words; kept only when the count matches the label."""
    import numpy as np
    toks = text.split()
    if len(toks) <= 1:
        return [(img, text.strip())] if text.strip() else []
    arr = np.array(img.convert("RGB"))
    res = det([arr])[0]
    boxes = res["words"] if isinstance(res, dict) else res
    boxes = sorted([b for b in boxes], key=lambda b: b[0])
    if len(boxes) != len(toks):
        return []
    h, w = arr.shape[:2]
    out = []
    for b, t in zip(boxes, toks):
        x0, y0, x1, y1 = int(b[0] * w), int(b[1] * h), int(b[2] * w + 0.999), int(b[3] * h + 0.999)
        if x1 - x0 >= 2 and y1 - y0 >= 2:
            out.append((img.crop((max(0, x0 - 2), max(0, y0 - 2), min(w, x1 + 2), min(h, y1 + 2))), t))
    return out if len(out) == len(toks) else []

def build_reader_data():
    from PIL import Image
    det = _finder()
    tr, va = os.path.join(WORK, "reco_train"), os.path.join(WORK, "reco_val")
    for d in (tr, va):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "images"))
    labels = {tr: {}, va: {}}
    kept = skipped = 0
    chars = set()
    def add(img, text, key):
        nonlocal kept
        dest = va if stable_val(key) else tr
        name = hashlib.sha1((key + text).encode("utf-8")).hexdigest()[:16] + ".png"
        img.convert("RGB").save(os.path.join(dest, "images", name))
        labels[dest][name] = text; chars.update(text); kept += 1
    for lab in glob.glob(os.path.join(SAMPLES, "*", "labels.txt")):
        root = os.path.dirname(lab)
        for rel, text in _read_tsv(lab):
            text = text.strip()
            p = os.path.join(root, rel.replace("/", os.sep))
            if not text or text == "(not text)" or not os.path.isfile(p):
                continue
            words = _split_words(det, Image.open(p), text)
            if not words:
                skipped += 1; continue
            for i, (im, t) in enumerate(words):
                add(im, t, f"{rel}#{i}")
    for lab in glob.glob(os.path.join(SAMPLES, "*", "det_labels.txt")):        # text boxes inside saved regions
        root = os.path.dirname(lab)
        for rel, js in _read_tsv(lab):
            p = os.path.join(root, rel.replace("/", os.sep))
            if not os.path.isfile(p):
                continue
            im = Image.open(p)
            for k, box in enumerate(json.loads(js)):
                t = box.get("transcription", "").strip()
                if not t or t == "###":
                    continue
                xs = [q[0] for q in box["points"]]; ys = [q[1] for q in box["points"]]
                crop = im.crop((max(0, min(xs) - 2), max(0, min(ys) - 2), min(im.width, max(xs) + 2), min(im.height, max(ys) + 2)))
                for i, (wim, wt) in enumerate(_split_words(det, crop, t)):
                    add(wim, wt, f"{rel}#{k}#{i}")
    for d in (tr, va):
        json.dump(labels[d], open(os.path.join(d, "labels.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    log(f"Reader samples: {len(labels[tr])} words to learn from, {len(labels[va])} held out "
        f"({skipped} lines skipped: word count did not match the label)")
    return len(labels[tr]), len(labels[va]), chars

def build_finder_data():
    from PIL import Image
    tr, va = os.path.join(WORK, "det_train"), os.path.join(WORK, "det_val")
    for d in (tr, va):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "images"))
    labels = {tr: {}, va: {}}
    for lab in glob.glob(os.path.join(SAMPLES, "*", "det_labels.txt")):
        root = os.path.dirname(lab)
        for rel, js in _read_tsv(lab):
            p = os.path.join(root, rel.replace("/", os.sep))
            if not os.path.isfile(p):
                continue
            im = Image.open(p).convert("RGB")
            polys = [b["points"] for b in json.loads(js) if b.get("transcription", "###") != "###"]
            dest = va if stable_val(rel) else tr
            name = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16] + ".png"
            im.save(os.path.join(dest, "images", name))
            labels[dest][name] = {"img_dimensions": [im.height, im.width], "img_hash": "", "polygons": polys}
    for d in (tr, va):
        json.dump(labels[d], open(os.path.join(d, "labels.json"), "w", encoding="utf-8"))
    log(f"Finder samples: {len(labels[tr])} regions to learn from, {len(labels[va])} held out")
    return len(labels[tr]), len(labels[va])

# ------------------------------------------------------------------ training runs (docTR's own reference scripts)
_RUNNER = r'''
import runpy, sys, os, json
cap = os.environ.get("AH_GPU_MEM_GB")
if cap:                                   # prove a run fits a smaller card: cap PyTorch's share of graphics memory
    import torch
    if torch.cuda.is_available():
        total = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
        torch.cuda.set_per_process_memory_fraction(min(1.0, float(cap) / total))
v = os.environ.get("AH_VOCAB_EXTRA", "")
if v:
    from doctr.datasets import vocabs
    vocabs.VOCABS["acronymhunter"] = vocabs.VOCABS["french"] + "".join(c for c in json.loads(v) if c not in vocabs.VOCABS["french"])
script = sys.argv[1]; sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(script))
try:
    runpy.run_path(script, run_name="__main__")
finally:
    try:
        import torch
        if torch.cuda.is_available():
            print(f"PEAK_GPU_GB {torch.cuda.max_memory_allocated() / 1024 ** 3:.2f}", flush=True)
    except Exception:
        pass
'''

def run_ref(kind, args, extra_vocab=""):
    import torch
    runner = os.path.join(WORK, "_run_ref.py")
    open(runner, "w", encoding="utf-8").write(_RUNNER)
    script = os.path.join(DOCTR_REF, "recognition" if kind == "reco" else "detection", "train.py")
    env = dict(os.environ, AH_VOCAB_EXTRA=extra_vocab, WANDB_MODE="disabled")
    cmd = [sys.executable, runner, script] + args + ["--device", "0" if torch.cuda.is_available() else "cpu", "-j", "0"]
    t0 = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    open(os.path.join(WORK, f"{kind}_{'test' if '--test-only' in args else 'train'}.log"), "w", encoding="utf-8").write(out)
    if p.returncode != 0:
        raise RuntimeError(f"docTR {kind} run failed:\n" + out[-1500:])
    return out, time.time() - t0

def _metric(out, kind):
    """Last validation result printed by docTR's script: reader exact-match %, finder recall/precision %."""
    if kind == "reco":
        m = re.findall(r"Exact:\s*([\d.]+)%", out)
        return float(m[-1]) if m else None
    m = re.findall(r"Recall:\s*([\d.]+)%\s*\|\s*Precision:\s*([\d.]+)%", out)
    return (float(m[-1][0]), float(m[-1][1])) if m else None

def train_reader():
    n_tr, n_va, chars = build_reader_data()
    if n_tr < 20 or n_va < 2:
        log("Not enough reader samples yet (need 20+ words to learn from). Save more corrected lines in the Trainer.")
        return None
    from doctr.datasets import VOCABS
    extra = sorted(c for c in chars if c not in VOCABS["french"] and not c.isspace())
    vocab_args = ["--vocab", "acronymhunter"] if extra else []
    extra_json = json.dumps(extra + [c for c in EXTRA_SYMBOLS if c not in VOCABS["french"]], ensure_ascii=False) if extra else ""
    if extra:
        log(f"New characters in your labels: {''.join(extra)}. The reader's alphabet is extended (stock alphabet + Greek, "
            f"sub/superscripts, math symbols). Its last layer restarts, so it needs more samples than usual.")
    common = ["--train_path", os.path.join(WORK, "reco_train"), "--val_path", os.path.join(WORK, "reco_val"),
              "--output_dir", os.path.join(WORK, "reco_out"), "--pretrained"]
    before_out, _ = run_ref("reco", ["crnn_vgg16_bn"] + common + ["--test-only", "-b", "64"] + (vocab_args if not extra else []))
    before = _metric(before_out, "reco") if not extra else 0.0
    epochs = 20 if n_tr < 300 else 10 if n_tr < 2000 else 5
    log(f"Reader before training: {before}% of held-out words read exactly. Training {epochs} passes over {n_tr} words...")
    out, secs = run_ref("reco", ["crnn_vgg16_bn"] + common + vocab_args + ["--epochs", str(epochs), "-b", "64", "--name", "reco",
                                                                          "--early-stop", "--early-stop-epochs", "4"], extra_json)
    after = _best_val(out, "reco")
    peak = re.findall(r"PEAK_GPU_GB ([\d.]+)", out)
    log(f"Reader after training: {after}% exact ({secs / 60:.1f} min" + (f", peak graphics memory {peak[-1]} GB" if peak else "") + ")")
    return {"before": before, "after": after, "pt": os.path.join(WORK, "reco_out", "reco.pt"), "vocab_extra": extra_json,
            "minutes": round(secs / 60, 1), "train": n_tr, "held_out": n_va}

def _best_val(out, kind):
    """Score of the saved (best) epoch: docTR saves when validation loss improves."""
    best, last_saved = None, False
    for line in out.splitlines():
        if "saving state" in line:
            last_saved = True
        elif "Validation loss" in line and "Epoch" in line:
            if last_saved or best is None:
                best = _metric(line, kind)
            last_saved = False
    return best

def train_finder():
    n_tr, n_va = build_finder_data()
    if n_tr < 10 or n_va < 1:
        log("Not enough finder samples yet (need 10+ regions to learn from). Box more regions in the Trainer.")
        return None
    import torch
    gpu = torch.cuda.is_available()
    common = ["--train_path", os.path.join(WORK, "det_train"), "--val_path", os.path.join(WORK, "det_val"),
              "--output_dir", os.path.join(WORK, "det_out"), "--pretrained", "-b", "2"] + (["--amp"] if gpu else [])
    before_out, _ = run_ref("det", ["db_mobilenet_v3_large"] + common + ["--test-only"])
    before = _metric(before_out, "det")
    epochs = 20 if n_tr < 100 else 10
    log(f"Finder before training: recall/precision {before}. Training {epochs} passes over {n_tr} regions...")
    out, secs = run_ref("det", ["db_mobilenet_v3_large"] + common + ["--epochs", str(epochs), "--name", "det",
                                                                     "--early-stop", "--early-stop-epochs", "4"])
    after = _best_val(out, "det")
    peak = re.findall(r"PEAK_GPU_GB ([\d.]+)", out)
    log(f"Finder after training: recall/precision {after} ({secs / 60:.1f} min" + (f", peak graphics memory {peak[-1]} GB" if peak else "") + ")")
    return {"before": before, "after": after, "pt": os.path.join(WORK, "det_out", "det.pt"), "minutes": round(secs / 60, 1),
            "train": n_tr, "held_out": n_va}

# ------------------------------------------------------------------ export
def export(reader, finder):
    import torch
    from doctr.models import db_mobilenet_v3_large, crnn_vgg16_bn
    from doctr.models.utils import export_model_to_onnx
    from doctr.datasets import VOCABS
    base = json.load(open(os.path.join(BASE_MODELS, "doctr_models.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    info = {"doctr": base.get("doctr", ""), "torch": torch.__version__, "trained_by": "Acronym Hunter Training Kit",
            "trained": time.strftime("%Y-%m-%d %H:%M"), "models": {}}
    report = ["ACRONYM HUNTER TRAINING KIT REPORT", time.strftime("%Y-%m-%d %H:%M"), ""]
    for key, res, better in (("doctr_reco", reader, reader and reader["after"] is not None and reader["after"] > (reader["before"] or 0)),
                             ("doctr_det", finder, finder and finder["after"] and (not finder["before"] or
                                                                                    sum(finder["after"]) > sum(finder["before"])))):
        entry = dict(base["models"][key])
        if res and better:
            if key == "doctr_reco":
                vocab = VOCABS["french"] + "".join(c for c in json.loads(res["vocab_extra"]) if c not in VOCABS["french"]) \
                    if res["vocab_extra"] else VOCABS["french"]
                m = crnn_vgg16_bn(pretrained=False, pretrained_backbone=False, exportable=True, vocab=vocab); shape = (1, 3, 32, 128)
                entry["vocab"] = vocab
            else:
                m = db_mobilenet_v3_large(pretrained=False, pretrained_backbone=False, exportable=True); shape = (1, 3, 1024, 1024)
            m.load_state_dict(torch.load(res["pt"], map_location="cpu", weights_only=True))
            m.eval()
            path = export_model_to_onnx(m, os.path.join(OUT, key), torch.rand(*shape))
            entry.update({"onnx": os.path.basename(path), "onnx_sha256": sha(path), "weights_url": "trained by the Training Kit",
                          "weights_sha256": sha(res["pt"]), "trained_samples": res["train"], "held_out": res["held_out"]})
            report.append(f"{'Reader' if key == 'doctr_reco' else 'Finder'}: IMPROVED  before {res['before']}  after {res['after']}  "
                          f"({res['train']} samples, {res['held_out']} held out, {res['minutes']} min)")
        else:
            shutil.copy2(os.path.join(BASE_MODELS, entry["onnx"]), os.path.join(OUT, entry["onnx"]))
            why = "not trained" if not res else f"not better (before {res['before']}, after {res['after']}): kept the current model"
            report.append(f"{'Reader' if key == 'doctr_reco' else 'Finder'}: {why}")
        info["models"][key] = entry
    json.dump(info, open(os.path.join(OUT, "doctr_models.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    report += ["", "Install: Acronym Hunter > Tools > Knowledge > Install trained docTR models > pick this folder.",
               "Share: after installing, Knowledge > Share with team includes these models."]
    open(os.path.join(OUT, "REPORT.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
    log("\n".join(report))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true"); ap.add_argument("--reader", action="store_true")
    ap.add_argument("--finder", action="store_true"); ap.add_argument("--packages", action="store_true")
    ap.add_argument("--export-only", action="store_true", help="export the last training results again")
    a = ap.parse_args()
    if a.packages:
        from importlib import metadata
        for d in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
            print(f"  {d.metadata['Name']}=={d.version}")
        return 0
    if a.check or not (a.reader or a.finder or a.export_only):
        return 0 if check() else 1
    os.makedirs(WORK, exist_ok=True)
    saved = os.path.join(WORK, "results.json")
    if a.export_only:
        r = json.load(open(saved, encoding="utf-8"))
        export(r.get("reader"), r.get("finder")); return 0
    reader = train_reader() if a.reader else None
    finder = train_finder() if a.finder else None
    json.dump({"reader": reader, "finder": finder}, open(saved, "w", encoding="utf-8"), ensure_ascii=False)
    if reader is None and finder is None:
        return 1
    export(reader, finder)
    return 0

if __name__ == "__main__":
    sys.exit(main())
