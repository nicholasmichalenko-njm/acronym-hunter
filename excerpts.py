"""Excerpts and bins (3.21.0): every capture keeps the customer's exact words and exactly where they sit.

An excerpt is the words picked in Review (part of a sentence, a sentence, or several sentences, next to each other or
not), each part with its document, version, page, paragraph, the RFP's numbering and the heading it sits under. It sits
in a bin: a built-in one (Submission, Other submission detail, Formatting, Customer objectives, Key points, and the
captures Review always had: contact, acronym, customer question, key date, evaluation factor, page limit, deliverable,
effort detail, hot button, graphic need) or one the team made (a custom bin, with a color, a key, and where it feeds).

A sentence keeps one decision (L, M, SOW, support, the customer's, ignore), which drives the matrix; it can sit in any
number of bins, which drive everything else. An excerpt carries a value only when one exists (a date, an e-mail, a
font size); Formatting excerpts are measured (a value) or written (text kept verbatim: a phrase check where one fits,
else a Final Checks item). A customer objective maps to the sections that answer it; 3.29.1: every capture can be placed in sections of the
structure, and follows them when the structure changes.

Kept in the effort record (record.json: "excerpts", and "bins" for the effort's own bins); a bin shared with the team
travels in a team pack (team_bins.json). Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, re, uuid

# key, name, what it feeds (shown to people), page-mark tag
BUILTIN = (("submit", "Submission", "Submission Rules and the dashboard dates"),
           ("other", "Other submission detail", "Submission Rules (listed, no rule needed)"),
           ("format", "Formatting", "Production Standards (measured) or a check (written)"),
           ("objective", "Customer objectives", "a matrix column, the setup, the Wall of Truth and the dashboard"),
           ("keypoint", "Key points", "the setup, win themes, the Wall of Truth and author briefs"),
           ("contact", "Contact", "Customer information"),
           ("acronym", "Acronym", "the effort's acronym list"),
           ("question", "Customer question", "Customer Q&A"),
           ("keydate", "Key date", "the effort calendar"),
           ("factor", "Evaluation factor", "Evaluation and hot buttons"),
           ("pagelimit", "Page limit", "the page allocation"),
           ("deliverable", "Deliverable", "the deliverables board"),
           ("detail", "Effort detail", "the Effort Record"),
           ("hot", "Hot button", "Evaluation and hot buttons"),
           ("graphic", "Graphic need", "Graphic needs"),
           ("unit", "Unit of measurement", "the Units of Measurement table"))          # 3.31.0
NAME = {k: n for k, n, _f in BUILTIN}
FEEDS_TEXT = {k: f for k, _n, f in BUILTIN}
BIN_KEYS = {"objective": "O", "keypoint": "K"}            # the two new bins most used while reading get their own key
FEEDS = (("setup", "Response Setup"), ("matrix", "a matrix column"), ("truth", "Wall of Truth"), ("dashboard", "Overview"))
COLORS = ("#7C3AED", "#0E7490", "#B45309", "#BE185D", "#15803D", "#1D4ED8", "#9F1239", "#4D7C0F", "#6D28D9")
FORMAT_KINDS = (("measured", "Measured (a value: font, margins, page limit)"), ("written", "Written (text: a marking, a label, a phrase)"))
WRITTEN_CHECKS = (("phrase", "A phrase check (Audit looks for these words)"), ("final", "A Final Checks item (someone ticks it)"))
TEAM_FILE = "team_bins.json"


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _who(who=None):
    return who or getpass.getuser()


def _clean(t, n=400):
    return " ".join(str(t or "").split())[:n]


# ------------------------------------------------------------------ bins
def custom_bins(rec):
    return [b for b in rec.data.get("bins", []) if isinstance(b, dict) and b.get("id")]


def team_bins(config_dir):
    """The bins shared with the team on this PC (installed from a team pack, or shared from an effort)."""
    import json, os
    try:
        with open(os.path.join(config_dir, TEAM_FILE), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError, TypeError):
        return []
    return [_bin_clean(b) for b in d if isinstance(b, dict) and b.get("name")] if isinstance(d, list) else []


def save_team_bins(config_dir, lst):
    import json, os
    out, seen = [], set()
    for b in lst:
        b = _bin_clean(b)
        if b["name"] and b["name"].casefold() not in seen:
            seen.add(b["name"].casefold()); out.append(b)
    os.makedirs(config_dir, exist_ok=True)
    tmp = os.path.join(config_dir, TEAM_FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(config_dir, TEAM_FILE))
    return out


def _bin_clean(b):
    name = _clean(b.get("name"), 40)
    color = b.get("color") if re.match(r"^#[0-9A-Fa-f]{6}$", str(b.get("color") or "")) else COLORS[0]
    feeds = [f for f in (b.get("feeds") or []) if f in dict(FEEDS)]
    bid = str(b.get("id") or "") or "c_" + re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")[:24]
    return {"id": bid, "name": name, "color": color, "feeds": feeds, "about": _clean(b.get("about"), 200),
            "shared": bool(b.get("shared"))}


def bins(rec, config_dir=None):
    """Every bin: [{"id", "name", "builtin", "color", "feeds", "key"}]; the effort's own bins, then the team's (a team
    bin the effort already has by name shows once). Custom bins get the keys Alt+1 to Alt+9 in order."""
    out = [{"id": k, "name": n, "builtin": True, "color": "", "feeds": [], "about": FEEDS_TEXT[k], "key": BIN_KEYS.get(k, "")}
           for k, n, _f in BUILTIN]
    have = set()
    custom = []
    for b in custom_bins(rec):
        custom.append(dict(_bin_clean(b), builtin=False)); have.add(custom[-1]["name"].casefold())
    for b in (team_bins(config_dir) if config_dir else []):
        if b["name"].casefold() not in have:
            custom.append(dict(b, builtin=False, team=True)); have.add(b["name"].casefold())
    for i, b in enumerate(custom):
        b["key"] = f"Alt+{i + 1}" if i < 9 else ""
    return out + custom


def bin_name(rec, bid, config_dir=None):
    if bid in NAME:
        return NAME[bid]
    b = next((x for x in bins(rec, config_dir) if x["id"] == bid), None)
    return b["name"] if b else bid


def add_bin(rec, name, color="", feeds=(), about="", who=None):
    """A bin of this effort's own. Returns its id (None without a name, or when the name is taken)."""
    name = _clean(name, 40)
    if not name or name.casefold() in {n.casefold() for n in NAME.values()} or \
            name.casefold() in {b["name"].casefold() for b in custom_bins(rec)}:
        return None
    used = {b.get("color") for b in custom_bins(rec)}
    color = color or next((c for c in COLORS if c not in used), COLORS[len(used) % len(COLORS)])
    b = _bin_clean({"name": name, "color": color, "feeds": list(feeds), "about": about})
    base, n = b["id"], 2
    while any(x["id"] == b["id"] for x in custom_bins(rec)) or b["id"] in NAME:
        b["id"] = f"{base}_{n}"; n += 1
    b.update(created=_now(), by=_who(who))
    rec.data.setdefault("bins", []).append(b)
    rec.log("effort", f"Bin added: {name}", who=who)
    rec.save()
    return b["id"]


