"""The author list (2.77.0): the one place names come from. Every author, section lead, contributor and owner picker
shows the names on this list that are set to show in the open effort. A name shows in every effort ("all") or in the
efforts named next to it. Names are typed in Settings or imported from a list (.txt, .csv, .xlsx); an import adds only
names that are not on the list yet and leaves every name already there exactly as it is. Kept in the config folder
(author_list.json) beside the efforts list. Nothing leaves the PC.
"""
import csv, datetime, json, os, re

FORMAT = 1
ALL = "all"
FILE = "author_list.json"
EXTS = (".xlsx", ".csv", ".txt")
_NAME_HEADS = ("name", "names", "author", "authors", "person", "people", "full name")
_EFF_HEADS = ("efforts", "effort", "shows in", "show in", "proposals", "proposal")


def clean(name):
    """One name: trimmed, inner spaces collapsed; '' for nothing usable."""
    n = " ".join(str(name or "").replace(" ", " ").split())
    n = n.strip(" ,;")
    if not n or len(n) > 80 or not re.search(r"[A-Za-z]", n):
        return ""
    return n


def key(name):
    return clean(name).casefold()


def _today():
    return datetime.date.today().isoformat()


def parse_efforts(text):
    """'All', 'All efforts' or '' (when blank means all) -> ALL; 'Heron; Osprey' -> ['Heron', 'Osprey']; None when blank."""
    t = " ".join(str(text or "").split())
    if not t:
        return None
    if t.casefold() in ("all", "all efforts", "any", "every effort", "*"):
        return ALL
    out = []
    for part in re.split(r"[;|\n]", t):
        p = " ".join(part.split())
        if p and p.casefold() not in [x.casefold() for x in out]:
            out.append(p)
    return out or None


def efforts_text(eff):
    if eff == ALL:
        return "All efforts"
    return "; ".join(eff) if eff else "No effort yet"


