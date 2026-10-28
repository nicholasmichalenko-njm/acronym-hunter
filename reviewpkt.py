"""Color team review packets (2.63.0): a Word file for a review stage (Red team, Gold team) with every compliance
requirement under the section of the response it is answered in: its ID, RFP reference, the requirement, its owner, and
two empty columns for the reviewer: Verdict (Compliant, Partly, Not compliant, Not addressed) and Comments. Reviewers
fill the table in Word and may add Word comments on any row. Read back: each verdict and comment, and every Word
comment on a row, goes to that requirement's sentence card (a review note on the requirement in the effort's record),
and the verdicts are kept with the matrix for the score by section. Rules only (No AI); nothing leaves the PC.
"""
import datetime, os, re, zipfile
import docxw

VERDICTS = ("Compliant", "Partly", "Not compliant", "Not addressed")
HEAD = ["ID", "RFP reference", "Requirement", "Owner", "Verdict", "Reviewer comments"]
WIDTHS = [900, 1150, 3500, 1050, 1060, 1700]
MARK = "Stationkeeper review packet"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _reviews(M):
    import setupdoc as SD
    return SD.setup_of(M).setdefault("reviews", {})


def rows_by_section(M):
    """[(section label or 'Not in a section yet', [requirement items])] in the order of the response structure."""
    import compliance as C
    import setupdoc as SD
    keeps = [it for it in M.items if it["decision"] == "Keep"]
    out, seen = [], set()
    for o in M.outline:
        lab = C.outline_label(o)
        here = [it for it in keeps if lab in SD.item_sections(M, it) and it["id"] not in seen]
        if here:
            out.append((lab, here))
            seen |= {it["id"] for it in here}
    loose = [it for it in keeps if it["id"] not in seen]
    if loose:
        out.append(("Not in a section yet", loose))
    return out


def build(M, path, effort_name="", stage="Review", reviewers="", when=None):
    """Write the packet. Returns {"path", "rows", "sections"}."""
    import setupdoc as SD
    when = when or datetime.date.today()
    inh = SD.inherited_sections(M)
    d = docxw.Doc()
    d.props = {"StationkeeperReviewPacket": f"{stage}|{when.isoformat()}", "StationkeeperEffort": effort_name or M.name}
    d.heading(f"{effort_name or M.name}: {stage} review", 1)
    d.rich([(f"{MARK}  |  {stage}  |  {when.strftime('%B')} {when.day}, {when.year}", {"color": "475569"})])
    if reviewers:
        d.rich([("Reviewers: ", {"bold": True}), (reviewers, {})])
    d.rich([("How to review: ", {"bold": True}),
            ("for each requirement, write a verdict in the Verdict column (" + ", ".join(VERDICTS) + ") and your comments "
             "beside it. Word comments on a row are read too. Leave the ID column as it is. Send the file back; it is read "
             "into Stationkeeper and each comment lands on that requirement's sentence card.", {})])
    n = 0
    groups = rows_by_section(M)
    for lab, items in groups:
        d.heading(lab, 2)
        rows = []
        for it in items:
            ref = SD.ref_of(M, it, inh)[0]
            rows.append([it["id"], ref, ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", ""),
                         SD.owner_of(M, it), "", ""])
        d.table(HEAD, rows, WIDTHS)
        n += len(rows)
    if not groups:
        d.para("No compliance requirements yet.")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    d.save(path)
    return {"path": path, "rows": n, "sections": len(groups)}


def _text(el):
    """A cell's or a comment's text, paragraphs joined by line breaks."""
    paras = []
    for p in el.iter(_W + "p"):
        paras.append("".join(t.text or "" for t in p.iter(_W + "t")).strip())
    return "\n".join(x for x in paras if x).strip()


def _verdict(text):
    t = " ".join((text or "").lower().split())
    if not t:
        return ""
    if t.startswith(("not compliant", "non-compliant", "noncompliant", "no")):
        return "Not addressed" if "address" in t else "Not compliant"
    if t.startswith(("not addressed", "missing", "absent")):
        return "Not addressed"
    if t.startswith(("partly", "partial", "part")):
        return "Partly"
    if t.startswith(("compliant", "yes", "ok", "meets")):
        return "Compliant"
    return ""


