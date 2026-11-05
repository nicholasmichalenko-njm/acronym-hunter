"""Technical Edit (3.54.0): copy review of a Word draft by rules (claude/stationkeeper-technical-edit-plan-3.54.html,
decisions in claude/stationkeeper-technical-edit-decisions-2026-11-04.md). Starter rules follow the Chicago Manual of
Style (with the team's choice of numbers one to nine spelled out), mechanics and federal plain language; the team's banned
phrases, dictionaries and acronym list, and each effort's style sheet, sit on top. Rules and word lists only, no AI.
A finding is a suggestion: {key, rule, group, level ("Fix" | "Check"), para, start, end, hit, fix, sentence, section,
why}. para is the paragraph's place in document.xml (every w:p in order, tables included), start/end the characters of
hit inside that paragraph's text, so techeditdocx can write the accepted ones as tracked changes in a copy.

read(path) / rules() / LEVELS / review(path or paras, level, sheet, refs) / section_stats(paras) / grade(text).
Nothing leaves the PC."""
import os, re, zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
FIX, CHECK = "Fix", "Check"
GROUPS = ("Mechanics", "Consistency", "Chicago style", "Plain language", "Customer language", "Persuasion", "Leftovers",
          "Acronyms", "Banned phrases")
LEVELS = {"full": ("Full copy review", GROUPS),
          "consistency": ("Consistency and mechanics", ("Mechanics", "Consistency", "Chicago style", "Acronyms", "Leftovers", "Banned phrases")),
          "last": ("Last look", ("Leftovers", "Banned phrases", "Mechanics:doubled", "Leftovers:stale"))}
SENTENCE_MAX = 30                                   # decision 2
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
TENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90, "hundred": 100}
UNITS = r"(?:kg|km|cm|mm|nm|µm|um|m|g|mg|lb|lbs|ft|in|V|mV|kV|W|kW|MW|A|mA|Hz|kHz|MHz|GHz|dB|dBW|dBm|s|ms|µs|us|min|hr|h|K|°C|°F|Mbps|Gbps|kbps|MB|GB|TB|N|Pa|kPa|psi)"
WORDY = {"in order to": "to", "due to the fact that": "because", "at this point in time": "now", "in the event that": "if",
         "prior to": "before", "subsequent to": "after", "a number of": "several", "the majority of": "most",
         "has the ability to": "can", "have the ability to": "can", "with regard to": "about", "with respect to": "about",
         "for the purpose of": "to", "in close proximity to": "near", "each and every": "each", "first and foremost": "first",
         "in spite of the fact that": "although", "at the present time": "now", "in an effort to": "to",
         "on a regular basis": "regularly", "is able to": "can", "are able to": "can", "in addition to": "besides",
         "a large number of": "many", "on an annual basis": "yearly", "until such time as": "until"}
NOMINAL = {"make a decision": "decide", "made a decision": "decided", "conduct an analysis": "analyze", "perform an analysis": "analyze",
           "provide assistance": "help", "perform an assessment": "assess", "conduct an assessment": "assess",
           "give consideration to": "consider", "make a recommendation": "recommend", "reach a conclusion": "conclude",
           "take action": "act", "make an adjustment": "adjust", "conduct a review": "review", "perform a review": "review",
           "provide an explanation": "explain", "make a determination": "determine", "achieve compliance": "comply"}
VARIANTS = (("website", "web site"), ("email", "e-mail"), ("online", "on-line"), ("dataset", "data set"), ("timeline", "time line"),
            ("workforce", "work force"), ("healthcare", "health care"), ("lifecycle", "life cycle"), ("database", "data base"),
            ("startup", "start-up"), ("ground station", "groundstation"), ("real time", "realtime"), ("cybersecurity", "cyber security"))
CLAIMS = ("world-class", "best-in-class", "unmatched", "unparalleled", "state-of-the-art", "cutting-edge", "industry-leading",
          "second to none", "unrivaled", "best-of-breed", "premier", "leading-edge")      # a space or hyphen between words both match
CUSTOMER_TERMS = {"client": "Government", "the customer's government": "the Government"}
PASSIVE = re.compile(r"\b(am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(\w+ed|\w+en|built|made|done|held|kept|sent|set|led|met|"
                     r"paid|put|run|said|seen|shown|told|won|bought|brought|caught|found|given|known|taken|written|chosen|"
                     r"drawn|grown|thrown|begun|sold|sought|taught|thought|understood|withheld)\b", re.I)
