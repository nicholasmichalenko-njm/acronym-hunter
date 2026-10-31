"""Folders and file names (2.95.0): the team's effort folder tree, where each thing the app makes goes, and how it is
named, set once in Settings > Folders and file names, kept in the config folder (folder_plan.json) and carried by a
team pack.

- The tree: the effort's folders as the team keeps them on SharePoint, in order, subfolders as "Parent/Child". A name
  may use fields: {Effort} {Client} {Solicitation} {Internal} {Company}. Four folders have a job: where customer
  documents go, where the volumes are, where Response Setup documents go, and where exports go by default.
- Where things go: each output (the compliance matrix export, the effort status, the calendar...) goes to a folder of
  the tree, under a name pattern: fields in braces, the rest as typed: {Solicitation}_{Company}_Compliance_Matrix_{Date}.
  Fields: {Effort} {Client} {Solicitation} {Internal} {Company} {Date} {Time} {Version} {Person} {Stage} {Doc}
  {DocVersion} {From} {To} {Matrix}.
- Options: how dates are written, what a space becomes in a file name, the company's name, and the folder in the tree
  where the effort list and its app data sit (the effort's root by default).
- Customer files keep the names the customer gave them (copied in as they are).

A new effort gets the whole tree. An effort that exists keeps its folders: a folder of the tree appears the first time
something is saved into it; nothing is ever renamed or moved. Standard library only.
"""
import datetime, json, os, re

FILE = "folder_plan.json"
ROLES = (("customer", "Customer documents"), ("volumes", "Volumes (our Word files)"), ("setup", "Response Setup documents"),
         ("exports", "Exports (the default for anything else)"))
ROLE_NAMES = dict(ROLES)
DEFAULT_TREE = [{"path": "Customer Documents", "role": "customer"}, {"path": "Volumes", "role": "volumes"},
                {"path": "Response Setup", "role": "setup"}, {"path": "Exports", "role": "exports"}]
# key: (what it is, the folder's job it goes to by default, the name pattern, the extension or "" for a folder)
OUTPUTS = [
    ("effort_list", "The effort list (new efforts)", "", "{Effort}_Effort_List", ".xlsx"),
    ("compliance_matrix", "The compliance matrix (new efforts)", "", "{Effort}_Compliance_Matrix", ".xlsx"),
    ("matrix_export", "Compliance matrix export", "exports", "{Effort}_Compliance_Matrix_{Date}", ".xlsx"),
    ("compliance_package", "Compliance package (a folder of files)", "exports", "", ""),
    ("lm_crosswalk", "L/M crosswalk", "exports", "{Effort}_LM_Crosswalk", ".xlsx"),
    ("setup_documents", "Response Setup documents (a folder of files)", "setup", "", ""),
    ("setup_changes", "Response Setup changes", "setup", "{Matrix}_Setup_changes_{Date}_{Time}", ".docx"),
    ("effort_status", "Effort status (Word)", "exports", "{Effort}_Effort_Status_{Date}", ".docx"),
    ("effort_summary", "Effort summary (Word)", "exports", "{Effort}_Effort_Summary_{Date}", ".docx"),
    ("tasks_questions", "Tasks and questions", "exports", "{Effort}_Tasks_and_Questions_{Person}_{Date}_{Time}", ".xlsx"),
    ("calendar", "Calendar", "exports", "{Effort}_Calendar", ".xlsx"),
    ("customer_questions", "Customer questions (Word, Excel or the customer's template)", "exports",
     "{Effort}_Customer_Questions_{Date}", ".docx"),
    ("calendar_template", "Calendar template", "exports", "{Effort}_Calendar_Template", ".xlsx"),
    ("postsub", "Post-submission checklist", "exports", "{Effort}_Post-Submission_Checklist", ".xlsx"),
    ("deliverables", "Deliverables", "exports", "{Effort}_Deliverables_{Date}", ".xlsx"),
    ("graphic_needs", "Graphic needs", "exports", "{Effort}_Graphic_Needs_{Date}", ".xlsx"),
    ("submission_rules", "Submission requirements", "exports", "{Effort}_Submission_Requirements", ".xlsx"),
    ("review_packet", "Review packet", "exports", "{Effort}_{Stage}_Review_Packet_{Date}", ".docx"),
    ("redline", "Redline between two versions", "exports", "{Doc}_{From}_to_{To}_Redline", ".docx"),
    ("change_list", "Change list between two versions", "exports", "{Doc}_{From}_to_{To}_Changes", ".xlsx"),
    ("author_briefs", "Author briefs for a new version", "exports", "{Doc}_{DocVersion}_Author_Briefs", ".docx"),
    ("impact_review", "Impact review of a new version", "exports", "{Doc}_{DocVersion}_Impact", ".docx"),
    ("acronym_report", "Acronym report", "exports", "{Effort}_Acronym_Report_{Date}", ".csv"),
    ("acronym_lists", "Acronym lists (one Word file per volume, a folder)", "exports", "", ""),
    ("acronym_lists_book", "Acronym lists (one workbook)", "exports", "Acronym_Lists", ".xlsx"),
    ("keywords", "Keywords for SharePoint", "exports", "{Effort}_Keywords", ".xlsx"),
    ("qaqc_report", "QA/QC report", "exports", "{Effort}_QAQC_Report", ".xlsx"),
    ("taken_from_library", "What was taken from the library", "exports", "Taken_from_the_library", ".xlsx"),
    ("export_all", "Export all (a folder of files)", "exports", "", ""),
]
OUT = {k: (lab, role, pat, ext) for k, lab, role, pat, ext in OUTPUTS}
FIELDS = ("Effort", "Client", "Solicitation", "Internal", "Company", "Date", "Time", "Version", "Person", "Stage", "Doc",
          "DocVersion", "From", "To", "Matrix")
