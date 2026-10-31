"""What changed since I last opened it (3.1.0): when a person opens an effort, what the others did since that person last
had it open: the effort record's paper trail (tasks, questions, stages, documents, captures) and the decisions made in
Review, with who made them. The last time each person opened the effort is kept in the effort's own app data, by user
name, so it follows the effort to another PC. Nothing about the content leaves the effort; logs hold counts only."""
import datetime, getpass, json, os

FILE = "last_opened.json"
SHOW = 40                                   # events kept for the list on Effort Home


def me():
    return os.environ.get("USERNAME") or getpass.getuser()


def _norm(t):
    """'2026-10-30 14:05' or '2026-10-30T14:05' -> '2026-10-30T14:05'."""
    return (t or "").strip().replace(" ", "T")[:16]


def last_opened(root, user=None):
    try:
        with open(os.path.join(root, FILE), encoding="utf-8") as f:
            return (json.load(f) or {}).get(user or me(), "")
    except (OSError, ValueError):
        return ""


def mark_opened(root, user=None, when=None):
    p = os.path.join(root, FILE)
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    d[user or me()] = _norm(when or datetime.datetime.now().isoformat(timespec="minutes"))
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, p)
    return d[user or me()]


def changes(rec, M, after, user=None):
    """What others did after `after`: {"after", "events" (newest first: {"at", "who", "kind", "text"}), "decisions"
    ({who: n} in Review), "people" (sorted), "count"}. None when there is no earlier visit to compare with."""
    if not after:
        return None
    user = (user or me()).casefold()
    after = _norm(after)
    ev = []
    for e in (rec.data.get("timeline", []) if rec is not None else []):
        if _norm(e.get("at")) > after and (e.get("who") or "").casefold() != user:
            ev.append({"at": _norm(e.get("at")), "who": e.get("who", ""), "kind": e.get("kind", ""), "text": e.get("text", "")})
    dec = {}
    for row in (getattr(M, "history", None) or []) if M is not None else []:
        if len(row) >= 4 and _norm(str(row[0])) > after and str(row[1] or "").casefold() != user:
            dec[str(row[1])] = dec.get(str(row[1]), 0) + 1
    ev.sort(key=lambda e: e["at"], reverse=True)
    people = sorted({e["who"] for e in ev if e["who"]} | set(dec), key=str.casefold)
    return {"after": after, "events": ev[:SHOW], "more": max(0, len(ev) - SHOW), "decisions": dec, "people": people,
            "count": len(ev) + sum(dec.values())}


def on_open(root, rec, M, user=None, now=None):
    """Called as the effort opens: what changed since this person's last visit, then this visit is noted."""
    got = changes(rec, M, last_opened(root, user), user)
    try:
        mark_opened(root, user, now)
    except OSError:
        pass
    return got


def when_text(iso):
    w = datetime.datetime.fromisoformat(iso) if iso else None
    if not w:
        return ""
    return f"{w.strftime('%b')} {w.day}, {w.hour % 12 or 12}:{w.minute:02d} {'a.m.' if w.hour < 12 else 'p.m.'}"


def summary(c):
    """One line: '14 changes by A. Lee and J. Garcia since Oct 29, 4:12 p.m.' ('' when nothing changed)."""
    if not c or not c["count"]:
        return ""
    ppl = c["people"]
    if len(ppl) > 4:
        ppl = ppl[:3] + [f"{len(ppl) - 3} others"]
    who = (ppl[0] if len(ppl) == 1 else ", ".join(ppl[:-1]) + " and " + ppl[-1]) if ppl else "others"
    return f"{c['count']} change{'s' if c['count'] != 1 else ''} by {who} since {when_text(c['after'])}"
