"""Acronym hunting without a window (2.64.0): the scan of the classic window and everything that happens to its results
afterwards, for the Qt edition. The rules are the classic window's own methods (shared, not copied): instances you
excluded, the customer's definitions, saved choices, definitions picked from the documents, the effort list (approved
definitions win, rejected terms are hidden), known names, where each term is known (customer documents, customer list,
master database), and the effort list's Found in. Rules only (No AI); nothing leaves the PC.
"""
import os
import app_gui as A
import diag
import effort as E
from effort_ui import EffortMixin
from effort_home import HomeMixin
from master_db import MasterMixin
from effort_wizard import WizardMixin
from keywords_ui import KeywordsMixin

G = A.AcronymAppGUI

# the classic window's own rules, used as they are
_SHARED = ("apply_instance_excludes", "_drop_instance", "exclude_instance", "restore_instances", "apply_saved_decisions",
           "load_choices", "save_choice", "status_matches", "found_in", "doc_kinds", "excludable", "sort_key", "path_for",
           "row_values", "wrap_locations")


class _Tree:
    """Stands in for the classic window's results table: what is selected."""
    def __init__(self):
        self.sel = []

    def selection(self):
        return list(self.sel)

    def selection_set(self, *items):
        self.sel = [x for it in items for x in (it if isinstance(it, (list, tuple)) else [it])]

    def exists(self, _iid):
        return False

    def see(self, _iid):
        pass

    def get_children(self):
        return []


class _Entry:
    """Stands in for the classic window's definition box (a definition typed for one term)."""
    def __init__(self):
        self.value = ""

    def get(self):
        return self.value

    def cget(self, _k):
        return "normal"

    def delete(self, *_a):
        self.value = ""

    def insert(self, _i, text):
        self.value += text

    def configure(self, **_k):
        pass


class _Status:
    def __init__(self):
        self.text = ""

    def configure(self, text="", **_k):
        self.text = text


