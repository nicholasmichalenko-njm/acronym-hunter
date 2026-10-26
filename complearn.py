"""Compliance C3 (2.10.0): learn Keep / Drop from the team's own decisions, and sections from rows already mapped.

Not generative AI and not a language model: a multinomial Naive Bayes over hashed word features, trained on this PC.
Privacy by design: features are hashed into numbered buckets before anything is stored, so the saved model holds bucket
numbers and counts only, never words or sentences from the RFP. Each matrix contributes its own counts, so learning
from the same matrix again replaces its earlier contribution instead of counting it twice.

Model file: config\\compliance_learned.json (this PC). Pure Python, no network.
"""
import datetime, hashlib, json, math, os, re

BUCKETS = 1 << 18
_TOKEN = re.compile(r"[a-z][a-z0-9\-]{1,}|\d+")


def _h(tok):
    return int.from_bytes(hashlib.blake2b(tok.encode("utf-8"), digest_size=4).digest(), "big") % BUCKETS


def features(item):
    """Hashed features: words and word pairs of the requirement (and its lead-in), plus the rule labels."""
    words = _TOKEN.findall(((item.get("lead") or "") + " " + item.get("text", "")).lower())
    toks = list(words) + [a + "_" + b for a, b in zip(words, words[1:])]
    toks += [f"#type={item.get('type', '')}", f"#actor={item.get('actor', '')}", f"#strength={item.get('strength', '')}",
             f"#modal={item.get('modal', '')}", f"#sec={(item.get('section') or '~')[:1]}", f"#rule={item.get('suggest', '')}"]
    out = {}
    for t in toks:
        b = _h(t)
        out[b] = out.get(b, 0) + 1
    return out


class Learner:
    def __init__(self, path):
        self.path = path
        self.data = {"version": 1, "sources": {}}
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("sources"), dict):
                self.data = d
        except (OSError, ValueError):
            pass
        self._totals()

    # ------------------------------------------------------------ counts
    def _totals(self):
        self.counts = {"Keep": {}, "Drop": {}}
        self.docs = {"Keep": 0, "Drop": 0}
        for src in self.data["sources"].values():
            for lab in ("Keep", "Drop"):
                self.docs[lab] += src.get("docs", {}).get(lab, 0)
                for b, n in src.get(lab, {}).items():
                    self.counts[lab][int(b)] = self.counts[lab].get(int(b), 0) + n
        self.tot = {lab: sum(c.values()) for lab, c in self.counts.items()}
        self.vocab = len(set(self.counts["Keep"]) | set(self.counts["Drop"]))

    @staticmethod
    def source_id(matrix_path):
        """A matrix is known by a hash of its file name, never the name itself."""
        return hashlib.sha256(os.path.basename(matrix_path).lower().encode()).hexdigest()[:16]

    def learn(self, matrix_path, items, outline=None):
        """Replace this matrix's contribution with its current decisions. Returns the number of decisions used.
        With the matrix's outline, its placements are learned too (2.30.0)."""
        if outline:
            self.placer().learn(self.source_id(matrix_path), items, outline)
        src = {"Keep": {}, "Drop": {}, "docs": {"Keep": 0, "Drop": 0}, "learned": datetime.date.today().isoformat()}
        n = 0
        for it in items:
            lab = it.get("decision")
            if lab not in ("Keep", "Drop"):
                continue
            n += 1
            src["docs"][lab] += 1
            for b, c in features(it).items():
                src[lab][str(b)] = src[lab].get(str(b), 0) + c
        sid = self.source_id(matrix_path)
        if n:
            self.data["sources"][sid] = src
        else:
            self.data["sources"].pop(sid, None)
        self._totals()
        return n

    def merge_pack(self, blob):
        """Add another PC's learning (from a Knowledge Pack), add-only: matrices this PC already learned from keep this
        PC's counts. Only bucket numbers and counts are read. Returns the number of decisions added."""
        d = json.loads(blob.decode("utf-8") if isinstance(blob, bytes) else blob)
        added = 0
        for sid, src in (d.get("sources") or {}).items():
            if sid in self.data["sources"] or not isinstance(src, dict):
                continue
            clean = {"docs": {k: int(src.get("docs", {}).get(k, 0)) for k in ("Keep", "Drop")}, "learned": str(src.get("learned", ""))[:10]}
            for lab in ("Keep", "Drop"):
                clean[lab] = {str(int(b)): int(n) for b, n in (src.get(lab) or {}).items() if 0 <= int(b) < BUCKETS and int(n) > 0}
            self.data["sources"][sid] = clean
            added += clean["docs"]["Keep"] + clean["docs"]["Drop"]
        import placelearn
        self.placed_added = placelearn.merge_sources(self.data, d)
        self._placer = None
        self._totals()
        return added

    def placer(self, reload=False):
        """Placement learning across proposals (2.30.0), kept in the same file; synonyms from the team list beside it."""
        import placelearn
        if reload or getattr(self, "_placer", None) is None:
            syn = placelearn.load_synonyms(placelearn.synonyms_path(os.path.dirname(os.path.abspath(self.path))))
            self._placer = placelearn.Placer(self.data, syn)
        return self._placer

    def forget_all(self):
        self.data["sources"] = {}
        self.data["placement"] = {"version": 1, "sources": {}}
        self._placer = None
        self._totals()

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, separators=(",", ":"))
        os.replace(tmp, self.path)

    def ready(self):
        return self.docs["Keep"] >= 5 and self.docs["Drop"] >= 3

    def summary(self):
        return {"decisions": self.docs["Keep"] + self.docs["Drop"], "keep": self.docs["Keep"], "drop": self.docs["Drop"],
                "matrices": len(self.data["sources"])}

    # ------------------------------------------------------------ scoring
    @staticmethod
    def _score(feats, counts, docs, tot, vocab):
        nd = docs["Keep"] + docs["Drop"]
        logp = {}
        for lab in ("Keep", "Drop"):
            lp = math.log((docs[lab] + 1) / (nd + 2))
            denom = tot[lab] + vocab + 1
            for b, c in feats.items():
                lp += c * math.log((counts[lab].get(b, 0) + 1) / denom)
            logp[lab] = lp
        m = max(logp.values())
        ek, ed = math.exp(logp["Keep"] - m), math.exp(logp["Drop"] - m)
        return ek / (ek + ed)

    def p_keep(self, item):
        """Probability the team keeps this row, or None before there are enough decisions."""
        if not self.ready():
            return None
        return self._score(features(item), self.counts, self.docs, self.tot, self.vocab)

    @staticmethod
    def label(p):
        if p is None:
            return ""
        return "Keep" if p >= 0.7 else "Drop" if p <= 0.3 else "Review"

    @staticmethod
    def cross_check(items, folds=5):
        """How often a model trained on the other rows agrees with each decided row (k-fold). Returns (agree, total,
        rule_agree): the learned model's agreement and, for comparison, the rule suggestion's."""
        dec = [it for it in items if it.get("decision") in ("Keep", "Drop")]
        if len(dec) < 10:
            return None
        feats = [features(it) for it in dec]
        agree = rule = 0
        for k in range(folds):
            counts = {"Keep": {}, "Drop": {}}; docs = {"Keep": 0, "Drop": 0}
            for i, it in enumerate(dec):
                if i % folds == k:
                    continue
                docs[it["decision"]] += 1
                for b, c in feats[i].items():
                    counts[it["decision"]][b] = counts[it["decision"]].get(b, 0) + c
            if not docs["Keep"] or not docs["Drop"]:
                continue
            tot = {lab: sum(c.values()) for lab, c in counts.items()}
            vocab = len(set(counts["Keep"]) | set(counts["Drop"]))
            for i, it in enumerate(dec):
                if i % folds != k:
                    continue
                p = Learner._score(feats[i], counts, docs, tot, vocab)
                agree += ("Keep" if p >= 0.5 else "Drop") == it["decision"]
                rule += it.get("suggest") == it["decision"]
        return agree, len(dec), rule


