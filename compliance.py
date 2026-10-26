"""Compliance matrix (2.8.0), C1 extract and triage + C2 outline and mapping. Rules only: no language model.

Pipeline: the app's readers give [(location label, text)] per RFP file -> lines rejoined (PDF line wraps) -> section
numbers tracked (L.4.2.1, C.3.4, 3.2.1, "SECTION L") -> sentences and list items -> candidates by trigger words
(shall / must / will / should / may / is required to, imperatives, evaluation and format language) -> rule-based
actor, type, strength, cross-references and a Keep / Drop / Review suggestion. The person decides.

Items keep file, location, section and paragraph text, so every row cites its source. The matrix lives in one Excel
workbook (atomic save, re-read on open, edits made in Excel count). Nothing leaves the PC.
"""
import datetime, hashlib, json, os, re, tempfile

# ------------------------------------------------------------------ vocabulary
MODALS = r"shall not|must not|will not|may not|shall|must|will|should|may|is required to|are required to|is to|are to|is expected to|are expected to"
_MODAL = re.compile(r"\b(" + MODALS + r")\b", re.I)
IMPERATIVES = ("describe", "provide", "submit", "identify", "demonstrate", "discuss", "explain", "include", "address",
               "propose", "deliver", "furnish", "specify", "list", "present", "show", "ensure", "maintain", "comply",
               "state", "indicate", "define", "detail", "outline", "summarize", "prepare", "document", "certify",
               "complete", "sign", "attach", "use", "limit", "organize", "label", "number", "format", "do not")
_IMPER = re.compile(r"^(?:\(?[a-z0-9ivx]{1,4}[.)]\s*)?(" + "|".join(IMPERATIVES) + r")\b", re.I)
_EVAL = re.compile(r"\b(will|shall)\s+(?:be\s+)?(evaluat\w*|assess\w*|consider\w*|rat(?:e|ed)|review\w*|scor\w*)\b|"
                   r"\bevaluation (?:factor|criteri\w+|subfactor)|\bbasis (?:for|of) (?:award|evaluation)\b|"
                   r"\b(?:strength|weakness|deficienc\w+|acceptab\w+|unacceptab\w+)\b.*\b(?:assign|assess|rat)", re.I)
_FORMAT = re.compile(r"\b(page limit|pages?\b(?=.*\b(?:limit|exceed|maximum|not to exceed|no more than))|font|point size|"
                     r"\d+[- ]point|\d+(?:\.\d+)?[- ]?inch(?:es)? margins?|margins? of \d|single[- ]spaced|double[- ]spaced|8[.,]5\s*(?:x|by)\s*11|letter[- ]size|"
                     r"due (?:date|no later)|no later than|\bNLT\b|electronic copy|hard ?cop(?:y|ies)|\bcopies\b|"
                     r"file format|\.pdf\b|\bPDF\b|searchable|file size|naming convention|cover (?:page|letter)|"
                     r"table of contents|tab(?:bed)? divider|binder|page numbers?)", re.I)
OFFEROR = r"offerors?|proposers?|bidders?|vendors?|quoters?|respondents?|you|your proposal|the proposal|proposals|each volume|the volume|the response|responses|the submission|submissions|the quote|the bid"
CONTRACTOR = r"contractors?|the contractor|subcontractors?|the seller|the supplier|the developer|the provider"
GOVERNMENT = r"government|contracting officer|\bco\b|\bpco\b|\baco\b|agency|nasa|usaf|ussf|air force|space force|army|navy|dod|department|evaluators?|evaluation (?:team|board|panel)|source selection|\bssa\b|\bssEB\b|the panel|the board"
_OFF, _CON, _GOV = (re.compile(r"\b(" + p + r")\b", re.I) for p in (OFFEROR, CONTRACTOR, GOVERNMENT))
_XREF = re.compile(r"\b(?:Section|Sec\.|Paragraph|Para\.?|¶)\s+[A-Z]?(?:\.?\d+)+(?:\.\d+)*\b|"
                   r"\b[A-M]\.\d+(?:\.\d+)*\b|"
                   r"\bSection\s+[A-M]\b|"
                   r"\bAttachment\s+(?:J[- ]?)?[A-Z0-9]+(?:[- ][A-Z0-9]+)?\b|\bExhibit\s+[A-Z0-9]+\b|\bAppendix\s+[A-Z0-9]+\b|"
                   r"\bCDRL\s+[A-Z]?\d{2,4}\b|\bDID\s+[A-Z]+-[A-Z]+-\d+\b|\bDI-[A-Z]+-\d+[A-Z]?\b|"
                   r"\b(?:FAR|DFARS|NFS)\s+\d{1,3}\.\d{2,4}(?:-\d+)?\b|\b(?:MIL|DOD|NASA)-(?:STD|HDBK|SPEC)-\d+[A-Z]?\b|"
                   r"\b(?:SOW|PWS|SOO)\s+(?:paragraph\s+|para\.?\s+|section\s+)?\d+(?:\.\d+)*\b", re.I)
_ABBR = ("e.g.", "i.e.", "etc.", "U.S.", "No.", "Inc.", "vs.", "para.", "Para.", "Fig.", "fig.", "approx.", "Sec.", "sec.",
         "Corp.", "Co.", "Ltd.", "a.m.", "p.m.", "A.M.", "P.M.", "St.", "Mr.", "Ms.", "Dr.", "Jr.", "Sr.", "ea.", "Vol.", "vol.", "Rev.", "rev.", "al.", "Ref.")

# Section headings: "L.4.2.1 Technical Volume", "SECTION L - INSTRUCTIONS", "3.2.1 Thermal", "C.3 SCOPE"
_SEC_LETTER = re.compile(r"^\s*(?:SECTION\s+)?([A-M])\.((?:\d+\.)*\d+)\.?(?:\s+|$)(.*)$")
_SEC_WORD = re.compile(r"^\s*SECTION\s+([A-M])\b\s*[-–—:.]?\s*(.*)$", re.I)
_SEC_NUM = re.compile(r"^\s*((?:\d+\.)+\d+|\d+\.)\s+(.*)$")
_LIST = re.compile(r"^\s*(?:[•●▪◦·\-–*]|\(?[a-z]\)|\(?[ivx]{1,4}\)|\(?\d{1,2}\)|[a-z]\.(?=\s)|\(\d{1,2}\))\s+")
_INLINE_ITEM = re.compile(r"(?:(?<=[:;])|(?<=;\s)|(?<=\s))\(([a-z]|[ivx]{1,4}|\d{1,2})\)\s+")
_STOPW = set("""a an and or of the to for in on by with at as from is are be been shall must will should may that this these those
its it their his her our your any all each such which who whom than then also not no into within upon under over per
offeror offerors contractor government proposal provide describe include""".split())

