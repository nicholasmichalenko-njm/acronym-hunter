"""Suggestions in Review (3.18.0): what each sentence most likely is, from rules you can read. Not AI: no model, no
statistics, nothing learned silently. The person asks for suggestions (Suggest), sees them on the page, and accepts,
changes or rejects each one; every accepted one stays marked until someone checks it.

Where a suggestion comes from, in order:
  1. Rules the team or this effort made, usually from a correction ("Proposals are limited to" is a requirement).
     A phrase found in the sentence (case and spacing ignored) decides; the longest phrase wins.
  2. The rules the reader already applies when it cuts each sentence out (compliance.py): who acts (the Offeror or the
     Contractor, or the Government), the verb (shall, must, will: Mandatory; should: Desired; may: Optional),
     evaluation wording, and the RFP section the sentence is in (Section L, M, C numbering or its title).
  3. No suggestion when the rules are not sure (no clear actor, Optional, a plain statement): the person decides.

Categories: L, M, SOW (a compliance requirement and its designation), ctx (support), cust (the customer's own
sentence), ignore (not used), none (a rule that says: never suggest anything for this). Nothing leaves the PC."""
import datetime, getpass, json, os, re

CATS = (("L", "L (Instructions)"), ("M", "M (Evaluation)"), ("SOW", "SOW (Work)"), ("ctx", "Support"),
        ("cust", "Customer's"), ("ignore", "Ignore"), ("none", "No suggestion"), ("I", "Customer interest (RFI)"))
CAT_NAME = dict(CATS)
FILE = "suggestion_rules.json"
_WS = re.compile(r"\s+")


def norm(text):
    return _WS.sub(" ", str(text or "")).strip().casefold()


# ------------------------------------------------------------------ rules the team or the effort made
def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return [r for r in (d.get("rules") if isinstance(d, dict) else d) or [] if isinstance(r, dict) and r.get("phrase")]
    except (OSError, ValueError):
        return []


def _save(path, rules):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": 1, "rules": rules}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def team_path(config_dir):
    return os.path.join(config_dir, FILE)


def team_rules(config_dir):
    return _load(team_path(config_dir))


def effort_rules(ws):
    return [r for r in ((ws.get("suggest_rules") if ws is not None else None) or []) if isinstance(r, dict) and r.get("phrase")]


def all_rules(config_dir, ws):
    """Effort rules first (they win over the team's), then the team's."""
    return [dict(r, scope="effort") for r in effort_rules(ws)] + [dict(r, scope="team") for r in team_rules(config_dir)]


