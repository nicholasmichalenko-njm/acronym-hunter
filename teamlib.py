"""The team library as files (4.7.0; claude/stationkeeper-team-library-files-decisions-2026-11-10.md, decisions 1 to 4).

The files are the truth; the app keeps a cache it rebuilds from them:
- Global Standards.xlsx: the values of the Global Standards and the field recipes (standardsbook). The
  app's production_standards.json and field_recipes.json are its cache.
- Content\\: the Word files the standards and the library keep (covers, back covers, title pages, Quick Parts sources,
  header and footer designs), one folder each for the standards' parts and the library's kept files. Edit them in Word;
  the app's copies follow. A file the app keeps (Bring in, a new cover) appears there.
- <effort> Effort Standards.xlsx (a program's: <program> Program Standards.xlsx), beside the effort's list: the same
  sheets with only that effort's changes (a blank cell means the Global Standards value). 4.59.0: named so by UX
  decision 133; one written under its earlier name, <effort> Effort Formatting.xlsx, is renamed once.

Where: Stationkeeper Data\\Team library unless Settings points it at another folder (a SharePoint library synced to
each PC, so the team shares one). Updates never touch it.

How the two ways meet: the app writes the workbook after its own changes (marked to write, then written on the next
tick, so a burst of edits writes once) and reads it when its size or time changed. Excel keeps the file locked while
it is open: the app waits and says so. A workbook that cannot be read is reported and skipped; the last good reading
stays. A sync conflict copy ("Global Standards-PCNAME.xlsx") is reported, never read. Nothing is deleted in the move:
the first run writes the files from the cache, and the JSON stays. Nothing leaves the PC."""
import hashlib, json, os, re, shutil, time

import diag

BOOK = "Global Standards.xlsx"
OLD_BOOK = "Company Standards.xlsx"              # its name from 4.7.0 to 4.30: read and renamed once (4.31.0)
CONTENT = "Content"
STATE = "team_library_state.json"
PAIRS = (("production_parts", "Standards parts"), (os.path.join("template_library", "sources"), "Library files"))
_reading = False
_said = []                                       # 4.56.2: lines for the person from the last writes (take_said)


def default_folder(data_dir):
    return os.path.join(data_dir, "Team library")


def folder(config_dir, settings=None):
    """The team library: Settings' choice, else beside the config folder in Stationkeeper Data."""
    s = settings if settings is not None else _settings()
    f = (s or {}).get("team_library") or ""
    return f if f else default_folder(os.path.dirname(os.path.abspath(config_dir)))


def _settings():
    try:
        import app_gui as A
        return A.load_settings()
    except Exception:  # noqa: BLE001
        return {}


def book_path(config_dir, settings=None):
    """The workbook. One written under its earlier name (Company Standards.xlsx, 4.7.0 to 4.30) is renamed once; while
    Excel has that one open it is used as it is and renamed the next time."""
    d = folder(config_dir, settings)
    new, old = os.path.join(d, BOOK), os.path.join(d, OLD_BOOK)
    if not os.path.isfile(new) and os.path.isfile(old):
        try:
            os.replace(old, new)
        except OSError:
            return old
    return new


def _state_path(config_dir):
    return os.path.join(config_dir, STATE)


