"""The acronym rules (3.14.0): what happens to a scan's results, without a window. These are the rules the retired
classic window kept in its own class and mixins (AcronymAppGUI, EffortMixin, HomeMixin, MasterMixin, WizardMixin,
KeywordsMixin), moved here as they were so the Qt edition keeps them exactly: instances you excluded, saved choices, the
customer's definitions, definitions picked from the documents, the effort list (approved definitions win, rejected terms
are hidden), where each term is known, the effort list's Found in, the lists to export, and the keywords.
The class expects what AcronymSession gives it: ws, efforts, effort, results, manual_items, session_decisions,
client_lists, tree, entry_def, status, and the hooks it overrides. Rules only (No AI); nothing leaves the PC."""
import csv, datetime, os, re, time
import diag
import effort as E
from app_gui import (CLIENT_TAG, DB_TAG, LOC_MAX_LINES, RESOLVED_WORDS, STATUS_RANK, _file_of, ctx_text, status_kind,
                     status_text)
from master_db import SRC_DOCS, SRC_LIST, SRC_MASTER, known_text

KW_EXPORT_COLS = ["Keyword", "Category", "SharePoint field", "Why", "Source", "Status", "Added by", "Date"]


def _eng():
    import app_gui
    return app_gui


def _safe(name):
    return re.sub(r"[^A-Za-z0-9 _.-]+", "", name).strip() or "Effort"


def files_of(d, file_of):
    """File names a result was found in."""
    return {file_of(l) for l in d.get("locations", []) if l and not l.startswith(("Added manually",))}


def clean_definition(text, term=""):
    """Selected words -> a definition: one line, no surrounding quotes or punctuation, no '(TERM)' after it."""
    t = " ".join((text or "").split()).strip(" \t\"'\u201c\u201d\u2018\u2019.,;:")
    if term:
        t = re.sub(r"\s*[\(\[]\s*" + re.escape(term) + r"s?\s*[\)\]]\s*$", "", t, flags=re.I)
        t = re.sub(r"^\s*" + re.escape(term) + r"s?\s*[:=\-\u2013\u2014]\s*", "", t, flags=re.I)
    t = t.strip(" \t\"'\u201c\u201d\u2018\u2019.,;:()[]")
    return t[:200]


