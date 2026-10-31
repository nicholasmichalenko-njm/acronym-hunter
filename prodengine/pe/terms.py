"""Terms: banned words and phrases, auto-replace (misspellings, trademark and registered marks), employee name near
misses, and the team's custom dictionaries written for Word.

scan(pkg, std)  -> [Hit]       read only; text stays in memory for the screens and is never logged
audit(hits)     -> [Finding]   area "terms"
op_terms(pkg, std, accept=("W2", "W3"), hit_ids=None)   replace on the guarded write path, keeping run formatting
export_dictionaries(std, folder) -> report   .dic (words Word accepts) and .lex (words Word flags), UTF-16 LE

Rules:
  W1 banned word or phrase. With a suggestion the fix is offered for review; without one it is report only.
  W2 a known misspelling: Fix all.
  W3 a product or program name without its mark (TM or R), on first use or on every use as the rule says: Fix all.
  W4 a name one letter off an employee name ("Jordon Reyes"): a question, never fixed without a yes.

What is searched: the visible text of the body, headers, footers, footnotes and endnotes. Field codes and the
results of TOC, REF, PAGEREF, STYLEREF and DOCPROPERTY fields are skipped (they come from somewhere else and change
when Word updates them); deleted text is skipped.
"""
import os
import re
from dataclasses import dataclass

from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, local

SKIP_RESULTS = ("TOC", "REF", "PAGEREF", "STYLEREF", "DOCPROPERTY", "NOTEREF", "SEQ", "PAGE", "NUMPAGES",
                "HYPERLINK", "INDEX")
MARKS = ("™", "®", "(TM)", "(R)", "℠")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


@dataclass
class Hit:
    id: int
    rule: str
    story: str
    para: int
    start: int
    end: int
    found: str
    suggest: str
    why: str
    context: str
    sure: bool
    sup: bool = False       # the added mark goes in its own superscript run


# ---------------------------------------------------------------- text streams
def _streams(root):
    """For each paragraph: (paragraph, text, [(t element, offset in text)]) of the searchable text."""
    out = []
    for p in root.iter(q("p")):
        if next(p.iterancestors(q("p")), None) is not None:
            continue                                   # text box paragraphs are reached on their own
        text, spans = [], []
        stack = []                                     # per open field: [instr, in_result]
        pos = 0
        for el in p.iter(q("r"), q("fldSimple")):
            if local(el) == "fldSimple":
                continue                               # simple fields: their runs are skipped below
            if next(el.iterancestors(q("del")), None) is not None or next(el.iterancestors(q("fldSimple")), None) is not None:
                continue
            fc = el.find("w:fldChar", NS)
            if fc is not None:
                t = fc.get(q("fldCharType"))
                if t == "begin":
                    stack.append(["", False])
                elif t == "separate" and stack:
                    stack[-1][1] = True
                elif t == "end" and stack:
                    stack.pop()
                continue
            it = el.find("w:instrText", NS)
            if it is not None and stack:
                stack[-1][0] += it.text or ""
                continue
            if any(not res for _i, res in stack):
                continue
            if any(i.strip().split(" ")[0].upper() in SKIP_RESULTS for i, _r in stack if i.strip()):
                continue
            for c in el:
                n = local(c)
                if n == "t":
                    spans.append((c, pos))
                    text.append(c.text or "")
                    pos += len(c.text or "")
                elif n in ("tab", "br", "cr"):
                    text.append(" "); pos += 1         # a boundary: no match runs across it
        out.append((p, "".join(text), spans))
    return out


def _stories(pkg):
    out = []
    for part in pkg.stories():
        root = pkg.tree(part)
        if local(root) in ("comments", "glossaryDocument"):
            continue
        out.append(part)
    return out


def _phrase_rx(phrase, flags=re.I):
    body = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", flags)


