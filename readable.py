"""Readable copy (2.46.0): everything an effort holds, in plain files anyone can open without Stationkeeper.

The app saves its work as it goes (the effort list and compliance matrix workbooks, and JSON files in the effort's
app data folder). Those are complete but some are technical (internal IDs, JSON). The readable copy is a folder beside
the effort list, "<effort> - readable copy (Stationkeeper)", rewritten a few seconds after every saved change:
- READ ME FIRST.txt: what each file is, when it was updated, how to use the files without the app.
- Effort summary.txt: the effort's details, due date, stage, open questions, tasks, what changed last.
- CSV files (open in Excel or Notepad; UTF-8): stages and gate goals, tasks, notes and open questions, deliverables,
  the timeline, submission requirements, customer documents, compliance assignments (each passage's role in words,
  section, owner, section people, reference, text), the response structure and people, acronyms, keywords.
- Customer document text: one .txt file per document version, named by document and version.
Names, not internal IDs. Files are written to a temporary name and then swapped in, so a reader never sees half a
file. Rules only (No AI); nothing leaves the PC.
"""
import csv, datetime, io, os, re

SUFFIX = " - readable copy (Stationkeeper)"
ROLE = {"Keep": "Compliance requirement", "Context": "Context", "Customer": "Customer's (not ours to answer)", "Drop": "Not used",
        "": "Not decided yet"}


def folder_for(list_path, effort_name=""):
    d, n = os.path.split(os.path.abspath(list_path))
    try:                                           # 2.95.0: in the effort's root when the list sits in a folder of the tree
        import effortfolders as EF
        d = EF.root(list_path) or d
    except Exception:
        pass
    name = effort_name or os.path.splitext(n)[0]
    return os.path.join(d, _safe(name) + SUFFIX)


def _safe(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", s or "").strip().rstrip(".")
    return re.sub(r"\s+", " ", s)[:90] or "Effort"


def _when(iso):
    """'2026-10-27T08:28' -> '2026-10-27 08:28' (sorts and reads)."""
    return (iso or "").replace("T", " ")[:16]


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return path
        except PermissionError:                      # open in Excel right now: keep the old copy, try again next save
            import time
            time.sleep(0.2)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return None


def _csv(path, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else str(v) for v in r])
    return _write(path, buf.getvalue())


# ------------------------------------------------------------------ the parts
def _stages(rec):
    data = rec.data
    names = {s["id"]: s["name"] for s in data["stages"]}
    rows = []
    for k, s in enumerate(data["stages"], 1):
        cur = "current" if s["id"] == data["stage"] else ("done" if s.get("ended") else "")
        goals = s.get("goals") or [{}]
        import effortrec as R
        starts = (s.get("planned", "") + (" " + s["planned_time"] if s.get("planned_time") and s.get("planned") else "")).strip()
        ends = (s.get("planned_end", "") + (" " + s["planned_end_time"] if s.get("planned_end_time") and s.get("planned_end") else "")).strip()
        gate = R.GATES.get(s.get("gate", ""), "") if s.get("gate") else ""
        for g in goals:
            rows.append([k, s["name"], cur, starts, ends, gate, _when(s.get("started")), _when(s.get("ended")), g.get("text", ""),
                         g.get("owner", ""), (g.get("due", "") or "").replace("T", " "),
                         ("checked by the app" if g.get("auto") else "checked by hand") if g else "",
                         "yes" if g.get("done") else ("no" if g else ""), g.get("by", ""), _when(g.get("at"))])
    return names, rows


