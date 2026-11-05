"""Team References (3.53.0, plan decision 7: one space): every list the team keeps and the spaces read, in one place.
Custom dictionaries (Word's, built here), banned phrases (Submission Check now, Technical Edit from 3.54.0), this PC's
acronym database, the Exclusion List, fixes for misread text (every picture read on this PC) and the team's Wall of
Truth. Each card says what the list is, how many it holds, who reads it, and opens it. The lists stay where they are
kept; nothing moves on disk. Rules only; nothing leaves the PC."""
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import diag
from . import design as D
from .adaptive import FlowLayout


def _count(f):
    try:
        return f()
    except Exception:  # noqa: BLE001  a list that cannot be read shows no count
        diag.swallowed()
        return None


class BannedDialog(QDialog):
    """The banned phrases: Phrase, Level (Banned or Avoid), Use instead, Why. Add, remove, save."""
    COLS = ("Phrase", "Level", "Use instead", "Why")

    def __init__(self, parent):
        import banned as BN
        super().__init__(parent)
        self.setWindowTitle("Banned phrases"); self.resize(900, 560)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Banned: always fixed. Avoid: checked by a person. A hyphen, space or line break between words all "
                            "match; * stands for any letters (utiliz*).", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(list(self.COLS))
        self.t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.t.setColumnWidth(0, 220); self.t.setColumnWidth(1, 100); self.t.setColumnWidth(2, 200)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        v.addWidget(self.t, 1)
        for r in BN.load():
            self.add_row(r)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Add a phrase", None, lambda: self.add_row({"Level": "Banned"})))
        row.addWidget(D.button("Remove", "ghost", lambda: self.remove()))
        row.addStretch(1)
        row.addWidget(D.button("Save", "primary", lambda: (self.save(), self.accept())))
        row.addWidget(D.button("Close", "ghost", self.reject))

    def add_row(self, r):
        import banned as BN
        n = self.t.rowCount(); self.t.insertRow(n)
        for c, k in enumerate(self.COLS):
            if k == "Level":
                box = QComboBox(); box.addItems(list(BN.LEVELS)); box.setCurrentText(r.get("Level") or "Banned")
                self.t.setCellWidget(n, c, box)
            else:
                self.t.setItem(n, c, QTableWidgetItem(r.get(k, "")))
        return n

    def remove(self):
        for r in sorted({i.row() for i in self.t.selectedIndexes()}, reverse=True):
            self.t.removeRow(r)

    def rows(self):
        out = []
        for n in range(self.t.rowCount()):
            r = {}
            for c, k in enumerate(self.COLS):
                r[k] = self.t.cellWidget(n, c).currentText() if k == "Level" else (self.t.item(n, c).text() if self.t.item(n, c) else "")
            out.append(r)
        return out

    def save(self):
        import banned as BN
        n = BN.save(self.rows())
        diag.activity("banned_phrases_saved", n=n)
        return n


class TeamReferencesPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        v.addWidget(D.label("The lists the team keeps, read by every space that needs them. Change one here and every effort and "
                            "tool uses it from then on.", "muted"))
        self.cards = {}
        grid = FlowLayout(); grid.setSpacing(D.SPACE["m"]); v.addLayout(grid)
        for key, title, what, readers, actions in self.catalog():
            c = D.Card(title, what)
            c.setMinimumWidth(360); c.setMaximumWidth(560)
            c.count = D.label("", "label"); c.add(c.count)
            c.add(D.label("Read by: " + readers, "muted"))
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
            for i, (label, fn) in enumerate(actions):
                h.addWidget(D.button(label, "primary" if i == 0 else None, fn))
            h.addStretch(1); c.add(row)
            grid.addWidget(c)
            self.cards[key] = c
        v.addStretch(1)
        from .dictview import DictionariesCard
        self.dict_card = DictionariesCard(host)          # the same card Settings shows, here as well
        v.addWidget(self.dict_card)

    def catalog(self):
        h = self.host
        return (
            ("banned", "Banned phrases", "Words and phrases the team does not write, and what to write instead.",
             "Submission Check (Technical Edit from 3.54.0)", [("Open...", lambda: self.open_banned())]),
            ("database", "This PC's acronym database", "Every term and meaning known on this PC: the provided database and the "
             "terms you added (usually after submission).", "Acronyms, Acronym Finder, First Use Check",
             [("Load a database...", lambda: h.settings_page.load_master()), ("Open in Excel", lambda: self.open_db())]),
            ("exclusion", "Exclusion List", "Terms left out of every effort's acronym list (place names, words that only look "
             "like acronyms).", "Acronyms, Acronym Finder", [("Open...", lambda: self.open_exclusion())]),
            ("ocrfix", "Fixes for misread text", "When the reader misreads a word in a picture, the fix used every time a "
             "picture is read on this PC.", "Every space that reads pictures", [("Open...", lambda: self.open_fixes())]),
            ("truth", "The team's Wall of Truth", "The company facts every effort can add: one approved way to write each.",
             "Wall of Truth in each effort", [("Open the Wall of Truth", lambda: h.go("truth"))]),
        )

    def counts(self):
        import acrdb
        import app_gui as A
        import banned as BN
        import ocrfixes as OF
        return {"banned": _count(lambda: len(BN.load())), "database": _count(lambda: len(A.read_db_rows())),
                "exclusion": _count(lambda: len(acrdb.exclusion_list())), "ocrfix": _count(lambda: len(OF.rows())),
                "truth": _count(lambda: len(__import__("walloftruth").team_load(self.host.config_dir)))}

    def refresh(self):
        words = {"banned": "phrase(s)", "database": "term(s)", "exclusion": "term(s)", "ocrfix": "fix(es)", "truth": "fact(s)"}
        for k, n in self.counts().items():
            self.cards[k].count.setText("" if n is None else f"{n} {words[k]}")
        try:
            self.dict_card.refresh()
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def open_banned(self, run=True):
        d = BannedDialog(self)
        if run:
            d.exec()
            self.refresh()
        return d

    def open_db(self):
        import sys
        import app_gui as A
        import os
        if sys.platform.startswith("win") and os.path.isfile(A.DB_FILE):
            os.startfile(A.DB_FILE)                       # noqa: S606  this PC's own database
        return A.DB_FILE

    def open_exclusion(self, run=True):
        from . import acrextras as AX
        d = AX.exclusion_window(self.host.acronym_page, run=run)
        self.refresh()
        return d

    def open_fixes(self, run=True):
        from . import acrextras as AX
        d = AX.ocr_fixes_window(self.host.acronym_page, run=run)
        self.refresh()
        return d
