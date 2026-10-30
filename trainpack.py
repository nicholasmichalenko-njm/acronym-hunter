"""One training data pack for the training team (2.55.0): File > Send training data to the training team... writes a
.sktrain file; Stationkeeper Training imports it (Gather > Import training data...) and files each area where it belongs.

Areas (each a box; all ticked by default):
- reading     misread lines and not-text regions: small pictures cut from documents, with the right text (the
              corrections pack, inside as reading.zip, so older tools read it the same way)
- ocrfix      OCR fixes (misread -> correct) and ignored readings
- compliance  compliance decisions, support links, RFP section headers and levels, Format and Customer's marks, the
              RFP outline and the response structure with placements; plus the learning made from them (numbered
              word buckets and counts only, the same form as a Knowledge Pack)
- words       compliance words added and removed, acronym choices, keyword choices (hashed), banned words

Left out always: Customer information, team names, file paths, user and PC names (the pack says only a short code for
the PC). Customer file names are replaced by a code. Sentence text (the RFP sentences, section titles, proposal section
titles) is in only when the box is ticked. New since the last send by default; everything is an option.
Rules only; nothing leaves the PC except the file the user saves.
"""
import csv, datetime, getpass, hashlib, io, json, os, platform, tempfile, zipfile

EXT = ".sktrain"
FORMAT = "StationkeeperTrainingData"
AREAS = (("reading", "Misread lines and not-text regions (small pictures with the right text)"),
         ("ocrfix", "OCR fixes and ignored readings"),
         ("compliance", "Compliance decisions, support links, RFP headers and levels, Format and Customer's marks, "
                        "RFP outline and response structure with placements"),
         ("words", "Compliance words added and removed, acronym choices, keyword and banned-word choices"))
WARNING = ("This pack can hold text and small pictures from customer documents. It goes only to this PC or the approved "
           "SharePoint folder; never e-mail, GitHub, USB or any other place. You are responsible for making sure it holds "
           "nothing that must not be shared there (classified, export-controlled, proprietary or personal information). "
           "Remove such content or leave the sentence text out.")
MAX_MEMBER = 200 * 1024 * 1024
ALLOWED = {"manifest.json", "reading.zip", "ocr_fixes.csv", "ocr_ignore.csv", "compliance_records.jsonl",
           "compliance_outlines.json", "compliance_learned.json", "words.json", "text_fixes.json"}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def code(text):
    """A short code standing for a name (a customer file, a matrix, this PC), never the name itself."""
    return hashlib.sha256((text or "").lower().encode("utf-8")).hexdigest()[:10]


def _state_path(config_dir):
    return os.path.join(config_dir, "training_data_sent.json")


def load_state(config_dir):
    try:
        with open(_state_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return {"sent": list(d.get("sent", [])), "last": d.get("last", "")}
    except (OSError, ValueError):
        pass
    return {"sent": [], "last": ""}


def save_state(config_dir, st):
    os.makedirs(config_dir, exist_ok=True)
    tmp = _state_path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, _state_path(config_dir))


# ------------------------------------------------------------------ Fix the text (Assign right-click)
def word_pairs(wrong, right):
    """Word pairs that differ between a misread sentence and its fix (same word count only)."""
    import re
    strip = lambda w: re.sub(r"^[^\w&/]+|[^\w&/.]+$", "", w)
    a, b = (wrong or "").split(), (right or "").split()
    if len(a) != len(b):
        return []
    return [(strip(x), strip(y)) for x, y in zip(a, b) if strip(x) and strip(y) and strip(x) != strip(y)]


def _fixes_path(config_dir):
    return os.path.join(config_dir, "text_fixes.json")


def text_fixes(config_dir):
    try:
        with open(_fixes_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def record_text_fix(config_dir, wrong, right):
    """Keep a sentence fix for the training team: the word pairs, and the sentences (sent only with sentence text)."""
    d = text_fixes(config_dir)
    d.append({"wrong": wrong, "right": right, "pairs": word_pairs(wrong, right),
              "date": datetime.date.today().isoformat()})
    os.makedirs(config_dir, exist_ok=True)
    tmp = _fixes_path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d[-5000:], f, ensure_ascii=False)
    os.replace(tmp, _fixes_path(config_dir))
    return d[-1]["pairs"]


