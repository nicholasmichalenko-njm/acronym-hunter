"""Team defaults (2.89.0): one file (.skteam) that sets up every PC on the team the same way.

What it can carry (the maker ticks the parts):
- authors: the author list (names, and which efforts each shows in)
- design: the team's matrix design (columns and their order)
- banned: the banned words and phrases the Submission check looks for
- goals: the default gate goals for new efforts, by stage
- logos: the company logos at the top of the menu (up to three)
- roles: the team's Effort Home layout for each role (Proposal Manager, Production, Author, Reviewer, Capture)
- markings: the sensitivity markings the team uses (CUI, CUI//SP-PROPIN, Proprietary...)
- topics: the team's topics, offered as one-click tags when context is taken from a library document
Installing adds: names, phrases, goals, markings and topics this PC does not have yet join the ones it has, and nothing
of the PC's own is changed or removed. A single-valued part (the matrix design, the logos, the role layouts) is taken
only where this PC has none of its own, unless the maker locked it. A locked part replaces this PC's own and stays as
the team set it: Settings shows it as set by the team, and the controls that would change it are off until the team pack
is undone. Every install keeps a copy of everything it touches; Undo puts all of it back and lifts the locks.
The file is checked before anything is read from it: only the listed members, each within its size and matching its
SHA-256, pictures that open as pictures. It holds names: keep it on the approved SharePoint folder, never on GitHub.
Rules only (No AI); nothing leaves the PC.
"""
import datetime, getpass, hashlib, io, json, os, platform, shutil, zipfile

FORMAT = "sk-team-1"
EXT = ".skteam"
INFO = "team_pack.json"
MAX_BYTES = 8 * 1024 * 1024
PARTS = ("authors", "design", "banned", "goals", "process", "doctypes", "logos", "roles", "markings", "topics", "postsub")
PART_NAMES = {"authors": "Author list", "design": "Matrix design", "banned": "Banned words and phrases", "goals": "Default gate goals",
              "logos": "Company logos", "roles": "Effort Home layouts by role", "markings": "Sensitivity markings",
              "topics": "Team topics", "postsub": "Post-submission checklist", "process": "Stages, gates and roles",
              "doctypes": "Document types"}
LOCKABLE = ("design", "logos", "roles", "goals", "markings", "postsub", "process", "doctypes")
FILES = {"authors": "author_list.json", "design": "matrix design.json", "banned": "banned_words.csv", "goals": "stage_goals.json",
         "roles": "team_roles.json", "markings": "team_markings.json", "topics": "team_topics.json", "postsub": "postsub_default.json",
         "process": "process.json", "doctypes": "doc_types.json"}
