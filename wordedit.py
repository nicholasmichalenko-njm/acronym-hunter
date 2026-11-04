"""Edit in Word (3.40.0): a kept page (cover, title page, back cover) opened in Word as a dated working copy; what you
save there is kept as a new version, and the page before it and every original stay as they were.

  start(parts_dir, name, when)    copies the kept page to parts_dir/Editing/<name> <date and time>.docx
  state(path, since)              'editing' while Word holds the copy, 'saved' once it was saved and Word let it go,
                                  'unchanged' when nothing was saved
  keep(parts_dir, path, label)    the saved copy kept as a new page file (named by its content); returns its name

Fields typed as {volume_name} or picked from the app's Fields list stay fields. Nothing leaves the PC."""
import datetime, os, shutil

SUB = "Editing"


def lock_names(path):
    """The lock files Word writes beside a document it has open (~$ and the name, short or long form)."""
    d, f = os.path.split(path)
    return [os.path.join(d, "~$" + f[2:]), os.path.join(d, "~$" + f[1:]), os.path.join(d, "~$" + f)]


def start(parts_dir, name, when=None):
    """A dated working copy of the kept page. Returns (path, mtime when started)."""
    when = when or datetime.datetime.now()
    src = os.path.join(parts_dir, name)
    if not os.path.isfile(src):
        raise FileNotFoundError(name)
    folder = os.path.join(parts_dir, SUB)
    os.makedirs(folder, exist_ok=True)
    stem = os.path.splitext(name)[0].rsplit("-", 1)[0] or "page"
    dst = os.path.join(folder, f"{stem} {when:%Y-%m-%d %H%M%S}.docx")
    shutil.copy2(src, dst)
    return dst, os.path.getmtime(dst)


def open_in_word(path, opener=None):
    """Opens the working copy in Word (Windows). opener (tests): called with the path instead. Returns True when asked."""
    if opener is not None:
        opener(path)
        return True
    import sys
    if not sys.platform.startswith("win"):
        return False
    try:
        os.startfile(path)                                   # noqa: S606  the dated working copy only
        return True
    except OSError:
        return False


def state(path, since):
    if any(os.path.exists(p) for p in lock_names(path)):
        return "editing"
    try:
        return "saved" if os.path.getmtime(path) > since + 0.5 else "unchanged"
    except OSError:
        return "unchanged"


def keep(parts_dir, path, label):
    """The saved working copy kept as a new page file. Returns its file name; '' when the copy is not a Word file."""
    import prodparts as PP
    import zipfile
    try:
        with open(path, "rb") as f:
            data = f.read()
        zipfile.ZipFile(path).testzip()
    except (OSError, zipfile.BadZipFile):
        return ""
    return os.path.basename(PP.save_part(parts_dir, data, label))
