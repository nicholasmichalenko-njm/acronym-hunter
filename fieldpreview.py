"""What a field shows (4.7.0; claude/stationkeeper-team-library-files-decisions-2026-11-10.md, decision 7; reference page
claude/stationkeeper-values-in-files-4.7.html). While a field code is typed, its sample result is worked out by rules on
a fictional sample page, the way Word would show it there:
- PAGE, NUMPAGES and SECTIONPAGES, with \\* ARABIC, ROMAN, roman, ALPHABETIC, alphabetic;
- SEQ, with its restart switch (\\s n restarts after each heading at level n; \\r n resets; \\c repeats; \\h hides);
- STYLEREF, by level or by style name (\\s and \\n give the heading's number);
- DOCPROPERTY (Title, Subject, Company and the sample's own properties);
- DATE, CREATEDATE, SAVEDATE and PRINTDATE, with \\@ date pictures;
- TOC: which levels and which bookmark it lists, in words.
Any other field says "Word shows this one". Check in Word (Field recipes) updates every field in a real copy and reports
any Error!. Rules only (No AI); nothing leaves the PC."""
import datetime, re

OTHER = "Word shows this one"
# the sample page: page 3 of 12, in section 2 (4 pages), under Heading 1 "2 Technical Approach" and Heading 2
# "2.1 Risk Management"; tables and figures already above it on that heading: one table, two figures
SAMPLE = {"page": 3, "numpages": 12, "sectionpages": 4, "section": 2,
          "headings": {1: ("2", "Technical Approach"), 2: ("2.1", "Risk Management"), 3: ("2.1.4", "Mitigation"),
                       7: ("A", "Resumes"), 8: ("A.1", "Program Manager")},
          "styles": {"Title": "Volume I Technical", "Cover Title": "Volume I Technical", "Heading 1": "Technical Approach"},
          "seq_before": {"Table": 1, "Figure": 2, "Equation": 0, "TableApp": 0},
          "props": {"Title": "Volume I Technical", "Subject": "Response to EX-26-R-0001", "Company": "Example Corp.",
                    "Author": "A. Writer", "Manager": "P. Manager", "Classification": "CUI", "Solicitation": "EX-26-R-0001"},
          "when": datetime.datetime(2026, 11, 10, 13, 45), "created": datetime.datetime(2026, 10, 2, 9, 5)}


def tokens(code):
    """The code's words, with quoted words kept whole (TOC \\o "1-3")."""
    return [a or b for a, b in re.findall(r'"([^"]*)"|(\S+)', code or "")]


def _switch(tok, name):
    """The value after \\name, or True when it takes none, or None when it is not there."""
    low = [t.lower() for t in tok]
    key = "\\" + name.lower()
    if key not in low:
        return None
    i = low.index(key)
    if i + 1 < len(tok) and not tok[i + 1].startswith("\\"):
        return tok[i + 1]
    return True


