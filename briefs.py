"""Author briefs (2.43.0): what a new customer version changed for each person, from its impact review (impact.py).

One brief per person the version touches:
- Your sections: compliance sentences changed or removed in the sections they own or lead or contribute to, quoted
  old and new; new sentences in an RFP section that feeds one of their sections (not assigned yet); an RFP heading
  renamed that one of their sections was named for.
- Your deliverables: a page limit or requirement that changed, a newer form version to fill, our file's page count.
- For everyone: due dates, page limits, format, file, copies and delivery rules the version changed.
- The due date and the days left.
A brief for Everyone holds the For everyone part alone, for the people the version did not touch directly.
Written from fixed sentences filled with the facts (rules only, no AI); nothing leaves the PC. Copy one, or save them
all as Word (one per page).
"""
import collections

EVERYONE = "Everyone"
FOR_ALL = ("Due", "Questions due", "Page limit", "Format", "File", "Copies", "Delivery")


def _q(s, n=300):
    s = " ".join((s or "").split())
    return f'"{s if len(s) <= n else s[:n - 3] + "..."}"'


def _num(section):
    return (section or "").split(" ", 1)[0]


def _new_brief(name):
    return {"to": name, "sections": collections.OrderedDict(), "deliverables": [], "everyone": []}


def build(r, matrix=None, owner_of=None, people_of=None):
    """{name: brief} in order of first appearance, then Everyone. owner_of(item) -> who writes it; people_of(label) ->
    {"lead", "with"} for a section (contributors get the brief too)."""
    owner_of = owner_of or (lambda it: it.get("owner", ""))
    people_of = people_of or (lambda label: {"lead": "", "with": ""})
    out = collections.OrderedDict()

    def who(label, owner=""):
        names = [" ".join(x.split()) for x in owner.replace(";", ",").split(",")] if owner else []   # 2.58.0: several authors
        p = people_of(label) if label else {"lead": "", "with": ""}
        names += [p.get("lead", "")] + [x.strip() for x in (p.get("with") or "").split(",")]
        seen = []
        for n in names:
            if n and n not in seen:
                seen.append(n)
        return seen

    def add(name, label, line):
        b = out.setdefault(name, _new_brief(name))
        b["sections"].setdefault(label or "Not placed in a section yet", []).append(line)

    c = r["compliance"]
    for x in c["changed"]:
        line = f"Changed ({x['id']}): was {_q(x['old'])}; now {_q(x['new'])}"
        for n in who(x["map"], x["owner"]):
            add(n, x["map"], line)
    for x in c["removed"]:
        line = f"Removed ({x['id']}): {_q(x['old'])} is no longer in the document. Keep, cut or change what answers it."
        for n in who(x["map"], x["owner"]):
            add(n, x["map"], line)
    feeds = collections.defaultdict(set)              # RFP section number -> our sections its sentences went to
    for it in (matrix.items if matrix is not None else []):
        if it.get("map") and it.get("section"):
            feeds[it["section"]].add(it["map"])
    for a in c["added"]:
        if a.get("map"):
            line = f"New ({a['id']}): {_q(a['text'])}"
            for n in who(a["map"], a.get("owner", "")):
                add(n, a["map"], line)
            continue
        num = _num(a["section"])
        for label in sorted(feeds.get(num, ())):
            line = f"New in RFP {num}, which this section answers (not assigned yet): {_q(a['text'])}"
            names = who(label, "")
            if not names and matrix is not None:
                names = sorted({" ".join(n.split()) for it in matrix.items if it.get("map") == label and owner_of(it)
                                for n in owner_of(it).replace(";", ",").split(",") if n.strip()})
            for n in names:
                add(n, label, line)
    for s in r["structure"]:
        if s["change"] == "renamed" and s["ours"]:
            line = f"RFP heading {s['num']} is now \"{s['now']}\" (was \"{s['was']}\"). This section was named for it: rename it to match?"
            for n in who(s["ours"]):
                add(n, s["ours"], line)
    for d in r["deliverables"]:
        if d["owner"]:
            out.setdefault(d["owner"], _new_brief(d["owner"]))["deliverables"].append(f"{d['name']}: " + "; ".join(d["why"]))
    everyone = []
    for x in r["requirements"]:
        if x["kind"] not in FOR_ALL:
            continue
        what = f"{x['kind']}, {x['subject']}"
        if x["change"] == "changed":
            everyone.append(f"{what}: was {x['was']}, now {x['now']}" if x["was"] else f"{what}: now {x['now']}")
        elif x["change"] == "removed":
            everyone.append(f"{what}: no longer in the document" + (f" (was {x['was']})" if x["was"] else ""))
        else:
            everyone.append(f"{what}: new, {x['now']}")
    for b in out.values():
        b["everyone"] = list(everyone)
    if everyone:
        out[EVERYONE] = _new_brief(EVERYONE)
        out[EVERYONE]["everyone"] = list(everyone)
    return out


