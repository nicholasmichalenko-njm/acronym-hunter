"""Corrected readings (2.15.0: shared by Stationkeeper and Stationkeeper Training).

Stationkeeper saves what people correct (Report misreading, Not text) in the training_data folder beside the program, then
sends them to the training team as a corrections pack (a zip for the approved SharePoint folder). Stationkeeper
Training imports the packs, lets the training team accept, reject or fix each line, trains a better reader, and
ships it back in a versioned Knowledge Pack.

The training_data folder holds crops of real documents: it is never shipped in a package or committed, and a corrections pack
carries the same handling as the documents it came from.
"""
import app_gui as eng          # engine first (sandbox, network guard, writers)
import os, io, csv, re, json, zipfile, hashlib, datetime, getpass, platform

TRAIN_DIR = IMG_DIR = LABELS_FILE = META_FILE = DET_DIR = DET_LABELS_FILE = SAVE_LOG = PACKAGE_DIR = ""
EXPORTED_FILE = REVIEW_FILE = PACKS_FILE = ""


def set_dir(path):
    """Point every training_data path at `path` (tests use a temporary folder)."""
    global TRAIN_DIR, IMG_DIR, LABELS_FILE, META_FILE, DET_DIR, DET_LABELS_FILE, SAVE_LOG, PACKAGE_DIR
    global EXPORTED_FILE, REVIEW_FILE, PACKS_FILE
    TRAIN_DIR = path
    eng.TRAIN_DIR = path                                    # Improve Reading and the banner read the same folder
    IMG_DIR = os.path.join(path, "images")
    LABELS_FILE = os.path.join(path, "labels.txt")          # recognition format: images/x.png<TAB>text
    META_FILE = os.path.join(path, "samples.csv")           # who/what/where for each sample
    DET_DIR = os.path.join(path, "regions")
    DET_LABELS_FILE = os.path.join(path, "det_labels.txt")  # detection format: regions/x.png<TAB>[boxes]
    SAVE_LOG = os.path.join(path, "save_log.jsonl")         # one line per save, so Undo removes the whole save
    PACKAGE_DIR = os.path.join(path, "package")
    EXPORTED_FILE = os.path.join(path, "sent.json")         # Stationkeeper: samples already sent to the training team
    REVIEW_FILE = os.path.join(path, "review.json")         # Training: rejected samples (not taught)
    PACKS_FILE = os.path.join(path, "packs.json")           # Training: corrections packs imported


set_dir(os.path.join(eng.BASE_DIR, "training_data"))

# --------------------------------------------------------------------------------------
# Training data store (inside the app folder; never shipped in the zip or committed)
# --------------------------------------------------------------------------------------
def _clean_text(t):
    return re.sub(r"[\t\r\n]+", " ", t).strip()

def _png(pil_img):
    buf = io.BytesIO(); pil_img.save(buf, "PNG"); return buf.getvalue()

def _sample_id(data):
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + hashlib.sha1(data).hexdigest()[:8] + "_" + os.urandom(3).hex()

def _meta(rows):
    new = not os.path.exists(META_FILE)
    with open(META_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Date", "Image", "Text", "OCR read", "Confidence", "Source", "Box (x0,y0,x1,y1)"])
        w.writerows(rows)

def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def save_sample(pil_img, text, ocr_text, conf, source, box):
    """One text-line image for recognition training (images/ + labels.txt). Returns the image path."""
    os.makedirs(IMG_DIR, exist_ok=True)
    data = _png(pil_img)
    rel = f"images/{_sample_id(data)}.png"
    with open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "wb") as f:
        f.write(data)
    with open(LABELS_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{rel}\t{_clean_text(text)}\n")
    _meta([[_now(), rel, _clean_text(text), _clean_text(ocr_text), f"{conf:.2f}", source,
            ",".join(str(int(v)) for v in box)]])
    return rel

def save_region(pil_img, text_boxes, unsure_boxes, not_text, source, region):
    """The whole drawn box for detection training (regions/ + det_labels.txt).
    text_boxes: [(box, text)] real text. unsure_boxes: lines left on Skip (marked ### = ignore, not taught either way).
    Everything else in the image, including every 'Not text' line, is taught as background."""
    os.makedirs(DET_DIR, exist_ok=True)
    data = _png(pil_img)
    rel = f"regions/{_sample_id(data)}.png"
    with open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "wb") as f:
        f.write(data)
    pts = lambda b: [[int(b[0]), int(b[1])], [int(b[2]), int(b[1])], [int(b[2]), int(b[3])], [int(b[0]), int(b[3])]]
    label = [{"transcription": _clean_text(t), "points": pts(b)} for b, t in text_boxes]
    label += [{"transcription": "###", "points": pts(b)} for b in unsure_boxes]
    if not label:   # PaddleOCR skips images with no boxes; a 1-pixel ignore box keeps a pure "not text" example
        label = [{"transcription": "###", "points": pts((0, 0, 1, 1))}]
    with open(DET_LABELS_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{rel}\t{json.dumps(label, ensure_ascii=False)}\n")
    rx, ry = region[0], region[1]
    _meta([[_now(), rel, "(not text)", _clean_text(t), f"{c:.2f}", source,
            ",".join(str(int(v)) for v in (rx + b[0], ry + b[1], rx + b[2], ry + b[3]))] for b, t, c in not_text])
    return rel

def _log_save(entry):
    os.makedirs(TRAIN_DIR, exist_ok=True)
    with open(SAVE_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _drop_lines(path, images):
    if not os.path.exists(path):
        return
    keep = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip() and l.split("\t", 1)[0] not in images]
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(l + "\n" for l in keep))
    os.replace(path + ".tmp", path)

