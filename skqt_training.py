"""Stationkeeper Training (Qt) (2.72.0): the Training Studio in the Qt window. It shares the app folder, its config and
training data with Stationkeeper Training (classic); its temp folder is its own. Importing app_gui first installs the
network guard and the folder sandbox; no tkinter window is opened (the Trainer opens in the classic Training program's
window). Rules and the local reader only (No generative AI); nothing leaves the PC."""
import os
import sys

os.environ.setdefault("SK_SANDBOX_TEMP", "temp_qt_training")   # never the classic app's temp folder (wiped at start)
import app_gui as A                                              # network guard, sandbox, config folder, the readers
A.TRAINING_APP = True


def main(argv=None):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from skqt import design
    from skqt.trainingwin import TrainingWindow
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Stationkeeper Training (Qt)")
    ico = os.path.join(A.BASE_DIR, "assets", "trainer.ico")
    if os.path.isfile(ico):
        app.setWindowIcon(QIcon(ico))
    design.apply(app)
    w = TrainingWindow(app)
    if "--selftest" in (argv or sys.argv):            # the build checks the built program starts and reads its training set
        w.show()
        app.processEvents()
        ok = w.windowTitle().startswith("Stationkeeper Training (Qt)") and w.stack.count() == 5
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
        return 0 if ok else 1
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
