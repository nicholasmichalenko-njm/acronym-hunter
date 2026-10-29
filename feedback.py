"""Feedback reports: bugs, improvements and ideas about the app's FEATURES, written as plain text.

Rules (the user's, 2026-10-23):
  - No screenshots, video or attachments. Nothing the tool processes may leave the PC.
  - Reports describe features, never document content.
  - A content guard checks every report, and every file of an export, against everything sensitive this PC knows
    (terms and definitions in the results, database, OCR fixes, client lists; file, folder and project names).
    A match blocks the save or the export. The guard runs only on this PC.

Files: feedback\\reports\\<time>.json (one per report). Export: one text-only zip the user saves where they choose.
The app never sends anything anywhere.
"""
import datetime, glob, json, os, platform, re, subprocess, sys, zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag

TYPES = ["Bug", "Improvement", "Idea"]
FEATURES = ["Scan / Scan Again", "Results table", "Preview pane", "Fix OCR", "Correct + Teach / Trainer", "Improve Reading",
            "Symbols", "Math reader", "Guide", "Client Lists", "Projects", "Knowledge Packs", "Export", "Effort List",
            "Compliance", "Speed", "Other"]
IMPORTANCE = ["Low", "Medium", "High"]
GENERIC_FOLDERS = {"users", "desktop", "documents", "downloads", "onedrive", "sharepoint", "c:", "d:", "program files",
                   "appdata", "local", "temp", "public", "home", "pictures", "acronymhunter", "acronym hunter",
                   "test_samples", "projects", "files", "new folder", "shared documents", "sites"}
_win = [None]


# ------------------------------------------------------------------ the guard
class Guard:
    """Knows what must not leave the PC. Built fresh each time from the app's current state."""

    def __init__(self, app):
        import app_gui as eng
        self.common = set(w.lower() for w in (eng.common_words() or []))
        exact, phrases = set(), set()                      # exact: case-sensitive whole tokens; phrases: any case

        def add(text):
            t = (text or "").strip()
            if len(t) < 2:
                return
            words = t.split()
            if len(words) > 1:
                if len(t) >= 6:
                    phrases.add(t.lower())
                for w in words:                            # acronym-looking words inside phrases count on their own
                    if self._acronymish(w):
                        exact.add(w.strip(".,;:()[]\"'"))
                return
            if self._acronymish(t):
                exact.add(t)
            elif t.lower() not in self.common and len(t) >= 4:
                phrases.add(t.lower())

        results = getattr(app, "results", {}) or {}
        for term, d in results.items():
            add(term)
            for defn in d.get("definitions", []) or []:
                add(defn)
            sd = d.get("selected_definition", "")
            if sd and not sd.startswith("["):
                add(sd)
            for loc in d.get("locations", []) or []:
                add(eng._file_of(loc))
        try:
            for r in eng.read_db_rows():
                add(r[0]); add(r[2])
        except Exception:
            diag.swallowed()
        try:
            for wrong, right, *_ in eng.read_ocr_fix_rows():
                add(wrong); add(right)
        except Exception:
            diag.swallowed()
        for lst in getattr(app, "client_lists", []) or []:
            add(lst.get("name", ""))
            for row in lst.get("rows", []):
                for cell in row:
                    add(cell)
        paths = list((getattr(app, "scanned_paths", {}) or {}).values())
        last = getattr(app, "last_scan", None) or {}
        paths += list(last.get("paths", []) or [])
        if last.get("folder"):
            paths.append(last["folder"])
        proj = getattr(app, "project", None)
        if proj is not None:
            add(getattr(proj, "name", ""))
            paths.append(getattr(proj, "path", "") or "")
        for p in paths:
            parts = re.split(r"[\\/]+", p or "")
            for i, comp in enumerate(parts):
                if not comp or comp.lower() in GENERIC_FOLDERS:
                    continue
                stem = os.path.splitext(comp)[0] if i == len(parts) - 1 else comp
                add(comp); add(stem)
                for piece in re.split(r"[_\-\s.]+", stem):   # Kestrel_RFP_v2 -> Kestrel, RFP
                    if len(piece) >= 4 and piece.lower() not in self.common and not piece.isdigit():
                        phrases.add(piece.lower())
                    elif self._acronymish(piece):
                        exact.add(piece)
        try:
            user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if len(user) >= 3:
                phrases.add(user.lower())
        except Exception:
            diag.swallowed()
        self.exact = {e for e in exact if len(e) >= 2}
        self.phrases = {p for p in phrases if len(p) >= 4}

    @staticmethod
    def _acronymish(w):
        w = w.strip(".,;:()[]\"'")
        return len(w) >= 2 and (sum(c.isupper() for c in w) >= 2 or any(c.isdigit() for c in w) and any(c.isalpha() for c in w)
                                or any(c in "&/-_" for c in w) and any(c.isupper() for c in w))

    def find(self, text):
        """Matches of sensitive items in text: list of (start, end, item). Never stored or shown outside this PC."""
        hits = []
        if not text:
            return hits
        low = text.lower()
        for ph in self.phrases:
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(ph) + r"(?![a-z0-9])", low):
                hits.append((m.start(), m.end(), ph))
        for ex in self.exact:
            for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(ex) + r"(?![A-Za-z0-9])", text):
                hits.append((m.start(), m.end(), ex))
        hits.sort()
        return hits


