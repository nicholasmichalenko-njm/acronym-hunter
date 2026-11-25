"""Matrix & Outline > Outline (4.3.0; claude/stationkeeper-matrix-outline-plan-4.3.md, step 2). The response structure's
home: the volumes and sections, built in the Structure Builder (skqt/builder.py), which moves here from Setup. Setup
still shows the same sections for who writes what, when and how long (the builder widget sits on whichever of the two
is open).

An effort with no outline asks once whether the solicitation prescribes it (claude/stationkeeper-releases-4.3-to-4.5-
decisions-2026-11-10.md, decision 4):
- Prescribed: the sections the RFP names, in its order (structstart.prescribed), then Apply; marked as the customer's.
- Ours: start from Section M's evaluation factors, the customer's headings, a Word outline, or blank.
Either way our own subsections go under the customer's. The answer is kept with the matrix (setup "outline_from").
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

import diag
from . import design as D

FROM = {"prescribed": "The customer tells us", "ours": "We build it"}
QUESTION = "Does the customer tell us how to structure our response?"          # 4.73.0 (his direction, 2026-11-24)
REASONS = ("No structure given", "A content list only", "A page limit only", "Other")


class OutlinePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = self.v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["s"])
        from .commandbar import CommandBar
        bar = self.bar = CommandBar()
        self.b_volume = bar.add("+ Volume", lambda: self.builder().add_volume(), "A new volume at the end, numbered the volumes' way")
        self.b_elements = bar.add("Add elements...", lambda: self.builder().add_elements(),
                                  "Table of Contents, the lists, Acronyms and Abbreviations, the Appendices section and the rest")
        self.b_place = bar.primary("Place requirements", lambda: self.host.go("place"),
                                   "The customer's page beside this outline: put each requirement in its section")
        bar.more("Edit as text / Start from", lambda: self.builder().show_text(not self.builder().text_panel.isVisible()),
                 "The sections as text, one per line, and Start from the RFP or a Word outline")
        bar.more("Sort in document order", lambda: self.builder().sort_order(),
                 "The items in every section in the order they appear in the customer documents")
        bar.more("Change how the outline starts...", lambda: self.ask(force=True), "The customer tells us, or we build it: ask again. Nothing is deleted")
        v.addWidget(bar)
        # the start question: once per effort. 4.73.0: his three answers; the marking is the page's second tab
        self.start = D.Card(QUESTION, "If Section L (or its like) says how the response is organized, mark it from the "
                            "customer's document and the outline fills. If not, the structure is ours to build. "
                            "You can change the answer later; changing it deletes nothing.", key=True)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); self.start.body.addLayout(row)
        self.b_pres = D.button(FROM["prescribed"], "primary", lambda: self.prescribed(),
                               "The customer's document opens beside the outline: mark its volumes and headings (1 to 4)")
        row.addWidget(self.b_pres)
        self.b_ours = D.button(FROM["ours"], None, lambda: self.we_build(), "White papers, RFIs and many others give no structure: it is ours")
        row.addWidget(self.b_ours)
        self.b_file = D.button("Start from a saved outline...", None, lambda: self.from_file(),
                               "An outline workbook, a Word outline or a PDF: brought in, then adjusted")
        row.addWidget(self.b_file); row.addStretch(1)
        v.addWidget(self.start)
        # 4.73.0: We build it: why, and where to start from
        from PySide6.QtWidgets import QComboBox
        self.build = D.Card("We build it", "Pick a start, or type the sections. Authors see in the setup that the structure is ours.", key=True)
        why = QHBoxLayout(); why.setSpacing(D.SPACE["s"]); self.build.body.addLayout(why)
        why.addWidget(D.label("Why:", "label", wrap=False))
        self.reason = QComboBox(); self.reason.addItems(list(REASONS))
        self.reason.setToolTip("Why the structure is ours: kept with the outline, with the date")
        self.reason.activated.connect(lambda _i: (self.set_reason(self.reason.currentText()), self.refresh()))
        why.addWidget(self.reason); why.addStretch(1)
        row3 = QHBoxLayout(); row3.setSpacing(D.SPACE["s"]); self.build.body.addLayout(row3)
        self.b_factors = D.button("Mirror the evaluation factors", "primary", lambda: self.ours("factors"), "A section for each factor and subfactor")
        self.b_heads = D.button("Mirror the customer's headings", None, lambda: self.ours("headings"), "The SOW, PWS or other headings as a start")
        self.b_blank = D.button("Type it", None, lambda: self.ours("blank"), "A blank outline: one section per line")
        for x in (self.b_factors, self.b_heads, self.b_blank):
            row3.addWidget(x)
        row3.addStretch(1)
        v.addWidget(self.build)
        # 4.6.0: an outline the effort type started by itself (from Section L's headings) still asks, once
        self.started = D.Card(QUESTION, "This outline started from the customer's headings. If the customer tells us the "
                              "structure, its sections are marked as the customer's, with their page limits. If not, the "
                              "headings stay as a start for ours.", key=True)
        row2 = QHBoxLayout(); row2.setSpacing(D.SPACE["s"]); self.started.body.addLayout(row2)
        self.b_yes = D.button("Yes, the customer tells us", "primary", lambda: self.answer("prescribed"),
                              "The sections are marked as the customer's, with the solicitation's page limits")
        self.b_no = D.button("No, we build it", None, lambda: self.answer("ours"), "The headings stay as a start; change them freely")
        row2.addWidget(self.b_yes); row2.addWidget(self.b_no); row2.addStretch(1)
        v.addWidget(self.started)
        self.slot = QVBoxLayout(); v.addLayout(self.slot, 1)
        from PySide6.QtWidgets import QSizePolicy                  # 4.73.0: a question is as tall as its words, at the top
        for c in (self.start, self.build, self.started):
            c.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.rest = QWidget(); v.addWidget(self.rest, 1)
        self.wait = D.EmptyState("Nothing marked yet", "Mark the volumes and headings in the customer's document, and they appear here.",
                                 "Open the customer's document", lambda: self.host.go("structpass"))
        v.addWidget(self.wait, 1); self.wait.setVisible(False)
        self.back = D.button("Change the answer", "ghost", lambda: self.ask(force=True), "Ask the question again. Nothing is deleted")
        back_row = QHBoxLayout(); back_row.addWidget(self.back); back_row.addStretch(1); v.addLayout(back_row)
        self.said = D.label("", "muted"); v.addWidget(self.said)
        # 4.62.0: nothing shredded yet: one sentence and one way in, in one place (no bar of buttons that cannot be used)
        self.none = D.EmptyState("No outline yet", "The outline starts from the customer's documents. Shred one first.",
                                 "Open Shred", lambda: self.host.go("assign"))
        v.insertWidget(1, self.none, 1); self.none.setVisible(False)

    # ------------------------------------------------------------------ the builder, borrowed from Setup
    def builder(self):
        return self.host.setups_page.builder

    def showEvent(self, e):
        b = self.builder()
        if b.parent() is not self:
            self.slot.addWidget(b, 1)
            b.show()
        self.refresh()
        super().showEvent(e)

    def M(self):
        R = self.host.review
        return R.M if R is not None else None

    def _setup(self):
        import setupdoc as SD
        M = self.M()
        return SD.setup_of(M) if M is not None else {}

    def refresh(self):
        M = self.M()
        has = M is not None and bool(M.outline)
        b = self.builder()
        texting = not b.text_panel.isHidden()
        asked = bool(self._setup().get("outline_from")) if M is not None else False
        self.start.setVisible(M is not None and not has and not texting and not asked)
        ours = asked and self._setup().get("outline_from") == "ours"
        self.build.setVisible(M is not None and not has and not texting and ours)          # 4.73.0
        if ours:
            self.reason.setCurrentIndex(max(0, self.reason.findText(self._setup().get("outline_reason", REASONS[0]))))
        self.started.setVisible(M is not None and has and not asked)          # 4.6.0
        wait = asked and not ours and not has and not texting          # the customer tells us; nothing marked yet
        self.wait.setVisible(M is not None and wait)
        b.setVisible(has or texting)
        self.rest.setVisible(not (has or texting) and M is not None and not wait)
        self.back.setVisible(M is not None and not has and not texting and asked)
        self.said.setVisible(has)
        for x in (self.b_volume, self.b_elements, self.b_place):
            x.setEnabled(has)
        self.none.setVisible(M is None); self.bar.setVisible(M is not None and (has or texting))   # 4.62.0
        src = self._setup().get("outline_from", "") if M is not None else ""
        extra = ""
        if src == "prescribed" and has:                  # 4.5.0: the customer's sections and the volumes' page limits
            St = self._setup()
            if not St.get("prescribed_marked"):
                import outlinemarks as OM
                got = OM.mark(M)
                St["prescribed_marked"] = True
                St["prescribed_pages"] = got["pages"]
                M.pending = True
                self.host.changed()
            pg = St.get("prescribed_pages") or {}
            extra = (" Its sections are marked as the customer's" + (": page limits from the solicitation, "
                     + ", ".join(f"{k} {v:g}" for k, v in pg.items()) if pg else "") + ".")
        why = self._setup().get("outline_reason", "") if src == "ours" else ""
        self.said.setText((f"{FROM.get(src, '')}" + (f" ({why.lower()}, {self._setup().get('outline_reason_on', '')})" if why else "") + "." + extra) if src else "")
        try:
            b.refresh()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return has

    # ------------------------------------------------------------------ the start question
    def _keep(self, how):
        St = self._setup()
        St["outline_from"] = how
        M = self.M()
        M.pending = True
        self.host.changed()

    def ask(self, force=False):
        St = self._setup()
        if force:
            St.pop("outline_from", None)
        self.builder().show_text(False)
        return self.refresh()

    def prescribed(self):
        """The customer tells us (4.73.0): the customer's document opens beside the outline, to mark its volumes and
        headings. The marks carry Required by, so nothing is marked the customer's wholesale."""
        if self.M() is None:
            return False
        self._keep("prescribed")
        self._setup()["prescribed_marked"] = True
        diag.activity("outline_start_prescribed")
        self.host.go("structpass")
        self.host.status("Select a piece that names a volume or a section and press 1 to 4. Also add sections for any evaluation factor the instructions do not cover.")
        return True

    def we_build(self):
        """We build it (4.73.0): the answer, a reason and the date; then where to start from."""
        if self.M() is None:
            return False
        self._keep("ours")
        self.set_reason(self._setup().get("outline_reason") or REASONS[0])
        self.refresh()
        diag.activity("outline_start_ours")
        return True

    def set_reason(self, reason):
        import datetime
        St = self._setup()
        St["outline_reason"] = reason if reason in REASONS else REASONS[0]
        St["outline_reason_on"] = datetime.date.today().isoformat()
        self.M().pending = True
        self.host.changed()
        return St["outline_reason"]

    def from_file(self):
        """Start from a saved outline: Setup's own Bring in an outline (a workbook, Word or PDF)."""
        if self.M() is None:
            return False
        return self.host.setups_page.bring_in()

    def ours(self, how):
        if self.M() is None:
            return False
        self._keep("ours")
        b = self.builder()
        if how == "headings":
            ok = b.from_headings()
        elif how == "word":
            b.show_text(True)
            ok = b.text_panel.from_word()
        elif how == "factors":
            ok = self.from_factors()
        else:
            ok = b.blank()
        self.refresh()
        diag.activity("outline_start_ours")
        return ok

    def answer(self, how):
        """4.6.0: the question for an outline already started from the customer's headings. Prescribed marks its
        sections as the customer's (on refresh, outlinemarks); ours keeps them as a start. Nothing is rebuilt."""
        if self.M() is None or how not in FROM:
            return False
        self._keep(how)
        self.refresh()
        if how == "prescribed":
            diag.activity("outline_answered_prescribed")
        else:
            diag.activity("outline_answered_ours")
        return True

    def from_factors(self):
        """Section M's factors and subfactors as the sections (Shred > Evaluation holds them)."""
        import custfocus as F
        import effortrec as R
        b = self.builder()
        b.show_text(True)
        fs = F.factors(R.Record(self.host.ws.root)) if self.host.ws is not None else []
        if not fs:
            self.host.status("No evaluation factors yet: add them on Shred > Evaluation Criteria, or pick another start.")
            return b.blank()
        tops = [f for f in fs if not f.get("parent")]
        lines, n = [], 0
        for t in tops:
            n += 1
            lines.append(f"{n} {t['name']}")
            for k, s in enumerate([f for f in fs if f.get("parent") == t["id"]], 1):
                lines.append(f"{n}.{k} {s['name']}")
        b.text.setPlainText("\n".join(lines))
        try:
            b.text_panel.preview()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.host.status(f"{len(lines)} sections from the evaluation factors. Edit them, then Apply.")
        return True
