"""The words shown for an acronym find's saved status (4.46.0; UX decision 64, Nicholas 2026-11-16 13:39 and 13:40).

What is saved does not change: a find keeps its status as the scan and the decisions wrote it ("NEW CANDIDATE",
"Resolved (In DB)", ...), the app goes on sorting finds by those words (app_gui.status_kind), and the effort's own
workbook keeps them. The screen and every file made by Export say them in the page's words: plain sentence case,
"customer" (never "client"), "acronym database" (never "DB"), "ignored" (never "excluded").

shown(status)          the status as the screen and an export say it
definition(text)       the Definition column's placeholders the same way
decision(effort)       To decide, In the list, Not a term as Undecided, Added to effort list, Ignored (4.26.1)

A status this table does not know is returned as it is, so a status a later release adds is never hidden.
The list: claude/stationkeeper-build-step-1-status-words-2026-11-16.md. Rules only (No AI)."""
import re

DECISIONS = {"To decide": "Undecided", "In the list": "Added to effort list", "Not a term": "Ignored"}

_EXACT = {
    "NEW CANDIDATE": "New, no definition on record",
    "New candidate": "New, no definition on record",
    "CHOOSE DEFINITION": "Choose a definition",
    "MULTIPLE (Kept All)": "All meanings kept",
    "Resolved (In DB)": "In the acronym database",
    "Client list": "On the customer's list",
    "Client list (database differs)": "On the customer's list (differs from the acronym database)",
    "Customer document": "Defined in a customer document",
    "Customer document (database differs)": "Defined in a customer document (differs from the acronym database)",
    "Defined in document": "Defined in the document",
    "User Selected": "Chosen by a person",
    "User Selected (client list)": "Chosen by a person (from the customer's list)",
    "User Selected (from the document)": "Chosen by a person (from the document)",
    "ADDED MANUALLY": "Added by hand",
    "Not a term in this effort": "Ignored in this effort",
    "EXCLUDED: heading word in capitals": "Ignored: heading word in capitals",
    "Excluded by DB rule": "Ignored by an acronym database rule",
    "On the Exclusion List": "On the ignore list",
    "All instances excluded": "Every place ignored",
    "SYMBOL NOT DEFINED": "Symbol not defined",
    "EQUATION": "Equation",
    "EQUATION (all symbols defined)": "Equation: all symbols defined",
    "CHECK EQUATION PICTURE": "Check the equation picture",
}


def _n(count, one, many):
    return f"{count} {one if str(count) == '1' else many}"


_PATTERNS = (
    (re.compile(r"^CHOOSE \(client list: (\d+) meanings?\)$"),
     lambda m: f"Choose: the customer's list has {_n(m.group(1), 'meaning', 'meanings')}"),
    (re.compile(r"^CHOOSE \(defined (\d+) ways?\)$"),
     lambda m: f"Choose: defined {_n(m.group(1), 'way', 'ways')} in the document"),
    (re.compile(r"^CUSTOMER DOCS DIFFER \((\d+)\)$"), lambda m: f"Customer documents differ ({m.group(1)})"),
    (re.compile(r"^EQUATION: (\d+) symbol\(s\) not defined$"),
     lambda m: f"Equation: {_n(m.group(1), 'symbol', 'symbols')} not defined"),
    (re.compile(r"^Alt form of (.+?) \(effort list: (.+)\)$"),
     lambda m: f"Another form of {m.group(1)} ({decision(m.group(2)).lower()})"),
    (re.compile(r"^Alt form of (.+)$"), lambda m: f"Another form of {m.group(1)}"),
    (re.compile(r"^Effort list: (To decide|In the list|Not a term)(.*)$"), lambda m: decision(m.group(1)) + m.group(2)),
)

_NO_DEFINITION = "No definition on record"
_MULTIPLE = re.compile(r"^MULTIPLE \((\d+) (?:client meanings|meanings|options)\) - Choose: (.*)$", re.S)


def decision(effort):
    """The decision a person made, in the page's words."""
    return DECISIONS.get(effort, effort)


def shown(status):
    """A saved status in the page's words; a status the table does not know as it is."""
    s = str(status or "")
    if s in _EXACT:
        return _EXACT[s]
    for rx, say in _PATTERNS:
        m = rx.match(s)
        if m:
            return say(m)
    return s


def definition(text):
    """The Definition column's placeholders: none on record, several to choose from, one that is ignored."""
    s = str(text or "")
    if s.startswith("[Not in Database"):
        return _NO_DEFINITION
    m = _MULTIPLE.match(s)
    if m:
        return f"{_n(m.group(1), 'meaning', 'meanings')}: " + "; ".join(x.strip() for x in m.group(2).split(" OR "))
    if s.startswith("[EXCLUDED] "):
        return s[len("[EXCLUDED] "):]
    return s
