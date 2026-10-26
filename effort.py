"""Effort List: one Excel workbook per effort (proposal), the keeper of every term found, chosen and approved.

Sheets:
  Effort List   one row per term (columns below). People may edit it in Excel; the app re-reads it on every scan.
  History       date, Windows user, term, change: an audit trail of what changed through the app.
  About         effort name, first-use rule, created date.

Writes are atomic (temporary file, then replace), so a crash never leaves half a workbook. When Excel has the file
open, Windows refuses the replace: the app says so and keeps the change pending until it can save.

The list holds customer content (terms, definitions, wording). It lives on this PC or a synced SharePoint folder only.
"""
import datetime, json, os, re, tempfile
import alt_forms as A

COLUMNS = ["Term", "Type", "Definition", "Alt forms", "Source", "Customer document", "Customer wording", "Other definitions",
           "Status", "SS Approver", "Approved on", "Used in volumes", "First use", "Notes",
           "Found in", "First found", "Last found", "Scan status", "Effort", "Client", "Solicitation"]   # 2.14.0: last 7
WIDTHS = [14, 14, 42, 18, 14, 30, 50, 36, 14, 22, 13, 24, 30, 30, 44, 12, 12, 30, 22, 18, 18]
SCAN_NEW, SCAN_FOUND, SCAN_GONE = "New in this scan", "Found", "No longer found in"
STATUSES = ["Proposed", "Needs author", "Approved", "Rejected"]
FIRST_USE_RULES = {"volume": "Restarts in each volume", "section": "Restarts in each section of each volume",
                   "submission": "Runs across the whole submission"}
SHEET, HIST, ABOUT = "Effort List", "History", "About"
KEYWORDS = "Keywords"                       # 2.16.0 Keyword Harvest: the effort's SharePoint keywords
KW_COLUMNS = ["Keyword", "Category", "Status", "Source", "Why", "Added by", "Date", "SharePoint field"]
KW_CATEGORIES = ["Customer emphasis", "Shared language", "Our response", "Our solution", "Differentiator", "Offering", "Acronym", "Other"]
KW_STATUSES = ["Proposed", "Keep", "Reject"]


class ListLocked(Exception):
    """The workbook is open in Excel (or another program), so it cannot be replaced right now."""


def user_name():
    return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"


def today():
    return datetime.date.today().isoformat()


def lock_file(path):
    """Excel's owner file (~$Name.xlsx) next to the workbook while it is open."""
    d, n = os.path.split(path)
    return os.path.join(d, "~$" + n[2:] if len(n) > 2 else "~$" + n)


def open_in_excel(path):
    return os.path.exists(lock_file(path)) or os.path.exists(os.path.join(os.path.dirname(path), "~$" + os.path.basename(path)))