DECISIONS = ("Keep", "Context", "Drop", "")      # 2.29.0: Context = not a requirement, but it gets a home too
TYPES = ("Instruction", "Evaluation", "SOW", "Format", "Information", "Requirement", "Context")
_BOILER = re.compile(r"^(?:page\s+\d+(?:\s+of\s+\d+)?|\d{1,4}|-\s*\d+\s*-|(?:un)?classified|cui|controlled unclassified information|"
                     r"for official use only|fouo|proprietary(?: information)?|source selection information|"
                     r"(?:solicitation|rfp)\s*(?:no\.?|number)?\s*[:#]?\s*[A-Z0-9-]+|draft|this page intentionally left blank)\.?$", re.I)


def context_item(text, lead, cur, label=""):
    """A sentence that is not a requirement (2.29.0): every sentence of the RFP becomes a row, so every one gets a
    decision. Repeated headers, footers, page numbers and markings are suggested Drop; the rest Context."""
    t = " ".join(text.split())
    if not re.search(r"[A-Za-z]{2}", t):
        return None
    boiler = bool(_BOILER.match(t)) or bool(re.search(r"\((?:Header|Footer)\b", label or ""))
    return {"text": t, "lead": lead if lead and lead != t else "", "section": cur[0], "section_title": cur[1],
            "actor": "", "type": "Context", "strength": "", "suggest": "Drop" if boiler else "Context", "modal": "",
            "xrefs": "; ".join(dict.fromkeys(m.group(0).strip() for m in _XREF.finditer(t) if m.group(0).strip() != cur[0])),
            "compound": False}


