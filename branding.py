"""Branding and the effort's identity (2.88.0).

- The effort's identity travels with the effort (record.json "identity", the effort picture in its data folder): the
  proposal manager, the sensitivity marking (Not CUI, CUI, Proprietary, or the team's own words), and the effort's own
  spots (label and value: capture manager, contract vehicle, value, anything). Client and solicitation stay in the
  effort list as before. Everyone who opens the effort sees the same facts, and packages and backups carry them.
- Company logos are the team's branding: up to three pictures (a prime and its teammates) in the app's config folder on
  this PC, shown at the top of the menu. The 2.89 team pack carries them.
- The Effort home layout is personal: each Windows user picks a role (Proposal Manager, Production, Author, Reviewer,
  Capture) for a starting layout, then shows, hides and orders the sections. Kept in that person's settings, never in
  the effort.
Pictures are only copied and made smaller (Pillow); nothing is read from them. Rules only (No AI); nothing leaves the PC.
"""
import datetime, json, os, shutil

PICTURE = "effort picture.png"        # the same file the classic window used (2.48.0), so older efforts keep theirs
KEEP = 800                            # a stored picture is at most this many pixels on its long side
LOGO_DIR = "brand"
LOGO_MAX = 3
PIC_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

# ------------------------------------------------------------------ sensitivity marking
NOT_SET, NOT_CUI, CUI, PROPRIETARY = "", "Not CUI", "CUI", "Proprietary"
MARKINGS = (NOT_CUI, CUI, PROPRIETARY)
MARK_TONE = {NOT_CUI: "ok", CUI: "cui", PROPRIETARY: "warn"}


def marking(sens):
    """(text for the strip across every page, tone) or None when the effort needs no strip.
    Not CUI and not set show no strip; CUI and every other marking do."""
    s = " ".join(str(sens or "").split())
    if not s or s == NOT_CUI:
        return None
    return s.upper() if s.upper().startswith("CUI") else s, MARK_TONE.get(s, "cui" if s.upper().startswith("CUI") else "warn")


def tone(sens):
    s = " ".join(str(sens or "").split())
    if not s:
        return "head"
    return MARK_TONE.get(s, "cui" if s.upper().startswith("CUI") else "warn")


# ------------------------------------------------------------------ the effort's identity
def identity(rec):
    d = dict(rec.data.get("identity") or {})
    return {"pm": d.get("pm", ""), "sensitivity": d.get("sensitivity", ""),
            "fields": [{"label": f.get("label", ""), "value": f.get("value", "")} for f in d.get("fields", []) if f.get("label")]}


def _clean(s, n=120):
    return " ".join(str(s or "").split())[:n]


def set_identity(rec, pm=None, sensitivity=None, fields=None, who=None):
    """Saves what changed and logs it on the timeline. fields: [{label, value}] in the order shown."""
    cur = identity(rec)
    new = dict(cur)
    if pm is not None:
        new["pm"] = _clean(pm, 80)
    if sensitivity is not None:
        new["sensitivity"] = _clean(sensitivity, 60)
    if fields is not None:
        seen, out = set(), []
        for f in fields:
            lab = _clean(f.get("label"), 40)
            if lab and lab.casefold() not in seen:
                seen.add(lab.casefold())
                out.append({"label": lab, "value": _clean(f.get("value"), 200)})
        new["fields"] = out
    if new == cur:
        return False
    said = []
    if new["pm"] != cur["pm"]:
        said.append(f"proposal manager {new['pm'] or '(none)'}")
    if new["sensitivity"] != cur["sensitivity"]:
        said.append(f"sensitivity {new['sensitivity'] or '(not set)'}")
    if new["fields"] != cur["fields"]:
        said.append("effort spots")
    rec.data["identity"] = new
    rec.log("effort", "Effort details: " + "; ".join(said), who=who, save=True)
    return True


def proposal_manager(rec, ident=None):
    """The named proposal manager, else the team member whose role says so."""
    ident = ident or identity(rec)
    if ident["pm"]:
        return ident["pm"]
    try:
        for m in rec.team():
            if "proposal manager" in (m.get("role") or "").casefold():
                return m["name"]
    except Exception:
        pass
    return ""