def update_bin(rec, bid, **f):
    b = next((x for x in custom_bins(rec) if x["id"] == bid), None)
    if b is None:
        return False
    if "name" in f and _clean(f["name"], 40):
        b["name"] = _clean(f["name"], 40)
    if "color" in f and re.match(r"^#[0-9A-Fa-f]{6}$", str(f["color"] or "")):
        b["color"] = f["color"]
    if "feeds" in f:
        b["feeds"] = [x for x in f["feeds"] if x in dict(FEEDS)]
    if "about" in f:
        b["about"] = _clean(f["about"], 200)
    rec.save()
    return True


def remove_bin(rec, bid):
    """Takes the effort's bin out; its excerpts stay, under Other until put in another bin. Returns how many moved."""
    before = len(rec.data.get("bins", []))
    rec.data["bins"] = [b for b in rec.data.get("bins", []) if b.get("id") != bid]
    if len(rec.data["bins"]) == before:
        return None
    n = 0
    for x in rec.data.get("excerpts", []):
        if x.get("bin") == bid:
            x["bin"] = "other"; n += 1
    rec.save()
    return n


def share_bin(rec, bid, config_dir):
    """Share the effort's bin with the team on this PC (it travels in the next team pack)."""
    b = next((x for x in custom_bins(rec) if x["id"] == bid), None)
    if b is None:
        return False
    b["shared"] = True
    rec.save()
    save_team_bins(config_dir, [x for x in team_bins(config_dir) if x["name"].casefold() != b["name"].casefold()] + [b])
    return True


