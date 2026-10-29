"""Stationkeeper (Qt): the start of the Qt edition (2.59.0). It shares the app folder, its config and every effort
file with Stationkeeper (classic); its temp folder is its own. Importing app_gui first installs the network guard
and the folder sandbox; no tkinter window is opened. Rules only (No AI); nothing leaves the PC."""
import os
import sys

os.environ.setdefault("SK_SANDBOX_TEMP", "temp_qt")      # never the classic app's temp folder (it is wiped at start)
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


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    if len(args) > 2 and args[1] == "--install-knowledge":     # 2.74.0: Stationkeeper.exe is the Qt window now
        return _install_knowledge(args[2])
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
    w = MainWindow(app, A.CONFIG_DIR, A.APP_VERSION)
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
    if w.efforts.current:
        w.open_effort(w.efforts.current)
    from PySide6.QtCore import QTimer
    pkg = next((a for a in args[1:] if a.lower().endswith((".skpkg", ".ahpkg")) and os.path.isfile(a)), None)
    if pkg:                                              # 2.74.0: an effort package double-clicked
        QTimer.singleShot(800, lambda: w.import_package(pkg))
    kp = next((a for a in args[1:] if a.lower().endswith(".skknow") and os.path.isfile(a)), None)
    if kp:                                               # a Knowledge Pack double-clicked: the install card
        QTimer.singleShot(800, lambda: (w.go("settings"), w.settings_page.install_pack(kp)))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
