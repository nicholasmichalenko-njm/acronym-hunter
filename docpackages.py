"""Packages (4.25.4; claude/stationkeeper-documents-board-2026-11-12.html, step D): what a customer document is part of.
The solicitation as issued is one package; each amendment is another, in the order issued. A document is in the package
it was set to; one not set is the amendment itself when it is one, and As issued otherwise. Internal documents are in
none. The package is one optional key on the document ("package": the amendment's document id), so no saved format
changes and an older effort reads the same. Standard library only.

4.84.0 (step I2 of claude/stationkeeper-document-intake-direction-2026-11-24.md): Part of and Arrived as. A file is Part of
a package (Solicitation, Pre-RFP (RFI / Sources Sought), Discussions & FPR, or one the team names) and Arrived as a dated
release (Final RFP, Draft RFP 2, Amendment 0002, Q&A set 1 ...). Both are optional keys on each version ("part_of",
"arrived_as", "arrived_on"), set in Add documents. A document's group is the release of its first version (what brought
it); its later versions keep their own. A document with no release reads as 4.25.4 did (As issued, or the amendment it
was put in), so an older effort reads the same."""
import datetime
import re

ISSUED = "issued"
ISSUED_NAME = "As issued"
INTERNAL_NAME = "Internal"
CUSTOMER_SIDE = ("customer", "bidders", "qa")


PACKAGES = ("Solicitation", "Pre-RFP (RFI / Sources Sought)", "Discussions & FPR")
KINDS = ("RFI", "Industry Day", "Draft RFP", "Final RFP", "Amendment", "Q&A set", "Conformed copy", "Evaluation Notices",
         "FPR request", "Other customer update")
NUMBERED = ("Draft RFP", "Amendment", "Q&A set")
REL = "rel:"
_AMD = re.compile(r"(?<![a-z])(?:amend(?:ment)?|amd)[\s_.-]*(?:no\.?\s*)?(\d{1,4})(?![0-9])", re.I)
_DRAFT = re.compile(r"(?<![a-z])(?:draft(?:[\s_.-]*(?:rfp|solicitation))?|drfp)[\s_.-]*(\d{0,2})(?![0-9])", re.I)
_QA = re.compile(r"(?<![a-z])(?:q\s*&\s*a|q\s*and\s*a|questions[\s_.-]*and[\s_.-]*answers)(?:[\s_.-]*(?:set)?[\s_.-]*(\d{1,2}))?(?![0-9])", re.I)


def release_name(kind, n=None):
    """'Amendment', 2 -> 'Amendment 0002'; 'Draft RFP', 2 -> 'Draft RFP 2'; a kind with no number is its own name."""
    if kind not in NUMBERED or not n:
        return kind
    return f"Amendment {int(n):04d}" if kind == "Amendment" else f"{kind} {int(n)}"


def kind_of_name(name):
    """'Amendment 0002' -> ('Amendment', 2); 'Final RFP' -> ('Final RFP', None)."""
    for k in NUMBERED:
        m = re.fullmatch(re.escape(k) + r"\s+(\d+)", name or "")
        if m:
            return k, int(m.group(1))
    return (name, None) if name in KINDS else ("Other customer update", None) if name else ("", None)


def first_release(d):
    """(part, name, date) of the release that brought the document, or None."""
    vs = d.get("versions") or []
    v = vs[0] if vs else {}
    return (v.get("part_of", ""), v["arrived_as"], v.get("arrived_on", "")) if v.get("arrived_as") else None


def release_key(part, name):
    return f"{REL}{part}|{name}"


def release_title(part, name):
    return f"{part}: {name}" if part else name


