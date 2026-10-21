"""Acronym Hunter Training Kit driver. Runs fully offline (see kit\\sitecustomize.py).

  Train.cmd                      menu: check, train reader, train finder, train both
  python\\python.exe kit\\train.py --check
  python\\python.exe kit\\train.py --rec --det [--epochs 40] [--allow-small]

Steps: merge every samples\\<name>\\ folder (a copy of a Trainer's training_data\\) -> remove duplicates ->
split train/check -> fine-tune from the PP-OCRv4 weights in pretrain\\ -> export -> convert to ONNX ->
output\\models\\ (rec.onnx + rec_keys.txt, det.onnx, model_info.json). Load that folder in the scanner with
Knowledge > Load Trained Models, score it, then Export Knowledge Pack to the approved SharePoint folder.
"""
import os, sys, json, re, shutil, hashlib, socket, subprocess, datetime, argparse

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
POCR = os.path.join(KIT, "PaddleOCR")
SAMPLES = os.path.join(KIT, "samples")
WORK = os.path.join(KIT, "work")
DATA = os.path.join(WORK, "data")
OUT = os.path.join(KIT, "output", "models")
LOGS = os.path.join(KIT, "kit", "logs")
DICT = os.path.join(POCR, "ppocr", "utils", "ppocr_keys_v1.txt")
REC_CFG = os.path.join(POCR, "configs", "rec", "PP-OCRv4", "ch_PP-OCRv4_rec.yml")
DET_CFG = os.path.join(POCR, "configs", "det", "ch_PP-OCRv4", "ch_PP-OCRv4_det_student.yml")
REC_WEIGHTS = os.path.join(KIT, "pretrain", "ch_PP-OCRv4_rec_train", "student")
DET_WEIGHTS = os.path.join(KIT, "pretrain", "ch_PP-OCRv4_det_train", "best_accuracy")
MIN_REC, MIN_DET = 300, 100
LOG_FILE = None
START = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg=""):
    print(msg, flush=True)
    if LOG_FILE:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

def posix(p):
    return p.replace("\\", "/")

# ---------------------------------------------------------------------------------------------------------
def check():
    ok = True
    lock = bool(getattr(sys.modules.get("sitecustomize"), "KIT_NETWORK_LOCKDOWN", False))
    log(f"Network lockdown loaded: {lock}"); ok &= lock
    tests = [("raw connect to 1.1.1.1:443", lambda: socket.socket().connect(("1.1.1.1", 443))),
             ("DNS lookup pypi.org", lambda: socket.getaddrinfo("pypi.org", 443)),
             ("HTTPS download", lambda: __import__("urllib.request").request.urlopen("https://pypi.org", timeout=5)),
             ("UDP to 8.8.8.8:53", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("8.8.8.8", 53)))]
    os.environ["KIT_SELFTEST"] = "1"      # these four refusals are logged as SELF-TEST, not as real attempts
    for name, fn in tests:
        try:
            fn(); log(f"  FAIL: {name} succeeded"); ok = False
        except OSError as e:
            log(f"  refused: {name}")
        except Exception as e:
            log(f"  refused: {name} ({type(e).__name__})")
    os.environ.pop("KIT_SELFTEST", None)
    import paddle
    log(f"PaddlePaddle {paddle.__version__} (CPU)")
    for label, path in (("PaddleOCR 2.8 source", os.path.join(POCR, "tools", "train.py")),
                        ("reader starting weights", REC_WEIGHTS + ".pdparams"),
                        ("finder starting weights", DET_WEIGHTS + ".pdparams"),
                        ("character list", DICT)):
        exists = os.path.exists(path); ok &= exists
        log(f"{label}: {'OK' if exists else 'MISSING'}")
    log("KIT CHECK " + ("PASSED" if ok else "FAILED"))
    return ok

