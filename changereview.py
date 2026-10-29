"""Change review (2.85.0): Compare with a finish line. Every change between two versions of a customer document gets a
decision, and each decision lands where people work:
- updates:  a compliance requirement takes the new wording; the old wording stays in its history; the requirement is
            marked "changed, owner to confirm" until its owner confirms the answer still fits;
- new:      the sentence becomes a compliance requirement in a section (done by the window, which owns the matrix);
- context:  context for a requirement (through the library's attachments, ctxdocs);
- removes:  the requirement is marked removed by that version (never deleted; its history stays);
- task, question, note: in the effort record, quoting the change;
- rule:     a submission rule (page limit, due date, format...) takes the new value: Submission rules shows Was and
            Now, the deliverables are checked again, and a new due date becomes the effort's;
- none:     no action, with the reason ("editorial"), so the question never comes back.
Several decisions can apply to one change. Each records who, when and why.

A change is keyed by what it is (kind, old and new wording, and which time it occurs), so the decisions stay with it
however often the two versions are compared. Requirement history (lineage): every update, removal and confirmation of
a requirement, from the RFP through each amendment. Stored in <effort data>\\changes\\review.json. Rules only (No AI);
nothing leaves the PC.
"""
import datetime, getpass, hashlib, os, uuid

KINDS = (("updates", "Updates a requirement"), ("new", "New requirement"), ("rule", "Updates a submission rule"),
         ("context", "Context for a requirement"),
         ("removes", "Removes a requirement"), ("task", "Task"), ("question", "Question for the customer"),
         ("note", "Note"), ("none", "No action"))
KIND_NAMES = dict(KINDS)
NEEDS_TARGET = {"updates", "context", "removes", "new"}


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def keyed(rows):
    """Give every row a key that stays the same however often the two versions are compared."""
    seen = {}
    for r in rows:
        base = f"{r['kind']}|{r.get('old', '')}|{r.get('new', '')}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        r["key"] = hashlib.sha1(f"{base}|{n}".encode("utf-8")).hexdigest()[:14]
    return rows


def pair_key(va, vb):
    return f"{va['id']}>{vb['id']}"


