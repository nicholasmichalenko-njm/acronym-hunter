"""The team library as files (4.7.0; claude/stationkeeper-team-library-files-decisions-2026-11-10.md, decisions 1 to 4).

The files are the truth; the app keeps a cache it rebuilds from them:
- Company Standards.xlsx: the values of the Company Standards (Default) and the field recipes (standardsbook). The
  app's production_standards.json and field_recipes.json are its cache.
- Content\\: the Word files the standards and the library keep (covers, back covers, title pages, Quick Parts sources,
  header and footer designs), one folder each for the standards' parts and the library's kept files. Edit them in Word;
  the app's copies follow. A file the app keeps (Bring in, a new cover) appears there.
- <effort> Effort Formatting.xlsx, beside the effort's list: the same sheets with only that effort's changes (a blank
  cell means the Company Standards (Default) value).

Where: Stationkeeper Data\\Team library unless Settings points it at another folder (a SharePoint library synced to
each PC, so the team shares one). Updates never touch it.

How the two ways meet: the app writes the workbook after its own changes (marked to write, then written on the next
tick, so a burst of edits writes once) and reads it when its size or time changed. Excel keeps the file locked while
it is open: the app waits and says so. A workbook that cannot be read is reported and skipped; the last good reading
stays. A sync conflict copy ("Company Standards-PCNAME.xlsx") is reported, never read. Nothing is deleted in the move:
the first run writes the files from the cache, and the JSON stays. Nothing leaves the PC."""
import hashlib, json, os, shutil, time

import diag

BOOK = "Company Standards.xlsx"
CONTENT = "Content"
STATE = "team_library_state.json"
PAIRS = (("production_parts", "Standards parts"), (os.path.join("template_library", "sources"), "Library files"))
_reading = False


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
    return os.path.join(folder(config_dir, settings), BOOK)


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
def write_book(config_dir, settings=None):
    """Write the workbook from the cache. Returns "written", or "waiting" when Excel has it open."""
    import fieldrecipes as FR
    import prodrules as PRL
    import standardsbook as SB
    p = book_path(config_dir, settings)
    st = state(config_dir)
    data = PRL.load(config_dir)
    SB.stamp_since(data["company"], st.get("rows") or {})        # Changed: the app, on the rows it changed
    try:
        import listsbook as LB                              # 4.7.1: the small lists as sheets
        SB.write(p, data["company"], FR.load(config_dir), st.get("own_cols") or {}, LB.load_all(config_dir))
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
        for sheet in LB.apply(config_dir, book):
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
def sync_content(config_dir, settings=None):
    """Mirror the app's kept Word files and the team library's Content folders, by file name: a file changed on one
    side since the last sync is copied to the other; a file changed on both keeps the newer and is reported; nothing
    is deleted. Returns {"in": [names], "out": [names], "both": [names]}."""
    base = folder(config_dir, settings)
    st = state(config_dir)
    last = st.setdefault("content", {})
    out = {"in": [], "out": [], "both": []}
    for rel, label in PAIRS:
        a, b = os.path.join(config_dir, rel), os.path.join(base, CONTENT, label)
        names = set()
        for d in (a, b):
            if os.path.isdir(d):
                names |= {f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and not f.startswith(("~$", "."))}
        for n in sorted(names):
            pa, pb = os.path.join(a, n), os.path.join(b, n)
            key = f"{label}/{n}"
            sa = _sha(pa) if os.path.isfile(pa) else None
            sb = _sha(pb) if os.path.isfile(pb) else None
            was = last.get(key)
            try:
                if sa and not sb:
                    os.makedirs(b, exist_ok=True); shutil.copy2(pa, pb); out["out"].append(n); last[key] = sa
                elif sb and not sa:
                    os.makedirs(a, exist_ok=True); shutil.copy2(pb, pa); out["in"].append(n); last[key] = sb
                elif sa == sb:
                    last[key] = sa
                elif sb != was and sa == was:
                    shutil.copy2(pb, pa); out["in"].append(n); last[key] = sb
                elif sa != was and sb == was:
                    shutil.copy2(pa, pb); out["out"].append(n); last[key] = sa
                else:                                            # changed on both sides: the newer wins, said
                    newer, older = (pa, pb) if os.path.getmtime(pa) >= os.path.getmtime(pb) else (pb, pa)
                    shutil.copy2(newer, older); out["both"].append(n); last[key] = _sha(newer)
            except OSError:
                diag.swallowed()
    _save_state(config_dir, st)
    if out["in"] or out["out"] or out["both"]:
        diag.activity("team_content_synced", n=len(out["in"]) + len(out["out"]) + len(out["both"]))
    return out


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
                said.append("The Company Standards workbook was written in the team library.")
        elif state(config_dir).get("dirty"):
            got = write_book(config_dir, settings)
            if got == "waiting":
                said.append("The Company Standards workbook is open in Excel: your changes are written when it closes.")
        else:
            res = read_book(config_dir, settings)
            if res.get("read") and res.get("changed"):
                said.append(f"Read from the Company Standards workbook: {len(res['changed'])} change(s).")
            for pr in res.get("problems") or []:
                said.append(pr)
            if res.get("conflicts"):
                said.append("A copy of the workbook from another PC is in the team library: " + ", ".join(res["conflicts"])
                            + ". It was not read; keep the one you want.")
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
def effort_book_path(effort_path, effort_name):
    return os.path.join(os.path.dirname(os.path.abspath(effort_path)), f"{effort_name} Effort Formatting.xlsx")


def write_effort_book(ws, effort_path, effort_name):
    """The effort's own changes (every volume) as a workbook: only what it sets; a blank means the default."""
    import effortformat as EFM
    import standardsbook as SB
    p = effort_book_path(effort_path, effort_name)
    lay = EFM.layer(ws)
    try:
        SB.write(p, lay, None, (ws.get("effort_book") or {}).get("own_cols") or {})
    except PermissionError:
        return "waiting"
    eb = dict(ws.get("effort_book") or {})
    eb.update(stamp=_stamp(p), sha=_sha(p), dirty=False)
    ws.set("effort_book", eb)
    return "written"


def read_effort_book(ws, effort_path, effort_name, force=False):
    """The effort's workbook into its layer when it changed. Returns the changes, or None when nothing was read."""
    import effortformat as EFM
    import standardsbook as SB
    p = effort_book_path(effort_path, effort_name)
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
    if book["problems"]:
        eb["stamp"] = now
        ws.set("effort_book", eb)
        return {"changed": [], "problems": book["problems"]}
    res = SB.apply(EFM.layer(ws), None, book, removed_answer="drop")
    lay = res["company"]
    lay.pop("book_meta", None)
    global _reading
    _reading = True
    try:
        EFM.set_layer(ws, lay)
    finally:
        _reading = False
    eb.update(stamp=now, sha=sha, own_cols=res["own_cols"])
    ws.set("effort_book", eb)
    return {"changed": res["changed"], "problems": res["problems"]}


def effort_tick(ws, effort_path, effort_name):
    """The effort's workbook: written the first time and after the app changed the effort's formatting, read after
    people changed it."""
    if ws is None or not effort_path:
        return None
    try:
        p = effort_book_path(effort_path, effort_name)
        eb = ws.get("effort_book") or {}
        if not os.path.isfile(p) or eb.get("dirty"):
            return write_effort_book(ws, effort_path, effort_name)
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
