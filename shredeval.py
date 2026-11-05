"""Shred accuracy (3.59.0, claude/stationkeeper-shred-accuracy-decisions-2026-11-05.md): the shred measured against
answer keys a person labels in Review. A key sits beside its RFP (<file>.answers.csv: each sentence's decision and
kind, as decided in Review). Scoring reads the RFP fresh with the shred's own reader (shredquick) and compares:
recall (the real requirements found), precision (the flags that were real requirements) and the kind (Requirement,
Instruction (L), Evaluation (M), SOW task) scored apart. The set lives on the person's PC, outside the repository;
history and the build print scores only, never a file's name or text. Rules only; nothing leaves the PC.

save_keys(M) / set_files(folder) / score_file(path, key) / score_set(folder) / history(path) / append_history(path, row, version)
"""
import csv, datetime, os, re

KEY_SUFFIX = ".answers.csv"
KEY_COLUMNS = ("Key", "Decision", "Kind", "Section", "Text")
HIST_COLUMNS = ("Date", "Version", "RFPs", "Requirements", "Recall", "Precision", "Kind right",
                "Recall Requirement", "Recall Instruction (L)", "Recall Evaluation (M)", "Recall SOW task")
TARGET = 95.0


def default_folder():
    return os.path.join(os.path.expanduser("~"), "Stationkeeper Shred Set")


def key_path(path):
    return path + KEY_SUFFIX


def _norm(t):
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


# ------------------------------------------------------------------ labels from Review
def save_keys(M):
    """Each RFP file of the matrix gets its answer key beside it: every sentence's decision and kind as decided in
    Review. Returns [(file path, key path, sentences, decided)]; a file no longer on this PC is skipped."""
    import shredquick as SQ
    import compliance as C
    where = {s[0]: s[3] for s in (M.sources or []) if len(s) > 3}
    out = []
    for name, path in where.items():
        if not path or not os.path.isfile(path):
            continue
        fk = C.file_kind(name)
        rows = [it for it in M.items if it.get("file") == name and it.get("type") != "Heading"]
        kp = key_path(path)
        tmp = kp + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(KEY_COLUMNS)
            for it in rows:
                dec = it.get("decision") or ""
                w.writerow([it.get("key") or C.text_key(it.get("text", "")), dec, SQ.kind_of(it, fk) if dec == "Keep" else "",
                            it.get("section", ""), " ".join((it.get("text") or "").split())])
        os.replace(tmp, kp)
        out.append((path, kp, len(rows), sum(1 for it in rows if it.get("decision"))))
    return out


