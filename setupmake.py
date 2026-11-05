"""The Setup page's rules (3.56.0, claude/stationkeeper-setup-decisions-2026-11-04.md): the setup is made from a structure,
layers and a template, and remade whenever one changes. A structure is the least it needs: headings typed, from a Word
outline, or from an RFP's headings, with no review. Layers say what fills each section: requirements, evaluation, PM
direction, pages, author and due date on by default; customer context, meeting notes and captures, topics when turned on.
Changes per author: what changed in each person's sections since the last setup, one Word file each.

layers(M) / set_layer(M, key, on) / due(M, label) / set_due / direction / set_direction / people / set_people /
structure_from_text / structure_from_docx / structure_from_rfp / start(path, name, text) / author_packets(M, folder).
Kept in the matrix's setup (layers, layer_skip, due: additive keys). Rules only; nothing leaves the PC."""
import os, re, zipfile

import setupdoc as SD

# key, what it is, the kinds it leaves out when off (setupdoc's kinds; req, eval, pages, author are the Setup page's own
# markers: requirements and evaluation both print as RFP text), on by default
LAYERS = (("requirements", "Requirements", ("req", "support"), True),
          ("evaluation", "Evaluation criteria", ("eval",), True),
          ("pm", "PM direction", ("pm",), True),
          ("pages", "Pages", ("pages",), True),
          ("author", "Author and due date", ("author",), True),
          ("customer", "Customer context", ("customer", "library", "objective"), False),
          ("captures", "Meeting notes and captures", ("capture",), False),
          ("topics", "Topics", ("topic",), False))
LAYER = {k: (t, kinds, on) for k, t, kinds, on in LAYERS}


def layers(M):
    """{key: on} for every layer (the defaults where none was set)."""
    got = SD.setup_of(M).get("layers") or {}
    return {k: bool(got.get(k, on)) for k, _t, _kinds, on in LAYERS}


def set_layer(M, key, on):
    S = SD.setup_of(M)
    cur = layers(M)
    if key in cur:
        cur[key] = bool(on)
    S["layers"] = cur
    S["layer_skip"] = sorted({k for lk, v in cur.items() if not v for k in LAYER[lk][1]})
    if hasattr(M, "pending"):
        M.pending = True
    return cur


def ensure_skip(M):
    """The kinds the layers leave out, kept beside the layers (setuptemplate reads them)."""
    S = SD.setup_of(M)
    cur = layers(M)
    S["layer_skip"] = sorted({k for lk, v in cur.items() if not v for k in LAYER[lk][1]})
    return S["layer_skip"]


def due(M, label):
    return (SD.setup_of(M).get("due") or {}).get(label, "")


def set_due(M, label, when):
    S = SD.setup_of(M)
    d = S.setdefault("due", {})
    when = " ".join(str(when or "").split())
    if when:
        d[label] = when
    else:
        d.pop(label, None)
    if hasattr(M, "pending"):
        M.pending = True


def direction(M, label):
    return SD.setup_of(M)["mgmt"].get(label, "")


def set_direction(M, label, text):
    S = SD.setup_of(M)
    text = (text or "").strip()
    if text:
        S["mgmt"][label] = text
    else:
        S["mgmt"].pop(label, None)
    if hasattr(M, "pending"):
        M.pending = True


def people(M, label):
    p = SD.setup_of(M)["owners"].get(label) or {}
    return p.get("lead", ""), p.get("with", "")


def set_people(M, label, lead, with_=""):
    SD.set_people(M, label, lead, with_)
    if hasattr(M, "pending"):
        M.pending = True


def sections(M):
    """[(label, level)] the structure in order."""
    import compliance as C
    return [(C.outline_label(o), int(o.get("level", 1) or 1)) for o in M.outline]


def preview(M, label):
    """[(layer title, what the section prints for it)] for the layers that are on."""
    import pagebudget as PB
    on = layers(M)
    B = SD.by_id(M)
    got = [B[i] for i in SD.placed_in(M).get(label, []) if i in B]
    n = {}
    for it in got:
        n[SD.kind_of(it)] = n.get(SD.kind_of(it), 0) + 1
    out = []
    if on["requirements"]:
        out.append(("Requirements", f"{n.get('Requirement', 0)} requirement(s), {n.get('Context', 0)} support"))
    if on["evaluation"]:
        out.append(("Evaluation criteria", f"{n.get('Evaluation', 0)} placed here"))
    if on["pm"]:
        d = direction(M, label)
        out.append(("PM direction", (d[:140] + ("..." if len(d) > 140 else "")) if d else "none yet"))
    if on["pages"]:
        pg = PB.pages(M, label)
        out.append(("Pages", f"{pg:g}" if pg else "not set"))
    if on["author"]:
        p = SD.section_people(M, label)
        who = p["lead"] or "no lead yet"
        if p["from"] and p["from"] != label:
            who += f" (from {p['from']})"
        out.append(("Author and due date", who + (f", contributors {p['with']}" if p["with"] else "")
                    + ", due " + (due(M, label) or "not set")))
    if on["customer"]:
        out.append(("Customer context", f"{n.get('Customer', 0)} customer sentence(s), objectives and library context"))
    if on["captures"]:
        out.append(("Meeting notes and captures", "the captures placed here in Review"))
    if on["topics"]:
        out.append(("Topics", "the topics this section answers"))
    return out