def releases(lib):
    """[{"key", "part", "name", "date"}] every release a customer document's version arrived as, oldest first."""
    seen = {}
    for d in lib.all:
        if d.get("category", "customer") not in CUSTOMER_SIDE or d.get("withdrawn"):
            continue
        for v in d.get("versions") or []:
            if not v.get("arrived_as"):
                continue
            k = release_key(v.get("part_of", ""), v["arrived_as"])
            when = v.get("arrived_on") or (v.get("added") or "")[:10]
            if k not in seen or when < seen[k]["date"]:
                seen[k] = {"key": k, "part": v.get("part_of", ""), "name": v["arrived_as"], "date": when}
    return sorted(seen.values(), key=lambda r: (r["date"], r["part"], r["name"]))


def package_names(lib):
    """The packages offered: the three every effort has, the ones the team named, and any a release used."""
    out = list(PACKAGES)
    for p in (getattr(lib, "extra", {}) or {}).get("packages", []) or []:
        n = " ".join(str((p or {}).get("name", "")).split())
        if n and n.casefold() not in {x.casefold() for x in out}:
            out.append(n)
    for r in releases(lib):
        if r["part"] and r["part"].casefold() not in {x.casefold() for x in out}:
            out.append(r["part"])
    return out


def add_package(lib, name, number=""):
    """A package the team names (New package...). Kept in Documents' own record. Returns its name, or "" when empty."""
    name = " ".join(str(name or "").split())[:80]
    if not name:
        return ""
    if name.casefold() in {x.casefold() for x in package_names(lib)}:
        return next(x for x in package_names(lib) if x.casefold() == name.casefold())
    lib.extra.setdefault("packages", []).append({"name": name, "number": " ".join(str(number or "").split())[:60]})
    return name


def numbers(lib, solicitation=""):
    """The solicitation numbers to strip when names are matched: the effort's one value and any a package holds."""
    out = [solicitation] if solicitation and solicitation.strip() else []
    for p in (getattr(lib, "extra", {}) or {}).get("packages", []) or []:
        if (p or {}).get("number"):
            out.append(p["number"])
    return [n.strip() for n in out if n.strip()]


def next_number(lib, part, kind):
    """The next number of a numbered kind in a package: one past the highest given (an Amendment in the Solicitation
    also counts the amendments added before 4.84.0)."""
    top = 0
    for r in releases(lib):
        k, n = kind_of_name(r["name"])
        if r["part"] == part and k == kind and n:
            top = max(top, n)
    if kind == "Amendment" and part == PACKAGES[0]:
        for d in amendments(lib):
            m = re.search(r"(\d+)\s*$", str(d.get("initial") or "")) or _AMD.search(d.get("name", ""))
            if m:
                top = max(top, int(m.group(1)))
    return top + 1


def guess(lib, names):
    """(part, kind, number) for the files of one add, read from their names; the person changes any of it."""
    text = " ".join(names or [])
    low = text.casefold()
    rs = releases(lib)
    if re.search(r"(?<![a-z])(?:rfi|sources[\s_.-]*sought|industry[\s_.-]*day)(?![a-z])", low):
        part = PACKAGES[1]
    elif re.search(r"(?<![a-z])(?:fpr|final[\s_.-]*proposal[\s_.-]*revision|evaluation[\s_.-]*notices?)(?![a-z])", low):
        part = PACKAGES[2]
    else:
        part = rs[-1]["part"] if rs and rs[-1]["part"] else PACKAGES[0]
    m = _AMD.search(text)
    if m:
        return part if part != PACKAGES[1] else PACKAGES[0], "Amendment", int(m.group(1)) or next_number(lib, part, "Amendment")
    m = _DRAFT.search(text)
    if m:
        return PACKAGES[0], "Draft RFP", int(m.group(1)) if m.group(1) else next_number(lib, PACKAGES[0], "Draft RFP")
    m = _QA.search(text)
    if m:
        return part, "Q&A set", int(m.group(1)) if m.group(1) else next_number(lib, part, "Q&A set")
    if part == PACKAGES[1]:
        return part, ("Industry Day" if "industry" in low else "RFI"), None
    if part == PACKAGES[2]:
        return part, ("FPR request" if "fpr" in low or "revision" in low else "Evaluation Notices"), None
    if any(r["part"] == part for r in rs) or (part == PACKAGES[0] and amendments(lib)):
        return part, "Amendment", next_number(lib, part, "Amendment")
    return part, "Final RFP", None


