"""Customer information: one place, typed or captured (4.75.0; Nicholas 2026-11-24 16:00 and 16:01, in
claude/stationkeeper-shred-structure-and-customer-facts-direction-2026-11-24.md, steps S3 and S4). The facts about the
customer and the buy that a team looks up again and again, each with a hint for where it usually is. Every fact can be
typed on the Customer information page or captured in Shred (More > Customer info); a captured one keeps where it came
from. A filled fact is never replaced silently: a capture that differs returns {"ask": ...} and changes nothing until
the person says Replace. Typing on the page is the person's own change.

Kept in the effort's record as "customer_facts" ({label: {"value", "how", "by", "on", "source"}}); a fact not there
reads from the older Effort details spots of the same label (Contract type, NAICS, ...), so nothing captured before is
lost. Contacts are the record's own contacts, with a role. Form block numbers are hints only (form revisions vary).
Rules only (No AI); nothing leaves the PC. Standard library only."""
import datetime

GROUPS = (
    ("Who the customer is", (
        ("Department", ""),
        ("Agency or sub-agency", ""),
        ("Buying office", "Issued by: SF 33 block 7, SF 1449 block 9, SF 30 block 6"),
        ("Buying office address", "Issued by: SF 33 block 7, SF 1449 block 9"),
        ("Office that manages the contract", "Administered by: SF 1449 block 16, SF 30 block 7"),
        ("Paying office", "SF 1449 block 18a"),
        ("Program office or end user", ""))),
    ("What is being bought", (
        ("Solicitation number", "SF 33 block 3, SF 1449 block 5"),
        ("Solicitation type", "RFP, RFQ, RFI, IFB, BAA, CSO, white paper call"),
        ("Issue date", ""),
        ("NAICS", "With its size standard"),
        ("Set-aside", "Often SF 1449 block 10"),
        ("Contract type", ""),
        ("Period of performance", "Section F"),
        ("Place of performance", ""),
        ("Security clearance", "The level, and the DD 254"))),
    ("When and where", (
        ("Proposal due", "Date, time and time zone: SF 33 block 9, SF 1449 block 8"),
        ("Questions due", ""),
        ("Submit to", "SF 33 block 8, Section L"),
        ("Deliver to", "SF 1449 block 15"))),
)
LABELS = tuple(lab for _g, rows in GROUPS for lab, _h in rows)
HINT = {lab: h for _g, rows in GROUPS for lab, h in rows}
ROLES = ("Contracting Officer", "Contract Specialist", "Technical POC / COR", "Program Manager (customer)", "Questions go to")


def _clean(v, n=400):
    return " ".join(str(v or "").split())[:n]


def _same(a, b):
    return _clean(a).casefold() == _clean(b).casefold()


def _store(rec):
    return rec.data.setdefault("customer_facts", {})


def fact(rec, label):
    """{"value", "how", "by", "on", "source"} for one fact; an older Effort details spot of the same label reads as typed."""
    f = (rec.data.get("customer_facts") or {}).get(label)
    if f and f.get("value"):
        return dict(f)
    for x in (rec.data.get("identity") or {}).get("fields", []) or []:
        if _same(x.get("label"), label) and x.get("value"):
            return {"value": x["value"], "how": "typed", "by": "", "on": "", "source": {}}
    return {"value": "", "how": "", "by": "", "on": "", "source": {}}


def where(f):
    """How a fact says where it came from: "typed by <name>, <date>", or "<document>, page 1"."""
    if not f.get("value"):
        return ""
    if f.get("how") == "captured":
        s = f.get("source") or {}
        bits = [x for x in (s.get("doc", ""), ("page " + str(s["page"])) if s.get("page") else "", s.get("loc", "")) if x]
        return ", ".join(bits) or "captured in Shred"
    by = ", ".join(x for x in (("by " + f["by"]) if f.get("by") else "", f.get("on", "")) if x)
    return ("typed " + by).strip() if by else "typed"


