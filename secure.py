"""SCIF-ready (2.97.0): the mode in which Stationkeeper writes no logs, keeps no training data, makes no bug reports or
support files, and cannot be switched back.

SCIF-ready is on when any of these is true, checked at start before anything is written:
- this is the SCIF build (buildvariant.SCIF: logging, training capture, feedback and support files are left out of it);
- the program folder holds the seal (SCIF-READY.seal), written when someone chose SCIF-ready;
- the data folder holds the seal: data used in SCIF-ready stays sealed, even under a fresh copy of the program.
Nothing in the app removes a seal. Leaving SCIF-ready means a fresh copy of the program AND a new data folder, which is
your site's decision, not the app's.

Also here: what the open effort allows (its sensitivity on sensitivity.py's scale) for training and bug reports.
Standard library only.
"""
import datetime, getpass, os

SEAL = "SCIF-READY.seal"
ACTIVE = False                       # set at start (app_gui) before logging begins
EFFORT_LEVEL = -1                    # the open effort's level (mainwin), -1 when not known
SEAL_TEXT = ("This Stationkeeper is SCIF-ready.\r\n\r\n"
             "It writes no logs, keeps no training data, makes no bug reports or support files, and cannot be switched\r\n"
             "back to another mode. This file was written when SCIF-ready was chosen; the app never removes it.\r\n"
             "Sealed: {when} by {who}.\r\n")


def build_scif():
    try:
        import buildvariant
        return bool(getattr(buildvariant, "SCIF", False))
    except Exception:
        return False


def sealed(base_dir="", data_dir=""):
    return any(d and os.path.isfile(os.path.join(d, SEAL)) for d in (base_dir, data_dir))


def scif(base_dir="", data_dir=""):
    return build_scif() or sealed(base_dir, data_dir)


def start(base_dir, data_dir):
    """At start, before logging: decide SCIF-ready. Returns it. The SCIF build also writes the seal on its first start,
    so an update pack (which may carry the regular program) never takes it out of SCIF-ready."""
    global ACTIVE
    ACTIVE = scif(base_dir, data_dir)
    if build_scif():
        text = SEAL_TEXT.format(when=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), who="the SCIF build")
        for d in (base_dir, data_dir):
            try:
                if d and not os.path.isfile(os.path.join(d, SEAL)):
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, SEAL), "w", encoding="utf-8") as f:
                        f.write(text)
            except OSError:
                pass
    return ACTIVE


def seal(base_dir, data_dir, who=None, clear=True):
    """Make this install SCIF-ready for good: the seal in the program folder and the data folder; clear: delete the
    logs, training data and bug reports kept before. Returns the folders sealed."""
    global ACTIVE
    text = SEAL_TEXT.format(when=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), who=who or getpass.getuser())
    done = []
    for d in (base_dir, data_dir):
        if d:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, SEAL), "w", encoding="utf-8") as f:
                f.write(text)
            done.append(d)
    ACTIVE = True
    try:
        import diag
        diag.off()                       # the crash file closes first, so the logs folder can be deleted
    except Exception:
        pass
    if clear:
        wipe(base_dir, data_dir)
    return done


def wipe(base_dir, data_dir):
    """Delete the logs, training data and bug reports this PC kept before it was sealed."""
    import shutil
    for d in (os.path.join(base_dir, "logs"), os.path.join(data_dir, "training_data"), os.path.join(base_dir, "training_data"),
              os.path.join(data_dir, "feedback"), os.path.join(base_dir, "feedback")):
        if d and os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)


def training_ok(level=None):
    """Training data may be kept or sent: never in SCIF-ready; the level (the open effort's by default) known and at
    most CUI."""
    import sensitivity as S
    if ACTIVE:
        return False
    return S.training_ok(EFFORT_LEVEL if level is None else level)


def feedback_ok():
    """Bug reports and support files: never in SCIF-ready, nor while an effort above CUI is open."""
    import sensitivity as S
    return not ACTIVE and EFFORT_LEVEL <= S.CUI


def logging_ok():
    return not ACTIVE
