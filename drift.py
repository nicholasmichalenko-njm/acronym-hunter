"""The drift report (3.79.0, after Production Standards retires): how far a live draft has moved from the copies made of
it.

Apply in Word and Fix a Copy work on a dated copy beside the draft ("<draft> - banned phrases 2026-11-06 2130.docx");
the author keeps writing in the draft. For each copy the report says, for every tracked change the copy holds, whether the
draft took it up (the new words are there and the old are gone), still has it to take (the old words are still there), or
moved on (neither: the passage was rewritten); and how many of the draft's paragraphs changed since the copy was made.
A copy whose draft moved on a lot is better made again.

copies_of(draft) -> [copy path], newest first
copy_changes(copy) -> [{"para", "old", "new"}]       the copy's tracked changes (deleted and inserted words)
original_paragraphs(copy) -> [text]                  the draft as it was when the copy was made
report(draft, copy) -> {...}                         one copy against the draft as it is now
reports(draft) -> [report]                           every copy of a draft
write_xlsx(reports, path)
Reads only; Word is not needed. Rules only (No AI); nothing leaves the PC."""
import datetime, difflib, os, re, zipfile

STAMP = re.compile(r" - (?P<what>.+?) (?P<when>\d{4}-\d{2}-\d{2} \d{4})\.docx$", re.I)
TAKEN, OPEN, MOVED = "Taken up", "Still to take", "The passage changed"
REMAKE_AT = 0.2                       # a fifth of the paragraphs changed: make the copy again


def _root(path):
    from lxml import etree
    import techeditdocx as TD
    with zipfile.ZipFile(path) as z:
        return etree.fromstring(z.read("word/document.xml"), parser=TD._parser()), TD.W


def _norm(s):
    return " ".join((s or "").split())


def copies_of(draft):
    """The dated copies beside a draft (any kind: banned phrases, fixed), newest first."""
    d, stem = os.path.dirname(os.path.abspath(draft)), os.path.splitext(os.path.basename(draft))[0]
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return []
    for n in names:
        if n.startswith(stem + " - ") and n.lower().endswith(".docx") and not n.startswith("~$") and STAMP.search(n):
            out.append(os.path.join(d, n))
    return sorted(out, key=lambda p: when_of(p) or datetime.datetime.min, reverse=True)


def when_of(copy):
    m = STAMP.search(os.path.basename(copy))
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group("when"), "%Y-%m-%d %H%M")
    except ValueError:
        return None


def kind_of(copy):
    m = STAMP.search(os.path.basename(copy))
    return m.group("what") if m else ""


def original_paragraphs(copy):
    """The copy's paragraphs with its deletions kept and its insertions left out: the draft when the copy was made."""
    root, W = _root(copy)
    out = []
    for p in root.iter(W + "p"):
        parts = []
        for x in p.iter(W + "t", W + "delText"):
            if any(a.tag == W + "ins" for a in x.iterancestors()):
                continue
            parts.append(x.text or "")
        out.append("".join(parts))
    return out


def copy_changes(copy):
    """Each paragraph's tracked changes as (old, new) pairs: a deletion and the insertion that follows it, or either alone."""
    root, W = _root(copy)
    out = []
    for i, p in enumerate(root.iter(W + "p")):
        pend = None
        for el in p.iter(W + "del", W + "ins"):
            txt = "".join(x.text or "" for x in el.iter(W + "delText" if el.tag == W + "del" else W + "t"))
            if el.tag == W + "del":
                if pend is not None:
                    out.append(pend)
                pend = {"para": i, "old": txt, "new": ""}
            else:
                if pend is not None and not pend["new"]:
                    pend["new"] = txt
                    out.append(pend); pend = None
                else:
                    out.append({"para": i, "old": "", "new": txt})
        if pend is not None:
            out.append(pend)
    return [c for c in out if _norm(c["old"]) or _norm(c["new"])]


def _draft_paragraphs(draft):
    import wordlab as WL
    return WL.docx_paragraphs(draft)


def _state(change, now_text):
    """Taken up: the copy's new words are in the draft and its old words are not (or a deletion is gone). Still to take:
    the old words are still there. The passage changed: neither."""
    old, new = _norm(change["old"]), _norm(change["new"])
    has_old = bool(old) and old in now_text
    if new and new in now_text and not has_old:
        return TAKEN
    if not new and old and not has_old:
        return TAKEN
    if has_old:
        return OPEN
    return MOVED


def report(draft, copy):
    """One copy against the draft as it is now."""
    was = original_paragraphs(copy)
    now = _draft_paragraphs(draft)
    sm = difflib.SequenceMatcher(None, [_norm(x) for x in was], [_norm(x) for x in now], autojunk=False)
    where = {}                                         # the copy's paragraph -> the draft's paragraph it became
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                where[i1 + k] = j1 + k
        else:
            changed += max(i2 - i1, j2 - j1)
            for k in range(i2 - i1):
                if j1 + k < j2:
                    where[i1 + k] = j1 + k
    rows = []
    for c in copy_changes(copy):
        j = where.get(c["para"])
        now_text = _norm(now[j]) if j is not None and j < len(now) else ""
        if not now_text:                               # the paragraph went: look across the whole draft
            now_text = _norm(" ".join(now))
        st = _state(c, now_text)
        rows.append(dict(c, state=st))
    total = max(1, len([x for x in was if _norm(x)]))
    share = changed / total
    out = {"draft": draft, "copy": copy, "kind": kind_of(copy), "when": when_of(copy), "changes": rows,
           "taken": sum(1 for r in rows if r["state"] == TAKEN), "open": sum(1 for r in rows if r["state"] == OPEN),
           "moved": sum(1 for r in rows if r["state"] == MOVED), "paras_changed": changed, "paras": total,
           "share": round(share, 3)}
    out["advice"] = ("Make the copy again: the draft has moved on." if share >= REMAKE_AT
                     else "The copy still fits the draft." if out["open"] or not rows else "Every change was taken up.")
    return out


def reports(draft):
    out = []
    for c in copies_of(draft):
        try:
            out.append(report(draft, c))
        except (OSError, KeyError, zipfile.BadZipFile, ValueError):
            import diag
            diag.swallowed()
    return out


def write_xlsx(reps, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active; ws.title = "Copies"
    ws.append(["Draft", "Copy", "Made", "Taken up", "Still to take", "The passage changed", "Paragraphs changed", "Advice"])
    for r in reps:
        ws.append([os.path.basename(r["draft"]), os.path.basename(r["copy"]), r["when"].strftime("%Y-%m-%d %H:%M") if r["when"] else "",
                   r["taken"], r["open"], r["moved"], f"{r['paras_changed']} of {r['paras']}", r["advice"]])
    ws2 = wb.create_sheet("Changes")
    ws2.append(["Copy", "Paragraph", "Was", "Copy says", "In the draft now"])
    for r in reps:
        for c in r["changes"]:
            ws2.append([os.path.basename(r["copy"]), c["para"] + 1, c["old"], c["new"], c["state"]])
    for s in (ws, ws2):
        for cell in s[1]:
            cell.font = Font(bold=True)
        s.freeze_panes = "A2"
    wb.save(path)
    return path