def today():
    return datetime.date.today().isoformat()


def is_amendment(d):
    return d.get("category", "customer") == "customer" and str(d.get("type") or "").casefold().startswith("amend")


def _order(d):
    m = re.search(r"(\d+)\s*$", str(d.get("initial") or ""))
    vs = d.get("versions") or []
    return (int(m.group(1)) if m else 10 ** 6, vs[0].get("added", "") if vs else "", d.get("name", "").casefold())


def amendments(lib):
    """The amendments, in the order issued (by their number, then by when they came in)."""
    return sorted((d for d in lib.all if is_amendment(d) and not d.get("withdrawn")), key=_order)


def packages(lib):
    """[(key, name)]: As issued, then each amendment by its name. 4.84.0: then each release, oldest first; an amendment
    that came with a release is in that release, not a package of its own."""
    old = [(d["id"], d.get("name") or "Amendment") for d in amendments(lib) if not first_release(d)]
    return [(ISSUED, ISSUED_NAME)] + old + [(r["key"], release_title(r["part"], r["name"])) for r in releases(lib)]


def of(lib, d):
    """The package's key: "" for an Internal document."""
    if d.get("category", "customer") not in CUSTOMER_SIDE:
        return ""
    keys = [k for k, _n in packages(lib)]
    r = first_release(d)
    if r and release_key(r[0], r[1]) in keys:
        return release_key(r[0], r[1])
    if d.get("package") in keys:
        return d["package"]
    return d["id"] if d["id"] in keys else ISSUED


def date_of(lib, key):
    """The date a release arrived on, or ""."""
    return next((r["date"] for r in releases(lib) if r["key"] == key), "")


def name_of(lib, d):
    k = of(lib, d)
    return dict(packages(lib)).get(k, "") if k else ""


def set_package(lib, ids, key):
    """Put the documents in a package. An amendment stays in its own; an Internal document takes none. Returns how many
    changed. 4.84.0: a release key sets the release on the document's first version (any customer document, an
    amendment too); As issued or an older amendment's package takes the release off."""
    keys = [k for k, _n in packages(lib)]
    if key not in keys:
        return 0
    rel = next((r for r in releases(lib) if r["key"] == key), None)
    n = 0
    for i in ids or []:
        d = lib.doc(i)
        if d is None or d.get("category", "customer") not in CUSTOMER_SIDE or of(lib, d) == key:
            continue
        if is_amendment(d) and rel is None and not (first_release(d) and key == ISSUED):
            continue
        v0 = (d.get("versions") or [{}])[0]
        if rel is not None:
            v0.update(part_of=rel["part"], arrived_as=rel["name"], arrived_on=rel["date"])
            d.pop("package", None)
        else:
            for k in ("part_of", "arrived_as", "arrived_on"):
                v0.pop(k, None)
            if key == ISSUED:
                d.pop("package", None)
            else:
                d["package"] = key
        n += 1
    if n:
        lib.save()
    return n


def grouped(lib, docs):
    """[(key, name, [documents])] in the order shown: As issued, each amendment, then Internal. Empty groups are left
    out. The order inside a group is the order given, with an amendment first in its own package."""
    out = []
    for k, n in packages(lib):
        mine = [d for d in docs if of(lib, d) == k]
        mine.sort(key=lambda d: not (d["id"] == k or (k.startswith(REL) and is_amendment(d))))
        if mine:
            out.append((k, n, mine))
    rest = [d for d in docs if not of(lib, d)]
    if rest:
        out.append(("", INTERNAL_NAME, rest))
    return out


def has_groups(lib):
    """Groups show once there is an amendment: before that every customer document is As issued. 4.84.0: or once a
    document has a release."""
    return bool(amendments(lib)) or bool(releases(lib))