def read_key(kp):
    with open(kp, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ the set
def set_files(folder):
    """[(RFP path, key path or None)] every file the reader takes in the folder and its subfolders."""
    import app_gui as A
    out = []
    if not folder or not os.path.isdir(folder):
        return out
    for root, _dirs, files in os.walk(folder):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            if fn.endswith(KEY_SUFFIX) or fn.startswith("~$") or os.path.splitext(fn)[1].lower() not in A.SUPPORTED_EXTS:
                continue
            out.append((p, key_path(p) if os.path.isfile(key_path(p)) else None))
    return out


def score_file(path, kp):
    """{"truth", "found", "predicted", "right", "kind_total", "kind_right", "by_kind": {kind: [truth, found]}, "decided", "sentences"}."""
    import shredquick as SQ
    import compliance as C
    key = read_key(kp)
    truth = [r for r in key if r.get("Decision") == "Keep"]
    other = {r["Key"] for r in key if r.get("Decision") and r.get("Decision") != "Keep"}
    rows = SQ.shred(path)["rows"]
    pred = {C.text_key(r["text"]): r for r in rows}
    pred_norm = [(_norm(r["text"]), r) for r in rows]
    by_kind = {k: [0, 0] for k in SQ.KINDS}
    found, kind_right, kind_total, hit = 0, 0, 0, set()
    for t in truth:
        r = pred.get(t["Key"])
        if r is None:                                # split or joined differently: the same words inside one another
            n = _norm(t.get("Text"))
            r = next((x for nx, x in pred_norm if n and len(n) > 20 and (n in nx or (len(nx) > 20 and nx in n))), None)
        k = t.get("Kind") or SQ.KINDS[0]
        by_kind.setdefault(k, [0, 0])[0] += 1
        if r is not None:
            found += 1; by_kind[k][1] += 1; hit.add(C.text_key(r["text"]))
            kind_total += 1; kind_right += r["kind"] == k
    wrong = sum(1 for kk in pred if kk not in hit and kk in other)          # flagged, decided not a requirement
    return {"truth": len(truth), "found": found, "predicted": len(pred), "right": len(hit), "false": wrong,
            "kind_total": kind_total, "kind_right": kind_right, "by_kind": by_kind,
            "decided": sum(1 for r in key if r.get("Decision")), "sentences": len(key)}


def _pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score_set(folder):
    """{"files": [{"path", "name", "labeled", ...score}], "rfps", "labeled", "requirements", "recall", "precision",
    "kind_right", "by_kind": {kind: recall}}."""
    import shredquick as SQ
    files, tot = [], {"truth": 0, "found": 0, "right": 0, "false": 0, "kind_total": 0, "kind_right": 0}
    bk = {k: [0, 0] for k in SQ.KINDS}
    for p, kp in set_files(folder):
        row = {"path": p, "name": os.path.basename(p), "labeled": kp is not None}
        if kp:
            try:
                s = score_file(p, kp)
            except Exception as e:  # noqa: BLE001
                row["error"] = type(e).__name__
            else:
                row.update(s)
                row["recall"] = _pct(s["found"], s["truth"])
                row["precision"] = _pct(s["right"], s["right"] + s["false"])
                for k in tot:
                    tot[k] += s[k]
                for k, (a, b) in s["by_kind"].items():
                    bk.setdefault(k, [0, 0]); bk[k][0] += a; bk[k][1] += b
        files.append(row)
    lab = [f for f in files if f["labeled"] and "error" not in f]
    return {"files": files, "rfps": len(files), "labeled": len(lab), "requirements": tot["truth"],
            "recall": _pct(tot["found"], tot["truth"]), "precision": _pct(tot["right"], tot["right"] + tot["false"]),
            "kind_right": _pct(tot["kind_right"], tot["kind_total"]),
            "by_kind": {k: _pct(b, a) for k, (a, b) in bk.items()}}


# ------------------------------------------------------------------ history (scores only)
def history(path):
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def append_history(path, result, version, when=None):
    when = when or datetime.datetime.now()
    row = [f"{when:%Y-%m-%d %H:%M}", version, result["labeled"], result["requirements"], result["recall"],
           result["precision"], result["kind_right"]] + [result["by_kind"].get(k) for k in
                                                          ("Requirement", "Instruction (L)", "Evaluation (M)", "SOW task")]
    new = not os.path.isfile(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HIST_COLUMNS)
        w.writerow(["" if v is None else v for v in row])
    return row


# ------------------------------------------------------------------ amendments (decision 6)
def is_amendment(doc, version=None):
    """An amendment: a document typed Amendment, or a new version the Library labels Amendment N."""
    return (doc or {}).get("type") == "Amendment" or str((version or {}).get("label", "")).lower().startswith("amendment")


def acknowledgment_rows(M, made):
    """A matrix row per amendment with none yet: Acknowledge it as the RFP asks. made: [(document, version)] as the
    Library adds them (or documents alone). Returns the rows added."""
    import compliance as C
    have = {it.get("key") for it in M.items}
    added = []
    for x in made:
        doc, ver = (x if isinstance(x, tuple) else (x, None))
        if not is_amendment(doc, ver):
            continue
        lab = (ver or {}).get("label", "")
        name = f"{lab} to {doc.get('name')}" if lab.lower().startswith("amendment") and doc.get("name") else (doc.get("name") or lab or "the amendment")
        text = (f"Acknowledge {name} as the RFP asks (the SF 30, the cover letter or the form it names). "
                "Added by Stationkeeper when the amendment entered the Library.")
        if C.text_key(text) in have:                 # one row per amendment, kept in the matrix by its words
            continue
        it = {"id": "", "file": "(Stationkeeper)", "key": C.text_key(text), "text": text, "type": "Instruction",
              "section": "", "section_title": "", "decision": "Keep", "suggest": "Keep",
              "page": "", "loc": "", "map": "", "owner": "", "status": "", "notes": ""}
        M.items.append(it); added.append(it)
    if added:
        C.assign_ids(M.items)
        M.pending = True
        try:
            M.log("matrix", f"{len(added)} amendment acknowledgment row(s) added")
        except Exception:  # noqa: BLE001
            pass
    return added
