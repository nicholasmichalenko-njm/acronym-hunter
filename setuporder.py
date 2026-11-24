"""The order of the kinds of text under a heading of the setup (4.63.0; Nicholas 2026-11-23: "I want to be able to set
the order of each type of item under each heading or sub heading in the setup. For example, set that all management
guidance text (as assigned by the style) goes beneath the RFP text within each heading/subheading").

One order for the whole setup; a heading may have its own. Until an order is set, a section is written as it always
was (a note under the requirement it is about, and so on). Once one is set, what is under a heading is grouped by kind
in that order; within a kind the pieces stay in the order they had (the customer's document order, or the order set by
hand). Support text travels with the requirement it supports: it has no row of its own. Kept in the matrix's setup
under "kind_order": {"": [kinds] for the whole setup, heading label: [kinds]}. Standard library only."""

ROWS = (("note", "Leads, page limits and part rules"),
        ("topic", "Topics the section answers"),
        ("objective", "Customer objectives"),
        ("capture", "Captures placed in the section"),
        ("rfp", "RFP text, with its support text"),
        ("customer", "The customer's own pieces"),
        ("pm", "Management guidance and notes"),
        ("library", "Context from library documents"))
NAMES = dict(ROWS)
WITH = {"support": "rfp"}            # a kind that travels with another
WHOLE = ""


def default():
    return [k for k, _n in ROWS]


def clean(order):
    """Every row once, the ones named first in the order given."""
    got = [k for n, k in enumerate(order or []) if k in NAMES and k not in list(order)[:n]]
    return got + [k for k in default() if k not in got]


def _store(S):
    ko = S.get("kind_order")
    return ko if isinstance(ko, dict) else {}


def own(S, label):
    """The order this heading has of its own, or None."""
    o = _store(S).get(label)
    return clean(o) if o else None


def order_for(S, label=WHOLE):
    """The order a heading is written in: its own, else the whole setup's, else None (written as it always was)."""
    return own(S, label) if label and own(S, label) else own(S, WHOLE)


def shown(S, label=WHOLE):
    """The rows to show for a heading: its order, or the usual one when none is set."""
    return order_for(S, label) or default()


def set_order(S, order, label=WHOLE):
    ko = dict(_store(S))
    ko[label] = clean(order)
    S["kind_order"] = ko
    return ko[label]


def clear(S, label=WHOLE):
    """A heading goes back to the whole setup's order; the whole setup goes back to how it was always written (the
    headings' own orders stay)."""
    ko = dict(_store(S))
    had = ko.pop(label, None) is not None
    S["kind_order"] = ko
    return had


def arrange(body, kind_at, c0, c1, order):
    """Group body[c0:c1] by kind in the order given, each kind's pieces in the order they had. kind_at: {index: kind}
    for the paragraphs that have one; anything else (the section's requirement table) stays with the RFP text. Returns
    True when anything moved."""
    if not order or c1 - c0 < 2:
        return False
    rank = {k: n for n, k in enumerate(clean(order))}
    last = [rank["rfp"]]

    def r(i):
        k = kind_at.get(i) or ""
        k = "capture" if k.startswith("cap:") else WITH.get(k, k)
        if k in rank:
            last[0] = rank[k]
            return rank[k]
        return rank["rfp"] if not k else last[0]
    keyed = [(r(i), i) for i in range(c0, c1)]
    new = sorted(keyed, key=lambda x: x[0])           # stable: the order within a kind is kept
    if [i for _r, i in new] == list(range(c0, c1)):
        return False
    body[c0:c1] = [body[i] for _r, i in new]
    return True
