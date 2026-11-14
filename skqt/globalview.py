"""Settings > Team data > Global Standards (4.30.0 step 1; 4.31.0 step 2a, the boards of 2026-11-13 and 2026-11-14): the
version of the foundation this PC is on, the folder it reads versions from (Link a folder...), a newer version that is
ready (Use it now), and, for someone who can write to that folder, Update Global Standards: the changes waiting on this
PC, each with Put back, a note, and Update to version N...

Words (Nicholas 2026-11-14): update, not publish; changes waiting, not a draft. A new version is taken when the app
opens, or at once with Use it now; never in the middle of a task. A PC that can update and has changes waiting is not
moved by itself: it is told, and Use it now says what it replaces. Rules only (No AI); nothing leaves the PC."""
import os

import diag
import globalfolder as GF
import globalstd as GS
from . import design as D


def add_card(page, v):
    page.gs_card = D.Card("Global Standards", "The foundation every effort starts from: formatting, rules, lists, styles, Quick "
                          "Parts, page layout, templates, acronyms, dictionaries, stages, roles, markings, document types "
                          "and the folder plan. One set, with a version number.")
    page.gs_text = page.gs_card.add(D.label("", None)); page.gs_text.setWordWrap(True)
    page.gs_parts = page.gs_card.add(D.label("", "muted")); page.gs_parts.setWordWrap(True)
    page.gs_folder = page.gs_card.add(D.label("", "muted")); page.gs_folder.setWordWrap(True)
    page.gs_ready = page.gs_card.add(D.label("", None)); page.gs_ready.setWordWrap(True)
    from PySide6.QtWidgets import QHBoxLayout, QWidget
    row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
    page.gs_use = D.button("Use it now", "primary", lambda: use_now(page))
    page.gs_link = D.button("Link a folder...", None, lambda: link(page),
                            "The folder this PC reads Global Standards versions from: a SharePoint library synced to this PC, or any folder.")
    page.gs_update = D.button("Update Global Standards...", None, lambda: update_dialog(page),
                              "For someone who can write to the linked folder: the changes waiting on this PC become the next version.")
    for b in (page.gs_use, page.gs_link, page.gs_update):
        h.addWidget(b)
    h.addStretch(1)
    page.gs_card.add(row)
    v.addWidget(page.gs_card)
    return page.gs_card


def _who(page):
    try:
        from .modes import settings
        return (settings() or {}).get("my_name", "")
    except Exception:  # noqa: BLE001
        return ""


def ready_words(cfg, folder):
    """What to say about a newer version in the folder ("" when there is none)."""
    man = GF.ready(cfg, folder) if folder else None
    if not man:
        return ""
    by = f", updated by {man['by']}" if man.get("by") else ""
    note = f' Note: "{man["note"]}"' if man.get("note") else ""
    n = len(GS.changed(cfg)) if GS.state(cfg)["version"] else 0
    lose = f" It replaces the changes waiting on this PC in {n} part{'s' if n != 1 else ''}; a backup is kept." if n else ""
    return f"Global Standards version {man['version']} is ready{by} on {man.get('when', '')}.{note}{lose}"


def show(page):
    """The line, the parts, the folder and what is ready, read again. Returns the line."""
    try:
        cfg = page.host.config_dir
        folder = GF.folder()
        page.gs_text.setText(GS.line(cfg))
        names = sorted(n for n, _m in GS.parts(cfg).values())
        page.gs_parts.setText(("Its parts on this PC: " + ", ".join(names) + ".") if names else "")
        if not folder:
            page.gs_folder.setText("Not linked to a folder. Link a folder... to read the versions your team keeps.")
        elif not os.path.isdir(folder):
            page.gs_folder.setText(f"Linked to {folder}. The folder cannot be reached now; this PC stays on the version it has.")
        else:
            can = GF.can_update(folder)
            page.gs_folder.setText(f"Linked to {folder}. " + ("You can update the Global Standards from this PC."
                                                              if can else "This PC reads versions from it."))
        said = ready_words(cfg, folder)
        page.gs_ready.setText(said); page.gs_ready.setVisible(bool(said)); page.gs_use.setVisible(bool(said))
        page.gs_update.setVisible(bool(folder) and os.path.isdir(folder) and GF.can_update(folder))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.gs_text.text()


def link(page, path=None):
    """Point this PC at the Global Standards folder. Returns the folder, or None when nothing was chosen."""
    if path is None:
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(page, "The Global Standards folder", GF.folder())
        if not path:
            return None
    GF.set_folder(path)
    diag.activity("global_standards_linked")
    show(page)
    return path


def _tell(host, got):
    """After a version is taken: its number, and once, what it replaced and where the backup is."""
    said = f"This PC is on Global Standards version {got['version']}."
    if got.get("replaced"):
        said += " It replaced this PC's own changes in: " + ", ".join(got["replaced"]) + f". They are kept in {got['backup']}."
    try:
        host.status(said)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return said


