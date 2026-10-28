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


def main(argv=None):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from skqt import design
    from skqt.mainwin import MainWindow
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Stationkeeper (Qt)")
    ico = os.path.join(A.BASE_DIR, "assets", "scanner.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))
    design.apply(app)
    import diag
    diag.activity("qt_started")
    w = MainWindow(app, A.CONFIG_DIR, A.APP_VERSION)
    if "--selftest" in (argv or sys.argv):            # the build checks the built program starts (no effort opened)
        w.show()
        app.processEvents()
        ok = w.windowTitle().startswith("Stationkeeper (Qt)")
        scan = _selftest_scan()                          # 2.64.0: the built program reads a Word file and finds its terms
        ok = ok and scan.startswith("ok")
        with open(os.path.join(A.SANDBOX_DIR, "qt_selftest.txt"), "w", encoding="utf-8") as f:
            f.write("QT SELFTEST " + ("PASS" if ok else "FAIL") + f" (scan: {scan})\n")
        w.close()
        return 0 if ok else 1
    w.show()
    if w.efforts.current:
        w.open_effort(w.efforts.current)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
