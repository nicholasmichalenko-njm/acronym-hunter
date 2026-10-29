"""Stationkeeper Training (Qt) (2.72.0): the Training Studio in the Qt window. It shares the app folder, its config and
training data with Stationkeeper Training (classic); its temp folder is its own. Importing app_gui first installs the
network guard and the folder sandbox; no tkinter window is opened (the Trainer opens in the classic Training program's
window). Rules and the local reader only (No generative AI); nothing leaves the PC."""
import os
import sys

os.environ.setdefault("SK_SANDBOX_TEMP", "temp_qt_training")   # never the classic app's temp folder (wiped at start)
try:                                                             # 2.76.0: put back an update that stopped part-way
    import updatepack
    updatepack.recover(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass
import app_gui as A                                              # network guard, sandbox, config folder, the readers
A.TRAINING_APP = True


def main(argv=None):
    args0 = list(sys.argv if argv is None else argv)
    if len(args0) > 1 and args0[1] in ("--apply-update", "--undo-update", "--check-program"):   # 2.76.0, no window
        from skqt import updates as UP
        log = os.path.join(A.LOG_DIR, "update.txt")
        if args0[1] == "--apply-update":
            return UP.apply_headless(args0[2], log) if len(args0) > 2 else 2
        return UP.undo_headless(log) if args0[1] == "--undo-update" else UP.check_headless(log)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from skqt import design
    from skqt.trainingwin import TrainingWindow
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Stationkeeper Training")
    ico = os.path.join(A.BASE_DIR, "assets", "trainer.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))
    design.apply(app)
    w = TrainingWindow(app)
    if "--selftest" in (argv or sys.argv):            # the build checks the built program starts and reads its training set
        w.show()
        app.processEvents()
        ok = w.windowTitle().startswith("Stationkeeper Training ") and w.stack.count() == 6
        try:
            import tess_train
            tools = all(os.path.isfile(os.path.join(A.TESS_DIR, t)) for t in ("lstmtraining.exe", "combine_tessdata.exe")) \
                if A.TESS_DIR and sys.platform.startswith("win") else True
            n = len(tess_train.read_samples(A.TRAIN_DIR))
            detail = f"training tools {'present' if tools else 'missing'}, {n} lines"
            ok = ok and tools
        except Exception as e:
            detail = f"failed: {type(e).__name__}"
            ok = False
        with open(os.path.join(A.SANDBOX_DIR, "qt_training_selftest.txt"), "w", encoding="utf-8") as f:
            f.write("QT TRAINING SELFTEST " + ("PASS" if ok else "FAIL") + f" ({detail})\n")
        w.close()
        args = list(argv or sys.argv)
        files = [x for x in args[args.index("--selftest") + 1:] if os.path.isfile(x)]
        if files:                                        # 2.74.0: the release smoke test scans the sample files
            A.run_selftest(files)
        return 0 if ok else 1
    w.show()
    upk = next((a for a in args0[1:] if a.lower().endswith(".skupdate") and os.path.isfile(a)), None)
    if upk:                                              # 2.76.0: an update pack double-clicked
        from PySide6.QtCore import QTimer
        from skqt import updates as UP
        QTimer.singleShot(800, lambda: (w.go("build"), UP.install_update(w, upk)))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
