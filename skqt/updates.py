"""Updates and security in Qt (2.76.0): the Updates card (Install update pack, Undo last update, Check program files)
and the About and security card (why Stationkeeper runs without admin rights), for Stationkeeper and Stationkeeper
Training. The work is updatepack's; this is the window around it. Offline: the person picks the file."""
import os
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout
import diag
import updatepack as U
from . import design as D

WHY_NO_ADMIN = (
    "Why Stationkeeper runs without an administrator password. Windows asks for one only when a program says it needs "
    "it, or when it changes protected, machine-wide places: Program Files, the Windows folder, the machine-wide registry, "
    "services and drivers. Installers ask because they write there. Stationkeeper has no installer. Its program says "
    "'run as the person who started me' (asInvoker), and it writes only inside its own folder, which you own. So "
    "Windows has nothing to ask permission for.\n\n"
    "The Windows sandbox is not the reason. Only the OCR reader (Tesseract) runs in a Windows AppContainer, and that "
    "takes rights away (no network, no files beyond two folders); a sandbox cannot grant or skip admin rights.\n\n"
    "What it means for security. Without admin rights the program cannot change Windows, install services or drivers, "
    "or touch other people's files. It can still read and write what you can, as any program you run can, so "
    "'no admin' is not an approval. Stationkeeper's protection comes from elsewhere: it has no network code, the build "
    "fails if a program file links a networking API, the OCR reader runs in the no-network sandbox, its third-party "
    "parts are pinned, listed (SBOM) and checked for known advisories, documents open read-only, and update packs must "
    "carry the publisher's signature.\n\n"
    "Running does not mean approved. It runs because this PC does not block programs in your own folders "
    "(AppLocker or WDAC); IT can turn that on at any time, and company policy may require approval for any program. "
    "Give IT security SECURITY.md (in this folder), the SBOM and the checksums. Because the program folder is yours, "
    "other software running as you could change its files: Check program files compares every file with this "
    "version's list.")


def program_name():
    import app_gui as A
    return "StationkeeperTraining" if getattr(A, "TRAINING_APP", False) else "Stationkeeper"


def app_dir():
    import app_gui as A
    return A.BASE_DIR


def version_text():
    import app_gui as A
    v = U.installed_version(app_dir())
    if not v:
        return (f"Version {A.APP_VERSION}. This copy has no list of its program files (it was not built as a release), "
                "so update packs cannot be checked against it.")
    b = U.backup_info(app_dir())
    return (f"Version {v}. Update packs (.skupdate) from the approved folder bring it up to date. Only program files "
            "change: efforts, settings, the database and training data stay as they are."
            + (f" Undo last update goes back to {b['from']}." if b and b.get("to") == v else ""))


def updates_card(win, on_close=None, install=None, undo=None):
    """win: a window with status() and toast(). on_close: saves and closes before the program restarts. install, undo:
    the page's own (it refreshes after)."""
    install = install or (lambda: install_update(win, on_close=on_close))
    undo = undo or (lambda: undo_update(win, on_close=on_close))
    card = D.Card("Updates", "Install Stationkeeper once; each new version arrives as one signed update pack.")
    card.lbl = card.add(D.label(version_text(), "muted"))
    row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
    row.addWidget(D.button("Install update pack...", "primary", lambda: install()))
    row.addWidget(D.button("Undo last update", None, lambda: undo()))
    row.addWidget(D.button("Check program files", None, lambda: check_program(win)))
    row.addStretch(1)
    card.body.addLayout(row)
    card.add(D.label("Get update packs only from the approved SharePoint folder. A pack that is not signed by the "
                     "Stationkeeper publisher, or was changed after it was made, is refused and nothing changes.", "muted"))
    return card


def security_card():
    card = D.Card("About and security", "Why Stationkeeper runs without an administrator password, and what that means.")
    lab = card.add(D.label(WHY_NO_ADMIN))
    lab.setWordWrap(True)
    return card


def _confirm(win, title, text, ok_text):
    box = QMessageBox(win); box.setWindowTitle(title); box.setText(text)
    ok = box.addButton(ok_text, QMessageBox.AcceptRole); box.addButton("Not now", QMessageBox.RejectRole)
    box.exec()
    return box.clickedButton() is ok


def _finish(win, on_close, restart):
    """Save and close, start the new version, and quit this one."""
    if on_close:
        on_close()
    if restart is None:
        U.restart(app_dir(), program_name())
        QApplication.instance().quit()
    else:
        restart()


