"""Assign shows the document itself (2.55.0): every character of the customer document, in the document's order, with
the review sentences laid over it.

Before 2.55.0 Assign drew the review's sentences one after another, so text the reader left out, merged, reordered or
kept only as a list lead-in was not on the page. Now the page is the file's own text (textcheck.raw_text: Word body,
tables, text boxes, headers, footers, notes; PDF text per page), and each review sentence is found in it:
- exactly, word for word, the next place after the sentence before it (or any free place);
- else by the longest common word runs (difflib) in the stretch between its neighbours, when most of its words are
  there; words the document has inside that stretch but the sentence lacks are marked as differences;
- else as six-word pieces anywhere still free;
- a sentence found nowhere is still shown, after the sentence before it, marked "not found in the document as written".
List lead-ins are tied to their list's first sentence; headings the reader uses as section titles are shown as
headings. Everything else is text not in the review: shown, and added to the review in its place.
Rules only (No AI); nothing leaves the PC.
"""
import difflib, os, re
import textcheck as T

WORD = re.compile(r"[A-Za-z0-9]+")
_CACHE = {}


def doc_lines(path):
    """[(where, line)] of the file, read straight from it (cached while the file is unchanged)."""
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = (os.path.abspath(path), st.st_size, int(st.st_mtime))
    if key not in _CACHE:
        if len(_CACHE) > 8:
            _CACHE.clear()
        try:
            _CACHE[key] = [(w, l.replace("\t", " ")) for w, l in T.content_text(path)]   # 2.57.0: no headers or footers
        except Exception:
            _CACHE[key] = []
    return _CACHE[key]


def _marker_end(line):
    m = T.LIST_MARK.match(line)
    return m.end() if m else 0


def _words(lines):
    """[(word lower, line index, start, end, is list marker)] in reading order."""
    out = []
    for li, (_w, line) in enumerate(lines):
        me = _marker_end(line)
        tm = T.TRAIL.search(line)
        for m in WORD.finditer(line):
            mark = m.end() <= me or (tm is not None and m.start() >= tm.start())
            out.append((m.group(0).lower(), li, m.start(), m.end(), mark))
    return out


def _real(w):
    return w not in T.TRIVIAL and not (len(w) == 1 and w.isalpha())


