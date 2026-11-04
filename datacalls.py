"""Internal data calls (3.39.0): what the proposal team needs from subject matter experts, asked in a way that gets
answered. Each call says what is needed, which section or requirement it serves, how much (word-count guidance), an
example of a good answer, who owns it and when it is due. The proposal manager sends each person one Word file with
their calls; the person types in the Your answer box and sends it back; Read answers puts each answer back on its
call; Place in the section puts an answer into the response structure as context for the section's author.

Kept in the effort record (record.json, "data_calls"). Each call has a code (DC-1, DC-2 ...) that never changes, so a
returned file finds its calls even when others were added or removed. Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, os, re, uuid, zipfile

KEY = "data_calls"
STATUSES = ("Draft", "Sent", "Answered", "Placed")
FIELDS = ("question", "section", "req", "words", "example", "owner", "due", "status", "answer", "note")
MARK = "StationkeeperDataCall"
ROWS = ("What we need", "For", "How much", "An example of a good answer", "Due", "Your answer")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=8000):
    return " ".join(str(v or "").split())[:n]


def items(rec):
    """Every call, in the order they were made (DC-1 first)."""
    return sorted((c for c in rec.data.get(KEY, []) if isinstance(c, dict)), key=lambda c: c.get("num", 0))


def get(rec, cid):
    return next((c for c in rec.data.get(KEY, []) if c.get("id") == cid), None)


def by_code(rec, code):
    return next((c for c in items(rec) if code_of(c) == code), None)


def code_of(c):
    return f"DC-{c.get('num', 0)}"


def add(rec, question, section="", req="", words="", example="", owner="", due="", who=None, save=True):
    """A new Draft call. Returns its id ('' without a question)."""
    question = _clean(question)
    if not question:
        return ""
    num = 1 + max([c.get("num", 0) for c in items(rec)] + [0])
    c = {"id": uuid.uuid4().hex[:10], "num": num, "question": question, "section": _clean(section, 200), "req": _clean(req, 1000),
         "words": _clean(words, 80), "example": _clean(example), "owner": _clean(owner, 80), "due": _clean(due, 16),
         "status": "Draft", "answer": "", "note": "", "who": who or getpass.getuser(), "at": _now(), "history": []}
    rec.data.setdefault(KEY, []).append(c)
    rec.log("datacall", f"Data call {code_of(c)} drafted" + (f" for {c['owner']}" if c["owner"] else ""), who=who)
    if save:
        rec.save()
    return c["id"]


def update(rec, cid, who=None, **f):
    """Change a call's fields (FIELDS). A status change is kept in its history with who and when; an answer typed in
    makes the call Answered."""
    c = get(rec, cid)
    if c is None:
        return False
    for k in FIELDS:
        if k not in f:
            continue
        v = f[k]
        if k == "status":
            if v not in STATUSES or v == c.get("status"):
                continue
            c.setdefault("history", []).append({"status": v, "was": c.get("status", ""), "who": who or getpass.getuser(), "at": _now()})
            rec.log("datacall", f"Data call {code_of(c)}: {v.lower()}", who=who)
        else:
            v = _clean(v, 80 if k in ("owner", "words") else 16 if k == "due" else 200 if k == "section" else 20000)
        c[k] = v
    if f.get("answer") and c.get("status") in ("Draft", "Sent"):
        update(rec, cid, who=who, status="Answered")
    rec.save()
    return True


def remove(rec, cid, who=None):
    c = get(rec, cid)
    if c is None:
        return False
    rec.data[KEY] = [x for x in rec.data.get(KEY, []) if x.get("id") != cid]
    rec.log("datacall", f"Data call {code_of(c)} removed", who=who)
    rec.save()
    return True


def counts(rec):
    out = {s: 0 for s in STATUSES}
    for c in items(rec):
        out[c.get("status", "Draft")] = out.get(c.get("status", "Draft"), 0) + 1
    return out


def overdue(rec, today=None):
    """Calls past their due date with no answer yet."""
    t = (today or datetime.date.today()).isoformat()
    return [c for c in items(rec) if c.get("due") and c["due"][:10] < t and c.get("status") in ("Draft", "Sent")]


def summary(rec, today=None):
    c = counts(rec)
    total = sum(c.values())
    if not total:
        return "No data calls yet."
    late = len(overdue(rec, today))
    return f"{total} data call(s): " + ", ".join(f"{n} {s.lower()}" for s, n in c.items() if n) + (f"; {late} overdue" if late else "")


def owners(rec):
    """Everyone with an open call (Draft or Sent), in name order."""
    return sorted({c["owner"] for c in items(rec) if c.get("owner") and c.get("status") in ("Draft", "Sent")}, key=str.casefold)


# ------------------------------------------------------------------ Word: one file per person
def file_name(effort, owner, when=None):
    when = when or datetime.datetime.now()
    safe = re.sub(r"[^\w .-]+", "", f"{effort} - Data call for {owner}").strip()
    return f"{safe} {when:%Y-%m-%d %H%M}.docx"


def export_docx(path, calls, effort="", owner="", marking="", when=None, from_name=""):
    """One person's data calls: a short note on what to do, then one box per call (what we need, what it is for, how
    much, an example, the due date, and an empty Your answer box). Returns the path."""
    import docxw
    when = when or datetime.date.today()
    d = docxw.Doc()
    if marking:
        d.marking = (marking, "C00000")
    d.props = {"Stationkeeper": MARK, "Effort": effort, "Owner": owner}
    d.rich([("Data call", {"bold": True, "size": 36, "color": "1F3864"})])
    d.rich([(f"{effort}  ·  for {owner}  ·  {when:%B %d, %Y}".replace(" 0", " "), {"color": "475569"})])
    d.rich([("Type each answer in its Your answer box, save this file and send it back" + (f" to {from_name}" if from_name else "")
             + ". Keep the call codes as they are: they put each answer back where it belongs.", None)])
    for c in calls:
        d.rich([(f"{code_of(c)}", {"bold": True, "size": 26, "color": "1F3864"})])
        vals = (c.get("question", ""), " / ".join(x for x in (c.get("section", ""), c.get("req", "")) if x) or "The response",
                c.get("words", "") or "As much as it takes, no more", c.get("example", "") or "None given", c.get("due", ""),
                c.get("answer", ""))
        rows = [[[(lab, {"bold": True})], val] for lab, val in zip(ROWS, vals)]
        d.table(["Call", code_of(c)], rows, [2600, 6760])
    d.save(path)
    return path


def export_all(folder, rec, effort="", marking="", when=None, who=None, owners_=None):
    """One Word file per person with an open call; their Draft calls become Sent. Returns [(owner, path)]."""
    when = when or datetime.datetime.now()
    os.makedirs(folder, exist_ok=True)
    out = []
    for o in owners_ or owners(rec):
        calls = [c for c in items(rec) if c.get("owner") == o and c.get("status") in ("Draft", "Sent")]
        if not calls:
            continue
        p = export_docx(os.path.join(folder, file_name(effort, o, when)), calls, effort, o, marking, when)
        for c in calls:
            if c.get("status") == "Draft":
                update(rec, c["id"], who=who, status="Sent")
        out.append((o, p))
    return out


def _text(el):
    out = []
    for p in el.iter(_W + "p"):
        out.append("".join(t.text or "" for t in p.iter(_W + "t")))
    return "\n".join(x for x in out if x.strip()).strip()


def read_back(path):
    """{code: answer} from a returned data call file (any file with the Call / Your answer boxes)."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
    out = {}
    for tbl in root.iter(_W + "tbl"):
        rows = tbl.findall(_W + "tr")
        if not rows:
            continue
        first = rows[0].findall(_W + "tc")
        if len(first) < 2 or _text(first[0]) != "Call":
            continue
        code = _text(first[1]).split()[0] if _text(first[1]) else ""
        for tr in rows[1:]:
            cells = tr.findall(_W + "tc")
            if len(cells) >= 2 and _text(cells[0]) == ROWS[5]:
                ans = _text(cells[1])
                if code and ans:
                    out[code] = ans
    return out


