"""Author kickoff packets (3.37.0): one Word file per author with everything they need for the sections they own, in
the order a writer reads it. For each section: their role, the page budget and due dates, the customer's requirements
word for word with where each is (and its L, M or SOW designation), the Section M factors that score it, the customer's
objectives, hot buttons and key points captured for it (verbatim, with their source), the win themes it carries with
their discriminator and proof, open meeting topics, answered customer questions, and the storyboard so far. Then the
effort's facts (Wall of Truth). The effort's marking sits at the top and bottom of every page.

section_pack() is also what Structure Builder's "Everything for this section" panel shows, so the packet and the panel
always agree. Built from the effort's own records: rules only, no AI; nothing leaves the PC."""
import datetime, os, re

GRAY, INK, NAVY = "64748B", "0F172A", "1E3A8A"
LM_WORD = {"L": "L", "M": "M", "C": "SOW", "I": "Interest"}


def _names(text):
    return [x.strip() for x in re.split(r"[,;]+", text or "") if x.strip()]


def authors(M):
    """{name: {"lead": [labels], "with": [labels]}}: who owns or writes each section (a subsection inherits its parent's
    people unless it has its own), and the sections where a sentence names its own author, in outline order."""
    import compliance as C, setupdoc as SD
    out = {}

    def add(name, role, lab):
        d = out.setdefault(name, {"lead": [], "with": []})
        if lab not in d["lead"] and lab not in d["with"]:
            d[role].append(lab)
    labels = [C.outline_label(o) for o in M.outline]
    for lab in labels:
        p = SD.section_people(M, lab)
        if p.get("lead"):
            add(p["lead"], "lead", lab)
        for n in _names(p.get("with", "")):
            add(n, "with", lab)
    for it in M.items:
        if it.get("decision") not in ("Keep", "Context"):
            continue
        for n in SD.split_names(it.get("owner", "")):
            for lab in SD.item_sections(M, it):
                if lab in labels:
                    add(n, "with", lab)
    for d in out.values():
        for k in ("lead", "with"):
            d[k].sort(key=lambda l: labels.index(l) if l in labels else 10 ** 6)
    return out


def _where(M, it):
    import matrixdesign as MD
    w = MD._where(it, M)
    return ", ".join(x for x in (it.get("file", ""), w) if x)


def section_pack(rec, M, label):
    """Everything for one section: {"label", "lead", "with", "pages", "reqs": [{ref, lm, text, where, support}],
    "factors", "objectives", "hot", "keypoints", "captures", "themes", "topics", "qa", "storyboard"}."""
    import setupdoc as SD, pagebudget as PB, matrixdesign as MD
    inh = SD.inherited_sections(M)
    p = SD.section_people(M, label)
    reqs, ids, Ls = [], set(), []
    for it in M.items:
        if it.get("decision") not in ("Keep", "Context") or label not in SD.item_sections(M, it):
            continue
        ids.add(it.get("id"))
        lm = SD.lm_of(M, it, inh)
        reqs.append({"ref": SD.ref_of(M, it, inh)[0] or it.get("section", "") or it.get("id", ""), "lm": LM_WORD.get(lm, ""),
                     "text": ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", ""), "where": _where(M, it),
                     "support": it.get("decision") == "Context"})
        if it.get("decision") == "Keep" and lm != "M":
            Ls.append(it)
    reqs.sort(key=lambda r: r["support"])
    out = {"label": label, "lead": p.get("lead", ""), "with": p.get("with", ""), "pages": PB.pages(M, label),
           "reqs": reqs, "factors": MD._factors(M, Ls, inh) if Ls else "",
           "objectives": [], "hot": [], "keypoints": [], "captures": [], "themes": [], "topics": [], "qa": [], "storyboard": {}}
    if rec is None:
        return out
    try:
        import excerpts as EX
        for x in EX.excerpts(rec):
            mine = label in (x.get("sections") or []) or any(pt.get("sid") in ids for pt in x.get("parts", []))
            if not mine:
                continue
            row = {"text": EX.text_of(x), "where": EX.where_of(x), "note": x.get("note", "")}
            key = {"objective": "objectives", "hot": "hot", "keypoint": "keypoints"}.get(x.get("bin"))
            if key:
                out[key].append(row)
            elif label in (x.get("sections") or []):
                out["captures"].append(dict(row, kind=EX.bin_name(rec, x.get("bin"))))
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    try:
        import themes as TH
        out["themes"] = [{"title": t.get("title", ""), "statement": t.get("statement", ""), "kind": t.get("kind", ""),
                          "discriminator": t.get("discriminator", ""), "proof": list(t.get("proof") or []), "hot": t.get("hot", "")}
                         for t in TH.for_section(rec, label)]
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    try:
        import meetings as MT
        for m, t in MT.topics(rec, open_only=True):
            if t.get("target") == label or t.get("target") in ids:
                out["topics"].append({"text": t.get("text", ""), "owner": t.get("owner", ""), "meeting": m.get("title", ""),
                                      "date": m.get("date", "")})
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    try:
        import custqa as Q
        for q in Q.items(rec):
            if q.get("sid") in ids and q.get("answer"):
                out["qa"].append({"question": q.get("question", ""), "answer": q.get("answer", ""), "doc": q.get("answer_doc", "")})
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    try:
        import storyboard as SB
        sb = SB.get(rec, label)
        out["storyboard"] = {k: sb.get(k) for k in ("status", "message", "approach")}
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    return out