# ------------------------------------------------------------------ learned mapping (similar rows already mapped)
def _vec(item):
    words = _TOKEN.findall(((item.get("lead") or "") + " " + item.get("text", "")).lower())
    v = {}
    for w in words:
        if len(w) > 2:
            v[w] = v.get(w, 0) + 1
    return v


def map_from_neighbors(item, items, min_sim=0.35, k=3):
    """Suggest an outline section from the most similar rows the person already mapped (cosine on TF-IDF).
    Returns (label, similarity) or ("", 0)."""
    mapped = [it for it in items if it.get("map") and it is not item and it.get("decision") == "Keep"]
    if not mapped:
        return "", 0.0
    df = {}
    allv = [_vec(it) for it in mapped]
    for v in allv:
        for w in v:
            df[w] = df.get(w, 0) + 1
    n = len(mapped) + 1
    idf = lambda w: math.log(1 + n / (1 + df.get(w, 0)))
    q = {w: c * idf(w) for w, c in _vec(item).items()}
    qn = math.sqrt(sum(x * x for x in q.values())) or 1.0
    sims = []
    for it, v in zip(mapped, allv):
        d = {w: c * idf(w) for w, c in v.items()}
        dot = sum(q[w] * d[w] for w in q if w in d)
        if dot:
            sims.append((dot / (qn * (math.sqrt(sum(x * x for x in d.values())) or 1.0)), it["map"]))
    sims.sort(reverse=True)
    top = [s for s in sims[:k] if s[0] >= min_sim]
    if not top:
        return "", 0.0
    votes = {}
    for s, lab in top:
        votes[lab] = votes.get(lab, 0) + s
    lab = max(votes, key=votes.get)
    return lab, round(max(s for s, l in top if l == lab), 2)