# ------------------------------------------------------------------ reading
def _join_lines(text):
    """PDF text wraps mid-sentence: join a line to the next unless it ends a sentence, is a heading or a list item."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")
            continue
        starts_block = bool(_LIST.match(line) or _SEC_LETTER.match(line) or _SEC_WORD.match(line) or
                            (_SEC_NUM.match(line) and len(line) < 140))
        if out and out[-1] and not starts_block and not re.search(r"[.:;?!]\s*$", out[-1]) and not _is_heading(out[-1]):
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)
    return out


def _is_heading(line):
    s = line.strip()
    if len(s) > 120 or s.endswith((".", ";", ",")) and not re.match(r"^[A-M]\.\d", s):
        return False
    if _SEC_WORD.match(s):
        return True
    m = _SEC_LETTER.match(s) or _SEC_NUM.match(s)
    if m:
        rest = m.groups()[-1]
        return not _MODAL.search(rest) and len(rest.split()) <= 14 and not rest.endswith(".")
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and len(s.split()) <= 10 and sum(c.isupper() for c in letters) / len(letters) > 0.8


def _label_section(label):
    """Word passages carry their heading in the label: "File.docx (section 'L.4 Technical', para 3-9)"."""
    m = re.search(r"section '([^']*)'", label)
    return m.group(1) if m else ""


def _page(label):
    m = re.search(r"\(p\.(\d+)", label)
    return int(m.group(1)) if m else None


def _sentences(par):
    """Split a paragraph into sentences without breaking at abbreviations, decimals or section numbers."""
    protected = par
    for a in _ABBR:
        protected = protected.replace(a, a.replace(".", "․"))
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])", protected)
    return [p.replace("․", ".").strip() for p in parts if p.strip()]


def _split_inline_list(sentence):
    """"The Offeror shall: (a) provide X; (b) describe Y; and (c) list Z." -> lead + items."""
    if ":" not in sentence:
        return sentence, []
    lead, rest = sentence.split(":", 1)
    marks = list(_INLINE_ITEM.finditer(" " + rest))
    if len(marks) < 2:
        return sentence, []
    items = []
    s = " " + rest
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(s)
        t = s[m.start():end].strip().rstrip(";,").strip()
        t = re.sub(r"[;,]?\s+and$|[;,]?\s+or$", "", t).strip()
        items.append(t)
    return lead.strip() + ":", items


def _section_from_line(line, cur):
    """(section, title, remaining text) when the line starts a numbered section or paragraph, else None."""
    m = _SEC_LETTER.match(line)
    if m:
        sec, rest = f"{m.group(1)}.{m.group(2)}", m.group(3).strip()
        if _is_heading(line):
            return sec, rest, ""
        parent_title = cur[1] if cur[0] and sec.startswith(cur[0]) else ""
        return sec, parent_title, rest                 # numbered paragraph: "L.4.2.1 The Offeror shall ..."
    m = _SEC_WORD.match(line)
    if m and _is_heading(line):
        return m.group(1).upper(), m.group(2).strip(), ""
    m = _SEC_NUM.match(line)
    if m:
        num, rest = m.group(1).rstrip("."), m.group(2).strip()
        if _is_heading(line):
            return num, rest, ""
        return num, (cur[1] if cur[0] and num.startswith(cur[0]) else ""), rest
    return None


def read_items(chunks, file_name, file_kind="", heads_out=None, every=True):
    """chunks: [(label, text)] from one file. file_kind: '' or a hint from the file name (Instruction / Evaluation / SOW).
    Returns items (dicts): the requirement candidates and, with every=True (2.29.0), every other sentence as Context."""
    items = []
    cur = ("", "")                                   # (section number, title)
    heads = {}                                       # heading number -> title, for numbered paragraphs under it

    def titled(sec, title):
        if title:
            heads[sec] = title
            if heads_out is not None and "." in sec:
                heads_out.append({"num": sec, "title": title, "file": file_name})
            return sec, title
        best = max((k for k in heads if sec == k or sec.startswith(k + ".")), key=len, default="")
        return sec, heads.get(best, "")
    for label, text in chunks:
        if not text:
            continue
        lab_sec = _label_section(label)
        if lab_sec:
            got = _section_from_line(lab_sec, cur)
            if got:
                cur = titled(got[0], got[1] or lab_sec)
            elif _is_heading(lab_sec):
                cur = (cur[0], lab_sec)
        lead_line = ""
        for line in _join_lines(text):
            if not line:
                lead_line = ""
                continue
            got = _section_from_line(line, cur)
            if got:
                cur = titled(got[0], got[1] if not got[2] else "")
                line = got[2]
                if not line:
                    continue
            elif _is_heading(line):
                cur = (cur[0], line.strip())
                continue
            is_item = bool(_LIST.match(line))
            body = _LIST.sub("", line, count=1) if is_item else line
            if is_item:
                body = re.sub(r"\s*[;,]\s*(?:and|or)?\s*$", "", body).strip()
            sents = [body] if is_item else _sentences(body)
            for s in sents:
                lead, sub = _split_inline_list(s)
                group = [(x, lead) for x in sub] if sub else [(s, lead_line if is_item else "")]
                for txt, ld in group:
                    if txt.rstrip().endswith(":") and not sub:
                        continue                         # a lead-in ("the Offeror shall:") is carried by its items
                    it = classify(txt, ld, cur, file_kind)
                    if it is None and every:
                        it = context_item(txt, ld, cur, label)
                    if it:
                        it.update({"file": file_name, "loc": label, "page": _page(label), "context": body[:700]})
                        items.append(it)
            if line.rstrip().endswith(":"):
                lead_line = (sents[-1] if sents else body) if not is_item else lead_line
            elif not is_item:
                lead_line = ""
    return items


def file_kind(name):
    n = name.lower().replace("_", " ")
    if re.search(r"\bsection l\b|instruction|\bl\b(?= )|proposal prep", n):
        return "Instruction"
    if re.search(r"\bsection m\b|evaluation|basis (?:for|of) award", n):
        return "Evaluation"
    if re.search(r"\bsow\b|\bpws\b|\bsoo\b|statement of (?:work|objectives)|performance work|\bsection c\b", n):
        return "SOW"
    return ""


# ------------------------------------------------------------------ classifying one sentence
def classify(text, lead, cur, kind_hint=""):
    t = " ".join(text.split())
    if len(t) < 12 or len(t) > 1500:
        return None
    probe = (lead + " " + t) if lead and not _MODAL.search(t) and not _IMPER.match(t) else t
    modal = _MODAL.search(probe)
    imper = _IMPER.match(t)
    ev = _EVAL.search(probe)
    fm = _FORMAT.search(t)
    if not (modal or imper or ev or (fm and re.search(r"\d", t))):
        return None
    word = modal.group(1).lower() if modal else ""
    # actor: the subject right before the modal; imperatives speak to the offeror
    actor = "Unclear"
    if modal:
        before = probe[:modal.start()][-90:]
        hits = [(m.start(), "Offeror") for m in _OFF.finditer(before)] + \
               [(m.start(), "Contractor") for m in _CON.finditer(before)] + \
               [(m.start(), "Government") for m in _GOV.finditer(before)]
        if hits:
            actor = max(hits)[1]
        elif imper:
            actor = "Offeror"
    elif imper:
        actor = "Offeror"
    sec = cur[0]
    letter = sec.split(".")[0] if sec and sec[0].isalpha() else ""
    kind = {"L": "Instruction", "M": "Evaluation", "C": "SOW"}.get(letter, kind_hint)
    if ev or (kind == "Evaluation" and actor == "Government"):
        typ = "Evaluation"
    elif fm and actor != "Government":
        typ = "Format"
    elif actor == "Government":
        typ = "Information"
    elif kind:
        typ = kind
    elif actor == "Contractor":
        typ = "SOW"
    elif actor == "Offeror" or imper:
        typ = "Instruction"
    else:
        typ = "Requirement"
    if typ == "Evaluation":
        strength = "Evaluation"
    elif actor == "Government":
        strength = "Information"
    elif word in ("shall", "must", "shall not", "must not", "is required to", "are required to", "is to", "are to", "may not", "will not") or \
            (imper and not word) or (word == "will" and actor != "Government"):
        strength = "Mandatory"
    elif word in ("should", "is expected to", "are expected to"):
        strength = "Desired"
    elif word == "may":
        strength = "Optional"
    elif actor == "Government":
        strength = "Information"
    else:
        strength = "Mandatory" if fm else "Check"
    if typ == "Information" or (actor == "Government" and typ != "Evaluation"):
        suggest = "Drop"
    elif strength == "Optional" or actor == "Unclear" and not fm and typ == "Requirement":
        suggest = "Review"
    else:
        suggest = "Keep"
    side = [m for m in _MODAL.finditer(t) if m.group(1).lower() in ("shall", "must", "will", "should")]
    compound = len(side) >= 2 or bool(re.search(r"\band\s+(?:shall|must|will)\b", t, re.I)) or \
        (bool(imper) and len(re.findall(r"[;]", t)) >= 1)
    return {"text": t, "lead": lead if lead and lead != t else "", "section": sec, "section_title": cur[1],
            "actor": actor, "type": typ, "strength": strength, "suggest": suggest, "modal": word or (imper.group(1).lower() if imper else ""),
            "xrefs": "; ".join(dict.fromkeys(m.group(0).strip() for m in _XREF.finditer(t) if m.group(0).strip() != sec)),
            "compound": compound}


def split_text(text):
    """Split a compound requirement at '; ' or at 'and shall / must / will' into its parts."""
    parts = re.split(r";\s+(?:and\s+)?|\s*,?\s+and\s+(?=(?:shall|must|will|should)\b)", text)
    parts = [p.strip().rstrip(".;,") for p in parts if p and len(p.strip()) > 3]
    if len(parts) < 2:
        return [text]
    subj = re.match(r"^(.*?\b(?:shall|must|will|should))\b", parts[0], re.I)
    head = subj.group(1).rsplit(" ", 1)[0] if subj else ""
    out = [parts[0] + "."]
    for p in parts[1:]:
        if head and re.match(r"^(shall|must|will|should)\b", p, re.I):
            p = head + " " + p
        out.append(p[0].upper() + p[1:] + ".")
    return out


# ------------------------------------------------------------------ the matrix
def text_key(text):
    return hashlib.sha1(re.sub(r"\W+", " ", text.lower()).strip().encode()).hexdigest()[:12]


def assign_ids(items):
    """Stable, readable IDs: section-based (L.4.2-03) or file-based (SOW-07)."""
    counts = {}
    used = {it["id"] for it in items if it.get("id")}
    for it in items:
        if it.get("id"):
            continue
        base = it["section"] or re.sub(r"[^A-Za-z0-9]+", "", os.path.splitext(it["file"])[0])[:10] or "REQ"
        n = counts.get(base, 0)
        while True:
            n += 1
            cand = f"{base}-{n:02d}"
            if cand not in used:
                break
        counts[base] = n
        it["id"] = cand
        used.add(cand)
    return items


def extract(files_chunks, headings=None, every=True):
    """files_chunks: [(file name, chunks)]. Returns items with IDs, links and suggestions.
    headings (list): filled with the RFP's numbered headings [{num, title, file}].
    every=True (2.29.0): every sentence is a row (requirements plus Context), so every sentence gets a decision."""
    items = []
    for name, chunks in files_chunks:
        items += read_items(chunks, name, file_kind(name), headings, every=every)
    seen, out = set(), []
    for it in items:                               # the same sentence repeated in a header or table: keep once
        k = (it["file"], text_key(it["text"]))
        if k in seen:
            continue
        seen.add(k)
        it.update({"key": text_key(it["text"]), "decision": "", "map": "", "owner": "", "status": "", "notes": "",
                   "response_page": "", "links": "", "new": "", "learned": ""})
        out.append(it)
    assign_ids(out)
    link_items(out)
    return out


def merge_reread(old, new):
    """Re-reading the RFP (an amendment): decisions, mapping and notes carry over to identical sentences.
    New sentences are marked; sentences no longer present are kept and marked 'Not in the latest read'."""
    by_fk = {(it.get("file", ""), it["key"]): it for it in old}
    by_key = {}
    for it in old:
        by_key.setdefault(it["key"], []).append(it)
    used_ids = {it["id"] for it in old}
    out, taken = [], set()
    new_fk = {(n.get("file", ""), n["key"]) for n in new}

    def match(it):
        """The same sentence in the same file first (a sentence repeated in two files stays two rows, 2.29.0), then the
        same sentence anywhere (an amendment that renamed the file)."""
        o = by_fk.get((it.get("file", ""), it["key"]))
        if o is not None and id(o) not in taken:
            return o
        return next((x for x in by_key.get(it["key"], []) if id(x) not in taken and
                     (x.get("file", ""), x["key"]) not in new_fk), None)
    for it in new:
        o = match(it)
        if o is not None:
            taken.add(id(o))
        if o:
            for f in ("id", "decision", "map", "owner", "status", "notes", "response_page", "text"):
                it[f] = o.get(f, "")
            it["new"] = ""
        else:
            it["new"] = "New in latest read"
            it["id"] = "" if it["id"] in used_ids else it["id"]
        out.append(it)
    for o in old:
        if id(o) not in taken:
            o["new"] = "Not in the latest read"
            out.append(o)
    assign_ids(out)
    link_items(out)
    return out


def _words(s):
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", s.lower())} - _STOPW


def link_items(items):
    """Link Evaluation (M) and SOW items to the Instruction items they concern: explicit section cross-references,
    then strong word overlap (Jaccard >= 0.3, best match only)."""
    instr = [it for it in items if it["type"] in ("Instruction", "Format")]
    for it in items:
        links = []
        refs = [r.strip() for r in it.get("xrefs", "").split(";") if r.strip()]
        for r in refs:
            num = re.sub(r"^(?:section|sec\.|paragraph|para\.?|¶)\s+", "", r, flags=re.I)
            if "." not in num:
                continue                                # "Section C" names a whole section: too broad to link
            for o in items:
                if o is not it and o["section"] and (o["section"] == num or o["section"].startswith(num + ".")):
                    links.append(o["id"])
        if it["type"] in ("Evaluation", "SOW") and not links and instr:
            w = _words(it["text"])
            best, score = None, 0.0
            for o in instr:
                ow = _words(o["text"])
                if w and ow:
                    j = len(w & ow) / len(w | ow)
                    if j > score:
                        best, score = o, j
            if best is not None and score >= 0.3:
                links.append(best["id"])
        it["links"] = "; ".join(dict.fromkeys(links))[:300]
    return items


def merge_items(items, ids):
    """Merge rows (in list order) into the first: texts joined, the rest removed. Returns the merged row or None."""
    rows = [it for it in items if it["id"] in ids]
    if len(rows) < 2:
        return None
    first = rows[0]
    first["text"] = " ".join(r["text"].rstrip() for r in rows)
    first["key"] = text_key(first["text"])
    first["xrefs"] = "; ".join(dict.fromkeys(x for r in rows for x in r.get("xrefs", "").split("; ") if x))
    first["compound"] = True
    first["notes"] = ((first.get("notes") or "") + "; " if first.get("notes") else "") + "merged " + ", ".join(r["id"] for r in rows[1:])
    for r in rows[1:]:
        items.remove(r)
    return first


def _word_diff(old, new):
    """Plain-text word diff: [-removed-] {+added+}."""
    import difflib
    a, b = old.split(), new.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(" ".join(a[i1:i2]))
        if op in ("delete", "replace"):
            out.append("[-" + " ".join(a[i1:i2]) + "-]")
        if op in ("insert", "replace"):
            out.append("{+" + " ".join(b[j1:j2]) + "+}")
    return " ".join(out)


def amendment_changes(items, min_ratio=0.6):
    """After a re-read: pair each new sentence with the most similar removed one (same file kind of change, ratio
    >= 0.6) as Changed; the rest are Added or Removed. Returns [{kind, id, old_id, old, new, diff, section}]."""
    import difflib
    new = [it for it in items if it.get("new") == "New in latest read"]
    gone = [it for it in items if it.get("new") == "Not in the latest read"]
    used, out = set(), []
    for n in new:
        best, score = None, 0.0
        for g in gone:
            if g["id"] in used:
                continue
            r = difflib.SequenceMatcher(None, g["text"], n["text"], autojunk=False).ratio()
            if r > score:
                best, score = g, r
        if best is not None and score >= min_ratio:
            used.add(best["id"])
            out.append({"kind": "Changed", "id": n["id"], "old_id": best["id"], "old": best["text"], "new": n["text"],
                        "diff": _word_diff(best["text"], n["text"]), "section": n["section"] or best["section"],
                        "decision": best.get("decision", "")})
        else:
            out.append({"kind": "Added", "id": n["id"], "old_id": "", "old": "", "new": n["text"], "diff": "", "section": n["section"], "decision": ""})
    for g in gone:
        if g["id"] not in used:
            out.append({"kind": "Removed", "id": "", "old_id": g["id"], "old": g["text"], "new": "", "diff": "", "section": g["section"],
                        "decision": g.get("decision", "")})
    order = {"Changed": 0, "Added": 1, "Removed": 2}
    out.sort(key=lambda c: (order[c["kind"]], sec_key(c["section"] or "~")))
    return out


def write_changes_excel(changes, path, name=""):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    wb = Workbook(); ws = wb.active; ws.title = "Amendment changes"
    ws.append(["Change", "New ID", "Old ID", "Section", "Old text", "New text", "Word differences", "Earlier decision"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for ch in changes:
        ws.append([ch["kind"], ch["id"], ch["old_id"], ch["section"], ch["old"], ch["new"], ch["diff"], ch["decision"]])
    for col, w in zip("ABCDEFGH", (10, 12, 12, 10, 60, 60, 70, 14)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"
    wb.save(path)


# ------------------------------------------------------------------ outline (C2)
_OUTLINE_LINE = re.compile(r"^(\s*)((?:Volume|Vol\.?)\s+[IVX\d]+|[A-M](?:\.\d+)+|\d+(?:\.\d+)*|[A-M]|[IVX]+)?[.)]?\s*[-–—:]?\s*(.*)$", re.I)


def parse_outline(text):
    """One section per line: '1.2 Management Approach', 'Volume I - Technical', or indented titles.
    Returns [{"num", "title", "level"}]."""
    out = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        line = raw.replace("\t", "    ")
        m = _OUTLINE_LINE.match(line)
        indent, num, title = len(m.group(1)), (m.group(2) or "").strip(), m.group(3).strip()
        if num and not title:
            title, num = num, ""
        if num.lower().startswith(("volume", "vol")):
            level = 1
        elif num:
            level = num.count(".") + 1 if num[0].isdigit() else num.count(".") + 1
        else:
            level = indent // 4 + 1
        out.append({"num": num, "title": title or num, "level": max(1, min(level, 6))})
    return out


def outline_text(outline):
    return "\n".join(("    " * (o["level"] - 1)) + (f"{o['num']} " if o["num"] else "") + o["title"] for o in outline)


def outline_label(o):
    return f"{o['num']} {o['title']}".strip()


def sec_key(num):
    """L.4.10 after L.4.2; letters before numbers."""
    return [(0, p) if not p.isdigit() else (1, int(p)) for p in re.split(r"[.]", num)]


def outline_from_headings(headings, letter="L"):
    """The RFP's numbered headings in one section (Section L by default), sorted by number: a starting outline."""
    seen, out = set(), []
    for h in sorted(headings, key=lambda h: sec_key(h["num"])):
        num = h["num"]
        if num in seen or (letter and not num.startswith(letter + ".")):
            continue
        seen.add(num)
        out.append({"num": num, "title": h["title"], "level": num.count(".") if num[0].isalpha() else num.count(".") + 1})
    return out


