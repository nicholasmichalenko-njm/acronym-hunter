"""Captures in Review (2.96.0): what a selected sentence, or the words dragged across inside it, holds, filed where the
effort keeps it. Rules only (No AI); the person confirms every capture.

- contact_guess(text): a point of contact's pieces: name, title, organization, e-mail, phone, address (what the
  sentence shows; the person fixes or completes it).
- rule_guess(text): the submission or formatting rules the sentence sets (subreq's reader): [(kind, subject, value)].
- acronym_guess(text): "Integrated Master Schedule (IMS)" or "IMS (Integrated Master Schedule)" -> (IMS, its long
  form); a bare abbreviation -> (IMS, "").
- due_guess(text): a due date, time and time zone written in the sentence -> ("YYYY-MM-DDTHH:MM", zone key) or None.
"""
import datetime, re

TITLES = ("Contracting Officer", "Contract Specialist", "Contracting Specialist", "Contracting Officer's Representative",
          "Program Manager", "Procuring Contracting Officer", "Administrative Contracting Officer", "Buyer", "Point of Contact",
          "Technical Point of Contact", "Small Business Specialist", "Program Analyst", "Contract Negotiator")
_TITLE = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(TITLES, key=len, reverse=True)) + r")\b(?:\s*\(([A-Z]{2,5})\))?", re.I)
_NAME = re.compile(r"\b(?:(?:Mr|Ms|Mrs|Dr|Capt|Maj|Lt|Col|Gen|SSgt|TSgt|MSgt)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-z'\-]+){1,2})\b")
_ORG = re.compile(r"\b((?:[A-Z][A-Za-z&]+\s+){0,5}(?:Command|Center|Agency|Office|Directorate|Division|Squadron|Wing|Group|Department|Administration|Laboratory|Institute)(?:\s+(?:of|for)\s+(?:[A-Z][A-Za-z&]+\s?){1,4})?)\b|\b([A-Z]{2,6}(?:/[A-Z]{2,6})+)\b")
_ACR_LONG_SHORT = re.compile(r"((?:[A-Za-z][\w&/\-]*\s+){1,9}?[A-Za-z][\w&/\-]*)\s*\(\s*([A-Z][A-Za-z0-9&/\-]{1,11})\s*\)")
_ACR_SHORT_LONG = re.compile(r"\b([A-Z][A-Z0-9&/\-]{1,11})\s*\(\s*([A-Za-z][^()]{3,80})\s*\)")


def contact_guess(text):
    """{"name", "title", "org", "email", "phone", "address"} found in the text ('' for each not found)."""
    import effortrec as R
    t = " ".join((text or "").split())
    out = {"name": "", "title": "", "org": "", "email": "", "phone": "", "address": ""}
    for kind, val in R.info_pieces(t):
        key = {"E-mail": "email", "Phone": "phone", "Address": "address"}.get(kind)
        if key and not out[key]:
            out[key] = val
    m = _TITLE.search(t)
    if m:
        out["title"] = next(x for x in TITLES if x.lower() == m.group(1).lower()) + (f" ({m.group(2)})" if m.group(2) else "")
    rest = _TITLE.sub(" ", t)
    for x in (out["email"], out["phone"], out["address"]):
        if x:
            rest = rest.replace(x, " ")
    skip = {"The", "Questions", "Proposals", "Offerors", "Offeror", "All", "Each", "Any", "Section", "Volume", "Attachment"}
    for m in _NAME.finditer(rest):
        cand = m.group(1)
        if cand.split()[0] in skip or _ORG.fullmatch(cand):
            continue
        out["name"] = cand
        break
    m = _ORG.search(rest)
    if m:
        out["org"] = (m.group(1) or m.group(2) or "").strip()
        if out["org"] == out["name"]:
            out["org"] = ""
    return out


def rule_guess(text):
    """[(kind, subject, value)] the submission and formatting rules the text sets."""
    import subreq as SR
    return [r for r in SR.find(text) if r[0] in ("Due", "Questions due", "Page limit", "Format", "File", "Copies", "Delivery")]


