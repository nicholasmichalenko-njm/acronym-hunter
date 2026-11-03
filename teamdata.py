"""Our data (3.22.0): one file that carries the team's foundational data, the things used the same way in every effort,
so one import sets up a PC.

Stationkeeper Data (.skdata) holds what QA/QC and template building run on: the master acronym list, custom
dictionaries, banned and avoided phrases, Production Standards with their covers, back covers and Quick Parts sources,
and the template library; and the team's setup lists: the author list, Review bins, suggestion rules, team topics and
markings, gate goals, stages and roles, document types, the folder plan, the matrix design, logos, role layouts, the
post-submission checklist, schedule defaults, compliance words, offerings, OCR fixes and section word synonyms.

Nothing about one effort goes in it: no Wall of Truth, no matrix, no captures, no effort record. An effort travels on its
own as an effort package (Settings > Export the full effort, Import effort package).

It is the team's data, not part of the program: labeled so inside (a README and the manifest) and out (the file name),
never written into a folder that git tracks, and shared only through the approved SharePoint folder. Knowledge Packs
(trained models and learned counts) stay separate.

Import shows what each part adds before anything is written, keeps a copy of every file it touches, and Undo puts them
back. Every part merges add-only: this PC's own entries, edits and Exclude choices win. The file has a format version
and each part its own; a newer Stationkeeper reads every older file, and a part this version does not know is reported
and left in the file, never dropped. Nothing leaves the PC."""
import datetime, getpass, hashlib, io, json, os, platform, shutil, zipfile

FORMAT = "sk-data-1"
EXT = ".skdata"
MANIFEST = "stationkeeper_data.json"
README = "README - TEAM DATA, NOT FOR GITHUB.txt"
MAX_BYTES = 64 * 1024 * 1024
BACKUPS = "data_backups"
LABEL = ("Stationkeeper Data: the team's own data (acronyms, dictionaries, phrases, standards, templates and team lists). "
         "Not part of the program. Never put it on GitHub. Share it only through the approved SharePoint folder.")
TEAM_PARTS = ("authors", "design", "goals", "process", "doctypes", "folders", "logos", "roles", "markings", "topics",
              "postsub", "access", "suggest", "bins")
# key: (name, version, [config-relative files], [config-relative folders], data-root files)
PARTS = {
    "acronyms": ("Master acronym list", 1, [], [], ["acronym_database.csv"]),
    "dictionaries": ("Custom dictionaries", 1, ["custom_dictionaries.json"], [], []),
    "banned": ("Banned and avoided phrases", 1, ["banned_words.csv"], [], []),
    "standards": ("Production Standards, with their covers, back covers and Quick Parts", 1, ["production_standards.json"],
                  ["production_parts"], []),
    "library": ("Template library", 1, [], ["template_library"], []),
    "schedule": ("Schedule defaults", 1, ["schedule_defaults.json"], [], []),
    "cwords": ("Compliance words", 1, ["compliance_words.json"], [], []),
    "offerings": ("Offerings catalog", 1, ["offerings.csv"], [], []),
    "ocr": ("OCR fixes and ignore list", 1, ["ocr_corrections.csv", "ocr_ignore.csv"], [], []),
    "synonyms": ("Section word synonyms", 1, ["placement_synonyms.csv"], [], []),
}


def _team_parts():
    import teampack as TP
    out = {}
    for p in TEAM_PARTS:
        files = [TP.FILES[p]] if p in TP.FILES else []
        folders = ["brand"] if p == "logos" else []
        out[p] = (TP.PART_NAMES[p], 1, files, folders, [])
    return out


def all_parts():
    d = dict(PARTS)
    d.update(_team_parts())
    return d


def _data_dir(config_dir):
    return os.path.dirname(os.path.abspath(config_dir))


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def in_git_folder(path):
    """True when the path sits inside a folder git tracks (the data file never goes there)."""
    p = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path) or ".")
    while True:
        if os.path.exists(os.path.join(p, ".git")):
            return True
        up = os.path.dirname(p)
        if up == p:
            return False
        p = up