def _remove_images(images):
    for rel in images:
        try:
            os.remove(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)))
        except OSError:
            pass
    _drop_lines(LABELS_FILE, images)
    _drop_lines(DET_LABELS_FILE, images)
    if os.path.exists(META_FILE):
        rows = [r for r in csv.reader(open(META_FILE, encoding="utf-8", newline="")) if not (len(r) > 1 and r[1] in images)]
        with open(META_FILE + ".tmp", "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
        os.replace(META_FILE + ".tmp", META_FILE)

def remove_last_save():
    """Undo the most recent save: its line samples, region sample, and ignore-list entries. Returns a description."""
    entries = []
    if os.path.exists(SAVE_LOG):
        entries = [l for l in open(SAVE_LOG, encoding="utf-8").read().splitlines() if l.strip()]
    if entries:
        last = json.loads(entries.pop())
        with open(SAVE_LOG + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(l + "\n" for l in entries))
        os.replace(SAVE_LOG + ".tmp", SAVE_LOG)
        _remove_images(set(last.get("images", [])))
        ignored = set(last.get("ignored", []))
        if ignored:
            eng.write_ocr_ignore_rows([r for r in eng.read_ocr_ignore_rows() if r[0] not in ignored])
        return last.get("summary", "last save")
    # samples saved before v1.3.1 have no log: remove the last line sample
    if not os.path.exists(LABELS_FILE):
        return None
    lines = [l for l in open(LABELS_FILE, encoding="utf-8").read().splitlines() if l.strip()]
    if not lines:
        return None
    img_rel, text = (lines[-1].split("\t", 1) + [""])[:2]
    _remove_images({img_rel})
    return f"sample '{text}'"

def _count(path):
    return sum(1 for l in open(path, encoding="utf-8") if l.strip()) if os.path.exists(path) else 0

def training_stats():
    """(text-line samples, region samples, not-text examples, bytes on disk)"""
    not_text = 0
    if os.path.exists(META_FILE):
        not_text = sum(1 for r in csv.reader(open(META_FILE, encoding="utf-8", newline="")) if len(r) > 2 and r[2] == "(not text)")
    size = 0
    for root, _d, files in os.walk(TRAIN_DIR):
        size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    return _count(LABELS_FILE), _count(DET_LABELS_FILE), not_text, size

def fixes_from_correction(ocr_text, corrected):
    """Word pairs that differ between what OCR read and the corrected text (same word count only)."""
    strip = lambda w: re.sub(r"^[^\w&/]+|[^\w&/.]+$", "", w)
    a, b = ocr_text.split(), corrected.split()
    if len(a) != len(b):
        return []
    return [(strip(x), strip(y)) for x, y in zip(a, b) if strip(x) and strip(y) and strip(x) != strip(y)]


# --------------------------------------------------------------------------------------
# Samples, review, and corrections packs
# --------------------------------------------------------------------------------------
PACK_FORMAT = "AcronymHunterCorrections"
PACK_MAX_FILES = 20000
PACK_MAX_BYTES = 30 * 1024 * 1024          # per picture
PACK_MAX_TOTAL = 2 * 1024 * 1024 * 1024
_SAFE_MEMBER = re.compile(r"^(images|regions)/[A-Za-z0-9_.-]{1,120}\.png$")


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def _label_lines(path):
    if not os.path.exists(path):
        return []
    return [l for l in open(path, encoding="utf-8").read().splitlines() if "\t" in l]


def meta_rows():
    """{image rel: [Date, Image, Text, OCR read, Confidence, Source, Box]} (the last row for each image)."""
    out = {}
    if os.path.exists(META_FILE):
        for r in csv.reader(open(META_FILE, encoding="utf-8", newline="")):
            if len(r) > 1 and r[1] and r[0] != "Date":
                out[r[1]] = (r + [""] * 7)[:7]
    return out


def rejected():
    return set(_read_json(REVIEW_FILE, {}).get("rejected", []))


def samples():
    """Every text-line sample: [{"rel", "text", "read", "conf", "source", "date", "rejected"}], oldest first."""
    meta, rej = meta_rows(), rejected()
    out = []
    for l in _label_lines(LABELS_FILE):
        rel, text = l.split("\t", 1)
        m = meta.get(rel, [""] * 7)
        out.append({"rel": rel, "text": text.strip(), "read": m[3], "conf": m[4], "source": m[5], "date": m[0],
                    "rejected": rel in rej})
    return out


def set_rejected(rels, on=True):
    rej = rejected()
    rej = (rej | set(rels)) if on else (rej - set(rels))
    _write_json(REVIEW_FILE, {"rejected": sorted(rej)})
    return len(rej)


def set_text(rel, text):
    """Fix the text of one sample (labels.txt and samples.csv)."""
    text = _clean_text(text)
    if not text or not os.path.exists(LABELS_FILE):
        return False
    lines = open(LABELS_FILE, encoding="utf-8").read().splitlines()
    hit = False
    for i, l in enumerate(lines):
        if l.split("\t", 1)[0] == rel:
            lines[i] = f"{rel}\t{text}"; hit = True
    if not hit:
        return False
    with open(LABELS_FILE + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(l + "\n" for l in lines if l.strip()))
    os.replace(LABELS_FILE + ".tmp", LABELS_FILE)
    if os.path.exists(META_FILE):
        rows = list(csv.reader(open(META_FILE, encoding="utf-8", newline="")))
        for r in rows:
            if len(r) > 2 and r[1] == rel:
                r[2] = text
        with open(META_FILE + ".tmp", "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
        os.replace(META_FILE + ".tmp", META_FILE)
    return True


def unsent():
    """(line rels, region rels) saved here and not yet sent to the training team."""
    sent = set(_read_json(EXPORTED_FILE, {}).get("sent", []))
    lines = [l.split("\t", 1)[0] for l in _label_lines(LABELS_FILE)]
    regions = [l.split("\t", 1)[0] for l in _label_lines(DET_LABELS_FILE)]
    return [r for r in lines if r not in sent], [r for r in regions if r not in sent]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def export_pack(out_path, everything=False, anonymous=False):
    """Write a corrections pack for the training team. Returns {"lines", "regions", "path"} (0 and 0: nothing written).
    anonymous (2.55.0, inside a training data pack): no user or PC name, and each picture's source is a code."""
    lines, regions = unsent()
    if everything:
        lines = [l.split("\t", 1)[0] for l in _label_lines(LABELS_FILE)]
        regions = [l.split("\t", 1)[0] for l in _label_lines(DET_LABELS_FILE)]
    lines = [r for r in lines if os.path.isfile(os.path.join(TRAIN_DIR, r.replace("/", os.sep)))]
    regions = [r for r in regions if os.path.isfile(os.path.join(TRAIN_DIR, r.replace("/", os.sep)))]
    if not lines and not regions:
        return {"lines": 0, "regions": 0, "path": ""}
    want = set(lines) | set(regions)
    lab = [l for l in _label_lines(LABELS_FILE) if l.split("\t", 1)[0] in want]
    det = [l for l in _label_lines(DET_LABELS_FILE) if l.split("\t", 1)[0] in want]
    meta = [m for rel, m in meta_rows().items() if rel in want]
    if anonymous:
        meta = [list(m[:5]) + [hashlib.sha256(str(m[5] if len(m) > 5 else "").lower().encode("utf-8")).hexdigest()[:10]]
                + list(m[6:]) for m in meta]
    files = {}
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(want):
            data = open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "rb").read()
            z.writestr(rel, data); files[rel] = _sha(data)
        for name, rows in (("labels.txt", lab), ("det_labels.txt", det)):
            data = "".join(r + "\n" for r in rows).encode("utf-8")
            z.writestr(name, data); files[name] = _sha(data)
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["Date", "Image", "Text", "OCR read", "Confidence", "Source", "Box (x0,y0,x1,y1)"]); w.writerows(meta)
        data = buf.getvalue().encode("utf-8"); z.writestr("samples.csv", data); files["samples.csv"] = _sha(data)
        manifest = {"format": PACK_FORMAT, "version": 1, "app_version": eng.APP_VERSION,
                    "created": datetime.datetime.now().isoformat(timespec="seconds"),
                    "from": (hashlib.sha256(f"{getpass.getuser()}@{platform.node()}".lower().encode("utf-8")).hexdigest()[:10]
                             if anonymous else f"{getpass.getuser()} on {platform.node()}"), "lines": len(lines), "regions": len(regions),
                    "files": files}
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
    os.replace(tmp, out_path)
    sent = set(_read_json(EXPORTED_FILE, {}).get("sent", [])) | want
    _write_json(EXPORTED_FILE, {"sent": sorted(sent), "last": manifest["created"]})
    return {"lines": len(lines), "regions": len(regions), "path": out_path}


