"""4.20.0: the shred's counts in one set of words (claude/stationkeeper-glossary-4.20.md). A piece is anything the shred
holds; a piece with a type is shredded. The menu, Shred's stepper, the bar under the page, the List, Documents' panel
and the Dashboard all read their words here, so the same count never reads four ways."""


def pieces(n):
    """'1 piece', '40 pieces'."""
    return f"{n} piece" + ("" if n == 1 else "s")


def progress(done, total):
    """'12 of 40 pieces shredded'."""
    return f"{done} of {pieces(total)} shredded"


def left(n):
    """What is left to do: '28 to shred', or 'all shredded'."""
    return f"{n} to shred" if n else "all shredded"


def under(done, total):
    """A heading's or a document's share in the List: '3 of 4 shredded'."""
    return f"{done} of {total} shredded"


def of_document(total, not_done):
    """Documents' panel: '40 pieces, 28 to shred' or '40 pieces, all shredded'."""
    return f"{pieces(total)}, {left(not_done)}"


NONE = "nothing extracted"
NO_TYPE = "no type"
