"""Meaning from context (2.13.0): when a term has several possible definitions, the words around each place it appears
suggest which one is meant. Rules only (No AI): shared words, role and document cues, and the long form spelled out
elsewhere in the same files. The app suggests; the person decides (Apply Choice, or Accept context suggestions).

  "The PM shall approve ..."             -> Program Manager       (a role word, followed by shall)
  "... per the PM plan and schedule ..."  -> Program Management    (followed by a document noun)
  "... the SOW tasks and deliverables" with "Statement of Work (SOW)" earlier in the file -> Statement of Work
"""
import re

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9&\-]*")
STOP = set("a an the of and or for to in on at by with from as is are be was were this that these those its it our "
           "their his her your we you they shall will must may should can each per all any not no".split())
ROLE = {"manager", "officer", "engineer", "lead", "director", "specialist", "representative", "administrator", "chief",
        "coordinator", "analyst", "authority", "agent", "inspector", "scientist", "architect", "supervisor", "owner",
        "contractor", "offeror", "monitor", "liaison", "technician", "planner"}
AFTER_ROLE = {"shall", "will", "must", "may", "should", "approves", "approve", "approved", "reviews", "review", "signs",
              "leads", "manages", "directs", "is", "has", "who", "coordinates", "reports", "oversees", "chairs", "and"}
BEFORE_ROLE = {"the", "our", "each", "a", "an", "deputy", "assistant", "acting", "government", "contractor"}
DOC_NOUNS = {"plan", "plans", "document", "documents", "report", "reports", "schedule", "process", "processes", "procedure",
             "procedures", "review", "reviews", "system", "approach", "matrix", "data", "standard", "standards",
             "requirements", "tasks", "deliverables", "activities", "office", "tool", "tools", "board", "database", "policy"}


def stem(w):
    w = w.lower()
    for suf in ("ments", "ment", "ings", "ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def words(text):
    return [m.group(0) for m in _WORD.finditer(text or "")]


def windows(text, term, n=6):
    """[(before words, after words)] around each whole-word occurrence of term in text (case-sensitive for acronyms)."""
    out = []
    if not text or not term:
        return out
    pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])")
    for m in pat.finditer(text):
        before = words(text[max(0, m.start() - 160):m.start()])[-n:]
        after = words(text[m.end():m.end() + 160])[:n]
        out.append((before, after))
    return out


def _def_tokens(defn):
    return [w for w in words(defn) if w.lower() not in STOP]


def score(defn, before, after, longforms=()):
    """(points, [cues]) for one definition at one place."""
    pts, cues = 0, []
    dstem = {stem(w) for w in _def_tokens(defn)}
    near = [w for w in before + after if w.lower() not in STOP]
    shared = sorted({w.lower() for w in near if stem(w) in dstem})
    if shared:
        pts += 2 * len(shared)
        cues.append("nearby: " + ", ".join(shared[:4]))
    toks = _def_tokens(defn)
    last = stem(toks[-1]) if toks else ""
    is_role = last in {stem(r) for r in ROLE}
    nxt = after[0].lower() if after else ""
    prev = before[-1].lower() if before else ""
    if is_role and (nxt in AFTER_ROLE or (prev in BEFORE_ROLE and nxt not in DOC_NOUNS)):
        pts += 2
        cues.append(f"a role: \"{prev + ' ' if prev else ''}...{' ' + nxt if nxt else ''}\"".replace(" ...", " ..."))
    if nxt in DOC_NOUNS and not is_role:
        pts += 1
        cues.append(f"followed by \"{nxt}\"")
    if nxt in DOC_NOUNS and is_role:
        pts -= 1
    for lf in longforms:
        if lf and lf.lower().strip() == defn.lower().strip():
            pts += 6
            cues.append("spelled out in the document")
            break
    return pts, cues


def suggest(defs, places, longforms=()):
    """places: {location: [(before, after), ...]}. Returns None or
    {"definition", "points", "runner_up", "places", "cues", "by_loc": {loc: [definition, [cues]]}}."""
    defs = [d for d in dict.fromkeys(defs) if d]
    if len(defs) < 2 or not places:
        return None
    total = {d: 0 for d in defs}
    cue_count = {d: {} for d in defs}
    by_loc = {}
    for loc, wins in places.items():
        loc_pts = {d: 0 for d in defs}
        loc_cues = {d: [] for d in defs}
        for before, after in wins:
            for d in defs:
                p, c = score(d, before, after, longforms)
                loc_pts[d] += p
                loc_cues[d] += c
        best = max(defs, key=lambda d: loc_pts[d])
        others = [loc_pts[d] for d in defs if d != best]
        if loc_pts[best] > 0 and loc_pts[best] > max(others):
            by_loc[loc] = [best, list(dict.fromkeys(loc_cues[best]))[:3]]
        for d in defs:
            total[d] += loc_pts[d]
            for c in loc_cues[d]:
                cue_count[d][c] = cue_count[d].get(c, 0) + 1
    if len({v[0] for v in by_loc.values()}) > 1:     # places disagree: no single answer, show it per place
        return {"definition": "", "mixed": True, "points": 0, "runner_up": 0, "places": len(by_loc), "cues": [], "by_loc": by_loc}
    ranked = sorted(defs, key=lambda d: -total[d])
    best, second = ranked[0], ranked[1]
    if total[best] <= 0 or total[best] - total[second] < 2:
        return {"definition": "", "points": total[best], "runner_up": total[second], "places": 0, "cues": [], "by_loc": by_loc} \
            if by_loc else None
    cues = [c for c, _n in sorted(cue_count[best].items(), key=lambda kv: -kv[1])][:3]
    return {"definition": best, "points": total[best], "runner_up": total[second],
            "places": sum(1 for v in by_loc.values() if v[0] == best), "cues": cues, "by_loc": by_loc}