def outline_from_docx_xml(document_xml):
    """Headings of a Word outline (Heading 1-6 styles), from word/document.xml bytes (hardened parser)."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    root = etree.fromstring(document_xml, parser)
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    out = []
    for p in root.iter(W + "p"):
        st = p.find(f"{W}pPr/{W}pStyle")
        if st is None:
            continue
        m = re.match(r"^(?:Heading|heading)\s*(\d)$", st.get(W + "val", ""))
        if not m:
            continue
        txt = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        if txt:
            o = parse_outline(txt)[0] if parse_outline(txt) else {"num": "", "title": txt}
            out.append({"num": o["num"], "title": o["title"], "level": int(m.group(1))})
    return out


def word_df(items):
    """How many requirements use each word (rare words carry more meaning)."""
    df = {}
    for it in items:
        for w in _words(it["text"] + " " + it.get("lead", "")):
            df[w] = df.get(w, 0) + 1
    return df, max(1, len(items))


def _leaves(outline):
    """Sections without subsections: requirements map to the most specific place (not 'Volume I')."""
    out = []
    for i, o in enumerate(outline):
        nxt = outline[i + 1] if i + 1 < len(outline) else None
        if not (nxt and nxt["level"] > o["level"]):
            out.append(o)
    return out


def suggest_map(item, outline, stats=None):
    """Best outline section for an item: the same section number first; otherwise rare shared words, where most of
    the section title's meaning must match. Returns (label, score) or ("", 0)."""
    if not outline:
        return "", 0.0
    import math
    df, n = stats or ({}, 1)
    idf = lambda w: math.log(1 + n / (1 + df.get(w, 0)))
    sec = item["section"]
    best, score = None, 0.0
    for o in outline:
        if sec and o["num"] and (sec == o["num"] or sec.startswith(o["num"] + ".")):
            s = 2.0 + o["num"].count(".") * 0.01           # deepest matching number wins
            if s > score:
                best, score = o, s
        for ref in re.findall(r"\[([A-Z]\.[\d.]*\d)\]", o["title"]):   # "1.1 Technical Approach [L.4.1]" (2.28.0)
            if sec and (sec == ref or sec.startswith(ref + ".")):
                s = 2.5 + ref.count(".") * 0.01
                if s > score:
                    best, score = o, s
    if best is not None:
        return outline_label(best), round(score, 2)
    w = _words(item["text"] + " " + item.get("lead", ""))
    for o in _leaves(outline):
        ow = {x for x in _words(o["title"]) if df.get(x, 0) > 0 or not stats}
        hit = w & ow
        if not hit:
            continue
        if len(hit) < math.ceil(len(ow) * 0.75):
            continue                                    # most title words must appear: "Risk Management" needs both
        got = sum(idf(x) for x in hit)
        frac = got / sum(idf(x) for x in ow)
        s = frac * min(1.0, got / 2.0) if frac >= 0.6 else 0.0
        if s > score:
            best, score = o, s
    return (outline_label(best), round(score, 2)) if best is not None and score >= 0.3 else ("", 0.0)