class PackError(Exception):
    pass


def read_pack(path):
    """Check a corrections pack before anything is copied. Returns (manifest, {member: bytes})."""
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        raise PackError("not a corrections pack (not a zip file)")
    with z:
        names = z.namelist()
        if "manifest.json" not in names:
            raise PackError("not a corrections pack (no manifest)")
        if len(names) > PACK_MAX_FILES:
            raise PackError("too many files")
        try:
            man = json.loads(z.read("manifest.json").decode("utf-8"))
        except ValueError:
            raise PackError("the manifest is not readable")
        if man.get("format") != PACK_FORMAT:
            raise PackError("not a corrections pack (wrong format)")
        files = man.get("files") or {}
        allowed = {"labels.txt", "det_labels.txt", "samples.csv", "manifest.json"}
        total = 0
        out = {}
        for info in z.infolist():
            n = info.filename
            if n == "manifest.json":
                continue
            if n not in allowed and not _SAFE_MEMBER.match(n):
                raise PackError(f"unexpected file in the pack: {n[:80]}")
            if info.file_size > PACK_MAX_BYTES:
                raise PackError(f"file too large: {n[:80]}")
            total += info.file_size
            if total > PACK_MAX_TOTAL:
                raise PackError("pack too large")
            data = z.read(n)
            if files.get(n) != _sha(data):
                raise PackError(f"checksum does not match: {n[:80]} (the pack was changed after it was made)")
            if n.endswith(".png") and not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise PackError(f"not a PNG picture: {n[:80]}")
            out[n] = data
        if set(files) - set(out):
            raise PackError("files listed in the manifest are missing")
    return man, out


