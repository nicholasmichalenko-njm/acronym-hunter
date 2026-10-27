"""Training Studio (2.50.0): the five steps of Stationkeeper Training and the scorecard behind the Knowledge Pack.

1 Gather: corrections packs (as before) and past compliance matrices; the matrices' decisions and placements are
  learned into compliance_learned.json (numbered word buckets and counts only, never RFP text).
2 Review: accept, reject or fix each corrected line. A share of the lines is set aside as the test set by a stable
  rule (the same line always lands in the same set), so nobody picks it.
3 Train: Improve Reading (it measures itself on the set-aside lines).
4 Measure: the scorecard. Each area is tested with the knowledge as it was and as it is now; an area that got worse is
  left out of the pack automatically, and the trainer can leave out any area.
5 Build: one .skknow file with the areas kept and the scorecard; Stationkeeper shows the scorecard on its install
  card and installs on double-click.
Rules and counts only; nothing leaves the PC.
"""
import json, os, re, hashlib

EXT = ".skknow"
TEST_SHARE = 10                     # percent of reviewed lines set aside (the same rule Improve Reading uses)

# area: (title, files in the pack, how it is tested)
AREAS = [
    ("reading", "Reading (the text reader)", ("models/",), "words read right on set-aside lines"),
    ("fixes", "OCR fixes and ignore list", ("ocr_corrections.csv", "ocr_ignore.csv"), "words right on corrected lines, with and without the fixes"),
    ("compliance", "Compliance learning (Keep or not, sections)", ("compliance_learned.json",), "agreement with the team's decisions on rows the model did not see"),
    ("acronyms", "Acronyms master database", ("acronym_database.csv",), "added, never replaces (not tested)"),
    ("keywords", "Keyword learning and offerings", ("keyword_learning.json", "offerings.csv"), "added, never replaces (not tested)"),
    ("banned", "Banned words (QA/QC)", ("banned_words.csv",), "added, never replaces (not tested)"),
    ("synonyms", "Section word synonyms", ("placement_synonyms.csv",), "added, never replaces (not tested)"),
]
TITLES = {k: t for k, t, _f, _h in AREAS}


def area_of(pack_name):
    for key, _t, files, _h in AREAS:
        if any(pack_name == f or (f.endswith("/") and pack_name.startswith(f)) for f in files):
            return key
    return ""


# ------------------------------------------------------------------ state (which matrices were gathered)
def _state_path(config_dir):
    return os.path.join(config_dir, "studio.json")


def load_state(config_dir):
    try:
        with open(_state_path(config_dir), encoding="utf-8") as f:
            d = json.load(f)
        return {"matrices": [p for p in d.get("matrices", []) if isinstance(p, str)], "left_out": list(d.get("left_out", []))}
    except (OSError, ValueError, AttributeError):
        return {"matrices": [], "left_out": []}


def save_state(config_dir, st):
    os.makedirs(config_dir, exist_ok=True)
    tmp = _state_path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, _state_path(config_dir))


def _matrices(paths):
    import compliance as C
    out = []
    for p in paths:
        if os.path.isfile(p):
            try:
                out.append(C.Matrix(p).load())
            except Exception:
                continue
    return out


def gather_matrices(paths, learned_path, config_dir):
    """Step 1: learn from past matrices (their Keep and Drop decisions and their placements). Returns
    [(file name, decisions used)]."""
    import complearn
    st = load_state(config_dir)
    L = complearn.Learner(learned_path)
    out = []
    for M in _matrices(paths):
        n = L.learn(M.path, M.items, M.outline)
        out.append((os.path.basename(M.path), n))
        if M.path not in st["matrices"]:
            st["matrices"].append(M.path)
    L.save()
    save_state(config_dir, st)
    return out


# ------------------------------------------------------------------ the test set
def in_test_set(rel):
    """The same stable rule as Improve Reading: about one line in ten is set aside to check the result."""
    return int(hashlib.sha256(rel.encode("utf-8")).hexdigest(), 16) % 100 < TEST_SHARE


def split(samples):
    """(train, test) of the reviewed lines (rejected lines are in neither)."""
    ok = [s for s in samples if not s.get("rejected")]
    test = [s for s in ok if in_test_set(s["rel"])]
    return [s for s in ok if not in_test_set(s["rel"])], test


# ------------------------------------------------------------------ tests per area
_WORD = re.compile(r"\S+")


def _fold(s):
    return " ".join(str(s).split()).casefold()


def apply_fixes(text, fixes, ignore=()):
    fixes = {_fold(k): v for k, v in (fixes or {}).items()}
    ignore = {_fold(k) for k in (ignore or ())}
    out = []
    for w in _WORD.findall(text or ""):
        k = _fold(w)
        if k in ignore:
            continue
        out.append(fixes.get(k, w))
    return " ".join(out)


def word_accuracy(pairs):
    """pairs: [(read, correct)] -> percent of the correct words found in the reading (order kept), or None."""
    right = total = 0
    for read, correct in pairs:
        r, c = [_fold(w) for w in _WORD.findall(read or "")], [_fold(w) for w in _WORD.findall(correct or "")]
        total += len(c)
        i = 0
        for w in c:                          # greedy in order: enough to compare before and after on the same lines
            j = next((k for k in range(i, len(r)) if r[k] == w), None)
            if j is not None:
                right += 1
                i = j + 1
    return round(100.0 * right / total, 1) if total else None


