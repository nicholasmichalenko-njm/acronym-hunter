"""Every Assign decision as plain functions on a compliance matrix, without any screen (2.59.0, for the Qt edition;
the same rules as compliance_page): compliance requirement in a section (a sentence can be in several), support
(context) for requirements, the customer's, not used, combine, split, sections, links, author(s), notes, and undo.
Rules only (No AI); nothing leaves the PC.
"""
import copy
import compliance as C
import setupdoc as SD

UNDO_STEPS = 40


class Review:
    """A matrix being assigned: its decisions, an undo history and the last requirement clicked (what C supports)."""

    def __init__(self, M):
        self.M = M
        self.undo = []
        self.last_req = None

    # ------------------------------------------------------------ looking
    def item(self, iid):
        return next((it for it in self.M.items if it.get("id") == iid), None)

    def files(self):
        out = []
        for it in self.M.items:
            if it.get("file") and it["file"] not in out:
                out.append(it["file"])
        return out

    def rows_of(self, f):
        return [it for it in self.M.items if it.get("file") == f]

    def labels(self):
        return [C.outline_label(o) for o in self.M.outline]

    def related(self, it):
        """(ids, how): a requirement's support sentences ("supports"), or the requirements a support sentence backs
        up ("hosts")."""
        if it is None:
            return [], ""
        if it.get("decision") == "Keep":
            return [x["id"] for x in self.M.items if x.get("decision") == "Context" and it["id"] in C.cf_ids(x.get("context_for", ""))], "supports"
        if it.get("decision") == "Context":
            return C.cf_ids(it.get("context_for", "")), "hosts"
        return [], ""

    def counts(self):
        """{section label: compliance requirements in it}."""
        out = {}
        for it in self.M.items:
            if it.get("decision") == "Keep":
                for lab in SD.item_sections(self.M, it):
                    out[lab] = out.get(lab, 0) + 1
        return out

    # ------------------------------------------------------------ history
    def snap(self):
        self.undo.append((copy.deepcopy(self.M.items), copy.deepcopy(SD.setup_of(self.M))))
        del self.undo[:-UNDO_STEPS]

    def changed(self):
        C.link_contexts(self.M.items)
        self.M.pending = True

    def undo_last(self):
        if not self.undo:
            return False
        items, setup = self.undo.pop()
        self.M.items[:] = items
        self.M.setup = setup
        self.M.pending = True
        return True

    # ------------------------------------------------------------ decisions
    def req(self, rows, label):
        """R: compliance requirements in section label; one already in another section is put in this one too."""
        if not rows or label not in set(self.labels()):
            return 0
        self.snap()
        new = [it for it in rows if it.get("decision") != "Keep" or not it.get("map")]
        for it in new:
            SD.clear_sections(self.M, it)
        if new:
            C.assign_requirement(self.M.items, new, label)
        for it in rows:
            if it in new:
                self.M.log(it["id"], f"compliance requirement in {label}")
            elif SD.add_section(self.M, it, label):
                self.M.log(it["id"], f"also in {label}")
        if len(rows) == 1:
            self.last_req = rows[0]["id"]
        self.changed()
        return len(rows)

    def ctx(self, rows, req_ids=None):
        """C: support for req_ids, else the last requirement clicked, else the nearest requirement."""
        if not rows:
            return 0
        self.snap()
        last = self.item(self.last_req) if self.last_req else None
        if last is not None and (last.get("decision") != "Keep" or last in rows):
            last = None
        for it in rows:
            ids = list(req_ids) if req_ids else ([last["id"]] if last is not None else
                                                 [x for x in [C.default_context_for(self.M.items, it)] if x])
            SD.clear_sections(self.M, it)
            C.assign_context(self.M.items, [it], ids)
            self.M.log(it["id"], f"context for {it.get('context_for', '') or 'nothing yet'}")
        self.changed()
        return len(rows)

    def customer(self, rows):
        if not rows:
            return 0
        self.snap()
        C.assign_customer(self.M.items, rows)
        for it in rows:
            SD.clear_sections(self.M, it)
            self.M.log(it["id"], "customer's (identified, not answered)")
        self.changed()
        return len(rows)

    def clear(self, rows):
        if not rows:
            return 0
        self.snap()
        C.clear_assignment(self.M.items, rows)
        for it in rows:
            SD.clear_sections(self.M, it)
            self.M.log(it["id"], "not used (cleared)")
        self.changed()
        return len(rows)

    def combine(self, rows, places=None):
        """M: one sentence from several (they need not be next to each other); each part keeps its place."""
        if len(rows) < 2:
            return None
        self.snap()
        for r in rows:
            if not r.get("place") and places and r["id"] in places:
                r["place"] = places[r["id"]][0]
        first = C.merge_items(self.M.items, [r["id"] for r in rows])
        self.M.log(first["id"], f"merged {len(rows)} rows")
        self.changed()
        return first

    def split(self, it, at=None):
        """S: the sentence in parts at character at (else where the rules see two requirements), the same way the
        tkinter edition splits: parts get ids with a, b..., no decision; support for the old row goes to the first part.
        Returns the parts, or [] when it cannot be split there."""
        text = it.get("text", "")
        if at is not None and 0 < at < len(text) and text[:at].strip() and text[at:].strip():
            parts = [text[:at].strip(), text[at:].strip()]
        else:
            parts = C.split_text(text)
        if len(parts) < 2:
            return []
        self.snap()
        i = self.M.items.index(it)
        new = []
        for n, p in enumerate(parts):
            x = dict(it)
            x.update(text=p, id=f"{it['id']}{chr(97 + n)}", key=C.text_key(p), compound=False, decision="", context_for="",
                     draft="", draft_cf="", place="")
            new.append(x)
        self.M.items[i:i + 1] = new
        C.remap_context_for(self.M.items, it["id"], new[0]["id"])
        SD.clear_sections(self.M, it)
        self.M.log(it["id"], f"split into {len(new)}")
        self.changed()
        return new

    def add_section(self, it, label):
        if label not in set(self.labels()):
            return False
        self.snap()
        ok = SD.add_section(self.M, it, label)
        self.changed()
        return ok

    def remove_section(self, it, label):
        self.snap()
        ok = SD.remove_section(self.M, it, label)
        self.M.log(it["id"], f"removed from {label}")
        self.changed()
        return ok

    def link(self, sup, req_id):
        self.snap()
        C.assign_context(self.M.items, [sup], list(dict.fromkeys(C.cf_ids(sup.get("context_for", "")) + [req_id])))
        self.changed()

    def unlink(self, sup, req_id):
        self.snap()
        ids = [i for i in C.cf_ids(sup.get("context_for", "")) if i != req_id]
        C.assign_context(self.M.items, [sup], ids, section=None if ids else (sup.get("map") or None))
        self.M.log(sup["id"], f"support no longer for {req_id}")
        self.changed()

    def set_authors(self, rows, text):
        value = ", ".join(SD.split_names(text))
        rows = [it for it in rows if it.get("decision") in ("Keep", "Context") and (it.get("owner") or "") != value]
        if not rows:
            return 0
        self.snap()
        for it in rows:
            it["owner"] = value
            self.M.log(it["id"], f"author(s): {value or '(section lead)'}")
        self.changed()
        return len(rows)

    def set_notes(self, it, text):
        text = (text or "").strip()
        if (it.get("notes") or "").strip() == text:
            return False
        it["notes"] = text
        self.M.log(it["id"], "notes changed")
        self.changed()
        return True
