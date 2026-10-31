"""Update packs (2.76.0): install Stationkeeper once, then bring it up to date with one .skupdate file.

What a pack is: a zip holding update_info.json (the new version's full list of program files with their SHA-256),
update_info.sig (the publisher's Ed25519 signature of that list) and payload/ (only the program files that changed
since 2.76.0, so any copy from 2.76.0 on can use it, skipping versions).

What it may change: program files only (Stationkeeper.exe or StationkeeperTraining.exe, _internal\\ and the four
documents). Never config\\, acronym_database.csv, efforts, logs, training data or anything else in the folder.

How it installs, offline and as the user (no admin):
  1. check: the signature matches a publisher key built into this program; every path is a program path; the pack
     is for this program and edition, newer than this copy, and holds every file this copy lacks.
  2. stage: the needed files are unpacked into _update\\staged\\ and each one's SHA-256 is checked again.
  3. apply: each old file is moved into _update\\backup\\ and the new one moved into place (Windows lets a running
     program's files be renamed, not overwritten). Any failure moves everything back. A crash part-way is put back
     at the next start, before the program loads anything else.
  4. Stationkeeper restarts on the new version. Undo last update moves the backup back.

Uses only the Python standard library and edsign (pure Python), so it can run at the very start of the program.
"""
import datetime, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile

FORMAT = 1
EXT = ".skupdate"
FIRST = "2.76.0"                       # the first version that installs update packs
SIG_DOMAIN = b"Stationkeeper update pack v1\n"
# The publisher's public keys. The private key never leaves the build PC (_local_sandbox\keys, never in GitHub).
PUBLIC_KEYS = ["87012556168e4fde1523cfb3729f63fd97e7aa4413522a0eb6ec21e754f2722e"]
PROGRAMS = ("Stationkeeper", "StationkeeperTraining")
MANIFEST = "_internal/program_manifest.json"
DOCS = ("README.txt", "OVERVIEW.md", "SECURITY.md", "CHECKSUM.txt")
UPDATE_DIR = "_update"
MAX_FILE = 600 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024
_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(10)} | {f"lpt{i}" for i in range(10)}


class UpdateError(Exception):
    """Something about the pack or this copy stops the update. The message says what, in plain words. Nothing was changed."""


# ---------------------------------------------------------------- versions and paths
def vtuple(v):
    try:
        parts = tuple(int(x) for x in str(v).strip().split("."))
    except ValueError:
        raise UpdateError(f"'{v}' is not a version number.")
    if not parts or len(parts) > 4:
        raise UpdateError(f"'{v}' is not a version number.")
    return parts + (0,) * (4 - len(parts))


def norm(rel):
    """A program path in the pack's form (forward slashes), or UpdateError for anything that could leave the folder."""
    if not isinstance(rel, str) or not rel or len(rel) > 400:
        raise UpdateError("The update pack names a file that is not allowed.")
    r = rel.replace("\\", "/")
    if r.startswith("/") or ":" in r or any(ord(c) < 32 for c in r):
        raise UpdateError("The update pack names a file outside the program folder.")
    for seg in r.split("/"):
        if seg in ("", ".", "..") or seg != seg.rstrip(" .") or seg.split(".")[0].lower() in _RESERVED:
            raise UpdateError("The update pack names a file outside the program folder.")
    return r


def is_program_path(rel, program):
    """True for the program's own files: the exe, _internal/..., the four documents. Never data."""
    r = norm(rel)
    return r == program + ".exe" or r.startswith("_internal/") or r in DOCS


def _abs(app_dir, rel):
    return os.path.join(app_dir, *rel.split("/"))


def sha256_file(path, limit=MAX_FILE):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            n += len(b)
            if n > limit:
                raise UpdateError("A file is larger than an update allows.")
            h.update(b)
    return h.hexdigest(), n


# ---------------------------------------------------------------- the program manifest (every build writes one)
def build_manifest(app_dir, program, version, edition="us"):
    """{format, program, edition, version, files: {path: {sha256, size}}}: the program files of this folder."""
    files = {}
    exe = program + ".exe"
    for rel in [exe] + [d for d in DOCS]:
        p = _abs(app_dir, rel)
        if os.path.isfile(p):
            h, n = sha256_file(p)
            files[rel] = {"sha256": h, "size": n}
    root = os.path.join(app_dir, "_internal")
    for d, _dirs, names in os.walk(root):
        for nm in names:
            rel = os.path.relpath(os.path.join(d, nm), app_dir).replace("\\", "/")
            if rel == MANIFEST:
                continue
            h, n = sha256_file(os.path.join(d, nm))
            files[rel] = {"sha256": h, "size": n}
    return {"format": FORMAT, "program": program, "edition": edition, "version": version, "files": dict(sorted(files.items()))}


