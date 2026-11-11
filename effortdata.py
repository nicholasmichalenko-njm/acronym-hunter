"""Effort data for Stationkeeper Macros (4.9.0; contract claude/stationkeeper-effort-data-contract-v1.md; decisions in
claude/stationkeeper-effort-data-evaluation-2026-11-10.md).

The app publishes a read-only snapshot of the effort's rules into the effort folder, and the Word macros read it:

    <effort folder>\\Stationkeeper Data\\
        manifest.json                 written last, every publish
        rules\\rules.json              manifest_revision = the manifest's revision
        rules\\effort-data.schema.json the JSON Schema rules.json follows (shipped with the app)
        templates\\effort.dotx         the effort's template: styles, table looks, Quick Parts; no macros
        dictionaries\\effort.dic       the team's custom dictionaries and the effort's acronyms, UTF-16 LE with a BOM
        README.txt

How (decided 19:30): a publisher on the app's 3-second timer works out each part's inputs and writes only the parts
that changed, within seconds of the change, and publishes the first snapshot when an effort without one opens. Each
part is written under a .tmp name and renamed (retried while a reader or OneDrive holds it); the manifest last. The
revision only goes up. The effort has a stable id. The template is rebuilt whenever its styles, table looks or Quick
Parts change, so the macros never read a stale one. Warning times are fixed at 24 hours (Aging) and 72 (Stale). The app
is the only writer, and everything is written inside the effort folder. Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, hashlib, json, os, platform, shutil, tempfile, time, uuid

import diag

CONTRACT = "stationkeeper.effort-data"
SCHEMA_VERSION = "1.0"
FOLDER = "Stationkeeper Data"
FRESHNESS = {"warn_after_hours": 24, "stale_after_hours": 72}
SCHEMA_FILE = "effort-data.schema.json"
README = ("Written by Stationkeeper. Do not edit. Edit the effort in Stationkeeper.\r\n\r\nStationkeeper Macros reads these "
          "files: manifest.json says which revision is here and each part's size and fingerprint.\r\n")
KEEP_ON_CLEAR = "Bold, Italic, Superscript, Subscript"


def folder(effort_path):
    return os.path.join(os.path.dirname(os.path.abspath(effort_path)), FOLDER)


def schema_path():
    """The schema shipped with the app (beside this module; bundled by Stationkeeper.spec)."""
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "effortdata", SCHEMA_FILE)


def effort_id(ws):
    """The effort's stable id, made once and kept with the effort (the app keys efforts by name)."""
    i = ws.get("effort_id") if ws is not None else ""
    if not i and ws is not None:
        i = uuid.uuid4().hex
        ws.set("effort_id", i)
    return i or ""


# ------------------------------------------------------------------ rules.json
def _caption(std, label):
    return next((c for c in std.get("captions") or [] if c.get("label") == label and c.get("part", "body") == "body"), {})


def _page_limits(ws, effort_path):
    out = []
    try:
        import docversions as DV
        import subreq as SR
        reg = SR.Register(DV.Library(ws.p("documents")).load())
        for r in reg.rows():
            if r.get("kind") == "Page limit":
                n = next((int(t) for t in str(r.get("value", "")).split() if t.isdigit()), None)
                if n:
                    out.append({"heading": str(r.get("subject") or ""), "max_pages": n})
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return out


def _acronyms(effort_path):
    """(in the list with a definition, not a term) from the effort's acronym list."""
    import effort as E
    keep, ignore = [], []
    try:
        lst = E.EffortList(effort_path).load()
        for t in lst.order:
            row = lst.rows.get(t) or {}
            st = row.get("Status") or E.IN
            if st == E.NOT:
                ignore.append({"text": t})
            elif (row.get("Definition") or "").strip():
                keep.append({"acronym": t, "definition": row["Definition"].strip()})
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return keep, ignore