# ------------------------------------------------------------------ the workbook
COLUMNS = ["ID", "Decision", "Suggested", "Learned", "Section", "Section title", "Requirement", "Lead-in", "Actor", "Type", "Strength",
           "Cross-references", "Linked items", "Outline section", "Owner", "Status", "Response page", "Notes",
           "Source file", "Location", "Compound", "Change", "Context", "Key"]
WIDTHS = [12, 10, 10, 10, 10, 24, 70, 30, 12, 13, 12, 22, 16, 28, 14, 12, 12, 24, 26, 30, 9, 14, 60, 13]
FIELD = {"ID": "id", "Decision": "decision", "Suggested": "suggest", "Learned": "learned", "Section": "section", "Section title": "section_title",
         "Requirement": "text", "Lead-in": "lead", "Actor": "actor", "Type": "type", "Strength": "strength",
         "Cross-references": "xrefs", "Linked items": "links", "Outline section": "map", "Owner": "owner", "Status": "status",
         "Response page": "response_page", "Notes": "notes", "Source file": "file", "Location": "loc",
         "Compound": "compound", "Change": "new", "Context": "context", "Key": "key"}


class Locked(Exception):
    """The workbook is open in Excel."""


class Matrix:
    def __init__(self, path, name=""):
        self.path = path
        self.name = name or os.path.splitext(os.path.basename(path))[0]
        self.items, self.outline, self.sources, self.history = [], [], [], []
        self.headings = []
        self.setup = None          # Setup Builder (2.13.0): see setupdoc.py
        self.pending = False

    def load(self):
        self.items, self.outline, self.sources, self.history = [], [], [], []
        self.headings = []
        self.setup = None
        if not os.path.isfile(self.path):
            return self
        from openpyxl import load_workbook
        wb = load_workbook(self.path, read_only=True, data_only=True)
        try:
            ws = wb["Compliance Matrix"] if "Compliance Matrix" in wb.sheetnames else wb.worksheets[0]
            it = ws.iter_rows(values_only=True)
            head = [str(h or "").strip() for h in next(it, [])]
            idx = {h: i for i, h in enumerate(head)}
            for vals in it:
                vals = list(vals or [])
                if not any(v not in (None, "") for v in vals):
                    continue
                row = {}
                for col, f in FIELD.items():
                    v = vals[idx[col]] if col in idx and idx[col] < len(vals) else None
                    row[f] = "" if v is None else str(v).strip()
                if not row["text"]:
                    continue
                row["compound"] = row["compound"].lower() in ("yes", "true", "1")
                row["decision"] = {"k": "Keep", "keep": "Keep", "yes": "Keep", "d": "Drop", "drop": "Drop", "no": "Drop",
                                   "c": "Context", "context": "Context"}.get(row["decision"].lower(), "")
                row["page"] = _page(row["loc"])
                row["key"] = row["key"] or text_key(row["text"])
                self.items.append(row)
            if "Outline" in wb.sheetnames:
                rows = list(wb["Outline"].iter_rows(values_only=True))[1:]
                for r in rows:
                    if r and len(r) >= 3 and (r[1] or r[0]):
                        try:
                            lvl = int(r[2] or 1)
                        except (TypeError, ValueError):
                            lvl = 1
                        self.outline.append({"num": str(r[0] or "").strip(), "title": str(r[1] or r[0]).strip(), "level": lvl})
            if "Sources" in wb.sheetnames:
                self.sources = [[("" if v is None else str(v)) for v in (list(r) + ["", "", "", ""])[:4]]
                                for r in list(wb["Sources"].iter_rows(values_only=True))[1:] if r and r[0]]
            if "RFP headings" in wb.sheetnames:
                self.headings = [{"num": str(r[0]), "title": str(r[1] or ""), "file": str(r[2] or "")}
                                 for r in list(wb["RFP headings"].iter_rows(values_only=True))[1:] if r and r[0]]
            if "History" in wb.sheetnames:
                self.history = [[("" if v is None else str(v)) for v in (list(r) + ["", "", "", ""])[:4]]
                                for r in list(wb["History"].iter_rows(values_only=True))[1:] if r and any(r)]
            if "About" in wb.sheetnames:
                for r in wb["About"].iter_rows(values_only=True):
                    if r and r[0] == "Matrix" and len(r) > 1 and r[1]:
                        self.name = str(r[1])
            if "Setup data" in wb.sheetnames:      # the Setup Builder's saved state (JSON in column A, split in parts)
                blob = "".join(str(r[0] or "") for r in wb["Setup data"].iter_rows(min_row=2, values_only=True) if r)
                try:
                    d = json.loads(blob) if blob else None
                    self.setup = d if isinstance(d, dict) else None
                except ValueError:
                    self.setup = None
        finally:
            wb.close()
        assign_ids(self.items)
        return self

    def _save_setup(self, wb, Font):
        """Setup sheet (readable: section, order, reference, text), Setup direction, and Setup data (the state)."""
        import setupdoc as SD
        S = SD.setup_of(self)
        P = SD.placed_in(self)
        B = SD.by_id(self)
        inh = SD.inherited_sections(self)
        ss = wb.create_sheet("Setup")
        ss.append(["Section", "Order", "ID", "Kind", "Reference", "Reference source", "RFP text", "Note (green)"])
        for lab, ids in P.items():
            for n, i in enumerate(ids, 1):
                it = B[i]
                ref, src = SD.ref_of(self, it, inh)
                ss.append([lab, n, i, SD.kind_of(it), ref, src, it["text"], S["notes"].get(i, "")])
        for c in ss[1]:
            c.font = Font(bold=True)
        for col, w in zip("ABCDEFGH", (34, 7, 14, 12, 14, 18, 90, 40)):
            ss.column_dimensions[col].width = w
        sd = wb.create_sheet("Setup direction")
        sd.append(["Section", "Management direction (green)"])
        for c in sd[1]:
            c.font = Font(bold=True)
        for lab in P:
            if S["mgmt"].get(lab, "").strip():
                sd.append([lab, S["mgmt"][lab]])
        sd.column_dimensions["A"].width = 34; sd.column_dimensions["B"].width = 100
        js = json.dumps(S, ensure_ascii=False, separators=(",", ":"))
        dd = wb.create_sheet("Setup data")
        dd.append(["Saved by Acronym Hunter. Do not edit: change the setup in the app."])
        for k in range(0, len(js), 30000):
            dd.append([js[k:k + 30000]])
        dd.sheet_state = "hidden"

    def log(self, what, change):
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
        self.history.append([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), user, what, change])
        self.pending = True

    def path_of(self, file_name):
        """Full path of an RFP file, from the Sources sheet (newest read first), if it is still there."""
        for row in reversed(self.sources):
            if row and row[0] == file_name and len(row) > 3 and row[3] and os.path.isfile(row[3]):
                return row[3]
        return ""

    def coverage(self):
        """Per source file (and a Total row): sentences, Keep, Context, Drop, undecided, placed, need a home (2.29.0)."""
        order = [s[0] for s in self.sources] + [it.get("file", "") for it in self.items]
        rows = {}
        for f in dict.fromkeys(order):
            rows[f] = {"file": f, "total": 0, "Keep": 0, "Context": 0, "Drop": 0, "": 0, "placed": 0, "needs_home": 0}
        for it in self.items:
            r = rows[it.get("file", "")]
            r["total"] += 1
            r[it["decision"]] = r.get(it["decision"], 0) + 1
            if it["decision"] in ("Keep", "Context"):
                r["placed" if it["map"] else "needs_home"] += 1
        out = [r for r in rows.values() if r["total"]]
        tot = {"file": "Total", **{k: sum(r[k] for r in out) for k in ("total", "Keep", "Context", "Drop", "", "placed", "needs_home")}}
        return out + [tot]

    def counts(self):
        c = {"total": len(self.items), "Keep": 0, "Context": 0, "Drop": 0, "": 0, "mapped": 0, "kept_unmapped": 0,
             "context_mapped": 0, "context_unmapped": 0}
        for it in self.items:
            c[it["decision"]] = c.get(it["decision"], 0) + 1
            if it["decision"] == "Keep":
                c["mapped" if it["map"] else "kept_unmapped"] += 1
            elif it["decision"] == "Context":
                c["context_mapped" if it["map"] else "context_unmapped"] += 1
        c["decided"] = c["total"] - c[""]
        c["placed"] = c["mapped"] + c["context_mapped"]
        c["needs_home"] = c["kept_unmapped"] + c["context_unmapped"]
        return c

    def save(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
        d = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(d, exist_ok=True)
        wb = Workbook()
        ws = wb.active; ws.title = "Compliance Matrix"
        ws.append(COLUMNS)
        for i, c in enumerate(ws[1], 1):
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
            ws.column_dimensions[c.column_letter].width = WIDTHS[i - 1]
        fills = {"Keep": "E7F6EC", "Drop": "EEEEEE"}
        for it in self.items:
            ws.append([("Yes" if it.get(FIELD[c]) else "") if c == "Compound" else it.get(FIELD[c], "") for c in COLUMNS])
            f = fills.get(it["decision"])
            if f:
                for c in ws[ws.max_row]:
                    c.fill = PatternFill("solid", fgColor=f)
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "C2"
        last = ws.cell(row=1, column=len(COLUMNS)).column_letter
        ws.auto_filter.ref = f"A1:{last}{max(2, ws.max_row)}"
        dv = DataValidation(type="list", formula1='"Keep,Context,Drop"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"B2:B{max(2, ws.max_row) + 500}")
        for col in ("Context", "Key"):
            ws.column_dimensions[ws.cell(row=1, column=COLUMNS.index(col) + 1).column_letter].hidden = col == "Key"
        ol = wb.create_sheet("Outline")
        ol.append(["Number", "Title", "Level", "Keep and Context rows placed"])
        for c in ol[1]:
            c.font = Font(bold=True)
        for o in self.outline:
            lab = outline_label(o)
            ol.append([o["num"], o["title"], o["level"], sum(1 for it in self.items if it["decision"] in ("Keep", "Context") and it["map"] == lab)])
        for col, w in zip("ABCD", (12, 60, 8, 18)):
            ol.column_dimensions[col].width = w
        so = wb.create_sheet("Sources")
        so.append(["File", "SHA-256", "Read on", "Path on this PC"])
        for src in self.sources:
            so.append(src)
        for col, w in zip("ABCD", (50, 68, 18, 70)):
            so.column_dimensions[col].width = w
        if self.setup:
            self._save_setup(wb, Font)
        cv = wb.create_sheet("Coverage")             # 2.29.0: proof that every sentence was considered
        cv.append(["File", "Sentences", "Keep", "Context", "Drop", "Undecided", "Placed", "Need a home", "Every sentence decided"])
        for c in cv[1]:
            c.font = Font(bold=True)
        for row in self.coverage():
            cv.append([row["file"], row["total"], row["Keep"], row["Context"], row["Drop"], row[""], row["placed"],
                       row["needs_home"], "Yes" if row["total"] and not row[""] else "No"])
        for col, w in zip("ABCDEFGHI", (50, 11, 8, 9, 8, 11, 9, 12, 22)):
            cv.column_dimensions[col].width = w
        rh = wb.create_sheet("RFP headings")
        rh.append(["Number", "Title", "File"])
        for h in self.headings:
            rh.append([h["num"], h["title"], h.get("file", "")])
        for col, w in zip("ABC", (12, 60, 40)):
            rh.column_dimensions[col].width = w
        hs = wb.create_sheet("History")
        hs.append(["Date", "User", "Item", "Change"])
        for h in self.history[-5000:]:
            hs.append(h)
        for col, w in zip("ABCD", (17, 14, 18, 70)):
            hs.column_dimensions[col].width = w
        ab = wb.create_sheet("About")
        c = self.counts()
        for r in (["Matrix", self.name], ["Saved", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
                  ["Sentences", c["total"]], ["Keep", c["Keep"]], ["Context", c["Context"]], ["Drop", c["Drop"]],
                  ["Undecided", c[""]], ["Placed (Keep or Context)", c["placed"]], ["Need a home", c["needs_home"]],
                  ["Note", "Decision: Keep (a requirement), Context (not a requirement, but it goes with the response) or Drop; "
                           "blank = undecided. Edit here or in Acronym Hunter; keep the column headings. "
                           "This workbook holds customer content: keep it on this PC or SharePoint."]):
            ab.append(r)
        ab.column_dimensions["A"].width = 18; ab.column_dimensions["B"].width = 90
        fd, tmp = tempfile.mkstemp(prefix=".matrix_", suffix=".xlsx", dir=d)
        os.close(fd)
        try:
            wb.save(tmp)
            try:
                os.replace(tmp, self.path)
            except PermissionError:
                raise Locked(self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.pending = False


# ------------------------------------------------------------------ Word outline export
def write_outline_docx(matrix, path, title=""):
    """Annotated outline: each outline section as a Word heading, with its kept requirements in a table
    (ID, RFP reference, requirement); then kept requirements not mapped yet."""
    import docxw
    doc = docxw.Doc()
    doc.heading(title or f"{matrix.name}: proposal outline with compliance requirements", 1)
    doc.para(f"Built {datetime.date.today().isoformat()} from the compliance matrix. Kept requirements only.")
    kept = [it for it in matrix.items if it["decision"] == "Keep"]
    for o in matrix.outline:
        lab = outline_label(o)
        doc.heading(lab, min(o["level"] + 1, 6))
        rows = [it for it in kept if it["map"] == lab]
        if rows:
            doc.table(["ID", "RFP reference", "Requirement"],
                      [[it["id"], " ".join(x for x in (it["section"], it["section_title"]) if x) or it["file"],
                        (it["lead"] + " " if it["lead"] else "") + it["text"]] for it in rows], [1300, 2000, 6060])
    rest = [it for it in kept if not it["map"]]
    if rest:
        doc.heading("Kept requirements not mapped to the outline", 2)
        doc.table(["ID", "RFP reference", "Requirement"],
                  [[it["id"], " ".join(x for x in (it["section"], it["section_title"]) if x) or it["file"], it["text"]] for it in rest],
                  [1300, 2000, 6060])
    doc.save(path)
    return {"sections": len(matrix.outline), "mapped": sum(1 for it in kept if it["map"]), "unmapped": len(rest)}


# ------------------------------------------------------------------ coverage report (2.29.0)
COVER_FILL = {"Keep": "D9F2E3", "Context": "DBEAFE", "Drop": "EEEEEE", "": "FECACA"}


def write_coverage_docx(matrix, path, title=""):
    """Every sentence of the RFP in reading order, highlighted by its decision, with its ID, decision and where it was
    placed: the proof that every line was considered. Opens with a table per file and a plain yes / no."""
    import docxw
    doc = docxw.Doc()
    doc.props = {"AcronymHunterMatrix": matrix.name or "", "AcronymHunterCoverage": datetime.date.today().isoformat()}
    cov = matrix.coverage()
    tot = cov[-1]
    doc.heading(title or f"{matrix.name}: RFP coverage, every sentence", 1)
    done = tot["total"] and not tot[""]
    doc.rich([(("Every sentence has a decision." if done else f"{tot['']} sentence(s) still need a decision (red below).")
               + (f" {tot['needs_home']} Keep or Context sentence(s) are not placed in the outline yet." if tot["needs_home"] else
                  " Every Keep and Context sentence is placed."), {"bold": True, "color": "15803D" if done and not tot["needs_home"] else "B91C1C"})])
    doc.para(f"Built {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} from the compliance matrix {os.path.basename(matrix.path)}.")
    doc.table(["File", "Sentences", "Keep", "Context", "Drop", "Undecided", "Placed", "Need a home"],
              [[r["file"], r["total"], r["Keep"], r["Context"], r["Drop"], r[""], r["placed"], r["needs_home"]] for r in cov],
              [3160, 900, 760, 900, 760, 1000, 860, 1020])
    doc.rich([("Key:  ", {"bold": True}), (" Keep (a requirement) ", {"fill": COVER_FILL["Keep"]}), ("  ", {}),
              (" Context (goes with the response) ", {"fill": COVER_FILL["Context"]}), ("  ", {}),
              (" Drop ", {"fill": COVER_FILL["Drop"], "color": "6B7280"}), ("  ", {}),
              (" Undecided ", {"fill": COVER_FILL[""], "bold": True})])
    by_file = {}
    for it in matrix.items:
        by_file.setdefault(it.get("file", ""), []).append(it)
    for r in cov[:-1]:
        f = r["file"]
        doc.heading(f or "(no file)", 2)
        sec = None
        for it in by_file.get(f, []):
            head = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
            if head and head != sec:
                doc.heading(head, 3)
                sec = head
            d = it["decision"]
            txt = ((it["lead"] + " ") if it.get("lead") else "") + it["text"]
            where = it["map"] or ("not placed" if d in ("Keep", "Context") else "")
            tag = f"   [{it['id']} · {d or 'UNDECIDED'}" + (f" · {where}" if where else "") + "]"
            doc.rich([(txt, {"fill": COVER_FILL.get(d, COVER_FILL[""]), "color": "6B7280" if d == "Drop" else None}),
                      (tag, {"size": 16, "color": "B91C1C" if not d or where == "not placed" else "475569", "bold": not d})])
    doc.save(path)
    return {"sentences": tot["total"], "undecided": tot[""], "needs_home": tot["needs_home"], "files": len(cov) - 1}


# ------------------------------------------------------------------ source page (PDF)
def render_page(path, page_no, text, scale=2.0):
    """A PDF page as a picture with the requirement highlighted (PDFium text search on its first words).
    Returns a PIL image."""
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[page_no - 1]
        w, h = page.get_size()
        img = page.render(scale=scale).to_pil().convert("RGBA")
        tp = page.get_textpage()
        words = text.replace("(a) ", "").split()
        for n in (8, 5, 3):
            probe = " ".join(words[:n])
            if not probe:
                break
            found = tp.search(probe, match_case=False, match_whole_word=False).get_next()
            if found:
                idx, _cnt = found
                full = min(len(text) + 5, tp.count_chars() - idx)
                over = Image.new("RGBA", img.size, (0, 0, 0, 0))
                d = ImageDraw.Draw(over)
                for i in range(tp.count_rects(idx, full)):
                    l, b, r, t = tp.get_rect(i)
                    d.rectangle([l * scale - 2, (h - t) * scale - 2, r * scale + 2, (h - b) * scale + 2], fill=(253, 224, 71, 110),
                                outline=(202, 138, 4, 255), width=2)
                img = Image.alpha_composite(img, over)
                break
        return img.convert("RGB")
    finally:
        pdf.close()
