"""Offerings catalog (2.17.0): Sierra Space's own offerings, kept once on this PC and attached to any effort's keywords.

BD and Production add offerings here (name, other names, group, description), import a list they already keep
(CSV, Excel, Word, PDF, text), and export it to share through the approved SharePoint folder. The catalog holds
company offering names, not proposal content. Keyword suggestions mark an offering when its name or another name
appears in the documents.
"""
import csv, os, re

COLUMNS = ["Offering", "Other names", "Group", "Description"]


def _eng():
    import app_gui
    return app_gui


def path():
    return os.path.join(_eng().CONFIG_DIR, "offerings.csv")


def load():
    p = path()
    out = []
    if os.path.isfile(p):
        with open(p, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                name = " ".join((r.get("Offering") or "").split())
                if name:
                    out.append({c: " ".join((r.get(c) or "").split()) for c in COLUMNS} | {"Offering": name})
    return out


def save(items):
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in sorted(items, key=lambda x: x["Offering"].lower()):
            w.writerow({c: it.get(c, "") for c in COLUMNS})
    os.replace(p + ".tmp", p)


def find(items, name):
    k = " ".join((name or "").split()).casefold()
    return next((i for i in items if i["Offering"].casefold() == k), None)


def add(name, other="", group="", description=""):
    """'added', 'exists' or 'empty'."""
    name = " ".join((name or "").split()).strip(" .,;:")[:120]
    if not name:
        return "empty"
    items = load()
    if find(items, name):
        return "exists"
    items.append({"Offering": name, "Other names": other.strip(), "Group": group.strip(), "Description": description.strip()[:400]})
    save(items)
    return "added"


def update(name, **fields):
    items = load()
    it = find(items, name)
    if not it:
        return False
    for c, v in fields.items():
        if c in COLUMNS and v is not None:
            it[c] = " ".join(str(v).split())
    save(items)
    return True


def remove(names):
    keep = {" ".join(n.split()).casefold() for n in names}
    items = [i for i in load() if i["Offering"].casefold() not in keep]
    save(items)
    return len(items)


def import_file(file_path):
    """Add the offerings in a list someone already keeps. Our own catalog CSV keeps every column; any other list is
    read as (offering, description) pairs. Returns (added, already there)."""
    items = load()
    rows = []
    if file_path.lower().endswith(".csv"):
        with open(file_path, encoding="utf-8-sig", newline="") as f:
            head = f.readline()
        if head.strip().startswith("Offering"):
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                rows = [{c: (r.get(c) or "") for c in COLUMNS} for r in csv.DictReader(f)]
    if not rows:
        rows = [{"Offering": t, "Description": d} for t, d in _eng().parse_client_list(file_path)]
    added = same = 0
    for r in rows:
        name = " ".join((r.get("Offering") or "").split())
        if not name:
            continue
        if find(items, name):
            same += 1; continue
        items.append({c: " ".join((r.get(c) or "").split()) for c in COLUMNS} | {"Offering": name})
        added += 1
    save(items)
    return added, same


def names_of(it):
    """The offering's name and its other names (separated by ; or ,)."""
    return [it["Offering"]] + [x.strip() for x in re.split(r"[;,]", it.get("Other names", "")) if x.strip()]