def file_name(when=None):
    return f"Stationkeeper Data - team data {(when or datetime.datetime.now()).strftime('%Y-%m-%d %H%M')}{EXT}"


def _members(config_dir, key, spec):
    """{member name in the file: local path} for one part."""
    _name, _v, files, folders, droot = spec
    out = {}
    for f in files:
        p = os.path.join(config_dir, f)
        if os.path.isfile(p):
            out["config/" + f] = p
    for fo in folders:
        base = os.path.join(config_dir, fo)
        if os.path.isdir(base):
            for root, dirs, names in os.walk(base):
                dirs[:] = [x for x in dirs if not x.startswith("_")]      # work folders (a collection in progress) stay
                for n in names:
                    if n.endswith(".tmp"):
                        continue
                    p = os.path.join(root, n)
                    out["config/" + os.path.relpath(p, config_dir).replace(os.sep, "/")] = p
    for f in droot:
        p = os.path.join(_data_dir(config_dir), f)
        if key == "acronyms":
            try:
                import app_gui
                p = app_gui.DB_FILE
            except Exception:                                   # noqa: BLE001  the program's own path when it is loaded
                pass
        if os.path.isfile(p):
            out["data/" + f] = p
    return out


def available(config_dir):
    """{part: its name and how many files} for every part this PC has something in."""
    out = {}
    for k, spec in all_parts().items():
        m = _members(config_dir, k, spec)
        if m:
            out[k] = f"{spec[0]} ({len(m)} file{'s' if len(m) != 1 else ''})"
    return out


def export(config_dir, out_path, parts=None, notes=""):
    """Writes the data file. parts: which to carry (every one with data when None). Refuses a folder git tracks.
    Returns the manifest."""
    if in_git_folder(out_path):
        raise ValueError("That folder is tracked by git. The team's data never goes there: pick a folder outside the code.")
    specs = all_parts()
    keys = [k for k in specs if (parts is None or k in parts)]
    members, plist = {}, {}
    for k in keys:
        m = _members(config_dir, k, specs[k])
        if not m:
            continue
        for name, p in m.items():
            with open(p, "rb") as f:
                members[name] = f.read()
        plist[k] = {"name": specs[k][0], "v": specs[k][1], "files": sorted(m)}
    import app_gui
    now = datetime.datetime.now()
    man = {"format": FORMAT, "label": LABEL, "created": now.strftime("%Y-%m-%d %H:%M"), "created_by": getpass.getuser(),
           "computer": platform.node(), "app_version": app_gui.APP_VERSION, "notes": (notes or "").strip()[:2000],
           "parts": plist, "files": {n: {"sha256": _sha(b), "bytes": len(b)} for n, b in members.items()}}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = out_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(README, LABEL + "\n\nMade " + man["created"] + " with Stationkeeper " + man["app_version"] +
                   ". Parts: " + ", ".join(p["name"] for p in plist.values()) + ".\n")
        z.writestr(MANIFEST, json.dumps(man, indent=1, ensure_ascii=False))
        for n, b in members.items():
            z.writestr(n, b)
    os.replace(tmp, out_path)
    return man


def _safe_member(n):
    return n and not n.startswith(("/", "\\")) and ".." not in n.replace("\\", "/").split("/") and ":" not in n \
        and n.startswith(("config/", "data/"))


def read(path):
    """(manifest, {member: bytes}) after checking every member; ValueError for a file that is not sound team data."""
    with zipfile.ZipFile(path) as z:
        names = {e.filename for e in z.infolist() if not e.is_dir()}
        if MANIFEST not in names:
            raise ValueError("Not a Stationkeeper Data file (its manifest is missing).")
        man = json.loads(z.read(MANIFEST).decode("utf-8"))
        fmt = str(man.get("format", ""))
        if not fmt.startswith("sk-data-"):
            raise ValueError("Not a Stationkeeper Data file.")
        data = {}
        for n, meta in (man.get("files") or {}).items():
            if not _safe_member(n) or n not in names:
                raise ValueError(f"The file lists a member it should not hold: {n}")
            info = z.getinfo(n)
            if info.file_size > MAX_BYTES:
                raise ValueError(f"{n} is too large")
            b = z.read(n)
            if _sha(b) != meta.get("sha256"):
                raise ValueError(f"{n} does not match its fingerprint: the file is damaged or was changed")
            data[n] = b
        extra = names - set(data) - {MANIFEST, README}
        if extra:
            raise ValueError("The file holds members its manifest does not name")
    return man, data


