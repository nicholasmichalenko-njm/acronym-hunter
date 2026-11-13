"""Packages (4.25.4; claude/stationkeeper-documents-board-2026-11-12.html, step D): what a customer document is part of.
The solicitation as issued is one package; each amendment is another, in the order issued. A document is in the package
it was set to; one not set is the amendment itself when it is one, and As issued otherwise. Internal documents are in
none. The package is one optional key on the document ("package": the amendment's document id), so no saved format
changes and an older effort reads the same. Standard library only."""
import re

ISSUED = "issued"
ISSUED_NAME = "As issued"
INTERNAL_NAME = "Internal"
CUSTOMER_SIDE = ("customer", "bidders", "qa")


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
    """[(key, name)]: As issued, then each amendment by its name."""
    return [(ISSUED, ISSUED_NAME)] + [(d["id"], d.get("name") or "Amendment") for d in amendments(lib)]


def of(lib, d):
    """The package's key: "" for an Internal document."""
    if d.get("category", "customer") not in CUSTOMER_SIDE:
        return ""
    keys = [k for k, _n in packages(lib)]
    if d.get("package") in keys:
        return d["package"]
    return d["id"] if d["id"] in keys else ISSUED


def name_of(lib, d):
    k = of(lib, d)
    return dict(packages(lib)).get(k, "") if k else ""


def set_package(lib, ids, key):
    """Put the documents in a package. An amendment stays in its own; an Internal document takes none. Returns how many
    changed."""
    keys = [k for k, _n in packages(lib)]
    if key not in keys:
        return 0
    n = 0
    for i in ids or []:
        d = lib.doc(i)
        if d is None or is_amendment(d) or d.get("category", "customer") not in CUSTOMER_SIDE or of(lib, d) == key:
            continue
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
        mine.sort(key=lambda d: d["id"] != k)
        if mine:
            out.append((k, n, mine))
    rest = [d for d in docs if not of(lib, d)]
    if rest:
        out.append(("", INTERNAL_NAME, rest))
    return out


def has_groups(lib):
    """Groups show once there is an amendment: before that every customer document is As issued."""
    return bool(amendments(lib))