def install_update(win, path=None, answer=None, on_close=None, restart=None):
    """answer (tests): 'install' or 'later'. restart (tests): called instead of restarting. Returns the result or None."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(win, "Install update pack (from the approved SharePoint folder)", "",
                                              f"Stationkeeper update pack (*{U.EXT})")
        if not path:
            return None
    prog, folder = program_name(), app_dir()
    try:
        plan = U.check(path, folder, prog)
    except U.UpdateError as e:
        diag.activity("update_refused")
        win.status(str(e))
        if answer is None:
            QMessageBox.information(win, "Update pack", str(e))
        return None
    info = plan["info"]
    text = (U.summary(plan) + "\n\nSigned by the Stationkeeper publisher; every file is checked before anything changes."
            + (f"\n\nNotes: {info['notes']}" if info.get("notes") else "")
            + "\n\nStationkeeper saves your work, closes, updates its program files and opens again (about a minute). "
              "Efforts, settings, the database and training data are not touched. Undo last update goes back.")
    if answer is None:
        answer = "install" if _confirm(win, "Install update pack", text, "Update now") else "later"
    if answer != "install":
        return None
    try:
        U.stage(plan, path, folder)
        res = U.apply(plan, folder)
    except U.UpdateError as e:
        diag.activity("update_failed")
        win.status(str(e))
        if restart is None:
            QMessageBox.warning(win, "Update pack", str(e))
        return None
    diag.activity("update_installed", files=res["copied"])
    win.toast(f"Updated to {res['to']}. Opening the new version...")
    _finish(win, on_close, restart)
    return res


def undo_update(win, answer=None, on_close=None, restart=None):
    prog, folder = program_name(), app_dir()
    b = U.backup_info(folder)
    if b is None:
        win.status("There is no update to undo.")
        return None
    if answer is None:
        answer = "undo" if _confirm(win, "Undo last update", f"Go back from {b['to']} to {b['from']}? Stationkeeper saves your "
                                    "work, closes and opens the earlier version. Your data is not touched.", "Undo the update") else "later"
    if answer != "undo":
        return None
    try:
        res = U.undo(folder, prog)
    except U.UpdateError as e:
        win.status(str(e))
        return None
    diag.activity("update_undone")
    win.toast(f"Back to {res['to']}. Opening it...")
    _finish(win, on_close, restart)
    return res


def check_program(win, show=True):
    r = U.check_files(app_dir())
    text = U.check_text(r)
    diag.activity("program_files_checked", n=0 if r is None else len(r["changed"]) + len(r["missing"]) + len(r["extra"]))
    if show:
        d = QDialog(win); d.setWindowTitle("Check program files"); d.setMinimumWidth(620)
        v = QVBoxLayout(d)
        lab = D.label(text); lab.setWordWrap(True); v.addWidget(lab)
        v.addWidget(D.label("This finds damaged or changed program files. It cannot prove a file is safe if someone "
                            "changed both a file and this version's list; the signed update packs and the published "
                            "checksums are the proof.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok); bb.accepted.connect(d.accept); v.addWidget(bb)
        d.exec()
    else:
        win.status(text.splitlines()[0])
    return r


def apply_headless(path, log):
    """--apply-update (IT, or the release build's test): install a pack with no window; the result goes to log."""
    prog, folder = program_name(), app_dir()
    try:
        plan = U.check(path, folder, prog)
        U.stage(plan, path, folder)
        res = U.apply(plan, folder)
        msg = f"UPDATE OK {res['from']} -> {res['to']} ({res['copied']} copied, {res['removed']} removed)"
        rc = 0
    except U.UpdateError as e:
        msg, rc = f"UPDATE REFUSED: {e}", 2
    _log(log, msg)
    return rc


def undo_headless(log):
    try:
        res = U.undo(app_dir(), program_name())
        msg, rc = f"UNDO OK {res['from']} -> {res['to']}", 0
    except U.UpdateError as e:
        msg, rc = f"UNDO REFUSED: {e}", 2
    _log(log, msg)
    return rc


def check_headless(log):
    r = U.check_files(app_dir())
    ok = r is not None and not (r["changed"] or r["missing"] or r["extra"])
    _log(log, ("CHECK OK " if ok else "CHECK FAILED ") + U.check_text(r).replace("\n", " | "))
    return 0 if ok else 3


def _log(log, msg):
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