def _reload(host):
    """The page in view reads the standards again (every page reads them when it is opened)."""
    try:
        fn = getattr(host.stack.currentWidget(), "refresh", None)
        if callable(fn):
            fn()
    except Exception:  # noqa: BLE001
        diag.swallowed()


def use_now(page):
    """Take the version that is ready. Returns what was said, or "" when nothing is ready."""
    cfg, folder = page.host.config_dir, GF.folder()
    if not GF.ready(cfg, folder):
        return ""
    try:
        got = GF.take(cfg, folder)
    except (OSError, ValueError) as e:
        page.host.status(f"The version could not be taken: {e}")
        return ""
    diag.activity("global_standards_taken")
    said = _tell(page.host, got)
    _reload(page.host)
    show(page)
    return said


def at_open(w):
    """When the app opens: a linked PC takes a newer version by itself, unless it can update and has changes waiting
    (then it is only told). Returns what was said ("" when nothing happened)."""
    try:
        cfg, folder = w.config_dir, GF.folder()
        if not folder or not GF.ready(cfg, folder):
            return ""
        if GS.state(cfg)["version"] and GS.changed(cfg) and GF.can_update(folder):
            said = ready_words(cfg, folder) + " Settings > Global Standards > Use it now."
            w.status(said)
            return said
        return _tell(w, GF.take(cfg, folder))
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return ""


def watch(w):
    """While the app runs (the team library's tick): say once when a newer version is ready. Nothing is taken."""
    try:
        man = GF.ready(w.config_dir, GF.folder())
        n = man["version"] if man else 0
        if n and n != getattr(w, "_gs_said", 0):
            w._gs_said = n
            said = f"Global Standards version {n} is ready. It is taken the next time Stationkeeper opens, or now: Settings > Global Standards > Use it now."
            w.status(said)
            return said
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return ""


def update_dialog(page, run=True, note=None):
    """Update Global Standards: the changes waiting on this PC against the version in use, Put back on the selected
    rows, a note, and Update to version N... With note given (tests) and run False, nothing is shown: the update is
    made and its manifest returned."""
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QAbstractItemView
    cfg, folder = page.host.config_dir, GF.folder()
    if not (folder and GF.can_update(folder)):
        page.host.status("Updating needs a linked folder this PC can write to.")
        return None
    if getattr(page.host, "effort_name", ""):
        page.host.status("Close the open effort first (All Efforts). The Global Standards are updated with no effort open.")
        return None

    def do(text):
        try:
            man = GF.update(cfg, folder, by=_who(page), note=text)
        except (OSError, ValueError) as e:
            page.host.status(f"The update was not made: {e}")
            return None
        diag.activity("global_standards_updated")
        page.host.status(f"Global Standards version {man['version']} is in the folder. Every linked PC takes it the next time it opens.")
        show(page)
        return man

    if run is False:
        return do(note or "")
    dlg = QDialog(page); dlg.setWindowTitle("Update Global Standards"); dlg.resize(860, 560)
    v = QVBoxLayout(dlg)
    cur = GF.current(folder)
    head = D.label("", None); v.addWidget(head)
    t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Part", "What", "The version has", "This PC has"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.horizontalHeader().setStretchLastSection(True)
    v.addWidget(t, 1)
    note_e = QLineEdit(); note_e.setPlaceholderText("A note for everyone: what this version changes and why")
    v.addWidget(note_e)
    row = QHBoxLayout()
    b_back = D.button("Put back", None, None, "The selected changes are dropped: those files are as the version has them again.")
    b_go = D.button("", "primary")
    row.addWidget(b_back); row.addStretch(1); row.addWidget(D.button("Close", None, dlg.reject)); row.addWidget(b_go)
    v.addLayout(row)
    dlg.rows = []

    def fill():
        dlg.rows = GF.waiting(cfg, folder)
        t.setRowCount(len(dlg.rows))
        for i, r in enumerate(dlg.rows):
            for j, k in enumerate(("part", "what", "old", "new")):
                t.setItem(i, j, QTableWidgetItem(str(r[k])))
        t.resizeColumnsToContents()
        n = len(dlg.rows)
        nxt = max(GF.versions(folder) + [(cur or {}).get("version", 0)]) + 1
        head.setText((f"Current: version {cur['version']}. " if cur else "No version in the folder yet. ")
                     + (f"{n} change{'s' if n != 1 else ''} waiting on this PC." if n else "Nothing is waiting on this PC."))
        b_go.setText(f"Update to version {nxt}...")
        b_go.setEnabled(bool(n)); b_back.setEnabled(bool(n) and cur is not None)

    def back():
        files = {dlg.rows[i.row()]["file"] for i in t.selectionModel().selectedRows()}
        if files:
            GF.put_back(cfg, folder, files)
            _reload(page.host)
            fill()

    def go():
        if do(note_e.text().strip()):
            dlg.accept()

    b_back.clicked.connect(back); b_go.clicked.connect(go)
    dlg.fill, dlg.table, dlg.note, dlg.b_go, dlg.b_back = fill, t, note_e, b_go, b_back
    fill()
    page.gs_dialog = dlg
    if run is True:
        dlg.exec()
    return dlg
