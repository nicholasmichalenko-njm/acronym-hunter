"""The effort's path (3.96.0; canvas "Navigation", boards 1 to 3; claude/stationkeeper-navigation-3.93.md): the menu is
the effort's five steps with the Dashboard as the map. Each step says where it stands (done, now, next, later), what is
left in a few words, how far along it is, and the one thing to do next. Every page in a step ends with that step's next
move. Numbers only from what the effort already holds; rules only (No AI); nothing leaves the PC."""
import datetime

STEPS = (("library", "Customer files", "What the customer gave us, every version"),
         ("assign", "Review", "Verify, Read, Compare, Place: every customer sentence in its place"),
         ("setups", "Setup", "The structure, its formatting, the setup in Word"),
         ("acronyms", "Write", "The drafts and what is checked in them"),
         ("finalcheck", "Submit", "The last checks, then what happens after"))
NAME = {k: n for k, n, _w in STEPS}
THEN = {"library": "Review, read and place the customer's sentences",       # what the next step does, for the bar's button
        "assign": "Setup, make the setup from what you placed",
        "setups": "Write, the drafts and what is checked in them",
        "acronyms": "Submit, the last checks"}


def _plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


def facts(ws, effort_path="", M=None, acronyms_left=None, today=None, drafts_on=True):
    """What the effort holds, as plain numbers (each part on its own: one that cannot be read is left as None)."""
    today = today or datetime.date.today()
    f = {"today": today, "docs": 0, "to_check": 0, "reqs": None, "compare": 0, "sections": 0, "made": False,
         "acronyms": acronyms_left, "drafts_read": False, "check": None, "due_date": None, "days": None, "due": "",
         "items": 0, "drafts_on": drafts_on, "acr_total": 0}
    if ws is None:
        return f
    import diag
    try:
        import effortstate as ES
        d = ES.State(ws, effort_path, M).dashboard(today)
        f["reqs"], f["due_date"], f["days"], f["due"] = d["reqs"], d["due_date"], d["days_to_due"], d["due"]
        f["to_check"] = d["to_review"]
        if f["acronyms"] is None:
            f["acronyms"] = d["acronyms"]["No definition"]
        f["acr_total"] = d["acronyms"]["total"]
    except Exception:  # noqa: BLE001
        diag.swallowed()
    try:
        import docversions as DV
        lib = DV.Library(ws.p("documents")).load()
        f["docs"] = len(lib.all)
        f["to_check"] = max(f["to_check"], len(lib.undecided()))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    try:
        import changereview as CHR
        f["compare"] = sum(n for _a, _b, n in CHR.Review(ws.root).load().undecided())
    except Exception:  # noqa: BLE001
        diag.swallowed()
    if M is not None:
        f["items"] = sum(1 for it in M.items if it.get("type") != "Heading")
        try:
            import outline_ops as O
            vols = O.volume_heads(M)
            f["sections"] = sum(1 for lab in O.labels(M) if lab not in vols)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        f["made"] = made(M)
    try:
        import effortrec as R
        import setupread as SRD
        rec = R.Record(ws.root)
        f["drafts_read"] = bool(SRD.dashboard(rec)["read"])
        last = next((e for e in reversed(rec.data.get("timeline") or [])
                     if e.get("kind") == "check" and str(e.get("text", "")).startswith("Final Check")), None)
        if last:
            f["check"] = {"at": str(last.get("at", ""))[:10], "ok": " 0 fail" in str(last.get("text", ""))}
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return f


def made(M):
    """The setup has been made at least once (Setup's Make the setup writes it in the matrix's history)."""
    return any(len(h) > 3 and h[2] == "(setup)" and str(h[3]).startswith("setup made") for h in (getattr(M, "history", None) or []))


def short_date(d):
    return d.strftime("%b %d").replace(" 0", " ") if d else ""