DATE_FORMATS = (("%Y-%m-%d", "2026-11-03"), ("%Y%m%d", "20261103"), ("%m-%d-%Y", "11-03-2026"), ("%d%b%Y", "03Nov2026"),
                ("%Y.%m.%d", "2026.11.03"))
SPACES = (("_", "Underscore (_)"), ("-", "Hyphen (-)"), (" ", "Keep the space"), ("", "Remove it"))
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PLAN = {}                                         # the plan in use (apply())


def default():
    return {"tree": [dict(t) for t in DEFAULT_TREE], "places": {}, "names": {}, "date_format": "%Y-%m-%d", "time_format": "%H%M",
            "space": "_", "company": "", "home": ""}


def _clean_path(p):
    parts = [" ".join(x.split()) for x in str(p or "").replace("\\", "/").split("/")]
    return "/".join(x for x in parts if x and x not in (".", ".."))


def load(config_dir):
    d = {}
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    out = default()
    tree = []
    for t in d.get("tree", []) if isinstance(d.get("tree"), list) else []:
        p = _clean_path(t.get("path") if isinstance(t, dict) else t)
        if p and p not in [x["path"] for x in tree]:
            tree.append({"path": p, "role": t.get("role", "") if isinstance(t, dict) and t.get("role") in ROLE_NAMES else ""})
    if tree:
        out["tree"] = tree
    for r, _n in ROLES:                                     # every job has a folder
        if not any(t["role"] == r for t in out["tree"]):
            name = next(x["path"] for x in DEFAULT_TREE if x["role"] == r)
            if any(t["path"] == name for t in out["tree"]):
                next(t for t in out["tree"] if t["path"] == name)["role"] = r
            else:
                out["tree"].append({"path": name, "role": r})
    paths = {t["path"] for t in out["tree"]}
    out["places"] = {k: _clean_path(v) for k, v in (d.get("places") or {}).items() if k in OUT and _clean_path(v) in paths | {""}}
    out["names"] = {k: str(v).strip()[:160] for k, v in (d.get("names") or {}).items() if k in OUT and str(v).strip()}
    if d.get("date_format") in dict(DATE_FORMATS):
        out["date_format"] = d["date_format"]
    if d.get("space") in dict(SPACES):
        out["space"] = d["space"]
    out["company"] = " ".join(str(d.get("company") or "").split())[:60]
    h = _clean_path(d.get("home"))
    out["home"] = h if h in paths else ""
    return out


def problems(plan):
    out = []
    for k, pat in plan.get("names", {}).items():
        bad = [f for f in re.findall(r"\{(\w+)\}", pat) if f not in FIELDS]
        if bad:
            out.append(f"{OUT[k][0]}: {', '.join('{' + b + '}' for b in bad)} is not a field")
        if _BAD.sub("", re.sub(r"\{\w+\}", "", pat)) != re.sub(r"\{\w+\}", "", pat):
            out.append(f"{OUT[k][0]}: a file name cannot hold < > : \" / \\ | ? *")
    for t in plan.get("tree", []):
        if any(_BAD.search(re.sub(r"\{\w+\}", "", x)) for x in t["path"].split("/")):
            out.append(f"Folder {t['path']}: a folder name cannot hold < > : \" \\ | ? *")
    return out


