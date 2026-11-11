"""The team's lists as files (4.7.1; claude/stationkeeper-team-library-files-decisions-2026-11-10.md, decision 3, phase 2).

The four tests decide where a list goes: a row defines it, people edit it, two readers use it, and it stays small.
- Small lists are sheets of the Company Standards workbook (standardsbook): Phrases (banned and avoided, with what to
  use instead), Authors (who writes, and for which efforts), Compliance words (the words that mark a requirement),
  Piece types (the shred's types: names, keys, colors, shown) and Document types (each with its initial).
- Large lists stay files of their own in the team library's Lists folder: the master acronym list
  (Acronyms.csv, the same columns the app keeps) and each custom dictionary as a Word dictionary (<name>.dic), so Word
  can use it as it is.
Each list keeps its own file in the config folder as the app's cache; the team library's files are the truth, read
when they change and written when the app changes them. Rules only (No AI); nothing leaves the PC."""
import os

import diag

# sheet: (columns, load(config_dir) -> rows, save(config_dir, rows))


def _phrases_load(cfg):
    import banned as B
    return [dict(r) for r in B.load()]


def _phrases_save(cfg, rows):
    import banned as B
    return B.save([{k: r.get(k) or "" for k in B.COLUMNS} for r in rows])


def _authors_load(cfg):
    import authorlist as AL
    lst = AL.AuthorList(os.path.join(cfg, AL.FILE)).load()
    return [{"Name": p["name"], "Efforts": "Every effort" if p.get("efforts") == AL.ALL else ", ".join(p.get("efforts") or []),
             "Added": p.get("added", ""), "Source": p.get("source", "")} for p in lst.people]


def _authors_save(cfg, rows):
    import authorlist as AL
    lst = AL.AuthorList(os.path.join(cfg, AL.FILE)).load()
    old = {p["name"].casefold(): p for p in lst.people}
    people = []
    for r in rows:
        name = " ".join(str(r.get("Name") or "").split())
        if not name:
            continue
        eff = str(r.get("Efforts") or "").strip()
        p = dict(old.get(name.casefold()) or {"added": r.get("Added") or "", "source": r.get("Source") or "the team library"})
        p["name"] = name
        p["efforts"] = AL.ALL if eff in ("", "Every effort", AL.ALL) else [e.strip() for e in eff.split(",") if e.strip()]
        people.append(p)
    lst.people = people
    lst._log("read from the team library", added=len(people))
    lst.save()
    return len(people)


def _cwords_load(cfg):
    import cwords as CW
    return [{"Word": w} for w in CW.load(cfg)["words"]]


def _cwords_save(cfg, rows):
    import cwords as CW
    d = CW.load(cfg)
    d["words"] = [str(r.get("Word") or "").strip() for r in rows if str(r.get("Word") or "").strip()]
    CW.save(d, cfg)
    return len(d["words"])


def _types_load(cfg):
    import shredtypes as ST
    return [{"Key": t["key"], "Name": t["name"], "Shortcut": t["short"], "Color": t["color"], "Shown": bool(t["shown"])}
            for t in ST.load(cfg).values()]


def _types_save(cfg, rows):
    import shredtypes as ST
    cur = ST.load(cfg)
    for r in rows:
        k = str(r.get("Key") or "").strip()
        if k in cur:
            cur[k].update(name=str(r.get("Name") or cur[k]["name"]), short=str(r.get("Shortcut") or cur[k]["short"])[:1].upper(),
                          color=str(r.get("Color") or cur[k]["color"]), shown=bool(r.get("Shown") if r.get("Shown") is not None else True))
    ST.save(cfg, cur)
    return len(cur)


def _doctypes_load(cfg):
    import doctypes as DT
    return [{"Name": t["name"], "Initial": t.get("initial", ""), "Numbered": bool(t.get("numbered")),
             "Builds the matrix": bool(t.get("matrix")), "Words that find it": t.get("words", "")} for t in DT.load(cfg)["types"]]


def _doctypes_save(cfg, rows):
    import doctypes as DT
    types = [{"name": str(r.get("Name") or "").strip(), "initial": DT.clean_initial(str(r.get("Initial") or "")),
              "numbered": bool(r.get("Numbered")), "matrix": bool(r.get("Builds the matrix")),
              "words": str(r.get("Words that find it") or "")} for r in rows if str(r.get("Name") or "").strip()]
    DT.save(cfg, types)
    return len(types)


SHEETS = {"Phrases": (("Phrase", "Level", "Use instead", "Why"), _phrases_load, _phrases_save),
          "Authors": (("Name", "Efforts", "Added", "Source"), _authors_load, _authors_save),
          "Compliance words": (("Word",), _cwords_load, _cwords_save),
          "Piece types": (("Key", "Name", "Shortcut", "Color", "Shown"), _types_load, _types_save),
          "Document types": (("Name", "Initial", "Numbered", "Builds the matrix", "Words that find it"), _doctypes_load, _doctypes_save)}


def load_all(config_dir):
    """{sheet: (columns, rows)} for the workbook. A list that cannot be read is left out (and said in the log)."""
    out = {}
    for sheet, (cols, load, _save) in SHEETS.items():
        try:
            out[sheet] = (list(cols), load(config_dir))
        except Exception:  # noqa: BLE001
            diag.swallowed()
    return out


def _norm(rows, cols):
    return [tuple("" if r.get(c) is None else str(r.get(c)) for c in cols) for r in rows]


def apply(config_dir, book):
    """The workbook's list sheets into each list's own file, only those that changed. Returns the sheets saved."""
    saved = []
    for sheet, (cols, load, save) in SHEETS.items():
        rows = book.get("sheets", {}).get(sheet)
        if rows is None:
            continue
        try:
            if _norm(rows, cols) != _norm(load(config_dir), cols):
                save(config_dir, rows)
                saved.append(sheet)
        except Exception:  # noqa: BLE001
            diag.swallowed()
    return saved


# ------------------------------------------------------------------ the large lists: Lists\Acronyms.csv and the .dic files
def dic_files(config_dir, folder):
    """Each custom dictionary as <folder>\\<name>.dic (Word's dictionary file). Returns the paths written."""
    import customdict as CD
    os.makedirs(folder, exist_ok=True)
    out = []
    for d in CD.Store(config_dir).dicts:
        p = os.path.join(folder, _safe(d["name"]) + ".dic")
        CD.write_dic(p, d["words"])
        out.append(p)
    return out


def read_dic_files(config_dir, folder):
    """The .dic files back into the dictionaries: a changed file's words become the dictionary's; a new file a new
    dictionary. Returns the names changed."""
    import customdict as CD
    if not os.path.isdir(folder):
        return []
    st = CD.Store(config_dir)
    changed = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(".dic") or f.startswith("~$"):
            continue
        name = os.path.splitext(f)[0]
        words = CD.sort_words(CD.read_dic(os.path.join(folder, f)))
        d = next((x for x in st.dicts if _safe(x["name"]).casefold() == name.casefold()), None)
        if d is None:
            import uuid
            st.dicts.append({"id": uuid.uuid4().hex[:10], "name": name, "words": words, "created": CD._now(), "changed": CD._now(),
                             "exports": []})
            changed.append(name)
        elif d["words"] != words:
            d["words"], d["changed"] = words, CD._now()
            changed.append(d["name"])
    if changed:
        st.save()
    return changed


def _safe(name):
    return "".join(ch for ch in str(name) if ch not in '\\/:*?"<>|').strip() or "Dictionary"
