"""Customer document versions and compare (2.37.0). Rules and counts only (No AI); nothing leaves the PC.

Every customer document the effort receives is kept as a document with versions (Original, Amendment 1, Rev B...).
Each version records when it arrived, who added it, the file name, its SHA-256 fingerprint and a copy of the text
read from it (sentence by sentence, with the RFP section each sentence sits under). The copy lets any two versions
be compared later even if the file is moved, replaced or deleted, and the fingerprint shows the file is the one read.

Stored in the effort's folder (workspace): documents\\index.json and documents\\<version id>.json. Saved at once.

When a new file arrives the library suggests which document it is a new version of: by name (the name with version
words such as Amendment 2, Amd1, Rev B, v3, dates and copy marks removed) and by how much of the text is the same.
A person confirms every match.

Compare: sentences are lined up in reading order (difflib over the sentence lists); a removed sentence next to an
added one in the same place is paired as Changed when they are at least 50% alike, with a word diff. The result
says which changes touch submission requirements (format, page limits, due dates, files and copies).
"""
import datetime, difflib, getpass, hashlib, json, os, re, uuid

VERSION_WORDS = re.compile(
    r"(?<![a-z])(?:amend(?:ment)?|amd|mod(?:ification)?|ver(?:sion)?|v|r)[\s_.-]*(?:no\.?\s*)?\d{1,3}(?![a-z])|"
    r"(?<![a-z])rev(?:ision)?[\s_.-]*(?:\d{1,3}|[a-z])?(?![a-z])|"
    r"(?<![a-z])(?:draft|final|updated?|conformed|clean|redline|copy)(?![a-z])|\(\d+\)|"
    r"\b\d{4}[-_.]\d{2}[-_.]\d{2}\b|\b\d{1,2}[-_.]\d{1,2}[-_.]\d{2,4}\b|"
    r"(?<![a-z])(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s_-]*\d{1,4}(?![a-z])", re.I)
PAGE_LIMIT = re.compile(r"\b(?:exceed|limit(?:ed)?|maximum|no more than|up to)\b[^.]{0,40}\b\d{1,3}\s*(?:-\s*)?pages?\b|"
                        r"\b\d{1,3}[- ]page (?:limit|maximum)\b", re.I)
STRONG, POSSIBLE = 0.6, 0.3


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def short_sha(h):
    return f"{h[:4]} {h[4:8]} ... {h[-4:]}" if h else ""


def stem(name):
    """'Kestrel_RFP_CLM_Amd2 (1).docx' -> 'kestrel rfp clm'."""
    s = os.path.splitext(os.path.basename(name or ""))[0]
    s = VERSION_WORDS.sub(" ", s)
    s = re.sub(r"[_\-.]+", " ", s)
    return " ".join(w for w in s.lower().split() if w)


def display_name(name):
    """'Kestrel_RFP_CLM_Amd2 (1).docx' -> 'Kestrel RFP CLM' (the file's own capitals kept)."""
    s = os.path.splitext(os.path.basename(name or ""))[0]
    s = VERSION_WORDS.sub(" ", s)
    s = re.sub(r"[_]+", " ", s)
    return " ".join(s.split()).strip(" -.") or os.path.basename(name or "")


def name_similarity(a, b):
    sa, sb = stem(a), stem(b)
    if not sa or not sb:
        return 0.0
    if sa == sb:
        return 1.0
    return difflib.SequenceMatcher(None, sa, sb).ratio()


def _shingles(sents, n=5):
    out = set()
    for s in sents:
        w = re.findall(r"[a-z0-9]+", s.lower())
        for i in range(max(1, len(w) - n + 1)):
            out.add(" ".join(w[i:i + n]))
    return out


def text_similarity(a_sents, b_sents):
    """Share of word runs in common (0 to 1)."""
    A, B = _shingles(a_sents), _shingles(b_sents)
    if not A or not B:
        return 0.0
    return len(A & B) / max(1, min(len(A), len(B)))


