"""Stationkeeper (Qt): the start of the Qt edition (2.59.0). It shares the app folder, its config and every effort
file with Stationkeeper (classic); its temp folder is its own. Importing app_gui first installs the network guard
and the folder sandbox; no tkinter window is opened. Rules only (No AI); nothing leaves the PC."""
import os
import sys

os.environ.setdefault("SK_SANDBOX_TEMP", "temp_qt")      # never the classic app's temp folder (it is wiped at start)
import app_gui as A                                        # network guard, sandbox, config folder, the readers


def main(argv=None):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from skqt import theme
    from skqt.mainwin import MainWindow
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Stationkeeper (Qt)")
    ico = os.path.join(A.BASE_DIR, "assets", "scanner.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))
    theme.apply(app)
    import diag
    diag.activity("qt_started")
    w = MainWindow(app, A.CONFIG_DIR, A.APP_VERSION)
    if "--selftest" in (argv or sys.argv):            # the build checks the built program starts (no effort opened)
        w.show()
        app.processEvents()
        ok = w.windowTitle().startswith("Stationkeeper (Qt)")
        with open(os.path.join(A.SANDBOX_DIR, "qt_selftest.txt"), "w", encoding="utf-8") as f:
            f.write("QT SELFTEST " + ("PASS" if ok else "FAIL") + "\n")
        w.close()
        return 0 if ok else 1
    w.show()
    if w.efforts.current:
        w.open_effort(w.efforts.current)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