def subject(r, b):
    return f"{r['doc']}, {r['version']}: what changed for " + ("the team" if b["to"] == EVERYONE else b["to"])


def text(r, b, due=""):
    """The brief as plain text, ready to paste into an email or a chat."""
    L = [f"Subject: {subject(r, b)}", ""]
    L.append(("Team," if b["to"] == EVERYONE else f"{b['to']},"))
    when = r["added"][:10]
    L.append(f"{r['version']} of {r['doc']} arrived ({r['file']}, added {when}). "
             + ("Here is what changed for everyone." if b["to"] == EVERYONE else "Here is what changed in your work."))
    if b["sections"]:
        L += ["", "YOUR SECTIONS"]
        for label, lines in b["sections"].items():
            L.append(label)
            L += [f"- {x}" for x in lines]
    if b["deliverables"]:
        L += ["", "YOUR DELIVERABLES"]
        L += [f"- {x}" for x in b["deliverables"]]
    if b["everyone"]:
        L += ["", "FOR EVERYONE"]
        L += [f"- {x}" for x in b["everyone"]]
    if not (b["sections"] or b["deliverables"] or b["everyone"]):
        L += ["", "Nothing in your sections or deliverables changed."]
    if due:
        L += ["", f"Proposal due {due}."]
    L += ["", "Questions: ask the proposal manager. The full impact review and the compare of the two versions are in "
              "Stationkeeper (Customer Documents > Impact)."]
    return "\n".join(L)


def counts(b):
    return {"sections": len(b["sections"]), "lines": sum(len(v) for v in b["sections"].values()),
            "deliverables": len(b["deliverables"]), "everyone": len(b["everyone"])}


def export_word(path, r, briefs, due="", effort_name=""):
    """Every brief, one per page."""
    import docxw
    d = docxw.Doc()
    GRAY, INK, NAVY = "64748B", "0F172A", "1E3A8A"
    first = True
    for b in briefs.values():
        if not first:
            d.page_break()
        first = False
        d.rich([(f"AUTHOR BRIEF  |  {effort_name}" if effort_name else "AUTHOR BRIEF", {"color": GRAY, "size": 18, "bold": True})])
        d.rich([("The team" if b["to"] == EVERYONE else b["to"], {"bold": True, "size": 36, "color": INK})])
        d.rich([(f"{r['version']} of {r['doc']} ({r['file']}, added {r['added'][:10]})" + (f"  |  Proposal due {due}" if due else ""),
                 {"color": GRAY, "size": 18})])
        if b["sections"]:
            d.heading("Your sections", 2)
            for label, lines in b["sections"].items():
                d.rich([(label, {"bold": True, "color": NAVY})])
                for x in lines:
                    d.para("- " + x)
        if b["deliverables"]:
            d.heading("Your deliverables", 2)
            for x in b["deliverables"]:
                d.para("- " + x)
        if b["everyone"]:
            d.heading("For everyone", 2)
            for x in b["everyone"]:
                d.para("- " + x)
        d.rich([("Made by Stationkeeper on this PC. Rules only, no AI. It quotes customer documents: share it the way you share "
                 "the proposal.", {"color": GRAY, "size": 16})])
    d.save(path)
    return path
