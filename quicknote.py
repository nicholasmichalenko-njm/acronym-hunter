"""Capture from anywhere (3.63.0): a quick note from any page (Ctrl+Shift+N, or Note in the top bar), sent at once to
the effort's notes or a deliverable's discussion, or left in Notes to sort and sent later. Kept in the effort record
("inbox"); a sent note leaves the inbox. Rules only; nothing leaves the PC."""
import datetime


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def inbox(rec):
    return rec.data.setdefault("inbox", [])


def add(rec, text, who=None, tags=""):
    import effortrec as ER
    text = (text or "").strip()
    if not text:
        return None
    n = {"id": ER._id(), "text": text, "at": _now(), "by": ER._who(who), "tags": " ".join((tags or "").split())}
    inbox(rec).append(n)
    rec.save()
    return n["id"]


def targets(rec, sections=()):
    """[(key, label)]: the effort, an open question, each deliverable, and (3.83.0) each section of the structure."""
    import deliverables as DL
    out = [("effort", "The effort's notes"), ("question", "An open question for the team")]
    out += [(f"deliverable:{d['id']}", f"Deliverable: {d['name']}") for d in DL.items(rec)]
    out += [(f"section:{s}", f"Section: {s}") for s in sections if s]
    return out


def send(rec, text, target, who=None):
    """Put a note where it belongs now. Returns what it became, or None."""
    text = (text or "").strip()
    if not text:
        return None
    if target in ("effort", "question"):
        return rec.add_note(text, question=target == "question", who=who)
    if target.startswith("section:"):              # 3.83.0: a note pointed at a section of the structure
        label = target.split(":", 1)[1]
        return rec.add_note(text, on="section", on_id=label, label=label, who=who) if label else None
    if target.startswith("deliverable:"):
        import delivmore as DM
        return DM.post(rec, target.split(":", 1)[1], text, who=who)
    return None


def send_from_inbox(rec, nid, target, who=None):
    n = next((x for x in inbox(rec) if x["id"] == nid), None)
    if n is None:
        return None
    got = send(rec, n["text"], target, who=who)
    if got:
        inbox(rec).remove(n)
        rec.save()
    return got


def remove(rec, nid):
    n = next((x for x in inbox(rec) if x["id"] == nid), None)
    if n is None:
        return False
    inbox(rec).remove(n)
    rec.save()
    return True
