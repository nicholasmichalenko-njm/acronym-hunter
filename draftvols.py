"""Drafts by volume (4.4.0; claude/stationkeeper-drafts-plan-4.4.md, decisions 6 and 7 of
claude/stationkeeper-releases-4.3-to-4.5-decisions-2026-11-10.md).

Each volume of the response structure has a folder, usually a SharePoint library synced to this PC. The volume's draft is
the newest Word file in it (Word's ~$ lock files ignored). Kept with the effort (workspace "draft_folders").

volumes(M) / folders(ws) / set_folder(ws, volume, folder) / newest(folder) / drafts(ws, M)
read_all(M, ws, rec, std, wpp): every volume's draft read by the outline (setupread.read), each read kept in the record.
check_acronyms(ws, M, entries): every volume's draft against the effort's list (acrfix.check).
send_unlisted(s, volume, report): a term not in the list goes back to Acros & Abs, marked "From our drafts: <volume>".
pending(s): the terms from our drafts still to decide there. Rules only; nothing leaves the PC."""
import datetime
import os

KEY = "draft_folders"
FROM = "From our drafts"


def volumes(M):
    """The volumes' names, as Setup groups the outline (one name when the response is one volume)."""
    if M is None or not M.outline:
        return []
    import setupdoc as SD
    return [n for n, _e in SD.volume_groups(M)]


def folders(ws):
    return dict(ws.get(KEY, {}) or {}) if ws is not None else {}


def set_folder(ws, volume, folder):
    f = folders(ws)
    if folder:
        f[volume] = folder
    else:
        f.pop(volume, None)
    ws.set(KEY, f)
    return f


def newest(folder):
    """The newest .docx in the folder (by when it was saved), or None."""
    if not folder or not os.path.isdir(folder):
        return None
    best = None
    for n in os.listdir(folder):
        p = os.path.join(folder, n)
        if n.lower().endswith(".docx") and not n.startswith("~$") and os.path.isfile(p):
            t = os.path.getmtime(p)
            if best is None or t > best[0]:
                best = (t, p)
    return best[1] if best else None


def saved(path):
    if not path or not os.path.isfile(path):
        return ""
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


def drafts(ws, M):
    """[{"volume", "folder", "file", "saved"}], one per volume, in the outline's order."""
    f = folders(ws)
    out = []
    for v in volumes(M):
        p = newest(f.get(v))
        out.append({"volume": v, "folder": f.get(v, ""), "file": p, "saved": saved(p)})
    return out


def _why_not(d):
    if not d["folder"]:
        return "No folder yet: More > Volume folders..."
    if not os.path.isdir(d["folder"]):
        return "The folder is not on this PC (is the library still synced?)"
    return "No Word file in the folder yet"


def read_all(M, ws, rec=None, std=None, wpp=None):
    """Every volume's newest draft read by the outline. [{volume, folder, file, saved, rep, said}]."""
    import setupread as SR
    rows = []
    for d in drafts(ws, M):
        r = dict(d, rep=None, said="")
        if not d["file"]:
            r["said"] = _why_not(d)
        else:
            try:
                rep = SR.read(M, d["file"], std=std, template=SR.file_template(d["file"]), wpp=wpp or SR.WORDS_PER_PAGE)
            except Exception as e:  # noqa: BLE001  a file Word cannot have written is said, never a crash
                r["said"] = f"Could not be read as a Word document ({type(e).__name__})"
            else:
                r["rep"] = rep
                if rep["matched"]:
                    if rec is not None:
                        SR.keep(rec, rep)
                    r["said"] = SR.summary_line(rep)
                else:
                    r["said"] = "None of this volume's headings were found in the draft"
        rows.append(r)
    return rows


def counts(r):
    """A volume's row: sections not started, under way (near budget too), over budget, requirements removed."""
    rep = r.get("rep") or {}
    c = rep.get("counts") or {}
    return {"not_started": c.get("Not started", 0), "under_way": c.get("Under way", 0) + c.get("Near budget", 0),
            "over": c.get("Over budget", 0), "removed": rep.get("removed", 0)}


# ------------------------------------------------------------------ acronyms in our drafts
def check_acronyms(ws, M, entries):
    """Every volume's newest draft against the effort's list. [{volume, folder, file, saved, report, said}]."""
    import acrfix as F
    rows = []
    for d in drafts(ws, M):
        r = dict(d, report=None, said="")
        if not d["file"]:
            r["said"] = _why_not(d)
        else:
            try:
                r["report"] = F.check(d["file"], entries)
            except Exception as e:  # noqa: BLE001
                r["said"] = f"Could not be read as a Word document ({type(e).__name__})"
        rows.append(r)
    return rows


def acr_counts(report):
    f = (report or {}).get("findings") or []
    tab = (report or {}).get("table") or {}
    return {"before": sum(1 for x in f if x["kind"] == "before"), "again": sum(1 for x in f if x["kind"] == "again"),
            "unlisted": sum(1 for x in f if x["kind"] == "unlisted"),
            "table": len(tab.get("listed_not_used") or []) + len(tab.get("used_not_listed") or []) if tab.get("rows") else None}


def send_unlisted(s, volume, report):
    """Each term the draft uses that is not in the list goes back to Acros & Abs, marked From our drafts: <volume>.
    A term already among the scan's is marked, not added again. Returns how many were added."""
    import acrmore as AM
    added = 0
    for f in (report or {}).get("findings") or []:
        if f["kind"] != "unlisted":
            continue
        t = " ".join(str(f["term"]).split())
        if t not in s.results:
            AM.add_manual(s, t, "Acronym", "", f"{FROM}: {volume}", ("results",))
            added += 1
        for d in (s.results.get(t), s.manual_items.get(t)):
            if d is not None:
                vols = list(d.get("from_drafts") or [])
                if volume not in vols:
                    vols.append(volume)
                d["from_drafts"] = vols
    s.save()
    return added


def pending(s):
    """{term: [volumes]}: the terms from our drafts still to decide on Acros & Abs (not in the list, not Not a term)."""
    if s is None:
        return {}
    return {t: list(d["from_drafts"]) for t, d in s.results.items()
            if d.get("from_drafts") and not d.get("excluded") and not d.get("effort")}