def add_rule(config_dir, ws, phrase, cat, scope="team", why="", who=None):
    """A rule: sentences holding phrase are cat. Replaces a rule with the same phrase in the same place. Returns it."""
    phrase = " ".join(str(phrase or "").split())
    if len(phrase) < 3 or cat not in CAT_NAME:
        return None
    r = {"phrase": phrase, "cat": cat, "why": (why or "").strip(), "who": who or getpass.getuser(),
         "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    if scope == "effort" and ws is not None:
        rules = [x for x in effort_rules(ws) if norm(x["phrase"]) != norm(phrase)] + [r]
        ws.set("suggest_rules", rules)
    else:
        rules = [x for x in team_rules(config_dir) if norm(x["phrase"]) != norm(phrase)] + [r]
        _save(team_path(config_dir), rules)
    return r


def remove_rule(config_dir, ws, phrase, scope="team"):
    if scope == "effort" and ws is not None:
        before = effort_rules(ws)
        ws.set("suggest_rules", [x for x in before if norm(x["phrase"]) != norm(phrase)])
        return len(before) - len(effort_rules(ws))
    before = team_rules(config_dir)
    after = [x for x in before if norm(x["phrase"]) != norm(phrase)]
    _save(team_path(config_dir), after)
    return len(before) - len(after)


def rule_for(text, rules):
    """The rule whose phrase is in the text (the longest), or None."""
    t = norm(text)
    hits = [r for r in rules if norm(r["phrase"]) and norm(r["phrase"]) in t]
    return max(hits, key=lambda r: len(norm(r["phrase"]))) if hits else None


# ------------------------------------------------------------------ the suggestion for one sentence
def suggest(M, it, rules=(), inherited=None, rfi=False):
    """{"cat": L|M|SOW|ctx|cust|ignore|I or None, "why": text, "clear": bool, "rule": phrase or ""}. rfi (3.28.0): an RFI
    effort, where a sentence naming what the Government wants to learn is a Customer interest."""
    r = rule_for(it.get("text", ""), rules)
    if r is not None:
        cat = None if r["cat"] == "none" else r["cat"]
        return {"cat": cat, "why": f"{'this effort' if r.get('scope') == 'effort' else 'team'} rule: \"{r['phrase']}\""
                + (f" ({r['why']})" if r.get("why") else ""), "clear": cat is not None, "rule": r["phrase"]}
    if rfi:                                                    # 3.28.0: RFI efforts: the Government's interests
        import topics as TP
        ph = TP.interest(it.get("text", ""))
        if ph:
            return {"cat": "I", "why": f"an RFI asks: \"{ph}\"", "clear": True, "rule": ""}
    actor, typ, strength = it.get("actor", ""), it.get("type", ""), it.get("strength", "")
    sug, modal = it.get("suggest", ""), it.get("modal", "")
    sec = it.get("section", "")
    where = f"Section {sec}" if sec else (f"under {it.get('section_title')}" if it.get("section_title") else "")
    if typ == "Context" and not actor and not strength:        # a heading or a lead-in line, not a sentence with a verb
        return {"cat": None, "why": "a heading or a line without a verb: your call", "clear": False, "rule": ""}
    if sug == "Drop":
        if actor == "Government":
            return {"cat": "cust", "why": "the Government acts" + (f" ({modal})" if modal else "") + ": the customer's, never answered",
                    "clear": True, "rule": ""}
        return {"cat": "ignore", "why": "boilerplate or information with no one to act", "clear": False, "rule": ""}
    if typ == "Evaluation" or strength == "Evaluation":
        return {"cat": "M", "why": "evaluation wording" + (f", {where}" if where else ""), "clear": True, "rule": ""}
    if sug == "Keep" and strength in ("Mandatory", "Desired"):
        import setupdoc as SD
        lm, lwhy = SD.lm_why(M, it, inherited)
        dtype = (SD.docs_of(M).get(it.get("file", "")) or {}).get("type", "")
        if not lm and (typ == "SOW" or actor == "Contractor" or dtype in ("SOW", "PWS", "SOO")):
            lm, lwhy = "SOW", "work the contractor does"
        if not lm:
            return {"cat": None, "why": f"{strength.lower()} ({modal or 'no modal verb'}), but not clearly L, M or work: your call",
                    "clear": False, "rule": ""}
        who = actor or "the Offeror"
        why = ", ".join(x for x in (modal or strength.lower(), who, lwhy) if x)
        clear = strength == "Mandatory" and actor in ("Offeror", "Contractor") and bool(lm)
        return {"cat": "L" if lm == "L" else "M" if lm == "M" else "SOW", "why": why, "clear": clear, "rule": ""}
    if sug == "Context":
        return {"cat": "ctx", "why": "supporting text near a requirement", "clear": False, "rule": ""}
    return {"cat": None, "why": ("optional (may): your call" if strength == "Optional" else "no clear actor or verb: your call"),
            "clear": False, "rule": ""}


# ------------------------------------------------------------------ what was suggested, kept with the effort
def store(ws):
    """{sentence id: {"cat", "why", "clear", "rule", "state": shown|accepted|changed|rejected, "unchecked": bool}}: kept
    in the effort's data (the matrix workbook holds only the decisions)."""
    d = (ws.get("suggestions") if ws is not None else None) or {}
    return {k: dict(v) for k, v in d.items() if isinstance(v, dict)}


def save_store(ws, d):
    if ws is not None:
        ws.set("suggestions", d)


def category(it, rec=None):
    """The sentence's own decision as a suggestion category ('' undecided)."""
    d = it.get("decision", "")
    if d == "Keep":
        return {"L": "L", "M": "M", "C": "SOW", "SOW": "SOW", "I": "I"}.get(it.get("lm") or "", "req")
    if d == "Context":
        return "ctx"
    if d == "Customer":
        return "cust"
    if d == "Drop" and it.get("type") != "Heading":            # 3.18.1: Ignore is a decision of its own
        return "ignore"
    if rec and rec.get("cat") == "ignore" and rec.get("state") == "accepted":
        return "ignore"
    return ""


def agrees(sg_cat, cat):
    return bool(sg_cat) and (cat == sg_cat or (cat == "req" and sg_cat in ("L", "M", "SOW", "I")))


def score(items, recs):
    """Counts: suggested, agreed, changed, rejected, waiting, missed (made a requirement where nothing was suggested),
    unchecked (accepted, nobody has checked it yet), and the share right of those decided. Each suggestion is judged by
    what the sentence is now."""
    c = {"suggested": 0, "agreed": 0, "changed": 0, "rejected": 0, "waiting": 0, "missed": 0, "unchecked": 0}
    for it in items:
        rec = recs.get(it["id"])
        if rec is None:
            continue
        cat = category(it, rec)
        if rec.get("cat"):
            c["suggested"] += 1
            if rec.get("state") == "rejected":
                c["rejected"] += 1
            elif not cat:
                c["waiting"] += 1
            elif agrees(rec["cat"], cat):
                c["agreed"] += 1
            else:
                c["changed"] += 1
            if rec.get("unchecked"):
                c["unchecked"] += 1
        elif cat in ("L", "M", "SOW", "req"):
            c["missed"] += 1
    judged = c["agreed"] + c["changed"] + c["rejected"] + c["missed"]
    c["right_pct"] = round(100.0 * c["agreed"] / judged) if judged else None
    return c


def phrase_from(text, words=6):
    """A starting phrase for a rule: the words around the verb that made the call, else the first words."""
    t = " ".join(str(text or "").split())
    m = re.search(r"\b(shall|must|will|should|may|is required to|are required to|are limited to|is limited to|"
                  r"not to exceed|no more than)\b", t, re.I)
    ws = t.split()
    if m:
        before = len(t[:m.start()].split())
        start = max(0, before - 2)
        return " ".join(ws[start:start + words])
    return " ".join(ws[:words])
