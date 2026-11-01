"""Issues and ideas (3.9.0): bugs, improvements and ideas about Stationkeeper's features, written by the person using
it, kept on this PC and exported as text when they choose.

Rules (the user's, 2026-10-23, carried over from the classic feedback reports):
  - No screenshots, video or attachments. Reports describe features, never document content.
  - A content guard checks every report, and the export again, against what this PC knows about the open effort and
    the team's lists: the effort's name, client and solicitation, its deliverables and drafts, the acronyms and
    definitions in its list, the master database, the author list, the custom dictionaries, file and folder names,
    and the Windows user name. A match blocks the save and shows, on this PC only, which words to take out.
  - Never in SCIF-ready, nor while an effort marked above CUI is open (secure.feedback_ok).
  - Each report carries content-free context only: version, time, the page it was written on, the last actions
    (their names, from the activity log).
Files: <data folder>\\feedback\\reports\\<time>.json, one per report (the classic app's folder, so both see them).
Export: one text-only zip (REPORT.md and reports.json) saved where the person chooses. Nothing is sent anywhere."""
import datetime, glob, json, os, re, zipfile

import diag

TYPES = ["Bug", "Improvement", "Idea"]
IMPORTANCE = ["Low", "Medium", "High"]
GENERIC = {"users", "desktop", "documents", "downloads", "onedrive", "sharepoint", "c:", "d:", "program files", "appdata",
           "local", "temp", "public", "home", "pictures", "stationkeeper", "stationkeeper data", "efforts", "projects",
           "files", "new folder", "shared documents", "sites", "volumes", "customer documents", "response setup", "exports",
           "production copies", "templates"}


class Blocked(Exception):
    """Reports are not kept here now (SCIF-ready, or an effort above CUI is open)."""


def reports_dir(data_dir=None):
    import secure
    if not secure.feedback_ok():
        raise Blocked("Issues and ideas are not kept in SCIF-ready, nor while an effort marked above CUI is open.")
    if data_dir is None:
        import app_gui
        data_dir = getattr(app_gui, "DATA_DIR", app_gui.BASE_DIR)
    d = os.path.join(data_dir, "feedback", "reports")
    os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------ the guard
def _acronymish(w):
    w = w.strip(".,;:()[]\"'")
    return len(w) >= 2 and (sum(c.isupper() for c in w) >= 2 or (any(c.isdigit() for c in w) and any(c.isalpha() for c in w))
                            or (any(c in "&/-_" for c in w) and any(c.isupper() for c in w)))


class Guard:
    """What must not go into a report, built fresh from what this PC knows. Finds are shown on this PC only."""

    def __init__(self, items=(), paths=(), common=()):
        self.common = {w.lower() for w in common}
        self.exact, self.phrases = set(), set()
        for t in items:
            self.add(t)
        for p in paths:
            self.add_path(p)
        try:
            user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if len(user) >= 3:
                self.phrases.add(user.lower())
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.exact = {e for e in self.exact if len(e) >= 2}
        self.phrases = {p for p in self.phrases if len(p) >= 4}

    def add(self, text):
        t = " ".join(str(text or "").split())
        if len(t) < 2:
            return
        words = t.split()
        if len(words) > 1:
            if len(t) >= 6:
                self.phrases.add(t.lower())
            for w in words:
                if _acronymish(w):
                    self.exact.add(w.strip(".,;:()[]\"'"))
            return
        if _acronymish(t):
            self.exact.add(t.strip(".,;:()[]\"'"))
        elif t.lower() not in self.common and len(t) >= 4:
            self.phrases.add(t.lower())

    def add_path(self, p):
        parts = [x for x in re.split(r"[\\/]+", p or "") if x]
        for i, comp in enumerate(parts):
            if comp.lower() in GENERIC:
                continue
            stem = os.path.splitext(comp)[0] if i == len(parts) - 1 else comp
            if stem.lower() in GENERIC:
                continue
            self.add(comp); self.add(stem)
            for piece in re.split(r"[_\-\s.]+", stem):
                if len(piece) >= 4 and piece.lower() not in self.common and piece.lower() not in GENERIC and not piece.isdigit():
                    self.phrases.add(piece.lower())
                elif _acronymish(piece):
                    self.exact.add(piece)

    def find(self, text):
        """[(start, end, matched)] in text."""
        hits = []
        if not text:
            return hits
        low = text.lower()
        for ph in self.phrases:
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(ph) + r"(?![a-z0-9])", low):
                hits.append((m.start(), m.end(), text[m.start():m.end()]))
        for ex in self.exact:
            for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(ex) + r"(?![A-Za-z0-9])", text):
                hits.append((m.start(), m.end(), ex))
        return sorted(set(hits))


