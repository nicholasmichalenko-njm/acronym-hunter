"""Work modes (2.79.0). Stationkeeper works fully offline in both; the mode decides where files go, what the app warns
about and which steps it shows.

- Secured: a SCIF or any closed network. Packages and backups go to a local folder or the site's approved transfer
  location. A folder that OneDrive (or another sync tool) uploads is flagged. Nothing suggests SharePoint.
- Connected: Microsoft 365 with OneDrive. One team folder (a OneDrive-synced SharePoint library) holds the team's
  packages and backups; OneDrive does the uploading, the app never connects. A small marker file in the team folder says
  who has which effort open, so the team sees it before opening a copy.

The mode is a statement of where the PC is used, chosen by the person (or the team's settings). It changes no security
control of the PC and certifies nothing: a site's security officer approves the software for a classified system.
Pure Python, no network.
"""
import datetime, getpass, json, os, platform, re

SECURED, CONNECTED = "secured", "connected"
NAMES = {SECURED: "Secured", CONNECTED: "Connected"}
WORKING = "Working on"            # the team folder's marker files
STALE_HOURS = 12


def onedrive_roots():
    """The folders OneDrive uploads on this PC (from the environment OneDrive sets)."""
    out = []
    for k in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        v = os.environ.get(k)
        if v and os.path.normcase(os.path.abspath(v)) not in [os.path.normcase(x) for x in out]:
            out.append(os.path.abspath(v))
    return out


def is_synced(path):
    """True when the folder is uploaded by OneDrive or a similar sync tool (SharePoint libraries sync through OneDrive)."""
    if not path:
        return False
    p = os.path.normcase(os.path.abspath(path))
    for r in onedrive_roots():
        r = os.path.normcase(r)
        if p == r or p.startswith(r.rstrip("\\/") + os.sep):
            return True
    return bool(re.search(r"[\\/](onedrive( - [^\\/]+)?|dropbox|google drive|box)[\\/]", p + os.sep, re.I))


def suggest():
    """Connected when OneDrive for work is set up on this PC, else Secured."""
    return CONNECTED if os.environ.get("OneDriveCommercial") else SECURED


def get(settings):
    m = (settings or {}).get("work_mode", "")
    return m if m in NAMES else ""


def team_dir(settings):
    return (settings or {}).get("team_dir", "") if get(settings) == CONNECTED else ""


def backup_dir(settings):
    """Where backups go: the folder chosen in Settings; in Connected mode with none chosen, the team folder's Backups."""
    bd = (settings or {}).get("backup_dir", "") or ""
    if not bd and team_dir(settings):
        bd = os.path.join(team_dir(settings), "Backups")
    return bd


def folder_warning(settings, path):
    """A warning (never a refusal) for a folder that does not fit the mode, or ''."""
    m = get(settings)
    if m == SECURED and is_synced(path):
        return ("This folder is uploaded by OneDrive or another sync tool, so files saved here leave this PC. In Secured "
                "mode use a local folder or your site's approved transfer location.")
    if m == CONNECTED and path and not is_synced(path):
        return ("This folder is not uploaded by OneDrive, so the team will not see what is saved here. Use the team's "
                "OneDrive-synced SharePoint folder.")
    return ""


def steps(mode):
    """How work moves between people in this mode, in plain steps (Settings and Help show them)."""
    if mode == SECURED:
        return ["Stationkeeper never connects to a network; nothing leaves this PC except files you save.",
                "Save backups and effort packages to a local folder or your site's approved transfer location.",
                "Move a package to another system only through your site's approved transfer process.",
                "Install update packs and Knowledge Packs that arrive the same way; each one is checked before it changes anything."]
    if mode == CONNECTED:
        return ["Stationkeeper never connects to a network; OneDrive uploads the files it saves to the team folder.",
                "Backups and effort packages go to the team folder automatically, so progress is never only on this PC.",
                "Before opening an effort, check who has it open; the app shows it and warns you.",
                "To hand an effort over, save its package to the team folder; the other person opens it and continues where you were."]
    return ["Choose where this PC is used: Secured (a SCIF or closed network) or Connected (Microsoft 365 with OneDrive)."]


# ---------------------------------------------------------------- who has an effort open (Connected mode)
def _safe(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name or "").strip().rstrip(".")[:90] or "Effort"


def marker_path(team, effort):
    return os.path.join(team, WORKING, _safe(effort) + ".json")


def mark(team, effort, app_version=""):
    if not team:
        return None
    p = marker_path(team, effort)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    d = {"effort": effort, "user": getpass.getuser(), "computer": platform.node(), "since": datetime.datetime.now().isoformat(timespec="minutes"),
         "app": app_version}
    old = who(team, effort)
    if old and old.get("user") == d["user"] and old.get("computer") == d["computer"]:
        d["since"] = old.get("since", d["since"])
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, p)
    return d


def who(team, effort):
    try:
        with open(marker_path(team, effort), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def someone_else(team, effort, now=None):
    """The marker of another person (or another PC) who has this effort open, when recent; else None."""
    d = who(team, effort)
    if not d or (d.get("user") == getpass.getuser() and d.get("computer") == platform.node()):
        return None
    try:
        since = datetime.datetime.fromisoformat(d.get("since", ""))
    except ValueError:
        return None
    try:
        age = (now or datetime.datetime.now()) - datetime.datetime.fromtimestamp(os.path.getmtime(marker_path(team, effort)))
    except OSError:
        age = (now or datetime.datetime.now()) - since
    return d if age.total_seconds() < STALE_HOURS * 3600 else None


def unmark(team, effort):
    d = who(team, effort)
    if d and d.get("user") == getpass.getuser() and d.get("computer") == platform.node():
        try:
            os.remove(marker_path(team, effort))
        except OSError:
            pass
        return True
    return False


def working(team):
    """Everyone's markers in the team folder: [{effort, user, computer, since}]."""
    out = []
    d = os.path.join(team or "", WORKING)
    if team and os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(d, f), encoding="utf-8") as fh:
                        out.append(json.load(fh))
                except (OSError, ValueError):
                    pass
    return out


def packages_dir(team, effort):
    return os.path.join(team, "Packages", _safe(effort))