def align(lines, items, heading_test=None):
    """Lay the review sentences (in review order) over the document's words.
    Returns {"owner": [owner per word], "words", "lost": [(item id, after word index or -1, why)],
             "diff": {item id: n words the document has that the sentence lacks}}.
    owner: ("i", id) a sentence, ("g", id) a word inside a sentence's stretch that the sentence lacks, ("l", id) the
    lead-in of id's list, "h" a heading, "m" a list marker or a trivial word, None text not in the review."""
    seq = _words(lines)
    words = [w for w, *_ in seq]
    n = len(words)
    owner = [None] * n
    at = {}
    for i, w in enumerate(words):
        at.setdefault(w, []).append(i)
    lost, diff, span = [], {}, {}

    def free(p, k):
        return any(owner[q] is None for q in range(p, p + k))

    def exact(ws, after):
        if not ws:
            return None
        j = min(range(len(ws)), key=lambda x: len(at.get(ws[x], ())))      # the rarest word anchors the search
        cands = [p - j for p in at.get(ws[j], ()) if p - j >= 0 and words[p - j:p - j + len(ws)] == ws]
        later = [p for p in cands if p >= after and free(p, len(ws))]
        anyf = [p for p in cands if free(p, len(ws))]
        return (later or anyf or [None])[0], bool(cands)

    order = [it for it in items if T.line_words(it.get("orig_text") or it.get("text") or "")]
    last = 0
    pending = []
    for it in order:
        ws = T.line_words(it.get("orig_text") or it.get("text") or "")
        p, seen = exact(ws, last)
        if p is None:
            pending.append((it, seen))
            continue
        for q in range(p, p + len(ws)):
            if owner[q] is None:
                owner[q] = ("i", it["id"])
        span[it["id"]] = (p, p + len(ws))
        last = p + len(ws)
    # fuzzy: between the neighbours that were found
    ids = [it["id"] for it in order]
    for it, seen in pending:
        ws = T.line_words(it.get("orig_text") or it.get("text") or "")
        k = ids.index(it["id"])
        lo = max([span[x][1] for x in ids[:k] if x in span] or [0])
        hi = min([span[x][0] for x in ids[k + 1:] if x in span] or [n])
        if hi <= lo:
            lo, hi = max(0, lo - 3 * len(ws)), min(n, lo + 4 * len(ws) + 20)
        if hi - lo > 6 * len(ws) + 200:
            hi = min(n, lo + 6 * len(ws) + 200)
        win = [q for q in range(lo, hi) if owner[q] is None]
        sm = difflib.SequenceMatcher(None, ws, [words[q] for q in win], autojunk=False)
        hit = [win[b + x] for a, b, size in sm.get_matching_blocks() for x in range(size)]
        if len(hit) >= max(2, int(0.6 * len(ws))):
            a, b = min(hit), max(hit) + 1
            got = set(hit)
            nd = 0
            for q in range(a, b):
                if owner[q] is None:
                    if q in got:
                        owner[q] = ("i", it["id"])
                    else:
                        owner[q] = ("g", it["id"])
                        nd += _real(words[q]) and not seq[q][4]
            span[it["id"]] = (a, b)
            if nd:
                diff[it["id"]] = nd
            continue
        got = False
        for s in range(0, len(ws), 4):                 # six-word pieces anywhere still free
            piece = ws[s:s + 6]
            if len(piece) < 4:
                continue
            p, _seen = exact(piece, lo)
            if p is not None:
                for q in range(p, p + len(piece)):
                    if owner[q] is None:
                        owner[q] = ("i", it["id"])
                span.setdefault(it["id"], (p, p + len(piece)))
                got = True
        if not got:
            prev = max([span[x][1] - 1 for x in ids[:k] if x in span] or [-1])
            lost.append((it["id"], prev, "same text as another sentence" if seen else "not found in the document as written"))
    # list lead-ins: just before their list's first sentence
    for it in order:
        ld = T.line_words(it.get("lead") or "")
        if not ld or it["id"] not in span:
            continue
        start = span[it["id"]][0]
        cands = [p - 0 for p in at.get(ld[0], ()) if words[p:p + len(ld)] == ld and p < start + 1]
        cands = [p for p in cands if free(p, len(ld))] or [p for p in cands if any(isinstance(owner[q], tuple) and owner[q][0] == "l" for q in range(p, p + len(ld)))]
        if cands:
            p = max(cands)
            for q in range(p, p + len(ld)):
                if owner[q] is None:
                    owner[q] = ("l", it["id"])
    # 2.56.1: text the review already holds elsewhere (a header or footer on every page, boilerplate said again) is a
    # repeat, not text missing from the review: it is shown plain and never added a second time
    bank = "|" + "|".join(" " + " ".join(T.line_words(it.get("orig_text") or it.get("text") or "")) + " "
                          for it in order) + "|"
    q = 0
    while q < n:
        if owner[q] is not None:
            q += 1
            continue
        r = q
        while r < n and owner[r] is None and seq[r][1] == seq[q][1]:
            r += 1
        stretch = " " + " ".join(words[q:r]) + " "
        if r - q >= 1 and stretch in bank:
            for k in range(q, r):
                owner[k] = "r"
        q = r
    # headings and the small stuff
    test = heading_test or T._looks_heading
    head_lines = set()
    for li, (_w, line) in enumerate(lines):
        if line.strip() and test(line.strip()):
            head_lines.add(li)
    for q, (w, li, _s, _e, mark) in enumerate(seq):
        if owner[q] is not None:
            continue
        if li in head_lines:
            owner[q] = "h"
        elif mark or not _real(w):
            owner[q] = "m"
    # a line holding only a short number (a page number) is not text to review
    by_line = {}
    for q, (w, li, *_x) in enumerate(seq):
        by_line.setdefault(li, []).append(q)
    for li, qs in by_line.items():
        if len(qs) == 1 and owner[qs[0]] is None and words[qs[0]].isdigit() and len(words[qs[0]]) <= 4:
            owner[qs[0]] = "m"
    return {"owner": owner, "words": seq, "lost": lost, "diff": diff, "span": span}


def repeats_filter(missing, items):
    """2.56.1: of the page's text not in the review, leave out what the review holds elsewhere (a repeated header or
    footer, boilerplate said again)."""
    bank = "|" + "|".join(" " + " ".join(T.line_words(it.get("orig_text") or it.get("text") or "")) + " " for it in items) + "|"
    return [m for m in missing if not T.line_words(m.get("text", "")) or (" " + " ".join(T.line_words(m["text"])) + " ") not in bank]