class EffortList:
    def __init__(self, path, name="", first_use="volume", client="", solicitation="", internal_no=""):
        self.path = path
        self.name = name or os.path.splitext(os.path.basename(path))[0]
        self.client, self.solicitation, self.internal_no = client, solicitation, internal_no
        self.first_use = first_use if first_use in FIRST_USE_RULES else "volume"
        self.rows = {}          # term -> {column: value}
        self.order = []         # terms in sheet order
        self.history = []       # [date, user, term, change]
        self.pending = False    # changes not yet saved (file was locked)
        self.keywords = []      # [{column: value}] in sheet order (2.16.0)

    # ------------------------------------------------------------ read
    def load(self):
        """Read the workbook. A missing file is an empty list (created on first save)."""
        self.rows, self.order, self.history, self.keywords = {}, [], [], []
        if not os.path.isfile(self.path):
            return self
        from openpyxl import load_workbook
        wb = load_workbook(self.path, read_only=True, data_only=True)
        try:
            ws = wb[SHEET] if SHEET in wb.sheetnames else wb.worksheets[0]
            it = ws.iter_rows(values_only=True)
            header = [str(h or "").strip() for h in next(it, [])]
            idx = {h: i for i, h in enumerate(header)}
            for vals in it:
                vals = list(vals or [])
                term = str(vals[idx["Term"]] if "Term" in idx and idx["Term"] < len(vals) and vals[idx["Term"]] is not None else "").strip()
                if not term:
                    continue
                row = {}
                for c in COLUMNS:
                    v = vals[idx[c]] if c in idx and idx[c] < len(vals) else None
                    if isinstance(v, (datetime.date, datetime.datetime)):
                        v = v.date().isoformat() if isinstance(v, datetime.datetime) else v.isoformat()
                    row[c] = "" if v is None else str(v).strip()
                if row["Status"] not in STATUSES:
                    row["Status"] = _norm_status(row["Status"])
                primary, alts = A.split_term(term)       # "TT&C (TTC)" typed in Excel: primary with an alt form (2.26.0)
                if alts:
                    term = primary
                    row["Term"] = primary
                    row["Alt forms"] = A.merge_alts(row["Alt forms"], alts)
                if term not in self.rows:
                    self.order.append(term)
                self.rows[term] = row
            if HIST in wb.sheetnames:
                hit = wb[HIST].iter_rows(values_only=True)
                next(hit, None)
                self.history = [[("" if v is None else str(v)) for v in (list(r) + ["", "", "", ""])[:4]] for r in hit if r and any(r)]
            if KEYWORDS in wb.sheetnames:
                kit = wb[KEYWORDS].iter_rows(values_only=True)
                khead = [str(h or "").strip() for h in next(kit, [])]
                for vals in kit:
                    k = {c: ("" if i >= len(vals or []) or vals[i] is None else str(vals[i]).strip())
                         for c in KW_COLUMNS for i in [khead.index(c) if c in khead else 999]}
                    if k["Keyword"]:
                        k["Status"] = k["Status"] if k["Status"] in KW_STATUSES else "Proposed"
                        self.keywords.append(k)
            if ABOUT in wb.sheetnames:
                for r in wb[ABOUT].iter_rows(values_only=True):
                    if r and r[0] == "First use" and len(r) > 1:
                        t = str(r[1]).lower()
                        self.first_use = "submission" if "submission" in t else "section" if "section" in t else "volume"
                    if r and r[0] == "Effort" and len(r) > 1 and r[1]:
                        self.name = str(r[1])
                    if r and r[0] in ("Client", "Solicitation", "Internal number") and len(r) > 1 and r[1]:
                        setattr(self, {"Client": "client", "Solicitation": "solicitation", "Internal number": "internal_no"}[r[0]], str(r[1]))
        finally:
            wb.close()
        return self

    # ------------------------------------------------------------ change
    def get(self, term):
        return self.rows.get(term)

    def add_or_update(self, term, change_note=None, **fields):
        """Add a term or update its fields. Returns 'added', 'updated' or 'unchanged'."""
        term = term.strip()
        if not term:
            return "unchanged"
        row = self.rows.get(term)
        if row is None:
            row = {c: "" for c in COLUMNS}
            row["Term"], row["Status"] = term, "Proposed"
            for k, v in fields.items():
                if k in row and v is not None:
                    row[k] = str(v)
            self.rows[term] = row; self.order.append(term)
            self._hist(term, change_note or f"added ({row['Status']}): {row['Definition'][:80]}")
            return "added"
        changed = []
        for k, v in fields.items():
            if k in row and v is not None and str(v) != row[k]:
                if k == "Definition" and row[k] and str(v) and row[k] != str(v):
                    others = [o for o in re.split(r"\s*\|\s*", row["Other definitions"]) if o]
                    if row[k] not in others:
                        others.append(row[k])
                    row["Other definitions"] = " | ".join(others)
                row[k] = str(v); changed.append(k)
        if changed:
            self._hist(term, change_note or "changed " + ", ".join(changed))
            return "updated"
        return "unchanged"

    # ------------------------------------------------------------ alternate forms (2.26.0)
    def alts(self, term):
        row = self.rows.get(term)
        return A.parse_alts(row["Alt forms"]) if row else []

    def alt_map(self):
        """{alt form: primary term} for every row that is not Rejected."""
        out = {}
        for t, r in self.rows.items():
            if r.get("Status") != "Rejected":
                for a in A.parse_alts(r.get("Alt forms", "")):
                    out.setdefault(a, t)
        return out

    def set_alts(self, term, alts, note=None):
        """Replace a row's alternate forms. An alt form that had a row of its own is folded in: its row is removed
        (its places and volumes stay on the primary). Returns the folded terms."""
        row = self.rows.get(term)
        if row is None:
            return []
        new = [a for a in A.parse_alts(A.merge_alts(alts)) if a != term]
        old = A.parse_alts(row["Alt forms"])
        folded = []
        for a in new:
            other = self.rows.get(a)
            if other is not None and a != term:
                for col in ("Used in volumes", "Found in"):
                    have = [x for x in re.split(r"\s*;\s*", row.get(col, "")) if x]
                    for x in re.split(r"\s*;\s*", other.get(col, "")):
                        if x and x not in have:
                            have.append(x)
                    row[col] = "; ".join(have)
                for b in A.parse_alts(other.get("Alt forms", "")):
                    if b != term and b not in new:
                        new.append(b)
                del self.rows[a]
                self.order = [t for t in self.order if t != a]
                self._hist(a, f"made an alt form of {term}")
                folded.append(a)
        row["Alt forms"] = " | ".join(new)
        if new != old:
            self._hist(term, note or ("alt forms: " + (", ".join(new) or "none")))
        return folded

    def add_alt(self, term, alt):
        return self.set_alts(term, A.parse_alts(self.rows[term]["Alt forms"]) + [alt]) if term in self.rows else []

    def set_status(self, terms, status, approver=None, note=None):
        if status not in STATUSES:
            raise ValueError("unknown status")
        n = 0
        for t in terms:
            row = self.rows.get(t)
            if row is None:
                continue
            row["Status"] = status
            if status == "Approved":
                if approver:
                    names = [a for a in re.split(r"\s*;\s*", row["SS Approver"]) if a]
                    for a in re.split(r"\s*;\s*", approver):
                        if a and a not in names:
                            names.append(a)
                    row["SS Approver"] = "; ".join(names)
                row["Approved on"] = today()
            if note:
                row["Notes"] = (row["Notes"] + "; " if row["Notes"] else "") + note
            self._hist(t, f"status {status}" + (f" by {approver}" if approver and status == "Approved" else ""))
            n += 1
        return n

    def record_scan(self, found, scanned_files, when=None):
        """After a scan: found = {term: set(file names)}; scanned_files = the files this scan read.
        Updates Found in, First found, Last found and Scan status for terms already in the list. Returns
        {"found": n, "gone": [terms]}. A term is 'No longer found in <file>' when a file it was found in was read
        again and no longer has it; nothing is removed."""
        when = when or today()
        scanned = set(scanned_files)
        gone = []
        n = 0
        for t, row in self.rows.items():
            had = [f for f in re.split(r"\s*;\s*", row.get("Found in", "")) if f]
            now = set(found.get(t, ()))
            if now:
                n += 1
                merged = sorted(set(had) | now, key=str.lower)
                row["Found in"] = "; ".join(merged)
                row["First found"] = row.get("First found") or when
                row["Last found"] = when
                missing = sorted(set(f for f in had if f in scanned) - now, key=str.lower)
                row["Scan status"] = (f"{SCAN_GONE} {', '.join(missing)}" if missing else SCAN_FOUND)
            else:
                missing = sorted(f for f in had if f in scanned)
                if missing:
                    status = f"{SCAN_GONE} {', '.join(missing)}"
                    if row.get("Scan status") != status:
                        self._hist(t, status)
                    row["Scan status"] = status
                    gone.append(t)
        if n or gone:
            self.pending = True
        return {"found": n, "gone": gone}

    def remove(self, term):
        if term in self.rows:
            del self.rows[term]; self.order.remove(term)
            self._hist(term, "removed from the list")
            return True
        return False

    # ------------------------------------------------------------ keywords (2.16.0)
    def keyword(self, text):
        k = " ".join((text or "").split()).casefold()
        return next((x for x in self.keywords if x["Keyword"].casefold() == k), None)

    def add_keyword(self, text, category="Other", source="", why="", status="Proposed", field=""):
        """Add a keyword. Returns 'added', 'exists' or 'empty'. The same words (any case or spacing) are one keyword."""
        text = " ".join((text or "").split()).strip(" .,;:")[:120]
        if not text:
            return "empty"
        if self.keyword(text):
            return "exists"
        self.keywords.append({"Keyword": text, "Category": category if category in KW_CATEGORIES else "Other",
                              "Status": status if status in KW_STATUSES else "Proposed", "Source": source[:200],
                              "Why": why[:400], "Added by": user_name(), "Date": today(), "SharePoint field": field})
        self._hist("(keyword)", f"keyword added: {text}" + (f" (from {source[:60]})" if source else ""))
        return "added"

    def update_keyword(self, text, **fields):
        k = self.keyword(text)
        if not k:
            return False
        changed = [c for c, v in fields.items() if c in KW_COLUMNS and v is not None and str(v) != k[c]]
        for c in changed:
            k[c] = str(fields[c])
        if changed:
            self._hist("(keyword)", f"keyword {k['Keyword']}: " + ", ".join(f"{c} {k[c]}" for c in changed)[:200])
        return bool(changed)

    def remove_keyword(self, text):
        k = self.keyword(text)
        if k:
            self.keywords.remove(k)
            self._hist("(keyword)", f"keyword removed: {k['Keyword']}")
        return bool(k)

    def _hist(self, term, change):
        self.history.append([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), user_name(), term, change])
        self.pending = True

    # ------------------------------------------------------------ write
    def save(self):
        """Write the workbook atomically. Raises ListLocked when Excel holds it open."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
        d = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(d, exist_ok=True)
        wb = Workbook()
        ws = wb.active; ws.title = SHEET
        ws.append(COLUMNS)
        head = PatternFill("solid", fgColor="1E3A8A")
        for i, c in enumerate(ws[1], 1):
            c.font = Font(bold=True, color="FFFFFF"); c.fill = head
            ws.column_dimensions[c.column_letter].width = WIDTHS[i - 1]
        fills = {"Approved": "E7F6EC", "Needs author": "FEF3E2", "Rejected": "EEEEEE", "Proposed": None}
        for t in self.order:
            r = self.rows[t]
            r["Effort"], r["Client"], r["Solicitation"] = self.name, self.client, self.solicitation   # every row says whose it is
            ws.append([r.get(c, "") for c in COLUMNS])
            f = fills.get(r.get("Status"))
            if f:
                for c in ws[ws.max_row]:
                    c.fill = PatternFill("solid", fgColor=f)
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(COLUMNS)).column_letter}{max(2, ws.max_row)}"
        dv = DataValidation(type="list", formula1='"' + ",".join(STATUSES) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        col = ws.cell(row=1, column=COLUMNS.index("Status") + 1).column_letter
        dv.add(f"{col}2:{col}5000")
        ks = wb.create_sheet(KEYWORDS)                 # 2.16.0
        ks.append(KW_COLUMNS)
        for c in ks[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = head
        for k in self.keywords:
            ks.append([k.get(c, "") for c in KW_COLUMNS])
        for col, w in zip("ABCDEFGH", (34, 18, 11, 34, 60, 14, 12, 18)):
            ks.column_dimensions[col].width = w
        ks.freeze_panes = "A2"
        kdv = DataValidation(type="list", formula1='"' + ",".join(KW_STATUSES) + '"', allow_blank=True)
        ks.add_data_validation(kdv); kdv.add("C2:C2000")
        hs = wb.create_sheet(HIST)
        hs.append(["Date", "User", "Term", "Change"])
        for c in hs[1]:
            c.font = Font(bold=True)
        for h in self.history:
            hs.append(h)
        for col, w in zip("ABCD", (17, 14, 16, 70)):
            hs.column_dimensions[col].width = w
        ab = wb.create_sheet(ABOUT)
        for r in (["Effort", self.name], ["Client", self.client], ["Solicitation", self.solicitation],
                  ["Internal number", self.internal_no], ["First use", FIRST_USE_RULES[self.first_use]],
                  ["Saved", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
                  ["Statuses", ", ".join(STATUSES)],
                  ["Note", "Edit Status, SS Approver and Notes here or in Acronym Hunter. Keep the column headings."]):
            ab.append(r)
        ab.column_dimensions["A"].width = 12; ab.column_dimensions["B"].width = 80
        fd, tmp = tempfile.mkstemp(prefix=".effort_", suffix=".xlsx", dir=d)
        os.close(fd)
        try:
            wb.save(tmp)
            try:
                os.replace(tmp, self.path)
            except PermissionError:
                raise ListLocked(self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.pending = False

    # ------------------------------------------------------------ exports for approvals
    def export_views(self, out_path):
        """A separate workbook with sheets people act on: Needs author, Conflicts, Approved, All."""
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook()
        views = [("Needs author", lambda r: r["Status"] in ("Proposed", "Needs author")),
                 ("Conflicts", lambda r: bool(r["Other definitions"])),
                 ("Approved", lambda r: r["Status"] == "Approved"),
                 ("All", lambda r: True)]
        first = True
        for title, keep in views:
            ws = wb.active if first else wb.create_sheet()
            first = False
            ws.title = title
            ws.append(COLUMNS)
            for c in ws[1]:
                c.font = Font(bold=True)
            for t in self.order:
                r = self.rows[t]
                if keep(r):
                    ws.append([r.get(c, "") for c in COLUMNS])
            for i, w in enumerate(WIDTHS, 1):
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
            ws.freeze_panes = "B2"
        wb.save(out_path)
        return {title: sum(1 for t in self.order if keep(self.rows[t])) for title, keep in views}


def _norm_status(s):
    s = (s or "").strip().lower()
    for st in STATUSES:
        if s == st.lower():
            return st
    if s.startswith("approv"):
        return "Approved"
    if s.startswith("reject") or s in ("no", "not a term"):
        return "Rejected"
    if "author" in s or "need" in s:
        return "Needs author"
    return "Proposed"


# ------------------------------------------------------------ the list of efforts on this PC
class Registry:
    """config\\efforts.json: the efforts this PC knows and which one is open."""

    def __init__(self, path):
        self.path = path
        self.data = {"current": "", "efforts": {}}
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                self.data.update(d)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def names(self):
        return sorted(self.data["efforts"])

    def get(self, name):
        return self.data["efforts"].get(name)

    def put(self, name, **info):
        e = self.data["efforts"].setdefault(name, {})
        e.update({k: v for k, v in info.items() if v is not None})
        self.save()
        return e

    def forget(self, name):
        self.data["efforts"].pop(name, None)
        if self.data.get("current") == name:
            self.data["current"] = ""
        self.save()

    @property
    def current(self):
        n = self.data.get("current") or ""
        return n if n in self.data["efforts"] else ""

    @current.setter
    def current(self, name):
        self.data["current"] = name or ""
        self.save()