def _local_path(config_dir, member):
    if member.startswith("data/"):
        if member == "data/acronym_database.csv":
            try:
                import app_gui
                return app_gui.DB_FILE
            except Exception:                                   # noqa: BLE001
                pass
        return os.path.join(_data_dir(config_dir), member[5:])
    return os.path.join(config_dir, member[7:])


def preview(config_dir, man, data):
    """[{"key", "name", "state", "said", "known"}] for each part in the file: new here, the same, adds what is missing, or
    not known to this version (kept in the file, not imported)."""
    specs = all_parts()
    out = []
    for k, p in (man.get("parts") or {}).items():
        known = k in specs and int(p.get("v", 1)) <= specs[k][1]
        if not known:
            out.append({"key": k, "name": p.get("name", k), "state": "unknown", "known": False,
                        "said": "Made by a newer Stationkeeper: kept in the file, not imported by this version"})
            continue
        files = [f for f in p.get("files", []) if f in data]
        here = [f for f in files if os.path.isfile(_local_path(config_dir, f))]
        same = [f for f in here if open(_local_path(config_dir, f), "rb").read() == data[f]]
        if len(same) == len(files):
            state, said = "same", "Already the same on this PC"
        elif not here:
            state, said = "new", f"New on this PC ({len(files)} file{'s' if len(files) != 1 else ''})"
        else:
            state, said = "merge", "Adds what this PC does not have; this PC's own entries and edits stay"
        out.append({"key": k, "name": specs[k][0], "state": state, "said": said, "known": True})
    return out


def _backup(config_dir, members):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")         # two imports in one second keep two backups
    folder = os.path.join(config_dir, BACKUPS, stamp)
    os.makedirs(folder, exist_ok=True)
    kept, absent = [], []
    for m in members:
        p = _local_path(config_dir, m)
        if os.path.isfile(p):
            dst = os.path.join(folder, m.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(p, dst)
            kept.append(m)
        else:
            absent.append(m)
    with open(os.path.join(folder, "kept.json"), "w", encoding="utf-8") as f:
        json.dump({"kept": kept, "absent": absent}, f, indent=1)
    return folder


def _write(path, b):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "wb") as f:
        f.write(b)
    os.replace(path + ".tmp", path)


def _merge_files(config_dir, files, data):
    """New files are written; files this PC already has stay (used for folders of content-named files and settings
    files that have no add-only merge)."""
    n = 0
    for m in files:
        p = _local_path(config_dir, m)
        if not os.path.isfile(p):
            _write(p, data[m]); n += 1
    return n


def _merge_csv_rows(path, b):
    """Add-only by the first column (casefolded): rows this file does not have are added; this PC's rows stay. A file
    this PC does not have is written as it is. Returns how many rows were added."""
    import csv
    if not os.path.isfile(path):
        _write(path, b)
        return max(0, len(b.decode("utf-8-sig", "replace").splitlines()) - 1)
    with open(path, encoding="utf-8-sig", newline="") as f:
        mine = list(csv.reader(f))
    theirs = list(csv.reader(io.StringIO(b.decode("utf-8-sig", "replace"))))
    if not theirs:
        return 0
    if not mine:
        _write(path, b)
        return len(theirs) - 1
    have = {r[0].strip().casefold() for r in mine[1:] if r}
    add = [r for r in theirs[1:] if r and r[0].strip() and r[0].strip().casefold() not in have]
    if add:
        out = io.StringIO()
        csv.writer(out, lineterminator="\n").writerows(mine + add)
        _write(path, out.getvalue().encode("utf-8"))
    return len(add)