def rules(config_dir, ws, effort_path, std=None):
    """The rules the macros read, from the effort's standard, phrases, acronym list and page limits."""
    import banned as B
    import prodrules as PRL
    std = std if std is not None else PRL.for_effort(config_dir, ws)
    tcap, fcap = _caption(std, "Table"), _caption(std, "Figure")
    tts = std.get("table_types") or {}
    rows = std.get("row_types") or {}
    limits = _page_limits(ws, effort_path)
    out = {"schema_version": SCHEMA_VERSION, "manifest_revision": 0,
           "settings": {"StylePrefix": "", "CaptionStyle": tcap.get("style") or "Caption",
                        "CaptionInFirstRow": (std.get("checks") or {}).get("table_caption_position") == "first row",
                        "KeepOnClear": KEEP_ON_CLEAR, "CheckTablesForDirectFormatting": True,
                        "TableWidthPercent": int((tts.get("std") or {}).get("width_pct") or 100),
                        "TableCaptionPosition": (tcap.get("position") or "above").capitalize(),
                        "FigureCaptionPosition": (fcap.get("position") or "below").capitalize(),
                        "TableLabel": tcap.get("label") or "Table", "FigureLabel": fcap.get("label") or "Figure",
                        "MaxKeepWithNextChain": 8, "PageLimitTotal": sum(x["max_pages"] for x in limits) or None}}
    allowed = list((std.get("styles") or {}).get("allowed") or []) or sorted((std.get("style_defs") or {}).keys())
    if allowed:
        out["allowed_styles"] = [{"style": s, "required": False, "notes": ""} for s in allowed]
    tt = []
    for _k, t in tts.items():
        roles = t.get("roles") or []
        hdr, body, note = rows.get("header") or {}, rows.get("body") or {}, rows.get("note") or {}
        tt.append({"type": t.get("name") or _k, "table_style": "", "header_row_repeats": bool(hdr.get("repeat", True)),
                   "rows_may_break_across_pages": False, "width_percent": int(t.get("width_pct") or 100),
                   "header_row_style": hdr.get("tag_style") or "", "body_style": body.get("tag_style") or "",
                   "notes_row_style": note.get("tag_style") or "", "has_notes_row": "note" in roles,
                   "cell_padding": (t.get("cell_margins") or {}).get("left")})
    if tt:
        out["table_types"] = tt
    ph, bp = [], []
    for r in B.load():
        if r.get("Why") == "Placeholder left in":
            ph.append({"text": r["Phrase"].rstrip("*")})
        else:
            bp.append({"phrase": r["Phrase"].rstrip("*"), "replacement": r.get("Use instead") or "", "rule_id": "",
                       "reason": r.get("Why") or r.get("Level") or "", "match_case": False, "whole_word": not r["Phrase"].endswith("*")})
    out["placeholders"], out["banned_phrases"] = ph, bp
    fonts = sorted({f for sc in (std.get("fonts") or {}).values() for f in ((sc or {}).get("fonts") or [])})
    if fonts:
        out["fonts"] = [{"font": f, "allowed": True} for f in fonts]
    acr, ign = _acronyms(effort_path)
    out["acronyms"], out["ignore"] = acr, ign
    if limits:
        out["page_limits"] = limits
    return out


def dictionary_words(config_dir, effort_path):
    """The team's custom dictionaries and the effort's acronyms (in the list), one word each, sorted."""
    import customdict as CD
    words = set()
    try:
        for d in CD.Store(config_dir).dicts:
            words.update(d.get("words") or [])
    except Exception:  # noqa: BLE001
        diag.swallowed()
    acr, _ign = _acronyms(effort_path)
    words.update(a["acronym"] for a in acr)
    return CD.sort_words(sorted(w for w in words if w))