# ------------------------------------------------------------------ storage
def feedback_dir():
    import app_gui as eng
    d = os.path.join(getattr(eng, "DATA_DIR", eng.BASE_DIR), "feedback", "reports")
    os.makedirs(d, exist_ok=True)
    return d


def context():
    """Content-free context attached to each report."""
    import app_gui as eng
    return {"version": eng.APP_VERSION, "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "recent_actions": [a.get("action") for a in diag.recent_activity(20)],
            "issues_logged_this_session": diag.issues_this_session()}


def system_info():
    import app_gui as eng
    info = {"version": eng.APP_VERSION, "frozen": bool(getattr(sys, "frozen", False)),
            "windows": platform.platform(terse=True), "python": platform.python_version(),
            "ocr_engine": getattr(eng, "OCR_BACKEND", "?"),
            "doctr": bool(getattr(eng, "doctr_active", lambda: False)()) if callable(getattr(eng, "doctr_active", None)) else None,
            "advanced_mode": None}
    try:
        settings = eng.load_ocr_settings() if hasattr(eng, "load_ocr_settings") else {}
        info["ocr_settings"] = {k: v for k, v in (settings or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    except Exception:
        diag.swallowed()
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True,
                             text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        info["gpu"] = [l.strip() for l in out.stdout.splitlines() if l.strip()][:2]
    except Exception:
        info["gpu"] = []
    try:
        st = open(os.path.join(eng.LOG_DIR, "selftest.txt"), encoding="utf-8").read()
        info["last_selftest"] = "OK" if "SELFTEST OK" in st else ("FAILED" if "SELFTEST FAILED" in st else "unknown")
    except Exception:
        info["last_selftest"] = "not run"
    return info


def list_reports():
    out = []
    for p in sorted(glob.glob(os.path.join(feedback_dir(), "*.json"))):
        try:
            out.append((p, json.load(open(p, encoding="utf-8"))))
        except Exception:
            diag.swallowed()
    return out


# ------------------------------------------------------------------ export
def build_report_md(reports):
    import app_gui as eng
    lines = [f"# Stationkeeper feedback export", "",
             f"Exported {datetime.datetime.now():%Y-%m-%d %H:%M}, app version {eng.APP_VERSION}.",
             "Feature feedback and content-free diagnostics only: no file names, document text or found terms.", "",
             f"## Reports ({len(reports)})", ""]
    for i, (_p, r) in enumerate(reports, 1):
        lines += [f"### {i}. [{r['type']}] {r['title']}", f"- Feature: {r['feature']}", f"- Importance: {r['importance']}",
                  f"- Written: {r['context'].get('time', '')} (version {r['context'].get('version', '')})",
                  f"- Recent actions: {', '.join(r['context'].get('recent_actions', [])) or 'none'}", "", r["text"].strip(), ""]
    ev = []
    for p in sorted(glob.glob(os.path.join(eng.LOG_DIR, "events.jsonl*")), reverse=True):
        try:
            ev += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        except Exception:
            diag.swallowed()
    lines += ["## Diagnostics summary", ""]
    if not ev:
        lines.append("No errors or warnings logged.")
    else:
        groups = {}
        for e in ev:
            k = (e.get("level"), e.get("area"), e.get("msg"), e.get("type"), (e.get("where") or [""])[0])
            g = groups.setdefault(k, {"count": 0, "first": e.get("time"), "last": e.get("time"), "versions": set(), "where": e.get("where")})
            g["count"] = max(g["count"] + (0 if e.get("repeats") else 1), e.get("repeats") or 0)
            g["last"] = max(g["last"] or "", e.get("time") or "")
            g["first"] = min(g["first"] or "", e.get("time") or "")
            g["versions"].add(e.get("version"))
        lines += ["| Level | Area | Message | Error type | Count | First | Last | Versions |", "|---|---|---|---|---|---|---|---|"]
        for (lvl, area, msg, typ, _w), g in sorted(groups.items(), key=lambda kv: -kv[1]["count"]):
            lines.append(f"| {lvl} | {area} | {msg} | {typ or ''} | {g['count']} | {g['first']} | {g['last']} | {', '.join(sorted(v for v in g['versions'] if v))} |")
        lines += ["", "Code locations for each group are in events.jsonl."]
    return "\n".join(lines) + "\n"


def export_files(reports):
    """{name in zip: text}. Text only."""
    import app_gui as eng
    files = {"REPORT.md": build_report_md(reports),
             "system.json": json.dumps(system_info(), indent=1, ensure_ascii=False),
             "reports.json": json.dumps([r for _p, r in reports], indent=1, ensure_ascii=False)}
    for name in ("events.jsonl", "activity.jsonl"):
        parts = []
        for p in sorted(glob.glob(os.path.join(eng.LOG_DIR, name + "*")), reverse=True):
            try:
                parts.append(open(p, encoding="utf-8").read())
            except Exception:
                diag.swallowed()
        files[name] = "".join(parts)
    return files


# ------------------------------------------------------------------ machine-file check
_EVENT_KEYS = {"time", "version", "level", "area", "msg", "type", "where", "repeats", "action", "ext", "w", "state"}
_RX = {"time": r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", "version": r"^[0-9A-Za-z.?\-]{1,20}$",
       "level": r"^(error|warning|crash)$", "area": r"^[a-z][a-z0-9_]{0,30}$", "action": r"^[a-z][a-z0-9_]{0,30}$",
       "type": r"^[A-Za-z_][A-Za-z0-9_. ]{0,60}$", "ext": r"^\.[a-z0-9]{1,6}$",
       "w": r"^[a-z][a-z0-9_.]{0,60}$", "state": r"^disabled$"}
_WHERE = re.compile(r"^[A-Za-z0-9_.\-]{1,60}\.py:\d{1,6}:[A-Za-z0-9_<>]{1,60}$")


def check_machine_file(name, text):
    """Logs are content-free by construction; this proves it again before export. Returns a list of problems."""
    import diag as d
    problems = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            problems.append(f"{name} line {n}: not valid JSON"); continue
        for k, v in e.items():
            if k in _RX:
                if not isinstance(v, str) or not re.match(_RX[k], v):
                    problems.append(f"{name} line {n}: unexpected {k}")
            elif k == "msg":
                if not isinstance(v, str) or len(v) > 160 or re.search(r"[\\/:]", v):
                    problems.append(f"{name} line {n}: unexpected message")
            elif k == "where":
                if not isinstance(v, list) or not all(isinstance(w, str) and _WHERE.match(w) for w in v):
                    problems.append(f"{name} line {n}: unexpected code location")
            elif k in d.COUNT_KEYS or re.match(r"^ext_[a-z0-9]{1,6}$", k) or k == "repeats":
                if not isinstance(v, int) or isinstance(v, bool):
                    problems.append(f"{name} line {n}: count {k} is not a number")
            else:
                problems.append(f"{name} line {n}: unexpected field {k}")
    return problems


# ------------------------------------------------------------------ window
def open_feedback(app):
    if _win[0] is not None and _win[0].winfo_exists():
        _win[0].deiconify(); _win[0].lift(); _win[0].focus_force(); return _win[0]
    diag.activity("feedback_opened")
    win = ctk.CTkToplevel(app); _win[0] = win
    win.title("Feedback"); win.geometry("640x620"); win.minsize(560, 520); win.transient(app); win.after(150, win.lift)
    ctk.CTkLabel(win, text="Feedback: bugs, improvements and ideas", font=("Arial", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
    ctk.CTkLabel(win, text="Describe the feature, not your documents. Never type file names, terms, definitions or text "
                           "from what you scanned: the app checks and will not save it.",
                 wraplength=600, justify="left", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16)
    form = ctk.CTkFrame(win, fg_color="transparent"); form.pack(fill="x", padx=16, pady=(10, 4))
    form.grid_columnconfigure(1, weight=1)
    type_var = tk.StringVar(value="Bug")
    ctk.CTkLabel(form, text="Type").grid(row=0, column=0, sticky="w", pady=4)
    ctk.CTkSegmentedButton(form, values=TYPES, variable=type_var).grid(row=0, column=1, sticky="w", pady=4)
    feat_var = tk.StringVar(value=FEATURES[0])
    ctk.CTkLabel(form, text="Feature").grid(row=1, column=0, sticky="w", pady=4)
    ctk.CTkComboBox(form, values=FEATURES, variable=feat_var, state="readonly", width=260).grid(row=1, column=1, sticky="w", pady=4)
    imp_var = tk.StringVar(value="Medium")
    ctk.CTkLabel(form, text="Importance").grid(row=2, column=0, sticky="w", pady=4)
    ctk.CTkSegmentedButton(form, values=IMPORTANCE, variable=imp_var).grid(row=2, column=1, sticky="w", pady=4)
    ctk.CTkLabel(form, text="Title").grid(row=3, column=0, sticky="w", pady=4, padx=(0, 10))
    e_title = ctk.CTkEntry(form, placeholder_text="Short summary, for example: Scan Again forgets the folder")
    e_title.grid(row=3, column=1, sticky="ew", pady=4)
    ctk.CTkLabel(win, text="What happened, or what you want (steps, expected vs actual, the idea):", anchor="w").pack(fill="x", padx=16, pady=(8, 2))
    box = ctk.CTkTextbox(win, height=200, wrap="word"); box.pack(fill="both", expand=True, padx=16)
    box.tag_config("leak", background="#FDE68A", foreground="#7C2D12")
    msg = ctk.CTkLabel(win, text="", anchor="w", justify="left", wraplength=600); msg.pack(fill="x", padx=16, pady=(6, 0))
    bar = ctk.CTkFrame(win, fg_color="transparent"); bar.pack(fill="x", padx=16, pady=12)

    def count_label():
        n = len(list_reports())
        exported = sum(1 for _p, r in list_reports() if r.get("exported"))
        return f"{n} report(s) saved, {n - exported} not yet exported."

    status = ctk.CTkLabel(win, text=count_label(), anchor="w", text_color=("#475569", "#94A3B8")); status.pack(fill="x", padx=16, pady=(0, 10))

    def check(text_widgets):
        g = Guard(app)
        bad = []
        box.tag_remove("leak", "1.0", "end")
        for kind, text in text_widgets:
            hits = g.find(text)
            if hits:
                bad.append(kind)
                if kind == "description":
                    for s, e, _item in hits:
                        box.tag_add("leak", f"1.0+{s}c", f"1.0+{e}c")
        return bad

    def save():
        title, text = e_title.get().strip(), box.get("1.0", "end").strip()
        if not title or not text:
            msg.configure(text="Add a title and a description.", text_color="#B91C1C"); return
        bad = check([("title", title), ("description", text)])
        if bad:
            diag.activity("feedback_blocked")
            msg.configure(text="Not saved: the highlighted words look like content from your documents, database or file names "
                               f"({' and '.join(bad)}). Describe the feature instead.", text_color="#B91C1C")
            return
        rep = {"type": type_var.get(), "feature": feat_var.get(), "importance": imp_var.get(), "title": title, "text": text,
               "context": context(), "exported": False}
        name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
        with open(os.path.join(feedback_dir(), name), "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        diag.activity("feedback_saved")
        e_title.delete(0, "end"); box.delete("1.0", "end")
        msg.configure(text="Saved on this PC. Export when you want to hand reports to Claude.", text_color="#047857")
        status.configure(text=count_label())

    ctk.CTkButton(bar, text="Save report", command=save, width=120).pack(side="left")
    ctk.CTkButton(bar, text="Export for Claude...", command=lambda: export_dialog(app, status, count_label), width=160,
                  fg_color="#0E7490").pack(side="left", padx=8)
    ctk.CTkButton(bar, text="Close", command=win.withdraw, width=80, fg_color="#475569").pack(side="right")
    win.bind("<Escape>", lambda e: win.withdraw())
    win._api = {"type": type_var, "feature": feat_var, "importance": imp_var, "title": e_title, "box": box, "save": save, "msg": msg}
    diag.register(win, "feedback")
    e_title.focus_set()
    return win


def export_dialog(app, status=None, count_label=None):
    reports = [(p, r) for p, r in list_reports() if not r.get("exported")]
    all_reports = list_reports()
    files = export_files(reports)
    g = Guard(app)
    leaks = []
    for _p, r in reports:                                    # what people wrote: the content guard
        if g.find(r.get("title", "")) or g.find(r.get("text", "")):
            leaks.append(f"report '{r.get('title', '')[:40]}'")
    for name in ("events.jsonl", "activity.jsonl"):           # what the app wrote: schema proof
        if check_machine_file(name, files[name]):
            leaks.append(name)
    if g.find(files["system.json"]):
        leaks.append("system.json")
    win = ctk.CTkToplevel(app); win.title("Export for Claude: review"); win.geometry("760x620"); win.transient(app)
    win.after(150, win.lift)
    head = (f"{len(reports)} new report(s) of {len(all_reports)}, plus content-free logs. This is everything in the zip. "
            "Read it before saving.")
    ctk.CTkLabel(win, text=head, wraplength=720, justify="left", anchor="w", font=("Arial", 13, "bold")).pack(fill="x", padx=14, pady=(12, 4))
    view = ctk.CTkTextbox(win, wrap="word", font=("Consolas", 12)); view.pack(fill="both", expand=True, padx=14, pady=4)
    for name, text in files.items():
        view.insert("end", f"===== {name} ({len(text):,} characters) =====\n{text[:20000]}\n"
                           + ("[... longer, shown in part ...]\n" if len(text) > 20000 else "") + "\n")
    view.configure(state="disabled")
    msg = ctk.CTkLabel(win, text="", anchor="w", wraplength=720, justify="left"); msg.pack(fill="x", padx=14)
    bar = ctk.CTkFrame(win, fg_color="transparent"); bar.pack(fill="x", padx=14, pady=10)

    def do_save():
        default = f"feedback_{datetime.datetime.now():%Y-%m-%d}.zip"
        start = os.path.join(os.path.expanduser("~"), "Desktop")
        path = filedialog.asksaveasfilename(parent=win, title="Save feedback zip", defaultextension=".zip",
                                            initialfile=default, initialdir=start if os.path.isdir(start) else None,
                                            filetypes=[("Zip", "*.zip")])
        if not path:
            return
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, text in files.items():
                z.writestr(name, text)
        for p, r in reports:
            r["exported"] = True
            with open(p, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=1)
        diag.activity("feedback_exported", items=len(reports))
        if status is not None and count_label is not None:
            status.configure(text=count_label())
        msg.configure(text="Saved. Hand this zip to Claude.", text_color="#047857")
        btn.configure(state="disabled")

    btn = ctk.CTkButton(bar, text="Save zip...", command=do_save, width=120)
    btn.pack(side="left")
    ctk.CTkButton(bar, text="Close", command=win.destroy, width=80, fg_color="#475569").pack(side="right")
    if leaks:
        btn.configure(state="disabled")
        msg.configure(text="Blocked: something in " + ", ".join(leaks) + " matches content from this PC. Edit or delete the "
                      "report in the feedback\\reports folder, then try again.", text_color="#B91C1C")
        diag.activity("feedback_export_blocked")
    win._api = {"files": files, "leaks": leaks, "save_btn": btn}
    diag.register(win, "feedback_export")
    return win
