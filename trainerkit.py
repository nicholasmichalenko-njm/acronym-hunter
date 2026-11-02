"""The Trainer's rules (3.14.0): the help text, the characters the reading model writes, and the training package for
the training team. The Trainer itself is the Qt Trainer page in Stationkeeper Training; these are the parts the
retired classic Trainer window kept that it still uses. Rules only; nothing leaves the PC."""
import app_gui as eng          # sandbox + temp redirect + network guard + OCR engine + config (must be first)
import os, hashlib
import corrections as C

TRAIN_DIR, IMG_DIR, LABELS_FILE, META_FILE = C.TRAIN_DIR, C.IMG_DIR, C.LABELS_FILE, C.META_FILE
DET_DIR, DET_LABELS_FILE, SAVE_LOG, PACKAGE_DIR = C.DET_DIR, C.DET_LABELS_FILE, C.SAVE_LOG, C.PACKAGE_DIR

CHOICES = ("Skip", "Save as text", "Not text")
OPEN_TYPES = [("Documents and images", "*.pdf *.pptx *.docx *.xlsx *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif *.svg *.svgz *.emf *.wmf *.emz *.wmz")]
PAD = 16                                                # white border added around a region before reading


def _model_characters():
    """Characters the current recognition model can output (from its ONNX metadata)."""
    if eng.OCR_BACKEND == "tesseract":   # Google's English model writes Latin letters, digits, and common symbols
        import string
        return set(string.printable) | set("±°µΩ×÷–—’‘“”•§©®™¼½¾²³")
    import onnxruntime as ort
    import rapidocr_onnxruntime as _ro
    custom = os.path.join(eng.MODELS_DIR, "rec.onnx")
    keys = os.path.join(eng.MODELS_DIR, "rec_keys.txt")
    if os.path.isfile(keys):
        return set(open(keys, encoding="utf-8").read().splitlines()) | {" "}
    path = custom if os.path.isfile(custom) else os.path.join(os.path.dirname(_ro.__file__), "models", "ch_PP-OCRv4_rec_infer.onnx")
    meta = ort.InferenceSession(path, providers=["CPUExecutionProvider"]).get_modelmeta().custom_metadata_map
    return set(meta.get("character", "").splitlines()) | {" "}

