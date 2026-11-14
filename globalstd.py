"""Global Standards (4.30.0, step 1 of the Standards board of 2026-11-13): the foundation every effort starts from, as
one set with a version number. It names every part (formatting, rules, lists, styles, Quick Parts, page layout,
templates, acronyms, dictionaries, banned words, stages, gates, roles, markings, document types, the folder plan) and
the files each part is kept in, fingerprints them, and remembers the version this PC is on and what it looked like.

Three layers, each with one home: Global Standards (this module), Effort Standards (the effort's folder) and this PC's
own settings. Step 1 changes nothing a person does: what is on the PC is draft 1, not published. Publishing a version to
a folder, linking a PC to that folder and installing a version from a file come in step 2; the team pack and the team
data file keep working until then.

    parts(config_dir)        {key: (name, {member: path})} for every part this PC has something in
    fingerprint(config_dir)  {key: sha256} of each part's files
    state(config_dir)        the version this PC is on: {"version", "source", "taken", "by", "note", "parts"}
    status(config_dir)       what to say: the version, where it came from, and the parts changed on this PC since
    take(config_dir, ...)    remember a version as the one in use (step 2 calls it after a publish, a link or an install)
    line(config_dir)         the status in one sentence

Standard library only. Rules only (No AI); nothing leaves the PC."""
import datetime, hashlib, json, os

FILE = "global_standards.json"
FORMAT = 1                                      # formats.py "global standards"
DRAFT, LINKED, INSTALLED, PUBLISHED = "draft", "linked", "installed", "published"
SOURCE_WORDS = {DRAFT: "not a version yet", LINKED: "from the linked folder", INSTALLED: "installed from a file",
                PUBLISHED: "updated from this PC"}
# parts the team data file does not carry: key: (name, [config files], [config folders])
MORE = {
    "rules": ("Rules", ["rules.json"], []),
    "named": ("Named templates", ["templates_named.json"], []),
    "piecetypes": ("Piece types", ["piece_types.json"], []),
    "sections": ("Section designs", [], ["section_designs"]),
    "outline": ("Outline layouts", ["outline_layouts.json"], []),
    "verify": ("Verify menu", ["verify_menu.json"], []),
}
LEFT_OUT = ("access",)                          # which Preview tools are on: a PC's own choice once Global Standards is read only


def _specs():
    import teamdata as TD
    d = {k: v for k, v in TD.all_parts().items() if k not in LEFT_OUT}
    for k, (name, files, folders) in MORE.items():
        d[k] = (name, 1, files, folders, [])
    return d


def parts(config_dir):
    """{key: (name, {member name: local path})} for every part with at least one file on this PC."""
    import teamdata as TD
    out = {}
    for k, spec in _specs().items():
        m = TD._members(config_dir, k, spec)
        if m:
            out[k] = (spec[0], m)
    return out


def names():
    return {k: v[0] for k, v in _specs().items()}


def _sha_file(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def fingerprint(config_dir):
    """{key: sha256}: one value per part, from its files' names and contents. A part with no file is left out."""
    out = {}
    for k, (_name, members) in parts(config_dir).items():
        h = hashlib.sha256()
        for m in sorted(members):
            h.update(m.encode("utf-8")); h.update(b"\0"); h.update(_sha_file(members[m]).encode("ascii")); h.update(b"\n")
        out[k] = h.hexdigest()
    return out


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def state(config_dir):
    """The version this PC is on. With no file: version 0, a draft, nothing remembered."""
    d = {}
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    v = d.get("version")
    return {"format": FORMAT, "version": v if isinstance(v, int) and v >= 0 else 0,
            "source": d.get("source") if d.get("source") in SOURCE_WORDS else DRAFT,
            "taken": str(d.get("taken") or ""), "by": str(d.get("by") or ""), "note": str(d.get("note") or ""),
            "parts": {str(k): str(x) for k, x in (d.get("parts") or {}).items()} if isinstance(d.get("parts"), dict) else {}}


def take(config_dir, version, source, by="", note="", when=None):
    """Remember this version as the one in use, with what the parts look like now. Returns the state saved."""
    st = {"format": FORMAT, "version": max(0, int(version)), "source": source if source in SOURCE_WORDS else DRAFT,
          "taken": (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"), "by": str(by or "")[:120],
          "note": str(note or "")[:600], "parts": fingerprint(config_dir)}
    os.makedirs(config_dir, exist_ok=True)
    tmp = _path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, _path(config_dir))
    return st


def changed(config_dir, st=None):
    """The keys of the parts that differ on this PC from the version it is on: changed, added or gone. With no version
    taken yet, every part there is."""
    st = st or state(config_dir)
    now, was = fingerprint(config_dir), st["parts"]
    if not st["version"]:
        return sorted(now)
    return sorted(k for k in set(now) | set(was) if now.get(k) != was.get(k))


def status(config_dir):
    """{"version", "draft", "source", "taken", "by", "note", "changed": [part names], "parts": how many}. draft is the
    number the next published version gets when this PC's parts differ from the version it is on (0 when they match)."""
    st = state(config_dir)
    ch = changed(config_dir, st)
    nm = names()
    return {"version": st["version"], "draft": st["version"] + 1 if ch or not st["version"] else 0, "source": st["source"],
            "taken": st["taken"], "by": st["by"], "note": st["note"], "changed": [nm.get(k, k) for k in ch],
            "parts": len(parts(config_dir))}


def line(config_dir):
    """The status in one sentence, as Settings shows it."""
    s = status(config_dir)
    n = f"{s['parts']} part" + ("" if s["parts"] == 1 else "s") + " on this PC"
    if not s["version"]:
        return f"Global Standards: not a version yet. {n}."
    head = f"Global Standards version {s['version']}, {SOURCE_WORDS[s['source']]}" + (f", taken {s['taken']}" if s["taken"] else "") + "."
    if not s["changed"]:
        return f"{head} {n}, all as that version has them."
    few = ", ".join(s["changed"][:6]) + (f" and {len(s['changed']) - 6} more" if len(s["changed"]) > 6 else "")
    return f"{head} Changes waiting on this PC: {few}."
