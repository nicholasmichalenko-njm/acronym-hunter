"""The effort's path (3.96.0; 4.0.0: six steps, claude/stationkeeper-six-steps-plan-4.0.md): the menu is the effort's
steps with the Dashboard as the map. Each step says where it stands (done, now, next, later), what is left in a few
words, how far along it is, and the one thing to do next. Every page in a step ends with that step's next move. Numbers
only from what the effort already holds; rules only (No AI); nothing leaves the PC."""
import datetime

STEPS = (("library", "Documents", "The solicitation package: complete, current and readable"),
         ("assign", "Shred", "What every piece of the customer's text is, and its acros and abs"),
         ("matrix", "Matrix & Outline", "What we answer, and where in our structure"),
         ("setups", "Setup", "Who writes what, when and how long; the setup in Word"),
         ("drafts", "Drafts", "The team's drafts read back: where each section stands"),
         ("finalcheck", "Submit", "The last checks, then what happens after"))
NAME = {k: n for k, n, _w in STEPS}
THEN = {"library": "Shred, what every piece of the customer's text is",       # what the next step does, for the bar's button
        "assign": "Matrix & Outline, place what we answer",
        "matrix": "Setup, make the setup from the outline",
        "setups": "Drafts, read the team's drafts back",
        "drafts": "Submit, the last checks"}


def _acros(n):
    """4.0.0: the team's words for acronyms, abbreviations, units and symbols."""
    return "1 acro or ab" if n == 1 else f"{n} acros and abs"


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
    """The six steps: [{key, n, name, what, done, state, badge, progress, summary}]. state is done, now, next or later:
    the first step not done is now, the one after it next."""
    out = []
    r = f.get("reqs")
    # 1 Documents
    docs, chk, cmp_ = f["docs"], f["to_check"], f["compare"]
    left1 = chk + cmp_
    bits = []
    if chk:
        bits.append(f"{chk} to check")
    if cmp_:
        bits.append(f"{_plural(cmp_, 'change')} to review")
    out.append({"key": "library", "done": docs > 0 and not left1, "progress": 1.0 if docs and not left1 else 0.5 if docs else 0.0,
                "badge": (bits[0] if len(bits) == 1 else f"{left1} left") if bits else ("" if docs else "add files"),
                "summary": (f"{_plural(docs, 'document')} in" + ("; " + ", ".join(bits) if bits else ".")) if docs
                           else "No customer documents yet."})
    # 2 Shred
    acr = f["acronyms"] or 0
    if r:
        und = r["undecided"]
        total = r["sentences"] or 1
        bits = [f"{r['decided']} of {_plural(r['sentences'], 'piece')} sorted"]
        if acr:
            bits.append(f"{_acros(acr)} to decide")
        out.append({"key": "assign", "done": not und and not acr, "progress": 1.0 if not und and not acr else r["decided"] / total,
                    "badge": f"{und} to shred" if und else (f"{acr} acros" if acr else ""), "summary": ". ".join(bits) + ".",
                    "left": und})
    else:
        out.append({"key": "assign", "done": False, "progress": 0.0, "badge": "", "left": 0,
                    "summary": "Nothing shredded yet." + (f" {_acros(acr)} to decide." if acr else "")})
    # 3 Matrix & Outline
    if r and r["reqs"]:
        unplaced = r["reqs"] - r["placed"]
        out.append({"key": "matrix", "done": not unplaced, "progress": r["placed"] / r["reqs"],
                    "badge": f"{unplaced} to place" if unplaced else "",
                    "summary": f"{r['placed']} of {_plural(r['reqs'], 'requirement')} placed.", "unplaced": unplaced})
    else:
        out.append({"key": "matrix", "done": False, "progress": 0.0, "badge": "", "unplaced": 0,
                    "summary": "No requirements to place yet."})
    # 4 Setup
    secs = f["sections"]
    out.append({"key": "setups", "done": bool(f["made"]), "progress": 1.0 if f["made"] else 0.4 if secs else 0.0,
                "badge": "", "summary": ("Made. Make it again after changes." if f["made"] else
                                         f"{_plural(secs, 'section')} in the structure. Not made yet." if secs else "No structure yet.")})
    # 5 Drafts
    out.append({"key": "drafts", "done": bool(f["drafts_read"]), "progress": 1.0 if f["drafts_read"] else 0.0, "badge": "",
                "summary": "Drafts read back." if f["drafts_read"] else "No drafts read back yet."})
    # 6 Submit
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
        if f["compare"]:
            return {"key": k, "go": "compare", "title": f"Review the {_plural(f['compare'], 'change')} a new version made",
                    "button": "Open Changes", "then": then,
                    "why": "Each changed passage: no impact, shred it again, or ask a question."}
        t = f"Check the {_plural(f['to_check'], 'customer document')} that came in" if f["to_check"] else "Add the customer's documents"
        return {"key": k, "go": "library", "title": t, "button": "Open Documents", "then": then,
                "why": "Each document's type and version, so the shred reads the right ones."}
    if k == "assign":
        r = f.get("reqs")
        if not r:
            return {"key": k, "go": "read", "title": "Extract the customer's documents", "button": "Open Shred", "then": then,
                    "why": "Extract pulls every sentence out, ready to shred."}
        if r["undecided"]:
            return {"key": k, "go": "assign", "title": f"Shred the {_plural(r['undecided'], 'piece')} left", "button": "Open Shred",
                    "then": then, "why": "What each piece of the customer's text is and asks of you."}
        return {"key": k, "go": "acronyms", "title": f"Decide the {_acros(f['acronyms'] or 0)} left", "button": "Open Acros & Abs",
                "then": then, "why": "Each acronym, abbreviation, unit or symbol on the customer's pages: in the list with its definition, or not one."}
    if k == "matrix":
        return {"key": k, "go": "assign", "title": f"Place the {_plural(now.get('unplaced', 0), 'requirement')} left",
                "button": "Open Shred", "then": then, "why": "Each requirement in its section of the response structure."}
    if k == "setups":
        return {"key": k, "go": "setups", "title": "Make the setup from the outline", "button": "Open Setup", "then": then,
                "why": "Who writes what, when and how long, and the setup in Word for the authors."}
    if k == "drafts":
        return {"key": k, "go": "drafts", "title": "Read the drafts back", "button": "Open Drafts", "then": then,
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
