"""Placement learning across proposals (2.30.0): where the team puts each kind of RFP sentence in the outline.

Rules plus counting, no AI model and no network. Every placed Keep or Context row teaches word links: words of the
sentence (and, more lightly, the sentences beside it) linked to words of the outline section title and its parent
titles, plus the volume type (Technical, Management, Past Performance...). Section numbers are not learned, so the
links carry over to a new proposal whose outline is numbered and titled differently. A short team synonym list joins
words that mean the same thing in section titles ("approach" and "solution").

Privacy: every word and word link is hashed into a numbered bucket before it is stored, so the saved counts never hold
RFP or outline text. The counts live in config\\compliance_learned.json beside the Keep / Drop learning and travel in
Knowledge Packs with it. Each matrix contributes its own counts (learning it again replaces them), and older matrices
count less (half weight after two years), so the suggestions follow how the team works now.

Scoring a section: for each title word, how much more often it appears with the sentence's words than chance (lift),
shrunk when the counts are small. The self-check scores each matrix with what was learned from the OTHER matrices:
how often the section the person chose was in the top 3.
"""
import datetime, functools, hashlib, math, os, re

BUCKETS = 1 << 20
HALF_LIFE_DAYS = 730
MIN_PLACED = 30                       # placements (from all matrices) before learned suggestions show
STRONG, POSSIBLE, LEAD = 0.25, 0.12, 1.3   # strong: score 0.25+ and 1.3 times the runner-up; possible: 0.12+

_WORD = re.compile(r"[a-z][a-z0-9\-]+")
STOP = set("""a an and or the of to in on for by with as at from into per via be is are was were been being this that these those it its
their there such any all each every other than then also not no nor but if when where which who whom whose what how
shall must will should may can could would might offeror offerors contractor contractors government proposal proposals
describe description provide provided providing include including includes address addressing demonstrate demonstrated
discuss explain identify submit submitted section sections paragraph volume volumes page pages part following
response respond rfp solicitation requirement requirements item items etc using use used within without including
approach""".split())
# "approach" is so common in proposal titles that it says nothing about where a sentence goes

VOLUME_TYPES = (("past performance", "past_performance"), ("past-performance", "past_performance"),
                ("executive summary", "summary"), ("small business", "small_business"),
                ("technical", "technical"), ("management", "management"), ("cost", "cost"), ("price", "cost"),
                ("pricing", "cost"), ("staffing", "staffing"), ("personnel", "staffing"), ("key personnel", "staffing"),
                ("transition", "transition"), ("security", "security"), ("contract", "contract"),
                ("schedule", "management"), ("program", "management"))

STARTER_SYNONYMS = """# One group per line: words that mean the same thing in section titles. The first word stands for the group.
# Lines starting with # are notes. The app joins these words before learning and scoring.
solution, approach, methodology, method, concept
management, program management, project management, pm
schedule, ims, timeline, milestones, master schedule
risk, risks, risk management, mitigation
staffing, personnel, key personnel, labor, workforce, team
past performance, experience, relevant experience, references, corporate experience
quality, quality assurance, qa, quality control
security, cybersecurity, information assurance, cyber
transition, phase-in, transition-in, startup
verification, test, testing, validation, v&v
cost, price, pricing, budget
systems engineering, se, engineering management
safety, mission assurance, reliability
subcontract, subcontractor, teaming, subcontract management
facilities, facility, infrastructure
training, education
data, data management, cdrl, deliverables
configuration management, cm, configuration control
logistics, sustainment, supportability
"""


@functools.lru_cache(maxsize=200000)
def _h(tok):
    return int.from_bytes(hashlib.blake2b(tok.encode("utf-8"), digest_size=4).digest(), "big") % BUCKETS


