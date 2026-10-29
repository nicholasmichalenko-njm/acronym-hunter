"""Where your data lives (2.80.0). The program folder holds only the program (replaced by update packs and new
downloads); your settings, the author list, the master acronym database, OCR fixes, knowledge, training lines and
feedback live in a folder of their own, "Stationkeeper Data", beside the program folder. Updates and new downloads never
touch it, a new download unzipped beside it picks it up, and deleting both folders still removes everything.

Which folder: SK_DATA_DIR when set (tests); a path written in the program folder's data_location.txt (Settings > Move
the data folder); else "Stationkeeper Data" beside the program folder. When that cannot be created (a program folder
IT installed in Program Files), the data stays in the program folder as before 2.80.0. Running from source (not
packaged) keeps the data in the source folder.

First start of 2.80.0: what the program folder held (config, acronym_database.csv, training_data, feedback and
_local_sandbox\\settings.json) is copied into the data folder, and a note in the old config folder says where it went.
Nothing is deleted. Standard library only.
"""
import datetime, json, os, shutil, sys

NAME = "Stationkeeper Data"
POINTER = "data_location.txt"
ITEMS = (("config", True), ("acronym_database.csv", False), ("training_data", True), ("feedback", True))
INFO = "data_info.json"
README = ("Stationkeeper Data\r\n==================\r\n\r\nYour work and your Stationkeeper settings. Update packs and new "
          "downloads never change this folder. Keep it with the Stationkeeper program folder; deleting both removes everything.\r\n\r\n"
          "Efforts\\               One folder per effort: its customer documents, volumes, Response Setup, exports, its\r\n"
          "                       compliance matrix and effort list, and the app's working files for it.\r\n"
          "acronym_database.csv   Your master acronym database (Stationkeeper makes it the first time it starts).\r\n"
          "config\\                Settings, the author list, OCR fixes and knowledge. Change them in the app, not here.\r\n"
          "feedback\\, training_data\\   What you send to improve the reader. Nothing leaves the PC by itself.\r\n\r\n"
          "Back up efforts with Settings > Backups.\r\n")
README_V = 2


def frozen():
    return bool(getattr(sys, "frozen", False))


