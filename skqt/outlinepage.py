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

FROM = {"prescribed": "The solicitation prescribes it", "ours": "We build our own"}


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
        bar.more("Start again...", lambda: self.ask(force=True), "Prescribed by the solicitation, or ours: start the outline again")
        v.addWidget(bar)
        # the start question: once per effort
        self.start = D.Card("How does this outline start?", "Some solicitations prescribe the response outline; for others "
                            "we build our own from the solicitation, our approach and what we offer. You can add our own "
                            "subsections under the customer's either way.", key=True)
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); self.start.body.addLayout(row)
        self.b_pres = D.button(FROM["prescribed"], "primary", lambda: self.prescribed(),
                               "The sections it names, in its order, with their page limits: edit, then Apply")
        row.addWidget(self.b_pres)
        self.b_ours = D.button(FROM["ours"], None, None, "Start from Section M's factors, the customer's headings, a Word "
                               "outline, or blank")
        from PySide6.QtWidgets import QMenu
        m = QMenu(self.b_ours); self.b_ours.setMenu(m)
        m.addAction("From the evaluation factors (Section M)", lambda: self.ours("factors"))
        m.addAction("From the customer's headings", lambda: self.ours("headings"))
        m.addAction("From a Word outline...", lambda: self.ours("word"))
        m.addAction("Blank: type it", lambda: self.ours("blank"))
        row.addWidget(self.b_ours); row.addStretch(1)
        v.addWidget(self.start)
        self.slot = QVBoxLayout(); v.addLayout(self.slot, 1)
        self.said = D.label("", "muted"); v.addWidget(self.said)

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
        b.setVisible(has or texting or asked)
        for x in (self.b_volume, self.b_elements, self.b_place):
            x.setEnabled(has)
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
        self.said.setText((f"Started: {FROM.get(src, '')}." + extra) if src else ("Extract a customer document in Shred first."
                                                                                  if M is None else ""))
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
        if self.M() is None:
            return False
        self._keep("prescribed")
        b = self.builder()
        ok = b.from_prescribed()
        if not ok:
            b.from_headings()
            self.host.status("The solicitation names no outline that the rules can find: its headings are shown instead. "
                             "Edit them, then Apply.")
        self.refresh()
        diag.activity("outline_start", how="prescribed")
        return ok

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
        diag.activity("outline_start", how=how)
        return ok

    def from_factors(self):
        """Section M's factors and subfactors as the sections (Shred > Evaluation holds them)."""
        import custfocus as F
        import effortrec as R
        b = self.builder()
        b.show_text(True)
        fs = F.factors(R.Record(self.host.ws.root)) if self.host.ws is not None else []
        if not fs:
            self.host.status("No evaluation factors yet: add them on Shred > Evaluation, or pick another start.")
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
