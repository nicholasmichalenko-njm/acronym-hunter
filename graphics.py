"""Graphic needs (3.0.4): a concept or thing in the effort that needs a graphic, tagged where it was found (a sentence, the
words picked in it, or a note) and listed on Effort Home for the graphics and production people. A tag only: the
graphic itself is made elsewhere. Kept in the effort record (record.json), so it goes into backups and team syncs with
the rest. Nothing leaves the PC; no AI and no ML."""
import datetime, getpass, uuid

STATUS = ("Needed", "In work", "Done")
KINDS = ("", "Figure", "Diagram", "Process flow", "Org chart", "Table", "Chart", "Photo", "Icon", "Other")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=600):
    return " ".join(str(v or "").split())[:n]


def items(rec):
    """Every graphic need, open first, then by when it was tagged."""
    gs = [g for g in rec.data.get("graphics", []) if isinstance(g, dict)]
    return sorted(gs, key=lambda g: (g.get("status") == "Done", STATUS.index(g["status"]) if g.get("status") in STATUS else 0,
                                     g.get("at", "")))


def get(rec, gid):
    return next((g for g in rec.data.get("graphics", []) if g.get("id") == gid), None)


def open_count(rec):
    return sum(1 for g in items(rec) if g.get("status") != "Done")


def add(rec, concept, kind="", section="", owner="", source=None, note_id="", who=None):
    """A graphic need. source: {"doc", "loc", "text", "sid"} where it was found in Review; note_id: the note it came
    from. Returns its id ('' when there is nothing to say what the graphic is)."""
    concept = _clean(concept, 300)
    if not concept:
        return ""
    src = source or {}
    g = {"id": uuid.uuid4().hex[:10], "concept": concept, "kind": kind if kind in KINDS else _clean(kind, 40),
         "section": _clean(section, 160), "owner": _clean(owner, 120), "status": "Needed",
         "doc": _clean(src.get("doc", ""), 200), "loc": _clean(src.get("loc", ""), 120), "sid": src.get("sid", "") or "",
         "quote": _clean(src.get("text", ""), 1200), "note": note_id or "", "who": who or getpass.getuser(), "at": _now(),
         "done": ""}
    rec.data.setdefault("graphics", []).append(g)
    rec.log("graphic", f"Graphic need: {concept}" + (f" ({g['sid']})" if g["sid"] else ""), ref={"graphic": g["id"]}, who=who)
    rec.save()
    return g["id"]


def update(rec, gid, who=None, **fields):
    g = get(rec, gid)
    if g is None:
        return False
    changed = []
    for k, v in fields.items():
        if k not in ("concept", "kind", "section", "owner", "status"):
            continue
        v = _clean(v, 300)
        if (k == "concept" and not v) or (k == "status" and v not in STATUS):
            continue
        if g.get(k, "") != v:
            g[k] = v
            changed.append(k)
    if "status" in changed:
        g["done"] = _now() if g["status"] == "Done" else ""
        rec.log("graphic", f"Graphic {g['status'].lower()}: {g['concept']}", ref={"graphic": gid}, who=who)
    elif changed:
        rec.log("graphic", f"Graphic need changed: {g['concept']}", ref={"graphic": gid}, who=who)
    if changed:
        rec.save()
    return bool(changed)


def remove(rec, gid, who=None):
    g = get(rec, gid)
    if g is None:
        return False
    rec.data["graphics"] = [x for x in rec.data.get("graphics", []) if x.get("id") != gid]
    rec.log("graphic", f"Graphic need removed: {g['concept']}", who=who)
    rec.save()
    return True


def for_sentence(rec, sid):
    return [g for g in items(rec) if sid and g.get("sid") == sid]


def for_note(rec, nid):
    return [g for g in items(rec) if nid and g.get("note") == nid]


def where_text(g):
    """Where the need was tagged, in words."""
    if g.get("sid"):
        return " ".join(x for x in (g.get("doc", ""), g.get("loc", ""), f"({g['sid']})") if x)
    if g.get("note"):
        return "From a note"
    return ""


def export_excel(path, rec, effort_name=""):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Graphic needs"
    head = ["No.", "Graphic needed", "Kind", "Section", "Owner", "Status", "Found in", "Customer's words", "Tagged by", "Tagged"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for k, g in enumerate(items(rec), 1):
        ws.append([k, g["concept"], g.get("kind", ""), g.get("section", ""), g.get("owner", ""), g.get("status", ""), where_text(g),
                   g.get("quote", ""), g.get("who", ""), g.get("at", "").replace("T", " ")])
        if g.get("status") == "Done":
            for c in ws[ws.max_row]:
                c.font = Font(color="6B7280")
    for i, w in enumerate([6, 40, 14, 26, 18, 10, 34, 60, 14, 16], 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C2"
    if effort_name:
        wb.properties.title = f"{effort_name} graphic needs"
    wb.save(path)
    return path
