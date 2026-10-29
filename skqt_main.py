"""Stationkeeper (Qt): the start of the Qt edition (2.59.0). It shares the app folder, its config and every effort
file with Stationkeeper (classic); its temp folder is its own. Importing app_gui first installs the network guard
and the folder sandbox; no tkinter window is opened. Rules only (No AI); nothing leaves the PC."""
import os
import sys

os.environ.setdefault("SK_SANDBOX_TEMP", "temp_qt")      # never the classic app's temp folder (it is wiped at start)


def _recover_update():
    """2.76.0: before anything else loads, put back an update that stopped part-way (standard library only)."""
    try:
        import updatepack
        here = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        return updatepack.recover(here)
    except Exception:
        return ""


_recover_update()
import app_gui as A                                        # network guard, sandbox, config folder, the readers


def _selftest_scan():
    """Write a small Word file in the temp folder and scan it as Scan and review does: 'ok, N terms' or what failed."""
    import tempfile
    import docxw
    try:
        d = tempfile.mkdtemp(dir=A.SANDBOX_TEMP if os.path.isdir(A.SANDBOX_TEMP) else None)
        p = os.path.join(d, "selftest.docx")
        doc = docxw.Doc()
        doc.para("The Statement of Work (SOW) sets the Integrated Master Schedule (IMS) for the Critical Design Review (CDR).")
        doc.save(p)
        res = A.analyze_batch([p], lambda _m: None)
        return f"ok, {len(res)} terms" if "SOW" in res else f"no SOW in {len(res)} terms"
    except Exception as e:
        return f"failed: {type(e).__name__}"


def _install_knowledge(path):
    """--install-knowledge (build.ps1 -KnowledgePack): install a pack with no window and write the result to the logs."""
    import traceback
    os.makedirs(A.LOG_DIR, exist_ok=True)
    with open(os.path.join(A.LOG_DIR, "knowledge_install.txt"), "w", encoding="utf-8") as f:
        try:
            f.write(A.install_knowledge_pack(path) + "\nINSTALL OK\n")
        except Exception:
            f.write(traceback.format_exc() + "INSTALL FAILED\n")
    return 0


def _update_args(args):
    """2.76.0, with no window (IT, or the release build's test): --apply-update <pack>, --undo-update, --check-program.
    The result goes to logs/update.txt."""
    if len(args) < 2 or args[1] not in ("--apply-update", "--undo-update", "--check-program"):
        return None
    from skqt import updates as UP
    log = os.path.join(A.LOG_DIR, "update.txt")
    if args[1] == "--apply-update":
        return UP.apply_headless(args[2], log) if len(args) > 2 else 2
    return UP.undo_headless(log) if args[1] == "--undo-update" else UP.check_headless(log)


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    if len(args) > 2 and args[1] == "--install-knowledge":     # 2.74.0: Stationkeeper.exe is the Qt window now
        return _install_knowledge(args[2])
    up = _update_args(args)
    if up is not None:
        return up
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from skqt import design
    from skqt.mainwin import MainWindow
    app = QApplication(args)
    app.setApplicationName("Stationkeeper")
    ico = os.path.join(A.BASE_DIR, "assets", "scanner.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))
    design.apply(app)
    import diag
    diag.activity("qt_started")
    import supportfile as SF                         # 2.81.0: two starts in a row that never finished: a safe start
    safe = SF.begin(A.SANDBOX_DIR) if "--selftest" not in args else False
    w = MainWindow(app, A.CONFIG_DIR, A.APP_VERSION)
    w.safety.install_crash_screen()                  # 2.78.0: save first, then a plain message
    if "--selftest" in args:            # the build checks the built program starts (no effort opened)
        w.show()
        app.processEvents()
        ok = "Stationkeeper" in w.windowTitle() and "classic" not in w.windowTitle()
        scan = _selftest_scan()                          # 2.64.0: the built program reads a Word file and finds its terms
        ok = ok and scan.startswith("ok")
        with open(os.path.join(A.SANDBOX_DIR, "qt_selftest.txt"), "w", encoding="utf-8") as f:
            f.write("QT SELFTEST " + ("PASS" if ok else "FAIL") + f" (scan: {scan})\n")
        w.close()
        files = [a for a in args[args.index("--selftest") + 1:] if os.path.isfile(a)]
        if files:                                        # 2.74.0: the release smoke test scans the sample files
            A.run_selftest(files)
        return 0 if ok else 1
    w.show()
    from PySide6.QtCore import QTimer as _QT
    _QT.singleShot(8000, lambda: SF.started(A.SANDBOX_DIR))
    from skqt import helpcenter as HC
    _QT.singleShot(1500, lambda: HC.after_update(w))  # what's new, once after an update
    from skqt import modes as MO                     # 2.79.0: where is this PC used? (asked once)
    if not MO.mode():
        QTimerX = __import__("PySide6.QtCore", fromlist=["QTimer"]).QTimer
        QTimerX.singleShot(300, lambda: MO.ask_mode(w))
    if safe:
        w.status("Safe start: Stationkeeper did not finish starting twice, so the last effort was not opened. Open it from "
                 "the Effort box; if it fails again, create a support file (Settings > Help and support).")
    elif w.efforts.current:
        w.open_effort(w.efforts.current)
    from PySide6.QtCore import QTimer
    pkg = next((a for a in args[1:] if a.lower().endswith((".skpkg", ".ahpkg")) and os.path.isfile(a)), None)
    if pkg:                                              # 2.74.0: an effort package double-clicked
        QTimer.singleShot(800, lambda: w.import_package(pkg))
    upk = next((a for a in args[1:] if a.lower().endswith(".skupdate") and os.path.isfile(a)), None)
    if upk:                                              # 2.76.0: an update pack double-clicked: what it changes, then Update
        QTimer.singleShot(800, lambda: (w.go("settings"), w.settings_page.install_update(upk)))
    kp = next((a for a in args[1:] if a.lower().endswith(".skknow") and os.path.isfile(a)), None)
    if kp:                                               # a Knowledge Pack double-clicked: the install card
        QTimer.singleShot(800, lambda: (w.go("settings"), w.settings_page.install_pack(kp)))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