def build(effort=None, rec=None, lib=None, req_rows=(), matrix=None, info=None, app_version=""):
    """Everything to write: {file name: (header, rows) or text}. Pure: no disk access except the library's text copies."""
    out = {}
    info = dict(info or {})
    names = {}
    if rec is not None:
        names, srows = _stages(rec)
        out["Stages and gate goals.csv"] = (["Order", "Stage", "State", "Planned start", "Planned end", "Gate", "Started", "Ended",
                                             "Gate goal", "Goal owner", "Goal deadline", "How checked", "Done", "Done by", "Done at"], srows)
        out["Tasks.csv"] = (["Task", "Owner", "Due", "Stage", "Status", "About", "Notes", "Added", "Added by", "Done"],
                            [[t["title"], t.get("owner", ""), t.get("due", "").replace("T", " "), names.get(t.get("stage"), ""), t.get("status", ""),
                              t.get("about", ""), t.get("notes", ""), _when(t.get("created")), t.get("by", ""), t.get("done", "")]
                             for t in rec.data.get("tasks", [])])
        out["Notes and open questions.csv"] = (["When", "Who", "Kind", "About", "Text", "Answer", "Resolved", "Stage"],
                                               [[_when(n.get("at")), n.get("who", ""), "Open question" if n.get("question") and not n.get("resolved")
                                                 else "Question (answered)" if n.get("question") else "Note", n.get("label", "") or n.get("on", ""),
                                                 n.get("text", ""), n.get("answer", ""), n.get("resolved", ""), names.get(n.get("stage"), "")]
                                                for n in rec.data.get("notes", [])])
        out["Deliverables.csv"] = (["Deliverable", "Kind", "Owner", "Status", "Format", "Limit", "Our file", "Customer form",
                                    "Done for stages", "Notes", "Added", "Added by"],
                                   [[d["name"], d.get("kind", ""), d.get("owner", ""), d.get("status", ""), d.get("format", ""),
                                     d.get("limit", ""), d.get("file", ""), _doc_name(lib, d.get("doc_id")),
                                     "; ".join(f"{names.get(sid, sid)} ({v})" for sid, v in (d.get("stages_done") or {}).items()),
                                     d.get("notes", ""), _when(d.get("created")), d.get("by", "")] for d in rec.data.get("deliverables", [])])
        if lib is not None:                                         # 2.94.0: page-limited and the formatting rules
            try:
                import formatreq as FR
                fc = FR.for_effort(lib, rec)
                out["Formatting requirements.csv"] = (["Rule", "Required", "What the documents say", "Where"],
                                                       [["Page-limited", "", FR.flag_text(fc), {"set": "set by the proposal manager",
                                                                                               "found": "found in the documents"}.get(fc["how"], "")]]
                                                       + [[f"Page limit: {x['subject']}", "yes", x["value"], x["where"]] for x in fc["limits"]]
                                                       + [[x["label"], "yes" if x["required"] else "no", x["value"] or "Not specified in the documents",
                                                           x["where"]] for x in fc["lines"]])
            except Exception:
                pass
        out["Timeline (paper trail).csv"] = (["When", "Who", "Kind", "Stage", "What happened"],
                                             [[_when(e.get("at")), e.get("who", ""), e.get("kind", ""), names.get(e.get("stage"), ""), e.get("text", "")]
                                              for e in rec.data.get("timeline", [])])
        info.setdefault("due", rec.data.get("due", ""))
        info.setdefault("zone", rec.data.get("zone", ""))
    rows = list(req_rows or [])
    out["Submission requirements.csv"] = (["Kind", "Subject", "Value", "Found in document", "Version", "Where", "Sentence",
                                           "Changed in a newer version", "Change reviewed", "Confirmed", "Typed in", "Not a requirement"],
                                          [[r["kind"], r["subject"], r["value"], r.get("doc", ""), r.get("version", ""), r.get("loc", ""),
                                            r.get("sentence", ""), "yes" if r.get("changed") else "", "not yet" if r.get("to_review") else
                                            (r.get("reviewed") or ""), r.get("confirmed", ""), "yes" if r.get("manual") else "",
                                            "yes" if r.get("hidden") else ""] for r in rows])
    if lib is not None:
        drows, texts = [], {}
        for d in lib.docs:
            for v in d["versions"]:
                drows.append([d["name"], v["label"], v.get("file", ""), _when(v.get("added")), v.get("who", ""), v.get("sha256", ""),
                              v.get("sentences", ""), v.get("reviewed", "") or ("not yet" if d["versions"].index(v) else "")])
                fname = f"{_safe(d['name'])} - {_safe(v['label'])}.txt"
                texts[fname] = v
        out["Customer documents.csv"] = (["Document", "Version", "File", "Added", "Added by", "Fingerprint (SHA-256)", "Sentences",
                                          "Changes reviewed"], drows)
        out["_texts"] = texts
    if matrix is not None and matrix.items:
        import setupdoc as SD
        inh = SD.inherited_sections(matrix) if hasattr(SD, "inherited_sections") else {}
        by_id = {it["id"]: it for it in matrix.items}
        crow = []
        for it in matrix.items:
            ppl = SD.section_people(matrix, it.get("map", "")) if it.get("map") else {"lead": "", "with": ""}
            try:
                ref, _src = SD.ref_of(matrix, it, inh)
            except Exception:
                ref = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
            cf = [x.strip() for x in (it.get("context_for") or "").replace(";", ",").split(",") if x.strip()]
            crow.append([it["id"], ROLE.get(it.get("decision", ""), it.get("decision", "")), it.get("map", ""),
                         SD.owner_of(matrix, it) if it.get("map") or it.get("owner") else "", ppl.get("lead", ""), ppl.get("with", ""),
                         ", ".join(cf), ref, it.get("file", ""), it.get("loc", ""), ((it.get("lead") or "") + " " + it["text"]).strip(),
                         it.get("status", ""), it.get("response_page", ""), it.get("notes", ""), it.get("new", "")])
        out["Compliance assignments.csv"] = (["ID", "Role", "Our section", "Owner", "Section lead", "Section contributors",
                                              "Context for (requirement IDs)", "RFP reference", "Customer file", "Where in the file",
                                              "RFP text", "Status", "Response page", "Notes", "Change"], crow)
        srows = []
        import compliance as C
        for o in matrix.outline:
            lab = C.outline_label(o)
            p = SD.section_people(matrix, lab)
            srows.append([o.get("num", ""), o.get("title", ""), o.get("level", 1), p.get("lead", ""), p.get("with", ""),
                          "" if p.get("from") in ("", lab) else f"from {p['from']}",
                          sum(1 for it in matrix.items if it.get("map") == lab and it.get("decision") == "Keep"),
                          sum(1 for it in matrix.items if it.get("map") == lab and it.get("decision") == "Context")])
        out["Response structure and people.csv"] = (["Number", "Title", "Level", "Lead", "Contributors", "People inherited",
                                                     "Compliance requirements", "Context sentences"], srows)
        info["matrix"] = os.path.basename(getattr(matrix, "path", "") or "")
        _ = by_id
    if effort is not None:
        cols = ["Term", "Type", "Definition", "Alt forms", "Status", "SS Approver", "Approved on", "Source", "Customer document",
                "Customer wording", "Used in volumes", "First use", "Notes"]
        out["Acronyms.csv"] = (cols, [[(effort.rows[t].get(c, "") if c != "Term" else t) for c in cols] for t in effort.order if t in effort.rows])
        kcols = ["Keyword", "Category", "Status", "Source", "Why", "Added by", "Date", "SharePoint field"]
        out["Keywords.csv"] = (kcols, [[k.get(c, "") for c in kcols] for k in (effort.keywords or [])])
        for k, attr in (("effort", "name"), ("client", "client"), ("solicitation", "solicitation"), ("internal", "internal_no")):
            info.setdefault(k, getattr(effort, attr, "") or "")
        info["list"] = os.path.basename(getattr(effort, "path", "") or "")
    out["Effort summary.txt"] = summary_text(info, rec, out, app_version)
    out["READ ME FIRST.txt"] = readme_text(info, out, app_version)
    return out