# ------------------------------------------------------------------ reading a file
def snapshot(name, chunks):
    """[(location label, text)] from the file reader -> [{"s": section, "t": section title, "x": text, "l": where}]."""
    import compliance as C
    heads = []
    items = C.extract([(name, chunks)], heads)
    return [{"s": it.get("section", ""), "t": it.get("section_title", ""), "x": ((it.get("lead") + " ") if it.get("lead") else "") + it["text"],
             "l": it.get("loc", "")} for it in items]


# ------------------------------------------------------------------ what each customer document is (2.68.0)
DOC_TYPES = ("RFP", "Amendment", "SOW", "SOO", "PWS", "Section L", "Section M", "Q&A", "Attachment", "CDRL", "DD 254", "Other")
TYPE_INITIAL = {"RFP": "R", "Amendment": "A", "SOW": "S", "SOO": "O", "PWS": "P", "Section L": "L", "Section M": "M", "Q&A": "Q",
                "Attachment": "J", "CDRL": "C", "DD 254": "D", "Other": "X"}


def clean_initial(text):
    """An initial: letters and digits only, upper case, at most 6 characters."""
    import re
    return re.sub(r"[^A-Za-z0-9]", "", text or "").upper()[:6]


def guess_type(name):
    """The document type a file name suggests (the person confirms it)."""
    import re
    n = (name or "").lower()
    for pat, t in ((r"amend|\bamd\b|_amd|amd\d|\bmod\b", "Amendment"), (r"\bsow\b|statement[\s_-]*of[\s_-]*work", "SOW"),
                   (r"\bsoo\b|statement[\s_-]*of[\s_-]*objectives", "SOO"), (r"\bpws\b|performance[\s_-]*work", "PWS"),
                   (r"q\s*&\s*a|questions|\bqa\b", "Q&A"), (r"cdrl", "CDRL"), (r"dd[\s_-]*254", "DD 254"),
                   (r"attachment|\batt\b|exhibit|\bj-\d", "Attachment"), (r"section[\s_]*l\b", "Section L"),
                   (r"section[\s_]*m\b", "Section M"), (r"\brfp\b|solicitation|\brfq\b", "RFP")):
        if re.search(pat, n.replace("_", " ")):
            return t
    return "RFP"


