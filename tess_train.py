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

def _plain_runner(cmd, timeout=None):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=_NOWIN)
    return r.returncode, r.stdout, r.stderr

def read_samples(train_dir):
    """[(abs image path, text)] from labels.txt, skipping missing images and empty or 'not text' labels."""
    labels = os.path.join(train_dir, "labels.txt")
    out = []
    try:                                       # lines the training team rejected are not taught (2.15.0)
        rej = set(json.load(open(os.path.join(train_dir, "review.json"), encoding="utf-8")).get("rejected", []))
    except (OSError, ValueError):
        rej = set()
    if os.path.exists(labels):
        for line in open(labels, encoding="utf-8").read().splitlines():
            if "\t" not in line:
                continue
            rel, text = line.split("\t", 1)
            text = text.strip()
            path = os.path.join(train_dir, rel.replace("/", os.sep))
            if text and text != "(not text)" and rel not in rej and os.path.isfile(path):
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

def _bwer(output):
    m = re.findall(r"BWER (?:eval|train)=([\d.]+)", output)
    return float(m[-1]) if m else None

def _misreads(output):
    """{correct text: what the reader produced} for the held-out lines it got wrong (lstmeval prints only those)."""
    out, truth = {}, None
    for line in output.splitlines():
        if line.startswith("Truth:"):
            truth = line[6:].strip()
        elif line.startswith("OCR") and ":" in line and truth is not None:
            out[truth] = line.split(":", 1)[1].strip()
            truth = None
    return out

def _pct(err):
    return None if err is None else max(0.0, 100.0 - err)

