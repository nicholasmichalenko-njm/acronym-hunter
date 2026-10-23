"""CPU-only fine-tuning of Tesseract's reader on the Trainer's saved text-line samples (US edition).

Everything runs on this PC with the engine's own tools (tesseract.exe, lstmtraining.exe, combine_tessdata.exe,
lstmeval.exe from the app's _internal\\tesseract folder). No GPU, no Python ML libraries, no network.

  samples   training_data\\labels.txt (images/x.png <TAB> correct text), written by "Save as text"
  base      Google's eng.traineddata (tessdata_best, float, the only kind Tesseract can fine-tune)
  output    training_data\\model\\acronym.traineddata, loaded with Scanner > Knowledge > Load Trained Models
"""
import os, re, csv, json, time, shutil, hashlib, datetime, subprocess
import numpy as np
import cv2

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MIN_SAMPLES = 20          # below this, training is refused (it would only memorize a handful of lines)
GOOD_SAMPLES = 300        # below this, the report says to keep collecting

def _tool(tess_dir, name):
    path = os.path.join(tess_dir, name)
    if not os.path.isfile(path):
        raise RuntimeError(f"{name} is missing from {tess_dir}. Use the AcronymHunter_US_WithTrainer package.")
    return path

def _run(cmd, cwd=None, timeout=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, creationflags=_NOWIN)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

def read_samples(train_dir):
    """[(abs image path, text)] from labels.txt, skipping missing images and empty or 'not text' labels."""
    labels = os.path.join(train_dir, "labels.txt")
    out = []
    if os.path.exists(labels):
        for line in open(labels, encoding="utf-8").read().splitlines():
            if "\t" not in line:
                continue
            rel, text = line.split("\t", 1)
            text = text.strip()
            path = os.path.join(train_dir, rel.replace("/", os.sep))
            if text and text != "(not text)" and os.path.isfile(path):
                out.append((path, text))
    return out

