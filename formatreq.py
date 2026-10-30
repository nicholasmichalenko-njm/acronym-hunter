"""Formatting requirements and the page-limited flag (2.94.0), for Effort Home, the overview and the readable copy.

From the submission requirements register (subreq: what the customer documents set, with the person's edits, hides and
additions): the page limits per volume, and one line per formatting rule (font, font in tables and figures, margins,
page size, line spacing, file format, file naming, plus any the person added), each either required (with its value
and where it was found) or not specified. Page-limited is what the proposal manager set (yes or no), else yes when a
page limit was found, else unknown: the app never calls an effort not page-limited on a guess. Standard library only.
"""
ASPECTS = (("Format", "Font"), ("Format", "Font in tables and figures"), ("Format", "Margins"), ("Format", "Page size"),
           ("Format", "Line spacing"), ("File", "File format"), ("File", "File naming"))
SETTINGS = {"": "Decide from the documents", "yes": "Page-limited", "no": "Not page-limited"}


def _where(r):
    """'Kestrel RFP Sections C L M, L.1 General Instructions, p. 3': the document's name, the section and page, short."""
    import re
    if r.get("manual"):
        return "typed in"
    name = (r.get("doc") or "").split(", ")[0]
    loc = r.get("loc") or ""
    sec = re.search(r"section '([^']+)'", loc)
    page = re.search(r"\bp\.?\s?(\d+)", loc)
    bits = [name] + ([sec.group(1).title() if sec.group(1).isupper() else sec.group(1)] if sec else []) + ([f"p. {page.group(1)}"] if page else [])
    if not sec and not page and loc:
        bits.append(loc.strip("()"))
    return ", ".join(b for b in bits if b)


def card(rows, setting=""):
    """{"page_limited": True/False/None, "how": "set"/"found"/"", "limits": [{subject, value, where, row}],
    "lines": [{label, value, where, required, row}]}."""
    limits = [{"subject": r["subject"], "value": r["value"], "where": _where(r), "row": r} for r in rows if r["kind"] == "Page limit"]
    if setting == "yes":
        pl, how = True, "set"
    elif setting == "no":
        pl, how = False, "set"
    elif limits:
        pl, how = True, "found"
    else:
        pl, how = None, ""
    by = {(r["kind"], r["subject"]): r for r in rows if r["kind"] in ("Format", "File")}
    lines = []
    for k in ASPECTS:
        r = by.pop(k, None)
        lines.append({"label": k[1], "value": r["value"] if r else "", "where": _where(r) if r else "", "required": r is not None, "row": r})
    for (kind, subj), r in sorted(by.items(), key=lambda x: x[0][1]):     # the person's own and anything else found
        lines.append({"label": subj, "value": r["value"], "where": _where(r), "required": True, "row": r})
    return {"page_limited": pl, "how": how, "limits": limits, "lines": lines}


def flag_text(c):
    """'PAGE-LIMITED: Volume I 40, Volume II 20', 'Not page-limited', or 'Page limits: none found yet'."""
    if c["page_limited"] is True:
        lim = limits_text(c)
        return "PAGE-LIMITED" + (f": {lim}" if lim else "")
    if c["page_limited"] is False:
        return "Not page-limited"
    return "Page limits: none found yet"


def limits_text(c, most=4):
    """'50 pages' (one limit for the proposal) or 'Vol I 40, Vol II 20' (per volume)."""
    lim = c["limits"]
    if len(lim) == 1 and lim[0]["subject"] in ("Proposal", ""):
        return lim[0]["value"]
    out = ", ".join(f"{x['subject'].replace('Volume ', 'Vol ')} {x['value'].replace(' pages', '')}" for x in lim[:most])
    return out + ("..." if len(lim) > most else "")


def spot_text(c):
    """The banner spot: 'Yes: 50 pages', 'No', or 'Not found yet'."""
    if c["page_limited"] is True:
        return "Yes" + (f": {limits_text(c)}" if c["limits"] else "")
    return "No" if c["page_limited"] is False else "Not found yet"


def for_effort(lib, rec):
    """card() for an effort's library and record (empty when either is missing)."""
    import subreq as SR
    rows = SR.Register(lib).rows() if lib is not None else []
    return card(rows, (rec.data.get("page_limited", "") if rec is not None else ""))
