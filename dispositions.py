"""Comment disposition for color reviews (3.39.0): every reviewer comment gets a disposition (Accept, Reject with a
reason, or Done), an owner and a due date, so recovery runs on dispositions, not scores. Comments come from two places:
a review packet read back (each reviewer comment and Word comment on a requirement's row), and Word comments in the
drafts in the Volumes folder, each placed under the heading it sits beneath. The recovery stages' gate goal is every
comment dispositioned.

Kept in the effort record (record.json, "review_comments"). A comment read twice (the same stage, file, place and
words) is kept once. Rules only (No AI); files are only read; nothing leaves the PC."""
import datetime, getpass, os, uuid, zipfile

KEY = "review_comments"
DISPOSITIONS = ("Accept", "Reject", "Done")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=8000):
    return " ".join(str(v or "").split())[:n]


def items(rec, stage=None, open_only=False):
    out = [c for c in rec.data.get(KEY, []) if isinstance(c, dict)]
    if stage:
        out = [c for c in out if c.get("stage") == stage]
    if open_only:
        out = [c for c in out if not c.get("disposition")]
    return out


def get(rec, cid):
    return next((c for c in rec.data.get(KEY, []) if c.get("id") == cid), None)


def _sig(stage, source, file, where, text):
    return "|".join(_clean(x, 400).casefold() for x in (stage, source, file, where, text))


def add(rec, stage, text, author="", where="", source="packet", file="", iid="", save=True):
    """A reviewer comment. Returns its id; a comment already kept returns the kept one's id; '' without words."""
    text = _clean(text)
    if not text:
        return ""
    sig = _sig(stage, source, file, where, text)
    old = next((c for c in items(rec) if c.get("sig") == sig), None)
    if old is not None:
        return old["id"]
    c = {"id": uuid.uuid4().hex[:10], "stage": _clean(stage, 80) or "Review", "text": text, "author": _clean(author, 80),
         "where": _clean(where, 300), "source": source, "file": _clean(file, 200), "iid": iid, "disposition": "", "reason": "",
         "owner": "", "due": "", "sig": sig, "at": _now(), "history": []}
    rec.data.setdefault(KEY, []).append(c)
    if save:
        rec.save()
    return c["id"]


def set_disposition(rec, cid, disposition="", reason=None, owner=None, due=None, who=None):
    """Set a comment's disposition (Accept, Reject, Done, or '' to reopen), reason, owner and due date. A Reject needs
    a reason. Returns '' when saved, else why not."""
    c = get(rec, cid)
    if c is None:
        return "No such comment."
    if disposition and disposition not in DISPOSITIONS:
        return "Choose Accept, Reject or Done."
    reason = c.get("reason", "") if reason is None else _clean(reason, 2000)
    if disposition == "Reject" and not reason:
        return "Say why it is rejected."
    if disposition != c.get("disposition"):
        c.setdefault("history", []).append({"disposition": disposition, "was": c.get("disposition", ""), "who": who or getpass.getuser(),
                                            "at": _now()})
        rec.log("review", f"{c['stage']} comment " + (disposition.lower() if disposition else "reopened"), who=who)
    c["disposition"], c["reason"] = disposition, reason
    if owner is not None:
        c["owner"] = _clean(owner, 80)
    if due is not None:
        c["due"] = _clean(due, 16)
    rec.save()
    return ""


def counts(rec, stage=None):
    cs = items(rec, stage)
    out = {"total": len(cs), "open": sum(1 for c in cs if not c.get("disposition")), "no_owner": sum(1 for c in cs if not c.get("owner"))}
    for d in DISPOSITIONS:
        out[d] = sum(1 for c in cs if c.get("disposition") == d)
    return out


def all_dispositioned(rec, stage=None):
    """True when every comment has a disposition; None when there are no comments yet (the gate goal)."""
    c = counts(rec, stage)
    return None if not c["total"] else c["open"] == 0


def summary(rec, stage=None):
    c = counts(rec, stage)
    if not c["total"]:
        return "No reviewer comments yet."
    done = c["total"] - c["open"]
    return (f"{done} of {c['total']} comments dispositioned: " + ", ".join(f"{c[d]} {d.lower()}" for d in DISPOSITIONS if c[d])
            + (f"; {c['open']} open" if c["open"] else "") + (f"; {c['no_owner']} without an owner" if c["no_owner"] else ""))


def stages(rec):
    seen = []
    for c in items(rec):
        if c.get("stage") and c["stage"] not in seen:
            seen.append(c["stage"])
    return seen