def _merge_dictionaries(config_dir, b):
    import customdict as CD
    st = CD.Store(config_dir)
    theirs = [d for d in (json.loads(b.decode("utf-8")) or {}).get("dicts", []) if isinstance(d, dict) and d.get("name")]
    added_d = added_w = 0
    for d in theirs:
        mine = next((x for x in st.dicts if x["name"].casefold() == d["name"].casefold()), None)
        if mine is None:
            st.dicts.append({"id": d.get("id") or d["name"], "name": d["name"], "words": CD.sort_words(d.get("words", [])),
                             "created": d.get("created", ""), "changed": d.get("changed", ""), "exports": []})
            added_d += 1
        else:
            have = {w.casefold() for w in mine["words"]}
            new = [w for w in d.get("words", []) if w.casefold() not in have]
            if new:
                mine["words"] = CD.sort_words(mine["words"] + new); added_w += len(new)
    st.save()
    return f"{added_d} dictionar{'ies' if added_d != 1 else 'y'} added, {added_w} word(s) added to ones you have"


def _merge_standards(config_dir, b):
    import prodrules as PRL
    theirs_raw = json.loads(b.decode("utf-8")) or {}
    p = os.path.join(config_dir, PRL.FILE)
    if not os.path.isfile(p):
        _write(p, b)
        return "the team's Production Standards written (this PC had none)"
    mine = PRL.load(config_dir)
    tmpd = os.path.join(config_dir, BACKUPS, "_theirs")
    os.makedirs(tmpd, exist_ok=True)
    _write(os.path.join(tmpd, PRL.FILE), b)
    theirs = PRL.load(tmpd)
    shutil.rmtree(tmpd, ignore_errors=True)
    said = []
    ids = {t["id"] for t in mine["types"]}
    names = {t["name"].casefold() for t in mine["types"]}
    new_t = [t for t in theirs["types"] if t["id"] not in ids and t.get("name", "").casefold() not in names]
    mine["types"] += new_t
    eids = {e["id"] for e in mine["effort_types"]}
    enames = {e["name"].casefold() for e in mine["effort_types"]}
    new_e = [e for e in theirs["effort_types"] if e["id"] not in eids and e.get("name", "").casefold() not in enames]
    valid = {t["id"] for t in mine["types"]}
    for e in new_e:
        e["profiles"] = [x for x in e.get("profiles", []) if x in valid] or [mine["default"]]
    mine["effort_types"] += new_e
    said.append(f"{len(new_t)} profile(s) and {len(new_e)} effort type(s) added")
    if not PRL.diff(mine["company"], PRL.COMPANY) and (theirs_raw.get("company") or {}):
        mine["company"] = theirs["company"]
        said.append("the team standard taken (this PC had not changed its own)")
    elif theirs_raw.get("company"):
        said.append("this PC's team standard kept")
    PRL.save(config_dir, mine)
    return "; ".join(said)