# ------------------------------------------------------------------ gathering
def _records(M, text):
    """Each decided sentence of a matrix as a record: what was decided and where, with no RFP words unless text."""
    import rfpoutline as RO
    sid = code(os.path.basename(M.path))
    S = RO._S(M)
    levels = S.get("header_levels", {})
    outline_num = {}
    try:
        import compliance as C
        outline_num = {C.outline_label(o): o.get("num", "") for o in M.outline or []}
    except Exception:
        pass
    out = []
    for it in M.items:
        dec = it.get("decision", "")
        head = it.get("type") == "Heading"
        if not dec and not head:
            continue
        r = {"m": sid, "id": it.get("id", ""), "file": code(it.get("file", "")), "decision": dec, "type": it.get("type", ""),
             "actor": it.get("actor", ""), "strength": it.get("strength", ""), "modal": it.get("modal", ""),
             "section": it.get("section", ""), "header": head,
             "level": int(levels.get(it.get("id", ""), RO.guess_level(it.get("section", "")))) if head else 0,
             "support_for": it.get("context_for", ""), "map_num": outline_num.get(it.get("map", ""), "")}
        if text:
            r.update({"text": it.get("text", ""), "lead": it.get("lead", ""), "section_title": it.get("section_title", ""),
                      "map": it.get("map", "")})
        out.append(r)
    return out


def _key(r):
    """What makes a record new: its decision and placement (never the text)."""
    k = {x: r.get(x) for x in ("m", "id", "decision", "type", "section", "header", "level", "support_for", "map_num")}
    return code(json.dumps(k, sort_keys=True))


def _outline(M, text):
    import rfpoutline as RO
    rfp = [{"num": h["num"], "level": h["level"], **({"title": h["title"]} if text else {})} for h in RO.headers(M)]
    ours = [{"num": o.get("num", ""), "level": o.get("level", 1), **({"title": o.get("title", "")} if text else {})}
            for o in (M.outline or [])]
    mp = {k: (v if text else "") for k, v in RO._S(M).get("rfp_map", {}).items()}
    return {"m": code(os.path.basename(M.path)), "rfp_outline": rfp, "response_structure": ours, "rfp_map": mp}


def gather(matrices=(), config_dir="", areas=None, everything=False, text=False, ocr_fixes=(), ocr_ignore=(),
           words=None, sensitivity=None):
    """What a pack would hold now: {"counts": {area: n}, "parts": {member: bytes}, "keys": [new record keys]}.
    matrices: loaded compliance.Matrix objects. ocr_fixes: [[misread, correct, note]]; ocr_ignore: [[reading, note]];
    words: {"cwords_added", "cwords_removed", "choices", "keywords", "banned"}."""
    areas = set(areas or [a for a, _ in AREAS])
    st = load_state(config_dir)
    sent = set(st["sent"])
    counts, parts, keys = {a: 0 for a, _ in AREAS}, {}, []

    def new(k):
        if everything or k not in sent:
            keys.append(k)
            return True
        return False

    if "reading" in areas:
        try:
            import corrections
            lines, regions = corrections.unsent()
            if everything:
                lines = [l.split("\t", 1)[0] for l in corrections._label_lines(corrections.LABELS_FILE)]
                regions = [l.split("\t", 1)[0] for l in corrections._label_lines(corrections.DET_LABELS_FILE)]
            counts["reading"] = len(lines) + len(regions)
        except Exception:
            counts["reading"] = 0
    if "ocrfix" in areas:
        fx = [r for r in ocr_fixes if r and r[0] and new("fix:" + code(r[0] + "\t" + r[1]))]
        ig = [r for r in ocr_ignore if r and r[0] and new("ign:" + code(r[0]))]
        tf = [x for x in text_fixes(config_dir) if new("tfix:" + code(x.get("wrong", "") + "\t" + x.get("right", "")))]
        counts["ocrfix"] = len(fx) + len(ig) + len(tf)
        if tf:
            parts["text_fixes.json"] = json.dumps([{"pairs": x.get("pairs", []), "date": x.get("date", ""),
                                                    **({"wrong": x.get("wrong", ""), "right": x.get("right", "")} if text else {})}
                                                   for x in tf], ensure_ascii=False).encode("utf-8")
        if fx:
            buf = io.StringIO(); w = csv.writer(buf); w.writerow(["Misread", "Correct"]); w.writerows([r[:2] for r in fx])
            parts["ocr_fixes.csv"] = buf.getvalue().encode("utf-8")
        if ig:
            buf = io.StringIO(); w = csv.writer(buf); w.writerow(["Reading"]); w.writerows([r[:1] for r in ig])
            parts["ocr_ignore.csv"] = buf.getvalue().encode("utf-8")
    if "compliance" in areas:
        recs, outs, learn_from = [], [], []
        for M in matrices:
            rs = [r for r in _records(M, text) if new("rec:" + _key(r))]
            if rs:
                recs += rs
                outs.append(_outline(M, text))
                learn_from.append(M)
        counts["compliance"] = len(recs)
        if recs:
            parts["compliance_records.jsonl"] = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs).encode("utf-8")
            parts["compliance_outlines.json"] = json.dumps(outs, ensure_ascii=False).encode("utf-8")
            import complearn
            with tempfile.TemporaryDirectory() as td:
                L = complearn.Learner(os.path.join(td, "learned.json"))
                for M in learn_from:
                    L.learn(M.path, M.items, M.outline)
                L.save()
                with open(L.path, "rb") as f:
                    parts["compliance_learned.json"] = f.read()
    if "words" in areas and words:
        w = {}
        for k in ("cwords_added", "cwords_removed", "banned"):
            v = [x for x in words.get(k, []) if x and new(f"w:{k}:" + code(x))]
            if v:
                w[k] = v
        ch = {t: c for t, c in (words.get("choices") or {}).items() if new("w:choice:" + code(t + json.dumps(c, sort_keys=True)))}
        if ch:
            w["choices"] = ch
        kw = {k: v for k, v in (words.get("keywords") or {}).items() if v}
        if kw and new("w:kw:" + code(json.dumps(kw, sort_keys=True))):
            w["keywords"] = kw                                  # hashed phrases and counts only
        counts["words"] = sum(len(v) for k, v in w.items() if k != "keywords") + sum(len(v) for v in kw.values() if "keywords" in w)
        if w:
            parts["words.json"] = json.dumps(w, ensure_ascii=False).encode("utf-8")
    return {"counts": counts, "parts": parts, "keys": keys}


