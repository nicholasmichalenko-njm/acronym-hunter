"""Compare > Any two files (3.55.0, decisions 4 and 5): two versions of anything the reader takes (Word, PDF, PowerPoint,
Excel), sentence by sentence, each change with the heading it sits under; the redline in Word. Customer versions kept
in an effort's Library still get decisions and impact on the Customer versions tab (changereview); this is the rest:
our drafts, loose files, a file from outside the app. The same sentence matching as Compare and Final Checks
(docversions.compare). Rules only; nothing leaves the PC.

snapshot(path) / compare(old, new) / by_section(rows) / export(path, result)."""
import os, re

import draftcompare as DC


def snapshot(path):
    """[{"x": sentence, "s": heading, "t": ""}] in reading order; Word files keep their headings, others the place."""
    if path.lower().endswith(".docx"):
        return DC.snapshot(path)
    import app_gui as A
    import walloftruth as WT
    out = []
    for label, text in A.typed_chunks(path):
        t = " ".join((text or "").split())
        if not t:
            continue
        m = re.search(r"\((?:page|p\.|Slide|sheet)\s*([^,)]+)", label or "", re.I)
        where = (m.group(0).strip("(") if m else "")
        for s in WT.sentences(t):
            out.append({"x": s, "s": where, "t": ""})
    return out


def compare(old_path, new_path):
    import docversions as DV
    rows = DV.compare(snapshot(old_path), snapshot(new_path))
    return {"rows": rows, "counts": DV.summary(rows), "old": dict(DC._version(old_path, "Earlier"), path=old_path),
            "new": dict(DC._version(new_path, "Later"), path=new_path)}


def by_section(rows):
    return DC.by_section(rows)


def export(path, result, only_changes=True):
    import filesafety as FS
    FS.guard(path, result["old"].get("path"), result["new"].get("path"))     # 3.57.0: never over a file compared
    return DC.export(path, result, os.path.splitext(result["new"]["file"])[0], only_changes)


# ------------------------------------------------------------------ 3.60.0: the tracked-changes copy
def _tokens(s):
    return re.findall(r"\S+|\s+", s or "")


def export_tracked(path, result, author="Compare", when=None):
    """A Word copy of the later file with every change from the earlier one as a real tracked change (Review > Accept or
    Reject in Word): removed words deleted, added words inserted, by author; the changes under their headings. Returns
    the number of revisions."""
    import datetime
    import difflib
    import docxw
    import filesafety as FS
    FS.guard(path, result["old"].get("path"), result["new"].get("path"))
    when = (when or datetime.datetime.now()).strftime("%Y-%m-%dT%H:%M:%SZ")
    x = docxw._x
    n = [0]

    def run(t):
        return f'<w:r><w:t xml:space="preserve">{x(t)}</w:t></w:r>' if t else ""

    def ins(t):
        n[0] += 1
        return f'<w:ins w:id="{n[0]}" w:author="{x(author)}" w:date="{when}"><w:r><w:t xml:space="preserve">{x(t)}</w:t></w:r></w:ins>' if t else ""

    def dele(t):
        n[0] += 1
        return (f'<w:del w:id="{n[0]}" w:author="{x(author)}" w:date="{when}"><w:r><w:delText xml:space="preserve">{x(t)}</w:delText>'
                '</w:r></w:del>') if t else ""

    d = docxw.Doc()
    d.heading(f"{result['new']['file']}: changes from {result['old']['file']}", 1)
    d.para("Review > Accept or Reject each change. Accept all gives the later file's words; Reject all gives the earlier's.",
           color="6B7280")
    sec = None
    for r in result["rows"]:
        if (r.get("section") or "") != sec:
            sec = r.get("section") or ""
            if sec:
                d.heading(sec, 2)
        k, old, new = r["kind"], r.get("old") or "", r.get("new") or ""
        if k == "same":
            body = run(new or old)
        elif k == "added":
            body = ins(new)
        elif k == "removed":
            body = dele(old)
        else:
            a, b = _tokens(old), _tokens(new)
            body = ""
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if op == "equal":
                    body += run("".join(a[i1:i2]))
                else:
                    body += dele("".join(a[i1:i2])) + ins("".join(b[j1:j2]))
        d.body.append(f"<w:p>{body}</w:p>")
    d.save(path)
    return n[0]