def write_manifest(app_dir, program, version, edition="us"):
    m = build_manifest(app_dir, program, version, edition)
    os.makedirs(os.path.join(app_dir, "_internal"), exist_ok=True)
    with open(_abs(app_dir, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    return m


def read_manifest(app_dir):
    p = _abs(app_dir, MANIFEST)
    try:
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m, dict) or not isinstance(m.get("files"), dict):
            return None
        return m
    except (OSError, ValueError):
        return None


def installed_version(app_dir, fallback=""):
    m = read_manifest(app_dir)
    return (m or {}).get("version") or fallback


# ---------------------------------------------------------------- making a pack (build PC only)
def make_pack(app_dir, out, secret, earlier=(), min_version=FIRST, notes="", always=()):
    """Write a signed pack for the build in app_dir. earlier: the program manifests of every release from min_version
    up to the one before this; a file goes in the pack when any of them has it different (or lacks it), so one pack
    serves every copy from min_version on. always: paths replaced even when unchanged (the build's own test)."""
    target = read_manifest(app_dir)
    if target is None:
        raise UpdateError("The build has no program_manifest.json.")
    fresh = build_manifest(app_dir, target["program"], target["version"], target.get("edition", "us"))
    if fresh["files"] != target["files"]:
        raise UpdateError("program_manifest.json does not match the build's files.")
    program = target["program"]
    for rel in target["files"]:
        if not is_program_path(rel, program):
            raise UpdateError(f"{rel} is not a program file.")
    earlier = [e for e in earlier if e.get("program") == program]
    payload = []
    for rel, meta in target["files"].items():
        if not earlier or any((e["files"].get(rel) or {}).get("sha256") != meta["sha256"] for e in earlier) or rel in always:
            payload.append(rel)
    payload.append(MANIFEST)
    mh, mn = sha256_file(_abs(app_dir, MANIFEST))
    pay = {rel: (target["files"][rel] if rel != MANIFEST else {"sha256": mh, "size": mn}) for rel in payload}
    info = {"format": FORMAT, "program": program, "edition": target.get("edition", "us"), "version": target["version"],
            "min_version": min_version, "built": datetime.datetime.now().isoformat(timespec="seconds"), "notes": notes,
            "files": target["files"], "manifest": {"sha256": mh, "size": mn}, "payload": dict(sorted(pay.items())),
            "always": sorted(always), "from_versions": sorted({e.get("version", "") for e in earlier}, key=lambda v: vtuple(v))}
    data = json.dumps(info, indent=1, sort_keys=True).encode("utf-8")
    sig = sign_bytes(secret, data)
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("update_info.json", data)
        z.writestr("update_info.sig", sig.hex())
        for rel in sorted(pay):
            z.write(_abs(app_dir, rel), "payload/" + rel)
    os.replace(tmp, out)
    return info


def sign_bytes(secret, data):
    import edsign
    return edsign.sign(secret, SIG_DOMAIN + data)


def load_secret(path):
    """The private key file: 64 hex characters on one line (made by tools/make_update.py --new-key)."""
    with open(path, encoding="ascii") as f:
        s = bytes.fromhex(f.read().strip())
    if len(s) != 32:
        raise UpdateError("The signing key file is not a 32-byte Ed25519 key.")
    return s


# ---------------------------------------------------------------- reading and checking a pack
def read_pack(path, keys=None):
    """The pack's update_info, after every check that needs no install: signature, paths, names, sizes."""
    keys = PUBLIC_KEYS if keys is None else keys
    if not os.path.isfile(path) or not zipfile.is_zipfile(path):
        raise UpdateError("This is not a Stationkeeper update pack.")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "update_info.json" not in names or "update_info.sig" not in names:
            raise UpdateError("This is not a Stationkeeper update pack.")
        if z.getinfo("update_info.json").file_size > 50 * 1024 * 1024 or z.getinfo("update_info.sig").file_size > 1024:
            raise UpdateError("This is not a Stationkeeper update pack.")
        data = z.read("update_info.json")
        try:
            sig = bytes.fromhex(z.read("update_info.sig").decode("ascii").strip())
        except (UnicodeDecodeError, ValueError):
            sig = b""
        import edsign
        good = False
        for k in keys:
            try:
                good = edsign.verify(bytes.fromhex(k), SIG_DOMAIN + data, sig)
            except ValueError:
                good = False
            if good:
                break
        if not good:
            raise UpdateError("This update pack is not signed by the Stationkeeper publisher, or it was changed after it "
                              "was made. Nothing was installed. Get the pack again from the approved folder.")
        try:
            info = json.loads(data.decode("utf-8"))
        except ValueError:
            raise UpdateError("This update pack is damaged.")
        if not isinstance(info, dict) or info.get("format") != FORMAT:
            raise UpdateError("This update pack needs a newer Stationkeeper. Download the full copy once.")
        program = info.get("program")
        if program not in PROGRAMS:
            raise UpdateError("This update pack is not for a Stationkeeper program.")
        vtuple(info.get("version")), vtuple(info.get("min_version"))
        files, pay = info.get("files"), info.get("payload")
        if not isinstance(files, dict) or not isinstance(pay, dict) or not files:
            raise UpdateError("This update pack is damaged.")
        total = 0
        for rel, meta in list(files.items()) + list(pay.items()):
            if not is_program_path(rel, program):
                raise UpdateError(f"This update pack tries to change {rel}, which is not a program file. Nothing was installed.")
            if (not isinstance(meta, dict) or not isinstance(meta.get("size"), int) or not 0 <= meta["size"] <= MAX_FILE
                    or not isinstance(meta.get("sha256"), str) or len(meta["sha256"]) != 64):
                raise UpdateError("This update pack is damaged.")
        for rel in pay:
            if rel != MANIFEST and files.get(rel) != pay[rel]:
                raise UpdateError("This update pack is damaged.")
            total += pay[rel]["size"]
        if MANIFEST not in pay or total > MAX_TOTAL:
            raise UpdateError("This update pack is damaged.")
        want = {"update_info.json", "update_info.sig"} | {"payload/" + r for r in pay}
        if set(names) != want or len(names) != len(want):
            raise UpdateError("This update pack holds files it does not list. Nothing was installed.")
        for rel in pay:
            if z.getinfo("payload/" + rel).file_size != pay[rel]["size"]:
                raise UpdateError("This update pack is damaged.")
    return info


def check(pack, app_dir, program, edition=None):
    """The install plan, or UpdateError. {info, from, to, replace, add, remove, keep, bytes}"""
    info = read_pack(pack)
    if info["program"] != program:
        other = "Stationkeeper Training" if info["program"] == "StationkeeperTraining" else "Stationkeeper"
        raise UpdateError(f"This update pack is for {other}. Install it from that program.")
    if edition and info.get("edition", "us") != edition:
        raise UpdateError("This update pack is for another edition of Stationkeeper.")
    inst = read_manifest(app_dir)
    if inst is None or inst.get("program") != program:
        raise UpdateError(f"This copy is older than {FIRST} (it has no list of its program files). Download the full copy "
                          "once; from then on, update packs bring it up to date.")
    iv, tv = vtuple(inst["version"]), vtuple(info["version"])
    if tv == iv:
        raise UpdateError(f"This copy already has version {info['version']}.")
    if tv < iv:
        raise UpdateError(f"This update pack holds version {info['version']}, older than this copy ({inst['version']}). "
                          "Nothing was installed. To go back after an update, use Undo last update.")
    if iv < vtuple(info["min_version"]):
        raise UpdateError(f"This update pack needs version {info['min_version']} or later; this copy is {inst['version']}. "
                          "Download the full copy once.")
    replace, add, keep, missing = [], [], [], []
    always = set(info.get("always") or [])
    for rel, meta in info["files"].items():
        p = _abs(app_dir, rel)
        need = rel in always or not os.path.isfile(p) or os.path.getsize(p) != meta["size"]
        if not need:
            try:
                need = sha256_file(p)[0] != meta["sha256"]
            except (OSError, UpdateError):
                need = True
        if not need:
            keep.append(rel)
        elif rel not in info["payload"]:
            missing.append(rel)
        else:
            (replace if os.path.isfile(p) else add).append(rel)
    if missing:
        raise UpdateError(f"This update pack does not hold {len(missing)} program file(s) this copy needs (it was made "
                          f"for copies from {info['min_version']} on, and this copy's files differ). Nothing was installed. "
                          "Use Check program files, or download the full copy.")
    (replace if os.path.isfile(_abs(app_dir, MANIFEST)) else add).append(MANIFEST)
    remove = [rel for rel in inst["files"] if rel not in info["files"] and is_program_path(rel, program)
              and os.path.isfile(_abs(app_dir, rel))]
    size = sum(info["payload"][r]["size"] for r in replace + add)
    return {"info": info, "from": inst["version"], "to": info["version"], "program": program,
            "replace": _order(replace, program), "add": _order(add, program), "remove": _order(remove, program),
            "keep": len(keep), "bytes": size}


def _order(rels, program):
    """_internal first, the documents next, the exe last: a crash part-way leaves the exe that can put things back."""
    def key(r):
        return (2 if r == program + ".exe" else 1 if r in DOCS else 0, r)
    return sorted(rels, key=key)


def summary(plan):
    n = len(plan["replace"]) + len(plan["add"])
    mb = plan["bytes"] / 1024 / 1024
    return (f"Update {plan['program']} from {plan['from']} to {plan['to']}: {n} program file(s) to copy in ({mb:.1f} MB)"
            + (f", {len(plan['remove'])} to remove" if plan["remove"] else "") + f"; {plan['keep']} stay as they are.")


# ---------------------------------------------------------------- staging and applying
def _udir(app_dir, *parts):
    return os.path.join(app_dir, UPDATE_DIR, *parts)


def stage(plan, pack, app_dir, progress=None):
    """Unpack the files the plan needs into _update\\staged\\, checking each one's SHA-256 as it is written."""
    sdir = _udir(app_dir, "staged")
    shutil.rmtree(sdir, ignore_errors=True)
    os.makedirs(sdir, exist_ok=True)
    need = plan["replace"] + plan["add"]
    free = shutil.disk_usage(app_dir).free
    if free < plan["bytes"] * 2 + 50 * 1024 * 1024:
        raise UpdateError("There is not enough free disk space for this update.")
    pay = plan["info"]["payload"]
    try:
        with zipfile.ZipFile(pack) as z:
            for i, rel in enumerate(need):
                dst = _abs(sdir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                h, n = hashlib.sha256(), 0
                with z.open("payload/" + rel) as src, open(dst, "wb") as out:
                    while True:
                        b = src.read(1024 * 1024)
                        if not b:
                            break
                        n += len(b)
                        if n > pay[rel]["size"]:
                            raise UpdateError("This update pack is damaged.")
                        h.update(b)
                        out.write(b)
                if n != pay[rel]["size"] or h.hexdigest() != pay[rel]["sha256"]:
                    raise UpdateError("This update pack is damaged (a file does not match its signed checksum). Nothing was installed.")
                if progress:
                    progress(i + 1, len(need))
    except UpdateError:
        shutil.rmtree(sdir, ignore_errors=True)
        raise
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        shutil.rmtree(sdir, ignore_errors=True)
        raise UpdateError(f"The update could not be unpacked ({type(e).__name__}). Nothing was installed.")
    return sdir


def _move(src, dst, tries=40):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.25)                     # a virus scanner reading a new file holds it for a moment


def _journal(app_dir, data):
    p = _udir(app_dir, "journal.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".part", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(p + ".part", p)


def read_journal(app_dir):
    try:
        with open(_udir(app_dir, "journal.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _put_back(app_dir, j, new_dir, old_dir):
    """Undo a part-done swap. Moves out (old to old_dir) all ran before moves in (new_dir to the app), so: a file whose
    new copy left new_dir and whose place is taken goes back to new_dir; then every old copy goes back. Safe to repeat."""
    for rel in j["in"]:
        here, fresh = _abs(app_dir, rel), _abs(new_dir, rel)
        if not os.path.exists(fresh) and os.path.isfile(here) and (rel not in j["out"] or os.path.isfile(_abs(old_dir, rel))):
            _move(here, fresh)
    for rel in j["out"]:
        old = _abs(old_dir, rel)
        if os.path.isfile(old) and not os.path.exists(_abs(app_dir, rel)):
            _move(old, _abs(app_dir, rel))


def _swap(app_dir, j, new_dir, old_dir, fail_after=None):
    _journal(app_dir, dict(j, state="applying"))
    done = 0
    try:
        for rel in j["out"]:
            _move(_abs(app_dir, rel), _abs(old_dir, rel))
            done += 1
            if fail_after is not None and done >= fail_after:
                raise OSError("test: stopped part-way")
        for rel in j["in"]:
            _move(_abs(new_dir, rel), _abs(app_dir, rel))
            done += 1
            if fail_after is not None and done >= fail_after:
                raise OSError("test: stopped part-way")
    except Exception:
        try:
            _put_back(app_dir, j, new_dir, old_dir)
            _journal(app_dir, dict(j, state="put back"))
        except Exception:
            pass                                 # the next start tries again (recover)
        raise
    _journal(app_dir, dict(j, state="done"))


def apply(plan, app_dir, fail_after=None):
    """Swap the staged files in; the replaced and removed ones go to _update\\backup\\ (for Undo). Returns the summary."""
    sdir, bdir = _udir(app_dir, "staged"), _udir(app_dir, "backup")
    if os.path.isdir(bdir):
        shutil.rmtree(bdir, ignore_errors=True)
        if os.path.isdir(bdir):                  # an older backup still in use: set it aside
            os.replace(bdir, _udir(app_dir, "old-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")))
    os.makedirs(bdir, exist_ok=True)
    j = {"kind": "update", "from": plan["from"], "to": plan["to"], "program": plan["program"],
         "out": plan["replace"] + plan["remove"], "in": plan["replace"] + plan["add"], "new": "staged", "old": "backup",
         "at": datetime.datetime.now().isoformat(timespec="seconds")}
    try:
        _swap(app_dir, j, sdir, bdir, fail_after)
    except Exception as e:
        if isinstance(e, PermissionError):
            raise UpdateError("Windows would not let the program files change (the folder may belong to IT, or another "
                              "copy of the program is open). Everything was put back as it was.")
        raise UpdateError(f"The update stopped ({type(e).__name__}). Everything was put back as it was.")
    with open(os.path.join(bdir, "backup_info.json"), "w", encoding="utf-8") as f:
        json.dump({"from": plan["from"], "to": plan["to"], "program": plan["program"], "replaced": plan["replace"],
                   "added": plan["add"], "removed": plan["remove"], "at": j["at"]}, f, indent=1)
    shutil.rmtree(sdir, ignore_errors=True)
    _prune_empty(app_dir, plan["remove"])
    return {"from": plan["from"], "to": plan["to"], "copied": len(j["in"]), "removed": len(plan["remove"])}


def _prune_empty(app_dir, rels):
    for rel in rels:
        d = os.path.dirname(_abs(app_dir, rel))
        while os.path.normcase(d).startswith(os.path.normcase(os.path.join(app_dir, "_internal") + os.sep)):
            try:
                os.rmdir(d)
            except OSError:
                break
            d = os.path.dirname(d)


def backup_info(app_dir):
    try:
        with open(_udir(app_dir, "backup", "backup_info.json"), encoding="utf-8") as f:
            b = json.load(f)
        return b if isinstance(b, dict) and b.get("to") else None
    except (OSError, ValueError):
        return None


def undo(app_dir, program):
    """Undo last update: the version before it comes back from _update\\backup\\. Returns {from, to}."""
    b = backup_info(app_dir)
    if b is None or b.get("program") != program:
        raise UpdateError("There is no update to undo.")
    inst = read_manifest(app_dir)
    if inst is None or inst.get("version") != b["to"]:
        raise UpdateError("This copy changed since the last update, so it cannot be undone. Download the full copy instead.")
    for rel in b["replaced"] + b["added"] + b["removed"]:
        if not is_program_path(rel, program):
            raise UpdateError("The update backup is damaged.")
    bdir, udir = _udir(app_dir, "backup"), _udir(app_dir, "undone")
    shutil.rmtree(udir, ignore_errors=True)
    os.makedirs(udir, exist_ok=True)
    # "out": the update's files go to undone; "in": the backup's files come back. The same swap, the other way.
    j = {"kind": "undo", "from": b["to"], "to": b["from"], "program": program, "out": b["replaced"] + b["added"],
         "in": b["replaced"] + b["removed"], "new": "backup", "old": "undone",
         "at": datetime.datetime.now().isoformat(timespec="seconds")}
    try:
        _swap(app_dir, j, bdir, udir)
    except Exception as e:
        raise UpdateError(f"Undo stopped ({type(e).__name__}). Everything was put back as it was.")
    try:
        os.remove(os.path.join(bdir, "backup_info.json"))
    except OSError:
        pass
    return {"from": b["to"], "to": b["from"]}


def recover(app_dir):
    """At start: finish putting back an update or undo that stopped part-way, and clear leftovers. Returns what it did."""
    j = read_journal(app_dir)
    did = ""
    if j and j.get("state") == "applying" and isinstance(j.get("out"), list) and isinstance(j.get("in"), list):
        try:
            prog = j.get("program", "Stationkeeper")
            if all(is_program_path(r, prog) for r in j["out"] + j["in"]):
                _put_back(app_dir, j, _udir(app_dir, j.get("new", "staged")), _udir(app_dir, j.get("old", "backup")))
                _journal(app_dir, dict(j, state="put back at start"))
                did = "put back"
        except Exception:
            did = "put back failed"
    if not (j and j.get("state") == "applying"):
        for d in ("staged", "undone"):
            shutil.rmtree(_udir(app_dir, d), ignore_errors=True)
        base = _udir(app_dir)
        if os.path.isdir(base):
            for nm in os.listdir(base):
                if nm.startswith("old-"):
                    shutil.rmtree(os.path.join(base, nm), ignore_errors=True)
    return did


# ---------------------------------------------------------------- checking the program files
def check_files(app_dir):
    """Compare the program files with this version's list: {version, ok, changed, missing, extra}."""
    m = read_manifest(app_dir)
    if m is None:
        return None
    ok, changed, missing = 0, [], []
    for rel, meta in m["files"].items():
        p = _abs(app_dir, rel)
        if not os.path.isfile(p):
            missing.append(rel)
            continue
        try:
            same = os.path.getsize(p) == meta["size"] and sha256_file(p)[0] == meta["sha256"]
        except (OSError, UpdateError):
            same = False
        if same:
            ok += 1
        else:
            changed.append(rel)
    extra, logos = [], []
    for d, _dirs, names in os.walk(os.path.join(app_dir, "_internal")):
        for nm in names:
            rel = os.path.relpath(os.path.join(d, nm), app_dir).replace("\\", "/")
            if rel != MANIFEST and rel not in m["files"]:
                (logos if is_company_logo(rel) else extra).append(rel)
    return {"version": m.get("version", ""), "ok": ok, "changed": changed, "missing": missing, "extra": sorted(extra),
            "logos": sorted(logos)}


def is_company_logo(rel):
    """3.0.4: a company logo placed in the program folder (_internal/assets/brand/logo_01.png ...): the team's own file, put
    there on purpose, never part of a version's list and never taken away by an update pack."""
    rel = rel.replace("\\", "/")
    head, name = os.path.split(rel)
    return head.lower() == "_internal/assets/brand" and re.fullmatch(r"logo[_\- ]?\w*\.(png|jpe?g|bmp|gif|svg)", name.lower()) is not None


def check_text(r):
    if r is None:
        return "This copy has no list of its program files (it is older than 2.76.0)."
    logos = r.get("logos") or []
    lt = (f" Company logos placed by your team ({len(logos)}): " + ", ".join(os.path.basename(x) for x in logos) + ".") if logos else ""
    if not (r["changed"] or r["missing"] or r["extra"]):
        return f"All {r['ok']} program files match version {r['version']}." + lt
    out = [f"Version {r['version']}: {r['ok']} program files match."]
    for label, key in (("Changed", "changed"), ("Missing", "missing"), ("Not part of this version", "extra")):
        if r[key]:
            out.append(f"{label} ({len(r[key])}): " + ", ".join(r[key][:12]) + (" ..." if len(r[key]) > 12 else ""))
    out.append("Download the full copy from the approved folder to put the program files right. Your data is not affected.")
    if logos:
        out.append(lt.strip() + " Copy them into the new copy's _internal\\assets\\brand folder too.")
    return "\n".join(out)


# ---------------------------------------------------------------- restart
# ---------------------------------------------------------------- the hand-over to the new version (2.82.0)
HANDOFF = "started.json"


def clear_handoff(app_dir):
    try:
        os.remove(_udir(app_dir, HANDOFF))
    except OSError:
        pass


def signal_started(app_dir, version):
    """The new version says its window is up, so the old one (showing 'Starting the new version') can close."""
    try:
        os.makedirs(_udir(app_dir), exist_ok=True)
        with open(_udir(app_dir, HANDOFF), "w", encoding="utf-8") as f:
            json.dump({"version": version, "pid": os.getpid(), "time": time.time()}, f)
        return True
    except OSError:
        return False


def started_seen(app_dir):
    return os.path.isfile(_udir(app_dir, HANDOFF))


def restart(app_dir, program, args=()):
    exe = os.path.join(app_dir, program + ".exe")
    if not os.path.isfile(exe):
        return False
    flags = 0
    if sys.platform == "win32":
        flags = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe] + list(args), cwd=app_dir, close_fds=True, creationflags=flags)
    return True
