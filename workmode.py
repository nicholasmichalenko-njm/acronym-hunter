"""Work modes (2.79.0; three since 2.97.0). Stationkeeper works fully offline in all of them; the mode decides where
files go, what the app keeps about itself and which steps it shows.

- Offline: this PC on its own, for testing and everyday work on General business, Proprietary and CUI documents.
  Content-free logs and training corrections are kept on this PC. A folder that OneDrive uploads is flagged.
- Connected: Microsoft 365 with OneDrive. One team folder (a OneDrive-synced SharePoint library) holds the team's
  packages and backups; OneDrive does the uploading, the app never connects. A small marker file in the team folder says
  who has which effort open, so the team sees it before opening a copy.
- SCIF-ready: a SCIF or any classified system. No logs, no training data, no bug reports or support files, and it
  cannot be switched back (secure.py: the SCIF build, or the seal written when it was chosen). Before 2.97.0 the
  setting "secured" meant a closed network without the lock; those PCs read as Offline until SCIF-ready is chosen,
  because the lock cannot be undone and is never set for anyone.

Documents marked above CUI are refused in Offline and Connected (sensitivity.guard); training never takes anything above
CUI in any mode.

The mode is a statement of where the PC is used, chosen by the person (or the team's settings). It changes no security
control of the PC and certifies nothing: a site's security officer approves the software for a classified system.
Pure Python, no network.
"""
import datetime, getpass, json, os, platform, re

OFFLINE, CONNECTED, SECURED = "offline", "connected", "secured"
NAMES = {OFFLINE: "Offline", CONNECTED: "Connected", SECURED: "SCIF-ready"}
LONG = {OFFLINE: "Offline (testing and everyday work, General business to CUI)",
        CONNECTED: "Connected (Microsoft 365 with OneDrive and SharePoint)",
        SECURED: "SCIF-ready (no logs, no training, locked)"}
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
    """Connected when OneDrive for work is set up on this PC, else Offline."""
    return CONNECTED if os.environ.get("OneDriveCommercial") else OFFLINE


def get(settings):
    """The mode: SCIF-ready whenever this install is sealed or is the SCIF build, whatever the settings say; a setting
    of "secured" from before 2.97.0 without the seal reads as Offline."""
    try:
        import secure
        if secure.ACTIVE:
            return SECURED
    except Exception:
        pass
    m = (settings or {}).get("work_mode", "")
    if m == SECURED:
        return OFFLINE
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
        return ("This folder is uploaded by OneDrive or another sync tool, so files saved here leave this PC. In "
                "SCIF-ready mode use a local folder or your site's approved transfer location.")
    if m == OFFLINE and is_synced(path):
        return ("This folder is uploaded by OneDrive or another sync tool, so files saved here leave this PC. In Offline "
                "mode use a local folder, or choose Connected mode for the team's SharePoint folder.")
    if m == CONNECTED and path and not is_synced(path):
        return ("This folder is not uploaded by OneDrive, so the team will not see what is saved here. Use the team's "
                "OneDrive-synced SharePoint folder.")
    return ""


def steps(mode):
    """How work moves between people in this mode, in plain steps (Settings and Help show them)."""
    if mode == OFFLINE:
        return ["Stationkeeper never connects to a network; nothing leaves this PC except files you save.",
                "For testing and everyday work on General business, Proprietary and CUI documents. A document marked above "
                "CUI is refused: nothing is copied, and you are told to follow your site's spillage procedure.",
                "Content-free logs (no document text, names or numbers) and the training corrections you choose to save stay "
                "on this PC, so problems can be fixed and reading improved. Training takes nothing above CUI, and nothing "
                "from an effort whose sensitivity is not known.",
                "Save backups and effort packages to a local folder."]
    if mode == SECURED:
        return ["SCIF-ready: Stationkeeper writes no logs, keeps no training data and makes no bug reports or support files. "
                "Nothing about the documents or the work is recorded outside the effort's own files.",
                "This cannot be switched back. Leaving SCIF-ready takes a fresh copy of the program and a new data folder, as "
                "your security officer directs.",
                "Stationkeeper never connects to a network. Save backups and effort packages to a local folder or your site's "
                "approved transfer location, and move them only through your site's approved transfer process.",
                "Install update packs that arrive the same way; each one is checked before it changes anything."]
    if mode == CONNECTED:
        return ["Stationkeeper never connects to a network; OneDrive uploads the files it saves to the team folder.",
                "Backups and effort packages go to the team folder automatically, so progress is never only on this PC.",
                "Before opening an effort, check who has it open; the app shows it and warns you.",
                "To hand an effort over, save its package to the team folder; the other person opens it and continues where you were."]
    return ["Choose where this PC is used: Offline (testing and everyday work), Connected (Microsoft 365 with OneDrive) or "
            "SCIF-ready (no logs, no training, locked)."]


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