def _doc_name(lib, doc_id):
    if not doc_id or lib is None:
        return ""
    d = lib.doc(doc_id)
    return d["name"] if d else ""


def summary_text(info, rec, out, app_version=""):
    L = [f"EFFORT: {info.get('effort', '')}"]
    for lab, k in (("Client", "client"), ("Solicitation or opportunity", "solicitation"), ("Internal number", "internal")):
        if info.get(k):
            L.append(f"{lab}: {info[k]}")
    if info.get("due"):
        try:
            import effortrec as ER
            L.append(f"Proposal due: {ER.due_text(info['due'], info.get('zone', ''))} ({ER.countdown_text(info['due'])} when this was written)")
        except Exception:
            L.append(f"Proposal due: {info['due']} {info.get('zone', '')}")
    if rec is not None:                                    # 2.92.0: the banner's details
        idt = rec.data.get("identity") or {}
        for lab, v in (("Proposal manager", idt.get("pm", "")), ("Sensitivity", idt.get("sensitivity", ""))):
            if v:
                L.append(f"{lab}: {v}")
        L += [f"{f.get('label', '')}: {f.get('value', '')}" for f in idt.get("fields", []) if f.get("label")]
    if rec is not None:
        st = rec.stage()
        L.append(f"Current stage: {st['name']}" + (f" (since {_when(st.get('started'))})" if st.get("started") else ""))
        goals = st.get("goals", [])
        if goals:
            L.append(f"Gate goals met: {sum(1 for g in goals if g.get('done'))} of {len(goals)}")
            L += [f"  - [{'x' if g.get('done') else ' '}] {g.get('text', '')}" for g in goals]
        qs = [n for n in rec.data.get("notes", []) if n.get("question") and not n.get("resolved")]
        if qs:
            L.append("")
            L.append(f"OPEN QUESTIONS ({len(qs)})")
            L += [f"  - {n['text']}" + (f" ({n['label']})" if n.get("label") else "") + f", {n.get('who', '')} {_when(n.get('at'))}" for n in qs]
        open_t = [t for t in rec.data.get("tasks", []) if t.get("status") != "Done"]
        if open_t:
            L.append("")
            L.append(f"OPEN TASKS ({len(open_t)})")
            L += [f"  - {t['title']}" + (f", {t['owner']}" if t.get("owner") else "") + (f", due {t['due']}" if t.get("due") else "") +
                  f" [{t.get('status', '')}]" for t in open_t]
        tl = rec.data.get("timeline", [])
        if tl:
            L.append("")
            L.append("LAST CHANGES")
            L += [f"  - {_when(e.get('at'))}  {e.get('who', '')}: {e.get('text', '')}" for e in tl[-12:][::-1]]
    counts = []
    for f, lab in (("Compliance assignments.csv", "compliance passages"), ("Acronyms.csv", "acronyms"), ("Deliverables.csv", "deliverables"),
                   ("Submission requirements.csv", "submission requirements"), ("Customer documents.csv", "customer document versions")):
        if f in out:
            counts.append(f"{len(out[f][1])} {lab}")
    if counts:
        L += ["", "IN THIS COPY: " + ", ".join(counts)]
    L += ["", f"Written {datetime.datetime.now():%Y-%m-%d %H:%M} by Stationkeeper {app_version}. See READ ME FIRST.txt."]
    return "\n".join(L) + "\n"


