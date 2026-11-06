"""The path strip (3.63.0): the moves of an effort with what is true about each, shaped by the kind of request.

Read, Requirements, Structure, Setup and Check (Sort joins in 3.64.0). Nothing is locked: every step opens its page in any
order, and a step is done when its count says so or when it is switched off for this effort. The request type sets
which steps matter and their words, never the rules. Kept in the effort record ("path"). Rules only; nothing leaves the PC.

claude/stationkeeper-sort-decisions-2026-11-05.md"""

TYPES = {
    "RFP": {"note": "Structure starts from Section L; the sections fill from the requirements.",
            "steps": {"read": "core", "reqs": "core", "structure": "core", "setup": "core", "check": "core"}},
    "RFI": {"note": "No Section L: the outline comes from the notice's questions and your own topics.",
            "steps": {"read": "core", "reqs": "core", "structure": "core", "setup": "opt", "check": "opt"},
            "words": {"reqs": "Questions"}},
    "Sources sought": {"note": "The point is fit: answer the asks with a capability statement.",
                       "steps": {"read": "core", "reqs": "core", "structure": "core", "setup": "skip", "check": "opt"},
                       "words": {"reqs": "Asks", "structure": "Response"}},
    "RFQ or task order": {"note": "Often short and driven by the PWS; the quote instructions set the structure.",
                          "steps": {"read": "core", "reqs": "core", "structure": "core", "setup": "core", "check": "core"}},
    "Draft RFP": {"note": "Understanding only: what is being bought, the gaps, and the questions for the customer.",
                  "steps": {"read": "core", "reqs": "core", "structure": "opt", "setup": "skip", "check": "skip"}},
}
TYPE_NAMES = tuple(TYPES)
STEPS = (("read", "Read", "library", "The customer's documents in the Library"),
         ("reqs", "Requirements", "assign", "Every shall, must, should and may, decided in Review"),
         ("structure", "Structure", "structure", "The response outline; every kept requirement in a section"),
         ("setup", "Setup", "setups", "Each section's lead, then the volume files"),
         ("check", "Check", "finalcheck", "Final Check on each volume before it goes"))
STATE_WORDS = {"core": "Core", "opt": "Optional", "skip": "Not needed"}


def path_of(rec):
    p = rec.data.get("path") if rec is not None else None
    p = p if isinstance(p, dict) else {}
    t = p.get("type") if p.get("type") in TYPES else "RFP"
    return {"type": t, "on": dict(p.get("on") or {})}


def set_type(rec, t, who=None):
    if t not in TYPES:
        return False
    p = rec.data.setdefault("path", {})
    if p.get("type") != t:
        p["type"] = t
        rec.log("effort", f"Request type: {t}", who=who)
        rec.save()
    return True


def set_step(rec, key, on):
    """Switch a step on or off for this effort (None goes back to the request type's default)."""
    if key not in dict((k, 1) for k, *_r in STEPS):
        return False
    p = rec.data.setdefault("path", {})
    on_map = p.setdefault("on", {})
    if on is None:
        on_map.pop(key, None)
    else:
        on_map[key] = bool(on)
    rec.save()
    return True


def _m_counts(M):
    items = [it for it in (M.items if M is not None else []) if it.get("type") != "Heading" and it.get("header") != "Yes"]
    undecided = sum(1 for it in items if not it.get("decision"))
    kept = [it for it in items if it.get("decision") == "Keep"]
    unplaced = sum(1 for it in kept if not it.get("map"))
    return len(items), undecided, unplaced


def steps(rec, lib=None, M=None, unadded=0):
    """[{key, label, page, what, state, on, done, count}] for the strip."""
    p = path_of(rec)
    t = TYPES[p["type"]]
    out = []
    n_items, undecided, unplaced = _m_counts(M)
    vols, sections, led = [], [], 0
    if M is not None:
        try:
            import outline_ops as O
            import setupdoc as SD
            vols = O.volume_heads(M)
            sections = [lab for lab in O.labels(M) if lab not in vols]
            led = sum(1 for lab in sections if SD.section_people(M, lab).get("lead"))
        except Exception:  # noqa: BLE001
            import diag
            diag.swallowed()
    last_check = next((e for e in reversed((rec.data.get("timeline") or []) if rec is not None else [])
                       if e.get("kind") == "check" and str(e.get("text", "")).startswith("Final Check")), None)
    ndocs = len(getattr(lib, "docs", []) or [])
    for key, label, page, what in STEPS:
        state = t["steps"].get(key, "core")
        on = p["on"].get(key, state != "skip")
        label = (t.get("words") or {}).get(key, label)
        if key == "read":
            count = f"{ndocs} document(s)" + (f", {unadded} in the folder not added" if unadded else "")
            done = ndocs > 0 and not unadded
        elif key == "reqs":
            count = f"{n_items} found, {undecided} to decide" if n_items else "None read yet"
            done = n_items > 0 and not undecided
        elif key == "structure":
            count = f"{len(vols)} volume(s), {unplaced} kept not in a section" if vols else "No volumes yet"
            done = bool(vols) and not unplaced
        elif key == "setup":
            count = f"{led} of {len(sections)} section(s) have a lead" if sections else "No sections yet"
            done = bool(sections) and led == len(sections)
        else:
            count = (f"Last run {last_check.get('at', '')[:10]}" if last_check else "Not run yet")
            done = bool(last_check) and " 0 fail" in str(last_check.get("text", ""))
        out.append({"key": key, "label": label, "page": page, "what": what, "state": state, "on": bool(on),
                    "done": bool(done) or not on, "count": count if on else "Not needed for this effort"})
    return out


def next_step(steps_):
    """The first step that is on and not done, or None."""
    return next((s for s in steps_ if s["on"] and not s["done"]), None)


def submission_line(rec, rows=()):
    """'Due ... · sent by ... · N copies' from the effort's own due date and the customer documents."""
    import subreq as SR
    s = SR.summary(rows or [])
    bits = []
    due = (rec.data.get("due") if rec is not None else "") or (s["due"]["value"] if s.get("due") else "")
    if due:
        bits.append("Due " + due.replace("T", " "))
    if s.get("delivery"):
        bits.append("Sent: " + s["delivery"][0]["value"])
    elif s.get("files"):
        bits.append("Files: " + s["files"][0]["value"])
    if s.get("copies"):
        bits.append("Copies: " + s["copies"][0]["value"])
    return "  ·  ".join(bits)