def facts(rec):
    """The effort's facts: [(label, value, source)]."""
    if rec is None:
        return []
    import walloftruth as WT
    return [(t.get("label", ""), t.get("value", ""), t.get("source", "")) for t in WT.items(rec)]


def dates(rec):
    """[(what, when)]: the proposal's due date and the stages still ahead, with their planned dates."""
    if rec is None:
        return []
    out = []
    try:
        import effortrec as R
        due = rec.data.get("due", "")
        if due:
            out.append(("Proposal due", R.due_text(due, rec.data.get("zone", ""))))
        cur = rec.index()
        for i, s in enumerate(rec.stages):
            if i >= max(cur, 0) and s.get("planned") and not s.get("ended"):
                out.append((s.get("name", ""), str(s["planned"])[:10]))
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    return out


def count(pack):
    """How much a section holds, for a short line: requirements, captures, themes, topics, answers."""
    return {"reqs": sum(1 for r in pack["reqs"] if not r["support"]), "support": sum(1 for r in pack["reqs"] if r["support"]),
            "captures": len(pack["objectives"]) + len(pack["hot"]) + len(pack["keypoints"]) + len(pack["captures"]),
            "themes": len(pack["themes"]), "topics": len(pack["topics"]), "qa": len(pack["qa"])}


# ------------------------------------------------------------------ the Word packet
def _section(d, pack, role):
    import pagebudget as PB
    d.heading(pack["label"], 1)
    d.table(["Your role", "Lead", "Writers", "Page budget", "Storyboard"],
            [[role, pack["lead"] or "-", pack["with"] or "-", (PB.fmt(pack["pages"]) + " pages") if pack["pages"] else "not set",
              (pack["storyboard"] or {}).get("status") or "Not started"]], [1500, 1900, 2300, 1600, 2060])
    d.heading("What the customer asks for", 2)
    reqs = [r for r in pack["reqs"] if not r["support"]]
    if reqs:
        d.table(["Reference", "L, M or SOW", "The customer's words", "Where"],
                [[r["ref"], r["lm"] or "-", r["text"], r["where"]] for r in reqs], [1300, 1000, 5060, 2000])
    else:
        d.para("No requirements are placed in this section yet.", color=GRAY)
    sup = [r for r in pack["reqs"] if r["support"]]
    if sup:
        d.heading("Supporting context", 3)
        d.table(["Reference", "The customer's words", "Where"], [[r["ref"], r["text"], r["where"]] for r in sup], [1300, 6060, 2000])
    if pack["factors"]:
        d.heading("How it is scored (Section M)", 2)
        for line in pack["factors"].splitlines():
            d.para("- " + line)
    for key, title in (("objectives", "The customer's objectives"), ("hot", "Hot buttons"), ("keypoints", "Key points")):
        if pack[key]:
            d.heading(title, 2)
            d.table(["What", "Source"], [[x["text"] + (f" ({x['note']})" if x.get("note") else ""), x["where"]] for x in pack[key]],
                    [6560, 2800])
    if pack["themes"]:
        d.heading("Win themes this section carries", 2)
        d.table(["Theme", "Discriminator", "Proof"],
                [[t["title"] + (f": {t['statement']}" if t["statement"] else ""), t["discriminator"], "; ".join(t["proof"])]
                 for t in pack["themes"]], [3600, 2900, 2860])
    if pack["captures"]:
        d.heading("Other captures placed here", 2)
        d.table(["Kind", "What", "Source"], [[x["kind"], x["text"], x["where"]] for x in pack["captures"]], [1600, 5160, 2600])
    if pack["topics"]:
        d.heading("Open meeting topics", 2)
        d.table(["Topic", "Owner", "Meeting"], [[t["text"], t["owner"] or "-", f"{t['meeting']} {t['date']}".strip()] for t in pack["topics"]],
                [5360, 1600, 2400])
    if pack["qa"]:
        d.heading("The customer's answers", 2)
        d.table(["Our question", "The customer's answer", "In"], [[q["question"], q["answer"], q["doc"]] for q in pack["qa"]],
                [3400, 4360, 1600])
    sb = pack["storyboard"] or {}
    if sb.get("message") or sb.get("approach"):
        d.heading("Your storyboard so far", 2)
        if sb.get("message"):
            d.rich([("Key message: ", {"bold": True}), (sb["message"], {})])
        for line in (sb.get("approach") or "").splitlines():
            if line.strip():
                d.para(line)


