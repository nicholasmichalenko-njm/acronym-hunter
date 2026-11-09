"""A heading on the same line as its text (3.92.1; claude/stationkeeper-navigation-3.93.md): "L.4.2.1 Telemetry,
Tracking and Command. The Offeror shall..." split in Verify into the heading and the text it runs into, so the outline
gets the heading and Review gets the text.

runin(text) -> the heading's words at the start of the text, or ""     the suggestion: a section number, a short title
                                                                      ending in a period or colon, then a sentence
at(line_text, head) -> where the heading ends in the line, or 0       matched word by word (spacing may differ)
split_doc(doc, splits) -> (doc, remap, heads, bodies)                 the reader's page form with each split line made
                                                                      two lines: the heading, then the text (its own
                                                                      character places kept)
Rules only; nothing leaves the PC."""
import re

_RUNIN = re.compile(r"^\s*((?:[A-Z]\.)?\d+(?:\.\d+)*\.?|[A-Z]\.\d+(?:\.\d+)*\.?|\(?[a-z]\)|[IVX]+\.)\s+"
                    r"([A-Z][^.:;?!]{1,90}?)([.:])\s+(?=[A-Z(\"'“])")
_REQ = re.compile(r"\b(shall|must|will|should)\b", re.I)


def runin(text):
    """The run-in heading at the start of a block's text: number, title (at most 12 words, no shall or must), its
    period or colon. "" when the text does not start that way."""
    m = _RUNIN.match(text or "")
    if not m:
        return ""
    title = m.group(2).strip()
    if len(title.split()) > 12 or _REQ.search(title):
        return ""
    rest = (text or "")[m.end():]
    if len(rest.split()) < 3:                       # a heading alone on its line is not run in
        return ""
    return (text or "")[:m.end()].strip()


def at(line_text, head):
    """Where head ends in the line (after its last character), matching words with any spacing; 0 when it is not
    the line's start."""
    words = (head or "").split()
    if not words:
        return 0
    rx = re.compile(r"^\s*" + r"\s+".join(re.escape(w) for w in words))
    m = rx.match(line_text or "")
    return m.end() if m else 0


def split_doc(doc, splits):
    """splits: {(page index, line index): heading text}. Returns (new doc, {old key: new key}, heading keys, text keys);
    a key with no match is left as it was."""
    pages, remap, heads, bodies = [], {}, set(), set()
    for pi, p in enumerate(doc["pages"]):
        lines = []
        for li, ln in enumerate(p["lines"]):
            head = splits.get((pi, li))
            k = at(ln["text"], head) if head else 0
            rest = ln["text"][k:] if k else ""
            if k and rest.strip():
                lead = len(rest) - len(rest.lstrip())
                remap[(pi, li)] = (pi, len(lines))
                heads.add((pi, len(lines)))
                lines.append(dict(ln, text=ln["text"][:k].rstrip()))
                bodies.add((pi, len(lines)))
                lines.append(dict(ln, text=rest.lstrip(), a=ln.get("a", 0) + k + lead))
            else:
                remap[(pi, li)] = (pi, len(lines))
                lines.append(ln)
        pages.append(dict(p, lines=lines))
    return dict(doc, pages=pages), remap, heads, bodies
