"""Marks on the page (3.18.1): which sentences something was captured from in Review (a contact, a submission or
formatting rule, an acronym, a customer question, a key date, a graphic need, the More captures) or had a task or a team
question made on it. Review draws those sentences with the capture color and names what was captured in the margin, so
a person sees what has been looked at. Kept in the effort's data ("page_marks": {sentence id: [kinds]}); tasks and
questions made before 3.18.1 are found in the effort record."""

TAG = {"contact": "POC", "submit": "SUBMIT", "format": "FORMAT", "acronym": "ACRONYM", "question": "CUST Q", "keydate": "DATE",
       "factor": "FACTOR", "pagelimit": "PAGES", "deliverable": "DELIV", "detail": "DETAIL", "hot": "HOT", "graphic": "GRAPHIC",
       "task": "TASK", "tquestion": "TEAM Q", "note": "NOTE"}
KEY = "page_marks"


def load(ws, record=None):
    """{sentence id: [kinds]} from the effort's data, plus tasks and questions in the record made on a sentence."""
    out = {}
    raw = (ws.get(KEY) if ws is not None else None) or {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, list):
                out[str(k)] = [x for x in v if x in TAG]
    if record is not None:
        try:
            for t in record.data.get("tasks", []):
                about = str(t.get("about", "") or "")
                if about.startswith("sentence:"):
                    _add(out, about.split(":", 1)[1], "task")
            for n in record.data.get("notes", []):
                if n.get("on") == "requirement" and n.get("on_id") and n.get("question"):
                    _add(out, n["on_id"], "tquestion")
        except (AttributeError, TypeError):
            pass
    return out


def _add(marks, sid, kind):
    if sid and kind in TAG:
        got = marks.setdefault(str(sid), [])
        if kind not in got:
            got.append(kind)


def add(ws, marks, sids, kind):
    """Mark these sentences with what was captured from them, and keep it with the effort. Returns how many."""
    n = 0
    for sid in sids:
        if sid:
            _add(marks, sid, kind); n += 1
    if n and ws is not None:
        mine = ws.get(KEY)
        mine = mine if isinstance(mine, dict) else {}
        for sid in sids:
            if sid:
                got = mine.setdefault(str(sid), [])
                if kind not in got:
                    got.append(kind)
        ws.set(KEY, mine)
    return n


def text(kinds):
    """The margin text: what was captured, in the order it was."""
    return ", ".join(TAG[k] for k in kinds if k in TAG)
