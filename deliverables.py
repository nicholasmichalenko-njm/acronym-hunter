"""Deliverables (2.41.0): what the effort owes the customer, and where each stands.

- Suggested from the submission requirements (Attachment J-2, SF 33, Volume I...) found in the customer documents;
  the team adds each one or marks it not ours. Others are typed in.
- Each deliverable: name, kind, format, limit and rules, owner, status, notes, our working file, the customer
  form or template it is filled on (a document in the version library), and done marks per stage.
- What changed it: the requirement or page limit behind it changed in a newer customer version and is not
  reviewed yet; a newer version of its form arrived (fill the new one; the old one stays for the record).
- Page count of our Word file (as Word last saved it) against its limit.
Kept in the effort record (record.json), so the effort package carries it. Rules only (No AI); nothing leaves the PC.
"""
import datetime, os, re
import subreq as SR

KINDS = ("Volume", "Attachment", "Form", "Plan", "Presentation", "Other")
STATUSES = ("Not started", "Drafting", "In review", "Final", "Submitted")


def kind_of(name):
    n = (name or "").strip()
    if re.match(r"volume\b|.*\bvolume$", n, re.I):
        return "Volume"
    if re.match(r"(attachment|exhibit|annex|enclosure)\b", n, re.I):
        return "Attachment"
    if re.match(r"(sf|dd|standard form)\b", n, re.I) or re.search(r"representations|certifications", n, re.I):
        return "Form"
    if re.search(r"\bplan\b", n, re.I):
        return "Plan"
    if re.search(r"\b(slides|oral|presentation)\b", n, re.I):
        return "Presentation"
    return "Other"


def default_format(kind, rows=()):
    ff = next((r["value"] for r in rows if r["kind"] == "File" and r["subject"] == "File format"), "")
    if kind == "Volume":
        return "Word, sent as " + (ff or "PDF")
    if kind == "Form":
        return "Signed PDF"
    if kind == "Presentation":
        return "PowerPoint"
    return ff


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(s):
    return " ".join((s or "").split())


def items(rec):
    return rec.data.setdefault("deliverables", [])


def get(rec, did):
    return next((d for d in items(rec) if d["id"] == did), None)


def suggestions(rec, rows):
    """Deliverables the customer documents name that the team has not added or dismissed yet."""
    have = {d.get("req_key") for d in items(rec) if d.get("req_key")}
    names = {d["name"].casefold() for d in items(rec)}
    gone = set(rec.data.get("deliv_dismissed", []))
    return [r for r in rows if r["kind"] == "Deliverable" and not r.get("hidden") and r["key"] not in have
            and r["key"] not in gone and r["subject"].casefold() not in names]


def add(rec, name, kind="", req_key="", fmt="", limit="", owner="", doc_id="", form_version="", file="", notes="", who=None):
    name = _clean(name)
    if not name:
        return None
    import effortrec as ER
    d = {"id": ER._id(), "name": name, "kind": kind if kind in KINDS else kind_of(name), "req_key": req_key, "format": _clean(fmt),
         "limit": _clean(limit), "owner": _clean(owner), "status": "Not started", "doc_id": doc_id, "form_version": form_version,
         "file": file, "notes": (notes or "").strip(), "stages_done": {}, "created": _now(), "by": ER._who(who)}
    items(rec).append(d)
    rec.log("deliverable", f"Deliverable added: {name}" + (f" (owner {d['owner']})" if d["owner"] else "") +
            (" from the customer documents" if req_key else ""), ref={"deliverable": d["id"]}, who=who)
    rec.save()
    return d["id"]


def dismiss(rec, req_key, label="", who=None):
    gone = rec.data.setdefault("deliv_dismissed", [])
    if req_key not in gone:
        gone.append(req_key)
        rec.log("deliverable", f"Not ours: {label or req_key.partition(' | ')[2]}", who=who)
        rec.save()
    return True


def update(rec, did, who=None, **fields):
    d = get(rec, did)
    if d is None:
        return False
    changed = []
    for k, v in fields.items():
        if k not in ("name", "kind", "format", "limit", "owner", "status", "doc_id", "form_version", "file", "notes"):
            continue
        v = v.strip() if k in ("notes", "file") and isinstance(v, str) else _clean(v) if isinstance(v, str) else v
        if k == "status" and v not in STATUSES:
            continue
        if d.get(k) != v:
            changed.append(k)
            d[k] = v
    if "status" in changed:
        rec.log("deliverable", f"{d['name']}: {d['status']}", ref={"deliverable": did}, who=who)
    if "owner" in changed:
        rec.log("assign", f"Deliverable {d['name']} assigned to {d['owner'] or 'nobody'}", ref={"deliverable": did}, who=who)
    if "form_version" in changed:
        rec.log("deliverable", f"{d['name']}: now filled on the newest form version", ref={"deliverable": did}, who=who)
    if changed:
        rec.save()
    return bool(changed)


def remove(rec, did, who=None):
    d = get(rec, did)
    if d is None:
        return False
    items(rec).remove(d)
    rec.log("deliverable", f"Deliverable removed: {d['name']}", who=who)
    rec.save()
    return True


def mark_stage(rec, did, done=True, who=None):
    d = get(rec, did)
    if d is None:
        return False
    import effortrec as ER
    sid = rec.data["stage"]
    if done:
        d["stages_done"][sid] = f"{datetime.date.today().isoformat()} {ER._who(who)}"
        rec.log("deliverable", f"{d['name']}: done for {rec.stage()['name']}", ref={"deliverable": did}, who=who)
    else:
        d["stages_done"].pop(sid, None)
    rec.save()
    return True