def read_back(path, M):
    """{"stage", "findings": [{"id", "verdict", "verdict_text", "comment", "word_comments": [(author, text)]}],
    "unknown": [ids not in the matrix]}. Reads the tables (any row whose first cell is a requirement ID) and the Word
    comments anchored in a row."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
        comments = {}
        if "word/comments.xml" in names:
            croot = etree.fromstring(z.read("word/comments.xml"), parser=parser)
            for c in croot.iter(_W + "comment"):
                comments[c.get(_W + "id")] = (c.get(_W + "author") or "", _text(c))
        stage = ""
        if "docProps/custom.xml" in names:
            m = re.search(rb"StationkeeperReviewPacket\"[^>]*>\s*<vt:lpwstr>([^<|]*)", z.read("docProps/custom.xml"))
            stage = m.group(1).decode("utf-8", "replace") if m else ""
    ids = {it["id"] for it in M.items}
    out, unknown = [], []
    for tr in root.iter(_W + "tr"):
        cells = tr.findall(_W + "tc")
        if len(cells) < len(HEAD):
            continue
        iid = _text(cells[0]).strip()
        if not iid or iid == HEAD[0]:
            continue
        if iid not in ids:
            unknown.append(iid)
            continue
        vt, comment = _text(cells[4]), _text(cells[5])
        wc = []
        for el in tr.iter(_W + "commentRangeStart", _W + "commentReference"):
            cid = el.get(_W + "id")
            if cid in comments and comments[cid] not in wc:
                wc.append(comments[cid])
        if vt or comment or wc:
            out.append({"id": iid, "verdict": _verdict(vt), "verdict_text": vt, "comment": comment, "word_comments": wc})
    return {"stage": stage, "findings": out, "unknown": unknown}


def apply(M, rec, result, stage="", who=None):
    """Each finding becomes a review note on its requirement (the sentence card shows it) and its verdict is kept with
    the matrix under the stage. Returns {"notes", "verdicts"}."""
    import setupdoc as SD
    stage = stage or result.get("stage") or "Review"
    by = {it["id"]: it for it in M.items}
    inh = SD.inherited_sections(M)
    rv = _reviews(M).setdefault(stage, {})
    notes = verdicts = 0
    for f in result["findings"]:
        it = by.get(f["id"])
        if it is None:
            continue
        if f["verdict"]:
            rv[f["id"]] = f["verdict"]
            verdicts += 1
        parts = []
        if f["verdict"] or f["verdict_text"]:
            parts.append(f["verdict"] or f["verdict_text"])
        if f["comment"]:
            parts.append(f["comment"])
        for author, text in f["word_comments"]:
            parts.append((f"{author}: " if author else "") + text)
        if rec is not None and parts:
            ref = SD.ref_of(M, it, inh)[0]
            nid = rec.add_note(f"{stage} review: " + ". ".join(p.rstrip(".") for p in parts) + ".", on="requirement", on_id=f["id"],
                               label=" ".join(x for x in (ref or f["id"], stage) if x), who=who)
            notes += bool(nid)
    if hasattr(M, "pending"):
        M.pending = True
    if rec is not None:
        rec.log("review", f"{stage} review packet read back: {verdicts} verdicts, {notes} comments on requirements", who=who, save=True)
    return {"notes": notes, "verdicts": verdicts}


def score(M, stage):
    """{"total", "Compliant", "Partly", "Not compliant", "Not addressed", "not_reviewed", "sections": [(label, counts)]}."""
    rv = _reviews(M).get(stage, {})
    out = {"total": 0, **{v: 0 for v in VERDICTS}, "not_reviewed": 0, "sections": []}
    for lab, items in rows_by_section(M):
        c = {v: 0 for v in VERDICTS}
        c["not_reviewed"] = 0
        for it in items:
            v = rv.get(it["id"], "")
            c[v if v else "not_reviewed"] += 1
        out["sections"].append((lab, c))
    keeps = {it["id"] for it in M.items if it["decision"] == "Keep"}
    out["total"] = len(keeps)
    for iid in keeps:
        v = rv.get(iid, "")
        out[v if v else "not_reviewed"] += 1
    return out


def stages_reviewed(M):
    return list(_reviews(M).keys())


def review_notes(rec, iid):
    """The review notes on one requirement, newest first (the sentence card)."""
    return [n for n in rec.notes(on="requirement", on_id=iid) if " review: " in n["text"]] if rec is not None else []