def resolve(base_dir):
    """(data_dir, why): why is 'env', 'pointer', 'beside', 'program folder' or 'source'."""
    env = os.environ.get("SK_DATA_DIR")
    if env:
        return os.path.abspath(env), "env"
    if not frozen():
        return base_dir, "source"
    try:
        with open(os.path.join(base_dir, POINTER), encoding="utf-8") as f:
            p = f.read().strip()
        if p and os.path.isdir(p):
            return os.path.abspath(p), "pointer"
    except OSError:
        pass
    beside = os.path.join(os.path.dirname(os.path.abspath(base_dir)), NAME)
    try:
        os.makedirs(beside, exist_ok=True)
        probe = os.path.join(beside, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return beside, "beside"
    except OSError:
        return base_dir, "program folder"


def ensure(data_dir, base_dir):
    """Create the data folder and bring what the program folder held. Returns the names copied (empty when nothing)."""
    if os.path.normcase(os.path.abspath(data_dir)) == os.path.normcase(os.path.abspath(base_dir)):
        return []
    os.makedirs(data_dir, exist_ok=True)
    copied = []
    for name, is_dir in ITEMS:
        src, dst = os.path.join(base_dir, name), os.path.join(data_dir, name)
        if os.path.exists(dst) or not os.path.exists(src):
            continue
        try:
            if is_dir:
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            copied.append(name)
        except OSError:
            pass
    old_settings = os.path.join(base_dir, "_local_sandbox", "settings.json")
    if os.path.isfile(old_settings) and not os.path.exists(os.path.join(data_dir, "settings.json")):
        try:
            shutil.copy2(old_settings, os.path.join(data_dir, "settings.json"))
            copied.append("settings.json")
        except OSError:
            pass
    os.makedirs(os.path.join(data_dir, "Efforts"), exist_ok=True)
    rd = os.path.join(data_dir, "READ ME.txt")
    try:                                               # 2.90.0: says what each item is; refreshed when the wording changes
        old = open(rd, encoding="utf-8").read() if os.path.exists(rd) else None
        if old != README and (old is None or old.startswith("Stationkeeper Data")):
            with open(rd, "w", encoding="utf-8") as f:
                f.write(README)
    except OSError:
        pass
    info = os.path.join(data_dir, INFO)
    if not os.path.exists(info):
        with open(info, "w", encoding="utf-8") as f:
            json.dump({"created": datetime.datetime.now().isoformat(timespec="seconds"), "from": base_dir, "copied": copied}, f, indent=1)
        if "config" in copied and os.path.isfile(os.path.join(base_dir, "config", "efforts.json")):   # real data, not the shipped defaults
            try:
                with open(os.path.join(base_dir, "config", "MOVED TO Stationkeeper Data.txt"), "w", encoding="utf-8") as f:
                    f.write(f"From 2.80.0 Stationkeeper keeps your data in:\r\n{data_dir}\r\nThis folder is no longer used.\r\n")
            except OSError:
                pass
    return copied


def set_location(base_dir, new_dir, current_dir):
    """Settings > Move the data folder: copy everything to new_dir and point the program at it. Returns the new path."""
    new_dir = os.path.abspath(new_dir)
    if os.path.normcase(new_dir) == os.path.normcase(os.path.abspath(current_dir)):
        return new_dir
    if os.path.isdir(new_dir) and os.listdir(new_dir):
        raise OSError("Choose an empty folder for the data.")
    shutil.copytree(current_dir, new_dir, dirs_exist_ok=True)
    with open(os.path.join(base_dir, POINTER), "w", encoding="utf-8") as f:
        f.write(new_dir + "\n")
    return new_dir


def efforts_dir(data_dir):
    return os.path.join(data_dir, "Efforts")


# ---------------------------------------------------------------- 2.90.0: a tidy program folder
ABOUT = "About Stationkeeper"
LEFTOVERS = "From the old program folder"


def ensure_about(base_dir, docs_dir=None):
    r"""Fill <program folder>\About Stationkeeper from the read-me files inside the program (_internal\docs), so a copy
    brought up to date by an update pack has them too. Only copies a file that is missing or different. Returns the names
    copied. A read-only program folder is left as it is."""
    docs_dir = docs_dir or os.path.join(getattr(sys, "_MEIPASS", ""), "docs")
    if not os.path.isdir(docs_dir):
        return []
    dst = os.path.join(base_dir, ABOUT)
    done = []
    try:
        os.makedirs(dst, exist_ok=True)
        for n in sorted(os.listdir(docs_dir)):
            a, b = os.path.join(docs_dir, n), os.path.join(dst, n)
            if not os.path.isfile(a):
                continue
            with open(a, "rb") as f:
                new = f.read()
            try:
                with open(b, "rb") as f:
                    if f.read() == new:
                        continue
            except OSError:
                pass
            with open(b + ".tmp", "wb") as f:
                f.write(new)
            os.replace(b + ".tmp", b)
            done.append(n)
    except OSError:
        pass
    return done


def tidy_program_folder(base_dir, data_dir):
    r"""Before 2.90.0 the program folder also held acronym_database.csv and config\ (since 2.80.0 the copies in use are in
    the data folder). When the data folder has its own, the old program-folder copies move into
    <data folder>\From the old program folder\ (never deleted). Nothing moves when the data lives in the program folder.
    Returns the names moved."""
    if os.path.normcase(os.path.abspath(data_dir)) == os.path.normcase(os.path.abspath(base_dir)):
        return []
    moved = []
    for name, is_dir in (("acronym_database.csv", False), ("config", True)):
        src, mine = os.path.join(base_dir, name), os.path.join(data_dir, name)
        if not os.path.exists(src) or not os.path.exists(mine):
            continue
        dst_dir = os.path.join(data_dir, LEFTOVERS)
        try:
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, name)
            if os.path.exists(dst):
                dst = os.path.join(dst_dir, datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + " " + name)
            shutil.move(src, dst)
            moved.append(name)
        except OSError:
            pass
    if moved:
        try:
            with open(os.path.join(data_dir, LEFTOVERS, "READ ME.txt"), "w", encoding="utf-8") as f:
                f.write("Before 2.90.0 the Stationkeeper program folder also held these. Stationkeeper uses the copies in this\r\n"
                        "data folder (since 2.80.0), so these old ones are not used. Delete this folder whenever you like.\r\n")
        except OSError:
            pass
    return moved