def install(config_dir, man, data, parts=None, who=None):
    """Imports the chosen parts (every known one when None), add-only. Keeps a copy of every file it touches first.
    Returns [(part key, what it did)]."""
    specs = all_parts()
    plan = {k: p for k, p in (man.get("parts") or {}).items()
            if (parts is None or k in parts) and k in specs and int(p.get("v", 1)) <= specs[k][1]}
    touched = [f for p in plan.values() for f in p.get("files", []) if f in data]
    if not touched:
        return []
    _backup(config_dir, touched)
    out = []
    team = {}
    for k, p in plan.items():
        files = [f for f in p.get("files", []) if f in data]
        try:
            if k in TEAM_PARTS:
                for f in files:
                    team[f[7:]] = data[f]
                continue
            if k == "acronyms":
                import app_gui
                if not os.path.isfile(app_gui.DB_FILE):
                    _write(app_gui.DB_FILE, data[files[0]]); out.append((k, "the master acronym list written"))
                else:
                    out.append((k, f"{app_gui.merge_pack_database(data[files[0]])} term(s) added"))
            elif k == "dictionaries":
                out.append((k, _merge_dictionaries(config_dir, data[files[0]])))
            elif k == "banned":
                import teampack as TP
                team[TP.FILES["banned"]] = data[files[0]]
            elif k == "standards":
                said = []
                js = [f for f in files if f.endswith("/production_standards.json")]
                said.append(f"{_merge_files(config_dir, [f for f in files if f not in js], data)} cover, back cover or Quick Parts file(s) added")
                if js:
                    said.insert(0, _merge_standards(config_dir, data[js[0]]))
                out.append((k, "; ".join(said)))
            elif k == "ocr":
                n = sum(_merge_csv_rows(_local_path(config_dir, f), data[f]) for f in files)
                out.append((k, f"{n} OCR fix(es) and ignore row(s) added"))
            elif k == "synonyms":
                import placelearn as PL
                pth = _local_path(config_dir, files[0])
                mine = open(pth, encoding="utf-8").read() if os.path.isfile(pth) else ""
                text, n = PL.merge_synonym_text(mine, data[files[0]].decode("utf-8"))
                if n or not mine:
                    _write(pth, text.encode("utf-8"))
                out.append((k, f"{n} synonym group(s) added"))
            elif k == "offerings":
                pth = _local_path(config_dir, files[0])
                if not os.path.isfile(pth):
                    _write(pth, data[files[0]]); out.append((k, "the offerings catalog written"))
                else:
                    import offerings as OF
                    tmp = os.path.join(config_dir, BACKUPS, "_offerings_in.csv")
                    _write(tmp, data[files[0]])
                    r = OF.import_file(tmp)
                    os.remove(tmp)
                    out.append((k, f"offerings merged ({r if isinstance(r, (int, str)) else 'done'})"))
            else:                                               # library, schedule, cwords: new files only
                n = _merge_files(config_dir, files, data)
                out.append((k, f"{n} file(s) added" if n else "this PC's own kept"))
        except Exception as e:                                  # noqa: BLE001  one part's trouble never stops the rest
            import diag
            diag.swallowed()
            out.append((k, f"not imported ({type(e).__name__})"))
    if team:
        import teampack as TP
        tparts = [p for p in TP.PARTS if TP.FILES.get(p) in team or (p == "logos" and any(n.startswith("brand/") for n in team))]
        logos = {n: b for n, b in team.items() if n.startswith("brand/")}
        tdata = {n: b for n, b in team.items() if not n.startswith("brand/")}
        for i, (n, b) in enumerate(sorted(logos.items()), 1):
            if i <= 3:
                tdata[f"brand/logo_{i:02d}.png"] = b
        for k, said in TP.install(config_dir, {"parts": tparts, "locks": [], "name": "Stationkeeper Data", "version": man.get("created", "")},
                                  tdata, who=who):
            key = "banned" if k == "banned" else k
            out.append((key, said))
    return out


def backups(config_dir):
    d = os.path.join(config_dir, BACKUPS)
    return sorted([x for x in os.listdir(d) if not x.startswith("_")], reverse=True) if os.path.isdir(d) else []


def undo(config_dir):
    """Puts back every file the last import touched, and takes out the ones it added. Returns how many."""
    b = backups(config_dir)
    if not b:
        return 0
    folder = os.path.join(config_dir, BACKUPS, b[0])
    try:
        with open(os.path.join(folder, "kept.json"), encoding="utf-8") as f:
            k = json.load(f)
    except (OSError, ValueError):
        return 0
    n = 0
    for m in k.get("kept", []):
        _write(_local_path(config_dir, m), open(os.path.join(folder, m.replace("/", os.sep)), "rb").read()); n += 1
    for m in k.get("absent", []):
        p = _local_path(config_dir, m)
        if os.path.isfile(p):
            os.remove(p); n += 1
    shutil.rmtree(folder, ignore_errors=True)
    return n