def apply_answers(rec, answers, who=None):
    """Put each answer on its call (the call becomes Answered). Returns {"answered": n, "unknown": [codes]}."""
    n, unknown = 0, []
    for code, ans in answers.items():
        c = by_code(rec, code)
        if c is None:
            unknown.append(code)
            continue
        if ans != c.get("answer"):
            update(rec, c["id"], who=who, answer=ans)
            n += 1
    if n:
        rec.log("datacall", f"Data call answers read back: {n}", who=who, save=True)
    return {"answered": n, "unknown": unknown}


# ------------------------------------------------------------------ into the response structure
def place(rec, M, cid, label="", who=None):
    """Put a call's answer into the response structure as context under its section (or label), for the section's
    author: it shows in the setup, the kickoff packet and Everything for this section. Returns the context id, or ''."""
    import compliance as C
    import setupdoc as SD
    c = get(rec, cid)
    if c is None or not c.get("answer") or M is None:
        return ""
    label = label or c.get("section", "")
    if label not in {C.outline_label(o) for o in M.outline}:
        return ""
    S = SD.setup_of(M)
    xid = c.get("placed_id") or ""
    if not any(x.get("id") == xid for x in S["context"]):
        xid = f"X-{len(S['context']) + 1:03d}"
        while any(x.get("id") == xid for x in S["context"]):
            xid = f"X-{int(xid[2:]) + 1:03d}"
        S["context"].append({"id": xid, "kind": "context", "text": c["answer"], "lead": "", "map": "", "decision": "Keep",
                             "type": "Context", "file": f"Data call {code_of(c)}" + (f" ({c['owner']})" if c.get("owner") else ""),
                             "loc": c.get("req", ""), "section": "", "section_title": "", "source": "data call", "datacall": c["id"]})
    else:
        next(x for x in S["context"] if x.get("id") == xid)["text"] = c["answer"]
    SD.place(M, xid, label)
    c["placed_id"] = xid
    update(rec, cid, who=who, status="Placed")
    if hasattr(M, "pending"):
        M.pending = True
    return xid
