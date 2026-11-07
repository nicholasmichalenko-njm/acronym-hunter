"""What efforts set beyond Effort Formatting's list (3.82.0): the count before Production Standards' editor goes.

Effort Formatting > Every setting... still opens the old full editor on an effort's own values. Before it is removed,
this report counts, for every effort this PC knows, which of the editor's sections hold a value of the effort's own
that Effort Formatting's list (effortformat.FIELDS) does not show. A section no effort uses becomes global-only; one
that efforts use gets rows on Effort Formatting. It counts settings by section only: it shows no setting's name or value
(Words to avoid can hold people's names), and never a document's text.

report(registry_path) -> {"efforts": n, "read": n, "sections": [{"key", "title", "efforts", "values"}]}
write_text(rep) -> plain text to copy into the chat
Rules only (No AI); nothing leaves the PC."""
import json, os

TITLES = {"variables": "Base fonts and sizes", "style_defs": "Styles", "fonts": "Font rules", "styles": "Allowed styles",
          "heading_numbering": "Heading numbering", "lists": "Lists", "setups": "Page setups", "quickparts": "Quick Parts",
          "table_types": "Table types", "rows": "Row looks", "row_rules": "How rows are recognized", "captions": "Captions",
          "hf_layouts": "Headers and footers", "toc": "Table of contents", "fillins": "Fields", "parts": "Document sections",
          "pages": "Sections in order", "terms": "Words to avoid and fix", "graphics": "Graphics", "office": "Excel and PowerPoint",
          "content_map": "Content map", "profile_parts": "Parts and versions"}


def _leaves(d, path=()):
    if isinstance(d, dict) and d:
        for k, v in d.items():
            yield from _leaves(v, path + (str(k),))
    else:
        yield path


def _covered(path):
    import effortformat as EFM
    for f in EFM.FIELDS:
        p = tuple(str(x) for x in f[3])
        if path[:len(p)] == p:
            return True
    return False


def _layers(settings):
    e = (settings or {}).get("prod_std") or {}
    out = [e.get("over") or {}]
    out += list((e.get("over_vol") or {}).values())
    return out


def report(registry_path):
    import effort as E
    import workspace as W
    reg = E.Registry(registry_path)
    names = reg.names()
    per = {}
    read = 0
    for n in names:
        info = reg.get(n) or {}
        lst = info.get("path", "")
        sp = os.path.join(W.data_dir_for(lst), "settings.json") if lst else ""
        if not sp or not os.path.isfile(sp):            # never make a folder for an effort that is not there
            continue
        try:
            with open(sp, encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            continue
        read += 1
        seen = {}
        for lay in _layers(st):
            for path in _leaves(lay):
                if path and not _covered(path):
                    seen.setdefault(path[0], set()).add(".".join(path[1:3]) or path[0])
        for k, vals in seen.items():
            row = per.setdefault(k, {"key": k, "title": TITLES.get(k, k), "efforts": 0, "values": set()})
            row["efforts"] += 1
            row["values"] |= vals
    sections = sorted(({**r, "values": sorted(r["values"])} for r in per.values()), key=lambda r: (-r["efforts"], r["title"]))
    return {"efforts": len(names), "read": read, "sections": sections}


def write_text(rep):
    lines = [f"Effort values beyond Effort Formatting's list: {rep['read']} of {rep['efforts']} effort(s) read."]
    if not rep["sections"]:
        lines.append("No effort sets a value outside Effort Formatting's list.")
    for r in rep["sections"]:
        lines.append(f"- {r['title']}: {r['efforts']} effort(s), {len(r['values'])} setting(s)")
    return "\n".join(lines)