class Review:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "changes", "review.json")
        self.pairs, self.lineage = {}, {}

    def load(self):
        import workspace as W
        d = W.read_json(self.path, None) or {}
        self.pairs = d.get("pairs", {}) if isinstance(d.get("pairs"), dict) else {}
        self.lineage = d.get("lineage", {}) if isinstance(d.get("lineage"), dict) else {}
        return self

    def save(self):
        import workspace as W
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        W.write_json(self.path, {"v": 1, "pairs": self.pairs, "lineage": self.lineage})

    # ------------------------------------------------------------ a comparison
    def opened(self, d, va, vb, rows, save=True):
        """Record what a comparison holds (its changes), for the counts on the dashboard and Effort home."""
        p = self.pairs.setdefault(pair_key(va, vb), {"doc": d["id"], "from": va["id"], "to": vb["id"], "decisions": {}})
        p.update(doc=d["id"], name=d.get("name", ""), labels=[va.get("label", ""), vb.get("label", "")],
                 changes=[r["key"] for r in rows if r["kind"] != "same"])
        if save:
            self.save()
        return p

    def decisions(self, pk, key):
        return (self.pairs.get(pk) or {}).get("decisions", {}).get(key, [])

    def decide(self, pk, key, kind, target="", why="", ref="", who=None, save=True):
        if kind not in KIND_NAMES:
            return None
        p = self.pairs.setdefault(pk, {"decisions": {}})
        lst = p.setdefault("decisions", {}).setdefault(key, [])
        for x in lst:
            if x["kind"] == kind and x.get("target", "") == (target or ""):
                return x
        dec = {"id": uuid.uuid4().hex[:10], "kind": kind, "target": target or "", "why": " ".join((why or "").split())[:300],
               "ref": ref or "", "who": who or getpass.getuser(), "when": _now()}
        lst.append(dec)
        if save:
            self.save()
        return dec

    def undo(self, pk, key, dec_id):
        lst = self.decisions(pk, key)
        keep = [x for x in lst if x["id"] != dec_id]
        if len(keep) == len(lst):
            return None
        gone = next(x for x in lst if x["id"] == dec_id)
        self.pairs[pk]["decisions"][key] = keep
        self.save()
        return gone

    def progress(self, pk, rows=None):
        """(decided, changes) for a comparison."""
        p = self.pairs.get(pk) or {}
        keys = [r["key"] for r in rows if r["kind"] != "same"] if rows is not None else p.get("changes", [])
        dec = p.get("decisions", {})
        return sum(1 for k in keys if dec.get(k)), len(keys)

    def undecided(self):
        """[(document name, from and to labels, changes still to decide)] for every comparison opened."""
        out = []
        for p in self.pairs.values():
            d, n = self.progress_of(p)
            if n - d > 0:
                out.append((p.get("name", ""), " to ".join(p.get("labels", [])), n - d))
        return out

    @staticmethod
    def progress_of(p):
        dec = p.get("decisions", {})
        keys = p.get("changes", [])
        return sum(1 for k in keys if dec.get(k)), len(keys)

    # ------------------------------------------------------------ requirement history
    def add_history(self, req_id, kind, old="", new="", doc="", label="", who=None, save=True):
        e = {"id": uuid.uuid4().hex[:10], "kind": kind, "old": old, "new": new, "doc": doc, "label": label,
             "who": who or getpass.getuser(), "when": _now(), "confirmed": ""}
        self.lineage.setdefault(req_id, []).append(e)
        if save:
            self.save()
        return e

    def history(self, req_id):
        return self.lineage.get(req_id, [])

    def awaiting(self):
        """Requirements changed or removed by a version whose owner has not confirmed the answer still fits."""
        return [r for r, es in self.lineage.items() if es and es[-1]["kind"] in ("updated", "removed") and not es[-1].get("confirmed")]

    def confirm(self, req_id, who=None):
        es = self.lineage.get(req_id) or []
        if not es or es[-1].get("confirmed"):
            return False
        es[-1]["confirmed"] = f"{datetime.date.today().isoformat()} {who or getpass.getuser()}"
        self.save()
        return True

    def drop_history(self, req_id, entry_id):
        es = self.lineage.get(req_id) or []
        keep = [e for e in es if e["id"] != entry_id]
        if len(keep) != len(es):
            self.lineage[req_id] = keep
            self.save()
            return True
        return False


# ------------------------------------------------------------ what decisions do to the matrix
def apply_update(M, rv, req_id, new_text, doc_name, label, who=None):
    """The requirement takes the new wording; the old wording goes to its history; the owner is to confirm."""
    import compliance as C
    it = next((x for x in M.items if x.get("id") == req_id), None)
    if it is None or not new_text:
        return None
    old = it.get("text", "")
    it["text"] = " ".join(new_text.split())
    it["key"] = C.text_key(it["text"])
    it["new"] = f"Changed by {doc_name} {label}: owner to confirm"
    M.log(req_id, f"wording changed by {doc_name} {label}")
    M.pending = True
    return rv.add_history(req_id, "updated", old, it["text"], doc_name, label, who)


def apply_remove(M, rv, req_id, doc_name, label, who=None):
    """Marked removed by the version: never deleted; its history stays."""
    it = next((x for x in M.items if x.get("id") == req_id), None)
    if it is None:
        return None
    it["new"] = f"Removed by {doc_name} {label}"
    M.log(req_id, f"removed by {doc_name} {label}")
    M.pending = True
    return rv.add_history(req_id, "removed", it.get("text", ""), "", doc_name, label, who)


def undo_effect(M, rv, dec):
    """Taking a decision off undoes what it did to the matrix (the requirement's wording and mark come back)."""
    req = dec.get("target", "")
    it = next((x for x in M.items if x.get("id") == req), None) if M is not None else None
    es = rv.lineage.get(req) or []
    e = next((x for x in reversed(es) if x["id"] == dec.get("ref")), None)
    if it is None or e is None:
        return False
    if e["kind"] == "updated":
        import compliance as C
        it["text"] = e["old"]
        it["key"] = C.text_key(e["old"])
    it["new"] = ""
    M.log(req, "change decision taken off")
    M.pending = True
    rv.drop_history(req, e["id"])
    return True
