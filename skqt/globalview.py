"""The Global Standards page's card (4.34.0, ST14 to ST19 of 2026-11-14; before that Settings > Global Standards, 4.30.0
to 4.33.1): the version this PC is on, the folder it reads versions from (Link a folder...), a newer version that is
ready (Use it now), Install a file..., Save a file to share..., and What changed...

A save in the Global Standards on a PC that can write to the linked folder is shared at once (share_now): no Update
button, no Put back. A PC with its own change while the folder holds a newer version is told and chooses (ST13). The
number is in the window's title (badge). Rules only (No AI); nothing leaves the PC."""
import os

import diag
import globalfile as GX
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
    page.gs_notice = page.gs_card.add(D.label("", None)); page.gs_notice.setWordWrap(True)      # 4.33.0: what the last version changed here
    from PySide6.QtWidgets import QHBoxLayout, QWidget
    row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
    page.gs_use = D.button("Use it now", "primary", lambda: use_now(page))
    page.gs_link = D.button("Link a folder...", None, lambda: link(page),
                            "The folder this PC reads Global Standards versions from: a SharePoint library synced to this PC, or any folder.")
    page.gs_save = D.button("Save a file to share...", None, lambda: save_file(page),
                            "One file holding the Global Standards as they are now, for a PC with no shared folder: send it, and it is dropped on that PC's window.")
    page.gs_install = D.button("Install a file...", None, lambda: install(page),
                               "For a PC with no linked folder: take a version from its file (Global Standards version N.skgs).")
    page.gs_changed = D.button("What changed...", None, lambda: changed_dialog(page),
                               "Each change the last version made on this PC, who updated and when. Mark as seen closes it.")
    for b in (page.gs_use, page.gs_link, page.gs_install, page.gs_save, page.gs_changed):
        h.addWidget(b)
    h.addStretch(1)
    page.gs_card.add(row)
    v.addWidget(page.gs_card)
    return page.gs_card


def add_link(page, v):
    """Settings: one line and the way to the page."""
    page.gsl_card = D.Card("Global Standards", "The foundation every effort starts from has its own page.",
                           actions=[D.button("Open Global Standards", None, lambda: page.host.go("globalstd"))])
    page.gsl_text = page.gsl_card.add(D.label("", None)); page.gsl_text.setWordWrap(True)
    v.addWidget(page.gsl_card)
    return page.gsl_card


def show_link(page):
    try:
        page.gsl_text.setText(GS.line(page.host.config_dir))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.gsl_text.text()


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
    lose = f" It replaces what this PC changed itself in {n} part{'s' if n != 1 else ''}; a backup is kept." if n else ""
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
            page.gs_folder.setText(STARTER if not GS.state(cfg)["version"] else
                                   "Not linked to a folder. Link a folder... to read the versions your team keeps, or Install a file... to take one.")
        elif not os.path.isdir(folder):
            page.gs_folder.setText(f"Linked to {folder}. The folder cannot be reached now; this PC stays on the version it has.")
        else:
            can = GF.can_update(folder)
            page.gs_folder.setText(f"Linked to {folder}. " + ("A change you save here reaches everyone the next time they open Stationkeeper."
                                                              if can else "This PC reads versions from it."))
        said = ready_words(cfg, folder)
        page.gs_ready.setText(said); page.gs_ready.setVisible(bool(said)); page.gs_use.setVisible(bool(said))
        page.gs_save.setVisible(bool(GS.state(cfg)["version"]) or bool(folder))
        nt = GX.notice(cfg)
        page.gs_notice.setText(GX.notice_words(nt) if nt else ""); page.gs_notice.setVisible(bool(nt)); page.gs_changed.setVisible(bool(nt))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.gs_text.text()


STARTER = ("This PC runs on the built-in starter: no folder is linked and no version is installed. Link a folder... to read "
           "the versions your team keeps, or Install a file... to take one.")


def install(page, path=None):
    """Take a version from its file. Returns what was said ("" when nothing was chosen or the file was refused)."""
    if path is None:
        from PySide6.QtWidgets import QFileDialog
        path, _f = QFileDialog.getOpenFileName(page, "A Global Standards file", "", f"Global Standards (*{GX.EXT})")
        if not path:
            return ""
    try:
        got = GX.install(page.host.config_dir, path)
    except (OSError, ValueError) as e:
        page.host.status(f"The file was not installed: {e}")
        return ""
    diag.activity("global_standards_installed")
    said = _tell(page.host, got)
    _reload(page.host)
    show(page)
    return said