FILES = [
    ("Effort summary.txt", "The effort at a glance: details, due date, current stage and its gate goals, open questions, open tasks, last changes."),
    ("Stages and gate goals.csv", "Every stage in order with its planned start and end, its gate, and its gate goals: owner, deadline, met or not, by whom, when; checked by the app or by hand."),
    ("Tasks.csv", "Every task: owner, due date, stage, status, what it is about, notes."),
    ("Notes and open questions.csv", "Every note and question: when, who, what it is about, the answer when resolved."),
    ("Deliverables.csv", "What the effort must deliver: kind, owner, status, format, page limit, our working file, the customer form, done marks per stage."),
    ("Formatting requirements.csv", "Whether the effort is page-limited, its page limits, and each formatting rule: required (what and where) or not specified."),
    ("Timeline (paper trail).csv", "Everything that happened, in order: documents added, decisions, stage moves, assignments, notes, tasks."),
    ("Submission requirements.csv", "Due dates, page limits, format, files, copies, delivery and deliverables: the value, the sentence and document it came from, and whether a change is reviewed."),
    ("Customer documents.csv", "Every customer document and version: file, when added, by whom, fingerprint, whether its changes are reviewed."),
    ("Customer document text", "Folder: the text of each customer document version, sentence by sentence, with the RFP section."),
    ("Compliance assignments.csv", "Every RFP sentence and its role: Compliance requirement, Context, Not used or Not decided yet; our section; owner; section lead and contributors; the requirements a context sentence supports; reference; text; status; notes."),
    ("Response structure and people.csv", "Our response outline with each section's lead and contributors and how many requirements and context sentences it holds."),
    ("Acronyms.csv", "The effort's acronyms, abbreviations, units and symbols: definition, alternate forms, status, approver, source, first use."),
    ("Keywords.csv", "The effort's keywords for SharePoint: category, status, source, why."),
]


