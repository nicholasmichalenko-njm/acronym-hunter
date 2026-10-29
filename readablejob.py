"""The readable copy, kept current by the Qt window (2.92.0; the classic window did this from 2.46.0 until it was retired).

A few seconds after the effort's saved files change, the readable copy beside the effort list is rewritten in the
background from those files (readable.py says what is in it): the CSV files and READ ME FIRST, plus the calendar (Excel,
CSV and Outlook), the post-submission checklist (Excel) and, when the effort closes or is backed up, the Effort overview
(Word). Nothing on screen waits for it. Rules only (No AI); nothing leaves the PC.
"""
import os

import readable as RD


def signature(list_path, data_dir, matrix_path=""):
    """The saved files' times: when any changes, the readable copy is out of date."""
    paths = [list_path, matrix_path] + [os.path.join(data_dir, *p) for p in (("record.json",), ("documents", "index.json"),
                                                                            ("documents", "register.json"), ("context", "attach.json"),
                                                                            ("changes", "review.json"), ("settings.json",))]
    out = []
    for p in paths:
        try:
            out.append((p, os.path.getmtime(p)))
        except (OSError, TypeError):
            out.append((p, 0))
    return tuple(out)


def job(name, list_path, data_dir, matrix_path="", info=None, version="", overview=False, my_zone=""):
    return {"name": name, "list": list_path, "data": data_dir, "matrix": matrix_path or "", "info": dict(info or {}),
            "version": version, "overview": overview, "folder": RD.folder_for(list_path, name), "my_zone": my_zone}


def write(j):
    """Write the readable copy from the effort's saved files (any thread). Returns the folder."""
    import compliance as C
    import docversions as DV
    import effort as E
    import effortrec as ER
    import subreq as SR
    info = j["info"]
    L = E.EffortList(j["list"], j["name"], client=info.get("client", ""), solicitation=info.get("solicitation", ""),
                     internal_no=info.get("internal_no", "")).load()
    rec = ER.Record(j["data"]) if j["data"] and os.path.isdir(j["data"]) else None
    lib = DV.Library(os.path.join(j["data"], "documents")).load() if j["data"] else None
    rows = SR.Register(lib).rows(include_hidden=True) if lib is not None else []
    M = C.Matrix(j["matrix"]).load() if j["matrix"] and os.path.isfile(j["matrix"]) else None
    parts = RD.build(L, rec, lib, rows, M, {"effort": j["name"], **{k: info.get(k, "") for k in ("client", "solicitation")}}, j["version"])
    parts.update(RD.more(rec, lib, j["data"], {"client": L.client, "solicitation": L.solicitation}))
    also = []
    folder = j["folder"]
    os.makedirs(folder, exist_ok=True)
    if rec is not None:
        import effortcal as EC
        import effortstate as ES
        crow = EC.rows_of(rec, ES.cal_extra_of(rec, rows))
        parts["Calendar.csv"] = (list(EC.COLUMNS), [[r[c] for c in EC.COLUMNS] for r in crow])
        for fn, w in (("Calendar.xlsx", EC.write_xlsx), ("Calendar.ics", EC.write_ics)):
            try:
                w(os.path.join(folder, fn), crow, j["name"])
                also.append(fn)
            except PermissionError:
                pass                                     # open in Excel or Outlook right now: the next write catches up
        if isinstance(rec.data.get("postsub"), dict) and rec.data["postsub"].get("items"):
            import postsub as PS
            try:
                PS.export_xlsx(rec, os.path.join(folder, "Post-submission checklist.xlsx"), j["name"], who="Stationkeeper")
                also.append("Post-submission checklist.xlsx")
            except PermissionError:
                pass
        if j.get("overview"):
            try:
                import statusdoc as SDOC
                import workspace as W
                st = ES.State(W.Workspace(j["data"], j["name"]), j["list"], M)
                SDOC.build(ES.status_snapshot(st, app_version=j["version"], name=j["name"], client=L.client,
                                              solicitation=L.solicitation, internal=L.internal_no, my_zone=j.get("my_zone", "")),
                           os.path.join(folder, "Effort overview.docx"))
                also.append("Effort overview.docx")
            except PermissionError:
                pass
    if os.path.isfile(os.path.join(folder, "Effort overview.docx")) and "Effort overview.docx" not in also:
        also.append("Effort overview.docx")
    parts["_also"] = also
    parts["READ ME FIRST.txt"] = RD.readme_text({"effort": j["name"], "list": os.path.basename(j["list"]),
                                                 "matrix": os.path.basename(j["matrix"] or "")}, parts, j["version"])
    RD.write(folder, parts, lib)
    return folder