# ------------------------------------------------------------------ pictures
def _store(src, dst, keep=KEEP):
    """Copies a picture as PNG, at most keep pixels on its long side. Returns dst."""
    from PIL import Image
    with Image.open(src) as im:
        im.load()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        if max(im.size) > keep:
            im.thumbnail((keep, keep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + ".tmp"
        im.save(tmp, "PNG")
    os.replace(tmp, dst)
    return dst


def picture_path(data_dir):
    return os.path.join(data_dir, PICTURE)


def has_picture(data_dir):
    return bool(data_dir) and os.path.isfile(picture_path(data_dir))


def set_picture(data_dir, src):
    if not os.path.splitext(src)[1].lower() in PIC_EXTS:
        raise ValueError("not a picture")
    return _store(src, picture_path(data_dir))


def clear_picture(data_dir):
    p = picture_path(data_dir)
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False


def logo_dir(config_dir):
    return os.path.join(config_dir, LOGO_DIR)


def logos(config_dir):
    """The company logos in their order: [path]."""
    d = logo_dir(config_dir)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith("logo_") and f.endswith(".png")][:LOGO_MAX]


def add_logo(config_dir, src):
    have = logos(config_dir)
    if len(have) >= LOGO_MAX:
        raise ValueError(f"at most {LOGO_MAX} logos")
    if not os.path.splitext(src)[1].lower() in PIC_EXTS:
        raise ValueError("not a picture")
    n = 1 + max([int(os.path.basename(p)[5:-4]) for p in have if os.path.basename(p)[5:-4].isdigit()] or [0])
    return _store(src, os.path.join(logo_dir(config_dir), f"logo_{n:02d}.png"), keep=600)


def remove_logo(config_dir, path):
    if os.path.dirname(os.path.abspath(path)) == os.path.abspath(logo_dir(config_dir)) and os.path.isfile(path):
        os.remove(path)
        return True
    return False


def move_logo(config_dir, path, step):
    """Moves a logo earlier (-1) or later (+1) by renumbering the files."""
    have = logos(config_dir)
    if path not in have:
        return False
    i = have.index(path); j = i + step
    if not 0 <= j < len(have):
        return False
    have[i], have[j] = have[j], have[i]
    d = logo_dir(config_dir)
    tmp = []
    for k, p in enumerate(have):
        t = os.path.join(d, f"tmp_{k:02d}.png"); shutil.move(p, t); tmp.append(t)
    for k, t in enumerate(tmp):
        shutil.move(t, os.path.join(d, f"logo_{k + 1:02d}.png"))
    return True


# ------------------------------------------------------------------ the countdown
def countdown(due_iso, now=None, zone="", now_utc=None):
    """(days, hours, minutes, seconds) to the due time, or ('passed', days since) once it has passed; None without one.
    2.92.0: with zone (the submission's time zone key) the due time is read in that zone and compared with the time now
    in UTC (now_utc, else the PC's clock), so a customer three time zones away counts down right. Without a zone it is
    read as this PC's local time."""
    if not due_iso:
        return None
    try:
        due = datetime.datetime.fromisoformat(due_iso)
    except ValueError:
        return None
    if len(due_iso) <= 10:
        due = due.replace(hour=23, minute=59)
    import tzones as TZ
    if zone and TZ.valid(zone) and now is None:
        secs = int((TZ.to_utc(due, zone) - (now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))).total_seconds())
    else:
        secs = int((due - (now or datetime.datetime.now())).total_seconds())
    if secs < 0:
        return ("passed", (-secs) // 86400)
    return (secs // 86400, (secs % 86400) // 3600, (secs % 3600) // 60, secs % 60)


def countdown_words(c):
    if c is None:
        return ""
    if c[0] == "passed":
        return "Due date passed" + (f" {c[1]} day(s) ago" if c[1] else " today")
    d, h, m, s = c
    return f"{d} day{'s' if d != 1 else ''}  {h:02d}:{m:02d}:{s:02d}"


def countdown_tone(c):
    if c is None:
        return "head"
    if c[0] == "passed" or c[0] < 3:
        return "crit"
    return "warn" if c[0] < 10 else "accent"


# ------------------------------------------------------------------ the personal Effort home layout
SECTIONS = (("stage", "Stage", "wide"), ("deliverables", "Deliverables", "wide"), ("mywork", "My work", "half"),
            ("goals", "Gate goals", "half"), ("notes", "Notes and open questions", "half"), ("tasks", "Tasks", "half"),
            ("calendar", "Calendar", "half"), ("formatting", "Formatting requirements", "half"),     # 2.94.0
            ("submission", "Submission instructions", "half"),                                        # 2.96.0
            ("custqa", "Customer Q&A", "half"),                                                       # 2.98.0
            ("custfocus", "Evaluation and hot buttons", "half"),                                      # 2.99.0
            ("info", "Customer information", "wide"), ("timeline", "Timeline", "wide"))
KEYS = tuple(k for k, _t, _w in SECTIONS)
TITLE = {k: t for k, t, _w in SECTIONS}
WIDTH = {k: w for k, _t, w in SECTIONS}
ROLES = {
    "Proposal Manager": ("stage", "formatting", "submission", "custqa", "custfocus", "goals", "notes", "tasks", "calendar", "deliverables", "info",
                         "timeline"),
    "Production": ("deliverables", "formatting", "submission", "calendar", "tasks", "stage", "notes", "timeline"),
    "Author": ("mywork", "tasks", "notes", "calendar", "formatting", "stage"),
    "Reviewer": ("stage", "calendar", "notes", "tasks", "formatting", "deliverables"),
    "Capture": ("stage", "info", "custfocus", "submission", "custqa", "notes", "calendar", "goals", "timeline"),
}
ROLE_NAMES = tuple(ROLES)
DEFAULT_ROLE = "Proposal Manager"
ROLE_SAYS = {"Proposal Manager": "Stage, gate goals, questions, tasks and the calendar first.",
             "Production": "Deliverables, page limits and dates first.",
             "Author": "What is assigned to you, your tasks and the questions first.",
             "Reviewer": "Where the effort is, the review dates and open questions first.",
             "Capture": "Stage, customer information and questions first."}


def preset(role, team=None):
    """A role's starting layout: the team's (a team pack, 2.89.0) where it has one, else the built-in one."""
    team = team or {}
    shown = [k for k in (team.get(role) or ROLES.get(role, ROLES[DEFAULT_ROLE])) if k in KEYS] or list(ROLES[DEFAULT_ROLE])
    return {"role": role if role in ROLES else DEFAULT_ROLE, "order": shown + [k for k in KEYS if k not in shown], "hidden":
            [k for k in KEYS if k not in shown], "custom": False}


def layout(settings, team=None):
    """The person's layout: {role, order (every key), hidden, custom}. team: the team's role layouts."""
    lay = (settings or {}).get("home_layout") or {}
    base = preset(lay.get("role", DEFAULT_ROLE), team)
    if not lay.get("custom"):
        return base
    order = [k for k in lay.get("order", []) if k in KEYS]
    order += [k for k in base["order"] if k not in order]
    return {"role": base["role"], "order": order, "hidden": [k for k in lay.get("hidden", []) if k in KEYS], "custom": True}


def shown(lay):
    return [k for k in lay["order"] if k not in lay["hidden"]]


def rows(keys):
    """Pairs half-width sections side by side: [[key] or [key, key]] in order."""
    out, held = [], None
    for k in keys:
        if WIDTH[k] == "wide":
            if held:
                out.append([held]); held = None
            out.append([k])
        elif held:
            out.append([held, k]); held = None
        else:
            held = k
    if held:
        out.append([held])
    return out


def custom_layout(role, order, hidden, team=None):
    order = [k for k in order if k in KEYS] + [k for k in KEYS if k not in order]
    lay = {"role": role if role in ROLES else DEFAULT_ROLE, "order": order, "hidden": [k for k in hidden if k in KEYS], "custom": True}
    base = preset(lay["role"], team)
    if lay["order"] == base["order"] and sorted(lay["hidden"]) == sorted(base["hidden"]):
        lay["custom"] = False
    return lay


def to_json(lay):
    return json.loads(json.dumps(lay))