def readme_text(info, out, app_version=""):
    name = info.get("effort", "") or "this effort"
    L = [f"READ ME FIRST: {name}, readable copy", "",
         "This folder is written by Stationkeeper a few seconds after every saved change, so it matches the last thing saved.",
         "Every file opens without Stationkeeper: the .csv files in Excel (or Notepad), the .txt files in Notepad or Word.",
         "Do not edit these files to change the effort: the app rewrites them. Make changes in the app, or copy a file elsewhere first.",
         "", "WHAT IS HERE"]
    for f, what in FILES + MORE_FILES:
        if f in out or (f == "Customer document text" and out.get("_texts")) or f in out.get("_also", ()):
            L.append(f"  {f}")
            L.append(f"      {what}")
    L += ["", "THE EFFORT'S WORKING FILES (what the app itself saves, beside this folder)",
          f"  {info.get('list') or '<effort>_Effort_List.xlsx'}: the acronym list, keywords and their history (Excel).",
          f"  {info.get('matrix') or '<effort>_Matrix.xlsx'}: the compliance matrix: every RFP sentence, its decision and place, the outline, setup, coverage and history (Excel)." if info.get("matrix") else
          "  The compliance matrix workbook, once there is one (Excel).",
          "  '<effort list> - app data' folder: the app's own files. record.json holds stages, tasks, notes, deliverables and the",
          "  timeline; documents\\ holds the customer document versions and their text; backups\\ holds dated copies of the two",
          "  workbooks; recovery\\ holds changes not yet written to a workbook (for example while Excel had it open).",
          "", "IF STATIONKEEPER CANNOT RUN",
          "  Everything up to the last saved change is in this folder and in the two workbooks. Copy this folder and the",
          "  workbooks to keep or share the state of the effort. The effort status report and Export all in the app give",
          "  formatted versions when the app runs again.",
          "", f"Written {datetime.datetime.now():%Y-%m-%d %H:%M} by Stationkeeper {app_version}. Rules only; nothing leaves this PC."]
    return "\n".join(L) + "\n"