def write(path, rec, M, name, roles, effort="", marking=None, when=None):
    """One author's packet. roles: {"lead": [labels], "with": [labels]}. Returns the path."""
    import docxw
    when = when or datetime.datetime.now()
    d = docxw.Doc()
    d.marking = marking
    d.props = {"StationkeeperKickoff": effort}
    d.rich([(f"AUTHOR KICKOFF PACKET  |  {effort}" if effort else "AUTHOR KICKOFF PACKET", {"color": GRAY, "size": 18, "bold": True})])
    d.rich([(name, {"bold": True, "size": 36, "color": INK})])
    d.rich([(f"Made {when:%B %d, %Y}", {"color": GRAY, "size": 18})])
    secs = [(lab, "Lead") for lab in roles.get("lead", [])] + [(lab, "Writer") for lab in roles.get("with", [])]
    d.heading("Your sections", 2)
    packs = {lab: section_pack(rec, M, lab) for lab, _r in secs}
    import pagebudget as PB
    d.table(["Section", "Your role", "Page budget", "Requirements"],
            [[lab, role, (PB.fmt(packs[lab]["pages"]) + " pages") if packs[lab]["pages"] else "not set", str(count(packs[lab])["reqs"])]
             for lab, role in secs], [4560, 1400, 1700, 1700])
    dl = dates(rec)
    if dl:
        d.heading("Dates", 2)
        d.table(["What", "When"], [[a, b] for a, b in dl], [4680, 4680])
    for lab, role in secs:
        d.page_break()
        _section(d, packs[lab], role)
    fx = facts(rec)
    if fx:
        d.page_break()
        d.heading("Facts to use (Wall of Truth)", 1)
        d.table(["Fact", "Value", "Source"], [[a, b, c] for a, b, c in fx], [3400, 3200, 2760])
    d.rich([("Made by Stationkeeper on this PC from the effort's own records. Rules only, no AI. It quotes customer documents: "
             "share it the way you share the proposal.", {"color": GRAY, "size": 16})])
    d.save(path)
    return path


def safe(name):
    return re.sub(r"[^A-Za-z0-9 _.-]+", "", name).strip().replace(" ", "_") or "Author"


def write_all(folder, rec, M, effort="", marking=None, names=None, when=None):
    """A packet for each author (or the names given), into a dated folder. Returns [(name, path)]."""
    when = when or datetime.datetime.now()
    people = authors(M)
    os.makedirs(folder, exist_ok=True)
    out = []
    for name in sorted(people, key=str.casefold):
        if names is not None and name not in names:
            continue
        p = os.path.join(folder, f"{safe(effort) + '_' if effort else ''}Kickoff_{safe(name)}_{when:%Y-%m-%d}.docx")
        out.append((name, write(p, rec, M, name, people[name], effort, marking, when)))
    return out


def panel_groups(pack):
    """[(group, [line])] for Structure Builder's Everything for this section panel (the same facts as the packet)."""
    import pagebudget as PB
    g = []
    who = ", ".join(x for x in (f"Lead: {pack['lead']}" if pack["lead"] else "", f"Writers: {pack['with']}" if pack["with"] else "") if x)
    g.append(("People and pages", [who or "No lead or writers set yet",
                                   f"Page budget: {PB.fmt(pack['pages'])} pages" if pack["pages"] else "Page budget: not set"]))
    c = count(pack)
    g.append(("What the customer asks for", [f"{c['reqs']} requirement(s), {c['support']} supporting sentence(s)"]
              + [f"{r['ref']} ({r['lm']}): {r['text']}" if r["lm"] else f"{r['ref']}: {r['text']}" for r in pack["reqs"] if not r["support"]]))
    if pack["factors"]:
        g.append(("How it is scored (Section M)", pack["factors"].splitlines()))
    for key, title in (("objectives", "The customer's objectives"), ("hot", "Hot buttons"), ("keypoints", "Key points")):
        if pack[key]:
            g.append((title, [f"{x['text']}  ({x['where']})" if x["where"] else x["text"] for x in pack[key]]))
    if pack["themes"]:
        g.append(("Win themes", [t["title"] + (f": {t['discriminator']}" if t["discriminator"] else "") for t in pack["themes"]]))
    if pack["captures"]:
        g.append(("Other captures", [f"{x['kind']}: {x['text']}" for x in pack["captures"]]))
    if pack["topics"]:
        g.append(("Open meeting topics", [f"{t['text']}" + (f" ({t['owner']})" if t["owner"] else "") for t in pack["topics"]]))
    if pack["qa"]:
        g.append(("The customer's answers", [f"Q: {q['question']}  A: {q['answer']}" for q in pack["qa"]]))
    sb = pack["storyboard"] or {}
    g.append(("Storyboard", [f"Status: {sb.get('status') or 'Not started'}"] + ([f"Key message: {sb['message']}"] if sb.get("message") else [])))
    return g