PLACEHOLDER = re.compile(r"\[(?:insert|tbd|tbr|add|placeholder|customer|company|name|xx+)[^\]]*\]|\bTBD\b|\bTBR\b|\bX{2,}\b|"
                         r"\bX\.X\b|\blorem ipsum\b|<\s*(?:customer|company|insert)[^>]*>|\bCompany Name\b", re.I)
_WORD = re.compile(r"[A-Za-z][A-Za-z'’]+")


# ------------------------------------------------------------------ reading
def read(path):
    """[{"i", "text", "style", "heading", "table", "outline"}] every paragraph in document.xml in order; also the document's
    leftovers: {"tracked": n, "comments": n, "hidden": n}."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
        has_comments = "word/comments.xml" in z.namelist()
        ncom = len(re.findall(rb"<w:comment ", z.read("word/comments.xml"))) if has_comments else 0
    out = []
    for i, p in enumerate(root.iter(W + "p")):
        st = p.find(f"{W}pPr/{W}pStyle")
        sid = st.get(W + "val") if st is not None else ""
        ol = p.find(f"{W}pPr/{W}outlineLvl")
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        table = any(a.tag == W + "tbl" for a in p.iterancestors())
        head = (ol is not None) or sid.lower().startswith("heading") or sid.lower() in ("title",)
        out.append({"i": i, "text": text, "style": sid, "heading": head, "table": table,
                    "outline": int(ol.get(W + "val")) if ol is not None else None})
    left = {"tracked": len(root.findall(f".//{W}ins")) + len(root.findall(f".//{W}del")), "comments": ncom,
            "hidden": len(root.findall(f".//{W}vanish"))}
    return out, left


def sentences(text):
    """[(start, end)] of each sentence in a paragraph."""
    out, s = [], 0
    for m in re.finditer(r"(?<=[.!?])[\"'”’)]?\s+(?=[A-Z0-9\"“(])", text):
        out.append((s, m.start() + (1 if text[m.start():m.start() + 1] in "\"'”’)" else 0)))
        s = m.end()
    if s < len(text):
        out.append((s, len(text)))
    return [(a, b) for a, b in out if text[a:b].strip()]


def _sentence_at(text, pos):
    for a, b in sentences(text):
        if a <= pos < b:
            return text[a:b].strip()
    return text.strip()


# ------------------------------------------------------------------ word lists
_WORDS = None


def word_list():
    """The offline word list (assets/spelling_words.txt, from SCOWL) as a set, read once; comment lines left out."""
    global _WORDS
    if _WORDS is None:
        import app_gui as A
        p = os.path.join(A.BASE_DIR, "assets", "spelling_words.txt")        # SCOWL, American, sizes up to 70
        try:
            with open(p, encoding="utf-8") as f:
                _WORDS = {w.strip().lower() for w in f if w.strip() and not w.startswith("#")}
        except OSError:
            _WORDS = set()
    return _WORDS


def _known(w, words, extra):
    lw = w.lower().replace("’", "'")
    if lw in words or lw in extra:
        return True
    for suf, rep in (("'s", ""), ("s", ""), ("es", ""), ("ies", "y"), ("ed", ""), ("ed", "e"), ("ing", ""), ("ing", "e"),
                     ("ly", ""), ("er", ""), ("est", ""), ("ment", ""), ("ness", ""), ("ation", "ate"), ("ization", "ize"),
                     ("able", ""), ("al", ""), ("ity", ""), ("ive", "e"), ("ive", "")):
        if lw.endswith(suf) and len(lw) - len(suf) >= 3 and (lw[: -len(suf)] + rep) in words:
            return True
    return False


# ------------------------------------------------------------------ the starter rules
def rules():
    """[{id, group, finds, level, example}] the starter rules, for the rules list and the style sheet's off switches."""
    return [dict(zip(("id", "group", "finds", "level", "example"), r)) for r in (
        ("doubled", "Mechanics", "A word written twice in a row", FIX, "the the"),
        ("spaces", "Mechanics", "Two or more spaces between words", FIX, "the  bus"),
        ("space_punct", "Mechanics", "A space before a comma, period, colon or semicolon", FIX, "word ,"),
        ("unmatched", "Mechanics", "A parenthesis or quote left open", CHECK, "(no closing"),
        ("range_dash", "Mechanics", "A hyphen between years in a range (use an en dash)", FIX, "2027-2029"),
        ("spelling", "Mechanics", "Words in no word list and no team dictionary", CHECK, "telemtry"),
        ("blank_paras", "Mechanics", "Blank paragraphs used for spacing", CHECK, "two empty paragraphs"),
        ("variants", "Consistency", "One term written two ways in the draft", CHECK, "website and web site"),
        ("hyphen_forms", "Consistency", "A hyphenated word also written closed or open", CHECK, "re-use and reuse"),
        ("government", "Consistency", "government in lower case when the draft capitalizes it for the customer", CHECK, "the government"),
        ("unit_space", "Consistency", "A number touching its unit", FIX, "5kg"),
        ("numbers_small", "Chicago style", "1 to 9 as numerals in running text (spell out)", CHECK, "7 engineers"),
        ("numbers_large", "Chicago style", "10 and up spelled out (use numerals)", CHECK, "twelve engineers"),
        ("serial_comma", "Chicago style", "A list of three with no comma before and or or", CHECK, "power, thermal and data"),
        ("percent", "Chicago style", "The % sign in running text (spell out percent)", CHECK, "15%"),
        ("long_sentence", "Plain language", f"A sentence longer than {SENTENCE_MAX} words", CHECK, "38 words"),
        ("passive", "Plain language", "Passive voice", CHECK, "was validated by"),
        ("wordy", "Plain language", "Wordy phrases", CHECK, "in order to"),
        ("nominal", "Plain language", "Nouns made from verbs", CHECK, "make a decision"),
        ("customer_terms", "Customer language", "Generic words for the customer's terms", CHECK, "client"),
        ("shall", "Customer language", "shall written by the offeror (the customer's word)", CHECK, "The payload shall"),
        ("claims", "Persuasion", "A claim with no number in its sentence", CHECK, "world-class"),
        ("captions", "Persuasion", "A figure or table caption that states no benefit", CHECK, "Figure 3. Block diagram"),
        ("placeholders", "Leftovers", "Placeholders and notes left in the draft", FIX, "[Insert], TBD, XX"),
        ("stale", "Leftovers", "Another effort's name from reused text", FIX, "a name from another effort"),
        ("file_left", "Leftovers", "Tracked changes, comments or hidden text still in the file", FIX, "3 comments"),
        ("acr_case", "Acronyms", "An acronym written another way than the acronym list", CHECK, "DOD for DoD"),
        ("acr_twice", "Acronyms", "An acronym spelled out more than once", CHECK, "(SOW) twice"),
        ("banned", "Banned phrases", "The team's banned phrases (Team References)", FIX, "utilize"))]