def write(folder, parts, lib=None):
    """Write the parts into the folder. Customer document text files are written once per version (they never change).
    Returns the list of files written."""
    os.makedirs(folder, exist_ok=True)
    done = []
    for name, val in parts.items():
        if name in ("_texts", "_also"):
            continue
        p = os.path.join(folder, name)
        if isinstance(val, tuple):
            r = _csv(p, *val)
        else:
            r = _write(p, val)
        if r:
            done.append(name)
    texts = parts.get("_texts") or {}
    if texts and lib is not None:
        tdir = os.path.join(folder, "Customer document text")
        for fname, v in texts.items():
            p = os.path.join(tdir, fname)
            if os.path.isfile(p):
                continue
            lines = [f"{fname[:-4]}  |  file {v.get('file', '')}  |  added {_when(v.get('added'))} by {v.get('who', '')}  |  SHA-256 {v.get('sha256', '')}", ""]
            last = None
            for s in lib.text(v):
                sec = " ".join(x for x in (s.get("s", ""), s.get("t", "")) if x)
                if sec and sec != last:
                    lines += ["", f"[{sec}]"]
                    last = sec
                lines.append(s.get("x", ""))
            if _write(p, "\n".join(lines) + "\n"):
                done.append("Customer document text/" + fname)
    return done


# ------------------------------------------------------------------ 2.92.0: everything newer, kept in the readable copy
MORE_FILES = [
    ("Effort details.csv", "The effort's banner: proposal manager, client, solicitation, sensitivity, the submission's time zone and the effort's own spots."),
    ("Calendar.xlsx", "Every date the effort has (the due date, stage plans, tasks, due dates, reviews and meetings) with times, time zones, owners, places and details. Calendar.csv is the same; Calendar.ics opens in Outlook."),
    ("Post-submission checklist.xlsx", "What the team does after submission: owners, due dates, status, who finished each and when, notes."),
    ("Library documents.csv", "Every document in the effort's library (customer, bidders, Q&A, ours): category, folder, tags, role, versions and where each file is."),
    ("Taken from documents.csv", "Every sentence taken from a library document and where it went: context for a section or requirement, a note, question or task."),
    ("Change decisions.csv", "What each new customer version changed and the decision made on it: who, when and why."),
    ("Team.csv", "The people on the effort and their roles."),
    ("Customer contacts.csv", "The customer's points of contact captured from the documents: name, title, organization, e-mail, phone, address, where found."),
    ("Customer questions.csv", "The questions for the customer: number, status, category, document, where, their wording, our question, the answer and where it came."),
    ("Effort overview.docx", "The effort status report as of the last time the effort was closed or backed up: stages, people and how far along they are, open questions, newest customer documents, the proposal manager's summary."),
]


