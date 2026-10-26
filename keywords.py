"""Keyword Harvest suggestions (2.16.0): phrases worth tagging a proposal with, and why. Rules and counts only (No AI).

Input: the typed text of the customer documents and of our own volumes. Candidates are 2 to 4 word phrases that do
not start or end with a small word, never cross punctuation, and are not RFP boilerplate. Signals:
- how often, and in how many sections, a phrase appears;
- where: customer documents, our volumes, or both (only in our volumes = our solution);
- headings: the phrase is in a section title;
- emphasis: it sits in a sentence with requirement or evaluation wording (shall, must, evaluate, factor...);
- distinctiveness: phrases made only of everyday English words score lower (SCOWL common words list);
- the effort list's approved acronyms with their long forms.
Each suggestion carries a bucket (Customer emphasis, Our solution, Differentiator, Acronym), a score, the reasons in
plain words, and up to three sample sentences with their location.

2.34.0 both sides: each suggestion has a side (customer, both, ours). A phrase in both is the customer's words used in
our answer (Shared language, scored up). A phrase only in our volumes is tied to the customer ask it answers when it
sits in one of our sections that answers it: the compliance matrix's placement (a Keep requirement placed in an outline
section whose heading matches our section), else our sections that use a phrase the customer emphasized. Tied phrases
are Our response (scored up) and say which ask they answer. The list keeps a share of each side so one side never
crowds out the other.
"""
import datetime, hashlib, json, math, os, re
from collections import defaultdict

STOP = set("""a an the and or nor but if then than so as at by for from in into of on onto to with within without via per
upon over under up down out off about above below between among through during before after against across along
around behind beyond is are was were be been being am do does did done has have had having will shall must may might can
could should would it its it's this that these those there here which who whom whose what when where while how why all
any each every both either neither some such no not only own same other another more most much many few less least very
also just too we our ours us you your they their them he she his her i me my mine one two three four five six seven eight
nine ten first second third new etc e.g i.e including include includes included provide provides provided providing use
uses used using based well like via whether""".split())
BOILER = set("""section sections page pages figure figures table tables volume volumes paragraph paragraphs attachment
attachments appendix exhibit item items contractor contractors government offeror offerors proposal proposals rfp rfq
solicitation contract contracts clause clauses requirement requirements shall must information data document documents
part parts note notes reference references see title instructions instruction contents award factor factors evaluation
evaluations general statement""".split())
GENERIC = {"statement of work", "table of contents", "past performance", "basis for award", "technical approach",
           "management approach", "cost approach", "price approach", "period of performance", "scope of work"}
EMPHASIS = re.compile(r"\b(shall|must|will be evaluated|evaluat\w*|factor|criteri\w*|objective|threshold|key performance|"
                      r"mission|priority|critical|essential|required)\b", re.I)
WORD = re.compile(r"[A-Za-z][A-Za-z0-9&/\-']*")
CLAUSE = re.compile(r"[.;:!?,()\[\]{}\"“”\n\t|]+")
BUCKETS = ["Customer emphasis", "Shared language", "Our response", "Our solution", "Differentiator", "Offering", "Acronym"]
SIDES = {"customer": "From the customer", "both": "In both", "ours": "From our volumes"}
_COMMON = None


def common_words():
    global _COMMON
    if _COMMON is None:
        _COMMON = set()
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "common_words.txt")
        try:
            with open(p, encoding="utf-8") as f:
                _COMMON = {l.strip().lower() for l in f if l.strip() and not l.startswith("#")}
        except OSError:
            pass
    return _COMMON


def _heading_of(label):
    m = re.search(r"section '([^']+)'", label or "")
    return m.group(1) if m else ""


def _file_of(label):
    return (label or "").split(" (", 1)[0]


def phrases(text, nmin=2, nmax=4):
    """[(key, surface, start index in text)] candidate phrases in one text."""
    out = []
    pos = 0
    for clause in CLAUSE.split(text):
        start = text.find(clause, pos) if clause else pos
        pos = start + len(clause) if start >= 0 else pos
        toks = [(m.group(0), m.start()) for m in WORD.finditer(clause)]
        low = [t.lower().strip("'-/") for t, _ in toks]
        for i in range(len(toks)):
            for n in range(nmin, nmax + 1):
                j = i + n
                if j > len(toks):
                    break
                w = low[i:j]
                if w[0] in STOP or w[-1] in STOP or len(w[0]) < 2 or len(w[-1]) < 2:
                    continue
                if all(x in STOP or x in BOILER for x in w):
                    continue
                if sum(x in BOILER for x in w) >= len(w) - 1:
                    continue
                if any(x.isdigit() or len(x) < 2 for x in w):
                    continue
                if " ".join(w) in GENERIC:
                    continue
                surface = " ".join(t for t, _ in toks[i:j])
                out.append((" ".join(w), surface, max(0, start) + toks[i][1]))
    return out


