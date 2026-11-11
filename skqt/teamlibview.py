"""The team library in the window (4.7.0; teamlib): the tick on opening and every two minutes, what it found said in
the status line, the question for a column taken out of the workbook (asked once), and Settings > The team > Team
library: where the files are, Change..., Open the folder and Open the workbook. Nothing leaves the PC."""
import os

import diag
from . import design as D

INTERVAL_MS = 120000


def on():
    """The tests turn it on themselves (SK_TEAMLIB_TEST): most of them never look at the team library."""
    return not os.environ.get("AH_TEST") or bool(os.environ.get("SK_TEAMLIB_TEST"))


def install(w):
    from PySide6.QtCore import QTimer
    w.team_timer = QTimer(w, interval=INTERVAL_MS, timeout=lambda: tick(w))
    if on():
        w.team_timer.start()
        QTimer.singleShot(4000, lambda: tick(w))


def tick(w, ask=True):
    """Run the team library's tick and the open effort's; say what happened. Returns the said lines."""
    import teamlib as T
    said = []
    try:
        res = T.tick(w.config_dir)
        said += res.get("said") or []
        if ask and res.get("question"):
            ask_removed(w, res["question"])
        if w.ws is not None and getattr(w, "effort_path", ""):
            r = T.effort_tick(w.ws, w.effort_path, w.effort_name)
            if isinstance(r, dict) and r.get("changed"):
                said.append(f"Read from this effort's formatting workbook: {len(r['changed'])} change(s).")
                try:
                    w.changed()
                except Exception:  # noqa: BLE001
                    diag.swallowed()
            elif r == "waiting":
                said.append("This effort's formatting workbook is open in Excel: your changes are written when it closes.")
            for pr in (r or {}).get("problems", []) if isinstance(r, dict) else []:
                said.append("This effort's formatting workbook: " + pr)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    if said:
        w.status("  ".join(said))
    return said


def ask_removed(w, cols, run=True, answer=None):
    """A property column taken out of the workbook: take it off every row, or keep the values. Asked once."""
    import teamlib as T
    names = ", ".join(f"{k} ({s})" for s, k in cols[:6])
    if answer is None and run and not os.environ.get("AH_TEST"):
        from PySide6.QtWidgets import QMessageBox
        m = QMessageBox(w)
        m.setWindowTitle("A column was taken out of the workbook")
        m.setText(f"The Company Standards workbook no longer has: {names}.")
        m.setInformativeText("Take it off every row of the standard, or keep the values as they are (the column comes back "
                             "on the next write)? You are asked once.")
        drop = m.addButton("Take it off every row", QMessageBox.AcceptRole)
        m.addButton("Keep the values", QMessageBox.RejectRole)
        m.exec()
        answer = "drop" if m.clickedButton() is drop else "keep"
    if answer is None:
        return None
    T.answer_removed(w.config_dir, answer)
    diag.activity("team_book_column_answered")
    return answer


# ------------------------------------------------------------------ Settings > The team > Team library
def card(page):
    """The Settings card. Returns it."""
    from PySide6.QtWidgets import QHBoxLayout
    import teamlib as T
    c = D.Card("Team library", "The Company Standards (Default) as files: the values in one Excel workbook (Company "
               "Standards.xlsx) and the Word files beside it (covers, title pages, Quick Parts). Edit them in Excel and Word "
               "or here: the app reads what changed and writes what it changes. Point it at a SharePoint library synced "
               "to each PC so the team shares one.")
    page.tl_where = D.label("", "muted")
    c.body.addWidget(page.tl_where)
    row = QHBoxLayout(); c.body.addLayout(row)
    row.addWidget(D.button("Change...", None, lambda: change(page), "Another folder, such as a synced SharePoint library"))
    row.addWidget(D.button("Open the folder", None, lambda: _open(T.folder(page.host.config_dir))))
    row.addWidget(D.button("Open the workbook", "primary", lambda: _open(T.book_path(page.host.config_dir)),
                           "Company Standards.xlsx in Excel"))
    row.addStretch(1)
    page.tl_card = c
    fill(page)
    return c


def fill(page):
    import teamlib as T
    try:
        st = T.state(page.host.config_dir)
        bits = [T.folder(page.host.config_dir)]
        if st.get("written"):
            bits.append(f"written {st['written']}")
        if st.get("read"):
            bits.append(f"read {st['read']}")
        if st.get("waiting"):
            bits.append("waiting for Excel to close it")
        page.tl_where.setText("  ·  ".join(bits))
    except Exception:  # noqa: BLE001
        diag.swallowed()


def change(page, path=None):
    """Point the team library at another folder (its files are written there on the next tick)."""
    import app_gui as A
    if path is None:
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(page, "The team library's folder", "")
        if not path:
            return None
    s = A.load_settings()
    s["team_library"] = path
    A.save_settings(s)
    import teamlib as T
    st = T.state(page.host.config_dir)
    st["book"] = None
    st["dirty"] = not os.path.isfile(os.path.join(path, T.BOOK))
    T._save_state(page.host.config_dir, st)
    fill(page)
    diag.activity("team_library_moved")
    return path


def _open(path):
    if os.environ.get("AH_TEST"):
        return path
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    if os.path.exists(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    return path