def build_training_package():
    """Split the samples into train/val lists that PaddleOCR reads directly from training_data\\.
    No images are copied, so the package adds only a few KB. Returns a report string."""
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    def split(src, prefix):
        lines = [l for l in open(src, encoding="utf-8").read().splitlines() if l.strip()] if os.path.exists(src) else []
        train, val = [], []
        for l in lines:   # stable split: the same sample always lands in the same set
            (val if int(hashlib.sha1(l.split("\t", 1)[0].encode()).hexdigest(), 16) % 10 == 0 else train).append(l)
        if lines and not val:
            val.append(train.pop())
        for name, rows in ((f"{prefix}_train.txt", train), (f"{prefix}_val.txt", val)):
            with open(os.path.join(PACKAGE_DIR, name), "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(r + "\n" for r in rows))
        return lines, len(train), len(val)
    rec, rec_t, rec_v = split(LABELS_FILE, "rec")
    det, det_t, det_v = split(DET_LABELS_FILE, "det")
    missing = set()
    try:
        chars = _model_characters()
        for l in rec:
            missing |= {c for c in l.split("\t", 1)[-1] if c not in chars}
    except Exception:
        eng.log_error("Could not read the recognition model's character list")
    report = [f"Training package written to {PACKAGE_DIR}",
              f"Text-line samples (recognition): {len(rec)}  ->  {rec_t} train / {rec_v} check",
              f"Region samples (detection):      {len(det)}  ->  {det_t} train / {det_v} check"]
    report.append("Recognition: ready to fine-tune." if len(rec) >= 300 else
                  f"Recognition: {len(rec)} of about 300 samples minimum (1,000+ recommended). Keep collecting.")
    report.append("Detection: ready to fine-tune." if len(det) >= 100 else
                  f"Detection: {len(det)} of about 100 region samples minimum (300+ recommended). Keep collecting.")
    if missing:
        report.append("Characters the current model cannot output (fix the label or they will be skipped): "
                      + " ".join(sorted(missing)))
    open(os.path.join(PACKAGE_DIR, "package_report.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
    return "\n".join(report)


HELP_TEXT_TESSERACT = """HOW YOUR SAMPLES MAKE THE SCANNER BETTER (US edition, Tesseract engine)

Right away (no training needed):
  1. "Not text" on a green line -> ignore list -> gone from the next scan.
  2. Correct a misread word, then "Add OCR Fixes from Corrections" -> fixed on the next scan.

Training the reader on this PC (CPU only, no GPU, no internet, no extra download):
  3. Keep saving lines with "Save as text". 20 is the minimum; 300+ gives a dependable gain.
     Save the styles the scanner gets wrong: small labels, unusual fonts, text on shading.
  4. Click "Improve Reading" (here, or on the banner in the scanner). It fine-tunes Google's
     English model on your lines with Tesseract's own training tool, on this PC's processor,
     and checks the result on lines it did not train on. A few hundred lines take minutes.
  5. It installs the new reader only if it scored better, then offers to rescan.
     The scanner uses config\\models\\acronym.traineddata from then on.
  6. Score it on real files. Worse? Scanner > Knowledge > Undo Last Knowledge Change.
  7. Better? Scanner > Knowledge > Export Knowledge Pack > approved SharePoint folder.
     Colleagues click Knowledge > Install Knowledge Pack.

What "Not text" regions do here: Tesseract finds text with fixed rules, so region samples do not
train it. They still feed the ignore list (step 1) and stay saved for any future engine.

Undo Last Save removes everything from the last save, including ignore-list entries it added.
training_data\\ holds crops of your documents: handle it at the documents' classification.
The trained model is learned from those crops: same handling, approved SharePoint only.
"""

HELP_TEXT = """WHAT EACH CHOICE DOES

Save as text
  You confirm the line is real text and its spelling is right (fix it in the box first).
  Saved: a picture of that one line + its correct text (training_data\\images, labels.txt).
  Teaches the READER (recognition model) to spell this style correctly.

Not text
  You confirm the "reading" is not text: a diagram line, arrow, border, speck, or hatching
  that OCR turned into letters or Asian characters.
  Saved: the whole box you drew, with the not-text spot marked as background
  (training_data\\regions, det_labels.txt). Teaches the FINDER (detection model) to stop
  drawing a text box there.
  Works right away too: if the line was GREEN (the scanner keeps it), that exact reading is
  added to config\\ocr_ignore.csv, so the scanner drops it from pictures on the next scan.
  It never affects typed text in documents. Review or edit the list with "Ignore List".

Skip
  Not used for training. In the region sample it is marked "unsure", so it teaches nothing either way.

GREEN vs RED
  Green = confidence at or above the cutoff (config\\ocr_settings.json: min_confidence, or
          tesseract_min_confidence in the US edition).
          The scanner keeps it, so a wrong green reading can become a false result.
  Red   = below the cutoff. The scanner already throws it away. Marking a red line
          "Not text" is still a useful training example; it just does not need the ignore list.

HOW YOUR SAMPLES MAKE THE SCANNER BETTER

Right away (no training needed):
  1. Not text on green lines -> ignore list -> gone from the next scan.
  2. Correct a misread word, then "Add OCR Fixes from Corrections" -> fixed on the next scan.

Over time (training a new model with the offline Training Kit):
  3. Keep saving. Aim for 300+ text lines (1,000+ is better) and 100+ regions.
  4. "Prepare Training Package" shows how many you have and flags any character
     the model cannot output.
  5. Copy this training_data\\ folder into the Training Kit's samples\\<your name>\\.
  6. Double-click Train.cmd in the kit. It trains offline (often overnight) and writes
     output\\models\\ (rec.onnx = reader, det.onnx = finder).
  7. Scanner > Knowledge > Load Trained Models > pick output\\models. Score it.
     Worse? Knowledge > Undo Last Knowledge Change.
  8. Better? Knowledge > Export Knowledge Pack > approved SharePoint folder.
     Colleagues click Knowledge > Install Knowledge Pack.

Undo Last Save removes everything from the last save, including ignore-list entries it added.
training_data\\ holds crops of your documents: handle it at the documents' classification.
"""

# --------------------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------------------