# ------------------------------------------------------------------ the library
class Library:
    def __init__(self, folder):
        self.folder = folder                       # <effort app data>\documents
        self.docs = []                             # [{"id", "name", "versions": [version...]}], versions oldest first

    @property
    def index_path(self):
        return os.path.join(self.folder, "index.json")

    def load(self):
        import workspace as W
        d = W.read_json(self.index_path, None) or {}
        self.docs = d.get("docs", [])
        return self

    def save(self):
        import workspace as W
        W.write_json(self.index_path, {"v": 1, "docs": self.docs})

    def text(self, version):
        import workspace as W
        return W.read_json(os.path.join(self.folder, version["id"] + ".json"), None) or []

    def _write_text(self, vid, sents):
        import workspace as W
        W.write_json(os.path.join(self.folder, vid + ".json"), sents)

    def doc(self, doc_id):
        return next((d for d in self.docs if d["id"] == doc_id), None)

    def find_sha(self, h):
        for d in self.docs:
            for v in d["versions"]:
                if v.get("sha256") == h:
                    return d, v
        return None

    def files(self):
        return {v.get("file", "").lower() for d in self.docs for v in d["versions"]}

    def latest(self, d):
        return d["versions"][-1] if d.get("versions") else None

    def suggest(self, name, sents):
        """[(doc, score, how)] best first: how the new file matches each document."""
        out = []
        for d in self.docs:
            last = self.latest(d)
            if last is None:
                continue
            ns = max(name_similarity(name, last.get("file", "")), name_similarity(name, d["name"]))
            ts = text_similarity(sents, [s["x"] for s in self.text(last)]) if sents else 0.0
            score = max(ts, 0.5 * ns + 0.5 * ts, ns if ns >= 0.95 and ts >= 0.15 else 0)
            how = f"{int(round(ts * 100))}% of the text is the same" + ("; the name matches" if ns >= 0.9 else "")
            out.append((d, round(score, 3), how))
        out.sort(key=lambda x: -x[1])
        return out

    @staticmethod
    def band(score):
        return "strong" if score >= STRONG else "possible" if score >= POSSIBLE else ""

    def next_label(self, d):
        n = len(d["versions"])
        return f"Amendment {n}" if n else "Original"

    def add(self, path, sents, doc_id=None, doc_name="", label="", sha=None, when=None, who=None, initial="", dtype=""):
        """Add a file as a new version of doc_id, or as a new document (2.68.0: with its initial and type). Returns
        (doc, version)."""
        h = sha or sha256(path)
        d = self.doc(doc_id) if doc_id else None
        if d is None:
            d = {"id": uuid.uuid4().hex[:12], "name": doc_name or display_name(path), "versions": [],
                 "initial": clean_initial(initial) if clean_initial(initial) not in self.initials() else "",
                 "type": dtype if dtype in DOC_TYPES else ""}
            self.docs.append(d)
        v = {"id": uuid.uuid4().hex[:12], "label": label or self.next_label(d), "file": os.path.basename(path),
             "added": when or datetime.datetime.now().isoformat(timespec="minutes"), "who": who or getpass.getuser(),
             "sha256": h, "sentences": len(sents), "reviewed": "", "path": os.path.abspath(path)}
        self._write_text(v["id"], sents)
        d["versions"].append(v)
        self.save()
        return d, v

    def move_version(self, vid, to_doc_id, label=""):
        """'This file is a version of another document': move a version (keeps its text and fingerprint)."""
        src = next((d for d in self.docs if any(v["id"] == vid for v in d["versions"])), None)
        dst = self.doc(to_doc_id)
        if src is None or dst is None or src is dst:
            return False
        v = next(v for v in src["versions"] if v["id"] == vid)
        src["versions"].remove(v)
        v["label"] = label or self.next_label(dst)
        dst["versions"].append(v)
        dst["versions"].sort(key=lambda x: x.get("added", ""))
        if not src["versions"]:
            self.docs.remove(src)
        self.save()
        return True

    def rename(self, doc_id=None, vid=None, name=""):
        name = " ".join((name or "").split())
        if not name:
            return False
        for d in self.docs:
            if doc_id and d["id"] == doc_id:
                d["name"] = name
            for v in d["versions"]:
                if vid and v["id"] == vid:
                    v["label"] = name
        self.save()
        return True

    # ------------------------------------------------------------ identity (2.68.0)
    def initials(self, but=None):
        return {d.get("initial", "") for d in self.docs if d.get("initial") and d["id"] != but}

    def suggest_initial(self, dtype, taken=()):
        """The type's letter, numbered when taken (R, R2...; amendments A1, A2...)."""
        base = TYPE_INITIAL.get(dtype, "X")
        used = self.initials() | set(taken)
        if dtype == "Amendment":
            n = 1
            while f"{base}{n}" in used:
                n += 1
            return f"{base}{n}"
        if base not in used:
            return base
        n = 2
        while f"{base}{n}" in used:
            n += 1
        return f"{base}{n}"

    def check_identity(self, initial, dtype, doc_id=None):
        """'' when fine, else what is wrong (the person sees it)."""
        ini = clean_initial(initial)
        if not ini:
            return "Give the document an initial (letters and digits, up to 6)."
        if dtype not in DOC_TYPES:
            return "Pick the document's type."
        if ini in self.initials(but=doc_id):
            return f"Another document already uses {ini}."
        return ""

    def set_identity(self, doc_id, initial, dtype):
        """The document's initial and type. Returns '' when set, else why not."""
        d = self.doc(doc_id)
        if d is None:
            return "No such document."
        why = self.check_identity(initial, dtype, doc_id)
        if why:
            return why
        d["initial"], d["type"] = clean_initial(initial), dtype
        self.save()
        return ""

    def missing_identity(self):
        return [d for d in self.docs if not d.get("initial") or not d.get("type")]

    def doc_of_file(self, file_name):
        f = os.path.basename(file_name or "").lower()
        return next((d for d in self.docs if any(v.get("file", "").lower() == f for v in d["versions"])), None)

    def identity_map(self):
        """{file name: {"initial", "type", "doc"}} for every version of every document."""
        return {v.get("file", ""): {"initial": d.get("initial", ""), "type": d.get("type", ""), "doc": d["name"]}
                for d in self.docs for v in d["versions"] if v.get("file")}

    def mark_reviewed(self, vid, who=None):
        for d in self.docs:
            for v in d["versions"]:
                if v["id"] == vid:
                    v["reviewed"] = f"{datetime.date.today().isoformat()} {who or getpass.getuser()}"
                    self.save()
                    return True
        return False

    def counts(self):
        return {"docs": len(self.docs), "versions": sum(len(d["versions"]) for d in self.docs),
                "unreviewed": sum(1 for d in self.docs for v in d["versions"][1:] if not v.get("reviewed"))}