def limit_row(d, rows, volumes=()):
    """The page-limit requirement that applies to a deliverable (by volume number or name), or None."""
    names = [d["name"]] + [v["name"] for v in volumes if d.get("file") and os.path.basename(d["file"]) in v.get("files", [])]
    for r in rows:
        if r["kind"] == "Page limit" and r["subject"].lower() != "proposal" and any(SR.match_volume(r["subject"], n) for n in names):
            return r
    return None


def state(d, rows=(), lib=None, volumes=(), rec=None):
    """Everything the tracker shows for one deliverable: limit, pages, over, changed, form, set_by, done_here, flags."""
    out = {"limit": d.get("limit", ""), "limit_from": "", "pages": None, "over": False, "changed": [], "form": None,
           "set_by": "", "done_here": False, "flags": []}
    byk = {r["key"]: r for r in rows}
    src = byk.get(d.get("req_key", ""))
    if src is not None:
        out["set_by"] = f"{src['doc']}, {src['version']}" if src.get("doc") else ""
        if src.get("to_review"):
            out["changed"].append(f"changed in {src['doc']}, {src['version']}")
    lr = limit_row(d, rows, volumes)
    if lr is not None:
        if not out["limit"]:
            out["limit"] = lr["value"]
            out["limit_from"] = f"{lr['doc']}, {lr['version']}" if lr.get("doc") else "typed in"
        if lr.get("to_review"):
            prev = next((h["value"] for h in reversed(lr.get("history", [])[:-1]) if h["value"]), "")
            out["changed"].append(f"page limit {('was ' + prev + ', now ') if prev else ''}{lr['value']} ({lr['doc']}, {lr['version']})")
    if d.get("file") and d["file"].lower().endswith(".docx") and os.path.isfile(d["file"]):
        out["pages"] = SR.word_pages(d["file"])
        n = SR._limit_n(out["limit"])
        if out["pages"] is not None and n:
            out["over"] = out["pages"] > n
    if d.get("doc_id") and lib is not None:
        doc = lib.doc(d["doc_id"])
        if doc and doc["versions"]:
            latest = doc["versions"][-1]
            working = next((v for v in doc["versions"] if v["id"] == d.get("form_version")), None)
            out["form"] = {"doc": doc["name"], "latest": latest["label"], "latest_id": latest["id"],
                           "working": working["label"] if working else "", "newer": bool(working) and working["id"] != latest["id"],
                           "versions": [(v["id"], v["label"], v["added"][:10], v.get("sha256", "")) for v in doc["versions"]]}
            if out["form"]["newer"]:
                out["changed"].append(f"new form version: {latest['label']} (fill it; {working['label']} stays for the record)")
    if rec is not None:
        out["done_here"] = rec.data["stage"] in d.get("stages_done", {})
    if out["over"]:
        out["flags"].append("over")
    if out["changed"]:
        out["flags"].append("changed")
    if not d.get("owner"):
        out["flags"].append("noowner")
    return out


def status_text(d, st):
    if st["over"]:
        return f"Over: {st['pages']} of {SR._limit_n(st['limit'])} pages"
    if st["changed"]:
        return "Changed: " + st["changed"][0]
    if st["pages"] is not None and SR._limit_n(st["limit"]):
        return f"{d['status']}  ({st['pages']} of {SR._limit_n(st['limit'])} pages)"
    return d["status"] + ("  (done for this stage)" if st["done_here"] else "")


def summary(rec, rows=(), lib=None, volumes=()):
    ds = items(rec)
    sts = [state(d, rows, lib, volumes, rec) for d in ds]
    return {"count": len(ds), "over": sum(1 for s in sts if s["over"]), "changed": sum(1 for s in sts if s["changed"]),
            "noowner": sum(1 for d in ds if not d.get("owner")), "suggested": len(suggestions(rec, rows)),
            "final": sum(1 for d in ds if d["status"] in ("Final", "Submitted"))}


def export_excel(path, rec, rows=(), lib=None, volumes=(), effort_name=""):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "Deliverables"
    stage_names = [s["name"] for s in rec.stages]
    head = ["Deliverable", "Kind", "Set by", "Format", "Limit and rules", "Owner", "Status", "Pages", "Changed", "Form version"] + \
           [f"Done: {n}" for n in stage_names] + ["Notes"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for d in items(rec):
        st = state(d, rows, lib, volumes, rec)
        form = st["form"]
        ws.append([d["name"], d["kind"], st["set_by"], d["format"], st["limit"], d["owner"], d["status"],
                   "" if st["pages"] is None else st["pages"], "; ".join(st["changed"]),
                   (f"{form['working'] or '-'} (newest {form['latest']})" if form else "")] +
                  [d["stages_done"].get(s["id"], "") for s in rec.stages] + [d["notes"]])
        fill = "FDE2E2" if st["over"] else "FEF3C7" if st["changed"] else None
        if fill:
            for c in ws[ws.max_row]:
                c.fill = PatternFill("solid", fgColor=fill)
    for r in suggestions(rec, rows):
        ws.append([r["subject"], kind_of(r["subject"]), f"{r['doc']}, {r['version']}", "", "", "", "Suggested, not confirmed", "", "", ""]
                  + [""] * len(stage_names) + [r["value"]])
        for c in ws[ws.max_row]:
            c.fill = PatternFill("solid", fgColor="E0F2FE")
    widths = [30, 12, 26, 24, 22, 16, 14, 8, 40, 22] + [14] * len(stage_names) + [40]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"
    if effort_name:
        wb.properties.title = f"{effort_name} deliverables"
    wb.save(path)
    return path