LOCKS = "team_locks.json"
INSTALLED = "team_installed.json"
BACKUPS = "team_backups"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _read(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


# ------------------------------------------------------------------ the team lists this PC keeps
def roles(config_dir):
    """The team's role layouts: {role: [section keys in order]} (empty: the built-in ones)."""
    d = _read(os.path.join(config_dir, FILES["roles"]), {}) or {}
    return {k: [x for x in v if isinstance(x, str)] for k, v in d.items() if isinstance(v, list)}


def markings(config_dir):
    return [m for m in (_read(os.path.join(config_dir, FILES["markings"]), []) or []) if isinstance(m, str) and m.strip()]


def topics(config_dir):
    return [t for t in (_read(os.path.join(config_dir, FILES["topics"]), []) or []) if isinstance(t, str) and t.strip()]


def save_topics(config_dir, lst):
    out = []
    for t in lst:
        t = " ".join(str(t).split())[:40]
        if t and t.casefold() not in {x.casefold() for x in out}:
            out.append(t)
    _write(os.path.join(config_dir, FILES["topics"]), out)
    return out


def save_markings(config_dir, lst):
    out = []
    for t in lst:
        t = " ".join(str(t).split())[:60]
        if t and t.casefold() not in {x.casefold() for x in out}:
            out.append(t)
    _write(os.path.join(config_dir, FILES["markings"]), out)
    return out


def locks(config_dir):
    """{part: pack name} for the parts the team locked on this PC."""
    return _read(os.path.join(config_dir, LOCKS), {}) or {}


def locked(config_dir, part):
    return part in locks(config_dir)


def installed(config_dir):
    return _read(os.path.join(config_dir, INSTALLED), None)


# ------------------------------------------------------------------ making a pack
def available(config_dir):
    """{part: short description} for the parts this PC has something to share."""
    import authorlist as AL
    import branding as BR
    out = {}
    try:
        n = len(AL.load(config_dir).names())
        if n:
            out["authors"] = f"{n} name(s)"
    except Exception:
        pass
    if os.path.isfile(os.path.join(config_dir, FILES["design"])):
        out["design"] = "the team matrix design saved on this PC"
    p = os.path.join(config_dir, FILES["banned"])
    if os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            n = max(0, sum(1 for ln in f if ln.strip()) - 1)
        if n:
            out["banned"] = f"{n} phrase(s)"
    g = (_read(os.path.join(config_dir, FILES["goals"]), {}) or {}).get("stages") or {}
    if g:
        out["goals"] = f"{sum(len(v) for v in g.values())} goal(s) in {len(g)} stage(s)"
    lg = BR.logos(config_dir)
    if lg:
        out["logos"] = f"{len(lg)} logo(s)"
    if roles(config_dir):
        out["roles"] = f"{len(roles(config_dir))} role layout(s)"
    if markings(config_dir):
        out["markings"] = ", ".join(markings(config_dir))
    if topics(config_dir):
        out["topics"] = f"{len(topics(config_dir))} topic(s)"
    if os.path.isfile(os.path.join(config_dir, FILES["process"])):        # 2.93.0
        import process as PR
        P = PR.load(config_dir)
        out["process"] = f"{len(P['stages'])} default stage(s), {len(P['gates'])} gate choice(s), {len(P['roles'])} role(s)"
    if os.path.isfile(os.path.join(config_dir, FILES["doctypes"])):       # 2.94.0
        import doctypes as DT
        out["doctypes"] = f"{len(DT.load(config_dir)['types'])} document type(s)"
    ps = (_read(os.path.join(config_dir, FILES["postsub"]), {}) or {}).get("items") or []
    if ps:
        out["postsub"] = f"{len(ps)} item(s)"
    return out


def make(config_dir, out_path, parts, lock=(), name="", notes="", role_layouts=None):
    """Writes the pack. parts: which to carry; lock: which of those the team locks. role_layouts: {role: order} to carry
    as the team's layouts (else the ones this PC holds). Returns the pack's info."""
    import authorlist as AL
    import branding as BR
    members = {}
    parts = [p for p in PARTS if p in parts]
    if "authors" in parts:
        lst = AL.load(config_dir)
        members[FILES["authors"]] = json.dumps({"format": AL.FORMAT, "people": [{"name": x["name"], "efforts": x["efforts"]} for x in lst.people]},
                                               ensure_ascii=False, indent=1).encode("utf-8")
    for part in ("design", "banned", "goals", "postsub", "process", "doctypes"):
        if part in parts:
            p = os.path.join(config_dir, FILES[part])
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    members[FILES[part]] = f.read()
    if "logos" in parts:
        for i, p in enumerate(BR.logos(config_dir)):
            with open(p, "rb") as f:
                members[f"brand/logo_{i + 1:02d}.png"] = f.read()
    if "roles" in parts:
        members[FILES["roles"]] = json.dumps(role_layouts if role_layouts is not None else roles(config_dir), indent=1).encode("utf-8")
    if "markings" in parts:
        members[FILES["markings"]] = json.dumps(markings(config_dir), indent=1).encode("utf-8")
    if "topics" in parts:
        members[FILES["topics"]] = json.dumps(topics(config_dir), indent=1, ensure_ascii=False).encode("utf-8")
    import app_gui
    now = datetime.datetime.now()
    info = {"format": FORMAT, "name": " ".join((name or "Team defaults").split())[:80], "version": now.strftime("%Y.%m.%d-%H%M"),
            "created": now.strftime("%Y-%m-%d %H:%M"), "created_by": getpass.getuser(), "computer": platform.node(),
            "app_version": app_gui.APP_VERSION, "notes": (notes or "").strip()[:2000], "parts": parts,
            "locks": [p for p in PARTS if p in lock and p in parts and p in LOCKABLE],
            "handling": "Holds the team's names and settings. Approved SharePoint folder only. Never GitHub.",
            "files": {n: {"sha256": _sha(b), "bytes": len(b)} for n, b in members.items()}}
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(INFO, json.dumps(info, indent=1, ensure_ascii=False))
        for n, b in members.items():
            z.writestr(n, b)
    os.replace(tmp, out_path)
    return info


# ------------------------------------------------------------------ reading a pack
def _allowed():
    return {INFO} | set(FILES.values()) | {f"brand/logo_{i:02d}.png" for i in range(1, 4)}


def read(path):
    """(info, {member: bytes}) after checking every member; ValueError for a file that is not a sound team pack."""
    with zipfile.ZipFile(path) as z:
        entries = [e for e in z.infolist() if not e.is_dir()]
        names = {e.filename for e in entries}
        for e in entries:
            if e.filename not in _allowed():
                raise ValueError(f"Unexpected file in the pack: {e.filename}")
            if e.file_size > MAX_BYTES:
                raise ValueError(f"{e.filename} is too large")
        if INFO not in names:
            raise ValueError("Not a team pack (team_pack.json is missing)")
        info = json.loads(z.read(INFO).decode("utf-8"))
        if info.get("format") != FORMAT:
            raise ValueError("Not a Stationkeeper team pack")
        data = {}
        for n, meta in (info.get("files") or {}).items():
            if n not in _allowed() or n not in names:
                raise ValueError(f"The pack lists a file it does not hold: {n}")
            b = z.read(n)
            if _sha(b) != meta.get("sha256"):
                raise ValueError(f"{n} does not match its fingerprint: the pack is damaged or was changed")
            data[n] = b
        if len(data) != len(entries) - 1:
            raise ValueError("The pack holds files its list does not name")
    for n, b in data.items():
        if n.startswith("brand/"):
            from PIL import Image
            try:
                with Image.open(io.BytesIO(b)) as im:
                    im.verify()
            except Exception:
                raise ValueError(f"{n} is not a picture")
        elif n.endswith(".json"):
            try:
                json.loads(b.decode("utf-8"))
            except ValueError:
                raise ValueError(f"{n} is not readable")
    info["parts"] = [p for p in info.get("parts", []) if p in PARTS]
    info["locks"] = [p for p in info.get("locks", []) if p in info["parts"] and p in LOCKABLE]
    return info, data


# ------------------------------------------------------------------ what installing does
def _csv_rows(b):
    import csv
    return list(csv.reader(io.StringIO(b.decode("utf-8-sig"))))


def preview(config_dir, info, data):
    """[(part, what happens)] in plain words, without changing anything."""
    import authorlist as AL
    import branding as BR
    out = []
    lk = set(info["locks"])
    if FILES["authors"] in data:
        have = {AL.key(n) for n in AL.load(config_dir).names()}
        theirs = [x.get("name", "") for x in json.loads(data[FILES["authors"]]).get("people", []) if isinstance(x, dict)]
        new = [n for n in theirs if AL.key(n) and AL.key(n) not in have]
        out.append(("authors", f"{len(new)} name(s) added to the author list; the {len(have)} here stay as they are"))
    if FILES["design"] in data:
        mine = os.path.isfile(os.path.join(config_dir, FILES["design"]))
        out.append(("design", "Replaces this PC's matrix design (locked by the team)" if "design" in lk else
                    "Kept: this PC has its own matrix design" if mine else "Becomes this PC's matrix design"))
    if FILES["banned"] in data:
        p = os.path.join(config_dir, FILES["banned"])
        have = {r[0].strip().casefold() for r in (_csv_rows(open(p, "rb").read())[1:] if os.path.isfile(p) else []) if r}
        new = [r for r in _csv_rows(data[FILES["banned"]])[1:] if r and r[0].strip() and r[0].strip().casefold() not in have]
        out.append(("banned", f"{len(new)} banned word(s) or phrase(s) added"))
    if FILES["goals"] in data:
        out.append(("goals", "Replaces the default gate goals (locked by the team)" if "goals" in lk else
                    f"{_goals_new(config_dir, data)} default gate goal(s) added for new efforts"))
    logos = sorted(n for n in data if n.startswith("brand/"))
    if logos:
        mine = BR.logos(config_dir)
        out.append(("logos", f"Replaces the logos here with the team's {len(logos)} (locked)" if "logos" in lk else
                    f"Kept: this PC has its own logo(s)" if mine else f"{len(logos)} logo(s) at the top of the menu"))
    if FILES["roles"] in data:
        mine = roles(config_dir)
        out.append(("roles", "The team's role layouts replace this PC's (locked)" if "roles" in lk else
                    "Kept: this PC has its own role layouts" if mine else
                    f"The team's layouts for {len(json.loads(data[FILES['roles']]))} role(s); a layout someone customized stays theirs"))
    if FILES["markings"] in data:
        new = [m for m in json.loads(data[FILES["markings"]]) if m.casefold() not in {x.casefold() for x in markings(config_dir)}]
        out.append(("markings", ("The team's markings replace this PC's (locked)" if "markings" in lk else f"{len(new)} marking(s) added")))
    if FILES["topics"] in data:
        new = [t for t in json.loads(data[FILES["topics"]]) if t.casefold() not in {x.casefold() for x in topics(config_dir)}]
        out.append(("topics", f"{len(new)} team topic(s) added"))
    if FILES["postsub"] in data:
        mine = os.path.isfile(os.path.join(config_dir, FILES["postsub"]))
        out.append(("postsub", "Replaces the default post-submission checklist (locked)" if "postsub" in lk else
                    "Kept: this PC has its own default checklist" if mine else "Becomes the default post-submission checklist"))
    if FILES["process"] in data:
        mine = os.path.isfile(os.path.join(config_dir, FILES["process"]))
        out.append(("process", "Replaces the stages, gates and roles here (locked by the team)" if "process" in lk else
                    "Adds the team's gate choices and roles; this PC's default stages stay" if mine else
                    "Becomes this PC's default stages, gate choices and roles"))
    if FILES["doctypes"] in data:
        mine = os.path.isfile(os.path.join(config_dir, FILES["doctypes"]))
        out.append(("doctypes", "Replaces the document types here (locked by the team)" if "doctypes" in lk else
                    "Adds the team's document types; the ones here stay" if mine else "Becomes this PC's document types"))
    return out


def _goals_new(config_dir, data):
    mine = (_read(os.path.join(config_dir, FILES["goals"]), {}) or {}).get("stages") or {}
    theirs = json.loads(data[FILES["goals"]]).get("stages") or {}
    n = 0
    for st, gl in theirs.items():
        have = {g.casefold() for g in mine.get(st, [])}
        n += sum(1 for g in gl if g.casefold() not in have)
    return n


def _touched(config_dir, data):
    out = [os.path.join(config_dir, f) for f in (LOCKS, INSTALLED)]
    out += [os.path.join(config_dir, FILES[p]) for p in FILES if FILES[p] in data]
    return out


def install(config_dir, info, data, who=None):
    """Applies the pack (add-only, locks replace). Keeps a copy of every file it touches first. Returns preview()."""
    import authorlist as AL
    import branding as BR
    said = preview(config_dir, info, data)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(config_dir, BACKUPS, stamp)
    os.makedirs(bdir, exist_ok=True)
    kept = {}
    for p in _touched(config_dir, data):
        rel = os.path.relpath(p, config_dir)
        if os.path.isfile(p):
            dst = os.path.join(bdir, rel.replace(os.sep, "__"))
            shutil.copy2(p, dst); kept[rel] = os.path.basename(dst)
        else:
            kept[rel] = None
    logo_dir = BR.logo_dir(config_dir)
    old_logos = []
    if any(n.startswith("brand/") for n in data):
        for p in BR.logos(config_dir):
            dst = os.path.join(bdir, "brand__" + os.path.basename(p)); shutil.copy2(p, dst); old_logos.append(os.path.basename(p))
    _write(os.path.join(bdir, "kept.json"), {"files": kept, "logos": old_logos, "pack": info.get("name"), "version": info.get("version")})
    lk = set(info["locks"])
    if FILES["authors"] in data:
        lst = AL.load(config_dir)
        theirs = [x for x in json.loads(data[FILES["authors"]]).get("people", []) if isinstance(x, dict)]
        added = 0
        for x in theirs:
            eff = x.get("efforts", AL.ALL)
            eff = AL.ALL if eff == AL.ALL else [e for e in (eff or []) if isinstance(e, str)]
            added += bool(lst.add(x.get("name", ""), eff, source="team pack", save=False))
        lst._log("team pack", added=added, kept=len(lst.people) - added)
        lst.save()
    if FILES["design"] in data:
        p = os.path.join(config_dir, FILES["design"])
        if "design" in lk or not os.path.isfile(p):
            with open(p, "wb") as f:
                f.write(data[FILES["design"]])
    if FILES["banned"] in data:
        p = os.path.join(config_dir, FILES["banned"])
        mine = _csv_rows(open(p, "rb").read()) if os.path.isfile(p) else []
        theirs = _csv_rows(data[FILES["banned"]])
        head = mine[0] if mine else (theirs[0] if theirs else ["Phrase"])
        have = {r[0].strip().casefold() for r in mine[1:] if r}
        rows = mine[1:] + [r for r in theirs[1:] if r and r[0].strip() and r[0].strip().casefold() not in have]
        import csv
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(head); w.writerows(rows)
    if FILES["goals"] in data:
        p = os.path.join(config_dir, FILES["goals"])
        theirs = json.loads(data[FILES["goals"]]).get("stages") or {}
        if "goals" in lk:
            _write(p, {"stages": theirs})
        else:
            mine = (_read(p, {}) or {}).get("stages") or {}
            for st, gl in theirs.items():
                cur = mine.setdefault(st, [])
                for g in gl:
                    if g.casefold() not in {x.casefold() for x in cur}:
                        cur.append(g)
            _write(p, {"stages": mine})
        import effortrec as R
        R.load_default_goals(config_dir)
    logos = sorted(n for n in data if n.startswith("brand/"))
    if logos and ("logos" in lk or not BR.logos(config_dir)):
        for p in BR.logos(config_dir):
            os.remove(p)
        os.makedirs(logo_dir, exist_ok=True)
        for i, n in enumerate(logos[:BR.LOGO_MAX]):
            with open(os.path.join(logo_dir, f"logo_{i + 1:02d}.png"), "wb") as f:
                f.write(data[n])
    if FILES["roles"] in data and ("roles" in lk or not roles(config_dir)):
        _write(os.path.join(config_dir, FILES["roles"]), json.loads(data[FILES["roles"]]))
    if FILES["markings"] in data:
        theirs = json.loads(data[FILES["markings"]])
        save_markings(config_dir, theirs if "markings" in lk else markings(config_dir) + theirs)
    if FILES["topics"] in data:
        save_topics(config_dir, topics(config_dir) + json.loads(data[FILES["topics"]]))
    if FILES["postsub"] in data:
        p = os.path.join(config_dir, FILES["postsub"])
        if "postsub" in lk or not os.path.isfile(p):
            with open(p, "wb") as f:
                f.write(data[FILES["postsub"]])
    if FILES["process"] in data:                                       # 2.93.0
        import process as PR
        p = os.path.join(config_dir, FILES["process"])
        theirs = json.loads(data[FILES["process"]])
        if "process" in lk or not os.path.isfile(p):
            _write(p, theirs)
        else:
            mine = PR.load(config_dir)
            ids = {g["id"] for g in mine["gates"]}
            PR.save(config_dir, gates=mine["gates"] + [g for g in theirs.get("gates", []) if isinstance(g, dict) and g.get("id") not in ids],
                    roles=mine["roles"] + [r for r in theirs.get("roles", []) if isinstance(r, str)])
        PR.apply(config_dir)
    if FILES["doctypes"] in data:                                      # 2.94.0
        import doctypes as DT
        p = os.path.join(config_dir, FILES["doctypes"])
        theirs = json.loads(data[FILES["doctypes"]]).get("types") or []
        if "doctypes" in lk or not os.path.isfile(p):
            _write(p, {"types": theirs})
        else:
            mine = DT.load(config_dir)["types"]
            have = {t["name"].casefold() for t in mine}
            DT.save(config_dir, mine + [t for t in theirs if isinstance(t, dict) and str(t.get("name", "")).casefold() not in have])
        DT.apply(config_dir)
    cur = locks(config_dir)
    for p in lk:
        cur[p] = info.get("name", "Team defaults")
    _write(os.path.join(config_dir, LOCKS), cur)
    _write(os.path.join(config_dir, INSTALLED), {"name": info.get("name"), "version": info.get("version"), "created_by": info.get("created_by"),
                                                  "installed": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "by": who or getpass.getuser(),
                                                  "parts": info["parts"], "locks": sorted(lk), "backup": stamp})
    return said


def can_undo(config_dir):
    i = installed(config_dir)
    return bool(i and i.get("backup") and os.path.isdir(os.path.join(config_dir, BACKUPS, i["backup"])))


def undo(config_dir):
    """Puts back every file the last install touched (and the logos), lifting its locks."""
    import branding as BR
    i = installed(config_dir)
    if not can_undo(config_dir):
        return False
    bdir = os.path.join(config_dir, BACKUPS, i["backup"])
    kept = _read(os.path.join(bdir, "kept.json"), {}) or {}
    for rel, saved in (kept.get("files") or {}).items():
        p = os.path.join(config_dir, rel)
        if saved:
            shutil.copy2(os.path.join(bdir, saved), p)
        elif os.path.isfile(p):
            os.remove(p)
    if "logos" in (i.get("parts") or []):
        for p in BR.logos(config_dir):
            os.remove(p)
        for n in kept.get("logos") or []:
            os.makedirs(BR.logo_dir(config_dir), exist_ok=True)
            shutil.copy2(os.path.join(bdir, "brand__" + n), os.path.join(BR.logo_dir(config_dir), n))
    try:
        import effortrec as R
        R.CUSTOM_GOALS.clear()
        R.load_default_goals(config_dir)
        import process as PR
        PR.apply(config_dir)
        import doctypes as DT
        DT.apply(config_dir)
    except Exception:
        pass
    shutil.rmtree(bdir, ignore_errors=True)
    return True