def guard_for(host=None, config_dir=None):
    """The guard from what this PC knows now: the open effort (name, details, deliverables, drafts, its acronym list),
    the master database, the author list, the custom dictionaries."""
    items, paths, common = [], [], []
    try:
        import app_gui as A
        common = A.common_words() or []
        config_dir = config_dir or getattr(A, "CONFIG_DIR", "")
        for r in A.read_db_rows() or []:
            items.append(r[0])
            if len(r) > 2:
                items.append(r[2])
    except Exception:  # noqa: BLE001
        diag.swallowed()
    try:
        import authorlist as AL
        items += AL.load(config_dir).names()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    try:
        import customdict as CD
        for d in CD.Store(config_dir).dicts:
            items.append(d.get("name", ""))
            items += d.get("words", [])
    except Exception:  # noqa: BLE001
        diag.swallowed()
    if host is not None and getattr(host, "ws", None) is not None:
        try:
            items.append(host.effort_name)
            info = host.efforts.get(host.effort_name) or {}
            items += [str(info.get(k) or "") for k in ("client", "solicitation", "internal_no")]
            paths += [str(info.get(k) or "") for k in ("path", "volumes_dir", "customer_dir")]
            paths.append(getattr(host, "effort_path", "") or "")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:
            import effortrec as R
            import deliverables as DL
            rec = R.Record(host.ws.root)
            for d in DL.items(rec):
                items.append(d.get("name", ""))
                paths.append(d.get("file", ""))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:
            lst = host.record_page.effort_list()
            for term, row in (getattr(lst, "rows", {}) or {}).items():
                items.append(term)
                items.append((row or {}).get("Definition", ""))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        try:
            for p in getattr(host.home_page, "theme_drafts", lambda: [])():
                paths.append(p[1])
        except Exception:  # noqa: BLE001
            diag.swallowed()
    return Guard(items, paths, common)


# ------------------------------------------------------------------ reports
def context(page="", app_version=""):
    if not app_version:
        try:
            import app_gui
            app_version = app_gui.APP_VERSION
        except Exception:  # noqa: BLE001
            app_version = ""
    try:
        recent = [a.get("action") for a in diag.recent_activity(15) if a.get("action")]
    except Exception:  # noqa: BLE001
        recent = []
    return {"version": app_version, "time": datetime.datetime.now().isoformat(timespec="seconds"), "page": page,
            "recent_actions": recent}


def check(report, guard):
    """The words a report must lose before it is kept: [matched]. Empty: it may be saved."""
    found = []
    for k in ("title", "text", "feature"):
        found += [m for _a, _b, m in guard.find(str(report.get(k) or ""))]
    return sorted(set(found), key=str.casefold)


def save(report, guard, data_dir=None, path=None):
    """Keep a report (a new one, or path to replace). Raises ValueError with the words to take out."""
    t = str(report.get("type") or "")
    if t not in TYPES:
        raise ValueError("Choose Bug, Improvement or Idea.")
    if not str(report.get("title") or "").strip():
        raise ValueError("Give it a short title.")
    bad = check(report, guard)
    if bad:
        raise ValueError("Take these out first (they come from your documents or lists): " + ", ".join(bad))
    d = reports_dir(data_dir)
    body = {"type": t, "title": " ".join(report["title"].split())[:120], "feature": report.get("feature", "Other"),
            "importance": report.get("importance") if report.get("importance") in IMPORTANCE else "Medium",
            "text": str(report.get("text") or "").strip()[:8000], "context": report.get("context") or context(),
            "status": report.get("status", "Open")}
    if path is None:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = os.path.join(d, stamp + ".json")
        n = 2
        while os.path.exists(path):
            path = os.path.join(d, f"{stamp}_{n}.json"); n += 1
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(body, f, indent=1, ensure_ascii=False)
    os.replace(path + ".tmp", path)
    diag.activity("issue_saved")
    return path


def reports(data_dir=None):
    """[(path, report)], oldest first."""
    out = []
    for p in sorted(glob.glob(os.path.join(reports_dir(data_dir), "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            if isinstance(r, dict) and r.get("type"):
                out.append((p, r))
        except (OSError, ValueError):
            diag.swallowed()
    return out


def remove(path, data_dir=None):
    d = reports_dir(data_dir)
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(d):
        raise ValueError("Not a report.")
    os.remove(path)
    diag.activity("issue_removed")


def report_md(items, app_version=""):
    lines = ["# Stationkeeper issues and ideas", "",
             f"Exported {datetime.datetime.now():%Y-%m-%d %H:%M}, version {app_version}.",
             "Feature feedback only: no document text, file names, terms or names.", "",
             f"## Reports ({len(items)})", ""]
    for i, (_p, r) in enumerate(items, 1):
        c = r.get("context") or {}
        lines += [f"### {i}. [{r['type']}] {r['title']}", f"- Feature: {r.get('feature', '')}", f"- Importance: {r.get('importance', '')}",
                  f"- Status: {r.get('status', 'Open')}", f"- Written: {c.get('time', '')} (version {c.get('version', '')}, page {c.get('page', '')})",
                  f"- Last actions: {', '.join(c.get('recent_actions') or []) or 'none'}", "", (r.get("text") or "").strip(), ""]
    return "\n".join(lines) + "\n"


def export(path, guard, data_dir=None, app_version="", only=None):
    """A text-only zip of the reports (all, or the paths in only). Every report is checked again; a match stops the
    export. Returns the number exported."""
    items = [(p, r) for p, r in reports(data_dir) if only is None or p in only]
    for _p, r in items:
        bad = check(r, guard)
        if bad:
            raise ValueError(f"\"{r['title']}\" now holds words from your documents or lists: " + ", ".join(bad) + ". Edit it first.")
    if os.path.exists(path):
        raise ValueError("A file with that name is already there.")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("REPORT.md", report_md(items, app_version))
        z.writestr("reports.json", json.dumps([r for _p, r in items], indent=1, ensure_ascii=False))
    diag.activity("issues_exported", n=len(items))
    return len(items)
