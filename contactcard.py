"""Contacts with several phones, e-mails and addresses (4.12.0), built a piece at a time on Shred's capture card.

A contact keeps its single fields as before (name, title, org, email, phone, address: every reader of a contact works as
it did) and adds "multi": {"phone"|"email"|"address": [{label, value, source}]}. The first value of a list is mirrored
into the single field. A contact saved before 4.12.0 has no lists: its phone, e-mail and address read as the first value,
labelled Main, and become a list the first time the contact changes.

"field_sources": {field: [source]} says where each single value came from; a source is {doc, loc, page, text, sid}.
A filed single value (name, title, org) changes only when the person says Replace; a new pick fills a blank one.
Rules only (No AI); kept in the effort record."""

SINGLE = ("name", "title", "org")
MULTI = ("phone", "email", "address")
FIELDS = SINGLE + MULTI
LABELS = ("Office", "Mobile", "Fax", "Main", "Other")
NAMES = {"name": "Name", "title": "Title or role", "org": "Organization", "phone": "Phone", "email": "E-mail", "address": "Address"}


def _clean(s, n=400):
    return " ".join(str(s or "").split())[:n]


def _src(source):
    if not source:
        return None
    s = {k: _clean(source.get(k), 400 if k == "text" else 200) for k in ("doc", "loc", "page", "text", "sid") if source.get(k)}
    return s or None


def values(c, field):
    """The values of a list field: [{label, value, source}], reading a contact saved before the lists."""
    if c is None or field not in MULTI:
        return []
    m = c.get("multi") or {}
    if field in m:
        return [dict(v) for v in m[field] if v.get("value")]
    return [{"label": "Main", "value": c[field], "source": None}] if c.get(field) else []


def _lists(c):
    """Turn the contact's single phone, e-mail and address into lists (once)."""
    m = c.setdefault("multi", {})
    for f in MULTI:
        if f not in m:
            m[f] = [{"label": "Main", "value": c[f], "source": None}] if c.get(f) else []
    c.setdefault("field_sources", {})
    return m


def _mirror(c):
    for f in MULTI:
        lst = c["multi"].get(f) or []
        c[f] = lst[0]["value"] if lst else ""


def label_of(label):
    lab = _clean(label, 40)
    return lab or "Main"


def blank():
    """A new card's values: singles empty, lists empty."""
    return {**{f: "" for f in SINGLE}, **{f: [] for f in MULTI}, "sources": {}}


def card_of(c):
    """A filed contact as a card's values (to show and edit)."""
    if c is None:
        return blank()
    out = {f: c.get(f, "") for f in SINGLE}
    out.update({f: values(c, f) for f in MULTI})
    out["sources"] = {f: list((c.get("field_sources") or {}).get(f, [])) for f in SINGLE}
    return out


def save_card(rec, card, cid=None, replace=(), who=None):
    """File a card. card: {name, title, org: str; phone, email, address: [{label, value, source}]; sources: {field: [src]}}.
    New contact (cid None) or one filed (cid): blank singles fill, a filed single changes only when its field is in
    replace; list values add (a value already there, compared without case and spaces, is skipped; its label is kept).
    Returns the contact's id, or None when the card holds nothing."""
    lst = rec.data.setdefault("contacts", [])
    c = rec.contact(cid) if cid else None
    new = c is None
    if new:
        import effortrec as ER
        c = {"id": ER._id(), **{k: "" for k in rec.CONTACT_FIELDS}, "other": [], "sources": [], "at": ER._now(), "who": ER._who(who)}
    _lists(c)
    changed = []
    for f in SINGLE:
        v = _clean(card.get(f))
        if v and (not c.get(f) or (f in replace and c[f] != v)):
            c[f] = v
            changed.append(f)
            srcs = [s for s in (_src(x) for x in (card.get("sources") or {}).get(f, [])) if s]
            if srcs:
                c["field_sources"][f] = srcs
    for f in MULTI:
        have = {_key(v["value"]) for v in c["multi"][f]}
        for v in card.get(f) or []:
            val = _clean(v.get("value"))
            if val and _key(val) not in have:
                c["multi"][f].append({"label": label_of(v.get("label")), "value": val, "source": _src(v.get("source"))})
                have.add(_key(val))
                changed.append(f)
    _mirror(c)
    for f in SINGLE:
        for s in (card.get("sources") or {}).get(f, []):
            s = _src(s)
            if s and s.get("text") and s not in c["sources"]:
                c["sources"].append(dict(s))
    if not any(c.get(k) for k in rec.CONTACT_FIELDS) and not c.get("other"):
        return None
    if new:
        lst.append(c)
    if new or changed:
        who_ = c["name"] or c["email"] or c["title"] or "a contact"
        rec.log("customer", f"Contact {'added' if new else 'updated'}: {who_}" +
                ("" if new else f" ({', '.join(NAMES[f].lower() for f in dict.fromkeys(changed))})"), who=who)
        rec.save()
    return c["id"]


def _key(v):
    return "".join(str(v or "").split()).casefold()


def edit_value(rec, cid, field, i, value=None, label=None, who=None):
    """Change one value of a list field (its words or its label). An empty value takes it out."""
    c = rec.contact(cid)
    if c is None or field not in MULTI:
        return False
    _lists(c)
    lst = c["multi"][field]
    if not 0 <= i < len(lst):
        return False
    if value is not None and not _clean(value):
        lst.pop(i)
    else:
        if value is not None:
            lst[i]["value"] = _clean(value)
        if label is not None:
            lst[i]["label"] = label_of(label)
    _mirror(c)
    rec.log("customer", f"Contact updated: {c['name'] or c['email'] or 'a contact'} ({NAMES[field].lower()})", who=who)
    rec.save()
    return True


def set_single(rec, cid, field, value, who=None):
    """Change a single field in place (the person typed it); empty clears it."""
    c = rec.contact(cid)
    if c is None or field not in SINGLE:
        return False
    v = _clean(value)
    if c.get(field) == v:
        return False
    c[field] = v
    rec.log("customer", f"Contact updated: {c['name'] or c['email'] or 'a contact'} ({NAMES[field].lower()})", who=who)
    rec.save()
    return True


def lines(c):
    """[(field name, text)] for showing a contact: each list value with its label."""
    out = [(NAMES[f], c[f]) for f in SINGLE if c.get(f)]
    for f in MULTI:
        for v in values(c, f):
            out.append((f"{NAMES[f]} ({v['label']})", v["value"]))
    return out


def summary(c):
    """One line: the name, title and the first phone and e-mail, and how many more."""
    bits = [x for x in (c.get("name"), c.get("title")) if x]
    for f in ("phone", "email"):
        vs = values(c, f)
        if vs:
            bits.append(vs[0]["value"] + (f" (+{len(vs) - 1})" if len(vs) > 1 else ""))
    return " · ".join(bits) or "a contact"