RULE = {r["id"]: r for r in rules()}


def _f(out, rid, p, start, end, fix, why="", level=None, hit=None, section=""):
    r = RULE[rid]
    text = p["text"]
    h = text[start:end] if hit is None else hit
    out.append({"key": f"{rid}|{p['i']}|{start}|{h}", "rule": rid, "title": r["finds"], "group": r["group"],
                "level": level or r["level"], "para": p["i"], "start": start, "end": end, "hit": h, "fix": fix,
                "sentence": _sentence_at(text, start), "section": section, "why": why})


def _word_re(phrase):
    return re.compile(r"(?<![\w-])" + r"[\s-]+".join(re.escape(w) for w in phrase.split()) + r"(?![\w-])", re.I)


def _matches_case(src, new):
    if src.isupper():
        return new.upper()
    if src[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


# ------------------------------------------------------------------ the review
def review(source, level="full", sheet=None, refs=None):
    """Findings for one draft. source: a .docx path or (paragraphs, leftovers) from read(). sheet: the effort's style sheet
    {"terms": {written: right}, "off": [rule ids], "skips": [keys]}. refs: {"dictionaries": set of words, "acronyms":
    {term: definition}, "banned": [items], "other_names": [names of other efforts], "customer_terms": {word: theirs}}."""
    paras, left = read(source) if isinstance(source, str) else source
    sheet, refs = sheet or {}, refs or {}
    groups = set(LEVELS.get(level, LEVELS["full"])[1])
    off, skips = set(sheet.get("off") or []), set(sheet.get("skips") or [])

    def on(rid):
        g = RULE[rid]["group"]
        return rid not in off and (g in groups or f"{g}:{rid}" in groups or (level == "last" and f"Mechanics:{rid}" in groups))

    out = []
    words = word_list()
    extra = {w.lower() for w in (refs.get("dictionaries") or set())} | {t.lower() for t in (refs.get("acronyms") or {})}
    body = [p for p in paras if p["text"].strip()]
    alltext = "\n".join(p["text"] for p in body)
    low_all = alltext.lower()
    freq = {}
    for w in _WORD.findall(alltext):
        freq[w.lower()] = freq.get(w.lower(), 0) + 1
    section = ""
    blank_run = 0
    acr = refs.get("acronyms") or {}
    acr_upper = {t.upper(): t for t in acr if t.upper() != t}
    defined = {}
    variant_seen = {}
    for a, b in VARIANTS + tuple((k, v) for k, v in (sheet.get("terms") or {}).items()):
        variant_seen[(a, b)] = (len(_word_re(a).findall(alltext)), len(_word_re(b).findall(alltext)))
    gov_cap = len(re.findall(r"\bGovernment\b", alltext))
    banned = [(it, __import__("banned").pattern(it["Phrase"])) for it in (refs.get("banned") or []) if it.get("Phrase")]
    others = [n for n in (refs.get("other_names") or []) if len(n) >= 4]
    for p in paras:
        t = p["text"]
        if not t.strip():
            blank_run += 1
            if blank_run == 2 and on("blank_paras"):
                _f(out, "blank_paras", p, 0, 0, "Use spacing before and after instead", "Spacing belongs to the style.", hit="")
            continue
        blank_run = 0
        if p["heading"]:
            section = t.strip()
        sec = section
        # mechanics
        if on("doubled"):
            for m in re.finditer(r"\b(\w+)(\s+)(\1)\b", t, re.I):
                if m.group(1).lower() not in ("had", "that", "is") and not m.group(1).isdigit():
                    _f(out, "doubled", p, m.start(), m.end(), m.group(1), "Mechanics.", section=sec)
        if on("spaces"):
            for m in re.finditer(r"(?<=\S)  +(?=\S)", t):
                _f(out, "spaces", p, m.start(), m.end(), " ", "One space between words.", section=sec)
        if on("space_punct"):
            for m in re.finditer(r"(?<=\w)\s+([,.;:])(?=\s|$)", t):
                _f(out, "space_punct", p, m.start(), m.end(), m.group(1), "No space before punctuation.", section=sec)
        if on("unmatched") and (t.count("(") != t.count(")") or t.count("“") != t.count("”") or t.count('"') % 2):
            _f(out, "unmatched", p, 0, min(len(t), 40), "Close it", "A parenthesis or quote opens and does not close.", hit=t[:40])
        if on("range_dash"):
            for m in re.finditer(r"\b((?:19|20)\d\d)-((?:19|20)\d\d)\b", t):
                _f(out, "range_dash", p, m.start(), m.end(), f"{m.group(1)}–{m.group(2)}", "Chicago: an en dash for ranges.", section=sec)
        if on("spelling") and not p["heading"]:
            for m in _WORD.finditer(t):
                w = m.group(0)
                if len(w) < 4 or w.isupper() or w[0].isupper() or freq.get(w.lower(), 0) >= 3:
                    continue
                if not _known(w, words, extra):
                    _f(out, "spelling", p, m.start(), m.end(), "Check the spelling, or add it to a dictionary",
                       "Not in the word list or the team's dictionaries.", section=sec)
        # consistency
        if on("variants"):
            for (a, b), (na, nb) in variant_seen.items():
                if na and nb:
                    minor, major = (b, a) if na >= nb else (a, b)
                    for m in _word_re(minor).finditer(t):
                        _f(out, "variants", p, m.start(), m.end(), _matches_case(m.group(0), major),
                           f"The draft writes both; {major} is used more (or set in the style sheet).", section=sec)
        if on("hyphen_forms"):
            for m in re.finditer(r"\b([a-z]{2,})-([a-z]{2,})\b", t):
                closed = m.group(1) + m.group(2)
                if re.search(r"\b" + closed + r"\b", low_all) and m.group(0).lower() not in ("e-mail", "on-line", "start-up"):
                    _f(out, "hyphen_forms", p, m.start(), m.end(), closed, "The draft also writes it closed.", section=sec)
        if on("government") and gov_cap:
            for m in re.finditer(r"\bthe government\b", t):
                _f(out, "government", p, m.start() + 4, m.end(), "Government", "Capitalized elsewhere for the customer.", section=sec)
        if on("unit_space"):
            for m in re.finditer(r"\b(\d+(?:\.\d+)?)(" + UNITS + r")\b", t):
                _f(out, "unit_space", p, m.start(), m.end(), f"{m.group(1)} {m.group(2)}", "A space between a number and its unit.", section=sec)
        # Chicago (with numbers one to nine spelled out)
        if on("numbers_small") and not p["table"] and not p["heading"]:
            for m in re.finditer(r"(?<![\w.,$/-])([1-9])(?![\w.,%/:-])(?!\s*(?:" + UNITS + r"|percent|%)\b)", t):
                before = t[max(0, m.start() - 12):m.start()]
                if re.search(r"(Figure|Table|Exhibit|Section|Volume|Appendix|Attachment|page|para|p\.|No\.|Rev|Phase|Step|Level|Tier|Option|CLIN|Item)\s*$", before, re.I):
                    continue
                if re.match(r"^\s*\d", t[m.end():m.end() + 3]) or re.search(r"\d\s*$", before):
                    continue
                if m.start() == 0 or re.search(r"[.!?]\s+$", before):
                    continue
                _f(out, "numbers_small", p, m.start(), m.end(), NUMBER_WORDS[int(m.group(1))], "One to nine spelled out in running text.", section=sec)
        if on("numbers_large") and not p["table"]:
            for m in re.finditer(r"\b(" + "|".join(TENS) + r")\b(?![- ](?:one|two|three|four|five|six|seven|eight|nine))", t, re.I):
                if m.start() == 0 or re.search(r"[.!?]\s+$", t[:m.start()]):
                    continue
                _f(out, "numbers_large", p, m.start(), m.end(), str(TENS[m.group(1).lower()]), "10 and up as numerals.", section=sec)
        if on("serial_comma"):
            for m in re.finditer(r"\b(\w+), (\w+(?: \w+)?) (and|or) (\w+)", t):
                if "," not in m.group(2):
                    i = m.start(3) - 1
                    _f(out, "serial_comma", p, m.start(2), m.start(3) - 1, m.group(2) + ",", "Chicago: a comma before and or or in a list of three or more.", section=sec)
        if on("percent") and not p["table"]:
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s?%", t):
                _f(out, "percent", p, m.start(), m.end(), f"{m.group(1)} percent", "Chicago: percent spelled out in running text.", section=sec)
        # plain language
        if not p["heading"] and not p["table"]:
            for a, b in sentences(t):
                n = len(t[a:b].split())
                if n > SENTENCE_MAX and on("long_sentence"):
                    _f(out, "long_sentence", p, a, b, "Split it", f"{n} words; the limit is {SENTENCE_MAX}.", hit=t[a:b], section=sec)
            if on("passive"):
                for m in PASSIVE.finditer(t):
                    _f(out, "passive", p, m.start(), m.end(), "Say who does it", "Plain language: active voice.", section=sec)
        for rid, table in (("wordy", WORDY), ("nominal", NOMINAL)):
            if on(rid):
                for phrase, better in table.items():
                    for m in _word_re(phrase).finditer(t):
                        _f(out, rid, p, m.start(), m.end(), _matches_case(m.group(0), better), "Plain language: fewer words.", section=sec)
        # customer language
        if on("customer_terms"):
            for word, theirs in {**CUSTOMER_TERMS, **(refs.get("customer_terms") or {})}.items():
                for m in _word_re(word).finditer(t):
                    _f(out, "customer_terms", p, m.start(), m.end(), theirs, "Use the customer's own word.", section=sec)
        if on("shall"):
            for m in re.finditer(r"\bshall\b", t):
                _f(out, "shall", p, m.start(), m.end(), "will", "shall is the customer's word for a requirement.", section=sec)
        # persuasion
        if on("claims"):
            for c in CLAIMS:
                for m in _word_re(c).finditer(t):
                    if not re.search(r"\d", _sentence_at(t, m.start())):
                        _f(out, "claims", p, m.start(), m.end(), "Say what is better, with a number", "A claim needs proof.", section=sec)
        if on("captions"):
            m = re.match(r"^\s*(Figure|Table|Exhibit)\s+[A-Z]?\d+(?:[.-]\d+)?[.:]?\s+(.*)$", t)
            if m and len(m.group(2).split()) <= 4:
                _f(out, "captions", p, m.start(2), len(t), "Say what the reader gets from it", "An action caption states the benefit.", section=sec)
        # leftovers
        if on("placeholders"):
            for m in PLACEHOLDER.finditer(t):
                _f(out, "placeholders", p, m.start(), m.end(), "Fill it in", "A placeholder left in the draft.", section=sec)
        if on("stale"):
            for n in others:
                for m in re.finditer(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", t):
                    _f(out, "stale", p, m.start(), m.end(), "This effort's name", f"{n} is another effort on this PC.", section=sec)
        # acronyms (read the acronym list; decisions stay in Acronyms)
        if on("acr_case"):
            for m in re.finditer(r"\b[A-Z][A-Z0-9&]{1,9}\b", t):
                right = acr_upper.get(m.group(0))
                if right and right != m.group(0):
                    _f(out, "acr_case", p, m.start(), m.end(), right, "The acronym list writes it this way.", section=sec)
        if on("acr_twice"):
            for m in re.finditer(r"\(([A-Z][A-Za-z0-9&]{1,9})\)", t):
                k = m.group(1)
                if k in defined:
                    _f(out, "acr_twice", p, m.start(), m.end(), "", f"Spelled out before, in {defined[k]}.", section=sec)
                else:
                    defined[k] = sec or "the draft"
        if on("banned"):
            for it, rx in banned:
                for m in rx.finditer(t):
                    lvl = FIX if it.get("Level") == "Banned" else CHECK
                    _f(out, "banned", p, m.start(), m.end(), it.get("Use instead") or "Rewrite", it.get("Why") or "On the team's banned list.",
                       level=lvl, section=sec)
    if on("file_left") and any(left.values()) and paras:
        what = ", ".join(f"{n} {k}" for k, n in (("tracked changes", left["tracked"]), ("comments", left["comments"]),
                                                   ("hidden text runs", left["hidden"])) if n)
        _f(out, "file_left", paras[0], 0, 0, "Accept or remove them before the copy goes out", what + " still in the file.", hit="")
    return [f for f in _no_overlap(out) if f["key"] not in skips]


# a finding covered by a stronger one on the same words is left out (a placeholder is not also a banned phrase)
STRONGER = {"banned": ("placeholders", "stale"), "claims": ("banned", "placeholders"), "spelling": ("placeholders", "stale", "acr_case"),
            "passive": (), "acr_case": ("acr_twice",)}


def _no_overlap(out):
    by = {}
    for f in out:
        by.setdefault(f["para"], []).append(f)
    keep = []
    for f in out:
        over = [g for g in by[f["para"]] if g is not f and g["rule"] in STRONGER.get(f["rule"], ())
                and g["start"] < f["end"] and f["start"] < g["end"]]
        if not over:
            keep.append(f)
    return keep


# ------------------------------------------------------------------ readability
def _syllables(w):
    w = w.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups) - (1 if w.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def grade(text):
    """Flesch-Kincaid grade level of a passage (0 when it has no sentences)."""
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    ws = _WORD.findall(text)
    if not sents or not ws:
        return 0.0
    return round(0.39 * len(ws) / len(sents) + 11.8 * sum(_syllables(w) for w in ws) / len(ws) - 15.59, 1)


def section_stats(paras):
    """[{section, words, sentences, per_sentence, grade, passive_share}] per section (the heading above), running text only."""
    out, cur, buf = [], "", []

    def close():
        text = " ".join(buf)
        if text.strip():
            sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            ws = _WORD.findall(text)
            out.append({"section": cur or "(before the first heading)", "words": len(ws), "sentences": len(sents),
                        "per_sentence": round(len(ws) / max(1, len(sents)), 1), "grade": grade(text),
                        "passive_share": round(sum(1 for s in sents if PASSIVE.search(s)) / max(1, len(sents)), 2)})
    for p in paras:
        if p["heading"] and p["text"].strip():
            close(); cur, buf = p["text"].strip(), []
        elif not p["table"]:
            buf.append(p["text"])
    close()
    return out
