"""Acronym hunting without a window (2.64.0): the scan of the classic window and everything that happens to its results
afterwards, for the Qt edition. The rules are in acrrules (3.14.0: moved out of the retired classic window): instances you
excluded, the customer's definitions, saved choices, definitions picked from the documents, the effort list (approved
definitions win, rejected terms are hidden), known names, where each term is known (customer documents, customer list,
master database), and the effort list's Found in. Rules only (No AI); nothing leaves the PC.
"""
import os
import app_gui as A
import diag
import effort as E
from acrrules import AcronymRules                             # 3.14.0: the rules the classic window kept, on their own


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


class AcronymSession(AcronymRules):
    """One effort's acronym results. ws: the effort's Workspace; effort_path: its acronym list; efforts: the registry."""

    def __init__(self, ws, effort_path, efforts, settings=None):
        self.ws, self.efforts = ws, efforts
        try:                                                # 3.80.0: the pictures' readings kept with the effort
            import picreadings as PR
            PR.use(getattr(ws, "root", None) or None)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.settings = settings if settings is not None else {}
        self.project = None
        self.results, self.manual_items, self.session_decisions = {}, {}, {}
        self.scanned_paths, self.queued_files = {}, []
        self.forms = {}
        self.last_scan = None
        self.volume_report = None
        self.plurals = {}
        self.omitted = {}                                    # 3.51.0: {term: True} omitted in this effort, on every scan
        self.parts = {}                                      # 3.76.0: {part: {"whole", "places"}} part of a longer term
        self.rules_extra = {}                                # 3.92.0: {"hyphen_whole": bool} the effort's own reading rules
        self.first_use_set = {}                              # 3.51.0: {term: {file: place}} chosen first uses
        self._last_vc = None
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
        self.plurals = dict(s.get("plurals") or {})                   # 2.86.0: {plural: singular}
        self.forms = dict(s.get("forms") or {})                       # 3.34.1: {FY27: FY}
        self.omitted = dict(s.get("omitted") or {})                   # 3.51.0
        self.parts = dict(s.get("parts") or {})                       # 3.76.0: part of a longer term
        self.rules_extra = dict(s.get("rules_extra") or {})           # 3.92.0: letters joined by a hyphen are one term
        self.first_use_set = dict(s.get("first_use_set") or {})
        for t in self.omitted:                                        # results saved before 3.51.0 kept the flag only
            if t in self.results:
                self.results[t]["excluded"] = True
        if self.results:
            self.apply_effort()
            self.apply_plurals()
            self.apply_forms()
            self.omitted_to_list()
        return len(self.results)

    def omitted_to_list(self):
        """3.76.0: Omit is gone from the Acronyms page; a term omitted in an effort becomes Not a term in its list."""
        if self.effort is None or not getattr(self, "omitted", None):
            return 0
        terms = [t for t in self.omitted if t in self.results]
        n = self.set_status(terms, "Not a term") if terms else 0
        self.omitted = {}
        self.save()
        return n

    def save(self):
        """Write the results back where the classic window keeps them, so either program resumes them."""
        import picreadings as PR
        PR.flush()
        s = self.ws.load_session() or {}
        s.update({"results": self.results, "manual_items": self.manual_items, "session_decisions": self.session_decisions,
                  "plurals": getattr(self, "plurals", {}), "forms": getattr(self, "forms", {}),
                  "omitted": getattr(self, "omitted", {}), "parts": getattr(self, "parts", {}), "rules_extra": getattr(self, "rules_extra", {}), "first_use_set": getattr(self, "first_use_set", {}),
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
        self.apply_plurals()
        self.apply_forms()                                      # 3.34.1
        self.apply_omitted()                                    # 3.51.0: Omit holds on every scan
        import acrparts
        acrparts.apply_parts(self)                              # 3.76.0: part of a longer term, where it sits
        import acrpage
        acrpage.join_hyphenated(self)                           # 3.92.0: the effort's hyphen rule, on every scan
        rec = self.effort_after_scan(self.queued_files) if self.effort is not None else None
        self.save()
        return rec

    # ------------------------------------------------------------ plurals (2.86.0)
    PLURAL = "Plural of"

    def apply_plurals(self):
        """A plural (CDRLs) stays a found term, tied to its singular (CDRL): its uses count for the singular, it is never
        a row of its own in the lists you submit, and it keeps being found in every scan."""
        pl = getattr(self, "plurals", None) or {}
        for term, d in self.results.items():
            sing = pl.get(term)
            if sing:
                d["plural_of"] = sing
                d["alt_of"] = sing
                d["status"] = f"{self.PLURAL} {sing}"
                sd = self.results.get(sing) or {}
                if sd.get("selected_definition") and not d.get("selected_definition"):
                    d["selected_definition"] = sd["selected_definition"]
            elif d.get("plural_of"):
                d.pop("plural_of", None)

    # ------------------------------------------------------------ 3.34.1 forms: FY27 is written as FY plus a number
    FORM = "Form of"

    @staticmethod
    def form_guess(term):
        """FY27 -> FY, FY2027 -> FY, CDRL-A001 -> CDRL, Rev2 -> ''; '' when no letters lead a number or code."""
        import re
        m = re.match(r"^([A-Z][A-Za-z&]{1,9})[-/ ]?(?:\d|[A-Z]\d)[\w./-]*$", term or "")
        return m.group(1) if m and m.group(1).isupper() and m.group(1) != term else ""

    def apply_forms(self):
        """A form (FY27) stays found and tied to its term (FY): never a row of its own in the lists you submit, its uses
        count for the term, and it takes the term's definition. A term found only inside its forms is kept as a term of
        its own, with their places, so you define it once."""
        fm = getattr(self, "forms", None) or {}
        by_base = {}
        for term, base in fm.items():
            d = self.results.get(term)
            if d is None:
                continue
            by_base.setdefault(base, []).append(d)
            d["form_of"] = base
            d["alt_of"] = base
            d["status"] = f"{self.FORM} {base}"
        for base, ds in by_base.items():
            bd = self.results.get(base)
            if bd is None or bd.get("from_forms"):
                locs = list(dict.fromkeys(l for d in ds for l in d.get("locations", [])))
                tmpl = dict(ds[0])
                for k in ("form_of", "alt_of", "plural_of", "selected_definition", "excluded", "status", "effort", "known"):
                    tmpl.pop(k, None)
                bd = dict(tmpl, locations=locs, count=sum(int(d.get("count") or 0) for d in ds), from_forms=True,
                          status=(bd or {}).get("status", "Needs Review"), definitions=(bd or {}).get("definitions", []),
                          **({"selected_definition": bd["selected_definition"]} if bd and bd.get("selected_definition") else {}))
                self.results[base] = bd
                self.manual_items[base] = dict(bd)
            for d in ds:
                if bd.get("selected_definition") and not d.get("selected_definition"):
                    d["selected_definition"] = bd["selected_definition"]
        for term, d in self.results.items():
            if d.get("form_of") and term not in fm:
                d.pop("form_of", None)

    def set_form(self, term, base):
        """term is written as base plus a number or code (FY27 as FY): base becomes a term (found or not) and term is
        tied to it. Returns True when set."""
        base = " ".join((base or "").split())
        if not term or not base or term == base:
            return False
        self.forms = dict(getattr(self, "forms", {}) or {})
        self.forms[term] = base
        self.apply_forms()
        self.apply_effort()
        self.apply_forms()
        self.save()
        return True

    def clear_form(self, term):
        fm = dict(getattr(self, "forms", {}) or {})
        base = fm.pop(term, None)
        if base is None:
            return False
        self.forms = fm
        d = self.results.get(term)
        if d is not None:
            d.pop("form_of", None); d.pop("alt_of", None)
            d["status"] = "Needs Review"
        if base not in fm.values():
            bd = self.results.get(base)
            if bd is not None and bd.get("from_forms"):
                self.results.pop(base, None)
                self.manual_items.pop(base, None)
        self.apply_effort()
        self.save()
        return True

    @staticmethod
    def singular_guess(term):
        """CDRLs -> CDRL, SOWs -> SOW, ICD's -> ICD; '' when it does not look like a plural."""
        import re
        m = re.match(r"^([A-Z][A-Z0-9&/.-]+?)(?:'s|s|es)$", term or "")
        return m.group(1) if m and len(m.group(1)) >= 2 else ""

    def set_plural(self, term, singular):
        singular = " ".join((singular or "").split())
        if not term or not singular or term == singular:
            return False
        self.plurals = dict(getattr(self, "plurals", {}) or {})
        self.plurals[term] = singular
        self.apply_plurals()
        self.save()
        return True

    def clear_plural(self, term):
        pl = dict(getattr(self, "plurals", {}) or {})
        if pl.pop(term, None) is None:
            return False
        self.plurals = pl
        d = self.results.get(term)
        if d is not None:
            d.pop("plural_of", None); d.pop("alt_of", None)
            d["status"] = "Needs Review"
        self.apply_effort()
        self.save()
        return True

    # ------------------------------------------------------------ QA/QC of our Word volumes (2.66.0)
    def qa_check(self, paths, status_callback=None, reg_rows=(), volumes=()):
        """Scan our Word volumes and check them against the effort list (first use, missing, not approved, definitions
        that differ, unused, each volume's acronym list, banned words, page limits). Returns the report (also kept in
        the effort's session, where the classic window reads it)."""
        import banned
        import volcheck as V
        import qacheck as VU
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
        self._last_vc = vc
        import firstuse as FU                                   # 3.51.0: the first uses the person chose
        FU.apply(self.results, self.first_use_set, {os.path.basename(p): p for p in paths}.get)
        report = VU.qa_report(self.results, self.effort, vc, A, list(reg_rows), list(volumes))
        self.volume_report = report
        s = self.ws.load_session() or {}
        s["volume_report"] = report
        self.ws.save_session(s)
        diag.activity("volume_check_report", terms=report["summary"]["terms_used"], rows=len(report["first_use"]))
        return report

    def qa_add_missing(self):
        import qacheck as VU
        if not self.volume_report or self.effort is None:
            return 0
        n = VU.qa_add_missing(self.effort, self.volume_report)
        diag.activity("volume_missing_added", added=n)
        self._save_effort_list()
        self.apply_effort()
        self.save()
        return n

    def qa_record_use(self):
        import qacheck as VU
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
        """3.51.0 Omit: the terms are left out of this effort (on), on this scan and every later one; off brings them back."""
        n = 0
        for t in terms:
            d = self.results.get(t)
            if on:
                self.omitted[t] = True
            else:
                self.omitted.pop(t, None)
            if d is not None and bool(d.get("excluded")) != on:
                d["excluded"] = on
                n += 1
        self.save()
        return n

    omit = exclude

    def apply_omitted(self):
        for t in self.omitted:
            d = self.results.get(t)
            if d is not None:
                d["excluded"] = True

    # ------------------------------------------------------------ 3.51.0 first use chosen by the person
    def set_first_use(self, term, loc):
        import firstuse as FU
        FU.set_first_use(self.first_use_set, term, loc)
        self.save()
        return True

    def clear_first_use(self, term, fname=None):
        import firstuse as FU
        FU.clear_first_use(self.first_use_set, term, fname)
        self.save()
        return True

    def qa_rebuild(self, reg_rows=(), volumes=()):
        """The last check's report again (after Set as first use), without reading the files again."""
        import qacheck as VU
        import firstuse as FU
        vc = self._last_vc
        if not vc or self.effort is None:
            return None
        paths = {os.path.basename(p): p for p in vc["paths"]}
        FU.apply(self.results, self.first_use_set, paths.get)
        report = VU.qa_report(self.results, self.effort, vc, A, list(reg_rows), list(volumes))
        self.volume_report = report
        return report

    def add(self, terms, definition=""):
        """Add to the effort list (a definition typed for one term goes in with it)."""
        self.entry_def.value = definition if len(terms) == 1 else ""
        self.add_to_effort(list(terms))
        self.entry_def.value = ""
        self.save()
        return self.status.text

    def forget_files(self, names):
        """4.23.3: documents deleted from the effort leave the acronym results too. Their places come off every term; a
        term found nowhere else, not in the effort's list and not added by hand, goes; the files leave the last scan.
        Returns how many terms went. (Acros & Abs kept showing a deleted document's page until the next scan.)"""
        names = {n for n in names if n}
        if not names:
            return 0
        mine = lambda loc: any(str(loc).startswith(n) for n in names)                  # noqa: E731
        gone = 0
        for t in list(self.results):
            d = self.results[t]
            locs = list(d.get("locations", []))
            kept = [x for x in locs if not mine(x)]
            if len(kept) == len(locs):
                continue
            d["locations"] = kept
            if not kept and not d.get("effort") and not d.get("manual"):
                del self.results[t]
                gone += 1
        if self.last_scan:
            self.last_scan["paths"] = [p for p in self.last_scan.get("paths", []) if os.path.basename(p) not in names]
        for n in names:
            self.scanned_paths.pop(n, None)
        self.save()
        return gone

    def set_status(self, terms, status, approver=""):
        """In the list or Not a term (3.76.0); terms not in the list are added first."""
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