# ------------------------------------------------------------------ from a review packet
def from_packet(rec, M, result, stage=""):
    """Every reviewer comment and Word comment on a packet row becomes a comment to disposition, placed at the
    requirement (its reference). Verdicts alone are not comments. Returns the number added."""
    import setupdoc as SD
    stage = stage or result.get("stage") or "Review"
    by = {it["id"]: it for it in M.items} if M is not None else {}
    inh = SD.inherited_sections(M) if M is not None else {}
    n0 = len(items(rec))
    for f in result.get("findings", []):
        it = by.get(f["id"])
        where = f["id"]
        if it is not None:
            ref = SD.ref_of(M, it, inh)[0]
            secs = SD.item_sections(M, it)
            where = " ".join(x for x in (ref or f["id"], f"({secs[0]})" if secs else "") if x)
        if f.get("comment"):
            add(rec, stage, f["comment"], where=where, source="packet", file=result.get("file", ""), iid=f["id"], save=False)
        for author, text in f.get("word_comments", []):
            add(rec, stage, text, author=author, where=where, source="packet", file=result.get("file", ""), iid=f["id"], save=False)
    rec.save()
    return len(items(rec)) - n0


# ------------------------------------------------------------------ Word comments in the drafts
def read_word_comments(path):
    """[(heading it sits under, author, text)] for every Word comment in a draft, in document order."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "word/comments.xml" not in names:
            return []
        croot = etree.fromstring(z.read("word/comments.xml"), parser=parser)
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
        sroot = etree.fromstring(z.read("word/styles.xml"), parser=parser) if "word/styles.xml" in names else None
    comments = {}
    for c in croot.iter(_W + "comment"):
        txt = " ".join("".join(t.text or "" for t in p.iter(_W + "t")) for p in c.iter(_W + "p")).strip()
        comments[c.get(_W + "id")] = (c.get(_W + "author") or "", " ".join(txt.split()))
    heading_ids = set()
    if sroot is not None:
        for s in sroot.iter(_W + "style"):
            nm = s.find(_W + "name")
            name = (nm.get(_W + "val") if nm is not None else "") or ""
            lvl = s.find(f"{_W}pPr/{_W}outlineLvl")
            if name.lower().startswith("heading") or lvl is not None:
                heading_ids.add(s.get(_W + "styleId"))
    out, seen, heading = [], set(), ""
    body = root.find(_W + "body")
    for p in body.iter(_W + "p"):
        ps = p.find(f"{_W}pPr/{_W}pStyle")
        if (ps is not None and ps.get(_W + "val") in heading_ids) or p.find(f"{_W}pPr/{_W}outlineLvl") is not None:
            t = "".join(x.text or "" for x in p.iter(_W + "t")).strip()
            if t:
                heading = t
        for el in p.iter(_W + "commentRangeStart", _W + "commentReference"):
            cid = el.get(_W + "id")
            if cid in comments and cid not in seen:
                seen.add(cid)
                a, t = comments[cid]
                if t:
                    out.append((heading or "Before the first heading", a, t))
    return out


def from_drafts(rec, paths, stage):
    """Word comments in the drafts become comments to disposition, each placed under its heading (and file). Returns
    {"added": n, "files": [(file, comments found)]}."""
    n0 = len(items(rec))
    files = []
    for p in paths:
        if not p.lower().endswith(".docx") or os.path.basename(p).startswith("~$"):
            continue
        try:
            got = read_word_comments(p)
        except (OSError, zipfile.BadZipFile, KeyError, ValueError):
            files.append((os.path.basename(p), -1))
            continue
        for heading, author, text in got:
            add(rec, stage, text, author=author, where=heading, source="draft", file=os.path.basename(p), save=False)
        files.append((os.path.basename(p), len(got)))
    rec.save()
    return {"added": len(items(rec)) - n0, "files": files}


# ------------------------------------------------------------------ the disposition log
def export_xlsx(path, rec, stage=None, effort=""):
    """The disposition log: one row per comment (stage, where, file, author, comment, disposition, reason, owner, due)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"
    head = ["Stage", "Where", "File", "Reviewer", "Comment", "Disposition", "Reason", "Owner", "Due"]
    ws.append(head)
    for c in items(rec, stage):
        ws.append([c.get("stage", ""), c.get("where", ""), c.get("file", ""), c.get("author", ""), c.get("text", ""),
                   c.get("disposition", "") or "Open", c.get("reason", ""), c.get("owner", ""), c.get("due", "")])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1E3A8A")
    for col, w in zip("ABCDEFGHI", (14, 28, 22, 16, 60, 13, 30, 16, 12)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    wb.properties.title = f"{effort} comment dispositions".strip()
    wb.save(path)
    return path
