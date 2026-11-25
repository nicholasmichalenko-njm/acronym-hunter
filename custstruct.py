"""The Customer Doc Structure (4.74.0; Nicholas 2026-11-24, claude/stationkeeper-shred-structure-and-customer-facts-
direction-2026-11-24.md, step S2): the sections, headings and subheads of the customer's documents, marked by a person
while shredding, so everything captured says where it came from in the customer's own numbering. A Customer heading
never adds to our outline. A piece's customer reference is the nearest customer heading marked above it in its
document (the number as printed, else the title); with none marked, the section the reader found, as before.

Also here: the pieces sent to the Outline page from Shred (Send to Outline), which wait there to be marked.

Kept in the matrix's setup, read only when there: "cust_heads" ({piece id: {"num", "title", "level"}}) and
"to_outline" ([piece ids]). Rules only (No AI); nothing leaves the PC. Standard library only."""
import re

import setupdoc as SD

LEVELS = ((1, "Section"), (2, "Heading"), (3, "Subhead"))
NAME = dict(LEVELS)
_NUM = re.compile(r"^\s*((?:Section|Attachment|Exhibit|Appendix|Annex|Factor|Subfactor|Volume|Part|Tab)\s+[A-Za-z0-9][\w.\-]*"
                  r"|[A-Z]\.\d+(?:\.\d+)*(?:\([a-z0-9]+\))*|\d+(?:\.\d+)+(?:\([a-z0-9]+\))*|\d+\.?(?=\s)|[A-Z]-\d+|[A-Z]\.(?=\s))"
                  r"[\s.:)\-–—]*(.*)$")


def heads(M):
    return SD.setup_of(M).setdefault("cust_heads", {})


def propose(it):
    """(number, title, level) read from a piece's own words: "L.3.2 Technical Approach" -> ("L.3.2", "Technical
    Approach", 2). The level goes by how deep the number is (one part a Section, two a Heading, more a Subhead); with
    no number it is a Heading. A section's own letter in front ("L.") does not count."""
    text = " ".join((it.get("text") or "").split())
    m = _NUM.match(text)
    num, title = (m.group(1).rstrip("."), m.group(2)) if m else ("", text)
    title = " ".join(title.strip(" .:;-").split()[:14])
    if num and not title and it.get("section_title"):
        title = it["section_title"]
    parts = [p for p in re.split(r"[.\-]", re.sub(r"^[A-Za-z]+\s+", "", num)) if p] if num else []
    if parts and parts[0].isalpha():                 # "L.3.2": the section's own letter is not a level
        parts = parts[1:] or parts
    level = 2 if not num else max(1, min(3, len(parts)))
    return num, title, level


def label(h):
    return " ".join(x for x in (h.get("num", ""), h.get("title", "")) if x)


def parse(text):
    """What a person typed on the bar, "L.3.2: Technical Approach", as (number, title)."""
    t = " ".join((text or "").split())
    if ":" in t:
        a, b = t.split(":", 1)
        return a.strip(), b.strip()
    m = _NUM.match(t)
    return (m.group(1).rstrip("."), m.group(2).strip()) if m and m.group(2).strip() else ("", t)


def mark(M, it, num, title, level=2):
    """Mark a piece as a section or heading of the customer's document. Returns its label."""
    h = {"num": " ".join((num or "").split()), "title": " ".join((title or "").split())[:160],
         "level": level if level in NAME else 2}
    if not (h["num"] or h["title"]):
        return ""
    heads(M)[it.get("id")] = h
    M.log(it.get("id", ""), f"Customer heading: {label(h)}")
    M.pending = True
    return label(h)


def unmark(M, it):
    if heads(M).pop(it.get("id"), None) is None:
        return False
    M.pending = True
    return True


def is_head(M, it):
    return it.get("id") in heads(M)


def above(M, it):
    """The nearest customer heading marked above a piece in its own document (the piece's own when it is one), or None."""
    hs = heads(M)
    if not hs:
        return None
    if it.get("id") in hs:
        return hs[it["id"]]
    best = None
    for x in M.items:
        if x is it or x.get("id") == it.get("id"):
            break
        if x.get("file") == it.get("file") and x.get("id") in hs:
            best = hs[x["id"]]
    return best


def ref_of(M, it):
    """The customer's reference for a piece, as printed: the number of the customer heading above it (its title when it
    has no number), else the section the reader found. The page is kept beside it by the columns that show it."""
    h = above(M, it)
    if h:
        return h.get("num") or h.get("title") or ""
    return it.get("section") or ""


def tree(M, file=None):
    """The marked headings in the customer's order: [{"id", "file", "label", "level"}]."""
    hs = heads(M)
    return [{"id": it["id"], "file": it.get("file", ""), "label": label(hs[it["id"]]), "level": hs[it["id"]].get("level", 2)}
            for it in M.items if it.get("id") in hs and (file is None or it.get("file") == file)]


# ------------------------------------------------------------------ Send to Outline
def sent(M):
    """The pieces sent to the Outline page and not yet dealt with there, in the customer's order."""
    ids = set(SD.setup_of(M).get("to_outline") or [])
    return [it for it in M.items if it.get("id") in ids]


def send(M, it):
    """Send to Outline: the piece waits on the Outline page; nothing else changes. Returns False when it already waits."""
    S = SD.setup_of(M)
    cur = list(S.get("to_outline") or [])
    if it.get("id") in cur:
        return False
    cur.append(it.get("id"))
    S["to_outline"] = cur
    M.log(it.get("id", ""), "sent to Outline")
    M.pending = True
    return True


def unsend(M, iid):
    S = SD.setup_of(M)
    cur = [i for i in (S.get("to_outline") or []) if i != iid]
    if len(cur) == len(S.get("to_outline") or []):
        return False
    S["to_outline"] = cur
    M.pending = True
    return True