def _match_case(src, repl):
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def _lev1(a, b):
    """True when a and b differ by exactly one edit."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    s, l = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(s) and s[i] == l[i]:
        i += 1
    return s[i:] == l[i + 1:]


# ---------------------------------------------------------------- scan
def scan(pkg, std):
    T = std["terms"]
    banned = [(_phrase_rx(b["find"]), b) for b in T["banned"]]
    repl = [(_phrase_rx(r["find"], 0 if r.get("case") == "exact" else re.I), r) for r in T["replace"]]
    names = [n.split() for n in T["lists"].get("employee_names", []) if len(n.split()) == 2]
    name_set = {" ".join(n) for n in names}
    cap_pair = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")
    hits, seen_first = [], set()
    k = 0
    for story in _stories(pkg):
        root = pkg.tree(story)
        for pi, (p, text, _spans) in enumerate(_streams(root)):
            if not text.strip():
                continue
            taken = []                                 # spans already claimed by a hit in this paragraph

            def free(a, b):
                return all(b <= x or a >= y for x, y in taken)

            def ctx(a, b):
                return text[max(0, a - 40):a] + "[" + text[a:b] + "]" + text[b:b + 40]

            for rx, r in repl:
                mark = r["replace"].startswith(r["find"]) and r["replace"][len(r["find"]):] in MARKS
                for m in rx.finditer(text):
                    a, b = m.span()
                    if mark:
                        if text[b:b + 4].startswith(MARKS) or text[b:b + 1] in "™®":
                            if r.get("when") == "first":
                                seen_first.add(r["find"])
                            continue
                        if r.get("when") == "first":
                            if r["find"] in seen_first or story != pkg.main:
                                continue
                            seen_first.add(r["find"])
                        rule, sug = "W3", r["replace"]
                    else:
                        rule, sug = "W2", _match_case(m.group(0), r["replace"])
                    if not free(a, b):
                        continue
                    taken.append((a, b)); k += 1
                    hits.append(Hit(k, rule, story, pi, a, b, m.group(0), sug, r.get("why", ""), ctx(a, b), True,
                                    sup=bool(mark and r.get("superscript"))))
            for rx, bnd in banned:
                for m in rx.finditer(text):
                    a, b = m.span()
                    if not free(a, b):
                        continue
                    taken.append((a, b)); k += 1
                    sug = _match_case(m.group(0), bnd["suggest"]) if bnd.get("suggest") else ""
                    hits.append(Hit(k, "W1", story, pi, a, b, m.group(0), sug, bnd.get("why", ""), ctx(a, b), False))
            if T.get("name_check") and names:
                for m in cap_pair.finditer(text):
                    pair = m.group(0)
                    if pair in name_set:
                        continue
                    f, l = m.group(1), m.group(2)
                    for nf, nl in names:
                        if (f == nf and _lev1(l, nl)) or (l == nl and _lev1(f, nf)):
                            a, b = m.span()
                            if free(a, b):
                                taken.append((a, b)); k += 1
                                hits.append(Hit(k, "W4", story, pi, a, b, pair, f"{nf} {nl}",
                                                "One letter off an employee name", ctx(a, b), False))
                            break
    return hits


def audit(hits):
    from prodengine.pe.docmap import Finding
    out = []
    groups = {}
    for h in hits:
        groups.setdefault((h.rule, h.found.lower(), h.suggest), []).append(h)
    label = {"W1": "Banned", "W2": "Misspelled", "W3": "Missing mark", "W4": "Name?"}
    for (rule, _f, sug), hs in groups.items():
        h = hs[0]
        n = len(hs)
        what = f"{label[rule]}: \"{h.found}\"" + (f" -> \"{sug}\"" if sug else "") + (f" ({n} places)" if n > 1 else "") + \
               (f". {h.why}" if h.why else "")
        fix = "op_terms" if sug and rule in ("W2", "W3") else ("review" if sug else "")
        out.append(Finding("terms", "error" if rule in ("W1", "W2", "W3") else "warning", rule, what, h.para, fix,
                           f"{rule}:{h.found.lower()}"))
    return out


# ---------------------------------------------------------------- fix
TERMS_ALLOWED = ("text", "text_len")


def _replace_in(p, spans, a, b, new):
    """Put new over text[a:b], keeping the formatting of the run where the match starts."""
    first = True
    for t, off in spans:
        tx = t.text or ""
        x, y = off, off + len(tx)
        if y <= a or x >= b:
            continue
        s0, s1 = max(a, x) - x, min(b, y) - x
        if first:
            t.text = tx[:s0] + new + tx[s1:]
            first = False
        else:
            t.text = tx[:s0] + tx[s1:]
        if t.text != t.text.strip():
            t.set(XML_SPACE, "preserve")


def _insert_sup(spans, at, mark):
    """Put mark at offset at in its own run, a copy of the run there with vertical alignment superscript."""
    import copy
    from lxml import etree
    from prodengine.engine.ordered import ensure
    for t, off in spans:
        tx = t.text or ""
        if not (off < at <= off + len(tx)):
            continue
        k = at - off
        run = t.getparent()
        rpr = run.find("w:rPr", NS)
        tail = etree.Element(q("r"))
        if rpr is not None:
            tail.append(copy.deepcopy(rpr))
        after_t = list(t.itersiblings())
        if k < len(tx) or after_t:
            t2 = etree.SubElement(tail, q("t")); t2.text = tx[k:]
            if t2.text != t2.text.strip():
                t2.set(XML_SPACE, "preserve")
            for el in after_t:
                tail.append(el)
        t.text = tx[:k]
        if t.text != t.text.strip():
            t.set(XML_SPACE, "preserve")
        sup = etree.Element(q("r"))
        srpr = copy.deepcopy(rpr) if rpr is not None else etree.Element(q("rPr"))
        sup.append(srpr)
        ensure(srpr, "vertAlign").set(q("val"), "superscript")
        st = etree.SubElement(sup, q("t")); st.text = mark
        run.addnext(sup)
        if len(tail) > (1 if rpr is not None else 0):
            sup.addnext(tail)
        return
    raise ValueError("no run at the place of the mark")


def op_terms(pkg, std, accept=("W2", "W3"), hit_ids=None):
    """accept: rules applied in full. hit_ids: single hits the person said yes to (any rule with a suggestion)."""
    hits = scan(pkg, std)
    chosen = [h for h in hits if h.suggest and (h.rule in accept or (hit_ids and h.id in hit_ids))]
    by_para = {}
    for h in chosen:
        by_para.setdefault((h.story, h.para), []).append(h)
    done = 0
    for story in _stories(pkg):
        root = pkg.tree(story)
        streams = None
        for (st, pi), hs in by_para.items():
            if st != story:
                continue
            if streams is None:
                streams = _streams(root)
                pkg.touch(story)
            p, text, spans = streams[pi]
            pkg.mark(p)
            expect = text
            for h in sorted(hs, key=lambda h: -h.start):          # right to left keeps the offsets valid
                if text[h.start:h.end] != h.found:
                    raise ValueError("the text moved since the scan")
                if h.sup:
                    _insert_sup(spans, h.end, h.suggest[len(h.found):])
                else:
                    _replace_in(p, spans, h.start, h.end, h.suggest)
                expect = expect[:h.start] + h.suggest + expect[h.end:]
                done += 1
            if _streams(p)[0][1] != expect:            # proof: only the matched words changed
                raise ValueError("a replacement changed more than the matched words")
    return {"replaced": done, "checks": []}


# ---------------------------------------------------------------- dictionaries for Word
def export_dictionaries(std, folder):
    """Writes each dictionary of std["terms"]["dictionaries"] into folder. Word reads custom dictionaries as
    Unicode (UTF-16 LE with a byte order mark), one word per line. A dictionary holds single words, so names are
    split into their words and banned phrases stay in the app's check (listed in the report)."""
    T = std["terms"]
    lists = dict(T["lists"])
    # Word's speller checks single words; a hyphenated compound or a phrase is not reliably flagged, so those stay
    # in the app's check only
    single = lambda w: " " not in w and "-" not in w
    lists["banned_words"] = sorted({b["find"] for b in T["banned"] if single(b["find"])} | set(lists.get("banned_words", [])))
    os.makedirs(folder, exist_ok=True)
    report = {"files": {}, "phrases_kept_in_app": [b["find"] for b in T["banned"] if " " in b["find"] or "-" in b["find"]], "skipped": []}
    for fname, d in T["dictionaries"].items():
        words = set()
        for ln in d["lists"]:
            for entry in lists.get(ln, []):
                for w in entry.split():
                    w = w.strip()
                    if not w or len(w) > 64:
                        report["skipped"].append(w)
                        continue
                    words.add(w)
        data = "\r\n".join(sorted(words, key=str.lower)) + "\r\n"
        path = os.path.join(folder, fname)
        with open(path, "wb") as f:
            f.write(b"\xff\xfe" + data.encode("utf-16-le"))
        report["files"][fname] = {"kind": d["kind"], "words": len(words)}
    if len(T["dictionaries"]) > 9:
        report["warning"] = "Word lists at most 10 custom dictionaries, CUSTOM.DIC included"
    return report
