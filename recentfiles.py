"""Recent files (3.53.0): the files a person last opened with a tool from Home, newest first, kept on this PC
(<config>\\recent_files.json: [{path, tool, at}], at most 30). Home shows the ones still on the PC. Nothing leaves the PC."""
import datetime, json, os

FILE = "recent_files.json"
KEEP = 30


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        return [r for r in d if isinstance(r, dict) and r.get("path")] if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def add(config_dir, paths, tool, when=None):
    """Puts the files at the top (once each) with the tool they were opened with. Returns the list."""
    when = (when or datetime.datetime.now()).isoformat(timespec="minutes")
    keys = {os.path.normcase(os.path.abspath(p)) for p in paths}
    rows = [{"path": p, "tool": tool, "at": when} for p in paths]
    rows += [r for r in load(config_dir) if os.path.normcase(os.path.abspath(r["path"])) not in keys]
    rows = rows[:KEEP]
    os.makedirs(config_dir, exist_ok=True)
    p = _path(config_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    os.replace(p + ".tmp", p)
    return rows


def shown(config_dir, n=8):
    """The newest n still on this PC."""
    return [r for r in load(config_dir) if os.path.isfile(r["path"])][:n]
