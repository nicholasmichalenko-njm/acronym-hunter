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
    return {"rows": rows, "counts": DV.summary(rows), "old": DC._version(old_path, "Earlier"), "new": DC._version(new_path, "Later")}


def by_section(rows):
    return DC.by_section(rows)


def export(path, result, only_changes=True):
    return DC.export(path, result, os.path.splitext(result["new"]["file"])[0], only_changes)