def state(config_dir):
    try:
        with open(_state_path(config_dir), encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def _save_state(config_dir, st):
    os.makedirs(config_dir, exist_ok=True)
    st["format"] = 1                                     # formats.py "team library state"
    p = _state_path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(p + ".tmp", p)


def _stamp(p):
    try:
        st = os.stat(p)
        return [st.st_mtime_ns, st.st_size]
    except OSError:
        return None


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mark_dirty_file(path):
    """A list saved in the config folder (banned_words.csv, author_list.json...): the workbook follows."""
    try:
        return mark_dirty(os.path.dirname(os.path.abspath(path)))
    except Exception:  # noqa: BLE001
        return False


def mark_dirty(config_dir):
    """The app changed the standards or the recipes: the workbook is written on the next tick. Not while reading it."""
    if _reading:
        return False
    st = state(config_dir)
    st["dirty"] = True
    _save_state(config_dir, st)
    return True


# ------------------------------------------------------------------ the workbook
def _moved(p, stamp, sha):
    """The workbook is not as the app last read or wrote it."""
    now = _stamp(p)
    return now is not None and now != stamp and _sha(p) != sha


def take_said():
    """The lines the last writes left for the person (a workbook read first, rows changed in both places)."""
    out = list(_said)
    del _said[:]
    return out


def _mine(write):
    """The workbook the app would write now, as a reading (written to a temp folder, read back, removed)."""
    import tempfile
    import standardsbook as SB
    d = tempfile.mkdtemp(prefix="sk_book_")
    try:
        return SB.read(write(os.path.join(d, "mine.xlsx")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _base(config_dir, p):
    import bookmerge as BM
    import standardsbook as SB
    b = BM.base_path(config_dir, p)
    if not os.path.isfile(b):
        return None
    got = SB.read(b)
    return None if got["problems"] else got


def _merge_book(config_dir, p, st, settings=None):
    """4.56.2: the workbook changed while the app's changes were waiting: read it first and merge row by row
    (bookmerge). Returns "merged", or "unread" when the workbook cannot be read (nothing is written over it)."""
    import bookmerge as BM
    import fieldrecipes as FR
    import listsbook as LB
    import prodrules as PRL
    import standardsbook as SB
    theirs = SB.read(p)
    if theirs["problems"]:
        _said.extend("The Global Standards workbook changed and could not be read, so your changes are not "
                     "written over it yet: " + x for x in theirs["problems"])
        return "unread"
    data = PRL.load(config_dir)
    recipes = FR.load(config_dir)
    SB.stamp_since(data["company"], st.get("rows") or {})
    mine = _mine(lambda t: SB.write(t, data["company"], recipes, st.get("own_cols") or {}, LB.load_all(config_dir)))
    merged, rep = BM.merge(_base(config_dir, p), mine, theirs, readonly=LB.READ_ONLY)
    res = SB.apply(data["company"], recipes, merged, removed_answer=(st.get("answers") or {}).get("removed"))
    global _reading
    _reading = True
    try:
        data["company"] = res["company"]
        PRL.save(config_dir, data)
        FR.save(config_dir, res["recipes"])
        LB.apply(config_dir, merged)
    finally:
        _reading = False
    st["own_cols"] = res["own_cols"]
    _save_state(config_dir, st)
    _said.extend(BM.said("The Global Standards workbook", rep))
    diag.activity("team_book_merged", rows=rep["taken"], warnings=len(rep["both"]))
    return "merged"


def write_book(config_dir, settings=None):
    """Write the workbook from the cache. Returns "written"; "waiting" when Excel has it open; "unread" when it
    changed since the app last saw it and cannot be read. 4.56.2: a workbook that changed meanwhile is read first."""
    import bookmerge as BM
    import fieldrecipes as FR
    import prodrules as PRL
    import standardsbook as SB
    p = book_path(config_dir, settings)
    st = state(config_dir)
    seen = _stamp(p)
    if seen is not None and SB.newer(p):                    # 4.57.0: a newer format is never written over
        _said.append("The Global Standards workbook: " + __import__("bookshape").FORMAT_NEWER + " Your changes wait.")
        return "unread"
    why = SB.wrong_kind(p, "global") if seen is not None else None
    if why:                                                 # 4.59.0: the wrong kind is never written over
        _said.append("The Global Standards workbook: " + why + " Your changes wait.")
        return "unread"
    if seen is not None and _moved(p, st.get("book"), st.get("sha")):
        if _merge_book(config_dir, p, st, settings) == "unread":
            return "unread"
        st = state(config_dir)
        if _stamp(p) != seen:                               # it changed again while it was read: the next tick
            return "waiting"
    data = PRL.load(config_dir)
    SB.stamp_since(data["company"], st.get("rows") or {})        # Changed: the app, on the rows it changed
    try:
        import listsbook as LB                              # 4.7.1: the small lists as sheets
        SB.write(p, data["company"], FR.load(config_dir), st.get("own_cols") or {}, LB.load_all(config_dir),
                 keep_dir=config_dir, kind="Global Standards")   # 4.58.0: a copy first; 4.59.0: its Read me
    except PermissionError:
        st["dirty"], st["waiting"] = True, time.strftime("%Y-%m-%d %H:%M")
        _save_state(config_dir, st)
        return "waiting"
    company = SB.remember_cols(data["company"])
    global _reading
    _reading = True
    try:
        data["company"] = company
        PRL.save(config_dir, data)
    finally:
        _reading = False
    st.update(dirty=False, waiting="", book=_stamp(p), sha=_sha(p), written=time.strftime("%Y-%m-%d %H:%M"),
              rows=SB.row_hashes(company))
    _save_state(config_dir, st)
    BM.keep_base(config_dir, p)
    diag.activity("team_book_written")
    return "written"


def read_book(config_dir, settings=None, removed_answer=None, force=False):
    """Read the workbook into the cache when it changed. Returns {"read": bool, "changed": [(sheet, name)],
    "problems": [...], "question": [(sheet, key)] or [], "conflicts": [...]}."""
    import fieldrecipes as FR
    import prodrules as PRL
    import standardsbook as SB
    p = book_path(config_dir, settings)
    out = {"read": False, "changed": [], "problems": [], "question": [], "conflicts": SB.conflict_copies(p)}
    st = state(config_dir)
    now = _stamp(p)
    if now is None or (not force and now == st.get("book")):
        return out
    sha = _sha(p)
    if not force and sha == st.get("sha"):
        st["book"] = now
        _save_state(config_dir, st)
        return out
    book = SB.read(p)
    why = __import__("bookreadme").refused(book, "global")   # 4.59.0: the wrong kind is not read
    if why:
        book["problems"] = list(book["problems"]) + [why]
    if book["problems"]:
        out["problems"] = book["problems"]
        st["problems"] = book["problems"]
        st["book"] = now                                   # reported once; read again when it changes
        _save_state(config_dir, st)
        return out
    data = PRL.load(config_dir)
    answer = removed_answer or (st.get("answers") or {}).get("removed")
    res = SB.apply(data["company"], FR.load(config_dir), book, removed_answer=answer)
    global _reading
    _reading = True
    try:
        data["company"] = res["company"]
        PRL.save(config_dir, data)
        FR.save(config_dir, res["recipes"])
        import listsbook as LB                              # 4.7.1: the list sheets into each list's own file
        lists_read = LB.apply(config_dir, book)
        for sheet in lists_read:
            res["changed"].append((sheet, ""))
    finally:
        _reading = False
    st.update(book=now, sha=sha, problems=[], own_cols=res["own_cols"], read=time.strftime("%Y-%m-%d %H:%M"),
              rows=SB.row_hashes(res["company"]))
    if res["removed_cols"] and not answer:
        st["question"] = res["removed_cols"]
        out["question"] = res["removed_cols"]
    _save_state(config_dir, st)
    out.update(read=True, changed=res["changed"], problems=res["problems"])
    __import__("bookmerge").keep_base(config_dir, p)          # 4.56.2: what the next merge compares with
    diag.activity("team_book_read", n=len(res["changed"]))
    return out


def answer_removed(config_dir, how, settings=None):
    """The person's answer for a property column taken out of the workbook: "drop" takes it off every row, "keep" keeps
    the values (they come back as a column on the next write). Asked once; kept."""
    st = state(config_dir)
    st.setdefault("answers", {})["removed"] = how
    st["question"] = []
    _save_state(config_dir, st)
    r = read_book(config_dir, settings, removed_answer=how, force=True)
    write_book(config_dir, settings)
    return r


# ------------------------------------------------------------------ the Word files
LIBRARY = "Library files"
INDEX = "Library files index.csv"                       # 4.10.0: plain name, the app's kept name, the fingerprint
HASHED = re.compile(r"^(.+)_([0-9a-f]{10})(\.[A-Za-z0-9]+)$")


def _files(d):
    if not os.path.isdir(d):
        return set()
    return {f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and not f.startswith(("~$", ".")) and f != INDEX}


def _plain(stem, ext, taken):
    base = " ".join(stem.replace("_", " ").split()) or "Part"
    name, k = base + ext, 1
    while name.casefold() in taken:
        k += 1
        name = f"{base} ({k}){ext}"
    return name


def _library_names(a, b, st, last):
    """4.10.0: the library's kept files (Cover_ab12cd34ef.docx, named by their content) appear in the team library under
    plain names (Cover.docx; Cover (2).docx for the next). Returns [(the app's name, the team library's name)]."""
    nm = st.setdefault("names", {}).setdefault(LIBRARY, {})
    app, team = _files(a), _files(b)
    for an in list(nm):                                   # both files gone: the name is free again
        if an not in app and nm[an] not in team:
            nm.pop(an)
    taken = {v.casefold() for v in nm.values()} | {t.casefold() for t in team if t not in nm.values() and t not in app}
    for an in sorted(app - set(nm), key=lambda n: (os.path.getmtime(os.path.join(a, n)), n)):
        m = HASHED.match(an)
        tn = _plain(m.group(1), m.group(3), taken) if m else an
        if m and an in team and not os.path.exists(os.path.join(b, tn)):
            try:                                          # a 4.7 to 4.9 team library: the file takes its plain name
                os.replace(os.path.join(b, an), os.path.join(b, tn))
                if f"{LIBRARY}/{an}" in last:
                    last[f"{LIBRARY}/{tn}"] = last.pop(f"{LIBRARY}/{an}")
                team.discard(an); team.add(tn)
            except OSError:
                diag.swallowed()
                tn = an
        nm[an] = tn
        taken.add(tn.casefold())
    mapped = set(nm.values())
    for tn in team - mapped:                              # a file someone put in the team library: the app keeps it as named
        nm[tn] = tn
    return sorted(nm.items(), key=lambda p: p[1].casefold())


def _write_index(b, pairs):
    rows = [["Name", "Kept in the app as", "Fingerprint"]]
    for an, tn in pairs:
        m = HASHED.match(an)
        rows.append([tn, an, m.group(2) if m else ""])
    p = os.path.join(b, INDEX)
    import csv, io
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(rows)
    data = buf.getvalue().encode("utf-8-sig")
    try:
        with open(p, "rb") as f:
            if f.read() == data:
                return
    except OSError:
        pass
    try:
        os.makedirs(b, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    except OSError:
        diag.swallowed()


def sync_content(config_dir, settings=None):
    """Mirror the app's kept Word files and the team library's Content folders: a file changed on one side since the
    last sync is copied to the other; a file changed on both keeps the newer and is reported; nothing is deleted.
    Library files carry plain names in the team library (4.10.0). Returns {"in": [names], "out": [names], "both": [names]}
    with the team library's names."""
    base = folder(config_dir, settings)
    st = state(config_dir)
    last = st.setdefault("content", {})
    out = {"in": [], "out": [], "both": []}
    for rel, label in PAIRS:
        a, b = os.path.join(config_dir, rel), os.path.join(base, CONTENT, label)
        if label == LIBRARY:
            pairs = _library_names(a, b, st, last)
        else:
            pairs = [(n, n) for n in sorted(_files(a) | _files(b))]
        for an, tn in pairs:
            got = {"in": [], "out": [], "both": []}
            _mirror(os.path.join(a, an), os.path.join(b, tn), f"{label}/{tn}", last, got)
            for k in got:
                out[k] += [tn] * len(got[k])
        if label == LIBRARY and pairs:
            _write_index(b, pairs)
    _save_state(config_dir, st)
    if out["in"] or out["out"] or out["both"]:
        diag.activity("team_content_synced", n=len(out["in"]) + len(out["out"]) + len(out["both"]))
    return out


# ------------------------------------------------------------------ the suggestion rules' counts (4.10.0)
SCORES = "Suggestion scores"                            # Lists\Suggestion scores\<PC>.json: each PC writes only its own
SCORES_FORMAT = 1                                       # formats.py "suggestion scores"


def _read_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, sort_keys=True)
    os.replace(tmp, p)


def _add(into, more):
    for ph, (k, n) in (more or {}).items():
        t = into.setdefault(ph, [0, 0])
        t[0] += int(k or 0); t[1] += int(n or 0)
    return into


def sync_scores(config_dir, ws=None, settings=None):
    """How often each team suggestion rule was kept and not right, summed over every effort on every PC that shares
    the team library: this PC's efforts in the config folder, this PC's sum in Lists, Suggestion scores, <PC>.json, and
    the sum of every PC's file for the workbook. Returns {phrase: [kept, not right]}."""
    import platform
    import re as _re
    import suggestrules as SR
    lp = os.path.join(config_dir, "suggestion_scores.json")
    loc = (_read_json(lp, {}) or {}).get("efforts") or {}
    if ws is not None and getattr(ws, "root", ""):
        t = SR.tally(ws)
        if loc.get(ws.root) != t:
            loc[ws.root] = t
            _write_json(lp, {"format": SCORES_FORMAT, "efforts": loc})
    mine = {}
    for t in loc.values():
        _add(mine, t)
    d = os.path.join(folder(config_dir, settings), LISTS, SCORES)
    pc = (_re.sub(r"[^A-Za-z0-9_-]+", "_", platform.node()) or "this-PC") + ".json"
    have = (_read_json(os.path.join(d, pc), None) or {}).get("scores")
    if have != mine and (mine or have is not None):
        try:
            _write_json(os.path.join(d, pc), {"format": SCORES_FORMAT, "scores": mine})
        except OSError:
            diag.swallowed()
    sums = {}
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.lower().endswith(".json"):
            _add(sums, (_read_json(os.path.join(d, f), {}) or {}).get("scores"))
    st = state(config_dir)
    if st.get("score_sums", {}) != sums:
        st["score_sums"] = sums
        st["dirty"] = True                                   # the workbook's counts follow
        _save_state(config_dir, st)
    return sums


def score_sums(config_dir):
    return state(config_dir).get("score_sums") or {}


# ------------------------------------------------------------------ the large lists (4.7.1)
LISTS = "Lists"


def _mirror(a, b, key, last, out):
    """One file kept the same in two places by the content rules (changed on one side: copied; both: the newer)."""
    sa = _sha(a) if os.path.isfile(a) else None
    sb = _sha(b) if os.path.isfile(b) else None
    was = last.get(key)
    try:
        if sa and not sb:
            os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(a, b); out["out"].append(key); last[key] = sa
        elif sb and not sa:
            os.makedirs(os.path.dirname(a), exist_ok=True); shutil.copy2(b, a); out["in"].append(key); last[key] = sb
        elif sa and sa == sb:
            last[key] = sa
        elif sa and sb and sb != was and sa == was:
            shutil.copy2(b, a); out["in"].append(key); last[key] = sb
        elif sa and sb and sa != was and sb == was:
            shutil.copy2(a, b); out["out"].append(key); last[key] = sa
        elif sa and sb:
            newer, older = (a, b) if os.path.getmtime(a) >= os.path.getmtime(b) else (b, a)
            shutil.copy2(newer, older); out["both"].append(key); last[key] = _sha(newer)
    except OSError:
        diag.swallowed()


def sync_lists(config_dir, settings=None):
    """The master acronym list (Lists\\Acronyms.csv, the same file as Stationkeeper Data\\acronym_database.csv) and each
    custom dictionary as Lists\\Dictionaries\\<name>.dic, both ways. Returns {"in", "out", "both", "dics"}."""
    import listsbook as LB
    base = os.path.join(folder(config_dir, settings), LISTS)
    st = state(config_dir)
    last = st.setdefault("content", {})
    out = {"in": [], "out": [], "both": [], "dics": []}
    data_dir = os.path.dirname(os.path.abspath(config_dir))
    _mirror(os.path.join(data_dir, "acronym_database.csv"), os.path.join(base, "Acronyms.csv"), "Lists/Acronyms.csv", last, out)
    dd = os.path.join(base, "Dictionaries")
    js = os.path.join(config_dir, "custom_dictionaries.json")
    jsha = _sha(js) if os.path.isfile(js) else ""
    dstate = st.setdefault("dics", {})
    files = {f: _sha(os.path.join(dd, f)) for f in (os.listdir(dd) if os.path.isdir(dd) else []) if f.lower().endswith(".dic")}
    global _reading
    if files and files != dstate.get("files"):                       # someone changed a .dic: the dictionaries follow
        _reading = True
        try:
            out["dics"] = LB.read_dic_files(config_dir, dd)
        finally:
            _reading = False
        jsha = _sha(js) if os.path.isfile(js) else ""
    elif jsha and jsha != dstate.get("json"):                       # the app changed a dictionary: the files follow
        LB.dic_files(config_dir, dd)
    files = {f: _sha(os.path.join(dd, f)) for f in (os.listdir(dd) if os.path.isdir(dd) else []) if f.lower().endswith(".dic")}
    dstate.update(json=jsha, files=files)
    _save_state(config_dir, st)
    return out


# ------------------------------------------------------------------ the tick
def tick(config_dir, settings=None):
    """On opening and every few minutes: the first run writes the files (nothing deleted); after that, what the app
    changed is written and what people changed is read. Returns what happened, in words, and the details."""
    p = book_path(config_dir, settings)
    said, res = [], {}
    try:
        if not os.path.isfile(p):
            if write_book(config_dir, settings) == "written":
                said.append("The Global Standards workbook was written in the team library.")
        elif state(config_dir).get("dirty"):
            got = write_book(config_dir, settings)
            if got == "waiting" and state(config_dir).get("waiting"):
                said.append("The Global Standards workbook is open in Excel: your changes are written when it closes.")
        else:
            if state(config_dir).get("book") == _stamp(p) and not os.path.isfile(
                    __import__("bookmerge").base_path(config_dir, p)):
                __import__("bookmerge").keep_base(config_dir, p)   # 4.56.2: the first base, from a workbook not changed since
            res = read_book(config_dir, settings)
            if res.get("read") and res.get("changed"):
                said.append(f"Read from the Global Standards workbook: {len(res['changed'])} change(s).")
            for pr in res.get("problems") or []:
                said.append(pr)
            if res.get("conflicts"):
                said.append("A copy of the workbook from another PC is in the team library: " + ", ".join(res["conflicts"])
                            + ". It was not read; keep the one you want.")
        said += take_said()
        ls = sync_lists(config_dir, settings)                   # 4.7.1
        if ls["in"] or ls["dics"]:
            said.append("Read from the team library's lists: " + ", ".join([os.path.basename(x) for x in ls["in"]] + ls["dics"]) + ".")
        c = sync_content(config_dir, settings)
        if c["in"]:
            said.append(f"{len(c['in'])} Word file(s) changed in the team library were brought in.")
        if c["both"]:
            said.append("Changed in both places, the newer kept: " + ", ".join(c["both"][:3]))
    except Exception:  # noqa: BLE001  the window must never stop over the library
        diag.swallowed()
    res["said"] = said
    return res


# ------------------------------------------------------------------ one effort's workbook
OLD_EFFORT_BOOK = "{} Effort Formatting.xlsx"   # its name from 4.7.0 to 4.58: renamed once (4.59.0)


def effort_kind(effort_path):
    """4.59.0: what an effort's workbook says it is: Program Standards for a program's (its list is <name>_Program_List),
    Effort Standards for an effort's."""
    import bookreadme as BR
    return BR.PROGRAM if str(effort_path or "").endswith(__import__("programs").LIST_TAIL) else BR.EFFORT


def effort_book_path(effort_path, effort_name, config_dir=None):
    """The effort's (or program's) workbook (4.59.0: "<name> Effort Standards.xlsx", "<name> Program Standards.xlsx").
    One under its earlier name is renamed once, with the copy the next merge compares with (config_dir); while Excel
    has it open it is used as it is and renamed the next time. With both there, the new name is used."""
    d = os.path.dirname(os.path.abspath(effort_path))
    new = os.path.join(d, f"{effort_name} {effort_kind(effort_path)}.xlsx")
    old = os.path.join(d, OLD_EFFORT_BOOK.format(effort_name))
    if not os.path.isfile(new) and os.path.isfile(old):
        try:
            os.replace(old, new)
        except OSError:
            return old
        diag.activity("effort_book_renamed")
        if config_dir:
            import bookmerge as BM
            try:
                if os.path.isfile(BM.base_path(config_dir, old)):
                    os.replace(BM.base_path(config_dir, old), BM.base_path(config_dir, new))
            except OSError:
                diag.swallowed()
    return new


def _volume_names(config_dir=None):
    """{volume profile id: its name}, for an effort workbook's Volume column (4.10.0)."""
    import prodrules as PRL
    if config_dir is None:
        import app_gui as A
        config_dir = A.CONFIG_DIR
    try:
        return {t["id"]: (t.get("name") or t["id"]) for t in PRL.load(config_dir).get("types") or []}
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return {}


def _effort_cfg(config_dir=None):
    if config_dir is None:
        import app_gui as A
        config_dir = A.CONFIG_DIR
    return config_dir


def _effort_write(ws, p, config_dir=None, kind=None, owner=None):
    """Write the effort's layers to the workbook at p (the real one, or a temp one for a merge). kind, owner (4.59.0):
    what its Read me tab says."""
    import effortformat as EFM
    import standardsbook as SB
    lay = EFM.layer(ws)
    names = _volume_names(config_dir)
    ov = EFM.eff_of(ws).get("over_vol") or {}
    vols = sorted(((names.get(t, t), EFM.layer(ws, t)) for t in ov), key=lambda x: x[0].casefold())
    return SB.write(p, lay, None, (ws.get("effort_book") or {}).get("own_cols") or {}, volumes=vols,
                    keep_dir=_effort_cfg(config_dir),      # 4.58.0: a copy first, before the plain names
                    kind=kind, owner=owner)


def write_effort_book(ws, effort_path, effort_name, config_dir=None):
    """The effort's own changes as a workbook: only what it sets; a blank means the default. Rows for every volume have
    a blank Volume; a change for one volume kind carries its name (4.10.0). 4.56.2: a workbook that changed since the
    app last read or wrote it is read first and merged (bookmerge); one that cannot be read is not written over."""
    import bookmerge as BM
    cfg = _effort_cfg(config_dir)
    p = effort_book_path(effort_path, effort_name, cfg)
    kind, owner = effort_kind(effort_path), effort_name
    eb = dict(ws.get("effort_book") or {})
    seen = _stamp(p)
    import standardsbook as SB
    if seen is not None and SB.newer(p):                    # 4.57.0: a newer format is never written over
        _said.append("This effort's formatting workbook: " + __import__("bookshape").FORMAT_NEWER + " Your changes wait.")
        return "unread"
    why = SB.wrong_kind(p, "effort") if seen is not None else None
    if why:                                                 # 4.59.0: the wrong kind is never written over
        _said.append("This effort's formatting workbook: " + why + " Your changes wait.")
        return "unread"
    if seen is not None and _moved(p, eb.get("stamp"), eb.get("sha")):
        theirs = SB.read(p)
        if theirs["problems"]:
            _said.extend("This effort's formatting workbook changed and could not be read, so your changes are not "
                         "written over it yet: " + x for x in theirs["problems"])
            return "unread"
        merged, rep = BM.merge(_base(cfg, p), _mine(lambda t: _effort_write(ws, t, config_dir, kind, owner)), theirs)
        _changed, _problems, own = _apply_effort(ws, merged, config_dir)
        eb = dict(ws.get("effort_book") or {})
        eb["own_cols"] = own
        ws.set("effort_book", eb)
        _said.extend(BM.said("This effort's formatting workbook", rep))
        diag.activity("effort_book_merged", rows=rep["taken"], warnings=len(rep["both"]))
        if _stamp(p) != seen:
            return "waiting"
    try:
        _effort_write(ws, p, config_dir, kind, owner)
    except PermissionError:
        return "waiting"
    eb = dict(ws.get("effort_book") or {})
    eb.update(stamp=_stamp(p), sha=_sha(p), dirty=False)
    ws.set("effort_book", eb)
    BM.keep_base(cfg, p)
    return "written"


def _apply_effort(ws, book, config_dir=None):
    """A reading of the effort's workbook into its layers. Returns (changed, problems, the columns people added)."""
    import effortformat as EFM
    import standardsbook as SB
    names = _volume_names(config_dir)
    by_name = {v.casefold(): k for k, v in names.items()}
    had = [names.get(t, t) for t in (EFM.eff_of(ws).get("over_vol") or {})]
    changed, problems, own = [], list(book.get("problems") or []), {}
    global _reading
    _reading = True
    try:
        for lab, part in sorted(SB.split_volumes(book, had).items()):
            tid = None
            if lab:
                tid = by_name.get(lab.casefold()) or (lab if lab in names else None)
                if tid is None:
                    problems.append(f"Volume \"{lab}\" is not a volume kind in the Global Standards; "
                                    "its rows were not read.")
                    continue
            part["problems"] = []
            res = SB.apply(EFM.layer(ws, tid), None, part, removed_answer="drop")
            lay = res["company"]
            lay.pop("book_meta", None)
            EFM.set_layer(ws, lay, tid)
            changed += [(sh, f"{n} ({lab})" if lab else n) for sh, n in res["changed"]]
            problems += [x for x in res["problems"] if x not in problems]
            own = own or res["own_cols"]
    finally:
        _reading = False
    return changed, problems, own


def read_effort_book(ws, effort_path, effort_name, force=False, config_dir=None):
    """The effort's workbook into its layer when it changed. Returns the changes, or None when nothing was read."""
    import standardsbook as SB
    p = effort_book_path(effort_path, effort_name, _effort_cfg(config_dir))
    eb = dict(ws.get("effort_book") or {})
    now = _stamp(p)
    if now is None or (not force and now == eb.get("stamp")):
        return None
    sha = _sha(p)
    if not force and sha == eb.get("sha"):
        eb["stamp"] = now
        ws.set("effort_book", eb)
        return None
    book = SB.read(p)
    why = __import__("bookreadme").refused(book, "effort")   # 4.59.0: the wrong kind is not read
    if book["problems"] or why:
        eb["stamp"] = now
        ws.set("effort_book", eb)
        return {"changed": [], "problems": book["problems"] or [why]}
    changed, problems, own = _apply_effort(ws, book, config_dir)
    eb.update(stamp=now, sha=sha, own_cols=own)
    ws.set("effort_book", eb)
    __import__("bookmerge").keep_base(_effort_cfg(config_dir), p)   # 4.56.2: what the next merge compares with
    return {"changed": changed, "problems": problems}


def effort_tick(ws, effort_path, effort_name):
    """The effort's workbook: written the first time and after the app changed the effort's formatting, read after
    people changed it."""
    if ws is None or not effort_path:
        return None
    try:
        p = effort_book_path(effort_path, effort_name, _effort_cfg())
        eb = ws.get("effort_book") or {}
        if not os.path.isfile(p) or eb.get("dirty"):
            return write_effort_book(ws, effort_path, effort_name)
        import bookmerge as BM
        if eb.get("stamp") == _stamp(p) and not os.path.isfile(BM.base_path(_effort_cfg(), p)):
            BM.keep_base(_effort_cfg(), p)                    # 4.56.2: the first base, from a workbook not changed since
        return read_effort_book(ws, effort_path, effort_name)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def mark_effort_dirty(ws):
    if ws is None or _reading:
        return
    eb = dict(ws.get("effort_book") or {})
    eb["dirty"] = True
    ws.set("effort_book", eb)