def test_fixes(samples, fixes, ignore=()):
    lines = [s for s in samples if not s.get("rejected") and s.get("read")]
    if not lines or not (fixes or ignore):
        return None
    before = word_accuracy([(s["read"], s["text"]) for s in lines])
    after = word_accuracy([(apply_fixes(s["read"], fixes, ignore), s["text"]) for s in lines])
    return {"now": before, "after": after, "n": len(lines), "unit": "%"}


def test_reading(report):
    """From Improve Reading's report: words read right before and after, on the set-aside lines."""
    if not report or report.get("words_correct_after_pct") is None:
        return None
    return {"now": report.get("words_correct_before_pct"), "after": report.get("words_correct_after_pct"),
            "n": report.get("check_lines", 0), "unit": "%", "applied": bool(report.get("better"))}


def test_compliance(matrices):
    """Keep or not: each decided row predicted by a model that did not see it (5 folds over all gathered matrices),
    against the rule suggestions; sections: each matrix scored with what was learned from the others (top 3)."""
    import complearn
    items = [it for M in matrices for it in M.items]
    cv = complearn.Learner.cross_check(items)
    out = []
    if cv:
        agree, total, rule = cv
        out.append({"test": "Keep or not: agrees with the team", "now": round(100.0 * rule / total, 1),
                    "after": round(100.0 * agree / total, 1), "n": total, "unit": "%", "now_is": "the rules alone"})
    if len(matrices) >= 2:
        import placelearn
        data = {"sources": {}, "placement": {"version": 1, "sources": {}}}
        P = placelearn.Placer(data)
        for M in matrices:
            if M.outline:
                P.learn(complearn.Learner.source_id(M.path), M.items, M.outline)
        t3 = tot = 0
        for M in matrices:
            if not M.outline:
                continue
            r = P.check(complearn.Learner.source_id(M.path), M.items, M.outline)
            if r:
                t3 += r["top3"]; tot += r["total"]
        if tot:
            out.append({"test": "Section suggestions: right section in the top 3", "now": None,
                        "after": round(100.0 * t3 / tot, 1), "n": tot, "unit": "%", "now_is": "no suggestions"})
    return out


# ------------------------------------------------------------------ the scorecard
def scorecard(samples, fixes, ignore, report, matrices, have_files, left_out=()):
    """Rows: {area, title, test, now, after, change, n, include, why}. An area whose test got worse is left out;
    left_out: areas the trainer left out. have_files: pack names that exist on this PC."""
    rows = []

    def row(area, test, res=None):
        files = [f for f in have_files if area_of(f) == area]
        r = {"area": area, "title": TITLES[area], "test": test, "now": None, "after": None, "change": None, "n": 0,
             "files": files}
        if res:
            r.update({k: res.get(k) for k in ("now", "after", "n")})
            if res.get("now") is not None and res.get("after") is not None:
                r["change"] = round(res["after"] - res["now"], 1)
            if res.get("now_is"):
                r["now_is"] = res["now_is"]
        rows.append(r)
        return r
    rd = test_reading(report)
    r = row("reading", "Words read right (set-aside lines)", rd)
    if rd and not rd.get("applied"):
        r["why_auto"] = "Improve Reading did not keep the new reader (it did not read better)"
    row("fixes", "Words right on corrected lines", test_fixes(samples, fixes, ignore))
    comp = test_compliance(matrices)
    if comp:
        for i, res in enumerate(comp):
            row("compliance", res["test"], res)
    else:
        row("compliance", "Keep or not: needs gathered matrices with 10 or more decisions")
    for a in ("acronyms", "keywords", "banned", "synonyms"):
        row(a, "Added, never replaces anyone's own (not tested)")
    worse = {r["area"] for r in rows if r["change"] is not None and r["change"] < 0}
    for r in rows:
        if not r["files"]:
            r.update(include=False, why="Nothing to ship")
        elif r["area"] in worse:
            r.update(include=False, why="Left out: got worse")
        elif r["area"] in left_out:
            r.update(include=False, why="Left out by you")
        else:
            r.update(include=True, why=r.get("why_auto", "In the pack"))
    return rows


def included_files(rows):
    keep = {r["area"] for r in rows if r["include"]}
    return {f for r in rows for f in r["files"] if r["area"] in keep}


def card_lines(info):
    """What Stationkeeper's install card says about a pack: the tests it passed and what it adds."""
    out = []
    for r in info.get("scorecard") or []:
        if not r.get("include"):
            continue
        if r.get("after") is not None:
            now = "none" if r.get("now") is None else f"{r['now']}%"
            out.append(f"{r['title']}: {r['test']}, {now} to {r['after']}%" + (f" (on {r['n']})" if r.get("n") else ""))
        else:
            out.append(f"{r['title']}: {r['test'].split(' (')[0].lower()}")
    return out


def default_name(date):
    return f"Stationkeeper Knowledge {date.isoformat()}{EXT}"