def changed_dialog(page, run=True):
    """What the last version changed on this PC: each change, who updated and when, the note. Mark as seen."""
    from PySide6.QtWidgets import QAbstractItemView, QDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout
    cfg = page.host.config_dir
    nt = GX.notice(cfg)
    if not nt:
        return None
    dlg = QDialog(page); dlg.setWindowTitle(f"Global Standards version {nt['version']}"); dlg.resize(820, 520)
    v = QVBoxLayout(dlg)
    head = D.label(GX.notice_words(nt) + (f' Note: "{nt["note"]}"' if nt.get("note") else "")
                   + (" It replaced this PC's own changes in: " + ", ".join(nt["replaced"]) + f". They are kept in {nt['backup']}."
                      if nt.get("replaced") else ""), None)
    head.setWordWrap(True); v.addWidget(head)
    t = QTableWidget(len(nt["rows"]), 4); t.setHorizontalHeaderLabels(["Part", "What", "It was", "It is now"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.horizontalHeader().setStretchLastSection(True)
    for i, r in enumerate(nt["rows"]):
        for j, k in enumerate(("part", "what", "was", "now")):
            t.setItem(i, j, QTableWidgetItem(str(r.get(k, ""))))
    t.resizeColumnsToContents(); v.addWidget(t, 1)
    row = QHBoxLayout(); row.addStretch(1); row.addWidget(D.button("Close", None, dlg.reject))

    def seen():
        GX.mark_seen(cfg); show(page); dlg.accept()

    b = D.button("Mark as seen", "primary", seen); row.addWidget(b); v.addLayout(row)
    dlg.table, dlg.head, dlg.b_seen = t, head, b
    page.gs_changed_dialog = dlg
    if run:
        dlg.exec()
    return dlg


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
        got = GX.take(cfg, folder)
    except (OSError, ValueError) as e:
        page.host.status(f"The version could not be taken: {e}")
        return ""
    diag.activity("global_standards_taken")
    said = _tell(page.host, got)
    try:
        GF.receipt(cfg, folder, name=_who(page)); page.host.title()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    _reload(page.host)
    show(page)
    return said


def at_open(w):
    """When the app opens: a linked PC takes a newer version by itself, unless it can update and has changes waiting
    (then it is only told). Returns what was said ("" when nothing happened)."""
    try:
        cfg, folder = w.config_dir, GF.folder()
        if folder and os.path.isdir(folder) and not GF.ready(cfg, folder):
            return share_now(w) or (GF.receipt(cfg, folder, name=_who_host(w)) and "")     # 4.34.0: nothing newer; share what was saved, leave the receipt
        if not folder or not GF.ready(cfg, folder):
            return ""
        if GS.state(cfg)["version"] and GS.changed(cfg) and GF.can_update(folder):
            said = ready_words(cfg, folder) + " Global Standards > Use it now."
            w.status(said)
            return said
        said = _tell(w, GX.take(cfg, folder))
        GF.receipt(cfg, folder, name=_who_host(w)); w.title()
        return said
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
            said = f"Global Standards version {n} is ready. It is taken the next time Stationkeeper opens, or now: Global Standards > Use it now."
            w.status(said)
            return said
        if not n:
            return share_now(w)                                     # 4.34.0: a save reaches everyone without a button
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return ""


def share_now(host):
    """ST18: what was saved in the Global Standards on this PC becomes the next version in the folder, with no button.
    Returns what was said ("" when there was nothing to share or this PC only reads)."""
    try:
        cfg, folder = host.config_dir, GF.folder()
        if not folder or not os.path.isdir(folder):
            return ""
        with __import__("effortset").as_global():
            man = GF.share(cfg, folder, by=_who_host(host))
            GF.receipt(cfg, folder, name=_who_host(host))
        if not man:
            return ""
        diag.activity("global_standards_shared")
        said = f"Global Standards {man['version']}: your change is shared. Everyone gets it the next time they open Stationkeeper."
        host.status(said)
        try:
            host.title()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return said
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return ""


def _who_host(host):
    try:
        from .modes import settings
        return (settings() or {}).get("my_name", "")
    except Exception:  # noqa: BLE001
        return ""


def badge(host):
    """For the window's title: the number every PC can be checked against at a glance."""
    try:
        n = GS.state(host.config_dir)["version"]
        return f"  \u00b7  Global Standards {n}" if n else ""
    except Exception:  # noqa: BLE001
        return ""


def save_file(page, path=None):
    """Save a file to share...: the Global Standards as this PC has them, in one file. Returns its path ("" when
    nothing was chosen or it could not be written)."""
    import shutil, tempfile
    cfg, folder = page.host.config_dir, GF.folder()
    tmp = ""
    try:
        with __import__("effortset").as_global():
            if folder and os.path.isdir(folder) and GF.current(folder):
                share_now(page.host)
                src, n = folder, GF.current(folder)["version"]
            else:                                                   # no shared folder: the next number when something changed since the last file
                tmp = tempfile.mkdtemp(prefix="skgs_out_")
                on = GS.state(cfg)["version"]
                src, n = tmp, GF.update(cfg, tmp, by=_who(page), after=on if (not on or GS.changed(cfg)) else on - 1)["version"]
            name = GX.file_name(n)
            if path is None:
                from PySide6.QtWidgets import QFileDialog
                path, _f = QFileDialog.getSaveFileName(page, "Save a file to share", name, f"Global Standards (*{GX.EXT})")
                if not path:
                    return ""
            made = GX.write(src, n)
            if os.path.abspath(made) != os.path.abspath(path):
                shutil.copyfile(made, path)
                if not tmp and os.path.dirname(os.path.abspath(made)) == os.path.abspath(folder):
                    os.remove(made)                                # the folder holds the version itself; the file is the copy to send
    except (OSError, ValueError) as e:
        page.host.status(f"The file was not saved: {e}")
        return ""
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    diag.activity("global_standards_file_saved")
    page.host.status(f"Saved {os.path.basename(path)}. On the other PC: drop it on the Stationkeeper window, or Global Standards > Install a file...")
    show(page)
    return path
