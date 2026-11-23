"""Linking the pieces of a customer's documents to the instructions they concern (4.59.3: moved out of compliance.py,
which is at its size limit, and made to work once per piece). Rules only (No AI); nothing leaves the PC."""
import re


def link_items(items):
    """Link Evaluation (M) and SOW items to the Instruction items they concern: explicit section cross-references,
    then strong word overlap (Jaccard >= 0.3, best match only).
    4.59.3: the same links, worked out once per item. Each instruction's words are read once and looked up by word, and
    sections are looked up by number; before, every item read every instruction's words again (25,000 items froze the
    window for a minute)."""
    import compliance as C
    _words = C._words
    by_section = {}                                    # a section number and each number above it -> the ids under it
    for o in items:
        s = o.get("section") or ""
        if not s:
            continue
        parts = s.split(".")
        for k in range(1, len(parts) + 1):
            by_section.setdefault(".".join(parts[:k]), []).append(o)
    instr = [it for it in items if it["type"] in ("Instruction", "Format")]
    iwords = [_words(o["text"]) for o in instr]
    by_word = {}
    for k, ow in enumerate(iwords):
        for x in ow:
            by_word.setdefault(x, []).append(k)
    for it in items:
        links = []
        refs = [r.strip() for r in it.get("xrefs", "").split(";") if r.strip()]
        for r in refs:
            num = re.sub(r"^(?:section|sec\.|paragraph|para\.?|¶)\s+", "", r, flags=re.I)
            if "." not in num:
                continue                                # "Section C" names a whole section: too broad to link
            for o in by_section.get(num, ()):
                if o is not it:
                    links.append(o["id"])
        if it["type"] in ("Evaluation", "SOW") and not links and instr:
            w = _words(it["text"])
            shared = {}
            for x in w:
                for k in by_word.get(x, ()):
                    shared[k] = shared.get(k, 0) + 1
            best, score = None, 0.0
            for k in sorted(shared):                    # in the instructions' order: the first of equal matches wins, as before
                j = shared[k] / (len(w) + len(iwords[k]) - shared[k])
                if j > score:
                    best, score = instr[k], j
            if best is not None and score >= 0.3:
                links.append(best["id"])
        it["links"] = "; ".join(dict.fromkeys(links))[:300]
    return items
