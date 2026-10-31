"""Custom dictionaries for Word (3.0.4): several named word lists kept with the app (the team's, for every effort), each
shown and edited in Settings; import an existing Word custom dictionary (.dic), add an effort's approved acronyms, and
export a .dic for Word (UTF-16 LE with a byte order mark, one word a line, as Word writes it), named with the date. Every
export is kept, dated, in the data folder; the dictionaries live in the config folder, so the backups carry them. Rules
only: no AI and no ML. Logs hold counts only."""
import datetime, json, os, re, shutil, uuid

FILE = "custom_dictionaries.json"
EXPORTS = "Dictionary exports"
MAX_WORD = 64
_BAD = re.compile(r"[\s\x00-\x1f]")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def clean_word(w):
    """One dictionary word, or '' when it cannot be one (empty, a space inside, too long)."""
    w = (w or "").strip().strip("﻿")
    if not w or _BAD.search(w) or len(w) > MAX_WORD:
        return ""
    return w


def sort_words(words):
    """Unique (exact spelling: Word's custom dictionaries are case-aware), sorted the way people read them."""
    seen, out = set(), []
    for w in words:
        w = clean_word(w)
        if w and w not in seen:
            seen.add(w); out.append(w)
    return sorted(out, key=lambda x: (x.casefold(), x))


class Store:
    """The dictionaries in the config folder: {"dicts": [{"id", "name", "words", "created", "changed", "exports"}]}."""

    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.path = os.path.join(config_dir, FILE)
        self.dicts = []
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.dicts = [d for d in data.get("dicts", []) if isinstance(d, dict) and d.get("id") and d.get("name")]
        except (OSError, ValueError):
            self.dicts = []
        for d in self.dicts:
            d["words"] = sort_words(d.get("words", []))
            d.setdefault("exports", [])
        return self

    def save(self):
        os.makedirs(self.config_dir, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"dicts": self.dicts}, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)

    def names(self):
        return [d["name"] for d in self.dicts]

    def get(self, did):
        return next((d for d in self.dicts if d["id"] == did), None)

    def by_name(self, name):
        return next((d for d in self.dicts if d["name"].casefold() == (name or "").strip().casefold()), None)

    def add(self, name, words=()):
        """A new dictionary; '' when the name is empty or already used."""
        name = " ".join((name or "").split())[:80]
        if not name or self.by_name(name):
            return ""
        d = {"id": uuid.uuid4().hex[:10], "name": name, "words": sort_words(words), "created": _now(), "changed": _now(), "exports": []}
        self.dicts.append(d)
        self.save()
        return d["id"]

    def rename(self, did, name):
        d = self.get(did)
        name = " ".join((name or "").split())[:80]
        other = self.by_name(name)
        if d is None or not name or (other is not None and other is not d):
            return False
        d["name"] = name; d["changed"] = _now()
        self.save()
        return True

    def remove(self, did):
        n = len(self.dicts)
        self.dicts = [d for d in self.dicts if d["id"] != did]
        if len(self.dicts) < n:
            self.save()
        return len(self.dicts) < n

    def add_words(self, did, words):
        """Adds the words not already in it; returns how many were new."""
        d = self.get(did)
        if d is None:
            return 0
        before = set(d["words"])
        d["words"] = sort_words(list(d["words"]) + list(words))
        n = len(set(d["words"]) - before)
        if n:
            d["changed"] = _now()
            self.save()
        return n

    def remove_words(self, did, words):
        d = self.get(did)
        if d is None:
            return 0
        gone = set(words)
        keep = [w for w in d["words"] if w not in gone]
        n = len(d["words"]) - len(keep)
        if n:
            d["words"] = keep; d["changed"] = _now()
            self.save()
        return n

    def replace_word(self, did, old, new):
        d = self.get(did)
        new = clean_word(new)
        if d is None or old not in d["words"] or not new:
            return False
        d["words"] = sort_words([new if w == old else w for w in d["words"]])
        d["changed"] = _now()
        self.save()
        return True

    # ------------------------------------------------------------ files
    def export_name(self, did, effort="", when=None):
        """'Sierra Space Custom 2026-10-30.dic', with the effort's name after the dictionary's when one is given."""
        d = self.get(did)
        when = when or datetime.date.today()
        base = " ".join(x for x in ((d or {}).get("name", "Custom"), effort or "", when.isoformat()) if x)
        return re.sub(r'[<>:"/\\|?*]+', "_", base) + ".dic"

    def export(self, did, path, data_dir=""):
        """Writes the .dic for Word; a dated copy is kept in data_dir's Dictionary exports. Returns the word count."""
        d = self.get(did)
        if d is None:
            return 0
        write_dic(path, d["words"])
        kept = ""
        if data_dir:
            folder = os.path.join(data_dir, EXPORTS)
            os.makedirs(folder, exist_ok=True)
            kept = os.path.join(folder, f"{datetime.datetime.now():%Y-%m-%d_%H%M} {os.path.basename(path)}")
            if os.path.abspath(kept) != os.path.abspath(path):
                shutil.copy2(path, kept)
        d["exports"] = (d.get("exports", []) + [{"at": _now(), "file": os.path.basename(path), "words": len(d["words"]),
                                                  "kept": os.path.basename(kept)}])[-50:]
        self.save()
        return len(d["words"])


def read_dic(path):
    """The words in a Word custom dictionary (UTF-16 with or without a byte order mark, UTF-8, or the Windows code page)."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw[3:].decode("utf-8", "replace")
    elif len(raw) > 1 and raw[1:2] == b"\x00":
        text = raw.decode("utf-16-le", "replace")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", "replace")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#LID"):                   # Word's language line in some dictionaries
            continue
        out.append(line)
    return [w for w in (clean_word(x) for x in out) if w]


def write_dic(path, words):
    """UTF-16 LE with a byte order mark and Windows line ends: how Word writes its own custom dictionaries."""
    body = "".join(w + "\r\n" for w in sort_words(words))
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(b"\xff\xfe" + body.encode("utf-16-le"))
    os.replace(tmp, path)
    return path


def from_effort(effort_list, include_proposed=False):
    """The acronyms an effort's list approved (and those still proposed, if asked), as dictionary words."""
    rows = getattr(effort_list, "rows", {}) or {}
    ok = ("Approved", "Proposed", "Needs author") if include_proposed else ("Approved",)
    return sort_words(t for t, r in rows.items() if (r or {}).get("Status", "") in ok)