def build(out_path, config_dir, app_version="", acknowledged=False, **kw):
    """Write the pack. The responsibility warning must be acknowledged. Returns {"path", "counts"} (path "" when there
    was nothing to send)."""
    if not acknowledged:
        raise PermissionError("the warning was not acknowledged")
    import secure
    if secure.ACTIVE:                                   # 2.97.0
        raise PermissionError("SCIF-ready: training data is never sent")
    sens = kw.pop("sensitivity", None) or "CUI"
    g = gather(config_dir=config_dir, **kw)
    areas = set(kw.get("areas") or [a for a, _ in AREAS])
    parts = dict(g["parts"])
    if "reading" in areas and g["counts"]["reading"]:
        import corrections
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "reading.zip")
            r = corrections.export_pack(p, everything=kw.get("everything", False), anonymous=True)
            if r.get("path"):
                with open(p, "rb") as f:
                    parts["reading.zip"] = f.read()
    if not parts:
        return {"path": "", "counts": g["counts"]}
    now = datetime.datetime.now().isoformat(timespec="seconds")
    man = {"format": FORMAT, "version": 1, "app_version": app_version, "created": now,
           "from": code(getpass.getuser() + "@" + platform.node()), "text": bool(kw.get("text")),
           "areas": sorted(areas), "counts": g["counts"], "files": {n: _sha(b) for n, b in parts.items()},
           "sensitivity": sens,                                     # 2.97.0: the highest level inside; never above CUI
           "sensitivity_rule": "Only efforts at most CUI with a known sensitivity; nothing from SCIF-ready."}
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)
        z.writestr("manifest.json", json.dumps(man, indent=1))
    os.replace(tmp, out_path)
    st = load_state(config_dir)
    st["sent"] = sorted(set(st["sent"]) | set(g["keys"]))
    st["last"] = now
    save_state(config_dir, st)
    return {"path": out_path, "counts": g["counts"]}


# ------------------------------------------------------------------ reading a pack (Stationkeeper Training)
class PackError(Exception):
    pass


