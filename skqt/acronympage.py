"""Acronym scan and review in Qt (2.64.0): scan files or a folder for acronyms, abbreviations, units and symbols (typed
text and text in pictures), then review every term: its status, its definition and where it came from (customer
documents, customer list, master database), where it was found, and the effort list. Choose a definition, add to the
effort list or say it is not a term (3.76.0: no approval; a term is in the list or Not a term), export the report. The rules are
the classic window's own (acrsession.py); results are shared with it. Rules only (No AI); nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLineEdit, QProgressBar,
                               QScrollArea, QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import app_gui as A
import acrsession as S
import scanprogress as SP
from . import design as D
from . import progress as PR
from .adaptive import FlowLayout
from . import acrextras as AX                                       # 3.51.0

COLS = ["Term", "Type", "Count", "Found in", "Change", "Status", "Definition", "Known in", "Acronym list", "Source"]   # 3.51.0: Change, Source
# 3.34.1: the few status filters a reviewer uses (Type, Found in and the search do the rest)
STATUS = ("All statuses", "To decide", "In the list", "No definition yet", "Needs a choice", "No longer found", "Not a term")   # 3.76.0


def status_ok(d, wanted, kind):
    """Whether a term passes a status filter. To decide: every term not in the effort's list yet and not Not a term
    (3.76.0: adding a term to the list is the decision; there is no approval)."""
    if wanted == "To decide":
        return (not d.get("excluded") and not d.get("known") and not d.get("effort") and kind != "error"
                and not d.get("gone"))
    if wanted == "In the list":
        return d.get("effort") == "In the list"
    if wanted == "No definition yet":
        return d.get("effort") == "In the list" and not (d.get("list_definition") or "").strip()
    if wanted == "Needs a choice":
        return kind == "choice"
    if wanted == "No longer found":
        return bool(d.get("gone"))
    if wanted == "Not a term":
        return bool(d.get("excluded")) or d.get("effort") == "Not a term"
    return True
KIND_TONE = {"choice": "warn", "candidate": "cust", "resolved": "ok", "error": "crit", "excluded": "head", "other": "accent"}


class ScanWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, session, paths, folder=None):
        super().__init__()
        self.session, self.paths, self.folder = session, paths, folder

    def run(self):
        try:
            rec = self.session.scan(self.paths, lambda m: (A.check_cancel(), self.progress.emit(str(m))), folder=self.folder)
            self.finished_ok.emit(rec)
        except A.ScanCancelled:
            self.failed.emit("cancelled")
        except Exception as e:
            diag.swallowed()
            self.failed.emit(type(e).__name__)


class AcronymPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.session = None
        self.worker = None
        self.terms = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.where = D.label("<b>START</b> &nbsp;Acronyms, abbreviations, units and symbols in the customer's documents, or in your "
                             "own drafts (Scan files..., Scan the library...). Add them to the acronym list; first use in your volumes "
                             "is checked in Submission Check, and the lists you submit come from Lists to Submit.", "muted")
        self.where.setTextFormat(Qt.RichText); v.addWidget(self.where)                  # 2.86.0: which end this page serves
        top = FlowLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.b_cust = D.button("Scan the customer documents", "primary", lambda: self.scan_customer(),
                               "Every customer document in the Library (the newest version of each), no picking")
        top.addWidget(self.b_cust)
        self.b_files = D.button("Scan files...", None, lambda: self.pick_files())
        self.b_folder = D.button("Scan a folder...", None, lambda: self.pick_folder())
        from . import acrbridge as AB                                    # 3.78.0: the Effort Library's folders
        self.b_lib = D.button("Scan the library...", None, lambda: AB.scan_library(self),
                              "The files in the Effort Library's folders you tick (Customer Documents and Graphics at first)")
        self.b_folder.hide()                                             # in an effort, Scan the library... (the tool keeps it)
        self.b_again = D.button("Scan again", None, lambda: self.scan_again(), "The same files again: new choices and definitions apply")
        self.b_paste = D.button("Paste a picture", None, lambda: AX.paste_picture(self), "A screenshot or a copied figure (Ctrl+V): "
                                "read with the files already scanned")             # 3.53.0
        self.b_cancel = D.button("Cancel", "danger", lambda: self.cancel()); self.b_cancel.hide()
        self.b_window = D.button("Open in its own window", "ghost", lambda: self.own_window(),     # 3.50.0
                                 "Acros & Abs Finder: scan any files and export the list, apart from this effort")
        for b in (self.b_files, self.b_lib, self.b_folder, self.b_again, self.b_paste, self.b_cancel, self.b_window):
            top.addWidget(b)
        self.progress = D.label("", "muted", wrap=False); top.addWidget(self.progress, 1)
        # 2.86.0: no separate customer acronym list: the customer's terms are every acronym in its documents, and a
        # glossary the customer includes is one of those documents: its definitions come first automatically
        self.p_active = D.Pill("0 terms", "accent"); self.p_choice = D.Pill("0 need a choice", "ok"); self.p_new = D.Pill("0 new", "ok")
        for p in (self.p_active, self.p_choice, self.p_new):
            top.addWidget(p)
        f = FlowLayout(); f.setSpacing(D.SPACE["s"]); v.addLayout(f)
        self.f_type = QComboBox(); self.f_type.addItem(A.ALL_TYPES)
        self.f_status = QComboBox(); self.f_status.addItems(list(STATUS))   # 3.34.1: the few that matter
        self.f_found = QComboBox(); self.f_found.addItems(list(A.FOUND_FILTERS))
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search terms and definitions"); self.f_search.setClearButtonEnabled(True)
        self.f_search.setMinimumWidth(280)
        from . import symbols as SYM
        SYM.attach(self.f_search)                                       # 3.50.0: search for H₂O, µm, Δv
        self.f_excl = QCheckBox("Show Not a term")
        self.f_pics = QCheckBox("Found in pictures")                     # 3.53.0: only terms read from a picture
        self.f_pics.setToolTip("Only the terms read from pictures: image files, pictures in documents, diagrams and charts")
        self.f_pics.toggled.connect(lambda _on: self.fill())
        self.f_forms = QCheckBox("Show plurals and forms")           # 3.34.1: decided ones stay out of the way
        self.f_forms.setToolTip("A term you set as a plural (CDRLs) or a form (FY27) is tied to its term and hidden from the "
                                "list; tick this to see them (greyed, with what they belong to). A search finds them too.")
        for w in (self.f_type, self.f_status, self.f_found):
            w.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_search.textChanged.connect(lambda _t: self.fill())
        self.f_excl.toggled.connect(lambda _on: self.fill())
        self.f_forms.toggled.connect(lambda _on: self.fill())
        for w in (self.f_type, self.f_status, self.f_found):
            f.addWidget(w)
        f.addWidget(self.f_search, 1); f.addWidget(self.f_pics); f.addWidget(self.f_excl); f.addWidget(self.f_forms)
        self.showing = D.label("", "muted", wrap=False); f.addWidget(self.showing)
        self.bulk = D.label("", None, wrap=False)                         # 3.88.0: the easy ones in one click, named
        self.bulk.setTextFormat(Qt.RichText); self.bulk.linkActivated.connect(lambda _h: self.add_one_customer())
        v.addWidget(self.bulk)
        f.addWidget(D.button("Export the report...", None, lambda: self.export(), "Exactly the rows shown, as a CSV that opens in Excel"))
        tb = FlowLayout(); tb.setSpacing(D.SPACE["s"]); v.addLayout(tb)            # 3.51.0: the classic window's tools
        for b in AX.top_buttons(self):
            tb.addWidget(b)
        # 3.71.0: while a scan runs, where it is, how much is done and about how long is left
        self.scanbar = QFrame(); self.scanbar.setObjectName("pinStrip")
        sb = QHBoxLayout(self.scanbar); sb.setContentsMargins(D.SPACE["m"], 6, D.SPACE["m"], 6); sb.setSpacing(D.SPACE["m"])
        self.scan_where = D.label("", None, wrap=False); self.scan_where.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.scan_pct = QProgressBar(); self.scan_pct.setRange(0, 100); self.scan_pct.setTextVisible(False); self.scan_pct.setFixedSize(280, 12)
        self.scan_left = D.label("", "muted", wrap=False); self.scan_left.setMinimumWidth(240)
        for w, st in ((self.scan_where, 1), (self.scan_pct, 0), (self.scan_left, 0)):
            sb.addWidget(w, st)
        self.scanbar.hide(); v.addWidget(self.scanbar)
        self.scan_prog = None
        self.scan_tick = QTimer(self, interval=1000, timeout=self.tick_scan)
        split = QSplitter(Qt.Horizontal)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(6, QHeaderView.Stretch)
        for i, w in enumerate((100, 120, 54, 70, 70, 150, 0, 110, 90, 170)):
            if i != 6:
                self.table.setColumnWidth(i, w)
        self.table.itemSelectionChanged.connect(self.show_detail)
        AX.install(self)                                                 # 3.51.0: sort, text size, right-click, Details
        AX.install_paste(self)                                           # 3.53.0: Ctrl+V pastes a picture
        split.addWidget(self.table)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True); self.card_area.setMinimumWidth(380)
        self.card = D.Card("Term")
        self.card_area.setWidget(self.card)
        self.body = QVBoxLayout(); self.body.setSpacing(D.SPACE["s"]); self.card.body.addLayout(self.body)
        split.addWidget(self.card_area)
        split.setSizes([1000, 420])
        v.addWidget(split, 1)
        self.empty = D.EmptyState("No terms yet", "Scan the customer documents: every acronym, abbreviation, unit "
                                                  "and symbol they use, in typed text and in pictures.", "Scan the customer documents",
                                   lambda: self.scan_customer())
        v.addWidget(self.empty)
        self.tool = False
        from . import acrlayout as AL                                    # 3.92.0: three panes, counts, keys
        AL.install(self)

    def tool_mode(self):
        """3.50.0: the page inside Acronym Finder: no effort, no customer Library; Scan files... starts it."""
        self.tool = True
        from . import acrtabs as TB
        TB.tool(self)                                                  # 3.93.0: no tabs in the tool
        self.b_cust.hide(); self.b_window.hide(); self.b_lib.hide(); self.b_folder.show()
        self.where.setText("<b>ACRONYM FINDER</b> &nbsp;Scan files or a folder: every acronym, abbreviation, unit and symbol, in "
                           "typed text and in pictures, with its meaning and the picture or passage where it was found.")
        self.empty.hide()
        self.empty = D.EmptyState("No terms yet", "Scan files or a folder: your drafts, submittals, customer documents, "
                                  "pictures or PDFs.", "Scan files...", lambda: self.pick_files())
        self.layout().addWidget(self.empty)

    def own_window(self):
        from .acrtool import open_tool
        return open_tool(getattr(self.host, "config_dir", None) or __import__("app_gui").CONFIG_DIR)

    # ------------------------------------------------------------ the effort
    def load(self):
        """Open the effort's acronym results (the classic window's last results, if any)."""
        h = self.host
        self.session = None
        if h.ws is not None:
            try:
                import app_gui
                self.session = S.AcronymSession(h.ws, h.effort_path, h.efforts, app_gui.load_settings())
                self.session.restore()
            except Exception:
                diag.swallowed()
                self.session = None
                h.status("The effort's acronym list could not be opened.")
        self.refresh()

    def refresh(self):
        h = self.host
        if self.session is not None and (h.ws is None or self.session.ws.root != h.ws.root):
            self.session = None
        if self.session is None and h.ws is not None and self.worker is None:
            self.load()
            return
        self.setEnabled(h.ws is not None)
        self.fill_types()
        self.fill()

    def fill_types(self):
        keep = self.f_type.currentText()
        types = sorted({A.base_type(d["category"]) for d in (self.session.results.values() if self.session else [])})
        self.f_type.blockSignals(True)
        self.f_type.clear(); self.f_type.addItems([A.ALL_TYPES] + types)
        self.f_type.setCurrentText(keep if keep in types else A.ALL_TYPES)
        self.f_type.blockSignals(False)

    def rows(self):
        s = self.session
        if s is None:
            return []
        ftype, fstat, ffound = self.f_type.currentText(), self.f_status.currentText(), self.f_found.currentText()
        q = self.f_search.text().strip().casefold()
        out = []
        for term, d in s.results.items():
            if d.get("excluded") and not (self.f_excl.isChecked() or fstat == "Not a term"):
                continue
            if (d.get("plural_of") or d.get("form_of") or d.get("part_of")) and not (self.f_forms.isChecked() or (q and q == term.casefold())):
                continue                                     # 3.34.1: a plural or form is decided: tied to its term, out of the list
            if ftype != A.ALL_TYPES and A.base_type(d["category"]) != ftype:
                continue
            if fstat != STATUS[0] and not status_ok(d, fstat, A.status_kind(d.get("status", ""))):
                continue
            if ffound != A.FOUND_FILTERS[0] and s.found_in(d) != ffound.split()[0]:
                continue
            if q and q not in term.casefold() and q not in d.get("selected_definition", "").casefold():
                continue
            if self.f_pics.isChecked() and not AX.in_pictures(d):
                continue
            out.append(term)
        return AX.sorted_terms(self, sorted(out, key=lambda t: s.sort_key(t, s.results[t])))

    def fill(self):
        s = self.session
        keep = self.current()
        self.terms = self.rows()
        has = bool(s and s.results)
        self.show_bulk()
        from . import acrlayout as AL
        AL.fill_counts(self)
        self.empty.setVisible(not has and self.worker is None)
        self.table.setVisible(has or self.worker is not None)
        self.card_area.setVisible(has)
        self.table.setRowCount(len(self.terms))
        fmap = {}                                              # 3.34.1: {term: its plurals and forms}
        for t_, d_ in (s.results.items() if s else []):
            b_ = d_.get("plural_of") or d_.get("form_of")
            if b_:
                fmap.setdefault(b_, []).append(t_)
        for i, t in enumerate(self.terms):
            d = s.results[t]
            kind = "excluded" if d.get("excluded") else A.status_kind(d.get("status", ""))
            from .acrextras import source_text
            vals = [t, d.get("category", ""), d.get("count", 0), s.found_in(d), d.get("change", ""), A.status_text(d.get("status", "")),
                    d.get("selected_definition", ""), s.known_cell(t, d), d.get("effort", ""), source_text(d)]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if c == 5:
                    it.setForeground(D.color(KIND_TONE.get(kind, "accent")))
                if c == 0 and d.get("excluded"):
                    it.setForeground(D.color("faint"))
                if d.get("plural_of") or d.get("form_of"):       # 3.34.1: greyed and italic, tied to its term
                    it.setForeground(D.color("faint"))
                    fi = it.font(); fi.setItalic(True); it.setFont(fi)
                    if c == 0:
                        it.setToolTip(f"{'Plural' if d.get('plural_of') else 'A form'} of {d.get('plural_of') or d.get('form_of')}")
                if c == 0 and (forms := sorted(fmap.get(t, []))):
                    it.setText(f"{t}  (+{', '.join(forms[:3])}{'...' if len(forms) > 3 else ''})")
                    it.setToolTip("Its plurals and forms: " + ", ".join(forms))
                self.table.setItem(i, c, it)
        n = s.counts() if s else {"active": 0, "choice": 0, "candidate": 0, "excluded": 0}
        self.p_active.setText(f"{n['active']} terms"); self.p_choice.setText(f"{n['choice']} need a choice")
        self.p_choice.set_tone("warn" if n["choice"] else "ok")
        self.p_new.setText(f"{n['candidate']} new candidates"); self.p_new.set_tone("cust" if n["candidate"] else "ok")
        self.showing.setText(f"Showing {len(self.terms)} of {len(s.results)}" if has else "")
        self.b_again.setEnabled(bool(s and s.last_scan) and self.worker is None)
        if keep in self.terms:
            self.select(keep)
        else:
            self.show_detail()

    def _forms_of(self, term):
        """3.34.1: the plurals and forms tied to a term."""
        s = self.session
        return sorted(t for t, d in (s.results.items() if s else []) if (d.get("plural_of") or d.get("form_of")) == term)

    def current(self):
        i = self.table.currentRow()
        return self.terms[i] if 0 <= i < len(self.terms) else None

    def selected_terms(self):
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        return [self.terms[r] for r in rows if r < len(self.terms)]

    def select(self, term):
        if term in self.terms:
            self.table.selectRow(self.terms.index(term))
            self.table.scrollToItem(self.table.item(self.terms.index(term), 0))
            return True
        return False

    # ------------------------------------------------------------ the card
    def _clear(self):
        mb = getattr(self, "mid_box", None)                              # 3.92.0: the page in the middle
        if mb is not None:
            for i in reversed(range(mb.count())):
                w = mb.itemAt(i).widget()
                if w is not None and w is not self.mid_hint:
                    mb.takeAt(i); w.setParent(None); w.deleteLater()
            self.mid_hint.setVisible(True)
        while self.body.count():
            it = self.body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None); w.deleteLater()
            elif it.layout() is not None:
                lay = it.layout()
                while lay.count():
                    x = lay.takeAt(0).widget()
                    if x is not None:
                        x.setParent(None); x.deleteLater()

    def show_detail(self):
        self._clear()
        s = self.session
        terms = self.selected_terms()
        if s is None or not terms:
            self.card.title.setText("Term")
            self.body.addWidget(D.label("Select a term to see its definitions, where it was found and the effort list.", "muted"))
            return
        if len(terms) > 1:
            self.card.title.setText(f"{len(terms)} terms")
            self._actions(terms)
            return
        t = terms[0]
        self.card.title.setText(t)
        from . import acrcard                                          # 3.61.0: a lighter card, details folded
        acrcard.build(self, t, KIND_TONE)
        from . import acrlayout as AL                                    # 3.92.0: keys, a longer term, where it goes
        AL.card_more(self, t)
        k = self.terms.index(t) if t in self.terms else -1               # 3.80.0: the next term's picture, drawn ahead
        if 0 <= k < len(self.terms) - 1:
            from . import foundview as FV
            nxt = self.terms[k + 1]
            FV.prefetch(nxt, s.results.get(nxt, {}).get("locations", []), self.path_of)

    def use_selected(self):
        """3.50.0: the words selected in the passage where the term was found become the definition typed."""
        wv = getattr(self, "where_view", None)
        sel = wv.text.textCursor().selectedText().strip() if wv is not None else ""
        if not sel and wv is not None:                                # 3.61.0: or the box clicked in the picture
            sel = wv.reading.text().strip()
        if not sel:
            self.host.status("Select the words in the passage under Where it was found first.")
            return ""
        self.typed.setText(" ".join(sel.replace("\u2029", " ").split()))
        self.typed.setFocus()
        return self.typed.text()

    def _actions(self, terms):
        """3.76.0: two decisions (Add to effort list, Not a term), what the picture says, and the rest under More."""
        from . import acrpart as AP
        r1 = QHBoxLayout(); r1.setSpacing(D.SPACE["s"])
        r1.addWidget(D.button("Add to effort list", "primary", lambda: self.add(terms)))
        not_term = all((self.session.results[t].get("effort") == "Not a term" or self.session.results[t].get("excluded"))
                       for t in terms)
        if not_term:
            r1.addWidget(D.button("Put back in the list", None, lambda: self.set_status(terms, "In the list"),
                                  "It is a term after all: back in this effort's list"))
        else:
            r1.addWidget(D.button("Not a term", "danger", lambda: self.set_status(terms, "Not a term"),
                                  "Not a term in this effort: this scan and every later one, new document versions too"))
        if len(terms) == 1 and AX.in_pictures(self.session.results[terms[0]]):
            r1.addWidget(D.button("The picture says something else...", None, lambda: AP.picture_menu(self, terms[0]),
                                  "Part of a longer term, misread letters, or not text at all"))
        self.more_btn = D.button("More", "ghost", lambda: AP.more_menu(self, terms))
        r1.addWidget(self.more_btn)
        r1.addStretch(1)
        self.body.addLayout(r1)

    def path_of(self, name):
        """Where a scanned file is (the last scan, else the Library's customer documents). 3.34.1: matched without
        regard to case, and a place written before its file name was read whole ('Section L (1).pdf') still finds it."""
        s = self.session
        known = dict((getattr(s, "scanned_paths", {}) or {}) if s is not None else {})
        p = known.get(name, "")
        if p and os.path.isfile(p):
            return p
        cands = [q for q in known.values() if q and os.path.isfile(q)] + self.customer_paths()
        low = (name or "").casefold()
        for q in cands:
            if os.path.basename(q).casefold() == low:
                return q
        hits = [q for q in cands if low.startswith(os.path.basename(q).casefold())]   # the longest name that starts it
        if hits:
            return max(hits, key=lambda q: len(os.path.basename(q)))
        return p

    def plural(self, term, singular=None):
        """2.86.0: the term is the plural of another term."""
        if singular is None:
            from PySide6.QtWidgets import QInputDialog
            singular, ok = QInputDialog.getText(self, "Plural of...", f"{term} is the plural of:", text=self.session.singular_guess(term))
            if not ok:
                return False
        ok = self.session.set_plural(term, singular)
        if ok:
            diag.activity("acronym_plural_set")
            self.host.toast(f"{term}: plural of {singular.strip()}. Still found; never its own row in the lists you submit.")
            self.fill()
            self.select(singular.strip())                      # 3.34.1: the plural leaves the list; its term is shown
        return ok

    def form(self, term, base=None):
        """3.34.1: the term is written as another term plus a number or code (FY27 as FY)."""
        if base is None:
            from PySide6.QtWidgets import QInputDialog
            base, ok = QInputDialog.getText(self, "A form of...", f"{term} is written as this term plus a number or code:",
                                            text=self.session.form_guess(term))
            if not ok:
                return False
        ok = self.session.set_form(term, base)
        if ok:
            diag.activity("acronym_form_set")
            self.host.toast(f"{term}: a form of {base.strip()}. Define {base.strip()} once; {term} stays found and tied to it.")
            self.fill()
            self.select(base.strip())
        return ok

    def not_form(self, term):
        ok = self.session.clear_form(term)
        if ok:
            self.fill()
        return ok

    def not_plural(self, term):
        ok = self.session.clear_plural(term)
        if ok:
            self.fill()
        return ok

    # ------------------------------------------------------------ decisions
    def choose(self, term, choice):
        self.session.choose(term, choice)
        diag.activity("qt_acronym_choice")
        self.fill()
        return self.session.results[term]["status"]

    def one_customer(self):
        import acrsuggest as AS
        s = self.session
        if s is None:
            return []
        return AS.one_customer(s.results, lambda d: status_ok(d, "To decide", A.status_kind(d.get("status", ""))))

    def show_bulk(self):
        terms = self.one_customer()
        if not terms:
            self.bulk.setText(""); self.bulk.setVisible(False)
            return terms
        names = ", ".join(terms[:6]) + (f" and {len(terms) - 6} more" if len(terms) > 6 else "")
        self.bulk.setText(f"<a href='add'>Add {len(terms)} with one customer definition: {names}</a>"
                          "  <span style='color:gray'>(spelled out once by the customer, nothing that disagrees)</span>")
        self.bulk.setVisible(True)
        return terms

    def add_one_customer(self):
        """Suggest, never decide: the link names the terms and the reason; each is added with its customer definition."""
        s = self.session
        terms = self.one_customer()
        for t in terms:
            d = s.results[t]
            s.add([t], (d.get("customer_definitions") or [""])[0])
        diag.activity("acronym_one_customer_added", n=len(terms))
        self.host.toast(f"{len(terms)} added with their customer definition.")
        self.fill()
        return terms

    def add(self, terms, definition=None):
        typed = definition if definition is not None else (self.typed.text().strip() if len(terms) == 1 and hasattr(self, "typed") else "")
        after = self._after(terms)
        msg = self.session.add(terms, typed)
        diag.activity("qt_acronym_added", n=len(terms))
        self.host.toast(msg or "Added to the effort list")
        self.fill()
        self._move_on(after)
        return msg

    def _after(self, terms):
        """4.23.0: the term to go to once these are decided: the next one still to decide after them, in the list's order
        (Nicholas 13:51: Add to effort list moves on by itself, as Not a term does)."""
        import acrpage as P
        from . import acrlayout as AL
        s, order = self.session, list(getattr(self, "terms", []) or [])
        if s is None or len(terms) != 1 or terms[0] not in order:
            return None
        k = order.index(terms[0]) + 1
        for t in order[k:] + order[:k - 1]:
            d = s.results.get(t)
            if d is not None and P.passes(d, "To decide", AL.kind_of(d)):
                return t
        return None

    def _move_on(self, t):
        if t is not None and t in getattr(self, "terms", []) and self.session is not None and t in self.session.results:
            self.select(t)

    def set_status(self, terms, status, approver=""):
        after = self._after(terms) if status == "Not a term" else None
        n = self.session.set_status(terms, status, approver)
        eff = self.session.effort
        if eff is None:                                     # the Acronym Finder window: Not a term hides it for this scan
            n = self.session.exclude(terms, status == "Not a term")
        what = "not a term" if status == "Not a term" else "in the list"
        self.host.toast(f"Acronym list: {n} {what}" + ("" if eff is None or not eff.pending else ". NOT SAVED yet: close the list in Excel."))
        self.fill()
        self._move_on(after)
        return n

    def exclude(self, terms, on=True):
        n = self.session.exclude(terms, on)
        diag.activity("qt_acronym_excluded", n=n)
        self.fill()
        return n

    # ------------------------------------------------------------ the scan
    def pick_files(self):
        exts = " ".join("*" + e for e in sorted(A.SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(self, "Scan files", "", f"Documents and pictures ({exts})")
        if paths:
            if not getattr(self, "tool", False) and self.host.ws is not None:     # 3.78.0: the bridge to the Effort Library
                from . import acrbridge as AB
                AB.add_first(self, paths)
            self.scan(paths)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Scan a folder")
        if folder:
            self.scan(self.folder_files(folder), folder)

    def customer_paths(self):
        """2.86.0: the newest version of every customer document in the Library that is on this PC."""
        if self.host.ws is None or getattr(self, "tool", False):
            return []
        import docversions as DV
        lib = DV.Library(self.host.ws.p("documents")).load()
        out = []
        for d in lib.docs:
            v = lib.latest(d)
            p = lib.path_of(v) if v else ""
            if p and os.path.isfile(p) and os.path.splitext(p)[1].lower() in A.SUPPORTED_EXTS:
                out.append(p)
        return out

    def scan_customer(self):
        paths = self.customer_paths()
        if not paths:
            self.host.status("No customer documents on this PC yet: add them in Documents.")
            return None
        diag.activity("customer_terms_scan", files=len(paths))
        return self.scan(paths)

    @staticmethod
    def folder_files(folder):
        return [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs
                if not f.startswith("~$") and os.path.splitext(f)[1].lower() in A.SUPPORTED_EXTS]

    def scan_again(self):
        s = self.session
        last = (s.last_scan or {}) if s else {}
        folder = last.get("folder")
        paths = self.folder_files(folder) if folder and os.path.isdir(folder) else [p for p in last.get("paths", []) if os.path.isfile(p)]
        if not paths:
            self.host.status("The files from the last scan are no longer there.")
            return None
        return self.scan(paths, folder)

    def scan(self, paths, folder=None):
        if self.session is None or self.worker is not None or not paths:
            return None
        diag.activity("qt_scan_started", files=len(paths))
        self.worker = ScanWorker(self.session, list(paths), folder)
        self.worker.progress.connect(self.on_progress)
        self.scan_prog = SP.Progress(); self.on_progress("")
        self.scanbar.show(); self.scan_tick.start()
        self.worker.finished_ok.connect(self.scan_done)
        self.worker.failed.connect(self.scan_failed)
        for b in (self.b_files, self.b_folder, self.b_lib, self.b_again, self.b_paste, self.b_cust):
            b.setEnabled(False)
        self.b_cancel.show()
        if getattr(self, "head_w", None) is not None:                 # 3.93.0: Cancel is in the tabs' row
            self.head_w.show(); self.empty.hide()
        self.worker.start()
        return self.worker

    def on_progress(self, msg):
        """3.71.0: each line the scan sends moves the bar."""
        if self.scan_prog is None:
            return
        self.scan_prog.update(msg)
        self.scan_where.setText(self.scan_prog.where())
        self.scan_pct.setValue(self.scan_prog.percent())
        self.tick_scan()

    def tick_scan(self):
        if self.scan_prog is not None and not A.CANCEL.is_set():
            self.scan_left.setText(f"{self.scan_prog.percent()}% done. {SP.left_words(self.scan_prog.left())}")

    def cancel(self):
        A.CANCEL.set()
        self.progress.setText("Stopping after the current page...")
        self.scan_left.setText("Stopping after the current page")

    def _end(self):
        if self.worker is not None:
            self.worker.wait(2000)
        self.worker = PR.let_go(self.worker)
        self.scan_tick.stop(); self.scanbar.hide(); self.scan_prog = None
        for b in (self.b_files, self.b_folder, self.b_lib, self.b_paste, self.b_cust):
            b.setEnabled(True)
        self.b_cancel.hide()

    def scan_done(self, rec):
        self._end()
        self.progress.setText("")
        self.fill_types()
        self.fill()
        from . import acrlayout as AL
        AL.note_scan(self)                                               # 3.92.0: the effort's timeline
        n = self.session.counts()
        msg = f"Scan done: {n['active']} terms, {n['choice']} need a choice, {n['candidate']} new candidates"
        if rec:
            msg += f". Acronym list: {rec['found']} found again, {rec['new']} new, {rec['gone']} no longer found"
        self.host.toast(msg)
        return rec

    def scan_failed(self, why):
        self._end()
        self.progress.setText("")
        self.host.status("Scan stopped." if why == "cancelled" else f"The scan failed ({why}). Details are in the logs (no file names or content).")
        self.fill()

    # ------------------------------------------------------------ export
    def export(self, path=None):
        s = self.session
        if s is None:
            return None
        terms = list(self.terms)
        terms = [t for t in terms if not s.results[t].get("known")]
        if not terms:
            self.host.status("No rows are showing. Change the filters, then export.")
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export the acronym report", self.host.out_path("acronym_report"),
                                                  "CSV report (*.csv)")
            if not path:
                return None
        try:
            n = A.write_acronym_report(path, terms, s.results, s.known_cell)
        except PermissionError:
            self.host.status("That file is open in Excel. Close it, then export again.")
            return None
        diag.activity("qt_acronym_report", n=n)
        self.host.toast(f"{n} rows exported")
        return path


# ---------------------------------------------------------------- the customer's acronym lists (2.67.0)
def _client_lists(self, add_paths=None, paste=None, remove=None, run=True):
    """The customer's acronym lists for this effort. add_paths, paste (name, text), remove (index) act at once (tests)."""
    import datetime as DT
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QInputDialog, QListWidget
    s = self.session
    if s is None:
        return None
    lists = list(s.client_lists)

    def stamp():
        return DT.datetime.now().strftime("%Y-%m-%d %H:%M")

    def save(note):
        s.set_client_lists(lists)
        s.ws.set("client_lists", lists)
        diag.activity("client_lists_changed", n=len(lists))
        self.host.toast(note + (". Scan again to apply them." if s.results else ""))

    def add_files(paths):
        got = []
        for p in paths:
            try:
                rows = A.parse_client_list(p)
            except Exception:
                A.log_error("Client list could not be read", ext=os.path.splitext(p)[1].lower())
                rows = []
            if rows:
                lists.append({"name": os.path.basename(p), "rows": [list(r) for r in rows], "added": stamp()})
                got.append(f"{os.path.basename(p)} ({len(rows)})")
        if got:
            save("Added: " + ", ".join(got))
        else:
            self.host.status("No acronym and definition pairs were found. Lists work best as two columns: acronym, definition.")
        return got

    def add_text(name, text):
        rows = A.parse_client_text(text)
        if rows:
            lists.append({"name": name or f"Pasted list {stamp()}", "rows": rows, "added": stamp()})
            save(f"Added: {lists[-1]['name']} ({len(rows)})")
        return rows
    if add_paths is not None:
        return add_files(add_paths)
    if paste is not None:
        return add_text(*paste)
    if remove is not None:
        gone = lists.pop(remove)
        save(f"Removed {gone['name']}")
        return gone
    dlg = QDialog(self); dlg.setWindowTitle("Customer acronym lists"); dlg.setMinimumSize(680, 460)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Acronym lists from the customer (an RFP's acronym list, for example). Their terms are found in your documents "
                        "even when the database does not hold them, and the customer's definition comes first. Kept with this effort.", "muted"))
    lw = QListWidget(); v.addWidget(lw, 1)

    def fill():
        lw.clear()
        for x in lists:
            lw.addItem(f"{x['name']}   ({len(x['rows'])} acronyms, added {x.get('added', '')})")
    fill()
    row = QHBoxLayout()

    def do_add():
        exts = " ".join("*" + e for e in sorted(A.CLIENT_IMAGE_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(dlg, "Add customer acronym list(s)", "",
                                                f"Acronym lists (*.csv *.tsv *.txt *.xlsx *.docx *.pdf);;Pictures of a list ({exts})")
        if paths:
            add_files(paths); fill()

    def do_paste():
        text, ok = QInputDialog.getMultiLineText(dlg, "Paste or type the customer's terms",
                                                 "One per line: ACR - definition, ACR: definition, or rows copied from Excel or Word:")
        if ok and text.strip():
            add_text("", text); fill()

    def do_view():
        i = lw.currentRow()
        if i >= 0:
            QInputDialog.getMultiLineText(dlg, lists[i]["name"], "Terms:", "\n".join(f"{t}\t{d}" for t, d in lists[i]["rows"]))

    def do_remove():
        i = lw.currentRow()
        if i >= 0:
            gone = lists.pop(i); save(f"Removed {gone['name']}"); fill()
    for text, kind, fn in (("Add list...", "primary", do_add), ("Paste or type...", None, do_paste), ("View terms", None, do_view),
                           ("Remove", "danger", do_remove)):
        row.addWidget(D.button(text, kind, fn))
    row.addStretch(1)
    v.addLayout(row)
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    if run:
        dlg.exec()
    return dlg


AcronymPage.client_lists = _client_lists