# ------------------------------------------------------------------ excerpts
# 3.41.0: where a capture came from. Reviewers can test where a theme came from; a capture made before 3.41 came from a
# customer document (Review was the only way in).
SOURCES = (("customer", "Customer document"), ("meeting", "Meeting"), ("intel", "Capture intel"), ("qa", "Customer Q&A answer"))
SOURCE_NAME = dict(SOURCES)


def part_from_meeting(m, words):
    """One part of a capture from a meeting's notes: the words, the meeting's title and date, who was there."""
    return {"sid": "", "source": "meeting", "mid": m.get("id", ""), "doc": _clean(f"Meeting: {m.get('title', 'Meeting')}", 200),
            "version": _clean(m.get("date", ""), 60), "page": "", "para": "", "loc": _clean(", ".join(m.get("participants") or []), 200),
            "num": "", "heading": "", "text": str(words or "").strip()[:4000]}


def part_from_file(name, words, page="", para="", heading=""):
    """One part of a capture from a capture file (capture intel: call notes, a capture plan, a competitor brief)."""
    return {"sid": "", "source": "intel", "doc": _clean(f"Capture file: {name}", 200), "version": "", "page": _clean(page, 10),
            "para": _clean(para, 10), "loc": "", "num": "", "heading": _clean(heading, 160), "text": str(words or "").strip()[:4000]}


def part_from_answer(q):
    """One part of a capture from the customer's answer to one of our questions (Customer Q&A)."""
    doc = f"Customer Q&A {q.get('n', '')} answer" + (f" ({q['answer_doc']})" if q.get("answer_doc") else "")
    return {"sid": q.get("sid", ""), "source": "qa", "qid": q.get("id", ""), "doc": _clean(doc, 200), "version": "", "page": "",
            "para": "", "loc": _clean(q.get("section", ""), 200), "num": "", "heading": "", "text": str(q.get("answer", "")).strip()[:4000]}


def source_of(x):
    """'customer', 'meeting', 'intel' or 'qa'."""
    s = x.get("source") or next((p.get("source") for p in x.get("parts", []) if p.get("source")), "")
    return s if s in SOURCE_NAME else "customer"


def part_of(it, doc="", page="", para="", loc="", version="", words=""):
    """One part of an excerpt from a matrix sentence (and where it sits on the page, when known)."""
    return {"sid": str(it.get("id", "")), "doc": _clean(doc or it.get("file", ""), 200), "version": _clean(version, 60),
            "page": _clean(page or it.get("page", ""), 10), "para": _clean(para, 10), "loc": _clean(loc or it.get("loc", ""), 200),
            "num": _clean(it.get("section", ""), 40), "heading": _clean(it.get("section_title", ""), 160),
            "text": str(words or it.get("text", "")).strip()[:4000]}


def excerpts(rec, bin_id=None):
    xs = [x for x in rec.data.get("excerpts", []) if isinstance(x, dict) and x.get("id")]
    return [x for x in xs if bin_id is None or x.get("bin") == bin_id]