def more(rec, lib, data_dir="", info=None):
    """The CSV parts for what came after 2.46.0 (pure apart from reading the effort's own JSON files)."""
    import workspace as W
    out = {}
    info = info or {}
    if rec is not None:
        idt = rec.data.get("identity") or {}
        rows = [["Proposal manager", idt.get("pm", "")], ["Client", info.get("client", "")], ["Solicitation", info.get("solicitation", "")],
                ["Sensitivity", idt.get("sensitivity", "")], ["Submission time zone", rec.zone_key() if hasattr(rec, "zone_key") else rec.data.get("zone", "")],
                ["Proposal due", rec.data.get("due", "").replace("T", " ")]]
        rows += [[f.get("label", ""), f.get("value", "")] for f in idt.get("fields", [])]
        out["Effort details.csv"] = (["Detail", "Value"], rows)
        out["Team.csv"] = (["Name", "Role"], [[m.get("name", ""), m.get("role", "")] for m in rec.data.get("team", [])])
        out["Customer contacts.csv"] = (["Name", "Title", "Organization", "E-mail", "Phone", "Address", "Other", "Found in"],   # 2.96.0
                                        [[c.get("name", ""), c.get("title", ""), c.get("org", ""), c.get("email", ""), c.get("phone", ""),
                                          c.get("address", ""), "; ".join(f"{o['label']}: {o['value']}" for o in c.get("other", [])),
                                          "; ".join(", ".join(x for x in (s_.get("doc"), s_.get("loc")) if x) for s_ in c.get("sources", []))]
                                         for c in rec.data.get("contacts", [])])
        import custqa as Q                                                                                                # 2.98.0
        out["Customer questions.csv"] = (["No.", "Status", "Category", "Document", "Where", "Their wording", "Our question", "Answer", "Answered in"],
                                         [[q.get("n", ""), q.get("status", ""), q.get("category", ""), q.get("doc", ""), Q.where(q),
                                           q.get("quote", ""), q.get("question", ""), q.get("answer", ""), q.get("answer_doc", "")]
                                          for q in Q.items(rec)])
        ps = rec.data.get("postsub")
        if isinstance(ps, dict) and ps.get("items"):
            import postsub as PS
            out["Post-submission checklist.csv"] = (["Task", "Owner", "Due", "Status", "Done by", "Done on", "Notes"],
                                                     [[i["text"], i.get("owner", ""), (PS.due_of(rec, i).isoformat() if PS.due_of(rec, i) else ""),
                                                       i.get("status", ""), i.get("done_by", ""), _when(i.get("done_at")), i.get("notes", "")]
                                                      for i in ps["items"]])
    if lib is not None:
        rows = []
        for d in getattr(lib, "all", lib.docs):
            for v in d["versions"]:
                rows.append([d["name"], d.get("category", "customer"), d.get("folder", ""), ", ".join(d.get("tags", [])), d.get("role", ""),
                             v.get("label", ""), v.get("file", ""), lib.path_of(v) if hasattr(lib, "path_of") else v.get("path", ""),
                             _when(v.get("added")), v.get("who", "")])
        out["Library documents.csv"] = (["Document", "Category", "Folder", "Tags", "Role", "Version", "File", "Where the file is",
                                         "Added", "Added by"], rows)
    if data_dir:
        ctx = W.read_json(os.path.join(data_dir, "context", "attach.json"), None) or {}
        att = ctx.get("att", []) if isinstance(ctx, dict) else []
        if att:
            docs = {d["id"]: d for d in (getattr(lib, "all", []) if lib is not None else [])}
            ver = {v["id"]: v.get("label", "") for d in docs.values() for v in d["versions"]}
            try:
                import ctxdocs as CX
                kinds = CX.KIND_NAMES
            except Exception:
                kinds = {}
            out["Taken from documents.csv"] = (["Document", "Version", "Where", "Text", "Kind", "Attached to", "Topics", "Note", "Who", "When"],
                                               [[(docs.get(a.get("doc", "")) or {}).get("name", a.get("doc", "")), ver.get(a.get("ver", ""), ""),
                                                 a.get("loc", ""), a.get("text", ""), kinds.get(a.get("kind", ""), a.get("kind", "")), a.get("target", ""),
                                                 ", ".join(a.get("topics", [])), a.get("note", ""), a.get("who", ""), _when(a.get("when"))] for a in att])
        cr = W.read_json(os.path.join(data_dir, "changes", "review.json"), None) or {}
        pairs = cr.get("pairs", {}) if isinstance(cr, dict) else {}
        docs = {d["id"]: d for d in (getattr(lib, "all", []) if lib is not None else [])}
        ver = {v["id"]: v.get("label", "") for d in docs.values() for v in d["versions"]}
        try:
            import changereview as CR
            kn = CR.KIND_NAMES
        except Exception:
            kn = {}
        rows = []
        for pk, p in (pairs.items() if isinstance(pairs, dict) else []):
            dname = (docs.get(p.get("doc", "")) or {}).get("name", "")
            vv = f"{ver.get(p.get('from', ''), '')} to {ver.get(p.get('to', ''), '')}".strip()
            for key, lst in (p.get("decisions") or {}).items():
                for x in lst if isinstance(lst, list) else []:
                    rows.append([dname, vv, key[:120], kn.get(x.get("kind", ""), x.get("kind", "")), x.get("target", ""), x.get("why", ""),
                                 x.get("who", ""), _when(x.get("when"))])
        if rows:
            out["Change decisions.csv"] = (["Document", "Version", "Change", "Decision", "On", "Why", "Who", "When"], rows)
    return out