def steps(f):
    """The five steps: [{key, n, name, what, done, state, badge, progress, summary}]. state is done, now, next or later:
    the first step not done is now, the one after it next."""
    out = []
    r = f.get("reqs")
    # 1 Customer files
    docs, chk = f["docs"], f["to_check"]
    out.append({"key": "library", "done": docs > 0 and not chk, "progress": 1.0 if docs and not chk else 0.5 if docs else 0.0,
                "badge": f"{chk} to check" if chk else ("" if docs else "add files"),
                "summary": (f"{_plural(docs, 'file')} in" + (f"; {chk} to check" if chk else ".")) if docs else "No customer files yet."})
    # 2 Review
    if r:
        unplaced = r["reqs"] - r["placed"]
        left = r["undecided"] + unplaced
        total = r["sentences"] + r["reqs"]
        prog = (r["decided"] + r["placed"]) / total if total else 0.0
        bits = [f"{r['placed']} of {_plural(r['reqs'], 'requirement')} placed"]
        if r["undecided"]:
            bits.append(f"{_plural(r['undecided'], 'sentence')} to decide")
        if f["compare"]:
            bits.append(f"{_plural(f['compare'], 'amendment change')} to decide")
        out.append({"key": "assign", "done": not left and not f["compare"], "progress": prog if (left or f["compare"]) else 1.0,
                    "badge": f"{left + f['compare']} left" if left or f["compare"] else "", "summary": ". ".join(bits) + ".",
                    "left": left, "unplaced": unplaced})
    else:
        out.append({"key": "assign", "done": False, "progress": 0.0, "badge": "", "summary": "Nothing read yet.", "left": 0, "unplaced": 0})
    # 3 Setup
    secs = f["sections"]
    out.append({"key": "setups", "done": bool(f["made"]), "progress": 1.0 if f["made"] else 0.4 if secs else 0.0,
                "badge": "", "summary": ("Made. Make it again after changes." if f["made"] else
                                         f"{_plural(secs, 'section')} in the structure. Not made yet." if secs else "No structure yet.")})
    # 4 Write
    acr = f["acronyms"] or 0
    listed = f.get("acr_total", 0) > 0 or acr > 0
    w_done = (f["drafts_read"] or not f.get("drafts_on", True)) and listed and not acr
    drafts = ("Drafts read back." if f["drafts_read"] else "No drafts in yet.") if f.get("drafts_on", True) else ""
    out.append({"key": "acronyms", "done": w_done, "progress": 1.0 if w_done else 0.6 if f["drafts_read"] else 0.3 if listed else 0.0,
                "badge": _plural(acr, "acronym") if acr else "",
                "summary": ((f"{_plural(acr, 'acronym')} to decide. " if acr else "Acronyms decided. " if listed else
                             "No acronyms scanned yet. ") + drafts).strip()})
    # 5 Submit
    ck = f["check"]
    out.append({"key": "finalcheck", "done": bool(ck and ck["ok"]), "progress": 1.0 if ck and ck["ok"] else 0.5 if ck else 0.0,
                "badge": short_date(f["due_date"]),
                "summary": ((f"Due {f['due']}. " if f["due"] else "No due date yet. ")
                            + (f"Final Check last run {ck['at']}" + ("." if ck["ok"] else ", with things to fix.") if ck else "Final Check not run."))})
    seen_now = seen_next = False
    for n, s in enumerate(out, 1):
        s["n"], s["name"], s["what"] = n, NAME[s["key"]], dict((k, w) for k, _n, w in STEPS)[s["key"]]
        if s["done"]:
            s["state"] = "done"
        elif not seen_now:
            s["state"], seen_now = "now", True
        elif not seen_next:
            s["state"], seen_next = "next", True
        else:
            s["state"] = "later"
        if s["state"] == "done":
            s["badge"] = "done"
        elif s["state"] == "next" and s["key"] not in ("finalcheck",):
            s["badge"] = "next"
    return out


def menu_badge(s):
    """What the menu shows beside a step: done, its count, next, or its date."""
    return s["badge"]


def next_step(sts, f):
    """Your next step: {key, go, title, why, button, then}. go is the page to open."""
    now = next((s for s in sts if s["state"] == "now"), None)
    if now is None:
        return {"key": "finalcheck", "go": "finalcheck", "title": "Every step is done", "button": "Open Submit",
                "why": "The Final Check passed. Keep it current until the proposal goes.", "then": ""}
    k = now["key"]
    later = [s["name"].lower() for s in sts if s["state"] in ("next", "later")][:2]
    then = ("then: " + ", then ".join(later)) if later else ""
    if k == "library":
        t = f"Check the {_plural(f['to_check'], 'customer file')} that came in" if f["to_check"] else "Add the customer's files"
        return {"key": k, "go": "library", "title": t, "button": "Open Customer files", "then": then,
                "why": "Each file's role and version, so Review reads the right ones."}
    if k == "assign":
        if f["compare"]:
            return {"key": k, "go": "compare", "title": f"Decide the {_plural(f['compare'], 'change')} the amendment made",
                    "button": "Open Compare", "then": then,
                    "why": "Compare shows each change on the page with what it means for what you placed."}
        r = f.get("reqs")
        if not r:
            return {"key": k, "go": "read", "title": "Read the customer's files", "button": "Open Read", "then": then,
                    "why": "Read turns the files into sentences to decide and place."}
        if r["undecided"]:
            return {"key": k, "go": "assign", "title": f"Decide the {_plural(r['undecided'], 'sentence')} left", "button": "Open Review",
                    "then": then, "why": "Keep, context or drop: what each customer sentence asks of you."}
        return {"key": k, "go": "assign", "title": f"Place the {_plural(now['unplaced'], 'requirement')} left", "button": "Open Review",
                "then": then, "why": "Each requirement in its section of the response structure."}
    if k == "setups":
        return {"key": k, "go": "setups", "title": "Make the setup from what you placed", "button": "Open Setup", "then": then,
                "why": "The structure, its formatting and the setup in Word, for the authors."}
    if k == "acronyms":
        if f["acronyms"] or not f.get("acr_total"):
            if not f["acronyms"]:
                return {"key": k, "go": "acronyms", "title": "Scan the drafts for acronyms", "button": "Open Acronyms", "then": then,
                        "why": "Every term on the page, in the list with its definition, or not a term."}
            return {"key": k, "go": "acronyms", "title": f"Decide the {_plural(f['acronyms'], 'acronym')} left", "button": "Open Acronyms",
                    "then": then, "why": "Each term on the page: in the list with its definition, or not a term."}
        return {"key": k, "go": "drafts", "title": "Read the drafts back", "button": "Open Draft Status", "then": then,
                "why": "Where each section stands against its page budget and requirements."}
    return {"key": k, "go": "finalcheck", "title": "Run the Final Check", "button": "Open Submit", "then": then,
            "why": "One report: the submission rules, the page limits, the acronyms and every check."}


def bar(step_key, sts):
    """The bar at the bottom of a page in a step: (what is left on this step, the next step's button text or '', its page)."""
    s = next((x for x in sts if x["key"] == step_key), None)
    if s is None:
        return None
    left = "This step is done." if s["done"] else s["summary"]
    keys = [k for k, _n, _w in STEPS]
    i = keys.index(step_key)
    if i + 1 < len(keys):
        nk = keys[i + 1]
        return {"left": left, "button": f"Next: {THEN[step_key]}", "go": nk}
    return {"left": left, "button": "", "go": ""}