def set_fact(rec, label, value, how="typed", who="", source=None, replace=None):
    """Fill a fact. Returns "set", "same" (nothing to change), "cleared", or {"ask": the fact it holds} when it is
    filled with something else and replace is None: nothing changes until the caller comes back with replace=True
    (replace=False leaves it). Typing passes replace=True."""
    label, value = _clean(label, 80), _clean(value)
    if not label:
        return "same"
    cur = fact(rec, label)
    if not value:
        if not cur["value"]:
            return "same"
        _store(rec)[label] = {"value": "", "how": "", "by": "", "on": "", "source": {}}
        rec.log("effort", f"Customer information: {label} cleared", who=who or None, save=True)
        return "cleared"
    if cur["value"] and _same(cur["value"], value):
        return "same"
    if cur["value"] and replace is None:
        return {"ask": cur}
    if cur["value"] and replace is False:
        return "same"
    src = {k: _clean((source or {}).get(k), 200) for k in ("doc", "page", "loc", "sid") if (source or {}).get(k)}
    _store(rec)[label] = {"value": value, "how": "captured" if how == "captured" else "typed", "by": _clean(who, 80),
                          "on": datetime.date.today().isoformat(), "source": src}
    rec.log("effort", f"Customer information: {label} {'captured' if how == 'captured' else 'typed'}", who=who or None, save=True)
    return "set"


def rows(rec):
    """Every fact for the page, in order: [{"group", "label", "value", "from", "hint", "how"}]."""
    out = []
    for g, items in GROUPS:
        for lab, hint in items:
            f = fact(rec, lab)
            out.append({"group": g, "label": lab, "value": f["value"], "from": where(f), "hint": hint, "how": f.get("how", "")})
    return out


def filled(rec):
    return sum(1 for r in rows(rec) if r["value"])


def guess(label, text):
    """The value a piece's words give for a fact: the older detail reading where it knows the label, else the words."""
    text = _clean(text, 600)
    try:
        import custfocus as F
        lab, val = F.detail_guess(text)
        if val and _same(lab, label):
            return _clean(val)
    except Exception:  # noqa: BLE001
        pass
    return text[:300]


# ------------------------------------------------------------------ contacts, with a role
def contacts(rec):
    """[{"id", "role", "name", "title", "org", "email", "phone", "from"}] for the page."""
    out = []
    for c in rec.data.get("contacts", []) or []:
        srcs = [s for lst in (c.get("field_sources") or {}).values() for s in lst] + list(c.get("sources") or [])
        s = srcs[0] if srcs and isinstance(srcs[0], dict) else {}
        frm = ", ".join(x for x in (s.get("doc", ""), ("page " + str(s["page"])) if s.get("page") else "") if x)
        out.append({"id": c.get("id", ""), "role": c.get("role", ""), "name": c.get("name", ""), "title": c.get("title", ""),
                    "org": c.get("org", ""), "email": c.get("email", ""), "phone": c.get("phone", ""),
                    "from": frm or (("typed by " + c["who"]) if c.get("who") else "typed")})
    return out


def set_role(rec, cid, role, who=""):
    c = rec.contact(cid)
    if c is None or c.get("role", "") == _clean(role, 60):
        return False
    c["role"] = _clean(role, 60)
    rec.log("effort", f"Customer information: {c.get('name') or 'a contact'} is {c['role'] or 'no role'}", who=who or None, save=True)
    return True


def add_contact(rec, name, role="", title="", org="", email="", phone="", who=""):
    """A contact typed on the page. Returns its id, or None with no name."""
    import contactcard as CC
    if not _clean(name):
        return None
    card = CC.blank()
    card.update({"name": _clean(name, 120), "title": _clean(title, 120), "org": _clean(org, 160)})
    card["email"] = [{"label": "Main", "value": _clean(email, 160), "source": {}}] if _clean(email) else []
    card["phone"] = [{"label": "Main", "value": _clean(phone, 60), "source": {}}] if _clean(phone) else []
    cid = CC.save_card(rec, card, who=who or None)
    if cid and role:
        set_role(rec, cid, role, who)
    return cid
