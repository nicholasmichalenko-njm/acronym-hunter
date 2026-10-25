"""Alternate forms of a term (2.26.0): TT&C written as TTC, or SATCOM as SatCom.

An alternate form is never a row of its own. It is kept with its primary term:
  - effort list: the "Alt forms" column of the primary's row
  - master database: the "Alt forms" column of the primary's row
  - any list the app reads: a term cell written "TT&C (TTC)" means primary TT&C with alternate form TTC
Every list the app writes shows the primary with its alternate forms in parentheses: "TT&C (TTC)".
Pure functions; nothing is read or written here.
"""
import re

ALT_COL = "Alt forms"
_SF = re.compile(r"^[A-Za-z0-9Ͱ-Ͽ][A-Za-z0-9&/\-.+Ͱ-Ͽ°µ]{0,15}$")
_SPLIT = re.compile(r"\s*(?:\||;|,|/(?=\s)|\bor\b)\s*")


def looks_like_term(s):
    """A short form: no spaces, has a capital or a digit or a symbol, at most 16 characters."""
    s = (s or "").strip()
    return bool(_SF.match(s)) and (any(c.isupper() or c.isdigit() for c in s) or not s.isalpha())


def parse_alts(text):
    """'TTC | T&C', 'TTC, T&C' or 'TTC; T&C' -> ['TTC', 'T&C'] (order kept, no repeats, blanks dropped)."""
    out = []
    for a in _SPLIT.split(text or ""):
        a = a.strip().strip("()").strip()
        if a and a not in out:
            out.append(a)
    return out


def split_term(cell):
    """'TT&C (TTC)' -> ('TT&C', ['TTC']). A cell without a parenthesized short form comes back unchanged with no alt
    forms, so 'Statement of Work' or 'C(3)' stay as they are."""
    s = (cell or "").strip()
    m = re.match(r"^(.+?)\s+\(([^()]+)\)\s*$", s)          # a space before the parenthesis: "C(3)" stays whole
    if not m:
        return s, []
    primary, inside = m.group(1).strip(), m.group(2)
    alts = parse_alts(inside)
    if not looks_like_term(primary) or not alts or not all(looks_like_term(a) for a in alts):
        return s, []
    return primary, [a for a in alts if a != primary]


def join_term(primary, alts):
    """('TT&C', ['TTC']) -> 'TT&C (TTC)'; no alt forms -> the primary alone."""
    alts = [a for a in (alts if isinstance(alts, (list, tuple)) else parse_alts(alts)) if a and a != primary]
    return f"{primary} ({', '.join(alts)})" if alts else primary


def merge_alts(*lists):
    """Union of several alt-form lists or 'A | B' strings, order kept -> 'A | B'."""
    out = []
    for x in lists:
        for a in (x if isinstance(x, (list, tuple)) else parse_alts(x)):
            if a and a not in out:
                out.append(a)
    return " | ".join(out)