def get(rec, xid):
    return next((x for x in excerpts(rec) if x["id"] == xid), None)


def text_of(x):
    """The customer's words, verbatim; parts that are not next to each other are joined with an ellipsis. 3.29.0: a
    list's lead-in carried with an item reads straight into it ("The objectives are to: reduce cost.")."""
    out, prev_intro = "", False
    for p in x.get("parts", []):
        t = p.get("text", "")
        if not t:
            continue
        out += (t if not out else ((" " if prev_intro else " ... ") + t))
        prev_intro = bool(p.get("intro"))
    return out


def lead_groups(parts, lead_of):
    """3.29.0: the objectives a selection makes when it holds a list. Each list item is its own objective and carries
    the list's lead-in ("The Government's objectives are to:"), either a selected sentence ending in a colon (it leads
    the parts after it) or the lead-in the reader kept on the item (lead_of(sid) -> a part, or None). [[parts], ...]:
    one group per item, the lead-in first and marked intro; one group with every part when nothing leads a list."""
    groups, intro, any_lead = [], None, False
    for p in parts:
        t = (p.get("text") or "").strip()
        if t.endswith(":") and p is not parts[-1]:
            intro = dict(p, intro=True)
            any_lead = True
            continue
        lead = intro or lead_of(p.get("sid", ""))
        if lead:
            any_lead = True
            groups.append([dict(lead, intro=True), p])
        else:
            groups.append([p])
    if not any_lead:
        return [list(parts)] if parts else []
    return groups


def where_of(x):
    """Where the words sit, part by part: 'Section_L.pdf p.14 para 3, L.5.2 Submission Instructions'."""
    out = []
    for p in x.get("parts", []):
        bits = [p.get("doc", "")]
        if p.get("version"):
            bits.append(f"({p['version']})")
        if p.get("page"):
            bits.append(f"p.{p['page']}")
        if p.get("para"):
            bits.append(f"para {p['para']}")
        head = " ".join(b for b in (p.get("num", ""), p.get("heading", "")) if b)
        s = " ".join(b for b in bits if b) + (f", {head}" if head else "")
        if not p.get("page") and p.get("loc") and p["loc"] not in s:
            s += f" ({p['loc']})"
        if s and s not in out:
            out.append(s)
    return "; ".join(out)


def add(rec, bin_id, parts, value="", note="", sub="", sections=(), ref="", who=None, source=""):
    """An excerpt in a bin. parts: [part_of(...)]; value: only when one exists; sub: for Formatting, measured or written
    (written: check phrase or final in 'check'); sections: for an objective, the sections that answer it; ref: what the
    capture filed (a rule key, or a list of them); source (3.41.0): customer, meeting, intel or qa (else from the parts).
    Returns its id (None with no words)."""
    parts = [p for p in (parts or []) if (p.get("text") or "").strip()]
    if not parts or not bin_id:
        return None
    x = {"id": uuid.uuid4().hex[:10], "bin": str(bin_id), "parts": parts, "value": _clean(value, 400), "note": _clean(note, 1000),
         "sub": sub if sub in dict(FORMAT_KINDS) else "", "check": "", "sections": [_clean(s, 200) for s in sections if _clean(s, 200)],
         "refs": [_clean(r, 200) for r in ([ref] if isinstance(ref, str) else (ref or [])) if _clean(r, 200)], "text_only": False, "at": _now(), "by": _who(who)}
    x["source"] = source if source in SOURCE_NAME else source_of({"parts": parts})     # 3.41.0
    if x["bin"] == "format" and not x["sub"]:
        x["sub"] = "measured" if x["value"] else "written"
    if x["sub"] == "written":
        x["check"] = written_check(text_of(x))
    rec.data.setdefault("excerpts", []).append(x)
    rec.save()
    return x["id"]