def save(config_dir, plan):
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    keep = {k: plan.get(k) for k in ("tree", "places", "names", "date_format", "space", "company", "home")}
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(keep, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return apply(config_dir)


def apply(config_dir):
    global _PLAN
    _PLAN = load(config_dir)
    return _PLAN


def current():
    return _PLAN or default()


# ------------------------------------------------------------------ names
def fill(pattern, fields, plan=None, when=None):
    """The pattern with its fields filled in ({Date} and {Time} from when, now by default); spaces become the plan's
    choice; characters Windows refuses are dropped; empty fields leave no doubled separators."""
    plan = plan or current()
    when = when or datetime.datetime.now()
    vals = {k: str(v) for k, v in (fields or {}).items() if v not in (None, "")}
    vals.setdefault("Date", when.strftime(plan.get("date_format", "%Y-%m-%d")))
    vals.setdefault("Time", when.strftime(plan.get("time_format", "%H%M")))
    if plan.get("company"):
        vals.setdefault("Company", plan["company"])
    s = re.sub(r"\{(\w+)\}", lambda m: vals.get(m.group(1), ""), pattern)
    s = _BAD.sub("", s)
    sp = plan.get("space", "_")
    s = re.sub(r"\s+", sp, s.strip()) if sp != " " else " ".join(s.split())
    s = re.sub(r"([_\-. ])[_\-. ]*\1+", r"\1", s)                # an empty field: no doubled separators
    s = re.sub(r"([_\- ]){2,}", r"\1", s).strip("_- .")
    return s or "Untitled"


def folder_path(rel, fields, plan=None):
    """A tree folder with its fields filled in, as parts for os.path.join."""
    plan = plan or current()
    out = []
    for part in rel.split("/"):
        f = re.sub(r"\{(\w+)\}", lambda m: str((fields or {}).get(m.group(1)) or (plan.get("company") if m.group(1) == "Company" else "") or ""), part)
        f = " ".join(_BAD.sub("", f).split()).strip(" .")
        if f:
            out.append(f)
    return out


def folder_of(key=None, role=None, plan=None):
    """The tree folder (relative) an output goes to, or the folder with that job."""
    plan = plan or current()
    if key is not None:
        if key in plan.get("places", {}):
            return plan["places"][key]
        role = OUT[key][1] if key in OUT else "exports"
    if not role:
        return plan.get("home", "")
    return next((t["path"] for t in plan["tree"] if t["role"] == role), "")


def name_of(key, fields, plan=None, when=None, ext=None):
    """The file name an output gets ("" for an output that is a folder)."""
    plan = plan or current()
    lab, _role, pat, e = OUT[key]
    pat = plan.get("names", {}).get(key, pat)
    if not pat:
        return ""
    return fill(pat, fields, plan, when) + (ext if ext is not None else e)


def next_version(folder, key, fields, plan=None, when=None, ext=None):
    """With {Version} in the pattern: v1, then v2... (the first number not used in the folder)."""
    plan = plan or current()
    pat = plan.get("names", {}).get(key, OUT[key][2])
    if "{Version}" not in pat:
        return name_of(key, fields, plan, when, ext)
    n = 1
    while True:
        nm = name_of(key, dict(fields or {}, Version=f"v{n}"), plan, when, ext)
        if not os.path.exists(os.path.join(folder, nm)):
            return nm
        n += 1


def preview(plan, key, fields=None):
    sample = {"Effort": "Kestrel", "Client": "USSF SSC", "Solicitation": "FA8810-26-R-0042", "Internal": "P-1123", "Person": "A. Lee",
              "Stage": "Red team", "Doc": "RFP", "DocVersion": "Amendment 2", "From": "Original", "To": "Amendment 2", "Matrix": "Kestrel_Compliance_Matrix"}
    sample.update({k: v for k, v in (fields or {}).items() if v})
    nm = name_of(key, dict(sample, Version="v1"), plan, datetime.datetime(2026, 11, 3, 14, 30))
    rel = folder_of(key, plan=plan)
    return "/".join(folder_path(rel, sample, plan) + ([nm] if nm else []))
