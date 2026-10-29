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
README = ("Stationkeeper Data\r\n==================\r\n\r\nYour Stationkeeper settings, author list, master acronym database, "
          "OCR fixes, knowledge, training lines and feedback.\r\nUpdate packs and new downloads never change this folder. "
          "Keep it with the Stationkeeper program folder; deleting both removes everything.\r\n\r\nEffort folders you create "
          "go in Efforts\\ unless you choose another place. Back them up with Settings > Backups.\r\n")


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
    if not os.path.exists(rd):
        with open(rd, "w", encoding="utf-8") as f:
            f.write(README)
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
