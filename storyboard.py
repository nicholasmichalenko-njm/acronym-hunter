"""Storyboards (3.2.0): the step between the Response Setup and the first draft. One sheet per section: its page
budget, lead and writers, the compliance requirements it answers, the win themes it carries, the key message and the
approach, features with their benefits and proof, and the graphics it needs. The author fills it in the app; Export
makes a Word storyboard (one section, or every section of a volume, a page each) for the storyboard review. Kept in the
effort record; the requirements and budgets come from the structure. Rules only."""
import datetime, getpass

STATUS = ("Not started", "Drafting", "Ready for review", "Approved")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=4000):
    return " ".join(str(v or "").split())[:n]


def _all(rec):
    s = rec.data.get("storyboards")
    if not isinstance(s, dict):
        s = rec.data["storyboards"] = {}
    return s


def get(rec, label):
    """The section's storyboard (an empty one when none is saved yet)."""
    sb = dict(_all(rec).get(label) or {})
    sb.setdefault("message", ""); sb.setdefault("approach", ""); sb.setdefault("features", []); sb.setdefault("graphics", "")
    sb.setdefault("themes", []); sb.setdefault("status", "Not started"); sb.setdefault("by", ""); sb.setdefault("at", "")
    return sb


def save(rec, label, who=None, **fields):
    """Saves the fields given (message, approach, features [{feature, benefit, proof}], graphics, themes [ids], status)."""
    if not label:
        return False
    cur = get(rec, label)
    new = dict(cur)
    for k, v in fields.items():
        if k in ("message", "graphics"):
            new[k] = _clean(v, 1500) if k == "message" else (v or "").strip()[:4000]
        elif k == "approach":
            new[k] = (v or "").strip()[:8000]
        elif k == "features":
            new[k] = [{"feature": _clean(f.get("feature"), 400), "benefit": _clean(f.get("benefit"), 400), "proof": _clean(f.get("proof"), 400)}
                      for f in (v or []) if any(_clean(f.get(x)) for x in ("feature", "benefit", "proof"))]
        elif k == "themes":
            new[k] = [t for t in v if t]
        elif k == "status" and v in STATUS:
            new[k] = v
    if {k: new[k] for k in new if k not in ("by", "at")} == {k: cur[k] for k in cur if k not in ("by", "at")}:
        return False
    new["by"], new["at"] = who or getpass.getuser(), _now()
    _all(rec)[label] = new
    if new["status"] != cur["status"]:
        rec.log("effort", f"Storyboard {label}: {new['status'].lower()}", who=who)
    rec.save()
    return True


def status_counts(rec, labels):
    out = {s: 0 for s in STATUS}
    for l in labels:
        out[get(rec, l)["status"]] += 1
    return out


def facts(rec, M, label):
    """What the structure says about the section: {"lead", "with", "pages", "reqs" [(ref, text)], "themes" [theme],
    "graphics" [graphic need]}."""
    import setupdoc as SD
    import pagebudget as PB
    import themes as TH
    import graphics as GX
    pp = SD.section_people(M, label) if M is not None else {"lead": "", "with": ""}
    reqs = []
    if M is not None:
        P = SD.placed_in(M)
        B = SD.by_id(M)
        inh = SD.inherited_sections(M)
        for i in P.get(label, []):
            it = B.get(i)
            if it is not None and it.get("decision") == "Keep":
                reqs.append(((SD.ref_of(M, it, inh)[0] or it["id"]), it.get("text", "")))
    sb = get(rec, label)
    chosen = set(sb["themes"])
    linked = {t["id"] for t in TH.for_section(rec, label)}
    return {"lead": pp.get("lead", ""), "with": pp.get("with", ""), "pages": PB.pages(M, label) if M is not None else None,
            "reqs": reqs, "themes": [t for t in TH.items(rec) if t["id"] in chosen | linked],
            "graphics": [g for g in GX.items(rec) if g.get("section") == label]}


def _sheet(d, rec, M, label, effort=""):
    import pagebudget as PB
    sb, f = get(rec, label), facts(rec, M, label)
    d.heading(f"Storyboard: {label}", 1)
    d.table(["Effort", "Lead", "Writers", "Page budget", "Status"],
            [[effort, f["lead"] or "-", f["with"] or "-", (PB.fmt(f["pages"]) + " pages") if f["pages"] else "not set", sb["status"]]],
            [2000, 1900, 2200, 1500, 1760])
    d.heading("Key message", 2)
    d.para(sb["message"] or "(not written yet)")
    d.heading("Win themes this section carries", 2)
    if f["themes"]:
        d.table(["Theme", "Discriminator", "Proof"], [[t["title"] + (f": {t['statement']}" if t.get("statement") else ""),
                                                        t.get("discriminator", ""), "; ".join(t.get("proof", []))] for t in f["themes"]],
                [3600, 2900, 2860])
    else:
        d.para("(none linked)")
    d.heading("Requirements to answer", 2)
    if f["reqs"]:
        d.table(["Reference", "Requirement"], [[r, t] for r, t in f["reqs"]], [1800, 7560])
    else:
        d.para("(none placed in this section)")
    d.heading("Approach", 2)
    for line in (sb["approach"] or "(not written yet)").splitlines():
        d.para(line)
    d.heading("Features, benefits and proof", 2)
    if sb["features"]:
        d.table(["Feature (what we offer)", "Benefit (to the customer)", "Proof"],
                [[x["feature"], x["benefit"], x["proof"]] for x in sb["features"]], [3120, 3120, 3120])
    else:
        d.para("(none yet)")
    d.heading("Graphics", 2)
    gl = [f"{g['concept']} ({g.get('status', '')})" for g in f["graphics"]] + [x for x in (sb["graphics"] or "").splitlines() if x.strip()]
    for g in gl or ["(none yet)"]:
        d.para(g)


def export(path, rec, M, labels, effort="", marking=None):
    """A Word storyboard: one section, or several (a page each). Returns the path."""
    import docxw
    d = docxw.Doc()
    d.marking = marking
    d.props = {"StationkeeperStoryboard": effort}
    for k, lab in enumerate(labels):
        if k:
            d.page_break()
        _sheet(d, rec, M, lab, effort)
    d.save(path)
    return path