def runs(lines, res):
    """Display runs per line: [(line index, start, end, owner)] covering the whole line, so nothing is left out.
    Characters between two words of the same owner belong to it; a sentence keeps the punctuation right after it."""
    seq, owner = res["words"], res["owner"]
    out = []
    by_line = {}
    for q, (_w, li, s, e, _m) in enumerate(seq):
        by_line.setdefault(li, []).append((s, e, owner[q]))
    for li, (_w, line) in enumerate(lines):
        ws = by_line.get(li, [])
        pos = 0
        cur = None
        for s, e, o in ws:
            if cur is not None and cur[2] == o:
                cur[1] = e
                continue
            if cur is not None:
                end = cur[1]
                while end < s and line[end] not in "  ":          # punctuation right after the word
                    end += 1
                cur[1] = end
                if pos < cur[0]:
                    out.append((li, pos, cur[0], "_"))
                out.append((li, cur[0], cur[1], cur[2]))
                pos = cur[1]
            st = s
            while st > pos and line[st - 1] not in "  " and o not in (None,):  # an opening bracket or quote
                st -= 1
            cur = [st, e, o]
        if cur is not None:
            end = cur[1]
            while end < len(line) and line[end] not in "  ":
                end += 1
            cur[1] = end
            if pos < cur[0]:
                out.append((li, pos, cur[0], "_"))
            out.append((li, cur[0], cur[1], cur[2]))
            pos = cur[1]
        if pos < len(line):
            out.append((li, pos, len(line), "_"))
    return out


def missing_runs(lines, res):
    """Stretches of real text not in the review: [(text, first word index, last word index)], each within one line
    or running on while the next line goes on with more of it."""
    seq, owner = res["words"], res["owner"]
    out, cur = [], None
    for q, (w, li, s, e, _m) in enumerate(seq):
        if owner[q] is None:
            if cur is not None and (li == cur[2] or li == cur[2] + 1):
                cur = (cur[0], q, li)
            else:
                if cur is not None:
                    out.append(cur)
                cur = (q, q, li)
        elif owner[q] == "m" and cur is not None and li == cur[2]:
            continue                                   # a small word inside the stretch stays in it
        else:
            if cur is not None:
                out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    texts = []
    fixed = []
    for a, b, li in out:                               # small words just before it on its line start the sentence too
        while a > 0 and owner[a - 1] == "m" and seq[a - 1][1] == seq[a][1] and not seq[a - 1][4]:
            a -= 1
        fixed.append((a, b, li))
    for a, b, _li in fixed:
        la, sa = seq[a][1], seq[a][2]
        lb, eb = seq[b][1], seq[b][3]
        while sa > 0 and lines[la][1][sa - 1] not in " \u00a0":     # an opening bracket or quote: "(719)"
            sa -= 1
        if la == lb:
            t = lines[la][1][sa:eb]
        else:
            t = lines[la][1][sa:] + " " + " ".join(lines[x][1] for x in range(la + 1, lb)) + " " + lines[lb][1][:eb]
        t = " ".join(t.split())
        if T.line_words(t) and any(_real(w) for w in T.line_words(t)):
            end = eb
            line = lines[lb][1]
            while end < len(line) and line[end] in ".,;:)?!”\"'":
                end += 1
            t = " ".join((t + line[eb:end]).split())
            texts.append((t, a, b))
    return texts


def where_label(where):
    """A small label where a new part of the file starts: Page 3, Header, Footer, Footnotes, Slide 2 notes."""
    w = where or ""
    m = re.match(r"p\.(\d+)$", w)
    if m:
        return f"Page {m.group(1)}"
    if w == "document":
        return ""
    m = re.match(r"(header|footer)(\d*)$", w)
    if m:
        return m.group(1).capitalize() + " (repeats on the pages)"
    if w in ("footnotes", "endnotes"):
        return w.capitalize()
    m = re.match(r"(slide|notes|SmartArt) (\d+)$", w)
    if m:
        return {"slide": "Slide", "notes": "Speaker notes, slide", "SmartArt": "SmartArt"}[m.group(1)] + " " + m.group(2)
    return w
