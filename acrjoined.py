"""Terms joined by a slash or an ampersand are taken whole (4.30.8; Nicholas 2026-11-13 20:55 and 20:58).

The reader's pattern for capital-letter terms stops at eight characters. A longer joined term was cut there, so the
reader offered its front piece ending in the slash as one find and the rest as another, beside the whole term found by
another pattern: two or three decisions for one term, one of them never a term. Now, when a find is part of a chain of
capital-letter pieces joined by "/" or "&", the whole chain is the find, and the pieces inside it are not offered. A find
left ending in "/" or "&" with nothing joined after it loses that mark.

Rules only (No AI). Standard library only; nothing leaves the PC."""
import re

CHAIN = re.compile(r"[A-Z][A-Z0-9]*(?:[/&][A-Z][A-Z0-9]*)+s?(?![A-Za-z0-9])")
MOST = 30            # a chain longer than this is a line of text, not a term


def whole(text, start, raw):
    """(the find to use, where it ends in the text) for a capital-letter find at start. A find inside a joined chain
    becomes the whole chain; one ending in a join mark with nothing after loses the mark; any other find is as it was."""
    end = start + len(raw)
    nxt = text[end:end + 1]
    if "/" in raw or "&" in raw or nxt in ("/", "&"):
        m = CHAIN.match(text, start)
        if m and len(m.group(0)) > len(raw.rstrip("/&")) and len(m.group(0)) <= MOST:
            return m.group(0), m.end()
    trimmed = raw.rstrip("/&")
    if trimmed != raw:
        return (trimmed if len(trimmed) >= 2 else ""), end
    return raw, end