def _roman(n):
    out, vals = "", ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                     (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out


def number_format(n, tok):
    fmt = _switch(tok, "*")
    f = str(fmt) if isinstance(fmt, str) else ""
    if f == "ROMAN":
        return _roman(n)
    if f == "roman":
        return _roman(n).lower()
    if f in ("ALPHABETIC", "alphabetic"):
        s = chr(ord("A") + (n - 1) % 26) * ((n - 1) // 26 + 1)
        return s if f == "ALPHABETIC" else s.lower()
    return str(n)


_PICTURE = (("yyyy", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("dddd", "%A"), ("ddd", "%a"),
            ("dd", "%d"), ("HH", "%H"), ("hh", "%I"), ("mm", "%M"), ("am/pm", "%p"), ("AM/PM", "%p"))


def date_picture(dt, pic):
    """A Word date picture (\\@ "MMMM d, yyyy") as the sample date shows it."""
    if not pic:
        return f"{dt.month}/{dt.day}/{dt.year}"
    out, i = "", 0
    while i < len(pic):
        for w, f in _PICTURE:
            if pic.startswith(w, i):
                out += dt.strftime(f)
                i += len(w)
                break
        else:
            ch = pic[i]
            if pic.startswith("M", i):
                out += str(dt.month); i += 1
            elif pic.startswith("d", i):
                out += str(dt.day); i += 1
            elif pic.startswith("H", i) or pic.startswith("h", i):
                out += str(dt.hour if ch == "H" else (dt.hour % 12 or 12)); i += 1
            else:
                out += ch; i += 1
    return out


def one(code, sample=None, seq=None):
    """What one field shows on the sample page: (text, known). known is False for a field the rules do not work out."""
    s = sample or SAMPLE
    tok = tokens(code)
    if not tok:
        return "", False
    name = tok[0].upper()
    if name == "PAGE":
        return number_format(s["page"], tok), True
    if name == "NUMPAGES":
        return number_format(s["numpages"], tok), True
    if name == "SECTIONPAGES":
        return number_format(s["sectionpages"], tok), True
    if name == "SECTION":
        return number_format(s["section"], tok), True
    if name == "SEQ" and len(tok) > 1:
        ident = tok[1]
        counts = seq if seq is not None else {}
        if _switch(tok, "h") is True:
            return "", True
        r = _switch(tok, "r")
        if isinstance(r, str) and r.isdigit():
            counts[ident] = int(r)
        elif _switch(tok, "c") is True:
            counts[ident] = counts.get(ident, s["seq_before"].get(ident, 0))
        else:
            restart = _switch(tok, "s")
            base = s["seq_before"].get(ident, 0) if not (isinstance(restart, str) and restart.isdigit()
                                                         and int(restart) not in s["headings"]) else 0
            counts[ident] = counts.get(ident, base) + 1
        return number_format(counts[ident], tok), True
    if name == "STYLEREF" and len(tok) > 1:
        what = tok[1]
        lvl = int(what) if what.isdigit() else next((int(m.group(1)) for m in [re.match(r"(?i)heading (\d)$", what)] if m), None)
        numbered = _switch(tok, "s") is True or _switch(tok, "n") is True or _switch(tok, "r") is True
        if lvl is not None and lvl in s["headings"]:
            num, text = s["headings"][lvl]
            return (num if numbered else text), True
        if what in s["styles"]:
            return s["styles"][what], True
        return "Error! No text of specified style in document.", True
    if name == "DOCPROPERTY" and len(tok) > 1:
        return s["props"].get(tok[1], f"Error! Unknown document property name."), True
    if name in ("DATE", "TIME", "SAVEDATE", "PRINTDATE", "CREATEDATE"):
        dt = s["created"] if name == "CREATEDATE" else s["when"]
        pic = _switch(tok, "@")
        if name == "TIME" and not isinstance(pic, str):
            pic = "h:mm am/pm"
        return date_picture(dt, pic if isinstance(pic, str) else ""), True
    if name == "TOC":
        o = _switch(tok, "o")
        b = _switch(tok, "b")
        bits = [f"Table of contents: heading levels {o}" if isinstance(o, str) else "Table of contents: the TOC styles"]
        if isinstance(b, str):
            bits.append(f"only what the bookmark {b} holds")
        if _switch(tok, "h") is True:
            bits.append("entries are links")
        if _switch(tok, "n") is not None:
            bits.append("no page numbers")
        return ", ".join(bits), True
    return OTHER, False


def recipe(codes, between="", sample=None, label=""):
    """A recipe's fields one after the other, with the text between them (a caption: STYLEREF then SEQ). Returns
    (text, every field known)."""
    seq = {}
    parts, known = [], True
    for c in codes or []:
        t, k = one(c, sample, seq)
        parts.append(t)
        known = known and k
    text = (between or "").join(parts)
    return ((label + " " if label else "") + text).strip(), known


def label_of(codes):
    """The caption's label from its SEQ identifier (Table, Figure), so a caption reads "Table 2-2"."""
    for c in codes or []:
        tok = tokens(c)
        if tok and tok[0].upper() == "SEQ" and len(tok) > 1:
            return re.sub(r"App$", "", tok[1])
    return ""
