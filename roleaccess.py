"""Roles and Preview tools (3.13.0): which tools each role opens, and which tools the team has turned on.

A role profile picks the tools a person opens: Proposal Manager (every tool), Production, Author, Reviewer, Capture.
Tools for another role stay in the menu, greyed; opening one says who it is for and who can change the role, instead
of opening it. A person can hide them (Settings). This is guidance for a shared way of working, not security: the app
runs on each person's PC.

The role comes from the open effort first: People and roles there (the proposal manager assigns it), or the effort's
proposal manager (Edit details). With no effort open, or a person the effort does not name, it is the person's own
choice (Customize... on the Effort Dashboard).

Preview tools are still being proven on real documents. They stay off for the whole team until the proposal manager
turns them on (Settings > Team defaults); a team pack carries the choice so every PC agrees.
Rules only; nothing leaves the PC."""
import json, os

PM = "Proposal Manager"
PROFILES = ("Proposal Manager", "Production", "Author", "Reviewer", "Capture")
ALWAYS = {"efforts", "mywork", "home", "deliverables", "settings", "tools", "refs"}   # 3.53.0: Your Tools, Team References
TOOLS = {
    "Production": {"shredreq", "shredacc", "techedit", "library", "requirements", "matrix", "setup", "setups", "acronyms", "acrlist", "finalcheck", "qa", "lists", "checks", "fixcopy", "audit",
                   "formatstd", "qpstd", "layoutstd", "profiles", "templates", "prodstd", "rules", "effortfmt", "postsub", "keywords", "exportall", "drafts"},
    "Author": {"shredreq", "techedit", "library", "compare", "requirements", "custqa", "assign", "setup", "setups", "storyboards", "truth", "acronyms",
               "acrlist", "keywords", "drafts"},
    "Reviewer": {"finalcheck", "techedit", "reviews", "library", "compare", "assign", "prove", "matrix", "truth", "checks", "audit"},
    "Capture": {"shredreq", "library", "read", "compare", "requirements", "custqa", "structure", "assign", "crosswalk", "storyboards", "truth"},
}
# a role written in People and roles (the team's own words) -> the profile it means; first match wins
WORDS = (("proposal manager", PM), ("capture manager", "Capture"), ("production", "Production"), ("desktop", "Production"),
         ("publish", "Production"), ("editor", "Production"), ("graphic", "Production"), ("review", "Reviewer"),
         ("pink team", "Reviewer"), ("red team", "Reviewer"), ("gold team", "Reviewer"), ("capture", "Capture"),
         ("business development", "Capture"), ("author", "Author"), ("writer", "Author"), ("lead", "Author"),
         ("sme", "Author"), ("subject matter", "Author"), ("contributor", "Author"))
PREVIEW = {"fixcopy": ("Fix a Copy", "fixes drafts into dated copies"),
           "template": ("Make a .dotx template", "writes templates from a profile")}
ACCESS_FILE = "team_access.json"


def profile_of(role_text):
    """The profile a role written in the team's words means, or ''."""
    low = " " + (role_text or "").casefold() + " "
    if low.strip() in ("pm",):
        return PM
    for w, p in WORDS:
        if w in low:
            return p
    return ""


MENU = ("tools", "mywork", "efforts", "home", "deliverables", "effortfmt", "record", "reviews", "postsub", "library", "read", "compare", "requirements",
        "custqa", "structure", "shredreq", "shredacc", "assign", "prove", "crosswalk", "matrix", "setup", "setups", "storyboards", "drafts", "truth", "acronyms", "acrlist", "techedit",
        "keywords", "finalcheck", "qa", "lists", "checks", "fixcopy", "audit", "formatstd", "qpstd", "layoutstd", "profiles", "templates", "rules", "refs", "exportall", "settings", "prodstd")


def allowed(profile, step):
    """Whether a profile opens a page. Pages that are not in the menu (inside other pages) are always open."""
    if profile not in TOOLS or step in ALWAYS or step not in MENU:
        return True
    return step in TOOLS[profile]


def roles_for(step):
    """The profiles that open a page, the proposal manager first."""
    return [PM] + [p for p in PROFILES[1:] if step in TOOLS[p]]


def current(effort_rec=None, my_name="", own_role=""):
    """(profile, where it came from: 'effort', 'pm', 'own')."""
    me = (my_name or "").strip()
    if effort_rec is not None and me:
        try:
            p = profile_of(effort_rec.role_of(me))
            if p:
                return p, "effort"
            import branding as BR
            pm = (BR.proposal_manager(effort_rec, BR.identity(effort_rec)) or "").strip()
            if pm and pm.casefold() == me.casefold():
                return PM, "pm"
        except Exception:
            pass
    return (own_role if own_role in PROFILES else PM), "own"


# ------------------------------------------------------------------ Preview tools
def _path(config_dir):
    return os.path.join(config_dir, ACCESS_FILE)


def load(config_dir):
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def preview_on(config_dir, key):
    return key in (load(config_dir).get("preview_on") or [])


def set_preview(config_dir, key, on):
    d = load(config_dir)
    cur = [k for k in (d.get("preview_on") or []) if k in PREVIEW and k != key]
    if on:
        cur.append(key)
    d["preview_on"] = sorted(cur)
    os.makedirs(config_dir, exist_ok=True)
    tmp = _path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, _path(config_dir))
    return d["preview_on"]


# ------------------------------------------------------------------ "For this stage"
STAGE_TOOLS = ((("intake", "kickoff", "kick-off", "capture", "start", "rfp release", "solicitation"), ("library", "read", "requirements", "custqa")),
               (("plan", "outline", "strategy", "storyboard"), ("structure", "assign", "crosswalk", "storyboards", "truth")),
               (("draft", "author", "writ"), ("setup", "assign", "truth", "acronyms", "compare")),
               (("pink",), ("reviews", "matrix", "compare")),
               (("red",), ("reviews", "prove", "qa", "truth")),
               (("gold", "white", "final", "production", "pubs", "publish"), ("checks", "qa", "lists", "audit", "fixcopy")),
               (("submit", "submitted", "post", "debrief", "lessons"), ("postsub", "keywords", "exportall")))


def stage_tools(stage):
    """The tools suggested for a stage: its own list (stage["tools"]) or, by its name, the defaults above."""
    if isinstance(stage, dict) and stage.get("tools"):
        return [k for k in stage["tools"] if isinstance(k, str)][:6]
    name = (stage.get("name", "") if isinstance(stage, dict) else str(stage or "")).casefold()
    for words, tools in STAGE_TOOLS:
        if any(w in name for w in words):
            return list(tools)
    return []