def import_pack(path):
    """Add a checked corrections pack to this training set. Samples already here are skipped.
    Returns {"lines", "regions", "skipped", "from", "created"}."""
    man, data = read_pack(path)
    os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(DET_DIR, exist_ok=True)
    have = {l.split("\t", 1)[0] for l in _label_lines(LABELS_FILE) + _label_lines(DET_LABELS_FILE)}
    who = f"{man.get('from', '?')}, {str(man.get('created', ''))[:10]}"
    got = {"lines": 0, "regions": 0, "skipped": 0}
    meta = {}
    for r in csv.reader(io.StringIO(data.get("samples.csv", b"").decode("utf-8"))):
        if len(r) > 1 and r[0] != "Date":
            meta[r[1]] = (r + [""] * 7)[:7]
    for name, dest, key in (("labels.txt", LABELS_FILE, "lines"), ("det_labels.txt", DET_LABELS_FILE, "regions")):
        new = []
        for l in data.get(name, b"").decode("utf-8").splitlines():
            if "\t" not in l:
                continue
            rel = l.split("\t", 1)[0]
            if rel not in data or not _SAFE_MEMBER.match(rel):
                continue
            if rel in have:
                got["skipped"] += 1; continue
            with open(os.path.join(TRAIN_DIR, rel.replace("/", os.sep)), "wb") as f:
                f.write(data[rel])
            new.append(l); have.add(rel); got[key] += 1
            m = meta.get(rel)
            if m:
                m[5] = f"Pack from {who}: {m[5]}"
                _meta([m])
        if new:
            with open(dest, "a", encoding="utf-8", newline="\n") as f:
                f.write("".join(l + "\n" for l in new))
    packs = _read_json(PACKS_FILE, [])
    packs.append({"file": os.path.basename(path), "from": man.get("from", ""), "created": man.get("created", ""),
                  "imported": datetime.datetime.now().isoformat(timespec="seconds"), **got})
    _write_json(PACKS_FILE, packs)
    got.update({"from": man.get("from", ""), "created": man.get("created", "")})
    return got


def packs():
    return _read_json(PACKS_FILE, [])
