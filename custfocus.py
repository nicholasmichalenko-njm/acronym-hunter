"""What the customer values (2.99.0): the evaluation factors and subfactors with their relative importance, the customer's
hot buttons (what the documents stress), and the effort details the documents state (contract type, period of
performance, NAICS, set-aside, place of performance, key personnel, clauses that matter). Captured in Assign from the
customer's own words, each with where it came from; shown on Effort Home and in the readable copy. Rules only (No AI) for
the suggestions; the person confirms every capture. Nothing leaves the PC."""
import datetime, getpass, re, uuid

IMPORTANCE = ("Significantly more important", "More important", "Approximately equal", "Less important", "Pass/fail", "Not stated")
DETAIL_LABELS = ("Contract type", "Period of performance", "NAICS", "Set-aside", "Place of performance", "Key personnel",
                 "Clause that matters", "Incumbent", "Estimated value", "Security clearance", "Other")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=600):
    return " ".join(str(v or "").split())[:n]


# ------------------------------------------------------------------ evaluation factors
def factors(rec):
    """In order: each factor followed by its subfactors."""
    fs = [f for f in rec.data.get("eval_factors", []) if isinstance(f, dict)]
    tops = [f for f in fs if not f.get("parent")]
    out = []
    for t in sorted(tops, key=lambda f: f.get("order", 0)):
        out.append(t)
        out += sorted((f for f in fs if f.get("parent") == t["id"]), key=lambda f: f.get("order", 0))
    return out + [f for f in fs if f.get("parent") and not any(t["id"] == f["parent"] for t in tops)]


def add_factor(rec, name, parent="", importance="Not stated", text="", source=None, who=None):
    name = _clean(name, 160)
    if not name:
        return ""
    fs = rec.data.setdefault("eval_factors", [])
    f = {"id": uuid.uuid4().hex[:10], "name": name, "parent": parent or "", "importance": importance if importance in IMPORTANCE else "Not stated",
         "text": _clean(text, 1200), "doc": _clean((source or {}).get("doc", ""), 200), "loc": _clean((source or {}).get("loc", ""), 80),
         "sid": (source or {}).get("sid", ""), "order": 1 + max([x.get("order", 0) for x in fs if x.get("parent", "") == (parent or "")] or [0]),
         "who": who or getpass.getuser(), "at": _now()}
    fs.append(f)
    rec.log("effort", f"Evaluation {'subfactor' if parent else 'factor'}: {name}", who=who)
    rec.save()
    return f["id"]


def remove_factor(rec, fid):
    before = len(rec.data.get("eval_factors", []))
    rec.data["eval_factors"] = [f for f in rec.data.get("eval_factors", []) if f.get("id") != fid and f.get("parent") != fid]
    rec.save()
    return len(rec.data["eval_factors"]) < before


_FACTOR = re.compile(r"\b(sub)?factor\s*(\d+(?:\.\d+)?)?\s*[:.,\-–—]?\s*(?:\()?([A-Z][A-Za-z/&,' ]{2,60}?)(?:\))?(?=[.:;,]|\s+(?:is|are|will|shall|consists|includes)\b|$)",
                     re.I)


def factor_guess(text):
    """{"name", "sub" (True for a subfactor), "number", "importance"} read from the customer's words, or None."""
    t = " ".join((text or "").split())
    m = _FACTOR.search(t)
    imp = importance_guess(t)
    if m:
        name = m.group(3).strip(" ,")
        return {"name": name, "sub": bool(m.group(1)), "number": m.group(2) or "", "importance": imp}
    m = re.search(r"\b([A-Z][A-Za-z ]{2,40}?)\s+(?:is|are)\s+(?:(?:significantly\s+)?(?:more|less)\s+important|(?:approximately\s+)?equal)\b", t)
    if m:
        return {"name": m.group(1).strip(), "sub": False, "number": "", "importance": imp}
    return None


def importance_guess(text):
    t = (text or "").lower()
    if re.search(r"significantly more important|much more important", t):
        return "Significantly more important"
    if re.search(r"\bmore important\b", t):
        return "More important"
    if re.search(r"approximately equal|equal(ly)? (in )?importan", t):
        return "Approximately equal"
    if re.search(r"\bless important\b", t):
        return "Less important"
    if re.search(r"pass/fail|acceptable/unacceptable|acceptable or unacceptable", t):
        return "Pass/fail"
    return "Not stated"


# ------------------------------------------------------------------ hot buttons
def hot_buttons(rec):
    return [h for h in rec.data.get("hot_buttons", []) if isinstance(h, dict)]