# ------------------------------------------------------------------ compare
def _words(s):
    return s.split()


def word_diff(old, new):
    """[(kind, text)] with kind '=' same, '-' removed, '+' added."""
    a, b = _words(old), _words(new)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(("=", " ".join(a[i1:i2])))
        if op in ("delete", "replace"):
            out.append(("-", " ".join(a[i1:i2])))
        if op in ("insert", "replace"):
            out.append(("+", " ".join(b[j1:j2])))
    return out


def is_submission(text):
    """Does a sentence set a submission requirement (format, page limits, due dates, files and copies)?"""
    import compliance as C
    return bool(C._FORMAT.search(text or "") or PAGE_LIMIT.search(text or ""))


def compare(old, new, pair_ratio=0.5):
    """old, new: snapshots. Returns [{"kind": same|changed|added|removed, "old", "new", "section", "diff",
    "submission"}] in reading order."""
    A = [s["x"] for s in old]
    B = [s["x"] for s in new]
    rows = []

    def sec(s):
        return " ".join(x for x in (s.get("s", ""), s.get("t", "")) if x)

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                rows.append({"kind": "same", "old": A[i1 + k], "new": B[j1 + k], "section": sec(new[j1 + k]), "diff": []})
            continue
        olds = list(range(i1, i2))
        news = list(range(j1, j2))
        used, block = set(), []
        for oi in olds:                            # pair each removed sentence with its closest added one
            best, score = None, 0.0
            for nj in news:
                if nj in used:
                    continue
                r = difflib.SequenceMatcher(None, A[oi], B[nj], autojunk=False).ratio()
                if r > score:
                    best, score = nj, r
            if best is not None and score >= pair_ratio:
                used.add(best)
                block.append((best, {"kind": "changed", "old": A[oi], "new": B[best], "section": sec(new[best]),
                                     "diff": word_diff(A[oi], B[best])}))
            else:                                  # a removed sentence sits where it stood, before what follows it
                block.append((j1 + (oi - i1) - 0.5, {"kind": "removed", "old": A[oi], "new": "", "section": sec(old[oi]), "diff": []}))
        for nj in news:
            if nj not in used:
                block.append((nj, {"kind": "added", "old": "", "new": B[nj], "section": sec(new[nj]), "diff": []}))
        rows += [r for _k, r in sorted(block, key=lambda x: x[0])]
    for r in rows:
        r["submission"] = r["kind"] != "same" and (is_submission(r["old"]) or is_submission(r["new"]))
    return rows


def summary(rows):
    c = {"changed": 0, "added": 0, "removed": 0, "same": 0, "submission": 0}
    for r in rows:
        c[r["kind"]] += 1
        c["submission"] += 1 if r.get("submission") else 0
    return c