class AuthorList:
    def __init__(self, path):
        self.path = path
        self.people = []        # [{name, efforts: ALL | [effort names], added, source}]
        self.history = []       # [{at, what, added, kept}]
        self.exists = False

    # ------------------------------------------------------------ files
    def load(self):
        self.people, self.history = [], []
        self.exists = os.path.isfile(self.path)
        if self.exists:
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                for p in d.get("people", []):
                    n = clean(p.get("name"))
                    if n and not self.find(n):
                        eff = p.get("efforts", ALL)
                        eff = ALL if eff == ALL else [e for e in (eff or []) if isinstance(e, str) and e.strip()]
                        self.people.append({"name": n, "efforts": eff, "added": p.get("added", ""), "source": p.get("source", "")})
                self.history = [h for h in d.get("history", []) if isinstance(h, dict)][-100:]
            except (OSError, ValueError, AttributeError):
                self.people, self.history = [], []
        return self

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"format": FORMAT, "people": self.people, "history": self.history[-100:]}, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)
        self.exists = True

    def _log(self, what, added=0, kept=0):
        self.history.append({"at": datetime.datetime.now().isoformat(timespec="seconds"), "what": what, "added": added, "kept": kept})

    # ------------------------------------------------------------ reading
    def find(self, name):
        k = key(name)
        return next((p for p in self.people if p["name"].casefold() == k), None) if k else None

    def names(self):
        return sorted((p["name"] for p in self.people), key=str.casefold)

    def shows_in(self, p, effort):
        return p["efforts"] == ALL or (effort and effort.casefold() in [e.casefold() for e in p["efforts"]])

    def for_effort(self, effort):
        """The names that show in this effort's pickers ([] with no effort)."""
        if not effort:
            return []
        return sorted((p["name"] for p in self.people if self.shows_in(p, effort)), key=str.casefold)

    def on_list(self, name):
        return self.find(name) is not None

    # ------------------------------------------------------------ changing
    def add(self, name, efforts=ALL, source="typed", save=True):
        n = clean(name)
        if not n or self.find(n):
            return False
        eff = ALL if efforts == ALL else list(dict.fromkeys(e for e in (efforts or []) if e))
        self.people.append({"name": n, "efforts": eff, "added": _today(), "source": source})
        self._log("added", added=1)
        if save:
            self.save()
        return True

    def remove(self, names):
        ks = {key(n) for n in names}
        before = len(self.people)
        self.people = [p for p in self.people if p["name"].casefold() not in ks]
        gone = before - len(self.people)
        if gone:
            self._log("removed", kept=len(self.people))
            self.save()
        return gone

    def rename(self, old, new):
        p, n = self.find(old), clean(new)
        if p is None or not n or (self.find(n) and self.find(n) is not p):
            return False
        p["name"] = n
        self.save()
        return True

    def set_efforts(self, names, efforts):
        """efforts: ALL or a list of effort names (an empty list: no effort yet)."""
        eff = ALL if efforts == ALL else list(dict.fromkeys(e for e in (efforts or []) if e))
        n = 0
        for nm in names:
            p = self.find(nm)
            if p is not None:
                p["efforts"] = eff if eff == ALL else list(eff)
                n += 1
        if n:
            self.save()
        return n

    def show_in(self, name, effort, on, all_efforts=()):
        """Tick or untick one effort for one name. Unticking a name that shows in all efforts leaves it in every other
        known effort."""
        p = self.find(name)
        if p is None or not effort:
            return False
        if on:
            if p["efforts"] == ALL or effort.casefold() in [e.casefold() for e in p["efforts"]]:
                return False
            p["efforts"].append(effort)
        else:
            if p["efforts"] == ALL:
                p["efforts"] = [e for e in all_efforts if e.casefold() != effort.casefold()]
            elif effort.casefold() in [e.casefold() for e in p["efforts"]]:
                p["efforts"] = [e for e in p["efforts"] if e.casefold() != effort.casefold()]
            else:
                return False
        self.save()
        return True

    def effort_renamed(self, old, new):
        n = 0
        for p in self.people:
            if p["efforts"] != ALL:
                for i, e in enumerate(p["efforts"]):
                    if e.casefold() == old.casefold():
                        p["efforts"][i] = new
                        n += 1
        if n:
            self.save()
        return n

    # ------------------------------------------------------------ importing and exporting
    def merge(self, entries, default=ALL, source="imported"):
        """entries: [(name, efforts or None)]. Names already on the list are kept exactly as they are; new names are
        added with their efforts from the file, or default. Returns {added, kept, skipped}."""
        added, kept, skipped, seen = [], [], 0, set()
        for name, eff in entries:
            n = clean(name)
            if not n:
                skipped += 1
                continue
            if n.casefold() in seen:
                continue
            seen.add(n.casefold())
            if self.find(n):
                kept.append(n)
                continue
            e = default if eff is None else eff
            self.people.append({"name": n, "efforts": ALL if e == ALL else list(e or []), "added": _today(), "source": source})
            added.append(n)
        self._log("imported", added=len(added), kept=len(kept))
        self.save()
        return {"added": added, "kept": kept, "skipped": skipped}

    def export(self, path):
        rows = [(p["name"], efforts_text(p["efforts"])) for p in sorted(self.people, key=lambda p: p["name"].casefold())]
        if path.lower().endswith(".xlsx"):
            import openpyxl
            from openpyxl.styles import Font
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Author list"
            ws.append(["Name", "Efforts"])
            for c in ws[1]:
                c.font = Font(bold=True)
            for r in rows:
                ws.append(list(r))
            ws.column_dimensions["A"].width = 32; ws.column_dimensions["B"].width = 60
            wb.save(path)
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Name", "Efforts"])
                w.writerows(rows)
        return len(rows)


def read_file(path):
    """[(name, efforts or None)] from a list: .txt (one name per line), .csv or .xlsx (a Name column, else the first
    column; an optional Efforts column: 'All efforts' or effort names separated by semicolons)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return [(ln.strip(), None) for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    if ext == ".csv":
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            rows = [r for r in csv.reader(f)]
    elif ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [["" if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
    else:
        raise ValueError("Use a .txt, .csv or .xlsx file.")
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return []
    head = [str(c).strip().casefold() for c in rows[0]]
    ni = next((i for i, h in enumerate(head) if h in _NAME_HEADS), None)
    ei = next((i for i, h in enumerate(head) if h in _EFF_HEADS), None)
    body = rows[1:] if (ni is not None or ei is not None) else rows
    ni = 0 if ni is None else ni
    out = []
    for r in body:
        name = r[ni] if ni < len(r) else ""
        eff = parse_efforts(r[ei]) if ei is not None and ei < len(r) else None
        out.append((name, eff))
    return out


def load(config_dir):
    return AuthorList(os.path.join(config_dir, FILE)).load()


def seed(lst, efforts):
    """First start of 2.77.0: start the list from the names on each effort's team, so nothing disappears.
    efforts: [(effort name, [team names])]. Each name shows in the efforts whose team it was on."""
    if lst.exists:
        return 0
    found = {}
    for eff, names in efforts:
        for n in names:
            c = clean(n)
            if c:
                found.setdefault(c.casefold(), [c, []])[1].append(eff)
    if not found:                               # nothing to start from: write nothing (a new PC, the build's self-test)
        return 0
    for _k, (n, effs) in sorted(found.items()):
        lst.people.append({"name": n, "efforts": list(dict.fromkeys(effs)), "added": _today(), "source": "from the effort's team"})
    lst._log("started from the efforts' teams", added=len(found))
    lst.save()
    return len(found)
