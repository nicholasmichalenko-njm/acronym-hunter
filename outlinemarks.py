"""A prescribed outline, marked (4.5.0 loose end; claude/stationkeeper-releases-4.3-to-4.5-decisions-2026-11-10.md,
decision 4). When the solicitation prescribes the outline (Matrix & Outline > Outline, setup "outline_from" =
"prescribed"), its sections are marked as the customer's ("by": "customer") and each volume takes its page limit
from the solicitation's words ("Volume I ... shall not exceed 40 pages", or a table row "I  Technical  40"), unless the
team already set one. Our own subsections added later carry no mark. Rules only (No AI); nothing leaves the PC.

limits(M) -> {volume number: pages}; mark(M) -> {"marked": n, "pages": {label: pages}}."""
import re

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
_N = r"(?P<n>[IVX]{1,4}|\d{1,2})"
_SENT = re.compile(r"\bVolume\s+" + _N + r"\b[^.]{0,120}?\b(?:shall not exceed|not to exceed|is limited to|limited to|no more than|"
                   r"maximum of|must not exceed)\s+(?P<p>\d{1,4})\s+pages", re.I)
_ROW = re.compile(r"^\s*" + _N + r"\s+[A-Za-z][A-Za-z &/,-]{1,60}?\s+(?P<p>\d{1,4})\s*(?:pages?)?\s*$")


def _num(s):
    s = (s or "").strip().upper()
    return ROMAN.get(s) or (int(s) if s.isdigit() else None)


def limits(M):
    """{volume number: pages} from the solicitation's sentences and table rows."""
    out = {}
    for it in M.items:
        t = it.get("text", "") or ""
        for m in _SENT.finditer(t):
            n = _num(m.group("n"))
            if n and n not in out:
                out[n] = int(m.group("p"))
        for line in t.splitlines() or [t]:
            m = _ROW.match(line)
            if m and _num(m.group("n")) and _num(m.group("n")) not in out:
                out[_num(m.group("n"))] = int(m.group("p"))
    return out


def _vol_no(o):
    m = re.search(r"\bvol(?:ume)?\.?\s+([IVX]{1,4}|\d{1,2})\b", f"{o.get('num', '')} {o.get('title', '')}", re.I)
    return _num(m.group(1)) if m else None


def mark(M):
    """Mark the prescribed outline as the customer's and give each volume its page limit (when not set)."""
    import compliance as C
    import pagebudget as PB
    lim = limits(M)
    n, pages = 0, {}
    for o in M.outline:
        if o.get("by") != "customer":
            o["by"] = "customer"
            n += 1
        v = _vol_no(o)
        if v and v in lim:
            lab = C.outline_label(o)
            try:
                if PB.pages(M, lab) is None:
                    PB.set_pages(M, lab, lim[v], "rfp")
                    pages[lab] = lim[v]
            except Exception:  # noqa: BLE001
                import diag
                diag.swallowed()
    if n or pages:
        M.pending = True
    return {"marked": n, "pages": pages}
