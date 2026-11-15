"""The selected template, seen whole (4.39.0; ST27 of 2026-11-14, step 4): under the list of templates, five rows, one
per component (styles, Quick Parts, page layout, numbering, starting pages), each with where it comes from, what it
holds and whether it fits the others, in color; and one line: ready to make, or what to look at first. Double-click a
row to open the page that changes that component. templateparts holds the rules; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

import namedtemplates as NT
import templateparts as TP
from . import design as D

COLS = ["Component", "Where it comes from", "What it holds", "Does it fit"]
SOFT = {"ok": "ok_soft", "warn": "warn_soft"}


def add(page, layout):
    """The card's widgets on the templates page: tp_title, tp_table, tp_line."""
    page.tp_title = D.label("", "label"); layout.addWidget(page.tp_title)
    t = QTableWidget(0, len(COLS)); t.setHorizontalHeaderLabels(COLS)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setWordWrap(True); t.setColumnWidth(0, 150); t.setColumnWidth(1, 340); t.setColumnWidth(3, 320)
    t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    t.setToolTip("Double-click a row to open the page that changes that component")
    t.doubleClicked.connect(lambda i: open_part(page, i.row()))
    t.setMaximumHeight(230)
    page.tp_table = t; layout.addWidget(t)
    page.tp_line = D.label("", None); page.tp_line.setObjectName("tpLine"); layout.addWidget(page.tp_line)
    page.tp_rows = []
    return t


def refresh(page):
    """Fills the card for the selected template; hides it when there is none."""
    tid = page.current()
    t = NT.get(page.host.config_dir, tid) if tid else None
    for w in (page.tp_title, page.tp_table, page.tp_line):
        w.setVisible(t is not None)
    page.tp_rows = []
    if t is None:
        return []
    rows = TP.rows(page.host.config_dir, t)
    page.tp_rows = rows
    page.tp_title.setText(f"{t['name']} is made of")
    tok = D.tokens()
    tb = page.tp_table
    tb.setRowCount(0)
    for r in rows:
        i = tb.rowCount(); tb.insertRow(i)
        for c, text in enumerate((r["name"], r["from"], r["holds"], r["says"])):
            it = QTableWidgetItem(text)
            if c == 3:
                it.setBackground(QColor(tok[SOFT[r["state"]]])); it.setForeground(QColor(tok[r["state"]]))
            tb.setItem(i, c, it)
    tb.resizeRowsToContents()
    ok, said = TP.ready(rows)
    page.tp_line.setText(said)
    page.tp_line.setStyleSheet(f"QLabel#tpLine{{color:{tok['ok' if ok else 'warn']};font-weight:600}}")
    return rows


def open_part(page, row):
    """Opens the page that changes this component. Returns its step, or ''."""
    if not 0 <= row < len(page.tp_rows):
        return ""
    step = page.tp_rows[row]["step"]
    page.host.go(step)
    return step