class AcronymSession(EffortMixin, HomeMixin, MasterMixin, WizardMixin, KeywordsMixin):
    """One effort's acronym results. ws: the effort's Workspace; effort_path: its acronym list; efforts: the registry."""

    def __init__(self, ws, effort_path, efforts, settings=None):
        self.ws, self.efforts = ws, efforts
        self.settings = settings if settings is not None else {}
        self.project = None
        self.results, self.manual_items, self.session_decisions = {}, {}, {}
        self.scanned_paths, self.queued_files = {}, []
        self.last_scan = None
        self.volume_report = None
        self.selected_term = None
        self.matrix = None                                   # the Qt edition sets the open compliance matrix (keyword asks)
        self.sort_col, self.sort_desc = "term", False
        self.effort = E.EffortList(effort_path, getattr(ws, "name", "") or "").load() if effort_path else None
        self.tree, self.entry_def, self.status = _Tree(), _Entry(), _Status()
        self._last_approver = ""
        self.client_lists = []
        try:
            self.set_client_lists(ws.get("client_lists", []) or [])
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ what the window would have done
    def set_client_lists(self, lists):
        self.client_lists = lists
        A.set_client_lists(lists)

    def session_changed(self):
        pass

    def resume_changed(self):
        pass

    def populate_table(self):
        pass

    def update_effort_ui(self):
        pass

    def home_refresh(self):
        pass

    def kw_refresh(self):
        pass

    def _save_effort_list(self, L=None, backup=True):
        """Save the effort list; False when Excel holds it open (kept pending and in the effort's recovery copy)."""
        L = L or self.effort
        if L is None:
            return False
        try:
            self.ws.write_recovery("effort", L.path, {"rows": L.rows, "order": L.order, "history": L.history, "keywords": L.keywords})
        except Exception:
            diag.swallowed()
        try:
            L.save()
            self.ws.clear_recovery("effort", L.path)
            if backup:
                try:
                    self.ws.backup(L.path, "effort")
                except OSError:
                    diag.swallowed()
            return True
        except (E.ListLocked, OSError):
            diag.swallowed()
            return False

    # ------------------------------------------------------------ restore and save the session (shared with the classic window)
    def restore(self):
        """The effort's last results (the classic window's session.json), as they were."""
        s = self.ws.load_session() or {}
        self.results = s.get("results") or {}
        self.manual_items = s.get("manual_items") or {}
        self.session_decisions = s.get("session_decisions") or {}
        ls = s.get("last_scan")
        if ls and ls.get("paths"):
            self.last_scan = {"paths": ls["paths"], "folder": ls.get("folder"), "cache": {}}
            self.scanned_paths.update({os.path.basename(f): f for f in ls["paths"]})
        self.volume_report = s.get("volume_report") or None
        if self.results:
            self.apply_effort()
        return len(self.results)

    def save(self):
        """Write the results back where the classic window keeps them, so either program resumes them."""
        s = self.ws.load_session() or {}
        s.update({"results": self.results, "manual_items": self.manual_items, "session_decisions": self.session_decisions,
                  "last_scan": {"paths": (self.last_scan or {}).get("paths", []), "folder": (self.last_scan or {}).get("folder")}
                  if self.last_scan else s.get("last_scan")})
        self.ws.save_session(s)

    # ------------------------------------------------------------ the scan
    def scan(self, paths, status_callback=None, folder=None):
        """Read the files (on a worker thread), then apply every rule. Returns the effort list report or None."""
        cb = status_callback or (lambda _m: None)
        self.queued_files = list(paths)
        self.scanned_paths.update({os.path.basename(f): f for f in paths})
        capture = {}
        self.last_scan = {"paths": list(paths), "folder": folder, "cache": capture}
        A.CANCEL.clear()
        results = A.analyze_batch(list(paths), cb, capture=capture)
        return self.after_scan(results)

    def after_scan(self, results):
        """The classic window's scan_done without the window."""
        diag.scan_finished(terms=len(results))
        self.results = results
        for term, item in self.manual_items.items():
            if term not in self.results:
                self.results[term] = item
        self.apply_instance_excludes()
        self.apply_customer_defs()
        self.apply_saved_decisions()
        self.apply_picked_definitions()
        self.apply_effort(reload=True)
        for d in self.results.values():
            if d.get("known") and not d.get("effort") and not d.get("excluded"):
                d["status"] = A.KNOWN_STATUS + (f": {d['omit_reason']}" if d.get("omit_reason") else "")
        self.mark_known_in()
        rec = self.effort_after_scan(self.queued_files) if self.effort is not None else None
        self.save()
        return rec

    # ------------------------------------------------------------ QA/QC of our Word volumes (2.66.0)
    def qa_check(self, paths, status_callback=None, reg_rows=(), volumes=()):
        """Scan our Word volumes and check them against the effort list (first use, missing, not approved, definitions
        that differ, unused, each volume's acronym list, banned words, page limits). Returns the report (also kept in
        the effort's session, where the classic window reads it)."""
        import banned
        import volcheck as V
        import volcheck_ui as VU
        cb = status_callback or (lambda _m: None)
        paths = sorted({os.path.abspath(p) for p in paths if p.lower().endswith(".docx")}, key=lambda p: V.natural_key(os.path.basename(p)))
        names = [os.path.basename(p) for p in paths]
        if not paths or len(set(names)) != len(names) or self.effort is None:
            return None
        diag.activity("volume_check_started", files=len(paths))
        try:
            words = banned.load()
        except Exception:
            diag.swallowed(); words = []
        vc = {"paths": paths, "names": names, "defs": {}, "lists": {}, "banned": {}}
        self.queued_files = list(paths)
        self.scanned_paths.update({os.path.basename(f): f for f in paths})
        A.CANCEL.clear()
        results = A.analyze_batch(list(paths), cb)
        VU.qa_collect(paths, A, words, vc)
        self.after_scan(results)
        report = VU.qa_report(self.results, self.effort, vc, A, list(reg_rows), list(volumes))
        self.volume_report = report
        s = self.ws.load_session() or {}
        s["volume_report"] = report
        self.ws.save_session(s)
        diag.activity("volume_check_report", terms=report["summary"]["terms_used"], rows=len(report["first_use"]))
        return report

    def qa_add_missing(self):
        import volcheck_ui as VU
        if not self.volume_report or self.effort is None:
            return 0
        n = VU.qa_add_missing(self.effort, self.volume_report)
        diag.activity("volume_missing_added", added=n)
        self._save_effort_list()
        self.apply_effort()
        self.save()
        return n

    def qa_record_use(self):
        import volcheck_ui as VU
        if not self.volume_report or self.effort is None:
            return 0
        n = VU.qa_record_use(self.effort, self.volume_report)
        diag.activity("volume_use_recorded", n=n)
        self._save_effort_list()
        return n

    # ------------------------------------------------------------ decisions
    def choose(self, term, choice):
        """Apply Choice: a definition for one term, kept for every later scan in this effort."""
        d = self.results.get(term)
        if d is None:
            return False
        self._set_choice(d, choice)
        self.save_choice(term, choice)
        self.save()
        return True

    def exclude(self, terms, on=True):
        n = 0
        for t in terms:
            d = self.results.get(t)
            if d is not None and bool(d.get("excluded")) != on:
                d["excluded"] = on
                n += 1
        self.save()
        return n

    def add(self, terms, definition=""):
        """Add to the effort list (a definition typed for one term goes in with it)."""
        self.entry_def.value = definition if len(terms) == 1 else ""
        self.add_to_effort(list(terms))
        self.entry_def.value = ""
        self.save()
        return self.status.text

    def set_status(self, terms, status, approver=""):
        """Proposed, Needs author, Approved (with the approver) or Rejected; terms not in the list are added first."""
        if self.effort is None:
            return 0
        terms = [t for t in terms if t in self.results]
        missing = [t for t in terms if t not in self.effort.rows]
        if missing:
            self.add_to_effort(missing)
        n = self.effort.set_status(terms, status, approver=(approver or "").strip() or None)
        diag.activity("qt_effort_status_set", n=n)
        self._save_effort_list()
        self.apply_effort()
        self.save()
        return n

    # ------------------------------------------------------------ the effort list itself
    def list_status(self, terms, status, approver=""):
        """Set the status of terms already in the effort list (scanned or not)."""
        if self.effort is None:
            return 0
        terms = [t for t in terms if t in self.effort.rows]
        n = self.effort.set_status(terms, status, approver=(approver or "").strip() or None)
        diag.activity("qt_effort_status_set", n=n)
        self._save_effort_list()
        self.apply_effort()
        self.save()
        return n

    def list_definition(self, term, text):
        ok = self.home_set_definition(term, text)
        self.save()
        return ok

    def list_remove(self, terms):
        self.remove_from_effort(list(terms))
        self.save()
        return len(terms)

    def counts(self):
        out = {"total": len(self.results), "active": 0, "excluded": 0, "choice": 0, "candidate": 0}
        for d in self.results.values():
            if d.get("excluded"):
                out["excluded"] += 1
                continue
            out["active"] += 1
            k = A.status_kind(d.get("status", ""))
            if k in ("choice", "candidate"):
                out[k] += 1
        return out


for _n in _SHARED + ("_set_choice",):
    setattr(AcronymSession, _n, G.__dict__[_n])               # staticmethods stay static