# ---------------------------------------------------------------------------------------------------------
def merge_samples():
    """Pool every samples\\*\\ folder. Images are renamed by content hash, so the same crop saved by two
    people (or twice) counts once."""
    shutil.rmtree(DATA, ignore_errors=True)
    os.makedirs(os.path.join(DATA, "images")); os.makedirs(os.path.join(DATA, "regions"))
    chars = set(open(DICT, encoding="utf-8").read().splitlines()) | {" "}
    rec, det, skipped, sources = {}, {}, [], []
    folders = [os.path.join(SAMPLES, d) for d in sorted(os.listdir(SAMPLES)) if os.path.isdir(os.path.join(SAMPLES, d))] \
        if os.path.isdir(SAMPLES) else []
    for folder in folders:
        n_rec = n_det = 0
        for label_file, kind in (("labels.txt", "images"), ("det_labels.txt", "regions")):
            path = os.path.join(folder, label_file)
            if not os.path.isfile(path):
                continue
            for line in open(path, encoding="utf-8").read().splitlines():
                if "\t" not in line:
                    continue
                rel, label = line.split("\t", 1)
                src = os.path.join(folder, rel.replace("/", os.sep))
                if not os.path.isfile(src):
                    continue
                blob = open(src, "rb").read()
                key = hashlib.sha1(blob).hexdigest()[:16]
                dest_rel = f"{kind}/{key}.png"
                if kind == "images":
                    bad = sorted({c for c in label if c not in chars})
                    if bad:
                        skipped.append(f"{os.path.basename(folder)}/{rel}: characters not in the model: {' '.join(bad)}"); continue
                    if dest_rel in rec:
                        continue
                    rec[dest_rel] = label; n_rec += 1
                else:
                    if dest_rel in det:
                        continue
                    det[dest_rel] = label; n_det += 1
                with open(os.path.join(DATA, dest_rel.replace("/", os.sep)), "wb") as f:
                    f.write(blob)
        sources.append((os.path.basename(folder), n_rec, n_det))
    def split(items, prefix):
        train, val = [], []
        for rel, label in sorted(items.items()):
            (val if int(hashlib.sha1(rel.encode()).hexdigest(), 16) % 10 == 0 else train).append(f"{rel}\t{label}")
        while items and len(val) < min(2, len(items) // 2):   # PaddleOCR on Windows needs 2+ check batches
            val.append(train.pop())
        if train == [] and val:
            train = list(val)
        for name, rows in ((f"{prefix}_train.txt", train), (f"{prefix}_val.txt", val)):
            open(os.path.join(DATA, name), "w", encoding="utf-8", newline="\n").write("".join(r + "\n" for r in rows))
        return len(train), len(val)
    rt, rv = split(rec, "rec"); dt, dv = split(det, "det")
    log("SAMPLES")
    for name, a, b in sources:
        log(f"  {name}: {a} new text lines, {b} new regions")
    log(f"  total after removing duplicates: {len(rec)} text lines ({rt} train / {rv} check), {len(det)} regions ({dt} train / {dv} check)")
    for s in skipped[:20]:
        log(f"  skipped {s}")
    return len(rec), len(det), rt

# ---------------------------------------------------------------------------------------------------------
def _two_batches(n, cap):
    """Batch size that gives at least 2 batches: PaddleOCR on Windows skips the last batch of every pass."""
    return max(1, min(cap, n // 2))

def write_config(base_cfg, kind, epochs, n_train):
    import yaml
    cfg = yaml.safe_load(open(base_cfg, encoding="utf-8"))
    g = cfg["Global"]
    out_dir = os.path.join(WORK, "out", kind)
    g.update({"use_gpu": False, "distributed": False, "epoch_num": epochs, "save_model_dir": posix(out_dir),
              "save_epoch_step": 1000000, "print_batch_step": 5, "use_visualdl": False, "checkpoints": None,
              "save_res_path": posix(os.path.join(out_dir, "predicts.txt")), "infer_img": None})
    cfg["Optimizer"]["lr"]["learning_rate"] = 0.0001          # fine-tuning: small steps from the starting weights
    cfg["Optimizer"]["lr"]["warmup_epoch"] = 0
    tr, ev = cfg["Train"], cfg["Eval"]
    n_val = sum(1 for _ in open(os.path.join(DATA, f"{kind}_val.txt"), encoding="utf-8"))
    for section, split in ((tr, "train"), (ev, "val")):
        section["dataset"]["data_dir"] = posix(DATA)
        section["dataset"]["label_file_list"] = [posix(os.path.join(DATA, f"{kind}_{split}.txt"))]
        section["loader"]["num_workers"] = 0                  # Windows: keep loading in the main process
    if kind == "rec":
        g["pretrained_model"] = posix(REC_WEIGHTS)
        g["character_dict_path"] = posix(DICT)
        bs = _two_batches(n_train, 32)
        tr["sampler"]["first_bs"] = bs
        tr["loader"]["batch_size_per_card"] = bs
        tr["loader"]["drop_last"] = False
        ev["loader"]["batch_size_per_card"] = _two_batches(n_val, 32)
        steps = max(1, n_train // bs - 1)
    else:
        g["pretrained_model"] = posix(DET_WEIGHTS)
        bs = _two_batches(n_train, 4)
        tr["loader"]["batch_size_per_card"] = bs
        ev["loader"]["batch_size_per_card"] = 1
        tr["dataset"].pop("ratio_list", None)
        # Leave MakeBorderMap/MakeShrinkMap total_epoch at the stock 500: PaddleOCR passes a seed (1024) as "epoch" into
        # shrink_ratio = 0.4 + 0.2 * epoch / total_epoch, and a small total_epoch pushes the ratio past 1 (every sample fails).
        steps = max(1, -(-n_train // bs) - 1)
    g["eval_batch_step"] = [0, steps]                         # check accuracy once per epoch
    os.makedirs(os.path.join(WORK, "configs"), exist_ok=True)
    path = os.path.join(WORK, "configs", f"{kind}.yml")
    yaml.safe_dump(cfg, open(path, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
    return path, out_dir

def run(args, label):
    log(f"> {label}")
    threads = str(os.cpu_count() or 4)
    env = dict(os.environ, OMP_NUM_THREADS=threads, MKL_NUM_THREADS=threads, OPENBLAS_NUM_THREADS=threads,
               CPU_NUM="1", FLAGS_use_mkldnn="1", PYTHONIOENCODING="utf-8")
    p = subprocess.Popen([PY] + args, cwd=POCR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", env=env)
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-60:]
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if re.search(r"best metric|epoch: \[\d+/\d+\].*loss|save model|Error|error:|Traceback", line):
            print("   " + line[-220:], flush=True)
    if p.wait() != 0:
        raise RuntimeError(f"{label} failed. Last lines:\n" + "\n".join(tail[-25:]))

def best_metric(kind):
    m = None
    for line in open(LOG_FILE, encoding="utf-8", errors="replace"):
        hit = re.search(r"best metric, (acc|hmean): ([\d.]+)", line)
        if hit:
            m = (hit.group(1), float(hit.group(2)))
    return m

def train_and_convert(kind, epochs, n_train):
    cfg, out_dir = write_config(REC_CFG if kind == "rec" else DET_CFG, kind, epochs, n_train)
    shutil.rmtree(out_dir, ignore_errors=True)
    run(["tools/train.py", "-c", cfg], f"Training the {'reader (recognition)' if kind == 'rec' else 'finder (detection)'}, {epochs} epochs")
    weights = os.path.join(out_dir, "best_accuracy")
    if not os.path.isfile(weights + ".pdparams"):
        weights = os.path.join(out_dir, "latest")
    export_dir = os.path.join(WORK, "export", kind)
    shutil.rmtree(export_dir, ignore_errors=True)
    run(["tools/export_model.py", "-c", cfg, "-o", f"Global.pretrained_model={posix(weights)}",
         f"Global.save_inference_dir={posix(export_dir)}"], "Exporting")
    os.makedirs(OUT, exist_ok=True)
    onnx_path = os.path.join(OUT, f"{kind}.onnx")
    run(["-c", "import sys; from paddle2onnx.command import main; sys.argv=['paddle2onnx'] + sys.argv[1:]; main()",
         "--model_dir", export_dir, "--model_filename", "inference.pdmodel", "--params_filename", "inference.pdiparams",
         "--save_file", onnx_path, "--opset_version", "14", "--enable_onnx_checker", "True"], "Converting to ONNX")
    import onnx, onnxruntime as ort, numpy as np
    if kind == "rec":
        keys = open(DICT, encoding="utf-8").read().splitlines()
        model = onnx.load(onnx_path)
        meta = model.metadata_props.add(); meta.key, meta.value = "character", "\n".join(keys)
        onnx.save(model, onnx_path)
        shutil.copy2(DICT, os.path.join(OUT, "rec_keys.txt"))
        shape = (1, 3, 48, 320)
    else:
        shape = (1, 3, 640, 640)
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    sess.run(None, {sess.get_inputs()[0].name: np.zeros(shape, dtype=np.float32)})
    log(f"  {os.path.basename(onnx_path)}: {os.path.getsize(onnx_path) / 1e6:.1f} MB, loads and runs in ONNX Runtime")
    return best_metric(kind)

# ---------------------------------------------------------------------------------------------------------
def main():
    global LOG_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rec", action="store_true", help="train the reader (text-line samples)")
    ap.add_argument("--det", action="store_true", help="train the finder (region samples, incl. Not text)")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--allow-small", action="store_true", help="train below the minimum sample counts (dry runs only)")
    a = ap.parse_args()
    os.makedirs(LOGS, exist_ok=True)
    LOG_FILE = os.path.join(LOGS, f"train_{datetime.datetime.now():%Y%m%d_%H%M%S}.log")
    if a.check or not (a.rec or a.det):
        sys.exit(0 if check() else 1)
    if not check():
        sys.exit("Kit check failed; nothing trained.")
    n_rec, n_det, _ = merge_samples()
    info = {"created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "epochs": a.epochs,
            "samples": {"text_lines": n_rec, "regions": n_det}, "base": "PP-OCRv4 ch (PaddleOCR 2.8)", "models": {}}
    shutil.rmtree(OUT, ignore_errors=True)
    for kind, n, minimum in (("rec", n_rec, MIN_REC), ("det", n_det, MIN_DET)):
        if not getattr(a, kind):
            continue
        if n < 2 or (n < minimum and not a.allow_small):
            log(f"Skipping {kind}: {n} samples, need {minimum}+ (use --allow-small only for a dry run).")
            continue
        n_train = sum(1 for _ in open(os.path.join(DATA, f"{kind}_train.txt"), encoding="utf-8"))
        rate = 0.7 if kind == "rec" else 0.3     # samples per second, measured on a laptop CPU (Ryzen AI 9, 2026-10-20)
        hours = n_train * a.epochs / rate / 3600
        log(f"Estimated time for the {'reader' if kind == 'rec' else 'finder'}: about {hours:.1f} hours on a laptop CPU "
            f"({n_train} samples x {a.epochs} passes). Leave the PC plugged in and awake.")
        metric = train_and_convert(kind, a.epochs, n_train)
        info["models"][f"{kind}.onnx"] = {"best": metric}
    if not info["models"]:
        sys.exit("Nothing was trained.")
    json.dump(info, open(os.path.join(OUT, "model_info.json"), "w", encoding="utf-8"), indent=1)
    log("")
    log(f"DONE. Models in {OUT}")
    log("Next: scanner > Knowledge > Load Trained Models > pick output\\models. Score with tools\\evaluate.py.")
    log("Keep them only if the score improves; Knowledge > Undo puts the old models back.")
    log(f"Full log: {LOG_FILE}")
    blocked = os.path.join(LOGS, "network_blocked.log")
    real = [l for l in open(blocked, encoding="utf-8") if "] REFUSED " in l and l[1:20] >= START] if os.path.exists(blocked) else []
    log(f"Network attempts refused during this run (excluding the self-test): {len(real)}" + (f"  -> see {blocked}" if real else ""))

if __name__ == "__main__":
    if "--packages" in sys.argv:          # exact versions, for KIT_MANIFEST.txt
        import importlib.metadata as md
        print("\n".join(sorted(f"  {d.metadata['Name']}=={d.version}" for d in md.distributions())))
        sys.exit(0)
    main()