def summary_text(c):
    return (f"{c['changed']} changed, {c['added']} added, {c['removed']} removed" +
            (f"; {c['submission']} {'touches' if c['submission'] == 1 else 'touch'} submission requirements" if c["submission"] else ""))


# ------------------------------------------------------------------ exports
def export_redline(path, doc_name, v_old, v_new, rows, only_changes=True):
    """A Word file: every sentence in reading order, removed words struck through in red, added words green."""
    import docxw
    d = docxw.Doc()
    d.props = {"StationkeeperCompare": f"{doc_name}: {v_old['label']} to {v_new['label']}"}
    d.heading(f"{doc_name}: {v_old['label']} compared with {v_new['label']}", 1)
    d.para(f"{v_old['label']}: {v_old['file']}, added {v_old['added']} by {v_old['who']}, SHA-256 {v_old['sha256']}")
    d.para(f"{v_new['label']}: {v_new['file']}, added {v_new['added']} by {v_new['who']}, SHA-256 {v_new['sha256']}")
    d.para(summary_text(summary(rows)) + f". Built {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} by Stationkeeper.", bold=True)
    sec = None
    for r in rows:
        if only_changes and r["kind"] == "same":
            continue
        if r["section"] and r["section"] != sec:
            d.heading(r["section"], 3)
            sec = r["section"]
        tag = {"same": "", "changed": "Changed", "added": "Added", "removed": "Removed"}[r["kind"]]
        parts = []
        if r["kind"] == "changed":
            for k, t in r["diff"]:
                st = {"-": {"strike": True, "color": "B91C1C"}, "+": {"bold": True, "color": "15803D"}}.get(k, {})
                parts.append((t + " ", st))
        elif r["kind"] == "added":
            parts.append((r["new"], {"bold": True, "color": "15803D"}))
        elif r["kind"] == "removed":
            parts.append((r["old"], {"strike": True, "color": "B91C1C"}))
        else:
            parts.append((r["new"], {}))
        if tag:
            parts.append(("   [" + tag + (", submission requirement" if r.get("submission") else "") + "]", {"size": 16, "color": "475569"}))
        d.rich(parts)
    d.save(path)
    return path


def export_list(path, lib, doc=None, compares=()):
    """Excel: the version history (every document or one) and, for each (doc, old, new, rows) in compares, a sheet
    of the changes. The trail: dates, who, file names and fingerprints."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    wb = Workbook()
    ws = wb.active; ws.title = "Version history"
    ws.append(["Document", "Version", "File", "Added", "Added by", "SHA-256", "Sentences", "Reviewed"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for d in ([doc] if doc else lib.docs):
        for v in d["versions"]:
            ws.append([d["name"], v["label"], v["file"], v["added"], v["who"], v["sha256"], v.get("sentences", ""), v.get("reviewed", "")])
    for col, w in zip("ABCDEFGH", (34, 16, 40, 18, 16, 70, 10, 22)):
        ws.column_dimensions[col].width = w
    for d, vo, vn, rows in compares:
        s = wb.create_sheet(re.sub(r"[\[\]:*?/\\]", "", f"{vo['label'][:12]} to {vn['label'][:12]}")[:31])
        s.append([f"{d['name']}: {vo['label']} ({vo['file']}) to {vn['label']} ({vn['file']})"])
        s.append(["Change", "Section", "Before", "After", "Words removed", "Words added", "Submission requirement"])
        for c in s[2]:
            c.font = Font(bold=True)
        for r in rows:
            if r["kind"] == "same":
                continue
            s.append([r["kind"].title(), r["section"], r["old"], r["new"],
                      " ".join(t for k, t in r["diff"] if k == "-"), " ".join(t for k, t in r["diff"] if k == "+"),
                      "Yes" if r.get("submission") else ""])
        for col, w in zip("ABCDEFG", (10, 26, 60, 60, 24, 24, 12)):
            s.column_dimensions[col].width = w
        for row in s.iter_rows(min_row=3):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)
    return path