def train(tess_dir, train_dir, out_dir, progress=lambda msg, frac=None: None, cancel=None, iterations=None, runner=None,
          current_model=None):
    """Fine-tune and write out_dir\\acronym.traineddata. Returns a report dict. Raises on failure.
    progress(message, fraction 0-1 or None) reports each stage. current_model is the reader in use now (Google's
    model, or the last trained one): the new reader is compared with it on the same held-out lines.
    runner(cmd, timeout) -> (exit code, stdout, stderr) runs each Tesseract tool; the app passes one that uses the
    no-network sandbox. Every file the tools touch is inside tess_dir (read) and out_dir (read/write)."""
    raw = runner or _plain_runner
    def _run(cmd, timeout=600):
        code, out, err = raw(cmd, timeout=timeout)
        return code, (out + err).decode("utf-8", "replace")
    def check():
        if cancel is not None and cancel.is_set():
            raise RuntimeError("Stopped. The reader was not changed.")
    tess = _tool(tess_dir, "tesseract.exe"); lstmtraining = _tool(tess_dir, "lstmtraining.exe")
    combine = _tool(tess_dir, "combine_tessdata.exe"); lstmeval = _tool(tess_dir, "lstmeval.exe")
    tessdata = os.path.join(tess_dir, "tessdata"); base = os.path.join(tessdata, "eng.traineddata")
    current = current_model if current_model and os.path.isfile(current_model) else base
    samples = read_samples(train_dir)
    if len(samples) < MIN_SAMPLES:
        raise RuntimeError(f"{len(samples)} corrected lines saved. Improving the reader needs at least {MIN_SAMPLES} "
                           f"(about {GOOD_SAMPLES}+ for a dependable gain).")
    work = os.path.join(out_dir, "work")
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    lstmf, skipped = [], 0
    for i, (src, text) in enumerate(samples, 1):
        check()
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
        if i % 5 == 0 or i == len(samples):
            progress(f"Step 1 of 4: preparing your corrected lines ({i} of {len(samples)})", 0.25 * i / len(samples))
    if len(lstmf) < MIN_SAMPLES:
        raise RuntimeError(f"Only {len(lstmf)} lines could be prepared ({skipped} could not be used).")
    # Stable split: the same line always lands in the same set (10% held out to check the result)
    train_l, eval_l = [], []
    for path, text in lstmf:
        (eval_l if int(hashlib.sha1(text.encode()).hexdigest(), 16) % 10 == 0 else train_l).append(path)
    if not eval_l:
        eval_l.append(train_l.pop())
    for name, rows in (("list.train", train_l), ("list.eval", eval_l)):
        with open(os.path.join(work, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(r + "\n" for r in rows))
    check()
    progress(f"Step 2 of 4: measuring the current reader on {len(eval_l)} lines it will not learn from", 0.27)
    code, log = _run([combine, "-e", base, os.path.join(work, "eng.lstm")])
    if code != 0:
        raise RuntimeError("Could not unpack the base model:\n" + log[-500:])
    _code, before_log = _run([lstmeval, "--model", current, "--eval_listfile", os.path.join(work, "list.eval")])
    check()
    iters = int(iterations or min(3000, max(400, 4 * len(train_l))))
    est = max(20, int(iters * 0.05 + len(train_l) * 0.02))
    progress(f"Step 3 of 4: teaching the reader ({len(train_l)} lines, about {max(1, round(est / 60))} min on this PC)", 0.30)
    cmd = [lstmtraining, "--model_output", os.path.join(work, "acr"), "--continue_from", os.path.join(work, "eng.lstm"),
           "--traineddata", base, "--train_listfile", os.path.join(work, "list.train"),
           "--eval_listfile", os.path.join(work, "list.eval"), "--max_iterations", str(iters), "--target_error_rate", "0.005"]
    t0 = time.time()
    code, log = _run(cmd, timeout=6 * 3600)
    ckpt = os.path.join(work, "acr_checkpoint")
    if not os.path.isfile(ckpt):
        raise RuntimeError("Training produced no checkpoint:\n" + "\n".join(log.splitlines()[-15:]))
    os.makedirs(out_dir, exist_ok=True)
    model = os.path.join(out_dir, "acronym.traineddata")
    code, log = _run([lstmtraining, "--stop_training", "--continue_from", ckpt, "--traineddata", base, "--model_output", model])
    if code != 0 or not os.path.isfile(model):
        raise RuntimeError("Could not write the trained model:\n" + log[-500:])
    progress("Step 4 of 4: measuring the new reader on the same held-out lines", 0.95)
    _code, after_log = _run([lstmeval, "--model", model, "--eval_listfile", os.path.join(work, "list.eval")])
    before_bad, after_bad = _misreads(before_log), _misreads(after_log)
    fixed = [(t, before_bad[t]) for t in before_bad if t not in after_bad][:6]
    broke = [(t, after_bad[t]) for t in after_bad if t not in before_bad][:6]
    b_c, a_c, b_w, a_w = _bcer(before_log), _bcer(after_log), _bwer(before_log), _bwer(after_log)
    report = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "samples": len(samples), "prepared": len(lstmf),
              "skipped": skipped, "train_lines": len(train_l), "check_lines": len(eval_l), "steps": iters,
              "seconds": int(time.time() - t0), "char_error_before_pct": b_c, "char_error_after_pct": a_c,
              "words_correct_before_pct": _pct(b_w), "words_correct_after_pct": _pct(a_w),
              "chars_correct_before_pct": _pct(b_c), "chars_correct_after_pct": _pct(a_c),
              "compared_with": "your previous trained reader" if current != base else "Google's English reader",
              "fixed_examples": fixed, "new_mistakes": broke, "model": model}
    report["better"] = a_c is not None and (b_c is None or a_c <= b_c)
    with open(os.path.join(out_dir, "training_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    if not os.environ.get("AH_KEEP_TRAIN_WORK"):
        shutil.rmtree(work, ignore_errors=True)   # the prepared line images are copies of document crops
    progress("Done", 1.0)
    return report

def describe(r):
    fmt = lambda v: "n/a" if v is None else f"{v:.0f}%"
    lines = [f"Words read correctly: {fmt(r.get('words_correct_before_pct'))} before, {fmt(r.get('words_correct_after_pct'))} after "
             f"(on {r['check_lines']} of your lines the reader did not learn from; before = {r.get('compared_with', 'current reader')}).",
             f"Characters read correctly: {fmt(r.get('chars_correct_before_pct'))} before, {fmt(r.get('chars_correct_after_pct'))} after."]
    if r.get("skipped"):
        lines.append(f"{r['skipped']} saved lines could not be used.")
    if r["samples"] < GOOD_SAMPLES:
        lines.append(f"Based on {r['samples']} saved lines. About {GOOD_SAMPLES}+ makes the result dependable.")
    return "\n".join(lines)