_SEC = re.compile(r"\s*((?:[A-Z]\.)?\d+(?:\.\d+)*)\.?\s+(.*)")


def _split_heading(h):
    """'3.2 Thermal Control' -> ('3.2', 'thermal control'); no number -> ('', 'thermal control')."""
    h = " ".join((h or "").split())
    m = _SEC.match(h)
    num, title = (m.group(1), m.group(2)) if m else ("", h)
    return num, title.casefold().strip(" .:-")


def heading_matches(ours, outline):
    """Our section heading is the outline section the matrix placed a requirement in (same number, or the same title)."""
    n1, t1 = _split_heading(ours)
    n2, t2 = _split_heading(outline)
    if n1 and n2:
        return n1 == n2 or (t1 and t1 == t2)
    if t1 and t2:
        return t1 == t2 or (len(t2) >= 8 and (t2.startswith(t1) or t1.startswith(t2)) and min(len(t1), len(t2)) >= 8)
    return False


def _balance(out, limit, share=5):
    """Best first, but each side (customer, both, ours) keeps up to limit/share places when it has candidates."""
    if len(out) <= limit:
        return out
    keep, per = [], max(1, limit // share)
    for side in ("customer", "both", "ours"):
        keep += [o for o in out if o.get("side") == side and o["bucket"] not in ("Offering", "Acronym")][:per]
    ids = {id(o) for o in keep}
    for o in out:
        if len(keep) >= limit:
            break
        if id(o) not in ids:
            keep.append(o); ids.add(id(o))
    keep.sort(key=lambda x: (-x["score"], x["phrase"].lower()))
    return keep


def offering_hits(chunks, offerings):
    """{offering: {"customer", "ours", "samples"}} for catalog offerings named in the text (whole words, any case)."""
    out = {}
    for it in offerings:
        pats = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", re.I) for n in _names(it) if len(n) >= 3]
        h = {"customer": 0, "ours": 0, "samples": []}
        for label, text, kind in chunks:
            for p in pats:
                for m in p.finditer(text or ""):
                    h["customer" if kind == "customer" else "ours"] += 1
                    if len(h["samples"]) < 3:
                        a = text.rfind(".", 0, m.start()) + 1
                        b = text.find(".", m.end())
                        h["samples"].append((label, " ".join(text[a:(b + 1 if b >= 0 else len(text))].split())[:240]))
        if h["customer"] or h["ours"]:
            out[it["Offering"]] = h
    return out


def _names(it):
    return [it["Offering"]] + [x.strip() for x in re.split(r"[;,]", it.get("Other names", "")) if x.strip()]


# ------------------------------------------------------------ past proposals and team history (2.18.0)
# Both are stored as hashed phrases with counts only: no proposal text is kept, the same rule as compliance learning.
def phrase_hash(text):
    return hashlib.sha1(" ".join(text.lower().split()).encode("utf-8")).hexdigest()[:16]


def _cfg(name):
    import app_gui
    return os.path.join(app_gui.CONFIG_DIR, name)


def _read(name, default):
    try:
        with open(_cfg(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(name, data):
    p = _cfg(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(p + ".tmp", p)


def build_baseline(docs):
    """docs: [[text, ...] per past proposal]. Saves in how many past proposals each phrase appears (hashed)."""
    df = defaultdict(int)
    for texts in docs:
        keys = set()
        for t in texts:
            keys |= {k for k, _s, _a in phrases(t)}
        for k in keys:
            df[phrase_hash(k)] += 1
    data = {"docs": len(docs), "built": datetime.date.today().isoformat(), "df": dict(df)}
    _write("keyword_baseline.json", data)
    return data


def baseline():
    return _read("keyword_baseline.json", {})


def clear_baseline():
    try:
        os.remove(_cfg("keyword_baseline.json"))
    except OSError:
        pass


def learning():
    d = _read("keyword_learning.json", {})
    return {"keep": d.get("keep", {}), "reject": d.get("reject", {})}


def learn(phrase, status):
    """Remember a Keep or Reject for later suggestions in every effort (hashed phrase, counts only)."""
    if status not in ("Keep", "Reject"):
        return
    d = learning()
    h = phrase_hash(phrase)
    side = d["keep"] if status == "Keep" else d["reject"]
    side[h] = side.get(h, 0) + 1
    _write("keyword_learning.json", d)


def suggest(chunks, acronyms=(), existing=(), limit=60, offerings=(), base=None, learned=None, asks=()):
    """chunks: [(location label, text, kind)] with kind 'customer' or 'ours'. acronyms: [(term, long form)].
    existing: keywords already listed (any status), never suggested again. asks: [(requirement id, outline section)]
    for Keep requirements the compliance matrix placed. Returns [{"phrase", "bucket", "score", "why": [str],
    "samples": [(label, sentence)], "count", "customer", "ours", "sections", "side", "answers": [str]}], best first."""
    common = common_words()
    seen = {" ".join(e.split()).casefold() for e in existing}
    st = defaultdict(lambda: {"count": 0, "customer": 0, "ours": 0, "sections": set(), "heading": False, "emph": 0,
                              "surface": defaultdict(int), "samples": [], "files": set()})
    ours_chunks = []                                                    # (heading, keys) of each section of ours
    ours_at = {}
    for label, text, kind in chunks:
        if not text:
            continue
        head = _heading_of(label).lower()
        if kind != "customer":
            sk = (_file_of(label), _heading_of(label))
            if sk not in ours_at or not sk[1]:                         # paragraphs of one section share one entry
                ours_at[sk] = len(ours_chunks); ours_chunks.append((sk[1], set()))
            cur_ours = ours_chunks[ours_at[sk]][1] if sk[1] else ours_chunks[-1][1]
        sec = (_file_of(label), head)
        for key, surface, at in phrases(text):
            s = st[key]
            s["count"] += 1
            s[kind if kind in ("customer", "ours") else "ours"] += 1
            s["sections"].add(sec); s["files"].add(_file_of(label))
            s["surface"][surface] += 1
            if kind != "customer":
                cur_ours.add(key)
            a = text.rfind(".", 0, at) + 1
            b = text.find(".", at)
            sentence = " ".join(text[a:(b + 1 if b >= 0 else len(text))].split())
            if EMPHASIS.search(sentence):
                s["emph"] += 1
            if len(s["samples"]) < 3 and sentence and all(sentence != x[1] for x in s["samples"]):
                s["samples"].append((label, sentence[:240]))
        if head:
            for key, surface, _at in phrases(_heading_of(label)):
                st[key]["heading"] = True
                st[key]["surface"][surface] += 0
    keys = [k for k, s in st.items() if s["count"] >= 2 or s["heading"]]
    # a shorter phrase that nearly always appears inside a longer one is the same idea: keep the longer
    drop = set()
    for k in keys:
        for longer in keys:
            if longer != k and len(longer) > len(k) and f" {k} " in f" {longer} " and st[longer]["count"] >= 0.8 * st[k]["count"]:
                drop.add(k); break
    # 2.34.0: which customer ask each of our chunks answers
    emph = [k for k in keys if k not in drop and st[k]["customer"] and (st[k]["emph"] or st[k]["heading"])]
    emph.sort(key=lambda k: -(st[k]["customer"] + 2 * st[k]["emph"] + (3 if st[k]["heading"] else 0)))
    emph_set = set(emph[:80])
    ties = defaultdict(lambda: defaultdict(int))                        # our-only phrase -> {ask label: count}
    for head, ks in ours_chunks:
        tied = []
        for rid, sec in asks:
            if head and sec and heading_matches(head, sec):
                tied.append(f"{rid} ({sec[:50]})")
        if not tied:
            hk = {k for k, _s, _a in phrases(head)} if head else set()
            used = [k for k in emph if k in emph_set and (k in hk or k in ks)]
            tied = ["'" + (max(st[k]["surface"].items(), key=lambda x: x[1])[0] if st[k]["surface"] else k) + "'" for k in used[:3]]
        if tied:
            for k in ks:
                if not st[k]["customer"]:
                    for t in tied:
                        ties[k][t] += 1
    out = []
    for k in keys:
        if k in drop or k in seen:
            continue
        s = st[k]
        words = [w for w in k.split() if w not in STOP]
        everyday = all(w in common for w in words)
        surface = max(s["surface"].items(), key=lambda x: (x[1], sum(c.isupper() for c in x[0])))[0] if s["surface"] else k
        spread = len(s["sections"])
        score = math.log2(1 + s["count"]) + 0.5 * min(spread, 6) + (2.0 if s["heading"] else 0) \
            + (1.5 if s["emph"] >= 2 else 0.5 if s["emph"] else 0) - (1.5 if everyday else 0) + 0.3 * (len(words) - 2)
        proper = any(t[:1].isupper() for t in surface.split()[1:]) or any(t.isupper() and len(t) > 1 for t in surface.split())
        if s["customer"] and (s["emph"] or s["heading"]):
            bucket = "Customer emphasis"
        elif s["ours"] and not s["customer"]:
            bucket = "Differentiator" if (proper or not everyday) and s["ours"] >= 2 else "Our solution"
        elif s["customer"]:
            bucket = "Customer emphasis"
        else:
            bucket = "Our solution"
        side = "both" if s["customer"] and s["ours"] else "customer" if s["customer"] else "ours"
        answers = [t for t, _n in sorted(ties.get(k, {}).items(), key=lambda x: -x[1])][:3] if side == "ours" else []
        if side == "both":
            score += 1.0
            if bucket != "Customer emphasis":
                bucket = "Shared language"
        if answers:
            score += 1.0
            if bucket in ("Our solution", "Differentiator"):
                bucket = "Our response"                              # past proposals can still make it a Differentiator
        why = [f"{s['count']} times in {spread} section(s)" + (f" of {len(s['files'])} files" if len(s["files"]) > 1 else "")]
        if s["customer"] and s["ours"]:
            why.append(f"the customer's words, used in our volumes (customer {s['customer']}, ours {s['ours']})")
        elif s["customer"]:
            why.append("in the customer documents only" + ("; not yet in our volumes" if ours_chunks else ""))
        elif s["ours"]:
            why.append("only in our volumes: what we propose")
        if answers:
            if answers[0].startswith("'"):
                why.append("in our sections that answer the customer's " + ", ".join(answers))
            else:
                why.append("in our answer to " + ", ".join(answers) + " (placed there in the compliance matrix)")
        if s["heading"]:
            why.append("in a section heading")
        if s["emph"]:
            why.append(f"near requirement or evaluation wording ({s['emph']}x)")
        if everyday:
            why.append("everyday words: less distinctive")
        h = phrase_hash(k)
        if base and base.get("docs", 0) >= 3:
            n = base["docs"]; d = base.get("df", {}).get(h, 0)
            if d / n >= 0.5:
                score -= 1.5; why.append(f"common in past proposals ({d} of {n})")
            elif d == 0:
                score += 1.0; why.append(f"new compared with {n} past proposals")
                if bucket in ("Our solution", "Our response"):
                    bucket = "Differentiator"
        if learned:
            kept, rej = learned.get("keep", {}).get(h, 0), learned.get("reject", {}).get(h, 0)
            if kept:
                score += 0.7 * min(kept, 3); why.append(f"kept in other efforts ({kept})")
            if rej:
                score -= 1.0 * min(rej, 3); why.append(f"rejected before ({rej})")
        out.append({"phrase": surface, "bucket": bucket, "score": round(score, 2), "why": why, "samples": s["samples"],
                    "count": s["count"], "customer": s["customer"], "ours": s["ours"], "sections": spread,
                    "side": side, "answers": answers})
    names_lower = set()
    for it in offerings:                                               # its names never show up twice
        names_lower |= {n.lower() for n in _names(it)}
    for name, h in offering_hits(chunks, offerings).items():          # 2.17.0: the offerings catalog
        if name.casefold() in seen:
            continue
        n = h["customer"] + h["ours"]
        why = [f"in the offerings catalog; named {n} times"]
        if h["ours"]:
            why.append(f"in our volumes ({h['ours']})")
        if h["customer"]:
            why.append(f"in the customer documents ({h['customer']})")
        out.append({"phrase": name, "bucket": "Offering", "score": round(4.0 + math.log2(1 + n), 2), "why": why,
                    "samples": h["samples"], "count": n, "customer": h["customer"], "ours": h["ours"], "sections": 0,
                    "side": "both" if h["customer"] and h["ours"] else "customer" if h["customer"] else "ours", "answers": []})
    out = [o for o in out if o["bucket"] == "Offering" or o["phrase"].lower() not in names_lower]
    for term, long_form in acronyms:
        lf = " ".join((long_form or "").split())
        if not lf or lf.casefold() in seen or term.casefold() in seen:
            continue
        hits = st.get(lf.lower(), {}).get("count", 0) if lf.lower() in st else 0
        out.append({"phrase": f"{lf} ({term})", "bucket": "Acronym", "score": round(2.0 + math.log2(1 + hits), 2),
                    "why": ["approved in the effort list" + (f"; the long form appears {hits} times" if hits else "")],
                    "samples": [], "count": hits, "customer": 0, "ours": 0, "sections": 0, "side": "", "answers": []})
    out.sort(key=lambda x: (-x["score"], x["phrase"].lower()))
    return _balance(out, limit)