class AcronymRules:
    # ---------------------------------------------------------------- from app_gui.py (AcronymAppGUI)
    def path_for(self, filename):
        """Full path of a scanned file, from this session's scans or the open project."""
        if filename in self.scanned_paths and os.path.exists(self.scanned_paths[filename]):
            return self.scanned_paths[filename]
        if self.project is not None:
            for rel in self.project.data.get("files", {}):
                if os.path.basename(rel.replace("/", os.sep)) == filename:
                    path = self.project.member_path(rel)
                    if os.path.exists(path):
                        return path
        return None

    def apply_saved_decisions(self):
        """Choices made with Apply Choice: this PC's saved choices, then the open project's (the project wins)."""
        decisions = dict(self.load_choices())
        if self.project is not None:
            decisions.update(self.project.data["decisions"])
        for term, choice in decisions.items():
            d = self.results.get(term)
            if d and (d.get("in_db") or d.get("customer_definitions")) and not d.get("excluded") and not d.get("gone") and \
                    (choice == "Keep All Possibilities" or choice in d.get("definitions", [])):
                self._set_choice(d, choice)

    def load_choices(self):
        """Apply Choice decisions for the open effort only (2.11.0), or for scans with no effort."""
        try:
            return self.ws.load_choices()
        except Exception:
            diag.swallowed()
            return {}

    def save_choice(self, term, choice):
        """Remember a definition choice for every later scan in this effort (written atomically)."""
        self.ws.save_choice(term, choice)

    @staticmethod
    def _set_choice(data, choice):
        if choice == "Keep All Possibilities":
            data["selected_definition"] = "MULTIPLE: " + " | ".join(data["definitions"])
            data["status"] = "MULTIPLE (Kept All)"
            return "ambiguous"
        for tag in (CLIENT_TAG, DB_TAG):
            if choice.startswith(tag):
                choice = choice[len(tag):]
        data["selected_definition"] = choice
        data["status"] = "User Selected" + (" (client list)" if data.get("client") and choice in data.get("client_definitions", []) else "")
        return "resolved"

    def sort_key(self, term, data):
        c = self.sort_col
        if c == "count":
            return (data["count"], term.casefold())
        if c == "locations":
            return (len(data["locations"]), term.casefold())
        if c == "category":
            return (data["category"].casefold(), term.casefold())
        if c == "status":
            rank = STATUS_RANK.get(status_kind(data["status"]), 9)
            return (rank, term.casefold())
        if c == "definition":
            return (data["selected_definition"].casefold(), term.casefold())
        if c == "knownin":
            return (self.known_cell(term, data), term.casefold())
        if c == "change":
            order = {"New": 0, "Changed": 1, "Database update": 1, "No longer found": 2, "Unchanged": 3}
            return (order.get(data.get("change", ""), 4), term.casefold())
        return (term.casefold(),)

    @staticmethod
    def status_matches(data, wanted):
        st = data["status"]
        kind = status_kind(st)
        return {
            "Needs choice": kind == "choice",
            "New candidates": kind == "candidate",
            "Resolved": kind == "resolved" and status_text(st).startswith(RESOLVED_WORDS),
            "Client list": data.get("client", False),
            "Alt forms": bool(data.get("alt_of")),
            "Equations and symbols": data.get("category", "").startswith(("Equation", "Symbol")) or bool(data.get("symbol")),
            "Undefined symbols": bool(data.get("symbol")) and kind == "candidate" or (data.get("equation") and "not defined" in st),
            "Client and database differ": bool(data.get("client") and data.get("db_definitions")),
            "Added manually": data.get("manual", False),
            "In effort list": bool(data.get("effort")),
            "Customer documents": bool(data.get("customer_definitions")),
            "Customer and database differ": bool(data.get("cust_db_differ")),
            "Not in effort list": not data.get("effort") and not data.get("excluded", False) and not data.get("known"),
            "Found in omit list": bool(data.get("known")),
            "New in this scan (not in the effort list)": bool(data.get("new_in_effort")) and not data.get("effort"),
            "Context suggests a meaning": bool((data.get("context") or {}).get("definition")) and kind == "choice",
            "Effort: needs author": data.get("effort") in ("Proposed", "Needs author"),
            "Effort: approved": data.get("effort") == "Approved",
            "New since last scan": data.get("change") == "New",
            "Changed since last scan": data.get("change") == "Changed",
            "No longer found": data.get("gone", False),
            "Errors / not scanned": kind == "error",
            "Excluded": data.get("excluded", False),
            "Database update": data.get("change") == "Database update",
            "Known in: customer docs": "Customer docs" in (data.get("known_in") or []),
            "Known in: customer list": "Customer list" in (data.get("known_in") or []),
            "Known in: master database only": (data.get("known_in") or []) == ["Master database"],
            "Known in: no source": not data.get("known_in") and not data.get("file_error"),
        }.get(wanted, True)

    def row_values(self, term, data):
        defn = data["selected_definition"]
        if status_kind(data.get("status", "")) == "choice" and ctx_text(data):
            defn = f"Context: {ctx_text(data)}\n{defn}"
        return (term, data["category"], data["count"], self.found_in(data), data.get("change", ""), data["status"],
                defn, self.known_cell(term, data), self.wrap_locations(data["locations"]))

    def doc_kinds(self):
        """{file name (lower case): 'customer' or 'ours'} for the open effort's documents (2.38.0)."""
        L = getattr(self, "effort", None)
        key = L.name if L is not None else None
        cache = getattr(self, "_doc_kinds", None)
        if cache is None or cache[0] != key or cache[2] < time.time() - 5:
            kinds = {}
            if L is not None and hasattr(self, "kw_sources"):
                try:
                    for p, kind in self.kw_sources():
                        kinds.setdefault(os.path.basename(p).lower(), kind)
                except Exception:
                    diag.swallowed()
            self._doc_kinds = cache = (key, kinds, time.time())
        return cache[1]

    def found_in(self, data):
        """'Customer', 'Ours' or 'Both': where a term was found, by the effort's customer documents and our documents."""
        kinds = self.doc_kinds()
        if not kinds:
            return ""
        got = {kinds.get(_file_of(l).lower()) for l in data.get("locations", []) if l}
        got.discard(None)
        return "Both" if got == {"customer", "ours"} else "Customer" if got == {"customer"} else "Ours" if got == {"ours"} else ""

    def wrap_locations(self, locations):
        """Locations wrapped to the column width, at most LOC_MAX_LINES lines (the rest: double-click the row)."""
        text = "; ".join(locations)
        if not hasattr(self, "tree"):
            return text
        width = max(80, int(self.tree.column("locations", "width")) - 16)
        measure = self.tree_font.measure
        lines, cur = [], ""
        for i, piece in enumerate(locations):
            add = piece + ("; " if i < len(locations) - 1 else "")
            if cur and measure(cur + add) > width:
                lines.append(cur.rstrip()); cur = ""
            while measure(add) > width and len(add) > 10:      # one very long location: break it
                cut = len(add)
                while cut > 10 and measure(add[:cut]) > width:
                    cut -= 5
                lines.append(add[:cut]); add = add[cut:]
            cur += add
        if cur:
            lines.append(cur.rstrip())
        if len(lines) > LOC_MAX_LINES:
            lines = lines[:LOC_MAX_LINES]
            lines[-1] = lines[-1][:max(0, len(lines[-1]) - 28)] + "...  (double-click for all)"
        return "\n".join(lines)

    def excludable(self, term):
        d = self.results.get(term)
        return bool(d) and not (d.get("excluded") or d.get("manual") or d.get("gone") or d.get("file_error"))

    @staticmethod
    def _drop_instance(d, loc):
        if loc not in d.get("locations", []):
            return False
        d["locations"].remove(loc)
        d["count"] = max(len(d["locations"]), int(d.get("count", 1)) - 1)
        lst = d.setdefault("excluded_instances", [])
        if loc not in lst:
            lst.append(loc)
        if not d["locations"] and not d.get("excluded"):
            d["_pre_instances"] = [d.get("status", ""), d.get("selected_definition", "")]
            d["excluded"] = True
            d["status"] = "All instances excluded"
        return True

    def apply_instance_excludes(self):
        """After every scan: take out the instances excluded in this effort."""
        try:
            ex = self.ws.instance_excludes()
        except Exception:
            diag.swallowed()
            return 0
        n = 0
        for term, locs in ex.items():
            d = self.results.get(term)
            if d:
                for loc in locs:
                    n += self._drop_instance(d, loc)
        return n

    def exclude_instance(self, term, loc):
        """Exclude one place a term was found (a misreading, a heading word). Saved for this effort only."""
        d = self.results.get(term)
        if not d or not self._drop_instance(d, loc):
            return False
        ex = self.ws.instance_excludes()
        if loc not in ex.setdefault(term, []):
            ex[term].append(loc)
        self.ws.save_instance_excludes(ex)
        diag.activity("exclude_instance", n=1)
        self.selected_term = term if not d.get("excluded") else None
        self.populate_table()
        return True

    def restore_instances(self, term):
        """Bring back every excluded instance of a term (they show again now and on later scans)."""
        d = self.results.get(term)
        ex = self.ws.instance_excludes()
        locs = ex.pop(term, [])
        self.ws.save_instance_excludes(ex)
        if d:
            back = [l for l in d.get("excluded_instances", []) if l not in d["locations"]]
            d["locations"].extend(back)
            d["count"] = int(d.get("count", 0)) + len(back)
            d.pop("excluded_instances", None)
            pre = d.pop("_pre_instances", None)
            if pre and d.get("status") == "All instances excluded":
                d["excluded"] = False
                d["status"], d["selected_definition"] = pre[0], pre[1]
        diag.activity("restore_instances", n=len(locs))
        self.selected_term = term
        self.populate_table()
        return len(locs)

    # ---------------------------------------------------------------- from effort_ui.py (EffortMixin)
    def _definition_for(self, d):
        sd = (d.get("selected_definition") or "").strip()
        if not sd or _eng().status_text(sd).startswith(("[", "MULTIPLE", "Rescan")):
            return ""
        return sd

    def _source_for(self, d, definition):
        if d.get("custdef_source") and definition in d.get("customer_definitions", []):
            return "Customer document"
        if d.get("client") and definition in d.get("client_definitions", []):
            return "Client list"
        if d.get("in_db") and definition:
            return "Database"
        if d.get("manual"):
            return "Added manually"
        return "Author" if definition else ""

    def add_to_effort(self, terms=None):
        if self.effort is None:
            return
        eng = _eng()
        terms = [t for t in (terms or self.tree.selection()) if t in self.results]
        if not terms:
            return
        typed = ""
        if len(terms) == 1:                      # a definition typed in the bottom box goes into the list
            try:
                typed = self.entry_def.get().strip() if str(self.entry_def.cget("state")) == "normal" else ""
            except Exception:
                diag.swallowed()
        added = updated = 0
        for t in terms:
            d = self.results[t]
            if d.get("file_error"):
                continue
            definition = typed or self._definition_for(d)
            cust = next((h for h in d.get("custdef_all", []) if h["definition"] == definition), None) or {}
            fields = dict(Type=eng.base_type(d.get("category", "")), Source=self._source_for(d, definition))
            # First use is checked only in our own Word deliverables (QA/QC tab), never from a scan of other files (2.24.0)
            if definition:
                fields["Definition"] = definition
            if cust and definition in d.get("customer_definitions", []):
                fields["Customer document"] = cust.get("where", "")
                fields["Customer wording"] = cust.get("sentence", "")[:500]
            others = [x for x in d.get("customer_definitions", []) + d.get("definitions", []) if x and x != definition]
            if others:
                fields["Other definitions"] = " | ".join(dict.fromkeys(others))[:500]
            docs = sorted({eng._file_of(l) for l in d.get("locations", []) if l and not l.startswith("Added manually")}, key=str.lower)
            if docs:
                row = self.effort.rows.get(t, {})
                had = [x for x in re.split(r"\s*;\s*", row.get("Found in", "")) if x]
                fields["Found in"] = "; ".join(sorted(set(had) | set(docs), key=str.lower))
                fields["Last found"] = E.today()
                if not row.get("First found"):
                    fields["First found"] = E.today()
            note = (f"added from {', '.join(docs)[:120]}" + (f": {definition[:60]}" if definition else "")) if docs and t not in self.effort.rows else None
            r = self.effort.add_or_update(t, change_note=note, **fields)
            added += r == "added"; updated += r == "updated"
        if typed:
            self.entry_def.delete(0, "end")      # used once; never carried over to the next term
        diag.activity("effort_add", added=added, n=updated)
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()
        self.status.configure(text=f"Effort list: {added} added, {updated} updated." + ("" if not self.effort.pending else " NOT SAVED yet: close the list in Excel."))

    def remove_from_effort(self, terms=None):
        if self.effort is None:
            return
        terms = [t for t in (terms or self.tree.selection()) if t in self.effort.rows]
        for t in terms:
            self.effort.remove(t)
        diag.activity("effort_remove", n=len(terms))
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()

    def customer_files(self):
        """Files in the effort's customer documents folder (Word, PowerPoint, Excel, PDF)."""
        if self.effort is None:
            return []
        info = self.efforts.get(self.effort.name) or {}
        d = info.get("customer_dir") or ""
        if not d or not os.path.isdir(d):
            return []
        out = []
        for root, _dirs, fs in os.walk(d):
            for f in fs:
                if not f.startswith("~$") and os.path.splitext(f)[1].lower() in (".docx", ".pptx", ".xlsx", ".pdf"):
                    out.append(os.path.join(root, f))
        return sorted(out)

    def customer_definitions(self):
        """{term: [definition hits]} from the customer documents, cached per file until the file changes."""
        import custdefs
        eng = _eng()
        cache = getattr(self, "_custdef_cache", {})
        self._custdef_cache = cache
        merged = {}
        for path in self.customer_files():
            try:
                st = os.stat(path)
                key = (path, st.st_size, st.st_mtime)
                if key not in cache:
                    cache[key] = custdefs.extract(eng.typed_chunks(path) + custdefs.table_chunks(path))
                for term, hits in cache[key].items():
                    lst = merged.setdefault(term, [])
                    for h in hits:
                        if not any(x["definition"].lower() == h["definition"].lower() for x in lst):
                            lst.append(h)
            except Exception:
                diag.swallowed()
        return merged

    def apply_customer_defs(self):
        """The customer's own definition outranks the database. Several different ones: the user chooses."""
        import custdefs
        eng = _eng()
        defs = self.customer_definitions() if self.effort is not None else {}
        n = custdefs.merge_into(self.results, defs, folded=lambda t: eng.fold(t).strip())
        diag.activity("customer_definitions_applied", terms=n, files=len(self.customer_files()) if defs else 0)
        for term, d in self.results.items():
            cdefs = d.get("customer_definitions")
            if not cdefs or d.get("excluded") or d.get("file_error"):
                continue
            db = [x for x in d.get("definitions", []) if x not in cdefs]
            d["db_or_client_definitions"] = db
            d["definitions"] = list(cdefs) + db
            d["cust_db_differ"] = bool(db)
            if len(cdefs) == 1:
                d["selected_definition"] = cdefs[0]
                d["status"] = "Customer document" + (" (database differs)" if db else "")
            else:
                d["selected_definition"] = "MULTIPLE: " + " | ".join(cdefs)
                d["status"] = f"CUSTOMER DOCS DIFFER ({len(cdefs)})"
        return n

    def apply_effort(self, reload=False):
        """Mark results with the effort list: approved definitions win; rejected terms are hidden for this effort."""
        eng = _eng()
        if reload and self.effort is not None and not self.effort.pending:
            try:
                self.effort.load()
            except Exception:
                diag.swallowed()
        L = self.effort
        alt_map = L.alt_map() if L is not None else {}
        for term, d in self.results.items():
            pre = d.get("_pre_effort")
            row = L.rows.get(term) if L is not None else None
            primary = alt_map.get(term) if row is None else None
            if primary is not None and primary in L.rows:    # an alt form of a term in the effort list (2.26.0)
                if not pre:
                    d["_pre_effort"] = (d.get("status", ""), d.get("selected_definition", ""), d.get("excluded", False))
                    pre = d["_pre_effort"]
                prow = L.rows[primary]
                d["effort"] = prow["Status"]
                d["alt_of"] = primary
                d["excluded"] = pre[2]
                d["status"] = f"{eng.ALT_STATUS} {primary} (effort list: {prow['Status']})"
                d["selected_definition"] = prow["Definition"] or pre[1]
                continue
            if row is None:
                if pre:                                     # left the list, or the effort was closed: restore
                    d["status"], d["selected_definition"], d["excluded"] = pre
                    d.pop("_pre_effort", None); d.pop("effort", None)
                    if d.get("alt_of") and not str(pre[0]).startswith(eng.ALT_STATUS):
                        d.pop("alt_of", None)
                continue
            if not pre:
                d["_pre_effort"] = (d.get("status", ""), d.get("selected_definition", ""), d.get("excluded", False))
                pre = d["_pre_effort"]
            st = row["Status"]
            d["effort"] = st
            d["excluded"] = pre[2] or st == "Rejected"
            if st == "Rejected":
                d["status"] = "Not a term in this effort"
                d["selected_definition"] = pre[1]
            else:
                d["status"] = f"Effort list: {st}"
                d["selected_definition"] = row["Definition"] or pre[1]
        if hasattr(self, "tree"):
            self.populate_table()
        if hasattr(self, "session_changed"):
            self.session_changed()

    # ---------------------------------------------------------------- from effort_home.py (HomeMixin)
    def home_set_definition(self, term, text, note=None):
        """Write a definition into the effort list (and into the scan results, if the term is there)."""
        text = clean_definition(text, term)
        L = self.effort
        if L is None or term not in L.rows or not text:
            return False
        if L.add_or_update(term, change_note=note or f"definition: {text[:80]}", Definition=text) != "unchanged":
            self._save_effort_list()
        self.ws_pick_definition(term, text)
        if term in self.results:
            self.apply_effort()
        self.home_refresh()
        return True

    def volumes(self):
        ws = getattr(self, "ws", None)
        v = (ws.get("volumes", []) if ws is not None else []) or []
        return [x for x in v if isinstance(x, dict) and x.get("name")]

    def ws_pick_definition(self, term, text):
        ws = getattr(self, "ws", None)
        if ws is None:
            return
        picks = dict(ws.get("picked_definitions", {}) or {})
        picks[term] = text
        ws.set("picked_definitions", picks)

    def apply_picked_definitions(self):
        """After every scan: definitions taken from the documents with Use as definition (this effort only)."""
        ws = getattr(self, "ws", None)
        picks = (ws.get("picked_definitions", {}) or {}) if ws is not None else {}
        for t, text in picks.items():
            d = self.results.get(t)
            if not d or d.get("excluded") or d.get("gone") or d.get("file_error") or d.get("known"):
                continue
            self._pick_into(d, text)

    @staticmethod
    def _pick_into(d, text):
        if text not in d.get("definitions", []):
            d["definitions"] = [text] + [x for x in d.get("definitions", []) if x]
        d["selected_definition"] = text
        d["status"] = "User Selected (from the document)"
        d["picked"] = text

    # ---------------------------------------------------------------- from master_db.py (MasterMixin)
    def db_terms(self, refresh=False):
        """Folded terms the database knows (include and omit rows), read again when the file changes."""
        eng = _eng()
        try:
            mt = os.path.getmtime(eng.DB_FILE)
        except OSError:
            mt = 0
        if refresh or getattr(self, "_db_terms_mt", None) != (eng.DB_FILE, mt):
            try:
                self._db_terms = set(eng.load_database()[0])
            except Exception:
                diag.swallowed(); self._db_terms = set()
            self._db_terms_mt = (eng.DB_FILE, mt)
        return self._db_terms

    def known_in(self, term, d):
        eng = _eng()
        out = []
        if d.get("customer_definitions"):
            out.append(SRC_DOCS)
        if d.get("client"):
            out.append(SRC_LIST)
        if eng.fold(term).strip() in self.db_terms():
            out.append(SRC_MASTER)
        return out

    def mark_known_in(self):
        for t, d in self.results.items():
            if not d.get("file_error"):
                d["known_in"] = self.known_in(t, d)

    def known_cell(self, term, d):
        if d.get("file_error"):
            return ""
        if "known_in" not in d:
            d["known_in"] = self.known_in(term, d)
        return known_text(d["known_in"])

    # ---------------------------------------------------------------- from effort_wizard.py (WizardMixin)
    def effort_after_scan(self, scanned_paths):
        """Found in / First found / Last found / Scan status in the effort list; new and gone terms in the results."""
        eng = _eng()
        L = self.effort
        if L is None:
            return None
        names = [os.path.basename(p) for p in scanned_paths]
        found = {t: files_of(d, eng._file_of) for t, d in self.results.items() if not d.get("file_error") and not d.get("gone")}
        rep = L.record_scan(found, names)
        seen = set(self.ws.get("seen_terms", []) or [])
        new = 0
        for t, d in self.results.items():
            fresh = t not in L.rows and t not in seen and not d.get("excluded") and not d.get("file_error") and not d.get("known")
            d["new_in_effort"] = fresh
            new += fresh
        self.ws.set("seen_terms", sorted(seen | set(found)))
        for t in rep["gone"]:
            if t not in self.results:
                row = L.rows[t]
                self.results[t] = {"category": row.get("Type") or "Acronym", "count": 0, "locations": [], "definitions": [row.get("Definition", "")],
                                   "in_db": True, "excluded": False, "gone": True, "effort": row.get("Status", ""),
                                   "selected_definition": row.get("Definition", ""), "status": "No longer found: " + row.get("Scan status", "")}
        if rep["found"] or rep["gone"]:
            self._save_effort_list()
        return {"new": new, "gone": len(rep["gone"]), "found": rep["found"]}

    def _list_rows(self, approved_only=False):
        eng = _eng()
        L = self.effort
        out = []
        for t in L.order:
            r = L.rows[t]
            if r["Status"] == "Rejected" or self.results.get(t, {}).get("known"):
                continue
            if approved_only and r["Status"] != "Approved":
                continue
            out.append(r)
        return sorted(out, key=lambda r: r["Term"].lower())

    def export_effort_lists(self, folder=None, scope=None, approved_only=False):
        """The effort's acronym list: whole effort, per volume (one per file in Found in), or both. Word + Excel."""
        import docxw
        from openpyxl import Workbook
        from openpyxl.styles import Font
        L = self.effort
        if L is None:
            return None
        info = self.efforts.get(L.name) or {}
        scope = scope or info.get("list_format", "whole")
        if not folder:                           # 3.14.0: the page asks for the folder
            return None
        rows = self._list_rows(approved_only)
        stamp = datetime.date.today().isoformat()
        stem = _safe(L.name).replace(" ", "_")
        made = []

        def word(path, title, rs):
            d = docxw.Doc()
            d.props = {"StationkeeperEffort": L.name, "Client": L.client, "Solicitation": L.solicitation}
            d.heading(title, 1)
            d.table(["Term", "Definition"], [[r["Term"], r["Definition"]] for r in rs], [1800, 7560])
            d.save(path); made.append(path)

        if scope in ("whole", "both"):
            word(os.path.join(folder, f"{stem}_Acronym_List_{stamp}.docx"), f"Acronyms and Abbreviations: {L.name}", rows)
        if scope in ("volume", "both"):
            vols = sorted({f for r in rows for f in re.split(r"\s*;\s*", r.get("Found in", "")) if f}, key=str.lower)
            cust = set()
            cdir = info.get("customer_dir") or ""
            if cdir and os.path.isdir(cdir):
                cust = set(os.listdir(cdir))
            for vname in vols:
                if vname in cust:
                    continue                                   # customer documents are sources, not volumes
                rs = [r for r in rows if vname in re.split(r"\s*;\s*", r.get("Found in", ""))]
                word(os.path.join(folder, f"{stem}_Acronym_List_{_safe(os.path.splitext(vname)[0])}_{stamp}.docx"),
                     f"Acronyms and Abbreviations: {os.path.splitext(vname)[0]}", rs)
        wb = Workbook(); ws = wb.active; ws.title = "Acronym list"
        cols = ["Term", "Definition", "Type", "Status", "Found in", "First found", "Last found", "Scan status", "Effort", "Client", "Solicitation"]
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r.get(c, "") if c not in ("Effort", "Client", "Solicitation") else
                       {"Effort": L.name, "Client": L.client, "Solicitation": L.solicitation}[c] for c in cols])
        for col, w in zip("ABCDEFGHIJK", (14, 44, 14, 12, 50, 12, 12, 30, 22, 18, 18)):
            ws.column_dimensions[col].width = w
        xp = os.path.join(folder, f"{stem}_Acronym_List_{stamp}.xlsx")
        wb.save(xp); made.append(xp)
        diag.activity("effort_lists_exported", files=len(made), rows=len(rows))
        return made

    # ---------------------------------------------------------------- from keywords_ui.py (KeywordsMixin)
    def kw_selected(self):
        return [self.kw_tree.set(i, "kw") for i in self.kw_tree.selection()] if hasattr(self, "kw_tree") else []

    def _kw_saved(self):
        self._save_effort_list()
        self.kw_refresh()

    def kw_add(self, text, category="Other", source="", why="", status="Proposed"):
        if self.effort is None:
            return "no effort"
        r = self.effort.add_keyword(text, category, source, why, status)
        if r == "added":
            diag.activity("keyword_added")
            self._kw_saved()
        return r

    def kw_set_status(self, status, words=None):
        import keywords
        words = words or self.kw_selected()
        n = 0
        for w in (words if self.effort is not None else []):
            if self.effort.update_keyword(w, Status=status):
                n += 1
                keywords.learn(w, status)            # later suggestions in every effort (hashed, counts only)
        if n:
            diag.activity("keyword_status", n=n)
            self._kw_saved()
        return n

    def kw_remove(self, words=None):
        words = words or self.kw_selected()      # 3.14.0: the page confirms before it calls this
        if words:
            for w in words:
                self.effort.remove_keyword(w)
            diag.activity("keyword_removed", n=len(words))
            self._kw_saved()

    def kw_sources(self):
        """[(path, 'customer' or 'ours')]: the customer documents, and our volumes / scanned files."""
        L = self.effort
        info = (self.efforts.get(L.name) or {}) if L is not None else {}
        out, seen = [], set()
        cd = info.get("customer_dir") or ""
        if cd and os.path.isdir(cd):
            for f in sorted(os.listdir(cd)):
                p = os.path.join(cd, f)
                if os.path.isfile(p) and f.lower().endswith((".docx", ".pdf", ".pptx", ".xlsx")):
                    out.append((p, "customer")); seen.add(os.path.normcase(os.path.abspath(p)))
        # 3.34.1: the customer documents are also the effort's Customer Documents folder and its Library documents
        epath = info.get("path") or ""
        extra = []
        try:
            import effortfolders as EF
            cf = EF.folder(epath, "customer", make=False) if epath else ""
            if cf and os.path.isdir(cf):
                extra += [os.path.join(cf, f) for f in sorted(os.listdir(cf))]
        except Exception:
            diag.swallowed()
        try:
            ws = getattr(self, "ws", None)
            if ws is not None:
                import docversions as DV
                lib = DV.Library(ws.p("documents")).load()
                for d in lib.docs:
                    for v in lib.versions(d) if hasattr(lib, "versions") else [lib.latest(d)]:
                        if v:
                            extra.append(lib.path_of(v))
        except Exception:
            diag.swallowed()
        for p in extra:
            if p and os.path.isfile(p) and p.lower().endswith((".docx", ".pdf", ".pptx", ".xlsx")) and \
                    os.path.normcase(os.path.abspath(p)) not in seen:
                out.append((p, "customer")); seen.add(os.path.normcase(os.path.abspath(p)))
        cust_names = {os.path.basename(p) for p, _k in out}
        ours = []
        for v in (self.volumes() if hasattr(self, "volumes") else []):
            ours += [self.path_for(f) for f in v.get("files", [])]
        vdir = ""
        try:
            import effortfolders as EF
            vdir = os.path.normcase(os.path.abspath(EF.folder(epath, "volumes", make=False))) if epath else ""
        except Exception:
            diag.swallowed()
        for p in ours:
            if p and os.path.isfile(p) and os.path.normcase(os.path.abspath(p)) not in seen and os.path.basename(p) not in cust_names:
                out.append((p, "ours")); seen.add(os.path.normcase(os.path.abspath(p)))
        # 3.34.1: a scanned file is ours only when it is one of our volumes or sits in the effort's Volumes folder;
        # anything else scanned (an RFP from Downloads, an attachment) is the customer's
        for p in list((getattr(self, "last_scan", None) or {}).get("paths", [])):
            if not p or not os.path.isfile(p) or os.path.normcase(os.path.abspath(p)) in seen or os.path.basename(p) in cust_names:
                continue
            mine = bool(vdir) and os.path.normcase(os.path.abspath(p)).startswith(vdir + os.sep)
            out.append((p, "ours" if mine else "customer")); seen.add(os.path.normcase(os.path.abspath(p)))
        return out

    def kw_compute(self, sources=None, progress=None):
        import keywords
        eng = _eng()
        chunks = []
        for i, (p, kind) in enumerate(sources if sources is not None else self.kw_sources(), 1):
            if progress:
                progress(f"Reading {i}: {os.path.basename(p)}")
            try:
                chunks += [(lbl, txt, kind) for lbl, txt in eng.typed_chunks(p)]
            except Exception:
                diag.swallowed()
        L = self.effort
        acr = [(t, r["Definition"]) for t, r in L.rows.items() if r["Status"] == "Approved" and r.get("Definition")] if L else []
        import offerings
        return keywords.suggest(chunks, acr, [k["Keyword"] for k in (L.keywords if L else [])], offerings=offerings.load(),
                                base=keywords.baseline(), learned=keywords.learning(), asks=self.kw_asks())

    def kw_asks(self):
        """[(requirement id, outline section)] for the Keep requirements the compliance matrix placed (2.34.0)."""
        M = getattr(self, "matrix", None)
        if M is None:
            return []
        return [(it["id"], it["map"]) for it in M.items if it.get("decision") == "Keep" and it.get("map")]

    def kw_export(self, path, keep_only=True):
        L = self.effort
        rows = [k for k in L.keywords if (k["Status"] == "Keep" if keep_only else k["Status"] != "Reject")]
        if path.lower().endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f); w.writerow(KW_EXPORT_COLS); w.writerows([[k.get(c, "") for c in KW_EXPORT_COLS] for k in rows])
        else:
            from openpyxl import Workbook
            from openpyxl.styles import Font
            wb = Workbook(); ws = wb.active; ws.title = "Keywords"
            ws.append(KW_EXPORT_COLS)
            for c in ws[1]:
                c.font = Font(bold=True)
            for k in rows:
                ws.append([k.get(c, "") for c in KW_EXPORT_COLS])
            for col, wd in zip("ABCDEFGH", (34, 18, 18, 60, 30, 10, 14, 12)):
                ws.column_dimensions[col].width = wd
            ab = wb.create_sheet("About")
            for r in (["Effort", L.name], ["Client", L.client], ["Solicitation", L.solicitation],
                      ["Exported", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]):
                ab.append(r)
            wb.save(path)
        diag.activity("keywords_exported", rows=len(rows))
        return len(rows)