def _prepare_line(src, dst, min_h=40):
    """Grayscale, white border, small lines enlarged so Tesseract sees strokes at a normal size."""
    img = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    if img.shape[0] < min_h:
        f = min_h / img.shape[0]
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    img = cv2.copyMakeBorder(img, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
    cv2.imwrite(dst, img)
    return img.shape[1], img.shape[0]

def _box_text(text, w, h):
    """Line-level box file (Tesseract 'WordStr' format): the whole image is one line of known text."""
    return f"WordStr 0 0 {w} {h} 0 #{text}\n\t {w} 0 {w + 1} {h} 0\n"

def _bcer(output):
    m = re.findall(r"BCER (?:eval|train)=([\d.]+)", output)
    return float(m[-1]) if m else None

def train(tess_dir, train_dir, out_dir, progress=lambda msg: None, cancel=None, iterations=None):
    """Fine-tune and write out_dir\\acronym.traineddata. Returns a report dict. Raises on failure."""
    tess = _tool(tess_dir, "tesseract.exe"); lstmtraining = _tool(tess_dir, "lstmtraining.exe")
    combine = _tool(tess_dir, "combine_tessdata.exe"); lstmeval = _tool(tess_dir, "lstmeval.exe")
    tessdata = os.path.join(tess_dir, "tessdata"); base = os.path.join(tessdata, "eng.traineddata")
    samples = read_samples(train_dir)
    if len(samples) < MIN_SAMPLES:
        raise RuntimeError(f"{len(samples)} text-line samples saved. Training needs at least {MIN_SAMPLES} "
                           f"(about {GOOD_SAMPLES}+ for a real improvement). Keep saving lines with 'Save as text'.")
    work = os.path.join(out_dir, "work")
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    progress(f"Preparing {len(samples)} samples...")
    lstmf, skipped = [], 0
    for i, (src, text) in enumerate(samples, 1):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("Training cancelled.")
        stem = os.path.join(work, f"s{i:05d}")
        size = _prepare_line(src, stem + ".png")
        if size is None:
            skipped += 1; continue
        with open(stem + ".box", "w", encoding="utf-8", newline="\n") as f:
            f.write(_box_text(text, *size))
        code, log = _run([tess, stem + ".png", stem, "--psm", "13", "--tessdata-dir", tessdata, "-l", "eng", "lstm.train"])
        if code == 0 and os.path.isfile(stem + ".lstmf"):
            lstmf.append((stem + ".lstmf", text))
        else:
            skipped += 1
        if i % 25 == 0:
            progress(f"Preparing samples: {i} of {len(samples)}")
    if len(lstmf) < MIN_SAMPLES:
        raise RuntimeError(f"Only {len(lstmf)} samples could be prepared ({skipped} failed).")
    # Stable split: the same sample always lands in the same set (10% held out to check the result)
    train_l, eval_l = [], []
    for path, text in lstmf:
        (eval_l if int(hashlib.sha1(text.encode()).hexdigest(), 16) % 10 == 0 else train_l).append(path)
    if not eval_l:
        eval_l.append(train_l.pop())
    for name, rows in (("list.train", train_l), ("list.eval", eval_l)):
        with open(os.path.join(work, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(r + "\n" for r in rows))
    code, log = _run([combine, "-e", base, os.path.join(work, "eng.lstm")])
    if code != 0:
        raise RuntimeError("Could not unpack the base model:\n" + log[-500:])
    _code, before_log = _run([lstmeval, "--model", base, "--eval_listfile", os.path.join(work, "list.eval")])
    before = _bcer(before_log)
    iters = int(iterations or min(3000, max(400, 4 * len(train_l))))
    progress(f"Training the reader: {iters} steps on {len(train_l)} lines (CPU)...")
    cmd = [lstmtraining, "--model_output", os.path.join(work, "acr"), "--continue_from", os.path.join(work, "eng.lstm"),
           "--traineddata", base, "--train_listfile", os.path.join(work, "list.train"),
           "--eval_listfile", os.path.join(work, "list.eval"), "--max_iterations", str(iters), "--target_error_rate", "0.005"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=_NOWIN)
    tail, t0 = [], time.time()
    for raw in p.stdout:
        line = raw.decode("utf-8", "replace").rstrip()
        tail = (tail + [line])[-40:]
        m = re.match(r"At iteration (\d+)/(\d+)/(\d+).*?BCER train=([\d.]+)%", line)
        if m:
            progress(f"Training: step {m.group(2)} of {iters}, character error on training lines {m.group(4)}%  "
                     f"({int(time.time() - t0)} s)")
        if cancel is not None and cancel.is_set():
            p.kill(); raise RuntimeError("Training cancelled.")
    p.wait()
    ckpt = os.path.join(work, "acr_checkpoint")
    if not os.path.isfile(ckpt):
        raise RuntimeError("Training produced no checkpoint:\n" + "\n".join(tail[-15:]))
    os.makedirs(out_dir, exist_ok=True)
    model = os.path.join(out_dir, "acronym.traineddata")
    code, log = _run([lstmtraining, "--stop_training", "--continue_from", ckpt, "--traineddata", base, "--model_output", model])
    if code != 0 or not os.path.isfile(model):
        raise RuntimeError("Could not write the trained model:\n" + log[-500:])
    _code, after_log = _run([lstmeval, "--model", model, "--eval_listfile", os.path.join(work, "list.eval")])
    after = _bcer(after_log)
    report = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "samples": len(samples), "prepared": len(lstmf),
              "skipped": skipped, "train_lines": len(train_l), "check_lines": len(eval_l), "steps": iters,
              "seconds": int(time.time() - t0), "char_error_before_pct": before, "char_error_after_pct": after,
              "model": model}
    with open(os.path.join(out_dir, "training_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    if not os.environ.get("AH_KEEP_TRAIN_WORK"):
        shutil.rmtree(work, ignore_errors=True)   # the prepared line images are copies of document crops
    return report

def describe(r):
    fmt = lambda v: "n/a" if v is None else f"{v:.2f}%"
    lines = [f"Trained on {r['train_lines']} lines, checked on {r['check_lines']} held-out lines "
             f"({r['steps']} steps, {r['seconds']} s, CPU).",
             f"Character error on the held-out lines: before {fmt(r['char_error_before_pct'])}, after {fmt(r['char_error_after_pct'])}."]
    if r["skipped"]:
        lines.append(f"{r['skipped']} samples could not be used (unreadable image or characters the model cannot write).")
    b, a = r["char_error_before_pct"], r["char_error_after_pct"]
    if a is not None and b is not None and a > b:
        lines.append("The new model is WORSE on the held-out lines. Do not install it; collect more varied samples.")
    if r["samples"] < GOOD_SAMPLES:
        lines.append(f"{r['samples']} samples saved; about {GOOD_SAMPLES}+ gives a dependable improvement.")
    return "\n".join(lines)