def add_hot(rec, text, quote="", source=None, who=None):
    text = _clean(text, 200)
    if not text:
        return ""
    h = {"id": uuid.uuid4().hex[:10], "text": text, "quote": _clean(quote, 1200), "doc": _clean((source or {}).get("doc", ""), 200),
         "loc": _clean((source or {}).get("loc", ""), 80), "sid": (source or {}).get("sid", ""), "who": who or getpass.getuser(), "at": _now()}
    rec.data.setdefault("hot_buttons", []).append(h)
    rec.log("effort", f"Hot button: {text}", who=who)
    rec.save()
    return h["id"]


def remove_hot(rec, hid):
    before = len(hot_buttons(rec))
    rec.data["hot_buttons"] = [h for h in hot_buttons(rec) if h.get("id") != hid]
    rec.save()
    return len(rec.data["hot_buttons"]) < before


def hot_guess(text):
    """A short phrase for what the sentence stresses: the words after 'emphasis on', 'critical', 'paramount'... or the
    sentence's first words."""
    t = " ".join((text or "").split())
    for pat in (r"(?:emphasis|focus|priority) (?:on|is) ([^.;:]{4,80})", r"([^.;:]{4,60}) (?:is|are) (?:critical|paramount|essential|of utmost importance)",
                r"(?:critical|paramount|essential) (?:that|to) ([^.;:]{4,80})"):
        m = re.search(pat, t, re.I)
        if m:
            return m.group(1).strip(" ,")
    return " ".join(t.split()[:8])


# ------------------------------------------------------------------ effort details
def detail_guess(text):
    """(label, value) of an effort detail the sentence states, or ("Other", the sentence)."""
    t = " ".join((text or "").split())
    m = re.search(r"\bNAICS(?: code)?\D{0,40}?(\d{6})\b", t, re.I)
    if m:
        return "NAICS", m.group(1)
    m = re.search(r"\b(firm[- ]fixed[- ]price|cost[- ]plus[- ][a-z- ]*fee|cost[- ]reimbursement|time[- ]and[- ]materials|"
                  r"labor[- ]hour|indefinite[- ]delivery[ ,/-]*indefinite[- ]quantity|IDIQ|BPA|FFP|CPFF|CPIF|CPAF|T&M)\b", t, re.I)
    if m and re.search(r"contract|award|order|type", t, re.I):
        return "Contract type", m.group(1)
    m = re.search(r"period of performance[^.]*?(\d+[^.]{0,80})", t, re.I)
    if m:
        return "Period of performance", m.group(1).strip()
    m = re.search(r"\b(total small business set-aside|small business set-aside|8\(a\)[^.,;]{0,30}|SDVOSB|service-disabled veteran[- ]owned[^.,;]{0,30}|"
                  r"HUBZone[^.,;]{0,20}|WOSB|women-owned[^.,;]{0,30}|full and open competition|unrestricted)\b", t, re.I)
    if m:
        return "Set-aside", m.group(1).strip()
    m = re.search(r"place of performance\W+(?:is|will be|shall be)?\s*([^.;]{3,100})", t, re.I)
    if m:
        return "Place of performance", m.group(1).strip()
    m = re.search(r"\b(CMMC[^.;]{0,40}|organizational conflicts? of interest|OCI|DFARS 252\.204-7012|FAR 52\.\d{3}-\d+)", t, re.I)
    if m:
        return "Clause that matters", m.group(1).strip()
    m = re.search(r"\b(top secret|secret|confidential)\s+(?:facility\s+)?(?:security\s+)?clearance", t, re.I)
    if m:
        return "Security clearance", m.group(0).strip()
    if re.search(r"\bkey personnel\b", t, re.I):
        m = re.search(r"key personnel\W+(?:are|include|shall include|consist of)?\s*([^.;]{3,160})", t, re.I)
        return "Key personnel", (m.group(1).strip() if m else t[:160])
    return "Other", t[:200]


def set_detail(rec, label, value, source=None, who=None):
    """An effort detail in Effort details (Edit details' own fields): one with the same label is replaced, its source
    kept beside it."""
    import branding as BR
    label, value = _clean(label, 60), _clean(value, 300)
    if not label or not value:
        return False
    cur = [dict(f) for f in BR.identity(rec).get("fields", [])]
    where = " ".join(x for x in ((source or {}).get("doc", ""), (source or {}).get("loc", "")) if x)
    row = {"label": label, "value": value + (f" ({where})" if where else "")}
    for f in cur:
        if f.get("label", "").casefold() == label.casefold():
            f.update(row)
            break
    else:
        cur.append(row)
    BR.set_identity(rec, fields=cur, who=who)
    return True