def update(rec, xid, who=None, **f):
    """Change an excerpt: value, note, bin, sub, check, sections, text_only, or the words of a part ({'part': i, 'text'})."""
    x = get(rec, xid)
    if x is None:
        return False
    if "value" in f:
        x["value"] = _clean(f["value"], 400)
    if "note" in f:
        x["note"] = _clean(f["note"], 1000)
    if f.get("bin"):
        x["bin"] = str(f["bin"])
    if "sub" in f and f["sub"] in ("", "measured", "written"):
        x["sub"] = f["sub"]
        if x["sub"] == "written" and not x.get("check"):
            x["check"] = written_check(text_of(x))
    if "check" in f and f["check"] in ("", "phrase", "final"):
        x["check"] = f["check"]
    if "sections" in f:
        x["sections"] = [_clean(s, 200) for s in f["sections"] if _clean(s, 200)]
    if "text_only" in f:
        x["text_only"] = bool(f["text_only"])
    if "part" in f and 0 <= int(f["part"]) < len(x.get("parts", [])) and str(f.get("text") or "").strip():
        x["parts"][int(f["part"])]["text"] = str(f["text"]).strip()[:4000]
    x["edited"], x["edited_by"] = _now(), _who(who)
    rec.save()
    return True


def remove(rec, xid):
    n = len(rec.data.get("excerpts", []))
    rec.data["excerpts"] = [x for x in rec.data.get("excerpts", []) if x.get("id") != xid]
    if len(rec.data["excerpts"]) < n:
        rec.save()
        return True
    return False


def of_sentence(rec, sid):
    """The excerpts that hold words of this sentence."""
    return [x for x in excerpts(rec) if any(p.get("sid") == sid for p in x.get("parts", []))]


def bins_of(rec):
    """{sentence id: [bin ids]} for the page marks."""
    out = {}
    for x in excerpts(rec):
        for p in x.get("parts", []):
            got = out.setdefault(p.get("sid", ""), [])
            if x["bin"] not in got:
                got.append(x["bin"])
    out.pop("", None)
    return out


def counts(rec):
    out = {}
    for x in excerpts(rec):
        out[x["bin"]] = out.get(x["bin"], 0) + 1
    return out


def place(rec, xids, label, on=True, only=False, who=None):
    """3.29.1: put captures in a section of the structure (on), take them out of it (on=False), or make it their only
    section (only). Returns how many changed."""
    n = 0
    lab = _clean(label, 200)
    for x in excerpts(rec):
        if x["id"] not in xids or not lab:
            continue
        cur = list(x.get("sections") or [])
        new = [lab] if only else ((cur + [lab]) if on and lab not in cur else ([s for s in cur if s != lab] if not on else cur))
        if new != cur:
            x["sections"] = new
            x["edited"] = _now(); x["edited_by"] = _who(who)
            n += 1
    if n:
        rec.save()
    return n


def in_section(rec, label):
    """3.29.1: the captures placed in a section."""
    return [x for x in excerpts(rec) if label in (x.get("sections") or [])]


def section_counts(rec):
    """3.29.1: {section label: captures placed in it}."""
    out = {}
    for x in excerpts(rec):
        for s in x.get("sections") or []:
            out[s] = out.get(s, 0) + 1
    return out


def relabel(rec, mapping):
    """3.29.1: captures and topics follow their sections when the structure renames, renumbers, moves or takes one out
    (a section taken out: to the section its sentences went to, or out of the structure). Returns how many changed."""
    n = 0
    for lst in (excerpts(rec), [t for t in rec.data.get("topics", []) if isinstance(t, dict)]):
        for x in lst:
            cur = list(x.get("sections") or [])
            if not any(s in mapping for s in cur):
                continue
            new = []
            for s in cur:
                t = mapping.get(s, s)
                if t and t not in new:
                    new.append(t)
            x["sections"] = new
            n += 1
    if n:
        rec.save()
    return n


def sections_state(rec):
    """3.29.1: {capture or topic id: its sections}, for Review's Undo."""
    return {x["id"]: list(x.get("sections") or []) for x in excerpts(rec) + [t for t in rec.data.get("topics", [])
                                                                              if isinstance(t, dict) and t.get("id")]}


