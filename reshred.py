"""The re-shred queue (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 7). On Documents > Changes, a change decided
Re-shred joins Shred's queue: its document, the version that made it, the old and the new wording, and the placed
requirement built from the old wording, if any, which shows "Changed by <version>" (flagged) until the passage is
shredded again. Shred shows "N to re-shred"; each queued passage opens with its old and new wording; Done takes it off the queue
and the flag off the requirement. Shred never waits on Changes.

Stored in <effort data>\\changes\\reshred.json (format 1). Rules only (No AI); nothing leaves the PC."""
import datetime
import getpass
import os
import uuid

FILE = os.path.join("changes", "reshred.json")
FORMAT = 1


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


class Queue:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, FILE)
        self.items = []

    def load(self):
        import workspace as W
        d = W.read_json(self.path, None) or {}
        self.items = [x for x in d.get("items", []) if isinstance(x, dict) and x.get("id")]
        return self

    def save(self):
        import workspace as W
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        W.write_json(self.path, {"format": FORMAT, "items": self.items})

    def add(self, pk, key, doc, label, old="", new="", section="", target="", who=None):
        """Queue a passage (once per change). Returns the entry."""
        for x in self.items:
            if x["pk"] == pk and x["key"] == key and not x.get("done"):
                return x
        e = {"id": uuid.uuid4().hex[:10], "pk": pk, "key": key, "doc": doc, "label": label, "old": old or "", "new": new or "",
             "section": section or "", "target": target or "", "who": who or getpass.getuser(), "when": _now(), "done": ""}
        self.items.append(e)
        self.save()
        return e

    def open_items(self):
        return [x for x in self.items if not x.get("done")]

    def get(self, qid):
        return next((x for x in self.items if x["id"] == qid), None)

    def done(self, qid, who=None):
        x = self.get(qid)
        if x is None or x.get("done"):
            return None
        x["done"] = f"{_now()} {who or getpass.getuser()}"
        self.save()
        return x

    def drop(self, pk, key):
        """Undo of a Re-shred decision: the open entry leaves the queue. Returns it or None."""
        x = next((x for x in self.items if x["pk"] == pk and x["key"] == key and not x.get("done")), None)
        if x is not None:
            self.items.remove(x)
            self.save()
        return x


def flagged(data_dir):
    """{requirement id: "Changed by <version>"}: the placed requirements built from a passage still to re-shred."""
    return {x["target"]: f"Changed by {x['label']}" for x in Queue(data_dir).load().open_items() if x.get("target")}