def acronym_guess(text):
    """(abbreviation, long form) from the text, or ("", "") when none is there."""
    t = " ".join((text or "").split())
    m = _ACR_LONG_SHORT.search(t)
    if m:
        short = m.group(2)
        words = m.group(1).split()
        letters = [c for c in short if c.isalpha()]
        take = max(len(letters), 1)
        for k in range(len(words), 0, -1):                  # the long form: the last words, as many as fit the letters
            cand = words[-k:]
            initials = "".join(w[0] for w in cand if w[0].isalpha()).upper()
            if initials.startswith("".join(letters).upper()[:2]) and k <= take + 3:
                long_ = " ".join(cand)
                break
        else:
            long_ = " ".join(words[-take:])
        return short, long_.strip(" ,;:")
    m = _ACR_SHORT_LONG.search(t)
    if m:
        return m.group(1), m.group(2).strip(" ,;:")
    m = re.search(r"\b([A-Z][A-Z0-9&/\-]{1,11})\b", t)
    return (m.group(1), "") if m else ("", "")


def due_guess(text, today=None):
    """("YYYY-MM-DDTHH:MM", zone key) for a due date written in the text (time 17:00 when none is written; the zone ''
    when none is written), or None."""
    import subreq as SR
    import tzones as TZ
    import effortrec as R
    t = " ".join((text or "").split())
    m = SR.DATE.search(t)
    if not m:
        return None
    d = R.parse_date(m.group(0).replace(",", ", ").replace("  ", " "))
    if d is None:
        try:
            d = datetime.datetime.strptime(re.sub(r"\s+", " ", m.group(0)), "%m/%d/%Y").date()
        except ValueError:
            return None
    hm = "17:00"
    tm = SR.TIME.search(t)
    if tm:
        s = tm.group(0).lower().replace(".", "")
        mm = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", s)
        m24 = re.match(r"(\d{2})(\d{2})\s*(?:hours|hrs)", s)
        if mm:
            h, mi = int(mm.group(1)) % 12 + (12 if mm.group(3) == "pm" else 0), int(mm.group(2) or 0)
            hm = f"{h:02d}:{mi:02d}"
        elif m24:
            hm = f"{m24.group(1)}:{m24.group(2)}"
    return f"{d.isoformat()}T{hm}", TZ.guess(t)


KEY_TITLES = ((r"\bquestions?\b.{0,40}\b(due|submitted|received|no later)", "Questions due", "Questions due"),
              (r"\bsite (visit|survey)\b", "Site visit", "Meeting"),
              (r"\bindustry day\b", "Industry day", "Meeting"),
              (r"\bpre-?proposal conference\b|\bbidders'? conference\b", "Pre-proposal conference", "Meeting"),
              (r"\boral (presentation|proposal)s?\b|\borals\b", "Orals", "Orals"),
              (r"\b(proposals?|offers?|responses?)\b.{0,60}\b(due|submitted|received|no later)", "Proposal due", "Proposal due"),
              (r"\baward\b", "Award", "Milestone"),
              (r"\bdiscussions?\b|\bnegotiations?\b", "Discussions", "Meeting"),
              (r"\bfinal proposal revisions?\b|\bfpr\b", "Final proposal revisions due", "Due"))


def key_date_guess(text):
    """2.98.0: a key date written in the text: {"date", "start" ('' when no time is written), "zone", "kind", "title"},
    or None without a date. kind is one of the calendar's kinds (Proposal due sets the effort's due date)."""
    import subreq as SR
    t = " ".join((text or "").split())
    g = due_guess(t)
    if g is None:
        return None
    day, hm = g[0].split("T")
    start = hm if SR.TIME.search(t) else ""
    title, kind = "Key date", "Milestone"
    for pat, ti, ki in KEY_TITLES:
        if re.search(pat, t, re.I):
            title, kind = ti, ki
            break
    return {"date": day, "start": start, "zone": g[1] or "", "kind": kind, "title": title}