def template_inputs(std):
    """What the effort's template is built from: its styles, table looks and types, Quick Parts and page parts (with
    their files' fingerprints)."""
    keys = ("style_defs", "styles", "table_styles", "row_types", "table_types", "quick_parts", "page_parts", "heading_numbering",
            "list_numbering", "captions", "page_setups", "pagination", "theme", "variables")
    blob = {k: std.get(k) for k in keys}
    pdir = std.get("_parts_dir") or ""
    files = sorted({str(e.get("file") or "") for e in (std.get("quick_parts") or {}).get("entries") or []} |
                   {str(v) for v in (std.get("page_parts") or {}).values()})
    for f in files:
        p = os.path.join(pdir, f) if f and pdir else ""
        try:
            st = os.stat(p)
            blob["file:" + f] = [st.st_size, int(st.st_mtime)]
        except OSError:
            pass
    return hashlib.sha256(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def build_template(std, out_path):
    """The effort's .dotx (no Word; no macros), written to out_path. Returns out_path, or "" when it cannot be made."""
    import prodtemplate as PT
    work = tempfile.mkdtemp(prefix="sk_effdata_")
    try:
        job = PT.make(dict(std), work)
        shutil.copyfile(job.copy, out_path)
        return out_path
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return ""
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ writing
def _replace(tmp, target, tries=5):
    """os.replace, retried with backoff while a reader or OneDrive holds the target (about 2 seconds in all)."""
    for k in range(tries):
        try:
            os.replace(tmp, target)
            return True
        except PermissionError:
            time.sleep(0.1 * (2 ** k))
    os.replace(tmp, target)
    return True


def _read(path):
    """The file's bytes, the handle closed at once (Windows will not replace a file that is open)."""
    with open(path, "rb") as f:
        return f.read()


def _write(path, data):
    """Write bytes under <name>.tmp beside the target, flushed and closed, then rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    _replace(tmp, path)
    return path


def _part(key, rel, fmt, data, rev):
    return {"key": key, "path": rel, "format": fmt, "part_revision": rev, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def read_manifest(effort_path):
    try:
        with open(os.path.join(folder(effort_path), "manifest.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def publish(config_dir, ws, effort_path, effort_name, app_version="", force=False, std=None, info=None):
    """Publish what changed. Returns {"revision", "written": [part keys]} or None when nothing changed."""
    import customdict as CD
    import prodrules as PRL
    std = std if std is not None else PRL.for_effort(config_dir, ws)
    base = folder(effort_path)
    st = dict(ws.get("effort_data") or {})
    man = read_manifest(effort_path)
    have = bool(man)
    r = rules(config_dir, ws, effort_path, std)
    rhash = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    words = dictionary_words(config_dir, effort_path)
    dhash = hashlib.sha256("\n".join(words).encode()).hexdigest()
    thash = template_inputs(std)
    parts_state = dict(st.get("parts") or {})
    changed = {"rules": rhash != (parts_state.get("rules") or {}).get("hash"),
               "dictionary": bool(words) and dhash != (parts_state.get("dictionary") or {}).get("hash"),
               "template": thash != (parts_state.get("template") or {}).get("hash")}
    if have and not force and not any(changed.values()):
        return None
    rev = max(int(st.get("revision") or 0), int((man or {}).get("revision") or 0)) + 1
    written, parts, pending = [], [], []
    if changed["template"] or force or not os.path.isfile(os.path.join(base, "templates", "effort.dotx")):
        tmp_out = os.path.join(base, "templates", "effort.dotx.building")
        os.makedirs(os.path.dirname(tmp_out), exist_ok=True)
        if build_template(std, tmp_out):
            with open(tmp_out, "rb") as f:
                data = f.read()
            os.remove(tmp_out)
            try:
                _write(os.path.join(base, "templates", "effort.dotx"), data)
                parts_state["template"] = {"hash": thash, "part_revision": rev}
                written.append("template")
            except PermissionError:                    # Word has it open as a document's template: the rest goes now,
                diag.swallowed()                       # the template on a later try (the manifest keeps the old one)
                pending.append("template")
                try:
                    os.remove(os.path.join(base, "templates", "effort.dotx.tmp"))
                except OSError:
                    pass
    if words and (changed["dictionary"] or force or not os.path.isfile(os.path.join(base, "dictionaries", "effort.dic"))):
        p = os.path.join(base, "dictionaries", "effort.dic")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        CD.write_dic(p + ".building", words)
        data = _read(p + ".building")
        os.remove(p + ".building")
        _write(p, data)
        parts_state["dictionary"] = {"hash": dhash, "part_revision": rev}
        written.append("dictionary")
    r["manifest_revision"] = rev                               # rules.json carries the manifest's revision, every time
    rdata = json.dumps(r, indent=1, ensure_ascii=False).encode("utf-8")
    _write(os.path.join(base, "rules", "rules.json"), rdata)
    parts_state["rules"] = {"hash": rhash, "part_revision": rev}
    written.append("rules")
    try:
        sp = schema_path()
        if os.path.isfile(sp):
            _write(os.path.join(base, "rules", SCHEMA_FILE), _read(sp))
    except OSError:
        diag.swallowed()
    if not os.path.isfile(os.path.join(base, "README.txt")):
        _write(os.path.join(base, "README.txt"), README.encode("utf-8"))
    parts.append(_part("rules", "rules/rules.json", "json", rdata, rev))
    for key, rel, fmt in (("template", "templates/effort.dotx", "dotx"), ("dictionary", "dictionaries/effort.dic", "dic-utf16")):
        p = os.path.join(base, *rel.split("/"))
        if key in parts_state and os.path.isfile(p):
            parts.append(_part(key, rel, fmt, _read(p), int(parts_state[key].get("part_revision") or rev)))
    info = info or {}
    manifest = {"contract": CONTRACT, "schema_version": SCHEMA_VERSION, "min_reader_version": "1.0",
                "effort": {"id": effort_id(ws), "name": effort_name, "solicitation": info.get("solicitation", ""),
                           "cui": bool(info.get("cui", True))},
                "revision": rev, "published_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "published_by": getpass.getuser(), "writer": {"app": "Stationkeeper", "app_version": app_version,
                                                               "machine": platform.node()},
                "freshness": dict(FRESHNESS), "parts": parts}
    _write(os.path.join(base, "manifest.json"), json.dumps(manifest, indent=1, ensure_ascii=False).encode("utf-8"))
    st.update(revision=rev, parts=parts_state, published=manifest["published_utc"])
    ws.set("effort_data", st)
    diag.activity("effort_data_published", n=len(written))
    return {"revision": rev, "written": written, "pending": pending}


def _inputs_stamp(w):
    """The times and sizes of every file the snapshot is made from, and the effort's own formatting."""
    import app_gui as A
    paths = [w.effort_path, os.path.join(w.config_dir, "production_standards.json"), os.path.join(w.config_dir, "banned_words.csv"),
             os.path.join(A.CONFIG_DIR, "banned_words.csv"), os.path.join(w.config_dir, "custom_dictionaries.json"),
             os.path.join(w.ws.p("documents"), "index.json"), os.path.join(folder(w.effort_path), "manifest.json")]
    out = []
    for p in paths:
        try:
            s_ = os.stat(p)
            out.append((p, s_.st_size, s_.st_mtime_ns))
        except OSError:
            out.append((p, None, None))
    out.append(json.dumps(w.ws.get("prod_std") or {}, sort_keys=True, default=str))
    return tuple(out)


def tick(w):
    """The window's 3-second timer: publish what changed for the open effort. Never stops the window."""
    if w.ws is None or not getattr(w, "effort_path", ""):
        return None
    if os.environ.get("AH_TEST") and not os.environ.get("SK_EFFORTDATA_TEST"):
        return None
    try:
        stamp = _inputs_stamp(w)                               # cheap: only when something it reads changed
        retry = getattr(w, "_effdata_retry", 0) and time.time() >= w._effdata_retry
        if stamp == getattr(w, "_effdata_stamp", None) and not retry:
            return None
        w._effdata_stamp, w._effdata_retry = stamp, 0
        info = (getattr(w, "efforts", None) or {}).get(w.effort_name) or {}
        res = publish(w.config_dir, w.ws, w.effort_path, w.effort_name, getattr(w, "version", ""),
                      info={"solicitation": info.get("solicitation", ""), "cui": True})
        if res and res.get("pending"):
            w._effdata_retry = time.time() + 60                # 4.9.0: the template again in a minute
        return res
    except Exception:  # noqa: BLE001
        diag.swallowed()
        w._effdata_retry = time.time() + 60
        return None