def restore_sections(rec, state):
    n = 0
    for x in excerpts(rec) + [t for t in rec.data.get("topics", []) if isinstance(t, dict) and t.get("id")]:
        if x["id"] in state and list(x.get("sections") or []) != state[x["id"]]:
            x["sections"] = list(state[x["id"]]); n += 1
    if n:
        rec.save()
    return n


def objectives_unmapped(rec):
    return [x for x in excerpts(rec, "objective") if not x.get("sections")]


def for_rule(rec, key):
    """The excerpts filed with a submission or formatting rule (by the rule's key)."""
    return [x for x in excerpts(rec) if key in (x.get("refs") or [])]


# ------------------------------------------------------------------ written formatting rules
_PHRASE = re.compile(r"[\"“]([^\"”]{3,120})[\"”]")
_MARK = re.compile(r"\b(?:mark(?:ed|ing)?|banner|label(?:ed)?|legend|header|footer|portion mark)", re.I)


def written_check(text):
    """How a written formatting rule is checked: 'phrase' when it quotes the words to carry (a marking, a legend), so
    Audit can look for them; else 'final', an item on Final Checks for someone to tick."""
    return "phrase" if (_PHRASE.search(text or "") and _MARK.search(text or "")) else "final"


def phrase_of(text):
    """The quoted words a written rule says to carry ('' when it quotes none)."""
    m = _PHRASE.search(text or "")
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------ 3.29.0: what review feeds
def promote(rec, xid, who=None):
    """An objective or key point on the effort's Wall of Truth (a Fact: its words, with where they sit as the source).
    Returns the truth's id; one already promoted returns its truth."""
    import walloftruth as WT
    x = get(rec, xid)
    if x is None:
        return ""
    if x.get("truth") and WT.get(rec, x["truth"]):
        return x["truth"]
    words = text_of(x)
    label = (x.get("note") or " ".join(words.split()[:8])).strip()
    tid = WT.add(rec, label, words, kind="Fact", source=where_of(x), notes=f"From Shred: {NAME.get(x['bin'], x['bin'])}", who=who)
    if tid:
        x["truth"] = tid
        rec.save()
    return tid


def written_rules(rec):
    """Written formatting excerpts: [{"id", "text", "where", "check": phrase|final, "phrase", "done", "by", "at"}]."""
    out = []
    for x in excerpts(rec, "format"):
        if x.get("sub") != "written":
            continue
        t = text_of(x)
        out.append({"id": x["id"], "text": t, "where": where_of(x), "check": x.get("check") or written_check(t),
                    "phrase": phrase_of(t), "done": bool(x.get("done")), "by": x.get("done_by", ""), "at": x.get("done_at", "")})
    return out


def tick(rec, xid, on=True, who=None):
    """A Final Checks item ticked (or unticked) by someone."""
    x = get(rec, xid)
    if x is None:
        return False
    x["done"] = bool(on)
    x["done_by"], x["done_at"] = (_who(who), _now()) if on else ("", "")
    rec.save()
    return True


def phrase_in(path, phrase):
    """3.29.0: where a Word draft carries the phrase: {"body": n, "headers": n, "footers": n} (read only)."""
    import zipfile
    out = {"body": 0, "headers": 0, "footers": 0}
    if not phrase:
        return out
    want = " ".join(phrase.split()).casefold()
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        return out
    for n in z.namelist():
        if not n.startswith("word/") or not n.endswith(".xml"):
            continue
        k = "headers" if n.startswith("word/header") else "footers" if n.startswith("word/footer") else "body" if n == "word/document.xml" else None
        if k is None:
            continue
        txt = " ".join("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m)) for m in re.findall(r"<w:p[ >].*?</w:p>", z.read(n).decode("utf-8", "replace"), re.S))
        out[k] += " ".join(txt.split()).casefold().count(want)
    return out
