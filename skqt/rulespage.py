"""The Rules page (3.38.0, Production > Rules): every rule in one list, in two families.

Our documents: the production rules (rulebook.py), each one plain sentence with how it is kept (checked by the app,
checked with Word, or a checklist for people), whether it is on for every effort, and a link to where its values live
(never a second copy). The team adds its own rules (kept by people). An effort departs from a rule only on Effort
Formatting; this page says how many this effort departs from.

Reading the customer's documents: the rules Review's Suggest follows (suggestrules.py), the built-in reading rules in
words, and the phrase rules the team or this effort made, which can be added and removed here. Rules only, no AI."""
import html, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import rulebook as RB
import suggestrules as SR
from . import design as D

READING = ("Who acts: a piece where the Offeror or the Contractor acts can be a requirement; one where the Government "
           "acts is support.",
           "The verb: shall, must and will are Mandatory; should is Desired; may is Optional (no suggestion).",
           "Evaluation wording (will be evaluated, rated, assessed) points to Section M.",
           "The RFP section a piece is in (Section L, M or C numbering, or its title) gives its designation.",
           "No suggestion when the rules are not sure: no clear actor, an Optional verb, a plain statement. You decide.")


def _where_text(where):
    page, sec = where
    if not page:
        return ""
    if page == "prodstd":
        try:
            import skqt.prodstdpage as PS
            return "Production Standards > " + dict(PS.SECTIONS).get(sec, "")
        except Exception:  # noqa: BLE001
            return "Production Standards"
    if page in ("formatstd", "layoutstd") and sec:                # 3.69.0: the library and its category
        import libcats as LC
        lib = "formatting" if page == "formatstd" else "layout"
        sub = {"styles": "Allowed styles", "roles": "Allowed styles (the styles the rules read)"}.get(sec) or LC.category_title(lib, sec)
        return f"{RB.WHERE_NAME.get(page, page)} > {sub}"
    return RB.WHERE_NAME.get(page, page)


class RulesPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self._loading = False
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(D.SPACE["m"])
        top = D.Card("Rules", "Every rule the app follows and checks, in one list. A rule's values live where they always "
                     "have (Production Standards, Effort Formatting, the Acros & Abs List); each rule links there.")
        self.summary = QLabel(""); self.summary.setTextFormat(Qt.RichText); self.summary.setWordWrap(True); top.add(self.summary)
        sw = QHBoxLayout(); sw.setSpacing(D.SPACE["s"])
        sw.addWidget(D.label("Show", "label", wrap=False))
        self.b_ours = QPushButton("Our documents"); self.b_theirs = QPushButton("Reading the customer's documents")
        self.b_recipes = QPushButton("Field recipes")                               # 3.66.0: the team's field codes
        self.b_checks = QPushButton("Fix a Copy's checks")                         # 3.69.0: from Production Standards
        for i, b in enumerate((self.b_ours, self.b_theirs, self.b_recipes, self.b_checks)):
            b.setCheckable(True); b.setAutoExclusive(True); b.clicked.connect(lambda _c=False, k=i: self.show_family(k))
            sw.addWidget(b)
        sw.addStretch(1)
        top.body.addLayout(sw)
        outer.addWidget(top)
        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_ours())
        self.stack.addWidget(self._build_theirs())
        from .recipesview import RecipesView
        self.recipes = RecipesView(host); self.stack.addWidget(self.recipes)
        self.checks = None                                                          # built when first shown
        self.checks_box = QWidget(); QVBoxLayout(self.checks_box).setContentsMargins(0, 0, 0, 0); self.stack.addWidget(self.checks_box)
        self.b_ours.setChecked(True)

    # ------------------------------------------------------------ our documents
    def _build_ours(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        c = D.Card("Rules for our documents", "Audit, Fix a Copy and Make templates follow and check these. Untick a rule to "
                   "turn it off for every effort; an effort departs from one on Effort Formatting.")
        self.t = QTableWidget(0, 5)
        self.t.setHorizontalHeaderLabels(["Rule", "The rule", "Kept by", "On for every effort", "Its values"])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setWordWrap(True)
        h = self.t.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents); h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in (2, 3, 4):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.t.setMinimumHeight(360)
        c.add(self.t)
        add = QHBoxLayout(); add.setSpacing(D.SPACE["s"])
        self.new_text = QLineEdit(); self.new_text.setPlaceholderText("Add a rule of your own, in one sentence (a checklist item for people)")
        self.new_group = QComboBox()
        for g in RB.GROUPS:
            self.new_group.addItem(g, g)
        self.new_group.setCurrentIndex(self.new_group.findData("Approach"))
        add.addWidget(self.new_text, 1); add.addWidget(self.new_group)
        add.addWidget(D.button("Add the rule", None, lambda: self.add_own()))
        self.b_remove = D.button("Remove the selected rule", "ghost", lambda: self.remove_own(),
                                 "Your own rules only; the built-in rules can be turned off but not removed")
        add.addWidget(self.b_remove)
        c.body.addLayout(add)
        v.addWidget(c)
        return w

    def fill_ours(self):
        rs = RB.rules(self.host.config_dir)
        mine = set(RB.effort_off(self.host.ws))
        self._loading = True
        self.t.setRowCount(0)
        last = None
        for r in rs:
            if r["group"] != last:
                last = r["group"]
                i = self.t.rowCount(); self.t.insertRow(i)
                g = QTableWidgetItem(last); f = g.font(); f.setBold(True); g.setFont(f); g.setFlags(Qt.ItemIsEnabled)
                self.t.setItem(i, 0, g); self.t.setSpan(i, 0, 1, 5)
            i = self.t.rowCount(); self.t.insertRow(i)
            lab = QTableWidgetItem(r["label"]); lab.setData(Qt.UserRole, r["id"])
            self.t.setItem(i, 0, lab)
            txt = r["text"] + ("  (this effort departs from it)" if r["id"] in mine else "") + ("  (your own)" if r["own"] else "")
            it = QTableWidgetItem(txt); it.setToolTip(r["text"])
            self.t.setItem(i, 1, it)
            self.t.setItem(i, 2, QTableWidgetItem(RB.KEPT_NAME[r["kept"]]))
            cb = QCheckBox(); cb.setChecked(r["on"]); cb.setToolTip("Off: no effort follows or checks it")
            cb.toggled.connect(lambda on, rid=r["id"]: self.set_on(rid, on))
            box = QWidget(); bl = QHBoxLayout(box); bl.setContentsMargins(8, 0, 0, 0); bl.addWidget(cb); bl.addStretch(1)
            self.t.setCellWidget(i, 3, box)
            if r["where"][0]:
                b = D.button("Change it: " + _where_text(r["where"]), "ghost", lambda _c=False, wh=r["where"]: self.open_where(wh))
                self.t.setCellWidget(i, 4, b)
            else:
                self.t.setItem(i, 4, QTableWidgetItem(""))
        self.t.resizeRowsToContents()
        self._loading = False

    def set_on(self, rid, on):
        if self._loading:
            return
        RB.set_on(self.host.config_dir, rid, on)
        if on:
            diag.activity("rule_turned_on")
        else:
            diag.activity("rule_turned_off")
        self.fill_summary()

    def add_own(self):
        rid = RB.add(self.host.config_dir, self.new_text.text(), group=self.new_group.currentData() or "Approach")
        if rid is None:
            self.host.status("Type the rule in one sentence first.")
            return None
        self.new_text.clear()
        diag.activity("rule_added")
        self.refresh()
        self.host.status(f"Rule {rid} added: a checklist item for people.")
        return rid

    def selected_rule(self):
        row = self.t.currentRow()
        it = self.t.item(row, 0) if row >= 0 else None
        return it.data(Qt.UserRole) if it is not None else None

    def remove_own(self):
        rid = self.selected_rule()
        r = RB.get(self.host.config_dir, rid) if rid else None
        if r is None or not r["own"]:
            self.host.status("Select one of your own rules to remove it. The built-in rules can be turned off.")
            return False
        RB.remove(self.host.config_dir, rid)
        diag.activity("rule_removed")
        self.refresh()
        return True

    def open_where(self, where):
        page, sec = where
        if page == "rules" and sec == "checks":                    # 3.69.0: the values now live here
            self.show_family(3)
            return True
        ok = self.host.go(page)
        if ok is not False and page == "formatstd" and sec in ("styles", "roles"):
            self.host.formatstd_page.style_rules(modal=not os.environ.get("AH_TEST"))
            return ok
        if ok is not False and page == "prodstd" and sec:
            try:
                import skqt.prodstdpage as PS
                self.host.prodstd_page.show_section([k for k, _t in PS.SECTIONS].index(sec))
            except Exception:  # noqa: BLE001
                diag.swallowed()
        return ok

    # ------------------------------------------------------------ reading the customer's documents
    def _build_theirs(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        c = D.Card("How Shred's Suggest reads a piece", "Built in, in this order after your phrase rules below. "
                   "Nothing is learned without you: a phrase rule is made when you add it here or correct a suggestion.")
        self.reading = QLabel("".join(f"<div style='margin:3px 0'>{i}. {html.escape(x)}</div>" for i, x in enumerate(READING, 1)))
        self.reading.setTextFormat(Qt.RichText); self.reading.setWordWrap(True); c.add(self.reading)
        v.addWidget(c)
        c2 = D.Card("Phrase rules", "A piece holding the phrase gets this suggestion (case and spacing ignored; the longest "
                    "phrase wins). This effort's rules win over the team's.")
        self.pt = QTableWidget(0, 4); self.pt.setHorizontalHeaderLabels(["Phrase", "Suggests", "For", "Why"])
        self.pt.verticalHeader().setVisible(False); self.pt.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pt.setSelectionBehavior(QAbstractItemView.SelectRows)
        ph = self.pt.horizontalHeader(); ph.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in (1, 2):
            ph.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        ph.setSectionResizeMode(3, QHeaderView.Stretch)
        self.pt.setMinimumHeight(260)
        c2.add(self.pt)
        add = QHBoxLayout(); add.setSpacing(D.SPACE["s"])
        self.p_text = QLineEdit(); self.p_text.setPlaceholderText("A phrase, for example: proposals are limited to")
        self.p_cat = QComboBox()
        for k, t in SR.CATS:
            self.p_cat.addItem(t, k)
        self.p_scope = QComboBox(); self.p_scope.addItem("Every effort", "team"); self.p_scope.addItem("This effort", "effort")
        add.addWidget(self.p_text, 1); add.addWidget(self.p_cat); add.addWidget(self.p_scope)
        add.addWidget(D.button("Add the phrase rule", None, lambda: self.add_phrase()))
        add.addWidget(D.button("Remove the selected", "ghost", lambda: self.remove_phrase()))
        c2.body.addLayout(add)
        v.addWidget(c2)
        v.addStretch(1)
        return w

    def fill_theirs(self):
        rows = SR.all_rules(self.host.config_dir, self.host.ws)
        self.pt.setRowCount(len(rows))
        for i, r in enumerate(rows):
            a = QTableWidgetItem(r["phrase"]); a.setData(Qt.UserRole, (r["phrase"], r["scope"]))
            self.pt.setItem(i, 0, a)
            self.pt.setItem(i, 1, QTableWidgetItem(SR.CAT_NAME.get(r.get("cat"), r.get("cat", ""))))
            self.pt.setItem(i, 2, QTableWidgetItem("This effort" if r["scope"] == "effort" else "Every effort"))
            self.pt.setItem(i, 3, QTableWidgetItem(r.get("why") or ""))
        self.p_scope.setEnabled(self.host.ws is not None)
        if self.host.ws is None:
            self.p_scope.setCurrentIndex(0)

    def add_phrase(self):
        scope = self.p_scope.currentData() if self.host.ws is not None else "team"
        r = SR.add_rule(self.host.config_dir, self.host.ws, self.p_text.text(), self.p_cat.currentData(), scope=scope)
        if r is None:
            self.host.status("Type a phrase of at least three letters.")
            return None
        self.p_text.clear()
        diag.activity("phrase_rule_added")
        self.refresh()
        return r

    def remove_phrase(self):
        row = self.pt.currentRow()
        it = self.pt.item(row, 0) if row >= 0 else None
        if it is None:
            self.host.status("Select a phrase rule to remove it.")
            return 0
        phrase, scope = it.data(Qt.UserRole)
        n = SR.remove_rule(self.host.config_dir, self.host.ws, phrase, scope=scope)
        self.refresh()
        return n

    # ------------------------------------------------------------ both
    def show_family(self, k):
        self.stack.setCurrentIndex(k)
        (self.b_ours, self.b_theirs, self.b_recipes, self.b_checks)[k].setChecked(True)
        if k == 2:
            self.recipes.refresh()
        if k == 3:
            self.show_checks()

    def show_checks(self):
        """3.69.0: graphics, Excel and PowerPoint, and the words Fix a Copy reports and fixes, in the Company Standards (Default)."""
        from .stdeditor import GlobalStore, LayerEditor
        if self.checks is None:
            self.checks = LayerEditor(self.host, GlobalStore(self.host.config_dir), ["graphics", "office", "terms"])
            self.checks_box.layout().addWidget(self.checks)
        elif not self.checks.dirty:
            self.checks.reload()
        return self.checks

    def fill_summary(self):
        sm = RB.summary(self.host.config_dir, self.host.ws)
        rs = RB.rules(self.host.config_dir)
        every = sum(1 for r in rs if not r["on"])
        mine = len(RB.effort_off(self.host.ws))
        parts = [f"<b>{sm['n']} rules</b> for our documents: {sm['app']} checked by the app, {sm['word']} checked with Word, "
                 f"{sm['people']} on the checklist for people."]
        if every:
            parts.append(f"{every} off for every effort.")
        if self.host.ws is not None:
            parts.append(f"{self.host.effort_name} departs from {mine} (Effort Formatting)." if mine else
                         f"{self.host.effort_name} follows every rule that is on.")
        n = len(SR.all_rules(self.host.config_dir, self.host.ws))
        parts.append(f"{n} phrase rule{'' if n == 1 else 's'} for reading the customer's documents.")
        self.summary.setText(" ".join(parts))

    def refresh(self):
        self.fill_summary()
        self.fill_ours()
        self.fill_theirs()
        if self.stack.currentIndex() == 2:
            self.recipes.refresh()
