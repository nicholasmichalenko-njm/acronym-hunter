"""3.24.1: a numbering level's text as people read it, not Word's %1 codes.

Word writes a level's number text as "%1.%2" (the level 1 number, a period, the level 2 number). Production Standards
shows it as it will look ("1.1", "Section A", "I.1") and turns what you type back into Word's codes: the last number
in the text is this level's own, the one before it the level above, and so on ("1.1.1" on level 3 is %1.%2.%3; "a)"
on level 2 is %2). Codes typed with % stay as typed.
"""
import re

SAMPLE = {"decimal": "1", "decimalZero": "01", "lowerLetter": "a", "upperLetter": "A",
          "lowerRoman": "i", "upperRoman": "I", "ordinal": "1st", "cardinalText": "One", "ordinalText": "First"}
CODE = re.compile(r"%([1-9])")
# a number standing alone: digits (with an optional leading zero), one letter, or a roman run, not inside a word
TOKEN = re.compile(r"(?<![A-Za-z0-9])(\d+(?:st|nd|rd|th)?|[IVXLC]+|[ivxlc]+|[A-Za-z])(?![A-Za-z0-9])")


def sample(fmt):
    return SAMPLE.get(fmt or "decimal", "1")


def show(text, fmts):
    """Word's codes in text, shown with each level's sample number (fmts: the formats of levels 1, 2, ...)."""
    if not text:
        return ""
    def one(m):
        n = int(m.group(1))
        return sample(fmts[n - 1] if n - 1 < len(fmts) else "decimal")
    return CODE.sub(one, str(text))


def parse(shown, level=9):
    """What was typed, back in Word's codes: the last number is this level's, the ones before it the levels above.
    Text that already has % codes, or no number at all (a bullet), is kept as typed."""
    s = (shown or "").strip()
    if not s or "%" in s:
        return s
    level = max(1, min(9, int(level or 1)))
    toks = list(TOKEN.finditer(s))[-level:]
    if not toks:
        return s
    first = level - len(toks) + 1
    out, last = [], 0
    for k, m in enumerate(toks):
        out.append(s[last:m.start()]); out.append(f"%{first + k}"); last = m.end()
    out.append(s[last:])
    return "".join(out)


def keep_or_parse(shown, raw, fmts, level=9):
    """The stored text: the original when the shown text was not changed (so a level that skips one, like %1.%3, stays)."""
    if raw is not None and (shown or "").strip() == show(raw, fmts).strip():
        return raw
    return parse(shown, level)