def read(path):
    """Check a pack before anything is used. Returns (manifest, {member: bytes})."""
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        raise PackError("not a training data pack (not a zip file)")
    with z:
        names = z.namelist()
        if "manifest.json" not in names:
            raise PackError("not a training data pack (no manifest)")
        try:
            man = json.loads(z.read("manifest.json").decode("utf-8"))
        except ValueError:
            raise PackError("the manifest is not readable")
        if man.get("format") != FORMAT:
            raise PackError("not a training data pack (wrong format)")
        files = man.get("files") or {}
        out = {}
        for info in z.infolist():
            n = info.filename
            if n == "manifest.json":
                continue
            if n not in ALLOWED:
                raise PackError(f"unexpected file in the pack: {n[:80]}")
            if info.file_size > MAX_MEMBER:
                raise PackError(f"file too large: {n[:80]}")
            data = z.read(n)
            if files.get(n) != _sha(data):
                raise PackError(f"checksum does not match: {n[:80]} (the pack was changed after it was made)")
            out[n] = data
        if set(files) - set(out):
            raise PackError("files listed in the manifest are missing")
    return man, out


def sensitivity_problem(man, confirmed_old=False):
    """2.97.0: why Stationkeeper Training refuses a pack ('' when it may be imported): its sensitivity must be known and
    at most CUI. A pack from before 2.97 says nothing: it is refused unless the person confirms it holds nothing above
    CUI."""
    import sensitivity as S
    s = man.get("sensitivity")
    if s is None:
        return "" if confirmed_old else ("This pack was made before Stationkeeper 2.97 and does not say its sensitivity. "
                                         "Import it only if you know it holds nothing above CUI.")
    lv = S.level_of_words(s)
    if lv < 0:
        return f"This pack's sensitivity ({str(s)[:40]}) is not known. It is not imported."
    if lv > S.TRAINING_MAX:
        return f"This pack is marked {S.name(lv)}. Nothing above CUI is ever imported for training."
    return ""


def import_pack(path, store_dir, learned_path, merge_fixes=None, merge_ignore=None, confirmed_old=False):
    """Stationkeeper Training: file each area where it belongs. Reading goes into the training set (as a corrections
    pack); OCR fixes and ignores merge add-only; compliance learning merges into the team's learning; the records,
    outlines and words are kept under store_dir for the Training Studio. Returns {area: count, "from", "created"}.
    2.97.0: a pack above CUI, or of unknown sensitivity, is refused (PackError) before anything is used."""
    man, data = read(path)
    why = sensitivity_problem(man, confirmed_old)
    if why:
        raise PackError(why)
    got = {"reading": 0, "ocrfix": 0, "compliance": 0, "learned": 0, "words": 0, "skipped": 0}
    if "reading.zip" in data:
        import corrections
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "reading.zip")
            with open(p, "wb") as f:
                f.write(data["reading.zip"])
            r = corrections.import_pack(p)
        got["reading"] = r["lines"] + r["regions"]
        got["skipped"] += r["skipped"]
    if "ocr_fixes.csv" in data and merge_fixes:
        got["ocrfix"] += merge_fixes(data["ocr_fixes.csv"])
    if "ocr_ignore.csv" in data and merge_ignore:
        got["ocrfix"] += merge_ignore(data["ocr_ignore.csv"])
    if "compliance_learned.json" in data:
        import complearn
        L = complearn.Learner(learned_path)
        got["learned"] = L.merge_pack(data["compliance_learned.json"])
        L.save()
    if "text_fixes.json" in data:
        got["ocrfix"] += len(json.loads(data["text_fixes.json"].decode("utf-8")))
    keep = {n: b for n, b in data.items() if n in ("compliance_records.jsonl", "compliance_outlines.json", "words.json",
                                                   "text_fixes.json")}
    if keep:
        d = os.path.join(store_dir, f"{man.get('from', 'pc')}_{str(man.get('created', ''))[:19].replace(':', '')}")
        os.makedirs(d, exist_ok=True)
        for n, b in keep.items():
            with open(os.path.join(d, n), "wb") as f:
                f.write(b)
        with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(man, f, indent=1)
    if "compliance_records.jsonl" in data:
        got["compliance"] = sum(1 for l in data["compliance_records.jsonl"].decode("utf-8").splitlines() if l.strip())
    if "words.json" in data:
        w = json.loads(data["words.json"].decode("utf-8"))
        got["words"] = sum(len(v) for k, v in w.items() if k != "keywords") + sum(len(v) for v in (w.get("keywords") or {}).values())
    got.update({"from": man.get("from", ""), "created": man.get("created", ""), "text": bool(man.get("text"))})
    return got