def stem(w):
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 6 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 5 and w.endswith("ed") and not w.endswith("eed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


# ------------------------------------------------------------------ synonyms
def synonyms_path(config_dir):
    return os.path.join(config_dir, "placement_synonyms.csv")


def load_synonyms(path):
    """Text of the team synonym list (the starter list when the file does not exist)."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return STARTER_SYNONYMS


def save_synonyms(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
    os.replace(tmp, path)


def parse_synonyms(text):
    """{phrase or word (stemmed): canonical token}. Multi-word entries are kept as phrases."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip().lower() for p in re.split(r"[,;\t]", line) if p.strip()]
        if len(parts) < 2:
            continue
        canon = "~" + "_".join(stem(w) for w in _WORD.findall(parts[0]))
        for p in parts:
            key = " ".join(stem(w) for w in _WORD.findall(p))
            if key:
                out.setdefault(key, canon)
    return out


def merge_synonym_text(mine, theirs):
    """Add the groups of another synonym list that this one does not have (add-only). Returns (text, groups added)."""
    have = {tuple(sorted(parse_synonyms(l).keys())) for l in mine.splitlines() if parse_synonyms(l)}
    words = set(parse_synonyms(mine))
    add = []
    for line in theirs.splitlines():
        p = parse_synonyms(line)
        if p and tuple(sorted(p)) not in have and not (set(p) <= words):
            add.append(line.strip())
    return (mine.rstrip() + "\n" + "\n".join(add) + "\n") if add else mine, len(add)


# ------------------------------------------------------------------ words
def tokens(text, syn):
    """Stemmed content words with synonym phrases joined (longest phrase first)."""
    ws = [stem(w) for w in _WORD.findall((text or "").lower())]
    out, i = [], 0
    while i < len(ws):
        hit = None
        for n in (3, 2, 1):
            if i + n <= len(ws) and " ".join(ws[i:i + n]) in syn:
                hit = (syn[" ".join(ws[i:i + n])], n); break
        if hit:
            out.append(hit[0]); i += hit[1]
            continue
        if ws[i] not in STOP and len(ws[i]) > 2 and not ws[i].isdigit():
            out.append(ws[i])
        i += 1
    return out


def volume_type(title):
    t = (title or "").lower()
    for key, typ in VOLUME_TYPES:
        if key in t:
            return typ
    return "other"


def section_paths(outline):
    """{label: (leaf title, [parent titles], volume type)} for the sections rows can be placed in."""
    out, stack = {}, []
    for o in outline:
        while stack and stack[-1]["level"] >= o["level"]:
            stack.pop()
        parents = [p["title"] for p in stack]
        vol = "other"
        for p in stack + [o]:                       # the volume heading names the type (Volume I - Technical)
            if p["level"] == 1 or "vol" in (p.get("num", "") + " " + p["title"]).lower()[:8]:
                vol = volume_type(p["title"])
                if vol != "other":
                    break
        if vol == "other":
            for p in stack:
                vol = volume_type(p["title"])
                if vol != "other":
                    break
        out[f"{o['num']} {o['title']}".strip()] = (o["title"], parents, vol)
        stack.append(o)
    return out


def title_feats(path, syn):
    title, parents, vol = path
    f = {}
    for w in tokens(title, syn):
        f[w] = max(f.get(w, 0), 1.0)
    for p in parents:
        for w in tokens(p, syn):
            f[w] = max(f.get(w, 0), 0.5)
    f["#vol=" + vol] = 0.6
    return f


def sentence_feats(item, neighbors, syn):
    f = {}
    for w in tokens((item.get("lead") or "") + " " + item.get("text", ""), syn):
        f[w] = 1.0
    for nb in neighbors:
        for w in tokens(nb.get("text", ""), syn):
            f.setdefault(w, 0.4)
    t = item.get("type", "")
    if t:
        f["#type=" + t] = 0.5
    sec = (item.get("section") or "")[:1]
    if sec.isalpha():
        f["#sec=" + sec.upper()] = 0.5
    return f


def neighbors_of(items):
    """{id: [previous, next]} rows of the same file in reading order (the sentences around each row)."""
    out, last = {}, {}
    seq = list(items)
    for i, it in enumerate(seq):
        f = it.get("file", "")
        nb = []
        if i and seq[i - 1].get("file", "") == f:
            nb.append(seq[i - 1])
        if i + 1 < len(seq) and seq[i + 1].get("file", "") == f:
            nb.append(seq[i + 1])
        out[it["id"]] = nb
    return out


# ------------------------------------------------------------------ the counts
def _weight(date_text, today=None):
    try:
        d = datetime.date.fromisoformat(str(date_text)[:10])
    except ValueError:
        return 1.0
    age = ((today or datetime.date.today()) - d).days
    return 0.5 ** (max(0, age) / HALF_LIFE_DAYS)


def _source_counts(items, outline, syn):
    """One matrix's counts: pair, sentence-word and title-word buckets, and the number of placements."""
    paths = section_paths(outline)
    nbs = neighbors_of(items)
    src = {"pair": {}, "s": {}, "t": {}, "n": 0}
    for it in items:
        if it.get("decision") not in ("Keep", "Context") or not it.get("map") or it["map"] not in paths:
            continue
        sf = sentence_feats(it, nbs.get(it["id"], []), syn)
        tf = title_feats(paths[it["map"]], syn)
        src["n"] += 1
        for w, a in sf.items():
            k = str(_h("s:" + w)); src["s"][k] = src["s"].get(k, 0) + a
            for t, b in tf.items():
                p = str(_h("p:" + w + "|" + t)); src["pair"][p] = src["pair"].get(p, 0) + a * b
        for t, b in tf.items():
            k = str(_h("t:" + t)); src["t"][k] = src["t"].get(k, 0) + b
    for key in ("pair", "s", "t"):
        src[key] = {k: round(v, 2) for k, v in src[key].items()}
    return src


class Placer:
    """Placement counts kept inside the Keep / Drop learner's data (data["placement"])."""

    def __init__(self, data, syn_text=None):
        self.data = data.setdefault("placement", {"version": 1, "sources": {}})
        self.data.setdefault("sources", {})
        self.syn = parse_synonyms(STARTER_SYNONYMS if syn_text is None else syn_text)
        self._totals()

    def _totals(self, skip=None):
        self.pair, self.s, self.t, self.n = {}, {}, {}, 0.0
        for sid, src in self.data["sources"].items():
            if sid == skip:
                continue
            w = _weight(src.get("learned", ""))
            self.n += w * src.get("n", 0)
            for key, tot in (("pair", self.pair), ("s", self.s), ("t", self.t)):
                for b, c in (src.get(key) or {}).items():
                    tot[int(b)] = tot.get(int(b), 0) + w * c

    def learn(self, sid, items, outline):
        src = _source_counts(items, outline, self.syn)
        src["learned"] = datetime.date.today().isoformat()
        old = self.data["sources"].get(sid, {})
        chk = getattr(self, "_pending", {}).pop(sid, None) or old.get("check")
        if chk:
            src["check"] = chk
        if src["n"]:
            self.data["sources"][sid] = src
        else:
            self.data["sources"].pop(sid, None)
        self._totals()
        return src["n"]

    def placed(self):
        return int(round(sum(s.get("n", 0) for s in self.data["sources"].values())))

    def matrices(self):
        return sum(1 for s in self.data["sources"].values() if s.get("n"))

    def ready(self):
        return self.n >= MIN_PLACED

    # ---------------------------------------------------------- scoring
    def _assoc(self, w, t):
        c = self.pair.get(_h("p:" + w + "|" + t), 0)
        if c <= 0:
            return 0.0
        cs, ct = self.s.get(_h("s:" + w), 0), self.t.get(_h("t:" + t), 0)
        if cs <= 0 or ct <= 0:
            return 0.0
        lift = c * self.n / (cs * ct)
        return max(0.0, math.log(lift)) * (c / (c + 2.0))

    def score(self, sf, tf):
        if not sf or not tf:
            return 0.0
        wsum = 0.0
        sw = {}
        for w, a in sf.items():
            cs = self.s.get(_h("s:" + w), 0)
            if cs <= 0:
                continue
            sw[w] = a * math.log(1 + self.n / cs)
            wsum += sw[w]
        if not wsum:
            return 0.0
        total = tw = 0.0
        for t, b in tf.items():
            tw += b
            total += b * sum(x * self._assoc(w, t) for w, x in sw.items()) / wsum
        return total / tw if tw else 0.0

    def rank(self, item, outline, neighbors=(), k=3):
        """[(label, score)] best first, at most k, only sections with some learned support."""
        if not self.ready() or not outline:
            return []
        paths = section_paths(outline)
        leaves = _leaf_labels(outline)
        sf = sentence_feats(item, list(neighbors), self.syn)
        out = []
        for lab in leaves:
            s = self.score(sf, title_feats(paths[lab], self.syn))
            if s > 0.05:
                out.append((lab, round(s, 3)))
        out.sort(key=lambda x: -x[1])
        return out[:k]

    @staticmethod
    def band(ranked):
        """'strong', 'possible' or '' (no strong match) for a rank() result: a clear leader is strong."""
        if not ranked:
            return ""
        s1 = ranked[0][1]
        s2 = ranked[1][1] if len(ranked) > 1 else 0.0
        if s1 >= STRONG and s1 >= LEAD * s2:
            return "strong"
        return "possible" if s1 >= POSSIBLE else ""

    def check(self, sid, items, outline):
        """Score this matrix with what was learned from the other matrices: (top-3 hits, top-1 hits, rows checked), or
        None when the other matrices have too few placements. Saves the result with the matrix's counts."""
        self._totals(skip=sid)
        try:
            if self.n < MIN_PLACED:
                return None
            paths = section_paths(outline)
            leaves = _leaf_labels(outline)
            tfs = {lab: title_feats(paths[lab], self.syn) for lab in leaves}
            nbs = neighbors_of(items)
            top3 = top1 = total = 0
            for it in items:
                if it.get("decision") not in ("Keep", "Context") or it.get("map") not in tfs:
                    continue
                sf = sentence_feats(it, nbs.get(it["id"], []), self.syn)
                ranked = sorted(((self.score(sf, tf), lab) for lab, tf in tfs.items()), reverse=True)[:3]
                labs = [lab for s, lab in ranked if s > 0.05]
                total += 1
                top3 += it["map"] in labs
                top1 += bool(labs) and labs[0] == it["map"]
            if not total:
                return None
            res = {"top3": top3, "top1": top1, "total": total, "sections": len(leaves),
                   "date": datetime.date.today().isoformat()}
            if sid in self.data["sources"]:
                self.data["sources"][sid]["check"] = res
            self._pending = getattr(self, "_pending", {}); self._pending[sid] = res
            return res
        finally:
            self._totals()

    def history(self):
        """Self-check results of every matrix, oldest first: [(date, top3, total)]."""
        rows = [(s["check"]["date"], s["check"]["top3"], s["check"]["total"])
                for s in self.data["sources"].values() if isinstance(s.get("check"), dict) and s["check"].get("total")]
        return sorted(rows)


def _leaf_labels(outline):
    out = []
    for i, o in enumerate(outline):
        nxt = outline[i + 1] if i + 1 < len(outline) else None
        if not (nxt and nxt["level"] > o["level"]):
            out.append(f"{o['num']} {o['title']}".strip())
    return out


def merge_sources(mine, theirs):
    """Add another PC's placement sources (add-only; numbers only). Returns placements added."""
    added = 0
    dst = mine.setdefault("placement", {"version": 1, "sources": {}}).setdefault("sources", {})
    for sid, src in ((theirs.get("placement") or {}).get("sources") or {}).items():
        if sid in dst or not isinstance(src, dict):
            continue
        clean = {"n": int(src.get("n", 0)), "learned": str(src.get("learned", ""))[:10]}
        for key in ("pair", "s", "t"):
            clean[key] = {str(int(b)): round(float(c), 2) for b, c in (src.get(key) or {}).items()
                          if 0 <= int(b) < BUCKETS and float(c) > 0}
        chk = src.get("check")
        if isinstance(chk, dict):
            clean["check"] = {k: (int(chk[k]) if k != "date" else str(chk[k])[:10]) for k in ("top3", "top1", "total", "sections", "date")
                              if k in chk}
        dst[sid] = clean
        added += clean["n"]
    return added
