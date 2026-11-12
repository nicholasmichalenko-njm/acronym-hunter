"""Sort > Structure (3.65.0): the topics beside the response outline. Map a topic to a section, make subsections from
topics (an RFI or sources sought: the response from the topics), place each topic's kept requirements in its section,
rate our fit per topic, and see what the structure still misses. topics.py holds the rules."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)
import diag
import topics as TP
from . import design as D


class StructureView(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page, self.host = page, page.host
        self.rows = []
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        v.addWidget(D.label("Each topic fills a section of the response. Section L still sets an RFP's volumes and top "
                            "sections; topics fill what sits under them. For an RFI or sources sought, make the response "
                            "from the topics.", "muted"))
        self.gaps = D.label("", None); v.addWidget(self.gaps)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Topic", "Fills", "Requirements", "Kept", "In a section", "Our fit"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.table, 1)
        r1 = QHBoxLayout(); r1.setSpacing(D.SPACE["s"]); v.addLayout(r1)
        r1.addWidget(D.label("Section", None, wrap=False))
        self.section = QComboBox(); r1.addWidget(self.section, 2)
        r1.addWidget(D.button("Map to it", None, lambda: self.map_selected(self.section.currentData()),
                              "The selected topics fill this section (a topic can fill more than one)"))
        r1.addWidget(D.button("Make subsections under it", None, lambda: self.make_subsections(self.section.currentData()),
                              "A section named for each selected topic, under the section or volume chosen; subtopics under them"))
        r2 = QHBoxLayout(); r2.setSpacing(D.SPACE["s"]); v.addLayout(r2)
        r2.addWidget(D.button("Place their requirements", "primary", lambda: self.place(),
                              "Each kept requirement with no section goes to its home topic's first section"))
        r2.addWidget(D.button("Make the response from the topics", "ghost", lambda: self.response_from_topics(),
                              "For an RFI or sources sought: a Response volume with a section per topic"))
        r2.addStretch(1)
        r2.addWidget(D.label("Our fit", None, wrap=False))
        self.fit = QComboBox(); self.fit.addItems(["(not rated)", "Strong", "Partial", "Gap"]); r2.addWidget(self.fit)
        r2.addWidget(D.button("Rate the selected", "ghost", lambda: self.rate(self.fit.currentText())))

    def rec(self):
        return self.page.rec()

    def labels(self):
        R = self.host.review
        return list(R.labels()) if R is not None else []

    def refresh(self):
        r, M = self.rec(), self.page.M
        if r is None:
            return
        items = M.items if M is not None else []
        labs = self.labels()
        self.rows = TP.structure_rows(r, items, labs)
        self.table.setRowCount(len(self.rows))
        for i, x in enumerate(self.rows):
            vals = [("    " if x["parent"] else "") + x["name"], ", ".join(x["sections"]) or "no section yet", x["home"], x["kept"],
                    x["placed"], x["fit"] or "not rated"]
            for j, val in enumerate(vals):
                c = QTableWidgetItem(str(val))
                if j == 1 and not x["sections"] and x["home"]:
                    c.setForeground(D.color("warn"))
                if j == 5 and x["fit"]:
                    c.setForeground(D.color({"Strong": "ok", "Partial": "warn", "Gap": "crit"}[x["fit"]]))
                self.table.setItem(i, j, c)
        cur = self.section.currentData()
        self.section.clear()
        try:
            import outline_ops as O
            vols = set(O.volume_heads(M)) if M is not None else set()
        except Exception:  # noqa: BLE001
            diag.swallowed(); vols = set()
        for lab in labs:
            self.section.addItem(("" if lab in vols else "    ") + lab, lab)
        self.section.setCurrentIndex(max(0, self.section.findData(cur)))
        g = TP.gaps(r, items, labs)
        bits = []
        if g["no_section"]:
            bits.append(f"{len(g['no_section'])} topic(s) with requirements and no section")
        if g["unplaced"]:
            bits.append(f"{g['unplaced']} kept requirement(s) with a topic and no section")
        self.gaps.setText(("Still to do: " + "; ".join(bits) + ".") if bits else
                          ("Every topic with requirements fills a section, and every kept requirement with a topic is placed."
                           if self.rows else "No topics yet: name them on Sort."))
        self.gaps_now = g

    def selected_ids(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.rows[i]["id"] for i in rows if 0 <= i < len(self.rows)]

    def _done(self, msg=""):
        self.page._after(msg)

    def map_selected(self, label, ids=None):
        ids = ids or self.selected_ids()
        r = self.rec()
        if not ids or not label:
            self.host.status("Select topics and a section first.")
            return 0
        for tid in ids:
            TP.map_section(r, tid, label)
        diag.activity("topics_mapped", n=len(ids))
        self._done(f"{len(ids)} topic(s) fill {label}.")
        return len(ids)

    def make_subsections(self, parent, ids=None):
        R = self.host.review
        ids = ids or self.selected_ids()
        if R is None or not ids:
            self.host.status("Select topics first (and read the requirements into Shred).")
            return {}
        R.snap("sections from topics")
        made = TP.make_subsections(self.rec(), R.M, ids, parent or "")
        self.host.changed()
        diag.activity("sort_subsections", n=len(made))
        self._done(f"{len(made)} section(s) made from topics" + (f" under {parent}." if parent else "."))
        return made

    def response_from_topics(self, title="Response"):
        """An RFI or sources sought: a Response volume, a section per topic, subtopics under them."""
        import outline_ops as O
        R = self.host.review
        r = self.rec()
        if R is None or r is None:
            self.host.status("Read the notice into Shred first.")
            return {}
        ids = [t["id"] for t in TP.roots(r) if not t.get("sections")]
        if not ids:
            self.host.status("Every topic already fills a section.")
            return {}
        R.snap("the response from the topics")
        vol = O.add_volume(R.M, title)
        made = TP.make_subsections(r, R.M, ids, vol)
        self.host.changed()
        diag.activity("sort_response_from_topics", n=len(made))
        self._done(f"{vol}: {len(made)} section(s), one per topic.")
        return {"volume": vol, "made": made}

    def place(self):
        R = self.host.review
        r = self.rec()
        if R is None or r is None:
            return 0
        todo = TP.to_place(r, R.M.items)
        labs = set(self.labels())
        n = 0
        with R.group():
            for sec, its in todo.items():
                if sec in labs:
                    n += R.req(its, sec) or 0
        self.host.changed()
        diag.activity("sort_placed", n=n)
        self._done(f"{n} requirement(s) placed in their topics' sections.")
        return n

    def rate(self, fit, ids=None):
        ids = ids or self.selected_ids()
        fit = "" if fit.startswith("(") else fit
        r = self.rec()
        for tid in ids:
            TP.set_fit(r, tid, fit)
        self._done()
        return len(ids)