def gaps(M):
    """{"no_lead": [labels], "no_due": [labels]} sections still missing a lead or a due date (leaf sections inherit)."""
    out = {"no_lead": [], "no_due": []}
    for lab, _lv in sections(M):
        if not SD.section_people(M, lab)["lead"]:
            out["no_lead"].append(lab)
        if not due(M, lab):
            out["no_due"].append(lab)
    return out


# ------------------------------------------------------------------ a structure with no review
def structure_from_text(text):
    import compliance as C
    return C.parse_outline(text or "")


def structure_from_docx(path):
    """The headings of a Word outline, as outline text."""
    import compliance as C
    with zipfile.ZipFile(path) as z:
        out = C.outline_from_docx_xml(z.read("word/document.xml"))
    return C.outline_text(out) if out else ""


def structure_from_rfp(path):
    """The structure an RFP prescribes, else its Section L headings, else its numbered headings, as outline text
    (the same choices Read into Review offers; nothing is kept)."""
    import app_gui as A
    import compliance as C
    import structstart as SS
    name = os.path.basename(path)
    heads = []
    items = C.extract([(name, A.typed_chunks(path))], heads, every=False)
    tmp = C.Matrix(path, name)
    tmp.items, tmp.headings = items, heads
    ol = SS.prescribed(tmp)[0] or C.outline_from_headings(heads, "L") or C.outline_from_headings(heads, "")
    return C.outline_text(ol) if ol else ""


def start(path, name, text):
    """A compliance matrix holding only the structure (the Review fills it later). Returns it, saved."""
    import compliance as C
    M = C.Matrix(path, name)
    M.outline = structure_from_text(text)
    SD.setup_of(M)
    ensure_skip(M)
    M.save()
    return M


# ------------------------------------------------------------------ changes per author (decision 5)
def changes_by_person(M):
    """{person: [(label, kind, text)]} what changed since the last setup, by each section's lead and contributors;
    sections with nobody named go to "(no author named)". None when no setup was made yet."""
    ch = SD.changes_since_last(M)
    if ch is None:
        return None
    out = {}
    for lab, kind, _iid, text in ch:
        p = SD.section_people(M, lab)
        names = [p["lead"]] + [x.strip() for x in (p["with"] or "").split(",")]
        names = [n for n in names if n] or ["(no author named)"]
        for n in names:
            out.setdefault(n, []).append((lab, kind, text))
    return out


def author_packets(M, folder, when=None):
    """One Word file per person with the changes in their sections. Returns the paths ([] when nothing changed)."""
    import datetime
    import docxw
    got = changes_by_person(M)
    if not got:
        return [] if got is not None else None
    when = when or datetime.datetime.now()
    os.makedirs(folder, exist_ok=True)
    paths = []
    for person, rows in sorted(got.items()):
        d = docxw.Doc()
        d.heading(f"Setup changes for {person}", 1)
        d.para(f"{when:%Y-%m-%d %H:%M}: what changed in your sections since the last setup.", color="6B7280")
        cur = None
        for lab, kind, text in rows:
            if lab != cur:
                d.heading(lab, 2); cur = lab
            d.rich([(kind + ": ", {"bold": True}), (text or "", {})])
        safe = re.sub(r"[^A-Za-z0-9 _.-]+", "", person).strip() or "No author"
        p = os.path.join(folder, f"Setup changes - {safe} - {when:%Y-%m-%d %H%M}.docx")
        d.save(p)
        paths.append(p)
    S = SD.setup_of(M)                              # changes handed over: the next comparison starts here
    S["exports"][-1].update(SD.snapshot(M))
    S["exports"][-1]["changes_exported"] = f"{when:%Y-%m-%d %H:%M}"
    if hasattr(M, "pending"):
        M.pending = True
    return paths
